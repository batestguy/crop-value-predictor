"""Build the separately labelled World Bank modeled-estimate lane.

This module never changes the observed-price Stage 1 decision. It creates a
reviewable, same-origin artifact only for modeled estimates, with explicit
provenance and source-aligned crop forms.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

try:
    from pipeline.qualification import qualify_series
except ModuleNotFoundError:
    from qualification import qualify_series

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "world-bank-rtfp"
FIELD_MAP = {
    "maize_fao": {"crop_form_id": "maize-grain-white", "app_crop_id": "maize-white"},
    "rice_fao": {"crop_form_id": "rice-milled", "app_crop_id": "rice-milled"},
    "gari_fao": {"crop_form_id": "gari-white", "app_crop_id": "gari-white"},
    "yam": {"crop_form_id": "yam-fresh", "app_crop_id": "yam"},
    "sorghum_fao": {"crop_form_id": "sorghum-white", "app_crop_id": "sorghum"},
    "millet": {"crop_form_id": "millet-pearl", "app_crop_id": "millet"},
}
COMPONENT_RE = re.compile(r"(?:^|,\s*)([a-z0-9_]+)\s*\(([^,]+),\s*Index Weight", re.I)
MASS_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)\s*(kg|kgs|kilogram|kilograms|g|gram|grams)$", re.I)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _component_units(value: object) -> dict[str, str]:
    return {match.group(1).lower(): match.group(2).strip() for match in COMPONENT_RE.finditer(str(value or ""))}


def _kg_from_component(value: str | None) -> float | None:
    if not value:
        return None
    match = MASS_RE.fullmatch(" ".join(value.lower().split()))
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2).lower()
    if number <= 0:
        return None
    return number / 1000 if unit in {"g", "gram", "grams"} else number


def _rows_from_zip(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv") and not name.endswith("/")]
        if len(members) != 1:
            raise ValueError(f"expected one World Bank CSV member, found {len(members)}")
        with archive.open(members[0]) as binary:
            return list(csv.DictReader(line.decode("utf-8-sig") for line in binary))


def normalize_modeled(path: Path, cutoff: str) -> tuple[list[dict], list[dict]]:
    accepted, rejected = [], []
    rows = _rows_from_zip(path)
    for row_number, row in enumerate(rows, 2):
        if row.get("ISO3") != "NGA":
            rejected.append({"source": SOURCE_ID, "source_row": row_number, "reason": "row_outside_nigeria"})
            continue
        observed = str(row.get("price_date") or "")[:10]
        ym = observed[:7]
        if not re.fullmatch(r"\d{4}-\d{2}", ym) or ym > cutoff:
            continue
        market = " ".join(str(row.get("mkt_name") or "").split())
        geo_id = str(row.get("geo_id") or "").strip()
        if not market or not geo_id:
            rejected.append({"source": SOURCE_ID, "source_row": row_number, "month": ym, "reason": "missing_market_identity"})
            continue
        if geo_id == "gid_nga_national_average":
            continue
        units = _component_units(row.get("components"))
        for field, mapping in FIELD_MAP.items():
            raw = row.get(f"c_{field}")
            package_kg = _kg_from_component(units.get(field))
            if raw in (None, ""):
                continue
            if package_kg is None:
                rejected.append({"source": SOURCE_ID, "source_row": row_number, "month": ym, "field": field, "reason": "unknown_component_mass"})
                continue
            try:
                value = float(raw) / package_kg
            except (TypeError, ValueError):
                rejected.append({"source": SOURCE_ID, "source_row": row_number, "month": ym, "field": field, "reason": "non_numeric_estimate"})
                continue
            if value <= 0:
                rejected.append({"source": SOURCE_ID, "source_row": row_number, "month": ym, "field": field, "reason": "non_positive_estimate"})
                continue
            accepted.append({
                "source": SOURCE_ID,
                "canonical_crop_id": mapping["crop_form_id"],
                "app_crop_id": mapping["app_crop_id"],
                "source_product": field,
                "source_commodity_id": field,
                "market": market,
                "market_id": geo_id,
                "canonical_market_id": f"world-bank:{geo_id}",
                "market_kind": "source_market",
                "month": ym,
                "observation_date": observed,
                "price_type": "modeled_estimate",
                "transaction_type": "modeled_estimate",
                "value": value,
                "source_package_unit": units[field],
                "package_kg": package_kg,
                "unit": "NGN/kg",
                "currency": row.get("currency") or "NGN",
                "provenance": "modeled_month_close",
                "rights": "open_data_reviewed_for_modeled_lane",
                "source_row_id": f"{geo_id}:{observed}:{field}",
                "source_row": row_number,
            })
    return accepted, rejected


def build_modeled_snapshot(
    raw_path: Path,
    cutoff: str,
    snapshot_date: date,
    *,
    output_path: Path | None = None,
) -> tuple[dict, dict]:
    accepted, rejected_rows = normalize_modeled(raw_path, cutoff)
    eligible, rejected_series = qualify_series(accepted, cutoff, snapshot_date)
    eligible_keys = {(item["canonical_crop_id"], item["canonical_market_id"], item["price_type"]) for item in eligible}
    latest: dict[tuple[str, str, str], dict] = {}
    for row in accepted:
        key = (row["canonical_crop_id"], row["canonical_market_id"], row["price_type"])
        if key in eligible_keys and (key not in latest or row["observation_date"] > latest[key]["observation_date"]):
            latest[key] = row
    source_hash = sha256(raw_path)
    suggestions = []
    for key, row in sorted(latest.items()):
        age = (snapshot_date - date.fromisoformat(row["observation_date"])).days
        suggestions.append({
            "suggestion_id": f"world-bank-rtfp:{row['canonical_crop_id']}:{row['canonical_market_id']}:{row['observation_date']}",
            "crop_id": row["app_crop_id"],
            "crop_form_id": row["canonical_crop_id"],
            "mapping_version": "modeled-lane-1.0.0",
            "canonical_market_id": row["canonical_market_id"],
            "market_id": row["canonical_market_id"],
            "market_name": row["market"],
            "price_type": "modeled_estimate",
            "observation_date": row["observation_date"],
            "value_ngn_per_kg": round(row["value"], 6),
            "source": {
                "source_id": SOURCE_ID,
                "attribution": "World Bank Real-Time Food Prices, Nigeria, modeled monthly close estimate.",
                "raw_artifact_sha256": source_hash,
                "commodity_id": row["source_commodity_id"],
                "commodity_label": row["source_product"],
            },
            "freshness": {"snapshot_date": snapshot_date.isoformat(), "age_days": age, "limit_days": 75},
            "provenance": {
                "source_row_id": row["source_row_id"],
                "source_row": row["source_row"],
                "normalized_from_unit": row["source_package_unit"],
                "kind": "modeled_estimate",
                "transaction_type_status": "unknown",
                "warning": "Modeled estimate; not an observed retail, wholesale, or farmer selling price.",
            },
        })
    crops = Counter(item["crop_id"] for item in suggestions)
    report = {
        "schema_version": "1.0.0",
        "lane": "world-bank-modeled-estimates",
        "status": "modeled_estimate_ready_for_review" if len(crops) >= 5 else "blocked",
        "stage_1_approved": False,
        "cutoff_month": cutoff,
        "snapshot_date": snapshot_date.isoformat(),
        "source_id": SOURCE_ID,
        "source_artifact_sha256": source_hash,
        "accepted_rows": len(accepted),
        "rejected_rows": len(rejected_rows),
        "eligible_series": len(eligible),
        "rejected_series": len(rejected_series),
        "qualified_crop_forms": sorted(crops),
        "qualified_crop_counts": dict(sorted(crops.items())),
        "transaction_type": "unknown",
        "provenance": "modeled_month_close",
        "warning": "Modeled estimates are not observed retail, wholesale, or farmer selling prices; this lane never qualifies Stage 1.",
        "rejection_reasons": dict(sorted(Counter(reason for row in rejected_rows for reason in [row.get("reason", "unknown")]).items())),
    }
    document = {"schema_version": "1.0.0", "snapshot_id": f"world-bank-modeled-{snapshot_date.isoformat()}", "mapping_version": "modeled-lane-1.0.0", "lane": "world-bank-modeled-estimates", "warning": report["warning"], "suggestions": suggestions}
    if output_path:
        output_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return document, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--cutoff-month", required=True)
    parser.add_argument("--snapshot-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    document, report = build_modeled_snapshot(args.raw, args.cutoff_month, date.fromisoformat(args.snapshot_date), output_path=args.output)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "suggestions": len(document["suggestions"]), "qualified_crop_forms": report["qualified_crop_forms"]}))
    return 0 if report["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
