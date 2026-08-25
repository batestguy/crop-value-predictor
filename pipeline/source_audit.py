"""Validate and optionally retrieve the Stage 1 source register.

The default mode is network-free and runs in ordinary CI. ``--fetch`` is used
only by the manually dispatched cloud audit workflow. It writes raw files,
checksums, and a machine-readable manifest, but never changes ``public/data``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "config" / "sources.json"
REQUIRED_FIELDS = {
    "source_id", "name", "role", "status", "url", "download_url", "terms_url",
    "auth_mode", "cadence", "formats", "price_types", "units", "coverage",
    "attribution", "redistribution_decision", "required_for_gate", "evidence_urls",
}
VALID_STATUSES = {"candidate", "qualified", "rejected", "deferred"}
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def load_register() -> list[dict]:
    document = json.loads(REGISTER.read_text(encoding="utf-8"))
    assert document.get("schema_version") == "1.1.0", "unsupported source schema"
    sources = document.get("sources")
    assert isinstance(sources, list) and sources, "source register is empty"
    source_ids: set[str] = set()
    for source in sources:
        missing = REQUIRED_FIELDS - source.keys()
        assert not missing, f"missing source fields for {source.get('source_id')}: {sorted(missing)}"
        source_id = source["source_id"]
        assert source_id not in source_ids, f"duplicate source_id: {source_id}"
        source_ids.add(source_id)
        assert source["status"] in VALID_STATUSES, f"unknown source status: {source['status']}"
        assert source["url"].startswith("https://"), f"invalid docs URL: {source_id}"
        assert source["terms_url"].startswith("https://"), f"invalid terms URL: {source_id}"
        assert all(url.startswith("https://") for url in source["evidence_urls"]), source_id
        assert isinstance(source["formats"], list) and source["formats"], source_id
        assert isinstance(source["units"], list) and source["units"], source_id
        if source["download_url"] is not None:
            assert source["download_url"].startswith("https://"), source_id
    return sources


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(source: dict, raw_dir: Path) -> dict:
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    record = {
        "source_id": source["source_id"],
        "url": source["download_url"],
        "retrieved_at": started,
        "status": "skipped",
    }
    if source["download_url"] is None:
        record["reason"] = "no public download URL; manual/API qualification required"
        return record

    suffix = {"json": ".json", "csv": ".csv", "zip_csv": ".zip", "pdf": ".pdf"}
    extension = suffix.get(source["formats"][0], ".bin")
    target = raw_dir / f"{source['source_id']}{extension}"
    request = Request(source["download_url"], headers={"User-Agent": "crop-value-predictor-stage1/1.0"})
    try:
        with urlopen(request, timeout=60) as response, target.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
        record.update({
            "status": "downloaded",
            "path": target.name,
            "bytes": target.stat().st_size,
            "sha256": sha256_file(target),
        })
        if target.suffix.lower() == ".json":
            payload = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("found", payload.get("total", 1)) == 0:
                record.update({"status": "failed", "error": "JSON API returned zero rows"})
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        record.update({"status": "failed", "error": str(error)})
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        record.update({"status": "failed", "error": f"invalid response: {error}"})
    return record


def profile_csv(path: Path) -> dict:
    date_keys = {"date", "period_date", "month", "date_start", "period"}
    row_count = 0
    dates: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        for row in reader:
            row_count += 1
            for key, value in row.items():
                if key.lower() in date_keys and value:
                    dates.append(value[:10])
    return {
        "format": "csv",
        "rows": row_count,
        "columns": fields,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
    }


def profile_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {"format": "json", "rows": None, "columns": [], "note": "no row array"}
    columns = sorted({key for row in rows if isinstance(row, dict) for key in row})
    return {"format": "json", "rows": len(rows), "columns": columns}


def profile_zip(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        members = archive.namelist()
    return {"format": "zip", "rows": None, "members": members[:100], "note": "archive member profiling pending"}


def profile_file(path: Path) -> dict:
    if path.suffix.lower() == ".csv":
        return profile_csv(path)
    if path.suffix.lower() == ".json":
        return profile_json(path)
    if path.suffix.lower() == ".zip":
        return profile_zip(path)
    return {"format": path.suffix.lstrip(".") or "binary", "rows": None, "note": "profile parser pending"}


def run_fetch(output_dir: Path, cutoff_month: str, sources: list[dict]) -> int:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    records = [download(source, raw_dir) for source in sources]
    manifest = {
        "schema_version": "1.0.0",
        "cutoff_month": cutoff_month,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "records": records,
    }
    profiles = []
    for record in records:
        if record["status"] == "downloaded":
            profiles.append({"source_id": record["source_id"], **profile_file(raw_dir / record["path"])})
    (output_dir / "raw_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "source_profile.json").write_text(json.dumps({"profiles": profiles}, indent=2) + "\n", encoding="utf-8")
    (output_dir / "qualification_report.json").write_text(json.dumps({
        "status": "not_run",
        "cutoff_month": cutoff_month,
        "reason": "retrieval and shallow profiling complete; canonical normalization and rights review remain pending",
        "eligible_series": [],
        "rejected_series": [],
    }, indent=2) + "\n", encoding="utf-8")
    required_failures = [
        record["source_id"] for record, source in zip(records, sources)
        if source["required_for_gate"] and record["status"] != "downloaded"
    ]
    if required_failures:
        print(f"required source retrieval failed: {', '.join(required_failures)}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="retrieve configured public sources")
    parser.add_argument("--output-dir", type=Path, default=Path("audit-output"))
    parser.add_argument("--cutoff-month", default=None)
    args = parser.parse_args(argv)
    sources = load_register()
    if not args.fetch:
        print(f"validated source register: {len(sources)} candidates")
        return 0
    if not args.cutoff_month or not MONTH_RE.fullmatch(args.cutoff_month):
        parser.error("--fetch requires --cutoff-month in YYYY-MM form")
    return run_fetch(args.output_dir, args.cutoff_month, sources)


if __name__ == "__main__":
    raise SystemExit(main())
