import unittest
from datetime import datetime

from backend.pricing_engine import estimate_demand, optimize_price


class PricingEngineTestCase(unittest.TestCase):
    def test_estimate_demand_peak_time(self):
        dt = datetime.fromisoformat("2026-04-07T08:00:00")
        result = estimate_demand("abbotsford", lag_usage=10.0, dt=dt, cluster=0)

        self.assertEqual(result["time_band"], "peak")
        self.assertIsInstance(result["expected_demand"], float)
        self.assertGreaterEqual(result["expected_demand"], 0.0)
        self.assertGreaterEqual(result["confidence_score"], 0.0)
        self.assertLessEqual(result["confidence_score"], 1.0)

    def test_optimize_price_applies_bounds(self):
        result = optimize_price(base_price=10.0, expected_demand=12.0, time_band="peak")

        self.assertGreaterEqual(result["recommended_price"], result["price_floor"])
        self.assertLessEqual(result["recommended_price"], result["price_cap"])
        self.assertIn(result["price_band"], {"low", "optimal", "surge"})
        self.assertGreaterEqual(result["expected_revenue"], 0.0)

    def test_optimize_price_handles_zero_demand(self):
        result = optimize_price(base_price=15.0, expected_demand=0.0, time_band="standard")

        self.assertEqual(result["recommended_price"], 15.00)
        self.assertEqual(result["expected_demand"], 0.00)
        self.assertEqual(result["expected_revenue"], 0.00)


if __name__ == "__main__":
    unittest.main()
