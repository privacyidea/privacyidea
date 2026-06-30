"""
This file contains the tests for the info module lib/info.py
"""

from unittest.mock import patch

from .base import MyTestCase
from privacyidea.lib.info.rss import get_news, invalidate_news_cache, RSS_FEEDS


class RSSTestCase(MyTestCase):

    def setUp(self):
        invalidate_news_cache()

    def test_01_check_definition(self):
        self.assertIn("Community News", RSS_FEEDS)
        self.assertIn("privacyIDEA News", RSS_FEEDS)
        self.assertIn("NetKnights News", RSS_FEEDS)

    def test_01_fetch_news(self):
        r = get_news()
        # Check, that we can fetch the three basic news feeds
        self.assertIn("Community News", r)
        self.assertIn("privacyIDEA News", r)
        self.assertIn("NetKnights News", r)

    def test_02_arbitrary_news(self):
        r = get_news({"Heise": "https://www.heise.de/newsticker/heise.rdf"})
        self.assertIn("Heise", r)

    def test_03_fail_fetching(self):
        r = get_news({"Broken": "https://netknights.it"})
        self.assertIn("Broken", r)
        # Since it is broken, it has an empty list.
        self.assertEqual(r.get("Broken"), [])


class _FakeFeed:
    def __init__(self, entries=None):
        self.entries = entries or []


class RSSCacheTestCase(MyTestCase):
    """The cache lives in a module-level dict; each test starts fresh."""

    def setUp(self):
        invalidate_news_cache()

    def test_second_call_hits_cache(self):
        with patch("privacyidea.lib.info.rss.feedparser.parse",
                   return_value=_FakeFeed()) as fp:
            get_news({"X": "http://example/feed"})
            get_news({"X": "http://example/feed"})
        self.assertEqual(fp.call_count, 1)

    def test_different_args_bypass_cache(self):
        # Different feed dict, channel, or days => separate cache key.
        with patch("privacyidea.lib.info.rss.feedparser.parse",
                   return_value=_FakeFeed()) as fp:
            get_news({"X": "http://example/feed"}, days=30)
            get_news({"X": "http://example/feed"}, days=60)
            get_news({"Y": "http://other/feed"}, days=30)
        self.assertEqual(fp.call_count, 3)

    def test_invalidate_forces_refetch(self):
        with patch("privacyidea.lib.info.rss.feedparser.parse",
                   return_value=_FakeFeed()) as fp:
            get_news({"X": "http://example/feed"})
            invalidate_news_cache()
            get_news({"X": "http://example/feed"})
        self.assertEqual(fp.call_count, 2)

    def test_ttl_expiry_refetches(self):
        # Simulate the cache being older than the TTL by patching time.monotonic.
        from privacyidea.lib.info import rss as rss_mod
        with (patch("privacyidea.lib.info.rss.feedparser.parse",
                    return_value=_FakeFeed()) as fp,
              patch("privacyidea.lib.info.rss.time.monotonic") as mono):
            mono.return_value = 1000.0
            get_news({"X": "http://example/feed"})
            mono.return_value = 1000.0 + rss_mod._CACHE_TTL_SECONDS + 1
            get_news({"X": "http://example/feed"})
        self.assertEqual(fp.call_count, 2)
