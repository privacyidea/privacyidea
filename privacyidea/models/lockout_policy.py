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
    Sequence,
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
from privacyidea.models.utils import MethodsMixin, utc_now

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
    policies are evaluated highest ``priority`` first.

    The actual thresholds and reactions live in the related
    :class:`LockoutPolicyStage` and :class:`LockoutStageAction` rows.
    """
    __tablename__ = 'lockout_policies'
    id: Mapped[int] = mapped_column(Integer, Sequence("lockoutpolicy_seq"), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(255), nullable=False, unique=True)
    time_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # With dry_run the policy is evaluated and the decision is logged,
    # but no action is enforced.
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # How the tracked counters are counted against the stage thresholds: per authentication_log row
    # ("PER_REQUEST", the default) or per whole authentication attempt ("PER_ATTEMPT").
    count_mode: Mapped[str] = mapped_column(Unicode(20), default=CountMode.PER_REQUEST, nullable=False)

    stages: Mapped[list["LockoutPolicyStage"]] = relationship(
        "LockoutPolicyStage",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="LockoutPolicyStage.priority.desc()")
    # The failure counter type(s) this policy tracks, normalized into the
    # lockout_policy_counter_types child table so the per-request lookup can be a
    # single indexed equality filter (``counter_type = :event_type``) instead of
    # loading every enabled policy and filtering a JSON list in Python.
    counter_types: Mapped[list["LockoutPolicyCounterType"]] = relationship(
        "LockoutPolicyCounterType",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="LockoutPolicyCounterType.id")
    # List-of-strings view over ``counter_types``: read it like a list, and assign
    # a list (e.g. ``LockoutPolicy(counter_types_to_track=["PIN_FAIL"])``) to
    # create the child rows. Order of assignment is preserved.
    counter_types_to_track: AssociationProxy[list[str]] = association_proxy(
        "counter_types", "counter_type",
        creator=lambda counter_type: LockoutPolicyCounterType(counter_type=counter_type))


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
    id: Mapped[int] = mapped_column(Integer, Sequence("lockoutpolicycountertype_seq"), primary_key=True)
    policy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('lockout_policies.id', ondelete='CASCADE'), nullable=False)
    counter_type: Mapped[str] = mapped_column(Unicode(100), nullable=False)

    policy: Mapped["LockoutPolicy"] = relationship("LockoutPolicy", back_populates="counter_types")


class LockoutPolicyStage(MethodsMixin, db.Model):
    """
    A failure threshold within a :class:`LockoutPolicy`. Each policy has
    N stages (e.g. 5, 10 and 15 failures).

    Within a policy the stages are evaluated highest ``priority`` first,
    so the most severe matching stage wins (e.g. evaluate the 15-fail
    stage before the 5-fail stage).
    """
    __tablename__ = 'lockout_policy_stages'
    __table_args__ = (
        # The unique constraint's backing index also serves lookups by
        # policy_id, so no separate index is needed.
        UniqueConstraint('policy_id', 'failure_threshold',
                         name='uq_lockout_stage_policy_threshold'),
    )
    id: Mapped[int] = mapped_column(Integer, Sequence("lockoutpolicystage_seq"), primary_key=True)
    policy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('lockout_policies.id', ondelete='CASCADE'), nullable=False)
    failure_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

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
    """
    __tablename__ = 'lockout_stage_actions'
    id: Mapped[int] = mapped_column(Integer, Sequence("lockoutstageaction_seq"), primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('lockout_policy_stages.id', ondelete='CASCADE'),
        nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    action_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    stage: Mapped["LockoutPolicyStage"] = relationship("LockoutPolicyStage", back_populates="actions")


class UserLockoutState(MethodsMixin, db.Model):
    """
    The current lockout status of a single user, keyed by the same
    ``(resolver, uid, realm)`` tuple used in :class:`AuthenticationLog`.

    There is deliberately **no failure counter** stored here: failure counts
    are derived on demand by querying ``authentication_log`` over a policy's
    time window. That keeps the data flexible (per-policy windows, easy reset,
    automatic decay) and avoids stale counters on user objects.

    ``lock_expires_at`` is the load-bearing field: a row whose
    ``lock_expires_at`` lies in the future means the user is currently locked
    (timestamps are naive UTC, see :func:`~privacyidea.models.utils.utc_now`).
    ``last_stage_triggered`` records which stage produced the current state,
    both for auditing and so a stage's actions are not fired twice (de-dup).
    """
    __tablename__ = 'user_lockout_state'
    resolver: Mapped[str] = mapped_column(Unicode(120), primary_key=True)
    uid: Mapped[str] = mapped_column(Unicode(320), primary_key=True)
    realm: Mapped[str] = mapped_column(Unicode(255), primary_key=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # SET NULL on delete: keep the lockout state row if its stage is removed.
    last_stage_triggered: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('lockout_policy_stages.id', ondelete='SET NULL'),
        nullable=True, index=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    last_stage: Mapped["LockoutPolicyStage | None"] = relationship("LockoutPolicyStage")


class BlockList(MethodsMixin, db.Model):
    """
    A blocked source identity (currently a source IP), written by the
    ``BLOCK_IP`` conditional-access action and consulted by the authentication
    pre-check on the *next* inbound request — exactly the live-state pattern of
    :class:`UserLockoutState`, but keyed by the request's source IP rather than
    by the user.

    The IP is the natural primary key. ``block_expires_at`` is the load-bearing
    field: a row whose ``block_expires_at`` lies in the future means the IP is
    currently blocked, and a ``NULL`` value means a permanent block (only an
    admin reset clears it). ``is_blocked`` lets an admin lift a block without
    deleting the row, so ``last_stage_triggered`` (which records the stage that
    produced the block, for de-duplication) is preserved. Timestamps are naive
    UTC, see :func:`~privacyidea.models.utils.utc_now`.
    """
    __tablename__ = 'block_list'
    # TODO: the blocked identity is a source IP for now. A future revision may
    # block other identifiers (device, API key, ...); the suggested shape is then
    # generic columns (id, entry_type, value) instead of an IP-typed primary key.
    # 50 matches authentication_log.source_ip, which is wide enough for an
    # IPv4-mapped IPv6 address.
    ip: Mapped[str] = mapped_column(Unicode(50), primary_key=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    block_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Free-form note on why the IP was blocked (e.g. the policy name); purely
    # informational, shown to admins, never to the blocked client.
    reason: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    # SET NULL on delete: keep the block if its originating stage is removed.
    last_stage_triggered: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('lockout_policy_stages.id', ondelete='SET NULL'),
        nullable=True, index=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    last_stage: Mapped["LockoutPolicyStage | None"] = relationship("LockoutPolicyStage")
