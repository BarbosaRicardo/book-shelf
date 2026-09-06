"""Baseline cross-validation, hyperparameter search, and gradient boosting.

Covers Q3 (three classifiers under cross-validation), Q4 (tuning three
hyperparameters of each) and Q5 (a tuned gradient-boosting model).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedKFold,
    cross_validate,
)
from sklearn.neighbors import KNeighborsClassifier
from sklearn import __version__ as SKLEARN_VERSION

from preprocess import make_pipeline


def _sklearn_at_least(major: int, minor: int) -> bool:
    parts = SKLEARN_VERSION.split(".")
    return (int(parts[0]), int(parts[1])) >= (major, minor)


# scikit-learn 1.8 deprecated LogisticRegression's `penalty` in favour of
# `l1_ratio` (0.0 = pure L2, 1.0 = pure L1).  Passing the old name on a new
# version is silently ignored, so the regularisation-type dial is named for
# whichever release is installed.
if _sklearn_at_least(1, 8):
    PENALTY_PARAM = "l1_ratio"
    PENALTY_VALUES = [0.0, 1.0]
    PENALTY_DOC = "pure L2 shrinkage (0.0) vs pure L1 sparsity (1.0)"
else:
    PENALTY_PARAM = "penalty"
    PENALTY_VALUES = ["l2", "l1"]
    PENALTY_DOC = "L2 (shrinkage) vs L1 (sparse)"

RANDOM_STATE = 42
N_SPLITS = 5

SCORING = {
    "roc_auc": "roc_auc",
    "pr_auc": "average_precision",
    "f1": "f1",
    "balanced_accuracy": "balanced_accuracy",
    "accuracy": "accuracy",
    "brier": "neg_brier_score",
}
PRIMARY_METRIC = "roc_auc"


def cv_splitter(n_splits: int = N_SPLITS) -> StratifiedKFold:
    """Stratified so every fold keeps the ~22% default rate."""
    return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)


# --------------------------------------------------------------------------- #
# Q3: three classifiers, default settings, cross-validated
# --------------------------------------------------------------------------- #

def baseline_estimators() -> dict[str, tuple[Any, bool]]:
    """Three learners with different inductive biases, plus whether they need scaling.

    Logistic regression is a linear, fully interpretable baseline; k-NN is a
    non-parametric local method; random forest is a non-linear ensemble that
    handles interactions and mixed scales.  Together they bracket the space.
    """
    return {
        "LogisticRegression": (
            LogisticRegression(max_iter=2000, random_state=RANDOM_STATE),
            True,
        ),
        "KNeighbors": (KNeighborsClassifier(n_neighbors=5, n_jobs=1), True),
        "RandomForest": (
            RandomForestClassifier(
                n_estimators=300, random_state=RANDOM_STATE, n_jobs=1
            ),
            False,
        ),
    }


def cross_validate_baselines(
    X: pd.DataFrame, y: pd.Series, columns: list[str], n_jobs: int = -1
) -> pd.DataFrame:
    rows = []
    for name, (estimator, scale) in baseline_estimators().items():
        pipe = make_pipeline(columns, estimator, scale=scale)
        start = time.perf_counter()
        scores = cross_validate(
            pipe,
            X[columns],
            y,
            cv=cv_splitter(),
            scoring=SCORING,
            n_jobs=n_jobs,
            return_train_score=True,
        )
        rows.append(_summarise(name, scores, time.perf_counter() - start))
    return pd.DataFrame(rows).sort_values(f"{PRIMARY_METRIC}_mean", ascending=False)


def _summarise(name: str, scores: dict, elapsed: float) -> dict:
    row: dict[str, Any] = {"model": name}
    for metric in SCORING:
        test = scores[f"test_{metric}"]
        if metric == "brier":  # sklearn returns the negated score
            test = -test
        row[f"{metric}_mean"] = round(float(np.mean(test)), 4)
        row[f"{metric}_std"] = round(float(np.std(test)), 4)
    train_auc = scores.get(f"train_{PRIMARY_METRIC}")
    if train_auc is not None:
        row["train_roc_auc_mean"] = round(float(np.mean(train_auc)), 4)
        row["overfit_gap"] = round(row["train_roc_auc_mean"] - row[f"{PRIMARY_METRIC}_mean"], 4)
    row["fit_seconds"] = round(elapsed, 1)
    return row


# --------------------------------------------------------------------------- #
# Q4: three hyperparameters per classifier
# --------------------------------------------------------------------------- #

@dataclass
class SearchSpec:
    name: str
    estimator: Any
    scale: bool
    param_grid: dict[str, list]
    strategy: str = "grid"          # "grid" or "random"
    n_iter: int = 20
    notes: str = ""
    tuned: dict[str, str] = field(default_factory=dict)


def search_specs() -> list[SearchSpec]:
    """Exactly three hyperparameters per classifier, each spanning a real range."""
    return [
        SearchSpec(
            name="LogisticRegression",
            estimator=LogisticRegression(solver="liblinear", max_iter=4000, random_state=RANDOM_STATE),
            scale=True,
            param_grid={
                "clf__C": [0.01, 0.1, 0.5, 1.0, 5.0, 20.0],
                f"clf__{PENALTY_PARAM}": PENALTY_VALUES,
                "clf__class_weight": [None, "balanced"],
            },
            tuned={
                "C": "inverse regularisation strength",
                PENALTY_PARAM: PENALTY_DOC,
                "class_weight": "whether to re-weight the 22% minority class",
            },
        ),
        SearchSpec(
            name="KNeighbors",
            estimator=KNeighborsClassifier(n_jobs=1),
            scale=True,
            param_grid={
                "clf__n_neighbors": [5, 15, 31, 63, 101],
                "clf__weights": ["uniform", "distance"],
                "clf__p": [1, 2],
            },
            tuned={
                "n_neighbors": "neighbourhood size (bias/variance dial)",
                "weights": "uniform vs inverse-distance voting",
                "p": "Manhattan vs Euclidean metric",
            },
        ),
        SearchSpec(
            name="RandomForest",
            estimator=RandomForestClassifier(n_estimators=300, random_state=RANDOM_STATE, n_jobs=1),
            scale=False,
            param_grid={
                "clf__max_depth": [6, 10, 16, None],
                "clf__min_samples_leaf": [1, 5, 20, 50],
                "clf__max_features": ["sqrt", 0.5, None],
            },
            strategy="random",
            n_iter=20,
            notes="randomised over a 48-point grid to keep the run affordable",
            tuned={
                "max_depth": "how far each tree may grow",
                "min_samples_leaf": "smoothing / minimum leaf support",
                "max_features": "features considered per split (decorrelates trees)",
            },
        ),
    ]


def gradient_boosting_spec() -> SearchSpec:
    """Q5: histogram gradient boosting, tuned over four hyperparameters."""
    return SearchSpec(
        name="HistGradientBoosting",
        estimator=HistGradientBoostingClassifier(
            random_state=RANDOM_STATE,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=25,
            max_iter=600,
        ),
        scale=False,
        param_grid={
            "clf__learning_rate": [0.02, 0.05, 0.1, 0.2],
            "clf__max_leaf_nodes": [15, 31, 63, 127],
            "clf__min_samples_leaf": [10, 20, 50, 100],
            "clf__l2_regularization": [0.0, 0.1, 1.0, 10.0],
        },
        strategy="random",
        n_iter=30,
        notes="early stopping decides the number of boosting rounds, so it is not searched",
        tuned={
            "learning_rate": "shrinkage per boosting round",
            "max_leaf_nodes": "capacity of each tree",
            "min_samples_leaf": "minimum leaf support",
            "l2_regularization": "penalty on leaf values",
        },
    )


def run_search(
    spec: SearchSpec,
    X: pd.DataFrame,
    y: pd.Series,
    columns: list[str],
    cv=None,
    n_jobs: int = -1,
    refit: bool = True,
):
    pipe = make_pipeline(columns, spec.estimator, scale=spec.scale)
    cv = cv or cv_splitter()
    common = dict(
        scoring=SCORING,
        refit=PRIMARY_METRIC if refit else False,
        cv=cv,
        n_jobs=n_jobs,
        return_train_score=True,
    )
    if spec.strategy == "grid":
        return GridSearchCV(pipe, spec.param_grid, **common)
    return RandomizedSearchCV(
        pipe, spec.param_grid, n_iter=spec.n_iter, random_state=RANDOM_STATE, **common
    )


def tune_all(
    specs: list[SearchSpec], X: pd.DataFrame, y: pd.Series, columns: list[str], n_jobs: int = -1
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows, fitted = [], {}
    for spec in specs:
        search = run_search(spec, X, y, columns, n_jobs=n_jobs)
        start = time.perf_counter()
        search.fit(X[columns], y)
        elapsed = time.perf_counter() - start

        best = search.cv_results_ | {}
        i = search.best_index_
        row = {
            "model": spec.name,
            "n_candidates": len(search.cv_results_["params"]),
            "best_params": {k.replace("clf__", ""): v for k, v in search.best_params_.items()},
        }
        for metric in SCORING:
            mean = best[f"mean_test_{metric}"][i]
            std = best[f"std_test_{metric}"][i]
            if metric == "brier":
                mean = -mean
            row[f"{metric}_mean"] = round(float(mean), 4)
            row[f"{metric}_std"] = round(float(std), 4)
        row["train_roc_auc_mean"] = round(float(best[f"mean_train_{PRIMARY_METRIC}"][i]), 4)
        row["overfit_gap"] = round(row["train_roc_auc_mean"] - row[f"{PRIMARY_METRIC}_mean"], 4)
        row["search_seconds"] = round(elapsed, 1)
        rows.append(row)
        fitted[spec.name] = search
    return pd.DataFrame(rows).sort_values(f"{PRIMARY_METRIC}_mean", ascending=False), fitted


def search_trace(search, top: int = 5) -> pd.DataFrame:
    """The top candidates of a search, for showing how much tuning actually moved."""
    res = pd.DataFrame(search.cv_results_)
    cols = ["params", f"mean_test_{PRIMARY_METRIC}", f"std_test_{PRIMARY_METRIC}"]
    out = res[cols].sort_values(f"mean_test_{PRIMARY_METRIC}", ascending=False).head(top)
    out = out.rename(
        columns={f"mean_test_{PRIMARY_METRIC}": "roc_auc_mean", f"std_test_{PRIMARY_METRIC}": "roc_auc_std"}
    )
    out["params"] = out["params"].map(lambda d: {k.replace("clf__", ""): v for k, v in d.items()})
    return out.round(4).reset_index(drop=True)
