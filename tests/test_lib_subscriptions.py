"""
This test file tests the lib.subscriptions.py
"""
import time
from datetime import datetime, timedelta

import mock
import requests

from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib.subscriptions import (save_subscription,
                                           delete_subscription,
                                           get_subscription,
                                           get_users_with_active_tokens,
                                           raise_exception_probability,
                                           check_subscription,
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
                                           METERED_APPLICATIONS,
                                           DASHBOARD_PLUGINS)
from privacyidea.lib import subscriptions as subscriptions_module
from privacyidea.lib.token import init_token
from privacyidea.lib.user import User
from privacyidea.models import ClientApplication, Subscription, db
from .base import MyTestCase

# 100 users
SUBSCRIPTION1 = {'by_address': 'provider-address', 'for_email': 'customer@example.com', 'num_tokens': 100,
                 'num_users': 100, 'level': 'Gold', 'for_comment': 'comment', 'date_from': '2016-10-24',
                 'for_address': 'customer-address',
                 'signature': '24287419543134291932335914280232067571967865893672677932354574121521748844689122490399903572722627692437421759860332653860825381771420923865100775095168810778157750122430333094307912014590689769228979527735405954705615614505247995506136338010930079794077541100403759754392432809967862978004604278914337052409517895998984832947211907032852653171723886377329563223486623362230032551555536271158219094006763746441282022250783412321241299993657761512776112262708235357995055119379697774465205945934356687189514600830870353192115780195534680601265109038104466390286558785622582056183085321696667197925775161589029048460315',
                 'for_phone': '12345', 'by_email': 'provider@example.com', 'date_till': '2026-10-22',
                 'by_name': 'NetKnights GmbH', 'application': 'demo_application', 'by_url': 'http://provider',
                 'for_name': 'customer', 'by_phone': '12345', 'for_url': 'http://customer', 'num_clients': 100}
# 200 users
SUBSCRIPTION2 = {'by_address': 'provider-address', 'for_email': 'customer@example.com', 'num_tokens': 200,
                 'num_users': 200, 'level': 'Gold', 'for_comment': 'comment', 'date_from': '2016-10-24',
                 'for_address': 'customer-address',
                 'signature': '7739944619832023057171856564536947684804659085734377461526188619495466460016232596334451477617490220407470317539208839916568031369962545460103329851753025522408316860382940269510239571246104606108789088924884250012996984392465587650164254167417175389148405024799708943598415578782692797235505314103527081364258159023532497905690799262748743833089614921591551752367521751795589729561233624021475231087255449694499023282740029627217820083163313686822693958227330536761267872521140459441397562124467380780097899392909105517928665281442694767953463924730492991936057685649584698964546493536802892903025256708438493092045',
                 'for_phone': '12345', 'by_email': 'provider@example.com', 'date_till': '2026-10-22',
                 'by_name': 'NetKnights GmbH', 'application': 'demo_application', 'by_url': 'http://provider',
                 'for_name': 'customer', 'by_phone': '12345', 'for_url': 'http://customer', 'num_clients': 200}
# expired
SUBSCRIPTION3 = {'by_address': 'provider-address', 'for_email': 'customer@example.com', 'num_tokens': 100,
                 'num_users': 100, 'level': 'Gold', 'for_comment': 'comment', 'date_from': '2015-10-22',
                 'for_address': 'customer-address',
                 'signature': '25407205465585578473052448351020802985222256541982387080470368702502395978929370244545432262489841701057444597515172775368305952894314763774108360927487838769161883939606658203871498172390640846806985487570176937817917267265370004247183037988076793238258268672447434743336052806908752658001766448386518941839874145101365174694427138442671647817496746983715439351013662042962255755683132569592229281599938902003341163052295582849710694963121233074090316812533101113257642365156343454293877847023436035373453938687754858064544899533624458220595546766026278380731783279327943668257725383564250176186223252875047051351456',
                 'for_phone': '12345', 'by_email': 'provider@example.com', 'date_till': '2015-10-23',
                 'by_name': 'NetKnights GmbH', 'application': 'demo_application', 'by_url': 'http://provider',
                 'for_name': 'customer', 'by_phone': '12345', 'for_url': 'http://customer', 'num_clients': 100}
# to few users
SUBSCRIPTION4 = {'by_address': 'provider-address', 'for_email': 'customer@example.com', 'num_tokens': 2, 'num_users': 2,
                 'level': 'Gold', 'for_comment': 'comment', 'date_from': '2016-10-24',
                 'for_address': 'customer-address',
                 'signature': '20346592907086113613613144053127696600954855632118912659244592297546722685102644737004917800740902823683165561890505394413161615565196942324183366911523586532480364480142395813451085772145850694880288743987097090178518740759591735258675622535771288955342647886999915053682075495569659500964255745041348331199607343835943327886852909447097828956308657662313333750485629170942329826174895259789802226712715316039123607236972656403854074148715274916089558594469178028739283660084424358222054505984834431900856390282544303735166577232959529266873257477468374577830190351093665000981590012656078589178079067689917735770682',
                 'for_phone': '12345', 'by_email': 'provider@example.com', 'date_till': '2026-10-22',
                 'by_name': 'NetKnights GmbH', 'application': 'demo_application', 'by_url': 'http://provider',
                 'for_name': 'customer', 'by_phone': '12345', 'for_url': 'http://customer', 'num_clients': 2}


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
        subscription = get_subscription("demo_application")[0]
        # Compare all keys in SUBSCRIPTION1 with the subscription object
        for key, value in SUBSCRIPTION1.items():
            self.assertEqual(subscription.get(key), value)

        # Update
        new_id = save_subscription(SUBSCRIPTION2)
        self.assertEqual(r, new_id)

        # Get
        subs = get_subscription()
        self.assertEqual(1, len(subs))
        subs = get_subscription("demo_application")
        self.assertEqual(1, len(subs))
        otrs_sub = subs[0]
        self.assertEqual("demo_application", otrs_sub.get("application"))
        self.assertEqual("customer", otrs_sub.get("for_name"))
        self.assertEqual("customer@example.com", otrs_sub.get("for_email"))
        self.assertEqual(200, otrs_sub.get("num_tokens"))

        # delete
        s = delete_subscription("demo_application")
        self.assertTrue(s)

        # get
        subs = get_subscription("demo_application")
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
        s = check_subscription("demo_application")
        self.assertTrue(s)

        # A subscription, that has expired
        r = save_subscription(SUBSCRIPTION3)
        self.assertTrue(r)
        # The subscription, which has expired 100 days ago raises an exception
        self.assertRaises(SubscriptionError, check_subscription,
                          "demo_application")

        self.setUp_user_realms()
        init_token({"type": "spass"}, user=User("cornelius", self.realm1))
        init_token({"type": "spass"}, user=User("cornelius", self.realm1))
        init_token({"type": "spass"}, user=User("cornelius", self.realm1))

        save_subscription(SUBSCRIPTION4)

        # We have only one user with tokens, so having a subscription of 3 is fine!
        s = check_subscription("demo_application")
        self.assertTrue(s)

        init_token({"type": "spass"}, user=User("shadow", self.realm1))
        init_token({"type": "spass"}, user=User("nopw", self.realm1))
        # Now we have three users with tokens, but only two are allowed. We fail with a probabiliy of 1/3
        # Fail subscription check
        with mock.patch("random.randrange") as mock_random:
            mock_random.return_value = 3
            self.assertRaises(SubscriptionError, check_subscription, "demo_application")
        # succeed subscription check
        with mock.patch("random.randrange") as mock_random:
            mock_random.return_value = 2
            self.assertTrue(check_subscription("demo_application"))
        with mock.patch("random.randrange") as mock_random:
            mock_random.return_value = 1
            self.assertTrue(check_subscription("demo_application"))

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
        # able to raise a SubscriptionError.
        self.assertNotIn("privacyidea-app", METERED_APPLICATIONS)
        self.assertEqual("privacyidea-app", get_metered_application("privacyIDEA-App"))
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
