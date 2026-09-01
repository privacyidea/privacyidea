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

from sqlalchemy import Boolean, ForeignKey, Identity, Index, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db
from privacyidea.models.utils import BigIntegerType, case_sensitive_unicode

# Maximum length of the string columns; the lib layer truncates values to these lengths before insert (see
# privacyidea.lib.conditional_access.outcome_log), the same contract as authentication_log_column_length.
#
# Each length matches the column the value is copied from, so a name that fits the policy configuration always
# fits here.
conditional_access_outcome_column_length = {
    # Mirrors conditional_access_stage_actions.action_type, whose vocabulary (ConditionalAccessAction) this column
    # stores.
    "action_type": 100,
    # Mirror conditional_access_policies.name and conditional_access_policy_stages.name.
    "policy_name": 255,
    "stage_name": 255,
}


class ConditionalAccessOutcome(db.Model):
    """
    History of what conditional access *did*: one row per action the engine executed for one request, plus dry-run
    rows recording what a dry-run policy *would* have done.

    This is the queryable counterpart of the live state in ``user_lock_state`` and ``block_list``, which show the
    restriction currently in force and then forget it. Only this table can answer "when was this user locked, by which
    policy, and for how long".

    Each row belongs to the ``authentication_log`` row of the request that caused it (``auth_log_id``, mandatory) and is
    only ever read together with it. The table therefore holds **only what it alone knows**: the subject (resolver, uid,
    realm, username, source IP) and *when* it happened are on the parent row and are not repeated here. Using the
    parent's ``timestamp`` is exact enough by construction - the engine evaluates a request against a single reference
    instant, so every outcome of one request shares it, a few milliseconds after the row itself was written.

    "Read together with" is a batched second ``SELECT`` (``selectinload``), not a ``JOIN``: the log listing pages the
    parent rows and then fetches ``WHERE auth_log_id IN (<the page's ids>)``. A join would multiply each parent row by
    its outcomes and break both ``LIMIT`` and the pagination count.

    Nothing on the authentication path ever reads this table - the engine counts over ``authentication_log`` and writes
    outcomes without reading them back - so the relationship that exposes them is declared ``lazy="raise"`` and only
    the paginated log query opts in.

    The policy is identified by **name only**, denormalized, with no id and no foreign key: an outcome must survive the
    deletion of the policy that produced it, and a stored ``policy_id`` could not be acted on afterwards. Ids are not
    reused on PostgreSQL or Oracle (a sequence), but SQLite hands out ``max(rowid)+1`` and MySQL/MariaDB recompute the
    ``AUTO_INCREMENT`` counter as ``max(id)+1`` on restart (MySQL persists it only from 8.0), so a deleted policy's id
    can turn up on a *different* policy - and finding the logged id on a policy with another name is indistinguishable
    from a rename, which is the one case an id was worth keeping for. Matching on the name an admin chose can at worst
    hit a policy deliberately recreated under that name; matching on a recycled surrogate key attributes history to a
    policy that never produced it.

    Whether the policy still exists is therefore a lookup by name (unique on ``conditional_access_policies``).
    ``auth_log_id``, in contrast, is a real foreign key and cascades: the history of a request is deleted with the
    request.

    There is deliberately **no stage id**:
    :func:`~privacyidea.lib.conditional_access.policy.update_conditional_access_policy` replaces a policy's stages as a
    whole, so every edit gives them fresh ids and a stored one would dangle. The stage is identified by its natural key
    instead: a stage is unique per policy by its threshold (``uq_ca_stage_policy_threshold``) and that survives
    edits, and the threshold is what a human reads anyway.

    Everything a triggered stage knows is therefore mandatory - ``policy_name``, ``threshold``, ``event_count`` -
    because the engine always has all three when it records an outcome. Only two columns are nullable,
    each meaning something: ``stage_name`` (the admin never named the stage) and ``info`` (the action had nothing of its
    own to record).

    The string columns use :func:`~privacyidea.models.utils.case_sensitive_unicode` for the same reason the
    authentication log does: matching must behave **identically on every backend**. MySQL/MariaDB's server-default
    collation is typically case-insensitive (``*_ci``) while SQLite, PostgreSQL and Oracle compare case-sensitively, so
    an unpinned column would make ``action_type == "lock_user"`` match on one database and not on another.

    Deliberately **without** :class:`~privacyidea.models.utils.MethodsMixin`, unlike its sibling models: the mixin's
    ``save()`` and ``delete()`` commit ``db.session``, and an outcome must be written on the conditional-access session
    so that a failure to record history cannot roll back the request's own work. Rows are created by
    :func:`~privacyidea.lib.conditional_access.outcome_log.record_outcomes` and removed with their parent by the
    authentication log's delete paths; not offering the two methods is cheaper than documenting that they are wrong.
    """
    __tablename__ = "conditional_access_outcome"
    __table_args__ = (
        # The join that decorates an authentication-log page (this table's whole purpose) and the lookup
        # the delete paths use to remove a request's outcomes with it.
        Index("ix_ca_outcome_authlog", "auth_log_id"),
        # The action-first history query ("every lock", "every email sent"); a time range comes from
        # joining the parent, where the timestamp lives.
        Index("ix_ca_outcome_action", "action_type"),
    )
    # The database generates the id (Oracle/PostgreSQL IDENTITY, MySQL/MariaDB AUTO_INCREMENT, SQLite's
    # rowid alias), so the type stays BigIntegerType: SQLite only aliases rowid for exactly "INTEGER
    # PRIMARY KEY", rendering INTEGER there and BIGINT elsewhere.
    id: Mapped[int] = mapped_column(BigIntegerType, Identity(always=False), primary_key=True)
    # The request this outcome belongs to; mandatory, since an outcome with no request is meaningless, and
    # the subject and time this table lacks are only reachable through it.
    auth_log_id: Mapped[int] = mapped_column(BigIntegerType,
                                             ForeignKey("authentication_log.id", ondelete="CASCADE"),
                                             nullable=False)
    # A ConditionalAccessAction value: the action that ran (LOCK_USER, BLOCK_IP, EMAIL_*, ...) or the pre-auth
    # decision (DENY).
    action_type: Mapped[str] = mapped_column(
        case_sensitive_unicode(conditional_access_outcome_column_length["action_type"]), nullable=False)
    # The policy was in dry run: nothing was actually done and this row says what would have happened.
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # The policy's name at the time, and its only identifier here.
    policy_name: Mapped[str] = mapped_column(
        case_sensitive_unicode(conditional_access_outcome_column_length["policy_name"]), nullable=False)
    # The triggered stage's threshold: with the policy it is the stage's natural key, and alone it is how a
    # human names the stage ("the threshold-5 one").
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    # The count that tripped the stage, i.e. how far past its threshold the subject was.
    event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # Only set when an admin named the stage; the threshold identifies it either way.
    stage_name: Mapped[str | None] = mapped_column(
        case_sensitive_unicode(conditional_access_outcome_column_length["stage_name"]))
    # Whatever the action has to say about itself, or NULL when it has nothing. A timed LOCK_USER / BLOCK_IP records
    # ``{"expires_at": "<ISO-8601 UTC>"}`` - the only surviving record of how long the restriction lasted once the
    # state row is gone; PERMANENT_* has no expiry by definition, and EMAIL_* / DENY create no restriction at all.
    #
    # Deliberately a JSON bag, not one column per action type: with seven action types and more to come, a per-type
    # column would be mostly NULL, and every new action would need a migration to record its detail.
    info: Mapped[dict | None] = mapped_column(JSON)

    def to_dict(self) -> dict:
        """
        Serialize the outcome for the API response.

        Every column is emitted, including the ones the WebUI does not display (``info``, ``event_count``): what to show
        is the view's decision, and a client querying the history needs the rest. There is no timestamp of its own - the
        entry this is nested under carries it.
        """
        return {name: getattr(self, name) for name in self.__table__.columns.keys()}
