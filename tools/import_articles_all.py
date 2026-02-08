#!/usr/bin/env python3
"""Import (or refresh) Squarespace blog posts from madisonmft.com.

Features:
- Crawls sitemap.xml for /articles/* URLs (excluding /category/ and /tag/)
- Extracts title/date/og:description/og:image
- Extracts main Squarespace blocks (<div class="sqs-block-content">...)
- Converts a small subset of HTML to readable markdown-ish text
- Preserves links as [text](href)
- Captures YouTube embeds (as links) when present
- Maps known image URLs to locally downloaded versions via src/_data/madisonmft_assets.json

Usage:
  python3 tools/import_articles_all.py [--limit 50] [--since 2019-01-01]
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from pathlib import Path

SITEMAP = "https://www.madisonmft.com/sitemap.xml"
OUT_DIR = Path("src/posts")
ASSET_MAP_PATH = Path("src/_data/madisonmft_assets.json")

UA = "Mozilla/5.0 (compatible; HeadlessSiteRebuild/1.0)"


def fetch_text(url: str, timeout=90) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def parse_sitemap(xml: str):
    urls = []
    for url_block in re.findall(r"<url>(.*?)</url>", xml, flags=re.S):
        locm = re.search(r"<loc>(.*?)</loc>", url_block)
        if not locm:
            continue
        loc = locm.group(1).strip()
        lmm = re.search(r"<lastmod>(.*?)</lastmod>", url_block)
        lastmod = lmm.group(1).strip() if lmm else None
        urls.append((loc, lastmod, url_block))
    return urls


def is_article(loc: str) -> bool:
    if not loc.startswith("https://www.madisonmft.com/articles"):
        return False
    if "/category/" in loc or "/tag/" in loc:
        return False
    if loc.rstrip("/") == "https://www.madisonmft.com/articles":
        return False
    return True


def parse_date_from_url(loc: str):
    m = re.search(r"/articles/(\d{4})/(\d{1,2})/(\d{1,2})/", loc)
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    return datetime(y, mo, d)


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"['’]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:90] or "post"


def extract_meta(html: str, prop: str):
    m = re.search(rf'<meta property="{re.escape(prop)}" content="([^"]+)"', html)
    return unescape(m.group(1)).strip() if m else None


def extract_title(html: str):
    return extract_meta(html, "og:title") or (re.search(r"<title>(.*?)</title>", html, flags=re.S).group(1).strip() if re.search(r"<title>(.*?)</title>", html, flags=re.S) else "Article")


def extract_blocks(html: str):
    return re.findall(r'<div class="sqs-block-content"[^>]*>(.*?)</div>\s*</div>', html, flags=re.S)


def map_asset(url: str, asset_map: dict) -> str:
    # Map an external URL to a local /assets path if present.
    if not url:
        return url
    items = asset_map.get("items", [])
    for it in items:
        if it.get("url") == url:
            return it.get("path")
    return url


def html_fragment_to_md(fragment: str, asset_map: dict) -> str:
    s = fragment

    # Images -> markdown images
    def img_repl(m):
        alt = m.group(1) or ""
        src = m.group(2) or ""
        src = unescape(src)
        src = map_asset(src, asset_map)
        alt = unescape(alt).strip()
        return f"![{alt}]({src})"

    s = re.sub(r"<img[^>]*alt=\"([^\"]*)\"[^>]*src=\"([^\"]+)\"[^>]*>", img_repl, s, flags=re.I)
    s = re.sub(r"<img[^>]*src=\"([^\"]+)\"[^>]*>", lambda m: f"![]({map_asset(unescape(m.group(1)), asset_map)})", s, flags=re.I)

    # Links -> [text](href)
    def link_repl(m):
        href = unescape(m.group(1) or "").strip()
        text = m.group(2) or ""
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", unescape(text)).strip() or href
        return f"[{text}]({href})"

    s = re.sub(r"<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", link_repl, s, flags=re.I | re.S)

    # Basic formatting
    s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p\s*>", "\n\n", s, flags=re.I)
    s = re.sub(r"</li\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    s = re.sub(r"</h[1-6]\s*>", "\n\n", s, flags=re.I)
    s = re.sub(r"<h2[^>]*>", "## ", s, flags=re.I)
    s = re.sub(r"<h3[^>]*>", "### ", s, flags=re.I)

    # Strip remaining tags
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"\u00a0", " ", s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def find_youtube_links(html: str):
    links = set()
    for m in re.finditer(r"https?://(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{6,})", html):
        vid = m.group(1)
        links.add(f"https://www.youtube.com/watch?v={vid}")
    for m in re.finditer(r"https?://youtu\.be/([A-Za-z0-9_-]{6,})", html):
        links.add(f"https://www.youtube.com/watch?v={m.group(1)}")
    return sorted(links)


def excerpt_from_body(body: str, max_len: int = 220) -> str:
    # Take first non-bullet paragraph-ish line
    for para in re.split(r"\n\n+", body):
        p = para.strip()
        if not p:
            continue
        if p.startswith("-"):
            continue
        p = re.sub(r"\s+", " ", p)
        if len(p) < 40:
            continue
        if len(p) > max_len:
            p = p[: max_len].rsplit(" ", 1)[0] + "…"
        return p
    return ""


def load_asset_map():
    if ASSET_MAP_PATH.exists():
        return json.loads(ASSET_MAP_PATH.read_text(encoding="utf-8"))
    return {"items": []}


def write_post(title: str, date_iso, excerpt: str, featured, youtube, body_md: str):
    import json as _json

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(title)
    filename = f"{date_iso}-{slug}.md" if date_iso else f"{slug}.md"
    out_path = OUT_DIR / filename

    fm = [
        "---",
        "layout: layouts/base.njk",
        "tags: [posts]",
        f"title: {_json.dumps(title)}",
    ]
    if date_iso:
        fm.append(f"date: {date_iso}")
    if excerpt:
        fm.append(f"excerpt: {_json.dumps(excerpt)}")
    if featured:
        fm.append(f"featuredImage: {_json.dumps(featured)}")
    if youtube:
        fm.append("youtube:")
        for y in youtube:
            fm.append(f"  - {_json.dumps(y)}")
    fm.append("---\n")

    content = "\n".join(fm) + "\n" + body_md.strip() + "\n"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--since", type=str, default="")
    args = ap.parse_args()

    since_dt = None
    if args.since:
        since_dt = datetime.fromisoformat(args.since)

    asset_map = load_asset_map()

    xml = fetch_text(SITEMAP)
    urls = parse_sitemap(xml)
    posts = []
    for loc, lastmod, _block in urls:
        if not is_article(loc):
            continue
        dt = parse_date_from_url(loc)
        if since_dt and dt and dt < since_dt:
            continue
        posts.append((loc, lastmod, dt))

    # Prefer newest first
    def sort_key(t):
        loc, lastmod, dt = t
        if dt:
            return dt
        if lastmod:
            try:
                return datetime.fromisoformat(lastmod)
            except Exception:
                pass
        return datetime(1970, 1, 1)

    posts.sort(key=sort_key, reverse=True)
    posts = posts[: args.limit]

    for loc, lastmod, dt in posts:
        print("Import", loc)
        html = fetch_text(loc)
        title = extract_title(html)
        desc = extract_meta(html, "og:description") or ""
        og_img = extract_meta(html, "og:image")
        featured = map_asset(og_img, asset_map) if og_img else None
        youtube = find_youtube_links(html)

        blocks = extract_blocks(html)
        texts = [html_fragment_to_md(b, asset_map) for b in blocks]
        texts = [t for t in texts if t]

        # Filter short boilerplate
        body_parts = []
        for t in texts:
            if "provides therapy for" in t and len(t) < 500:
                continue
            body_parts.append(t)

        body = "\n\n".join(body_parts).strip()
        if not body:
            body = "(Imported content pending — Squarespace markup variant.)"

        date_iso = dt.strftime("%Y-%m-%d") if dt else (lastmod[:10] if lastmod else None)
        excerpt = desc.strip() or excerpt_from_body(body)

        # Normalize: make sure post content is wrapped in .prose for now
        body_md = "<div class=\"prose\">\n" + body + "\n\n"
        if youtube:
            body_md += "## Video\n\n" + "\n".join([f"- {u}" for u in youtube]) + "\n"
        body_md += "</div>\n"

        out_path = write_post(title=title, date_iso=date_iso, excerpt=excerpt, featured=featured, youtube=youtube, body_md=body_md)
        print(" ->", out_path)

    print("Done. Imported", len(posts), "posts.")


if __name__ == "__main__":
    main()
