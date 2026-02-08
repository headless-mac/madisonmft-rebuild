#!/usr/bin/env python3
"""Scan src/posts for external image URLs and download them.

- Finds markdown image URLs in posts
- Downloads Squarespace CDN images into src/assets/images/madisonmft/
- Updates src/_data/madisonmft_assets.json

Usage:
  python3 tools/collect_post_images.py
"""

import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

POSTS_DIR = Path('src/posts')
OUT_DIR = Path('src/assets/images/madisonmft')
DATA_OUT = Path('src/_data/madisonmft_assets.json')

UA = 'Mozilla/5.0 (compatible; HeadlessSiteRebuild/1.0)'


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def norm_name(url: str) -> str:
    u = urllib.parse.urlparse(url)
    base = os.path.basename(u.path) or 'asset'
    base = re.sub(r'[^A-Za-z0-9._-]+', '-', base).strip('-')
    h = hashlib.sha1(url.encode('utf-8')).hexdigest()[:10]
    ext = ''
    m = re.search(r'\.(jpe?g|png|webp|gif|svg)$', base, flags=re.I)
    if m:
        ext = m.group(0).lower()
        base = re.sub(r'\.(jpe?g|png|webp|gif|svg)$', '', base, flags=re.I)
    return f"{base[:60]}-{h}{ext or '.jpg'}"


def load_map():
    if DATA_OUT.exists():
        return json.loads(DATA_OUT.read_text(encoding='utf-8'))
    return {'source': 'derived', 'count': 0, 'items': []}


def main():
    m = load_map()
    known = {it.get('url'): it.get('path') for it in m.get('items', []) if it.get('url')}

    urls = set()
    for p in POSTS_DIR.glob('*.md'):
        txt = p.read_text(encoding='utf-8', errors='ignore')
        for u in re.findall(r'!\[[^\]]*\]\((https?://[^)\s]+)\)', txt):
            if 'squarespace-cdn.com' in u or 'static.squarespace.com' in u:
                urls.add(u)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    new_items = 0
    for url in sorted(urls):
        if url in known:
            continue
        fn = norm_name(url)
        out_path = OUT_DIR / fn
        rel_path = '/assets/images/madisonmft/' + fn

        print('Download', url)
        try:
            data = fetch(url)
            out_path.write_bytes(data)
            m['items'].append({'url': url, 'path': rel_path})
            new_items += 1
        except Exception as e:
            print('WARN failed', url, e, file=sys.stderr)
            m['items'].append({'url': url, 'path': rel_path, 'error': str(e)})

    m['count'] = len(m.get('items', []))
    DATA_OUT.write_text(json.dumps(m, indent=2), encoding='utf-8')
    print('Added', new_items, 'images. Total items:', m['count'])


if __name__ == '__main__':
    main()
