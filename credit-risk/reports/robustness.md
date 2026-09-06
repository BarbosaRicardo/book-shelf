# 6 — Sample size, tuning, and robustness

> **Numbers below come from the calibrated stand-in, not the real Kaggle file.**
> Kaggle was unreachable from the environment this ran in, so `src/data.py` generated a
> frame with the real file's schema, marginals and conditional default rates. Drop the real
> `credit_risk_dataset.csv` into `data/` and re-run to regenerate every number here.

## Is 32k rows a lot or a little?

For this problem it is a comfortable middle. It is large enough that a 20% held-out set
still contains ~6,515 loans and ~1,441
defaults, so a single split gives a usable estimate. But the minority class is what
constrains everything: with a 22.1% base rate the
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

|   train_size |   train_mean |   cv_mean |   cv_std |
|-------------:|-------------:|----------:|---------:|
|         2084 |       0.8904 |    0.7953 |   0.0095 |
|         4765 |       0.8616 |    0.8041 |   0.0079 |
|         7445 |       0.845  |    0.8097 |   0.0063 |
|        10125 |       0.8393 |    0.8115 |   0.0068 |
|        12806 |       0.8383 |    0.8113 |   0.007  |
|        15486 |       0.8365 |    0.8128 |   0.0063 |
|        18166 |       0.8337 |    0.8145 |   0.0058 |
|        20847 |       0.8326 |    0.8139 |   0.0061 |

Between the last two points the cross-validated AUC moves by **-0.0006**. The curve
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
| tuned inner-CV score (what a naive report would quote) | 0.8138 |
| nested CV (honest estimate of the procedure) | 0.8121 ± 0.0068 |
| **selection optimism** | **+0.0017** |

Outer-fold scores: [0.8015, 0.8109, 0.809, 0.8198, 0.8191]

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
+0.0017.

**b. Bootstrap confidence intervals on the held-out set** — how precise the estimate is
at all. ROC-AUC = 0.8118, 95% CI
[0.7982, 0.8244], width 0.0262.
Any two models closer together than that width are not distinguishable on this data.

**c. Seed / partition sensitivity** — re-run cross-validation under five different fold
partitions. If the score swings with the partition, the ranking of models is noise:

|   seed |   mean |    std |
|-------:|-------:|-------:|
|      0 | 0.8124 | 0.0084 |
|      1 | 0.8131 | 0.0057 |
|      7 | 0.8136 | 0.0096 |
|     13 | 0.8125 | 0.0059 |
|     42 | 0.8138 | 0.0061 |

Spread across seeds: **0.0014**.

**d. Learning curve** — above. Separates "needs more data" from "needs better features",
and shows whether the train/CV gap is variance or bias.

**e. Slice-level evaluation** — the average hides the segments. Across the slices in
`modelling.md`, per-slice AUC ranges from 0.721 to
0.832. Within a single grade the model has much less to work with
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
