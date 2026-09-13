"""Promote an explicitly reviewed Stage 1 report into a static price snapshot.

This is deliberately a manual command.  It has no network code and writes the
manifest last, so an invalid review or malformed artifact leaves the previous
browser release untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

try:
    from pipeline.qualification import _downloaded_record, _retrieval_date, build_report, canonical_digest, gate_review_evidence, normalize_fews, qualify_series, report_digest
except ModuleNotFoundError:
    from qualification import _downloaded_record, _retrieval_date, build_report, canonical_digest, gate_review_evidence, normalize_fews, qualify_series, report_digest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "public" / "data" / "v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return value


def _validate_approval(audit_dir: Path, approval: dict, report_path: Path, report: dict,
                       recomputed: dict, mappings: dict) -> None:
    required = {"approval_type", "stage_1_approved", "rights_approved", "allow_price_suggestions", "reviewer", "reviewed_at", "qualification_report_sha256", "qualification_digest", "audit_manifest_sha256", "selected_series_sha256", "mapping_version", "mapping_sha256", "mapping_reviewed"}
    if not required.issubset(approval):
        raise ValueError("approval is missing an explicit review field")
    if approval["stage_1_approved"] is not True or approval["rights_approved"] is not True or approval["allow_price_suggestions"] is not True:
        raise ValueError("approval does not explicitly authorize price suggestions")
    if not isinstance(approval["reviewer"], str) or not approval["reviewer"].strip() or not isinstance(approval["reviewed_at"], str):
        raise ValueError("approval reviewer and reviewed_at are required")
    if approval["qualification_report_sha256"] != sha256(report_path):
        raise ValueError("approval is not bound to this qualification report")
    if report.get("qualification_digest") != report_digest(report):
        raise ValueError("supplied qualification report digest is invalid")
    if report_digest(report) != report_digest(recomputed) or report.get("publishable_series") != recomputed.get("publishable_series"):
        raise ValueError("supplied qualification report does not match current manifest-bound raw inputs")
    manifest_path = audit_dir / "raw_manifest.json"
    if approval["qualification_digest"] != report_digest(recomputed):
        raise ValueError("approval is not bound to the recomputed qualification digest")
    if approval["audit_manifest_sha256"] != sha256(manifest_path):
        raise ValueError("approval is not bound to the immutable raw manifest")
    if approval["selected_series_sha256"] != canonical_digest(recomputed.get("publishable_series", [])):
        raise ValueError("approval is not bound to the recomputed selected series")
    contract = mappings.get("release_mapping_contract", {})
    if contract.get("review_required_in_approval") is not True or approval["mapping_reviewed"] is not True:
        raise ValueError("reviewed crop/form and market mapping approval is required")
    if approval["mapping_version"] != contract.get("mapping_version"):
        raise ValueError("approval mapping version does not match the release contract")
    if approval["mapping_sha256"] != sha256(ROOT / "config" / "mappings.json"):
        raise ValueError("approval is not bound to this mappings registry")
    if not recomputed.get("technical_gate_passed") or not recomputed.get("local_review_complete") or len(recomputed.get("selected_crops", [])) < 5:
        raise ValueError("Stage 1 technical, rights, mapping, and two-review gate did not pass")
    review = gate_review_evidence(audit_dir, mappings, manifest_path)
    if review["status"] != "passed":
        raise ValueError("manifest-bound rights, mapping, and two-review evidence is required")
    if recomputed.get("cross_source_check", {}).get("disagreement_count", 0):
        raise ValueError("cross-source disagreement prevents promotion")
    if recomputed.get("cross_source_check", {}).get("status") != "comparable":
        raise ValueError("cross-source evidence is not comparable through reviewed market crosswalks")
    # This repository intentionally has no protected signing key or external
    # approval verifier.  A local JSON file can be fabricated, regardless of
    # its reviewer ID or hash fields, so do not promote on that representation.
    if approval["approval_type"] != "protected_external_signed":
        raise ValueError("a protected external signed approval artifact is required")
    raise ValueError("protected external approval signature verification is not configured; promotion fails closed")


def build_price_suggestions(audit_dir: Path, report: dict, catalog: dict) -> list[dict]:
    manifest = read_json(audit_dir / "raw_manifest.json")
    fews = _downloaded_record(manifest, "fews-net")
    if not fews:
        raise ValueError("primary FEWS artifact is absent")
    mappings = read_json(ROOT / "config" / "mappings.json")
    accepted, _ = normalize_fews(audit_dir / "raw" / fews["path"], report["cutoff_month"], mappings)
    eligible, _ = qualify_series(accepted, report["cutoff_month"], _retrieval_date(manifest, "fews-net"))
    selected_cohorts = {(item["canonical_crop_id"], item["price_type"])
                        for item in report.get("selected_crops", [])}
    selected = {(item["canonical_crop_id"], item.get("canonical_market_id"), item["price_type"])
                for item in report.get("publishable_series", [])}
    if not selected_cohorts or any((crop_id, price_type) not in selected_cohorts
                                   for crop_id, _market_id, price_type in selected):
        raise ValueError("report publishable series are not limited to selected crop/type cohorts")
    eligible_keys = {(item["canonical_crop_id"], item.get("canonical_market_id"), item["price_type"]) for item in eligible}
    if not selected or not selected.issubset(eligible_keys):
        raise ValueError("report references missing or no-longer-qualified primary series")
    crop_ids = {crop["crop_id"] for crop in catalog.get("crops", [])}
    contract = mappings.get("release_mapping_contract", {})
    mapping_version = contract.get("mapping_version")
    app_mappings = {item.get("crop_form_id"): item for item in mappings.get("app_crop_mappings", [])}
    latest: dict[tuple[str, str, str], dict] = {}
    for row in accepted:
        key = (row["canonical_crop_id"], row.get("canonical_market_id"), row["price_type"])
        if key in selected and (key not in latest or (row["observation_date"], row["source_row"]) > (latest[key]["observation_date"], latest[key]["source_row"])):
            latest[key] = row
    snapshot_date = _retrieval_date(manifest, "fews-net")
    result = []
    for key, row in sorted(latest.items()):
        crop_mapping = app_mappings.get(row["canonical_crop_id"])
        if not crop_mapping or crop_mapping.get("app_crop_id") not in crop_ids:
            raise ValueError(f"unreviewed or incompatible crop/form mapping: {row['canonical_crop_id']}")
        if not row.get("canonical_market_id"):
            raise ValueError("unreviewed source market crosswalk reached promotion")
        observation = date.fromisoformat(row["observation_date"])
        age = (snapshot_date - observation).days
        if age < 0 or age > 75:
            raise ValueError("stale price row reached promotion")
        result.append({
            "suggestion_id": f"fews-net:{row['canonical_crop_id']}:{row['canonical_market_id']}:{row['price_type']}:{row['observation_date']}",
            "crop_id": crop_mapping["app_crop_id"], "crop_form_id": row["canonical_crop_id"], "mapping_version": mapping_version,
            "canonical_market_id": row["canonical_market_id"], "market_id": row["canonical_market_id"], "market_name": row["market"], "price_type": row["price_type"], "observation_date": row["observation_date"], "value_ngn_per_kg": row["value"],
            "source": {"source_id": "fews-net", "attribution": "FEWS NET Nigeria staple food price data.", "raw_artifact_sha256": fews["sha256"], "commodity_id": row.get("source_commodity_id", ""), "commodity_label": row.get("source_commodity_label", row["source_product"])},
            "freshness": {"snapshot_date": snapshot_date.isoformat(), "age_days": age, "limit_days": 75},
            "provenance": {"source_row_id": str(row.get("source_row_id") or ""), "source_row": row["source_row"], "normalized_from_unit": str(row["source_package_unit"])},
        })
    if len(result) < 5:
        raise ValueError("fewer than five approved crop/market suggestions remain")
    return result


def promote(audit_dir: Path, approval_path: Path, data_dir: Path = DEFAULT_DATA) -> str:
    report_path = audit_dir / "qualification_report.json"
    report, approval = read_json(report_path), read_json(approval_path)
    mappings = read_json(ROOT / "config" / "mappings.json")
    recomputed = build_report(audit_dir, report.get("cutoff_month", ""))
    _validate_approval(audit_dir, approval, report_path, report, recomputed, mappings)
    current_manifest, catalog = read_json(data_dir / "manifest.json"), read_json(data_dir / "catalog.json")
    suggestions = build_price_suggestions(audit_dir, recomputed, catalog)
    snapshot_id = f"price-suggestions-{recomputed['snapshot_date']}"
    price_document = {"schema_version": "1.1.0", "snapshot_id": snapshot_id, "mapping_version": mappings["release_mapping_contract"]["mapping_version"], "suggestions": suggestions}
    markets = {item["canonical_market_id"]: {"market_id": item["canonical_market_id"], "canonical_market_id": item["canonical_market_id"], "market_name": item["market_name"], "covered_crop_ids": []} for item in suggestions}
    for item in suggestions:
        if item["crop_id"] not in markets[item["market_id"]]["covered_crop_ids"]:
            markets[item["market_id"]]["covered_crop_ids"].append(item["crop_id"])
    approved_markets = {"schema_version": "1.0.0", "snapshot_id": snapshot_id, "markets": sorted(markets.values(), key=lambda item: item["market_id"])}
    artifacts = ["catalog.json", "defaults.json", "forecasts.json", "quality.json", "approved_markets.json", "price_suggestions.json"]
    documents = {name: read_json(data_dir / name) for name in ["catalog.json", "defaults.json", "forecasts.json", "quality.json"]}
    for document in documents.values(): document["snapshot_id"] = snapshot_id
    documents["quality.json"]["pipeline"] = {"status": "approved_price_suggestions", "generated_at": approval["reviewed_at"], "source_count": 1, "last_known_good": True}
    staged = {**documents, "approved_markets.json": approved_markets, "price_suggestions.json": price_document}
    new_manifest = {**current_manifest, "schema_version": "1.2.0", "snapshot_id": snapshot_id, "generated_at": approval["reviewed_at"], "stage_1_approved": True, "artifacts": artifacts, "warnings": ["Approved FEWS NET price suggestions are editable local prefills, not forecasts or guarantees."]}
    targets = [data_dir / name for name in [*staged, "manifest.json"]]
    previous = {target: target.read_bytes() if target.exists() else None for target in targets}
    def write_atomic(target: Path, document: dict) -> None:
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
    try:
        # The manifest arrives last, so browsers never discover a partial
        # release.  Rollback also restores every local artifact on disk if a
        # filesystem failure occurs during promotion.
        for name, document in staged.items(): write_atomic(data_dir / name, document)
        write_atomic(data_dir / "manifest.json", new_manifest)
    except Exception:
        for target, content in previous.items():
            if content is None:
                if target.exists(): target.unlink()
            else:
                temporary = target.with_name(target.name + ".rollback")
                temporary.write_bytes(content)
                temporary.replace(target)
        raise
    return snapshot_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True, help="review artifact with report checksum and explicit authorizations")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args(argv)
    print(json.dumps({"snapshot_id": promote(args.audit_dir, args.approval, args.data_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
