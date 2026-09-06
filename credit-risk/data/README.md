# Where the data goes

Put the Kaggle file here as `credit_risk_dataset.csv`:

- https://www.kaggle.com/datasets/laotse/credit-risk-dataset

Either download it from the browser, or with the Kaggle CLI:

    pip install kaggle                     # needs ~/.kaggle/kaggle.json
    kaggle datasets download -d laotse/credit-risk-dataset -p . --unzip

`src/data.py` picks the file up automatically on the next run. If it is absent,
the pipeline falls back to the calibrated stand-in described in the top-level
README and labels every report accordingly.

The expected 12 columns are:

    person_age, person_income, person_home_ownership, person_emp_length,
    loan_intent, loan_grade, loan_amnt, loan_int_rate, loan_status,
    loan_percent_income, cb_person_default_on_file, cb_person_cred_hist_length
