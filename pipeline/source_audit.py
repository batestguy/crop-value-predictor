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
import time
from typing import Callable
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
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
SAFE_URL = re.compile(r"^(https://[^?\s#]+)")


def sanitize_url(url: str) -> str:
    """Keep only the stable origin/path; never persist signed query tokens."""
    match = SAFE_URL.match(str(url or ""))
    if not match:
        raise ValueError("download URL must be an HTTPS URL")
    return match.group(1)


def _request_json(url: str, *, opener=urlopen, retries: int = 3, sleep: Callable[[float], None] = time.sleep) -> dict:
    last_error = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={"User-Agent": "crop-value-predictor-stage1/1.0", "Accept": "application/json"})
            with opener(request, timeout=60) as response:
                status = getattr(response, "status", 200)
                if status == 429 or status >= 500:
                    raise HTTPError(url, status, "transient HTTP response", hdrs=None, fp=None)
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("CKAN response is not an object")
            return payload
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            last_error = error
            status = getattr(error, "code", None)
            transient = isinstance(error, (TimeoutError, URLError, OSError)) or status == 429 or (status is not None and status >= 500)
            if not transient or attempt == retries - 1:
                raise
            sleep(min(2 ** attempt, 4))
    raise RuntimeError(str(last_error))


def discover_wfp_hdx(*, opener=urlopen, package_slug: str = "wfp-food-prices-for-nigeria", retrieval: dict | None = None) -> dict:
    """Discover the unique WFP Nigeria CSV through public CKAN metadata."""
    endpoint = "https://data.humdata.org/api/3/action/package_show?id=" + package_slug
    payload = _request_json(endpoint, opener=opener)
    if not payload.get("success") or not isinstance(payload.get("result"), dict):
        raise ValueError("HDX CKAN package_show failed")
    result = payload["result"]
    organization = result.get("organization") or {}
    title = str(result.get("title") or "")
    if "nigeria" not in (title + " " + str(result.get("name") or "")).lower():
        raise ValueError("HDX package is not Nigeria")
    retrieval = retrieval or {}
    expected_dataset = retrieval.get("dataset_id")
    if expected_dataset and result.get("id") != expected_dataset: raise ValueError("HDX dataset identity drift")
    org = result.get("organization") or {}
    if retrieval.get("organization_id") and org.get("id") != retrieval["organization_id"]: raise ValueError("HDX organization identity drift")
    if retrieval.get("organization_name") and str(org.get("name", "")).lower() != str(retrieval["organization_name"]).lower(): raise ValueError("HDX organization name drift")
    resources = []
    for r in result.get("resources", []):
        if not isinstance(r, dict) or str(r.get("format", "")).lower() != "csv": continue
        if retrieval.get("resource_id") and r.get("id") != retrieval["resource_id"]: continue
        if retrieval.get("resource_name") and r.get("name") != retrieval["resource_name"]: continue
        if retrieval.get("resource_description") and r.get("description") != retrieval["resource_description"]: continue
        resource_filename = r.get("filename") or str(r.get("download_url") or r.get("url") or "").rstrip("/").rsplit("/", 1)[-1]
        if retrieval.get("resource_filename") and resource_filename != retrieval["resource_filename"]: continue
        if retrieval.get("resource_url_type") and r.get("url_type") != retrieval["resource_url_type"]: continue
        if retrieval.get("resource_type") and r.get("resource_type") != retrieval["resource_type"]: continue
        resources.append(r)
    if len(resources) != 1:
        candidates = [{"id": r.get("id"), "name": r.get("name"), "description": r.get("description"), "filename": r.get("filename") or str(r.get("download_url") or r.get("url") or "").rstrip("/").rsplit("/", 1)[-1], "url_type": r.get("url_type"), "resource_type": r.get("resource_type")} for r in result.get("resources", []) if isinstance(r, dict)]
        raise ValueError(f"expected one exact Nigeria WFP CSV resource, found {len(resources)}; candidates={candidates}")
    resource = resources[0]
    url = sanitize_url(resource.get("url") or resource.get("download_url"))
    license_id = str(result.get("license_id") or result.get("license_title") or "").strip()
    if not license_id:
        raise ValueError("HDX dataset has no live license identifier")
    return {"package_slug": package_slug, "dataset_id": result.get("id"), "dataset_name": result.get("name"),
            "title": title, "organization": organization.get("name"), "provider": organization.get("title"),
            "license_id": license_id, "license_url": result.get("license_url"), "dataset_url": "https://data.humdata.org/dataset/" + package_slug,
            "resource_id": resource.get("id"), "resource_name": resource.get("name"), "resource_description": resource.get("description"), "resource_filename": resource.get("filename") or str(resource.get("download_url") or resource.get("url") or "").rstrip("/").rsplit("/", 1)[-1], "url": url,
            "format": "csv", "last_modified": resource.get("last_modified") or result.get("metadata_modified")}


def download_http_csv(discovery: dict, target: Path, *, opener=urlopen, retries: int = 3, sleep: Callable[[float], None] = time.sleep, max_bytes: int = 250_000_000) -> dict:
    """Download a discovered CSV atomically, rejecting HTML/empty/oversize responses."""
    url = sanitize_url(discovery["url"]); last_error = None
    for attempt in range(retries):
        temporary = target.with_name(target.name + ".tmp")
        try:
            request = Request(url, headers={"User-Agent": "crop-value-predictor-stage1/1.0", "Accept": "text/csv"})
            with opener(request, timeout=120) as response:
                status = getattr(response, "status", 200)
                if status == 429 or status >= 500:
                    raise HTTPError(url, status, "transient HTTP response", hdrs=None, fp=None)
                content_type = str(getattr(response, "headers", {}).get("Content-Type", "")).lower()
                total = 0
                with temporary.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk: break
                        total += len(chunk)
                        if total > max_bytes: raise ValueError("CSV response exceeds maximum size")
                        handle.write(chunk)
            if total == 0: raise ValueError("CSV response is empty")
            sample = temporary.read_bytes()[:512].lstrip().lower()
            if "text/html" in content_type or sample.startswith(b"<!doctype html") or sample.startswith(b"<html"):
                raise ValueError("CSV response is HTML")
            temporary.replace(target)
            return {"status": "downloaded", "path": target.name, "bytes": total, "sha256": sha256_file(target), "url": url}
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            last_error = error
            if temporary.exists(): temporary.unlink()
            status = getattr(error, "code", None)
            transient = isinstance(error, (TimeoutError, URLError, OSError)) or status == 429 or (status is not None and status >= 500)
            if not transient or attempt == retries - 1: raise
            sleep(min(2 ** attempt, 4))
    raise RuntimeError(str(last_error))


def load_register() -> list[dict]:
    document = json.loads(REGISTER.read_text(encoding="utf-8"))
    assert document.get("schema_version") == "1.3.0", "unsupported source schema"
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
        if source.get("retrieval", {}).get("mode") == "nada_paginated_json":
            retrieval = source["retrieval"]
            assert retrieval.get("page_size") == 100, source_id
            assert retrieval.get("filter") == {"ISO3": "NGA"}, source_id
        if source.get("retrieval", {}).get("mode") == "fews_v3_paginated_json":
            retrieval = source["retrieval"]
            assert source["download_url"].endswith(".json"), source_id
            assert retrieval.get("country_parameter") == "country", source_id
            assert retrieval.get("country_code") == "NG", source_id
            assert retrieval.get("page_size_parameter") == "page_size", source_id
            assert retrieval.get("offset_parameter") == "offset", source_id
            assert retrieval.get("response_total_field") == "count", source_id
            assert retrieval.get("response_rows_field") == "results", source_id
            assert retrieval.get("row_country_fields") == ["country_code", "country"], source_id
    return sources


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_rows(payload: object) -> list[dict]:
    """Return a NADA page's row array, rejecting malformed responses."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("NADA response does not contain a data row array")
    rows = payload["data"]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("NADA response contains a non-object row")
    return rows


def download_nada_paginated(
    source: dict,
    target: Path,
    *,
    opener: Callable = urlopen,
    sleep: Callable[[float], None] = time.sleep,
    retries: int = 3,
) -> dict:
    """Retrieve a filtered NADA table, validating every page and total.

    NADA's endpoint uses ``/{limit}/{offset}`` pagination.  The server may
    return fewer rows than requested, so offsets advance by the actual page
    length.  The consolidated file is replaced atomically only after all
    rows pass the exact country filter.
    """
    retrieval = source.get("retrieval", {})
    page_size = int(retrieval.get("page_size", 100))
    filters = retrieval.get("filter", {"ISO3": "NGA"})
    if filters != {"ISO3": "NGA"}:
        raise ValueError("NADA adapter requires the exact ISO3=NGA filter")
    base_url = source["download_url"].rstrip("/")
    rows: list[dict] = []
    found_total: int | None = None
    pages = 0
    offset = 0
    while found_total is None or len(rows) < found_total:
        url = f"{base_url}/{page_size}/{offset}?ISO3=NGA"
        payload = None
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                request = Request(url, headers={"User-Agent": "crop-value-predictor-stage1/1.0"})
                with opener(request, timeout=60) as response:
                    status = getattr(response, "status", 200)
                    if status == 429 or status >= 500:
                        raise HTTPError(url, status, "transient HTTP response", hdrs=None, fp=None)
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
                last_error = error
                status = getattr(error, "code", None)
                transient = isinstance(error, (TimeoutError, URLError, OSError)) or status == 429 or (status is not None and status >= 500)
                if not transient or attempt == retries - 1:
                    break
                sleep(min(2 ** attempt, 4))
        if payload is None:
            raise RuntimeError(f"NADA page retrieval failed after {retries} attempts: {last_error}")
        if not isinstance(payload, dict) or not isinstance(payload.get("found"), int):
            raise ValueError("NADA response has no integer found total")
        page_found = payload["found"]
        if page_found <= 0:
            raise ValueError("NADA API returned zero rows")
        if found_total is None:
            found_total = page_found
        elif page_found != found_total:
            raise ValueError("NADA found total changed during pagination")
        page_rows = _json_rows(payload)
        if not page_rows:
            raise ValueError("NADA returned an empty page before found rows were collected")
        for row in page_rows:
            if row.get("ISO3") != "NGA":
                raise ValueError("NADA response contains a row outside ISO3=NGA")
        rows.extend(page_rows)
        pages += 1
        if len(rows) > found_total:
            raise ValueError("NADA returned more rows than its found total")
        offset += len(page_rows)
    if found_total is None or len(rows) != found_total:
        raise ValueError("NADA pagination ended before all found rows were collected")
    payload = {"found": found_total, "data": rows}
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(target)
    return {
        "status": "downloaded",
        "path": target.name,
        "bytes": target.stat().st_size,
        "sha256": sha256_file(target),
        "pages": pages,
        "rows": len(rows),
        "found": found_total,
        "source_total": found_total,
        "filter": filters,
        "requested_page_size": page_size,
    }


def download_fews_paginated(
    source: dict,
    target: Path,
    *,
    opener=urlopen,
    sleep: Callable[[float], None] = time.sleep,
    retries: int = 3,
) -> dict:
    """Download documented FEWS Data Explorer v3 pages, fail-closed.

    The configured contract is deliberately narrow: a ``.json`` endpoint,
    ``country=NG`` plus ``page_size``/``offset`` query parameters, and a
    ``count``/``results`` response.  Alternate envelopes are not silently
    accepted because they could change geography or pagination semantics.
    """
    retrieval = source.get("retrieval", {})
    if retrieval.get("mode") not in {None, "fews_v3_paginated_json"}:
        raise ValueError("FEWS adapter requires the documented v3 retrieval mode")
    if not str(source.get("download_url", "")).endswith(".json"):
        raise ValueError("FEWS adapter requires a .json endpoint")
    if retrieval.get("country_parameter", "country") != "country" or retrieval.get("country_code") != "NG":
        raise ValueError("FEWS adapter requires country=NG")
    if retrieval.get("page_size_parameter", "page_size") != "page_size" or retrieval.get("offset_parameter", "offset") != "offset":
        raise ValueError("FEWS adapter requires page_size and offset pagination")
    if retrieval.get("response_total_field", "count") != "count" or retrieval.get("response_rows_field", "results") != "results":
        raise ValueError("FEWS adapter requires count/results response fields")
    page_size = int(retrieval.get("page_size", 500))
    if page_size < 1 or page_size > 10_000:
        raise ValueError("FEWS page size is outside the safe range")
    offset_key = "offset"
    query_base = {"country": "NG", "page_size": page_size}
    for query_key, retrieval_key in (("start_date", "canary_start_date"), ("end_date", "canary_end_date")):
        if retrieval.get(retrieval_key):
            query_base[query_key] = str(retrieval[retrieval_key])
    rows: list[dict] = []
    total: int | None = None
    offset = 0
    pages = 0
    while total is None or len(rows) < total:
        query = {**query_base, offset_key: offset}
        url = f"{source['download_url']}?{urlencode(query)}"
        payload = None
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                request = Request(url, headers={"User-Agent": "crop-value-predictor-stage1/1.0", "Accept": "application/json"})
                with opener(request, timeout=60) as response:
                    status = getattr(response, "status", 200)
                    if status == 429 or status >= 500:
                        raise HTTPError(url, status, "transient HTTP response", hdrs=None, fp=None)
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
                last_error = error
                status = getattr(error, "code", None)
                transient = isinstance(error, (TimeoutError, URLError, OSError)) or status == 429 or (status is not None and status >= 500)
                if not transient or attempt == retries - 1:
                    break
                sleep(min(2 ** attempt, 4))
        if not isinstance(payload, dict):
            raise RuntimeError(f"FEWS page retrieval failed after {retries} attempts: {last_error}")
        reported_total = payload.get("count")
        page_rows = payload.get("results")
        if not isinstance(page_rows, list) or not all(isinstance(row, dict) for row in page_rows):
            raise ValueError("FEWS response does not contain an object row array")
        if reported_total is None or reported_total < 1:
            raise ValueError("FEWS response has no positive integer total")
        if total is None:
            total = reported_total
        elif total != reported_total:
            raise ValueError("FEWS total changed during pagination")
        if not page_rows:
            raise ValueError("FEWS returned an empty page before all rows were collected")
        country_fields = retrieval.get("row_country_fields", ["country_code", "country"])
        if not isinstance(country_fields, list) or country_fields != ["country_code", "country"]:
            raise ValueError("FEWS row geography fields are not configured exactly")
        if any(not any(str(row.get(field, "")).upper() in {"NG", "NGA", "NIGERIA"} for field in country_fields) for row in page_rows):
            raise ValueError("FEWS response contains a row outside Nigeria")
        rows.extend(page_rows)
        pages += 1
        if len(rows) > total:
            raise ValueError("FEWS returned more rows than its reported total")
        offset += len(page_rows)
    if total is None or len(rows) != total:
        raise ValueError("FEWS pagination ended before all rows were collected")
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps({"count": total, "results": rows}, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(target)
    return {"status": "downloaded", "path": target.name, "bytes": target.stat().st_size, "sha256": sha256_file(target), "pages": pages, "rows": len(rows), "source_total": total, "filter": {"country": "NG"}, "requested_page_size": page_size}


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
    if source.get("retrieval", {}).get("mode") == "nada_paginated_json":
        try:
            record.update(download_nada_paginated(source, target))
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as error:
            record.update({"status": "failed", "error": str(error)})
        return record

    if source.get("retrieval", {}).get("mode") == "fews_v3_paginated_json":
        target = raw_dir / f"{source['source_id']}.json"
        try:
            record.update(download_fews_paginated(source, target))
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as error:
            record.update({"status": "failed", "error": str(error)})
        return record

    if source.get("retrieval", {}).get("mode") == "hdx_ckan_wfp_csv":
        try:
            discovery = discover_wfp_hdx(package_slug=source["retrieval"]["package_slug"], retrieval=source["retrieval"])
            expected = str(source["retrieval"].get("expected_provider", "")).lower()
            observed = (str(discovery.get("organization", "")) + " " + str(discovery.get("provider", ""))).lower()
            if expected and expected not in observed:
                raise ValueError("HDX publisher/provider is not the expected WFP")
            allowed = {str(value).lower() for value in source["retrieval"].get("allowed_license_ids", [])}
            if str(discovery.get("license_id", "")).lower() not in allowed:
                raise ValueError("HDX license is not in the configured allowed license set")
            target = raw_dir / f"{source['source_id']}.csv"
            record.update(download_http_csv(discovery, target))
            record.update({"dataset_id": discovery.get("dataset_id"), "resource_id": discovery.get("resource_id"), "resource_name": discovery.get("resource_name"), "resource_description": discovery.get("resource_description"), "resource_filename": discovery.get("resource_filename") or source["retrieval"].get("resource_filename"), "license_id": discovery.get("license_id"), "last_modified": discovery.get("last_modified"), "dataset_url": discovery.get("dataset_url"), "url": discovery.get("url")})
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as error:
            record.update({"status": "failed", "error": str(error)})
        return record
    request = Request(source["download_url"], headers={"User-Agent": "crop-value-predictor-stage1/1.0"})
    temporary = target.with_name(target.name + ".tmp")
    try:
        with urlopen(request, timeout=60) as response, temporary.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
        if not temporary.stat().st_size: raise ValueError("empty response")
        sample = temporary.read_bytes()[:512].lstrip().lower()
        if sample.startswith(b"<!doctype html") or sample.startswith(b"<html"):
            raise ValueError("response is HTML")
        if target.suffix.lower() == ".zip":
            with zipfile.ZipFile(temporary): pass
        temporary.replace(target)
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
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, zipfile.BadZipFile) as error:
        record.update({"status": "failed", "error": str(error)})
        if temporary.exists(): temporary.unlink()
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


def _date_value(row: dict) -> str | None:
    for key, value in row.items():
        if key.upper() in {"DATES", "DATE", "PERIOD_DATE", "MONTH", "DATE_START", "PERIOD"} and value:
            return str(value)[:10]
    return None


def _market_value(row: dict) -> str | None:
    for key, value in row.items():
        if key.lower() in {"market", "market_id", "market_name", "marketcode", "mkt_name"} and value:
            return str(value)
    return None


def profile_json_rows(rows: object, cutoff_month: str | None = None) -> dict:
    """Profile an already-decoded JSON row array.

    Location counts use ``geo_id`` where it is available.  This prevents a
    display-name collision from changing the market count and makes the World
    Bank national aggregate an explicit, separate location.
    """
    if not isinstance(rows, list):
        return {"format": "json", "rows": None, "columns": [], "note": "no row array"}
    columns = sorted({key for row in rows if isinstance(row, dict) for key in row})
    dates = [date for row in rows if isinstance(row, dict) for date in [_date_value(row)] if date]
    profile = {
        "format": "json", "rows": len(rows), "columns": columns,
        "date_min": min(dates) if dates else None, "date_max": max(dates) if dates else None,
    }
    if cutoff_month:
        eligible = [row for row in rows if isinstance(row, dict) and (_date_value(row) or "")[:7] <= cutoff_month]
        after = [row for row in rows if isinstance(row, dict) and (_date_value(row) or "")[:7] > cutoff_month]
        location_keys = {
            str(row.get("geo_id") or _market_value(row))
            for row in eligible if row.get("geo_id") or _market_value(row)
        }
        aggregate_geo_id = "gid_nga_national_average"
        aggregate_rows = [row for row in eligible if row.get("geo_id") == aggregate_geo_id]
        aggregate_locations = {
            str(row.get("geo_id") or _market_value(row))
            for row in aggregate_rows if row.get("geo_id") or _market_value(row)
        }
        source_markets = location_keys - aggregate_locations
        profile.update({
            "cutoff_month": cutoff_month,
            "rows_through_cutoff": len(eligible),
            "rows_after_cutoff": len(after),
            "in_scope_location_count": len(location_keys),
            "in_scope_market_count": len(source_markets),
            "national_aggregate_count": len(aggregate_rows),
            "national_aggregate_row_count": len(aggregate_rows),
            "national_aggregate_location_count": len(aggregate_locations),
            "national_aggregate_geo_id": aggregate_geo_id,
        })
    return profile


def profile_json(path: Path, cutoff_month: str | None = None) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("data") if isinstance(payload, dict) else payload
    return profile_json_rows(rows, cutoff_month)


def profile_zip(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        members = archive.namelist()
    return {"format": "zip", "rows": None, "members": members[:100], "note": "archive member profiling pending"}


def profile_file(path: Path, cutoff_month: str | None = None) -> dict:
    if path.suffix.lower() == ".csv":
        return profile_csv(path)
    if path.suffix.lower() == ".json":
        return profile_json(path, cutoff_month)
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
            profiles.append({"source_id": record["source_id"], **profile_file(raw_dir / record["path"], cutoff_month)})
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
    parser.add_argument("--source-id", action="append", default=[], help="source ID to retrieve; repeat to limit a reviewed run")
    parser.add_argument("--fews-canary", action="store_true", help="fetch one bounded FEWS v3 canary page (requires --fetch)")
    parser.add_argument("--canary-start", help="optional FEWS v3 start_date YYYY-MM-DD")
    parser.add_argument("--canary-end", help="optional FEWS v3 end_date YYYY-MM-DD")
    parser.add_argument("--canary-page-size", type=int, default=25, help="bounded FEWS canary page size (1-100)")
    args = parser.parse_args(argv)
    sources = load_register()
    if args.fews_canary and not args.fetch:
        parser.error("--fews-canary requires --fetch")
    if not args.fetch:
        print(f"validated source register: {len(sources)} candidates")
        return 0
    if args.fews_canary:
        if not 1 <= args.canary_page_size <= 100:
            parser.error("--canary-page-size must be between 1 and 100")
        for name, value in (("--canary-start", args.canary_start), ("--canary-end", args.canary_end)):
            if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                parser.error(f"{name} must be YYYY-MM-DD")
        sources = [source for source in sources if source["source_id"] == "fews-net"]
        source = dict(sources[0]); source["retrieval"] = dict(source["retrieval"])
        source["retrieval"]["page_size"] = args.canary_page_size
        # Date filters are part of the canary request contract only; normal
        # audited retrieval remains governed by its immutable source register.
        if args.canary_start: source["retrieval"]["canary_start_date"] = args.canary_start
        if args.canary_end: source["retrieval"]["canary_end_date"] = args.canary_end
        sources = [source]
    if not args.cutoff_month or not MONTH_RE.fullmatch(args.cutoff_month):
        parser.error("--fetch requires --cutoff-month in YYYY-MM form")
    if args.source_id:
        requested = set(args.source_id)
        configured = {source["source_id"] for source in sources}
        unknown = sorted(requested - configured)
        if unknown: parser.error(f"unknown --source-id: {', '.join(unknown)}")
        sources = [source for source in sources if source["source_id"] in requested]
    return run_fetch(args.output_dir, args.cutoff_month, sources)


if __name__ == "__main__":
    raise SystemExit(main())
