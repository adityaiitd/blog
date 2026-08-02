#!/usr/bin/env python3
"""Turn raw bookmark JSON into simple digests (+ optional link enrichment)."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def fetch_page(url: str, timeout: int = 12) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read(400_000)
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def meta(html: str, prop: str) -> str | None:
    patterns = [
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(prop)}["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.I)
        if m:
            return unescape(m.group(1).strip())
    return None


def enrich_link(url: str) -> dict[str, str]:
    html = fetch_page(url)
    if not html:
        host = urlparse(url).netloc.replace("www.", "")
        return {
            "url": url,
            "title": host or url,
            "description": "",
            "site_name": host,
        }
    title = meta(html, "og:title") or meta(html, "twitter:title")
    if not title:
        tm = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
        title = unescape(re.sub(r"\s+", " ", tm.group(1))).strip() if tm else ""
    desc = (
        meta(html, "og:description")
        or meta(html, "twitter:description")
        or meta(html, "description")
        or ""
    )
    site = meta(html, "og:site_name") or urlparse(url).netloc.replace("www.", "")
    return {
        "url": url,
        "title": title[:200],
        "description": desc[:400],
        "site_name": site[:120],
    }


def guess_category(text: str, links: list[dict[str, Any]]) -> str:
    blob = " ".join(
        [text]
        + [l.get("title", "") + " " + l.get("description", "") for l in links]
    ).lower()
    rules = [
        ("AI / ML", ["ai", "llm", "gpt", "machine learning", "model", "openai", "anthropic"]),
        ("Startup / Funding", ["raised", "funding", "seed", "series", "startup", "vc"]),
        ("Product Launch", ["launch", "announcing", "introducing", "shipped", "release"]),
        ("Politics / News", ["election", "congress", "president", "war", "policy"]),
        ("Science", ["study", "research", "paper", "scientists", "nature"]),
        ("Crypto", ["crypto", "bitcoin", "ethereum", "blockchain", "token"]),
        ("Jobs / Hiring", ["hiring", "we're hiring", "job", "career"]),
        ("Tools / Software", ["open source", "github", "api", "sdk", "devtools"]),
    ]
    for label, keys in rules:
        if any(k in blob for k in keys):
            return label
    return "Other"


def company_or_topic(author: str, text: str, links: list[dict[str, Any]]) -> str:
    for link in links:
        site = (link.get("site_name") or "").strip()
        title = (link.get("title") or "").strip()
        if site and site.lower() not in {"x.com", "twitter.com", "t.co"}:
            # Prefer a human title over bare domain when short
            if title and len(title) < 60 and "http" not in title.lower():
                return title
            return site
    # First @mention or hashtag-ish proper noun
    m = re.search(r"@([A-Za-z0-9_]{2,})", text)
    if m:
        return f"@{m.group(1)}"
    words = re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", text)
    if words:
        return " ".join(words[:3])
    return f"Post by @{author}" if author else "Untitled topic"


def simple_summary(text: str, links: list[dict[str, Any]]) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        if links and links[0].get("description"):
            clean = links[0]["description"]
        elif links and links[0].get("title"):
            clean = f"Shared a link: {links[0]['title']}"
        else:
            return "This post doesn't have much text. It may be mostly a picture or video."

    # Keep it eighth-grader simple and short
    sentence = clean
    # Prefer first 1-2 sentences
    parts = re.split(r"(?<=[.!?])\s+", clean)
    if parts:
        sentence = " ".join(parts[:2])
    if len(sentence) > 280:
        sentence = sentence[:277].rsplit(" ", 1)[0] + "..."

    # Light plain-language polish
    sentence = sentence.replace("&amp;", "and")
    return sentence


def why_it_matters(text: str, links: list[dict[str, Any]], category: str) -> str:
    if links and links[0].get("description"):
        d = links[0]["description"]
        if len(d) > 180:
            d = d[:177].rsplit(" ", 1)[0] + "..."
        return f"There's a link with more info: {d}"
    hints = {
        "AI / ML": "This is about artificial intelligence — tools that help computers learn and do smart tasks.",
        "Startup / Funding": "This is about a company getting money to grow.",
        "Product Launch": "Someone is showing off something new people can use.",
        "Politics / News": "This is news about the world or government.",
        "Science": "This is about a science finding or research.",
        "Crypto": "This is about digital money or blockchain tech.",
        "Jobs / Hiring": "Someone is looking for workers or talking about jobs.",
        "Tools / Software": "This is about software or a tool builders use.",
    }
    return hints.get(
        category,
        "You saved this because it looked useful or interesting. Ask if you want a deeper dive.",
    )


def key_facts(post: dict[str, Any]) -> list[str]:
    facts = []
    if post.get("author_handle"):
        facts.append(f"Posted by @{post['author_handle']}")
    if post.get("posted_at"):
        facts.append(f"Original post date: {post['posted_at'][:10]}")
    for link in post.get("links") or []:
        if link.get("url"):
            host = urlparse(link["url"]).netloc.replace("www.", "")
            facts.append(f"Link: {host}")
            break
    if post.get("media"):
        facts.append(f"Has {len(post['media'])} image(s)")
    return facts[:5]


def process_post(raw: dict[str, Any], enrich: bool) -> dict[str, Any]:
    links_in = raw.get("links") or []
    enriched_links = []
    for link in links_in[:3]:
        url = link.get("url") if isinstance(link, dict) else str(link)
        if not url:
            continue
        if enrich:
            enriched_links.append(enrich_link(url))
        else:
            enriched_links.append(
                {
                    "url": url,
                    "title": (link.get("title") if isinstance(link, dict) else "") or "",
                    "description": "",
                    "site_name": urlparse(url).netloc.replace("www.", ""),
                }
            )

    text = raw.get("text") or ""
    category = guess_category(text, enriched_links)
    topic = company_or_topic(raw.get("author_handle", ""), text, enriched_links)
    summary = simple_summary(text, enriched_links)
    matter = why_it_matters(text, enriched_links, category)

    out = {
        **raw,
        "links": enriched_links,
        "company_or_topic": topic,
        "simple_summary": summary,
        "why_it_matters": matter,
        "category": category,
        "tags": [category.lower().replace(" / ", "-").replace(" ", "-")],
        "key_facts": key_facts({**raw, "links": enriched_links}),
        "read_time_seconds": 90,
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="bookmarks-digest/data/raw-bookmarks.json",
        help="Raw export JSON from the browser script",
    )
    parser.add_argument(
        "--output",
        default="bookmarks-digest/data/bookmarks.json",
        help="Enriched digest JSON for the viewer",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip fetching linked pages",
    )
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        raise SystemExit(f"Missing input file: {inp}")

    data = json.loads(inp.read_text(encoding="utf-8"))
    posts = data.get("posts") or data
    if isinstance(posts, dict):
        posts = posts.get("posts", [])

    digests = []
    for i, post in enumerate(posts[: args.limit]):
        print(f"[{i+1}/{min(len(posts), args.limit)}] @{post.get('author_handle')}…")
        digests.append(process_post(post, enrich=not args.no_enrich))

    out = {
        "exported_at": data.get("exported_at"),
        "processed_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "source": data.get("source", "x.com/i/bookmarks"),
        "count": len(digests),
        "posts": digests,
    }
    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(digests)} digests → {outp}")


if __name__ == "__main__":
    main()
