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
            self.assertEqual(self.load(name)["snapshot_id"], manifest["snapshot_id"])

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


if __name__ == "__main__":
    unittest.main()
