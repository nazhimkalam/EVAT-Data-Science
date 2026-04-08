import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from backend.app import app


class PricingApiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_pricing_endpoint_returns_expected_fields(self):
        start_time = datetime(2025, 4, 18, 16, 0).isoformat()
        response = self.client.get(
            "/pricing",
            params={"suburb": "abbotsford", "start": start_time}
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data.get("found"))
        self.assertEqual(data.get("suburb"), "abbotsford")
        self.assertIn("recommended_price", data)
        self.assertIn("expected_demand", data)
        self.assertIn("expected_revenue", data)
        self.assertIn("confidence_score", data)
        self.assertIn("price_floor", data)
        self.assertIn("price_cap", data)
        self.assertIn("price_band", data)
        self.assertIn(data.get("price_band"), ["low", "optimal", "surge"])

    def test_listings_endpoint_returns_listings(self):
        response = self.client.get("/listings")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("count", data)
        self.assertIn("listings", data)
        self.assertIsInstance(data["listings"], list)
        self.assertGreaterEqual(data["count"], 0)

    def test_pricing_endpoint_handles_unknown_suburb(self):
        response = self.client.get("/pricing", params={"suburb": "nonexistent-town"})
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertFalse(data.get("found"))
        self.assertIn("message", data)


if __name__ == "__main__":
    unittest.main()
