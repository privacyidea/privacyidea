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
Tests for the conditional-access lockout-policy CRUD layer
(:mod:`privacyidea.lib.conditional_access.lockout_policy`).
"""

from unittest import mock

from privacyidea.lib.conditional_access import lockout_policy as lockout_policy_module
from privacyidea.lib.conditional_access.authentication_event_types import CA_ENFORCEMENT_EVENT_TYPES  # noqa: F401
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, CountMode
from privacyidea.lib.conditional_access.authentication_log import AuthLogUserRole
from privacyidea.lib.conditional_access.conditions import (ConditionOperator, ConditionType,
                                                           get_condition_types)
from privacyidea.lib.conditional_access.engine import LockoutAction, LockoutTarget
from privacyidea.lib.conditional_access.lockout_policy import (
    _ACTIONS_BY_TARGET,
    _COUNT_MODES_BY_TARGET,
    _DEFAULT_COUNT_MODE_BY_TARGET,
    create_lockout_policy,
    delete_lockout_policy,
    enable_lockout_policy,
    get_lockout_policy,
    get_target_constraints,
    list_lockout_policies,
    reorder_lockout_policies,
    update_lockout_policy,
)
from privacyidea.lib.error import ConflictError, ParameterError, ResourceNotFoundError
from privacyidea.models import db
from privacyidea.models.lockout_policy import (
    LockoutPolicy,
    LockoutPolicyCondition,
    LockoutPolicyCounterType,
    LockoutPolicyStage,
    LockoutStageAction,
)

from .base import MyTestCase


def _stage(threshold=5, actions=None, retrigger=False):
    if actions is None:
        actions = [{"action_type": "LOCK_USER", "action_value": {"lock_duration_seconds": 600}}]
    # retrigger is per action; apply it to each action of this stage.
    actions = [{**action, "retrigger_above_threshold": retrigger} for action in actions]
    return {"failure_threshold": threshold, "actions": actions}


class LockoutPolicyCrudTestCase(MyTestCase):
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
        for model in (LockoutStageAction, LockoutPolicyStage, LockoutPolicyCondition,
                      LockoutPolicyCounterType, LockoutPolicy):
            db.session.query(model).delete()
        db.session.commit()
        db.session.expunge_all()

    def test_01_create_and_get(self):
        policy_id = create_lockout_policy(
            "Brute Force", 600, ["PIN_FAIL", "MFA_FAIL"],
            stages=[_stage(5),
                    _stage(10,
                           actions=[{"action_type": "PERMANENT_LOCK_USER", "action_value": None},
                                    {"action_type": "EMAIL_ADMIN",
                                     "action_value": {"smtp_identifier": "mock"}}])],
            target=LockoutTarget.USER, priority=3)
        policy = get_lockout_policy(policy_id)
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
        self.assertEqual({"lock_duration_seconds": 600}, policy["stages"][0]["actions"][0]["action_value"])
        # retrigger_above_threshold defaults to False on a lock action (fire once).
        self.assertFalse(policy["stages"][0]["actions"][0]["retrigger_above_threshold"])

    def test_01b_action_retrigger_flag_round_trips(self):
        # The per-action retrigger_above_threshold checkbox round-trips within one
        # stage: the lock action re-triggers while the email fires once.
        policy_id = create_lockout_policy(
            "Retrig", 600, ["PIN_FAIL"],
            stages=[{"failure_threshold": 8,
                     "actions": [{"action_type": "LOCK_USER",
                                  "action_value": {"lock_duration_seconds": 300},
                                  "retrigger_above_threshold": True},
                                 {"action_type": "EMAIL_ADMIN",
                                  "action_value": {"smtp_identifier": "x"},
                                  "retrigger_above_threshold": False}]}],
            target=LockoutTarget.USER, priority=1)
        policy = get_lockout_policy(policy_id)
        by_type = {action["action_type"]: action for action in policy["stages"][0]["actions"]}
        self.assertTrue(by_type["LOCK_USER"]["retrigger_above_threshold"])
        self.assertFalse(by_type["EMAIL_ADMIN"]["retrigger_above_threshold"])

    def test_01c_retrigger_default_is_action_aware(self):
        # When the client omits retrigger_above_threshold, the standing DENY verdict
        # defaults to re-trigger and the lock/email/block effects to fire-once.
        policy_id = create_lockout_policy(
            "Defaults", 600, ["PIN_FAIL"],
            stages=[{"failure_threshold": 3, "actions": [{"action_type": "DENY"}]},
                    {"failure_threshold": 5,
                     "actions": [{"action_type": "LOCK_USER",
                                  "action_value": {"lock_duration_seconds": 60}}]}],
            target=LockoutTarget.USER, priority=1)
        policy = get_lockout_policy(policy_id)
        by_threshold = {stage["failure_threshold"]: stage for stage in policy["stages"]}
        self.assertTrue(by_threshold[3]["actions"][0]["retrigger_above_threshold"])  # DENY
        self.assertFalse(by_threshold[5]["actions"][0]["retrigger_above_threshold"])  # LOCK_USER

    def test_01d_threshold_zero_is_only_for_standing_decisions(self):
        # A threshold counts failures, so anything reacting to a count starts at 1. DENY states a standing
        # verdict instead, so 0 means "always": the lockdown idiom.
        usr = LockoutTarget.USER
        policy_id = create_lockout_policy(
            "zero_deny", 600, ["PIN_FAIL"],
            [{"failure_threshold": 0, "actions": [{"action_type": "DENY"}]}],
            target=usr, priority=1)
        policy = get_lockout_policy(policy_id)
        self.assertEqual(0, policy["stages"][0]["failure_threshold"])
        delete_lockout_policy(policy_id)

        # Everything that reacts to a count is refused at 0, as is a stage with no action to justify it.
        for stage in ([{"failure_threshold": 0, "actions": [{"action_type": "LOCK_USER",
                                                             "action_value": {"duration_seconds": 60}}]}],
                      [{"failure_threshold": 0, "actions": [{"action_type": "EMAIL_ADMIN"}]}],
                      # A mixed stage is refused too: the LOCK_USER half would fire at zero failures.
                      [{"failure_threshold": 0, "actions": [{"action_type": "DENY"},
                                                            {"action_type": "LOCK_USER",
                                                             "action_value": {"duration_seconds": 60}}]}],
                      [{"failure_threshold": 0, "actions": []}]):
            self.assertRaises(ParameterError, create_lockout_policy, "zero_bad", 600, ["PIN_FAIL"],
                              stage, target=usr, priority=1)

    def test_02_create_validation_errors(self):
        valid = dict(
            time_window_seconds=600,
            counter_types_to_track=["PIN_FAIL"],
            stages=[_stage()],
            target=LockoutTarget.USER,
            priority=1,
        )
        # name
        self.assertRaises(ParameterError, create_lockout_policy, "", **valid)
        self.assertRaises(ParameterError, create_lockout_policy, None, **valid)
        self.assertRaises(ParameterError, create_lockout_policy, "x" * 256, **valid)
        # duplicate name
        create_lockout_policy("Taken", **valid)
        self.assertRaises(ParameterError, create_lockout_policy, "Taken", **valid)
        self.assertRaises(ParameterError, create_lockout_policy, "  Taken  ", **valid)
        usr = LockoutTarget.USER
        # window / priority; a valid, unique priority keeps the intended later check the one that raises
        self.assertRaises(ParameterError, create_lockout_policy, "P", 0, ["PIN_FAIL"], [_stage()],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_lockout_policy, "P", "600", ["PIN_FAIL"], [_stage()],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"], [_stage()],
                          target=usr, priority=0)
        # target
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"], [_stage()],
                          target="planet", priority=2)
        # counter types
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, [], [_stage()],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["NOT_A_TYPE"], [_stage()],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, "PIN_FAIL", [_stage()],
                          target=usr, priority=2)
        # stages
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"], [],
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"], None,
                          target=usr, priority=2)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"name": "no threshold"}], target=usr, priority=2)  # missing threshold
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(5), _stage(5)], target=usr, priority=2)  # duplicate threshold
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "bogus": 1}], target=usr, priority=2)  # unknown stage key
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [5], target=usr, priority=2)  # stage is not a dict
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],  # actions not a list
                          [{"failure_threshold": 5, "actions": "notalist"}], target=usr, priority=2)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "actions": [42]}], target=usr, priority=2)  # action not a dict
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "NOT_AN_ACTION"}])], target=usr, priority=2)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "LOCK_USER", "bogus": 1}])], target=usr, priority=2)
        # nothing invalid was persisted
        self.assertEqual(1, db.session.query(LockoutPolicy).count())

    def test_02c_count_mode_per_attempt(self):
        # PER_ATTEMPT tracks the same AuthEventType vocabulary; only the counting unit differs.
        policy_id = create_lockout_policy(
            "RateLimit",
            60,
            [AuthEventType.MFA_FAIL, AuthEventType.LOGIN_SUCCESS],
            [_stage(10)],
            target=LockoutTarget.USER,
            count_mode=CountMode.PER_ATTEMPT,
            priority=1,
        )
        policy = get_lockout_policy(policy_id)
        self.assertEqual(CountMode.PER_ATTEMPT, policy["count_mode"])
        self.assertEqual([AuthEventType.MFA_FAIL, AuthEventType.LOGIN_SUCCESS], policy["counter_types_to_track"])

    def test_02d_count_mode_validation(self):
        # An unknown mode is rejected as such (not, say, mistaken for a target error).
        self.assertRaisesRegex(
            ParameterError,
            "Unknown count_mode 'SOMETHING'",
            create_lockout_policy,
            "P",
            600,
            [AuthEventType.PIN_FAIL],
            [_stage()],
            target=LockoutTarget.USER,
            count_mode="SOMETHING",
            priority=1,
        )
        self.assertEqual(0, db.session.query(LockoutPolicy).count())

    def test_02e_update_count_mode(self):
        # Switching the mode alone is allowed (the vocabulary is shared); the tracked counters are untouched.
        policy_id = create_lockout_policy(
            "Switch", 600, [AuthEventType.PIN_FAIL], [_stage()], target=LockoutTarget.USER, priority=1
        )
        update_lockout_policy(policy_id, count_mode=CountMode.PER_ATTEMPT)
        policy = get_lockout_policy(policy_id)
        self.assertEqual(CountMode.PER_ATTEMPT, policy["count_mode"])
        self.assertEqual([AuthEventType.PIN_FAIL], policy["counter_types_to_track"])

    def _ip_stage(self, threshold=20):
        return _stage(threshold, actions=[{"action_type": "BLOCK_IP", "action_value": {"duration_seconds": 3600}}])

    def test_02f_count_mode_defaults_per_target(self):
        # No count_mode given: a user policy defaults to PER_REQUEST, a source_ip policy to DISTINCT_USERS,
        # so the stored value always states what the policy actually counts.
        user_id = create_lockout_policy("U", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1)
        self.assertEqual(CountMode.PER_REQUEST, get_lockout_policy(user_id)["count_mode"])
        ip_id = create_lockout_policy(
            "I", 300, ["PASSWORD_FAIL"], [self._ip_stage()], target=LockoutTarget.SOURCE_IP, priority=2
        )
        self.assertEqual(CountMode.DISTINCT_USERS, get_lockout_policy(ip_id)["count_mode"])

    def test_02g_count_mode_target_compatibility(self):
        # DISTINCT_USERS is the one mode specific to source_ip (there is no distinct-accounts notion for a single user),
        # so it is the only incompatible target/mode pair and is rejected before anything is written; the volume modes
        # are valid for either target.
        self.assertRaisesRegex(
            ParameterError,
            "count_mode 'DISTINCT_USERS' is not allowed for target 'user'",
            create_lockout_policy,
            "P",
            600,
            ["PIN_FAIL"],
            [_stage()],
            target=LockoutTarget.USER,
            count_mode=CountMode.DISTINCT_USERS,
            priority=1,
        )
        self.assertEqual(0, db.session.query(LockoutPolicy).count())
        # source_ip accepts either volume mode as well as its DISTINCT_USERS default, storing exactly what was asked.
        for index, mode in enumerate((CountMode.PER_REQUEST, CountMode.PER_ATTEMPT), start=1):
            policy_id = create_lockout_policy(
                f"IP-{mode.value}",
                300,
                ["PASSWORD_FAIL"],
                [self._ip_stage()],
                target=LockoutTarget.SOURCE_IP,
                count_mode=mode,
                priority=index,
            )
            self.assertEqual(mode, get_lockout_policy(policy_id)["count_mode"])

    def test_02h_update_target_revalidates_count_mode(self):
        # Switching a source_ip policy (default DISTINCT_USERS) to user without also fixing the mode is rejected: the
        # effective (target, count_mode) pair is validated, not just each field in isolation. (The compatible switch
        # that also supplies a volume count_mode is covered end-to-end by the API test suite.)
        reject_id = create_lockout_policy(
            "Reject", 300, ["PASSWORD_FAIL"], [self._ip_stage()], target=LockoutTarget.SOURCE_IP, priority=1
        )
        # Assert on the message so a stage/action-compatibility error cannot masquerade as the count_mode rejection
        # (the stages here are deliberately LOCK_USER, i.e. already target-compatible, so only count_mode can fail).
        self.assertRaisesRegex(
            ParameterError,
            "count_mode 'DISTINCT_USERS' is not allowed for target 'user'",
            update_lockout_policy,
            reject_id,
            target=LockoutTarget.USER,
            stages=[_stage()],
        )

    def test_02i_update_source_ip_accepts_volume_count_mode(self):
        # A source_ip policy can be switched from its DISTINCT_USERS default to a volume mode (plain per-IP rate
        # limiting); the new mode is stored.
        ip_id = create_lockout_policy(
            "Spray", 300, ["PASSWORD_FAIL"], [self._ip_stage()], target=LockoutTarget.SOURCE_IP, priority=1
        )
        update_lockout_policy(ip_id, count_mode=CountMode.PER_ATTEMPT)
        self.assertEqual(CountMode.PER_ATTEMPT, get_lockout_policy(ip_id)["count_mode"])

    def test_02b_duplicate_counter_types_are_deduplicated(self):
        # A repeated counter type is silently de-duplicated (order preserved),
        # not rejected: tracking the same event type twice has no effect.
        policy_id = create_lockout_policy(
            "Dedup", 600, ["MFA_FAIL", "PIN_FAIL", "MFA_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1
        )
        self.assertEqual(["MFA_FAIL", "PIN_FAIL"], get_lockout_policy(policy_id)["counter_types_to_track"])

    def test_02c_event_types_written_by_conditional_access_are_not_trackable(self):
        # A policy counting its own rejections is a lock that feeds itself: while the user is locked, every request adds
        # to the count, so a re-triggering lock never expires and no successful login can clear it; refusing the value
        # at the CRUD boundary makes that impossible rather than merely discouraged.
        for event_type in CA_ENFORCEMENT_EVENT_TYPES:
            self.assertRaises(
                ParameterError,
                create_lockout_policy,
                f"Self feeding {event_type}", 600, [str(event_type)], [_stage()],
                target=LockoutTarget.USER, priority=1,
            )

    def test_02j_target_action_compatibility(self):
        # BLOCK_IP only makes sense on a source_ip target; LOCK_USER only on a user target.
        self.assertRaises(
            ParameterError,
            create_lockout_policy,
            "P",
            600,
            ["PIN_FAIL"],
            [_stage(actions=[{"action_type": "BLOCK_IP"}])],
            target=LockoutTarget.USER,
            priority=1,
        )
        self.assertRaises(
            ParameterError,
            create_lockout_policy,
            "P",
            600,
            ["PIN_FAIL"],
            [_stage(actions=[{"action_type": "LOCK_USER"}])],
            target=LockoutTarget.SOURCE_IP,
            priority=2,
        )
        # a source_ip policy may block the offending IP
        create_lockout_policy(
            "Spray",
            300,
            ["PIN_FAIL"],
            [_stage(20, actions=[{"action_type": "BLOCK_IP", "action_value": {"duration_seconds": 3600}}])],
            target=LockoutTarget.SOURCE_IP,
            priority=3,
        )

    def test_03_list_and_order(self):
        # Listed by ascending priority number (lowest number = highest precedence).
        create_lockout_policy("Low", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1)
        create_lockout_policy(
            "High", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=9, enabled=False
        )
        policies = list_lockout_policies()
        self.assertEqual(["Low", "High"], [p["name"] for p in policies])
        enabled_only = list_lockout_policies(enabled=True)
        self.assertEqual(["Low"], [p["name"] for p in enabled_only])
        disabled_only = list_lockout_policies(enabled=False)
        self.assertEqual(["High"], [p["name"] for p in disabled_only])

    def test_04_update(self):
        policy_id = create_lockout_policy(
            "Original", 600, ["PIN_FAIL"], [_stage(5)], target=LockoutTarget.USER, priority=1
        )
        # partial update: only the given fields change
        update_lockout_policy(policy_id, name="Renamed", dry_run=True)
        policy = get_lockout_policy(policy_id)
        self.assertEqual("Renamed", policy["name"])
        self.assertTrue(policy["dry_run"])
        self.assertEqual(600, policy["time_window_seconds"])
        self.assertEqual(["PIN_FAIL"], policy["counter_types_to_track"])
        # the remaining scalar fields can be updated individually too
        update_lockout_policy(policy_id, time_window_seconds=900, priority=7, enabled=False)
        policy = get_lockout_policy(policy_id)
        self.assertEqual(900, policy["time_window_seconds"])
        self.assertEqual(7, policy["priority"])
        self.assertFalse(policy["enabled"])
        # renaming to its own name is not a collision
        update_lockout_policy(policy_id, name="Renamed")
        # replace children as a whole
        update_lockout_policy(
            policy_id, counter_types_to_track=["MFA_FAIL"], stages=[_stage(3, actions=[{"action_type": "DENY"}])]
        )
        policy = get_lockout_policy(policy_id)
        self.assertEqual(["MFA_FAIL"], policy["counter_types_to_track"])
        self.assertEqual(1, len(policy["stages"]))
        self.assertEqual("DENY", policy["stages"][0]["actions"][0]["action_type"])
        # the old child rows are gone, not orphaned
        self.assertEqual(1, db.session.query(LockoutPolicyStage).count())
        self.assertEqual(1, db.session.query(LockoutPolicyCounterType).count())
        self.assertEqual(1, db.session.query(LockoutStageAction).count())
        # replacing children with a reused counter type / threshold stays within the (policy_id, counter_type) and
        # (policy_id, failure_threshold) unique constraints
        update_lockout_policy(
            policy_id, counter_types_to_track=["MFA_FAIL"], stages=[_stage(3, actions=[{"action_type": "DENY"}])]
        )
        policy = get_lockout_policy(policy_id)
        self.assertEqual(["MFA_FAIL"], policy["counter_types_to_track"])
        self.assertEqual(3, policy["stages"][0]["failure_threshold"])
        self.assertEqual("DENY", policy["stages"][0]["actions"][0]["action_type"])
        self.assertEqual(1, db.session.query(LockoutPolicyStage).count())
        self.assertEqual(1, db.session.query(LockoutPolicyCounterType).count())

    def test_05_update_validation(self):
        policy_id = create_lockout_policy("A", 600, ["PIN_FAIL"], [_stage(5)], target=LockoutTarget.USER, priority=1)
        create_lockout_policy("B", 600, ["PIN_FAIL"], [_stage(5)], target=LockoutTarget.USER, priority=2)
        # name collision with another policy
        self.assertRaises(ParameterError, update_lockout_policy, policy_id, name="B")
        # invalid values are rejected without changing anything
        self.assertRaises(ParameterError, update_lockout_policy, policy_id, time_window_seconds=-1)
        self.assertRaises(ParameterError, update_lockout_policy, policy_id, counter_types_to_track=[])
        self.assertRaises(ParameterError, update_lockout_policy, policy_id, stages=[])
        # an invalid stage list does not apply a simultaneous rename
        self.assertRaises(
            ParameterError, update_lockout_policy, policy_id, name="StillA", stages=[{"failure_threshold": -1}]
        )
        db.session.rollback()
        self.assertEqual("A", get_lockout_policy(policy_id)["name"])
        # unknown id
        self.assertRaises(ResourceNotFoundError, update_lockout_policy, 424242, name="X")

    def test_06_delete(self):
        policy_id = create_lockout_policy(
            "Doomed", 600, ["PIN_FAIL"], [_stage(5), _stage(10)], target=LockoutTarget.USER, priority=1
        )
        self.assertEqual(policy_id, delete_lockout_policy(policy_id))
        self.assertRaises(ResourceNotFoundError, get_lockout_policy, policy_id)
        # cascades removed the children
        self.assertEqual(0, db.session.query(LockoutPolicyStage).count())
        self.assertEqual(0, db.session.query(LockoutStageAction).count())
        self.assertEqual(0, db.session.query(LockoutPolicyCounterType).count())
        self.assertRaises(ResourceNotFoundError, delete_lockout_policy, policy_id)

    def test_07_enable_disable(self):
        policy_id = create_lockout_policy(
            "Toggle", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1
        )
        enable_lockout_policy(policy_id, enable=False)
        self.assertFalse(get_lockout_policy(policy_id)["enabled"])
        enable_lockout_policy(policy_id)
        self.assertTrue(get_lockout_policy(policy_id)["enabled"])
        self.assertRaises(ResourceNotFoundError, enable_lockout_policy, 424242)

    def test_08_actions_by_target_is_exhaustive(self):
        # Guards the manual registration in _ACTIONS_BY_TARGET so a newly added enum option isn't silently forgotten:
        # every LockoutTarget must have an entry (a missing key would KeyError at validation), and every LockoutAction
        # must be allowed on at least one target, or it is unusable on any policy.
        self.assertSetEqual(
            set(LockoutTarget), set(_ACTIONS_BY_TARGET), "a LockoutTarget is missing from _ACTIONS_BY_TARGET"
        )
        covered = set().union(*_ACTIONS_BY_TARGET.values())
        self.assertSetEqual(set(LockoutAction), covered, "a LockoutAction is not assignable to any target")

    def test_09_count_modes_by_target_is_exhaustive(self):
        # Guards the per-target count-mode registration like test_08 does for actions: every target needs an entry in
        # both maps (a missing key KeyErrors at validation), each target's default must be one of its allowed modes, and
        # every CountMode must be usable on some target, or it is dead.
        self.assertSetEqual(
            set(LockoutTarget), set(_COUNT_MODES_BY_TARGET), "a LockoutTarget is missing from _COUNT_MODES_BY_TARGET"
        )
        self.assertSetEqual(
            set(LockoutTarget),
            set(_DEFAULT_COUNT_MODE_BY_TARGET),
            "a LockoutTarget is missing from _DEFAULT_COUNT_MODE_BY_TARGET",
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
        self.assertSetEqual({t.value for t in LockoutTarget}, set(constraints))
        for target, entry in constraints.items():
            self.assertSetEqual({"actions", "count_modes"}, set(entry))
            self.assertListEqual(sorted(entry["actions"]), entry["actions"])
            self.assertListEqual(sorted(entry["count_modes"]), entry["count_modes"])
        self.assertListEqual(
            [CountMode.PER_ATTEMPT.value, CountMode.PER_REQUEST.value],
            constraints[LockoutTarget.USER.value]["count_modes"],
        )
        self.assertListEqual(
            [CountMode.DISTINCT_USERS.value, CountMode.PER_ATTEMPT.value, CountMode.PER_REQUEST.value],
            constraints[LockoutTarget.SOURCE_IP.value]["count_modes"],
        )
        self.assertIn(LockoutAction.BLOCK_IP.value, constraints[LockoutTarget.SOURCE_IP.value]["actions"])
        self.assertIn(LockoutAction.LOCK_USER.value, constraints[LockoutTarget.USER.value]["actions"])

    def test_11_duplicate_priority_rejected(self):
        # priority must be unique across policies: a second policy reusing a
        # priority is rejected and nothing is persisted.
        create_lockout_policy("First", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1)
        self.assertRaises(
            ParameterError,
            create_lockout_policy,
            "Second",
            600,
            ["PIN_FAIL"],
            [_stage()],
            target=LockoutTarget.USER,
            priority=1,
        )
        self.assertEqual(1, db.session.query(LockoutPolicy).count())

    def test_12_update_to_used_priority_rejected(self):
        first = create_lockout_policy("First", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1)
        create_lockout_policy("Second", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=2)
        # moving one policy onto another policy's priority collides
        self.assertRaises(ParameterError, update_lockout_policy, first, priority=2)
        self.assertEqual(1, get_lockout_policy(first)["priority"])

    def test_13_update_keeping_own_priority_ok(self):
        policy_id = create_lockout_policy("Solo", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=5)
        # re-passing the policy's own current priority is not a collision
        update_lockout_policy(policy_id, name="Solo2", priority=5)
        policy = get_lockout_policy(policy_id)
        self.assertEqual("Solo2", policy["name"])
        self.assertEqual(5, policy["priority"])

    def test_14_create_priority_race_reported_as_parameter_error(self):
        # The app-level uniqueness check races with concurrent writers: two requests can both pass validation and only
        # collide at the DB unique constraint on commit. That must surface as a clean ParameterError (a 400), not bubble
        # as a 500, and must leave the session usable.
        create_lockout_policy("Winner", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1)
        # Bypass the app-level check to force the DB-constraint path (the race window).
        with mock.patch.object(
            lockout_policy_module, "_validate_priority", side_effect=lambda priority, exclude_id=None: priority
        ):
            self.assertRaises(
                ParameterError,
                create_lockout_policy,
                "Racer",
                600,
                ["PIN_FAIL"],
                [_stage()],
                target=LockoutTarget.USER,
                priority=1,
            )
        # The session recovered from the rolled-back conflict: a normal create still works.
        create_lockout_policy("After", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=2)
        self.assertListEqual(["Winner", "After"], [p["name"] for p in list_lockout_policies()])

    def test_15_update_priority_race_reported_as_parameter_error(self):
        create_lockout_policy("A", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1)
        second = create_lockout_policy("B", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=2)
        with mock.patch.object(
            lockout_policy_module, "_validate_priority", side_effect=lambda priority, exclude_id=None: priority
        ):
            self.assertRaises(ParameterError, update_lockout_policy, second, priority=1)
        # Rolled back: B keeps priority 2 and the session is usable.
        self.assertEqual(2, get_lockout_policy(second)["priority"])

    # --- reordering ------------------------------------------------------------

    def _numbered(self, *priorities) -> list[int]:
        """Create one policy per given priority, named after it, and return their ids."""
        return [
            create_lockout_policy(
                f"P{priority}", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=priority
            )
            for priority in priorities
        ]

    def _order(self):
        """The current evaluation order as (name, priority) pairs."""
        return [(policy["name"], policy["priority"]) for policy in list_lockout_policies()]

    def test_16_reorder_swaps_two_policies(self):
        first, second = self._numbered(1, 2)
        reorder_lockout_policies([second, first])
        # The two values are exchanged, not recomputed.
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_17_reorder_preserves_the_set_of_priorities(self):
        # Gapped numbering reorders exactly like contiguous numbering: the values
        # held by the listed policies are reassigned, never renumbered.
        low, mid, high = self._numbered(10, 20, 30)
        reorder_lockout_policies([high, low, mid])
        self.assertListEqual([("P30", 10), ("P10", 20), ("P20", 30)], self._order())
        self.assertListEqual([10, 20, 30], sorted(p["priority"] for p in list_lockout_policies()))

    def test_18_reorder_subset_leaves_others_untouched(self):
        # Only the listed policies swap; the unlisted one keeps its priority, so a
        # single arrow click can send just the two affected ids.
        first, second, third = self._numbered(1, 2, 3)
        reorder_lockout_policies([third, second])
        self.assertListEqual([("P1", 1), ("P3", 2), ("P2", 3)], self._order())

    def test_19_reorder_is_idempotent(self):
        first, second, third = self._numbered(1, 2, 3)
        reorder_lockout_policies([first, second, third])
        self.assertListEqual([("P1", 1), ("P2", 2), ("P3", 3)], self._order())
        # Replaying the same order changes nothing.
        reorder_lockout_policies([first, second, third])
        self.assertListEqual([("P1", 1), ("P2", 2), ("P3", 3)], self._order())

    def test_20_reorder_full_reversal(self):
        # Every row changes owner in one transaction: the parking step must keep the
        # unique constraint satisfied at every statement.
        ids = self._numbered(1, 2, 3, 4, 5)
        reorder_lockout_policies(list(reversed(ids)))
        self.assertListEqual([("P5", 1), ("P4", 2), ("P3", 3), ("P2", 4), ("P1", 5)], self._order())

    def test_21_reorder_returns_nothing(self):
        # A write, not a read: the new order is observed through list_lockout_policies().
        first, second = self._numbered(1, 2)
        self.assertIsNone(reorder_lockout_policies([second, first]))
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_22_reorder_validation_errors(self):
        first, second = self._numbered(1, 2)
        for invalid in ([], None, "1,2", 5):
            self.assertRaises(ParameterError, reorder_lockout_policies, invalid)
        # a policy listed twice
        self.assertRaises(ParameterError, reorder_lockout_policies, [first, first])
        # a non-numeric id
        self.assertRaises(ParameterError, reorder_lockout_policies, [first, "x"])
        # an unknown id
        self.assertRaises(ResourceNotFoundError, reorder_lockout_policies, [first, 424242])
        # nothing moved
        self.assertListEqual([("P1", 1), ("P2", 2)], self._order())

    def test_23_reorder_single_policy_is_a_no_op(self):
        (only,) = self._numbered(7)
        reorder_lockout_policies([only])
        self.assertListEqual([("P7", 7)], self._order())

    def test_24_reorder_only_the_moved_rows_is_equivalent_to_sending_all(self):
        # The rows whose position changes are the permutation's support (a union of cycles), so they hold the same set
        # of priority values before and after the swap; sending only those rows must therefore land exactly the order
        # that sending every row would.
        a, b, c, d = self._numbered(1, 2, 3, 4)
        # drag P4 two places up: A P4 B C  ->  the moved rows are P4, P2, P3
        reorder_lockout_policies([d, b, c], expected_priorities=[4, 2, 3])
        self.assertListEqual([("P1", 1), ("P4", 2), ("P2", 3), ("P3", 4)], self._order())

    def test_25_reorder_assertion_accepts_the_current_priorities(self):
        first, second = self._numbered(10, 20)
        reorder_lockout_policies([second, first], expected_priorities=[20, 10])
        self.assertListEqual([("P20", 10), ("P10", 20)], self._order())

    def test_26_reorder_assertion_rejects_a_concurrent_change(self):
        # Another admin reordered in between, so the priorities this caller is about to
        # overwrite are no longer the ones it read: refuse instead of clobbering silently.
        first, second = self._numbered(1, 2)
        reorder_lockout_policies([second, first])  # the other admin's save
        with self.assertRaises(ConflictError) as caught:
            reorder_lockout_policies([second, first], expected_priorities=[2, 1])
        self.assertIn("P2", str(caught.exception))
        # nothing moved a second time
        self.assertListEqual([("P2", 1), ("P1", 2)], self._order())

    def test_27_reorder_assertion_ignores_untouched_policies(self):
        # Two admins rearranging disjoint parts of the list must both succeed: the assertion covers only the submitted
        # rows, so an unrelated change is not a conflict - this is the whole point of sending a subset.
        a, b, c, d = self._numbered(1, 2, 3, 4)
        reorder_lockout_policies([d, c], expected_priorities=[4, 3])  # admin 2 swaps P3/P4
        reorder_lockout_policies([b, a], expected_priorities=[2, 1])  # admin 1 swaps P1/P2
        self.assertListEqual([("P2", 1), ("P1", 2), ("P4", 3), ("P3", 4)], self._order())

    def test_28_reorder_assertion_validation_errors(self):
        first, second = self._numbered(1, 2)
        # one entry per id
        self.assertRaises(ParameterError, reorder_lockout_policies, [first, second], [1])
        self.assertRaises(ParameterError, reorder_lockout_policies, [first, second], 1)
        # entries must be positive ints
        self.assertRaises(ParameterError, reorder_lockout_policies, [first, second], [1, "x"])
        self.assertRaises(ParameterError, reorder_lockout_policies, [first, second], [1, 0])
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
        return create_lockout_policy(name, 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER,
                                     priority=priority, conditions=conditions)

    def test_29_conditions_round_trip(self):
        policy_id = self._create_with_conditions("Conditioned", [self._condition()])
        conditions = get_lockout_policy(policy_id)["conditions"]
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
                             [c["condition_type"] for c in get_lockout_policy(policy_id)["conditions"]])

    def test_30_conditions_are_optional(self):
        policy_id = create_lockout_policy("Unconditioned", 600, ["PIN_FAIL"], [_stage()],
                                          target=LockoutTarget.USER, priority=1)
        self.assertListEqual([], get_lockout_policy(policy_id)["conditions"])

    def test_31_condition_values_are_deduplicated(self):
        self.setUp_user_realms()
        policy_id = self._create_with_conditions(
            "Deduplicated", [self._condition(ConditionType.USER_REALM, value=["realm1", "realm1", " realm1 "])])
        # Surrounding whitespace is stripped and the duplicates collapse to one entry.
        self.assertListEqual([self.realm1], get_lockout_policy(policy_id)["conditions"][0]["value"])

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
        _, changed = update_lockout_policy(
            policy_id, conditions=[self._condition(operator=ConditionOperator.NOT_IN,
                                                   value=[str(AuthLogUserRole.ADMIN_INTERNAL)])])
        self.assertIn("conditions", changed)
        conditions = get_lockout_policy(policy_id)["conditions"]
        self.assertEqual(1, len(conditions))
        self.assertEqual(str(ConditionOperator.NOT_IN), conditions[0]["operator"])

    def test_39_update_can_clear_conditions(self):
        policy_id = self._create_with_conditions("Clearable", [self._condition()])
        update_lockout_policy(policy_id, conditions=[])
        self.assertListEqual([], get_lockout_policy(policy_id)["conditions"])

    def test_40_update_leaves_conditions_untouched_when_omitted(self):
        policy_id = self._create_with_conditions("Untouched", [self._condition()])
        _, changed = update_lockout_policy(policy_id, name="Renamed")
        self.assertNotIn("conditions", changed)
        self.assertEqual(1, len(get_lockout_policy(policy_id)["conditions"]))

    def test_41_invalid_conditions_do_not_partially_apply(self):
        policy_id = self._create_with_conditions("Atomic", [self._condition()])
        self.assertRaises(ParameterError, update_lockout_policy, policy_id,
                          name="NewName", conditions=[self._condition(value=["nope"])])
        db.session.rollback()
        # Neither the rename nor the conditions were written.
        policy = get_lockout_policy(policy_id)
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
