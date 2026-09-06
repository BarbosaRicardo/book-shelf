# 1 & 2 — Feature exploration

> **Numbers below come from the calibrated stand-in, not the real Kaggle file.**
> Kaggle was unreachable from the environment this ran in, so `src/data.py` generated a
> frame with the real file's schema, marginals and conditional default rates. Drop the real
> `credit_risk_dataset.csv` into `data/` and re-run to regenerate every number here.

## The file

32,574 loan applications, 12 columns. Cleaning removed
5 rows with an impossible age and
2 with an impossible employment length
(from 32,581 raw rows). Extreme-but-possible values were kept.

| column                     | dtype   |   n_unique |   missing |   missing_pct | example   |
|:---------------------------|:--------|-----------:|----------:|--------------:|:----------|
| person_age                 | int64   |         44 |         0 |          0    | 23        |
| person_income              | int64   |       2463 |         0 |          0    | 97400     |
| person_home_ownership      | str     |          4 |         0 |          0    | RENT      |
| person_emp_length          | float64 |        183 |       895 |          2.75 | 2.4       |
| loan_intent                | str     |          6 |         0 |          0    | EDUCATION |
| loan_grade                 | str     |          7 |         0 |          0    | A         |
| loan_amnt                  | int64   |        345 |         0 |          0    | 6400      |
| loan_int_rate              | float64 |       1446 |      3114 |          9.56 | 7.45      |
| loan_status                | int64   |          2 |         0 |          0    | 0         |
| loan_percent_income        | float64 |         83 |         0 |          0    | 0.07      |
| cb_person_default_on_file  | str     |          2 |         0 |          0    | N         |
| cb_person_cred_hist_length | int64   |         28 |         0 |          0    | 5         |

## 1. Which variable is the dependent variable?

**`loan_status`.** It is the only column that is (a) binary, (b) an *outcome* of the
loan rather than an input to it, and (c) unknown at the moment of application. Every
other column is either an applicant attribute, a term of the application, or the
lender's own pricing decision — all of them things you know *before* you know whether
the money came back.

| column                     |   n_unique | binary   | kind                    |
|:---------------------------|-----------:|:---------|:------------------------|
| person_home_ownership      |          4 | False    | applicant attribute     |
| person_age                 |         44 | False    | applicant attribute     |
| person_emp_length          |        183 | False    | applicant attribute     |
| person_income              |       2463 | False    | applicant attribute     |
| cb_person_default_on_file  |          2 | True     | credit bureau attribute |
| cb_person_cred_hist_length |         28 | False    | credit bureau attribute |
| loan_grade                 |          7 | False    | lender decision         |
| loan_int_rate              |       1446 | False    | lender decision         |
| loan_intent                |          6 | False    | loan application term   |
| loan_percent_income        |         83 | False    | loan application term   |
| loan_amnt                  |        345 | False    | loan application term   |
| loan_status                |          2 | True     | outcome                 |

`loan_status = 1` means the loan defaulted. The base rate is
**22.1%**, so the problem is imbalanced roughly 78/22 and plain
accuracy is a useless score: predicting "everyone repays" already scores
77.9%. ROC-AUC and average precision are used instead.

A note on framing: it is tempting to read this as *"will the application be granted?"*,
but the file contains only loans that were **already granted** — there are no declined
applicants in it. What can honestly be learned here is *default risk on approved loans*,
which is an input to a granting decision, not the decision itself. The gap between the
two is survivorship bias, and it is discussed in `robustness.md`.

## 2. How the variables relate

### Strength of each feature's relationship with the target

| feature                    | type        | statistic        |   value |   mutual_info |
|:---------------------------|:------------|:-----------------|--------:|--------------:|
| loan_grade                 | categorical | Cramer's V       |   0.416 |        0.0773 |
| loan_percent_income        | numeric     | point-biserial r |   0.388 |        0.0696 |
| loan_int_rate              | numeric     | point-biserial r |   0.335 |        0.0592 |
| person_income              | numeric     | point-biserial r |  -0.276 |        0.0636 |
| person_home_ownership      | categorical | Cramer's V       |   0.193 |        0.0409 |
| cb_person_default_on_file  | categorical | Cramer's V       |   0.134 |        0.0078 |
| person_age                 | numeric     | point-biserial r |  -0.079 |        0.0024 |
| loan_amnt                  | numeric     | point-biserial r |   0.074 |        0      |
| cb_person_cred_hist_length | numeric     | point-biserial r |  -0.069 |        0.005  |
| person_emp_length          | numeric     | point-biserial r |  -0.051 |        0.0068 |
| loan_intent                | categorical | Cramer's V       |   0.031 |        0.0079 |

### Default rate by category

**person_home_ownership**

| person_home_ownership   |     n |   default_rate |   share |
|:------------------------|------:|---------------:|--------:|
| MORTGAGE                | 12333 |          0.139 |   0.379 |
| OTHER                   |    94 |          0.181 |   0.003 |
| OWN                     |  1997 |          0.085 |   0.061 |
| RENT                    | 18150 |          0.292 |   0.557 |

**loan_intent**

| loan_intent       |    n |   default_rate |   share |
|:------------------|-----:|---------------:|--------:|
| DEBTCONSOLIDATION | 5098 |          0.243 |   0.157 |
| EDUCATION         | 6385 |          0.219 |   0.196 |
| HOMEIMPROVEMENT   | 3688 |          0.217 |   0.113 |
| MEDICAL           | 6137 |          0.233 |   0.188 |
| PERSONAL          | 5518 |          0.215 |   0.169 |
| VENTURE           | 5748 |          0.199 |   0.176 |

**cb_person_default_on_file**

| cb_person_default_on_file   |     n |   default_rate |   share |
|:----------------------------|------:|---------------:|--------:|
| N                           | 27220 |          0.196 |   0.836 |
| Y                           |  5354 |          0.347 |   0.164 |

**loan_grade**

| loan_grade   |     n |   default_rate |   share |
|:-------------|------:|---------------:|--------:|
| A            | 10778 |          0.1   |   0.331 |
| B            | 10425 |          0.159 |   0.32  |
| C            |  6484 |          0.225 |   0.199 |
| D            |  3648 |          0.597 |   0.112 |
| E            |   978 |          0.638 |   0.03  |
| F            |   195 |          0.713 |   0.006 |
| G            |    66 |          1     |   0.002 |

### Spearman correlation among the numeric columns

| feature                    |   person_age |   person_income |   person_emp_length |   loan_amnt |   loan_int_rate |   loan_percent_income |   cb_person_cred_hist_length |   loan_status |
|:---------------------------|-------------:|----------------:|--------------------:|------------:|----------------:|----------------------:|-----------------------------:|--------------:|
| person_age                 |        1     |           0.08  |               0.138 |       0.016 |          -0.111 |                -0.054 |                        0.746 |        -0.086 |
| person_income              |        0.08  |           1     |               0.01  |       0.258 |          -0.505 |                -0.553 |                        0.066 |        -0.346 |
| person_emp_length          |        0.138 |           0.01  |               1     |      -0.001 |          -0.1   |                -0.011 |                        0.099 |        -0.047 |
| loan_amnt                  |        0.016 |           0.258 |              -0.001 |       1     |           0.017 |                 0.621 |                        0.01  |         0.076 |
| loan_int_rate              |       -0.111 |          -0.505 |              -0.1   |       0.017 |           1     |                 0.412 |                       -0.089 |         0.32  |
| loan_percent_income        |       -0.054 |          -0.553 |              -0.011 |       0.621 |           0.412 |                 1     |                       -0.047 |         0.336 |
| cb_person_cred_hist_length |        0.746 |           0.066 |               0.099 |       0.01  |          -0.089 |                -0.047 |                        1     |        -0.071 |
| loan_status                |       -0.086 |          -0.346 |              -0.047 |       0.076 |           0.32  |                 0.336 |                       -0.071 |         1     |

### Features that are not independent of each other

| feature_a           | feature_b                  |   spearman_rho | why                                   |
|:--------------------|:---------------------------|---------------:|:--------------------------------------|
| loan_percent_income | loan_amnt                  |          0.621 | numerator of the ratio                |
| loan_percent_income | person_income              |         -0.553 | denominator of the ratio              |
| loan_int_rate       | loan_grade                 |          0.948 | interest rate is priced off the grade |
| person_age          | cb_person_cred_hist_length |          0.746 | history cannot start before adulthood |

### What the structure means for modelling

1. **`loan_grade` and `loan_int_rate` are the lender's own risk verdict, not
   measurements of the applicant.** They are the strongest predictors in the file —
   default rates run from 10.0% at grade A to
   100.0% at grade G, a spread of
   90.0% — precisely because an underwriter already condensed the applicant's
   risk into them. That makes them *post-treatment* variables: legitimate if the model
   is meant to run after grading, but leakage-like if it is meant to replace grading.
   Both feature sets are therefore scored separately in `modelling.md`.

2. **`loan_int_rate` is a near-deterministic function of `loan_grade`** (Spearman
   0.95).
   Keeping both is fine for tree ensembles but splits the coefficient between them in a
   linear model, so neither looks individually important.

3. **`loan_percent_income` is `loan_amnt / person_income` by construction.** It is also
   the strongest *applicant-side* predictor, which is the substantive finding: what
   drives default is not how much someone earns or how much they borrow, but the ratio
   between them — debt service capacity.

4. **`person_age` and `cb_person_cred_hist_length` are near-duplicates**
   (Spearman 0.75),
   because a credit file cannot predate adulthood. Only one of them carries independent
   information.

5. **Missingness is not random.** `loan_int_rate` is missing on
   9.6% of rows and `person_emp_length` on
   2.7%. Imputation is fitted inside
   each cross-validation fold so the imputed values never carry information from the
   validation split.

6. **Renters default far more than owners** — 29.2%
   versus 8.5% —
   and `cb_person_default_on_file = Y` roughly doubles the rate. Both are consistent
   with the standard credit picture: collateral and past behaviour dominate.

### Figures

- `figures/01_target_balance.png` — class imbalance
- `figures/02_default_rate_by_category.png` — default rate per category
- `figures/03_numeric_by_outcome.png` — numeric distributions split by outcome
- `figures/04_spearman_correlation.png` — correlation heatmap
