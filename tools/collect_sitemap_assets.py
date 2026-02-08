#!/usr/bin/env python3
"""Collect image and media URLs from madisonmft.com sitemap and download them.

- Reads sitemap.xml
- Extracts <image:loc> URLs (Squarespace feature images)
- Downloads to src/assets/images/madisonmft/
- Writes src/_data/madisonmft_assets.json with mapping

Usage:
  python3 tools/collect_sitemap_assets.py [--limit 200] [--dry]
"""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SITEMAP = "https://www.madisonmft.com/sitemap.xml"
OUT_DIR = Path("src/assets/images/madisonmft")
DATA_OUT = Path("src/_data/madisonmft_assets.json")

UA = "Mozilla/5.0 (compatible; HeadlessSiteRebuild/1.0)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def norm_name(url: str) -> str:
    # produce stable filename from URL path + query
    u = urllib.parse.urlparse(url)
    base = os.path.basename(u.path) or "asset"
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-")
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    # Keep extension if present
    ext = ""
    m = re.search(r"\.(jpe?g|png|webp|gif|svg)$", base, flags=re.I)
    if m:
        ext = m.group(0).lower()
        base = re.sub(r"\.(jpe?g|png|webp|gif|svg)$", "", base, flags=re.I)
    return f"{base[:60]}-{h}{ext or '.jpg'}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=250)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    xml = fetch(SITEMAP).decode("utf-8", "ignore")
    img_urls = re.findall(r"<image:loc>(.*?)</image:loc>", xml)
    img_urls = [u.strip() for u in img_urls if u.strip()]

    # Also include the global botanical background image referenced in CSS.
    bg = "https://static.squarespace.com/static/52ec12dce4b008cb96e75c44/t/53193181e4b078aab7f8e291/1394160001232/dlAttach.php.jpeg"
    if bg not in img_urls:
        img_urls.append(bg)

    # De-dupe, stable order
    seen = set()
    uniq = []
    for u in img_urls:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)

    uniq = uniq[: args.limit]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    mapping = {
        "source": SITEMAP,
        "count": len(uniq),
        "items": [],
    }

    for i, url in enumerate(uniq, start=1):
        fn = norm_name(url)
        out_path = OUT_DIR / fn
        rel_path = "/assets/images/madisonmft/" + fn

        item = {"url": url, "path": rel_path}

        if out_path.exists():
            mapping["items"].append(item)
            continue

        print(f"[{i}/{len(uniq)}] {url} -> {out_path}")
        if args.dry:
            mapping["items"].append(item)
            continue

        try:
            data = fetch(url)
            out_path.write_bytes(data)
        except Exception as e:
            print("WARN download failed:", url, e, file=sys.stderr)
            item["error"] = str(e)

        mapping["items"].append(item)

    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    print("Wrote", DATA_OUT)


if __name__ == "__main__":
    main()
