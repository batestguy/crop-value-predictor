"""Fail-closed Stage 1 qualification over immutable audit artifacts."""
from __future__ import annotations

import argparse, calendar, csv, hashlib, io, json, re, zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

try:
    from pipeline.source_audit import profile_file, profile_json_rows
except ModuleNotFoundError:  # direct ``python pipeline/qualification.py`` invocation
    from source_audit import profile_file, profile_json_rows

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = ROOT / "audit-output-local"
FRESHNESS_DAYS = 75
MIN_HISTORY = 36
RECENT_WINDOW = 36


def month(value: object) -> str | None:
    text = str(value or "")[:10]
    return text[:7] if re.match(r"^\d{4}-\d{2}", text) else None


def shift_month(ym: str, delta: int) -> str:
    year, number = map(int, ym.split("-"))
    index = year * 12 + number - 1 + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _month_end(ym: str) -> date:
    year, number = map(int, ym.split("-"))
    return date(year, number, calendar.monthrange(year, number)[1])


def _date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _label(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def canonical_crop(product: str, mappings: dict | None = None) -> str:
    """Use exact aliases so crop forms never merge by substring."""
    value = _label(product)
    for item in (mappings or {}).get("crops", []):
        aliases = [item.get("crop_id", ""), *item.get("aliases", [])]
        if value in {_label(alias) for alias in aliases if alias}:
            return item["crop_id"]
    return _slug(value)


def convert_kg(unit: str, common_unit: str = "") -> float | None:
    """Parse explicit mass package sizes; reject counts and ambiguous units."""
    del common_unit
    raw = _label(unit).replace("_", " ")
    if raw in {"kg", "kgs", "kilogram", "kilograms"}:
        return 1.0
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(?:kg|kgs|kilogram|kilograms)", raw)
    if not match:
        return None
    value = float(match.group(1))
    return value if value > 0 else None


def _market(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def canonical_market(source_id: str, source_market_id: object, mappings: dict | None = None) -> str | None:
    """Resolve a source market only through the reviewed registry.

    A registry-free caller retains its source market ID for unit tests and
    exploratory normalization.  The repository release contract always has a
    registry (which may be empty), making unknown production markets fail.
    """
    if not mappings or "market_registry" not in mappings:
        return str(source_market_id or "").strip() or None
    registry = mappings.get("market_registry") or {}
    for market in registry.get("markets", []):
        for identity in market.get("source_identities", []):
            if identity.get("source_id") == source_id and str(identity.get("source_market_id", "")).strip() == str(source_market_id or "").strip():
                return str(market.get("canonical_market_id") or "").strip() or None
    return None


def app_crop_mapping(crop_form_id: str, mappings: dict) -> dict | None:
    return next((item for item in mappings.get("app_crop_mappings", []) if item.get("crop_form_id") == crop_form_id), None)


def normalize_fews(path: Path, cutoff: str, mappings: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Normalize immutable FEWS CSV or API JSON; never infer a mass unit."""
    accepted, rejected = [], []
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("data", payload.get("results", [])) if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            return [], [{"source": "fews-net", "reason": "invalid_json_row_envelope"}]
    else:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    for row_number, row in enumerate(rows, 1):
            def value(*names: str) -> object:
                return next((row.get(name) for name in names if row.get(name) not in (None, "")), "")
            ym = month(value("period_date", "date", "date_start"))
            transaction = _label(row.get("price_type"))
            package_kg = convert_kg(str(value("unit")), str(value("common_unit")))
            raw_value = str(value("value", "price")).strip().replace(",", "")
            market = _market(value("market", "market_name"))
            market_id = str(value("market_id", "market_code") or market).strip()
            product = str(value("product", "commodity", "commodity_name")).strip()
            reason = None
            if not ym or ym > cutoff: reason = "outside_cutoff_or_missing_month"
            elif _label(value("data_usage_policy", "usage_policy", "access")) != "public": reason = "rights_not_public"
            elif transaction not in {"retail", "wholesale"}: reason = "transaction_type_not_retail_or_wholesale"
            elif package_kg is None: reason = "unknown_or_count_based_unit"
            elif str(value("currency")).upper() != "NGN": reason = "currency_not_ngn"
            elif not market or not market_id: reason = "missing_market"
            elif not _label(product): reason = "missing_product"
            elif mappings and canonical_crop(product, mappings) not in {item.get("crop_id") for item in mappings.get("crops", [])}: reason = "unmapped_commodity"
            elif not raw_value: reason = "missing_value"
            if reason:
                rejected.append({"source": "fews-net", "source_row": row_number, "month": ym, "product": product, "market": market, "reason": reason})
                continue
            try: package_value = float(raw_value)
            except ValueError:
                rejected.append({"source": "fews-net", "source_row": row_number, "month": ym, "reason": "non_numeric_value"}); continue
            if package_value <= 0:
                rejected.append({"source": "fews-net", "source_row": row_number, "month": ym, "reason": "non_positive_value"}); continue
            observation = _date(value("period_date", "date", "date_start")) or _month_end(ym)
            canonical_market_id = canonical_market("fews-net", market_id, mappings)
            accepted.append({
                "source": "fews-net", "canonical_crop_id": canonical_crop(product, mappings), "source_product": product,
                "source_commodity_id": str(value("commodity_id", "product_id", "product_code") or "").strip(), "source_commodity_label": product,
                "market": market, "market_id": market_id, "canonical_market_id": canonical_market_id, "month": ym, "observation_date": observation.isoformat(),
                "price_type": transaction, "transaction_type": transaction, "value": package_value / package_kg,
                "source_package_value": package_value, "source_package_unit": value("unit"), "package_kg": package_kg,
                "unit": "NGN/kg", "currency": "NGN", "provenance": "observed", "rights": "public",
                "source_row_id": value("id", "uuid", "record_id"), "source_row": row_number,
            })
    return accepted, rejected


def normalize_wfp(path: Path, cutoff: str, mappings: dict | None = None, native_columns: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Normalize WFP CSV only when every semantic field is explicit."""
    accepted, rejected = [], []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        native_columns = native_columns or {"date": "date", "market_id": "market_id", "market": "market", "commodity_id": "commodity_id", "commodity": "commodity", "unit": "unit", "price": "price", "price_type": "price_type", "currency": "currency", "flag": "flag"}
        fields = {str(field).strip().lower(): field for field in (reader.fieldnames or [])}
        required = {"date", "market_id", "market", "commodity_id", "commodity", "unit", "price", "price_type", "currency"}
        missing = sorted(name for name in required if str(native_columns.get(name, name)).lower() not in fields)
        if missing:
            return [], [{"source": "wfp-hdx", "reason": "required_columns_missing", "columns": missing}]
        for row_number, row in enumerate(reader, 2):
            def value(name: str) -> str: return str(row.get(fields[str(native_columns.get(name, name)).lower()], "")).strip()
            ym = month(value("date")); price_type = _label(value("price_type")); unit = value("unit")
            reason = None
            if not ym or ym > cutoff: reason = "outside_cutoff_or_missing_month"
            elif not value("market_id") or not value("market"): reason = "missing_stable_market_identity"
            elif not value("commodity_id") or not value("commodity"): reason = "missing_stable_commodity_identity"
            elif price_type not in {"retail", "wholesale"}: reason = "transaction_type_not_retail_or_wholesale"
            elif value("currency").upper() != "NGN": reason = "currency_not_ngn"
            elif convert_kg(unit) is None: reason = "unknown_or_count_based_unit"
            elif _label(row.get(fields.get(str(native_columns.get("flag", "flag")).lower(), ""), "")) not in {"", "actual", "observed", "aggregate"}: reason = "unsupported_provenance_flag"
            if reason:
                rejected.append({"source": "wfp-hdx", "source_row": row_number, "month": ym, "reason": reason}); continue
            try: raw_price = float(value("price"))
            except ValueError: rejected.append({"source": "wfp-hdx", "source_row": row_number, "reason": "non_numeric_value"}); continue
            if not (raw_price > 0): rejected.append({"source": "wfp-hdx", "source_row": row_number, "reason": "non_positive_value"}); continue
            kg = convert_kg(unit)
            crop_id = canonical_crop(value("commodity"), mappings)
            if mappings and crop_id not in {item.get("crop_id") for item in mappings.get("crops", [])}:
                rejected.append({"source": "wfp-hdx", "source_row": row_number, "reason": "unmapped_commodity", "commodity": value("commodity"), "commodity_id": value("commodity_id")}); continue
            canonical_market_id = canonical_market("wfp-hdx", value("market_id"), mappings)
            accepted.append({"source": "wfp-hdx", "canonical_crop_id": crop_id, "source_product": value("commodity"), "source_commodity_id": value("commodity_id"), "source_commodity_label": value("commodity"), "market": value("market"), "market_id": value("market_id"), "canonical_market_id": canonical_market_id, "month": ym, "observation_date": (_date(value("date")) or _month_end(ym)).isoformat(), "price_type": price_type, "transaction_type": price_type, "value": raw_price / kg, "source_package_value": raw_price, "source_package_unit": unit, "package_kg": kg, "unit": "NGN/kg", "currency": "NGN", "provenance": _label(row.get(fields.get(str(native_columns.get("flag", "flag")).lower(), ""), "")) or "observed", "rights": "pending_live_license", "source_row": row_number, "source_row_id": row.get(fields.get("id", ""), "")})
    return accepted, rejected


def _component_units(value: object) -> dict[str, str]:
    return {m.group(1).lower(): m.group(2).strip() for m in re.finditer(r"(?:^|,\s*)([a-z0-9_]+)\s*\(([^,]+),\s*Index Weight", str(value or ""), re.I)}


def normalize_world_bank(rows: list[dict], cutoff: str, mappings: dict | None = None) -> tuple[list[dict], list[dict]]:
    accepted, rejected = [], []
    provenance = {"c": "modeled_month_close", "o": "modeled_ohlc_open", "h": "modeled_ohlc_high", "l": "modeled_ohlc_low"}
    for row in rows:
        ym = month(row.get("DATES") or row.get("date") or row.get("period"))
        if not ym or ym > cutoff: continue
        market = _market(row.get("mkt_name") or row.get("market"))
        if not market:
            rejected.append({"source": "world-bank-rtfp", "reason": "missing_market"}); continue
        units = _component_units(row.get("components")); found = False
        for field, value in row.items():
            match = re.fullmatch(r"([cohl])_(.+)", str(field), re.I)
            if not match or value in (None, ""): continue
            try: numeric = float(value)
            except (TypeError, ValueError): continue
            found = True; prefix, product = match.group(1).lower(), match.group(2).lower()
            accepted.append({
                "source": "world-bank-rtfp", "canonical_crop_id": canonical_crop(product.replace("_", " "), mappings), "source_product": product,
                "market": market, "market_kind": "national_aggregate" if row.get("geo_id") == "gid_nga_national_average" else "source_market",
                "geo_id": row.get("geo_id"), "month": ym, "price_type": "unknown", "transaction_type": "unknown",
                "transaction_type_status": "unknown", "value": numeric, "currency": row.get("currency") or "NGN",
                "source_unit": units.get(product, "unknown"), "provenance": provenance[prefix], "field": field,
                "recommendation_eligible": False,
            })
        if not found: rejected.append({"source": "world-bank-rtfp", "month": ym, "market": market, "reason": "no_numeric_ohlc_fields"})
    return accepted, rejected


def summarize_world_bank(rows: list[dict], cutoff: str, mappings: dict) -> dict:
    counts, products, markets = Counter(), Counter(), set(); aggregate_rows = 0; values = 0; latest = None
    prefixes = {"c": "close", "o": "open", "h": "high", "l": "low"}
    through = 0
    for row in rows:
        ym = month(row.get("DATES") or row.get("date"))
        if not ym or ym > cutoff: continue
        through += 1; latest = max(latest or ym, ym)
        if row.get("geo_id") == "gid_nga_national_average": aggregate_rows += 1
        elif _market(row.get("mkt_name") or row.get("market")): markets.add(_market(row.get("mkt_name") or row.get("market")))
        for field, value in row.items():
            match = re.fullmatch(r"([cohl])_(.+)", str(field), re.I)
            if not match or value in (None, ""): continue
            try: float(value)
            except (TypeError, ValueError): continue
            prefix, product = match.group(1).lower(), match.group(2).replace("_", " ")
            counts[prefixes[prefix]] += 1; products[canonical_crop(product, mappings)] += 1; values += 1
    return {"status": "validation_evidence_only", "recommendation_eligible": False, "transaction_type": "unknown", "provenance": ["modeled_month_close", "modeled_ohlc_open", "modeled_ohlc_high", "modeled_ohlc_low"], "rows_through_cutoff": through, "source_market_count": len(markets), "national_aggregate_row_count": aggregate_rows, "latest_month": latest, "normalized_value_count": values, "field_counts": dict(sorted(counts.items())), "crop_value_counts": dict(products.most_common()), "comparability_note": "Modeled values are validation evidence only until transaction type and form comparability are documented."}


def national_median(rows: list[dict], minimum_markets: int = 3) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows: grouped[(row["canonical_crop_id"], row["month"], row["price_type"])].append(row)
    result = []
    for (crop, ym, price_type), values in sorted(grouped.items()):
        usable = [v for v in values if v.get("market_kind") != "national_aggregate" and v.get("geo_id") != "gid_nga_national_average" and v.get("market") != "Market Average"]
        markets = {v["market"] for v in usable}
        if len(markets) < minimum_markets: continue
        ordered = sorted(v["value"] for v in usable); mid = len(ordered) // 2
        result.append({"canonical_crop_id": crop, "month": ym, "price_type": price_type, "market_count": len(markets), "value": ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2, "unit": "NGN/kg"})
    return result


def qualify_series(rows: list[dict], cutoff: str, today: date | None = None) -> tuple[list[dict], list[dict]]:
    snapshot = today or date.today(); groups = defaultdict(list)
    # Keep source IDs distinct when no crosswalk exists, but group reviewed
    # aliases under their canonical market so that identity reaches release.
    for row in rows:
        market_key = row.get("canonical_market_id") or row.get("market_id") or row["market"]
        groups[(row["canonical_crop_id"], market_key, row["price_type"])].append(row)
    expected = {shift_month(cutoff, -i) for i in range(RECENT_WINDOW)}; eligible, rejected = [], []
    for key, values in sorted(groups.items()):
        reasons = []; canonical_keys = [(v["canonical_crop_id"], v.get("source_commodity_id") or v["canonical_crop_id"], v.get("market_id") or v["market"], v["month"], v["price_type"]) for v in values]
        duplicates = len(canonical_keys) - len(set(canonical_keys))
        if duplicates: reasons.append("duplicate_canonical_key")
        months = {v["month"] for v in values}; completeness = len(months & expected) / RECENT_WINDOW
        if len(months) < MIN_HISTORY: reasons.append("history_under_36_months")
        if completeness < .8: reasons.append("latest_36_completeness_under_80_percent")
        dates = [_date(v.get("observation_date")) or _month_end(v["month"]) for v in values]; latest_date = max(dates) if dates else None
        freshness = (snapshot - latest_date).days if latest_date else None
        if freshness is None or freshness > FRESHNESS_DAYS: reasons.append("latest_value_over_75_days_old")
        elif freshness < 0: reasons.append("latest_observation_after_snapshot")
        origins = sum(all(shift_month(origin, h) in months for h in range(3)) for origin in sorted(months) if shift_month(origin, 2) <= cutoff)
        if origins < 6: reasons.append("forecast_origin_windows_under_6")
        record = {"canonical_crop_id": key[0], "market": values[0].get("market", key[1]), "market_id": values[0].get("market_id", key[1]), "canonical_market_id": values[0].get("canonical_market_id"), "price_type": key[2], "months": len(months), "recent_completeness": round(completeness, 6), "latest_month": max(months) if months else None, "latest_observation_date": latest_date.isoformat() if latest_date else None, "snapshot_date": snapshot.isoformat(), "freshness_days": freshness, "freshness_limit_days": FRESHNESS_DAYS, "forecast_origin_windows": origins, "duplicate_count": duplicates, "status": "eligible" if not reasons else "rejected"}
        if reasons: record["rejection_reasons"] = reasons; rejected.append(record)
        else: eligible.append(record)
    return eligible, rejected


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(audit_dir: Path, manifest: dict) -> list[dict]:
    evidence, errors = [], []
    for record in manifest.get("records", []):
        if record.get("status") != "downloaded": evidence.append({"source_id": record.get("source_id"), "status": record.get("status")}); continue
        path = audit_dir / "raw" / str(record.get("path")); actual_bytes = path.stat().st_size if path.is_file() else None; actual_sha = _sha(path) if path.is_file() else None
        size_ok, sha_ok = actual_bytes == record.get("bytes"), actual_sha == record.get("sha256")
        evidence.append({"source_id": record.get("source_id"), "path": f"raw/{record.get('path')}", "expected_bytes": record.get("bytes"), "actual_bytes": actual_bytes, "expected_sha256": record.get("sha256"), "actual_sha256": actual_sha, "size_verified": size_ok, "sha256_verified": sha_ok, "status": "verified" if size_ok and sha_ok else "failed"})
        if not size_ok or not sha_ok: errors.append(str(record.get("source_id")))
    if errors: raise ValueError(f"manifest verification failed for: {', '.join(errors)}")
    return evidence


def _retrieval_date(manifest: dict, source_id: str) -> date:
    record = next((r for r in manifest.get("records", []) if r.get("source_id") == source_id), None)
    if not record or not record.get("retrieved_at"): raise ValueError(f"missing retrieval date for {source_id}")
    return datetime.fromisoformat(str(record["retrieved_at"]).replace("Z", "+00:00")).date()


def _downloaded_record(manifest: dict, source_id: str) -> dict | None:
    """Return an artifact only when the immutable manifest marks it downloaded."""
    return next((r for r in manifest.get("records", [])
                 if r.get("source_id") == source_id and r.get("status") == "downloaded"), None)


def _crop_map(mappings: dict) -> dict[str, dict]: return {c["crop_id"]: c for c in mappings.get("crops", [])}


def extract_faostat_yields(path: Path, crop_ids: list[str], mappings: dict) -> dict:
    crop_map = _crop_map(mappings); aliases = defaultdict(set)
    for crop_id in crop_ids:
        for item in crop_map.get(crop_id, {}).get("faostat_items", []): aliases[_label(item)].add(crop_id)
    records = []
    with zipfile.ZipFile(path) as archive:
        members = [n for n in archive.namelist() if n.endswith("All_Data_(Normalized).csv")]
        if len(members) != 1: raise ValueError("FAOSTAT normalized CSV member missing or ambiguous")
        with archive.open(members[0]) as binary:
            with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
                for row in csv.DictReader(text):
                    if _label(row.get("Area")) != "nigeria" or _label(row.get("Element")) != "yield": continue
                    item_label = _label(row.get("Item"))
                    matched = set(aliases.get(item_label, set()))
                    if not matched:
                        # FAOSTAT occasionally revises display labels (for
                        # example ``Maize (corn)`` versus ``Maize``). Match
                        # only the configured commodity stem, never a crop
                        # form, so this remains conservative.
                        for crop_id in crop_ids:
                            stems = {_label(item).split(",")[0] for item in crop_map.get(crop_id, {}).get("faostat_items", [])}
                            if any(stem and stem in item_label for stem in stems):
                                matched.add(crop_id)
                    unit = str(row.get("Unit") or "").lower()
                    if not matched or unit not in {"kg/ha", "hg/ha", "t/ha"}: continue
                    try: value, year = float(row["Value"]), int(row["Year"])
                    except (KeyError, TypeError, ValueError): continue
                    factor = {"kg/ha": .001, "hg/ha": .0001, "t/ha": 1.0}[unit]
                    records.append({"canonical_crop_form_ids": sorted(matched), "faostat_item": row.get("Item"), "year": year, "value": value, "unit": unit, "yield_t_per_ha": value * factor, "flag": row.get("Flag"), "note": row.get("Note") or None})
    summary = {}
    for crop_id in crop_ids:
        matches = [r for r in records if crop_id in r["canonical_crop_form_ids"]]
        if matches:
            latest = max(matches, key=lambda r: r["year"]); summary[crop_id] = {"record_count": len(matches), "year_min": min(r["year"] for r in matches), "year_max": latest["year"], "latest_faostat_item": latest["faostat_item"], "latest_yield_t_per_ha": latest["yield_t_per_ha"], "latest_flag": latest["flag"]}
    return {"status": "matched" if records else "no_matching_records", "country": "Nigeria", "element": "Yield", "normalized_unit": "t/ha", "license": "CC-BY-4.0", "records": sorted(records, key=lambda r: (r["faostat_item"], r["year"])), "crop_summary": summary}


def _rejection_evidence(rows: list[dict]) -> dict:
    counts = Counter(r["reason"] for r in rows); samples = defaultdict(list)
    for row in rows:
        if len(samples[row["reason"]]) < 5: samples[row["reason"]].append(row)
    return {"total": len(rows), "counts_by_reason": dict(sorted(counts.items())), "samples_by_reason": dict(sorted(samples.items()))}


def _write_profile(audit_dir: Path, manifest: dict, cutoff: str, world_rows: list[dict]) -> dict:
    profiles = []
    for record in manifest.get("records", []):
        if record.get("status") != "downloaded": continue
        path = audit_dir / "raw" / record["path"]
        profile = profile_json_rows(world_rows, cutoff) if record["source_id"] == "world-bank-rtfp" else profile_file(path, cutoff)
        profiles.append({"source_id": record["source_id"], **profile})
    document = {"schema_version": "1.1.0", "cutoff_month": cutoff, "generated_from_manifest_at": manifest.get("generated_at"), "profiles": profiles}
    (audit_dir / "source_profile.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return document


def build_report(audit_dir: Path = DEFAULT_AUDIT, cutoff: str = "2026-07") -> dict:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", cutoff): raise ValueError("cutoff must be YYYY-MM")
    manifest = json.loads((audit_dir / "raw_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("cutoff_month") != cutoff: raise ValueError("cutoff does not match immutable manifest")
    integrity = verify_manifest(audit_dir, manifest)
    mappings = json.loads((ROOT / "config/mappings.json").read_text(encoding="utf-8"))
    fews_record = _downloaded_record(manifest, "fews-net")
    accepted, rejected_rows, eligible, rejected_series = [], [], [], []
    if fews_record:
        fews_path = audit_dir / "raw" / str(fews_record["path"])
        if fews_path.is_file():
            accepted, rejected_rows = normalize_fews(fews_path, cutoff, mappings)
            eligible, rejected_series = qualify_series(accepted, cutoff, _retrieval_date(manifest, "fews-net"))
    wfp_accepted, wfp_rejected_rows, wfp_eligible, wfp_rejected_series = [], [], [], []
    wfp_record = _downloaded_record(manifest, "wfp-hdx")
    if wfp_record:
        wfp_config = next((s for s in json.loads((ROOT / "config/sources.json").read_text(encoding="utf-8")).get("sources", []) if s.get("source_id") == "wfp-hdx"), {})
        native_columns = wfp_config.get("retrieval", {}).get("native_columns", {})
        wfp_accepted, wfp_rejected_rows = normalize_wfp(audit_dir / "raw" / wfp_record["path"], cutoff, mappings, native_columns)
        wfp_snapshot = _retrieval_date(manifest, "wfp-hdx")
        wfp_eligible, wfp_rejected_series = qualify_series(wfp_accepted, cutoff, wfp_snapshot)

    # FEWS is the only primary candidate.  WFP rows are cross-check evidence;
    # they can reject a disagreeing matching series but can never fill missing
    # FEWS history or turn an incomplete FEWS series into an eligible one.
    # Cross-source comparison is only meaningful after both source market IDs
    # resolve to the same reviewed canonical market.  Raw IDs are source
    # scoped, even when their text happens to match.
    fews_keys = {(item["canonical_crop_id"], item["canonical_market_id"], item["price_type"]) for item in eligible if item.get("canonical_market_id")}
    wfp_keys = {(item["canonical_crop_id"], item["canonical_market_id"], item["price_type"]) for item in wfp_eligible if item.get("canonical_market_id")}
    def latest(rows: list[dict], key: tuple[str, str, str]) -> dict | None:
        matches = [row for row in rows if (row["canonical_crop_id"], row.get("canonical_market_id"), row["price_type"]) == key]
        return max(matches, key=lambda row: (row.get("observation_date", ""), row.get("source_row", 0))) if matches else None
    agreements = []
    for key in sorted(fews_keys & wfp_keys):
        primary, cross = latest(accepted, key), latest(wfp_accepted, key)
        if not primary or not cross: continue
        ratio = max(primary["value"], cross["value"]) / min(primary["value"], cross["value"])
        agreements.append({"canonical_crop_id": key[0], "canonical_market_id": key[1], "price_type": key[2], "fews_value_ngn_per_kg": primary["value"], "wfp_value_ngn_per_kg": cross["value"], "ratio": round(ratio, 6), "status": "agree" if ratio <= 1.5 else "disagree"})
    disagreeing = {(item["canonical_crop_id"], item["canonical_market_id"], item["price_type"]) for item in agreements if item["status"] == "disagree"}
    publishable_series = [item for item in eligible if item.get("canonical_market_id") and (item["canonical_crop_id"], item["canonical_market_id"], item["price_type"]) not in disagreeing]
    crop_series = defaultdict(lambda: {"markets": set(), "series": []})
    for series in publishable_series: crop_series[series["canonical_crop_id"]]["markets"].add(series["canonical_market_id"]); crop_series[series["canonical_crop_id"]]["series"].append(series)
    ranked = []
    for crop_id, values in crop_series.items(): ranked.append({"canonical_crop_id": crop_id, "qualified_market_count": len(values["markets"]), "qualified_series_count": len(values["series"]), "recent_completeness": min(s["recent_completeness"] for s in values["series"]), "history_length": min(s["months"] for s in values["series"])})
    ranked.sort(key=lambda r: (-r["qualified_market_count"], -r["recent_completeness"], -r["history_length"], r["canonical_crop_id"]))
    technical = [{**item, "status": "price_technically_qualified"} for item in ranked]
    selected = technical[:8] if len(technical) >= 5 else []
    source_date = _retrieval_date(manifest, "fews-net") if fews_record else date.today()
    report = {
        "schema_version": "1.3.0", "status": "gate_review" if len(selected) >= 5 else "calculator_only_fallback", "stage_1_approved": False, "stage_2_status": "in_progress_calculator_only", "cutoff_month": cutoff, "snapshot_date": source_date.isoformat(), "snapshot_source": "fews-net", "freshness_rule_days": FRESHNESS_DAYS,
        "selected_crops": selected, "ranked_technically_qualified_crops": technical, "minimum_crops_required": 5, "technical_gate_passed": len(selected) >= 5, "price_technical_gate_passed": len(selected) >= 5, "price_rights_gate_passed": False, "price_source_qualified": len(selected) >= 5, "recommendation_defaults_qualified": False, "stage_1_decision": "explicit_review_required" if len(selected) >= 5 else "calculator_only_fallback", "eligible_series": eligible, "publishable_series": publishable_series, "rejected_series": rejected_series,
        "fews_row_quality": {"raw_rows": len(accepted) + len(rejected_rows), "normalized_rows": len(accepted), "qualified_series": len(eligible), "rejections": _rejection_evidence(rejected_rows), "normalization": "original NGN package value divided by explicit source-package kilograms", "transaction_types_retained_separately": ["retail", "wholesale"]},
        "wfp_row_quality": {"raw_rows": len(wfp_accepted) + len(wfp_rejected_rows), "normalized_rows": len(wfp_accepted), "qualified_series": len(wfp_eligible), "rejections": _rejection_evidence(wfp_rejected_rows), "normalization": "explicit source mass divided by explicit source-package kilograms", "transaction_types_retained_separately": ["retail", "wholesale"]},
        "cross_source_check": {"source": "wfp-hdx", "status": "comparable" if agreements else ("not_comparable" if wfp_record else "unavailable"), "agreements": agreements, "disagreement_count": len(disagreeing), "rule": "comparison requires reviewed canonical-market crosswalks and matching qualified FEWS/WFP series; WFP never fills FEWS history"},
        "rights_decisions": {"fews-net": "public rows are technical evidence only; redistribution and Stage 1 review remain required", "wfp-hdx": "independent cross-check only; never a fallback or merged series"},
        "manifest_integrity": {"status": "passed", "records": integrity}, "known_limitations": ["No yield or cost defaults are qualified.", "No browser API calls are allowed.", "Stage 6 human-comprehension pilot remains independent and in progress.", "Stage 1 requires an explicit review artifact before promotion."]
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT); parser.add_argument("--cutoff-month", default="2026-07"); args = parser.parse_args(argv)
    report = build_report(args.audit_dir, args.cutoff_month)
    target = args.audit_dir / "qualification_report.json"
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(json.dumps({"status": report["status"], "selected": len(report["selected_crops"]), "eligible_series": len(report["eligible_series"]), "technical_gate_passed": report["technical_gate_passed"], "stage_2_status": report["stage_2_status"]}, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
