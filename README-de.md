# faz-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/faz-mcp

Inoffizieller **schreibgeschützter** MCP-Server für **[FAZ.NET — Frankfurter Allgemeine Zeitung](https://www.faz.net)** — eine der größten deutschen Qualitätszeitungen (gegründet 1949) — über die offiziellen RSS-Feeds (den Hauptfeed /rss/aktuell/, 169 Einträge, plus 11 Ressort-Feeds) und Artikelseiten, deren Volltext aus dem JSON-LD-NewsArticle-`articleBody` gelesen wird (die serverseitig gerenderten `<article>`-Absätze sind der Fallback). Neueste Meldungen, Stichwortsuche, Artikel nach Ressort und nach Autor:in, die Ressorts des heutigen Feeds und Volltexte. Kein Schlüssel, kein Login.

> Gebaut von Mohammad Abbasi im Rahmen der „Germany MCP factory". Nicht mit der FAZ verbunden.

## Für KI-Agenten

In die MCP-Client-Konfiguration eintragen (stdio):

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

Oder lokal starten: `python -m faz_mcp.server` (benötigt `mcp<2`, `httpx`).

## Werkzeuge

| Werkzeug | Beschreibung |
|------|-------------|
| `faz_latest` | Neueste FAZ-Meldungen (der offizielle Haupt-RSS-Feed, ~169 Einträge), neueste zuerst — `limit` 1..50. Jeder Eintrag hat Titel, Artikel-Link, Teaser, Autor:in (dc:creator, sofern der Feed sie trägt), Ressort, Art (article/video/podcast), Bild-URL und Veröffentlichungszeit |
| `faz_search_news` | Stichwortsuche in den FAZ-Meldungen (Titel + Teaser + Autor:in) über den offiziellen Haupt-RSS-Feed — `query` (z. B. "Rente" oder "Klimaschutz"), `limit` 1..50 |
| `faz_by_section` | Neueste FAZ-Meldungen aus einem Ressort-Feed — `section`: politik, wirtschaft, sport, feuilleton, finanzen, gesellschaft, wissen, besser-leben, rhein-main, karriere-hochschule, technik-motor; `limit` 1..50 |
| `faz_sections` | Die Ressorts des heutigen FAZ-Hauptfeeds mit der Anzahl der Artikel je Ressort — häufigste zuerst |
| `faz_by_author` | Neueste FAZ-Meldungen einer Autor:in (dc:creator des Feeds, z. B. "Stephan Klenner" — als Teilstring ohne Beachtung von Groß-/Kleinschreibung verglichen, ein Nachname reicht) — `limit` 1..50 |
| `faz_get_article` | Volltext einer FAZ-Artikelseite (JSON-LD-NewsArticle-`articleBody`, `<article>`-Absätze als Fallback) — `url`: eine faz.net-Artikel-URL (/aktuell/<section>/…-<id>.html). Gibt Titel, Autor:in, Veröffentlichungszeit, das Ressort aus der BreadcrumbList der Seite (z. B. "Politik > Inland"), Text und Wortzahl zurück. Eine FAZ+-Seite gibt `paywalled: true` mit nur dem Teaser als Text zurück — der Volltext braucht ein Abo. Eine Videoseite gibt `kind: "video"` mit Beschreibung und Dauer zurück. Feed-URLs, die Startseite und externe Links werden abgelehnt |
| `faz_health` | Erreichbarkeitsprüfung (ok / blocked / error) — eine höfliche Anfrage |

Beispielausgabe (`faz_latest`, `limit` 1):

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

Hinweise:
- Der Server liest den offiziellen **Haupt-RSS-Feed** — `https://www.faz.net/rss/aktuell/` (169 Einträge, live verifiziert 2026-11-27) — plus **11 Ressort-Feeds** unter `/rss/aktuell/<section>/` (politik 46, wirtschaft, sport, feuilleton, finanzen, gesellschaft, wissen, besser-leben, rhein-main, karriere-hochschule, technik-motor). `/rss/<section>/` (ohne /aktuell/) geben alle 404 zurück, ebenso `/rss/aktuell/kultur/` — diese 12 sind die einzigen Feeds. Hauptfeed und Ressort-Feeds überschneiden sich stark; Einträge werden per kanonischem Link dedupliziert.
- **Keine Themen-Tags:** Die Feeds enthalten keine `<category>`-Werte, daher gibt es kein Themen-Werkzeug — Artikel werden stattdessen nach Ressort gruppiert (aus dem Artikel-Linkpfad abgeleitet, z. B. `/aktuell/politik/…`). `faz_by_section` liest den jeweiligen Ressort-Feed.
- Der Hauptfeed enthält `dc:creator` bei ~83 % der Einträge (141/169) und bei jedem Eintrag ein `media:content`-Bild (webp). Die echte Autor:in eines Artikels meldet `faz_get_article` aus dem JSON-LD-Autor (z. B. "Stephan Klenner"). Die `pubDate`s des Feeds sind GMT.
- Der Hauptfeed mischt Arten: 163 Artikel, 3 Videos (`/video/…`) und 3 Podcasts (`/podcasts/…`) — sie werden unverändert mit gesetztem `kind` zurückgegeben und von `faz_latest` nie abgerufen. Außerdem enthält er 4 FAZ+-Artikel (`/premium/…`-Links); ihr Paywall-Status ist erst auf der Artikelseite bekannt.
- Feed-Links enden auf `-<id>.html` und leiten per 301 auf die kanonische URL weiter (wird automatisch gefolgt).
- **Artikeltext, ehrlich:** FAZ-Seiten enthalten DOCH einen echten JSON-LD-`articleBody` (Stichprobe: 4.971 Zeichen / 642 Wörter bei einem kostenlosen Artikel). Der Text wird whitespace-normalisiert; die `<article>`-`<p>`-Tags sind der Fallback, wenn `articleBody` fehlt (die Überschrift "Zusammenfassung", der Bildunterschrift+Teaser-Absatz, Bildunterschriften "Foto:", die Abo-Werbung "Zugang zu allen FAZ+ Beiträgen", die Fußzeile "Die F.A.Z. berichtet frei…" und Byline-Fragmente werden gefiltert).
- **Paywall, ehrlich (live verifiziert):** Ein FAZ+-Meinungsartikel trägt `isAccessibleForFree: false` und KEINEN `articleBody` — `faz_get_article` gibt `paywalled: true` mit nur dem Teaser als Text zurück (31 Wörter in der Stichprobe), niemals erfundenen Text. Das SSR-`<article>` einer Bezahlseite enthält nur einen Teil-Teaser plus Abo-Werbung — es wird nie als Text verwendet.
- **Videoseiten, ehrlich:** Eine `/video/…`-Seite trägt ein JSON-LD-`VideoObject` und keinen `NewsArticle` — `faz_get_article` gibt `kind: "video"` mit der Beschreibung als Text und der Dauer zurück, niemals erfundenen Text.
- Daten: öffentliche RSS-Feeds und Artikelseiten von FAZ.NET — kein Schlüssel, kein Login, nur lesend.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parst die beiden echten, aufgezeichneten Feeds (Hauptfeed + Ressort-Feed Politik) plus zwei echte Artikelseiten (ein kostenloser Artikel mit echtem JSON-LD-`articleBody` und eine echte FAZ+-Bezahlseite); der SSR-Fallback und der Video-Zweig nutzen kleine synthetische Seiten
- `tests/test_live.py` — vorsichtige Live-Anfragen an faz.net

Tests: 34/34 grün (27 offline + 7 live, 2026-11-27).

## Lizenz

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — kostenlos für persönliche und nicht-kommerzielle Nutzung; kommerzielle Nutzung braucht eine separate Lizenz (siehe LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
