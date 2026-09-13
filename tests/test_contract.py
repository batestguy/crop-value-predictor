import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data" / "v1"


class SnapshotContractTests(unittest.TestCase):
    def load(self, name):
        return json.loads((DATA / name).read_text(encoding="utf-8"))

    def test_all_artifacts_share_snapshot(self):
        manifest = self.load("manifest.json")
        for name in manifest["artifacts"]:
            expected = manifest.get("modeled_estimate_snapshot_id") if name == "modeled_price_suggestions.json" else manifest["snapshot_id"]
            self.assertEqual(self.load(name)["snapshot_id"], expected)

    def test_modeled_context_is_explicitly_separate_from_observed_stage_one(self):
        manifest = self.load("manifest.json")
        modeled = self.load("modeled_price_suggestions.json")
        self.assertFalse(manifest["stage_1_approved"])
        self.assertTrue(manifest["modeled_estimates_enabled"])
        self.assertEqual(modeled["lane"], "world-bank-modeled-estimates")
        self.assertIn("not observed", modeled["warning"])
        self.assertTrue(all(item["price_type"] == "modeled_estimate" for item in modeled["suggestions"]))

    def test_forecasts_have_ordered_intervals_and_explicit_units(self):
        catalog = self.load("catalog.json")
        crop_ids = {crop["crop_id"] for crop in catalog["crops"]}
        forecasts = self.load("forecasts.json")["forecasts"]
        self.assertGreaterEqual(len(crop_ids), 5)
        for forecast in forecasts:
            self.assertIn(forecast["crop_id"], crop_ids)
            self.assertEqual((forecast["currency"], forecast["unit"]), ("NGN", "kg"))
            self.assertLessEqual(forecast["lower_80"], forecast["point"])
            self.assertLessEqual(forecast["point"], forecast["upper_80"])

    def test_unapproved_release_cannot_advertise_price_suggestions(self):
        manifest = self.load("manifest.json")
        if not manifest["stage_1_approved"]:
            self.assertNotIn("price_suggestions.json", manifest["artifacts"])


if __name__ == "__main__":
    unittest.main()
