"""MCP server: unofficial read-only access to FAZ.NET — the
Frankfurter Allgemeine Zeitung (faz.net), one of Germany's
biggest quality daily newspapers (founded 1949) — via its
official RSS feeds (the main feed /rss/aktuell/, 169 items, plus
11 per-section feeds) and article pages (full text from the
JSON-LD NewsArticle articleBody; the server-rendered <article>
paragraphs are the fallback). No key, no login."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import domain as _dom
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for FAZ.NET — the Frankfurter
Allgemeine Zeitung (faz.net), one of Germany's biggest quality
daily newspapers — via its official RSS feeds (no key, no login)
and article pages. The latest news (the main feed, 169 items,
newest first), keyword search across the main feed (title +
teaser + author), stories by section (11 section feeds: politik,
wirtschaft, sport, feuilleton, finanzen, gesellschaft, wissen,
besser-leben, rhein-main, karriere-hochschule, technik-motor),
the sections and authors in today's main feed, and full article
text (the JSON-LD NewsArticle articleBody — ~5,000 characters
sampled — with the server-rendered <article> paragraphs as
fallback). The feeds carry no topic tags, so there is no topic
tool; the section of one article (e.g. "Politik > Inland") is
reported by faz_get_article from the page's BreadcrumbList. FAZ+
articles are paywalled: a paywalled page is reported as
paywalled=true with the teaser only, never fabricated text.
Video and podcast pages return kind="video"/"podcast" with their
description only.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · \
https://mabbasi.ir — Germany MCP factory.\
"""


_SOURCE = "faz.net"
_DISCLAIMER = "Unofficial read-only data from FAZ.NET's public RSS feeds and article pages; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


mcp = FastMCP("faz-mcp", instructions=INSTRUCTIONS)


def _main_feed(limit: int) -> dict:
    """Fetch the main FAZ feed (/rss/aktuell/, ~169 items), newest
    first, capped."""
    parsed = _dom.parse_rss(_http.fetch_feed(_dom.MAIN_FEED))
    merged = _dom.dedupe_sort(parsed["items"])
    return {
        "feed_title": parsed["feed_title"],
        "total_results": len(merged),
        "count": min(limit, len(merged)),
        "items": merged[:limit],
    }


@mcp.tool()
def faz_latest(limit: int = 10) -> str:
    """Top FAZ news (the official main RSS feed, ~169 items), newest
first. limit: 1..50 (default 10). Every item carries a title, a
per-article link for faz_get_article, a teaser (description),
author (dc:creator, when the feed carries one), section, kind
(article/video/podcast) and image URL and publish time."""
    try:
        lim = _dom.validate_limit(limit)
        out = _main_feed(lim)
    except (_http.FazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def faz_search_news(query: str, limit: int = 10) -> str:
    """Search FAZ news by keyword (title + teaser + author) across
the official main RSS feed (~169 items). query: free text, e.g.
"Rente" or "Klimaschutz". limit: 1..50 (default 10). Newest
first, de-duplicated by link."""
    try:
        if not (query or "").strip():
            return _ok({"error": "query must not be empty"})
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.MAIN_FEED))
        found = _dom.search_items(
            _dom.dedupe_sort(parsed["items"]), query.strip()
        )
        out = {
            "query": query.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.FazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def faz_by_section(section: str, limit: int = 10) -> str:
    """Newest FAZ stories from one section feed. section: one of
politik, wirtschaft, sport, feuilleton, finanzen, gesellschaft,
wissen, besser-leben, rhein-main, karriere-hochschule,
technik-motor. limit: 1..50 (default 10). Items carry title, link
(a per-article URL for faz_get_article), teaser, author, section,
kind and image URL and publish time."""
    try:
        if not (section or "").strip():
            return _ok({"error": "section must not be empty"})
        lim = _dom.validate_limit(limit)
        sec = _dom.validate_section(section.strip())
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.SECTION_FEEDS[sec]))
        merged = _dom.dedupe_sort(parsed["items"])
        out = {
            "section": sec,
            "feed_title": parsed["feed_title"],
            "total_results": len(merged),
            "count": min(lim, len(merged)),
            "items": merged[:lim],
        }
    except (_http.FazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def faz_sections() -> str:
    """The sections in today's FAZ main feed, with how many stories
each carries — most stories first. Use faz_by_section to read one
section's stories."""
    try:
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.MAIN_FEED))
        sections = _dom.sections_with_counts(
            _dom.dedupe_sort(parsed["items"])
        )
        out = {
            "total_results": len(sections),
            "count": len(sections),
            "sections": sections,
        }
    except (_http.FazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def faz_by_author(author: str, limit: int = 10) -> str:
    """Newest FAZ stories by one author (the feed's dc:creator,
e.g. "Stephan Klenner" — matched case-insensitively as a
substring, so a surname is enough). author: free text.
limit: 1..50 (default 10). Items carry title, link (a
per-article URL for faz_get_article), teaser, author, section,
kind and image URL and publish time."""
    try:
        if not (author or "").strip():
            return _ok({"error": "author must not be empty"})
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.MAIN_FEED))
        found = _dom.items_by_author(
            _dom.dedupe_sort(parsed["items"]), author.strip()
        )
        out = {
            "author": author.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.FazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def faz_get_article(url: str) -> str:
    """Full text of one FAZ article page (the JSON-LD NewsArticle
articleBody, with the server-rendered <article> paragraphs as
fallback). url: a faz.net article URL, e.g. from faz_latest
(/aktuell/<section>/…-<id>.html). Returns title, author, publish
time, the section from the page's BreadcrumbList (e.g. "Politik >
Inland"), the body text and its word count. A FAZ+ page returns
paywalled=true with only the teaser as body — the full text needs
a subscription. A video page returns kind="video" with its
description and duration. Feed URLs, the home page and off-site
links are refused. Nothing is ever fabricated."""
    try:
        if not (url or "").strip():
            return _ok({"error": "url must not be empty"})
        url = url.strip()
        article = _dom.parse_article(_http.fetch_article(url), url)
        paywalled = article["paywalled"]
        note = ""
        if paywalled:
            note = (
                "This article is paywalled (FAZ+): only the teaser is "
                "available; the full text needs a subscription."
            )
        elif article["teaser_only"]:
            note = (
                "Only the teaser is available for this item; the teaser "
                "is the whole freely available text."
            )
        out = {
            "url": url,
            "title": article["title"],
            "author": article["author"],
            "published": article["published"],
            "section": article["section"],
            "kind": article["kind"],
            "paywalled": paywalled,
            "teaser_only": article["teaser_only"],
            "word_count": article["word_count"],
            "body": article["body"],
            "description": article["description"],
            "note": note,
        }
        if article["kind"] == "video":
            out["duration"] = article.get("duration")
    except (_http.FazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def faz_health() -> str:
    """Check whether the FAZ RSS feed is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
