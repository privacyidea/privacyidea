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
__doc__ = """What conditional access did, and how it becomes the history of a request.

The engine judges a request; it does not write history. It builds transient
:class:`~privacyidea.models.conditional_access_outcome.ConditionalAccessOutcome` instances with
:func:`outcome_for_stage` (no ``auth_log_id`` yet) and returns them, and the request context has them recorded here once
the request's authentication-log row exists. That is what keeps the engine free of both Flask and the id of a row it
never sees, and it is what makes the *pre-auth* decision recordable at all: that runs before any log row is written, so
its outcome has to be carried rather than stored on the spot.

The model is deliberately left as schema only. Deriving an outcome from a policy and a stage is domain knowledge of this
layer, not of the table - and a model that reached for ``LockoutPolicy`` could not even import it, since
``models/__init__`` loads ``conditional_access_outcome`` before ``lockout_policy``.

**Outcomes are only ever written from here.** They are rows of the conditional-access subsystem, so they must go on its
session, where a failure cannot roll back the request's own work: never call ``save()`` on one.

This is the queryable history the state tables cannot provide: ``user_lockout_state`` and ``block_list`` show the
restriction in force *now* and forget it the moment it lapses.

Nothing here is read back on the authentication path. The engine counts over the authentication log, never over this
table (see :class:`~privacyidea.models.conditional_access_outcome.ConditionalAccessOutcome`), so this module only ever
writes.

Two things are deliberately **not** recorded here, so their absence is not read as a bug:

* An action the engine recognized but **skipped** - an invalid lock duration, an email without a recipient, a
  never-block IP. Only what happened is stored, so counting rows answers "how often was this user locked" without a
  filter; the ``log.warning`` each skip emits is the record of the misconfiguration.
* An admin **lifting** a lock or a block. That is a management operation whose interesting fact is *who* did it under
  which authorization, which the audit log records and this table has no column for (nor an authentication-log row to
  hang it on).
"""
import logging
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select

from privacyidea.lib.conditional_access.session import get_ca_session, guarded_write
from privacyidea.models import ConditionalAccessOutcome, LockoutPolicy, LockoutPolicyStage

log = logging.getLogger(__name__)


def outcome_for_stage(policy: LockoutPolicy, stage: LockoutPolicyStage, action_type: str, event_count: int, *,
                      dry_run: bool = False,
                      expires_at: datetime | None = None) -> ConditionalAccessOutcome:
    """
    Describe what one action of *stage* did (or, in dry run, would have done), copying out of the policy configuration
    what the history has to keep on its own: the policy name, the threshold and the stage name. Deliberately not the
    policy's id - see
    :class:`~privacyidea.models.conditional_access_outcome.ConditionalAccessOutcome` on why a recycled id is worse than
    no id.

    The result is **transient** - ``auth_log_id`` is left unset, because the engine that calls this has no row to point
    at yet - and :func:`record_outcomes` supplies it and writes the row.

    This lives in the lib layer rather than on the model on purpose: which policy fields an outcome denormalizes, and
    that a stage is identified by its threshold, is conditional-access domain knowledge. The table only has to store it.

    :param policy: the deciding policy
    :param stage: the triggered stage
    :param action_type: the action that ran. Hinted ``str`` rather than ``LockoutAction``: that enum is a ``str``
        subclass, so a member satisfies it, and it lives in the engine - which imports *this* module
    :param event_count: the count that tripped the stage
    :param dry_run: the policy was in dry run, so nothing was actually done
    :param expires_at: the expiry the action wrote, or would have written in dry run. Kept a typed parameter so call
        sites stay readable, and recorded in the row's ``info`` (see :func:`_restriction_info`); an action with nothing
        to expire simply omits it.
    """
    return ConditionalAccessOutcome(action_type=str(action_type), policy_name=policy.name,
                                    threshold=stage.failure_threshold, event_count=event_count,
                                    dry_run=dry_run, stage_name=stage.name,
                                    info=_restriction_info(expires_at))


def _restriction_info(expires_at: datetime | None) -> dict | None:
    """
    The ``info`` payload for an action that created a timed restriction, or ``None`` when there is nothing to record.

    The expiry is stored as an **aware** ISO-8601 UTC string.

    This is the one place that knows the key, so the action-specific shape of ``info`` is defined here rather than at
    each call site (see the column's comment for the rule on what may live in it).
    """
    if expires_at is None:
        return None
    aware = expires_at if expires_at.tzinfo is not None else expires_at.replace(tzinfo=timezone.utc)
    return {"expires_at": aware.isoformat()}


def record_outcomes(outcomes: Sequence[ConditionalAccessOutcome], auth_log_id: int | None) -> bool:
    """
    Record *outcomes* as the conditional-access history of the authentication-log row *auth_log_id*.

    The outcomes arrive transient, as the engine built them, and are stamped with *auth_log_id* here.

    All outcomes of one request are written as a single transaction. That does not conflict with
    :func:`~privacyidea.lib.conditional_access.session.guarded_write`'s "one write per block" rule, which exists to
    keep two row locks in different tables from being held at once: these are inserts into a single table, so there is
    no lock order to get wrong (the same reason
    :func:`~privacyidea.lib.conditional_access.authentication_log.write_authentication_events` batches its inserts).

    Writing history must never break the response that produced it, so a failure is logged and swallowed. The caller
    keeps the outcomes, which makes a later retry possible.

    Without an *auth_log_id* the outcomes are **dropped** rather than stored: every outcome belongs to the request that
    caused it, and the columns this table does not carry - the subject, the time - are only reachable through that row.
    A missing row therefore means the request never wrote one, which is either legitimate (a poll carries no
    authentication event) or a bug in the logging, and in neither case is a parentless outcome the right answer.

    :param outcomes: what the engine decided or did, in the order it happened
    :param auth_log_id: id of the request's authentication-log row
    :return: whether the outcomes are now stored (``True`` for an empty *outcomes*, nothing to do)
    """
    if not outcomes:
        return True
    if not auth_log_id:
        log.info(f"Dropping {len(outcomes)} conditional-access outcome(s): this request has no authentication-log "
                 f"row to record them against.")
        return False
    label = ("the conditional-access outcome" if len(outcomes) == 1
             else f"the {len(outcomes)} conditional-access outcomes")
    # Named `write`, not `outcome`, because `outcome` already means a conditional-access outcome in this module;
    # `write` is the database-write result.
    with guarded_write(f"{label} of authentication log entry {auth_log_id}") as write:
        for outcome in outcomes:
            outcome.auth_log_id = auth_log_id
        get_ca_session().add_all(outcomes)
    return write.succeeded


def get_outcomes(auth_log_id: int) -> Sequence[ConditionalAccessOutcome]:
    """
    Return the conditional-access outcomes recorded for one authentication-log row, oldest first.

    A single-row lookup for the CLI and the test suite. The WebUI does **not** use it: the log listing loads a whole
    page's outcomes in one batched query instead (see
    :func:`~privacyidea.lib.conditional_access.authentication_log.get_authentication_logs_paginate`), because one query
    per entry would multiply with the page size.
    """
    stmt = (select(ConditionalAccessOutcome)
            .where(ConditionalAccessOutcome.auth_log_id == auth_log_id)
            .order_by(ConditionalAccessOutcome.id))
    return get_ca_session().scalars(stmt).all()
