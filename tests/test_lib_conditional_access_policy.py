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
from privacyidea.lib.conditional_access.engine import LockoutAction, LockoutTarget
from privacyidea.lib.conditional_access.lockout_policy import (_ACTIONS_BY_TARGET,
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
        for model in (LockoutStageAction, LockoutPolicyStage, LockoutPolicyCounterType, LockoutPolicy):
            db.session.query(model).delete()
        db.session.commit()

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
        self.assertEqual(["PIN_FAIL", "MFA_FAIL"], policy["counter_types_to_track"])
        self.assertEqual(2, len(policy["stages"]))
        # stages are ordered by stage priority desc (evaluation order)
        self.assertEqual(10, policy["stages"][0]["failure_threshold"])
        self.assertEqual(2, len(policy["stages"][0]["actions"]))
        self.assertEqual({"lock_duration_seconds": 600},
                         policy["stages"][1]["actions"][0]["action_value"])

    def test_02_create_validation_errors(self):
        valid = dict(time_window_seconds=600, counter_types_to_track=["PIN_FAIL"],
                     stages=[_stage()], target=LockoutTarget.USER, priority=1)
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
                          [{"priority": 1}], target=usr, priority=2)  # missing threshold
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(5), _stage(5)], target=usr, priority=2)  # duplicate threshold
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "bogus": 1}], target=usr, priority=2)  # unknown stage key
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [5], target=usr, priority=2)  # stage is not a dict
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "actions": "notalist"}], target=usr, priority=2)  # actions not a list
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [{"failure_threshold": 5, "actions": [42]}], target=usr, priority=2)  # action not a dict
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "NOT_AN_ACTION"}])], target=usr, priority=2)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "LOCK_USER", "bogus": 1}])], target=usr, priority=2)
        # nothing invalid was persisted
        self.assertEqual(1, db.session.query(LockoutPolicy).count())

    def test_02b_duplicate_counter_types_are_deduplicated(self):
        # A repeated counter type is silently de-duplicated (order preserved),
        # not rejected: tracking the same event type twice has no effect.
        policy_id = create_lockout_policy("Dedup", 600,
                                          ["MFA_FAIL", "PIN_FAIL", "MFA_FAIL"], [_stage()],
                                          target=LockoutTarget.USER, priority=1)
        self.assertEqual(["MFA_FAIL", "PIN_FAIL"],
                         get_lockout_policy(policy_id)["counter_types_to_track"])

    def test_02c_target_action_compatibility(self):
        # BLOCK_IP only makes sense on a source_ip target; LOCK_USER only on a user target.
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "BLOCK_IP"}])], target=LockoutTarget.USER,
                          priority=1)
        self.assertRaises(ParameterError, create_lockout_policy, "P", 600, ["PIN_FAIL"],
                          [_stage(actions=[{"action_type": "LOCK_USER"}])], target=LockoutTarget.SOURCE_IP,
                          priority=2)
        # a source_ip policy may block the offending IP
        create_lockout_policy("Spray", 300, ["PIN_FAIL"],
                              [_stage(20, actions=[{"action_type": "BLOCK_IP",
                                                    "action_value": {"duration_seconds": 3600}}])],
                              target=LockoutTarget.SOURCE_IP, priority=3)

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
                                          target=LockoutTarget.USER, priority=1)
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
        policy_id = create_lockout_policy("A", 600, ["PIN_FAIL"], [_stage(5)],
                                          target=LockoutTarget.USER, priority=1)
        create_lockout_policy("B", 600, ["PIN_FAIL"], [_stage(5)], target=LockoutTarget.USER, priority=2)
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
                                          target=LockoutTarget.USER, priority=1)
        self.assertEqual(policy_id, delete_lockout_policy(policy_id))
        self.assertRaises(ResourceNotFoundError, get_lockout_policy, policy_id)
        # cascades removed the children
        self.assertEqual(0, db.session.query(LockoutPolicyStage).count())
        self.assertEqual(0, db.session.query(LockoutStageAction).count())
        self.assertEqual(0, db.session.query(LockoutPolicyCounterType).count())
        self.assertRaises(ResourceNotFoundError, delete_lockout_policy, policy_id)

    def test_07_enable_disable(self):
        policy_id = create_lockout_policy("Toggle", 600, ["PIN_FAIL"], [_stage()],
                                          target=LockoutTarget.USER, priority=1)
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

    def test_09_duplicate_priority_rejected(self):
        # priority must be unique across policies: a second policy reusing a
        # priority is rejected and nothing is persisted.
        create_lockout_policy("First", 600, ["PIN_FAIL"], [_stage()], target=LockoutTarget.USER, priority=1)
        self.assertRaises(ParameterError, create_lockout_policy, "Second", 600, ["PIN_FAIL"],
                          [_stage()], target=LockoutTarget.USER, priority=1)
        self.assertEqual(1, db.session.query(LockoutPolicy).count())

    def test_10_update_to_used_priority_rejected(self):
        first = create_lockout_policy("First", 600, ["PIN_FAIL"], [_stage()],
                                      target=LockoutTarget.USER, priority=1)
        create_lockout_policy("Second", 600, ["PIN_FAIL"], [_stage()],
                              target=LockoutTarget.USER, priority=2)
        # moving one policy onto another policy's priority collides
        self.assertRaises(ParameterError, update_lockout_policy, first, priority=2)
        self.assertEqual(1, get_lockout_policy(first)["priority"])

    def test_11_update_keeping_own_priority_ok(self):
        policy_id = create_lockout_policy("Solo", 600, ["PIN_FAIL"], [_stage()],
                                          target=LockoutTarget.USER, priority=5)
        # re-passing the policy's own current priority is not a collision
        update_lockout_policy(policy_id, name="Solo2", priority=5)
        policy = get_lockout_policy(policy_id)
        self.assertEqual("Solo2", policy["name"])
        self.assertEqual(5, policy["priority"])
