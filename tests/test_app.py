"""Basic tests for the form and the API. Run from the project root:

    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_app import app  # noqa: E402

CALM = {"app_checks_per_day": 2, "portfolio_drawdown_pct": 8, "single_stock_crypto_share_pct": 10}
AVERAGE = {"app_checks_per_day": 15, "portfolio_drawdown_pct": 22, "single_stock_crypto_share_pct": 50}
STRESSED = {"app_checks_per_day": 28, "portfolio_drawdown_pct": 38, "single_stock_crypto_share_pct": 95}


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    # --- HTML front end ---------------------------------------------------
    def test_home_page_loads(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Panic Sale Risk Predictor", res.data)

    def test_form_post_returns_prediction(self):
        res = self.client.post("/", data=STRESSED)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"probability of a panic sale", res.data)
        self.assertIn(b"High risk", res.data)

    def test_form_post_invalid_shows_error(self):
        res = self.client.post("/", data={**CALM, "portfolio_drawdown_pct": 99})
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Must be between 5 and 40", res.data)

    # --- API --------------------------------------------------------------
    def test_api_post_valid(self):
        res = self.client.post("/api/predict", json=AVERAGE)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertIn(body["prediction"], ("stays_invested", "panic_sale"))
        self.assertAlmostEqual(
            body["probability_panic_sale"] + body["probability_stays_invested"], 1.0, places=3
        )
        self.assertIn(body["risk_level"], ("low", "moderate", "high"))

    def test_api_get_query_string(self):
        res = self.client.get("/api/predict", query_string=CALM)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["risk_level"], "low")

    def test_risk_increases_with_each_variable(self):
        def panic(**override):
            res = self.client.post("/api/predict", json={**AVERAGE, **override})
            return res.get_json()["probability_panic_sale"]

        base = panic()
        self.assertGreater(panic(app_checks_per_day=28), base)
        self.assertGreater(panic(portfolio_drawdown_pct=38), base)
        self.assertGreater(panic(single_stock_crypto_share_pct=95), base)

    def test_calm_vs_stressed(self):
        calm = self.client.post("/api/predict", json=CALM).get_json()
        stressed = self.client.post("/api/predict", json=STRESSED).get_json()
        self.assertEqual(calm["prediction"], "stays_invested")
        self.assertEqual(stressed["prediction"], "panic_sale")
        self.assertLess(calm["probability_panic_sale"], stressed["probability_panic_sale"])

    def test_boundary_values_accepted(self):
        for payload in (
            {"app_checks_per_day": 0, "portfolio_drawdown_pct": 5, "single_stock_crypto_share_pct": 0},
            {"app_checks_per_day": 30, "portfolio_drawdown_pct": 40, "single_stock_crypto_share_pct": 100},
        ):
            self.assertEqual(self.client.post("/api/predict", json=payload).status_code, 200)

    def test_api_missing_field(self):
        res = self.client.post("/api/predict", json={"app_checks_per_day": 5})
        self.assertEqual(res.status_code, 400)
        self.assertIn("portfolio_drawdown_pct", res.get_json()["details"])

    def test_api_out_of_range(self):
        res = self.client.post("/api/predict", json={**CALM, "app_checks_per_day": 31})
        self.assertEqual(res.status_code, 400)

    def test_api_non_numeric_and_bad_values(self):
        for bad in ("abc", "nan", "inf", True, None, ""):
            res = self.client.post("/api/predict", json={**CALM, "app_checks_per_day": bad})
            self.assertEqual(res.status_code, 400, msg=f"value {bad!r}")

    def test_api_not_json(self):
        res = self.client.post("/api/predict", data="not json", content_type="text/plain")
        self.assertEqual(res.status_code, 400)

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.get_json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
