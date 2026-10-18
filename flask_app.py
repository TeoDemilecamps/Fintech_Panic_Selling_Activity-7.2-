"""
Panic Sale Risk Predictor: Flask web app and JSON API.

Loads the trained logistic regression pipeline (fintech.joblib) and serves:
    GET  /               HTML form (also handles form submission via POST)
    GET  /api/predict    JSON prediction from query parameters
    POST /api/predict    JSON prediction from a JSON body
    GET  /api/health     simple status check

The model predicts whether an investor "stays_invested" (1) or makes a panic
sale (0) in the 3 trading days after a portfolio drop. The app reports the
panic-sale probability as the headline number.
"""

import logging
import math
import os
import subprocess
import sys

import joblib
import pandas as pd
from flask import Flask, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

# ---------------------------------------------------------------------------
# Paths: always resolve relative to this file, because PythonAnywhere does not
# run the app from the project folder.
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "fintech.joblib")
TRAIN_SCRIPT = os.path.join(BASE_DIR, "fintech.py")

app = Flask(__name__)
# Behind PythonAnywhere's proxy, trust the forwarded scheme and host so links
# and the example URL on the page use https and the real domain.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("panic-sale-app")

# ---------------------------------------------------------------------------
# Input definition: single source of truth for the form, the API and validation
# ---------------------------------------------------------------------------
FEATURES = {
    "app_checks_per_day": {
        "label": "App checks per day",
        "unit": "times per day",
        "min": 0.0,
        "max": 30.0,
        "default": 12,
        "step": 0.5,
        "help": "Average number of times the user opened the investing app per "
                "day over the previous 7 days.",
    },
    "portfolio_drawdown_pct": {
        "label": "Portfolio drawdown",
        "unit": "%",
        "min": 5.0,
        "max": 40.0,
        "default": 20,
        "step": 0.5,
        "help": "Fall of the portfolio from its 3-month peak, in %.",
    },
    "single_stock_crypto_share_pct": {
        "label": "Single stock / crypto share",
        "unit": "%",
        "min": 0.0,
        "max": 100.0,
        "default": 40,
        "step": 1,
        "help": "Share of the portfolio held in single stocks or crypto "
                "instead of ETFs, in %.",
    },
}
FEATURE_ORDER = list(FEATURES.keys())

# Risk bands applied to the panic-sale probability
RISK_BANDS = [
    (0.30, "low", "Low risk",
     "No action needed. Keep the normal experience and, if useful, show "
     "a short reminder of the user's long-term plan."),
    (0.60, "moderate", "Moderate risk",
     "Show a calm, educational message about past market recoveries and "
     "diversification before the user can place a large sell order."),
    (1.01, "high", "High risk",
     "Trigger a cooling-off step: a confirmation screen that shows what is "
     "being sold and the cost of locking in the loss, and offer a call or "
     "chat with an adviser."),
]


# ---------------------------------------------------------------------------
# Model loading (with a safe fallback)
# ---------------------------------------------------------------------------
def load_model():
    """Load fintech.joblib. If it cannot be loaded (for example because the
    scikit-learn version differs from the one used for training), retrain it
    with fintech.py in this environment and load the fresh file."""
    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not load %s (%s). Retraining with fintech.py.", MODEL_PATH, exc)
        subprocess.run([sys.executable, TRAIN_SCRIPT], cwd=BASE_DIR, check=True)
        return joblib.load(MODEL_PATH)


model = load_model()


# ---------------------------------------------------------------------------
# Validation and prediction
# ---------------------------------------------------------------------------
def validate_inputs(raw):
    """Return (clean_values, errors). Every feature is required, numeric,
    finite and inside its allowed range."""
    clean, errors = {}, {}
    for name, spec in FEATURES.items():
        value = raw.get(name)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors[name] = "This value is required."
            continue
        if isinstance(value, bool):
            errors[name] = "Must be a number."
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            errors[name] = "Must be a number."
            continue
        if not math.isfinite(number):
            errors[name] = "Must be a finite number."
            continue
        if number < spec["min"] or number > spec["max"]:
            errors[name] = f"Must be between {spec['min']:g} and {spec['max']:g}."
            continue
        clean[name] = number
    return clean, errors


def risk_band(prob_panic):
    for upper, key, label, action in RISK_BANDS:
        if prob_panic < upper:
            return key, label, action
    return RISK_BANDS[-1][1:]


def predict(clean):
    """Apply the trained pipeline to validated inputs."""
    frame = pd.DataFrame([[clean[name] for name in FEATURE_ORDER]], columns=FEATURE_ORDER)
    prob_stays = float(model.predict_proba(frame)[0][1])
    prob_panic = 1.0 - prob_stays
    stays_invested = int(prob_stays >= 0.5)
    key, label, action = risk_band(prob_panic)
    return {
        "inputs": clean,
        "prediction": "stays_invested" if stays_invested else "panic_sale",
        "prediction_label": "Likely to stay invested" if stays_invested
                            else "Likely to panic sell",
        "stays_invested": stays_invested,
        "probability_panic_sale": round(prob_panic, 4),
        "probability_stays_invested": round(prob_stays, 4),
        "risk_level": key,
        "risk_label": label,
        "recommended_action": action,
        "model": "logistic_regression",
        "target_definition": (
            "stays_invested = 1 if the user sells less than 20% of portfolio "
            "value in the 3 trading days after the observation date; "
            "0 = panic sale."
        ),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    """HTML front end. POST works without JavaScript; the page script also
    calls /api/predict for instant results."""
    result, errors, values = None, {}, {}
    if request.method == "POST":
        values = request.form.to_dict()
        clean, errors = validate_inputs(values)
        if not errors:
            result = predict(clean)
    else:
        values = {name: spec["default"] for name, spec in FEATURES.items()}
    return render_template(
        "index.html",
        features=FEATURES,
        values=values,
        errors=errors,
        result=result,
    )


@app.route("/api/predict", methods=["GET", "POST"])
def api_predict():
    """JSON API. Accepts a JSON body (POST) or query parameters (GET)."""
    if request.method == "POST":
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({
                "error": "Request body must be a JSON object.",
                "expected_fields": FEATURE_ORDER,
            }), 400
    else:
        payload = request.args.to_dict()

    clean, errors = validate_inputs(payload)
    if errors:
        return jsonify({"error": "Invalid input.", "details": errors}), 400
    return jsonify(predict(clean))


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "model_loaded": model is not None,
                    "features": FEATURE_ORDER})


if __name__ == "__main__":
    app.run(debug=False, port=5000)
