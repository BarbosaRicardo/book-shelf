# Credit risk — will this loan be repaid?

An end-to-end classification study on the Kaggle credit risk dataset
([laotse/credit-risk-dataset](https://www.kaggle.com/datasets/laotse/credit-risk-dataset)):
32,581 granted loans described by twelve columns of applicant, bureau and
underwriting information.

## Run it

```bash
pip install -r requirements.txt
python run_analysis.py            # full run, ~20 min on 4 cores
python run_analysis.py --quick    # smaller search budgets, ~4 min
```

The dataset downloads itself. When `data/credit_risk_dataset.csv` is missing,
`src/data.py` fetches it with `kagglehub`:

```python
import kagglehub

path = kagglehub.dataset_download("laotse/credit-risk-dataset")
print("Path to dataset files:", path)
```

That needs a Kaggle API token — `~/.kaggle/kaggle.json`, or `KAGGLE_USERNAME` and
`KAGGLE_KEY`. Run `python download_data.py` to do the download on its own and see any
error in isolation. If the download cannot happen, the pipeline says why and falls back
to the stand-in described below rather than failing. See `data/README.md`.

Everything lands in `reports/`:

| file | covers |
| --- | --- |
| `reports/eda.md` | Q1 — picking the dependent variable; Q2 — how the variables relate |
| `reports/modelling.md` | Q3 — three classifiers cross-validated; Q4 — tuning three hyperparameters each; Q5 — tuned gradient boosting |
| `reports/robustness.md` | Q6 — dataset size, whether tuning guarantees generalisation, how to measure robustness |
| `reports/results.json` | every number above, machine-readable |
| `reports/figures/` | seven figures |

## A note on the data used for the numbers in `reports/`

**The committed reports were produced from a calibrated stand-in, not the real
Kaggle file.** The environment this ran in has no network route to Kaggle (nor to
Hugging Face, OpenML or the UCI archive — all blocked by egress policy), so
`src/data.py` falls back to `synthesize_credit_risk()`, which draws from a generative
model hand-calibrated to the real file's published summary statistics.

What the stand-in reproduces, to within a point or two:

| property | real file | stand-in |
| --- | --- | --- |
| rows × columns | 32,581 × 12 | 32,581 × 12 |
| default rate | 21.8% | 22.1% |
| default rate by grade | A 9.9% → D 59.1% → G 98.5% | A 10.0% → D 59.7% → G 100% |
| grade shares | A .331, B .320, C .199, D .112 | A .331, B .320, C .199, D .112 |
| missing `loan_int_rate` / `person_emp_length` | 3,116 / 895 | 3,114 / 895 |
| r(`loan_percent_income`, default) | ≈ +0.38 | +0.379 |
| r(`loan_int_rate`, default) | ≈ +0.34 | +0.335 |
| mean interest rate | 11.01% | 11.03% |

What it does **not** reproduce is the real file's sharper *joint* structure: the best
model here reaches ROC-AUC ≈ 0.81, whereas gradient boosting on the real data does
better. The generator was deliberately left at the setting that matches the real
univariate correlations rather than tuned upward to hit a headline AUC — inflating the
`loan_percent_income` effect until AUC rose also pushed its correlation with the target
well past the real +0.38, which would have made the stand-in less faithful, not more.

**So**: the *structure* of the analysis, the relative ordering of the models, and every
qualitative conclusion carry over. The absolute metric values do not. Drop the real
`credit_risk_dataset.csv` into `data/` and re-run — the reports regenerate end to end
and relabel themselves as sourced from Kaggle.

## Layout

```
credit-risk/
├── run_analysis.py        orchestrator; writes every report and figure
├── download_data.py       explicit kagglehub download step
├── src/
│   ├── data.py            loading, schema, and the calibrated stand-in generator
│   ├── preprocess.py      cleaning rules and the leakage-safe pipeline
│   ├── eda.py             Q1/Q2 — profiling, associations, figures
│   ├── experiments.py     Q3/Q4/Q5 — baselines, hyperparameter search, boosting
│   └── robustness.py      Q6 — nested CV, learning curve, bootstrap, slices
├── data/                  put credit_risk_dataset.csv here (gitignored)
└── reports/               generated output
```

## The short version of the answers

1. **Dependent variable: `loan_status`** — the only binary *outcome* column; everything
   else is known before repayment is. Base rate 21.8%, so accuracy is not a usable
   metric.
2. **Relations**: `loan_grade` and `loan_int_rate` dominate, but they are the lender's
   own risk verdict rather than measurements of the applicant, so they are scored both
   in and out. The strongest applicant-side signal is `loan_percent_income` — debt
   service capacity, not income or loan size on their own. `loan_int_rate` is a lookup
   on `loan_grade`; `loan_percent_income` is `loan_amnt / person_income`;
   `person_age` and `cb_person_cred_hist_length` are near-duplicates.
3. **Three classifiers** (logistic regression, k-NN, random forest) under 5-fold
   stratified CV, with imputation/scaling/encoding fitted inside each fold.
4. **Three hyperparameters each**, grid or randomised search on the same folds.
5. **Gradient boosting** (`HistGradientBoostingClassifier`) tuned over four
   hyperparameters; best model overall.
6. **Hyperparameter optimisation guarantees nothing** about unseen data — the reported
   best score is a maximum over noisy estimates and is biased upward. Nested CV
   measures that bias; bootstrap intervals measure precision; seed sweeps measure
   partition sensitivity; the learning curve separates "needs more rows" from "needs
   better features"; slice-level AUC finds the segments the average hides. See
   `reports/robustness.md`.

One structural caveat runs through all six: this file contains only loans that were
**already approved**. It supports modelling *default risk on approved loans*, not
*whether an application will be granted*. Treating the second as the first is
survivorship bias.
