import json
import tempfile
import unittest
from unittest.mock import Mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from pipeline.source_audit import download_nada_paginated, profile_json, profile_zip


class _Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self):
        return json.dumps(self.payload).encode()


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

    def test_nada_consolidates_pages_and_profiles_cutoff(self):
        pages = {
            0: {"found": 3, "data": [
                {"ISO3": "NGA", "DATES": "2026-06", "MARKET": "A"},
                {"ISO3": "NGA", "DATES": "2026-07", "MARKET": "B"},
            ]},
            2: {"found": 3, "data": [{"ISO3": "NGA", "DATES": "2026-08", "MARKET": "A"}]},
        }
        def opener(request, timeout):
            offset = int(request.full_url.rsplit("/", 1)[1].split("?", 1)[0])
            return _Response(pages[offset])
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "wb.json"
            result = download_nada_paginated(
                {"download_url": "https://example.test/table", "retrieval": {"page_size": 100, "filter": {"ISO3": "NGA"}}},
                target, opener=opener, sleep=lambda _: None,
            )
            profile = profile_json(target, "2026-07")
        self.assertEqual(result["pages"], 2)
        self.assertEqual(result["rows"], result["found"], 3)
        self.assertEqual(result["filter"], {"ISO3": "NGA"})
        self.assertEqual(profile["date_min"], "2026-06")
        self.assertEqual(profile["date_max"], "2026-08")
        self.assertEqual(profile["rows_through_cutoff"], 2)
        self.assertEqual(profile["rows_after_cutoff"], 1)
        self.assertEqual(profile["in_scope_market_count"], 2)

    def test_nada_rejects_wrong_country_and_changing_totals(self):
        def wrong_country(request, timeout):
            return _Response({"found": 1, "data": [{"ISO3": "GHA"}]})
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                download_nada_paginated({"download_url": "https://example.test/table", "retrieval": {"page_size": 100, "filter": {"ISO3": "NGA"}}}, Path(folder) / "x.json", opener=wrong_country, sleep=lambda _: None)

    def test_nada_retries_transient_failures(self):
        calls = Mock(side_effect=[TimeoutError("timeout"), _Response({"found": 1, "data": [{"ISO3": "NGA"}]})])
        with tempfile.TemporaryDirectory() as folder:
            result = download_nada_paginated({"download_url": "https://example.test/table", "retrieval": {"page_size": 100, "filter": {"ISO3": "NGA"}}}, Path(folder) / "x.json", opener=calls, sleep=lambda _: None)
        self.assertEqual(result["rows"], 1)
        self.assertEqual(calls.call_count, 2)


if __name__ == "__main__":
    unittest.main()
