"""
This file contains the tests for the info module lib/info.py
"""

from .base import MyTestCase
from privacyidea.lib.info.rss import get_news, RSS_FEEDS


class RSSTestCase(MyTestCase):

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
