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
Unit tests for the conditional-access lockout policy engine
(:mod:`privacyidea.lib.conditional_access.engine`): the failure-count query, the
pre-check lock test, and the policy-evaluation workflow (stage selection,
de-duplication, dry-run, and the LOCK_USER / PERMANENT_LOCK_USER actions).
"""
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from email import message_from_string

import mock

from privacyidea.lib.conditional_access import engine
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, CountMode
from privacyidea.lib.conditional_access.authentication_log import AuthLogUserRole
from privacyidea.lib.conditional_access.conditions import (CONDITION_TYPES, ConditionOperator, ConditionType,
                                                           ConditionTypeSpec, condition_matches,
                                                           conditions_match_row, policy_conditions_are_scopable,
                                                           policy_matches_context)
from privacyidea.lib.conditional_access.context import CAContext
from privacyidea.lib.conditional_access.engine import (
    AccessDecision,
    LockoutAction,
    LockoutTarget,
    count_user_events,
    count_user_attempts,
    count_distinct_users_for_ip,
    count_ip_events,
    count_ip_attempts,
    evaluate_access_decision,
    evaluate_lockout_policies,
    get_user_lockout,
    is_user_locked,
    is_ip_blocked,
    is_ip_never_block,
    get_ip_block,
    render_error_message,
    RestrictionStatus,
    _lock_duration_seconds,
    _policy_count_ip,
    _safe_format,
    _resolve_admin_recipients,
)
from privacyidea.lib.conditional_access.lockout_policy import (StageDefinition, StageActionDefinition,
                                                               _build_stages)
from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config, SYSCONF
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.lib.user import User
from privacyidea.models import Admin, db
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.lockout_policy import (
    BlockList,
    LockoutPolicy,
    LockoutPolicyCondition,
    LockoutPolicyStage,
    LockoutStageAction,
    UserLockoutState,
)
from privacyidea.models.utils import utc_now
from . import smtpmock
from .conditional_access_lockout_base import LockoutTestCase


class LockoutEngineTestCase(LockoutTestCase):

    def _seed_attempt(self, attempt_id: str, event_types: list[AuthEventType],
                      timestamp: datetime | None = None, user: User | None = None) -> None:
        """Insert one row per event type (in order) sharing *attempt_id*; row ids increase with insertion order,
        so the last event type has the highest id (the 'latest' event of the attempt)."""
        user = user or self.user
        timestamp = timestamp if timestamp is not None else utc_now()
        for event_type in event_types:
            db.session.add(AuthenticationLog(
                event_type=str(event_type), resolver=user.resolver, uid=user.uid,
                realm=user.realm, timestamp=timestamp, attempt_id=attempt_id))
        db.session.commit()

    def _make_policy(self, *, name: str, counter_type, window: int = 3600, enabled: bool = True,
                     dry_run: bool = False, priority: int = 1, target: LockoutTarget = LockoutTarget.USER,
                     count_mode: CountMode | None = None,
                     conditions: Sequence[LockoutPolicyCondition] = (),
                     stages: Sequence[StageDefinition] = (
                             StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)]),)):
        """
        Build a policy with its stages and actions from :class:`StageDefinition` specs, persisted via the production
        :func:`_build_stages`. Builds the ORM rows directly (not through ``create_lockout_policy``) so engine tests
        can also construct deliberately invalid policies (e.g. an unknown action type) that the CRUD would reject.

        ``count_mode`` defaults to the target's default (``DISTINCT_USERS`` for source_ip, else ``PER_REQUEST``),
        mirroring the CRUD default. An action spec that leaves ``retrigger_above_threshold`` unset gets the same
        action-aware default an admin would get (re-trigger for the ALLOW/DENY decisions, fire-once for the
        post-response effects), because :func:`_build_stages` resolves it.

        :param stages: the :class:`StageDefinition` specs to create
        """
        if count_mode is None:
            count_mode = CountMode.DISTINCT_USERS if target == LockoutTarget.SOURCE_IP else CountMode.PER_REQUEST
        counter_types = counter_type if isinstance(counter_type, (list, tuple)) else [counter_type]
        policy = LockoutPolicy(name=name, counter_types_to_track=[str(t) for t in counter_types],
                               time_window_seconds=window, enabled=enabled, dry_run=dry_run,
                               priority=priority, target=str(target), count_mode=str(count_mode),
                               conditions=list(conditions), stages=_build_stages(list(stages)))
        db.session.add(policy)
        db.session.commit()
        return policy, list(policy.stages)

    # --- count_distinct_users_for_ip (spraying signal) ------------------------

    def test_count_distinct_users_for_ip_counts_users_not_rows(self):
        ip = "10.0.0.1"
        # 3 users, 2 failures each from the same IP -> 3 distinct users, not 6 rows.
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3, per_user=2)
        self.assertEqual(3, count_distinct_users_for_ip(ip, [AuthEventType.PASSWORD_FAIL], 300))

    def test_count_distinct_users_for_ip_filters_ip_and_type(self):
        self._seed_ip_events("10.0.0.1", AuthEventType.PASSWORD_FAIL, n_users=4)
        # A different IP and a different event type must not contribute.
        self._seed_ip_events("10.0.0.2", AuthEventType.PASSWORD_FAIL, n_users=5)
        self._seed_ip_events("10.0.0.1", AuthEventType.MFA_FAIL, n_users=7)
        self.assertEqual(4, count_distinct_users_for_ip("10.0.0.1", [AuthEventType.PASSWORD_FAIL], 300))

    def test_count_distinct_users_for_ip_window_boundary(self):
        ip = "10.0.0.1"
        now = utc_now()
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=2, timestamp=now)
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3,
                             timestamp=now - timedelta(seconds=7200))
        self.assertEqual(2, count_distinct_users_for_ip(ip, [AuthEventType.PASSWORD_FAIL], 300, window_end=now))

    def test_count_distinct_users_for_ip_counts_unknown_usernames(self):
        # Enumeration / credential stuffing: many *nonexistent* usernames from one IP never resolve
        # (resolver/uid/realm are NULL), so keying on the identity tuple would collapse them all to one.
        # Keying on the attempted username counts each guess as a distinct targeted account.
        ip = "10.0.0.9"
        self._seed_ip_unknown_events(ip, AuthEventType.USER_UNKNOWN, [f"guess{i}" for i in range(8)])
        self.assertEqual(8, count_distinct_users_for_ip(ip, [AuthEventType.USER_UNKNOWN], 300))

    def test_count_distinct_users_for_ip_mixes_resolved_and_unknown(self):
        # Real victims and guessed accounts add up into one "distinct targeted accounts" signal.
        ip = "10.0.0.10"
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        self._seed_ip_unknown_events(ip, AuthEventType.PASSWORD_FAIL, ["ghost1", "ghost2"])
        self.assertEqual(5, count_distinct_users_for_ip(ip, [AuthEventType.PASSWORD_FAIL], 300))

    def test_count_distinct_users_for_ip_userless_rows_collapse(self):
        # A request with no user at all (e.g. an initial usernameless passkey auth) has a NULL username
        # and must not inflate the signal: any number of such rows collapses into a single group.
        ip = "10.0.0.11"
        self._seed_ip_unknown_events(ip, AuthEventType.CHALLENGE_ANSWERED_FAIL, [None, None, None, None])
        self.assertEqual(1, count_distinct_users_for_ip(ip, [AuthEventType.CHALLENGE_ANSWERED_FAIL], 300))

    # --- count_ip_events / count_ip_attempts (per-IP volume, no success reset) -----

    def _seed_ip_attempt(self, source_ip: str, attempt_id: str, event_types: list[AuthEventType],
                         timestamp: datetime | None = None) -> None:
        """Insert one row per event type (in order) from *source_ip* sharing *attempt_id* - the per-IP PER_ATTEMPT
        shape. No user identity is set; only source_ip/attempt_id/event_type/timestamp matter to the IP counters."""
        timestamp = timestamp if timestamp is not None else utc_now()
        for event_type in event_types:
            db.session.add(AuthenticationLog(
                event_type=str(event_type), source_ip=source_ip, attempt_id=attempt_id, timestamp=timestamp))
        db.session.commit()

    def test_count_ip_events_counts_rows_not_users(self):
        ip = "10.1.0.1"
        # 3 users, 2 rows each -> PER_REQUEST counts all 6 rows (where DISTINCT_USERS would count 3).
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3, per_user=2)
        self.assertEqual(6, count_ip_events(ip, [AuthEventType.PASSWORD_FAIL], 300))
        self.assertEqual(3, count_distinct_users_for_ip(ip, [AuthEventType.PASSWORD_FAIL], 300))

    def test_count_ip_events_filters_ip_type_and_window(self):
        now = utc_now()
        self._seed_ip_events("10.1.0.2", AuthEventType.PASSWORD_FAIL, n_users=4, timestamp=now)
        self._seed_ip_events("10.1.0.3", AuthEventType.PASSWORD_FAIL, n_users=5, timestamp=now)
        self._seed_ip_events("10.1.0.2", AuthEventType.MFA_FAIL, n_users=7, timestamp=now)
        self._seed_ip_events("10.1.0.2", AuthEventType.PASSWORD_FAIL, n_users=3,
                             timestamp=now - timedelta(seconds=7200))
        self.assertEqual(4, count_ip_events("10.1.0.2", [AuthEventType.PASSWORD_FAIL], 300, window_end=now))

    def test_count_ip_events_counts_userless_rows(self):
        # The userless / serial-only rows that DISTINCT_USERS collapses to one still each count as raw volume.
        ip = "10.1.0.4"
        self._seed_ip_unknown_events(ip, AuthEventType.CHALLENGE_ANSWERED_FAIL, [None, None, None, None])
        self.assertEqual(4, count_ip_events(ip, [AuthEventType.CHALLENGE_ANSWERED_FAIL], 300))
        self.assertEqual(1, count_distinct_users_for_ip(ip, [AuthEventType.CHALLENGE_ANSWERED_FAIL], 300))

    def test_count_ip_attempts_collapses_multi_row_attempt(self):
        ip = "10.1.0.5"
        # Two distinct attempts, one spanning three rows: PER_ATTEMPT counts 2 (PER_REQUEST would count 4).
        self._seed_ip_attempt(ip, "a1", [AuthEventType.CHALLENGE_ANSWERED_FAIL, AuthEventType.PASSWORD_FAIL])
        self._seed_ip_attempt(ip, "a2", [AuthEventType.PASSWORD_FAIL, AuthEventType.PASSWORD_FAIL, AuthEventType.PASSWORD_FAIL])
        self.assertEqual(2, count_ip_attempts(ip, [AuthEventType.PASSWORD_FAIL], 300))
        self.assertEqual(4, count_ip_events(ip, [AuthEventType.PASSWORD_FAIL], 300))

    def test_count_ip_attempts_login_success_supersedes_failure_in_attempt(self):
        # A LOGIN_SUCCESS is terminal for its attempt (fetched even though untracked), so a failed row in the same
        # attempt does not make it count as a failure.
        ip = "10.1.0.6"
        self._seed_ip_attempt(ip, "won", [AuthEventType.PASSWORD_FAIL, AuthEventType.LOGIN_SUCCESS])
        self._seed_ip_attempt(ip, "lost", [AuthEventType.PASSWORD_FAIL])
        self.assertEqual(1, count_ip_attempts(ip, [AuthEventType.PASSWORD_FAIL], 300))

    def test_count_ip_volume_modes_do_not_reset_on_success(self):
        # A successful login by one account must not clear per-IP volume aggregated across the IP (unlike the user
        # counters' since_last_success). Both volume modes keep counting the pre-success failures.
        ip = "10.1.0.7"
        self._seed_ip_attempt(ip, "s1", [AuthEventType.PASSWORD_FAIL])
        self._seed_ip_attempt(ip, "s2", [AuthEventType.PASSWORD_FAIL])
        self._seed_ip_attempt(ip, "ok", [AuthEventType.LOGIN_SUCCESS])
        self.assertEqual(2, count_ip_events(ip, [AuthEventType.PASSWORD_FAIL], 300))
        self.assertEqual(2, count_ip_attempts(ip, [AuthEventType.PASSWORD_FAIL], 300))

    def test_source_ip_per_request_policy_blocks_on_volume_from_one_user(self):
        # PER_REQUEST on a source_ip target = plain per-IP rate limiting: raw request volume from a single account
        # trips it, where the DISTINCT_USERS spraying signal (1 distinct user) never would.
        ip = "203.0.113.20"
        self._make_policy(name="ratelimit", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP, count_mode=CountMode.PER_REQUEST,
                          stages=(StageDefinition(failure_threshold=5, priority=1,
                                                  actions=[StageActionDefinition(LockoutAction.BLOCK_IP, {"duration_seconds": 3600})]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=1, per_user=5)
        self.assertFalse(is_ip_blocked(ip))
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        self.assertTrue(is_ip_blocked(ip))

    # --- source_ip target evaluation (spraying) -------------------------------

    def test_spraying_policy_blocks_ip(self):
        ip = "203.0.113.7"
        self._make_policy(name="spray", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(20, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, {"duration_seconds": 3600})]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=20)
        self.assertFalse(is_ip_blocked(ip))
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        self.assertTrue(is_ip_blocked(ip))

    def test_spraying_policy_below_threshold_does_not_block(self):
        ip = "203.0.113.8"
        self._make_policy(name="spray", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(20, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, {"duration_seconds": 3600})]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=19)
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        self.assertFalse(is_ip_blocked(ip))

    def test_spraying_policy_without_source_ip_is_skipped(self):
        self._make_policy(name="spray", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(1, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, {"duration_seconds": 3600})]),))
        self._seed_ip_events("203.0.113.9", AuthEventType.PASSWORD_FAIL, n_users=5)
        # No source IP on the current request -> the IP-targeted policy cannot act.
        self.assertEqual([], evaluate_lockout_policies(CAContext(self.user, None),
                                                      AuthEventType.PASSWORD_FAIL).notices)

    # --- count_user_events ----------------------------------------------------

    def test_count_user_events_window_boundary(self):
        now = utc_now()
        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now)
        self._seed_events(AuthEventType.MFA_FAIL, 1, timestamp=now - timedelta(seconds=7200))
        # Only the two recent events fall inside the 1h window.
        self.assertEqual(2, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600, window_end=now))
        # Widening the window picks up the old one as well.
        self.assertEqual(3, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 100000, window_end=now))

    def test_count_user_events_excludes_future_rows(self):
        now = utc_now()
        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now - timedelta(seconds=60))
        # A row time-stamped after `now` (clock skew, a concurrent insert, or an
        # explicitly historical `now`) must not be counted: the window ends at `now`.
        self._seed_events(AuthEventType.MFA_FAIL, 1, timestamp=now + timedelta(seconds=60))
        self.assertEqual(2, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600, window_end=now))

    def test_count_user_events_filters_event_type_and_user(self):
        self._seed_events(AuthEventType.MFA_FAIL, 2)
        self._seed_events(AuthEventType.PIN_FAIL, 5)
        self.assertEqual(2, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600))
        # A different user identity is not counted.
        self.assertEqual(0, count_user_events("other", "999", self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600))

    def test_count_user_events_since_last_success_floors_at_login(self):
        now = utc_now()
        # Two failures, then a successful login, then one more failure.
        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now - timedelta(seconds=300))
        self._seed_events(AuthEventType.LOGIN_SUCCESS, 1, timestamp=now - timedelta(seconds=200))
        self._seed_events(AuthEventType.MFA_FAIL, 1, timestamp=now - timedelta(seconds=100))
        args = (self.user.resolver, self.user.uid, self.user.realm, [AuthEventType.MFA_FAIL], 3600)
        # Without the reset, all three failures are in the window.
        self.assertEqual(3, count_user_events(*args, window_end=now))
        # With the reset, only the failure after the successful login counts.
        self.assertEqual(1, count_user_events(*args, window_end=now, since_last_success=True))

    def test_count_user_events_since_last_success_no_login_counts_all(self):
        now = utc_now()
        self._seed_events(AuthEventType.MFA_FAIL, 3, timestamp=now - timedelta(seconds=100))
        # No LOGIN_SUCCESS in the window -> the floor does not apply, count is unchanged.
        self.assertEqual(3, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600, window_end=now,
                                              since_last_success=True))

    def test_count_user_events_since_last_success_ignores_login_outside_window(self):
        now = utc_now()
        # The successful login is older than the window, so it must not floor the count.
        self._seed_events(AuthEventType.LOGIN_SUCCESS, 1, timestamp=now - timedelta(seconds=7200))
        self._seed_events(AuthEventType.MFA_FAIL, 3, timestamp=now - timedelta(seconds=100))
        self.assertEqual(3, count_user_events(self.user.resolver, self.user.uid, self.user.realm,
                                              [AuthEventType.MFA_FAIL], 3600, window_end=now,
                                              since_last_success=True))

    def test_count_user_events_combined_types(self):
        # A list of event types is counted together (OR-sum), not per type; an
        # untracked type does not contribute.
        self._seed_events(AuthEventType.PASSWORD_FAIL, 2)
        self._seed_events(AuthEventType.TOKEN_ONLY_FAIL, 3)
        self._seed_events(AuthEventType.MFA_FAIL, 4)
        args = (self.user.resolver, self.user.uid, self.user.realm)
        self.assertEqual(5, count_user_events(
            *args, [AuthEventType.PASSWORD_FAIL, AuthEventType.TOKEN_ONLY_FAIL], 3600))
        # A single-element list counts just that type.
        self.assertEqual(2, count_user_events(*args, [AuthEventType.PASSWORD_FAIL], 3600))

    # --- count_user_attempts --------------------------------------------------

    def _count_attempts(self, event_types: list[AuthEventType], window: int = 3600,
                        window_end: datetime | None = None, since_last_success: bool = False) -> int:
        return count_user_attempts(self.user.resolver, self.user.uid, self.user.realm,
                                   event_types, window, window_end=window_end,
                                   since_last_success=since_last_success)

    def test_count_attempts_multi_row_attempt_counts_once(self):
        # A challenge attempt spanning several rows is one attempt: its representative is the latest event.
        self._seed_attempt("a1", [AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.MFA_FAIL])
        self.assertEqual(1, self._count_attempts([AuthEventType.MFA_FAIL]))
        # The trigger event is not the representative (a later failure superseded it).
        self.assertEqual(0, self._count_attempts([AuthEventType.CHALLENGE_TRIGGERED]))

    def test_count_attempts_distinct_attempts(self):
        self._seed_attempt("a1", [AuthEventType.MFA_FAIL])
        self._seed_attempt("a2", [AuthEventType.PIN_FAIL, AuthEventType.MFA_FAIL])
        # Two separate attempts, both ending in MFA_FAIL.
        self.assertEqual(2, self._count_attempts([AuthEventType.MFA_FAIL]))

    def test_count_attempts_login_success_absorbs_retry(self):
        # A wrong answer then a correct one on the same attempt is a success, not a failure.
        self._seed_attempt("a1", [AuthEventType.MFA_FAIL, AuthEventType.LOGIN_SUCCESS])
        self.assertEqual(0, self._count_attempts([AuthEventType.MFA_FAIL]))
        self.assertEqual(1, self._count_attempts([AuthEventType.LOGIN_SUCCESS]))

    def test_count_attempts_login_success_absorbs_later_stray(self):
        # A stray answer replayed after the attempt already logged in (same attempt_id, higher id) must not
        # flip the success to a failure.
        self._seed_attempt("a1", [AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.LOGIN_SUCCESS,
                                  AuthEventType.CHALLENGE_ANSWERED_FAIL])
        self.assertEqual(1, self._count_attempts([AuthEventType.LOGIN_SUCCESS]))
        self.assertEqual(0, self._count_attempts([AuthEventType.CHALLENGE_ANSWERED_FAIL]))

    def test_count_attempts_multichallenge_order_by_id(self):
        # Same event types, opposite order: the representative is the latest event (by row id), which an
        # event-type ranking could not tell apart.
        # Wrong answer then progressed (continue) -> in progress, not a failure.
        self._seed_attempt("a1", [AuthEventType.MFA_FAIL, AuthEventType.CHALLENGE_CONTINUED])
        # Progressed then failed the next challenge -> a failure.
        self._seed_attempt("a2", [AuthEventType.CHALLENGE_CONTINUED, AuthEventType.MFA_FAIL])
        self.assertEqual(1, self._count_attempts([AuthEventType.MFA_FAIL]))  # only a2
        self.assertEqual(1, self._count_attempts([AuthEventType.CHALLENGE_CONTINUED]))  # only a1

    def test_count_attempts_ignores_a_conditional_access_rejection_row(self):
        # The rejection rows conditional access writes for itself are not outcomes *of* the attempt and must not
        # classify one. The representative is the latest row by id, so a rejection correlated into an existing attempt
        # (a client retrying an answered transaction while locked) would otherwise displace the tracked failure with an
        # untracked type and *remove* an attempt that had already been counted - which would stop an escalation from
        # reaching its next stage once the lock expired. Excluding the type from the trackable vocabulary cannot help
        # here: every in-window row of the subject is fetched, whatever its type.
        self._seed_attempt("a1", [AuthEventType.MFA_FAIL])
        self.assertEqual(1, self._count_attempts([AuthEventType.MFA_FAIL]))

        self._seed_attempt("a1", [AuthEventType.USER_LOCKED])
        self.assertEqual(1, self._count_attempts([AuthEventType.MFA_FAIL]))

    def test_count_attempts_of_a_rejection_only_attempt_is_zero(self):
        # An attempt made up of nothing but rejections contributes nothing, rather than counting as an attempt of an
        # untracked type.
        self._seed_attempt("only", [AuthEventType.IP_BLOCKED, AuthEventType.ACCESS_DENIED])
        self.assertEqual(0, self._count_attempts([AuthEventType.MFA_FAIL]))
        self.assertEqual(0, self._count_attempts([AuthEventType.IP_BLOCKED]))

    def test_count_attempts_combined_types_and_window(self):
        now = utc_now()
        self._seed_attempt("a1", [AuthEventType.MFA_FAIL], timestamp=now)
        self._seed_attempt("a2", [AuthEventType.PIN_FAIL], timestamp=now)
        self._seed_attempt("a3", [AuthEventType.MFA_FAIL], timestamp=now - timedelta(seconds=7200))
        # Both failure types counted together, and only the two inside the 1h window.
        self.assertEqual(2, self._count_attempts([AuthEventType.MFA_FAIL, AuthEventType.PIN_FAIL],
                                                 window=3600, window_end=now))
        # A different user is not counted.
        self.assertEqual(0, count_user_attempts("other", "999", self.user.realm,
                                                [AuthEventType.MFA_FAIL], 3600, window_end=now))

    def test_count_attempts_since_last_success_resets(self):
        # A successful attempt floors the per-attempt count: only failed attempts after the last completed login
        # count, so a good login clears the slate (the per-attempt counterpart of count_user_events' reset).
        self._seed_attempt("a1", [AuthEventType.MFA_FAIL])
        self._seed_attempt("a2", [AuthEventType.LOGIN_SUCCESS])
        self._seed_attempt("a3", [AuthEventType.MFA_FAIL])
        self.assertEqual(1, self._count_attempts([AuthEventType.MFA_FAIL], since_last_success=True))
        # Without the reset, both failed attempts (before and after the success) count.
        self.assertEqual(2, self._count_attempts([AuthEventType.MFA_FAIL], since_last_success=False))

    def test_count_attempts_since_last_success_no_success_counts_all(self):
        # With no successful attempt in the window the floor is inert: all failed attempts count.
        self._seed_attempt("a1", [AuthEventType.MFA_FAIL])
        self._seed_attempt("a2", [AuthEventType.MFA_FAIL])
        self.assertEqual(2, self._count_attempts([AuthEventType.MFA_FAIL], since_last_success=True))

    # --- is_user_locked -------------------------------------------------------

    def test_is_user_locked_no_row(self):
        self.assertFalse(is_user_locked(self.user))

    def test_is_user_locked_timed_future(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self.assertTrue(is_user_locked(self.user))

    def test_is_user_locked_timed_expired(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=utc_now() - timedelta(seconds=600)))
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

    def test_is_user_locked_permanent(self):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=None))
        db.session.commit()
        self.assertTrue(is_user_locked(self.user))

    def test_is_user_locked_unresolved_user(self):
        self.assertFalse(is_user_locked(User()))

    # --- get_user_lockout clear_expired ---------------------------------------

    def _add_lockout(self, lock_expires_at):
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, lock_expires_at=lock_expires_at))
        db.session.commit()

    def test_clear_expired_deletes_stale_row(self):
        # An expired timed lock is dropped when the pre-check opts in.
        self._add_lockout(utc_now() - timedelta(seconds=600))
        self.assertIsNone(get_user_lockout(self.user, clear_expired=True))
        self.assertIsNone(self._state())

    def test_clear_expired_default_keeps_stale_row(self):
        # The default is a pure read: an expired row reads as unlocked but stays.
        self._add_lockout(utc_now() - timedelta(seconds=600))
        self.assertIsNone(get_user_lockout(self.user))
        self.assertIsNotNone(self._state())

    def test_clear_expired_keeps_active_lock(self):
        # A still-active timed lock is never deleted, even with clear_expired.
        self._add_lockout(utc_now() + timedelta(seconds=600))
        self.assertIsNotNone(get_user_lockout(self.user, clear_expired=True))
        self.assertIsNotNone(self._state())

    def test_clear_expired_keeps_permanent_lock(self):
        # A permanent lock is never deleted, even with clear_expired.
        self._add_lockout(None)
        status = get_user_lockout(self.user, clear_expired=True)
        self.assertIsNotNone(status)
        self.assertTrue(status.permanent)
        self.assertIsNotNone(self._state())

    def test_is_user_locked_clear_expired_deletes_stale_row(self):
        # The boolean wrapper threads clear_expired through to get_user_lockout.
        self._add_lockout(utc_now() - timedelta(seconds=600))
        self.assertFalse(is_user_locked(self.user, clear_expired=True))
        self.assertIsNone(self._state())

    # --- is_ip_blocked --------------------------------------------------------

    def test_is_ip_blocked_no_row(self):
        self.assertFalse(is_ip_blocked("203.0.113.5"))

    def test_is_ip_blocked_timed_future(self):
        db.session.add(BlockList(ip="203.0.113.5", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self.assertTrue(is_ip_blocked("203.0.113.5"))

    def test_is_ip_blocked_timed_expired(self):
        db.session.add(BlockList(ip="203.0.113.5", block_expires_at=utc_now() - timedelta(seconds=600)))
        db.session.commit()
        self.assertFalse(is_ip_blocked("203.0.113.5"))

    def test_is_ip_blocked_permanent(self):
        db.session.add(BlockList(ip="203.0.113.5", block_expires_at=None))
        db.session.commit()
        self.assertTrue(is_ip_blocked("203.0.113.5"))

    def test_is_ip_blocked_empty_ip(self):
        # A request without a resolvable source IP is never blocked.
        self.assertFalse(is_ip_blocked(None))
        self.assertFalse(is_ip_blocked(""))

    # --- get_ip_block ---------------------------------------------------------

    def test_get_ip_block_none_when_not_blocked(self):
        self.assertIsNone(get_ip_block("203.0.113.5"))
        self.assertIsNone(get_ip_block(None))

    def test_get_ip_block_timed_reports_remaining(self):
        now = utc_now()
        db.session.add(BlockList(ip="203.0.113.5", block_expires_at=now + timedelta(seconds=600)))
        db.session.commit()
        block = get_ip_block("203.0.113.5", now=now)
        self.assertEqual(False, block.permanent, block)
        self.assertEqual(600, block.seconds_remaining, block)
        self.assertIsNotNone(block.expires_at, block)

    def test_get_ip_block_expired_reads_as_unblocked(self):
        db.session.add(BlockList(ip="203.0.113.5", block_expires_at=utc_now() - timedelta(seconds=1)))
        db.session.commit()
        self.assertIsNone(get_ip_block("203.0.113.5"))

    def test_get_ip_block_permanent(self):
        db.session.add(BlockList(ip="203.0.113.5", block_expires_at=None))
        db.session.commit()
        block = get_ip_block("203.0.113.5")
        self.assertEqual(True, block.permanent, block)
        self.assertIsNone(block.seconds_remaining, block)
        self.assertIsNone(block.expires_at, block)

    # --- get_ip_block clear_expired -------------------------------------------

    def _add_block(self, ip, block_expires_at):
        db.session.add(BlockList(ip=ip, block_expires_at=block_expires_at))
        db.session.commit()

    def test_ip_clear_expired_deletes_stale_row(self):
        # An expired timed block is dropped when the pre-check opts in.
        self._add_block("203.0.113.5", utc_now() - timedelta(seconds=600))
        self.assertIsNone(get_ip_block("203.0.113.5", clear_expired=True))
        self.assertIsNone(self._block("203.0.113.5"))

    def test_ip_clear_expired_default_keeps_stale_row(self):
        # The default is a pure read: an expired row reads as unblocked but stays.
        self._add_block("203.0.113.5", utc_now() - timedelta(seconds=600))
        self.assertIsNone(get_ip_block("203.0.113.5"))
        self.assertIsNotNone(self._block("203.0.113.5"))

    def test_ip_clear_expired_keeps_active_block(self):
        # A still-active timed block is never deleted, even with clear_expired.
        self._add_block("203.0.113.5", utc_now() + timedelta(seconds=600))
        self.assertIsNotNone(get_ip_block("203.0.113.5", clear_expired=True))
        self.assertIsNotNone(self._block("203.0.113.5"))

    def test_ip_clear_expired_keeps_permanent_block(self):
        # A permanent block is never deleted, even with clear_expired.
        self._add_block("203.0.113.5", None)
        block = get_ip_block("203.0.113.5", clear_expired=True)
        self.assertIsNotNone(block)
        self.assertTrue(block.permanent)
        self.assertIsNotNone(self._block("203.0.113.5"))

    def test_is_ip_blocked_clear_expired_deletes_stale_row(self):
        # The boolean wrapper threads clear_expired through to get_ip_block.
        self._add_block("203.0.113.5", utc_now() - timedelta(seconds=600))
        self.assertFalse(is_ip_blocked("203.0.113.5", clear_expired=True))
        self.assertIsNone(self._block("203.0.113.5"))

    # --- evaluate_lockout_policies --------------------------------------------

    def test_evaluate_triggers_lock(self):
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        state = self._state()
        self.assertIsNotNone(state)
        self.assertIsNotNone(state.lock_expires_at)
        self.assertGreater(state.lock_expires_at, utc_now())
        self.assertTrue(is_user_locked(self.user))

    def test_evaluate_below_threshold_does_not_lock(self):
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 2)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    def test_evaluate_no_op_for_unresolved_user(self):
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        # No event_type / no resolved user must be a no-op without raising.
        evaluate_lockout_policies(CAContext(self.user), None)
        evaluate_lockout_policies(CAContext(User()), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    def test_evaluate_disabled_policy_skipped(self):
        self._make_policy(name="off", counter_type=AuthEventType.MFA_FAIL, enabled=False)
        self._seed_events(AuthEventType.MFA_FAIL, 5)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    def test_evaluate_non_matching_event_type_skipped(self):
        self._make_policy(name="mfa", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.PIN_FAIL, 5)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.PIN_FAIL)
        self.assertIsNone(self._state())

    def test_evaluate_combined_count_across_tracked_types(self):
        # A policy tracking several types locks on the *combined* count: 2 + 1 = 3
        # reaches the threshold even though neither type alone does.
        self._make_policy(name="combo",
                          counter_type=[AuthEventType.PASSWORD_FAIL, AuthEventType.MFA_FAIL])
        self._seed_events(AuthEventType.PASSWORD_FAIL, 2)
        self._seed_events(AuthEventType.MFA_FAIL, 1)
        # The current request is an MFA_FAIL — one of the tracked types.
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_evaluate_untracked_current_event_skips_policy(self):
        # The policy only reacts when the *current* event type is one it tracks,
        # even if enough events of its tracked types already exist.
        self._make_policy(name="combo",
                          counter_type=[AuthEventType.PASSWORD_FAIL, AuthEventType.PIN_FAIL])
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3)
        # MFA_FAIL is not tracked by this policy -> skipped, no lock.
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())
        # A tracked type triggers it.
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.PASSWORD_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_stage_exact_threshold_selection(self):
        # A stage fires only at its EXACT threshold: threshold 5 (mild) and
        # threshold 15 (severe). An intermediate count between the two triggers
        # nothing; each stage fires when its own threshold is hit exactly.
        _, stages = self._make_policy(
            name="tiers", counter_type=AuthEventType.MFA_FAIL,
            stages=(StageDefinition(15, 2, [StageActionDefinition(LockoutAction.LOCK_USER, 1800)]),
                    StageDefinition(5, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)])))
        severe_stage, mild_stage = stages[0], stages[1]

        # Exactly 5 -> the mild stage fires. The recorded outcome names the stage by its threshold.
        self._seed_events(AuthEventType.MFA_FAIL, 5)
        self.assertListEqual([mild_stage.failure_threshold], self._triggered_thresholds())

        # 6..14 are between the two thresholds -> nothing fires.
        self._seed_events(AuthEventType.MFA_FAIL, 3)  # total 8
        self.assertListEqual([], self._triggered_thresholds())

        # Exactly 15 -> the severe stage fires.
        self._seed_events(AuthEventType.MFA_FAIL, 7)  # total 15
        self.assertListEqual([severe_stage.failure_threshold], self._triggered_thresholds())

    def test_successful_login_resets_lock_counter(self):
        # A completed login clears the accumulated failures: the threshold then
        # applies to failures *after* the login, so a single later typo does not
        # re-lock a user who already authenticated successfully.
        now = utc_now()
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3, timestamp=now - timedelta(seconds=300))
        self._seed_events(AuthEventType.LOGIN_SUCCESS, 1, timestamp=now - timedelta(seconds=200))

        # One failure after the successful login: 1 < 3 -> not locked, the three
        # pre-login failures no longer count.
        self._seed_events(AuthEventType.MFA_FAIL, 1, timestamp=now - timedelta(seconds=100))
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL, now=now)
        self.assertIsNone(self._state())
        self.assertFalse(is_user_locked(self.user))

        # Two more post-login failures reach the threshold again (1 + 2 = 3) -> locked.
        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now - timedelta(seconds=50))
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL, now=now)
        self.assertTrue(is_user_locked(self.user))

    def test_expired_lock_is_reapplied_when_the_threshold_is_still_met(self):
        # An expired lock leaves the failures in the window, so the stage locks the user again rather than leaving a
        # dead zone in which the threshold is met but nothing is in force.
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

        # The lock runs out while the original failures are still in the window.
        state = self._state()
        state.lock_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

        # The threshold is still met, so the stage locks again.
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_admin_unlock_is_undone_when_the_threshold_is_still_met(self):
        # An admin lifting the lock deletes the row, but the failures stay in the window, so the stage locks the user
        # again on the next evaluation.
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

        # Admin lifts the lock by deleting the row.
        db.session.delete(self._state())
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

        # The threshold is still met, so the stage locks again.
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_fire_once_default_does_not_refire_above_threshold(self):
        # Default (retrigger_above_threshold unset): after the lock expires, a
        # further failure that pushes the count above the threshold does NOT
        # re-fire the threshold-3 stage.
        self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

        state = self._state()
        state.lock_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

        # Count climbs to 4 (> 3) -> no exact match -> no re-lock.
        self._seed_events(AuthEventType.MFA_FAIL, 1)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertFalse(is_user_locked(self.user))

    def test_retrigger_above_threshold_refires(self):
        # With retrigger_above_threshold the action keeps firing while the count is
        # at or above its threshold: after the lock expires, a further failure
        # (count 4 >= 3) re-locks the classic way.
        _, stages = self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        stages[0].actions[0].retrigger_above_threshold = True
        db.session.commit()
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

        state = self._state()
        state.lock_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

        # Count climbs to 4 (>= 3) -> the re-triggering action fires again.
        self._seed_events(AuthEventType.MFA_FAIL, 1)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_dry_run_writes_no_state(self):
        self._make_policy(name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True)
        self._seed_events(AuthEventType.MFA_FAIL, 5)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())
        self.assertFalse(is_user_locked(self.user))

    def test_dry_run_returns_an_outcome_for_every_action_it_would_have_run(self):
        # A dry-run policy writes no state; what it *would* have done comes back as outcomes for the caller to record
        # as this request's history (the engine itself never writes them).
        policy, _stages = self._make_policy(name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluation = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)

        self.assertEqual(1, len(evaluation.outcomes))
        outcome = evaluation.outcomes[0]
        self.assertTrue(outcome.dry_run)
        self.assertEqual(str(LockoutAction.LOCK_USER), outcome.action_type)
        self.assertEqual("dry", outcome.policy_name)
        self.assertEqual(3, outcome.threshold)
        self.assertEqual(3, outcome.event_count)
        # An unnamed stage contributes no name; the threshold identifies the stage either way.
        self.assertIsNone(outcome.stage_name)
        # The expiry the lock *would* have had, so a dry run is comparable with an enforced one. Action-specific
        # detail lives in `info`, not in a column only two of the seven action types would ever fill.
        self.assertIn("expires_at", outcome.info)
        # Still a dry run: no lockout state is ever written.
        self.assertIsNone(self._state())
        self.assertFalse(is_user_locked(self.user))

    def test_dry_run_one_outcome_per_matching_policy(self):
        # Several dry-run policies tracking the same event all evaluate on one request, so one request yields one
        # outcome per policy that would have triggered.
        self._make_policy(name="dry_a", counter_type=AuthEventType.MFA_FAIL, dry_run=True)
        self._make_policy(name="dry_b", counter_type=AuthEventType.MFA_FAIL, dry_run=True, priority=2,
                          stages=(StageDefinition(2, 1, [StageActionDefinition(LockoutAction.PERMANENT_LOCK_USER)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluation = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)

        # dry_b's PERMANENT_LOCK_USER is fire-once at threshold 2 and the count is 3, so only dry_a matches.
        self.assertEqual(["dry_a"], [outcome.policy_name for outcome in evaluation.outcomes])
        self.assertIsNone(self._state())

    def test_dry_run_outcome_records_the_stage_name_when_the_stage_has_one(self):
        # A named stage puts its label in the outcome, so an admin reading the history sees "Lock 10 min" rather than
        # only a threshold.
        self._make_policy(
            name="dry_named", counter_type=AuthEventType.MFA_FAIL, dry_run=True,
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)],
                                    name="Lock 10 min"),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        outcome = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes[0]
        self.assertEqual("Lock 10 min", outcome.stage_name)

    def test_dry_run_below_threshold_records_nothing(self):
        self._make_policy(name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True)
        self._seed_events(AuthEventType.MFA_FAIL, 2)  # below the threshold of 3
        self.assertEqual([], evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes)
        self.assertIsNone(self._state())

    def test_dry_run_fire_once_records_nothing_above_threshold(self):
        # A fire-once action (the default) only fires at the EXACT threshold, and dry-run enforces nothing that would
        # stop the count climbing. So once the count has passed the threshold a dry-run policy records nothing until
        # the window rolls over or a success resets it - the same semantics as a live fire-once policy.
        self._make_policy(name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True)
        self._seed_events(AuthEventType.MFA_FAIL, 6)  # well past the threshold of 3
        self.assertEqual([], evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes)

    def test_dry_run_retrigger_records_a_outcome_above_threshold(self):
        # With a re-triggering action the dry run keeps reporting for as long as the count stays at or above the
        # threshold, which is what makes dry-run usable for sizing a policy.
        _, stages = self._make_policy(name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True)
        stages[0].actions[0].retrigger_above_threshold = True
        db.session.commit()
        self._seed_events(AuthEventType.MFA_FAIL, 6)  # count 6 >= threshold 3
        outcomes = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes

        self.assertEqual(1, len(outcomes))
        self.assertEqual(3, outcomes[0].threshold)
        self.assertEqual(6, outcomes[0].event_count)
        self.assertIsNone(self._state())

    def test_dry_run_records_on_every_qualifying_request(self):
        # A re-triggering action qualifies on every request at or above its threshold, so both requests record an
        # outcome. Dry run differs only in enforcement: it writes no lock, so no state exists at the end.
        _, stages = self._make_policy(name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True)
        stages[0].actions[0].retrigger_above_threshold = True
        db.session.commit()
        self._seed_events(AuthEventType.MFA_FAIL, 3)

        self.assertEqual(1, len(evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes))
        self._seed_events(AuthEventType.MFA_FAIL, 1)
        self.assertEqual(1, len(evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes))
        self.assertIsNone(self._state())

    def test_dry_run_records_one_outcome_per_pending_action_of_the_stage(self):
        # One outcome per action, not one per stage: each action is a separate thing that would have happened, and the
        # history is queried by action.
        self._make_policy(
            name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True,
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600),
                                           StageActionDefinition(LockoutAction.PERMANENT_LOCK_USER)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        outcomes = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes

        self.assertEqual([str(LockoutAction.LOCK_USER), str(LockoutAction.PERMANENT_LOCK_USER)],
                         [outcome.action_type for outcome in outcomes])
        # Only the timed action carries an expiry; a permanent lock has none by definition, so it records no info.
        self.assertIn("expires_at", outcomes[0].info)
        self.assertIsNone(outcomes[1].info)

    def test_dry_run_outcome_has_no_expiry_when_the_duration_is_misconfigured(self):
        # An invalid duration would make the enforced path skip the action entirely. In dry run the outcome is still
        # produced - with no expiry, which is exactly the misconfiguration a dry run is meant to surface.
        self._make_policy(
            name="dry_broken", counter_type=AuthEventType.MFA_FAIL, dry_run=True,
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, "not-a-duration")]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        outcome = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes[0]
        self.assertEqual(str(LockoutAction.LOCK_USER), outcome.action_type)
        self.assertIsNone(outcome.info)

    def test_dry_run_source_ip_policy_records_a_outcome_without_blocking(self):
        ip = "10.10.0.5"
        self._make_policy(name="dry_ip", counter_type=AuthEventType.PASSWORD_FAIL, dry_run=True,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(2, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 600)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=2, per_user=1)
        outcomes = evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL).outcomes

        self.assertEqual("dry_ip", outcomes[0].policy_name)
        self.assertEqual(str(LockoutAction.BLOCK_IP), outcomes[0].action_type)
        # Dry run: the IP is never actually blocked.
        self.assertIsNone(self._block(ip))

    def test_a_failing_policy_does_not_cost_the_other_policies_their_evaluation(self):
        # Guarded per policy: the first one raising must neither disable the ones ordered behind it nor let the
        # failure escape - the caller evaluates the classification again when the call does not return, and a stage
        # whose actions leave no live state (EMAIL-only) has no de-dup to stop the second pass repeating them.
        self._make_policy(name="broken", counter_type=AuthEventType.MFA_FAIL, priority=1)
        self._make_policy(name="works", counter_type=AuthEventType.MFA_FAIL, priority=2)
        self._seed_events(AuthEventType.MFA_FAIL, 3)

        real = engine._evaluate_policy
        calls = []

        def fail_the_first(policy, *args, **kwargs):
            calls.append(policy.name)
            if policy.name == "broken":
                raise RuntimeError("policy boom")
            return real(policy, *args, **kwargs)

        with mock.patch.object(engine, "_evaluate_policy", side_effect=fail_the_first):
            evaluation = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)

        self.assertListEqual(["broken", "works"], calls)
        # The surviving policy still locked the user, and nothing propagated to the caller.
        self.assertListEqual([str(LockoutAction.LOCK_USER)], [outcome.action_type for outcome in evaluation.outcomes])
        self.assertTrue(is_user_locked(self.user))

    def test_dry_run_returns_no_notices(self):
        self._make_policy(name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        self.assertEqual([], evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).notices)

    @smtpmock.activate
    def test_dry_run_email_action_records_the_outcome_but_sends_nothing(self):
        # Dry-run must not produce the side effect itself: the outcome names EMAIL_ADMIN, but no mail is sent and no
        # user-facing notice is returned.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        db.session.add(Admin(username="ca_dry_adm", email="dryadm@example.com"))
        db.session.commit()
        try:
            self._make_policy(
                name="dry_mail", counter_type=AuthEventType.MFA_FAIL, dry_run=True,
                stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.EMAIL_ADMIN,
                                                                     {"smtp_identifier": "lockoutmail",
                                                                      "subject": "s", "body": "b"})]),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            evaluation = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)

            self.assertListEqual([str(LockoutAction.EMAIL_ADMIN)],
                                 [outcome.action_type for outcome in evaluation.outcomes])
            self.assertEqual([], evaluation.notices)
            # Nothing was handed to the SMTP layer at all (the mock reports no recipient).
            self.assertIsNone(smtpmock.get_sent_recipient())
        finally:
            delete_smtpserver("lockoutmail")
            db.session.query(Admin).filter_by(username="ca_dry_adm").delete()
            db.session.commit()

    def test_dry_run_does_not_suppress_a_live_policy_on_the_same_request(self):
        # A dry-run policy is inert, not blocking: an enforcing policy tripped by the same request still locks. Both
        # produce an outcome, and only the dry-run one is flagged.
        self._make_policy(name="dry", counter_type=AuthEventType.MFA_FAIL, dry_run=True, priority=1)
        self._make_policy(name="live", counter_type=AuthEventType.MFA_FAIL, priority=2)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        outcomes = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes

        self.assertEqual([("dry", True), ("live", False)],
                         [(outcome.policy_name, outcome.dry_run) for outcome in outcomes])
        self.assertTrue(is_user_locked(self.user))

    # --- outcomes of an enforced policy: only what actually happened ------------

    def test_enforced_lock_records_the_expiry_it_wrote(self):
        self._make_policy(name="live", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        outcomes = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes

        self.assertEqual(1, len(outcomes))
        self.assertFalse(outcomes[0].dry_run)
        self.assertEqual(str(LockoutAction.LOCK_USER), outcomes[0].action_type)
        # The recorded expiry is the one that ended up in the state row, so the history says how long the lock lasted
        # even after the row is gone - as an aware ISO-8601 string, since `info` is a JSON column.
        self.assertEqual({"expires_at": self._state().lock_expires_at.replace(tzinfo=timezone.utc).isoformat()},
                         outcomes[0].info)

    def test_enforced_permanent_lock_records_no_expiry(self):
        self._make_policy(name="perma", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(3, 1,
                                                  [StageActionDefinition(LockoutAction.PERMANENT_LOCK_USER)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        outcomes = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes

        self.assertEqual(str(LockoutAction.PERMANENT_LOCK_USER), outcomes[0].action_type)
        self.assertIsNone(outcomes[0].info)

    def test_a_skipped_action_records_nothing(self):
        # A misconfigured duration makes the action a no-op, and the history must not claim a lock that never happened.
        # The server log (a warning from _execute_stage_actions) is the record of the misconfiguration.
        self._make_policy(
            name="broken", counter_type=AuthEventType.MFA_FAIL,
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, "not-a-duration")]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        self.assertListEqual([], evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes)
        self.assertFalse(is_user_locked(self.user))

    def test_never_block_ip_records_nothing(self):
        # The never-block allowlist makes BLOCK_IP a no-op, so there is nothing to record either.
        self._make_policy(name="ip_live", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(2, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 600)]),))
        self._seed_ip_events("127.0.0.1", AuthEventType.PASSWORD_FAIL, n_users=2, per_user=1)
        evaluation = evaluate_lockout_policies(CAContext(self.user, "127.0.0.1"), AuthEventType.PASSWORD_FAIL)

        self.assertListEqual([], evaluation.outcomes)
        self.assertIsNone(self._block("127.0.0.1"))

    def test_declined_downgrade_of_a_permanent_lock_records_nothing(self):
        # A timed lock must not weaken an existing permanent one; since nothing changed, nothing is recorded.
        self._make_policy(name="perma", counter_type=AuthEventType.MFA_FAIL, priority=1,
                          stages=(StageDefinition(2, 1,
                                                  [StageActionDefinition(LockoutAction.PERMANENT_LOCK_USER)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 2)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state().lock_expires_at)

        self._make_policy(name="timed", counter_type=AuthEventType.MFA_FAIL, priority=2,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 1)
        outcomes = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes

        self.assertListEqual([], outcomes)
        # The permanent lock is untouched.
        self.assertIsNone(self._state().lock_expires_at)


    # --- per-action fire-once / re-trigger semantics ---------------------------

    def test_retrigger_action_also_fires_at_the_exact_threshold(self):
        # "At or above" includes the threshold itself, so a re-triggering action fires on the first qualifying request
        # too, not only above it.
        _, stages = self._make_policy(name="lock3", counter_type=AuthEventType.MFA_FAIL)
        stages[0].actions[0].retrigger_above_threshold = True
        db.session.commit()
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_fire_once_and_retrigger_actions_in_one_stage_are_decided_separately(self):
        # The flag is per action: above the threshold only the re-triggering LOCK_USER still fires, while the
        # fire-once EMAIL_ADMIN stays silent - one stage that keeps a user locked but emails only once.
        _, stages = self._make_policy(
            name="mixed", counter_type=AuthEventType.MFA_FAIL,
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600,
                                                                 retrigger_above_threshold=True),
                                           StageActionDefinition(LockoutAction.EMAIL_ADMIN,
                                                                 {"smtp_identifier": "nosuch"},
                                                                 retrigger_above_threshold=False)]),))
        lock_action, email_action = stages[0].actions[0], stages[0].actions[1]
        self.assertTrue(lock_action.retrigger_above_threshold)
        self.assertFalse(email_action.retrigger_above_threshold)

        # At a count above the threshold only the re-triggering action is pending, so the stage still fires (the
        # unreachable SMTP identifier would raise if the email action were executed, and is guarded per action).
        self._seed_events(AuthEventType.MFA_FAIL, 5)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_dry_run_outcome_reports_only_the_pending_actions(self):
        # Mirrors the live behaviour above: above the threshold the fire-once action is not pending, so the outcome
        # lists only the re-triggering one.
        self._make_policy(
            name="dry_mixed", counter_type=AuthEventType.MFA_FAIL, dry_run=True,
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600,
                                                                 retrigger_above_threshold=True),
                                           StageActionDefinition(LockoutAction.PERMANENT_LOCK_USER, None,
                                                                 retrigger_above_threshold=False)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 6)  # count 6 > threshold 3
        outcomes = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).outcomes

        self.assertListEqual([str(LockoutAction.LOCK_USER)], [outcome.action_type for outcome in outcomes])

    def test_retrigger_stage_selection_prefers_the_highest_priority_pending_stage(self):
        # Both stages re-trigger and both thresholds are passed, so the most severe (highest-priority) stage is the one
        # that fires; only that one stage's actions run per policy per request.
        _, stages = self._make_policy(
            name="tiers", counter_type=AuthEventType.MFA_FAIL,
            stages=(StageDefinition(5, 2, [StageActionDefinition(LockoutAction.LOCK_USER, 1800,
                                                                 retrigger_above_threshold=True)]),
                    StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600,
                                                                 retrigger_above_threshold=True)])))
        severe_stage = stages[0]
        self._seed_events(AuthEventType.MFA_FAIL, 6)  # past both thresholds

        self.assertListEqual([severe_stage.failure_threshold], self._triggered_thresholds())

    def test_retrigger_falls_back_to_the_lower_stage_when_the_severe_one_is_not_pending(self):
        # The severe stage is fire-once at 15 and the count is 6, so it is not pending; the re-triggering stage at 3 is,
        # and it fires instead.
        _, stages = self._make_policy(
            name="tiers", counter_type=AuthEventType.MFA_FAIL,
            stages=(StageDefinition(15, 2, [StageActionDefinition(LockoutAction.LOCK_USER, 1800)]),
                    StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600,
                                                                 retrigger_above_threshold=True)])))
        mild_stage = stages[1]
        self._seed_events(AuthEventType.MFA_FAIL, 6)

        self.assertListEqual([mild_stage.failure_threshold], self._triggered_thresholds())

    def test_permanent_lock_action(self):
        self._make_policy(name="perm", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.PERMANENT_LOCK_USER)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        state = self._state()
        self.assertIsNone(state.lock_expires_at)
        self.assertTrue(is_user_locked(self.user))

    def test_permanent_lock_not_downgraded_to_timed(self):
        # Pre-existing permanent lock (set by a higher-severity stage).
        db.session.add(UserLockoutState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm,
                                        lock_expires_at=None))
        db.session.commit()
        # A timed LOCK_USER policy now tries to lock the same user.
        self._make_policy(name="timed", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        # The permanent lock must remain permanent (lock_expires_at stays None).
        self.assertIsNone(self._state().lock_expires_at)
        self.assertTrue(is_user_locked(self.user))

    def test_invalid_duration_action_skipped(self):
        self._make_policy(name="baddur", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    def test_unknown_action_type_skipped(self):
        # An unknown action type must be skipped by the engine, not raise. Built via _make_policy (which builds the
        # ORM directly, without CRUD validation) so the invalid action reaches the engine.
        self._make_policy(name="weird", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition("TELEPORT_USER")]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        # Unknown action types are logged and skipped, not raised.
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state())

    # --- never-block allowlist ------------------------------------------------

    def test_loopback_is_never_block_by_default(self):
        self.assertTrue(is_ip_never_block("127.0.0.1"))
        self.assertTrue(is_ip_never_block("127.5.6.7"))
        self.assertTrue(is_ip_never_block("::1"))

    def test_normal_ip_is_not_never_block(self):
        self.assertFalse(is_ip_never_block("203.0.113.7"))

    def test_empty_or_unparseable_ip_is_never_block(self):
        # Fail safe: never block an address the engine cannot positively identify.
        self.assertTrue(is_ip_never_block(None))
        self.assertTrue(is_ip_never_block(""))
        self.assertTrue(is_ip_never_block("not-an-ip"))

    def test_configured_cidr_is_never_block(self):
        set_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK, "203.0.113.0/24, 198.51.100.5")
        try:
            self.assertTrue(is_ip_never_block("203.0.113.7"))
            self.assertTrue(is_ip_never_block("198.51.100.5"))
            self.assertFalse(is_ip_never_block("198.51.100.6"))
            # The built-in loopback default still applies alongside the config.
            self.assertTrue(is_ip_never_block("127.0.0.1"))
        finally:
            delete_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK)

    def test_invalid_config_entry_ignored(self):
        set_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK, "garbage, 203.0.113.0/24")
        try:
            self.assertTrue(is_ip_never_block("203.0.113.7"))
            self.assertFalse(is_ip_never_block("198.51.100.5"))
        finally:
            delete_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK)

    def test_block_ip_action_skips_never_block_ip(self):
        # A BLOCK_IP action must never write a block for a never-block IP (loopback).
        self._make_policy(name="blockloop", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 900)]),))
        self._seed_ip_events("127.0.0.1", AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(self.user, "127.0.0.1"), AuthEventType.PASSWORD_FAIL)
        self.assertEqual(0, db.session.query(BlockList).count())
        self.assertFalse(is_ip_blocked("127.0.0.1"))

    def test_allowlisted_ip_block_row_is_not_enforced(self):
        # Even with an existing block row, an allowlisted IP reads as not blocked, so
        # adding an IP to the allowlist immediately lifts a stale or mistaken block.
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=900)))
        db.session.commit()
        self.assertTrue(is_ip_blocked("203.0.113.7"))
        set_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK, "203.0.113.0/24")
        try:
            self.assertFalse(is_ip_blocked("203.0.113.7"))
            self.assertIsNone(get_ip_block("203.0.113.7"))
        finally:
            delete_privacyidea_config(SYSCONF.CONDITIONAL_ACCESS_NEVER_BLOCK)

    # --- BLOCK_IP action ------------------------------------------------------

    def test_block_ip_action_blocks_source_ip(self):
        ip = "203.0.113.7"
        _, stages = self._make_policy(
            name="blockip", counter_type=AuthEventType.PASSWORD_FAIL,
            target=LockoutTarget.SOURCE_IP,
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 900)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        block = self._block(ip)
        self.assertIsNotNone(block)
        self.assertIsNotNone(block.block_expires_at)
        self.assertGreater(block.block_expires_at, utc_now())
        self.assertTrue(is_ip_blocked(ip))
        # A BLOCK_IP-only stage writes no user lock.
        self.assertIsNone(self._state())

    def test_block_ip_action_without_source_ip_skipped(self):
        # No source IP on the request -> the source-IP policy cannot act; skipped, not raised.
        self._make_policy(name="blocknoip", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 900)]),))
        self._seed_ip_events("203.0.113.7", AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(self.user, None), AuthEventType.PASSWORD_FAIL)
        self.assertEqual(0, db.session.query(BlockList).count())

    def test_block_ip_action_invalid_duration_skipped(self):
        ip = "203.0.113.7"
        self._make_policy(name="blockbaddur", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.BLOCK_IP)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        self.assertIsNone(self._block(ip))

    def test_block_ip_does_not_downgrade_permanent_block(self):
        ip = "203.0.113.7"
        # Pre-existing permanent block (block_expires_at is None).
        db.session.add(BlockList(ip=ip, block_expires_at=None))
        db.session.commit()
        self._make_policy(name="blocktimed", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 900)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        # The permanent block must remain permanent (block_expires_at stays None).
        self.assertIsNone(self._block(ip).block_expires_at)
        self.assertTrue(is_ip_blocked(ip))

    def test_permanent_block_ip_action(self):
        ip = "203.0.113.7"
        # Mirror of PERMANENT_LOCK_USER: a permanent IP block (block_expires_at None).
        self._make_policy(name="permblock", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.PERMANENT_BLOCK_IP)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        block = self._block(ip)
        self.assertIsNotNone(block)
        self.assertIsNone(block.block_expires_at)
        self.assertTrue(is_ip_blocked(ip))

    def test_permanent_block_ip_ignores_action_value(self):
        ip = "203.0.113.7"
        # action_value is irrelevant for the permanent variant: even a "valid"
        # duration does not make it timed.
        self._make_policy(name="permblockdur", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(
                              StageDefinition(3, 1, [StageActionDefinition(LockoutAction.PERMANENT_BLOCK_IP, 900)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        self.assertIsNone(self._block(ip).block_expires_at)

    def test_permanent_block_ip_without_source_ip_skipped(self):
        # Like BLOCK_IP, a request with no source IP is logged and skipped, not raised.
        self._make_policy(name="permblocknoip", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.PERMANENT_BLOCK_IP)]),))
        self._seed_ip_events("203.0.113.7", AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(self.user, None), AuthEventType.PASSWORD_FAIL)
        self.assertEqual(0, db.session.query(BlockList).count())

    def test_expired_block_is_reapplied_when_the_threshold_is_still_met(self):
        # The IP counterpart of test_expired_lock_is_reapplied_when_the_threshold_is_still_met.
        ip = "203.0.113.7"
        self._make_policy(name="blockip", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 900)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        # The block runs out while the failures are still in the window.
        block = self._block(ip)
        block.block_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        self.assertFalse(is_ip_blocked(ip))
        # The threshold is still met (3 distinct users), so the stage blocks again.
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        self.assertTrue(is_ip_blocked(ip))

    def test_source_ip_policy_fires_for_unresolved_user(self):
        # A source-IP policy must still act when the current request's user is
        # unresolved (unknown username) - that is the spraying/enumeration case.
        # A user-target policy in the same run stays a no-op for the unknown user.
        ip = "203.0.113.60"
        self._make_policy(name="spray", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP, priority=1,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.BLOCK_IP,
                                                                               {"duration_seconds": 3600})]),))
        self._make_policy(name="userlock", counter_type=AuthEventType.PASSWORD_FAIL, priority=2,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 60)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        evaluate_lockout_policies(CAContext(User(), ip), AuthEventType.PASSWORD_FAIL)
        self.assertTrue(is_ip_blocked(ip), "source-IP policy did not fire for an unresolved user")
        self.assertEqual(0, db.session.query(UserLockoutState).count(),
                         "user policy wrote lock state for an unresolved user")

    # --- multiple policies on one request -------------------------------------

    def test_multiple_policies_fire_together(self):
        # Several enabled policies of different targets trip on one request: a
        # per-user timed lock (user target, threshold 5) plus a timed and a
        # permanent IP block (source_ip target, threshold 7). All apply, and the
        # permanent block wins over the timed one regardless of evaluation order
        # (cross-policy, same request).
        ip = "203.0.113.50"
        self._make_policy(name="lock", counter_type=AuthEventType.PIN_FAIL, priority=1,
                          stages=(StageDefinition(5, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 60)]),))
        self._make_policy(name="blocktimed", counter_type=AuthEventType.PIN_FAIL, priority=10,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(7, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 60)]),))
        self._make_policy(name="blockperm", counter_type=AuthEventType.PIN_FAIL, priority=4,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(7, 1, [StageActionDefinition(LockoutAction.PERMANENT_BLOCK_IP)]),))
        # 5 failures for the current user (trips the per-user lock) plus 7 distinct
        # users from the IP (trips both IP-block policies).
        self._seed_events(AuthEventType.PIN_FAIL, 5)
        self._seed_ip_events(ip, AuthEventType.PIN_FAIL, n_users=7)
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PIN_FAIL)
        # user locked with a timeout
        state = self._state()
        self.assertIsNotNone(state)
        self.assertIsNotNone(state.lock_expires_at)
        # IP blocked permanently: the timed block did not downgrade the permanent one
        block = self._block(ip)
        self.assertIsNotNone(block)
        self.assertIsNone(block.block_expires_at)
        self.assertTrue(is_ip_blocked(ip))

    # --- evaluate_access_decision (ALLOW / DENY) ------------------------------

    def test_access_decision_no_policies_is_continue(self):
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_deny_when_threshold_met(self):
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(self.user)).decision)
        # DENY is stateless: it persists no lockout state.
        self.assertIsNone(self._state())

    def test_access_decision_below_threshold_is_continue(self):
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 2)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_deny_default_refires_above_threshold(self):
        # DENY defaults to re-trigger, so the decision stands while the count is at
        # or above the threshold, not only at the exact count.
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_fire_once_deny_only_at_exact_threshold(self):
        # A decision action switched to fire-once decides only at the exact count:
        # once the count climbs past the threshold it no longer denies.
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(
                              LockoutAction.DENY, retrigger_above_threshold=False)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(self.user)).decision)
        self._seed_events(AuthEventType.PASSWORD_FAIL, 1)  # count 4 > 3
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_denies_on_combined_count(self):
        # The pre-auth decision also counts all tracked types together: 2 + 2 = 4
        # crosses the threshold of 3, so the request is denied.
        self._make_policy(name="deny",
                          counter_type=[AuthEventType.PASSWORD_FAIL, AuthEventType.MFA_FAIL],
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 2)
        self._seed_events(AuthEventType.MFA_FAIL, 2)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_does_not_reset_on_success(self):
        # Unlike the lock, the DENY decision counts every failure in the raw
        # window: a successful login in between does NOT clear it (it self-heals
        # only as the failures age out). Pins the "lock only" reset scope.
        now = utc_now()
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3, timestamp=now - timedelta(seconds=300))
        self._seed_events(AuthEventType.LOGIN_SUCCESS, 1, timestamp=now - timedelta(seconds=200))
        # The three pre-login failures still trigger DENY despite the login.
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(self.user), now=now).decision)

    def test_access_decision_allow_threshold_zero_is_default_allow(self):
        # A stage with threshold 0 always matches -> default allow, no events needed.
        self._make_policy(name="allow", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(0, 1, [StageActionDefinition(LockoutAction.ALLOW)]),))
        self.assertEqual(AccessDecision.ALLOW, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_higher_priority_allow_overrides_deny(self):
        # An ALLOW policy at higher precedence (lower priority number) wins over a
        # DENY with a higher number.
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL, priority=10,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._make_policy(name="allow", counter_type=AuthEventType.PASSWORD_FAIL, priority=1,
                          stages=(StageDefinition(0, 1, [StageActionDefinition(LockoutAction.ALLOW)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.ALLOW, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_higher_priority_deny_overrides_allow(self):
        self._make_policy(name="allow", counter_type=AuthEventType.PASSWORD_FAIL, priority=10,
                          stages=(StageDefinition(0, 1, [StageActionDefinition(LockoutAction.ALLOW)]),))
        self._make_policy(name="deny", counter_type=AuthEventType.PASSWORD_FAIL, priority=1,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_ignores_lockout_only_stage(self):
        # A LOCK_USER stage is a post-response side effect, not a pre-auth decision.
        self._make_policy(name="lock", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_dry_run_not_enforced(self):
        self._make_policy(name="drydeny", counter_type=AuthEventType.PASSWORD_FAIL, dry_run=True,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_disabled_policy_skipped(self):
        self._make_policy(name="offdeny", counter_type=AuthEventType.PASSWORD_FAIL, enabled=False,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_unresolved_user_is_continue(self):
        self._make_policy(name="allow", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(0, 1, [StageActionDefinition(LockoutAction.ALLOW)]),))
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(User())).decision)

    def test_access_decision_both_actions_on_stage_denies(self):
        # A stage misconfigured with both ALLOW and DENY fails closed (DENY wins).
        self._make_policy(name="both", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.ALLOW),
                                                         StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(self.user)).decision)

    def test_access_decision_skips_unknown_action_type(self):
        # An unrecognized action type in a decision stage is ignored (not raised),
        # so the stage contributes no decision. Uses direct ORM since the CRUD
        # layer would reject the invalid type.
        self._make_policy(name="unknown", counter_type=AuthEventType.PASSWORD_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition("TELEPORT_USER")]),))
        self._seed_events(AuthEventType.PASSWORD_FAIL, 3)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user)).decision)

    # --- evaluate_access_decision, source-IP target ---------------------------

    def test_access_decision_source_ip_deny(self):
        # An IP that sprayed >= threshold distinct users is denied pre-auth.
        ip = "203.0.113.30"
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(self.user, ip)).decision)

    def test_access_decision_source_ip_deny_for_unresolved_user(self):
        # IP decisions fire regardless of whether the current user resolved -
        # that is the point of an IP-scoped DENY (spraying/enumeration).
        ip = "203.0.113.31"
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=3)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(User(), ip)).decision)

    def test_access_decision_source_ip_below_threshold_continues(self):
        ip = "203.0.113.32"
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=2)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user, ip)).decision)

    def test_access_decision_source_ip_never_block_is_exempt(self):
        # A never-block IP (loopback) is never denied by an IP policy, mirroring BLOCK_IP.
        ip = "127.0.0.1"
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user, ip)).decision)

    def test_access_decision_source_ip_without_ip_continues(self):
        self._make_policy(name="ipdeny", counter_type=AuthEventType.PASSWORD_FAIL,
                          target=LockoutTarget.SOURCE_IP,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_ip_events("203.0.113.33", AuthEventType.PASSWORD_FAIL, n_users=5)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(CAContext(self.user, None)).decision)

    # --- _lock_duration_seconds -----------------------------------------------

    def test_lock_duration_parsing(self):
        self.assertEqual(600, _lock_duration_seconds(600))
        self.assertEqual(600, _lock_duration_seconds("600"))
        self.assertEqual(300, _lock_duration_seconds({"duration_seconds": 300}))
        self.assertEqual(120, _lock_duration_seconds({"duration": 120}))
        for invalid in (None, 0, -5, True, False, "abc", {}, {"foo": 1}):
            self.assertIsNone(_lock_duration_seconds(invalid), invalid)

    # --- EMAIL_ADMIN / EMAIL_USER actions -------------------------------------

    @smtpmock.activate
    def test_email_user_action_sends_to_user(self):
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailuser", counter_type=AuthEventType.MFA_FAIL,
                stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.EMAIL_USER,
                                                                     {"smtp_identifier": "lockoutmail",
                                                                      "subject": "Locked: {username}",
                                                                      "body": "{username}@{realm} locked after {count} failures."})]),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            evaluate_lockout_policies(CAContext(self.user, "10.0.0.9"), AuthEventType.MFA_FAIL)

            user_email = self.user.info.get("email")
            self.assertTrue(user_email, "test user must resolve to an email address")
            self.assertEqual([user_email], smtpmock.get_sent_recipient())
            parsed = message_from_string(smtpmock.get_sent_message())
            # {tags} are substituted in both subject and body.
            self.assertEqual("Locked: cornelius", parsed["Subject"])
            body = parsed.get_payload(decode=True).decode("utf-8")
            self.assertEqual(f"cornelius@{self.user.realm} locked after 3 failures.", body)
            # A pure notification action writes no lockout state.
            self.assertIsNone(self._state())
        finally:
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_email_admin_action_sends_to_internal_admins(self):
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        db.session.add(Admin(username="ca_adm1", email="adm1@example.com"))
        db.session.add(Admin(username="ca_adm2", email="adm2@example.com"))
        db.session.add(Admin(username="ca_noemail", email=None))
        db.session.commit()
        try:
            self._make_policy(
                name="mailadmin", counter_type=AuthEventType.MFA_FAIL,
                stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.EMAIL_ADMIN,
                                                                     {"smtp_identifier": "lockoutmail",
                                                                      "recipient_group": "internal_admins",
                                                                      "subject": "{username} locked",
                                                                      "body": "{count} failures in realm {realm}."})]),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
            # Both admins with an email are notified in one message; the email-less admin is skipped.
            recipients = set(smtpmock.get_sent_recipient())
            self.assertTrue({"adm1@example.com", "adm2@example.com"}.issubset(recipients), recipients)
        finally:
            Admin.query.filter(
                Admin.username.in_(["ca_adm1", "ca_adm2", "ca_noemail"])).delete(synchronize_session=False)
            db.session.commit()
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_email_admin_alerts_on_userless_spraying_traffic(self):
        # A source-IP policy fires on traffic that resolved no user, which is exactly the traffic an
        # EMAIL_ADMIN alert exists to report. The user-derived tags render empty, but the alert is sent.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        ip = "10.0.0.32"
        try:
            email_config = {"smtp_identifier": "lockoutmail",
                            "recipient_group": "soc@example.com",
                            "subject": "spraying from {client_ip}",
                            "body": "{count} accounts, user {username}."}
            self._make_policy(
                name="spray alert", counter_type=AuthEventType.MFA_FAIL,
                target=LockoutTarget.SOURCE_IP, count_mode=CountMode.DISTINCT_USERS,
                stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.EMAIL_ADMIN,
                                                                     email_config)]),))
            self._seed_ip_accounts(ip, (self.realm1, self.realm1, self.realm1))

            evaluate_lockout_policies(CAContext(None, source_ip=ip), AuthEventType.MFA_FAIL)

            self.assertEqual(["soc@example.com"], smtpmock.get_sent_recipient())
            parsed = message_from_string(smtpmock.get_sent_message())
            self.assertEqual(f"spraying from {ip}", parsed["Subject"])
            # The user tags resolve to empty rather than dropping the alert.
            self.assertEqual("3 accounts, user .",
                             parsed.get_payload(decode=True).decode("utf-8"))
        finally:
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_email_admin_explicit_recipient_list(self):
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailadmin2", counter_type=AuthEventType.MFA_FAIL,
                stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.EMAIL_ADMIN,
                                                                     {"smtp_identifier": "lockoutmail",
                                                                      "recipient_group": "soc@example.com, ciso@example.com",
                                                                      "subject": "alert", "body": "alert"})]),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
            self.assertEqual(["soc@example.com", "ciso@example.com"], smtpmock.get_sent_recipient())
        finally:
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_email_action_missing_config_is_skipped(self):
        # No subject/body in action_value -> the action is logged and skipped, never sent or raised.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailbad", counter_type=AuthEventType.MFA_FAIL,
                stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.EMAIL_USER,
                                                                     {"smtp_identifier": "lockoutmail"})]),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
            self.assertIsNone(smtpmock.get_sent_message())
        finally:
            delete_smtpserver("lockoutmail")

    def test_email_failure_does_not_break_other_actions(self):
        # A stage that both locks the user and emails them: the email points at an
        # unknown SMTP server, so sending raises. Per-action guarding must keep the
        # LOCK_USER write intact.
        _, stages = self._make_policy(
            name="lockandmail", counter_type=AuthEventType.MFA_FAIL,
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)]),))
        db.session.add(LockoutStageAction(
            stage_id=stages[0].id, action_type=str(LockoutAction.EMAIL_USER),
            action_value={"smtp_identifier": "does-not-exist", "subject": "x", "body": "x"}))
        db.session.commit()
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        # Must not raise even though the mail action fails.
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        state = self._state()
        self.assertIsNotNone(state)

    @smtpmock.activate
    def test_email_action_returns_login_notice(self):
        # A sent EMAIL_* action returns a user-facing notice for the login screen.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailnotice", counter_type=AuthEventType.MFA_FAIL,
                stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.EMAIL_ADMIN,
                                                                     {"smtp_identifier": "lockoutmail",
                                                                      "recipient_group": "soc@example.com",
                                                                      "subject": "s", "body": "b"})]),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            notices = evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).notices
            self.assertEqual(["Your administrator has been notified by email."], notices)
        finally:
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_email_action_custom_login_notice_with_tags(self):
        # An admin-supplied login_notice template overrides the default and is {tag}-rendered.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            self._make_policy(
                name="mailnotice2", counter_type=AuthEventType.MFA_FAIL,
                stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.EMAIL_USER,
                                                                     {"smtp_identifier": "lockoutmail", "subject": "s",
                                                                      "body": "b",
                                                                      "login_notice": "We emailed {username} about {count} failures."})]),))
            self._seed_events(AuthEventType.MFA_FAIL, 3)
            self.assertEqual(["We emailed cornelius about 3 failures."],
                             evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).notices)
        finally:
            delete_smtpserver("lockoutmail")

    def test_no_login_notice_for_non_email_action(self):
        # A LOCK_USER-only stage locks the user but produces no login-screen notice.
        self._make_policy(name="lockonly", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        self.assertEqual([], evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).notices)
        self.assertTrue(is_user_locked(self.user))

    # --- _safe_format / _resolve_admin_recipients -----------------------------

    def test_safe_format_leaves_unknown_tags_and_never_raises(self):
        self.assertEqual("hi cornelius", _safe_format("hi {user}", {"user": "cornelius"}))
        # Unknown placeholder is left verbatim instead of raising KeyError.
        self.assertEqual("{missing} kept", _safe_format("{missing} kept", {"user": "x"}))
        # A malformed template is returned unchanged rather than raising.
        self.assertEqual("oops {", _safe_format("oops {", {}))

    def test_resolve_admin_recipients_explicit_and_unknown(self):
        self.assertEqual(["a@x.com", "b@y.com"],
                         _resolve_admin_recipients("a@x.com, b@y.com"))
        # An unknown, non-email group resolves to no recipients.
        self.assertEqual([], _resolve_admin_recipients("marketing"))

    # --- policy conditions (applicability) ------------------------------------

    @staticmethod
    def _condition(condition_type: ConditionType | str, operator: ConditionOperator | str,
                   value: list[str] | None) -> LockoutPolicyCondition:
        return LockoutPolicyCondition(condition_type=str(condition_type), operator=str(operator), value=value)

    def test_policy_without_conditions_applies_to_everyone(self):
        # no condition rows means no restriction.
        policy, _ = self._make_policy(name="unconditioned", counter_type=AuthEventType.MFA_FAIL)
        self.assertTrue(policy_matches_context(policy, CAContext(self.user)))

    def test_realm_condition_matches_only_its_realms(self):
        policy, _ = self._make_policy(
            name="realm scoped", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.IN, [self.realm1])])
        self.assertTrue(policy_matches_context(policy, CAContext(self.user)))
        self.assertFalse(policy_matches_context(policy, CAContext(User("cornelius", self.realm2))))

    def test_realm_condition_negated(self):
        policy, _ = self._make_policy(
            name="realm excluded", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.NOT_IN, [self.realm1])])
        self.assertFalse(policy_matches_context(policy, CAContext(self.user)))

    def test_role_condition_matches_the_context_role(self):
        policy, _ = self._make_policy(
            name="admins only", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_ROLE, ConditionOperator.IN,
                                        [str(AuthLogUserRole.ADMIN_EXTERNAL)])])
        self.assertTrue(policy_matches_context(
            policy, CAContext(self.user, user_role=str(AuthLogUserRole.ADMIN_EXTERNAL))))
        self.assertFalse(policy_matches_context(
            policy, CAContext(self.user, user_role=str(AuthLogUserRole.USER))))

    def test_conditions_are_anded(self):
        policy, _ = self._make_policy(
            name="realm and role", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.IN, [self.realm1]),
                        self._condition(ConditionType.USER_ROLE, ConditionOperator.IN, [str(AuthLogUserRole.USER)])])
        self.assertTrue(policy_matches_context(
            policy, CAContext(self.user, user_role=str(AuthLogUserRole.USER))))
        # Realm holds but role does not: the AND fails.
        self.assertFalse(policy_matches_context(
            policy, CAContext(self.user, user_role=str(AuthLogUserRole.ADMIN_INTERNAL))))

    def test_missing_value_does_not_match_a_positive_condition(self):
        # An unresolved user has no realm, and a context built outside /auth has no
        # role. A missing value is in no set, so an IN condition does not match.
        realm_policy, _ = self._make_policy(
            name="needs realm", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.IN, [self.realm1])])
        self.assertFalse(policy_matches_context(realm_policy, CAContext(User())))
        role_policy, _ = self._make_policy(
            name="needs role", counter_type=AuthEventType.MFA_FAIL, priority=2,
            conditions=[self._condition(ConditionType.USER_ROLE, ConditionOperator.IN,
                                        [str(AuthLogUserRole.USER)])])
        self.assertFalse(policy_matches_context(role_policy, CAContext(self.user)))

    def test_missing_value_matches_when_negated(self):
        # A missing value belongs to no set, so NOT_IN matches it. This is what
        # keeps an exemption honest: an anti-enumeration policy carrying
        # "realm NOT_IN [other]" must still apply to the probes of non-existent
        # usernames it exists to stop, which resolve to no realm at all.
        policy, _ = self._make_policy(
            name="needs realm negated", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.NOT_IN, ["other"])])
        self.assertTrue(policy_matches_context(policy, CAContext(User())))

    def test_unknown_condition_type_or_operator_does_not_match(self):
        # Only reachable via a version downgrade (the CRUD rejects both at write
        # time). It must not raise, and must not silently widen the policy.
        context = CAContext(self.user)
        self.assertFalse(condition_matches(
            self._condition("NO_SUCH_TYPE", ConditionOperator.IN, ["x"]), context, "p"))
        self.assertFalse(condition_matches(
            self._condition(ConditionType.USER_REALM, "NO_SUCH_OP", ["x"]), context, "p"))

    # Only a hand-edited row reaches the evaluators with any of these, since the CRUD writes nothing but a
    # non-empty list of strings. Each has to be rejected outright rather than compared, and NOT_IN is what
    # makes that load-bearing: a value no row can match answers False for IN on its own, but True for
    # NOT_IN, so a corrupted exemption would apply to *everything* instead of to nothing.
    MALFORMED_CONDITION_VALUES = [("not a list", "realm1"), ("empty list", []), ("non-strings", [1, 2])]

    def test_malformed_condition_value_does_not_match(self):
        for label, value in self.MALFORMED_CONDITION_VALUES:
            for operator in (ConditionOperator.IN, ConditionOperator.NOT_IN):
                with self.subTest(value=label, operator=operator):
                    self.assertFalse(condition_matches(
                        self._condition(ConditionType.USER_REALM, operator, value),
                        CAContext(self.user), "p"))

    def test_malformed_condition_value_does_not_match_a_row(self):
        # The row evaluator answers a malformed value the same way as the gate, so a corrupted condition
        # cannot gate one way and scope another.
        row = AuthenticationLog(event_type=str(AuthEventType.MFA_FAIL), realm=self.realm1,
                                attempt_id="att-malformed", timestamp=utc_now())
        priority = 0
        for label, value in self.MALFORMED_CONDITION_VALUES:
            for operator in (ConditionOperator.IN, ConditionOperator.NOT_IN):
                priority += 1
                with self.subTest(value=label, operator=operator):
                    policy, _ = self._make_policy(
                        name=f"malformed {label} {operator}", counter_type=AuthEventType.MFA_FAIL,
                        priority=priority,
                        conditions=[self._condition(ConditionType.USER_REALM, operator, value)])
                    self.assertFalse(conditions_match_row(policy, row))

    def test_conditions_gate_the_post_response_engine(self):
        # A policy excluded by its realm condition neither counts nor locks.
        self._make_policy(
            name="other realm only", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.IN, [self.realm2])],
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        self.assertEqual([], evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).notices)
        self.assertFalse(is_user_locked(self.user))

    def _spray_policy(self, *, threshold: int = 3,
                      operator: ConditionOperator = ConditionOperator.IN,
                      values: list[str] | None = None,
                      condition_type: ConditionType | str = ConditionType.USER_REALM
                      ) -> tuple[LockoutPolicy, list[LockoutPolicyStage]]:
        """
        A source-IP spraying policy scoped by one condition, blocking the IP once the scoped count
        reaches *threshold* distinct accounts.

        :param threshold: distinct accounts at which the BLOCK_IP stage fires
        :param operator: the :class:`ConditionOperator` the condition compares with
        :param values: the condition's values; defaults to ``[self.realm1]``
        :param condition_type: the :class:`ConditionType` the condition reads
        :return: the ``(policy, stages)`` tuple :meth:`_make_policy` returns
        """
        return self._make_policy(
            name="scoped spray", counter_type=AuthEventType.MFA_FAIL,
            target=LockoutTarget.SOURCE_IP, count_mode=CountMode.DISTINCT_USERS,
            conditions=[self._condition(condition_type, operator,
                                        values if values is not None else [self.realm1])],
            stages=(StageDefinition(threshold, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 600)]),))

    def _seed_ip_accounts(self, ip: str, realms: Sequence[str | None], role: str | None = None) -> None:
        """
        Insert one MFA_FAIL row per entry of *realms*, each a distinct account (``sprayed0``..) from
        *ip*, so a DISTINCT_USERS count over that IP equals ``len(realms)`` before any scoping.

        :param ip: the source IP all rows are written for
        :param realms: one realm per row; ``None`` writes a NULL realm, which is what a login naming
            no realm produces and what the missing-value rule is exercised against
        :param role: the ``user_role`` to stamp on every row, or ``None`` to leave it unset
        :return: None; the rows are committed
        """
        for index, realm in enumerate(realms):
            db.session.add(AuthenticationLog(event_type=str(AuthEventType.MFA_FAIL), source_ip=ip,
                                             username=f"sprayed{index}", realm=realm, user_role=role,
                                             timestamp=utc_now()))
        db.session.commit()

    def test_conditions_scope_a_source_ip_count_to_the_rows_they_describe(self):
        # Having passed the gate, a source-IP policy counts only the history its conditions describe.
        # Its subject is the IP, whose rows span many users, so this is what makes it count what the
        # admin asked for: three realm1 accounts reach the threshold, the two realm2 ones are ignored.
        ip = "10.0.0.9"
        self._spray_policy(threshold=3)
        self._seed_ip_accounts(ip, (self.realm1, self.realm1, self.realm1, self.realm2, self.realm2))

        evaluate_lockout_policies(CAContext(User("cornelius", self.realm1), source_ip=ip),
                                  AuthEventType.MFA_FAIL)
        self.assertTrue(is_ip_blocked(ip))

    def test_conditions_exclude_rows_outside_them_from_a_source_ip_count(self):
        # The complement: five realm2 accounts plus two realm1 ones is seven rows, which would trip a
        # threshold of 3 unscoped. Scoped to realm1 the count is 2 and nothing fires.
        ip = "10.0.0.10"
        self._spray_policy(threshold=3)
        self._seed_ip_accounts(ip, (self.realm1, self.realm1,
                                    self.realm2, self.realm2, self.realm2, self.realm2, self.realm2))

        evaluate_lockout_policies(CAContext(User("cornelius", self.realm1), source_ip=ip),
                                  AuthEventType.MFA_FAIL)
        self.assertFalse(is_ip_blocked(ip))

    def test_a_source_ip_policy_is_still_gated_by_its_conditions(self):
        # Scoping is *in addition to* the gate, not instead of it: a request the conditions exclude is
        # not judged by the policy at all, whatever the IP's history looks like.
        ip = "10.0.0.14"
        self._spray_policy(threshold=3)
        self._seed_ip_accounts(ip, (self.realm1, self.realm1, self.realm1))

        evaluate_lockout_policies(CAContext(User("cornelius", self.realm2), source_ip=ip),
                                  AuthEventType.MFA_FAIL)
        self.assertFalse(is_ip_blocked(ip))

    def test_positive_condition_excludes_rows_with_no_value_from_the_count(self):
        # The IN half of the missing-value rule, on the counting side: a row whose realm is NULL is in
        # no set, so an IN-scoped count skips it - matching the gate, which does not apply an IN policy
        # to a request carrying no realm. Three NULL-realm accounts therefore never reach a threshold
        # of 2, however many of them there are.
        ip = "10.0.0.15"
        self._spray_policy(threshold=2, operator=ConditionOperator.IN, values=[self.realm1])
        self._seed_ip_accounts(ip, (None, None, None))

        evaluate_lockout_policies(CAContext(User("cornelius", self.realm1), source_ip=ip),
                                  AuthEventType.MFA_FAIL)
        self.assertFalse(is_ip_blocked(ip))

    def test_negated_condition_gates_and_counts_rows_with_no_value_alike(self):
        # The gate and the filter cannot disagree, because matches_missing and the SQL are aligned on a
        # missing value: NOT_IN admits a request carrying no realm, and its filter admits the NULL-realm
        # rows such requests write. Plain "realm NOT IN (...)" is false for NULL in SQL, which would
        # have excluded exactly the enumeration traffic the exemption is written to catch.
        ip = "10.0.0.11"
        self._spray_policy(threshold=3, operator=ConditionOperator.NOT_IN, values=[self.realm2])
        self._seed_ip_accounts(ip, (None, None, None))

        evaluate_lockout_policies(CAContext(User(), source_ip=ip), AuthEventType.MFA_FAIL)
        self.assertTrue(is_ip_blocked(ip))

    def test_role_condition_scopes_a_source_ip_count(self):
        # Scoping is registry-driven, so the role condition narrows through its own log column.
        ip = "10.0.0.12"
        self._spray_policy(threshold=2, condition_type=ConditionType.USER_ROLE,
                           values=[str(AuthLogUserRole.USER)])
        context = CAContext(User("cornelius", self.realm1), source_ip=ip,
                            user_role=str(AuthLogUserRole.USER))
        self._seed_ip_accounts(ip, (self.realm1, self.realm1), role=str(AuthLogUserRole.ADMIN_EXTERNAL))
        evaluate_lockout_policies(context, AuthEventType.MFA_FAIL)
        # Both rows are admin-external, so a user-role scope counts none of them.
        self.assertFalse(is_ip_blocked(ip))

        self._seed_ip_accounts(ip, (self.realm1, self.realm1), role=str(AuthLogUserRole.USER))
        evaluate_lockout_policies(context, AuthEventType.MFA_FAIL)
        self.assertTrue(is_ip_blocked(ip))

    def test_scoping_leaves_a_user_target_outcome_unchanged(self):
        # For a user target the filters are redundant: the subject is one (resolver, uid, realm)
        # identity, so the realm is pinned and with it the role - an admin realm holds only admins, and
        # an internal admin has no realm, so no identity is ever both. They are still applied, and the
        # point of this test is that they must not exclude the subject's *own* rows: a policy conditioned
        # on the realm and role it is already scoped to has to keep firing exactly as an unconditioned
        # one would.
        self._make_policy(
            name="scoped to its own subject", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.IN, [self.realm1]),
                        self._condition(ConditionType.USER_ROLE, ConditionOperator.IN,
                                        [str(AuthLogUserRole.USER)])],
            stages=(StageDefinition(2, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)]),))
        for _ in range(2):
            db.session.add(AuthenticationLog(event_type=str(AuthEventType.MFA_FAIL),
                                             resolver=self.user.resolver, uid=self.user.uid,
                                             realm=self.user.realm, user_role=str(AuthLogUserRole.USER),
                                             timestamp=utc_now()))
        db.session.commit()

        evaluate_lockout_policies(CAContext(self.user, user_role=str(AuthLogUserRole.USER)),
                                  AuthEventType.MFA_FAIL)
        self.assertTrue(is_user_locked(self.user))

    def test_a_user_target_policy_still_gates_on_its_conditions(self):
        self._make_policy(
            name="other realm only", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.IN, [self.realm2])],
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.LOCK_USER, 600)]),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        self.assertEqual([], evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL).notices)
        self.assertFalse(is_user_locked(self.user))

    def test_a_condition_that_cannot_be_a_predicate_leaves_the_count_unscoped(self):
        # A condition type the log does not record cannot narrow a query, so such a policy counts
        # everything the subject did and relies on the gate alone - the behaviour it had before scoping
        # existed. All or nothing: honouring only the scopable conditions of a mixed policy would count
        # rows the admin excluded. Simulated with a spec carrying no log_column.
        ip = "10.0.0.13"
        unscopable = ConditionTypeSpec(name="CLIENT_LABEL", label="Client label",
                                       operators=frozenset({ConditionOperator.IN}),
                                       resolve=lambda context: "kiosk", choices=None)
        self.assertIsNone(unscopable.log_column)
        with mock.patch.dict(CONDITION_TYPES, {"CLIENT_LABEL": unscopable}):
            policy = self._make_policy(
                name="unscopable", counter_type=AuthEventType.MFA_FAIL,
                target=LockoutTarget.SOURCE_IP, count_mode=CountMode.DISTINCT_USERS,
                conditions=[self._condition("CLIENT_LABEL", ConditionOperator.IN, ["kiosk"])],
                stages=(StageDefinition(2, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 600)]),))[0]
            self.assertFalse(policy_conditions_are_scopable(policy))
            # Two accounts in different realms: unscoped they both count and the threshold is reached.
            self._seed_ip_accounts(ip, (self.realm1, self.realm2))
            evaluate_lockout_policies(CAContext(User("cornelius", self.realm1), source_ip=ip),
                                      AuthEventType.MFA_FAIL)
            self.assertTrue(is_ip_blocked(ip))

    def test_conditions_gate_the_pre_auth_decision(self):
        # A DENY at threshold 0 always fires for a matching context, and contributes
        # no decision at all for one its realm condition excludes.
        self._make_policy(
            name="deny realm1", counter_type=AuthEventType.MFA_FAIL,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.IN, [self.realm1])],
            stages=(StageDefinition(0, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(CAContext(self.user)).decision)
        self.assertEqual(AccessDecision.CONTINUE,
                         evaluate_access_decision(CAContext(User("cornelius", self.realm2))).decision)

    # --- PER_ATTEMPT scoping: conditions apply to the reduced outcome, not to the rows ------------

    def _seed_ip_attempt_rows(self, source_ip: str, attempt_id: str,
                              rows: Sequence[tuple[AuthEventType, str | None]]) -> None:
        """
        Insert one row per ``(event_type, realm)`` pair sharing *attempt_id*, in order, so row ids
        increase with insertion order. Per-row realms are what make an attempt straddle a condition:
        the rows of one attempt need not all carry the same value (see conditions_match_row).
        """
        for event_type, realm in rows:
            db.session.add(AuthenticationLog(event_type=str(event_type), source_ip=source_ip,
                                             attempt_id=attempt_id, realm=realm, timestamp=utc_now()))
        db.session.commit()

    def _attempt_policy(self, *, operator: ConditionOperator, values: list[str],
                        counter_type=AuthEventType.MFA_FAIL):
        """A source-IP PER_ATTEMPT policy scoped by one realm condition, for counting via _policy_count_ip."""
        policy, _stages = self._make_policy(
            name="attempt scoped", counter_type=counter_type,
            target=LockoutTarget.SOURCE_IP, count_mode=CountMode.PER_ATTEMPT,
            conditions=[self._condition(ConditionType.USER_REALM, operator, values)],
            stages=(StageDefinition(1, 1, [StageActionDefinition(LockoutAction.BLOCK_IP, 600)]),))
        return policy

    def test_a_condition_that_would_drop_a_success_does_not_turn_the_attempt_into_a_failure(self):
        # The reduction needs the whole attempt: a LOGIN_SUCCESS supersedes the attempt's failures. A
        # condition applied to the *rows* could admit the failure and drop the success - NOT_IN matches a
        # missing value, so a NULL-realm failure passes while the realm1 success does not - and the attempt
        # would count as a failure. Applying it to the reduced outcome instead leaves the success in charge.
        ip = "10.0.0.40"
        self._seed_ip_attempt_rows(ip, "att-mixed", [(AuthEventType.MFA_FAIL, None),
                                                     (AuthEventType.LOGIN_SUCCESS, self.realm1)])
        policy = self._attempt_policy(operator=ConditionOperator.NOT_IN, values=[self.realm1])

        self.assertEqual(0, _policy_count_ip(policy, ip, utc_now()))

    def test_conditions_scope_a_per_attempt_count_by_the_outcome_row(self):
        # Having kept the reduction whole, the conditions still scope: of two failed attempts the realm1
        # one counts and the realm2 one does not.
        ip = "10.0.0.41"
        self._seed_ip_attempt_rows(ip, "att-r1", [(AuthEventType.MFA_FAIL, self.realm1)])
        self._seed_ip_attempt_rows(ip, "att-r2", [(AuthEventType.MFA_FAIL, self.realm2)])
        policy = self._attempt_policy(operator=ConditionOperator.IN, values=[self.realm1])

        self.assertEqual(1, _policy_count_ip(policy, ip, utc_now()))

    def test_per_attempt_scoping_reads_the_success_row_not_a_later_stray(self):
        # A policy tracking LOGIN_SUCCESS (a rate limit tracking every type) counts succeeded attempts, so
        # which row the condition is read from becomes visible: the attempt is classified by its success,
        # and must be filtered by that same row rather than by the stray replay that follows it.
        ip = "10.0.0.42"
        self._seed_ip_attempt_rows(ip, "att-stray", [(AuthEventType.LOGIN_SUCCESS, self.realm1),
                                                     (AuthEventType.CHALLENGE_ANSWERED_FAIL, self.realm2)])
        policy = self._attempt_policy(operator=ConditionOperator.IN, values=[self.realm1],
                                      counter_type=AuthEventType.LOGIN_SUCCESS)

        self.assertEqual(1, _policy_count_ip(policy, ip, utc_now()))

    def test_an_unscopable_condition_leaves_a_per_attempt_count_unscoped(self):
        # Mirrors the PER_REQUEST rule: a condition that cannot be expressed against the log scopes
        # nothing, so the count stays wide rather than silently dropping every attempt.
        ip = "10.0.0.43"
        self._seed_ip_attempt_rows(ip, "att-a", [(AuthEventType.MFA_FAIL, self.realm1)])
        self._seed_ip_attempt_rows(ip, "att-b", [(AuthEventType.MFA_FAIL, self.realm2)])
        policy = self._attempt_policy(operator=ConditionOperator.IN, values=[self.realm1])
        with mock.patch.dict(CONDITION_TYPES,
                             {ConditionType.USER_REALM: ConditionTypeSpec(
                                 name=ConditionType.USER_REALM,
                                 label=CONDITION_TYPES[ConditionType.USER_REALM].label,
                                 operators=CONDITION_TYPES[ConditionType.USER_REALM].operators,
                                 resolve=CONDITION_TYPES[ConditionType.USER_REALM].resolve,
                                 choices=CONDITION_TYPES[ConditionType.USER_REALM].choices,
                                 log_column=None)}):
            self.assertFalse(policy_conditions_are_scopable(policy))
            self.assertEqual(2, _policy_count_ip(policy, ip, utc_now()))

    def test_conditions_scope_the_pre_auth_decision_count(self):
        # The pre-auth counterpart of test_conditions_exclude_rows_outside_them_from_a_source_ip_count:
        # gating and scoping are separate, so a policy the conditions admit must still count only the
        # rows they describe. Two realm1 accounts plus five realm2 ones is seven distinct accounts,
        # which would deny on a threshold of 3 unscoped; scoped to realm1 the count is 2.
        ip = "10.0.0.30"
        self._make_policy(
            name="scoped spray deny", counter_type=AuthEventType.MFA_FAIL,
            target=LockoutTarget.SOURCE_IP, count_mode=CountMode.DISTINCT_USERS,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.IN, [self.realm1])],
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_ip_accounts(ip, (self.realm1, self.realm1,
                                    self.realm2, self.realm2, self.realm2, self.realm2, self.realm2))

        self.assertEqual(AccessDecision.CONTINUE,
                         evaluate_access_decision(CAContext(User("cornelius", self.realm1), source_ip=ip)).decision)

    def test_pre_auth_decision_denies_once_the_scoped_count_reaches_the_threshold(self):
        # The complement, so the test above cannot pass merely by never denying: three realm1 accounts
        # do reach the same threshold, and the two realm2 ones neither add to nor block that.
        ip = "10.0.0.31"
        self._make_policy(
            name="scoped spray deny", counter_type=AuthEventType.MFA_FAIL,
            target=LockoutTarget.SOURCE_IP, count_mode=CountMode.DISTINCT_USERS,
            conditions=[self._condition(ConditionType.USER_REALM, ConditionOperator.IN, [self.realm1])],
            stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)]),))
        self._seed_ip_accounts(ip, (self.realm1, self.realm1, self.realm1, self.realm2, self.realm2))

        self.assertEqual(AccessDecision.DENY,
                         evaluate_access_decision(CAContext(User("cornelius", self.realm1), source_ip=ip)).decision)

    # --- the error message a restriction carries ------------------------------

    def test_lock_stores_the_triggering_stage_error_message(self):
        # The row is the whole truth about the lock: the wording is copied in when it is applied, so it
        # survives the policy being edited or deleted and costs no join on the authentication path.
        message = "Locked. Try again in about {duration}."
        lock = [StageActionDefinition(LockoutAction.LOCK_USER, {"duration_seconds": 600})]
        self._make_policy(name="msg", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(3, 1, lock, error_message=message),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertEqual(message, self._state().error_message)
        self.assertEqual(message, get_user_lockout(self.user).error_message)

    def test_lock_without_a_stage_message_stores_none(self):
        # The default is silence, so nothing is carried and the rejection stays generic.
        self._make_policy(name="silent", counter_type=AuthEventType.MFA_FAIL)
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertIsNone(self._state().error_message)
        self.assertIsNone(get_user_lockout(self.user).error_message)

    def test_relock_by_a_later_stage_replaces_the_stored_message(self):
        # An escalating policy moves the user from one stage to a more severe one; the message must
        # describe the restriction now in force, not the one it replaced.
        short = [StageActionDefinition(LockoutAction.LOCK_USER, {"duration_seconds": 600})]
        long = [StageActionDefinition(LockoutAction.LOCK_USER, {"duration_seconds": 3600})]
        self._make_policy(name="escalating", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(3, 1, short, error_message="First."),
                                  StageDefinition(5, 2, long, error_message="Second."),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertEqual("First.", self._state().error_message)

        self._seed_events(AuthEventType.MFA_FAIL, 2)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertEqual("Second.", self._state().error_message)

    def test_declined_downgrade_keeps_the_permanent_lock_message(self):
        # A permanent lock is never downgraded to a timed one, so the timed stage's wording must not
        # overwrite the permanent one's either - the message would then describe a lock not in force.
        self._make_policy(name="permanent", counter_type=AuthEventType.MFA_FAIL, priority=1,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.PERMANENT_LOCK_USER)],
                                                  error_message="Permanent."),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertEqual("Permanent.", self._state().error_message)

        timed = [StageActionDefinition(LockoutAction.LOCK_USER, {"duration_seconds": 600})]
        self._make_policy(name="timed", counter_type=AuthEventType.MFA_FAIL, priority=2,
                          stages=(StageDefinition(3, 1, timed, error_message="Timed."),))
        evaluate_lockout_policies(CAContext(self.user), AuthEventType.MFA_FAIL)
        self.assertEqual("Permanent.", self._state().error_message)

    def test_ip_block_stores_and_surfaces_the_stage_message(self):
        ip = "203.0.113.77"
        block = [StageActionDefinition(LockoutAction.BLOCK_IP, {"duration_seconds": 3600})]
        self._make_policy(name="blockmsg", counter_type=AuthEventType.PASSWORD_FAIL, window=300,
                          target=LockoutTarget.SOURCE_IP, count_mode=CountMode.PER_REQUEST,
                          stages=(StageDefinition(3, 1, block, error_message="Blocked for {duration}."),))
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=1, per_user=3)
        evaluate_lockout_policies(CAContext(self.user, ip), AuthEventType.PASSWORD_FAIL)
        self.assertEqual("Blocked for {duration}.", self._block(ip).error_message)
        self.assertEqual("Blocked for {duration}.", get_ip_block(ip).error_message)

    def test_render_error_message_substitutes_only_the_duration_tag(self):
        template = "Locked. Retry in about {duration}. Braces {} and {other} stay."
        rendered = render_error_message(template, RestrictionStatus(False, None, 90))
        self.assertEqual("Locked. Retry in about 2 minute(s). Braces {} and {other} stay.", rendered)

    def test_render_error_message_switches_to_hours(self):
        self.assertEqual("Retry in about 2 hour(s).",
                         render_error_message("Retry in about {duration}.", RestrictionStatus(False, None, 5400)))

    def test_duration_tag_is_left_as_written_where_there_is_no_remaining_time(self):
        # A countdown configured for something that does not count down is a misconfiguration, so the tag
        # is left visible exactly like any other tag we do not substitute - quietly dropping the message
        # would leave an admin wondering why their wording never appears.
        template = "Retry in about {duration}."
        self.assertEqual(template, render_error_message(template, RestrictionStatus(True, None, None)))
        # A DENY or a notify-only stage leaves no restriction behind at all, so it behaves the same.
        self.assertEqual(template, render_error_message(template))

    def test_a_message_without_the_tag_is_shown_wherever_it_applies(self):
        # Only the tag needs a duration; wording that does not use it is shown everywhere.
        message = "Your account has been locked. Please contact your administrator."
        self.assertEqual(message, render_error_message(message, RestrictionStatus(True, None, None)))
        self.assertEqual(message, render_error_message(message, RestrictionStatus(False, None, 90)))
        self.assertEqual(message, render_error_message(message))

    def test_render_error_message_is_none_without_a_message(self):
        # Nothing stored means the caller stays generic rather than inventing wording.
        self.assertIsNone(render_error_message(None, RestrictionStatus(False, None, 60)))
        self.assertIsNone(render_error_message("", RestrictionStatus(False, None, 60)))

    def test_deny_decision_carries_the_stage_message(self):
        # A DENY decides this one request and persists nothing, so its wording is read live off the
        # deciding stage rather than copied to a state row.
        self._make_policy(name="deny msg", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(3, 1, [StageActionDefinition(LockoutAction.DENY)],
                                                  error_message="Access denied."),))
        self._seed_events(AuthEventType.MFA_FAIL, 3)
        result = evaluate_access_decision(CAContext(self.user))
        self.assertEqual(AccessDecision.DENY, result.decision)
        self.assertEqual("Access denied.", result.error_message)

    def test_allow_carries_no_message(self):
        # An ALLOW turns nothing away, so it has nothing to tell the user even with wording configured.
        self._make_policy(name="allow msg", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(0, 1, [StageActionDefinition(LockoutAction.ALLOW)],
                                                  error_message="Should never be shown."),))
        allowed = evaluate_access_decision(CAContext(self.user))
        self.assertEqual(AccessDecision.ALLOW, allowed.decision)
        self.assertIsNone(allowed.error_message)

    def test_undecided_request_carries_no_message(self):
        # Below the threshold no stage decides, so the configured wording stays unused.
        self._make_policy(name="deny high", counter_type=AuthEventType.MFA_FAIL,
                          stages=(StageDefinition(99, 1, [StageActionDefinition(LockoutAction.DENY)],
                                                  error_message="Not reached."),))
        undecided = evaluate_access_decision(CAContext(self.user))
        self.assertEqual(AccessDecision.CONTINUE, undecided.decision)
        self.assertIsNone(undecided.error_message)
