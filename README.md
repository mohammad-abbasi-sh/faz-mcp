# faz-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/faz-mcp

Unofficial **read-only** MCP server for **[FAZ.NET — Frankfurter Allgemeine Zeitung](https://www.faz.net)** — one of Germany's biggest quality daily newspapers (founded 1949) — via its official RSS feeds (the main feed /rss/aktuell/, 169 items, plus 11 per-section feeds) and article pages, whose full text is read from the JSON-LD NewsArticle `articleBody` (the server-rendered `<article>` paragraphs are the fallback). Latest news, keyword search, stories by section and by author, the sections in today's feed, and full article text. No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory". Not affiliated with FAZ.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "faz": {
      "command": "uvx",
      "args": ["faz-mcp==0.1.0"]
    }
  }
}
```

Or run locally: `python -m faz_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `faz_latest` | Latest FAZ news (the official main RSS feed, ~169 items), newest first — `limit` 1..50. Every item carries a title, a per-article link, a teaser, author (dc:creator, when the feed carries one), section, kind (article/video/podcast), an image URL and publish time |
| `faz_search_news` | Search FAZ news by keyword (title + teaser + author) across the official main RSS feed — `query` (e.g. "Rente" or "Klimaschutz"), `limit` 1..50 |
| `faz_by_section` | Newest FAZ stories from one section feed — `section`: politik, wirtschaft, sport, feuilleton, finanzen, gesellschaft, wissen, besser-leben, rhein-main, karriere-hochschule, technik-motor; `limit` 1..50 |
| `faz_sections` | The sections in today's FAZ main feed, with how many stories each carries — most stories first |
| `faz_by_author` | Newest FAZ stories by one author (the feed's dc:creator, e.g. "Stephan Klenner" — matched case-insensitively as a substring, so a surname is enough) — `limit` 1..50 |
| `faz_get_article` | Full text of one FAZ article page (JSON-LD NewsArticle `articleBody`, `<article>` paragraphs as fallback) — `url`: a faz.net article URL (/aktuell/<section>/…-<id>.html). Returns title, author, publish time, the section from the page's BreadcrumbList (e.g. "Politik > Inland"), body text and word count. A FAZ+ page returns `paywalled: true` with only the teaser as body — the full text needs a subscription. A video page returns `kind: "video"` with its description and duration. Feed URLs, the home page and off-site links are refused |
| `faz_health` | Reachability probe (ok / blocked / error) — one polite request |

Example output (`faz_latest`, `limit` 1):

```json
{"feed_title": "Aktuell - FAZ.NET", "total_results": 169, "count": 1,
 "items": [
  {"title": "Parteitag in Dresden: „Ob ich im BSW bleibe, wird sich auf dem Parteitag entscheiden“",
   "link": "https://www.faz.net/aktuell/politik/inland/bsw-parteitag-streit-ueber-zusammenarbeit-mit-afd-accg-201721261.html",
   "description": "Auf einem Bundesparteitag in Dresden berät das BSW über seinen künftigen Kurs. Über den Umgang mit der AfD ist ein heftiger Streit entbrannt.",
   "published": "2026-11-27T09:58:08+00:00", "author": "Stephan Klenner, Dresden",
   "section": "politik", "kind": "article",
   "image_url": "https://media0.faz.net/image/514207f8116a/w3000h1687x0y2/202601/43601.0.1697382717/josephine-thyret-ko.webp"},
  ...]}
```

Notes:
- The server reads the official **main RSS feed** — `https://www.faz.net/rss/aktuell/` (169 items, verified live 2026-11-27) — plus **11 per-section feeds** under `/rss/aktuell/<section>/` (politik 46, wirtschaft, sport, feuilleton, finanzen, gesellschaft, wissen, besser-leben, rhein-main, karriere-hochschule, technik-motor). `/rss/<section>/` (without /aktuell/) all 404, and `/rss/aktuell/kultur/` 404 — those 12 are the only feeds. The main feed and the section feeds overlap heavily; items are de-duplicated by canonical link.
- **No topic tags:** the feeds carry no `<category>` values, so there is no topic tool — stories are grouped by section instead (derived from the article link path, e.g. `/aktuell/politik/…`). `faz_by_section` reads that section's own feed.
- The main feed carries `dc:creator` on ~83% of items (141/169) and a `media:content` image (webp) on every item. The real author of one article is reported by `faz_get_article` from the JSON-LD author (e.g. "Stephan Klenner"). Feed `pubDate`s are GMT.
- The main feed mixes kinds: 163 articles, 3 videos (`/video/…`) and 3 podcasts (`/podcasts/…`) — returned as-is with `kind` set, never fetched by `faz_latest`. It also carries 4 FAZ+ articles (`/premium/…` links); their paywall status is only known from the article page.
- Feed links end `-<id>.html` and 301 to the canonical URL (followed automatically).
- **Article text, honestly:** FAZ pages DO carry a real JSON-LD `articleBody` (sampled: 4,971 characters / 642 words on a free article). The body is whitespace-normalised; the `<article>` `<p>` tags are the fallback when `articleBody` is absent (the "Zusammenfassung" heading, the caption+teaser paragraph, photo captions "Foto:", the "Zugang zu allen FAZ+ Beiträgen" subscription promo, the "Die F.A.Z. berichtet frei…" footer and byline fragments are filtered).
- **Paywall, honestly (verified live):** a FAZ+ opinion article carries `isAccessibleForFree: false` and NO `articleBody` — `faz_get_article` returns `paywalled: true` with only the teaser as body (31 words sampled), never fabricated text. The SSR `<article>` of a paywalled page holds only a partial teaser plus the subscription promo — it is never used as body.
- **Video pages, honestly:** a `/video/…` page carries a JSON-LD `VideoObject` and no `NewsArticle` — `faz_get_article` returns `kind: "video"` with the description as body and its duration, never fabricated text.
- Data: FAZ.NET public RSS feeds and article pages — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parses the two real captured feeds (main + politik section) plus two real article pages (a free article with a real JSON-LD `articleBody`, and a real FAZ+ paywalled page); the SSR fallback and the video branch use small synthetic pages
- `tests/test_live.py` — cautious live requests against faz.net

Tests: 34/34 green (27 offline + 7 live, 2026-11-27).

## License

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — free for personal and non-commercial use; commercial use needs a separate license (see LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
