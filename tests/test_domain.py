"""Offline tests — parse the real captured faz.net RSS feeds and two
real article pages (a free NewsArticle with a real JSON-LD
articleBody, and a FAZ+ paywalled page with isAccessibleForFree=false
and NO articleBody), no network. The SSR fallback is tested with a
small synthetic page built like a real FAZ page. Fixture HTML had
FAZ's own public Google API key scrubbed to REDACTED (see AGENTS.md
fixture rule — tests never depend on key strings)."""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from faz_mcp import domain as dom
from faz_mcp import http as http_mod

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def _merged() -> list:
    main = dom.parse_rss(_read("headlines.xml"))
    return dom.dedupe_sort(main["items"])


# Free page with NO articleBody — the SSR <article> paragraphs are
# the fallback; the "Zusammenfassung" heading, the caption+teaser
# paragraph and the FAZ+ promo must be filtered out.
_SSR_ONLY_HTML = """<!DOCTYPE html><html><head><title>Test: Nur SSR | FAZ.NET</title>
<meta property="og:description" content="Kurzer Teaser über den Test.">
<script type="application/ld+json">{"@context": "https://schema.org",
"@type": "NewsArticle", "headline": "Test: Nur SSR",
"description": "Kurzer Teaser über den Test.",
"isAccessibleForFree": true,
"author": {"@type": "Person", "name": "Erika Muster"},
"datePublished": "2026-11-27T09:00:00Z"}
</script>
<script type="application/ld+json">{"@context": "https://schema.org",
"@type": "BreadcrumbList", "itemListElement": [
{"@type": "ListItem", "position": 1, "name": "FAZ.NET"},
{"@type": "ListItem", "position": 2, "name": "Politik"},
{"@type": "ListItem", "position": 3, "name": "Test: Nur SSR"}]}
</script>
</head><body><article>
<p>Zusammenfassung</p>
<p>Erika Muster, Testautorin, im November in Berlin dpaKurzer Teaser über den Test.</p>
<p>Erster Absatz des Artikels mit echtem Inhalt.</p>
<p>Zweiter Absatz des Artikels mit echtem Inhalt.</p>
<p>Zugang zu allen FAZ+ Beiträgen (Originalpreis: 13,80&nbsp;€) jetzt nur 0,99&nbsp;€</p>
<p>Die F.A.Z. berichtet frei von externen Einflüssen</p>
</article></body></html>"""

# Video page, synthetic — a VideoObject block and no NewsArticle.
_VIDEO_HTML = """<!DOCTYPE html><html><head><title>Test: Video | FAZ.NET</title>
<meta property="og:description" content="Kurze Videobeschreibung.">
<script type="application/ld+json">{"@context": "https://schema.org",
"@type": "VideoObject", "name": "Test: Video",
"description": "Kurze Videobeschreibung.",
"uploadDate": "2026-11-27T08:00:00Z", "duration": "PT2M13S"}
</script>
</head><body><article><p>Kurze Videobeschreibung.</p></article>
</body></html>"""


class TestMainFeed:
    def test_main_shape(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        assert parsed["feed_title"] == "Aktuell - FAZ.NET"
        assert parsed["count"] == 169
        assert len(parsed["items"]) == 169

    def test_main_first_item(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        first = parsed["items"][0]
        assert first["title"] == (
            "Parteitag in Dresden: „Ob ich im BSW bleibe, wird sich "
            "auf dem Parteitag entscheiden“"
        )
        assert first["link"] == (
            "https://www.faz.net/aktuell/politik/inland/"
            "bsw-parteitag-streit-ueber-zusammenarbeit-mit-afd-"
            "accg-201721261.html"
        )
        assert first["description"].startswith(
            "Auf einem Bundesparteitag in Dresden berät das BSW"
        )
        assert first["published"] == "2026-11-27T09:58:08+00:00"
        assert first["author"] == "Stephan Klenner, Dresden"
        assert first["section"] == "politik"
        assert first["kind"] == "article"
        assert first["image_url"] == (
            "https://media0.faz.net/image/514207f8116a/"
            "w3000h1687x0y2/202601/43601.0.1697382717/"
            "josephine-thyret-ko.webp"
        )

    def test_main_items_all_have_title_description_image(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        assert all(i["title"] and i["description"] for i in parsed["items"])
        assert all(i["image_url"] for i in parsed["items"])
        assert all(
            i["link"].startswith("https://www.faz.net/")
            for i in parsed["items"]
        )

    def test_main_feed_mixes_kinds(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        kinds = {i["kind"] for i in parsed["items"]}
        assert kinds == {"article", "video", "podcast"}
        assert sum(1 for i in parsed["items"] if i["kind"] == "video") == 3
        assert sum(1 for i in parsed["items"] if i["kind"] == "podcast") == 3

    def test_main_feed_has_premium_links(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        premium = [
            i for i in parsed["items"] if i["link"].startswith(
                "https://www.faz.net/premium/"
            )
        ]
        assert len(premium) == 4
        assert all(i["kind"] == "article" for i in premium)


class TestSectionFeed:
    def test_politik_shape(self):
        parsed = dom.parse_rss(_read("section-politik.xml"))
        assert parsed["feed_title"] == "Politik - FAZ.NET"
        assert parsed["count"] == 46
        assert len(parsed["items"]) == 46

    def test_politik_first_item_matches_main_feed(self):
        parsed = dom.parse_rss(_read("section-politik.xml"))
        main = dom.parse_rss(_read("headlines.xml"))
        assert parsed["items"][0]["link"] == main["items"][0]["link"]
        assert all(i["section"] == "politik" for i in parsed["items"])


class TestArticle:
    def test_free_article(self):
        art = dom.parse_article(_read("article-free.html"))
        assert art["kind"] == "article"
        assert art["title"] == (
            "BSW-Parteitag: Streit über Zusammenarbeit mit AfD"
        )
        assert art["author"] == "Stephan Klenner"
        assert art["published"] == "2026-11-27T09:58:08Z"
        # Section comes from the BreadcrumbList (positions 2..).
        assert art["section"] == "Politik > Inland"
        assert art["word_count"] == 642
        assert art["paywalled"] is False
        assert art["teaser_only"] is False

    def test_free_article_body_is_json_ld(self):
        # faz.net pages DO carry a real JSON-LD articleBody — it is
        # the body (the SSR <article> paragraphs are only the
        # fallback).
        art = dom.parse_article(_read("article-free.html"))
        assert art["body"].startswith(
            "Überschattet von Streit über die Zusammenarbeit mit der AfD"
        )
        assert "Die Gruppe um die früheren Linkspartei" in art["body"]
        assert art["description"].startswith(
            "Auf einem Bundesparteitag in Dresden berät das BSW"
        )

    def test_free_article_body_has_no_caption_or_promo(self):
        art = dom.parse_article(_read("article-free.html"))
        assert "Zusammenfassung" not in art["body"]
        assert "Zugang zu allen FAZ+ Beiträgen" not in art["body"]

    def test_paywalled_article_returns_teaser_only(self):
        # Real FAZ+ page: isAccessibleForFree=false, NO articleBody.
        art = dom.parse_article(_read("article-paywalled.html"))
        assert art["kind"] == "article"
        assert art["title"] == (
            "„Die fetten Jahre sind vorbei“: Hans-Werner Sinn über "
            "die Zukunft Deutschlands"
        )
        assert art["author"] == "Alexander Armbruster"
        assert art["published"] == "2026-11-26T09:07:10Z"
        assert art["section"] == "Wirtschaft"
        assert art["paywalled"] is True
        assert art["teaser_only"] is True
        # Only the teaser is exposed — never the full text.
        assert art["body"] == art["description"]
        assert art["word_count"] == 31
        assert "Abonnenten" not in art["body"]
        assert "Zugang zu allen FAZ+ Beiträgen" not in art["body"]

    def test_ssr_fallback_filters_caption_promo_footer(self):
        art = dom.parse_article(_SSR_ONLY_HTML)
        assert art["paywalled"] is False
        assert art["author"] == "Erika Muster"
        assert art["section"] == "Politik"
        assert "Zusammenfassung" not in art["body"]
        assert "Zugang zu allen FAZ+ Beiträgen" not in art["body"]
        assert "Die F.A.Z. berichtet frei" not in art["body"]
        assert "dpaKurzer Teaser" not in art["body"]
        assert art["body"] == (
            "Erster Absatz des Artikels mit echtem Inhalt.\n\n"
            "Zweiter Absatz des Artikels mit echtem Inhalt."
        )

    def test_video_page_returns_description_only(self):
        art = dom.parse_article(_VIDEO_HTML)
        assert art["kind"] == "video"
        assert art["title"] == "Test: Video"
        assert art["published"] == "2026-11-27T08:00:00Z"
        assert art["section"] == "video"
        assert art["body"] == "Kurze Videobeschreibung."
        assert art["teaser_only"] is True
        assert art["paywalled"] is False
        assert art["duration"] == "PT2M13S"


class TestValidators:
    def test_limit(self):
        assert dom.validate_limit(1) == 1
        assert dom.validate_limit(50) == 50
        with pytest.raises(ValueError):
            dom.validate_limit(0)
        with pytest.raises(ValueError):
            dom.validate_limit(51)

    def test_section(self):
        assert dom.validate_section("Politik") == "politik"
        assert dom.validate_section("rhein-main") == "rhein-main"
        with pytest.raises(ValueError):
            dom.validate_section("kultur")
        with pytest.raises(ValueError):
            dom.validate_section("")


class TestSearchSectionAuthorAndDedupe:
    def test_search_items(self):
        merged = _merged()
        found = dom.search_items(merged, "Rente")
        assert len(found) == 8
        assert dom.search_items(merged, "RENTE") == found
        assert len(dom.search_items(merged, "Klenner")) == 1
        assert dom.search_items(merged, "NiemandXYZ") == []
        with pytest.raises(ValueError):
            dom.search_items(merged, "   ")

    def test_items_by_section(self):
        merged = _merged()
        assert len(dom.items_by_section(merged, "politik")) == 14
        assert len(dom.items_by_section(merged, "wirtschaft")) == 35
        assert dom.items_by_section(merged, "WIRTSCHAFT") == (
            dom.items_by_section(merged, "wirtschaft")
        )
        with pytest.raises(ValueError):
            dom.items_by_section(merged, "kultur")

    def test_items_by_author(self):
        merged = _merged()
        assert len(dom.items_by_author(merged, "Klenner")) == 1
        assert len(dom.items_by_author(merged, "klenner")) == 1
        assert dom.items_by_author(merged, "NiemandXYZ") == []
        with pytest.raises(ValueError):
            dom.items_by_author(merged, "   ")

    def test_sections_with_counts(self):
        merged = _merged()
        sections = dom.sections_with_counts(merged)
        assert sections[0] == {"section": "wirtschaft", "count": 35}
        assert {"section": "politik", "count": 14} in sections
        counts = [s["count"] for s in sections]
        assert counts == sorted(counts, reverse=True)

    def test_authors_with_counts(self):
        merged = _merged()
        authors = dom.authors_with_counts(merged)
        assert authors[0] == {"author": "Katrin Hummel", "count": 4}
        counts = [a["count"] for a in authors]
        assert counts == sorted(counts, reverse=True)

    def test_dedupe_sort(self):
        merged = _merged()
        doubled = merged + merged[:5]
        out = dom.dedupe_sort(doubled)
        assert len(out) == 169
        pubs = [i["published"] for i in out]
        assert pubs == sorted(pubs, reverse=True)

    def test_section_from_link(self):
        assert dom.section_from_link(
            "https://www.faz.net/aktuell/politik/inland/x-1.html"
        ) == "politik"
        assert dom.section_from_link(
            "https://www.faz.net/premium/einspruch/exklusiv/x-1.html"
        ) == "einspruch"
        assert dom.section_from_link(
            "https://www.faz.net/video/x-1.html"
        ) == "video"
        assert dom.kind_from_link(
            "https://www.faz.net/podcasts/x-1.html"
        ) == "podcast"


class TestFeedGuards:
    def test_parse_rss_rejects_garbage(self):
        with pytest.raises(ValueError):
            dom.parse_rss("<html><body>not rss</body></html>")

    def test_fetch_article_refuses_feed_urls(self):
        with pytest.raises(http_mod.FazError):
            http_mod.fetch_article("https://www.faz.net/rss/aktuell/")
        with pytest.raises(http_mod.FazError):
            http_mod.fetch_article("https://www.faz.net/rss/aktuell/politik/")
        with pytest.raises(http_mod.FazError):
            http_mod.fetch_article("https://www.faz.net/")

    def test_fetch_article_refuses_other_hosts(self):
        with pytest.raises(http_mod.FazError):
            http_mod.fetch_article(
                "https://www.spiegel.de/politik/deutschland/afd-100.html"
            )
        with pytest.raises(http_mod.FazError):
            http_mod.fetch_article(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )

    def test_fetch_feed_refuses_non_feed_urls(self):
        with pytest.raises(http_mod.FazError):
            http_mod.fetch_feed("https://www.faz.net/aktuell/")
        with pytest.raises(http_mod.FazError):
            http_mod.fetch_feed("https://www.faz.net/rss/politik/")
        with pytest.raises(http_mod.FazError):
            http_mod.fetch_feed("https://www.faz.net/rss/aktuell/kultur/")
        with pytest.raises(http_mod.FazError):
            http_mod.fetch_feed(
                "https://www.faz.net/aktuell/politik/inland/x-1.html"
            )


class TestServerEnvelope:
    def test_tools_return_json_envelope(self):
        # Offline: the tools hit the network, so only the error path
        # is exercised here — but the envelope shape is the same.
        from faz_mcp import server as srv

        out = json.loads(srv.faz_latest(51))
        assert "error" in out
        assert out["source"] == "faz.net"
        assert "fetched_at" in out
