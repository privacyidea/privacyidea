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

from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType,
                                                                           CA_ENFORCEMENT_EVENT_TYPES,
                                                                           TRACKABLE_EVENT_TYPES, CountMode)
from privacyidea.lib.conditional_access.engine import LockoutAction
from privacyidea.lib.conditional_access.lockout_policy import (create_lockout_policy,
                                                               get_default_error_messages,
                                                               list_lockout_policies)
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.models import db
from privacyidea.lib.conditional_access.authentication_log import AuthLogUserRole
from privacyidea.lib.conditional_access.conditions import ConditionOperator, ConditionType
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.lockout_policy import (
    BlockList,
    LockoutPolicy,
    LockoutPolicyCondition,
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
                      LockoutPolicyCondition, LockoutPolicyCounterType, LockoutPolicy,
                      AuthenticationLog):
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
                "priority": 1,
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

    def test_create_duplicate_priority_is_400(self):
        # Priorities are unique across policies, so the evaluation order is never
        # ambiguous. The rejection names the policy already holding the priority.
        self._create_policy(name="First", priority=7)
        res = self._request("policy", method="POST",
                            json_data=self._policy_body(name="Second", priority=7))
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("First", res.json["result"]["error"]["message"])

    def test_create_free_priority_is_accepted(self):
        # The counterpart: a priority no other policy holds goes through.
        self._create_policy(name="First", priority=7)
        self._create_policy(name="Second", priority=8)

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

    def test_create_without_priority_is_400(self):
        # priority is a required create param (unique precedence, no default).
        body = self._policy_body()
        del body["priority"]
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
        # target may change as long as the new target/action AND target/count_mode combinations are compatible:
        # flip a user policy to source_ip while swapping in BLOCK_IP and the source_ip count_mode.
        policy_id = self._create_policy()
        res = self._request(f"policy/{policy_id}", method="PATCH",
                            json_data={"target": "source_ip",
                                       "count_mode": str(CountMode.DISTINCT_USERS),
                                       "stages": [{"failure_threshold": 20,
                                                   "actions": [{"action_type": str(LockoutAction.BLOCK_IP),
                                                                "action_value": {"duration_seconds": 60}}]}]})
        self.assertEqual(200, res.status_code, res.json)
        result = self._request(f"policy/{policy_id}").json["result"]["value"]
        self.assertEqual("source_ip", result["target"])
        self.assertEqual(str(CountMode.DISTINCT_USERS), result["count_mode"])

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
        # the real client flow: fetch the catalog once, add a priority, POST a template's policy
        catalog = {entry["key"]: entry for entry in self._request("template").json["result"]["value"]}
        policy = {**catalog["password_bruteforce"]["policy"], "priority": 1}
        res = self._request("policy", method="POST", json_data=policy)
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
        # retrigger_above_threshold defaults to False on a lock action when omitted.
        self.assertFalse(policy["stages"][0]["actions"][0]["retrigger_above_threshold"])

    def test_create_action_retrigger_flag_round_trips(self):
        # One stage, two actions with independent modes: the lock re-triggers, the
        # email fires once.
        body = self._policy_body(
            name="Retrig",
            stages=[{"failure_threshold": 8,
                     "actions": [{"action_type": str(LockoutAction.LOCK_USER),
                                  "action_value": {"lock_duration_seconds": 300},
                                  "retrigger_above_threshold": True},
                                 {"action_type": str(LockoutAction.EMAIL_ADMIN),
                                  "action_value": {"smtp_identifier": "x"},
                                  "retrigger_above_threshold": False}]}])
        res = self._request("policy", method="POST", json_data=body)
        self.assertEqual(200, res.status_code, res.json)
        policy = self._request(f"policy/{res.json['result']['value']}").json["result"]["value"]
        by_type = {action["action_type"]: action for action in policy["stages"][0]["actions"]}
        self.assertTrue(by_type[str(LockoutAction.LOCK_USER)]["retrigger_above_threshold"])
        self.assertFalse(by_type[str(LockoutAction.EMAIL_ADMIN)]["retrigger_above_threshold"])

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
        # The *trackable* subset, in definition order: what a policy may count.
        self.assertListEqual([event_type.value for event_type in TRACKABLE_EVENT_TYPES], values)
        self.assertIn(str(AuthEventType.PIN_FAIL), values)

    def test_list_event_types_omits_what_conditional_access_writes_itself(self):
        # Offering these would invite a policy that counts its own rejections, which is a lock that feeds itself. The
        # authentication log's own event-type list still has them, so an admin can filter for a rejection.
        values = self._request("eventtypes").json["result"]["value"]
        for event_type in CA_ENFORCEMENT_EVENT_TYPES:
            self.assertNotIn(str(event_type), values)

    def test_list_action_types(self):
        res = self._request("actiontypes")
        self.assertEqual(200, res.status_code, res.json)
        values = res.json["result"]["value"]
        self.assertListEqual([action.value for action in LockoutAction], values)
        self.assertIn(str(LockoutAction.LOCK_USER), values)

    def test_list_targets(self):
        res = self._request("targets")
        self.assertEqual(200, res.status_code, res.json)
        constraints = res.json["result"]["value"]
        self.assertSetEqual({"user", "source_ip"}, set(constraints))
        # Each target carries its allowed actions and supported count modes.
        self.assertIn(str(LockoutAction.LOCK_USER), constraints["user"]["actions"])
        self.assertNotIn(str(LockoutAction.LOCK_USER), constraints["source_ip"]["actions"])
        self.assertIn(str(LockoutAction.BLOCK_IP), constraints["source_ip"]["actions"])
        self.assertNotIn(str(LockoutAction.BLOCK_IP), constraints["user"]["actions"])
        # Volume modes are valid for both; DISTINCT_USERS is source_ip-only.
        self.assertListEqual([str(CountMode.PER_ATTEMPT), str(CountMode.PER_REQUEST)],
                             constraints["user"]["count_modes"])
        self.assertListEqual([str(CountMode.DISTINCT_USERS), str(CountMode.PER_ATTEMPT), str(CountMode.PER_REQUEST)],
                             constraints["source_ip"]["count_modes"])

    def test_list_default_error_messages(self):
        # Only the transport seam here: that the endpoint serves the catalog in the documented shape, and
        # that the lazy_gettext error message survives JSON encoding. Its ordering, categories and tag placement
        # are contracts of the catalog itself and are asserted in test_lib_conditional_access_policy.
        res = self._request("defaulterrormessages")
        self.assertEqual(200, res.status_code, res.json)
        suggestions = res.json["result"]["value"]
        self.assertEqual(len(get_default_error_messages()), len(suggestions))
        for entry in suggestions:
            self.assertSetEqual({"action_type", "category", "message"}, set(entry))
            self.assertTrue(entry["message"])

    def test_list_default_error_messages_requires_admin(self):
        res = self._request("defaulterrormessages", auth_token="not-a-token")
        self.assertEqual(401, res.status_code, res.json)

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

    def test_patch_to_used_priority_is_400(self):
        # Moving a policy onto a priority another policy holds collides; the
        # target policy keeps its own priority.
        self._create_policy(name="Holder", priority=3)
        policy_id = self._create_policy(name="Mover", priority=4)
        res = self._request(f"policy/{policy_id}", method="PATCH", json_data={"priority": 3})
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("Holder", res.json["result"]["error"]["message"])
        self.assertEqual(4, self._request(f"policy/{policy_id}").json["result"]["value"]["priority"])

    def test_patch_keeping_own_priority_is_allowed(self):
        # Re-sending a policy's current priority is not a self-collision.
        policy_id = self._create_policy(name="Solo", priority=3)
        res = self._request(f"policy/{policy_id}", method="PATCH",
                            json_data={"name": "Solo2", "priority": 3})
        self.assertEqual(200, res.status_code, res.json)
        policy = self._request(f"policy/{policy_id}").json["result"]["value"]
        self.assertEqual("Solo2", policy["name"])
        self.assertEqual(3, policy["priority"])

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
                "priority": "1",
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
                "priority": "1",
                "counter_types_to_track": json.dumps(["PIN_FAIL"]),
                "stages": "{not json"}
        with self.app.test_request_context("/conditionalaccess/policy", method="POST", data=data,
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(400, res.status_code, res.json)

    # --- PUT /policy/order (reorder) --------------------------------------------

    def _order(self) -> list[tuple[str, int]]:
        """
        The current evaluation order as (name, priority) pairs.
        """
        return [(policy["name"], policy["priority"]) for policy in list_lockout_policies()]

    def _numbered(self, *priorities) -> list[int]:
        """
        Create one policy per given priority, named after it, and return their ids.
        """
        return [create_lockout_policy(
            name=f"P{priority}", time_window_seconds=600,
            counter_types_to_track=[str(AuthEventType.PIN_FAIL)],
            stages=[{"failure_threshold": 5,
                     "actions": [{"action_type": str(LockoutAction.LOCK_USER),
                                  "action_value": {"lock_duration_seconds": 300}}]}],
            target="user", priority=priority) for priority in priorities]

    def test_reorder_swaps_two_policies(self):
        first, second = self._numbered(1, 2)
        res = self._request("policy/order", method="PUT", json_data={"policy_ids": [second, first]})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_reorder_subset_leaves_other_policies_untouched(self):
        self._numbered(1, 2, 3)
        ids = {policy["name"]: policy["id"] for policy in list_lockout_policies()}
        res = self._request("policy/order", method="PUT",
                            json_data={"policy_ids": [ids["P3"], ids["P2"]]})
        self.assertEqual(200, res.status_code, res.json)
        self.assertListEqual([("P1", 1), ("P3", 2), ("P2", 3)], self._order())

    def test_reorder_preserves_gapped_numbering(self):
        low, mid, high = self._numbered(10, 20, 30)
        self._request("policy/order", method="PUT", json_data={"policy_ids": [high, low, mid]})
        self.assertListEqual([("P30", 10), ("P10", 20), ("P20", 30)], self._order())

    def test_reorder_is_idempotent(self):
        first, second = self._numbered(1, 2)
        for _ in range(2):
            res = self._request("policy/order", method="PUT", json_data={"policy_ids": [first, second]})
            self.assertEqual(200, res.status_code, res.json)
        self.assertListEqual([("P1", 1), ("P2", 2)], self._order())

    def test_reorder_without_policy_ids_is_400(self):
        res = self._request("policy/order", method="PUT", json_data={})
        self.assertEqual(400, res.status_code, res.json)

    def test_reorder_empty_list_is_400(self):
        res = self._request("policy/order", method="PUT", json_data={"policy_ids": []})
        self.assertEqual(400, res.status_code, res.json)

    def test_reorder_duplicate_id_is_400(self):
        first, second = self._numbered(1, 2)
        res = self._request("policy/order", method="PUT", json_data={"policy_ids": [first, first]})
        self.assertEqual(400, res.status_code, res.json)
        self.assertListEqual([("P1", 1), ("P2", 2)], self._order())

    def test_reorder_unknown_id_is_404(self):
        first, second = self._numbered(1, 2)
        res = self._request("policy/order", method="PUT",
                            json_data={"policy_ids": [second, first, 424242]})
        self.assertEqual(404, res.status_code, res.json)
        # nothing was moved
        self.assertListEqual([("P1", 1), ("P2", 2)], self._order())

    def test_reorder_route_coexists_with_the_policy_id_route(self):
        # 'policy/<policy_id>' uses a string converter, so the literal 'policy/order'
        # also matches it. Only PUT is routed to the reorder endpoint; the other verbs
        # fall through to the id route and must fail cleanly on the non-numeric id
        # rather than acting on some policy.
        first, second = self._numbered(1, 2)
        self.assertEqual(200, self._request("policy/order", method="PUT",
                                            json_data={"policy_ids": [second, first]}).status_code)
        for method in ("GET", "PATCH", "DELETE"):
            res = self._request("policy/order", method=method, json_data={})
            self.assertEqual(400, res.status_code, f"{method}: {res.json}")
            self.assertIn("Invalid policy id", res.json["result"]["error"]["message"])
        # the reorder above is still the only change that happened
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_reorder_requires_write_permission(self):
        first, second = self._numbered(1, 2)
        set_policy("ca_read_only", scope=SCOPE.ADMIN, action=str(PolicyAction.LOCKOUT_POLICY_READ))
        try:
            res = self._request("policy/order", method="PUT", json_data={"policy_ids": [second, first]})
            self.assertEqual(403, res.status_code, res.json)
        finally:
            delete_policy("ca_read_only")

    def test_reorder_with_matching_expected_priorities(self):
        first, second = self._numbered(1, 2)
        res = self._request("policy/order", method="PUT",
                            json_data={"policy_ids": [second, first], "expected_priorities": [2, 1]})
        self.assertEqual(200, res.status_code, res.json)
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_reorder_with_stale_expected_priorities_is_409(self):
        # Another admin rearranged in between: refuse rather than silently overwriting.
        first, second = self._numbered(1, 2)
        self._request("policy/order", method="PUT", json_data={"policy_ids": [second, first]})
        res = self._request("policy/order", method="PUT",
                            json_data={"policy_ids": [second, first], "expected_priorities": [2, 1]})
        self.assertEqual(409, res.status_code, res.json)
        message = res.json["result"]["error"]["message"]
        # Names the mismatching policy; deliberately no priority numbers and no advice
        # about what the client should do next.
        self.assertIn("P2", message)
        self.assertIn("expected priorities", message)
        self.assertNotIn("Reload", message)
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_reorder_of_disjoint_rows_does_not_conflict(self):
        # Two admins rearranging different parts of the list both succeed - the whole
        # reason the client sends only the rows it moved.
        self._numbered(1, 2, 3, 4)
        ids = {policy["name"]: policy["id"] for policy in list_lockout_policies()}
        self.assertEqual(200, self._request("policy/order", method="PUT",
                                            json_data={"policy_ids": [ids["P4"], ids["P3"]],
                                                       "expected_priorities": [4, 3]}).status_code)
        self.assertEqual(200, self._request("policy/order", method="PUT",
                                            json_data={"policy_ids": [ids["P2"], ids["P1"]],
                                                       "expected_priorities": [2, 1]}).status_code)
        self.assertListEqual([("P2", 1), ("P1", 2), ("P4", 3), ("P3", 4)], self._order())

    def test_reorder_mismatched_expected_priorities_length_is_400(self):
        first, second = self._numbered(1, 2)
        res = self._request("policy/order", method="PUT",
                            json_data={"policy_ids": [second, first], "expected_priorities": [2]})
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

    # --- conditions ------------------------------------------------------------

    def test_list_condition_types(self):
        self.setUp_user_realms()
        res = self._request("conditiontypes")
        self.assertEqual(200, res.status_code, res.json)
        metadata = res.json["result"]["value"]
        self.assertSetEqual({str(ConditionType.USER_REALM), str(ConditionType.USER_ROLE)}, set(metadata))
        realm_entry = metadata[str(ConditionType.USER_REALM)]
        self.assertListEqual([str(ConditionOperator.IN), str(ConditionOperator.NOT_IN)],
                             [operator["name"] for operator in realm_entry["operators"]])
        # choices are resolved per call, so a realm created in this test shows up.
        self.assertIn(self.realm1, realm_entry["choices"])

    def test_create_with_conditions_round_trips(self):
        policy_id = self._create_policy(
            conditions=[{"condition_type": str(ConditionType.USER_ROLE),
                         "operator": str(ConditionOperator.IN),
                         "value": [str(AuthLogUserRole.USER)]}])
        res = self._request(f"policy/{policy_id}")
        self.assertEqual(200, res.status_code, res.json)
        conditions = res.json["result"]["value"]["conditions"]
        self.assertEqual(1, len(conditions))
        self.assertEqual(str(ConditionType.USER_ROLE), conditions[0]["condition_type"])
        self.assertListEqual([str(AuthLogUserRole.USER)], conditions[0]["value"])

    def test_create_without_conditions_yields_empty_list(self):
        policy_id = self._create_policy()
        res = self._request(f"policy/{policy_id}")
        self.assertListEqual([], res.json["result"]["value"]["conditions"])

    def test_create_with_invalid_condition_is_400(self):
        res = self._request("policy", method="POST", json_data=self._policy_body(
            conditions=[{"condition_type": "NO_SUCH_TYPE", "operator": "IN", "value": ["x"]}]))
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("NO_SUCH_TYPE", res.json["result"]["error"]["message"])

    def test_patch_replaces_and_clears_conditions(self):
        policy_id = self._create_policy(
            conditions=[{"condition_type": str(ConditionType.USER_ROLE),
                         "operator": str(ConditionOperator.IN),
                         "value": [str(AuthLogUserRole.USER)]}])
        res = self._request(f"policy/{policy_id}", method="PATCH", json_data={
            "conditions": [{"condition_type": str(ConditionType.USER_ROLE),
                            "operator": str(ConditionOperator.NOT_IN),
                            "value": [str(AuthLogUserRole.ADMIN_INTERNAL)]}]})
        self.assertEqual(200, res.status_code, res.json)
        conditions = self._request(f"policy/{policy_id}").json["result"]["value"]["conditions"]
        self.assertEqual(str(ConditionOperator.NOT_IN), conditions[0]["operator"])
        # An empty list removes every condition, widening the policy to all requests.
        self._request(f"policy/{policy_id}", method="PATCH", json_data={"conditions": []})
        self.assertListEqual([], self._request(f"policy/{policy_id}").json["result"]["value"]["conditions"])

    def test_create_with_stage_error_message_round_trips(self):
        message = "Your account is locked. Please try again in about {duration}."
        stages = self._policy_body()["stages"]
        stages[0]["error_message"] = message
        policy_id = self._create_policy(stages=stages)
        stages = self._request(f"policy/{policy_id}").json["result"]["value"]["stages"]
        self.assertEqual(message, stages[0]["error_message"])

    def test_create_without_stage_error_message_yields_none(self):
        # The default is silence: with no message the rejection stays generic.
        policy_id = self._create_policy()
        stages = self._request(f"policy/{policy_id}").json["result"]["value"]["stages"]
        self.assertIsNone(stages[0]["error_message"])

    def test_create_with_over_long_stage_error_message_is_400(self):
        body = self._policy_body()
        body["stages"][0]["error_message"] = "x" * 501
        res = self._request("policy", method="POST", json_data=body)
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("500", res.json["result"]["error"]["message"])

    def test_patch_replaces_and_clears_the_stage_error_message(self):
        stages = self._policy_body()["stages"]
        stages[0]["error_message"] = "Old."
        policy_id = self._create_policy(stages=stages)
        patched = [{**stages[0], "error_message": "New."}]
        res = self._request(f"policy/{policy_id}", method="PATCH", json_data={"stages": patched})
        self.assertEqual(200, res.status_code, res.json)
        stages = self._request(f"policy/{policy_id}").json["result"]["value"]["stages"]
        self.assertEqual("New.", stages[0]["error_message"])
        # Stages are replaced wholesale, so a stage sent without a message clears it.
        cleared = [{key: value for key, value in patched[0].items() if key != "error_message"}]
        self._request(f"policy/{policy_id}", method="PATCH", json_data={"stages": cleared})
        stages = self._request(f"policy/{policy_id}").json["result"]["value"]["stages"]
        self.assertIsNone(stages[0]["error_message"])
