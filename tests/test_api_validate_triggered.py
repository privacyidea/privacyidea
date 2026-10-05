# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import time


from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.token import (init_token, remove_token)
from .base import MyApiTestCase



class TriggeredPoliciesTestCase(MyApiTestCase):

    def setUp(self):
        super(TriggeredPoliciesTestCase, self).setUp()
        self.setUp_user_realms()

    def test_00_two_policies(self):
        set_policy("otppin", scope=SCOPE.AUTH, action="{0!s}=none".format(PolicyAction.OTPPIN))
        set_policy("lastauth", scope=SCOPE.AUTHZ, action="{0!s}=1s".format(PolicyAction.LASTAUTH))

        # Create a Spass token
        init_token({"serial": "triggtoken", "type": "spass"})

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "triggtoken", "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertTrue(data.get("result").get("value"))

        # This authentication triggered the policy "otppin"
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"policies": "*otppin*"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get(
                "count"), 1)

        # Now wait a second and try to authenticate. Authentication should fail
        # due to policy "lastauth". Thus the policies "otppin" and "lastauth" are
        # triggered
        time.sleep(1.5)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "triggtoken", "pass": ""}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = res.json
            self.assertTrue(data.get("result").get("status"))
            self.assertFalse(data.get("result").get("value"))

        # This authentication triggered the policy "otppin" and "lastauth"
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           query_string={"policies": "*lastauth*"},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = res.json
            self.assertTrue(json_response.get("result").get("status"), res)
            self.assertEqual(json_response.get("result").get("value").get("count"), 1)
            # Both policies have triggered
            audit_policies = json_response.get("result").get("value").get("auditdata")[0].get("policies").split(",")
            self.assertEqual({"otppin", "lastauth"}, set(audit_policies))

        # clean up
        remove_token("triggtoken")
        delete_policy("otppin")
        delete_policy("lastauth")
