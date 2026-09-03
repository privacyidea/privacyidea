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
Tests for the conditional-access policy CRUD layer
(:mod:`privacyidea.lib.conditional_access.policy`).
"""

from unittest import mock

from privacyidea.lib.conditional_access import policy as policy_module
from privacyidea.lib.conditional_access.authentication_event_types import CA_ENFORCEMENT_EVENT_TYPES  # noqa: F401
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, CountMode
from privacyidea.lib.conditional_access.authentication_log import AuthLogUserRole
from privacyidea.lib.conditional_access.conditions import (ConditionOperator, ConditionType,
                                                           get_condition_types)
from privacyidea.lib.conditional_access.engine import (ACTION_SEVERITY, ConditionalAccessAction, ConditionalAccessTarget,
                                                       RESTRICTION_ACTIONS)
from privacyidea.lib.conditional_access.policy import (
    DEFAULT_ERROR_MESSAGES,
    _ACTION_VALUE_VALIDATORS,
    _ACTIONS_BY_TARGET,
    _COUNT_MODES_BY_TARGET,
    _DEFAULT_COUNT_MODE_BY_TARGET,
    MAX_ERROR_MESSAGE_LENGTH,
    compose_default_error_message,
    create_conditional_access_policy,
    default_error_message,
    delete_conditional_access_policy,
    enable_conditional_access_policy,
    get_default_error_messages,
    get_conditional_access_policy,
    get_target_constraints,
    list_conditional_access_policies,
    reorder_conditional_access_policies,
    update_conditional_access_policy,
)
from privacyidea.lib.error import ConflictError, ParameterError, ResourceNotFoundError
from privacyidea.models import db
from privacyidea.models.conditional_access_policy import (
    ConditionalAccessPolicy,
    ConditionalAccessPolicyCondition,
    ConditionalAccessPolicyCounterType,
    ConditionalAccessPolicyStage,
    ConditionalAccessStageAction,
)

from .base import MyTestCase


def _stage(threshold=5, actions=None, retrigger=False):
    if actions is None:
        actions = [{"action_type": "LOCK_USER", "action_value": {"duration_seconds": 600}}]
    # retrigger is per action; apply it to each action of this stage.
    actions = [{**action, "retrigger_above_threshold": retrigger} for action in actions]
    return {"failure_threshold": threshold, "actions": actions}


def _block_ip_stage(threshold=5):
    """A stage whose action is valid under a source_ip target (BLOCK_IP), unlike _stage's LOCK_USER default."""
    return _stage(threshold,
                  actions=[{"action_type": str(ConditionalAccessAction.BLOCK_IP),
                            "action_value": {"duration_seconds": 60}}])


class ConditionalAccessPolicyCrudTestCase(MyTestCase):
    def setUp(self):
        self._clear()

    def tearDown(self):
        self._clear()

    @staticmethod
    def _clear():
        # Roll back anything a failed CRUD call left pending, then delete all rows; expunge_all clears the identity map
        # so a test's stale loaded object can't collide with a later test reusing the same primary key, mirroring the
        # per-request session teardown that isolates this in production.
        db.session.rollback()
        for model in (ConditionalAccessStageAction, ConditionalAccessPolicyStage, ConditionalAccessPolicyCondition,
                      ConditionalAccessPolicyCounterType, ConditionalAccessPolicy):
            db.session.query(model).delete()
        db.session.commit()
        db.session.expunge_all()

    def test_01_create_and_get(self):
        policy_id = create_conditional_access_policy(
            "Brute Force", 600, ["PIN_FAIL", "MFA_FAIL"],
            stages=[_stage(5),
                    _stage(10,
                           actions=[{"action_type": "PERMANENT_LOCK_USER", "action_value": None},
                                    {"action_type": "EMAIL_ADMIN",
                                     "action_value": {"smtp_identifier": "mock",
                                                      "subject": "Locked", "body": "{username} is locked."}}])],
            target=ConditionalAccessTarget.USER, priority=3)
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual("Brute Force", policy["name"])
        self.assertEqual(600, policy["time_window_seconds"])
        self.assertTrue(policy["enabled"])
        self.assertFalse(policy["dry_run"])
        self.assertEqual(3, policy["priority"])
        self.assertEqual(CountMode.PER_REQUEST, policy["count_mode"])
        self.assertEqual(["PIN_FAIL", "MFA_FAIL"], policy["counter_types_to_track"])
        self.assertEqual(2, len(policy["stages"]))
        # stages are ordered by ascending failure_threshold (first to trigger first)
        self.assertEqual(5, policy["stages"][0]["failure_threshold"])
        self.assertEqual(10, policy["stages"][1]["failure_threshold"])
        self.assertEqual(2, len(policy["stages"][1]["actions"]))
        self.assertEqual({"duration_seconds": 600}, policy["stages"][0]["actions"][0]["action_value"])
        # A successful login clears the counted events unless the policy says otherwise.
        self.assertTrue(policy["reset_on_success"])
        # retrigger_above_threshold defaults to False on a lock action (fire once).
        self.assertFalse(policy["stages"][0]["actions"][0]["retrigger_above_threshold"])

    def test_01b_action_retrigger_flag_round_trips(self):
        # The per-action retrigger_above_threshold checkbox round-trips within one
        # stage: the lock action re-triggers while the email fires once.
        policy_id = create_conditional_access_policy(
            "Retrig", 600, ["PIN_FAIL"],
            stages=[{"failure_threshold": 8,
                     "actions": [{"action_type": "LOCK_USER",
                                  "action_value": {"duration_seconds": 300},
                                  "retrigger_above_threshold": True},
                                 {"action_type": "EMAIL_ADMIN",
                                  "action_value": {"smtp_identifier": "x", "subject": "s", "body": "b"},
                                  "retrigger_above_threshold": False}]}],
            target=ConditionalAccessTarget.USER, priority=1)
        policy = get_conditional_access_policy(policy_id)
        by_type = {action["action_type"]: action for action in policy["stages"][0]["actions"]}
        self.assertTrue(by_type["LOCK_USER"]["retrigger_above_threshold"])
        self.assertFalse(by_type["EMAIL_ADMIN"]["retrigger_above_threshold"])

    def test_01c_retrigger_default_is_action_aware(self):
        # When the client omits retrigger_above_threshold, the standing DENY verdict
        # defaults to re-trigger and the lock/email/block effects to fire-once.
        policy_id = create_conditional_access_policy(
            "Defaults", 600, ["PIN_FAIL"],
            stages=[{"failure_threshold": 3, "actions": [{"action_type": "DENY"}]},
                    {"failure_threshold": 5,
                     "actions": [{"action_type": "LOCK_USER",
                                  "action_value": {"duration_seconds": 60}}]}],
            target=ConditionalAccessTarget.USER, priority=1)
        policy = get_conditional_access_policy(policy_id)
        by_threshold = {stage["failure_threshold"]: stage for stage in policy["stages"]}
        self.assertTrue(by_threshold[3]["actions"][0]["retrigger_above_threshold"])  # DENY
        self.assertFalse(by_threshold[5]["actions"][0]["retrigger_above_threshold"])  # LOCK_USER

    def test_01d_threshold_zero_is_only_for_standing_decisions(self):
        # A threshold counts failures, so anything reacting to a count starts at 1. DENY states a standing
        # verdict instead, so 0 means "always": the lockdown idiom.
        usr = ConditionalAccessTarget.USER
        policy_id = create_conditional_access_policy(
            "zero_deny", 600, ["PIN_FAIL"],
            [{"failure_threshold": 0, "actions": [{"action_type": "DENY"}]}],
            target=usr, priority=1)
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual(0, policy["stages"][0]["failure_threshold"])
        delete_conditional_access_policy(policy_id)

        # Everything that reacts to a count is refused at 0, as is a stage with no action to justify it.
        for stage in ([{"failure_threshold": 0, "actions": [{"action_type": "LOCK_USER",
                                                             "action_value": {"duration_seconds": 60}}]}],
                      [{"failure_threshold": 0, "actions": [{"action_type": "EMAIL_ADMIN"}]}],
                      # A mixed stage is refused too: the LOCK_USER half would fire at zero failures.
                      [{"failure_threshold": 0, "actions": [{"action_type": "DENY"},
                                                            {"action_type": "LOCK_USER",
                                                             "action_value": {"duration_seconds": 60}}]}],
                      [{"failure_threshold": 0, "actions": []}]):
            self.assertRaises(ParameterError, create_conditional_access_policy, "zero_bad", 600, ["PIN_FAIL"],
                              stage, target=usr, priority=1)

    def test_02_create_validation_errors(self):
        valid = dict(
            time_window_seconds=600,
            counter_types_to_track=["PIN_FAIL"],
            stages=[_stage()],
            target=ConditionalAccessTarget.USER,
            priority=1,
        )
        # name
        self.assertRaises(ParameterError, create_conditional_access_policy, "", **valid)
        self.assertRaises(ParameterError, create_conditional_access_policy, None, **valid)
        self.assertRaises(ParameterError, create_conditional_access_policy, "x" * 256, **valid)
        # duplicate name
        create_conditional_access_policy("Taken", **valid)
        self.assertRaises(ParameterError, create_conditional_access_policy, "Taken", **valid)
        self.assertRaises(ParameterError, create_conditional_access_policy, "  Taken  ", **valid)
        usr = ConditionalAccessTarget.USER
        # window / priority; a valid, unique priority keeps the intended later check the one that raises
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 0, ["PIN_FAIL"], [_stage()],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", "600", ["PIN_FAIL"], [_stage()],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"], [_stage()],
                          target=usr, priority=0)
        # target
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"], [_stage()],
                          target="planet", priority=2)
        # counter types
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, [], [_stage()],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["NOT_A_TYPE"], [_stage()],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, "PIN_FAIL", [_stage()],
                          target=usr, priority=2)
        # stages
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"], [],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"], None,
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"],
                          [{"name": "no threshold"}], target=usr, priority=2)  # missing threshold
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(5), _stage(5)], target=usr, priority=2)  # duplicate threshold
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "bogus": 1}], target=usr, priority=2)  # unknown stage key
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"],
                          [5], target=usr, priority=2)  # stage is not a dict
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"],
                # actions not a list
                          [{"failure_threshold": 5, "actions": "notalist"}], target=usr, priority=2)
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "actions": [42]}], target=usr, priority=2)  # action not a dict
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "NOT_AN_ACTION"}])], target=usr, priority=2)
        self.assertRaises(ParameterError, create_conditional_access_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "LOCK_USER", "bogus": 1}])], target=usr, priority=2)
        # nothing invalid was persisted
        self.assertEqual(1, db.session.query(ConditionalAccessPolicy).count())

    def test_02c_count_mode_per_attempt(self):
        # PER_ATTEMPT tracks the same AuthEventType vocabulary; only the counting unit differs.
        policy_id = create_conditional_access_policy(
            "RateLimit",
            60,
            [AuthEventType.MFA_FAIL, AuthEventType.LOGIN_SUCCESS],
            [_stage(10)],
            target=ConditionalAccessTarget.USER,
            count_mode=CountMode.PER_ATTEMPT,
            priority=1,
        )
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual(CountMode.PER_ATTEMPT, policy["count_mode"])
        self.assertEqual([AuthEventType.MFA_FAIL, AuthEventType.LOGIN_SUCCESS], policy["counter_types_to_track"])

    def test_02d_count_mode_validation(self):
        # An unknown mode is rejected as such (not, say, mistaken for a target error).
        self.assertRaisesRegex(
            ParameterError,
            "Unknown count_mode 'SOMETHING'",
            create_conditional_access_policy,
            "P",
            600,
            [AuthEventType.PIN_FAIL],
            [_stage()],
            target=ConditionalAccessTarget.USER,
            count_mode="SOMETHING",
            priority=1,
        )
        self.assertEqual(0, db.session.query(ConditionalAccessPolicy).count())

    def test_02e_update_count_mode(self):
        # Switching the mode alone is allowed (the vocabulary is shared); the tracked counters are untouched.
        policy_id = create_conditional_access_policy(
            "Switch", 600, [AuthEventType.PIN_FAIL], [_stage()], target=ConditionalAccessTarget.USER, priority=1
        )
        update_conditional_access_policy(policy_id, count_mode=CountMode.PER_ATTEMPT)
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual(CountMode.PER_ATTEMPT, policy["count_mode"])
        self.assertEqual([AuthEventType.PIN_FAIL], policy["counter_types_to_track"])

    def _ip_stage(self, threshold=20):
        return _stage(threshold, actions=[{"action_type": "BLOCK_IP", "action_value": {"duration_seconds": 3600}}])

    def test_02f_count_mode_defaults_per_target(self):
        # No count_mode given: a user policy defaults to PER_REQUEST, a source_ip policy to DISTINCT_USERS,
        # so the stored value always states what the policy actually counts.
        user_id = create_conditional_access_policy("U", 600, ["PIN_FAIL"], [_stage()],
                target=ConditionalAccessTarget.USER, priority=1)
        self.assertEqual(CountMode.PER_REQUEST, get_conditional_access_policy(user_id)["count_mode"])
        ip_id = create_conditional_access_policy(
            "I", 300, ["PASSWORD_FAIL"], [self._ip_stage()], target=ConditionalAccessTarget.SOURCE_IP, priority=2
        )
        self.assertEqual(CountMode.DISTINCT_USERS, get_conditional_access_policy(ip_id)["count_mode"])

    def test_02g_count_mode_target_compatibility(self):
        # DISTINCT_USERS is the one mode specific to source_ip (there is no distinct-accounts notion for a single user),
        # so it is the only incompatible target/mode pair and is rejected before anything is written; the volume modes
        # are valid for either target.
        self.assertRaisesRegex(
            ParameterError,
            "count_mode 'DISTINCT_USERS' is not allowed for target 'user'",
            create_conditional_access_policy,
            "P",
            600,
            ["PIN_FAIL"],
            [_stage()],
            target=ConditionalAccessTarget.USER,
            count_mode=CountMode.DISTINCT_USERS,
            priority=1,
        )
        self.assertEqual(0, db.session.query(ConditionalAccessPolicy).count())
        # source_ip accepts either volume mode as well as its DISTINCT_USERS default, storing exactly what was asked.
        for index, mode in enumerate((CountMode.PER_REQUEST, CountMode.PER_ATTEMPT), start=1):
            policy_id = create_conditional_access_policy(
                f"IP-{mode.value}",
                300,
                ["PASSWORD_FAIL"],
                [self._ip_stage()],
                target=ConditionalAccessTarget.SOURCE_IP,
                count_mode=mode,
                priority=index,
            )
            self.assertEqual(mode, get_conditional_access_policy(policy_id)["count_mode"])

    def test_02h_update_target_revalidates_count_mode(self):
        # Switching a source_ip policy (default DISTINCT_USERS) to user without also fixing the mode is rejected: the
        # effective (target, count_mode) pair is validated, not just each field in isolation. (The compatible switch
        # that also supplies a volume count_mode is covered end-to-end by the API test suite.)
        reject_id = create_conditional_access_policy(
            "Reject", 300, ["PASSWORD_FAIL"], [self._ip_stage()], target=ConditionalAccessTarget.SOURCE_IP, priority=1
        )
        # Assert on the message so a stage/action-compatibility error cannot masquerade as the count_mode rejection
        # (the stages here are deliberately LOCK_USER, i.e. already target-compatible, so only count_mode can fail).
        self.assertRaisesRegex(
            ParameterError,
            "count_mode 'DISTINCT_USERS' is not allowed for target 'user'",
            update_conditional_access_policy,
            reject_id,
            target=ConditionalAccessTarget.USER,
            stages=[_stage()],
        )

    def test_02i_update_source_ip_accepts_volume_count_mode(self):
        # A source_ip policy can be switched from its DISTINCT_USERS default to a volume mode (plain per-IP rate
        # limiting); the new mode is stored.
        ip_id = create_conditional_access_policy(
            "Spray", 300, ["PASSWORD_FAIL"], [self._ip_stage()], target=ConditionalAccessTarget.SOURCE_IP, priority=1
        )
        update_conditional_access_policy(ip_id, count_mode=CountMode.PER_ATTEMPT)
        self.assertEqual(CountMode.PER_ATTEMPT, get_conditional_access_policy(ip_id)["count_mode"])

    def test_02b_duplicate_counter_types_are_deduplicated(self):
        # A repeated counter type is silently de-duplicated (order preserved),
        # not rejected: tracking the same event type twice has no effect.
        policy_id = create_conditional_access_policy(
            "Dedup", 600, ["MFA_FAIL", "PIN_FAIL",
                    "MFA_FAIL"], [_stage()], target=ConditionalAccessTarget.USER, priority=1
        )
        self.assertEqual(["MFA_FAIL", "PIN_FAIL"], get_conditional_access_policy(policy_id)["counter_types_to_track"])

    def test_02c_event_types_written_by_conditional_access_are_not_trackable(self):
        # A policy counting its own rejections is a lock that feeds itself: while the user is locked, every request adds
        # to the count, so a re-triggering lock never expires and no successful login can clear it; refusing the value
        # at the CRUD boundary makes that impossible rather than merely discouraged.
        for event_type in CA_ENFORCEMENT_EVENT_TYPES:
            self.assertRaises(
                ParameterError,
                create_conditional_access_policy,
                f"Self feeding {event_type}", 600, [str(event_type)], [_stage()],
                target=ConditionalAccessTarget.USER, priority=1,
            )

    def test_02j_target_action_compatibility(self):
        # BLOCK_IP only makes sense on a source_ip target; LOCK_USER only on a user target. Both actions carry a
        # valid duration so the rejection is pinned to the target mismatch rather than to the action_value check,
        # which runs first (_validate_stages before _validate_target_actions).
        self.assertRaisesRegex(
            ParameterError,
            "not allowed for target 'user'",
            create_conditional_access_policy,
            "P",
            600,
            ["PIN_FAIL"],
            [_stage(actions=[{"action_type": "BLOCK_IP", "action_value": 3600}])],
            target=ConditionalAccessTarget.USER,
            priority=1,
        )
        self.assertRaisesRegex(
            ParameterError,
            "not allowed for target 'source_ip'",
            create_conditional_access_policy,
            "P",
            600,
            ["PIN_FAIL"],
            [_stage(actions=[{"action_type": "LOCK_USER", "action_value": 600}])],
            target=ConditionalAccessTarget.SOURCE_IP,
            priority=2,
        )
        # a source_ip policy may block the offending IP
        create_conditional_access_policy(
            "Spray",
            300,
            ["PIN_FAIL"],
            [_stage(20, actions=[{"action_type": "BLOCK_IP", "action_value": {"duration_seconds": 3600}}])],
            target=ConditionalAccessTarget.SOURCE_IP,
            priority=3,
        )

    def _create_with_action(self, action, target=ConditionalAccessTarget.USER, name="P", priority=1):
        """Create a one-stage policy carrying exactly *action*, for the action_value validation tests."""
        return create_conditional_access_policy(name, 600, ["PIN_FAIL"], [_stage(actions=[action])],
                                     target=target, priority=priority)

    def test_02k_lock_user_requires_a_positive_duration(self):
        # A LOCK_USER the engine could not act on must not be storable: without a duration it is skipped at
        # runtime with only a log line, so the admin sees a saved policy that never locks anyone.
        for action_value in (None, 0, -5, True, "abc", {}):
            self.assertRaisesRegex(
                ParameterError, "duration",
                self._create_with_action, {"action_type": "LOCK_USER", "action_value": action_value},
            )
        # The legacy key is named in the error rather than reported as a generic "no duration".
        self.assertRaisesRegex(
            ParameterError, "lock_duration_seconds",
            self._create_with_action,
            {"action_type": "LOCK_USER", "action_value": {"lock_duration_seconds": 600}},
        )
        self.assertEqual(0, db.session.query(ConditionalAccessPolicy).count())

    def test_02l_lock_user_accepts_every_shape_the_engine_reads(self):
        # Whatever parse_lock_duration_seconds accepts is storable, and is stored verbatim: normalizing here
        # would make the round-trip a different thing from what the admin sent.
        for index, action_value in enumerate((600, "600", {"duration_seconds": 600}, {"duration": 600}), start=1):
            policy_id = self._create_with_action({"action_type": "LOCK_USER", "action_value": action_value},
                                                 name=f"P{index}", priority=index)
            policy = get_conditional_access_policy(policy_id)
            self.assertEqual(action_value, policy["stages"][0]["actions"][0]["action_value"])

    def test_02m_block_ip_requires_a_positive_duration(self):
        self.assertRaisesRegex(
            ParameterError, "duration",
            self._create_with_action, {"action_type": "BLOCK_IP", "action_value": None},
            ConditionalAccessTarget.SOURCE_IP,
        )
        self._create_with_action({"action_type": "BLOCK_IP", "action_value": 3600}, ConditionalAccessTarget.SOURCE_IP)

    def test_02n_duration_action_value_rejects_an_unknown_key(self):
        # A valid duration next to a key nothing reads is still a mistake worth reporting: the admin who wrote
        # it believes it does something.
        self.assertRaisesRegex(
            ParameterError, "lock_duration_seconds",
            self._create_with_action,
            {"action_type": "LOCK_USER", "action_value": {"duration_seconds": 600, "lock_duration_seconds": 600}},
        )

    def test_02o_permanent_and_decision_actions_take_no_action_value(self):
        # These never read action_value, so a duration on one of them describes an expiry that never comes.
        for index, action_type in enumerate(("PERMANENT_LOCK_USER", "DENY"), start=1):
            self.assertRaisesRegex(
                ParameterError, "takes no action_value",
                self._create_with_action, {"action_type": action_type, "action_value": 600},
                ConditionalAccessTarget.USER, f"P{index}", index,
            )
        self.assertRaisesRegex(
            ParameterError, "takes no action_value",
            self._create_with_action, {"action_type": "PERMANENT_BLOCK_IP", "action_value": 600},
            ConditionalAccessTarget.SOURCE_IP,
        )
        # An explicit null and an omitted key are both fine.
        self._create_with_action({"action_type": "PERMANENT_LOCK_USER", "action_value": None}, name="Null")
        self._create_with_action({"action_type": "DENY"}, name="Omitted", priority=2)

    def test_02p_email_action_requires_subject_and_body(self):
        self.assertRaisesRegex(
            ParameterError, "'subject'",
            self._create_with_action,
            {"action_type": "EMAIL_ADMIN", "action_value": {"smtp_identifier": "mock"}},
        )
        self.assertRaisesRegex(
            ParameterError, "'body'",
            self._create_with_action,
            {"action_type": "EMAIL_ADMIN", "action_value": {"smtp_identifier": "mock", "subject": "s"}},
        )
        # A non-object payload cannot carry any of them.
        self.assertRaisesRegex(
            ParameterError, "must be an object",
            self._create_with_action, {"action_type": "EMAIL_USER", "action_value": 600},
        )

    def test_02q_email_action_accepts_a_blank_smtp_identifier(self):
        # The shipped MFA_BRUTEFORCE template ships the identifier blank for the admin to fill in once an SMTP
        # server exists, so a blank one must stay storable.
        policy_id = self._create_with_action(
            {"action_type": "EMAIL_ADMIN", "action_value": {"smtp_identifier": "", "subject": "s", "body": "b"}})
        self.assertEqual({"smtp_identifier": "", "subject": "s", "body": "b"},
                         get_conditional_access_policy(policy_id)["stages"][0]["actions"][0]["action_value"])

    def test_02r_email_action_value_vocabulary_is_checked(self):
        base = {"smtp_identifier": "mock", "subject": "s", "body": "b"}
        self.assertRaisesRegex(
            ParameterError, "subjekt",
            self._create_with_action, {"action_type": "EMAIL_ADMIN", "action_value": {**base, "subjekt": "x"}},
        )
        self.assertRaisesRegex(
            ParameterError, "mimetype",
            self._create_with_action, {"action_type": "EMAIL_ADMIN", "action_value": {**base, "mimetype": "pdf"}},
        )
        self.assertRaisesRegex(
            ParameterError, "recipient_group",
            self._create_with_action,
            {"action_type": "EMAIL_ADMIN", "action_value": {**base, "recipient_group": "soc-team"}},
        )
        self.assertRaisesRegex(
            ParameterError, "must be a string",
            self._create_with_action, {"action_type": "EMAIL_ADMIN", "action_value": {**base, "subject": 5}},
        )
        # A key nothing in the engine reads (however plausible-sounding) is rejected like any other typo,
        # rather than silently accepted as a no-op - the same trap as the duration validator's
        # ``lock_duration_seconds`` example, reintroduced under a new key.
        self.assertRaisesRegex(
            ParameterError, "login_notice",
            self._create_with_action,
            {"action_type": "EMAIL_ADMIN", "action_value": {**base, "login_notice": "Check your mail."}},
        )
        # The groups the engine resolves, an address list, and the optional keys it reads are all accepted.
        for index, extra in enumerate(({"recipient_group": "internal_admins"},
                                       {"recipient_group": "soc@example.com, ops@example.com"},
                                       {"mimetype": "html"},
                                       {"identifier": "alias"}), start=1):
            self._create_with_action({"action_type": "EMAIL_ADMIN", "action_value": {**base, **extra}},
                                     name=f"Mail{index}", priority=index)

    def test_02s_update_revalidates_action_values(self):
        policy_id = self._create_with_action({"action_type": "LOCK_USER", "action_value": 600})
        self.assertRaisesRegex(
            ParameterError, "duration",
            update_conditional_access_policy, policy_id,
            stages=[_stage(actions=[{"action_type": "LOCK_USER", "action_value": None}])],
        )
        # Nothing of the rejected update is applied.
        self.assertEqual(600, get_conditional_access_policy(policy_id)["stages"][0]["actions"][0]["action_value"])

    def test_02t_a_stored_bad_action_value_stays_editable(self):
        # Validation is on the write path only, so a policy stored before this rule (or through the ORM) can
        # still be switched off and renamed - the WebUI's enable/dry-run toggles rely on that. Only sending the
        # stages back re-checks them, which is the repair path.
        policy_id = self._create_with_action({"action_type": "LOCK_USER", "action_value": 600})
        action = db.session.query(ConditionalAccessStageAction).one()
        action.action_value = {"lock_duration_seconds": 600}
        db.session.commit()
        update_conditional_access_policy(policy_id, enabled=False)
        update_conditional_access_policy(policy_id, name="Renamed")
        self.assertEqual("Renamed", get_conditional_access_policy(policy_id)["name"])
        self.assertRaisesRegex(
            ParameterError, "lock_duration_seconds",
            update_conditional_access_policy, policy_id,
            stages=[_stage(actions=[{"action_type": "LOCK_USER",
                                     "action_value": {"lock_duration_seconds": 600}}])],
        )

    def test_03_list_and_order(self):
        # Listed by ascending priority number (lowest number = highest precedence).
        create_conditional_access_policy("Low", 600, ["PIN_FAIL"], [_stage()], target=ConditionalAccessTarget.USER,
                priority=1)
        create_conditional_access_policy(
            "High", 600, ["PIN_FAIL"], [_stage()], target=ConditionalAccessTarget.USER, priority=9, enabled=False
        )
        policies = list_conditional_access_policies()
        self.assertEqual(["Low", "High"], [p["name"] for p in policies])
        enabled_only = list_conditional_access_policies(enabled=True)
        self.assertEqual(["Low"], [p["name"] for p in enabled_only])
        disabled_only = list_conditional_access_policies(enabled=False)
        self.assertEqual(["High"], [p["name"] for p in disabled_only])

    def test_04_update(self):
        policy_id = create_conditional_access_policy(
            "Original", 600, ["PIN_FAIL"], [_stage(5)], target=ConditionalAccessTarget.USER, priority=1
        )
        # partial update: only the given fields change
        update_conditional_access_policy(policy_id, name="Renamed", dry_run=True)
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual("Renamed", policy["name"])
        self.assertTrue(policy["dry_run"])
        self.assertEqual(600, policy["time_window_seconds"])
        self.assertEqual(["PIN_FAIL"], policy["counter_types_to_track"])
        # the remaining scalar fields can be updated individually too
        update_conditional_access_policy(policy_id, time_window_seconds=900, priority=7, enabled=False)
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual(900, policy["time_window_seconds"])
        self.assertEqual(7, policy["priority"])
        self.assertFalse(policy["enabled"])
        # renaming to its own name is not a collision
        update_conditional_access_policy(policy_id, name="Renamed")
        # replace children as a whole
        update_conditional_access_policy(
            policy_id, counter_types_to_track=["MFA_FAIL"], stages=[_stage(3, actions=[{"action_type": "DENY"}])]
        )
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual(["MFA_FAIL"], policy["counter_types_to_track"])
        self.assertEqual(1, len(policy["stages"]))
        self.assertEqual("DENY", policy["stages"][0]["actions"][0]["action_type"])
        # the old child rows are gone, not orphaned
        self.assertEqual(1, db.session.query(ConditionalAccessPolicyStage).count())
        self.assertEqual(1, db.session.query(ConditionalAccessPolicyCounterType).count())
        self.assertEqual(1, db.session.query(ConditionalAccessStageAction).count())
        # replacing children with a reused counter type / threshold stays within the (policy_id, counter_type) and
        # (policy_id, failure_threshold) unique constraints
        update_conditional_access_policy(
            policy_id, counter_types_to_track=["MFA_FAIL"], stages=[_stage(3, actions=[{"action_type": "DENY"}])]
        )
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual(["MFA_FAIL"], policy["counter_types_to_track"])
        self.assertEqual(3, policy["stages"][0]["failure_threshold"])
        self.assertEqual("DENY", policy["stages"][0]["actions"][0]["action_type"])
        self.assertEqual(1, db.session.query(ConditionalAccessPolicyStage).count())
        self.assertEqual(1, db.session.query(ConditionalAccessPolicyCounterType).count())

    def test_05_update_validation(self):
        policy_id = create_conditional_access_policy("A", 600, ["PIN_FAIL"], [_stage(5)],
                target=ConditionalAccessTarget.USER, priority=1)
        create_conditional_access_policy("B", 600, ["PIN_FAIL"], [_stage(5)], target=ConditionalAccessTarget.USER,
                priority=2)
        # name collision with another policy
        self.assertRaises(ParameterError, update_conditional_access_policy, policy_id, name="B")
        # invalid values are rejected without changing anything
        self.assertRaises(ParameterError, update_conditional_access_policy, policy_id, time_window_seconds=-1)
        self.assertRaises(ParameterError, update_conditional_access_policy, policy_id, counter_types_to_track=[])
        self.assertRaises(ParameterError, update_conditional_access_policy, policy_id, stages=[])
        # an invalid stage list does not apply a simultaneous rename
        self.assertRaises(
            ParameterError, update_conditional_access_policy, policy_id, name="StillA",
            stages=[{"failure_threshold": -1}]
        )
        db.session.rollback()
        self.assertEqual("A", get_conditional_access_policy(policy_id)["name"])
        # unknown id
        self.assertRaises(ResourceNotFoundError, update_conditional_access_policy, 424242, name="X")

    def test_06_delete(self):
        policy_id = create_conditional_access_policy(
            "Doomed", 600, ["PIN_FAIL"], [_stage(5), _stage(10)], target=ConditionalAccessTarget.USER, priority=1
        )
        self.assertEqual(policy_id, delete_conditional_access_policy(policy_id))
        self.assertRaises(ResourceNotFoundError, get_conditional_access_policy, policy_id)
        # cascades removed the children
        self.assertEqual(0, db.session.query(ConditionalAccessPolicyStage).count())
        self.assertEqual(0, db.session.query(ConditionalAccessStageAction).count())
        self.assertEqual(0, db.session.query(ConditionalAccessPolicyCounterType).count())
        self.assertRaises(ResourceNotFoundError, delete_conditional_access_policy, policy_id)

    def test_07_enable_disable(self):
        policy_id = create_conditional_access_policy(
            "Toggle", 600, ["PIN_FAIL"], [_stage()], target=ConditionalAccessTarget.USER, priority=1
        )
        enable_conditional_access_policy(policy_id, enable=False)
        self.assertFalse(get_conditional_access_policy(policy_id)["enabled"])
        enable_conditional_access_policy(policy_id)
        self.assertTrue(get_conditional_access_policy(policy_id)["enabled"])
        self.assertRaises(ResourceNotFoundError, enable_conditional_access_policy, 424242)

    def test_08_actions_by_target_is_exhaustive(self):
        # Guards the manual registration in _ACTIONS_BY_TARGET so a newly added enum option isn't silently forgotten:
        # every ConditionalAccessTarget must have an entry (a missing key would KeyError at validation), and every
        # ConditionalAccessAction must be allowed on at least one target, or it is unusable on any policy.
        self.assertSetEqual(
            set(ConditionalAccessTarget), set(_ACTIONS_BY_TARGET),
            "a ConditionalAccessTarget is missing from _ACTIONS_BY_TARGET"
        )
        covered = set().union(*_ACTIONS_BY_TARGET.values())
        self.assertSetEqual(set(ConditionalAccessAction), covered,
                "a ConditionalAccessAction is not assignable to any target")

    def test_08b_action_value_validators_are_exhaustive(self):
        # Guard the manual registration in _ACTION_VALUE_VALIDATORS the way test_08 guards _ACTIONS_BY_TARGET.
        # The dispatch is indexed without a default, so a missing entry is a KeyError on the first policy that
        # uses the new action - which is the point: a new action type must declare what action_value it takes
        # rather than inheriting "anything goes".
        self.assertSetEqual({action.value for action in ConditionalAccessAction}, set(_ACTION_VALUE_VALIDATORS),
                            "a ConditionalAccessAction is missing from _ACTION_VALUE_VALIDATORS")

    def test_09_count_modes_by_target_is_exhaustive(self):
        # Guards the per-target count-mode registration like test_08 does for actions: every target needs an entry in
        # both maps (a missing key KeyErrors at validation), each target's default must be one of its allowed modes, and
        # every CountMode must be usable on some target, or it is dead.
        self.assertSetEqual(
            set(ConditionalAccessTarget), set(_COUNT_MODES_BY_TARGET),
            "a ConditionalAccessTarget is missing from _COUNT_MODES_BY_TARGET"
        )
        self.assertSetEqual(
            set(ConditionalAccessTarget),
            set(_DEFAULT_COUNT_MODE_BY_TARGET),
            "a ConditionalAccessTarget is missing from _DEFAULT_COUNT_MODE_BY_TARGET",
        )
        for target, default in _DEFAULT_COUNT_MODE_BY_TARGET.items():
            self.assertIn(
                default,
                _COUNT_MODES_BY_TARGET[target],
                f"the default count_mode for {target} is not among its allowed modes",
            )
        covered = set().union(*_COUNT_MODES_BY_TARGET.values())
        self.assertSetEqual(set(CountMode), covered, "a CountMode is not usable on any target")

    def test_10_target_constraints_expose_actions_and_count_modes(self):
        constraints = get_target_constraints()
        self.assertSetEqual({t.value for t in ConditionalAccessTarget}, set(constraints))
        for target, entry in constraints.items():
            self.assertSetEqual({"actions", "count_modes"}, set(entry))
            self.assertListEqual(sorted(entry["actions"]), entry["actions"])
            self.assertListEqual(sorted(entry["count_modes"]), entry["count_modes"])
        self.assertListEqual(
            [CountMode.PER_ATTEMPT.value, CountMode.PER_REQUEST.value],
            constraints[ConditionalAccessTarget.USER.value]["count_modes"],
        )
        self.assertListEqual(
            [CountMode.DISTINCT_USERS.value, CountMode.PER_ATTEMPT.value, CountMode.PER_REQUEST.value],
            constraints[ConditionalAccessTarget.SOURCE_IP.value]["count_modes"],
        )
        self.assertIn(ConditionalAccessAction.BLOCK_IP.value,
                constraints[ConditionalAccessTarget.SOURCE_IP.value]["actions"])
        self.assertIn(ConditionalAccessAction.LOCK_USER.value,
                constraints[ConditionalAccessTarget.USER.value]["actions"])

    def test_10a_default_error_messages_are_ordered_most_severe_first(self):
        # The exact list, because both membership and order are contracts: the order is ACTION_SEVERITY, the
        # one ordering there is, an action that rejects nothing is absent for having nothing to say, and the
        # EMAIL_* pair comes last. A new action added here has to be a deliberate decision, not a surprise.
        suggestions = get_default_error_messages()
        self.assertListEqual([ConditionalAccessAction.PERMANENT_LOCK_USER.value, ConditionalAccessAction.PERMANENT_BLOCK_IP.value,
                              ConditionalAccessAction.LOCK_USER.value, ConditionalAccessAction.BLOCK_IP.value,
                              ConditionalAccessAction.DENY.value, ConditionalAccessAction.EMAIL_USER.value,
                              ConditionalAccessAction.EMAIL_ADMIN.value],
                             [entry["action_type"] for entry in suggestions])
        # Resolved to plain strings, not lazy proxies the JSON encoder would choke on.
        for entry in suggestions:
            self.assertIsInstance(entry["message"], str)
            self.assertTrue(entry["message"])

    def test_10a3_the_table_and_the_severity_ordering_cover_the_same_actions(self):
        # One thing seen twice: every action that ranks has a message, and every message belongs to an action
        # that ranks. Nothing may be reachable from only one of them.
        self.assertSetEqual(set(ACTION_SEVERITY), set(DEFAULT_ERROR_MESSAGES))

    def test_10a3b_a_suggestion_is_the_entries_joined_in_the_order_served(self):
        # The order is the whole composition rule, so a client needs nothing but the list: joining the entries a
        # stage carries is what the runtime reports for it. Asserted against the runtime's own composition, so
        # the two cannot drift - here for a notify-only stage, which is all the runtime composes stage-side.
        served = {entry["action_type"]: entry["message"] for entry in get_default_error_messages()}
        actions = [ConditionalAccessAction.EMAIL_USER, ConditionalAccessAction.EMAIL_ADMIN]
        self.assertEqual(" ".join(served[action.value] for action in actions),
                         compose_default_error_message(actions))

    def test_10a4_a_restriction_row_finds_its_error_message_by_shape(self):
        # A stored restriction remembers its expiry and its subject, not which action wrote it. Those two
        # facts name the action exactly, which is what lets a row be described without reading the policy.
        self.assertEqual(ConditionalAccessAction.LOCK_USER, RESTRICTION_ACTIONS[(ConditionalAccessTarget.USER, False)])
        self.assertEqual(ConditionalAccessAction.PERMANENT_LOCK_USER, RESTRICTION_ACTIONS[(ConditionalAccessTarget.USER, True)])
        self.assertEqual(ConditionalAccessAction.BLOCK_IP, RESTRICTION_ACTIONS[(ConditionalAccessTarget.SOURCE_IP, False)])
        self.assertEqual(ConditionalAccessAction.PERMANENT_BLOCK_IP, RESTRICTION_ACTIONS[(ConditionalAccessTarget.SOURCE_IP, True)])
        for (target, permanent), action in RESTRICTION_ACTIONS.items():
            self.assertEqual(str(default_error_message(action)),
                             str(DEFAULT_ERROR_MESSAGES[action]), f"{target}/{permanent}")

    def test_10a5_an_action_without_an_error_message_falls_back_to_nothing(self):
        # An action the table does not cover has nothing to say, and a caller must not have to know which
        # those are - so the lookup answers for any action, not only the ones with error message.
        self.assertIsNone(default_error_message("SOME_FUTURE_ACTION"))
        self.assertIsNone(compose_default_error_message(["SOME_FUTURE_ACTION"]))
        self.assertIsNone(compose_default_error_message([]))

    def test_10a6_a_stage_composes_its_notifications_most_severe_first(self):
        # The order is ACTION_SEVERITY, not the order the actions were configured in, so a stage falling back
        # to the default reads like the one next to it that had the suggestion written in.
        composed = compose_default_error_message([ConditionalAccessAction.EMAIL_ADMIN, ConditionalAccessAction.EMAIL_USER])
        self.assertEqual(" ".join([str(DEFAULT_ERROR_MESSAGES[ConditionalAccessAction.EMAIL_USER]),
                                   str(DEFAULT_ERROR_MESSAGES[ConditionalAccessAction.EMAIL_ADMIN])]), composed)

    def test_10a6b_the_restriction_is_left_to_the_row_that_holds_it(self):
        # A restriction is described from the row it left behind, so composing a stage's fallback never
        # includes one - otherwise the user reads it twice, once per source, and with a {duration} this side
        # cannot substitute.
        self.assertEqual(str(DEFAULT_ERROR_MESSAGES[ConditionalAccessAction.EMAIL_USER]),
                         compose_default_error_message([ConditionalAccessAction.LOCK_USER, ConditionalAccessAction.EMAIL_USER]))
        # A stage that only restricted has nothing left to say from here.
        self.assertIsNone(compose_default_error_message([ConditionalAccessAction.LOCK_USER]))
        self.assertIsNone(compose_default_error_message([ConditionalAccessAction.PERMANENT_BLOCK_IP, ConditionalAccessAction.DENY]))

    def test_10b_only_timed_restrictions_suggest_the_duration_tag(self):
        # A permanent lock has no remaining time, and DENY is not a restriction at all, so
        # {duration} must appear only where the engine can substitute it.
        timed = {ConditionalAccessAction.LOCK_USER, ConditionalAccessAction.BLOCK_IP}
        for action, message in DEFAULT_ERROR_MESSAGES.items():
            self.assertEqual(action in timed, "{duration}" in str(message),
                             f"{action} duration tag mismatch")

    def test_10b_reset_on_success_round_trips(self):
        # Off is storable and readable back; the update reports it as changed only when it was sent, so a
        # PATCH of something else never silently rewrites it.
        policy_id = create_conditional_access_policy("NoReset", 600, ["PIN_FAIL"], [_stage()], ConditionalAccessTarget.USER, 1,
                                          reset_on_success=False)
        self.assertFalse(get_conditional_access_policy(policy_id)["reset_on_success"])
        _, changed = update_conditional_access_policy(policy_id, reset_on_success=True)
        self.assertIn("reset_on_success", changed)
        self.assertTrue(get_conditional_access_policy(policy_id)["reset_on_success"])
        _, changed = update_conditional_access_policy(policy_id, name="NoReset renamed")
        self.assertNotIn("reset_on_success", changed)
        self.assertTrue(get_conditional_access_policy(policy_id)["reset_on_success"])

    def test_10c_reset_on_success_rejected_for_source_ip(self):
        # A source-IP policy never resets on a successful login, so asking for it is a ParameterError rather than a
        # setting that is stored and then ignored.
        self.assertRaises(ParameterError, create_conditional_access_policy, "IPReset", 600, ["PASSWORD_FAIL"],
                          [_block_ip_stage()],
                          ConditionalAccessTarget.SOURCE_IP, 1, reset_on_success=True)
        # Omitting it (or sending it off) is fine and stores the only value that target can have.
        policy_id = create_conditional_access_policy("IPNoReset", 600, ["PASSWORD_FAIL"], [_block_ip_stage()],
                                          ConditionalAccessTarget.SOURCE_IP, 2)
        self.assertFalse(get_conditional_access_policy(policy_id)["reset_on_success"])
        self.assertRaises(ParameterError, update_conditional_access_policy, policy_id, reset_on_success=True)
        self.assertFalse(get_conditional_access_policy(policy_id)["reset_on_success"])

    def test_10d_switching_to_source_ip_clears_reset_on_success(self):
        # The stored reset is not carried into a target that cannot honour it: the switch clears it and says so,
        # so the policy never claims a reset it does not perform.
        policy_id = create_conditional_access_policy("Switcher", 600, ["PASSWORD_FAIL"], [_stage()], ConditionalAccessTarget.USER, 1)
        self.assertTrue(get_conditional_access_policy(policy_id)["reset_on_success"])
        _, changed = update_conditional_access_policy(
            policy_id, target=ConditionalAccessTarget.SOURCE_IP, count_mode=CountMode.DISTINCT_USERS,
            stages=[_block_ip_stage()])
        self.assertIn("reset_on_success", changed)
        self.assertFalse(get_conditional_access_policy(policy_id)["reset_on_success"])
        # Switching back leaves it off: the admin re-enables it deliberately.
        _, changed = update_conditional_access_policy(policy_id, target=ConditionalAccessTarget.USER,
                                           count_mode=CountMode.PER_REQUEST, stages=[_stage()])
        self.assertNotIn("reset_on_success", changed)
        self.assertFalse(get_conditional_access_policy(policy_id)["reset_on_success"])

    def test_11_duplicate_priority_rejected(self):
        # priority must be unique across policies: a second policy reusing a
        # priority is rejected and nothing is persisted.
        create_conditional_access_policy("First", 600, ["PIN_FAIL"], [_stage()], target=ConditionalAccessTarget.USER,
                priority=1)
        self.assertRaises(
            ParameterError,
            create_conditional_access_policy,
            "Second",
            600,
            ["PIN_FAIL"],
            [_stage()],
            target=ConditionalAccessTarget.USER,
            priority=1,
        )
        self.assertEqual(1, db.session.query(ConditionalAccessPolicy).count())

    def test_12_update_to_used_priority_rejected(self):
        first = create_conditional_access_policy("First", 600, ["PIN_FAIL"], [_stage()],
                target=ConditionalAccessTarget.USER, priority=1)
        create_conditional_access_policy("Second", 600, ["PIN_FAIL"], [_stage()], target=ConditionalAccessTarget.USER,
                priority=2)
        # moving one policy onto another policy's priority collides
        self.assertRaises(ParameterError, update_conditional_access_policy, first, priority=2)
        self.assertEqual(1, get_conditional_access_policy(first)["priority"])

    def test_13_update_keeping_own_priority_ok(self):
        policy_id = create_conditional_access_policy("Solo", 600, ["PIN_FAIL"], [_stage()],
                target=ConditionalAccessTarget.USER, priority=5)
        # re-passing the policy's own current priority is not a collision
        update_conditional_access_policy(policy_id, name="Solo2", priority=5)
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual("Solo2", policy["name"])
        self.assertEqual(5, policy["priority"])

    def test_14_create_priority_race_reported_as_parameter_error(self):
        # The app-level uniqueness check races with concurrent writers: two requests can both pass validation and only
        # collide at the DB unique constraint on commit. That must surface as a clean ParameterError (a 400), not bubble
        # as a 500, and must leave the session usable.
        create_conditional_access_policy("Winner", 600, ["PIN_FAIL"], [_stage()],
                                         target=ConditionalAccessTarget.USER, priority=1)
        # Bypass the app-level check to force the DB-constraint path (the race window).
        with mock.patch.object(
            policy_module, "_validate_priority", side_effect=lambda priority, exclude_id=None: priority
        ):
            self.assertRaises(
                ParameterError,
                create_conditional_access_policy,
                "Racer",
                600,
                ["PIN_FAIL"],
                [_stage()],
                target=ConditionalAccessTarget.USER,
                priority=1,
            )
        # The session recovered from the rolled-back conflict: a normal create still works.
        create_conditional_access_policy("After", 600, ["PIN_FAIL"], [_stage()], target=ConditionalAccessTarget.USER,
                priority=2)
        self.assertListEqual(["Winner", "After"], [p["name"] for p in list_conditional_access_policies()])

    def test_15_update_priority_race_reported_as_parameter_error(self):
        create_conditional_access_policy("A", 600, ["PIN_FAIL"], [_stage()], target=ConditionalAccessTarget.USER,
                priority=1)
        second = create_conditional_access_policy("B", 600, ["PIN_FAIL"], [_stage()],
                target=ConditionalAccessTarget.USER, priority=2)
        with mock.patch.object(
            policy_module, "_validate_priority", side_effect=lambda priority, exclude_id=None: priority
        ):
            self.assertRaises(ParameterError, update_conditional_access_policy, second, priority=1)
        # Rolled back: B keeps priority 2 and the session is usable.
        self.assertEqual(2, get_conditional_access_policy(second)["priority"])

    # --- reordering ------------------------------------------------------------

    def _numbered(self, *priorities) -> list[int]:
        """Create one policy per given priority, named after it, and return their ids."""
        return [
            create_conditional_access_policy(
                f"P{priority}", 600, ["PIN_FAIL"], [_stage()], target=ConditionalAccessTarget.USER, priority=priority
            )
            for priority in priorities
        ]

    def _order(self):
        """The current evaluation order as (name, priority) pairs."""
        return [(policy["name"], policy["priority"]) for policy in list_conditional_access_policies()]

    def test_16_reorder_swaps_two_policies(self):
        first, second = self._numbered(1, 2)
        reorder_conditional_access_policies([second, first])
        # The two values are exchanged, not recomputed.
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_17_reorder_preserves_the_set_of_priorities(self):
        # Gapped numbering reorders exactly like contiguous numbering: the values
        # held by the listed policies are reassigned, never renumbered.
        low, mid, high = self._numbered(10, 20, 30)
        reorder_conditional_access_policies([high, low, mid])
        self.assertListEqual([("P30", 10), ("P10", 20), ("P20", 30)], self._order())
        self.assertListEqual([10, 20, 30], sorted(p["priority"] for p in list_conditional_access_policies()))

    def test_18_reorder_subset_leaves_others_untouched(self):
        # Only the listed policies swap; the unlisted one keeps its priority, so a
        # single arrow click can send just the two affected ids.
        first, second, third = self._numbered(1, 2, 3)
        reorder_conditional_access_policies([third, second])
        self.assertListEqual([("P1", 1), ("P3", 2), ("P2", 3)], self._order())

    def test_19_reorder_is_idempotent(self):
        first, second, third = self._numbered(1, 2, 3)
        reorder_conditional_access_policies([first, second, third])
        self.assertListEqual([("P1", 1), ("P2", 2), ("P3", 3)], self._order())
        # Replaying the same order changes nothing.
        reorder_conditional_access_policies([first, second, third])
        self.assertListEqual([("P1", 1), ("P2", 2), ("P3", 3)], self._order())

    def test_20_reorder_full_reversal(self):
        # Every row changes owner in one transaction: the parking step must keep the
        # unique constraint satisfied at every statement.
        ids = self._numbered(1, 2, 3, 4, 5)
        reorder_conditional_access_policies(list(reversed(ids)))
        self.assertListEqual([("P5", 1), ("P4", 2), ("P3", 3), ("P2", 4), ("P1", 5)], self._order())

    def test_21_reorder_returns_nothing(self):
        # A write, not a read: the new order is observed through list_conditional_access_policies().
        first, second = self._numbered(1, 2)
        self.assertIsNone(reorder_conditional_access_policies([second, first]))
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_22_reorder_validation_errors(self):
        first, second = self._numbered(1, 2)
        for invalid in ([], None, "1,2", 5):
            self.assertRaises(ParameterError, reorder_conditional_access_policies, invalid)
        # a policy listed twice
        self.assertRaises(ParameterError, reorder_conditional_access_policies, [first, first])
        # a non-numeric id
        self.assertRaises(ParameterError, reorder_conditional_access_policies, [first, "x"])
        # an unknown id
        self.assertRaises(ResourceNotFoundError, reorder_conditional_access_policies, [first, 424242])
        # nothing moved
        self.assertListEqual([("P1", 1), ("P2", 2)], self._order())

    def test_23_reorder_single_policy_is_a_no_op(self):
        (only,) = self._numbered(7)
        reorder_conditional_access_policies([only])
        self.assertListEqual([("P7", 7)], self._order())

    def test_24_reorder_only_the_moved_rows_is_equivalent_to_sending_all(self):
        # The rows whose position changes are the permutation's support (a union of cycles), so they hold the same set
        # of priority values before and after the swap; sending only those rows must therefore land exactly the order
        # that sending every row would.
        a, b, c, d = self._numbered(1, 2, 3, 4)
        # drag P4 two places up: A P4 B C  ->  the moved rows are P4, P2, P3
        reorder_conditional_access_policies([d, b, c], expected_priorities=[4, 2, 3])
        self.assertListEqual([("P1", 1), ("P4", 2), ("P2", 3), ("P3", 4)], self._order())

    def test_25_reorder_assertion_accepts_the_current_priorities(self):
        first, second = self._numbered(10, 20)
        reorder_conditional_access_policies([second, first], expected_priorities=[20, 10])
        self.assertListEqual([("P20", 10), ("P10", 20)], self._order())

    def test_26_reorder_assertion_rejects_a_concurrent_change(self):
        # Another admin reordered in between, so the priorities this caller is about to
        # overwrite are no longer the ones it read: refuse instead of clobbering silently.
        first, second = self._numbered(1, 2)
        reorder_conditional_access_policies([second, first])  # the other admin's save
        with self.assertRaises(ConflictError) as caught:
            reorder_conditional_access_policies([second, first], expected_priorities=[2, 1])
        self.assertIn("P2", str(caught.exception))
        # nothing moved a second time
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_27_reorder_assertion_ignores_untouched_policies(self):
        # Two admins rearranging disjoint parts of the list must both succeed: the assertion covers only the submitted
        # rows, so an unrelated change is not a conflict - this is the whole point of sending a subset.
        a, b, c, d = self._numbered(1, 2, 3, 4)
        reorder_conditional_access_policies([d, c], expected_priorities=[4, 3])  # admin 2 swaps P3/P4
        reorder_conditional_access_policies([b, a], expected_priorities=[2, 1])  # admin 1 swaps P1/P2
        self.assertListEqual([("P2", 1), ("P1", 2), ("P4", 3), ("P3", 4)], self._order())

    def test_28_reorder_assertion_validation_errors(self):
        first, second = self._numbered(1, 2)
        # one entry per id
        self.assertRaises(ParameterError, reorder_conditional_access_policies, [first, second], [1])
        self.assertRaises(ParameterError, reorder_conditional_access_policies, [first, second], 1)
        # entries must be positive ints
        self.assertRaises(ParameterError, reorder_conditional_access_policies, [first, second], [1, "x"])
        self.assertRaises(ParameterError, reorder_conditional_access_policies, [first, second], [1, 0])
        self.assertListEqual([("P1", 1), ("P2", 2)], self._order())

    # --- conditions -----------------------------------------------------------

    @staticmethod
    def _condition(condition_type: ConditionType | str = ConditionType.USER_ROLE,
                   operator: ConditionOperator | str = ConditionOperator.IN,
                   value: list | str | None = None, **extra) -> dict:
        return {"condition_type": str(condition_type), "operator": str(operator),
                "value": value if value is not None else [str(AuthLogUserRole.USER)], **extra}

    def _create_with_conditions(self, name: str, conditions, priority: int = 1) -> int:
        """Create a policy carrying *conditions*, deliberately left unannotated: several tests pass
        malformed input (a bare string, a list of non-dicts, a falsy non-list) to assert it is
        rejected. Returns the new policy id."""
        return create_conditional_access_policy(name, 600, ["PIN_FAIL"], [_stage()],
                target=ConditionalAccessTarget.USER,
                                     priority=priority, conditions=conditions)

    def test_29_conditions_round_trip(self):
        policy_id = self._create_with_conditions("Conditioned", [self._condition()])
        conditions = get_conditional_access_policy(policy_id)["conditions"]
        self.assertEqual(1, len(conditions))
        # No id is served: nothing addresses a condition, and an update replaces them wholesale.
        self.assertSetEqual({"condition_type", "operator", "value"}, set(conditions[0]))
        self.assertEqual(str(ConditionType.USER_ROLE), conditions[0]["condition_type"])
        self.assertEqual(str(ConditionOperator.IN), conditions[0]["operator"])
        self.assertListEqual([str(AuthLogUserRole.USER)], conditions[0]["value"])

    def test_29a_conditions_are_served_in_condition_type_order(self):
        # A canonical order, whichever order they were written in: they are ANDed, so order means
        # nothing, and a stable serialization is what lets a client diff a policy against its draft.
        self.setUp_user_realms()
        policy_id = self._create_with_conditions(
            "Ordered", [self._condition(ConditionType.USER_ROLE),
                        self._condition(ConditionType.USER_REALM, value=[self.realm1])])
        self.assertListEqual([str(ConditionType.USER_REALM), str(ConditionType.USER_ROLE)],
                             [c["condition_type"] for c in get_conditional_access_policy(policy_id)["conditions"]])

    def test_30_conditions_are_optional(self):
        policy_id = create_conditional_access_policy("Unconditioned", 600, ["PIN_FAIL"], [_stage()],
                                          target=ConditionalAccessTarget.USER, priority=1)
        self.assertListEqual([], get_conditional_access_policy(policy_id)["conditions"])

    def test_31_condition_values_are_deduplicated(self):
        self.setUp_user_realms()
        policy_id = self._create_with_conditions(
            "Deduplicated", [self._condition(ConditionType.USER_REALM, value=["realm1", "realm1", " realm1 "])])
        # Surrounding whitespace is stripped and the duplicates collapse to one entry.
        self.assertListEqual([self.realm1], get_conditional_access_policy(policy_id)["conditions"][0]["value"])

    def test_32_condition_value_case_must_match_exactly(self):
        # Realm names are canonically lower-case, so a differently-cased value is a
        # typo and is reported rather than silently rewritten.
        self.setUp_user_realms()
        self.assertRaises(ParameterError, self._create_with_conditions,
                          "Miscased", [self._condition(ConditionType.USER_REALM, value=["REALM1"])])

    def test_33_unknown_condition_type_is_rejected(self):
        self.assertRaises(ParameterError, self._create_with_conditions,
                          "Bad type", [self._condition("NO_SUCH_TYPE")])

    def test_34_operator_not_allowed_for_type_is_rejected(self):
        self.assertRaises(ParameterError, self._create_with_conditions,
                          "Bad operator", [self._condition(operator="MATCHES")])

    def test_35_unknown_value_is_rejected(self):
        # A misspelled role would silently never match, so it fails at write time.
        self.assertRaises(ParameterError, self._create_with_conditions,
                          "Bad value", [self._condition(value=["superuser"])])
        self.setUp_user_realms()
        self.assertRaises(ParameterError, self._create_with_conditions,
                          "Bad realm", [self._condition(ConditionType.USER_REALM, value=["nosuchrealm"])])

    def test_36_malformed_condition_is_rejected(self):
        for conditions in ([self._condition(value=[])],  # empty value list
                           [self._condition(value="user")],  # not a list
                           [self._condition(value=[1])],  # non-string entry
                           [self._condition(unknown_key="x")],  # unknown key
                           [self._condition(id=3)],  # conditions carry no id, so it is not accepted either
                           [self._condition(key="somekey")],  # conditions take no sub-key
                           ["not a dict"]):
            self.assertRaises(ParameterError, self._create_with_conditions, "Malformed", conditions)
        self.assertRaises(ParameterError, self._create_with_conditions, "Malformed", "not a list")

    def test_36a_falsy_non_list_conditions_are_rejected(self):
        # A falsy non-list must be a 400 like any other malformed value, not read as "no conditions": that would create
        # a policy applying to *everyone*, the wrong direction to fail for an access-control policy. Only an omitted
        # parameter means unconditioned (test_30). Distinct name *and* priority per case is deliberate: both are unique
        # across policies, so a validation regression would leak a policy on the first case, and every later case would
        # then raise on that collision instead of on the value - passing for the wrong reason and hiding the regression.
        for index, conditions in enumerate((0, False, {}, "")):
            with self.subTest(conditions=conditions):
                self.assertRaises(ParameterError, self._create_with_conditions,
                                  f"Falsy{index}", conditions, priority=index + 1)

    def test_37_duplicate_condition_type_is_rejected(self):
        self.assertRaises(ParameterError, self._create_with_conditions, "Duplicate",
                          [self._condition(value=[str(AuthLogUserRole.USER)]),
                           self._condition(operator=ConditionOperator.NOT_IN,
                                           value=[str(AuthLogUserRole.ADMIN_INTERNAL)])])

    def test_38_update_replaces_conditions_wholesale(self):
        policy_id = self._create_with_conditions("Updatable", [self._condition()])
        # Reusing the same condition type across the update must stay within the
        # (policy_id, condition_type) unique constraint.
        _, changed = update_conditional_access_policy(
            policy_id, conditions=[self._condition(operator=ConditionOperator.NOT_IN,
                                                   value=[str(AuthLogUserRole.ADMIN_INTERNAL)])])
        self.assertIn("conditions", changed)
        conditions = get_conditional_access_policy(policy_id)["conditions"]
        self.assertEqual(1, len(conditions))
        self.assertEqual(str(ConditionOperator.NOT_IN), conditions[0]["operator"])

    def test_39_update_can_clear_conditions(self):
        policy_id = self._create_with_conditions("Clearable", [self._condition()])
        update_conditional_access_policy(policy_id, conditions=[])
        self.assertListEqual([], get_conditional_access_policy(policy_id)["conditions"])

    def test_40_update_leaves_conditions_untouched_when_omitted(self):
        policy_id = self._create_with_conditions("Untouched", [self._condition()])
        _, changed = update_conditional_access_policy(policy_id, name="Renamed")
        self.assertNotIn("conditions", changed)
        self.assertEqual(1, len(get_conditional_access_policy(policy_id)["conditions"]))

    def test_41_invalid_conditions_do_not_partially_apply(self):
        policy_id = self._create_with_conditions("Atomic", [self._condition()])
        self.assertRaises(ParameterError, update_conditional_access_policy, policy_id,
                          name="NewName", conditions=[self._condition(value=["nope"])])
        db.session.rollback()
        # Neither the rename nor the conditions were written.
        policy = get_conditional_access_policy(policy_id)
        self.assertEqual("Atomic", policy["name"])
        self.assertEqual(1, len(policy["conditions"]))

    def test_42_condition_type_metadata(self):
        self.setUp_user_realms()
        metadata = get_condition_types()
        self.assertSetEqual({t.value for t in ConditionType}, set(metadata))
        realm_entry = metadata[ConditionType.USER_REALM.value]
        self.assertSetEqual({"label", "operators", "choices"}, set(realm_entry))
        self.assertListEqual([ConditionOperator.IN.value, ConditionOperator.NOT_IN.value],
                             [operator["name"] for operator in realm_entry["operators"]])
        self.assertIn(self.realm1, realm_entry["choices"])
        self.assertListEqual(sorted(role.value for role in AuthLogUserRole),
                             metadata[ConditionType.USER_ROLE.value]["choices"])

    def test_43_stage_error_message_round_trips(self):
        message = "Your account is locked. Please try again in about {duration}."
        policy_id = create_conditional_access_policy(
            "Message", 600, ["PIN_FAIL"],
            stages=[{"failure_threshold": 5, "error_message": message,
                     "actions": [{"action_type": "LOCK_USER",
                                  "action_value": {"duration_seconds": 600}}]}],
            target=ConditionalAccessTarget.USER, priority=1)
        self.assertEqual(message, get_conditional_access_policy(policy_id)["stages"][0]["error_message"])

    def test_44_stage_error_message_defaults_to_none(self):
        # No message means the rejection stays generic: nothing is surfaced unless
        # an admin wrote it.
        policy_id = create_conditional_access_policy("NoMessage", 600, ["PIN_FAIL"], stages=[_stage(5)],
                                          target=ConditionalAccessTarget.USER, priority=1)
        self.assertIsNone(get_conditional_access_policy(policy_id)["stages"][0]["error_message"])

    def test_45_blank_stage_error_message_is_stored_as_none(self):
        for blank in ("", "   ", "\n\t"):
            policy_id = create_conditional_access_policy(f"Blank{len(blank)}", 600, ["PIN_FAIL"],
                                              stages=[{**_stage(5), "error_message": blank}],
                                              target=ConditionalAccessTarget.USER, priority=1)
            self.assertIsNone(get_conditional_access_policy(policy_id)["stages"][0]["error_message"])
            delete_conditional_access_policy(policy_id)

    def test_46_stage_error_message_is_stripped(self):
        policy_id = create_conditional_access_policy("Strip", 600, ["PIN_FAIL"],
                                          stages=[{**_stage(5), "error_message": "  Locked.  "}],
                                          target=ConditionalAccessTarget.USER, priority=1)
        self.assertEqual("Locked.", get_conditional_access_policy(policy_id)["stages"][0]["error_message"])

    def test_47_unknown_brace_expressions_are_kept_verbatim(self):
        # Brace expressions other than {duration} are deliberately not validated:
        # only {duration} is substituted at rejection time, so an admin can write
        # braces in ordinary prose without escaping them.
        message = "Locked {} for {duration} — see {unknown} or {{escaped}}."
        policy_id = create_conditional_access_policy("Braces", 600, ["PIN_FAIL"],
                                          stages=[{**_stage(5), "error_message": message}],
                                          target=ConditionalAccessTarget.USER, priority=1)
        self.assertEqual(message, get_conditional_access_policy(policy_id)["stages"][0]["error_message"])

    def test_48_stage_error_message_validation_errors(self):
        for invalid in (123, [], {}, True):
            self.assertRaises(ParameterError, create_conditional_access_policy, "Invalid", 600, ["PIN_FAIL"],
                              stages=[{**_stage(5), "error_message": invalid}],
                              target=ConditionalAccessTarget.USER, priority=1)
        # Over the model's Unicode(500), rejected here rather than truncated by the DB.
        self.assertRaises(ParameterError, create_conditional_access_policy, "TooLong", 600, ["PIN_FAIL"],
                          stages=[{**_stage(5), "error_message": "x" * (MAX_ERROR_MESSAGE_LENGTH + 1)}],
                          target=ConditionalAccessTarget.USER, priority=1)

    def test_49_stage_error_message_at_the_length_limit_is_accepted(self):
        message = "x" * MAX_ERROR_MESSAGE_LENGTH
        policy_id = create_conditional_access_policy("AtLimit", 600, ["PIN_FAIL"],
                                          stages=[{**_stage(5), "error_message": message}],
                                          target=ConditionalAccessTarget.USER, priority=1)
        self.assertEqual(message, get_conditional_access_policy(policy_id)["stages"][0]["error_message"])

    def test_50_update_replaces_and_clears_the_stage_error_message(self):
        policy_id = create_conditional_access_policy("Update", 600, ["PIN_FAIL"],
                                          stages=[{**_stage(5), "error_message": "Old."}],
                                          target=ConditionalAccessTarget.USER, priority=1)
        update_conditional_access_policy(policy_id, stages=[{**_stage(5), "error_message": "New."}])
        self.assertEqual("New.", get_conditional_access_policy(policy_id)["stages"][0]["error_message"])
        # Stages are replaced wholesale, so omitting the message clears it.
        update_conditional_access_policy(policy_id, stages=[_stage(5)])
        self.assertIsNone(get_conditional_access_policy(policy_id)["stages"][0]["error_message"])

    def test_51_docstrings_do_not_reference_the_nonexistent_lockout_policy_module(self):
        # The write-CRUD module is `privacyidea.lib.conditional_access.policy` (file policy.py) and its
        # bundled template module is `policy_template.py`; a `lockout_policy[_template]` module has never
        # existed. A Sphinx cross-reference to it renders as a dead link, so guard against the name
        # leaking back into a docstring or comment.
        import inspect

        from privacyidea.lib.conditional_access import engine as engine_module
        from privacyidea.lib.conditional_access import policy_template as policy_template_module
        from privacyidea.models import conditional_access_policy as models_module

        sources = {
            "engine.parse_lock_duration_seconds": inspect.getsource(engine_module.parse_lock_duration_seconds),
            "policy._validate_email_action_value": inspect.getsource(policy_module._validate_email_action_value),
            "models.ConditionalAccessStageAction": inspect.getsource(models_module.ConditionalAccessStageAction),
        }
        for name, source in sources.items():
            self.assertNotIn("lockout_policy", source, f"{name} still references the nonexistent "
                                                        f"'lockout_policy' module.")
        # The real modules exist under the names the fixed references point to.
        self.assertTrue(hasattr(policy_module, "_validate_duration_action_value"))
        self.assertTrue(hasattr(policy_template_module, "MFA_BRUTEFORCE"))

