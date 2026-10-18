"""
Fintech project: predicting panic selling after a portfolio drop.

Model: logistic regression on synthetic behavioural and portfolio data.
Target: stays_invested
    1 = good: the user sells less than 20% of their portfolio value in the
        3 trading days after the observation date.
    0 = bad: panic sale (everyone else).

Outputs:
    fintech.xlsx   synthetic dataset (no index)
    fintech.joblib trained model (scaler + logistic regression pipeline)
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# 1. Reproducibility and settings
# ---------------------------------------------------------------------------
SEED = 42
N_ROWS = 2000
np.random.seed(SEED)
rng = np.random.default_rng(SEED)

FEATURES = [
    "app_checks_per_day",
    "portfolio_drawdown_pct",
    "single_stock_crypto_share_pct",
]
TARGET = "stays_invested"

# ---------------------------------------------------------------------------
# 2. Generate synthetic data with numpy
# ---------------------------------------------------------------------------
# Average number of times the user opened the investing app per day
# over the previous 7 days (continuous, 0 to 30).
app_checks_per_day = rng.uniform(0, 30, N_ROWS)

# Fall of the portfolio from its 3-month peak, in % (continuous, 5 to 40).
portfolio_drawdown_pct = rng.uniform(5, 40, N_ROWS)

# Share of the portfolio held in single stocks or crypto instead of ETFs,
# in % (continuous, 0 to 100).
single_stock_crypto_share_pct = rng.uniform(0, 100, N_ROWS)

# ---------------------------------------------------------------------------
# 3. Generate the binary target
# ---------------------------------------------------------------------------
# The probability of staying invested FALLS as app checks, drawdown and the
# single stock / crypto share RISE: all three coefficients are negative.
# The target is drawn from a Bernoulli distribution (not thresholded), so the
# data contain realistic randomness and the model is not artificially perfect.
INTERCEPT = 5.0
COEF_APP_CHECKS = -0.12
COEF_DRAWDOWN = -0.09
COEF_SHARE = -0.025

logit = (
    INTERCEPT
    + COEF_APP_CHECKS * app_checks_per_day
    + COEF_DRAWDOWN * portfolio_drawdown_pct
    + COEF_SHARE * single_stock_crypto_share_pct
)
prob_stays_invested = 1 / (1 + np.exp(-logit))
stays_invested = rng.binomial(n=1, p=prob_stays_invested)

# ---------------------------------------------------------------------------
# 4. Build the data frame and save it to Excel (without index)
# ---------------------------------------------------------------------------
df = pd.DataFrame(
    {
        "app_checks_per_day": app_checks_per_day.round(2),
        "portfolio_drawdown_pct": portfolio_drawdown_pct.round(2),
        "single_stock_crypto_share_pct": single_stock_crypto_share_pct.round(2),
        "stays_invested": stays_invested,
    }
)
df.to_excel("fintech.xlsx", index=False)

print("Dataset shape:", df.shape)
print("\nTarget distribution (1 = stays invested, 0 = panic sale):")
print(df[TARGET].value_counts(normalize=True).round(3).sort_index())

# ---------------------------------------------------------------------------
# 5. Train / test split
# ---------------------------------------------------------------------------
X = df[FEATURES]
y = df[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=SEED, stratify=y
)

# ---------------------------------------------------------------------------
# 6. Logistic regression (scaling + model in one pipeline)
# ---------------------------------------------------------------------------
# The scaler is stored inside the same joblib file, so the web app can pass
# raw user inputs straight to the model without repeating any preprocessing.
model = Pipeline(
    steps=[
        ("scaler", StandardScaler()),
        ("logistic_regression", LogisticRegression(random_state=SEED)),
    ]
)
model.fit(X_train, y_train)

# ---------------------------------------------------------------------------
# 7. Validation: classification report on train and test
# ---------------------------------------------------------------------------
target_names = ["0 - panic sale", "1 - stays invested"]

print("\n=== Classification report: TRAIN ===")
print(classification_report(y_train, model.predict(X_train), target_names=target_names))

print("=== Classification report: TEST ===")
print(classification_report(y_test, model.predict(X_test), target_names=target_names))

# Coefficients on the original (unscaled) variables, for interpretation.
scaler = model.named_steps["scaler"]
logreg = model.named_steps["logistic_regression"]
raw_coefficients = logreg.coef_[0] / scaler.scale_
print("Model coefficients (original units, negative = lowers chance of staying invested):")
for name, coef in zip(FEATURES, raw_coefficients):
    print(f"  {name}: {coef:+.4f}")

# ---------------------------------------------------------------------------
# 8. Save the model
# ---------------------------------------------------------------------------
joblib.dump(model, "fintech.joblib")
print("\nSaved: fintech.xlsx and fintech.joblib")
