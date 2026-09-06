"""Loading for the Kaggle credit risk dataset, with a calibrated stand-in.

`load_credit_risk` returns the real Kaggle file whenever it is present on disk.
When it is not, it falls back to `synthesize_credit_risk`, which draws from a
generative model hand-calibrated to the published marginals and conditional
default rates of the real file.  The fallback exists so the pipeline is runnable
in environments with no network access to Kaggle; it is not a substitute for the
real data, and every report states which source produced it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REAL_CSV = DATA_DIR / "credit_risk_dataset.csv"

TARGET = "loan_status"

NUMERIC_FEATURES = [
    "person_age",
    "person_income",
    "person_emp_length",
    "loan_amnt",
    "loan_int_rate",
    "loan_percent_income",
    "cb_person_cred_hist_length",
]
NOMINAL_FEATURES = ["person_home_ownership", "loan_intent", "cb_person_default_on_file"]
ORDINAL_FEATURES = ["loan_grade"]
GRADE_ORDER = ["A", "B", "C", "D", "E", "F", "G"]

# Features the lender only knows *after* it has priced the loan.  Kept separate
# so the modelling code can quantify how much of the signal they carry.
UNDERWRITING_FEATURES = ["loan_grade", "loan_int_rate"]

ALL_FEATURES = NUMERIC_FEATURES + NOMINAL_FEATURES + ORDINAL_FEATURES


@dataclass
class Dataset:
    frame: pd.DataFrame
    source: str  # "kaggle" or "synthetic"

    @property
    def is_real(self) -> bool:
        return self.source == "kaggle"

    @property
    def X(self) -> pd.DataFrame:
        return self.frame[ALL_FEATURES]

    @property
    def y(self) -> pd.Series:
        return self.frame[TARGET]


def load_credit_risk(path: Path | None = None) -> Dataset:
    """Read the real CSV if available, otherwise synthesize a stand-in."""
    path = path or REAL_CSV
    if path.exists():
        frame = pd.read_csv(path)
        missing = set(ALL_FEATURES + [TARGET]) - set(frame.columns)
        if missing:
            raise ValueError(f"{path} is missing expected columns: {sorted(missing)}")
        return Dataset(frame=frame, source="kaggle")
    return Dataset(frame=synthesize_credit_risk(), source="synthetic")


# --------------------------------------------------------------------------- #
# Stand-in generator
# --------------------------------------------------------------------------- #

# Marginals and conditional default rates below are the published summary
# statistics of laotse/credit-risk-dataset (32,581 rows, 21.8% default rate).
_HOME_OWNERSHIP_P = {"RENT": 0.505, "MORTGAGE": 0.413, "OWN": 0.079, "OTHER": 0.003}
_INTENT_P = {
    "EDUCATION": 0.199,
    "MEDICAL": 0.186,
    "VENTURE": 0.175,
    "PERSONAL": 0.169,
    "DEBTCONSOLIDATION": 0.159,
    "HOMEIMPROVEMENT": 0.112,
}
# Mean APR the lender charges at each internal grade.
_GRADE_RATE = {"A": 7.33, "B": 10.99, "C": 13.47, "D": 15.36, "E": 17.01, "F": 18.61, "G": 20.25}
# Grade-level log-odds of default, solved so the simulated conditional default
# rates land on the real file's (A 9.9% ... D 59.1% ... G 98.5%).
_GRADE_DEFAULT_LOGIT = {
    "A": -2.561,
    "B": -1.968,
    "C": -1.575,
    "D": 0.488,
    "E": 0.736,
    "F": 1.214,
    "G": 5.002,
}

N_ROWS = 32_581


def synthesize_credit_risk(n: int = N_ROWS, seed: int = 20240517) -> pd.DataFrame:
    """Draw a frame with the real file's schema, marginals and dependencies.

    The generative story mirrors how the data arises: applicant attributes come
    first, the lender then assigns a grade (and therefore an interest rate) from
    those attributes, and repayment depends on both.
    """
    rng = np.random.default_rng(seed)

    # --- applicant attributes -------------------------------------------- #
    person_age = np.clip(np.round(20 + rng.gamma(shape=2.6, scale=3.1, size=n)), 20, 94).astype(int)
    # A handful of impossible ages survive in the real file; keep them so the
    # cleaning step in the pipeline has something to do.
    person_age[rng.choice(n, size=5, replace=False)] = rng.choice([123, 144], size=5)

    log_income = rng.normal(loc=11.03, scale=0.60, size=n) + 0.011 * (person_age - 27)
    person_income = np.clip(np.round(np.exp(log_income), -2), 4_000, 6_000_000).astype(int)

    emp_length = np.clip(rng.gamma(shape=1.7, scale=2.9, size=n), 0, 41)
    emp_length = np.minimum(emp_length, np.maximum(person_age - 18, 0)).round(1)
    emp_length[rng.choice(n, size=int(0.0275 * n), replace=False)] = np.nan  # 895 NaNs in the real file
    emp_length[rng.choice(n, size=2, replace=False)] = 123.0  # the two known outliers

    home = rng.choice(list(_HOME_OWNERSHIP_P), size=n, p=list(_HOME_OWNERSHIP_P.values()))
    # Mortgage holders skew older and richer; renters younger.
    mortgage_pull = (person_age > 30) & (person_income > 60_000) & (rng.random(n) < 0.45)
    home[mortgage_pull] = "MORTGAGE"
    rent_pull = (person_age < 26) & (rng.random(n) < 0.45)
    home[rent_pull] = "RENT"

    intent = rng.choice(list(_INTENT_P), size=n, p=list(_INTENT_P.values()))

    # Credit history starts a couple of years after adulthood: r(age, hist) ~ .86
    cred_hist = np.clip(
        np.round((person_age - 18) * rng.uniform(0.25, 0.75, size=n) + rng.normal(2, 1.1, size=n)),
        2,
        30,
    ).astype(int)

    prior_default_logit = -1.9 + 0.55 * (person_income < 45_000) + 0.35 * (home == "RENT") - 0.02 * cred_hist
    prior_default = np.where(rng.random(n) < _sigmoid(prior_default_logit), "Y", "N")

    loan_amnt = np.clip(
        np.round(np.exp(rng.normal(9.05, 0.62, size=n) + 0.28 * (log_income - 11.03)), -2), 500, 35_000
    ).astype(int)
    loan_percent_income = np.round(loan_amnt / person_income, 2)
    loan_amnt[loan_percent_income > 0.83] = np.round(
        person_income[loan_percent_income > 0.83] * 0.83, -2
    ).astype(int)
    loan_percent_income = np.clip(np.round(loan_amnt / person_income, 2), 0.0, 0.83)

    # --- the lender's own risk assessment --------------------------------- #
    # Grade is a monotone function of applicant risk, so it is a *consequence*
    # of the features above rather than an independent measurement.
    grade_score = (
        1.55 * loan_percent_income
        + 0.62 * (prior_default == "Y")
        + 0.30 * (home == "RENT")
        - 0.35 * _zscore(np.log(person_income))
        - 0.10 * _zscore(np.nan_to_num(emp_length, nan=np.nanmedian(emp_length)))
        + rng.normal(0, 0.62, size=n)
    )
    cuts = np.quantile(grade_score, [0.331, 0.651, 0.850, 0.962, 0.992, 0.998])
    loan_grade = np.array(GRADE_ORDER)[np.searchsorted(cuts, grade_score)]

    loan_int_rate = np.array([_GRADE_RATE[g] for g in loan_grade]) + rng.normal(0, 0.95, size=n)
    loan_int_rate = np.clip(loan_int_rate, 5.42, 23.22).round(2)
    # 3,116 interest rates are missing in the real file.
    loan_int_rate[rng.choice(n, size=int(0.0956 * n), replace=False)] = np.nan

    # --- repayment outcome ------------------------------------------------ #
    # Everything the lender did not fold into the grade enters as within-grade
    # variation, so `_GRADE_DEFAULT_LOGIT` carries the pure grade effect and the
    # residual term carries the rest.
    residual = (
        4.10 * loan_percent_income
        + 0.95 * (home == "RENT")
        - 0.85 * (home == "OWN")
        + 0.42 * (prior_default == "Y")
        - 0.55 * _zscore(np.log(person_income))
        - 0.09 * _zscore(np.nan_to_num(emp_length, nan=np.nanmedian(emp_length)))
        + 0.22 * (intent == "DEBTCONSOLIDATION")
        + 0.16 * (intent == "MEDICAL")
        - 0.20 * (intent == "VENTURE")
    )
    residual -= pd.Series(residual).groupby(loan_grade).transform("mean").to_numpy()

    default_logit = (
        np.array([_GRADE_DEFAULT_LOGIT[g] for g in loan_grade])
        + residual
        + rng.normal(0, 0.45, size=n)
    )
    loan_status = (rng.random(n) < _sigmoid(default_logit)).astype(int)

    return pd.DataFrame(
        {
            "person_age": person_age,
            "person_income": person_income,
            "person_home_ownership": home,
            "person_emp_length": emp_length,
            "loan_intent": intent,
            "loan_grade": loan_grade,
            "loan_amnt": loan_amnt,
            "loan_int_rate": loan_int_rate,
            "loan_status": loan_status,
            "loan_percent_income": loan_percent_income,
            "cb_person_default_on_file": prior_default,
            "cb_person_cred_hist_length": cred_hist,
        }
    )


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _zscore(x: np.ndarray) -> np.ndarray:
    return (x - np.nanmean(x)) / np.nanstd(x)
