"""
This test file tests the lib.subscriptions.py
"""
from datetime import datetime, timedelta

import mock
import requests

from privacyidea.lib.subscriptions import (save_subscription,
                                           delete_subscription,
                                           get_subscription,
                                           raise_exception_probability,
                                           check_subscription,
                                           SubscriptionError,
                                           subscription_status,
                                           get_plugin_subscription_status,
                                           get_server_subscription_status,
                                           get_subscription_application,
                                           get_latest_github_versions,
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

    def test_05_useragent_aliases(self):
        # Alias user-agents resolve to the application whose subscription they
        # count against; non-aliases pass through lower-cased.
        self.assertEqual("privacyidea-pam", get_subscription_application("pam-passkey"))
        self.assertEqual("privacyidea-pam", get_subscription_application("PAM-Passkey"))
        self.assertEqual("privacyidea-keycloak",
                         get_subscription_application("entraid-via-keycloak"))
        self.assertEqual("privacyidea-cp", get_subscription_application("privacyidea-cp"))
        self.assertEqual("privacyidea-cp", get_subscription_application("Privacyidea-CP"))
        self.assertEqual("", get_subscription_application(""))

        # check_subscription for an alias looks up the primary's subscription
        # rather than the alias user-agent name.
        with mock.patch("privacyidea.lib.subscriptions.get_users_with_active_tokens",
                        return_value=0):
            with mock.patch("privacyidea.lib.subscriptions.get_subscription",
                            return_value=[]) as mock_get_subscription:
                self.assertTrue(check_subscription("pam-passkey"))
        mock_get_subscription.assert_called_once_with("privacyidea-pam")


class PluginSubscriptionStatusTestCase(MyTestCase):
    """
    Tests for :func:`get_plugin_subscription_status`. Each entry carries two
    independent axes: ``usage`` (yes/no) and ``subscription``
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
        self.assertEqual([e["application"] for e in overview], DASHBOARD_PLUGINS)
        for entry in overview:
            # No subscription and never seen -> usage no, subscription none.
            self.assertEqual(entry["usage"], "no")
            self.assertEqual(entry["subscription"], "none")
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
        # exceeded: valid subscription but more token users than allowed
        self._add_clientapp("privacyidea-pam")
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

        self.assertEqual(overview["privacyidea-keycloak"]["subscription"], "valid")
        self.assertGreaterEqual(overview["privacyidea-keycloak"]["days_left"], 60)
        self.assertIsNotNone(overview["privacyidea-keycloak"]["date_till"])

        self.assertEqual(overview["privacyidea-adfs"]["subscription"], "expiring")
        self.assertLess(overview["privacyidea-adfs"]["days_left"], 60)

        self.assertEqual(overview["privacyidea-pam"]["subscription"], "exceeded")

        self.assertEqual(overview["privacyidea-cp"]["subscription"], "expired")
        self.assertLess(overview["privacyidea-cp"]["days_left"], 0)

        self.assertEqual(overview["privacyidea-shibboleth"]["subscription"], "none")

        # A subscription on file always counts as used (usage yes).
        self.assertEqual(overview["privacyidea-keycloak"]["usage"], "yes")
        # No subscription and never seen -> usage no.
        self.assertEqual(overview["privacyidea-shibboleth"]["usage"], "no")

    def test_03_usage_axis(self):
        # Recently seen without a subscription -> used (yes), subscription none.
        self._add_clientapp("privacyidea-cp", seen_days_ago=1)
        # Seen more than USAGE_RECENT_DAYS ago, no subscription -> not used (no).
        self._add_clientapp("privacyidea-shibboleth", seen_days_ago=30)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertEqual(overview["privacyidea-cp"]["usage"], "yes")
        self.assertEqual(overview["privacyidea-cp"]["subscription"], "none")
        self.assertEqual(overview["privacyidea-shibboleth"]["usage"], "no")

    def test_04_valid_subscription_stays_valid_within_token_limit(self):
        # A valid subscription with room for the token users stays "valid".
        self._add_clientapp("privacyidea-cp")
        self._add_subscription("privacyidea-cp", days_left=100, num_tokens=10000)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=5000):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertEqual(overview["privacyidea-cp"]["subscription"], "valid")

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
            self.assertEqual(entry["subscription"], "none")
            self.assertEqual(entry["usage"], "no")

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
        self.assertEqual(overview["privacyidea-keycloak"]["usage"], "no")
        self.assertEqual(overview["privacyidea-keycloak"]["subscription"], "none")

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
            self.assertEqual(entry["subscription"], "none")

    def test_08_alias_useragent_stays_separate_with_own_last_seen(self):
        # pam-passkey remains its own dashboard entry with its own last_seen,
        # even though it is counted against privacyidea-pam.
        self.assertIn("pam-passkey", DASHBOARD_PLUGINS)
        self._add_clientapp("pam-passkey")

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertIn("pam-passkey", overview)
        self.assertIsNotNone(overview["pam-passkey"]["last_seen"])
        # privacyidea-pam had no client activity of its own.
        self.assertIsNone(overview["privacyidea-pam"]["last_seen"])

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
        self.assertEqual(pam_passkey["subscription"], "valid")
        self.assertEqual(pam_passkey["usage"], "yes")
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

        self.assertEqual(overview["pam-passkey"]["subscription"], "none")
        self.assertEqual(overview["pam-passkey"]["usage"], "yes")

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
        self.assertEqual(entraid["subscription"], "valid")
        self.assertEqual(entraid["usage"], "yes")
        self.assertIsNotNone(entraid["last_seen"])

    def test_13_authenticator_app_useragent_wired_to_row(self):
        # The Authenticator App sends the user-agent "privacyIDEA-App", which is
        # the dashboard row (privacyidea-app) and is counted against the
        # "privacyidea authenticator" subscription.
        self.assertIn("privacyidea-app", DASHBOARD_PLUGINS)
        self.assertEqual("privacyidea authenticator",
                         get_subscription_application("privacyIDEA-App"))
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
        self.assertEqual(app_row["subscription"], "valid")
        self.assertEqual(app_row["usage"], "yes")
        # The version parsed from the user-agent is reported.
        self.assertEqual(app_row["versions"], ["4.7.3"])

    def test_14_versions_collected_from_useragents(self):
        # Distinct versions seen in the user-agents are reported, newest first.
        self._add_clientapp("privacyidea-keycloak", version="1.2.3")
        self._add_clientapp("privacyidea-keycloak", version="1.3.0")

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        self.assertEqual(overview["privacyidea-keycloak"]["versions"], ["1.3.0", "1.2.3"])
        # A plugin never seen has no versions.
        self.assertEqual(overview["privacyidea-shibboleth"]["versions"], [])

    def test_12_radius_row_mirrors_server_subscription(self):
        # RADIUS has no subscription of its own; it is covered by the server
        # ("privacyidea") subscription and mirrors it.
        self.assertIn("privacyidea-radius", DASHBOARD_PLUGINS)
        self._add_subscription("privacyidea", days_left=100)

        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            overview = {e["application"]: e
                        for e in get_plugin_subscription_status()}

        radius = overview["privacyidea-radius"]
        self.assertEqual(radius["subscription"], "valid")
        self.assertEqual(radius["usage"], "yes")


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
        self.assertEqual(entry["application"], "privacyidea")
        self.assertEqual(entry["subscription"], "none")
        self.assertEqual(entry["usage"], "no")
        self.assertIsNone(entry["date_till"])
        self.assertIsNone(entry["days_left"])
        # The server row reports its running version, with any dev/local
        # suffix (e.g. "3.13.1+gc6d73eab6...") truncated.
        self.assertEqual(len(entry["versions"]), 1)
        self.assertNotIn("+", entry["versions"][0])

    def test_02_valid(self):
        self._add_server_subscription(days_left=100)
        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            entry = get_server_subscription_status()
        self.assertEqual(entry["subscription"], "valid")
        self.assertEqual(entry["usage"], "yes")
        self.assertGreaterEqual(entry["days_left"], 60)

    def test_03_expiring(self):
        self._add_server_subscription(days_left=5)
        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            entry = get_server_subscription_status()
        self.assertEqual(entry["subscription"], "expiring")
        self.assertLess(entry["days_left"], 60)
        self.assertGreaterEqual(entry["days_left"], 0)

    def test_04_expired(self):
        self._add_server_subscription(days_left=-5)
        with mock.patch(
                "privacyidea.lib.subscriptions.get_users_with_active_tokens",
                return_value=0):
            entry = get_server_subscription_status()
        self.assertEqual(entry["subscription"], "expired")
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
        self.assertEqual(entry["subscription"], "valid")
        self.assertGreaterEqual(entry["days_left"], 60)


class GithubVersionTestCase(MyTestCase):
    """
    Tests for :func:`get_latest_github_versions`. The network is mocked so the
    tests never contact GitHub.
    """

    def setUp(self):
        super().setUp()
        subscriptions_module._github_version_cache["fetched_at"] = None
        subscriptions_module._github_version_cache["versions"] = {}

    def tearDown(self):
        subscriptions_module._github_version_cache["fetched_at"] = None
        subscriptions_module._github_version_cache["versions"] = {}
        super().tearDown()

    def test_01_fetch_parses_and_caches(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {"tag_name": "v4.7.3",
                                      "published_at": "2026-05-20T10:00:00Z",
                                      "html_url": "https://github.com/privacyidea/privacyidea/releases/tag/v4.7.3"}
        with mock.patch("privacyidea.lib.subscriptions.requests.get",
                        return_value=response) as mock_get:
            versions = get_latest_github_versions()
        # Leading "v" stripped, date truncated to the day, keyed by application.
        self.assertEqual(versions["privacyidea"]["version"], "4.7.3")
        self.assertEqual(versions["privacyidea"]["released"], "2026-05-20")
        # Server and app are link-suppressed (not downloaded from GitHub).
        self.assertIsNone(versions["privacyidea"]["url"])
        self.assertIsNone(versions["privacyidea-app"]["url"])
        # Other clients keep the release page link.
        self.assertEqual(versions["privacyidea-keycloak"]["version"], "4.7.3")
        self.assertEqual(versions["privacyidea-keycloak"]["url"],
                         "https://github.com/privacyidea/privacyidea/releases/tag/v4.7.3")
        self.assertTrue(mock_get.called)

        # A second call within the TTL is served from cache (no new fetch).
        with mock.patch("privacyidea.lib.subscriptions.requests.get") as mock_get2:
            versions2 = get_latest_github_versions()
            mock_get2.assert_not_called()
        self.assertEqual(versions2["privacyidea"]["version"], "4.7.3")

    def test_02_unreachable_repo_maps_to_none(self):
        with mock.patch("privacyidea.lib.subscriptions.requests.get",
                        side_effect=requests.RequestException("boom")):
            versions = get_latest_github_versions()
        self.assertIsNone(versions["privacyidea"])
