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
    assert manifest["schema_version"] == "1.0.0"
    assert set(manifest["artifacts"]) == set(FILES[1:])
    for name, document in documents.items():
        assert document["snapshot_id"] == snapshot, f"snapshot mismatch: {name}"

    crop_ids = {crop["crop_id"] for crop in documents["catalog.json"]["crops"]}
    assert 5 <= len(crop_ids) <= 8, "pilot must contain 5-8 crops"
    location_ids = {location["location_id"] for location in documents["catalog.json"]["locations"]}
    assert "nigeria-national-median" in location_ids

    forecast_keys = set()
    for forecast in documents["forecasts.json"]["forecasts"]:
        key = (forecast["crop_id"], forecast["location_id"], forecast["horizon_months"])
        assert key not in forecast_keys, f"duplicate forecast: {key}"
        forecast_keys.add(key)
        assert forecast["currency"] == "NGN" and forecast["unit"] == "kg"
        assert forecast["lower_80"] <= forecast["point"] <= forecast["upper_80"]
        assert forecast["crop_id"] in crop_ids

    assert len(documents["defaults.json"]["yield_defaults"]) >= len(crop_ids)
    assert len(documents["defaults.json"]["cost_defaults"]) >= len(crop_ids)
    print(f"validated {snapshot}: {len(crop_ids)} crops, {len(forecast_keys)} forecast records")


if __name__ == "__main__":
    main()
