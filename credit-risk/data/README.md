# Where the data goes

The pipeline looks for `credit_risk_dataset.csv` in this directory. There are
three ways it can get here, tried in that order.

## 1. Let the pipeline fetch it

`run_analysis.py` calls `kagglehub` on its own when the file is missing, so in
most cases there is nothing to do:

    pip install kagglehub
    python run_analysis.py

## 2. Download it explicitly

Useful when you want the download step isolated and its errors visible:

    python download_data.py

Both routes run the same code:

```python
import kagglehub

path = kagglehub.dataset_download("laotse/credit-risk-dataset")
print("Path to dataset files:", path)
```

kagglehub caches under `~/.cache/kagglehub/`; `download_via_kagglehub()` in
`src/data.py` copies the CSV out of that cache into this directory.

**Credentials.** kagglehub needs a Kaggle API token — either `~/.kaggle/kaggle.json`
(Kaggle → Settings → API → *Create New Token*) or the `KAGGLE_USERNAME` and
`KAGGLE_KEY` environment variables.

## 3. Download it by hand

From <https://www.kaggle.com/datasets/laotse/credit-risk-dataset>, and drop the
CSV in this directory.

## If none of that works

The pipeline prints why the download failed, falls back to the calibrated
stand-in in `src/data.py`, and labels every generated report as stand-in-sourced.
Nothing silently pretends to be real data.

## Expected schema

    person_age, person_income, person_home_ownership, person_emp_length,
    loan_intent, loan_grade, loan_amnt, loan_int_rate, loan_status,
    loan_percent_income, cb_person_default_on_file, cb_person_cred_hist_length

32,581 rows. `loan_status` is the target: 1 = defaulted, 0 = repaid.
