"""Domain logic: shape FAZ.NET's official RSS feeds and article pages
into compact dicts (stdlib only).

Data source: the official FAZ RSS feeds (no key, no login) —
https://www.faz.net/rss/aktuell/ (169 items, newest first) plus
11 per-section feeds under /rss/aktuell/<section>/ — plus article
pages, whose full text lives in the JSON-LD NewsArticle
"articleBody" (the server-rendered <article> paragraphs are the
fallback).

Honest limitations (verified live 2026-11-27):
- The feeds carry NO <category> tags, so there is no topic-tag
  tool: stories are grouped by section instead (the section is
  derived from the article link path, e.g. /aktuell/politik/…,
  and reported by faz_get_article from the page's BreadcrumbList).
- /rss/<section>/ (without /aktuell/) all 404, and
  /rss/aktuell/kultur/ 404 — the 11 section feeds listed in
  SECTIONS are the only ones. Feed links end -<id>.html and 301
  to the canonical URL (httpx follows redirects).
- Feed items include video pages (/video/…) and podcast pages
  (/podcasts/…) alongside articles; they are returned as-is with
  kind="video"/"podcast" and are never fetched by faz_latest —
  faz_get_article on a video page returns kind="video" with the
  description and duration, never fabricated text.
- The main feed also carries FAZ+ articles (/premium/… links);
  their paywall status is only known from the article page.
- Article body: the JSON-LD NewsArticle articleBody IS the full
  text (sampled: 4,971 characters on a free article,
  isAccessibleForFree=true). The <article> <p> tags are the
  fallback when articleBody is absent.
- PAYWALL (verified live): a FAZ+ opinion article carries
  isAccessibleForFree=false and NO articleBody — faz_get_article
  returns paywalled=true with only the feed teaser as body, never
  fabricated text. The SSR <article> of a paywalled page holds
  only a partial teaser plus the "Zugang zu allen FAZ+ Beiträgen"
  subscription promo — it is never used as body.
- SSR fallback filters: the "Zusammenfassung" heading, the
  caption+teaser paragraph (the image caption merged with the
  teaser text), photo captions ("Foto:"), byline fragments (bare
  author-name tokens), repeats of the title / description, and
  the "Die F.A.Z. berichtet frei von externen Einflüssen" footer.
- Feed pubDates are GMT (RFC 2822); dc:creator is present on
  ~83% of items (141/169) — faz_by_author matches it as a
  substring. media:content carries an image/webp on every item.
"""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

BASE = "https://www.faz.net"
MAIN_FEED = f"{BASE}/rss/aktuell/"
SECTIONS = (
    "politik",
    "wirtschaft",
    "sport",
    "feuilleton",
    "finanzen",
    "gesellschaft",
    "wissen",
    "besser-leben",
    "rhein-main",
    "karriere-hochschule",
    "technik-motor",
)
SECTION_FEEDS = {s: f"{BASE}/rss/aktuell/{s}/" for s in SECTIONS}
FEEDS = (MAIN_FEED,) + tuple(SECTION_FEEDS[s] for s in SECTIONS)

_DC_NS = "http://purl.org/dc/elements/1.1/"
_MEDIA_NS = "http://search.yahoo.com/mrss/"


def validate_limit(limit: int) -> int:
    """Clamp/validate the page size (the main feed carries ~169 items)."""
    if not 1 <= limit <= 50:
        raise ValueError(f"limit out of range: {limit} (expected 1..50)")
    return limit


def validate_section(section: str) -> str:
    """Normalise a section slug; raises ValueError on unknown sections."""
    s = (section or "").strip().lower()
    if s not in SECTIONS:
        raise ValueError(
            f"unknown section: {section!r} (expected one of: "
            + ", ".join(SECTIONS)
            + ")"
        )
    return s


def _text(elem, tag: str) -> str:
    child = elem.find(tag)
    if child is None or child.text is None:
        return ""
    return html.unescape(child.text).strip()


def _iso(date_text: str) -> str | None:
    if not date_text:
        return None
    text = date_text.strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(raw: str) -> str:
    text = _TAG_RE.sub("", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _published(item: ET.Element) -> str | None:
    """pubDate (RSS 2.0) or dc:date — matched by local name."""
    for child in item:
        local = child.tag.rsplit("}", 1)[-1]
        if local in ("pubDate", "date") and child.text:
            return _iso(child.text)
    return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def canonical_link(link: str) -> str:
    """Strip tracking query params from a feed link."""
    parsed = urlparse(link)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def section_from_link(link: str) -> str:
    """Section slug from an FAZ article link path.

    /aktuell/<section>/… → <section>; /premium/<section>/… →
    <section>; /video/… → "video"; /podcasts/… → "podcasts".
    """
    path = urlparse(link).path
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "aktuell":
        return parts[1]
    if len(parts) >= 2 and parts[0] == "premium":
        return parts[1]
    if parts and parts[0] in ("video", "podcasts"):
        return parts[0]
    return parts[0] if parts else ""


def kind_from_link(link: str) -> str:
    """article / video / podcast, from the link path."""
    path = urlparse(link).path
    if path.startswith("/video/"):
        return "video"
    if path.startswith("/podcasts/"):
        return "podcast"
    return "article"


def compact_item(item: ET.Element) -> dict | None:
    """One RSS 2.0 <item>: title, canonical link, teaser, publish
    time, author (dc:creator, when the feed carries one), section
    (from the link path), kind (article/video/podcast) and image
    URL (media:content image/*, else media:thumbnail).

    Returns None for off-site links.
    """
    link = canonical_link(_text(item, "link"))
    if not link.startswith("https://www.faz.net/"):
        return None
    title = _text(item, "title")
    description = _strip_tags(_text(item, "description"))
    if not title:
        title = description
    author = ""
    image_url = None
    for child in item:
        local = _local(child.tag)
        if local == "creator" and child.text:
            author = html.unescape(child.text).strip()
        elif local == "content":
            mime = (child.get("type") or "").strip()
            url = (child.get("url") or "").strip()
            if mime.startswith("image/") and url and image_url is None:
                image_url = html.unescape(url)
        elif local == "thumbnail":
            url = (child.get("url") or "").strip()
            if url and image_url is None:
                image_url = html.unescape(url)
    return {
        "title": title,
        "link": link,
        "description": description,
        "published": _published(item),
        "author": author,
        "section": section_from_link(link),
        "kind": kind_from_link(link),
        "image_url": image_url,
    }


def parse_rss(xml_text: str) -> dict:
    """Parse one FAZ RSS 2.0 feed into {feed_title, count, items}.

    Raises ValueError on malformed XML or a non-RSS document.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"invalid RSS XML: {e}") from e
    channel = root.find("channel")
    if channel is None:
        raise ValueError("unexpected RSS shape: no <channel> element")
    items = []
    for it in channel.findall("item"):
        compacted = compact_item(it)
        if compacted is not None:
            items.append(compacted)
    return {
        "feed_title": _text(channel, "title"),
        "count": len(items),
        "items": items,
    }


_LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    re.S | re.I,
)
_ARTICLE_RE = re.compile(r"<article[^>]*>(.*?)</article>", re.S | re.I)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_OG_DESC_RE = re.compile(
    r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',
    re.S | re.I,
)


def _author_name(raw) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return str(raw.get("name") or "").strip()
    if isinstance(raw, list):
        names = [_author_name(a) for a in raw]
        return ", ".join(n for n in names if n)
    return ""


def _ld_blocks(html_text: str) -> list:
    """JSON-LD blocks; a block may be a single object, a list, or an
    object with an @graph array — flatten it so the article node is
    found."""
    blocks: list[dict] = []

    def _add(data):
        if isinstance(data, dict):
            blocks.append(data)
            graph = data.get("@graph")
            if isinstance(graph, list):
                blocks.extend(b for b in graph if isinstance(b, dict))
        elif isinstance(data, list):
            for b in data:
                _add(b)

    for match in _LD_JSON_RE.finditer(html_text):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        _add(data)
    return blocks


def _page_title(html_text: str) -> str:
    match = _TITLE_RE.search(html_text)
    if not match:
        return ""
    title = _strip_tags(match.group(1))
    return re.sub(r"\s*\|\s*FAZ\.NET\s*$", "", title, flags=re.I)


def _section_from_breadcrumbs(blocks: list) -> str:
    """Top sections of the article from the BreadcrumbList block
    (positions 2.., e.g. "Politik > Inland"); "" when absent."""
    for block in blocks:
        if block.get("@type") != "BreadcrumbList":
            continue
        elements = block.get("itemListElement") or []
        names = []
        for el in elements:
            if isinstance(el, dict) and el.get("position", 0) > 1:
                name = str(el.get("name") or "").strip()
                if name:
                    names.append(name)
        # Last element is the article itself — drop it.
        if len(names) > 1:
            names = names[:-1]
        return " > ".join(names)
    return ""


def _clean_body_text(raw: str) -> str:
    """Normalise a JSON-LD articleBody: collapse runs of spaces,
    keep paragraph breaks, strip leading/trailing whitespace."""
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.splitlines()]
    paras: list[str] = []
    buf = ""
    for ln in lines:
        if ln:
            buf = f"{buf} {ln}".strip() if buf else ln
        elif buf:
            paras.append(buf)
            buf = ""
    if buf:
        paras.append(buf)
    return "\n\n".join(paras).strip()


def _ssr_body(
    html_text: str, title: str, description: str, author: str = ""
) -> str:
    """Body text from the server-rendered <article> paragraphs
    (fallback when the JSON-LD articleBody is absent).

    Filters out the "Zusammenfassung" heading, the caption+teaser
    paragraph (image caption merged with the teaser text), photo
    captions ("Foto:"), the FAZ+ subscription promo ("Zugang zu
    allen FAZ+ Beiträgen"), the "Die F.A.Z. berichtet frei…"
    footer, byline fragments (bare author-name tokens), repeats
    of the title / description, and de-duplicates identical
    paragraphs. Raises ValueError when no usable body paragraphs
    are found.
    """
    match = _ARTICLE_RE.search(html_text)
    if not match:
        raise ValueError(
            "no article text found on this page (no <article> body) — "
            "the page may be JS-rendered or an error page"
        )
    author_tokens = {
        t.casefold() for t in re.split(r"[^A-Za-zÀ-ÿ-]+", author) if t
    }
    paras: list[str] = []
    seen: set[str] = set()
    for raw in _P_RE.findall(match.group(1)):
        text = _strip_tags(raw)
        if not text:
            continue
        if text == "Zusammenfassung":
            continue  # summary heading, not article text
        if text.startswith("Foto:"):
            continue  # photo caption, not article text
        if "Zugang zu allen FAZ+ Beiträgen" in text:
            continue  # subscription promo, not article text
        if text.startswith("Die F.A.Z. berichtet frei"):
            continue  # footer line, not article text
        if " " not in text and text.casefold() in author_tokens:
            continue  # byline fragment: a bare author-name token
        if title and text == title:
            continue  # header paragraph: the title again
        if description and text == description:
            continue  # teaser paragraph: the description again
        if description and description in text:
            continue  # caption merged with the teaser text
        if text in seen:
            continue  # repeated paragraph (teaser echo)
        seen.add(text)
        paras.append(text)
    body = "\n\n".join(paras).strip()
    if not body:
        raise ValueError(
            "no article text found on this page (the <article> body is "
            "empty after filtering)"
        )
    return body


def parse_article(html_text: str, url: str = "") -> dict:
    """Extract the article from a faz.net page.

    Metadata comes from the JSON-LD NewsArticle block (headline,
    description, author, datePublished, isAccessibleForFree); the
    section comes from the page's BreadcrumbList (falling back to
    the link path); the body comes from the JSON-LD articleBody,
    falling back to the server-rendered <article> paragraphs. A
    paywalled page (isAccessibleForFree=false) returns
    paywalled=true with only the teaser as body — never fabricated
    text. A video page (JSON-LD VideoObject, no NewsArticle)
    returns kind="video" with the description as body and its
    duration. Returns {title, description, body, author,
    published, section, word_count, teaser_only, paywalled, kind}.
    Raises ValueError when no usable text is found.
    """
    blocks = _ld_blocks(html_text)
    article_block = None
    video_block = None
    for block in blocks:
        if block.get("@type") in ("NewsArticle", "Article"):
            article_block = block
            break
        if block.get("@type") == "VideoObject" and video_block is None:
            video_block = block

    title = _page_title(html_text)
    description = ""
    og = _OG_DESC_RE.search(html_text)
    if og:
        description = html.unescape(og.group(1)).strip()

    if article_block is None and video_block is not None:
        # Video page: no article text exists — description only.
        vtitle = _strip_tags(str(video_block.get("name") or "")) or title
        vdesc = _strip_tags(str(video_block.get("description") or ""))
        body = vdesc or description
        if not body:
            raise ValueError(
                "no article text found on this page (video page "
                "without a description)"
            )
        return {
            "title": vtitle,
            "description": body,
            "body": body,
            "author": "",
            "published": str(video_block.get("uploadDate") or "") or None,
            "section": "video",
            "word_count": len(body.split()),
            "teaser_only": True,
            "paywalled": False,
            "kind": "video",
            "duration": str(video_block.get("duration") or "") or None,
        }

    paywalled = False
    body = ""
    if article_block is not None:
        free = article_block.get("isAccessibleForFree")
        if free is not None:
            paywalled = not bool(free)
        title = (
            _strip_tags(str(article_block.get("headline") or "")) or title
        )
        description = description or _strip_tags(
            str(article_block.get("description") or "")
        )
        if not paywalled:
            body = _clean_body_text(
                str(article_block.get("articleBody") or "")
            )

    author = ""
    published = None
    section = ""
    if article_block is not None:
        author = _author_name(article_block.get("author"))
        published = str(article_block.get("datePublished") or "") or None

    section = _section_from_breadcrumbs(blocks)
    if not section and url:
        section = section_from_link(url)

    if paywalled:
        # Only the teaser is available — never the full text.
        body = description
        if not body:
            raise ValueError(
                "no article text found on this page (paywalled and no "
                "teaser available)"
            )
    elif not body:
        body = _ssr_body(html_text, title, description, author)

    teaser_only = paywalled or (bool(body) and body == description)
    return {
        "title": title,
        "description": description,
        "body": body,
        "author": author,
        "published": published,
        "section": section,
        "word_count": len(body.split()),
        "teaser_only": teaser_only,
        "paywalled": paywalled,
        "kind": "article",
    }


def search_items(items: list, query: str) -> list:
    """Case-insensitive substring match over title + description + author."""
    q = (query or "").strip().casefold()
    if not q:
        raise ValueError("query must not be empty")
    return [
        it for it in items
        if q in (it.get("title") or "").casefold()
        or q in (it.get("description") or "").casefold()
        or q in (it.get("author") or "").casefold()
    ]


def items_by_section(items: list, section: str) -> list:
    """Newest items whose section slug matches (exact, case-insensitive)."""
    q = validate_section(section)
    return [it for it in items if (it.get("section") or "") == q]


def items_by_author(items: list, author: str) -> list:
    """Case-insensitive substring match over the dc:creator author."""
    q = (author or "").strip().casefold()
    if not q:
        raise ValueError("author must not be empty")
    return [
        it for it in items
        if q in (it.get("author") or "").casefold()
    ]


def sections_with_counts(items: list) -> list:
    """Distinct sections in the feeds, with their story counts, most
    stories first."""
    counts: dict[str, int] = {}
    for it in items:
        name = (it.get("section") or "").strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
    return [
        {"section": name, "count": n}
        for name, n in sorted(
            counts.items(), key=lambda kv: (-kv[1], kv[0])
        )
    ]


def authors_with_counts(items: list) -> list:
    """Distinct authors in the feeds, with their story counts, most
    stories first (items without an author are skipped)."""
    counts: dict[str, int] = {}
    for it in items:
        name = (it.get("author") or "").strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
    return [
        {"author": name, "count": n}
        for name, n in sorted(
            counts.items(), key=lambda kv: (-kv[1], kv[0])
        )
    ]


def dedupe_sort(items: list) -> list:
    """De-duplicate by canonical link, newest first (empty publish
    time sorts last). The main feed and the section feeds overlap
    heavily — the same article appears in both."""
    seen: dict[str, dict] = {}
    order: list[dict] = []
    for it in items:
        if it["link"] not in seen:
            seen[it["link"]] = it
            order.append(it)
    order.sort(key=lambda it: it.get("published") or "", reverse=True)
    return order
