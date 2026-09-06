"""Cleaning rules and the leakage-safe preprocessing pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from data import (
    ALL_FEATURES,
    GRADE_ORDER,
    NOMINAL_FEATURES,
    NUMERIC_FEATURES,
    ORDINAL_FEATURES,
    UNDERWRITING_FEATURES,
)

MAX_PLAUSIBLE_AGE = 100
MAX_PLAUSIBLE_EMP_LENGTH = 60


def clean(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Drop records that are impossible rather than merely extreme.

    Only physically impossible values are removed (ages of 123 and 144, employment
    histories longer than a working life).  Genuine but extreme values — a
    $6M income, a loan worth 83% of income — are kept: they are real applicants
    and the model has to cope with them.
    """
    before = len(frame)
    impossible_age = frame["person_age"] > MAX_PLAUSIBLE_AGE
    impossible_emp = frame["person_emp_length"] > MAX_PLAUSIBLE_EMP_LENGTH
    cleaned = frame.loc[~(impossible_age | impossible_emp)].reset_index(drop=True)
    report = {
        "rows_before": before,
        "impossible_age": int(impossible_age.sum()),
        "impossible_emp_length": int(impossible_emp.sum()),
        "rows_after": len(cleaned),
    }
    return cleaned, report


def feature_columns(include_underwriting: bool = True) -> list[str]:
    """The model's input columns, optionally without the lender's own risk grade."""
    if include_underwriting:
        return list(ALL_FEATURES)
    return [c for c in ALL_FEATURES if c not in UNDERWRITING_FEATURES]


def build_preprocessor(columns: list[str], scale: bool = True) -> ColumnTransformer:
    """Impute, encode and (optionally) scale — all fitted inside each CV fold.

    `scale=True` is required by the distance- and penalty-based learners
    (logistic regression, k-NN); tree ensembles are invariant to it.
    """
    numeric = [c for c in NUMERIC_FEATURES if c in columns]
    nominal = [c for c in NOMINAL_FEATURES if c in columns]
    ordinal = [c for c in ORDINAL_FEATURES if c in columns]

    numeric_steps: list[tuple[str, object]] = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))

    # loan_grade is genuinely ordered (A is better than G), so an ordinal code
    # preserves information a one-hot encoding would throw away.
    ordinal_steps: list[tuple[str, object]] = [
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("encode", OrdinalEncoder(categories=[GRADE_ORDER] * len(ordinal))),
    ]
    if scale:
        ordinal_steps.append(("scale", StandardScaler()))

    transformers = []
    if numeric:
        transformers.append(("num", Pipeline(numeric_steps), numeric))
    if ordinal:
        transformers.append(("ord", Pipeline(ordinal_steps), ordinal))
    if nominal:
        transformers.append(
            (
                "nom",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore", drop="if_binary")),
                    ]
                ),
                nominal,
            )
        )
    return ColumnTransformer(transformers, remainder="drop")


def feature_names(preprocessor: ColumnTransformer) -> list[str]:
    return [n.split("__", 1)[-1] for n in preprocessor.get_feature_names_out()]


def make_pipeline(columns: list[str], estimator, scale: bool = True) -> Pipeline:
    return Pipeline([("prep", build_preprocessor(columns, scale=scale)), ("clf", estimator)])
