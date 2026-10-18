# Panic Sale Risk Predictor

A machine-learning web application that estimates the probability that a retail investor **panic sells after a portfolio drop**. It has an HTML front end for people and a JSON API for other applications, both backed by the same trained logistic regression model.

- **Live app:** https://teodemilecamps.pythonanywhere.com
- **API endpoint:** `POST https://teodemilecamps.pythonanywhere.com/api/predict`



---

## 1. The Fintech problem

When a portfolio falls, some investors sell in a hurry and lock in their losses. For the user this turns a paper loss into a real one. For the investing platform it creates outflows, churn and complaints. **Risk area: behavioural and investor-protection risk.**

The idea is simple: if the app can see that a user is likely to panic sell, it can respond *before* the sale, in proportion to the risk:

| Panic-sale probability | Risk level | Suggested platform action |
|---|---|---|
| below 30% | Low | No action. Keep the normal experience. |
| 30% to 60% | Moderate | Show a calm, educational message about market recoveries and diversification before a large sell order. |
| above 60% | High | Trigger a cooling-off step: a confirmation screen showing what is being sold and the cost of locking in the loss, with access to an adviser. |

**Users in the analysis:** retail investors on an investing app whose portfolio has fallen from its 3-month peak.

## 2. The model

- **Task:** binary classification with **logistic regression** (scikit-learn).
- **Target variable:** `stays_invested`
  - `1` (good): the user sells **less than 20%** of their portfolio value in the 3 trading days after the observation date.
  - `0` (bad): **panic sale**, everyone else.
- **Pipeline:** `StandardScaler` followed by `LogisticRegression`, saved as one file (`fintech.joblib`), so the app passes raw inputs straight to the model.
- **Data:** 2,000 synthetic investors generated with numpy (seed 42). The probability of staying invested is built to fall as app checks, drawdown and single stock / crypto share rise, and the outcome is drawn randomly so the data contain realistic noise. No real customer data is used.
- **Split:** 75% train / 25% test, stratified by the target.

### Input variables

| Variable | Meaning | Range |
|---|---|---|
| `app_checks_per_day` | Average number of times the user opened the investing app per day over the previous 7 days | 0 to 30 |
| `portfolio_drawdown_pct` | Fall of the portfolio from its 3-month peak, in % | 5 to 40 |
| `single_stock_crypto_share_pct` | Share of the portfolio held in single stocks or crypto instead of ETFs, in % | 0 to 100 |

### Results

| Data set | Accuracy | Precision (panic / stays) | Recall (panic / stays) |
|---|---|---|---|
| Train (1,500 rows) | 0.75 | 0.74 / 0.75 | 0.74 / 0.75 |
| Test (500 rows) | 0.76 | 0.78 / 0.75 | 0.72 / 0.80 |

Coefficients (original units) are all negative, as intended: app checks −0.120, drawdown −0.091, single stock / crypto share −0.025. Each increase in any of the three variables lowers the chance of staying invested.

The model reports `probability_stays_invested`. The app and API also return `probability_panic_sale = 1 - probability_stays_invested`, which is the headline number.

---

## 3. API

### `POST /api/predict`

Receives the three model inputs as JSON and returns the prediction and probabilities as JSON.

**Request**

```http
POST /api/predict
Content-Type: application/json

{
  "app_checks_per_day": 18,
  "portfolio_drawdown_pct": 30,
  "single_stock_crypto_share_pct": 70
}
```

**Example with curl**

```bash
curl -X POST https://teodemilecamps.pythonanywhere.com/api/predict \
  -H "Content-Type: application/json" \
  -d '{"app_checks_per_day": 18, "portfolio_drawdown_pct": 30, "single_stock_crypto_share_pct": 70}'
```

**Example with Python**

```python
import requests

url = "https://teodemilecamps.pythonanywhere.com/api/predict"
payload = {
    "app_checks_per_day": 18,
    "portfolio_drawdown_pct": 30,
    "single_stock_crypto_share_pct": 70,
}
print(requests.post(url, json=payload, timeout=30).json())
```

**Response (200 OK)**

```json
{
  "inputs": {
    "app_checks_per_day": 18.0,
    "portfolio_drawdown_pct": 30.0,
    "single_stock_crypto_share_pct": 70.0
  },
  "model": "logistic_regression",
  "prediction": "panic_sale",
  "prediction_label": "Likely to panic sell",
  "stays_invested": 0,
  "probability_panic_sale": 0.8257,
  "probability_stays_invested": 0.1743,
  "risk_level": "high",
  "risk_label": "High risk",
  "recommended_action": "Trigger a cooling-off step: a confirmation screen that shows what is being sold and the cost of locking in the loss, and offer a call or chat with an adviser.",
  "target_definition": "stays_invested = 1 if the user sells less than 20% of portfolio value in the 3 trading days after the observation date; 0 = panic sale."
}
```

| Field | Description |
|---|---|
| `prediction` | `stays_invested` or `panic_sale` (threshold: probability of staying invested ≥ 0.5) |
| `stays_invested` | `1` or `0`, the model's class prediction |
| `probability_panic_sale` | Probability of a panic sale (0 to 1) |
| `probability_stays_invested` | Probability of staying invested (0 to 1) |
| `risk_level` | `low`, `moderate` or `high`, based on `probability_panic_sale` |
| `recommended_action` | Suggested response for the investing platform |

**Errors (400 Bad Request)**: missing, non-numeric or out-of-range values return a JSON explanation.

```json
{
  "error": "Invalid input.",
  "details": {
    "app_checks_per_day": "Must be between 0 and 30.",
    "portfolio_drawdown_pct": "Must be a number.",
    "single_stock_crypto_share_pct": "This value is required."
  }
}
```

### Other endpoints

| Endpoint | Description |
|---|---|
| `GET /` | HTML form. Enter the three values and get a live prediction. |
| `GET /api/predict?app_checks_per_day=18&portfolio_drawdown_pct=30&single_stock_crypto_share_pct=70` | Same prediction using query parameters, handy for quick browser tests. |
| `GET /api/health` | Status check. Confirms the model is loaded. |

---

## 4. Project structure

```
.
├── flask_app.py          Flask web app: HTML form and /api/predict
├── fintech.py            Data generation, model training and validation
├── fintech.xlsx          Synthetic dataset (created by fintech.py)
├── fintech.joblib        Trained model pipeline (created by fintech.py)
├── requirements.txt      Python dependencies (pinned versions)
├── templates/
│   └── index.html        HTML front end
├── static/
│   ├── style.css         Styles
│   └── app.js            Form behaviour and live prediction
├── tests/
│   └── test_app.py       Automated tests for the form and API
├── docs/
│   └── DEPLOYMENT.md     PythonAnywhere deployment steps
└── README.md
```

## 5. Run it locally

Requires Python 3.12 or newer.

```bash
git clone https://github.com/TeoDemilecamps/Fintech_Panic_Selling_Activity-7.2-.git
cd Fintech_Panic_Selling_Activity-7.2-

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python fintech.py                  # regenerates fintech.xlsx and fintech.joblib (optional)
python flask_app.py                # opens on http://127.0.0.1:5000
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```

## 6. Deploy on PythonAnywhere

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the step-by-step guide. In short: clone the repository in a PythonAnywhere Bash console, create a virtualenv and install `requirements.txt`, add a web app with manual configuration, point the WSGI file at `flask_app.app`, and reload.

The app loads the model from a path relative to `flask_app.py`, and if `fintech.joblib` cannot be loaded (for example because of a scikit-learn version difference), it retrains the model automatically with `fintech.py`.

## 7. Limitations and disclaimer

- The model is trained on **synthetic data** built from assumed relationships. It illustrates the approach and is not validated on real investor behaviour.
- Only three variables are used. A production model would add trading history, account age, market conditions and more, and would be monitored for fairness and drift.
- The suggested platform actions are examples. This is an educational project, **not financial advice**.
