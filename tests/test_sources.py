import json
import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
from pipeline.source_audit import download_nada_paginated, download_fews_paginated, profile_json, profile_zip, discover_wfp_hdx, download_http_csv, run_fetch, sanitize_url
from pipeline.qualification import (
    convert_kg, qualify_series, canonical_crop, national_median,
    normalize_fews, verify_manifest, build_report,
)
from pipeline.promote_price_suggestions import promote
from pipeline.qualification import normalize_wfp


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
    def test_fews_is_primary_and_wfp_is_cross_check_only(self):
        sources = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))["sources"]
        by_id = {s["source_id"]: s for s in sources}
        self.assertTrue(by_id["fews-net"]["required_for_gate"])
        self.assertEqual(by_id["fews-net"]["retrieval"]["mode"], "fews_v3_paginated_json")
        self.assertTrue(by_id["fews-net"]["download_url"].endswith(".json"))
        self.assertEqual(by_id["fews-net"]["retrieval"]["page_size_parameter"], "page_size")
        self.assertFalse(by_id["wfp-hdx"]["required_for_gate"])
        self.assertFalse(by_id["world-bank-rtfp"]["required_for_gate"])
        self.assertFalse(by_id["faostat-qcl"]["required_for_gate"])
        self.assertEqual(by_id["wfp-hdx"]["retrieval"]["excluded_resources"][0]["name"], "Nigeria - Markets")

    def test_synthetic_five_crop_three_stable_market_price_gate(self):
        rows = []
        for crop in [f"crop-{i}" for i in range(5)]:
            for market_id in ["m1", "m2", "m3"]:
                for offset in range(36):
                    year, month = divmod(2023 * 12 + 8 + offset, 12)
                    rows.append({"canonical_crop_id": crop, "market_id": market_id, "market": market_id, "price_type": "retail", "month": f"{year:04d}-{month + 1:02d}", "observation_date": f"{year:04d}-{month + 1:02d}-15"})
        eligible, rejected = qualify_series(rows, "2026-08", date(2026, 8, 25))
        self.assertEqual(len(eligible), 15)
        self.assertFalse(rejected)
    def test_required_fews_missing_is_fail_closed_without_wfp_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / "raw").mkdir()
            (root / "raw_manifest.json").write_text(json.dumps({"cutoff_month": "2026-07", "records": []}), encoding="utf-8")
            report = build_report(root, "2026-07")
        self.assertFalse(report["price_source_qualified"])
        self.assertEqual(report["snapshot_source"], "fews-net")
        self.assertEqual(report["eligible_series"], [])

    def test_optional_artifacts_absent_do_not_make_price_defaults_qualified(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / "raw").mkdir()
            (root / "raw_manifest.json").write_text(json.dumps({"cutoff_month": "2026-07", "records": []}), encoding="utf-8")
            report = build_report(root, "2026-07")
        self.assertFalse(report["recommendation_defaults_qualified"])
        self.assertFalse(report["price_source_qualified"])
    def test_wfp_ckan_discovery_requires_unique_csv_and_sanitizes_url(self):
        payload = {"success": True, "result": {"id": "pkg", "name": "wfp-food-prices-for-nigeria", "title": "WFP Food Prices Nigeria", "organization": {"name": "World Food Programme", "title": "World Food Programme"}, "license_id": "cc-by-igo", "resources": [{"id": "r1", "format": "CSV", "url": "https://files.example.test/nigeria.csv?token=secret"}]}}
        result = discover_wfp_hdx(opener=lambda request, timeout: _Response(payload))
        self.assertEqual(result["url"], "https://files.example.test/nigeria.csv")
        self.assertNotIn("token", result["url"])
        self.assertEqual(sanitize_url(result["url"]), result["url"])

    def test_wfp_normalization_requires_explicit_fields_and_mass(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wfp.csv"
            path.write_text("date,market_id,market,commodity_id,commodity,unit,price,price_type,currency,flag\n2026-06-30,m1,A,c1,Maize Grain (White),100 KG,10000,Retail,NGN,actual\n2026-06-30,m1,A,c1,Maize Grain (White),bag,10000,Retail,NGN,actual\n", encoding="utf-8")
            accepted, rejected = normalize_wfp(path, "2026-06", {"crops": [{"crop_id": "maize-grain-white", "aliases": ["maize grain (white)"]}]})
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["value"], 100)
        self.assertEqual(rejected[0]["reason"], "unknown_or_count_based_unit")

    def test_wfp_download_rejects_html(self):
        class RawResponse(_Response):
            def read(self, *_): return b"<html>bad</html>"
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                download_http_csv({"url": "https://example.test/file.csv?sig=secret"}, Path(folder) / "x.csv", opener=lambda request, timeout: RawResponse("ignored"))
    def test_register_contains_required_roles(self):
        document = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = document["sources"]
        roles = {source["role"] for source in sources}
        self.assertTrue(any(role.startswith("market_price") for role in roles))
        self.assertTrue(any(role.startswith("yield_") for role in roles))
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

    def test_json_profile_supports_fews_v3_results_envelope(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fews.json"
            path.write_text(json.dumps({"count": 1, "results": [{"period_date": "2026-08-01", "market": "Kano"}]}), encoding="utf-8")
            profile = profile_json(path, "2026-08")
        self.assertEqual(profile["rows"], 1)
        self.assertEqual(profile["date_max"], "2026-08-01")
        self.assertEqual(profile["in_scope_market_count"], 1)

    def test_json_profile_recognizes_mkt_name_and_excludes_national_aggregate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rows.json"
            path.write_text(json.dumps({"data": [
                {"DATES": "2026-07", "mkt_name": "A", "geo_id": "gid_a"},
                {"DATES": "2026-07", "mkt_name": "B", "geo_id": "gid_b"},
                {"DATES": "2026-07", "mkt_name": "Market Average", "geo_id": "gid_nga_national_average"},
                {"DATES": "2026-08", "mkt_name": "A", "geo_id": "gid_a"},
            ]}), encoding="utf-8")
            profile = profile_json(path, "2026-07")
        self.assertEqual(profile["in_scope_location_count"], 3)
        self.assertEqual(profile["in_scope_market_count"], 2)
        self.assertEqual(profile["national_aggregate_count"], 1)

    def test_qualification_unit_and_gate_boundaries(self):
        self.assertEqual(convert_kg("2.5 KG"), 2.5)
        self.assertEqual(convert_kg("100_kg"), 100)
        self.assertEqual(convert_kg("50_kg"), 50)
        self.assertIsNone(convert_kg("1 bag"))
        self.assertIsNone(convert_kg("100_tubers", "kg"))
        rows = [{"canonical_crop_id": "maize", "market": "A", "price_type": "retail", "month": f"{y:04d}-{m:02d}"} for y in (2023, 2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 7)]
        eligible, rejected = qualify_series(rows, "2026-07")
        self.assertEqual(len(eligible), 1)
        self.assertFalse(rejected)

    def test_freshness_uses_75_day_boundary_and_keeps_june_fresh(self):
        rows = [{"canonical_crop_id": "maize", "market": "A", "price_type": "retail", "month": f"{y:04d}-{m:02d}", "observation_date": f"{y:04d}-{m:02d}-15"} for y in (2023, 2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 6)]
        rows[-1]["observation_date"] = "2026-06-11"  # exactly 75 days before 2026-08-25
        eligible, rejected = qualify_series(rows, "2026-06", date(2026, 8, 25))
        self.assertEqual(len(eligible), 1)
        self.assertEqual(eligible[0]["freshness_days"], 75)
        rows[-1]["observation_date"] = "2026-06-10"
        eligible, rejected = qualify_series(rows, "2026-06", date(2026, 8, 25))
        self.assertFalse(eligible)
        self.assertIn("latest_value_over_75_days_old", rejected[0]["rejection_reasons"])

    def test_crop_forms_are_not_merged(self):
        mappings = {"crops": [{"crop_id": "gari-white", "aliases": ["gari (white)"]}, {"crop_id": "gari-yellow", "aliases": ["gari (yellow)"]}]}
        self.assertEqual(canonical_crop("Gari (White)", mappings), "gari-white")
        self.assertEqual(canonical_crop("Gari (Yellow)", mappings), "gari-yellow")

    def test_normalization_divides_mass_packages_and_retains_transactions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fews.csv"
            path.write_text("period_date,data_usage_policy,price_type,unit,common_unit,currency,market,product,value,id\n2026-06-30,Public,Wholesale,100_kg,kg,NGN,A,Maize Grain (White),10000,1\n2026-06-30,Public,Retail,kg,kg,NGN,A,Maize Grain (White),150,2\n2026-06-30,Public,Wholesale,100_tubers,ea,NGN,A,Yams,9000,3\n", encoding="utf-8")
            accepted, rejected = normalize_fews(path, "2026-06", {"crops": [{"crop_id": "maize-grain-white", "aliases": ["maize grain (white)"]}]})
        self.assertEqual({row["price_type"] for row in accepted}, {"retail", "wholesale"})
        self.assertEqual(next(row["value"] for row in accepted if row["price_type"] == "wholesale"), 100)
        self.assertEqual(rejected[0]["reason"], "unknown_or_count_based_unit")

    def test_duplicate_detection_happens_after_canonical_normalization(self):
        rows = [{"canonical_crop_id": "gari-white", "market": "A", "price_type": "wholesale", "month": "2026-06", "observation_date": "2026-06-30"}, {"canonical_crop_id": "gari-white", "market": "A", "price_type": "wholesale", "month": "2026-06", "observation_date": "2026-06-30"}]
        eligible, rejected = qualify_series(rows, "2026-06", date(2026, 8, 25))
        self.assertFalse(eligible)
        self.assertIn("duplicate_canonical_key", rejected[0]["rejection_reasons"])

    def test_completeness_and_forecast_window_gates_are_explicit(self):
        rows = [{"canonical_crop_id": "rice", "market": "A", "price_type": "retail", "month": f"{y:04d}-{m:02d}", "observation_date": f"{y:04d}-{m:02d}-15"} for y in (2023, 2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 6) and not (y == 2025 and m in {1, 2, 3, 4, 5, 6, 7, 8})]
        eligible, rejected = qualify_series(rows, "2026-06", date(2026, 8, 25))
        self.assertFalse(eligible)
        self.assertIn("latest_36_completeness_under_80_percent", rejected[0]["rejection_reasons"])
        self.assertGreaterEqual(rejected[0]["forecast_origin_windows"], 6)

    def test_national_median_uses_three_source_markets_and_excludes_aggregate(self):
        rows = [{"canonical_crop_id": "maize", "month": "2026-06", "price_type": "retail", "market": market, "value": value, "market_kind": kind} for market, value, kind in [("A", 10, "source_market"), ("B", 20, "source_market"), ("C", 30, "source_market"), ("Market Average", 999, "national_aggregate")]]
        medians = national_median(rows)
        self.assertEqual(len(medians), 1)
        self.assertEqual(medians[0]["market_count"], 3)
        self.assertEqual(medians[0]["value"], 20)

    def test_manifest_hash_and_size_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); raw = root / "raw"; raw.mkdir(); payload = raw / "x.bin"; payload.write_bytes(b"abc")
            import hashlib
            manifest = {"records": [{"source_id": "x", "status": "downloaded", "path": "x.bin", "bytes": 3, "sha256": hashlib.sha256(b"abc").hexdigest()}]}
            evidence = verify_manifest(root, manifest)
        self.assertEqual(evidence[0]["status"], "verified")

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

    def test_fews_pagination_consolidates_documented_v3_results(self):
        pages = {0: {"count": 3, "results": [{"country_code": "NG"}, {"country_code": "NG"}]}, 2: {"count": 3, "results": [{"country_code": "NG"}]}}
        timeouts = []
        def opener(request, timeout):
            timeouts.append(timeout)
            offset = int(request.full_url.split("offset=")[1].split("&", 1)[0])
            return _Response(pages[offset])
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "fews.json"
            result = download_fews_paginated({"download_url": "https://example.test/fews.json", "retrieval": {"mode": "fews_v3_paginated_json", "country_parameter": "country", "country_code": "NG", "page_size_parameter": "page_size", "offset_parameter": "offset", "response_total_field": "count", "response_rows_field": "results", "row_country_fields": ["country_code", "country"], "page_size": 2, "request_timeout_seconds": 7, "retries": 1}}, target, opener=opener, sleep=lambda _: None)
            payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual((result["pages"], result["rows"], payload["count"]), (2, 3, 3))
        self.assertEqual(len(payload["results"]), 3)
        self.assertEqual(timeouts, [7, 7])

    def test_required_retrieval_failure_writes_manual_only_fallback_record(self):
        sources = [{"source_id": "fews-net", "required_for_gate": True, "download_url": "https://example.test/fews.json", "formats": ["json"]}]
        with tempfile.TemporaryDirectory() as folder:
            with patch("pipeline.source_audit.download", return_value={"source_id": "fews-net", "status": "failed", "error": "timed out"}):
                result = run_fetch(Path(folder), "2026-08", sources)
            report = json.loads((Path(folder) / "qualification_report.json").read_text(encoding="utf-8"))
            manifest = json.loads((Path(folder) / "raw_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(result, 1)
        self.assertEqual(manifest["records"][0]["status"], "failed")
        self.assertEqual(report["status"], "calculator_only_fallback")
        self.assertEqual(report["required_retrieval_failures"], ["fews-net"])
        self.assertFalse(report["promotion_permitted"])

    def test_malformed_or_unapproved_promotion_preserves_last_known_good_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); audit = root / "audit"; data = root / "data"; (audit / "raw").mkdir(parents=True); data.mkdir()
            report = {"technical_gate_passed": False, "selected_crops": [], "cross_source_check": {"disagreement_count": 0}}
            report_path = audit / "qualification_report.json"; report_path.write_text(json.dumps(report), encoding="utf-8")
            import hashlib
            approval = {"stage_1_approved": True, "rights_approved": True, "allow_price_suggestions": True, "reviewer": "reviewer", "reviewed_at": "2026-08-25T00:00:00Z", "qualification_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest()}
            approval_path = root / "approval.json"; approval_path.write_text(json.dumps(approval), encoding="utf-8")
            original = {"snapshot_id": "last-known-good", "stage_1_approved": False, "artifacts": []}
            (data / "manifest.json").write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaises(ValueError): promote(audit, approval_path, data)
            self.assertEqual(json.loads((data / "manifest.json").read_text(encoding="utf-8")), original)

    def test_cross_source_without_market_crosswalk_is_not_comparable(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); raw = root / "raw"; raw.mkdir()
            fews_rows, wfp_rows = [], []
            for crop in ["maize-grain-white", "rice-milled", "gari-white", "yam-fresh", "sorghum-white"]:
                for offset in range(36):
                    year, month_number = divmod(2023 * 12 + 7 + offset, 12)
                    observed = f"{year:04d}-{month_number + 1:02d}-15"
                    fews_rows.append({"period_date": observed, "data_usage_policy": "Public", "price_type": "Retail", "unit": "kg", "currency": "NGN", "market": "Market A", "market_id": "m1", "product": crop, "value": 100, "id": f"f-{crop}-{offset}"})
                    wfp_rows.append(f"{observed},m1,Market A,{crop},{crop},kg,1000,Retail,NGN,actual")
            fews_path = raw / "fews-net.json"; fews_path.write_text(json.dumps({"count": len(fews_rows), "data": fews_rows}), encoding="utf-8")
            wfp_path = raw / "wfp-hdx.csv"; wfp_path.write_text("date,market_id,market,commodity_id,commodity,unit,price,pricetype,currency,priceflag\n" + "\n".join(wfp_rows) + "\n", encoding="utf-8")
            def record(source_id, path): return {"source_id": source_id, "status": "downloaded", "path": path.name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "retrieved_at": "2026-08-25T00:00:00Z"}
            (root / "raw_manifest.json").write_text(json.dumps({"cutoff_month": "2026-07", "records": [record("fews-net", fews_path), record("wfp-hdx", wfp_path)]}), encoding="utf-8")
            report = build_report(root, "2026-07")
        self.assertEqual(report["wfp_row_quality"]["qualified_series"], 5)
        self.assertEqual(report["cross_source_check"]["status"], "not_comparable")
        self.assertEqual(report["cross_source_check"]["disagreement_count"], 0)
        self.assertEqual(report["publishable_series"], [])
        self.assertFalse(report["technical_gate_passed"])

    def test_promotion_rejects_unreviewed_crop_forms_and_market_crosswalks(self):
        import hashlib
        crops = ["maize-grain-white", "rice-milled", "gari-white", "yam-fresh", "sorghum-white"]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); audit = root / "audit"; raw = audit / "raw"; data = root / "data"; raw.mkdir(parents=True); data.mkdir()
            rows = []
            for crop in crops:
                for offset in range(36):
                    year, month_number = divmod(2023 * 12 + 7 + offset, 12)
                    rows.append({"period_date": f"{year:04d}-{month_number + 1:02d}-15", "data_usage_policy": "Public", "price_type": "Retail", "unit": "kg", "currency": "NGN", "market": "Market A", "market_id": "m1", "product": crop, "value": 100, "id": f"{crop}-{offset}"})
            raw_path = raw / "fews-net.json"; raw_path.write_text(json.dumps({"count": len(rows), "data": rows}), encoding="utf-8")
            record = {"source_id": "fews-net", "status": "downloaded", "path": raw_path.name, "bytes": raw_path.stat().st_size, "sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(), "retrieved_at": "2026-08-25T00:00:00Z"}
            (audit / "raw_manifest.json").write_text(json.dumps({"cutoff_month": "2026-07", "records": [record]}), encoding="utf-8")
            report = build_report(audit, "2026-07"); report_path = audit / "qualification_report.json"; report_path.write_text(json.dumps(report), encoding="utf-8")
            documents = {"manifest.json": {"snapshot_id": "old", "stage_1_approved": False, "artifacts": ["catalog.json", "defaults.json", "forecasts.json", "quality.json"]}, "catalog.json": {"snapshot_id": "old", "crops": [{"crop_id": crop} for crop in crops]}, "defaults.json": {"snapshot_id": "old"}, "forecasts.json": {"snapshot_id": "old"}, "quality.json": {"snapshot_id": "old", "pipeline": {}}}
            for name, document in documents.items(): (data / name).write_text(json.dumps(document), encoding="utf-8")
            approval = {"stage_1_approved": True, "rights_approved": True, "allow_price_suggestions": True, "reviewer": "reviewer", "reviewed_at": "2026-08-25T00:00:00Z", "qualification_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest()}
            approval_path = root / "approval.json"; approval_path.write_text(json.dumps(approval), encoding="utf-8")
            original_manifest = (data / "manifest.json").read_text(encoding="utf-8")
            with self.assertRaises(ValueError):
                promote(audit, approval_path, data)
            self.assertEqual((data / "manifest.json").read_text(encoding="utf-8"), original_manifest)

    def test_reviewed_crosswalk_qualifies_and_promotes_canonical_market(self):
        import hashlib
        import pipeline.qualification as qualification_module
        import pipeline.promote_price_suggestions as promotion_module
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); audit = root / "audit"; raw = audit / "raw"; data = root / "data"; config = root / "config"
            raw.mkdir(parents=True); data.mkdir(); config.mkdir()
            crop_forms = [f"form-{index}" for index in range(5)]
            mappings = {
                "release_mapping_contract": {"mapping_version": "test-1", "review_required_in_approval": True},
                "crops": [{"crop_id": form, "aliases": [f"Crop {index}"]} for index, form in enumerate(crop_forms)],
                "app_crop_mappings": [{"crop_form_id": form, "app_crop_id": f"app-{index}"} for index, form in enumerate(crop_forms)],
                "market_registry": {"registry_version": "test-1", "markets": [{"canonical_market_id": "market-kano", "source_identities": [{"source_id": "fews-net", "source_market_id": "fews-kano"}, {"source_id": "wfp-hdx", "source_market_id": "wfp-kano"}]}]},
            }
            sources = {"sources": [{"source_id": "wfp-hdx", "retrieval": {"native_columns": {"date": "date", "market_id": "market_id", "market": "market", "commodity_id": "commodity_id", "commodity": "commodity", "unit": "unit", "price": "price", "price_type": "pricetype", "currency": "currency", "flag": "priceflag"}}}]}
            (config / "mappings.json").write_text(json.dumps(mappings), encoding="utf-8")
            (config / "sources.json").write_text(json.dumps(sources), encoding="utf-8")
            fews_rows, wfp_rows = [], []
            for index in range(5):
                for offset in range(36):
                    year, month_number = divmod(2023 * 12 + 7 + offset, 12)
                    observed = f"{year:04d}-{month_number + 1:02d}-15"
                    fews_rows.append({"period_date": observed, "data_usage_policy": "Public", "price_type": "Retail", "unit": "kg", "currency": "NGN", "market": "Kano", "market_id": "fews-kano", "product": f"Crop {index}", "product_id": f"f{index}", "value": 100, "id": f"f-{index}-{offset}"})
                    wfp_rows.append(f"{observed},wfp-kano,Kano,w{index},Crop {index},kg,100,Retail,NGN,actual")
            fews_path = raw / "fews-net.json"; fews_path.write_text(json.dumps({"count": len(fews_rows), "results": fews_rows}), encoding="utf-8")
            wfp_path = raw / "wfp-hdx.csv"; wfp_path.write_text("date,market_id,market,commodity_id,commodity,unit,price,pricetype,currency,priceflag\n" + "\n".join(wfp_rows) + "\n", encoding="utf-8")
            def record(source_id, path): return {"source_id": source_id, "status": "downloaded", "path": path.name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "retrieved_at": "2026-08-25T00:00:00Z"}
            (audit / "raw_manifest.json").write_text(json.dumps({"cutoff_month": "2026-07", "records": [record("fews-net", fews_path), record("wfp-hdx", wfp_path)]}), encoding="utf-8")
            documents = {"manifest.json": {"snapshot_id": "old", "stage_1_approved": False, "artifacts": ["catalog.json", "defaults.json", "forecasts.json", "quality.json"]}, "catalog.json": {"snapshot_id": "old", "crops": [{"crop_id": f"app-{index}"} for index in range(5)]}, "defaults.json": {"snapshot_id": "old"}, "forecasts.json": {"snapshot_id": "old"}, "quality.json": {"snapshot_id": "old", "pipeline": {}}}
            for name, document in documents.items(): (data / name).write_text(json.dumps(document), encoding="utf-8")
            with patch.object(qualification_module, "ROOT", root), patch.object(promotion_module, "ROOT", root):
                report = build_report(audit, "2026-07")
                self.assertEqual(report["cross_source_check"]["status"], "comparable")
                self.assertEqual(len(report["publishable_series"]), 5)
                self.assertTrue(all(row["canonical_market_id"] == "market-kano" for row in report["publishable_series"]))
                report_path = audit / "qualification_report.json"; report_path.write_text(json.dumps(report), encoding="utf-8")
                approval = {"stage_1_approved": True, "rights_approved": True, "allow_price_suggestions": True, "reviewer": "reviewer", "reviewed_at": "2026-08-25T00:00:00Z", "qualification_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(), "mapping_version": "test-1", "mapping_sha256": hashlib.sha256((config / "mappings.json").read_bytes()).hexdigest(), "mapping_reviewed": True}
                approval_path = root / "approval.json"; approval_path.write_text(json.dumps(approval), encoding="utf-8")
                promote(audit, approval_path, data)
            suggestions = json.loads((data / "price_suggestions.json").read_text(encoding="utf-8"))["suggestions"]
        self.assertEqual(len(suggestions), 5)
        self.assertTrue(all(item["canonical_market_id"] == "market-kano" for item in suggestions))


if __name__ == "__main__":
    unittest.main()
