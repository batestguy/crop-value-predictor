import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from pipeline.world_bank_modeled import build_modeled_snapshot, normalize_modeled


def make_archive(rows):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["ISO3", "price_date", "mkt_name", "geo_id", "components", "currency", "c_maize_fao"])
        writer.writeheader()
        writer.writerows(rows)
        archive.writestr("NGA_RTFP_mkt_test.csv", output.getvalue())
    return payload.getvalue()


class WorldBankModeledTests(unittest.TestCase):
    def test_normalization_uses_price_date_mass_and_separate_modeled_type(self):
        rows = [{"ISO3": "NGA", "price_date": "2026-08-01", "mkt_name": "Kano", "geo_id": "gid_kano", "components": "maize_fao (2.5 KG, Index Weight 1)", "currency": "NGN", "c_maize_fao": "25000"}, {"ISO3": "NGA", "price_date": "2026-08-01", "mkt_name": "Market Average", "geo_id": "gid_nga_national_average", "components": "maize_fao (2.5 KG, Index Weight 1)", "currency": "NGN", "c_maize_fao": "25000"}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.zip"
            path.write_bytes(make_archive(rows))
            accepted, rejected = normalize_modeled(path, "2026-08")
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["value"], 10000)
        self.assertEqual(accepted[0]["price_type"], "modeled_estimate")
        self.assertEqual(accepted[0]["transaction_type"], "modeled_estimate")
        self.assertEqual(accepted[0]["provenance"], "modeled_month_close")
        self.assertFalse(rejected)

    def test_snapshot_keeps_stage_one_false_and_labels_artifact(self):
        rows = []
        for index in range(36):
            year, month = divmod(2023 * 12 + index, 12)
            rows.append({"ISO3": "NGA", "price_date": f"{year:04d}-{month + 1:02d}-01", "mkt_name": "Kano", "geo_id": "gid_kano", "components": "maize_fao (2.5 KG, Index Weight 1)", "currency": "NGN", "c_maize_fao": "25000"})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.zip"
            path.write_bytes(make_archive(rows))
            document, report = build_modeled_snapshot(path, "2025-12", __import__("datetime").date(2026, 1, 15))
        self.assertFalse(report["stage_1_approved"])
        self.assertEqual(document["lane"], "world-bank-modeled-estimates")
        self.assertIn("not observed", document["warning"])
        self.assertTrue(all(item["price_type"] == "modeled_estimate" for item in document["suggestions"]))


if __name__ == "__main__":
    unittest.main()
