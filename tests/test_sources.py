import json
import io
import zipfile
import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from datetime import date, datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
from pipeline.source_audit import (
    download_nada_paginated, download_fews_paginated, profile_json, profile_zip,
    discover_wfp_hdx, discover_world_bank_bulk, download_world_bank_bulk,
    download_http_csv, discover_fews_static_export, download_fews_static_export,
    validate_fews_static_csv, run_fetch, sanitize_url,
)
from pipeline.qualification import (
    convert_kg, qualify_series, canonical_crop, national_median,
    normalize_fews, verify_manifest, build_report, gate_review_evidence,
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


class _BytesResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, *_):
        payload, self.payload = self.payload, b""
        return payload


class _HttpBytesResponse(_BytesResponse):
    def __init__(self, payload, content_type="text/csv", final_url=None):
        super().__init__(payload)
        self.headers = {"Content-Type": content_type}
        self.final_url = final_url
    def geturl(self):
        return self.final_url or "https://fdw.fews.net/export.csv"


class SourceRegisterTests(unittest.TestCase):
    def test_fews_is_primary_and_wfp_is_cross_check_only(self):
        sources = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))["sources"]
        by_id = {s["source_id"]: s for s in sources}
        self.assertTrue(by_id["fews-net"]["required_for_gate"])
        self.assertEqual(by_id["fews-net"]["retrieval"]["mode"], "fews_static_export")
        self.assertIsNone(by_id["fews-net"]["download_url"])
        self.assertEqual(by_id["fews-net"]["retrieval"]["accepted_extensions"], [".csv"])
        self.assertEqual(by_id["fews-net"]["diagnostic_retrieval"]["mode"], "fews_v3_paginated_json")
        self.assertEqual(by_id["fews-net"]["diagnostic_retrieval"]["country_parameter"], "country")
        self.assertEqual(by_id["fews-net"]["diagnostic_retrieval"]["query_parameters"]["dataset"], "FEWS_NET_Staple_Food_Price_Data")
        self.assertFalse(by_id["wfp-hdx"]["required_for_gate"])
        self.assertFalse(by_id["world-bank-rtfp"]["required_for_gate"])
        self.assertFalse(by_id["faostat-qcl"]["required_for_gate"])
        self.assertEqual(by_id["wfp-hdx"]["retrieval"]["excluded_resources"][0]["name"], "Nigeria - Markets")

    def test_world_bank_bulk_discovery_chooses_latest_open_candidate(self):
        source = {"source_id": "world-bank-rtfp", "url": "https://catalog.test/4503", "download_url": "https://catalog.test/files", "retrieval": {"mode": "world_bank_bulk_zip", "study_idno": "NGA_2021_RTFP_v02_M", "expected_filename_prefix": "NGA_RTFP_mkt_", "accepted_extensions": [".zip"]}}
        payload = {"status": "success", "files": [
            {"filename": "NGA_RTFP_mkt_2026-07-24.zip", "study_idno": "NGA_2021_RTFP_v02_M", "data_access_type": "open", "dcdate": "2026-07-24", "changed": "2026-07-24", "resource_id": 1, "links": {"download": "https://files.test/old.zip"}},
            {"filename": "NGA_RTFP_mkt_2026-08-24.zip", "study_idno": "NGA_2021_RTFP_v02_M", "data_access_type": "open", "dcdate": "2026-08-24", "changed": "2026-08-24", "resource_id": 2, "links": {"download": "https://files.test/new.zip"}},
            {"filename": "NGA_RTFP_mkt_private.zip", "study_idno": "NGA_2021_RTFP_v02_M", "data_access_type": "restricted", "dcdate": "2027-01-01", "links": {"download": "https://files.test/private.zip"}},
        ]}
        result = discover_world_bank_bulk(source, opener=lambda request, timeout: _Response(payload))
        self.assertEqual(result["url"], "https://files.test/new.zip")
        self.assertEqual(result["resource_id"], 2)

    def test_world_bank_bulk_download_validates_country_and_csv_schema(self):
        source = {"source_id": "world-bank-rtfp", "url": "https://catalog.test/4503", "download_url": "https://catalog.test/files", "retrieval": {"mode": "world_bank_bulk_zip", "study_idno": "NGA_2021_RTFP_v02_M", "expected_filename_prefix": "NGA_RTFP_mkt_", "accepted_extensions": [".zip"]}}
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
            handle.writestr("NGA_RTFP_mkt_2026-08-24.csv", "ISO3,price_date\nNGA,2026-08-01\n")
        catalog = {"status": "success", "files": [{"filename": "NGA_RTFP_mkt_2026-08-24.zip", "study_idno": "NGA_2021_RTFP_v02_M", "data_access_type": "open", "dcdate": "2026-08-24", "changed": "2026-08-24", "resource_id": 2, "links": {"download": "https://files.test/new.zip"}}]}
        calls = iter([_Response(catalog), _BytesResponse(archive.getvalue())])
        with tempfile.TemporaryDirectory() as folder:
            result = download_world_bank_bulk(source, Path(folder) / "world-bank.zip", opener=lambda request, timeout: next(calls))
        self.assertEqual(result["rows"], 1)
        self.assertEqual(result["date_max"], "2026-08-01")

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

    def _technical_gate_report(self, market_count, review=None, price_types=None):
        import hashlib
        import pipeline.qualification as qualification_module
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); audit = root / "audit"; raw = audit / "raw"; config = root / "config"
            raw.mkdir(parents=True); config.mkdir()
            crops = [f"crop-{index}" for index in range(5)]
            markets = [f"market-{index}" for index in range(market_count)]
            mappings = {"release_mapping_contract": {"mapping_version": "test-1"}, "crops": [], "market_registry": {"markets": []}}
            (config / "mappings.json").write_text(json.dumps(mappings), encoding="utf-8")
            fews = raw / "fews.json"; fews.write_text("[]", encoding="utf-8")
            manifest = {"cutoff_month": "2026-07", "generated_at": "2026-08-25T00:00:00Z", "records": [{"source_id": "fews-net", "status": "downloaded", "path": fews.name, "bytes": fews.stat().st_size, "sha256": hashlib.sha256(fews.read_bytes()).hexdigest(), "retrieved_at": "2026-08-25T00:00:00Z"}]}
            manifest_path = audit / "raw_manifest.json"; manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            rows = [{"canonical_crop_id": crop, "canonical_market_id": market, "market_id": market, "market": market, "price_type": (price_types or ["retail"])[index % len(price_types or ["retail"])], "value": 100, "observation_date": "2026-07-15", "months": 36, "recent_completeness": 1.0} for crop in crops for index, market in enumerate(markets)]
            if review is not None:
                review["mapping_sha256"] = hashlib.sha256((config / "mappings.json").read_bytes()).hexdigest()
                review["audit_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                for item in review.get("review_records", []): item["audit_manifest_sha256"] = review["audit_manifest_sha256"]
                (audit / "stage_1_gate_review.json").write_text(json.dumps(review), encoding="utf-8")
            with patch.object(qualification_module, "ROOT", root), patch.object(qualification_module, "normalize_fews", return_value=(rows, [])), patch.object(qualification_module, "qualify_series", return_value=(rows, [])):
                return build_report(audit, "2026-07")

    def test_technical_success_without_rights_stays_out_of_gate_review(self):
        report = self._technical_gate_report(3)
        self.assertTrue(report["technical_gate_passed"])
        self.assertEqual(report["status"], "technical_review_required")
        self.assertFalse(report["price_source_qualified"])
        self.assertFalse(report["promotion_permitted"])

    def test_crop_gate_rejects_fewer_than_three_comparable_markets(self):
        report = self._technical_gate_report(2)
        self.assertFalse(report["technical_gate_passed"])
        self.assertEqual(len(report["crop_gate_rejections"]), 5)
        self.assertTrue(all("comparable_canonical_markets_under_3_for_price_type" in row["rejection_reasons"] for row in report["crop_gate_rejections"]))

    def test_crop_gate_does_not_pool_retail_and_wholesale_markets(self):
        report = self._technical_gate_report(3, price_types=["retail", "retail", "wholesale"])
        self.assertFalse(report["technical_gate_passed"])
        self.assertEqual({row["price_type"] for row in report["crop_gate_rejections"]}, {"retail", "wholesale"})
        self.assertTrue(all(row["qualified_market_count"] < 3 for row in report["crop_gate_rejections"]))

    def test_gate_review_requires_two_distinct_review_records(self):
        duplicate = {"schema_version": "1.0.0", "rights_approved": True, "mapping_reviewed": True, "mapping_version": "test-1", "review_records": [{"review_id": "one", "reviewer_id": "reviewer-a", "reviewed_at": "2026-08-25T00:00:00Z", "scope": "source_rights_mapping_and_claims", "decision": "pass"}, {"review_id": "one", "reviewer_id": "reviewer-a", "reviewed_at": "2026-08-25T00:00:00Z", "scope": "source_rights_mapping_and_claims", "decision": "pass"}]}
        report = self._technical_gate_report(3, duplicate)
        self.assertTrue(report["technical_gate_passed"])
        self.assertFalse(report["review_gate_passed"])
        self.assertFalse(report["price_source_qualified"])
        self.assertIn("two_distinct_valid_review_records_required", report["gate_review_evidence"]["rejection_reasons"])

    def test_review_records_require_aware_nonfuture_post_retrieval_timestamps(self):
        with tempfile.TemporaryDirectory() as folder:
            audit = Path(folder); manifest = audit / "raw_manifest.json"
            manifest.write_text(json.dumps({"generated_at": "2026-08-25T12:00:00Z", "records": [{"retrieved_at": "2026-08-25T12:00:00Z"}]}), encoding="utf-8")
            mappings = {"release_mapping_contract": {"mapping_version": "test-1"}}
            manifest_sha = __import__("hashlib").sha256(manifest.read_bytes()).hexdigest()
            base = {"schema_version": "1", "rights_approved": True, "mapping_reviewed": True, "mapping_version": "test-1", "mapping_sha256": "wrong", "audit_manifest_sha256": manifest_sha}
            for timestamp, expected in [("2026-08-25", "reviewed_at_must_be_timezone_aware_iso8601"), ("2026-08-26T00:00:00Z", "reviewed_at_is_in_the_future"), ("2026-08-25T11:00:00Z", "reviewed_at_precedes_manifest_generation_or_retrieval")]:
                review = {**base, "review_records": [{"review_id": "one", "reviewer_id": "a", "reviewed_at": timestamp, "scope": "source_rights_mapping_and_claims", "decision": "pass", "audit_manifest_sha256": manifest_sha}]}
                (audit / "stage_1_gate_review.json").write_text(json.dumps(review), encoding="utf-8")
                evidence = gate_review_evidence(audit, mappings, manifest, now=datetime(2026, 8, 25, 13, tzinfo=timezone.utc))
                self.assertIn(expected, evidence["rejection_reasons"])
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

    def _static_source(self):
        return {
            "source_id": "fews-net",
            "url": "https://fews.net/nigeria-weekly-fews-net-staple-food-price-data-1",
            "download_url": None,
            "retrieval": {
                "mode": "fews_static_export",
                "allowed_hosts": ["fews.net", "fdw.fews.net"],
                "required_link_label": "Nigeria Weekly FEWS NET Staple Food Price Data",
                "accepted_extensions": [".csv"],
                "required_columns": {
                    "country": ["country"], "date": ["period_date"],
                    "market": ["market"], "product": ["product"],
                    "price": ["value"], "price_type": ["price_type"],
                    "unit": ["unit"], "currency": ["currency"],
                    "public_usage": ["data_usage_policy"],
                },
                "retries": 1,
            },
        }

    def _static_html(self, links):
        return ("<html><body>" + "".join(f'<a href="{href}">{label}</a>' for href, label in links) + "</body></html>").encode()

    def _static_csv(self):
        return b"country,period_date,market,product,price_type,unit,currency,data_usage_policy,value\nNigeria,2026-08-31,Kano,Maize,Retail,kg,NGN,Public,100\n"

    def test_fews_static_discovery_selects_exact_official_csv_link(self):
        source = self._static_source()
        html = self._static_html([
            ("/exports/nigeria.xlsx", "Nigeria Weekly FEWS NET Staple Food Price Data (.xlsx) Download File"),
            ("https://fdw.fews.net/exports/nigeria.csv", "Nigeria Weekly FEWS NET Staple Food Price Data (.csv) Download File"),
            ("/exports/nigeria.json", "Nigeria Weekly FEWS NET Staple Food Price Data (.json) Download File"),
        ])
        result = discover_fews_static_export(source, opener=lambda request, timeout: _HttpBytesResponse(html, "text/html", source["url"]))
        self.assertEqual(result["url"], "https://fdw.fews.net/exports/nigeria.csv")
        self.assertIn(".csv", result["link_label"])

    def test_fews_static_discovery_rejects_external_or_ambiguous_links(self):
        source = self._static_source()
        external = self._static_html([("https://evil.example/nigeria.csv", "Nigeria Weekly FEWS NET Staple Food Price Data (.csv)")])
        with self.assertRaises(ValueError):
            discover_fews_static_export(source, opener=lambda request, timeout: _HttpBytesResponse(external, "text/html", source["url"]))
        for links in (
            [],
            [("/one.csv", "Nigeria Weekly FEWS NET Staple Food Price Data (.csv)"), ("/two.csv", "Nigeria Weekly FEWS NET Staple Food Price Data (.csv)")],
        ):
            html = self._static_html(links)
            with self.assertRaises(ValueError):
                discover_fews_static_export(source, opener=lambda request, timeout, html=html: _HttpBytesResponse(html, "text/html", source["url"]))

    def test_fews_static_download_rejects_bot_response_and_preserves_target(self):
        source = self._static_source(); target_content = b"previous"
        html = self._static_html([("https://fdw.fews.net/exports/nigeria.csv", "Nigeria Weekly FEWS NET Staple Food Price Data (.csv)")])
        def opener(request, timeout):
            if request.full_url.startswith(source["url"]):
                return _HttpBytesResponse(html, "text/html", source["url"])
            return _HttpBytesResponse(b"<html><script>captcha challenge</script></html>", "text/html", request.full_url)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "fews-net.csv"; target.write_bytes(target_content)
            with self.assertRaisesRegex(ValueError, "HTML|bot"):
                download_fews_static_export(source, target, opener=opener)
            self.assertEqual(target.read_bytes(), target_content)

    def test_fews_static_download_rejects_redirect_to_unknown_host(self):
        source = self._static_source()
        html = self._static_html([("https://fdw.fews.net/exports/nigeria.csv", "Nigeria Weekly FEWS NET Staple Food Price Data (.csv)")])
        def opener(request, timeout):
            if request.full_url.startswith(source["url"]):
                return _HttpBytesResponse(html, "text/html", source["url"])
            return _HttpBytesResponse(self._static_csv(), "text/csv", "https://evil.example/nigeria.csv")
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "configured FEWS host"):
                download_fews_static_export(source, Path(folder) / "fews-net.csv", opener=opener)

    def test_fews_static_download_is_atomic_and_records_hash_size_cutoff(self):
        source = self._static_source()
        html = self._static_html([("https://fdw.fews.net/exports/nigeria.csv", "Nigeria Weekly FEWS NET Staple Food Price Data (.csv)")])
        payload = self._static_csv()
        def opener(request, timeout):
            if request.full_url.startswith(source["url"]):
                return _HttpBytesResponse(html, "text/html", source["url"])
            return _HttpBytesResponse(payload, "text/csv", request.full_url)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "fews-net.csv"
            result = download_fews_static_export(source, target, cutoff_month="2026-08", opener=opener)
            self.assertEqual(result["bytes"], len(payload))
            self.assertEqual(result["sha256"], __import__("hashlib").sha256(payload).hexdigest())
            self.assertEqual(result["cutoff_month"], "2026-08")
            self.assertEqual(target.read_bytes(), payload)

    def test_fews_static_schema_requires_explicit_country_and_semantic_columns(self):
        source = self._static_source()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fews.csv"
            path.write_text("period_date,market,product,price_type,unit,currency,data_usage_policy,value\n2026-08-31,Kano,Maize,Retail,kg,NGN,Public,100\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "country"):
                validate_fews_static_csv(path, source["retrieval"])
            path.write_text("country,period_date,market,product,price_type,unit,currency,data_usage_policy,value\nGhana,2026-08-31,Kano,Maize,Retail,kg,NGN,Public,100\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside Nigeria"):
                validate_fews_static_csv(path, source["retrieval"])

    def test_static_failure_keeps_calculator_only_fallback_and_modes_cannot_be_stitched(self):
        source = self._static_source(); source["required_for_gate"] = True
        with tempfile.TemporaryDirectory() as folder:
            with patch("pipeline.source_audit.download", return_value={"source_id": "fews-net", "status": "failed", "error": "static export unavailable", "retrieval_mode": "fews_static_export"}):
                result = run_fetch(Path(folder), "2026-08", [source])
            report = json.loads((Path(folder) / "qualification_report.json").read_text(encoding="utf-8"))
        self.assertEqual(result, 1)
        self.assertEqual(report["status"], "calculator_only_fallback")
        with self.assertRaisesRegex(ValueError, "cannot be stitched"):
            run_fetch(Path(folder), "2026-08", [source, {**source, "retrieval": {"mode": "fews_v3_paginated_json"}}])

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
        timeouts, urls = [], []
        def opener(request, timeout):
            timeouts.append(timeout)
            urls.append(request.full_url)
            offset = int(request.full_url.split("offset=")[1].split("&", 1)[0])
            return _Response(pages[offset])
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "fews.json"
            result = download_fews_paginated({"download_url": "https://example.test/fews.json", "retrieval": {"mode": "fews_v3_paginated_json", "country_parameter": "country_code", "country_code": "NG", "page_size_parameter": "page_size", "offset_parameter": "offset", "response_total_field": "count", "response_rows_field": "results", "row_country_fields": ["country_code", "country"], "page_size": 2, "request_timeout_seconds": 7, "retries": 1}}, target, opener=opener, sleep=lambda _: None)
            payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual((result["pages"], result["rows"], payload["count"]), (2, 3, 3))
        self.assertEqual(len(payload["results"]), 3)
        self.assertEqual(timeouts, [7, 7])
        self.assertTrue(all("country_code=NG" in url and "country=NG" not in url for url in urls))
        self.assertEqual(result["filter"], {"country_code": "NG"})

    def test_fews_dataset_filter_is_preserved_in_documented_request(self):
        urls = []
        def opener(request, timeout):
            urls.append(request.full_url)
            return _Response({"count": 1, "results": [{"country": "Nigeria"}]})
        with tempfile.TemporaryDirectory() as folder:
            result = download_fews_paginated({
                "download_url": "https://example.test/marketpricefacts/",
                "retrieval": {
                    "mode": "fews_v3_paginated_json", "country_parameter": "country",
                    "country_value": "NG", "page_size_parameter": "page_size",
                    "offset_parameter": "offset", "response_total_field": "count",
                    "response_rows_field": "results", "row_country_fields": ["country_code", "country"],
                    "query_parameters": {"dataset": "FEWS_NET_Staple_Food_Price_Data", "fields": "website"},
                    "format_parameter": "format", "format": "json", "history_months": 60, "page_size": 1,
                    "request_timeout_seconds": 7, "retries": 1, "transient_statuses": [403, 429, 500],
                    "page_delay_seconds": 0,
                },
            }, Path(folder) / "fews.json", cutoff_month="2026-08", opener=opener, sleep=lambda _: None)
        self.assertEqual(result["filter"], {"country": "NG"})
        self.assertIn("country=NG", urls[0])
        self.assertIn("dataset=FEWS_NET_Staple_Food_Price_Data", urls[0])
        self.assertIn("format=json", urls[0])
        self.assertIn("start_date=2021-09-01", urls[0])
        self.assertIn("end_date=2026-08-31", urls[0])

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
            markets = [("kano", "fews-kano", "wfp-kano"), ("lagos", "fews-lagos", "wfp-lagos"), ("ibadan", "fews-ibadan", "wfp-ibadan")]
            mappings = {
                "release_mapping_contract": {"mapping_version": "test-1", "review_required_in_approval": True},
                "crops": [{"crop_id": form, "aliases": [f"Crop {index}"]} for index, form in enumerate(crop_forms)],
                "app_crop_mappings": [{"crop_form_id": form, "app_crop_id": f"app-{index}"} for index, form in enumerate(crop_forms)],
                "market_registry": {"registry_version": "test-1", "markets": [{"canonical_market_id": f"market-{name}", "source_identities": [{"source_id": "fews-net", "source_market_id": fews_id}, {"source_id": "wfp-hdx", "source_market_id": wfp_id}]} for name, fews_id, wfp_id in markets]},
            }
            sources = {"sources": [{"source_id": "wfp-hdx", "retrieval": {"native_columns": {"date": "date", "market_id": "market_id", "market": "market", "commodity_id": "commodity_id", "commodity": "commodity", "unit": "unit", "price": "price", "price_type": "pricetype", "currency": "currency", "flag": "priceflag"}}}]}
            (config / "mappings.json").write_text(json.dumps(mappings), encoding="utf-8")
            (config / "sources.json").write_text(json.dumps(sources), encoding="utf-8")
            fews_rows, wfp_rows = [], []
            for index in range(5):
                for offset in range(36):
                    year, month_number = divmod(2023 * 12 + 7 + offset, 12)
                    observed = f"{year:04d}-{month_number + 1:02d}-15"
                    for name, fews_id, wfp_id in markets:
                        fews_rows.append({"period_date": observed, "data_usage_policy": "Public", "price_type": "Retail", "unit": "kg", "currency": "NGN", "market": name.title(), "market_id": fews_id, "product": f"Crop {index}", "product_id": f"f{index}", "value": 100, "id": f"f-{index}-{offset}-{name}"})
                        wfp_rows.append(f"{observed},{wfp_id},{name.title()},w{index},Crop {index},kg,100,Retail,NGN,actual")
            fews_path = raw / "fews-net.json"; fews_path.write_text(json.dumps({"count": len(fews_rows), "results": fews_rows}), encoding="utf-8")
            wfp_path = raw / "wfp-hdx.csv"; wfp_path.write_text("date,market_id,market,commodity_id,commodity,unit,price,pricetype,currency,priceflag\n" + "\n".join(wfp_rows) + "\n", encoding="utf-8")
            def record(source_id, path): return {"source_id": source_id, "status": "downloaded", "path": path.name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "retrieved_at": "2026-08-25T00:00:00Z"}
            manifest_path = audit / "raw_manifest.json"; manifest_path.write_text(json.dumps({"cutoff_month": "2026-07", "generated_at": "2026-08-25T00:00:00Z", "records": [record("fews-net", fews_path), record("wfp-hdx", wfp_path)]}), encoding="utf-8")
            documents = {"manifest.json": {"snapshot_id": "old", "stage_1_approved": False, "artifacts": ["catalog.json", "defaults.json", "forecasts.json", "quality.json"]}, "catalog.json": {"snapshot_id": "old", "crops": [{"crop_id": f"app-{index}"} for index in range(5)]}, "defaults.json": {"snapshot_id": "old"}, "forecasts.json": {"snapshot_id": "old"}, "quality.json": {"snapshot_id": "old", "pipeline": {}}}
            for name, document in documents.items(): (data / name).write_text(json.dumps(document), encoding="utf-8")
            with patch.object(qualification_module, "ROOT", root), patch.object(promotion_module, "ROOT", root):
                manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                review = {"schema_version": "1.0.0", "rights_approved": True, "mapping_reviewed": True, "mapping_version": "test-1", "mapping_sha256": hashlib.sha256((config / "mappings.json").read_bytes()).hexdigest(), "audit_manifest_sha256": manifest_sha, "review_records": [{"review_id": "rights-review", "reviewer_id": "reviewer-a", "reviewed_at": "2026-08-25T00:00:00Z", "scope": "source_rights_mapping_and_claims", "decision": "pass", "audit_manifest_sha256": manifest_sha}, {"review_id": "mapping-review", "reviewer_id": "reviewer-b", "reviewed_at": "2026-08-25T01:00:00Z", "scope": "source_rights_mapping_and_claims", "decision": "pass", "audit_manifest_sha256": manifest_sha}]}
                (audit / "stage_1_gate_review.json").write_text(json.dumps(review), encoding="utf-8")
                report = build_report(audit, "2026-07")
                self.assertEqual(report["cross_source_check"]["status"], "comparable")
                self.assertEqual(len(report["publishable_series"]), 15)
                self.assertFalse(report["gate_review_evidence"]["trust_authority"])
                self.assertTrue(report["local_review_complete"])
                self.assertFalse(report["approval_ready"])
                report_path = audit / "qualification_report.json"; report_path.write_text(json.dumps(report), encoding="utf-8")
                approval = {"approval_type": "protected_external_signed", "stage_1_approved": True, "rights_approved": True, "allow_price_suggestions": True, "reviewer": "reviewer", "reviewed_at": "2026-08-25T00:00:00Z", "qualification_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(), "qualification_digest": report["qualification_digest"], "audit_manifest_sha256": manifest_sha, "selected_series_sha256": qualification_module.canonical_digest(report["publishable_series"]), "mapping_version": "test-1", "mapping_sha256": hashlib.sha256((config / "mappings.json").read_bytes()).hexdigest(), "mapping_reviewed": True}
                approval_path = root / "approval.json"; approval_path.write_text(json.dumps(approval), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "signature verification is not configured"):
                    promote(audit, approval_path, data)
            self.assertFalse((data / "price_suggestions.json").exists())

    def test_promotion_recomputes_and_rejects_forged_stale_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); audit = root / "audit"; raw = audit / "raw"; data = root / "data"; raw.mkdir(parents=True); data.mkdir()
            (audit / "raw_manifest.json").write_text(json.dumps({"cutoff_month": "2026-07", "generated_at": "2026-08-25T00:00:00Z", "records": []}), encoding="utf-8")
            forged = {"cutoff_month": "2026-07", "qualification_digest": "forged", "technical_gate_passed": True, "local_review_complete": True, "selected_crops": [{"canonical_crop_id": "maize"}] * 5, "publishable_series": [{"canonical_crop_id": "maize", "canonical_market_id": "market-a", "price_type": "retail"}], "cross_source_check": {"status": "comparable", "disagreement_count": 0}}
            report_path = audit / "qualification_report.json"; report_path.write_text(json.dumps(forged), encoding="utf-8")
            approval = {"approval_type": "protected_external_signed", "stage_1_approved": True, "rights_approved": True, "allow_price_suggestions": True, "reviewer": "reviewer", "reviewed_at": "2026-08-25T01:00:00Z", "qualification_report_sha256": __import__("hashlib").sha256(report_path.read_bytes()).hexdigest(), "qualification_digest": "forged", "audit_manifest_sha256": __import__("hashlib").sha256((audit / "raw_manifest.json").read_bytes()).hexdigest(), "selected_series_sha256": "forged", "mapping_version": "x", "mapping_sha256": "x", "mapping_reviewed": True}
            approval_path = root / "approval.json"; approval_path.write_text(json.dumps(approval), encoding="utf-8")
            (data / "manifest.json").write_text(json.dumps({"snapshot_id": "old"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "supplied qualification report"):
                promote(audit, approval_path, data)

    def test_mixed_transaction_types_do_not_pool_markets_for_the_crop_gate(self):
        report = self._report_from_eligible_series([
            *self._cohort("maize", "retail", 2),
            *self._cohort("maize", "wholesale", 1),
        ])
        rejected = {(item["price_type"], item["qualified_market_count"])
                    for item in report["crop_gate_rejections"]}
        self.assertEqual(rejected, {("retail", 2), ("wholesale", 1)})
        self.assertEqual(report["ranked_technically_qualified_crops"], [])
        self.assertEqual(report["publishable_series"], [])

    def test_publishable_series_are_limited_to_selected_crop_type_cohorts(self):
        eligible = []
        for index in range(5):
            eligible.extend(self._cohort(f"crop-{index}", "retail", 3))
        eligible.extend(self._cohort("crop-0", "wholesale", 3))
        report = self._report_from_eligible_series(eligible)
        selected = {(item["canonical_crop_id"], item["price_type"])
                    for item in report["selected_crops"]}
        published = {(item["canonical_crop_id"], item["price_type"])
                     for item in report["publishable_series"]}
        self.assertTrue(report["technical_gate_passed"])
        self.assertEqual(len(report["publishable_series"]), 15)
        self.assertEqual(published, selected)
        self.assertNotIn(("crop-0", "wholesale"), published)

    def test_five_crop_gate_requires_five_distinct_crop_ids(self):
        eligible = []
        for crop_id, price_type in [
            ("crop-0", "retail"), ("crop-0", "wholesale"),
            ("crop-1", "retail"), ("crop-2", "retail"), ("crop-3", "retail"),
        ]:
            eligible.extend(self._cohort(crop_id, price_type, 3))
        report = self._report_from_eligible_series(eligible)
        self.assertEqual(len(report["ranked_technically_qualified_crops"]), 5)
        self.assertFalse(report["technical_gate_passed"])
        self.assertEqual(report["selected_crops"], [])
        self.assertEqual(report["publishable_series"], [])

    @staticmethod
    def _cohort(crop_id, price_type, market_count):
        return [{"canonical_crop_id": crop_id, "canonical_market_id": f"market-{index}",
                 "market": f"Market {index}", "price_type": price_type,
                 "recent_completeness": 1.0, "months": 36}
                for index in range(market_count)]

    @staticmethod
    def _report_from_eligible_series(eligible):
        import hashlib
        import pipeline.qualification as qualification_module
        with tempfile.TemporaryDirectory() as folder:
            audit = Path(folder); raw = audit / "raw"; raw.mkdir()
            payload = b"{}"; (raw / "fews.json").write_bytes(payload)
            manifest = {"cutoff_month": "2026-07", "records": [{
                "source_id": "fews-net", "status": "downloaded", "path": "fews.json",
                "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                "retrieved_at": "2026-08-25T00:00:00Z",
            }]}
            (audit / "raw_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(qualification_module, "normalize_fews", return_value=([], [])), \
                 patch.object(qualification_module, "qualify_series", return_value=(eligible, [])):
                return build_report(audit, "2026-07")


if __name__ == "__main__":
    unittest.main()
