"""
This test file tests the lib.subscriptions.py
"""
from .base import MyTestCase
from datetime import datetime, timedelta
from privacyidea.lib.subscriptions import (save_subscription,
                                           delete_subscription,
                                           get_subscription,
                                           raise_exception_probability,
                                           check_subscription,
                                           SubscriptionError,
                                           SUBSCRIPTION_DATE_FORMAT)


class SubscriptionApplicationTestCase(MyTestCase):

    def test_01_subscriptions(self):
        r = save_subscription({"application": "otrs",
                               "for_name": "customer",
                               "for_email": "cust@example.com",
                               "for_phone": "123456",
                               "by_name": "NetKnights",
                               "by_email": "provider@example.com",
                               "date_from": datetime.now().strftime(
                                   SUBSCRIPTION_DATE_FORMAT),
                               "date_till": (datetime.now() + timedelta(
                                   days=10)).strftime(SUBSCRIPTION_DATE_FORMAT)})
        self.assertTrue(r)

        # Update
        r = save_subscription({"application": "otrs",
                               "for_name": "customer2",
                               "for_email": "cust@example.com"})

        # Get
        subs = get_subscription()
        self.assertEqual(len(subs), 1)
        subs = get_subscription("otrs")
        self.assertEqual(len(subs), 1)
        otrs_sub = subs[0]
        self.assertEqual(otrs_sub.get("application"), "otrs")
        self.assertEqual(otrs_sub.get("for_name"), "customer2")
        self.assertEqual(otrs_sub.get("for_email"), "cust@example.com")

        # delete
        s = delete_subscription("otrs")
        self.assertTrue(s)

        # get
        subs = get_subscription("otrs")
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
        subscription = {"date_till": subdate }
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
        r = save_subscription({"application": "demo_application",
                               "for_name": "customer",
                               "for_email": "cust@example.com",
                               "for_phone": "123456",
                               "by_name": "NetKnights",
                               "by_email": "provider@example.com",
                               "date_from": datetime.now().strftime(
                                   SUBSCRIPTION_DATE_FORMAT),
                               "date_till": (datetime.now() + timedelta(
                                   days=10)).strftime(
                                   SUBSCRIPTION_DATE_FORMAT)})
        self.assertTrue(r)
        s = check_subscription("demo_application")
        self.assertTrue(s)

        # A subscription, that has expired
        r = save_subscription({"application": "demo_application",
                               "for_name": "customer",
                               "for_email": "cust@example.com",
                               "for_phone": "123456",
                               "by_name": "NetKnights",
                               "by_email": "provider@example.com",
                               "date_from": datetime.now().strftime(
                                   SUBSCRIPTION_DATE_FORMAT),
                               "date_till": (datetime.now() + timedelta(
                                   days=-100)).strftime(
                                   SUBSCRIPTION_DATE_FORMAT)})
        self.assertTrue(r)
        # The subscription, which has expired 100 days ago raises an exception
        self.assertRaises(SubscriptionError, check_subscription,
                          "demo_application")

