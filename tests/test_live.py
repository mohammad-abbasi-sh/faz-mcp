"""Live tests — hit the real faz.net RSS feeds and article pages.
Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set FAZ_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from faz_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("FAZ_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="FAZ_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_latest_live(self):
        out = json.loads(srv.faz_latest(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["description"] for i in out["items"]))
        self.assertTrue(all(i["image_url"] for i in out["items"]))
        print(f"\nLIVE latest: {out['count']} items, first: {out['items'][0]['title']}")

    def test_search_live(self):
        out = json.loads(srv.faz_search_news("Rente", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        print(f"\nLIVE search 'Rente': {out['total_results']} hits")

    def test_by_section_live(self):
        out = json.loads(srv.faz_by_section("politik", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["section"] == "politik" for i in out["items"]))
        print(f"\nLIVE by_section politik: {out['count']} items")

    def test_sections_live(self):
        out = json.loads(srv.faz_sections())
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 5)
        self.assertTrue(all(s["count"] >= 1 for s in out["sections"]))
        print(f"\nLIVE sections: {out['count']} sections")

    def test_by_author_live(self):
        head = json.loads(srv.faz_latest(limit=50))
        self.assertNotIn("error", head)
        authors = [i["author"] for i in head["items"] if i["author"]]
        self.assertTrue(authors)
        author = authors[0].split(",")[0]
        out = json.loads(srv.faz_by_author(author, limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(author.casefold() in i["author"].casefold()
                            for i in out["items"]))
        print(f"\nLIVE by_author {author!r}: {out['count']} items")

    def test_get_article_live(self):
        head = json.loads(srv.faz_latest(limit=10))
        self.assertNotIn("error", head)
        # First free article in the feed (skip video/podcast items).
        url = next(i["link"] for i in head["items"] if i["kind"] == "article")
        out = json.loads(srv.faz_get_article(url))
        self.assertNotIn("error", out)
        self.assertEqual(out["url"], url)
        self.assertTrue(out["section"])
        if not out["paywalled"]:
            self.assertGreater(out["word_count"], 100)
        print(
            f"\nLIVE article: {out['title']!r} — {out['word_count']} words, "
            f"section {out['section']!r}, paywalled={out['paywalled']}"
        )

    def test_health_live(self):
        out = json.loads(srv.faz_health())
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["http_status"], 200)
        print(f"\nLIVE health: {out}")
