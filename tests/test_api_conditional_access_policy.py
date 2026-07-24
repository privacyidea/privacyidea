# (c) NetKnights GmbH 2026,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
CRUD tests for the ``/conditionalaccess/policy`` REST endpoints: create (POST),
read (GET), update (PATCH) and delete (DELETE) lockout policies, plus the
admin-policy gate (``lockout_policy_read`` / ``lockout_policy_write``) and the
admin-only access restriction.

Each endpoint x case has its own test method so a failure names exactly the
endpoint and case that broke.
"""
import json

from werkzeug.test import TestResponse

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.engine import LockoutAction
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.models import db
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.lockout_policy import (
    BlockList,
    LockoutPolicy,
    LockoutPolicyCounterType,
    LockoutPolicyStage,
    LockoutStageAction,
    UserLockoutState,
)
from .base import MyApiTestCase


class ConditionalAccessPolicyApiTestCase(MyApiTestCase):

    def setUp(self):
        super().setUp()
        self.authenticate()
        self._clear()

    def tearDown(self):
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear() -> None:
        for model in (UserLockoutState, BlockList, LockoutStageAction, LockoutPolicyStage,
                      LockoutPolicyCounterType, LockoutPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _request(self, path: str, method: str = "GET", json_data: dict | None = None,
                 auth_token: str | None = None) -> TestResponse:
        kwargs: dict = {"method": method, "headers": {"Authorization": auth_token or self.at}}
        if json_data is not None:
            kwargs["json"] = json_data
        with self.app.test_request_context(f"/conditionalaccess/{path}", **kwargs):
            return self.app.full_dispatch_request()

    @staticmethod
    def _policy_body(name: str = "API Policy", **overrides) -> dict:
        body = {"name": name,
                "time_window_seconds": 600,
                "target": "user",
                "counter_types_to_track": [str(AuthEventType.PIN_FAIL)],
                "stages": [{"failure_threshold": 5,
                            "actions": [{"action_type": str(LockoutAction.LOCK_USER),
                                         "action_value": {"lock_duration_seconds": 300}}]}]}
        body.update(overrides)
        return body

    def _create_policy(self, **overrides) -> int:
        res = self._request("policy", method="POST", json_data=self._policy_body(**overrides))
        self.assertEqual(200, res.status_code, res.json)
        return res.json["result"]["value"]

    # --- POST /policy (create) -------------------------------------------------

    def test_create_returns_new_id(self):
        policy_id = self._create_policy()
        self.assertIsInstance(policy_id, int)

    def test_create_missing_required_param_is_400(self):
        res = self._request("policy", method="POST", json_data={"name": "Broken"})
        self.assertEqual(400, res.status_code, res.json)

    def test_create_invalid_counter_type_is_400(self):
        res = self._request("policy", method="POST",
                            json_data=self._policy_body(counter_types_to_track=["BOGUS"]))
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("BOGUS", res.json["result"]["error"]["message"])

    def test_create_invalid_action_type_is_400(self):
        body = self._policy_body()
        body["stages"][0]["actions"][0]["action_type"] = "NOPE"
        res = self._request("policy", method="POST", json_data=body)
        self.assertEqual(400, res.status_code, res.json)

    def test_create_duplicate_name_is_400(self):
        self._create_policy(name="Dup")
        res = self._request("policy", method="POST", json_data=self._policy_body(name="Dup"))
        self.assertEqual(400, res.status_code, res.json)

    # --- target (user vs source_ip) --------------------------------------------

    def test_create_source_ip_policy(self):
        body = self._policy_body(name="Spray", target="source_ip",
                                 counter_types_to_track=[str(AuthEventType.PASSWORD_FAIL)],
                                 stages=[{"failure_threshold": 20,
                                          "actions": [{"action_type": str(LockoutAction.BLOCK_IP),
                                                       "action_value": {"duration_seconds": 3600}}]}])
        res = self._request("policy", method="POST", json_data=body)
        self.assertEqual(200, res.status_code, res.json)
        policy = self._request(f"policy/{res.json['result']['value']}").json["result"]["value"]
        self.assertEqual("source_ip", policy["target"])

    def test_create_without_target_is_400(self):
        # target is required (not defaulted): it decides counting and allowed actions.
        body = self._policy_body()
        del body["target"]
        res = self._request("policy", method="POST", json_data=body)
        self.assertEqual(400, res.status_code, res.json)

    def test_create_invalid_target_is_400(self):
        res = self._request("policy", method="POST", json_data=self._policy_body(target="planet"))
        self.assertEqual(400, res.status_code, res.json)

    def test_create_source_ip_deny_is_allowed(self):
        # ALLOW/DENY are valid on a source_ip policy (IP-scoped pre-auth decision).
        body = self._policy_body(name="IP deny", target="source_ip",
                                 counter_types_to_track=[str(AuthEventType.PASSWORD_FAIL)],
                                 stages=[{"failure_threshold": 20,
                                          "actions": [{"action_type": str(LockoutAction.DENY)}]}])
        res = self._request("policy", method="POST", json_data=body)
        self.assertEqual(200, res.status_code, res.json)

    def test_create_incompatible_action_for_target_is_400(self):
        # LOCK_USER (the default body's action) is not allowed under a source_ip policy.
        body = self._policy_body(name="Bad", target="source_ip",
                                 counter_types_to_track=[str(AuthEventType.PASSWORD_FAIL)])
        res = self._request("policy", method="POST", json_data=body)
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("source_ip", res.json["result"]["error"]["message"])

    def test_create_block_ip_under_user_target_is_400(self):
        body = self._policy_body(name="Bad2",
                                 stages=[{"failure_threshold": 5,
                                          "actions": [{"action_type": str(LockoutAction.BLOCK_IP),
                                                       "action_value": {"duration_seconds": 60}}]}])
        res = self._request("policy", method="POST", json_data=body)
        self.assertEqual(400, res.status_code, res.json)

    def test_patch_change_target_with_compatible_stages(self):
        # target may change as long as the new target/action combination is
        # compatible: flip a user policy to source_ip while swapping in BLOCK_IP.
        policy_id = self._create_policy()
        res = self._request(f"policy/{policy_id}", method="PATCH",
                            json_data={"target": "source_ip",
                                       "stages": [{"failure_threshold": 20,
                                                   "actions": [{"action_type": str(LockoutAction.BLOCK_IP),
                                                                "action_value": {"duration_seconds": 60}}]}]})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual("source_ip",
                         self._request(f"policy/{policy_id}").json["result"]["value"]["target"])

    def test_patch_change_target_incompatible_with_stages_is_400(self):
        # flipping to source_ip while the existing LOCK_USER stage remains is rejected
        policy_id = self._create_policy()
        res = self._request(f"policy/{policy_id}", method="PATCH", json_data={"target": "source_ip"})
        self.assertEqual(400, res.status_code, res.json)

    def test_patch_same_target_is_accepted(self):
        # echoing the unchanged target (full-object PATCH) is a compatible no-op
        policy_id = self._create_policy()
        res = self._request(f"policy/{policy_id}", method="PATCH",
                            json_data={"target": "user", "priority": 5})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(5, self._request(f"policy/{policy_id}").json["result"]["value"]["priority"])

    # --- GET /template (read templates) ----------------------------------------

    def test_list_templates_returns_full_catalog(self):
        res = self._request("template")
        self.assertEqual(200, res.status_code, res.json)
        catalog = {entry["key"]: entry for entry in res.json["result"]["value"]}
        self.assertIn("password_bruteforce", catalog)
        mfa = catalog["mfa_bruteforce"]
        self.assertTrue(mfa["description"].strip())
        self.assertEqual("user", mfa["policy"]["target"])
        self.assertListEqual([str(AuthEventType.MFA_FAIL)], mfa["policy"]["counter_types_to_track"])
        self.assertEqual(3, len(mfa["policy"]["stages"]))
        # the spraying template is source_ip-targeted and blocks the IP
        spray = catalog["password_spraying"]
        self.assertEqual("source_ip", spray["policy"]["target"])
        self.assertEqual(str(LockoutAction.BLOCK_IP),
                         spray["policy"]["stages"][0]["actions"][0]["action_type"])

    def test_template_policy_posts_verbatim(self):
        # the real client flow: fetch the catalog once, POST a template's policy
        catalog = {entry["key"]: entry for entry in self._request("template").json["result"]["value"]}
        res = self._request("policy", method="POST", json_data=catalog["password_bruteforce"]["policy"])
        self.assertEqual(200, res.status_code, res.json)

    # --- GET /policy and /policy/<id> (read) -----------------------------------

    def test_get_single_returns_full_policy(self):
        policy_id = self._create_policy()
        res = self._request(f"policy/{policy_id}")
        self.assertEqual(200, res.status_code, res.json)
        policy = res.json["result"]["value"]
        self.assertEqual("API Policy", policy["name"])
        self.assertListEqual([str(AuthEventType.PIN_FAIL)], policy["counter_types_to_track"])
        self.assertEqual(5, policy["stages"][0]["failure_threshold"])
        self.assertEqual(str(LockoutAction.LOCK_USER), policy["stages"][0]["actions"][0]["action_type"])

    def test_get_unknown_id_is_404(self):
        res = self._request("policy/424242")
        self.assertEqual(404, res.status_code, res.json)

    def test_list_returns_created_policies(self):
        policy_id = self._create_policy()
        res = self._request("policy")
        self.assertEqual(200, res.status_code, res.json)
        self.assertListEqual([policy_id], [p["id"] for p in res.json["result"]["value"]])

    def test_list_enabled_filter(self):
        policy_id = self._create_policy()
        self._request(f"policy/{policy_id}", method="PATCH", json_data={"enabled": False})
        self.assertListEqual([], self._request("policy?enabled=true").json["result"]["value"])
        self.assertListEqual([policy_id],
                             [p["id"] for p in self._request("policy?enabled=false").json["result"]["value"]])

    # --- GET /eventtypes and /actiontypes (constant lists) ---------------------

    def test_list_event_types(self):
        res = self._request("eventtypes")
        self.assertEqual(200, res.status_code, res.json)
        values = res.json["result"]["value"]
        self.assertListEqual([event_type.value for event_type in AuthEventType], values)
        self.assertIn(str(AuthEventType.PIN_FAIL), values)

    def test_list_action_types(self):
        res = self._request("actiontypes")
        self.assertEqual(200, res.status_code, res.json)
        values = res.json["result"]["value"]
        self.assertListEqual([action.value for action in LockoutAction], values)
        self.assertIn(str(LockoutAction.LOCK_USER), values)

    def test_list_targets(self):
        res = self._request("targets")
        self.assertEqual(200, res.status_code, res.json)
        actions_by_target = res.json["result"]["value"]
        self.assertSetEqual({"user", "source_ip"}, set(actions_by_target))
        self.assertIn(str(LockoutAction.LOCK_USER), actions_by_target["user"])
        self.assertNotIn(str(LockoutAction.LOCK_USER), actions_by_target["source_ip"])
        self.assertIn(str(LockoutAction.BLOCK_IP), actions_by_target["source_ip"])
        self.assertNotIn(str(LockoutAction.BLOCK_IP), actions_by_target["user"])

    # --- PATCH /policy/<id> (update) -------------------------------------------

    def test_patch_renames_and_replaces_stages(self):
        policy_id = self._create_policy()
        res = self._request(f"policy/{policy_id}", method="PATCH",
                            json_data={"name": "Renamed",
                                       "stages": [{"failure_threshold": 3,
                                                   "actions": [{"action_type": "DENY"}]}]})
        self.assertEqual(200, res.status_code, res.json)
        policy = self._request(f"policy/{policy_id}").json["result"]["value"]
        self.assertEqual("Renamed", policy["name"])
        self.assertEqual(3, policy["stages"][0]["failure_threshold"])

    def test_patch_leaves_unspecified_fields_untouched(self):
        policy_id = self._create_policy()
        self._request(f"policy/{policy_id}", method="PATCH", json_data={"name": "Renamed"})
        policy = self._request(f"policy/{policy_id}").json["result"]["value"]
        self.assertEqual(600, policy["time_window_seconds"])

    def test_patch_disable_then_enable(self):
        policy_id = self._create_policy()
        self._request(f"policy/{policy_id}", method="PATCH", json_data={"enabled": False})
        self.assertFalse(self._request(f"policy/{policy_id}").json["result"]["value"]["enabled"])
        self._request(f"policy/{policy_id}", method="PATCH", json_data={"enabled": True})
        self.assertTrue(self._request(f"policy/{policy_id}").json["result"]["value"]["enabled"])

    def test_patch_unknown_id_is_404(self):
        res = self._request("policy/424242", method="PATCH", json_data={"name": "X"})
        self.assertEqual(404, res.status_code, res.json)

    def test_patch_invalid_value_is_400(self):
        policy_id = self._create_policy()
        res = self._request(f"policy/{policy_id}", method="PATCH",
                            json_data={"time_window_seconds": -1})
        self.assertEqual(400, res.status_code, res.json)

    # --- DELETE /policy/<id> ---------------------------------------------------

    def test_delete_removes_policy_and_children(self):
        policy_id = self._create_policy()
        res = self._request(f"policy/{policy_id}", method="DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(404, self._request(f"policy/{policy_id}").status_code)
        self.assertEqual(0, db.session.query(LockoutPolicyStage).count())

    def test_delete_unknown_id_is_404(self):
        res = self._request("policy/424242", method="DELETE")
        self.assertEqual(404, res.status_code, res.json)

    # --- form-encoded structured params ----------------------------------------

    def test_create_form_encoded_string_time_window_is_400(self):
        # Form values arrive as strings; time_window_seconds is not converted, so
        # the positive-int validation rejects it. This documents that behavior.
        data = {"name": "Form Policy",
                "time_window_seconds": "600",
                "counter_types_to_track": json.dumps(["PIN_FAIL"]),
                "stages": json.dumps([{"failure_threshold": 5,
                                       "actions": [{"action_type": "LOCK_USER",
                                                    "action_value": {"lock_duration_seconds": 60}}]}])}
        with self.app.test_request_context("/conditionalaccess/policy", method="POST", data=data,
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(400, res.status_code, res.json)

    def test_create_form_encoded_malformed_json_is_400(self):
        data = {"name": "Form Policy",
                "time_window_seconds": "600",
                "counter_types_to_track": json.dumps(["PIN_FAIL"]),
                "stages": "{not json"}
        with self.app.test_request_context("/conditionalaccess/policy", method="POST", data=data,
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(400, res.status_code, res.json)

    # --- authorization ---------------------------------------------------------

    def test_read_requires_admin(self):
        self.setUp_user_realms()
        self.authenticate_selfservice_user()
        res = self._request("policy", auth_token=self.at_user)
        self.assertEqual(401, res.status_code, res.json)

    def test_write_requires_admin(self):
        self.setUp_user_realms()
        self.authenticate_selfservice_user()
        res = self._request("policy", method="POST", json_data=self._policy_body(),
                            auth_token=self.at_user)
        self.assertEqual(401, res.status_code, res.json)

    def test_read_only_admin_policy_allows_read(self):
        set_policy("ca_read_only", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.LOCKOUT_POLICY_READ))
        try:
            self.assertEqual(200, self._request("policy").status_code)
        finally:
            delete_policy("ca_read_only")

    def test_read_only_admin_policy_blocks_write(self):
        set_policy("ca_read_only", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.LOCKOUT_POLICY_READ))
        try:
            res = self._request("policy", method="POST", json_data=self._policy_body())
            self.assertEqual(403, res.status_code, res.json)
        finally:
            delete_policy("ca_read_only")

    def test_write_admin_policy_allows_write(self):
        set_policy("ca_write", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.LOCKOUT_POLICY_READ},"
                          f"{PolicyAction.LOCKOUT_POLICY_WRITE}")
        try:
            res = self._request("policy", method="POST", json_data=self._policy_body(name="Gated"))
            self.assertEqual(200, res.status_code, res.json)
        finally:
            delete_policy("ca_write")
