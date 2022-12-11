# -*- coding: utf-8 -*-
from .base import MyApiTestCase
from privacyidea.lib.user import (User)
from privacyidea.lib.token import init_token
from privacyidea.lib.policy import SCOPE, ACTION, set_policy
from privacyidea.lib.machine import attach_token


class OfflinePassNoTokenTestCase(MyApiTestCase):
    """
    Ensure that an user with no tokens do not receive any offline values
    https://github.com/privacyidea/privacyidea/issues/3333
    """

    def test_00_setup(self):
        self.setUp_user_realms()

    def test_01_create_tokens(self):
        # create token for 1st user

        userA = User("shadow", self.realm1, self.resolvername1)
        userB = User("cornelius", self.realm1, self.resolvername1)
        userC = User("usernotoken", self.realm1, self.resolvername1)
        tokA = init_token({"otpkey": self.otpkey, "serial": "tokA"},
                          user=userA)
        tokB = init_token({"otpkey": self.otpkey, "serial": "tokB"},
                          user=userB)
        # attach tokens to offline
        attach_token("tokA", "offline")
        attach_token("tokB", "offline")
        # set passonnotoken
        set_policy(name="pol1", scope=SCOPE.AUTH, action=ACTION.PASSNOTOKEN)

        # Validate userB
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": self.valid_otp_values[1]},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertEqual("ACCEPT", result.get("authentication"))
            detail = data.get("detail")
            self.assertEqual("matching 1 tokens", detail.get("message"))
            auth_items = data.get("auth_items")
            self.assertIn("offline", auth_items)
            offline = auth_items.get("offline")
            # One offline entry
            self.assertEqual(1, len(offline))
            self.assertEqual("cornelius", offline[0].get("username"))
            serial = offline[0].get("serial")
            self.assertEqual("tokB", serial)
            refilltoken = offline[0].get("refilltoken")

        # Test refill
        with self.app.test_request_context('/validate/offlinerefill',
                                           method='POST',
                                           data={"serial": serial,
                                                 "refilltoken": refilltoken,
                                                 "pass": self.valid_otp_values[3]},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            auth_items = data.get("auth_items")
            self.assertIn("offline", auth_items)
            offline = auth_items.get("offline")
            self.assertEqual(1, len(offline))
            self.assertIn("serial", offline[0])

        # PassOnNoToken userC
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "usernotoken",
                                                 "pass": "sthelse"},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertTrue(result.get("value"))
            detail = data.get("detail")
            self.assertEqual("user has no token, accepted due to 'pol1'",
                             detail.get("message"))
            # No AuthItems for this user
            self.assertNotIn("auth_items", data)

        # Validate userA
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "shadow",
                                                 "pass": self.valid_otp_values[1]},
                                           environ_base={'REMOTE_ADDR': '192.168.0.2'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            result = data.get("result")
            self.assertEqual("ACCEPT", result.get("authentication"))
            detail = data.get("detail")
            self.assertEqual("matching 1 tokens", detail.get("message"))
            auth_items = data.get("auth_items")
            self.assertIn("offline", auth_items)
            offline = auth_items.get("offline")
            # One offline entry
            self.assertEqual(1, len(offline))
            self.assertEqual("shadow", offline[0].get("username"))