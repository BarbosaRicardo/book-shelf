"""Q6: how much of the reported performance would survive new applicants.

Four independent checks: nested cross-validation (is the tuned score honest?),
a learning curve (is 32k rows enough?), bootstrap intervals on the held-out set
(how precise is the estimate?), and subgroup / seed stress tests (does it hold
away from the bulk of the data?).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, learning_curve

from experiments import PRIMARY_METRIC, RANDOM_STATE, run_search


def nested_cv(spec, X, y, columns, outer_splits=5, inner_splits=3, n_iter=10, n_jobs=-1):
    """Score the *whole procedure* — tuning included — on data the search never saw.

    A single `GridSearchCV.best_score_` is optimistically biased: the same folds
    chose the hyperparameters and reported the score.  Wrapping the search in an
    outer loop removes that bias.
    """
    spec = _with_budget(spec, n_iter)
    inner = StratifiedKFold(n_splits=inner_splits, shuffle=True, random_state=RANDOM_STATE)
    outer = StratifiedKFold(n_splits=outer_splits, shuffle=True, random_state=RANDOM_STATE)
    search = run_search(spec, X, y, columns, cv=inner, n_jobs=1)
    scores = cross_val_score(
        search, X[columns], y, cv=outer, scoring=PRIMARY_METRIC, n_jobs=n_jobs
    )
    return {
        "model": spec.name,
        "outer_scores": [round(float(s), 4) for s in scores],
        "mean": round(float(scores.mean()), 4),
        "std": round(float(scores.std()), 4),
    }


def _with_budget(spec, n_iter):
    import copy

    spec = copy.copy(spec)
    spec.strategy = "random"
    spec.n_iter = n_iter
    return spec


def seed_sensitivity(estimator, X, y, columns, seeds=(0, 1, 7, 13, 42), n_jobs=-1):
    """Re-run cross-validation under different fold partitions."""
    out = []
    for seed in seeds:
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        s = cross_val_score(estimator, X[columns], y, cv=cv, scoring=PRIMARY_METRIC, n_jobs=n_jobs)
        out.append({"seed": seed, "mean": round(float(s.mean()), 4), "std": round(float(s.std()), 4)})
    frame = pd.DataFrame(out)
    frame.attrs["spread"] = round(float(frame["mean"].max() - frame["mean"].min()), 4)
    return frame


def learning_curve_data(estimator, X, y, columns, n_jobs=-1):
    """Does the curve still climb at 100% of the data, or has it flattened?"""
    sizes, train, test = learning_curve(
        estimator,
        X[columns],
        y,
        train_sizes=np.linspace(0.1, 1.0, 8),
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
        scoring=PRIMARY_METRIC,
        n_jobs=n_jobs,
        shuffle=True,
        random_state=RANDOM_STATE,
    )
    return pd.DataFrame(
        {
            "train_size": sizes,
            "train_mean": train.mean(axis=1).round(4),
            "cv_mean": test.mean(axis=1).round(4),
            "cv_std": test.std(axis=1).round(4),
        }
    )


def bootstrap_test_metrics(y_true, y_proba, n_boot=2000, seed=RANDOM_STATE, threshold=0.5):
    """Percentile intervals for the held-out metrics."""
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    n = len(y_true)
    stats = {"roc_auc": [], "pr_auc": [], "f1": [], "balanced_accuracy": [], "brier": []}
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yt, yp = y_true[idx], y_proba[idx]
        if yt.min() == yt.max():
            continue
        pred = (yp >= threshold).astype(int)
        stats["roc_auc"].append(roc_auc_score(yt, yp))
        stats["pr_auc"].append(average_precision_score(yt, yp))
        stats["f1"].append(f1_score(yt, pred, zero_division=0))
        stats["balanced_accuracy"].append(balanced_accuracy_score(yt, pred))
        stats["brier"].append(brier_score_loss(yt, yp))
    rows = []
    for metric, values in stats.items():
        v = np.asarray(values)
        rows.append(
            {
                "metric": metric,
                "point_estimate": round(float(_point(metric, y_true, y_proba, threshold)), 4),
                "ci_lo_2.5": round(float(np.percentile(v, 2.5)), 4),
                "ci_hi_97.5": round(float(np.percentile(v, 97.5)), 4),
                "ci_width": round(float(np.percentile(v, 97.5) - np.percentile(v, 2.5)), 4),
            }
        )
    return pd.DataFrame(rows)


def _point(metric, y_true, y_proba, threshold):
    pred = (y_proba >= threshold).astype(int)
    return {
        "roc_auc": lambda: roc_auc_score(y_true, y_proba),
        "pr_auc": lambda: average_precision_score(y_true, y_proba),
        "f1": lambda: f1_score(y_true, pred, zero_division=0),
        "balanced_accuracy": lambda: balanced_accuracy_score(y_true, pred),
        "brier": lambda: brier_score_loss(y_true, y_proba),
    }[metric]()


def subgroup_performance(frame, y_true, y_proba, columns=("loan_grade", "person_home_ownership", "loan_intent")):
    """AUC computed within slices — an average can hide a segment it fails on."""
    rows = []
    for col in columns:
        for value, idx in frame.groupby(col).groups.items():
            pos = frame.index.get_indexer(idx)
            yt = np.asarray(y_true)[pos]
            if len(np.unique(yt)) < 2 or len(yt) < 50:
                rows.append({"slice": col, "value": value, "n": len(yt), "roc_auc": None,
                             "default_rate": round(float(yt.mean()), 3)})
                continue
            rows.append(
                {
                    "slice": col,
                    "value": value,
                    "n": len(yt),
                    "roc_auc": round(float(roc_auc_score(yt, np.asarray(y_proba)[pos])), 4),
                    "default_rate": round(float(yt.mean()), 3),
                }
            )
    return pd.DataFrame(rows)


def threshold_table(y_true, y_proba, thresholds=(0.2, 0.3, 0.4, 0.5, 0.6, 0.7)):
    """Ranking quality is threshold-free; an approve/decline decision is not."""
    rows = []
    y_true = np.asarray(y_true)
    for t in thresholds:
        pred = (np.asarray(y_proba) >= t).astype(int)
        tp = int(((pred == 1) & (y_true == 1)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        fn = int(((pred == 0) & (y_true == 1)).sum())
        tn = int(((pred == 0) & (y_true == 0)).sum())
        rows.append(
            {
                "threshold": t,
                "declined_pct": round(100 * (tp + fp) / len(y_true), 1),
                "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                "recall": round(tp / (tp + fn), 3) if tp + fn else None,
                "f1": round(f1_score(y_true, pred, zero_division=0), 3),
                "defaults_caught": tp,
                "good_loans_rejected": fp,
                "defaults_missed": fn,
                "good_loans_approved": tn,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #

def plot_learning_curve(curve: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(curve["train_size"], curve["train_mean"], "o-", label="train", color="#4C78A8")
    ax.plot(curve["train_size"], curve["cv_mean"], "o-", label="cross-validated", color="#E45756")
    ax.fill_between(
        curve["train_size"],
        curve["cv_mean"] - curve["cv_std"],
        curve["cv_mean"] + curve["cv_std"],
        alpha=0.2,
        color="#E45756",
    )
    ax.set_xlabel("training examples")
    ax.set_ylabel("ROC-AUC")
    ax.set_title("Learning curve — has the data run out of signal?")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def plot_evaluation(y_true, y_proba, path: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))

    fpr, tpr, _ = roc_curve(y_true, y_proba)
    axes[0].plot(fpr, tpr, color="#4C78A8", label=f"AUC = {roc_auc_score(y_true, y_proba):.3f}")
    axes[0].plot([0, 1], [0, 1], "--", c="grey", lw=1)
    axes[0].set_xlabel("false positive rate")
    axes[0].set_ylabel("true positive rate")
    axes[0].set_title("ROC (held-out set)")
    axes[0].legend()

    prec, rec, _ = precision_recall_curve(y_true, y_proba)
    axes[1].plot(rec, prec, color="#E45756", label=f"AP = {average_precision_score(y_true, y_proba):.3f}")
    axes[1].axhline(np.mean(y_true), ls="--", c="grey", lw=1, label="base rate")
    axes[1].set_xlabel("recall")
    axes[1].set_ylabel("precision")
    axes[1].set_title("Precision-recall")
    axes[1].legend()

    frac_pos, mean_pred = calibration_curve(y_true, y_proba, n_bins=12, strategy="quantile")
    axes[2].plot(mean_pred, frac_pos, "o-", color="#54A24B")
    axes[2].plot([0, 1], [0, 1], "--", c="grey", lw=1)
    axes[2].set_xlabel("predicted probability")
    axes[2].set_ylabel("observed default rate")
    axes[2].set_title(f"Calibration (Brier = {brier_score_loss(y_true, y_proba):.4f})")

    for ax in axes:
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def plot_model_comparison(baseline: pd.DataFrame, tuned: pd.DataFrame, path: Path) -> Path:
    merged = baseline[["model", "roc_auc_mean", "roc_auc_std"]].merge(
        tuned[["model", "roc_auc_mean", "roc_auc_std"]], on="model", how="outer", suffixes=("_base", "_tuned")
    )
    merged = merged.sort_values("roc_auc_mean_tuned")
    y = np.arange(len(merged))
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.barh(y - 0.2, merged["roc_auc_mean_base"], height=0.38, xerr=merged["roc_auc_std_base"],
            label="default settings", color="#B9C6D9")
    ax.barh(y + 0.2, merged["roc_auc_mean_tuned"], height=0.38, xerr=merged["roc_auc_std_tuned"],
            label="tuned", color="#4C78A8")
    ax.set_yticks(y, merged["model"])
    ax.set_xlim(0.5, 1.0)
    ax.set_xlabel("cross-validated ROC-AUC")
    ax.set_title("What hyperparameter optimisation bought")
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path
