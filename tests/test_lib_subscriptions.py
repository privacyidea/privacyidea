"""
This test file tests the lib.subscriptions.py
"""
import time
from datetime import datetime, timedelta

from unittest import mock
import requests

from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.subscriptions import (save_subscription,
                                           delete_subscription,
                                           get_subscription,
                                           get_users_with_active_tokens,
                                           raise_exception_probability,
                                           check_subscription,
                                           check_signature,
                                           SubscriptionError,
                                           subscription_status,
                                           _USER_COUNT_KEY,
                                           _count_interval_seconds,
                                           _users_with_active_tokens_for_check,
                                           get_plugin_subscription_status,
                                           get_server_subscription_status,
                                           get_metered_application,
                                           get_subscription_owner,
                                           get_latest_github_versions,
                                           invalidate_github_version_cache,
                                           version_sort_key,
                                           _subscription_state,
                                           SubscriptionState,
                                           EXPIRING_THRESHOLD_DAYS,
                                           APPLICATIONS,
                                           DASHBOARD_PLUGINS)
from privacyidea.lib.integrations import AGENT_TO_INTEGRATION
from privacyidea.lib import subscriptions as subscriptions_module
from privacyidea.lib.token import init_token, enable_token, remove_token
from privacyidea.lib.user import User
from privacyidea.models import ClientApplication, Subscription, db
from .base import MyTestCase

# 100 users
SUBSCRIPTION1 = {'by_address': 'Ludwig-Erhard-Str. 12 / Kassel / Germany', 'for_email': 'info@netknights.it',
                 'for_address': ' / Kassel / DE', 'level': 'privacyIDEA Small Business SLA',
                 'for_url': 'http://www.netknights.it', 'date_from': '2026-10-22',
                 'by_url': 'https://support.netknights.it', 'for_phone': 'N/A',
                 'by_email': 'support@netknights.it', 'date_till': '2036-10-22', 'num_users': 100,
                 'application': 'privacyIDEA', 'num_tokens': 100, 'num_clients': 100,
                 'signature': '17941919867303932473076578692591320079191278600840328030609490140912890567352866586574099288334373876078015088947172703645433569126285716638755912171557916764779693512704791308228840892846219470297828198685890145453826588590039520429254723841015944401545021512255965528170081174094262301069011479397754147196147954233139895730486539807542148785452626834760093112183027619887337519667566729507778070026018471420381397016520449392019404081500337138254143685673819349833808720501902957519069636726831580915586862012619330027529658275576879903357992223930621716314003698362410254059102899535512731575596834038158666058466',
                 'for_name': 'Dummy Customer', 'by_phone': 'N/A', 'for_comment': 'Unittest',
                 'by_name': 'NetKnights GmbH'}
# 200 users
SUBSCRIPTION2 = {'by_address': 'Ludwig-Erhard-Str. 12 / Kassel / Germany', 'for_email': 'info@netknights.it',
                 'for_address': ' / Kassel / DE', 'level': 'privacyIDEA Enterprise SLA',
                 'for_url': 'http://www.netknights.it', 'date_from': '2026-10-22',
                 'by_url': 'https://support.netknights.it', 'for_phone': 'N/A', 'by_email': 'support@netknights.it',
                 'date_till': '2036-10-22', 'num_users': 200, 'application': 'privacyIDEA', 'num_tokens': 200,
                 'num_clients': 200, 'signature': '22375418200541525807209673839667698318126357301896492039309902382963344248297077135092198834370501925689262450980454561118656684868660568861363185332565341554730744219489786638033806806576825042404082739826450593645634853514773200439957663144989075851522058208475627424209422685218277476979108881289516188691942693039221710538565485294282898253133757282393996541642530095181393216301340342018163700733009074878123686308729260759892610731267268275242548112086632485924244912331374075300502286205321027376835924454640822679945630204411283271106090441558625405310407883962530803842035375522607490583851817448907015096874',
                 'for_name': 'Dummy Customer', 'by_phone': '+49 561 9979 15 47', 'for_comment': 'Unittest',
                 'by_name': 'NetKnights GmbH'}
# expired
SUBSCRIPTION3 = {'by_address': 'provider-address', 'for_email': 'customer@example.com', 'num_tokens': 100,
                 'num_users': 100, 'level': 'Gold', 'for_comment': 'comment', 'date_from': '2015-10-22',
                 'for_address': 'customer-address',
                 'signature': '25407205465585578473052448351020802985222256541982387080470368702502395978929370244545432262489841701057444597515172775368305952894314763774108360927487838769161883939606658203871498172390640846806985487570176937817917267265370004247183037988076793238258268672447434743336052806908752658001766448386518941839874145101365174694427138442671647817496746983715439351013662042962255755683132569592229281599938902003341163052295582849710694963121233074090316812533101113257642365156343454293877847023436035373453938687754858064544899533624458220595546766026278380731783279327943668257725383564250176186223252875047051351456',  # noqa: E501
                 'for_phone': '12345', 'by_email': 'provider@example.com', 'date_till': '2015-10-23',
                 'by_name': 'NetKnights GmbH', 'application': 'demo_application', 'by_url': 'http://provider',
                 'for_name': 'customer', 'by_phone': '12345', 'for_url': 'http://customer', 'num_clients': 100}
# to 10 users
SUBSCRIPTION4 = {'by_address': 'Ludwig-Erhard-Str. 12 / Kassel / Germany', 'for_email': 'info@netknights.it',
                 'for_address': ' / Kassel / DE', 'level': 'privacyIDEA Small Business SLA',
                 'for_url': 'http://www.netknights.it', 'date_from': '2026-10-22',
                 'by_url': 'https://support.netknights.it', 'for_phone': 'N/A',
                 'by_email': 'support@netknights.it', 'date_till': '2036-10-22', 'num_users': 10,
                 'application': 'privacyIDEA', 'num_tokens': 10, 'num_clients': 10,
                 'signature': '372419503710461285591842418538761559282413229240720090557923804849100327490030827850375196139230113552116202922029981331597920712394735102466193468010812554108965786364991883624093221808379787006099302170716894108468573305266838502513202877298055991493230671361578214252391379062951849546705621046771082383334140647522704329871918780977581375630796944085344217320782641958679429060755746450827151909666930051757502732076512867428969118682344284654992115575621563152961247080771694528053850258206185895605450540216483689014860648650207500221090509505419925316612375990016110921654488851062485457242696296180966814588',
                 'for_name': 'Dummy Customer', 'by_phone': 'N/A', 'for_comment': 'Unittest', 'by_name': 'NetKnights GmbH'}


class SubscriptionApplicationTestCase(MyTestCase):

    def setUp(self):
        super().setUp()
        # These tests assign tokens and expect the very next check to judge the
        # subscription against them. The check normally reuses the number of
        # users it counted moments ago, so count on every check here instead.
        self.app.config["PI_SUBSCRIPTION_COUNT_INTERVAL"] = 0

    def tearDown(self):
        self.app.config.pop("PI_SUBSCRIPTION_COUNT_INTERVAL", None)
        super().tearDown()

    def test_01_subscriptions(self):
        r = save_subscription(SUBSCRIPTION1)
        self.assertTrue(r)
        subscription = get_subscription("privacyIDEA")[0]
        # Compare all keys in SUBSCRIPTION1 with the subscription object
        for key, value in SUBSCRIPTION1.items():
            self.assertEqual(subscription.get(key), value)

        # Update
        new_id = save_subscription(SUBSCRIPTION2)
        self.assertEqual(r, new_id)

        # Get
        subs = get_subscription()
        self.assertEqual(1, len(subs))
        subs = get_subscription("privacyIDEA")
        self.assertEqual(1, len(subs))
        otrs_sub = subs[0]
        self.assertEqual("privacyIDEA", otrs_sub.get("application"))
        self.assertEqual("Dummy Customer", otrs_sub.get("for_name"))
        self.assertEqual("info@netknights.it", otrs_sub.get("for_email"))
        self.assertEqual(200, otrs_sub.get("num_tokens"))

        # delete
        s = delete_subscription("privacyIDEA")
        self.assertTrue(s)

        # get
        subs = get_subscription("privacyIDEA")
        self.assertEqual(len(subs), 0)

    def test_02_exception_propability(self):
        s = raise_exception_probability()
        self.assertTrue(s in [0, 1])

        # Valid subscriptions
        subdate = (datetime.now() + timedelta(days=30))
        subscription = {"date_till": subdate}
        s = raise_exception_probability(subscription)
        # do not raise
        self.assertFalse(s)

        # Subscription expired for 30 days
        subdate = (datetime.now() - timedelta(days=30))
        subscription = {"date_till": subdate}
        s = raise_exception_probability(subscription)
        # sometimes raise
        self.assertTrue(s in [True, False])

        # Subscription expired for 100 days
        subdate = (datetime.now() - timedelta(days=100))
        subscription = {"date_till": subdate}
        s = raise_exception_probability(subscription)
        # always raise
        self.assertTrue(s)

    def test_03_check_subscription(self):
        # A valid subscription
        r = save_subscription(SUBSCRIPTION1)
        self.assertTrue(r)
        s = check_subscription("privacyIDEA")
        self.assertTrue(s)

        # A subscription, that has expired
        r = save_subscription(SUBSCRIPTION3)
        self.assertTrue(r)
        # The subscription, which has expired 100 days ago raises an exception
        self.assertRaises(SubscriptionError, check_subscription, "demo_application")

        self.setUp_user_realms()
        init_token({"type": "spass"}, user=User("cornelius", self.realm1))
        init_token({"type": "spass"}, user=User("cornelius", self.realm1))
        init_token({"type": "spass"}, user=User("cornelius", self.realm1))

        save_subscription(SUBSCRIPTION4)

        # We have only one user with tokens, so having a subscription of 10 is fine!
        s = check_subscription("privacyIDEA")
        self.assertTrue(s)

        for username in ["shadow", "nopw", "autoassignuser", "selfservice", "timelimituser",
                         "passthru", "disableduser", "lockeduser", "usernotoken", "multichal"]:
            init_token({"type": "spass"}, user=User(username, self.realm1))
        # Now we have eleven users with tokens, but only ten are allowed. We fail with a probabiliy of 1/12
        # Fail subscription check
        with mock.patch("random.randrange") as mock_random:
            mock_random.return_value = 11
            self.assertRaises(SubscriptionError, check_subscription, "privacyIDEA")
        # succeed subscription check
        with mock.patch("random.randrange") as mock_random:
            mock_random.return_value = 10
            self.assertTrue(check_subscription("privacyIDEA"))
        with mock.patch("random.randrange") as mock_random:
            mock_random.return_value = 1
            self.assertTrue(check_subscription("privacyIDEA"))

        # try to save some broken subscriptions
        sub1 = SUBSCRIPTION1.copy()
        sub1['date_from'] = '1234'
        with self.assertRaises(ValueError):
            save_subscription(sub1)

        sub1 = SUBSCRIPTION1.copy()
        sub1['by_name'] = 'unknown vendor'
        with self.assertRaisesRegex(
                SubscriptionError,
                'Verifying the signature of your subscription'):
            save_subscription(sub1)

        sub1 = SUBSCRIPTION1.copy()
        sub1['signature'] = str(int(sub1['signature']) + 1)
        with self.assertRaisesRegex(
                SubscriptionError,
                'Signature of your subscription does not'):
            save_subscription(sub1)

    def test_04_subscription_status(self):
        save_subscription(SUBSCRIPTION1)
        res = subscription_status()
        # Token count < 50
        self.assertEqual(0, res)

    def test_05_metered_clients(self):
        # A metered client resolves to the application it is counted against; any other
        # name passes through lower-cased.
        self.assertEqual("privacyidea-pam", get_metered_application("pam-passkey"))
        self.assertEqual("privacyidea-pam", get_metered_application("PAM-Passkey"))
        self.assertEqual("privacyidea-pam", get_metered_application("pam-privacyidea"))
        self.assertEqual("privacyidea-keycloak",
                         get_metered_application("entraid-via-keycloak"))
        self.assertEqual("privacyidea-cp", get_metered_application("privacyidea-cp"))
        self.assertEqual("privacyidea-cp", get_metered_application("Privacyidea-CP"))
        self.assertEqual("", get_metered_application(""))

        # check_subscription for a metered client looks up its application's
        # subscription rather than the client's own name.
        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=0):
            with mock.patch("privacyidea.lib.subscriptions.get_subscription",
                            return_value=[]) as mock_get_subscription:
                self.assertTrue(check_subscription("pam-passkey"))
        mock_get_subscription.assert_called_once_with("privacyidea-pam")

    def test_06_authenticator_app_is_never_metered(self):
        # The Authenticator App is free to use: its authentications must not be counted
        # against any subscription, however many users have tokens, and it must not be
        # able to raise a SubscriptionError. It resolves to a real product - unlike a
        # name with no product of its own, e.g. "" - but that product's free_users is
        # None, which is what actually turns enforcement off, see check_subscription().
        self.assertEqual("privacyidea authenticator", get_metered_application("privacyIDEA-App"))
        self.assertIsNone(APPLICATIONS["privacyidea authenticator"])
        # The dashboard still reports it under the authenticator subscription.
        self.assertEqual("privacyidea authenticator", get_subscription_owner("privacyIDEA-App"))

        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=100_000) as mock_token_users:
            with mock.patch("privacyidea.lib.subscriptions.get_subscription") as mock_get_subscription:
                for _ in range(20):
                    self.assertTrue(check_subscription("privacyIDEA-App"))
        # Not metered at all: neither the free tier nor a subscription is consulted.
        mock_get_subscription.assert_not_called()
        mock_token_users.assert_not_called()

    def test_07_freeradius_is_metered_like_the_server(self):
        # FreeRADIUS is covered by the server's subscription and counts against the same
        # free tier, so it resolves to "privacyidea" for metering and for display.
        self.assertEqual("privacyidea", get_metered_application("FreeRADIUS"))
        self.assertEqual("privacyidea", get_subscription_owner("FreeRADIUS"))
        self.assertEqual(APPLICATIONS["privacyidea"], APPLICATIONS[get_metered_application("FreeRADIUS")])

        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=0):
            with mock.patch("privacyidea.lib.subscriptions.get_subscription",
                            return_value=[]) as mock_get_subscription:
                self.assertTrue(check_subscription("FreeRADIUS"))
        mock_get_subscription.assert_called_once_with("privacyidea")

    def test_08_simplesamlphp_checks_the_legacy_application_name_too(self):
        # "simplesamlphp" and "privacyidea-simplesamlphp" were merged into one product
        # for the UI, but a subscription file signed under the pre-merge name must still
        # validate, so check_subscription looks up both names.
        self.assertEqual("privacyidea-simplesamlphp", get_metered_application("simpleSAMLphp"))

        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=0):
            with mock.patch("privacyidea.lib.subscriptions.get_subscription",
                            return_value=[]) as mock_get_subscription:
                self.assertTrue(check_subscription("simpleSAMLphp"))
        mock_get_subscription.assert_any_call("privacyidea-simplesamlphp")
        mock_get_subscription.assert_any_call("simplesamlphp")
        self.assertEqual(2, mock_get_subscription.call_count)

    def test_10_valid_legacy_subscription_wins_over_an_expired_canonical_one(self):
        # A product's subscription may be filed under any of its names, so the records
        # found across those names have to be ranked by date_till: the valid one decides,
        # regardless of which name it carries.
        now = datetime.now()
        expired_canonical = {"application": "privacyidea-simplesamlphp",
                             "date_till": now - timedelta(days=30),
                             "num_tokens": 10000}
        valid_legacy = {"application": "simplesamlphp",
                        "date_till": now + timedelta(days=30),
                        "num_tokens": 10000}

        def _by_name(name=None):
            return {"privacyidea-simplesamlphp": [expired_canonical],
                    "simplesamlphp": [valid_legacy]}.get(name, [])

        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=0):
            with mock.patch("privacyidea.lib.subscriptions.get_subscription", side_effect=_by_name):
                with mock.patch("privacyidea.lib.subscriptions.check_signature",
                                return_value=True) as mock_check_signature:
                    self.assertTrue(check_subscription("simpleSAMLphp"))

        # Only a subscription that is still valid gets its signature checked, so this
        # having run at all shows the valid record was the one selected.
        mock_check_signature.assert_called_once_with(valid_legacy)

    def test_11_vendor_name_cannot_escape_the_key_directory(self):
        # The vendor is read from the uploaded subscription file and is used to build the path
        # of the public key. A vendor carrying a path separator is rejected, so the lookup
        # cannot be pointed at a file outside the key directory.
        subscription = dict(SUBSCRIPTION1, by_name="../../../tmp/NetKnights GmbH")
        with self.assertRaises(SubscriptionError) as cm:
            check_signature(subscription)
        self.assertIn("Invalid vendor", f"{cm.exception}")

    def test_09_subscription_status_never_enforced_product(self):
        # subscription_status() must honor free_users=None (the Authenticator App's
        # "never counted or enforced" state) the same way check_subscription() does,
        # without even counting tokens.
        self.assertIsNone(APPLICATIONS["privacyidea authenticator"])
        with mock.patch("privacyidea.lib.subscriptions.get_tokens") as mock_get_tokens:
            self.assertEqual(0, subscription_status("privacyIDEA-App"))
        mock_get_tokens.assert_not_called()


class PluginSubscriptionStatusTestCase(MyTestCase):
    """
    Tests for :func:`get_plugin_subscription_status`. Each entry carries two
    independent axes: ``in_use`` (bool) and ``subscription``
    (none/valid/expiring/exceeded/expired), covered here by setting up a
    ``ClientApplication`` row, optionally a ``Subscription`` row, and mocking
    the active-token-user count.
    """

    def setUp(self):
        super().setUp()
        # Tests in this class manipulate the same rows; isolate them.
        db.session.query(ClientApplication).delete()
        db.session.query(Subscription).delete()
        db.session.commit()
        # The tests mock the active-token-user count and change it within a single
        # test, which the subscription check would otherwise reuse between calls
        self.app.config["PI_SUBSCRIPTION_COUNT_INTERVAL"] = 0

    def tearDown(self):
        self.app.config.pop("PI_SUBSCRIPTION_COUNT_INTERVAL", None)
        super().tearDown()

    @staticmethod
    def _add_clientapp(plugin, version="1.0", seen_days_ago=0):
        db.session.add(ClientApplication(
            ip="1.2.3.4",
            clienttype=f"{plugin}/{version} test/1",
            node="localnode",
            lastseen=datetime.now() - timedelta(days=seen_days_ago)))
        db.session.commit()

    @staticmethod
    def _add_subscription(application, days_left, num_tokens=10000):
        db.session.add(Subscription(
            application=application,
            for_name="customer", for_email="c@x", for_phone="0",
            by_name="vendor", by_email="v@x",
            date_from=datetime.now() - timedelta(days=10),
            date_till=datetime.now() + timedelta(days=days_left),
            num_users=10, num_tokens=num_tokens, num_clients=10,
            level="Gold", signature="0"))
        db.session.commit()

    def test_01_none_by_default(self):
        overview = get_plugin_subscription_status()
        self.assertListEqual(DASHBOARD_PLUGINS, [e["application"] for e in overview])
        for entry in overview:
            # No subscription and never seen -> not in use, subscription none.
            self.assertFalse(entry["in_use"])
            self.assertEqual("none", entry["subscription"])
            self.assertIsNone(entry["last_seen"])
            self.assertIsNone(entry["date_till"])
            self.assertIsNone(entry["days_left"])

    def test_02_subscription_states(self):
        # valid: subscription with more than 60 days left, within token limit
        self._add_clientapp("privacyidea-keycloak")
        self._add_subscription("privacyidea-keycloak", days_left=100)
        # expiring: subscription with less than 60 days left
        self._add_clientapp("privacyidea-adfs")
        self._add_subscription("privacyidea-adfs", days_left=5)
        # exceeded: valid subscription but more token users than allowed. The PAM row is
        # keyed on the name the module sends; its subscription is privacyidea-pam.
        self._add_clientapp("PAM")
        self._add_subscription("privacyidea-pam", days_left=100, num_tokens=5)
        # expired: subscription end date in the past
        self._add_clientapp("privacyidea-cp")
        self._add_subscription("privacyidea-cp", days_left=-5)
        # none: no subscription, never seen -> privacyidea-shibboleth

        # 1000 token users: exceeds the pam limit (5) but not the others (10000)
        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=1000):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertEqual("valid", overview["privacyidea-keycloak"]["subscription"])
        self.assertGreaterEqual(overview["privacyidea-keycloak"]["days_left"], 60)
        self.assertIsNotNone(overview["privacyidea-keycloak"]["date_till"])

        self.assertEqual("expiring", overview["privacyidea-adfs"]["subscription"])
        self.assertLess(overview["privacyidea-adfs"]["days_left"], 60)

        self.assertEqual("exceeded", overview["pam"]["subscription"])

        self.assertEqual("expired", overview["privacyidea-cp"]["subscription"])
        self.assertLess(overview["privacyidea-cp"]["days_left"], 0)

        self.assertEqual("none", overview["privacyidea-shibboleth"]["subscription"])

        # A subscription on file always counts as in use.
        self.assertTrue(overview["privacyidea-keycloak"]["in_use"])
        # No subscription and never seen -> not in use.
        self.assertFalse(overview["privacyidea-shibboleth"]["in_use"])

    def test_03_usage_axis(self):
        # Recently seen without a subscription -> in use, subscription none.
        self._add_clientapp("privacyidea-cp", seen_days_ago=1)
        # Seen more than USAGE_RECENT_DAYS ago, no subscription -> not in use.
        self._add_clientapp("privacyidea-shibboleth", seen_days_ago=30)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertTrue(overview["privacyidea-cp"]["in_use"])
        self.assertEqual("none", overview["privacyidea-cp"]["subscription"])
        self.assertFalse(overview["privacyidea-shibboleth"]["in_use"])

    def test_04_valid_subscription_stays_valid_within_token_limit(self):
        # A valid subscription with room for the token users stays "valid".
        self._add_clientapp("privacyidea-cp")
        self._add_subscription("privacyidea-cp", days_left=100, num_tokens=10000)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=5000):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertEqual("valid", overview["privacyidea-cp"]["subscription"])

    def test_05_unparseable_useragent_is_skipped(self):
        # A row whose user-agent string does not match the plugin format
        # must not crash the function or leak into the overview.
        db.session.add(ClientApplication(
            ip="1.2.3.4",
            clienttype="!!! totally not a user-agent !!!",
            node="localnode",
            lastseen=datetime.now()))
        db.session.commit()

        overview = get_plugin_subscription_status()
        for entry in overview:
            self.assertEqual("none", entry["subscription"])
            self.assertFalse(entry["in_use"])

    def test_06_null_lastseen_does_not_crash(self):
        # ClientApplication.lastseen is nullable. If every row for a clienttype
        # has lastseen=NULL the SQL MAX() is NULL and must not be compared
        # against a real datetime from another iteration. The column has a
        # default=datetime.now, so set it to NULL explicitly after insert.
        row = ClientApplication(
            ip="1.2.3.4",
            clienttype="privacyidea-keycloak/1.0 test/1",
            node="localnode")
        db.session.add(row)
        db.session.commit()
        row.lastseen = None
        db.session.commit()

        overview = {e["application"]: e
                    for e in get_plugin_subscription_status()}
        self.assertFalse(overview["privacyidea-keycloak"]["in_use"])
        self.assertEqual("none", overview["privacyidea-keycloak"]["subscription"])

    def test_07_null_application_subscription_is_skipped(self):
        # Subscription.application is nullable and Subscription.get() drops
        # None fields. Such rows must not crash the dict comprehension.
        db.session.add(Subscription(
            application=None,
            for_name="customer", for_email="c@x", for_phone="0",
            by_name="vendor", by_email="v@x",
            date_from=datetime.now() - timedelta(days=10),
            date_till=datetime.now() + timedelta(days=100),
            num_users=10, num_tokens=10, num_clients=10,
            level="Gold", signature="0"))
        db.session.commit()

        overview = get_plugin_subscription_status()
        # All plugins still report none (no matching subscription rows seeded).
        for entry in overview:
            self.assertEqual("none", entry["subscription"])

    def test_08_alias_useragent_stays_separate_with_own_last_seen(self):
        # pam-passkey remains its own dashboard entry with its own last_seen, even though
        # it is counted against privacyidea-pam like the PAM module itself.
        self.assertIn("pam-passkey", DASHBOARD_PLUGINS)
        self._add_clientapp("pam-passkey")

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertIn("pam-passkey", overview)
        self.assertIsNotNone(overview["pam-passkey"]["last_seen"])
        # The PAM row itself had no client activity.
        self.assertIsNone(overview["pam"]["last_seen"])

    def test_09_alias_useragent_mirrors_owning_subscription(self):
        # pam-passkey has no subscription of its own; its row reflects the
        # privacyidea-pam subscription's state while keeping its own last_seen.
        self._add_clientapp("pam-passkey")
        self._add_subscription("privacyidea-pam", days_left=100)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        pam_passkey = overview["pam-passkey"]
        self.assertEqual("valid", pam_passkey["subscription"])
        self.assertTrue(pam_passkey["in_use"])
        self.assertIsNotNone(pam_passkey["date_till"])
        self.assertIsNotNone(pam_passkey["last_seen"])

    def test_10_alias_useragent_without_subscription_is_none(self):
        # With no owning subscription, pam-passkey reports subscription none,
        # but recent activity still makes it used.
        self._add_clientapp("pam-passkey")

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=1000):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertEqual("none", overview["pam-passkey"]["subscription"])
        self.assertTrue(overview["pam-passkey"]["in_use"])

    def test_11_entraid_row_mirrors_keycloak(self):
        # entraid-via-keycloak is its own dashboard row but counts against and
        # mirrors the privacyidea-keycloak subscription.
        self.assertIn("entraid-via-keycloak", DASHBOARD_PLUGINS)
        self._add_clientapp("entraid-via-keycloak")
        self._add_subscription("privacyidea-keycloak", days_left=100)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        entraid = overview["entraid-via-keycloak"]
        self.assertEqual("valid", entraid["subscription"])
        self.assertTrue(entraid["in_use"])
        self.assertIsNotNone(entraid["last_seen"])

    def test_13_authenticator_app_useragent_wired_to_row(self):
        # The Authenticator App sends the user-agent "privacyIDEA-App", which is the
        # dashboard row (privacyidea-app) and reports the "privacyidea authenticator"
        # subscription without being metered against it.
        self.assertIn("privacyidea-app", DASHBOARD_PLUGINS)
        self.assertEqual("privacyidea authenticator",
                         get_subscription_owner("privacyIDEA-App"))
        self._add_clientapp("privacyIDEA-App", version="4.7.3")
        self._add_subscription("privacyidea authenticator", days_left=100)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        app_row = overview["privacyidea-app"]
        # The app's activity lands on this row ...
        self.assertIsNotNone(app_row["last_seen"])
        # ... and it resolves the authenticator subscription.
        self.assertEqual("valid", app_row["subscription"])
        self.assertTrue(app_row["in_use"])
        # The version parsed from the user-agent is reported.
        self.assertListEqual(["4.7.3"], app_row["versions"])

    def test_14_versions_collected_from_useragents(self):
        # Distinct versions seen in the user-agents are reported, newest first.
        self._add_clientapp("privacyidea-keycloak", version="1.2.3")
        self._add_clientapp("privacyidea-keycloak", version="1.3.0")

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertListEqual(["1.3.0", "1.2.3"], overview["privacyidea-keycloak"]["versions"])
        # A plugin never seen has no versions.
        self.assertListEqual([], overview["privacyidea-shibboleth"]["versions"])

    def test_16_versions_are_ordered_by_number(self):
        # Newest first means by number: a character sort would put 1.9.0 above 1.10.0.
        self._add_clientapp("privacyidea-cp", version="1.9.0")
        self._add_clientapp("privacyidea-cp", version="1.10.0")
        self._add_clientapp("privacyidea-cp", version="1.10.1")

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertListEqual(["1.10.1", "1.10.0", "1.9.0"], overview["privacyidea-cp"]["versions"])
        # Anything a client may send stays sortable, numeric or not.
        self.assertListEqual(["10.0", "2.0.0-rc1", "1.2.3", "1.2"],
                             sorted(["1.2", "10.0", "1.2.3", "2.0.0-rc1"],
                                    key=version_sort_key, reverse=True))

    def test_17_subscription_without_end_date_is_not_valid(self):
        # Subscription.date_till is nullable. Such a record cannot be reported as
        # covering anything, and must not leave the row green forever.
        db.session.add(Subscription(
            application="privacyidea-cp",
            for_name="customer", for_email="c@x", for_phone="0",
            by_name="vendor", by_email="v@x",
            date_from=datetime.now() - timedelta(days=10), date_till=None,
            num_users=10, num_tokens=10000, num_clients=10,
            level="Gold", signature="0"))
        db.session.commit()

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        credential_provider = overview["privacyidea-cp"]
        self.assertEqual("expired", credential_provider["subscription"])
        self.assertIsNone(credential_provider["date_till"])
        self.assertIsNone(credential_provider["days_left"])

    def test_18_metering_ignores_a_subscription_without_end_date(self):
        # Metering must neither raise on the missing date nor block the client outright:
        # the record is ignored and the free tier applies as if none were on file.
        unusable = [{"application": "privacyidea-cp", "date_till": None}]
        with mock.patch("privacyidea.lib.subscriptions.get_subscription", return_value=unusable):
            with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                            return_value=0):
                self.assertTrue(check_subscription("privacyidea-cp"))
            # Far beyond the free tier it fails like an install without a subscription.
            with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                            return_value=100_000):
                self.assertRaises(SubscriptionError, check_subscription, "privacyidea-cp")

    def test_12_radius_row_mirrors_server_subscription(self):
        # FreeRADIUS identifies itself as "FreeRADIUS" and has no subscription of its
        # own; it is covered by the server ("privacyidea") subscription and mirrors it.
        self.assertIn("freeradius", DASHBOARD_PLUGINS)
        self._add_subscription("privacyidea", days_left=100)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        radius = overview["freeradius"]
        self.assertEqual("valid", radius["subscription"])
        self.assertTrue(radius["in_use"])

    def test_15_pam_row_matches_the_user_agent_the_module_sends(self):
        # The PAM module identifies itself as "PAM/<version>", so that is the row's key.
        # "privacyidea-pam" stays the application whose subscription the row reports, and
        # remains accepted as a client name of its own.
        self.assertIn("pam", DASHBOARD_PLUGINS)
        self.assertEqual("privacyidea-pam", get_metered_application("PAM"))
        self.assertEqual("privacyidea-pam", get_metered_application("privacyidea-pam"))
        self._add_clientapp("PAM", version="1.1.0")
        self._add_subscription("privacyidea-pam", days_left=100)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        pam = overview["pam"]
        self.assertTrue(pam["in_use"])
        self.assertListEqual(["1.1.0"], pam["versions"])
        self.assertEqual("valid", pam["subscription"])

    def test_19_secondary_agent_name_marks_its_integration_row(self):
        # An integration can be known by more than one wire name (the PAM row answers to
        # both "PAM" and "privacyidea-pam"). The dashboard rows are keyed by integration
        # id, so an observation under a secondary name has to resolve to the same row
        # instead of keying itself and matching nothing.
        self.assertIn("pam-privacyidea", AGENT_TO_INTEGRATION)
        self.assertEqual("pam", AGENT_TO_INTEGRATION["pam-privacyidea"])
        self._add_clientapp("pam-privacyidea", version="1.2.0")

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        pam = overview["pam"]
        self.assertTrue(pam["in_use"])
        self.assertIsNotNone(pam["last_seen"])
        self.assertListEqual(["1.2.0"], pam["versions"])

    def test_13_nextcloud_row_matches_the_user_agent_the_app_sends(self):
        # The Nextcloud app identifies itself as "privacyidea-nextcloud/<version>", which
        # has to be the row's key: a name the clients do not send would leave the row
        # permanently unused without any error.
        db.session.add(ClientApplication(
            ip="1.2.3.4",
            clienttype="privacyidea-nextcloud/1.2.0",
            node="localnode",
            lastseen=datetime.now()))
        db.session.commit()

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        nextcloud = overview["privacyidea-nextcloud"]
        self.assertTrue(nextcloud["in_use"])
        self.assertListEqual(["1.2.0"], nextcloud["versions"])


class SubscriptionDayCountTestCase(MyTestCase):
    """
    Tests for the day count :func:`_subscription_state` reports. date_till carries a
    calendar date, so the count is between dates and does not depend on the time of day
    the dashboard happens to be opened.
    """

    @staticmethod
    def _state(date_till, now, num_tokens=10000):
        return _subscription_state({"date_till": date_till, "num_tokens": num_tokens}, now, 0)

    def test_01_expiry_day_counts_as_today(self):
        date_till = datetime(2026, 6, 30)
        # Anywhere on the day itself the subscription is over — the date is exclusive,
        # matching check_subscription — but no whole day has passed yet.
        for now in (datetime(2026, 6, 30, 0, 0, 1),
                    datetime(2026, 6, 30, 12, 0),
                    datetime(2026, 6, 30, 23, 59, 59)):
            info = self._state(date_till, now)
            self.assertEqual(SubscriptionState.EXPIRED, info.state)
            self.assertEqual(0, info.days_left)

    def test_02_days_ago_counts_whole_dates(self):
        info = self._state(datetime(2026, 6, 30), datetime(2026, 7, 3, 0, 0, 1))
        self.assertEqual(SubscriptionState.EXPIRED, info.state)
        self.assertEqual(-3, info.days_left)

    def test_03_last_day_of_cover_is_one_day_left(self):
        # A subscription running out tomorrow has a day left whatever the clock says.
        for now in (datetime(2026, 6, 29, 0, 0, 1), datetime(2026, 6, 29, 23, 0)):
            info = self._state(datetime(2026, 6, 30), now)
            self.assertEqual(1, info.days_left)

    def test_04_expiring_threshold_does_not_move_with_the_clock(self):
        # The threshold reads the same count, so the day it turns yellow is a date, not a
        # date plus a time of day.
        date_till = datetime(2026, 6, 30)
        outside = date_till - timedelta(days=EXPIRING_THRESHOLD_DAYS)
        for now in (outside, outside.replace(hour=23, minute=59)):
            self.assertEqual(SubscriptionState.VALID, self._state(date_till, now).state)
        inside = date_till - timedelta(days=EXPIRING_THRESHOLD_DAYS - 1)
        for now in (inside, inside.replace(hour=23, minute=59)):
            self.assertEqual(SubscriptionState.EXPIRING, self._state(date_till, now).state)


class ServerSubscriptionStatusTestCase(MyTestCase):
    """
    Tests for :func:`get_server_subscription_status`. Covers the subscription
    states (none / valid / expiring / expired) plus the duplicate-row
    tiebreaker.
    """

    def setUp(self):
        super().setUp()
        db.session.query(Subscription).delete()
        db.session.commit()

    @staticmethod
    def _add_server_subscription(days_left, by_email="v@x"):
        db.session.add(Subscription(
            application="privacyidea",
            for_name="customer", for_email="c@x", for_phone="0",
            by_name="vendor", by_email=by_email,
            date_from=datetime.now() - timedelta(days=10),
            date_till=datetime.now() + timedelta(days=days_left),
            num_users=10, num_tokens=10000, num_clients=10,
            level="Gold", signature="0"))
        db.session.commit()

    def test_01_no_subscription(self):
        entry = get_server_subscription_status()
        self.assertTrue(entry["is_server"])
        self.assertEqual("privacyidea", entry["application"])
        self.assertEqual("none", entry["subscription"])
        # The server answering the request is in use whether or not it has a subscription.
        self.assertTrue(entry["in_use"])
        self.assertIsNone(entry["date_till"])
        self.assertIsNone(entry["days_left"])
        # The server row reports its running version, with any dev/local
        # suffix (e.g. "3.13.1+gc6d73eab6...") truncated.
        self.assertEqual(1, len(entry["versions"]))
        self.assertNotIn("+", entry["versions"][0])

    def test_02_valid(self):
        self._add_server_subscription(days_left=100)
        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            entry = get_server_subscription_status()
        self.assertEqual("valid", entry["subscription"])
        self.assertTrue(entry["in_use"])
        self.assertGreaterEqual(entry["days_left"], 60)

    def test_03_expiring(self):
        self._add_server_subscription(days_left=5)
        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            entry = get_server_subscription_status()
        self.assertEqual("expiring", entry["subscription"])
        self.assertLess(entry["days_left"], 60)
        self.assertGreaterEqual(entry["days_left"], 0)

    def test_04_expired(self):
        self._add_server_subscription(days_left=-5)
        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            entry = get_server_subscription_status()
        self.assertEqual("expired", entry["subscription"])
        self.assertLess(entry["days_left"], 0)

    def test_05_picks_latest_date_till_when_duplicates_exist(self):
        # Two rows for the same application — the one with the latest
        # date_till must win so the dashboard does not flap.
        self._add_server_subscription(days_left=-5, by_email="old@x")
        self._add_server_subscription(days_left=100, by_email="new@x")
        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            entry = get_server_subscription_status()
        self.assertEqual("valid", entry["subscription"])
        self.assertGreaterEqual(entry["days_left"], 60)


class GithubVersionTestCase(MyTestCase):
    """
    Tests for :func:`get_latest_github_versions`. The network is mocked so the
    tests never contact GitHub.
    """

    def setUp(self):
        super().setUp()
        self._clear_cache()

    def tearDown(self):
        self._clear_cache()
        super().tearDown()

    @staticmethod
    def _clear_cache():
        invalidate_github_version_cache()

    def test_01_fetch_parses_and_caches(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {"tag_name": "v4.7.3",
                                      "published_at": "2026-05-20T10:00:00Z",
                                      "html_url": "https://github.com/privacyidea/privacyidea/releases/tag/v4.7.3"}
        with mock.patch("privacyidea.lib.subscriptions.requests.get",
                        return_value=response) as mock_get:
            versions = get_latest_github_versions()
        # Leading "v" stripped, date truncated to the day, keyed by application.
        self.assertEqual("4.7.3", versions["privacyidea"].version)
        self.assertEqual("2026-05-20", versions["privacyidea"].released)
        # Server and app are link-suppressed (not downloaded from GitHub).
        self.assertIsNone(versions["privacyidea"].url)
        self.assertIsNone(versions["privacyidea-app"].url)
        # Other clients keep the release page link.
        self.assertEqual("4.7.3", versions["privacyidea-keycloak"].version)
        self.assertEqual("https://github.com/privacyidea/privacyidea/releases/tag/v4.7.3",
                         versions["privacyidea-keycloak"].url)
        self.assertTrue(mock_get.called)

        # A second call within the TTL is served from cache (no new fetch).
        with mock.patch("privacyidea.lib.subscriptions.requests.get") as mock_get2:
            versions2 = get_latest_github_versions()
            mock_get2.assert_not_called()
        self.assertEqual("4.7.3", versions2["privacyidea"].version)

    def test_02_unreachable_repo_maps_to_none(self):
        with mock.patch("privacyidea.lib.subscriptions.requests.get",
                        side_effect=requests.RequestException("boom")):
            versions = get_latest_github_versions()
        self.assertIsNone(versions["privacyidea"])

    def test_03_failed_lookup_is_cached_too(self):
        # A server that cannot reach GitHub must not pay the timeout on every request,
        # so the empty result is cached for the same TTL as a successful one.
        with mock.patch("privacyidea.lib.subscriptions.requests.get",
                        side_effect=requests.RequestException("boom")):
            get_latest_github_versions()
            with mock.patch("privacyidea.lib.subscriptions.requests.get") as mock_get:
                versions = get_latest_github_versions()
                mock_get.assert_not_called()
        self.assertIsNone(versions["privacyidea"])

    def test_05_empty_lookup_is_retried_sooner_than_a_good_one(self):
        # A lookup that found nothing is a network or rate-limit problem, so it must not
        # keep the column empty for the full TTL. One that found releases is kept.
        response = mock.Mock(status_code=200)
        response.json.return_value = {"tag_name": "v4.7.3", "published_at": "2026-05-20T10:00:00Z",
                                      "html_url": "https://github.com/privacyidea/privacyidea/releases/tag/v4.7.3"}
        stale = datetime.now() - (subscriptions_module.GITHUB_VERSION_FAILURE_TTL + timedelta(minutes=1))

        with mock.patch("privacyidea.lib.subscriptions.requests.get",
                        side_effect=requests.RequestException("boom")):
            empty = get_latest_github_versions()

        # Age both cache levels: the shared one would otherwise still answer.
        self._age_caches(stale, empty)
        with mock.patch("privacyidea.lib.subscriptions.requests.get",
                        return_value=response) as mock_get:
            good = get_latest_github_versions()
            self.assertEqual("4.7.3", good["privacyidea"].version)
            self.assertTrue(mock_get.called)

        # The successful result survives the same age, up to the full TTL.
        self._age_caches(stale, good)
        with mock.patch("privacyidea.lib.subscriptions.requests.get") as mock_get:
            get_latest_github_versions()
            mock_get.assert_not_called()

    @staticmethod
    def _age_caches(fetched_at, releases):
        """Pretend the given lookup was made at ``fetched_at``, in both cache levels."""
        subscriptions_module._github_version_cache.store(fetched_at, releases)
        subscriptions_module._store_shared_releases(fetched_at, releases)

    def test_06_another_worker_reuses_the_shared_lookup(self):
        # A worker with a cold process-local cache must pick up the lookup a previous one
        # published, instead of asking GitHub again: that is what keeps a multi-worker
        # installation inside GitHub's rate limit.
        response = mock.Mock(status_code=200)
        response.json.return_value = {"tag_name": "v4.7.3", "published_at": "2026-05-20T10:00:00Z",
                                      "html_url": "https://github.com/privacyidea/privacyidea/releases/tag/v4.7.3"}
        with mock.patch("privacyidea.lib.subscriptions.requests.get", return_value=response):
            get_latest_github_versions()

        # Same shared cache, cold process: no fetch, same result.
        subscriptions_module._github_version_cache.store(None, {})
        with mock.patch("privacyidea.lib.subscriptions.requests.get") as mock_get:
            versions = get_latest_github_versions()
            mock_get.assert_not_called()
        self.assertEqual("4.7.3", versions["privacyidea"].version)
        self.assertEqual("https://github.com/privacyidea/privacyidea/releases/tag/v4.7.3",
                         versions["privacyidea-keycloak"].url)

    def test_07_shared_lookup_is_skipped_when_it_does_not_fit(self):
        # The config value has a limited length. A payload beyond it is not shared rather
        # than failing the request, so each worker falls back to its own lookup.
        response = mock.Mock(status_code=200)
        response.json.return_value = {"tag_name": "v4.7.3", "published_at": "2026-05-20T10:00:00Z",
                                      "html_url": "https://github.com/privacyidea/privacyidea/releases/tag/v4.7.3"}
        with mock.patch("privacyidea.lib.subscriptions.CONFIG_VALUE_LENGTH", 10):
            with mock.patch("privacyidea.lib.subscriptions.requests.get", return_value=response):
                self.assertEqual("4.7.3", get_latest_github_versions()["privacyidea"].version)

            subscriptions_module._github_version_cache.store(None, {})
            with mock.patch("privacyidea.lib.subscriptions.requests.get",
                            return_value=response) as mock_get:
                get_latest_github_versions()
                self.assertTrue(mock_get.called)

    def test_08_unreadable_shared_lookup_is_fetched_again(self):
        # Whatever is in the config row, a value that cannot be read must not break the
        # overview; it is treated as an empty cache.
        subscriptions_module.set_privacyidea_config(
            subscriptions_module.GITHUB_VERSION_CONFIG_KEY, "not json at all")
        subscriptions_module._github_version_cache.store(None, {})
        response = mock.Mock(status_code=200)
        response.json.return_value = {"tag_name": "v1.0.0", "published_at": "2026-05-20T10:00:00Z",
                                      "html_url": "https://github.com/privacyidea/privacyidea/releases/tag/v1.0.0"}

        with mock.patch("privacyidea.lib.subscriptions.requests.get", return_value=response) as mock_get:
            versions = get_latest_github_versions()
            self.assertTrue(mock_get.called)
        self.assertEqual("1.0.0", versions["privacyidea"].version)

    def test_04_version_check_can_be_switched_off(self):
        # PI_SUBSCRIPTION_VERSION_CHECK = False skips the lookup entirely, for
        # installations without internet access.
        with mock.patch("privacyidea.lib.subscriptions.get_app_config_value",
                        return_value=False):
            with mock.patch("privacyidea.lib.subscriptions.requests.get") as mock_get:
                versions = get_latest_github_versions()
                mock_get.assert_not_called()
        # Every dashboard client is still reported, just without a version.
        self.assertEqual(set(subscriptions_module.GITHUB_REPOS), set(versions))
        self.assertTrue(all(release is None for release in versions.values()))
        # Nothing was cached, so a later call with the check enabled fetches.
        self.assertIsNone(subscriptions_module._github_version_cache.fetched_at)


class SubscriptionUserCountTestCase(MyTestCase):
    """
    ``check_subscription`` runs on every authentication carrying a known
    plugin's user agent, so it does not count the users every time.
    """

    def setUp(self):
        super().setUp()
        self.app.config["PI_SUBSCRIPTION_COUNT_INTERVAL"] = 60

    def tearDown(self):
        self.app.config.pop("PI_SUBSCRIPTION_COUNT_INTERVAL", None)
        get_app_local_store().pop(_USER_COUNT_KEY, None)
        super().tearDown()

    def test_01_the_users_are_counted_once_per_interval(self):
        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=1) as mock_count:
            for _ in range(5):
                self.assertEqual(1, _users_with_active_tokens_for_check(50))
        self.assertEqual(1, mock_count.call_count)

    def test_02_an_interval_of_zero_counts_every_time(self):
        self.app.config["PI_SUBSCRIPTION_COUNT_INTERVAL"] = 0
        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=1) as mock_count:
            for _ in range(3):
                _users_with_active_tokens_for_check(50)
        self.assertEqual(3, mock_count.call_count)

    def test_03_a_number_that_would_deny_access_is_never_reused(self):
        # Tokens deleted a moment ago would otherwise keep users locked out for
        # the rest of the interval, so the count is taken again before the
        # subscription can be declared exceeded
        get_app_local_store()[_USER_COUNT_KEY] = (time.monotonic(), 80)
        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=10) as mock_count:
            self.assertEqual(10, _users_with_active_tokens_for_check(50))
        self.assertEqual(1, mock_count.call_count)

    def test_04_a_number_within_the_subscription_is_reused(self):
        get_app_local_store()[_USER_COUNT_KEY] = (time.monotonic(), 10)
        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=99) as mock_count:
            self.assertEqual(10, _users_with_active_tokens_for_check(50))
            # Exactly at the limit is still within it
            get_app_local_store()[_USER_COUNT_KEY] = (time.monotonic(), 50)
            self.assertEqual(50, _users_with_active_tokens_for_check(50))
        self.assertEqual(0, mock_count.call_count)

    def test_05_a_number_older_than_the_interval_is_counted_again(self):
        get_app_local_store()[_USER_COUNT_KEY] = (time.monotonic() - 61, 10)
        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=11) as mock_count:
            self.assertEqual(11, _users_with_active_tokens_for_check(50))
        self.assertEqual(1, mock_count.call_count)

    def test_06_a_malformed_interval_falls_back_to_the_default(self):
        self.app.config["PI_SUBSCRIPTION_COUNT_INTERVAL"] = "not a number"
        self.assertEqual(60, _count_interval_seconds())
        self.app.config["PI_SUBSCRIPTION_COUNT_INTERVAL"] = -5
        self.assertEqual(0, _count_interval_seconds())

    def test_07_the_displayed_count_stays_exact(self):
        # The subscription overview and the statistics task must not be served a
        # number that was counted a minute ago
        get_app_local_store()[_USER_COUNT_KEY] = (time.monotonic(), 4711)
        self.assertEqual(0, get_users_with_active_tokens())


class UsersWithActiveTokensTestCase(MyTestCase):
    """
    The number a subscription is measured against counts users, not tokens.
    """

    def test_01_a_user_with_several_tokens_counts_once(self):
        self.setUp_user_realms()
        self.assertEqual(0, get_users_with_active_tokens())

        cornelius = User("cornelius", self.realm1)
        init_token({"serial": "count01", "type": "spass"}, user=cornelius)
        init_token({"serial": "count02", "type": "spass"}, user=cornelius)
        self.assertEqual(1, get_users_with_active_tokens())

        init_token({"serial": "count03", "type": "spass"}, user=User("selfservice", self.realm1))
        self.assertEqual(2, get_users_with_active_tokens())

        # A token nobody owns has no user to count
        init_token({"serial": "count04", "type": "spass"})
        self.assertEqual(2, get_users_with_active_tokens())

        # A user counts as long as any of their tokens is active
        enable_token("count01", enable=False)
        self.assertEqual(2, get_users_with_active_tokens())
        enable_token("count02", enable=False)
        self.assertEqual(1, get_users_with_active_tokens())

        for serial in ["count01", "count02", "count03", "count04"]:
            remove_token(serial)
        self.assertEqual(0, get_users_with_active_tokens())

    def test_02_the_same_user_id_in_two_resolvers_counts_twice(self):
        # Users are counted as (resolver, user id) pairs, because an id is only unique
        # within its resolver: "franzi" in reso3 carries the same id as "cornelius" in
        # resolver1
        self.setUp_user_realms()
        self.setUp_user_realm3()
        self.assertEqual(0, get_users_with_active_tokens())

        init_token({"serial": "count05", "type": "spass"}, user=User("cornelius", self.realm1))
        init_token({"serial": "count06", "type": "spass"}, user=User("franzi", self.realm3))
        self.assertEqual(2, get_users_with_active_tokens())

        remove_token("count05")
        remove_token("count06")
        self.assertEqual(0, get_users_with_active_tokens())
