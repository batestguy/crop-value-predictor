import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pipeline.online_estimate import local_estimate, parse_mass_unit, parse_tavily_response, read_external_key


class OnlineEstimateTests(unittest.TestCase):
    def test_mass_unit_conversion_accepts_mass_only(self):
        self.assertEqual(parse_mass_unit("KG"), 1)
        self.assertEqual(parse_mass_unit("2.5 KG"), 2.5)
        self.assertEqual(parse_mass_unit("400 G"), 0.4)
        self.assertIsNone(parse_mass_unit("L"))
        self.assertIsNone(parse_mass_unit("30 pcs"))

    def test_local_estimate_balances_markets_and_uses_recent_rows(self):
        fields = ["date", "admin1", "admin2", "market", "market_id", "latitude", "longitude", "category", "commodity", "commodity_id", "unit", "priceflag", "pricetype", "currency", "price", "usdprice"]
        rows = [
            ["2026-07-15", "Lagos", "A", "Market A", "a", "6", "3", "cereals and tubers", "Maize (white)", "1", "KG", "actual", "Retail", "NGN", "100", ""],
            ["2026-07-15", "Lagos", "A", "Market A", "a", "6", "3", "cereals and tubers", "Maize (white)", "1", "KG", "actual", "Retail", "NGN", "110", ""],
            ["2026-07-15", "Lagos", "B", "Market B", "b", "6", "3", "cereals and tubers", "Maize (white)", "1", "KG", "actual", "Retail", "NGN", "300", ""],
            ["2024-01-15", "Lagos", "C", "Old", "c", "6", "3", "cereals and tubers", "Maize (white)", "1", "KG", "actual", "Retail", "NGN", "999", ""],
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wfp.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(fields)
                writer.writerows(rows)
            result = local_estimate(path, "maize-white", "Lagos", as_of=date(2026, 9, 13), max_age_days=365)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["market_count"], 2)
        self.assertEqual(result["estimate_ngn_per_kg"], 105)
        self.assertEqual(result["date_to"], "2026-07-15")

    def test_tavily_answer_requires_explicit_marker_and_keeps_sources(self):
        payload = {"answer": "Evidence values are 800 and 900. ESTIMATE_NGN_PER_KG: 850", "results": [{"title": "Source", "url": "https://example.test/price"}]}
        result = parse_tavily_response(payload, "maize-white", "Lagos", "Retail")
        self.assertEqual(result["estimate_ngn_per_kg"], 850)
        self.assertEqual(result["source_count"], 1)
        natural = {"answer": "As of 2026, maize retails for ₦816 per kg in Lagos. Recent data shows a range from ₦349 to ₦816 per kg.", "results": []}
        natural_result = parse_tavily_response(natural, "maize-white", "Lagos", "Retail")
        self.assertEqual(natural_result["estimate_ngn_per_kg"], 816)
        self.assertEqual(natural_result["low_ngn_per_kg"], 349)
        metric_ton = {"answer": "Retail maize in Bauchi is around NGN 35,417 per metric ton in 2026.", "results": []}
        metric_result = parse_tavily_response(metric_ton, "maize-white", "Bauchi", "Retail")
        self.assertEqual(metric_result["estimate_ngn_per_kg"], 35.42)
        self.assertIn("metric-ton", metric_result["warnings"][1])
        self.assertIsNone(parse_tavily_response({"answer": "No reliable value."}, "maize-white", "Lagos", "Retail"))

    def test_credential_path_inside_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            path = Path(folder) / "key.txt"
            path.write_text("secret", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_external_key(path)


if __name__ == "__main__":
    unittest.main()
