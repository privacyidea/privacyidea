"""
This test file tests the lib.subscriptions.py
"""
import time
from datetime import datetime, timedelta

import mock

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
                                           _users_with_active_tokens_for_check)
from privacyidea.lib.token import init_token
from privacyidea.lib.user import User
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
