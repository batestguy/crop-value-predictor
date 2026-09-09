"""Validate the deployable snapshot contract without network access.

Run with: python pipeline/validate.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data" / "v1"
FILES = ["manifest.json", "catalog.json", "defaults.json", "forecasts.json", "quality.json"]


def load(name: str) -> dict:
    with (DATA / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    documents = {name: load(name) for name in FILES}
    manifest = documents["manifest.json"]
    snapshot = manifest["snapshot_id"]
    assert manifest["schema_version"] in {"1.1.0", "1.2.0", "1.3.0"}
    if not manifest["stage_1_approved"]:
        assert set(FILES[1:]).issubset(manifest["artifacts"])
        assert "price_suggestions.json" not in manifest["artifacts"]
    for name, document in documents.items():
        assert document["snapshot_id"] == snapshot, f"snapshot mismatch: {name}"

    crop_ids = {crop["crop_id"] for crop in documents["catalog.json"]["crops"]}
    assert 5 <= len(crop_ids) <= 8, "pilot must contain 5-8 crops"
    location_ids = {location["location_id"] for location in documents["catalog.json"]["locations"]}
    assert "nigeria-national-median" in location_ids

    forecast_keys = set()
    forecasts = documents["forecasts.json"]["forecasts"]
    assert not forecasts, "calculator-only snapshot cannot contain forecasts"
    assert not documents["defaults.json"]["yield_defaults"]
    assert not documents["defaults.json"]["cost_defaults"]
    assert documents["quality.json"]["pipeline"]["status"] in {"calculator_only", "calculator_only_with_modeled_context"}
    for forecast in forecasts:
        key = (forecast["crop_id"], forecast["location_id"], forecast["horizon_months"])
        assert key not in forecast_keys, f"duplicate forecast: {key}"
        forecast_keys.add(key)
        assert forecast["currency"] == "NGN" and forecast["unit"] == "kg"
        assert forecast["lower_80"] <= forecast["point"] <= forecast["upper_80"]
        assert forecast["crop_id"] in crop_ids

    assert all(not crop["eligible_for_recommendation"] for crop in documents["catalog.json"]["crops"])
    if manifest["stage_1_approved"]:
        assert "price_suggestions.json" in manifest["artifacts"] and "approved_markets.json" in manifest["artifacts"]
        suggestions = load("price_suggestions.json")
        markets = load("approved_markets.json")
        assert suggestions["schema_version"] == "1.1.0" and suggestions["snapshot_id"] == snapshot
        assert markets["schema_version"] == "1.0.0" and markets["snapshot_id"] == snapshot
        approved_markets = {item["market_id"] for item in markets["markets"]}
        suggestion_ids = set()
        for item in suggestions["suggestions"]:
            assert item["suggestion_id"] not in suggestion_ids, "duplicate suggestion ID"
            suggestion_ids.add(item["suggestion_id"])
            assert item["crop_id"] in crop_ids and item["canonical_market_id"] in approved_markets
            assert item["market_id"] == item["canonical_market_id"]
            assert item["crop_form_id"] and item["mapping_version"] == suggestions["mapping_version"]
            assert item["price_type"] in {"retail", "wholesale"} and item["value_ngn_per_kg"] > 0
            assert item["freshness"]["age_days"] <= item["freshness"]["limit_days"]
            assert item["source"]["source_id"] == "fews-net" and item["source"]["raw_artifact_sha256"]
            assert item["source"].get("commodity_label")
    else:
        assert "price_suggestions.json" not in manifest["artifacts"]
    if manifest.get("modeled_estimates_enabled"):
        assert "modeled_price_suggestions.json" in manifest["artifacts"]
        modeled = load("modeled_price_suggestions.json")
        assert modeled["snapshot_id"] == manifest["modeled_estimate_snapshot_id"]
        assert modeled["lane"] == "world-bank-modeled-estimates"
        assert "not observed" in modeled["warning"]
        assert modeled["suggestions"]
        assert all(item["price_type"] == "modeled_estimate" for item in modeled["suggestions"])
    print(f"validated {snapshot}: {len(crop_ids)} crops, calculator-only snapshot")


if __name__ == "__main__":
    main()
