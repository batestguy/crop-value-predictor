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


def parse_tavily_response(payload: dict[str, Any], crop_id: str, state: str, price_type: str) -> dict[str, Any] | None:
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
    low = _parse_number(range_match.group(1)) / range_divisor if range_match else None
    high = _parse_number(range_match.group(2)) / range_divisor if range_match else None
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
        "warnings": ["No usable local observation was found; this is a web-grounded estimate and requires farmer confirmation."] + (["The provider returned a metric-ton value; it was converted to NGN/kg by dividing by 1,000."] if divisor == 1000.0 else []),
    }


def tavily_fallback(crop_id: str, state: str, price_type: str, tavily_key: str, timeout_seconds: int = 30) -> dict[str, Any] | None:
    search_terms = {"maize-white": "white maize", "rice": "rice", "rice-milled": "milled rice", "yam": "yam", "sorghum": "sorghum", "millet": "millet", "gari-white": "white gari", "cassava": "cassava"}
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
    return parse_tavily_response(document, crop_id, state, price_type)


def read_external_key(path: Path) -> str:
    resolved = path.resolve()
    if ROOT.resolve() in resolved.parents or resolved == ROOT.resolve():
        raise ValueError("credential files must be outside the project workspace")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("credential file is empty")
    return value


def estimate(raw_path: Path, crop_id: str, state: str, price_type: str = "Retail", as_of: date | None = None, max_age_days: int = 365, tavily_key: str | None = None) -> dict[str, Any]:
    local = local_estimate(raw_path, crop_id, state, price_type, as_of, max_age_days)
    if local is not None:
        return local
    if not tavily_key:
        return {"status": "no_estimate", "crop_id": crop_id, "state": state, "price_type": price_type.lower(), "warnings": ["No usable local observation and no web-search credential was supplied."]}
    try:
        result = tavily_fallback(crop_id, state, price_type, tavily_key)
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
    parser.add_argument("--as-of", type=date.fromisoformat)
    args = parser.parse_args()
    key = os.environ.get("TAVILY_API_KEY")
    if key is None and args.api_key_file.exists():
        key = read_external_key(args.api_key_file)
    print(json.dumps(estimate(args.raw, args.crop, args.state, args.price_type, args.as_of, tavily_key=key), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
