"""
Build the per-crop photographs used by the app.

Source images are Wikimedia Commons files whose licence, author and description are
read from the MediaWiki API and written next to the output, so attribution travels
with the files rather than living only in this script.

Why these particular files: each must (a) actually show the named crop, (b) be
photographed in Nigeria, and (c) be dignified enough to sit in a product we are
pitching to employers. Several otherwise-suitable Commons images were rejected on
(c) because they showed identifiable children who were partly unclothed.

Usage:
    python scripts/build-crop-photos.py            # verify + build
    python scripts/build-crop-photos.py --check    # verify only, no writes

Output:
    public/crops/<crop>-<width>.webp   responsive widths
    public/crops/credits.json          attribution, licence, source page
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "crops"
UA = "SeasonMarginCropPhotos/1.0 (contact: batesthommie@gmail.com)"

# crop id -> (Commons file title, caption shown under the photo)
CROPS: dict[str, tuple[str, str]] = {
    "maize-white": ("File:Alapere Community Lagos Nigeria- (15).jpg", "Boiled maize for sale in Lagos"),
    "rice": ("File:@SASUPHOTOGRAPGHY 173 11.jpg", "Rice sellers at a Nigerian market"),
    "rice-milled": ("File:@SASUPHOTOGRAPGHY 173 13.jpg", "Milled rice on display"),
    "yam": ("File:DISPLAY OF YAMS IN MARKET.jpg", "Yams at a Nigerian market"),
    "sorghum": ("File:Way of Drying Freshly Harvested Sorghum in Atyap Land.jpg", "Sorghum drying after harvest, Atyap"),
    "millet": ("File:Millet in an iron bowl.jpg", "Millet grain in a bowl"),
    "gari-white": ("File:@SASUPHOTOGRAPGHY 146.jpg", "Sieving garri from cassava"),
    "cassava": ("File:A cassava, corn and palm plantation.jpg", "A cassava, maize and palm plantation"),
}

# 160w feeds the 44 px list thumbnail at 3.6x. The banner renders at up to 520 px, so
# 640 covers 1x and 1024 covers 2x; 1280 cost ~25% more bytes for no visible gain.
WIDTHS = (160, 640, 1024)
QUALITY = 74
# One aspect ratio for every crop, so the banner never jumps height between crops
# and a portrait original cannot blow up the file size.
ASPECT = 16 / 10

FILE_RE = "https://commons.wikimedia.org/w/api.php"
ALLOWED_LICENCES = ("cc by-sa 4.0", "cc by 4.0", "cc0", "public domain")


def api(params: dict) -> dict:
    url = FILE_RE + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def file_meta(title: str) -> dict:
    data = api({
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
    })
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    if "imageinfo" not in page:
        raise SystemExit(f"no imageinfo for {title!r} (missing file?)")
    info = page["imageinfo"][0]
    meta = info.get("extmetadata", {})

    def field(name: str) -> str:
        return (meta.get(name) or {}).get("value", "")

    return {
        "title": title,
        "url": info["url"],
        "width": info["width"],
        "height": info["height"],
        "licence": field("LicenseShortName").strip(),
        "licence_url": field("LicenseUrl"),
        "artist": field("Artist"),
        "credit": field("Credit"),
        "page": info.get("descriptionurl"),
    }


def strip_html(value: str) -> str:
    """Commons artist fields often contain anchors; keep the readable text."""
    out, depth = [], 0
    for ch in value:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return " ".join("".join(out).split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify licences only")
    parser.add_argument("--force", action="store_true", help="rebuild existing files")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    credits = {}
    problems = []

    for crop_id, (title, caption) in CROPS.items():
        try:
            meta = file_meta(title)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{crop_id}: metadata failed ({exc})")
            continue

        licence = meta["licence"].lower()
        if not any(allowed in licence for allowed in ALLOWED_LICENCES):
            problems.append(f"{crop_id}: licence {meta['licence']!r} is not on the allow list")
            continue
        if meta["width"] < 1200:
            problems.append(f"{crop_id}: only {meta['width']}px wide, too small for a 2x banner")

        credits[crop_id] = {
            "caption": caption,
            "file": meta["title"],
            "artist": strip_html(meta["artist"]) or "Unknown",
            "licence": meta["licence"],
            "licence_url": meta["licence_url"],
            "source": meta["page"],
            "original_width": meta["width"],
        }
        print(f"{crop_id:12} {meta['licence']:14} {meta['width']}x{meta['height']}  {strip_html(meta['artist'])[:40]}")

        if args.check:
            continue

        existing = [OUT / f"{crop_id}-{w}.webp" for w in WIDTHS]
        if all(p.exists() for p in existing) and not args.force:
            print(f"             up to date ({len(existing)} sizes)")
            continue

        req = urllib.request.Request(meta["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=180) as response:
            blob = response.read()
        source = Image.open(io.BytesIO(blob))
        source = source.convert("RGB")

        # Centre-crop to the shared aspect ratio before resizing.
        if source.width / source.height > ASPECT:
            new_w = round(source.height * ASPECT)
            left = (source.width - new_w) // 2
            source = source.crop((left, 0, left + new_w, source.height))
        else:
            new_h = round(source.width / ASPECT)
            top = (source.height - new_h) // 2
            source = source.crop((0, top, source.width, top + new_h))

        for width in WIDTHS:
            if width > source.width:
                width_used = source.width
            else:
                width_used = width
            height = round(source.height * width_used / source.width)
            resized = source.resize((width_used, height), Image.LANCZOS)
            target = OUT / f"{crop_id}-{width}.webp"
            resized.save(target, "WEBP", quality=QUALITY, method=6)
            print(f"             {target.name:26} {target.stat().st_size:>8,} B  {width_used}x{height}")

    payload = json.dumps(credits, indent=2, ensure_ascii=False) + "\n"

    # Published copy: lets anyone verify the licence and source of every photograph.
    (OUT / "credits.json").write_text(payload, encoding="utf-8")
    # Imported copy. Vite does not support importing from public/, and drops such
    # imports silently, so the app reads this one from src/ instead.
    (ROOT / "src" / "cropPhotoCredits.json").write_text(payload, encoding="utf-8")
    print(f"\nwrote {OUT / 'credits.json'}")
    print(f"wrote {ROOT / 'src' / 'cropPhotoCredits.json'}")

    if problems:
        print("\nRESULT: FAIL")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"\nRESULT: PASS ({len(credits)} crops, licences verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
