# -*- coding: utf-8 -*-
from .base import MyApiTestCase
from urllib.parse import urlencode, quote
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE, ACTION
import mock


class RSSTest(MyApiTestCase):

    def test_01_get_rss(self):
        with self.app.test_request_context('/info/rss',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            feeds = result.get("value")
            self.assertEqual(3, len(feeds))
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
            self.assertEqual(1, len(feeds))
            self.assertIn("Community News", feeds)
            self.assertNotIn("privacyIDEA News", feeds)
            self.assertNotIn("NetKnights News", feeds)

    def test_03_custom_rssfeeds_success(self):
        set_policy("rssfeed", scope=SCOPE.WEBUI,
                   action={ACTION.RSS_FEEDS: "'Community News':'https://community.privacyidea.org/c/news.rss'-"
                                             "'privacyIDEA News':'https://privacyidea.org/feed'"})

        with self.app.test_request_context('/info/rss', method='GET', headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            feeds = result.get("value")

            self.assertIn("Community News", feeds)
            self.assertIn("privacyIDEA News", feeds)
            self.assertNotIn("NetKnights News", feeds)
            self.assertEqual(2, len(feeds))

        delete_policy("rssfeed")

    def test_04_custom_rssfeeds_fail(self):
        # Wrong policy (wrong separator)
        action = {ACTION.RSS_FEEDS: "'Community News': 'https://community.privacyidea.org/c/news.rss', "
                                    "'privacyIDEA News':'https://privacyidea.org/feed'"}

        set_policy("rssfeed", scope=SCOPE.WEBUI, action=action)
        with mock.patch("logging.Logger.debug") as mock_log:
            with self.app.test_request_context('/info/rss',
                                               method='GET',
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                feeds = result.get("value")
                # Get the default due to faulty policy
                self.assertIn("Community News", feeds)
                self.assertIn("privacyIDEA News", feeds)
                self.assertIn("NetKnights News", feeds)
                self.assertEqual(3, len(feeds))

                expected = ("Invalid action format. The key-value pair is not separated by ':': "
                            "Community News': 'https://community.privacyidea.org/c/news.rss")
                mock_log.assert_called_with(expected)
        delete_policy("rssfeed")
