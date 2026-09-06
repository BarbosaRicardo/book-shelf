"""Feature exploration: what the columns are, and how they relate (Q1 and Q2)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif

from data import GRADE_ORDER, NOMINAL_FEATURES, NUMERIC_FEATURES, ORDINAL_FEATURES, TARGET
from preprocess import build_preprocessor, feature_columns, feature_names

CATEGORICALS = NOMINAL_FEATURES + ORDINAL_FEATURES


def profile(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-column type, cardinality, missingness — the 'what is in here' table."""
    rows = []
    for col in frame.columns:
        s = frame[col]
        rows.append(
            {
                "column": col,
                "dtype": str(s.dtype),
                "n_unique": int(s.nunique(dropna=True)),
                "missing": int(s.isna().sum()),
                "missing_pct": round(100 * s.isna().mean(), 2),
                "example": _example(s),
            }
        )
    return pd.DataFrame(rows)


def _example(s: pd.Series):
    v = s.dropna()
    return v.iloc[0] if len(v) else None


def target_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Score every column on how well it could serve as a supervised label.

    A usable label has to be (a) low-cardinality or binary, (b) an *outcome*
    rather than an input, and (c) known only after the fact.  Only the
    cardinality part can be measured; the rest is judgement, recorded here.
    """
    rows = []
    for col in frame.columns:
        s = frame[col]
        n_unique = int(s.nunique(dropna=True))
        rows.append(
            {
                "column": col,
                "n_unique": n_unique,
                "binary": n_unique == 2,
                "kind": _semantic_kind(col),
            }
        )
    return pd.DataFrame(rows).sort_values(["kind", "n_unique"]).reset_index(drop=True)


def _semantic_kind(col: str) -> str:
    if col == TARGET:
        return "outcome"
    if col in {"loan_grade", "loan_int_rate"}:
        return "lender decision"
    if col.startswith("cb_"):
        return "credit bureau attribute"
    if col.startswith("person_"):
        return "applicant attribute"
    return "loan application term"


def association_with_target(frame: pd.DataFrame) -> pd.DataFrame:
    """One comparable strength-of-relationship number per feature.

    Point-biserial correlation for numeric columns, Cramer's V for categoricals,
    plus mutual information on the encoded matrix so the two families are
    directly comparable.
    """
    y = frame[TARGET]
    rows = []
    for col in NUMERIC_FEATURES:
        s = frame[col]
        mask = s.notna()
        rows.append(
            {
                "feature": col,
                "type": "numeric",
                "statistic": "point-biserial r",
                "value": round(float(np.corrcoef(s[mask], y[mask])[0, 1]), 3),
            }
        )
    for col in CATEGORICALS:
        rows.append(
            {
                "feature": col,
                "type": "categorical",
                "statistic": "Cramer's V",
                "value": round(cramers_v(frame[col], y), 3),
            }
        )

    cols = feature_columns()
    prep = build_preprocessor(cols, scale=False)
    X = prep.fit_transform(frame[cols])
    mi = mutual_info_classif(X, y, random_state=0)
    mi_by_name = dict(zip(feature_names(prep), mi))
    # One-hot expands a categorical into several columns; take the total.
    grouped: dict[str, float] = {}
    for name, value in mi_by_name.items():
        base = next((c for c in cols if name == c or name.startswith(c + "_")), name)
        grouped[base] = grouped.get(base, 0.0) + value

    out = pd.DataFrame(rows)
    out["mutual_info"] = out["feature"].map(lambda c: round(grouped.get(c, float("nan")), 4))
    return out.reindex(out["value"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def cramers_v(x: pd.Series, y: pd.Series) -> float:
    """Bias-corrected Cramer's V between two categorical series."""
    table = pd.crosstab(x, y).to_numpy()
    n = table.sum()
    if n == 0:
        return float("nan")
    row = table.sum(axis=1, keepdims=True)
    col = table.sum(axis=0, keepdims=True)
    expected = row @ col / n
    chi2 = float(((table - expected) ** 2 / np.where(expected == 0, np.nan, expected)).sum())
    phi2 = chi2 / n
    r, k = table.shape
    phi2_corr = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    r_corr = r - (r - 1) ** 2 / (n - 1)
    k_corr = k - (k - 1) ** 2 / (n - 1)
    denom = min(k_corr - 1, r_corr - 1)
    return float(np.sqrt(phi2_corr / denom)) if denom > 0 else float("nan")


def default_rate_by_category(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out = {}
    for col in CATEGORICALS:
        t = frame.groupby(col)[TARGET].agg(n="size", default_rate="mean")
        t["default_rate"] = t["default_rate"].round(3)
        t["share"] = (t["n"] / len(frame)).round(3)
        if col == "loan_grade":
            t = t.reindex([g for g in GRADE_ORDER if g in t.index])
        out[col] = t.reset_index()
    return out


def numeric_correlations(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[NUMERIC_FEATURES + [TARGET]].corr(method="spearman").round(3)


def redundancy_check(frame: pd.DataFrame) -> pd.DataFrame:
    """Pairs of features that carry the same information.

    `loan_percent_income` is loan_amnt / person_income by construction, and
    `loan_int_rate` is essentially a lookup on `loan_grade` — both matter for how
    coefficients should be read.
    """
    pairs = [
        ("loan_percent_income", "loan_amnt"),
        ("loan_percent_income", "person_income"),
        ("loan_int_rate", "loan_grade"),
        ("person_age", "cb_person_cred_hist_length"),
    ]
    rows = []
    for a, b in pairs:
        if b == "loan_grade":
            codes = frame[b].map({g: i for i, g in enumerate(GRADE_ORDER)})
            mask = frame[a].notna() & codes.notna()
            rho = float(frame.loc[mask, a].corr(codes[mask], method="spearman"))
            note = "interest rate is priced off the grade"
        else:
            mask = frame[a].notna() & frame[b].notna()
            rho = float(frame.loc[mask, a].corr(frame.loc[mask, b], method="spearman"))
            note = {
                "loan_amnt": "numerator of the ratio",
                "person_income": "denominator of the ratio",
                "cb_person_cred_hist_length": "history cannot start before adulthood",
            }[b]
        rows.append({"feature_a": a, "feature_b": b, "spearman_rho": round(rho, 3), "why": note})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #

def write_figures(frame: pd.DataFrame, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = [
        _fig_target_balance(frame, out_dir / "01_target_balance.png"),
        _fig_default_by_category(frame, out_dir / "02_default_rate_by_category.png"),
        _fig_numeric_distributions(frame, out_dir / "03_numeric_by_outcome.png"),
        _fig_correlation(frame, out_dir / "04_spearman_correlation.png"),
    ]
    return written


def _fig_target_balance(frame: pd.DataFrame, path: Path) -> Path:
    counts = frame[TARGET].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(4.5, 3.6))
    ax.bar(["repaid (0)", "defaulted (1)"], counts.to_numpy(), color=["#4C78A8", "#E45756"])
    for i, v in enumerate(counts):
        ax.text(i, v, f"{v:,}\n{v / len(frame):.1%}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("applications")
    ax.set_title("loan_status is imbalanced ~78/22")
    ax.set_ylim(0, counts.max() * 1.2)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def _fig_default_by_category(frame: pd.DataFrame, path: Path) -> Path:
    tables = default_rate_by_category(frame)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for ax, (col, t) in zip(axes.ravel(), tables.items()):
        ax.bar(t[col].astype(str), t["default_rate"], color="#4C78A8")
        ax.axhline(frame[TARGET].mean(), ls="--", c="#E45756", lw=1, label="overall rate")
        ax.set_title(col, fontsize=10)
        ax.set_ylabel("default rate")
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
        ax.legend(fontsize=7)
    fig.suptitle("Default rate by category")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def _fig_numeric_distributions(frame: pd.DataFrame, path: Path) -> Path:
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.5))
    for ax, col in zip(axes.ravel(), NUMERIC_FEATURES):
        data = [frame.loc[frame[TARGET] == k, col].dropna() for k in (0, 1)]
        if col in {"person_income", "loan_amnt"}:
            data = [np.log10(d[d > 0]) for d in data]
            ax.set_xlabel(f"log10({col})", fontsize=8)
        else:
            ax.set_xlabel(col, fontsize=8)
        ax.hist(data[0], bins=40, alpha=0.6, density=True, label="repaid", color="#4C78A8")
        ax.hist(data[1], bins=40, alpha=0.6, density=True, label="defaulted", color="#E45756")
        ax.set_yticks([])
    axes.ravel()[-1].axis("off")
    axes.ravel()[0].legend(fontsize=8)
    fig.suptitle("Numeric features by repayment outcome")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def _fig_correlation(frame: pd.DataFrame, path: Path) -> Path:
    corr = numeric_correlations(frame)
    fig, ax = plt.subplots(figsize=(7.2, 6))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(corr)), corr.index, fontsize=8)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("Spearman correlation")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path
