#!/usr/bin/env python3
"""Import page text blocks from madisonmft.com into this Eleventy site.

Approach:
- Download HTML
- Extract Squarespace content blocks: <div class="sqs-block-content"> ...
- Strip tags into plain-ish text (keep simple formatting)

This is not a perfect Squarespace exporter, but it's fast and stable.
"""

import re
import sys
import urllib.request
from html import unescape
from pathlib import Path

COMMON_INTRO_SNIPPET = (
    "provides therapy for"
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; HeadlessSiteRebuild/1.0)"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "ignore")


def extract_blocks(html: str):
    blocks = re.findall(
        r'<div class="sqs-block-content"[^>]*>(.*?)</div>\s*</div>',
        html,
        flags=re.S,
    )
    return blocks


def html_to_text(fragment: str) -> str:
    # Convert a subset of HTML tags to readable text.
    s = fragment
    s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p\s*>", "\n\n", s, flags=re.I)
    s = re.sub(r"</li\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    s = re.sub(r"</h[1-6]\s*>", "\n\n", s, flags=re.I)
    s = re.sub(r"<h1[^>]*>", "# ", s, flags=re.I)
    s = re.sub(r"<h2[^>]*>", "## ", s, flags=re.I)
    s = re.sub(r"<h3[^>]*>", "### ", s, flags=re.I)
    # Links: keep link text, drop href (we'll manually relink later)
    s = re.sub(r"<a [^>]*>", "", s, flags=re.I)
    s = re.sub(r"</a>", "", s, flags=re.I)

    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"\u00a0", " ", s)
    # normalize whitespace but keep newlines
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def clean_blocks(block_texts):
    cleaned = []
    for t in block_texts:
        t = t.strip()
        if not t:
            continue
        # Drop navigation / repeated boilerplate blocks that show up on many pages.
        if COMMON_INTRO_SNIPPET in t and len(t) < 450:
            # This often matches the short header boilerplate paragraph.
            continue
        cleaned.append(t)
    return cleaned


def write_page(dest_path: Path, title: str, permalink: str, body_md: str):
    frontmatter = f"---\nlayout: layouts/base.njk\ntitle: {title}\npermalink: {permalink}\n---\n\n"
    content = frontmatter + "<div class=\"prose\">\n" + body_md + "\n</div>\n"
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(content, encoding="utf-8")


def import_one(url: str):
    html = fetch(url)
    blocks = extract_blocks(html)
    texts = [html_to_text(b) for b in blocks]
    texts = [t for t in texts if t]
    texts = clean_blocks(texts)
    return "\n\n".join(texts)


def main():
    pages = [
        ("https://www.madisonmft.com/about-madison-mft", "src/pages/about.md", "About", "/about/"),
        ("https://www.madisonmft.com/our-team", "src/pages/team.md", "Our Team", "/team/"),
        ("https://www.madisonmft.com/contact", "src/pages/contact.md", "Contact", "/contact/"),
        ("https://www.madisonmft.com/faq", "src/pages/faq.md", "FAQ", "/faq/"),

        ("https://www.madisonmft.com/individual-therapy", "src/pages/services/individual.md", "Individual Therapy", "/services/individual/"),
        ("https://www.madisonmft.com/couples-therapy", "src/pages/services/couples.md", "Couples Therapy", "/services/couples/"),
        ("https://www.madisonmft.com/family-therapy", "src/pages/services/family.md", "Family Therapy", "/services/family/"),
        ("https://www.madisonmft.com/anger-management", "src/pages/services/anger.md", "Anger Management", "/services/anger/"),
        ("https://www.madisonmft.com/grief-management", "src/pages/services/grief.md", "Grief Management", "/services/grief/"),

        ("https://www.madisonmft.com/melissa-kester", "src/pages/team/melissa-kester.md", "Melissa Kester", "/team/melissa-kester/"),
        ("https://www.madisonmft.com/relational-wisdom-intensive", "src/pages/workshops/relational-wisdom-intensive.md", "Relational Wisdom Intensive", "/workshops/relational-wisdom-intensive/"),
    ]

    for url, dest, title, permalink in pages:
        print("Importing", url, "->", dest)
        body = import_one(url)
        if not body:
            print("WARNING: no body extracted for", url, file=sys.stderr)
        # Ensure H1 at top
        if not body.lstrip().startswith("#"):
            body = f"# {title}\n\n" + body
        write_page(Path(dest), title, permalink, body)


if __name__ == "__main__":
    main()
