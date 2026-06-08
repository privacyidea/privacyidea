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
    Sequence,
    Unicode,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin, utc_now

log = logging.getLogger(__name__)


class LockoutPolicy(MethodsMixin, db.Model):
    """
    Container for a set of conditional-access lockout rules.

    A policy defines which failure counter to track (e.g. ``MFA_FAIL``,
    ``PASSWORD_FAIL``) within a sliding time window. Admins can define
    multiple policies (e.g. "Admin Policy" vs "Default User Policy");
    policies are evaluated highest ``priority`` first.

    The actual thresholds and reactions live in the related
    :class:`LockoutPolicyStage` and :class:`LockoutStageAction` rows.
    """
    __tablename__ = 'lockout_policies'
    id: Mapped[int] = mapped_column(Integer, Sequence("lockoutpolicy_seq"), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(255), nullable=False, unique=True)
    counter_type_to_track: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    time_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # With dry_run the policy is evaluated and the decision is logged,
    # but no action is enforced.
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    stages: Mapped[list["LockoutPolicyStage"]] = relationship(
        "LockoutPolicyStage",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="LockoutPolicyStage.priority.desc()")


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
