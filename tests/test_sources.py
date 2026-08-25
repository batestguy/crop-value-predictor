import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from pipeline.source_audit import profile_json, profile_zip


class SourceRegisterTests(unittest.TestCase):
    def test_register_contains_required_roles(self):
        document = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = document["sources"]
        roles = {source["role"] for source in sources}
        self.assertTrue(any(role.startswith("market_price") for role in roles))
        self.assertIn("yield_default", roles)
        self.assertIn("cost_default", roles)

    def test_register_ids_and_urls_are_unique_and_https(self):
        document = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = document["sources"]
        self.assertEqual(len({source["source_id"] for source in sources}), len(sources))
        self.assertTrue(all(source["url"].startswith("https://") for source in sources))

    def test_register_has_audit_metadata_and_no_false_approvals(self):
        document = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = document["sources"]
        required = {
            "download_url", "terms_url", "auth_mode", "formats", "price_types",
            "units", "coverage", "attribution", "redistribution_decision",
            "required_for_gate", "evidence_urls",
        }
        for source in sources:
            self.assertTrue(required.issubset(source))
            self.assertIn(source["status"], {"candidate", "qualified", "rejected", "deferred"})

    def test_mapping_units_fail_closed_for_unknown_units(self):
        document = json.loads((ROOT / "config" / "mappings.json").read_text(encoding="utf-8"))
        units = {item["source_unit"]: item for item in document["units"]}
        self.assertEqual(units["kg"]["factor"], 1)
        self.assertEqual(units["hg/ha"]["canonical_unit"], "t/ha")
        self.assertIsNone(units["unknown"]["canonical_unit"])

    def test_json_profile_counts_rows_and_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rows.json"
            path.write_text(json.dumps({"data": [{"month": "2026-01", "beans": 1.2}]}), encoding="utf-8")
            profile = profile_json(path)
        self.assertEqual(profile["rows"], 1)
        self.assertEqual(profile["columns"], ["beans", "month"])


if __name__ == "__main__":
    unittest.main()
