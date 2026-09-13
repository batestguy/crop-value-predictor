"""Local-first internet aggregate estimate helper.

This module is deliberately separate from the offline browser release. It reads
the retained raw WFP/HDX CSV for a local estimate and uses Tavily's grounded
answer only when the requested state/crop/basis has no usable local evidence.
API keys are read only from an external file or process environment and are
never included in returned payloads.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "audit-output-remediation-2026-09-10" / "raw" / "wfp-hdx.csv"
DEFAULT_KEY = Path(os.environ.get("USERPROFILE", "")) / ".config" / "crop-value-predictor" / "tavily-key.txt"
TAVILY_URL = "https://api.tavily.com/search"

# Only mappings already represented by the calculator's source contract are
# allowed. Fresh cassava is intentionally absent: gari is not fresh cassava.
CROP_COMMODITIES = {
    "maize-white": {"Maize (white)"},
    "rice": {"Rice (local)", "Rice (imported)"},
    "rice-milled": {"Rice (milled, local)"},
    "yam": {"Yam"},
    "sorghum": {"Sorghum", "Sorghum (white)"},
    "millet": {"Millet"},
    "gari-white": {"Gari (white)"},
}

COST_SEARCH_TERMS = {
    "land_preparation": "land preparation",
    "seed": "seed",
    "fertilizer": "fertilizer",
    "pesticide": "pesticide",
    "labour": "labour labor",
    "irrigation": "irrigation",
    "transport": "transport",
    "storage": "storage",
}


def parse_mass_unit(unit: str) -> float | None:
    """Return package mass in kg, or None for units needing crop rules."""
    normalized = unit.strip().upper()
    if normalized == "KG":
        return 1.0
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*KG", normalized)
    if match:
        return float(match.group(1))
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*G", normalized)
    if match:
        return float(match.group(1)) / 1000.0
    return None


def weighted_median(values: list[float], weights: list[float]) -> float:
    if not values or len(values) != len(weights):
        raise ValueError("weighted median requires matching non-empty values and weights")
    ordered = sorted(zip(values, weights), key=lambda item: item[0])
    target = sum(weights) / 2.0
    running = 0.0
    for value, weight in ordered:
        running += weight
        if running >= target:
            return value
    return ordered[-1][0]


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _local_candidates(rows: Iterable[dict[str, str]], crop_id: str, state: str, price_type: str, as_of: date, max_age_days: int) -> list[dict[str, Any]]:
    commodities = CROP_COMMODITIES.get(crop_id, set())
    if not commodities:
        return []
    cutoff = as_of - timedelta(days=max_age_days)
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if row.get("admin1", "").casefold() != state.casefold():
            continue
        if row.get("pricetype", "").casefold() != price_type.casefold():
            continue
        if row.get("commodity", "") not in commodities:
            continue
        try:
            observed = _parse_date(row["date"])
            price = float(row["price"])
            package_kg = parse_mass_unit(row["unit"])
        except (KeyError, ValueError):
            continue
        if observed > as_of or observed < cutoff or package_kg is None or not math.isfinite(price) or price <= 0:
            continue
        candidates.append({
            "value_ngn_per_kg": price / package_kg,
            "date": observed,
            "market_id": row["market_id"],
            "market": row["market"],
            "commodity": row["commodity"],
            "unit": row["unit"],
            "priceflag": row["priceflag"],
        })
    return candidates


def local_estimate(raw_path: Path, crop_id: str, state: str, price_type: str = "Retail", as_of: date | None = None, max_age_days: int = 365) -> dict[str, Any] | None:
    """Return a state estimate balanced across markets, or None."""
    as_of = as_of or date.today()
    rows = _local_candidates(_read_rows(raw_path), crop_id, state, price_type, as_of, max_age_days)
    if not rows:
        return None
    by_market: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_market[row["market_id"]].append(row)
    market_values: list[float] = []
    market_weights: list[float] = []
    market_dates: list[date] = []
    for market_rows in by_market.values():
        values = sorted(row["value_ngn_per_kg"] for row in market_rows)
        midpoint = len(values) // 2
        market_value = values[midpoint] if len(values) % 2 else (values[midpoint - 1] + values[midpoint]) / 2
        latest = max(row["date"] for row in market_rows)
        age = max(0, (as_of - latest).days)
        market_values.append(market_value)
        market_weights.append(math.exp(-age / 180.0))
        market_dates.append(latest)
    ordered = sorted(market_values)
    q1 = ordered[max(0, math.floor((len(ordered) - 1) * 0.25))]
    q3 = ordered[min(len(ordered) - 1, math.ceil((len(ordered) - 1) * 0.75))]
    return {
        "status": "local",
        "estimate_ngn_per_kg": round(weighted_median(market_values, market_weights), 2),
        "low_ngn_per_kg": round(q1, 2),
        "high_ngn_per_kg": round(q3, 2),
        "price_type": price_type.lower(),
        "crop_id": crop_id,
        "state": state,
        "observation_count": len(rows),
        "market_count": len(by_market),
        "date_from": min(row["date"] for row in rows).isoformat(),
        "date_to": max(market_dates).isoformat(),
        "source": {"source_id": "wfp-hdx-raw", "publisher": "World Food Programme via HDX", "artifact": str(raw_path)},
        "warnings": ["This is a dated snapshot; it is not a live market quote."],
    }


def _parse_number(value: str) -> float | None:
    cleaned = value.replace(",", "").strip()
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number if math.isfinite(number) and number > 0 else None


def _marked_number(answer: str, marker: str, allow_zero: bool = False) -> float | None:
    match = re.search(rf"{re.escape(marker)}\s*[:=]\s*(?:NGN|Naira|N)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)", answer, re.IGNORECASE)
    if not match:
        return None
    value = _parse_number(match.group(1))
    if value is None or (not allow_zero and value <= 0):
        return None
    return value


def _custom_input_estimates(answer: str) -> tuple[float | None, dict[str, float]]:
    yield_value = _marked_number(answer, "YIELD_T_PER_HA")
    if yield_value is None:
        match = re.search(r"(?:yield|production|harvest)[^0-9]{0,100}([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:t/ha|tonnes?\s+per\s+hectare|tons?\s+per\s+hectare)", answer, re.IGNORECASE)
        yield_value = _parse_number(match.group(1)) if match else None
    costs: dict[str, float] = {}
    for category, terms in COST_SEARCH_TERMS.items():
        marked = _marked_number(answer, f"COST_{category.upper()}_NGN_PER_HA", allow_zero=True)
        if marked is not None:
            costs[category] = marked
            continue
        alternatives = "|".join(re.escape(term) for term in terms.split()) if category == "labour" else re.escape(terms)
        patterns = (
            rf"(?:{alternatives})[^0-9]{{0,80}}(?:NGN|Naira|N)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:per|/)\s*(?:ha|hectare)",
            rf"(?:NGN|Naira|N)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:for|of|on)\s+(?:the\s+)?(?:{alternatives})s?",
            rf"(?:{alternatives})s?[^0-9]{{0,80}}(?:NGN|Naira|N)\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
        )
        match = next((re.search(pattern, answer, re.IGNORECASE) for pattern in patterns if re.search(pattern, answer, re.IGNORECASE)), None)
        value = _parse_number(match.group(1)) if match else None
        if value is not None:
            costs[category] = value
    return yield_value, costs


def parse_tavily_response(payload: dict[str, Any], crop_id: str, state: str, price_type: str, custom_crop: bool = False) -> dict[str, Any] | None:
    answer = payload.get("answer")
    if not isinstance(answer, str):
        return None
    match = re.search(r"ESTIMATE_NGN_PER_KG\s*[:=]\s*[₦N]?\s*([0-9][0-9,]*(?:\.[0-9]+)?)", answer, re.IGNORECASE)
    divisor = 1.0
    if not match:
        match = re.search(r"(?:price|retail(?:s| price)?|estimate|average|cost|around)[^₦N0-9]{0,100}(?:₦|NGN|Naira)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:per|/)\s*(?P<unit>kg|kilogram|metric\s+ton|tonne|ton)", answer, re.IGNORECASE)
        if match and match.group("unit").casefold() not in {"kg", "kilogram"}:
            divisor = 1000.0
    if not match:
        return None
    estimate = _parse_number(match.group(1))
    if estimate is None:
        return None
    sources = []
    for result in payload.get("results", []):
        if isinstance(result, dict) and isinstance(result.get("url"), str):
            sources.append({"title": result.get("title", ""), "url": result["url"]})
    range_match = re.search(r"range\s+from\s+(?:₦|NGN|Naira)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s+to\s+(?:₦|NGN|Naira)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:per|/)\s*(?P<range_unit>kg|kilogram|metric\s+ton|tonne|ton)", answer, re.IGNORECASE)
    range_divisor = 1000.0 if range_match and range_match.group("range_unit").casefold() not in {"kg", "kilogram"} else 1.0
    explicit_low = _marked_number(answer, "LOW_NGN_PER_KG")
    explicit_high = _marked_number(answer, "HIGH_NGN_PER_KG")
    low = explicit_low if explicit_low is not None else (_parse_number(range_match.group(1)) / range_divisor if range_match else None)
    high = explicit_high if explicit_high is not None else (_parse_number(range_match.group(2)) / range_divisor if range_match else None)
    yield_value, costs = _custom_input_estimates(answer) if custom_crop else (None, {})
    return {
        "status": "web_fallback",
        "estimate_ngn_per_kg": round(estimate / divisor, 2),
        "low_ngn_per_kg": round(low, 2) if low is not None else None,
        "high_ngn_per_kg": round(high, 2) if high is not None else None,
        "price_type": price_type.lower(),
        "crop_id": crop_id,
        "state": state,
        "confidence": "low",
        "source_count": len(sources),
        "sources": sources[:8],
        "answer": answer,
        **({"yield_t_per_ha": round(yield_value, 2)} if yield_value is not None else {}),
        **({"costs_per_ha": {key: round(value, 2) for key, value in costs.items()}} if costs else {}),
        "warnings": ["No usable local observation was found; this is a web-grounded estimate and requires farmer confirmation."] + (["The provider returned a metric-ton value; it was converted to NGN/kg by dividing by 1,000."] if divisor == 1000.0 else []),
    }


def tavily_fallback(crop_id: str, state: str, price_type: str, tavily_key: str, timeout_seconds: int = 30, crop_name: str | None = None, crop_form: str | None = None) -> dict[str, Any] | None:
    search_terms = {"maize-white": "white maize", "rice": "rice", "rice-milled": "milled rice", "yam": "yam", "sorghum": "sorghum", "millet": "millet", "gari-white": "white gari", "cassava": "cassava"}
    if crop_name and crop_form:
        cost_markers = ", ".join(f"COST_{category.upper()}_NGN_PER_HA" for category in COST_SEARCH_TERMS)
        query = (
            f"{state} Nigeria {crop_name} {crop_form} average farm yield tonnes per hectare "
            f"{price_type.lower()} market price NGN per kilogram production cost per hectare 2026. "
            "Use multiple recent sources and give a practical average, not a single quote. "
            "Return clearly labelled values: ESTIMATE_NGN_PER_KG, LOW_NGN_PER_KG, HIGH_NGN_PER_KG, "
            f"YIELD_T_PER_HA, and any available {cost_markers}. Use NGN/kg and NGN/ha; omit values you cannot support."
        )
    else:
        query = f"{state} {search_terms.get(crop_id, crop_id)} market price Nigeria 2026 {price_type.lower()} per kilogram"
    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": 8,
        "include_answer": True,
        "include_raw_content": False,
    }
    request = urllib.request.Request(TAVILY_URL, data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {tavily_key}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        document = json.loads(response.read().decode("utf-8"))
    return parse_tavily_response(document, crop_id, state, price_type, custom_crop=bool(crop_name and crop_form))


def read_external_key(path: Path) -> str:
    resolved = path.resolve()
    if ROOT.resolve() in resolved.parents or resolved == ROOT.resolve():
        raise ValueError("credential files must be outside the project workspace")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("credential file is empty")
    return value


def estimate(raw_path: Path, crop_id: str, state: str, price_type: str = "Retail", as_of: date | None = None, max_age_days: int = 365, tavily_key: str | None = None, crop_name: str | None = None, crop_form: str | None = None) -> dict[str, Any]:
    local = local_estimate(raw_path, crop_id, state, price_type, as_of, max_age_days)
    if local is not None:
        return local
    if not tavily_key:
        return {"status": "no_estimate", "crop_id": crop_id, "state": state, "price_type": price_type.lower(), "warnings": ["No usable local observation and no web-search credential was supplied."]}
    try:
        result = tavily_fallback(crop_id, state, price_type, tavily_key, crop_name=crop_name, crop_form=crop_form)
    except Exception:
        result = None
    return result or {"status": "no_estimate", "crop_id": crop_id, "state": state, "price_type": price_type.lower(), "warnings": ["Web search returned no parseable price evidence within the bounded request."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crop", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--price-type", choices=["Retail", "Wholesale"], default="Retail")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--api-key-file", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--crop-name")
    parser.add_argument("--crop-form")
    parser.add_argument("--as-of", type=date.fromisoformat)
    args = parser.parse_args()
    key = os.environ.get("TAVILY_API_KEY")
    if key is None and args.api_key_file.exists():
        key = read_external_key(args.api_key_file)
    print(json.dumps(estimate(args.raw, args.crop, args.state, args.price_type, args.as_of, tavily_key=key, crop_name=args.crop_name, crop_form=args.crop_form), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
