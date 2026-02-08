#!/usr/bin/env python3

import re
import sys
import urllib.request
from html import unescape
from pathlib import Path
from datetime import datetime

SITEMAP = 'https://www.madisonmft.com/sitemap.xml'
OUT_DIR = Path('src/posts')
OUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; HeadlessSiteRebuild/1.0)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'ignore')


def extract_blocks(html: str):
    return re.findall(r'<div class="sqs-block-content"[^>]*>(.*?)</div>\s*</div>', html, flags=re.S)


def html_to_text(fragment: str) -> str:
    s = fragment
    s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p\s*>", "\n\n", s, flags=re.I)
    s = re.sub(r"</li\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    s = re.sub(r"</h[1-6]\s*>", "\n\n", s, flags=re.I)
    s = re.sub(r"<h2[^>]*>", "## ", s, flags=re.I)
    s = re.sub(r"<h3[^>]*>", "### ", s, flags=re.I)
    s = re.sub(r"<a [^>]*>", "", s, flags=re.I)
    s = re.sub(r"</a>", "", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"\u00a0", " ", s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def parse_sitemap(xml: str):
    locs = re.findall(r'<loc>(.*?)</loc>', xml)
    lastmods = re.findall(r'<lastmod>(.*?)</lastmod>', xml)
    # sitemap order is url blocks; easiest: iterate url entries
    urls = []
    for url_block in re.findall(r'<url>(.*?)</url>', xml, flags=re.S):
        loc = re.search(r'<loc>(.*?)</loc>', url_block)
        if not loc:
            continue
        loc = loc.group(1).strip()
        lm = re.search(r'<lastmod>(.*?)</lastmod>', url_block)
        lastmod = lm.group(1).strip() if lm else None
        urls.append((loc, lastmod))
    return urls


def is_article_post(loc: str) -> bool:
    if not loc.startswith('https://www.madisonmft.com/articles/'):
        return False
    if '/category/' in loc or '/tag/' in loc:
        return False
    # posts typically have /YYYY/
    return bool(re.search(r'/articles/\d{4}/\d{1,2}/\d{1,2}/', loc))


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s[:80] or 'post'


def extract_title(html: str) -> str:
    m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    if m:
        return unescape(m.group(1)).strip()
    m = re.search(r'<title>(.*?)</title>', html, flags=re.S)
    if m:
        return re.sub(r'\s+', ' ', unescape(m.group(1))).strip()
    return 'Article'


def parse_date_from_url(loc: str):
    m = re.search(r'/articles/(\d{4})/(\d{1,2})/(\d{1,2})/', loc)
    if not m:
        return None
    y,mo,d = map(int, m.groups())
    return datetime(y,mo,d)


def import_post(loc: str):
    html = fetch(loc)
    title = extract_title(html)
    dt = parse_date_from_url(loc)
    blocks = [html_to_text(b) for b in extract_blocks(html)]
    blocks = [b for b in blocks if b]

    # drop very short boilerplate blocks
    blocks2 = []
    for b in blocks:
        if 'provides therapy for' in b and len(b) < 500:
            continue
        blocks2.append(b)

    body = '\n\n'.join(blocks2).strip()
    if not body:
        body = '(Imported content pending — Squarespace markup variant.)'

    date_iso = dt.strftime('%Y-%m-%d') if dt else None
    filename = f"{date_iso}-{slugify(title)}.md" if date_iso else f"{slugify(title)}.md"

    import json
    fm = ["---", "layout: layouts/base.njk", "tags: [posts]", f"title: {json.dumps(title)}" ]
    if date_iso:
        fm.append(f"date: {date_iso}")
    fm.append("---\n")

    out = '\n'.join(fm) + "\n<div class=\"prose\">\n" + body + "\n</div>\n"
    (OUT_DIR / filename).write_text(out, encoding='utf-8')


def main():
    xml = fetch(SITEMAP)
    urls = parse_sitemap(xml)
    posts = [(loc, lm) for (loc,lm) in urls if is_article_post(loc)]

    # sort by lastmod desc, fallback to url-date
    def key(x):
        loc,lm = x
        if lm:
            try:
                return lm
            except:
                pass
        dt = parse_date_from_url(loc)
        return dt.isoformat() if dt else ''

    posts = sorted(posts, key=key, reverse=True)

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    for loc,lm in posts[:limit]:
        print('Import', loc)
        import_post(loc)

    print('Imported', min(limit, len(posts)), 'posts into', OUT_DIR)


if __name__ == '__main__':
    main()
