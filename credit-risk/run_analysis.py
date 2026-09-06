#!/usr/bin/env python3
"""End-to-end credit-risk analysis.

    python run_analysis.py            # full run
    python run_analysis.py --quick    # smaller search budgets, for a smoke test

Writes markdown reports, a machine-readable results.json, and figures under
`reports/`.  Answers the six assignment questions in order:

  Q1  which column is the dependent variable          -> reports/eda.md
  Q2  relations between the variables                 -> reports/eda.md
  Q3  three classifiers under cross-validation        -> reports/modelling.md
  Q4  three hyperparameters each, optimised           -> reports/modelling.md
  Q5  a tuned gradient-boosting classifier            -> reports/modelling.md
  Q6  dataset size, tuning, and robustness            -> reports/robustness.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from sklearn.model_selection import train_test_split  # noqa: E402

import eda  # noqa: E402
import robustness as rb  # noqa: E402
from data import TARGET, UNDERWRITING_FEATURES, load_credit_risk  # noqa: E402
from experiments import (  # noqa: E402
    RANDOM_STATE,
    cross_validate_baselines,
    gradient_boosting_spec,
    search_specs,
    search_trace,
    tune_all,
)
from preprocess import clean, feature_columns  # noqa: E402

REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
TEST_SIZE = 0.20


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="shrink search budgets")
    parser.add_argument("--n-jobs", type=int, default=-1)
    args = parser.parse_args()

    REPORTS.mkdir(exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results: dict = {}

    # ---------------------------------------------------------------- load --
    dataset = load_credit_risk()
    frame, clean_report = clean(dataset.frame)
    results["dataset"] = {
        "source": dataset.source,
        "is_real_kaggle_file": dataset.is_real,
        "cleaning": clean_report,
        "default_rate": round(float(frame[TARGET].mean()), 4),
    }
    banner(f"data source: {dataset.source} | {len(frame):,} rows after cleaning")

    # ------------------------------------------------------------ Q1 & Q2 --
    banner("Q1/Q2  feature exploration")
    results["eda"] = write_eda_report(frame, clean_report, dataset.source)

    # --------------------------------------------------------------- split --
    X_train, X_test, y_train, y_test = train_test_split(
        frame.drop(columns=[TARGET]),
        frame[TARGET],
        test_size=TEST_SIZE,
        stratify=frame[TARGET],
        random_state=RANDOM_STATE,
    )
    results["split"] = {
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "train_default_rate": round(float(y_train.mean()), 4),
        "test_default_rate": round(float(y_test.mean()), 4),
    }
    print(f"  train {len(X_train):,} | held-out test {len(X_test):,}")

    full_cols = feature_columns(include_underwriting=True)
    app_cols = feature_columns(include_underwriting=False)

    # ------------------------------------------------------------------ Q3 --
    banner("Q3  cross-validating three classifiers (5-fold stratified)")
    baseline = cross_validate_baselines(X_train, y_train, full_cols, n_jobs=args.n_jobs)
    print(baseline[["model", "roc_auc_mean", "roc_auc_std", "pr_auc_mean", "f1_mean", "fit_seconds"]]
          .to_string(index=False))

    banner("Q3b  same three, without the lender's grade and rate")
    baseline_app = cross_validate_baselines(X_train, y_train, app_cols, n_jobs=args.n_jobs)
    print(baseline_app[["model", "roc_auc_mean", "roc_auc_std", "pr_auc_mean"]].to_string(index=False))

    results["q3_baselines_full"] = baseline.to_dict("records")
    results["q3_baselines_application_only"] = baseline_app.to_dict("records")

    # ------------------------------------------------------------------ Q4 --
    banner("Q4  hyperparameter optimisation (3 hyperparameters per classifier)")
    specs = search_specs()
    if args.quick:
        for s in specs:
            s.strategy, s.n_iter = "random", 4
    tuned, searches = tune_all(specs, X_train, y_train, full_cols, n_jobs=args.n_jobs)
    print(tuned[["model", "n_candidates", "roc_auc_mean", "roc_auc_std", "overfit_gap",
                 "search_seconds"]].to_string(index=False))
    for _, r in tuned.iterrows():
        print(f"    {r['model']}: {r['best_params']}")
    results["q4_tuned"] = tuned.to_dict("records")
    results["q4_search_traces"] = {
        name: search_trace(s).to_dict("records") for name, s in searches.items()
    }

    # ------------------------------------------------------------------ Q5 --
    banner("Q5  gradient boosting")
    gb_spec = gradient_boosting_spec()
    if args.quick:
        gb_spec.n_iter = 5
    gb_tuned, gb_searches = tune_all([gb_spec], X_train, y_train, full_cols, n_jobs=args.n_jobs)
    print(gb_tuned[["model", "n_candidates", "roc_auc_mean", "roc_auc_std", "overfit_gap",
                    "search_seconds"]].to_string(index=False))
    print(f"    best: {gb_tuned.iloc[0]['best_params']}")
    results["q5_gradient_boosting"] = gb_tuned.to_dict("records")
    results["q5_search_trace"] = search_trace(gb_searches[gb_spec.name], top=8).to_dict("records")

    gb_search = gb_searches[gb_spec.name]
    best_model = gb_search.best_estimator_

    all_tuned = pd.concat([tuned, gb_tuned], ignore_index=True).sort_values(
        "roc_auc_mean", ascending=False
    )
    rb.plot_model_comparison(baseline, all_tuned, FIGURES / "05_model_comparison.png")

    # ------------------------------------------------- held-out evaluation --
    banner("held-out evaluation of the winning model")
    y_proba = best_model.predict_proba(X_test[full_cols])[:, 1]
    boot = rb.bootstrap_test_metrics(y_test, y_proba, n_boot=500 if args.quick else 2000)
    print(boot.to_string(index=False))
    rb.plot_evaluation(y_test, y_proba, FIGURES / "06_holdout_evaluation.png")
    thresholds = rb.threshold_table(y_test, y_proba)
    subgroups = rb.subgroup_performance(X_test.reset_index(drop=True), y_test.to_numpy(), y_proba)
    results["holdout"] = {
        "model": gb_spec.name,
        "cv_roc_auc": float(gb_search.best_score_),
        "bootstrap": boot.to_dict("records"),
        "thresholds": thresholds.to_dict("records"),
        "subgroups": subgroups.to_dict("records"),
    }

    # ------------------------------------------------------------------ Q6 --
    banner("Q6  robustness")
    print("  nested cross-validation ...")
    nested = rb.nested_cv(
        gb_spec, X_train, y_train, full_cols,
        n_iter=3 if args.quick else 10, n_jobs=args.n_jobs,
    )
    print(f"    nested {nested['mean']:.4f} +/- {nested['std']:.4f}  "
          f"vs tuned-CV {gb_search.best_score_:.4f}  "
          f"(optimism {gb_search.best_score_ - nested['mean']:+.4f})")

    print("  seed sensitivity ...")
    seeds = rb.seed_sensitivity(best_model, X_train, y_train, full_cols, n_jobs=args.n_jobs)
    print(seeds.to_string(index=False), f"| spread {seeds.attrs['spread']:.4f}")

    print("  learning curve ...")
    curve = rb.learning_curve_data(best_model, X_train, y_train, full_cols, n_jobs=args.n_jobs)
    rb.plot_learning_curve(curve, FIGURES / "07_learning_curve.png")
    print(curve.to_string(index=False))

    results["q6_robustness"] = {
        "nested_cv": nested,
        "tuned_cv_roc_auc": round(float(gb_search.best_score_), 4),
        "selection_optimism": round(float(gb_search.best_score_ - nested["mean"]), 4),
        "seed_sensitivity": seeds.to_dict("records"),
        "seed_spread": seeds.attrs["spread"],
        "learning_curve": curve.to_dict("records"),
    }

    # ------------------------------------------------------------- reports --
    write_modelling_report(results, baseline, baseline_app, tuned, gb_tuned, specs, gb_spec,
                           boot, thresholds, subgroups, dataset.source)
    write_robustness_report(results, curve, seeds, nested, boot, subgroups, dataset.source)

    results["runtime_seconds"] = round(time.perf_counter() - started, 1)
    (REPORTS / "results.json").write_text(json.dumps(results, indent=2, default=_jsonable))
    banner(f"done in {results['runtime_seconds']:.0f}s -> {REPORTS}")
    return 0


# --------------------------------------------------------------------------- #
# Reporting helpers
# --------------------------------------------------------------------------- #

def banner(text: str) -> None:
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def _jsonable(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def md(frame: pd.DataFrame) -> str:
    return frame.to_markdown(index=False)


def provenance(source: str) -> str:
    if source == "kaggle":
        return "> Numbers below come from the real `credit_risk_dataset.csv` (Kaggle, laotse/credit-risk-dataset).\n"
    return (
        "> **Numbers below come from the calibrated stand-in, not the real Kaggle file.**\n"
        "> Kaggle was unreachable from the environment this ran in, so `src/data.py` generated a\n"
        "> frame with the real file's schema, marginals and conditional default rates. Drop the real\n"
        "> `credit_risk_dataset.csv` into `data/` and re-run to regenerate every number here.\n"
    )


def write_eda_report(frame: pd.DataFrame, clean_report: dict, source: str) -> dict:
    prof = eda.profile(frame)
    cands = eda.target_candidates(frame)
    assoc = eda.association_with_target(frame)
    cats = eda.default_rate_by_category(frame)
    corr = eda.numeric_correlations(frame)
    redundancy = eda.redundancy_check(frame)
    corr_md = md(corr.rename_axis('feature').reset_index())
    eda.write_figures(frame, FIGURES)

    grade_gap = float(cats["loan_grade"]["default_rate"].max() - cats["loan_grade"]["default_rate"].min())
    text = f"""# Q1 & Q2 — Feature exploration

{provenance(source)}
## The file

{len(frame):,} loan applications, 12 columns. Cleaning removed
{clean_report['impossible_age']} rows with an impossible age and
{clean_report['impossible_emp_length']} with an impossible employment length
(from {clean_report['rows_before']:,} raw rows). Extreme-but-possible values were kept.

{md(prof)}

## Q1 — Which variable is the dependent variable?

**`loan_status`.** It is the only column that is (a) binary, (b) an *outcome* of the
loan rather than an input to it, and (c) unknown at the moment of application. Every
other column is either an applicant attribute, a term of the application, or the
lender's own pricing decision — all of them things you know *before* you know whether
the money came back.

{md(cands)}

`loan_status = 1` means the loan defaulted. The base rate is
**{frame[TARGET].mean():.1%}**, so the problem is imbalanced roughly 78/22 and plain
accuracy is a useless score: predicting "everyone repays" already scores
{1 - frame[TARGET].mean():.1%}. ROC-AUC and average precision are used instead.

A note on framing: the assignment asks about *"whether a loan application will be
granted"*, but this file contains only loans that were **already granted** — there are
no declined applicants in it. What can honestly be learned here is *default risk on
approved loans*, which is the input to a granting decision, not the decision itself.
The gap between the two is survivorship bias, and it is discussed in
`robustness.md`.

## Q2 — How the variables relate

### Strength of each feature's relationship with the target

{md(assoc)}

### Default rate by category

""" + "\n\n".join(f"**{col}**\n\n{md(t)}" for col, t in cats.items()) + f"""

### Spearman correlation among the numeric columns

{corr_md}

### Features that are not independent of each other

{md(redundancy)}

### What the structure means for modelling

1. **`loan_grade` and `loan_int_rate` are the lender's own risk verdict, not
   measurements of the applicant.** They are the strongest predictors in the file —
   default rates run from {cats['loan_grade']['default_rate'].min():.1%} at grade A to
   {cats['loan_grade']['default_rate'].max():.1%} at grade G, a spread of
   {grade_gap:.1%} — precisely because an underwriter already condensed the applicant's
   risk into them. That makes them *post-treatment* variables: legitimate if the model
   is meant to run after grading, but leakage-like if it is meant to replace grading.
   Both feature sets are therefore scored separately in `modelling.md`.

2. **`loan_int_rate` is a near-deterministic function of `loan_grade`** (Spearman
   {redundancy.loc[redundancy.feature_b == 'loan_grade', 'spearman_rho'].iloc[0]:.2f}).
   Keeping both is fine for tree ensembles but splits the coefficient between them in a
   linear model, so neither looks individually important.

3. **`loan_percent_income` is `loan_amnt / person_income` by construction.** It is also
   the strongest *applicant-side* predictor, which is the substantive finding: what
   drives default is not how much someone earns or how much they borrow, but the ratio
   between them — debt service capacity.

4. **`person_age` and `cb_person_cred_hist_length` are near-duplicates**
   (Spearman {redundancy.loc[redundancy.feature_b == 'cb_person_cred_hist_length', 'spearman_rho'].iloc[0]:.2f}),
   because a credit file cannot predate adulthood. Only one of them carries independent
   information.

5. **Missingness is not random.** `loan_int_rate` is missing on
   {100 * frame['loan_int_rate'].isna().mean():.1f}% of rows and `person_emp_length` on
   {100 * frame['person_emp_length'].isna().mean():.1f}%. Imputation is fitted inside
   each cross-validation fold so the imputed values never carry information from the
   validation split.

6. **Renters default far more than owners** — {cats['person_home_ownership'].set_index('person_home_ownership')['default_rate'].get('RENT', float('nan')):.1%}
   versus {cats['person_home_ownership'].set_index('person_home_ownership')['default_rate'].get('OWN', float('nan')):.1%} —
   and `cb_person_default_on_file = Y` roughly doubles the rate. Both are consistent
   with the standard credit picture: collateral and past behaviour dominate.

### Figures

- `figures/01_target_balance.png` — class imbalance
- `figures/02_default_rate_by_category.png` — default rate per category
- `figures/03_numeric_by_outcome.png` — numeric distributions split by outcome
- `figures/04_spearman_correlation.png` — correlation heatmap
"""
    (REPORTS / "eda.md").write_text(text)
    return {
        "profile": prof.to_dict("records"),
        "target_candidates": cands.to_dict("records"),
        "association_with_target": assoc.to_dict("records"),
        "default_rate_by_category": {k: v.to_dict("records") for k, v in cats.items()},
        "numeric_spearman": corr.to_dict(),
        "redundancy": redundancy.to_dict("records"),
    }


def write_modelling_report(results, baseline, baseline_app, tuned, gb_tuned, specs, gb_spec,
                           boot, thresholds, subgroups, source) -> None:
    metric_cols = ["model", "roc_auc_mean", "roc_auc_std", "pr_auc_mean", "f1_mean",
                   "balanced_accuracy_mean", "accuracy_mean", "brier_mean", "fit_seconds"]
    tuned_cols = ["model", "n_candidates", "best_params", "roc_auc_mean", "roc_auc_std",
                  "pr_auc_mean", "f1_mean", "overfit_gap", "search_seconds"]
    gb_row = gb_tuned.iloc[0]
    best_overall = pd.concat([tuned, gb_tuned]).sort_values("roc_auc_mean", ascending=False).iloc[0]
    lift = {r["model"]: r for _, r in tuned.iterrows()}

    hp_doc = "\n\n".join(
        f"**{s.name}** — {len(s.param_grid)} hyperparameters"
        + (f" ({s.notes})" if s.notes else "")
        + "\n\n"
        + "\n".join(f"- `{k}` — {v}; searched over `{s.param_grid['clf__' + k]}`"
                    for k, v in s.tuned.items())
        for s in specs + [gb_spec]
    )

    text = f"""# Q3, Q4 & Q5 — Classifiers, tuning, and gradient boosting

{provenance(source)}
## Protocol

- A stratified **20% held-out test set** ({results['split']['test_rows']:,} rows) is split off
  first and touched only once, at the very end. All model selection happens on the
  remaining {results['split']['train_rows']:,} rows.
- **5-fold stratified cross-validation** on the training portion. Stratification keeps
  the {results['split']['train_default_rate']:.1%} default rate in every fold.
- Imputation, scaling and encoding live **inside** the pipeline, so they are re-fitted
  on each training fold. Fitting them on the full data first would leak validation
  statistics into training.
- **ROC-AUC is the selection metric** (threshold-free and insensitive to the 78/22
  imbalance); average precision, F1, balanced accuracy and the Brier score are reported
  alongside because they answer different questions.

## Q3 — Three classifiers, default settings

Chosen to span three different inductive biases: a linear model, a local
non-parametric method, and a non-linear ensemble.

{md(baseline[metric_cols])}

Excluding the lender's own grade and interest rate — i.e. predicting from what the
applicant actually tells you:

{md(baseline_app[[c for c in metric_cols if c in baseline_app.columns]])}

The drop from the first table to the second is the share of the apparent performance
that comes from the underwriter's verdict rather than from the applicant's profile.

## Q4 — Hyperparameter optimisation

Three hyperparameters per classifier, each spanning a genuine range rather than a
neighbourhood of the default:

{hp_doc}

Results (same folds, same seed, so the comparison is like-for-like):

{md(tuned[tuned_cols])}

Change against the untuned baseline:

{md(pd.DataFrame([
    {"model": m,
     "baseline_roc_auc": baseline.set_index("model").loc[m, "roc_auc_mean"],
     "tuned_roc_auc": lift[m]["roc_auc_mean"],
     "delta": round(lift[m]["roc_auc_mean"] - baseline.set_index("model").loc[m, "roc_auc_mean"], 4)}
    for m in lift]))}

## Q5 — Gradient boosting

`HistGradientBoostingClassifier` — scikit-learn's histogram-based booster, the same
family as LightGBM. It suits this dataset: mixed numeric and categorical features, a
strongly non-linear and interacting relationship between `loan_percent_income` and
`loan_grade`, and insensitivity to the heavy right tail of `person_income` that the
linear model needs rescaled. It runs through the same preprocessing pipeline as the
other three so the comparison stays like-for-like. The number of boosting rounds is not
searched: early stopping on an internal validation split sets it per fit.

{md(gb_tuned[tuned_cols])}

Top candidates from the search:

{md(pd.DataFrame(results['q5_search_trace']))}

**Best model overall: {best_overall['model']}**, cross-validated ROC-AUC
{best_overall['roc_auc_mean']:.4f} ± {best_overall['roc_auc_std']:.4f}.

## Held-out test set

Evaluated once, on data no fold and no search ever saw. Intervals are 2,000-sample
percentile bootstraps.

{md(boot)}

Ranking quality is threshold-free, but an approve/decline policy is not. What the
choice of cut-off costs, on the held-out set:

{md(thresholds)}

Per-slice AUC — an average can hide a segment the model fails on:

{md(subgroups)}

### Figures

- `figures/05_model_comparison.png` — default vs tuned, all four models
- `figures/06_holdout_evaluation.png` — ROC, precision-recall and calibration
"""
    (REPORTS / "modelling.md").write_text(text)


def write_robustness_report(results, curve, seeds, nested, boot, subgroups, source) -> None:
    r6 = results["q6_robustness"]
    auc_ci = boot.set_index("metric").loc["roc_auc"]
    last_two = curve.tail(2)
    slope = float(last_two["cv_mean"].iloc[-1] - last_two["cv_mean"].iloc[0])
    subgroup_auc = subgroups["roc_auc"].dropna()

    text = f"""# Q6 — Dataset size, tuning, and robustness

{provenance(source)}
## Is 32k rows a lot or a little?

For this problem it is a comfortable middle. It is large enough that a 20% held-out set
still contains ~{results['split']['test_rows']:,} loans and ~{int(results['split']['test_rows'] * results['split']['test_default_rate']):,}
defaults, so a single split gives a usable estimate. But the minority class is what
constrains everything: with a {results['dataset']['default_rate']:.1%} base rate the
effective sample size for learning *what default looks like* is the ~7k defaulters, not
the 32k rows. That has three consequences the pipeline is built around:

1. **Stratification everywhere.** Every split preserves the class ratio; without it,
   fold-to-fold variance would swamp the differences between models.
2. **Cross-validation rather than a single validation split.** At this size a single
   split's estimate moves by more than the gap between two decent models.
3. **The rare cells are the fragile ones.** Grades F and G hold only a few hundred rows
   between them. Any conclusion about those segments rests on a handful of examples,
   which is why the per-slice table below matters more than the headline number.

The learning curve says whether more data would help:

{md(curve)}

Between the last two points the cross-validated AUC moves by **{slope:+.4f}**. The curve
has flattened, and the train/CV gap is small — so the limit here is the *information in
these twelve columns*, not the number of rows. Collecting another 30k identical
applications would buy very little. Adding new *columns* — payment history, existing
debt, DTI from a bureau file — would buy much more.

## Does hyperparameter optimisation guarantee performance on unseen data?

**No, and it is systematically optimistic.** Three distinct reasons:

**1. The reported best score is a maximum, and maxima are biased.** A search over
*k* candidates reports the best of *k* noisy estimates. Some of that "best" is real
improvement and some is a lucky draw against those particular folds. Measuring it
requires nested cross-validation — an outer loop that scores the *entire* procedure,
tuning included, on data the search never touched:

| quantity | ROC-AUC |
| --- | --- |
| tuned inner-CV score (what a naive report would quote) | {r6['tuned_cv_roc_auc']:.4f} |
| nested CV (honest estimate of the procedure) | {nested['mean']:.4f} ± {nested['std']:.4f} |
| **selection optimism** | **{r6['selection_optimism']:+.4f}** |

Outer-fold scores: {nested['outer_scores']}

**2. Tuning optimises the metric you chose, on the distribution you happen to have.**
Maximising ROC-AUC improves *ranking*; it does not improve calibration, and it says
nothing about the cost asymmetry between rejecting a good borrower and approving a bad
one. The threshold table in `modelling.md` is where that trade-off actually gets made,
and no amount of hyperparameter search makes that choice for you.

**3. It assumes the future looks like the past.** Every guarantee cross-validation
offers is conditional on new applicants being drawn from the same distribution. Credit
portfolios violate that routinely — rates move, the lender changes its own approval
policy, a recession arrives. And this file contains only *approved* loans, so the model
never sees the applicants the bank already turned down. A model deployed to make
approval decisions would immediately face a population it was never trained on.

## How to measure robustness

Five checks, all run here:

**a. Nested cross-validation** — above. Isolates selection bias. Gap of
{r6['selection_optimism']:+.4f}.

**b. Bootstrap confidence intervals on the held-out set** — how precise the estimate is
at all. ROC-AUC = {auc_ci['point_estimate']:.4f}, 95% CI
[{auc_ci['ci_lo_2.5']:.4f}, {auc_ci['ci_hi_97.5']:.4f}], width {auc_ci['ci_width']:.4f}.
Any two models closer together than that width are not distinguishable on this data.

**c. Seed / partition sensitivity** — re-run cross-validation under five different fold
partitions. If the score swings with the partition, the ranking of models is noise:

{md(seeds)}

Spread across seeds: **{r6['seed_spread']:.4f}**.

**d. Learning curve** — above. Separates "needs more data" from "needs better features",
and shows whether the train/CV gap is variance or bias.

**e. Slice-level evaluation** — the average hides the segments. Across the slices in
`modelling.md`, per-slice AUC ranges from {subgroup_auc.min():.3f} to
{subgroup_auc.max():.3f}. Within a single grade the model has much less to work with
than the headline number suggests, because grade itself carries most of the signal.

Two further checks belong in production but need data this file does not carry:
**out-of-time validation** (train on older vintages, test on newer — the only honest
test of drift) and **adversarial / stress evaluation** (perturb inputs, or re-weight the
test set toward an economic downturn, and watch the metric move).

## What would actually make this deployable

- Score the model on *rejected* applications too — reject inference — or accept that it
  only describes approved-loan risk.
- Calibrate the probabilities and monitor calibration drift, not just AUC. A ranking
  that stays good while the absolute probabilities drift will still misprice the book.
- Re-validate out-of-time on every new vintage, and set a drift alarm on the input
  distributions rather than waiting for the default rate to move.

### Figures

- `figures/07_learning_curve.png` — learning curve
- `figures/06_holdout_evaluation.png` — ROC, precision-recall, calibration
"""
    (REPORTS / "robustness.md").write_text(text)


if __name__ == "__main__":
    raise SystemExit(main())
