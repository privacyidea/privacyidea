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
Shared test fixtures for the conditional-access suites.

:class:`ConditionalAccessFixtureMixin` holds everything a conditional-access test needs to set a scene and read it
back: the table wipe, the writers that put a lock or a block in force, the readers that look one up, the
authentication-log seeders that stand in for the events a policy counts, and the policy factories. It is a plain
mixin so both base classes below - and the token suites, which need their own fixture class - share one vocabulary
rather than each reinventing it.

:class:`ConditionalAccessTestCase` is the base for the lib suites (engine, templates, state) and
:class:`ConditionalAccessApiTestCase` the base for those that dispatch real requests.

The writers overwrite whatever row is already there (``merge``), because a fixture states what is in force rather
than negotiating with it: the production write path declines anything but a strictly stronger lock, which would
silently drop a test's second, weaker scene.

This module is deliberately **not** named ``test_*`` so pytest does not collect it; the concrete suites import from
it and add their own tests.
"""
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta

from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType, AuthLogUserRole,
                                                                          RestrictionCause)
from privacyidea.lib.conditional_access.context import CAContext
from privacyidea.lib.conditional_access.engine import (ConditionalAccessAction, ConditionalAccessTarget,
                                                       evaluate_conditional_access_policies)
from privacyidea.lib.conditional_access.policy import create_conditional_access_policy
from privacyidea.lib.user import User
from privacyidea.models import Challenge, ConditionalAccessOutcome, db
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.authentication_log_reason import AuthenticationLogReason
from privacyidea.models.conditional_access_policy import (
    BlockList,
    ConditionalAccessPolicy,
    ConditionalAccessPolicyCondition,
    ConditionalAccessPolicyCounterType,
    ConditionalAccessPolicyStage,
    ConditionalAccessStageAction,
    UserLockState,
)
from privacyidea.models.utils import utc_now
from .base import MyApiTestCase, MyTestCase

#: How long a lock or block the fixtures write stays in force when a test does not say.
DEFAULT_DURATION = 600

#: The source IP the block tests use - not loopback, which is on the never-block list.
BLOCKED_IP = "203.0.113.9"

#: The source IP a stateless source-IP DENY is decided for. Distinct from BLOCKED_IP so a test can tell the two
#: restrictions apart, and routable for the same reason: a never-block address is exempt from an IP DENY too.
DENIED_IP = "203.0.113.8"


class ConditionalAccessFixtureMixin:
    """
    The conditional-access scene-setting vocabulary, shared by every suite that has one.

    Mixed in ahead of the ``TestCase`` base so a suite can still override any of it.
    """

    #: Everything a conditional-access test may write, wiped around each test. Children first: a bulk delete runs no
    #: ORM cascade and SQLite does not enforce the foreign key, so orphaned rows would attach themselves to the next
    #: row that reuses the freed id (SQLite hands out max(rowid)+1).
    ca_tables: tuple = (ConditionalAccessOutcome, AuthenticationLogReason, UserLockState, BlockList,
                        ConditionalAccessStageAction, ConditionalAccessPolicyStage,
                        ConditionalAccessPolicyCondition, ConditionalAccessPolicyCounterType,
                        ConditionalAccessPolicy, AuthenticationLog)

    #: The user the fixtures act on unless a call names another one. "cornelius" resolves to a non-empty uid ("root"
    #: has an empty one), so it is a fully resolved (resolver, uid, realm) identity the engine acts on, and it
    #: carries an email the EMAIL_* actions target.
    username = "cornelius"

    user: User

    # --- the clean slate ------------------------------------------------------

    @classmethod
    def _clear(cls) -> None:
        for model in cls.ca_tables:
            db.session.query(model).delete()
        db.session.commit()

    # --- writers: put a restriction in force ----------------------------------

    def _lock_user(self, lock_expires_at: datetime | None, *, user: User | None = None,
                   error_message: str | None = None, cause: RestrictionCause | str = RestrictionCause.POLICY,
                   resolver: str | None = None, uid: str | None = None,
                   realm: str | None = None, username: str | None = None,
                   user_role: AuthLogUserRole | str | None = None) -> None:
        """
        Lock *user* (default: the test user) until *lock_expires_at*, or permanently when that is ``None``.
        The expiry is required rather than defaulted, since a lock that never lifts is never the incidental choice;
        :meth:`_lock_user_for` is the timed one.

        Writes the row a *policy* lock leaves behind, which is the scene nearly every test wants - including the
        ``error_message`` a stage configured, which :func:`~privacyidea.lib.conditional_access.state.lock_user`
        deliberately clears. Use that function instead wherever the manual path is what is under test.

        The identity columns are overridable so a suite can write the rows no supported call produces - a local-admin
        row, or one standing under a spelling no account has any more.
        """
        user = user or self.user
        db.session.merge(UserLockState(
            resolver=resolver if resolver is not None else user.resolver,
            uid=uid if uid is not None else user.uid,
            realm=realm if realm is not None else user.realm,
            username=username if username is not None else user.login,
            # Both spelled out rather than left to the column default: ``merge`` copies only the attributes the
            # instance actually carries, so an omitted one keeps whatever the existing row holds. The cause has to
            # travel with the expiry (see RestrictionCause) or a fixture write onto an admin's lock would leave the
            # row attributed to them; the role is NOT NULL, so omitting it fails outright on an update.
            user_role=str(user_role) if user_role is not None else str(AuthLogUserRole.USER),
            lock_cause=str(cause),
            lock_expires_at=lock_expires_at, error_message=error_message))
        db.session.commit()

    def _lock_user_for(self, seconds: int = DEFAULT_DURATION, **kwargs) -> None:
        """Lock the user for *seconds* from now - the timed lock most tests want, without restating the arithmetic."""
        self._lock_user(utc_now() + timedelta(seconds=seconds), **kwargs)

    @staticmethod
    def _block_ip(ip: str, block_expires_at: datetime | None, *, error_message: str | None = None,
                  cause: RestrictionCause | str = RestrictionCause.POLICY) -> None:
        """Block *ip* until *block_expires_at*, or permanently when that is ``None``; see :meth:`_block_ip_for`.

        The IP-side counterpart of :meth:`_lock_user`, writing what a policy block leaves behind. It also skips the
        never-block check and the canonicalization that
        :func:`~privacyidea.lib.conditional_access.state.block_ip` applies, so a suite can file the rows the
        production path refuses - which is the point of testing that the pre-check still ignores them."""
        db.session.merge(BlockList(ip=ip, block_expires_at=block_expires_at, error_message=error_message,
                                   block_cause=str(cause)))
        db.session.commit()

    def _block_ip_for(self, ip: str, seconds: int = DEFAULT_DURATION, **kwargs) -> None:
        """Block *ip* for *seconds* from now."""
        self._block_ip(ip, utc_now() + timedelta(seconds=seconds), **kwargs)

    # --- readers --------------------------------------------------------------

    def _state(self, user: User | None = None) -> UserLockState | None:
        user = user or self.user
        return db.session.get(UserLockState, (user.resolver, user.uid, user.realm))

    @staticmethod
    def _block_state(ip: str) -> BlockList | None:
        return db.session.get(BlockList, ip)

    # --- seeding the events a policy counts -----------------------------------

    def _seed_events(self, event_type, count: int, timestamp: datetime | None = None, user: User | None = None):
        """Insert *count* authentication-log rows for *user* (default: the test user)."""
        user = user or self.user
        timestamp = timestamp if timestamp is not None else utc_now()
        for _ in range(count):
            db.session.add(AuthenticationLog(
                event_type=str(event_type), resolver=user.resolver, uid=user.uid,
                realm=user.realm, timestamp=timestamp))
        db.session.commit()

    def _seed_attempts(self, event_type, count: int, timestamp: datetime | None = None, user: User | None = None,
                       start: int = 0):
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

    def _seed_ip_events(self, source_ip: str, event_type, n_users: int, per_user: int = 1,
                        timestamp: datetime | None = None, start: int = 0, user: User | None = None):
        """Seed *n_users* distinct users (``spray<start>``..), each with *per_user* rows, all from
        *source_ip* (the password-spraying shape: one IP hitting many users). Each user carries a
        distinct ``username`` (as a resolved row does in production), which is the key
        :func:`count_distinct_users_for_ip` counts on. *start* offsets the user index so several calls
        can seed non-overlapping users. The users are synthetic and need not resolve - only the distinct
        ``(username, realm, resolver)`` count matters - so they borrow *user*'s resolver and realm."""
        user = user or self.user
        timestamp = timestamp if timestamp is not None else utc_now()
        for i in range(start, start + n_users):
            for _ in range(per_user):
                db.session.add(AuthenticationLog(
                    event_type=str(event_type), resolver=user.resolver, uid=f"spray{i}",
                    realm=user.realm, username=f"spray{i}", source_ip=source_ip, timestamp=timestamp))
        db.session.commit()

    @staticmethod
    def _seed_ip_unknown_events(source_ip: str, event_type, usernames: Iterable[str | None],
                                timestamp: datetime | None = None):
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

    # --- policy factories -----------------------------------------------------

    @staticmethod
    def _counter_types(counter_type) -> list[str]:
        """Normalize a single AuthEventType (or string) or an iterable of them into
        the list-of-strings shape stored in ``ConditionalAccessPolicy.counter_types_to_track``."""
        values = counter_type if isinstance(counter_type, (list, tuple)) else [counter_type]
        return [str(t) for t in values]

    @classmethod
    def _make_lock_policy(cls, *, counter_type, threshold: int, duration: int, window: int = 3600,
                          dry_run: bool = False, priority: int = 1, error_message: str | None = None,
                          reset_on_success: bool | None = None, conditions: Sequence[dict] = (),
                          name: str = "ca_lock") -> int:
        return create_conditional_access_policy(
            name=name, time_window_seconds=window,
            counter_types_to_track=cls._counter_types(counter_type),
            stages=[{"failure_threshold": threshold, "error_message": error_message,
                     "actions": [{"action_type": str(ConditionalAccessAction.LOCK_USER), "action_value": duration}]}],
            conditions=list(conditions) or None,
            target=ConditionalAccessTarget.USER, dry_run=dry_run, priority=priority,
            reset_on_success=reset_on_success)

    @classmethod
    def _make_block_ip_policy(cls, *, counter_type, threshold: int, duration: int, window: int = 3600,
                              priority: int = 1, error_message: str | None = None,
                              name: str = "ca_blockip") -> int:
        return create_conditional_access_policy(
            name=name, time_window_seconds=window,
            counter_types_to_track=cls._counter_types(counter_type),
            stages=[{"failure_threshold": threshold, "error_message": error_message,
                     "actions": [{"action_type": str(ConditionalAccessAction.BLOCK_IP), "action_value": duration}]}],
            target=ConditionalAccessTarget.SOURCE_IP, priority=priority)

    @classmethod
    def _make_decision_policy(cls, *, name: str, counter_type, threshold: int, action,
                              priority: int = 1, window: int = 3600, error_message: str | None = None,
                              target=ConditionalAccessTarget.USER) -> int:
        """A policy whose stage carries a decision (DENY, PERMANENT_LOCK_USER, ...) - an action without a duration."""
        return create_conditional_access_policy(
            name=name, time_window_seconds=window,
            counter_types_to_track=cls._counter_types(counter_type),
            stages=[{"failure_threshold": threshold, "error_message": error_message,
                     "actions": [{"action_type": str(action), "action_value": None}]}],
            target=target, priority=priority)

    # --- evaluation -----------------------------------------------------------

    def _triggered_thresholds(self, event_type: AuthEventType = AuthEventType.MFA_FAIL,
                              source_ip: str | None = None) -> list[int]:
        """
        Evaluate the policies and return the threshold of every stage that fired, in order.

        The threshold is a stage's natural key within its policy, so this identifies which stage acted without
        depending on a surrogate id that a policy edit would replace. Empty when nothing fired.
        """
        outcomes = evaluate_conditional_access_policies(CAContext(self.user, source_ip), event_type)
        return [outcome.threshold for outcome in outcomes]


class ConditionalAccessTestCase(ConditionalAccessFixtureMixin, MyTestCase):
    """
    Base for the conditional-access lib tests: a resolved test user plus a clean
    slate of all conditional-access tables - and of Flask's ``g`` - around every test.
    """

    def setUp(self):
        # The app context is pushed once per class, so g outlives individual requests and leftovers bleed between
        # tests (e.g. a previous /auth leaving resolved_user.is_local_admin set, which build_ca_context reads for
        # the role); the engine's inputs come from g, so these tests start it empty.
        self.reset_flask_g()
        self.setUp_user_realms()
        self.user = User(self.username, self.realm1, self.resolvername1)
        self._clear()

    def tearDown(self):
        self._clear()
        super().tearDown()


class ConditionalAccessApiTestCase(ConditionalAccessFixtureMixin, MyApiTestCase):
    """
    Base for the conditional-access suites that dispatch real requests.

    Adds the challenge table to the wipe: these suites drive endpoints that hand out challenges, and one surviving
    into the next test changes what the authentication under test does. A suite that enrolls a token still removes
    it itself - the log it asserts on silently changes when the user owns a token they never created.
    """

    ca_tables = ConditionalAccessFixtureMixin.ca_tables + (Challenge,)

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.user = User(self.username, self.realm1, self.resolvername1)
        self._clear()

    def tearDown(self) -> None:
        self._clear()
        super().tearDown()
