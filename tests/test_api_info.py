# -*- coding: utf-8 -*-
from .base import MyApiTestCase


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

