"""
This test file tests the lib.subscriptions.py
"""
from .base import MyTestCase
from datetime import datetime, timedelta
from privacyidea.lib.subscriptions import (save_subscription,
                                           delete_subscription,
                                           get_subscription,
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

