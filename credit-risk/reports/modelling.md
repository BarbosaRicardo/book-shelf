# Q3, Q4 & Q5 — Classifiers, tuning, and gradient boosting

> **Numbers below come from the calibrated stand-in, not the real Kaggle file.**
> Kaggle was unreachable from the environment this ran in, so `src/data.py` generated a
> frame with the real file's schema, marginals and conditional default rates. Drop the real
> `credit_risk_dataset.csv` into `data/` and re-run to regenerate every number here.

## Protocol

- A stratified **20% held-out test set** (6,515 rows) is split off
  first and touched only once, at the very end. All model selection happens on the
  remaining 26,059 rows.
- **5-fold stratified cross-validation** on the training portion. Stratification keeps
  the 22.1% default rate in every fold.
- Imputation, scaling and encoding live **inside** the pipeline, so they are re-fitted
  on each training fold. Fitting them on the full data first would leak validation
  statistics into training.
- **ROC-AUC is the selection metric** (threshold-free and insensitive to the 78/22
  imbalance); average precision, F1, balanced accuracy and the Brier score are reported
  alongside because they answer different questions.

## Q3 — Three classifiers, default settings

Chosen to span three different inductive biases: a linear model, a local
non-parametric method, and a non-linear ensemble.

| model              |   roc_auc_mean |   roc_auc_std |   pr_auc_mean |   f1_mean |   balanced_accuracy_mean |   accuracy_mean |   brier_mean |   fit_seconds |
|:-------------------|---------------:|--------------:|--------------:|----------:|-------------------------:|----------------:|-------------:|--------------:|
| LogisticRegression |         0.8079 |        0.0066 |        0.599  |    0.4736 |                   0.6572 |          0.8249 |       0.1288 |           1.4 |
| RandomForest       |         0.8    |        0.0071 |        0.5919 |    0.499  |                   0.6708 |          0.8251 |       0.1301 |          16.5 |
| KNeighbors         |         0.7339 |        0.0078 |        0.4603 |    0.4581 |                   0.6504 |          0.8027 |       0.1521 |           5.3 |

Excluding the lender's own grade and interest rate — i.e. predicting from what the
applicant actually tells you:

| model              |   roc_auc_mean |   roc_auc_std |   pr_auc_mean |   f1_mean |   balanced_accuracy_mean |   accuracy_mean |   brier_mean |   fit_seconds |
|:-------------------|---------------:|--------------:|--------------:|----------:|-------------------------:|----------------:|-------------:|--------------:|
| LogisticRegression |         0.8035 |        0.006  |        0.5854 |    0.4495 |                   0.6455 |          0.8204 |       0.1309 |           0.4 |
| RandomForest       |         0.7853 |        0.0052 |        0.5566 |    0.4545 |                   0.6481 |          0.8126 |       0.136  |          14.2 |
| KNeighbors         |         0.7136 |        0.0032 |        0.4289 |    0.4216 |                   0.6313 |          0.7942 |       0.1582 |           6.1 |

The drop from the first table to the second is the share of the apparent performance
that comes from the underwriter's verdict rather than from the applicant's profile.

## Q4 — Hyperparameter optimisation

Three hyperparameters per classifier, each spanning a genuine range rather than a
neighbourhood of the default:

**LogisticRegression** — 3 hyperparameters

- `C` — inverse regularisation strength; searched over `[0.01, 0.1, 0.5, 1.0, 5.0, 20.0]`
- `l1_ratio` — pure L2 shrinkage (0.0) vs pure L1 sparsity (1.0); searched over `[0.0, 1.0]`
- `class_weight` — whether to re-weight the 22% minority class; searched over `[None, 'balanced']`

**KNeighbors** — 3 hyperparameters

- `n_neighbors` — neighbourhood size (bias/variance dial); searched over `[5, 15, 31, 63, 101]`
- `weights` — uniform vs inverse-distance voting; searched over `['uniform', 'distance']`
- `p` — Manhattan vs Euclidean metric; searched over `[1, 2]`

**RandomForest** — 3 hyperparameters (randomised over a 48-point grid to keep the run affordable)

- `max_depth` — how far each tree may grow; searched over `[6, 10, 16, None]`
- `min_samples_leaf` — smoothing / minimum leaf support; searched over `[1, 5, 20, 50]`
- `max_features` — features considered per split (decorrelates trees); searched over `['sqrt', 0.5, None]`

**HistGradientBoosting** — 4 hyperparameters (early stopping decides the number of boosting rounds, so it is not searched)

- `learning_rate` — shrinkage per boosting round; searched over `[0.02, 0.05, 0.1, 0.2]`
- `max_leaf_nodes` — capacity of each tree; searched over `[15, 31, 63, 127]`
- `min_samples_leaf` — minimum leaf support; searched over `[10, 20, 50, 100]`
- `l2_regularization` — penalty on leaf values; searched over `[0.0, 0.1, 1.0, 10.0]`

Results (same folds, same seed, so the comparison is like-for-like):

| model              |   n_candidates | best_params                                                       |   roc_auc_mean |   roc_auc_std |   pr_auc_mean |   f1_mean |   overfit_gap |   search_seconds |
|:-------------------|---------------:|:------------------------------------------------------------------|---------------:|--------------:|--------------:|----------:|--------------:|-----------------:|
| RandomForest       |             20 | {'min_samples_leaf': 50, 'max_features': 'sqrt', 'max_depth': 10} |         0.812  |        0.0067 |        0.609  |    0.4827 |        0.0238 |            202.3 |
| LogisticRegression |             24 | {'C': 0.1, 'class_weight': 'balanced', 'l1_ratio': 1.0}           |         0.8081 |        0.0068 |        0.5983 |    0.5459 |        0.0009 |             17.6 |
| KNeighbors         |             20 | {'n_neighbors': 101, 'p': 1, 'weights': 'distance'}               |         0.8006 |        0.0074 |        0.5934 |    0.4436 |        0.1994 |            178.1 |

Change against the untuned baseline:

| model              |   baseline_roc_auc |   tuned_roc_auc |   delta |
|:-------------------|-------------------:|----------------:|--------:|
| RandomForest       |             0.8    |          0.812  |  0.012  |
| LogisticRegression |             0.8079 |          0.8081 |  0.0002 |
| KNeighbors         |             0.7339 |          0.8006 |  0.0667 |

## Q5 — Gradient boosting

`HistGradientBoostingClassifier` — scikit-learn's histogram-based booster, the same
family as LightGBM. It suits this dataset: mixed numeric and categorical features, a
strongly non-linear and interacting relationship between `loan_percent_income` and
`loan_grade`, and insensitivity to the heavy right tail of `person_income` that the
linear model needs rescaled. It runs through the same preprocessing pipeline as the
other three so the comparison stays like-for-like. The number of boosting rounds is not
searched: early stopping on an internal validation split sets it per fit.

| model                |   n_candidates | best_params                                                                                      |   roc_auc_mean |   roc_auc_std |   pr_auc_mean |   f1_mean |   overfit_gap |   search_seconds |
|:---------------------|---------------:|:-------------------------------------------------------------------------------------------------|---------------:|--------------:|--------------:|----------:|--------------:|-----------------:|
| HistGradientBoosting |             30 | {'min_samples_leaf': 10, 'max_leaf_nodes': 15, 'learning_rate': 0.05, 'l2_regularization': 10.0} |         0.8138 |        0.0061 |        0.6133 |    0.5089 |        0.0178 |             46.3 |

Top candidates from the search:

| params                                                                                            |   roc_auc_mean |   roc_auc_std |
|:--------------------------------------------------------------------------------------------------|---------------:|--------------:|
| {'min_samples_leaf': 10, 'max_leaf_nodes': 15, 'learning_rate': 0.05, 'l2_regularization': 10.0}  |         0.8138 |        0.0061 |
| {'min_samples_leaf': 100, 'max_leaf_nodes': 15, 'learning_rate': 0.05, 'l2_regularization': 0.0}  |         0.8133 |        0.0064 |
| {'min_samples_leaf': 20, 'max_leaf_nodes': 15, 'learning_rate': 0.1, 'l2_regularization': 0.0}    |         0.8125 |        0.0062 |
| {'min_samples_leaf': 10, 'max_leaf_nodes': 31, 'learning_rate': 0.02, 'l2_regularization': 0.1}   |         0.8123 |        0.0062 |
| {'min_samples_leaf': 50, 'max_leaf_nodes': 15, 'learning_rate': 0.2, 'l2_regularization': 10.0}   |         0.8122 |        0.0066 |
| {'min_samples_leaf': 10, 'max_leaf_nodes': 15, 'learning_rate': 0.1, 'l2_regularization': 0.1}    |         0.8121 |        0.0061 |
| {'min_samples_leaf': 100, 'max_leaf_nodes': 31, 'learning_rate': 0.02, 'l2_regularization': 10.0} |         0.812  |        0.0063 |
| {'min_samples_leaf': 50, 'max_leaf_nodes': 31, 'learning_rate': 0.02, 'l2_regularization': 0.0}   |         0.8118 |        0.0066 |

**Best model overall: HistGradientBoosting**, cross-validated ROC-AUC
0.8138 ± 0.0061.

## Held-out test set

Evaluated once, on data no fold and no search ever saw. Intervals are 2,000-sample
percentile bootstraps.

| metric            |   point_estimate |   ci_lo_2.5 |   ci_hi_97.5 |   ci_width |
|:------------------|-----------------:|------------:|-------------:|-----------:|
| roc_auc           |           0.8118 |      0.7982 |       0.8244 |     0.0262 |
| pr_auc            |           0.6048 |      0.577  |       0.6317 |     0.0547 |
| f1                |           0.5022 |      0.4755 |       0.5278 |     0.0523 |
| balanced_accuracy |           0.6722 |      0.6588 |       0.6856 |     0.0268 |
| brier             |           0.1272 |      0.1217 |       0.1329 |     0.0112 |

Ranking quality is threshold-free, but an approve/decline policy is not. What the
choice of cut-off costs, on the held-out set:

|   threshold |   declined_pct |   precision |   recall |    f1 |   defaults_caught |   good_loans_rejected |   defaults_missed |   good_loans_approved |
|------------:|---------------:|------------:|---------:|------:|------------------:|----------------------:|------------------:|----------------------:|
|         0.2 |           35.6 |       0.449 |    0.724 | 0.554 |              1043 |                  1278 |               398 |                  3796 |
|         0.3 |           24.3 |       0.535 |    0.588 | 0.56  |               847 |                   735 |               594 |                  4339 |
|         0.4 |           17.7 |       0.615 |    0.493 | 0.547 |               710 |                   445 |               731 |                  4629 |
|         0.5 |           12.6 |       0.692 |    0.394 | 0.502 |               568 |                   253 |               873 |                  4821 |
|         0.6 |            8.5 |       0.768 |    0.296 | 0.427 |               426 |                   129 |              1015 |                  4945 |
|         0.7 |            5.4 |       0.825 |    0.203 | 0.325 |               292 |                    62 |              1149 |                  5012 |

Per-slice AUC — an average can hide a segment the model fails on:

| slice                 | value             |    n |   roc_auc |   default_rate |
|:----------------------|:------------------|-----:|----------:|---------------:|
| loan_grade            | A                 | 2094 |    0.7305 |          0.098 |
| loan_grade            | B                 | 2079 |    0.7212 |          0.16  |
| loan_grade            | C                 | 1371 |    0.7343 |          0.23  |
| loan_grade            | D                 |  719 |    0.7277 |          0.576 |
| loan_grade            | E                 |  200 |    0.758  |          0.66  |
| loan_grade            | F                 |   35 |  nan      |          0.714 |
| loan_grade            | G                 |   17 |  nan      |          1     |
| person_home_ownership | MORTGAGE          | 2464 |    0.8046 |          0.134 |
| person_home_ownership | OTHER             |   23 |  nan      |          0.174 |
| person_home_ownership | OWN               |  379 |    0.8323 |          0.106 |
| person_home_ownership | RENT              | 3649 |    0.7808 |          0.292 |
| loan_intent           | DEBTCONSOLIDATION |  990 |    0.8128 |          0.257 |
| loan_intent           | EDUCATION         | 1197 |    0.8037 |          0.237 |
| loan_intent           | HOMEIMPROVEMENT   |  729 |    0.7935 |          0.228 |
| loan_intent           | MEDICAL           | 1307 |    0.8176 |          0.233 |
| loan_intent           | PERSONAL          | 1151 |    0.8102 |          0.199 |
| loan_intent           | VENTURE           | 1141 |    0.8273 |          0.179 |

### Figures

- `figures/05_model_comparison.png` — default vs tuned, all four models
- `figures/06_holdout_evaluation.png` — ROC, precision-recall and calibration
