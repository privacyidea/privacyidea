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
Shared test fixtures for the conditional-access lockout tests.

:class:`LockoutTestCase` is the common base for the engine and template suites:
it resolves a real test user, wipes every lockout table before and after each
test, and offers helpers to seed ``authentication_log`` events and read back
the resulting lock / block state.

This module is deliberately **not** named ``test_*`` so pytest does not collect
it; the concrete suites import :class:`LockoutTestCase` and add their own tests.
"""
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.context import CAContext
from privacyidea.lib.conditional_access.engine import evaluate_lockout_policies
from privacyidea.lib.user import User
from privacyidea.models import db
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
from privacyidea.models.utils import utc_now
from .base import MyTestCase


class LockoutTestCase(MyTestCase):
    """
    Base for conditional-access lockout tests: a resolved test user plus a clean
    slate of all lockout tables - and of Flask's ``g`` - around every test.
    """

    def setUp(self):
        # The app context is pushed once per class, so g outlives individual requests and leftovers bleed between
        # tests (e.g. a previous /auth leaving resolved_user.is_local_admin set, which build_ca_context reads for
        # the role); the engine's inputs come from g, so these tests start it empty.
        self.reset_flask_g()
        self.setUp_user_realms()
        # "cornelius" resolves to a non-empty uid ("root" has an empty one), so it is a fully resolved
        # (resolver, uid, realm) identity the engine acts on, and it carries an email the EMAIL_* actions target.
        self.user = User("cornelius", self.realm1, self.resolvername1)
        self._clear()

    def tearDown(self):
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        for model in (UserLockoutState, BlockList, LockoutStageAction, LockoutPolicyStage,
                      LockoutPolicyCondition, LockoutPolicyCounterType, LockoutPolicy,
                      AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _seed_events(self, event_type, count, timestamp=None, user=None):
        """Insert *count* authentication-log rows for *user* (default: the test user)."""
        user = user or self.user
        timestamp = timestamp if timestamp is not None else utc_now()
        for _ in range(count):
            db.session.add(AuthenticationLog(
                event_type=str(event_type), resolver=user.resolver, uid=user.uid,
                realm=user.realm, timestamp=timestamp))
        db.session.commit()

    def _seed_attempts(self, event_type, count, timestamp=None, user=None, start=0):
        """Insert *count* single-row authentication attempts for *user* (default: the test user), each with its own
        ``attempt_id`` (``att<start>``..). This is the PER_ATTEMPT shape where every attempt is one request, so the
        engine counts *count* distinct attempts (unlike :func:`_seed_events`, whose rows share a null attempt_id and
        collapse to one attempt under PER_ATTEMPT). *start* offsets the index so several calls stay non-overlapping."""
        user = user or self.user
        timestamp = timestamp if timestamp is not None else utc_now()
        for i in range(start, start + count):
            db.session.add(AuthenticationLog(
                event_type=str(event_type), resolver=user.resolver, uid=user.uid,
                realm=user.realm, timestamp=timestamp, attempt_id=f"att{i}"))
        db.session.commit()

    def _seed_ip_events(self, source_ip, event_type, n_users, per_user=1, timestamp=None, start=0):
        """Seed *n_users* distinct users (``spray<start>``..), each with *per_user* rows, all from
        *source_ip* (the password-spraying shape: one IP hitting many users). Each user carries a
        distinct ``username`` (as a resolved row does in production), which is the key
        :func:`count_distinct_users_for_ip` counts on. *start* offsets the user index so several calls
        can seed non-overlapping users."""
        timestamp = timestamp if timestamp is not None else utc_now()
        for i in range(start, start + n_users):
            for _ in range(per_user):
                db.session.add(AuthenticationLog(
                    event_type=str(event_type), resolver=self.user.resolver, uid=f"spray{i}",
                    realm=self.user.realm, username=f"spray{i}", source_ip=source_ip, timestamp=timestamp))
        db.session.commit()

    def _seed_ip_unknown_events(self, source_ip, event_type, usernames, timestamp=None):
        """Seed one unresolved ``USER_UNKNOWN``-style row per attempted *usernames* from *source_ip*:
        resolver/uid/realm are ``None`` (the user never resolved) and only the tried ``username`` is
        recorded, the enumeration / credential-stuffing shape. A ``None`` entry seeds a fully
        userless row (e.g. an initial usernameless passkey request)."""
        timestamp = timestamp if timestamp is not None else utc_now()
        for username in usernames:
            db.session.add(AuthenticationLog(
                event_type=str(event_type), resolver=None, uid=None, realm=None,
                username=username, source_ip=source_ip, timestamp=timestamp))
        db.session.commit()

    def _state(self, user: User | None = None) -> UserLockoutState | None:
        user = user or self.user
        return db.session.get(UserLockoutState, (user.resolver, user.uid, user.realm))

    def _block(self, ip: str) -> BlockList | None:
        return db.session.get(BlockList, ip)

    def _triggered_thresholds(self, event_type: AuthEventType = AuthEventType.MFA_FAIL,
                              source_ip: str | None = None) -> list[int]:
        """
        Evaluate the policies and return the threshold of every stage that fired, in order.

        The threshold is a stage's natural key within its policy, so this identifies which stage acted without
        depending on a surrogate id that a policy edit would replace. Empty when nothing fired.
        """
        evaluation = evaluate_lockout_policies(CAContext(self.user, source_ip), event_type)
        return [outcome.threshold for outcome in evaluation.outcomes]
