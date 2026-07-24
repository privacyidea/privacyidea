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
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, CountMode
from privacyidea.lib.conditional_access.engine import LockoutAction, LockoutTarget
from privacyidea.lib.conditional_access.lockout_policy import (_ACTIONS_BY_TARGET,
                                                               _COUNT_MODES_BY_TARGET,
                                                               _DEFAULT_COUNT_MODE_BY_TARGET,
                                                               create_lockout_policy,
                                                               delete_lockout_policy,
                                                               enable_lockout_policy,
                                                               get_lockout_policy,
                                                               list_lockout_policies,
                                                               update_lockout_policy)
from privacyidea.lib.error import ParameterError, ResourceNotFoundError
from privacyidea.models import db
from privacyidea.models.lockout_policy import (LockoutPolicy, LockoutPolicyCounterType,
                                               LockoutPolicyStage, LockoutStageAction)
from .base import MyTestCase


def _stage(threshold=5, priority=1, actions=None):
    if actions is None:
        actions = [{"action_type": "LOCK_USER", "action_value": {"lock_duration_seconds": 600}}]
    return {"failure_threshold": threshold, "priority": priority, "actions": actions}


class LockoutPolicyCrudTestCase(MyTestCase):

    def setUp(self):
        self._clear()

    def tearDown(self):
        self._clear()

    @staticmethod
    def _clear():
        # Roll back anything a failed CRUD call left pending, then drop all rows. expunge_all clears the identity map
        # so a persistent object a test loaded (e.g. via a rejected update) cannot collide with a later test that
        # reuses the same primary key - mirroring the per-request session teardown that isolates this in production.
        db.session.rollback()
        for model in (LockoutStageAction, LockoutPolicyStage, LockoutPolicyCounterType, LockoutPolicy):
            db.session.query(model).delete()
        db.session.commit()
        db.session.expunge_all()

    def test_01_create_and_get(self):
        policy_id = create_lockout_policy(
            "Brute Force", 600, ["PIN_FAIL", "MFA_FAIL"],
            stages=[_stage(5),
                    _stage(10, priority=2,
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
        # stages are ordered by stage priority desc (evaluation order)
        self.assertEqual(10, policy["stages"][0]["failure_threshold"])
        self.assertEqual(2, len(policy["stages"][0]["actions"]))
        self.assertEqual({"lock_duration_seconds": 600},
                         policy["stages"][1]["actions"][0]["action_value"])

    def test_02_create_validation_errors(self):
        valid = dict(time_window_seconds=600, counter_types_to_track=["PIN_FAIL"],
                     stages=[_stage()], target=LockoutTarget.USER)
        # name
        self.assertRaises(ParameterError, create_lockout_policy, "", **valid)
        self.assertRaises(ParameterError, create_lockout_policy, None, **valid)
        self.assertRaises(ParameterError, create_lockout_policy, "x" * 256, **valid)
        # duplicate name
        create_lockout_policy("Taken", **valid)
        self.assertRaises(ParameterError, create_lockout_policy, "Taken", **valid)
        self.assertRaises(ParameterError, create_lockout_policy, "  Taken  ", **valid)
        usr = LockoutTarget.USER
        # window / priority
        self.assertRaises(ParameterError, create_lockout_policy, "P", 0, ["PIN_FAIL"], [_stage()], target=usr)
        self.assertRaises(ParameterError, create_lockout_policy, "P", "600", ["PIN_FAIL"], [_stage()], target=usr)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"], [_stage()],
                          target=usr, priority=0)
        # target
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"], [_stage()],
                          target="planet")
        # counter types
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, [], [_stage()], target=usr)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["NOT_A_TYPE"], [_stage()], target=usr)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, "PIN_FAIL", [_stage()], target=usr)
        # stages
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"], [], target=usr)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"], None, target=usr)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"priority": 1}], target=usr)  # missing threshold
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(5), _stage(5)], target=usr)  # duplicate threshold
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "bogus": 1}], target=usr)  # unknown stage key
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [5], target=usr)  # stage is not a dict
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "actions": "notalist"}], target=usr)  # actions not a list
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "actions": [42]}], target=usr)  # action not a dict
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "NOT_AN_ACTION"}])], target=usr)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "LOCK_USER", "bogus": 1}])], target=usr)
        # nothing invalid was persisted
        self.assertEqual(1, db.session.query(LockoutPolicy).count())

    def test_02c_count_mode_per_attempt(self):
        # PER_ATTEMPT tracks the same AuthEventType vocabulary; only the counting unit differs.
        policy_id = create_lockout_policy("RateLimit", 60, [AuthEventType.MFA_FAIL, AuthEventType.LOGIN_SUCCESS],
                                          [_stage(10)], target=LockoutTarget.USER,
                                          count_mode=CountMode.PER_ATTEMPT)
        policy = get_lockout_policy(policy_id)
        self.assertEqual(CountMode.PER_ATTEMPT, policy["count_mode"])
        self.assertEqual([AuthEventType.MFA_FAIL, AuthEventType.LOGIN_SUCCESS], policy["counter_types_to_track"])

    def test_02d_count_mode_validation(self):
        # An unknown mode is rejected as such (not, say, mistaken for a target error).
        self.assertRaisesRegex(ParameterError, "Unknown count_mode 'SOMETHING'",
                               create_lockout_policy, "P", 600, [AuthEventType.PIN_FAIL], [_stage()],
                               target=LockoutTarget.USER, count_mode="SOMETHING")
        self.assertEqual(0, db.session.query(LockoutPolicy).count())

    def test_02e_update_count_mode(self):
        # Switching the mode alone is allowed (the vocabulary is shared); the tracked counters are untouched.
        policy_id = create_lockout_policy("Switch", 600, [AuthEventType.PIN_FAIL], [_stage()],
                                          target=LockoutTarget.USER)
        update_lockout_policy(policy_id, count_mode=CountMode.PER_ATTEMPT)
        policy = get_lockout_policy(policy_id)
        self.assertEqual(CountMode.PER_ATTEMPT, policy["count_mode"])
        self.assertEqual([AuthEventType.PIN_FAIL], policy["counter_types_to_track"])

    def _ip_stage(self, threshold=20):
        return _stage(threshold, actions=[{"action_type": "BLOCK_IP", "action_value": {"duration_seconds": 3600}}])

    def test_02f_count_mode_defaults_per_target(self):
        # No count_mode given: a user policy defaults to PER_REQUEST, a source_ip policy to DISTINCT_USERS,
        # so the stored value always states what the policy actually counts.
        user_id = create_lockout_policy("U", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER)
        self.assertEqual(CountMode.PER_REQUEST, get_lockout_policy(user_id)["count_mode"])
        ip_id = create_lockout_policy("I", 300, ["PASSWORD_FAIL"], [self._ip_stage()], target=LockoutTarget.SOURCE_IP)
        self.assertEqual(CountMode.DISTINCT_USERS, get_lockout_policy(ip_id)["count_mode"])

    def test_02g_count_mode_target_compatibility(self):
        # DISTINCT_USERS is the one mode specific to source_ip (there is no distinct-accounts notion for a single
        # user), so it is the only incompatible pair and is rejected before anything is written. The volume modes are
        # valid for either target.
        self.assertRaisesRegex(ParameterError, "count_mode 'DISTINCT_USERS' is not allowed for target 'user'",
                               create_lockout_policy, "P", 600, ["PIN_FAIL"], [_stage()],
                               target=LockoutTarget.USER, count_mode=CountMode.DISTINCT_USERS)
        self.assertEqual(0, db.session.query(LockoutPolicy).count())
        # source_ip accepts either volume mode as well as its DISTINCT_USERS default, storing exactly what was asked.
        for mode in (CountMode.PER_REQUEST, CountMode.PER_ATTEMPT):
            policy_id = create_lockout_policy(f"IP-{mode.value}", 300, ["PASSWORD_FAIL"], [self._ip_stage()],
                                              target=LockoutTarget.SOURCE_IP, count_mode=mode)
            self.assertEqual(mode, get_lockout_policy(policy_id)["count_mode"])

    def test_02h_update_target_revalidates_count_mode(self):
        # Switching a source_ip policy (default DISTINCT_USERS) to user without also fixing the mode is rejected: the
        # effective (target, count_mode) pair is validated, not just each field in isolation, and DISTINCT_USERS is
        # invalid for a user target. (The compatible switch that also supplies a volume count_mode is covered
        # end-to-end by the API test suite.)
        reject_id = create_lockout_policy("Reject", 300, ["PASSWORD_FAIL"], [self._ip_stage()],
                                          target=LockoutTarget.SOURCE_IP)
        # Assert on the message so a stage/action-compatibility error cannot masquerade as the count_mode rejection
        # (the stages here are deliberately LOCK_USER, i.e. already target-compatible, so only count_mode can fail).
        self.assertRaisesRegex(ParameterError, "count_mode 'DISTINCT_USERS' is not allowed for target 'user'",
                               update_lockout_policy, reject_id,
                               target=LockoutTarget.USER, stages=[_stage()])

    def test_02i_update_source_ip_accepts_volume_count_mode(self):
        # A source_ip policy can be switched from its DISTINCT_USERS default to a volume mode (plain per-IP rate
        # limiting); the new mode is stored.
        ip_id = create_lockout_policy("Spray", 300, ["PASSWORD_FAIL"], [self._ip_stage()],
                                      target=LockoutTarget.SOURCE_IP)
        update_lockout_policy(ip_id, count_mode=CountMode.PER_ATTEMPT)
        self.assertEqual(CountMode.PER_ATTEMPT, get_lockout_policy(ip_id)["count_mode"])

    def test_02b_duplicate_counter_types_are_deduplicated(self):
        # A repeated counter type is silently de-duplicated (order preserved),
        # not rejected: tracking the same event type twice has no effect.
        policy_id = create_lockout_policy("Dedup", 600,
                                          ["MFA_FAIL", "PIN_FAIL", "MFA_FAIL"], [_stage()],
                                          target=LockoutTarget.USER)
        self.assertEqual(["MFA_FAIL", "PIN_FAIL"],
                         get_lockout_policy(policy_id)["counter_types_to_track"])

    def test_02c_target_action_compatibility(self):
        # BLOCK_IP only makes sense on a source_ip target; LOCK_USER only on a user target.
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "BLOCK_IP"}])], target=LockoutTarget.USER)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "LOCK_USER"}])], target=LockoutTarget.SOURCE_IP)
        # a source_ip policy may block the offending IP
        create_lockout_policy("Spray", 300, ["PIN_FAIL"],
                              [_stage(20, actions=[{"action_type": "BLOCK_IP",
                                                    "action_value": {"duration_seconds": 3600}}])],
                              target=LockoutTarget.SOURCE_IP)

    def test_03_list_and_order(self):
        # Listed by ascending priority number (lowest number = highest precedence).
        create_lockout_policy("Low", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1)
        create_lockout_policy("High", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER,
                              priority=9, enabled=False)
        policies = list_lockout_policies()
        self.assertEqual(["Low", "High"], [p["name"] for p in policies])
        enabled_only = list_lockout_policies(enabled=True)
        self.assertEqual(["Low"], [p["name"] for p in enabled_only])
        disabled_only = list_lockout_policies(enabled=False)
        self.assertEqual(["High"], [p["name"] for p in disabled_only])

    def test_04_update(self):
        policy_id = create_lockout_policy("Original", 600, ["PIN_FAIL"], [_stage(5)],
                                          target=LockoutTarget.USER)
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
        update_lockout_policy(policy_id, counter_types_to_track=["MFA_FAIL"],
                              stages=[_stage(3, actions=[{"action_type": "DENY"}])])
        policy = get_lockout_policy(policy_id)
        self.assertEqual(["MFA_FAIL"], policy["counter_types_to_track"])
        self.assertEqual(1, len(policy["stages"]))
        self.assertEqual("DENY", policy["stages"][0]["actions"][0]["action_type"])
        # the old child rows are gone, not orphaned
        self.assertEqual(1, db.session.query(LockoutPolicyStage).count())
        self.assertEqual(1, db.session.query(LockoutPolicyCounterType).count())
        self.assertEqual(1, db.session.query(LockoutStageAction).count())
        # replacing children with a reused counter type / threshold stays within
        # the (policy_id, counter_type) and (policy_id, failure_threshold) unique
        # constraints
        update_lockout_policy(policy_id, counter_types_to_track=["MFA_FAIL"],
                              stages=[_stage(3, actions=[{"action_type": "ALLOW"}])])
        policy = get_lockout_policy(policy_id)
        self.assertEqual(["MFA_FAIL"], policy["counter_types_to_track"])
        self.assertEqual(3, policy["stages"][0]["failure_threshold"])
        self.assertEqual("ALLOW", policy["stages"][0]["actions"][0]["action_type"])
        self.assertEqual(1, db.session.query(LockoutPolicyStage).count())
        self.assertEqual(1, db.session.query(LockoutPolicyCounterType).count())

    def test_05_update_validation(self):
        policy_id = create_lockout_policy("A", 600, ["PIN_FAIL"], [_stage(5)], target=LockoutTarget.USER)
        create_lockout_policy("B", 600, ["PIN_FAIL"], [_stage(5)], target=LockoutTarget.USER)
        # name collision with another policy
        self.assertRaises(ParameterError, update_lockout_policy, policy_id, name="B")
        # invalid values are rejected without changing anything
        self.assertRaises(ParameterError, update_lockout_policy, policy_id, time_window_seconds=-1)
        self.assertRaises(ParameterError, update_lockout_policy, policy_id, counter_types_to_track=[])
        self.assertRaises(ParameterError, update_lockout_policy, policy_id, stages=[])
        # an invalid stage list does not apply a simultaneous rename
        self.assertRaises(ParameterError, update_lockout_policy, policy_id,
                          name="StillA", stages=[{"failure_threshold": -1}])
        db.session.rollback()
        self.assertEqual("A", get_lockout_policy(policy_id)["name"])
        # unknown id
        self.assertRaises(ResourceNotFoundError, update_lockout_policy, 424242, name="X")

    def test_06_delete(self):
        policy_id = create_lockout_policy("Doomed", 600, ["PIN_FAIL"],
                                          [_stage(5), _stage(10, priority=2)],
                                          target=LockoutTarget.USER)
        self.assertEqual(policy_id, delete_lockout_policy(policy_id))
        self.assertRaises(ResourceNotFoundError, get_lockout_policy, policy_id)
        # cascades removed the children
        self.assertEqual(0, db.session.query(LockoutPolicyStage).count())
        self.assertEqual(0, db.session.query(LockoutStageAction).count())
        self.assertEqual(0, db.session.query(LockoutPolicyCounterType).count())
        self.assertRaises(ResourceNotFoundError, delete_lockout_policy, policy_id)

    def test_07_enable_disable(self):
        policy_id = create_lockout_policy("Toggle", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER)
        enable_lockout_policy(policy_id, enable=False)
        self.assertFalse(get_lockout_policy(policy_id)["enabled"])
        enable_lockout_policy(policy_id)
        self.assertTrue(get_lockout_policy(policy_id)["enabled"])
        self.assertRaises(ResourceNotFoundError, enable_lockout_policy, 424242)

    def test_08_actions_by_target_is_exhaustive(self):
        # Guard the manual registration in _ACTIONS_BY_TARGET so a newly added enum
        # option is not silently forgotten: every LockoutTarget must have an entry
        # (a missing key would KeyError at validation), and every LockoutAction must
        # be allowed on at least one target (else it is unusable on any policy).
        self.assertSetEqual(set(LockoutTarget), set(_ACTIONS_BY_TARGET),
                            "a LockoutTarget is missing from _ACTIONS_BY_TARGET")
        covered = set().union(*_ACTIONS_BY_TARGET.values())
        self.assertSetEqual(set(LockoutAction), covered,
                            "a LockoutAction is not assignable to any target")

    def test_09_count_modes_by_target_is_exhaustive(self):
        # Guard the per-target count-mode registration like test_08 does for actions: every target needs an entry in
        # both maps (a missing key KeyErrors at validation), each target's default must be one of its allowed modes,
        # and every CountMode must be usable on some target (else it is dead).
        self.assertSetEqual(set(LockoutTarget), set(_COUNT_MODES_BY_TARGET),
                            "a LockoutTarget is missing from _COUNT_MODES_BY_TARGET")
        self.assertSetEqual(set(LockoutTarget), set(_DEFAULT_COUNT_MODE_BY_TARGET),
                            "a LockoutTarget is missing from _DEFAULT_COUNT_MODE_BY_TARGET")
        for target, default in _DEFAULT_COUNT_MODE_BY_TARGET.items():
            self.assertIn(default, _COUNT_MODES_BY_TARGET[target],
                          f"the default count_mode for {target} is not among its allowed modes")
        covered = set().union(*_COUNT_MODES_BY_TARGET.values())
        self.assertSetEqual(set(CountMode), covered, "a CountMode is not usable on any target")
