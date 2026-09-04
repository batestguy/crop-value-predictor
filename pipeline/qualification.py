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


def normalize_fews(path: Path, cutoff: str, mappings: dict | None = None) -> tuple[list[dict], list[dict]]:
    accepted, rejected = [], []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), 2):
            ym = month(row.get("period_date"))
            transaction = _label(row.get("price_type"))
            package_kg = convert_kg(row.get("unit", ""), row.get("common_unit", ""))
            raw_value = str(row.get("value") or "").strip().replace(",", "")
            reason = None
            if not ym or ym > cutoff: reason = "outside_cutoff_or_missing_month"
            elif _label(row.get("data_usage_policy")) != "public": reason = "rights_not_public"
            elif transaction not in {"retail", "wholesale"}: reason = "transaction_type_not_retail_or_wholesale"
            elif package_kg is None: reason = "unknown_or_count_based_unit"
            elif str(row.get("currency") or "").upper() != "NGN": reason = "currency_not_ngn"
            elif not _market(row.get("market")): reason = "missing_market"
            elif not _label(row.get("product")): reason = "missing_product"
            elif not raw_value: reason = "missing_value"
            if reason:
                rejected.append({"source": "fews-net", "source_row": row_number, "month": ym, "product": row.get("product"), "market": row.get("market"), "reason": reason})
                continue
            try: package_value = float(raw_value)
            except ValueError:
                rejected.append({"source": "fews-net", "source_row": row_number, "month": ym, "reason": "non_numeric_value"}); continue
            if package_value <= 0:
                rejected.append({"source": "fews-net", "source_row": row_number, "month": ym, "reason": "non_positive_value"}); continue
            observation = _date(row.get("period_date")) or _month_end(ym)
            product = str(row["product"]).strip()
            accepted.append({
                "source": "fews-net", "canonical_crop_id": canonical_crop(product, mappings), "source_product": product,
                "market": _market(row["market"]), "month": ym, "observation_date": observation.isoformat(),
                "price_type": transaction, "transaction_type": transaction, "value": package_value / package_kg,
                "source_package_value": package_value, "source_package_unit": row.get("unit"), "package_kg": package_kg,
                "unit": "NGN/kg", "currency": "NGN", "provenance": "observed", "rights": "public",
                "source_row_id": row.get("id"), "source_row": row_number,
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
            accepted.append({"source": "wfp-hdx", "canonical_crop_id": crop_id, "source_product": value("commodity"), "source_commodity_id": value("commodity_id"), "market": value("market"), "market_id": value("market_id"), "month": ym, "observation_date": (_date(value("date")) or _month_end(ym)).isoformat(), "price_type": price_type, "transaction_type": price_type, "value": raw_price / kg, "source_package_value": raw_price, "source_package_unit": unit, "package_kg": kg, "unit": "NGN/kg", "currency": "NGN", "provenance": _label(row.get(fields.get(str(native_columns.get("flag", "flag")).lower(), ""), "")) or "observed", "rights": "pending_live_license", "source_row": row_number, "source_row_id": row.get(fields.get("id", ""), "")})
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
    for row in rows: groups[(row["canonical_crop_id"], row.get("market_id") or row["market"], row["price_type"])].append(row)
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
        record = {"canonical_crop_id": key[0], "market": values[0].get("market", key[1]), "market_id": values[0].get("market_id", key[1]), "price_type": key[2], "months": len(months), "recent_completeness": round(completeness, 6), "latest_month": max(months) if months else None, "latest_observation_date": latest_date.isoformat() if latest_date else None, "snapshot_date": snapshot.isoformat(), "freshness_days": freshness, "freshness_limit_days": FRESHNESS_DAYS, "forecast_origin_windows": origins, "duplicate_count": duplicates, "status": "eligible" if not reasons else "rejected"}
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
    world_rows = []
    wb_record = _downloaded_record(manifest, "world-bank-rtfp")
    wb_path = audit_dir / "raw" / str(wb_record.get("path")) if wb_record else None
    if wb_path and wb_path.is_file():
        with wb_path.open(encoding="utf-8") as handle: payload = json.load(handle)
        world_rows = payload.get("data") if isinstance(payload, dict) else payload
    profile = _write_profile(audit_dir, manifest, cutoff, world_rows); world_evidence = summarize_world_bank(world_rows, cutoff, mappings) if world_rows else {"status": "optional_artifact_unavailable", "recommendation_eligible": False}
    wb_profile = next((p for p in profile["profiles"] if p["source_id"] == "world-bank-rtfp"), {})
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
    # WFP is the required price source. Optional FEWS data is validation evidence
    # only and can never be used as a fallback when WFP is absent or fails.
    price_accepted, price_eligible, price_rejected = wfp_accepted, wfp_eligible, wfp_rejected_series
    price_snapshot = _retrieval_date(manifest, "wfp-hdx") if wfp_record else date.today()
    eligible_keys = {(r["canonical_crop_id"], r.get("market_id", r["market"]), r["price_type"]) for r in price_eligible}
    qualified_rows = [r for r in price_accepted if (r["canonical_crop_id"], r.get("market_id", r["market"]), r["price_type"]) in eligible_keys]
    medians = national_median(qualified_rows)
    crop_series = defaultdict(lambda: {"markets": set(), "series": []})
    for series in price_eligible: crop_series[series["canonical_crop_id"]]["markets"].add(series.get("market_id", series["market"])); crop_series[series["canonical_crop_id"]]["series"].append(series)
    ranked = []
    for crop_id, values in crop_series.items(): ranked.append({"canonical_crop_id": crop_id, "qualified_market_count": len(values["markets"]), "qualified_series_count": len(values["series"]), "recent_completeness": min(s["recent_completeness"] for s in values["series"]), "history_length": min(s["months"] for s in values["series"]), "cross_source_agreement": 0})
    ranked.sort(key=lambda r: (-r["qualified_market_count"], -r["recent_completeness"], -r["history_length"], -r["cross_source_agreement"], r["canonical_crop_id"]))
    # Yield evidence is extracted independently of the price gate so a
    # calculator-only fallback still documents the available Nigerian defaults.
    faostat_record = _downloaded_record(manifest, "faostat-qcl")
    faostat_path = audit_dir / "raw" / str(faostat_record.get("path")) if faostat_record else None
    faostat = extract_faostat_yields(faostat_path, [c["crop_id"] for c in mappings.get("crops", [])], mappings) if faostat_path and faostat_path.is_file() else {"status": "optional_artifact_unavailable", "crop_summary": {}}
    technical = [{**item, "status": "price_technically_qualified"} for item in ranked]
    selected = technical[:8] if len(technical) >= 5 else []
    defaults = [item for item in technical if item["canonical_crop_id"] in faostat.get("crop_summary", {}) and mappings.get("crops", [])]
    wfp_license = next((r.get("license_id") for r in manifest.get("records", []) if r.get("source_id") == "wfp-hdx"), None)
    wfp_gate_reason = "missing_required_artifact" if not wfp_record else ("rights_not_allowed" if wfp_license != "cc-by-igo" else "technical_qualification_failed")
    report = {
        "schema_version": "1.1.0", "status": "gate_review" if len(selected) >= 5 else "calculator_only_fallback", "stage_1_approved": False, "stage_2_status": "in_progress_calculator_only", "cutoff_month": cutoff, "snapshot_date": price_snapshot.isoformat(), "snapshot_source": "wfp-hdx" if wfp_record else "fews-net", "freshness_rule_days": FRESHNESS_DAYS,
        "selected_crops": selected, "ranked_technically_qualified_crops": technical, "minimum_crops_required": 5, "technical_gate_passed": len(selected) >= 5, "price_technical_gate_passed": len(selected) >= 5, "price_rights_gate_passed": bool(wfp_record and wfp_license == "cc-by-igo"), "price_source_qualified": len(selected) >= 5, "recommendation_defaults_qualified": False, "recommendation_defaults_evidence": defaults, "stage_1_decision": "explicit_review_required" if len(selected) >= 5 else "calculator_only_fallback", "eligible_series": price_eligible, "rejected_series": price_rejected,
        "fews_row_quality": {"raw_rows": len(accepted) + len(rejected_rows), "normalized_rows": len(accepted), "qualified_rows": sum(1 for r in accepted if (r["canonical_crop_id"], r.get("market_id", r["market"]), r["price_type"]) in {(s["canonical_crop_id"], s.get("market_id", s["market"]), s["price_type"]) for s in eligible}), "qualified_series": len(eligible), "rejections": _rejection_evidence(rejected_rows), "normalization": "original NGN package value divided by explicit source-package kilograms", "transaction_types_retained_separately": ["retail", "wholesale"]},
        "wfp_row_quality": {"raw_rows": len(wfp_accepted) + len(wfp_rejected_rows), "normalized_rows": len(wfp_accepted), "qualified_rows": len(qualified_rows), "qualified_series": len(wfp_eligible), "rejections": _rejection_evidence(wfp_rejected_rows), "normalization": "explicit source mass divided to NGN/kg; no inferred units or forms", "transaction_types_retained_separately": ["retail", "wholesale"]},
        "wfp_eligible_series": wfp_eligible, "wfp_rejected_series": wfp_rejected_series, "wfp_gate_decision": {"required": True, "artifact_status": "downloaded" if wfp_record else "missing_or_failed", "rights_license_id": wfp_license, "decision": "pass" if not wfp_gate_reason else "fail", "reason": wfp_gate_reason},
        "national_median_coverage": {"minimum_markets": 3, "qualified_crop_forms": len({r["canonical_crop_id"] for r in medians}), "qualified_crop_month_transaction_groups": len(medians), "records": medians},
        "world_bank_validation_evidence": world_evidence, "world_bank_profile_evidence": {"rows": wb_profile.get("rows"), "rows_through_cutoff": wb_profile.get("rows_through_cutoff"), "rows_after_cutoff": wb_profile.get("rows_after_cutoff"), "locations": wb_profile.get("in_scope_location_count"), "source_markets": wb_profile.get("in_scope_market_count"), "national_aggregate_locations": wb_profile.get("national_aggregate_location_count"), "national_aggregate_rows": wb_profile.get("national_aggregate_row_count"), "national_aggregate_geo_id": wb_profile.get("national_aggregate_geo_id")},
        "faostat": faostat, "nbs_costs": {"status": "deferred", "reason": "table units and redistribution rights are not reproducible", "recommendation_eligible": False},
        "rights_decisions": {"wfp-hdx": "pass only for manifest license cc-by-igo; technical gate still required", "fews-net": "optional public rows only; never a WFP fallback", "world-bank-rtfp": "optional modeled validation evidence only; transaction type unknown", "faostat-qcl": "optional CC-BY-4.0 yield evidence", "nbs-nass-2023": "optional deferred pending reproducible units and rights"},
        "manifest_integrity": {"status": "passed", "records": integrity}, "known_limitations": ["World Bank modeled close/OHLC data do not drive recommendations.", "FEWS redistribution terms still require explicit Stage 1 review.", "NBS costs remain deferred.", "Stage 2 remains in progress as a calculator-only fallback until Stage 1 is explicitly approved."]
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
