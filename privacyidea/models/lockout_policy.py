# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
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
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Index,
    Identity,
    Unicode,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.lib.conditional_access.authentication_event_types import CountMode
from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin, utc_now, case_sensitive_unicode

log = logging.getLogger(__name__)


class LockoutPolicy(MethodsMixin, db.Model):
    """
    Container for a set of conditional-access lockout rules.

    A policy defines which failure counter(s) to track (e.g. ``MFA_FAIL``,
    ``PASSWORD_FAIL``) within a sliding time window. The tracked types live in
    the related :class:`LockoutPolicyCounterType` rows; ``counter_types_to_track``
    is the list-of-strings view over them used throughout the code and tests
    (assignable as a plain list). Their events are counted **together** (a single
    combined count over all listed types) against the stage thresholds. Admins
    can define multiple policies (e.g. "Admin Policy" vs "Default User Policy");
    policies are evaluated by ascending ``priority`` (a lower number means higher
    precedence, matching privacyIDEA's policy engine). The ``priority`` is unique
    across policies so the evaluation order - and thus which policy wins an
    allow/deny decision - is always unambiguous.

    The actual thresholds and reactions live in the related
    :class:`LockoutPolicyStage` and :class:`LockoutStageAction` rows, and the
    related :class:`LockoutPolicyCondition` rows restrict *to whom* the policy
    applies at all.
    """
    __tablename__ = 'lockout_policies'
    __table_args__ = (UniqueConstraint('priority', name='uq_lockout_policy_priority'),)
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(255), nullable=False, unique=True)
    time_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # With dry_run set, the policy is evaluated and logged but no action is enforced.
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    # The identity this policy counts and acts on: "user" or "source_ip".
    target: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    # Counting mode against the stage thresholds: per authentication_log row
    # (PER_REQUEST) or per whole authentication attempt (PER_ATTEMPT).
    count_mode: Mapped[str] = mapped_column(Unicode(20), default=CountMode.PER_REQUEST, nullable=False)

    stages: Mapped[list["LockoutPolicyStage"]] = relationship(
        "LockoutPolicyStage",
        back_populates="policy",
        cascade="all, delete-orphan",
        # Descending threshold, which is the evaluation order: the most severe matching stage wins. The
        # (policy_id, failure_threshold) unique constraint makes this a total order, so the triggered stage never
        # depends on insertion order.
        order_by="LockoutPolicyStage.failure_threshold.desc()")
    # The failure counter type(s) this policy tracks, normalized into this indexed child table: the
    # per-request lookup is one equality filter on counter_type, avoiding a Python scan of every enabled policy.
    counter_types: Mapped[list["LockoutPolicyCounterType"]] = relationship(
        "LockoutPolicyCounterType",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="LockoutPolicyCounterType.id")
    # List-of-strings view over ``counter_types``: read it like a list, and assign a list (e.g.
    # ``LockoutPolicy(counter_types_to_track=["PIN_FAIL"])``) to create the child rows, in order.
    counter_types_to_track: AssociationProxy[list[str]] = association_proxy(
        "counter_types", "counter_type",
        creator=lambda counter_type: LockoutPolicyCounterType(counter_type=counter_type))
    # Whether this policy applies to a request, evaluated before anything is counted: all conditions
    # must match (AND); none at all means the policy applies to everyone.
    # Ordered by condition_type, not id, so the same set of conditions always reads back in the same
    # order, letting a client compare a policy against its own draft without sorting first.
    conditions: Mapped[list["LockoutPolicyCondition"]] = relationship(
        "LockoutPolicyCondition",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="LockoutPolicyCondition.condition_type")


class LockoutPolicyCondition(MethodsMixin, db.Model):
    """
    One restriction on which requests a :class:`LockoutPolicy` applies to, e.g.
    "only for users of the realms sales and support" or "not for admins".

    This is the *applicability* axis, orthogonal to the counting one: conditions
    decide **whether** a policy is evaluated for a request, while the counter
    types, the count mode and the stage thresholds decide **what** trips it.
    Keeping them separate is what lets the two compose - a policy can restrict
    itself to a realm *and* still require a threshold of failures.

    All of a policy's conditions must match (AND); a policy with no conditions
    applies to everyone, which is why adding this table leaves existing policies
    behaving exactly as before.

    The row is deliberately generic so a new kind of condition is a new
    ``condition_type`` in the registry rather than a schema change:

    * ``condition_type`` names what to read from the request context (e.g.
      ``USER_REALM``, ``USER_ROLE``). A policy carries **at most one condition of
      each type**, enforced by the unique constraint: two conditions on the same
      value could only narrow to a contradiction, since they are ANDed.
    * ``operator`` names how to compare, and determines the shape of ``value``:
      a list for the set-membership operators (``IN`` / ``NOT_IN``), a scalar for
      future comparison operators, ``NULL`` for future zero-arity ones.
    * ``value`` is JSON rather than a normalized child table because nothing
      filters on it in SQL - conditions are evaluated in Python against the
      request context - so normalizing would only add a join.

    A condition type with an *open* key space (an HTTP header name, a userinfo
    attribute) would need a ``key`` column alongside ``condition_type``, and the
    unique constraint widened to include it. None of the types defined today is
    keyed, so the column is deliberately absent rather than carried empty; adding
    it later is a column plus a constraint rebuild.
    """
    __tablename__ = 'lockout_policy_conditions'
    __table_args__ = (
        UniqueConstraint('policy_id', 'condition_type', name='uq_lockout_condition_policy'),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    policy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('lockout_policies.id', ondelete='CASCADE'), nullable=False, index=True)
    condition_type: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    operator: Mapped[str] = mapped_column(Unicode(20), nullable=False)
    value: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    policy: Mapped["LockoutPolicy"] = relationship("LockoutPolicy", back_populates="conditions")


class LockoutPolicyCounterType(MethodsMixin, db.Model):
    """
    One failure counter type tracked by a :class:`LockoutPolicy`, normalized out
    of the former ``counter_types_to_track`` JSON column.

    A policy has one row here per tracked :class:`AuthEventType` value. Keeping
    the types in their own indexed table lets the authentication hot path select
    just the policies that track the current event type with a single equality
    filter, instead of loading every enabled policy and filtering the JSON list
    in Python (which grew the per-request DB work with the total policy count).
    """
    __tablename__ = 'lockout_policy_counter_types'
    __table_args__ = (
        UniqueConstraint('policy_id', 'counter_type',
                         name='uq_lockout_counter_type_policy'),
        # Leading column is counter_type: the per-request lookup filters by the
        # current event type, then joins back to the small set of policy ids.
        Index('ix_lockout_counter_type_lookup', 'counter_type', 'policy_id'),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    policy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('lockout_policies.id', ondelete='CASCADE'), nullable=False)
    counter_type: Mapped[str] = mapped_column(Unicode(100), nullable=False)

    policy: Mapped["LockoutPolicy"] = relationship("LockoutPolicy", back_populates="counter_types")


class LockoutPolicyStage(MethodsMixin, db.Model):
    """
    A failure threshold within a :class:`LockoutPolicy`. Each policy has
    N stages (e.g. 5, 10 and 15 failures).

    Post-response, each of a stage's actions fires when the failure count reaches
    the stage's ``failure_threshold`` (see
    :attr:`LockoutStageAction.retrigger_above_threshold` for the per-action
    fire-once vs re-trigger choice); escalation is expressed as separate stages
    per threshold. Stages are evaluated by descending ``failure_threshold``, so
    the most severe matching stage is the one that acts (and, on the pre-auth
    path, the one that supplies the ALLOW/DENY verdict). The threshold is unique
    per policy, so that order is total and needs nothing else configured.

    A threshold counts failures and therefore starts at 1; the CRUD layer allows
    0 only on a stage whose every action is ``ALLOW``, the unconditional
    default-allow idiom.
    """
    __tablename__ = 'lockout_policy_stages'
    __table_args__ = (
        # The unique constraint's backing index also serves lookups by policy_id, so no separate index is needed.
        UniqueConstraint('policy_id', 'failure_threshold',
                         name='uq_lockout_stage_policy_threshold'),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    policy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('lockout_policies.id', ondelete='CASCADE'), nullable=False)
    # Optional human-readable label for the stage (e.g. "Warn", "Lock 10 min").
    name: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    failure_threshold: Mapped[int] = mapped_column(Integer, nullable=False)

    policy: Mapped["LockoutPolicy"] = relationship("LockoutPolicy", back_populates="stages")
    actions: Mapped[list["LockoutStageAction"]] = relationship(
        "LockoutStageAction",
        back_populates="stage",
        cascade="all, delete-orphan")


class LockoutStageAction(MethodsMixin, db.Model):
    """
    What to do when a :class:`LockoutPolicyStage` is triggered. One stage
    can have multiple actions (e.g. lock the user *and* email the admin).

    ``action_value`` is the action-specific payload, stored as JSON:
    e.g. the lock duration in seconds for ``LOCK_USER``/``BLOCK_IP`` or
    an email template ID for ``EMAIL_ADMIN``/``EMAIL_USER``.

    ``retrigger_above_threshold`` controls how this action fires as the failure
    count crosses its stage's threshold. False: fire once, when the count equals
    the threshold exactly. True: keep firing while the count stays at or above the
    threshold (the classic re-triggering lockout; de-dup still throttles repeats
    within one incident). Because it is per action, one stage can e.g. email once
    at its threshold while re-triggering the user lock. The CRUD layer picks an
    action-aware default when the client omits it (ALLOW/DENY decisions default to
    True, the lock/email/block effects to False); see
    :func:`~privacyidea.lib.conditional_access.lockout_policy._validate_stages`
    and :func:`~privacyidea.lib.conditional_access.engine._action_threshold_met`.
    """
    __tablename__ = 'lockout_stage_actions'
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('lockout_policy_stages.id', ondelete='CASCADE'),
        nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    action_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    retrigger_above_threshold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    stage: Mapped["LockoutPolicyStage"] = relationship("LockoutPolicyStage", back_populates="actions")


class UserLockoutState(MethodsMixin, db.Model):
    """
    The current lockout status of a single user, keyed by the same
    ``(resolver, uid, realm)`` tuple used in :class:`AuthenticationLog`.

    There is deliberately **no failure counter** stored here: failure counts
    are derived on demand by querying ``authentication_log`` over a policy's
    time window. That keeps the data flexible (per-policy windows, easy reset,
    automatic decay) and avoids stale counters on user objects.

    ``lock_expires_at`` is the load-bearing field: a row exists only while the
    user is locked, and a row whose ``lock_expires_at`` lies in the future (or is
    ``NULL`` for a permanent lock) means the user is currently locked; an admin
    lifts a lock by deleting the row (timestamps are naive UTC, see
    :func:`~privacyidea.models.utils.utc_now`).

    The row records the lock itself, not which policy produced it: what a stage
    did, and to whom, is the conditional-access history
    (:class:`~privacyidea.models.conditional_access_outcome.ConditionalAccessOutcome`).
    """
    __tablename__ = 'user_lockout_state'
    resolver: Mapped[str] = mapped_column(case_sensitive_unicode(120), primary_key=True)
    uid: Mapped[str] = mapped_column(case_sensitive_unicode(320), primary_key=True)
    realm: Mapped[str] = mapped_column(case_sensitive_unicode(255), primary_key=True)
    # Denormalized login captured at lock time; lets management views display/filter by name and lets
    # a user-scoped read policy be enforced in SQL without a live resolver lookup, which fails for a deleted user.
    username: Mapped[str | None] = mapped_column(case_sensitive_unicode(255), nullable=True)
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # When the lock was applied; refreshed on each (re)lock, so it marks the start of the current
    # active lock, not a generic audit timestamp.
    locked_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class BlockList(MethodsMixin, db.Model):
    """
    A blocked source identity (currently a source IP), written by the
    ``BLOCK_IP`` conditional-access action and consulted by the authentication
    pre-check on the *next* inbound request — exactly the live-state pattern of
    :class:`UserLockoutState`, but keyed by the request's source IP rather than
    by the user.

    The IP is the natural primary key. ``block_expires_at`` is the load-bearing
    field: a row exists only while the IP is blocked, and a row whose
    ``block_expires_at`` lies in the future means the IP is currently blocked,
    while a ``NULL`` value means a permanent block (only an admin reset, which
    deletes the row, clears it). Timestamps are naive UTC, see
    :func:`~privacyidea.models.utils.utc_now`.

    Like :class:`UserLockoutState` the row records the block itself, not which
    policy produced it; that is the conditional-access history
    (:class:`~privacyidea.models.conditional_access_outcome.ConditionalAccessOutcome`).
    """
    __tablename__ = 'block_list'
    # TODO: the blocked identity is a source IP for now; a future revision may generalize to other
    # identifiers (device, API key, ...) via generic columns (id, entry_type, value).
    # 50 matches authentication_log.source_ip, wide enough for an IPv4-mapped IPv6 address.
    ip: Mapped[str] = mapped_column(Unicode(50), primary_key=True)
    block_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # When the block was applied; refreshed on each (re)block, so it marks the start of the current
    # active block, not a generic audit timestamp.
    blocked_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False)
