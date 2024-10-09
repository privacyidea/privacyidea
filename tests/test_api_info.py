# -*- coding: utf-8 -*-
from .base import MyApiTestCase
from urllib.parse import urlencode, quote


class RSSTest(MyApiTestCase):

    def test_01_get_rss(self):
        with self.app.test_request_context('/info/rss',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            feeds = result.get("value")
            # we have two tokens
            self.assertEqual(len(feeds), 3)
            self.assertIn("Community News", feeds)
            self.assertIn("privacyIDEA News", feeds)
            self.assertIn("NetKnights News", feeds)

    def test_02_get_specific_rss(self):
        with self.app.test_request_context('/info/rss',
                                           method='GET',
                                           query_string=urlencode({"channel": "Community News"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            feeds = result.get("value")
            # we have two tokens
            self.assertEqual(len(feeds), 1)
            self.assertIn("Community News", feeds)
            self.assertNotIn("privacyIDEA News", feeds)
            self.assertNotIn("NetKnights News", feeds)
