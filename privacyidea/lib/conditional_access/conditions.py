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
"""
Which requests a conditional-access policy applies to.

This is the *applicability* axis of a policy, orthogonal to the counting one: the
conditions here decide **whether** a policy is evaluated for a request at all,
while the policy's counter types, count mode and stage thresholds decide **what**
trips it. Keeping them separate is what lets the two compose - a policy can
restrict itself to a realm *and* still require a threshold of failures.

A condition is a triple of *what to read* (``condition_type``), *how to compare*
(``operator``) and *what to compare against* (``value``), evaluated against the
:class:`~privacyidea.lib.conditional_access.context.CAContext` of the current
request. Two registries define the vocabulary:

* :data:`CONDITION_TYPES` - one :class:`ConditionTypeSpec` per readable value,
  declaring how to resolve it from the context and which operators it permits.
* :data:`OPERATORS` - one :class:`OperatorSpec` per comparison, including what
  that comparison means when the request carries no value.

Adding a condition kind is therefore a registry entry, not a schema change.

All of a policy's conditions must hold (AND). A policy with **no** conditions
applies to everyone, which is why introducing them leaves existing policies
behaving exactly as before.

**Missing values follow from the operator**, by treating an absent value as one
that belongs to no set: ``IN`` does not match it, ``NOT_IN`` does. This is not
configurable, and deliberately so - it is the only reading that keeps an
exemption honest. Consider an anti-enumeration policy on a source IP carrying
``USER_REALM NOT_IN [sales]`` to spare one realm: the requests it exists to stop
probe *non-existent* usernames, which resolve to no realm at all. Were a missing
value to make the condition fail, the exemption would swallow exactly the traffic
the policy was written for. Treating "no realm" as "not sales" keeps it applying.

That one rule governs **both** things a condition does, so they can never
contradict each other - but note they ask it about different subjects:

============  ======================================  =====================================
operator      gate: the *request* carries no value    count: a *log row*'s column is NULL
============  ======================================  =====================================
``IN``        no match - the policy does not apply    row is not counted
``NOT_IN``    matches - the policy applies            row is counted
============  ======================================  =====================================

:attr:`OperatorSpec.matches_missing` states it for the gate and
:attr:`OperatorSpec.sql` for the count; the second needs the null case spelled out
because SQL's three-valued logic makes ``col NOT IN (...)`` *false* for ``NULL``,
which would have inverted the exemption in the query relative to Python. So a
request the gate admits is one whose rows the filter admits - what differs is only
that the gate reads one value (this request's) while the filter reads each row's.

**Nothing here raises.** This runs on the authentication hot path, pre-auth and
post-response, and the engine is built so that conditional access can never break
an authentication. An unknown condition type, an unknown operator, or a failing
resolver is logged and treated as *not matching*, i.e. the policy does not apply.
That is the conservative reading of "this policy carries a restriction I cannot
evaluate": a policy is never applied on the strength of a condition that could not
be checked.
"""
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import or_

from privacyidea.lib import lazy_gettext
from privacyidea.lib.conditional_access.authentication_log import AuthLogUserRole
from privacyidea.models import AuthenticationLog

if TYPE_CHECKING:
    from privacyidea.lib.conditional_access.context import CAContext
    from privacyidea.models.conditional_access_policy import ConditionalAccessPolicy, ConditionalAccessPolicyCondition

log = logging.getLogger(__name__)


class ConditionOperator(str, Enum):
    """
    How a condition compares the value read from the request against the value
    stored on the condition.

    Only set membership exists for now, which is deliberate rather than
    provisional: every condition type currently defined reads from a closed,
    enumerable vocabulary (realm names, roles, endpoints), where a multi-select of known
    values beats a free-text comparator - it cannot be typo'd into a condition
    that silently never matches. Scalar comparison operators (equality, regex)
    earn their place when a condition type with an *open* value space arrives, and
    should then delegate to :func:`~privacyidea.lib.utils.compare.compare_values`
    rather than reimplement its regex and date handling.

    The names mirror that module's ``in`` / ``!in`` comparators, so the product
    speaks one vocabulary; the implementation differs because ``compare_values``
    expects its right-hand side as a comma-separated *string*, whereas a condition
    stores a JSON list.

    ``str`` is used instead of ``StrEnum`` (3.11+) for compatibility with Python
    3.10, mirroring
    :class:`~privacyidea.lib.conditional_access.authentication_event_types.AuthEventType`.
    """
    IN = "IN"
    NOT_IN = "NOT_IN"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class OperatorSpec:
    """
    One comparison a condition can use.

    :ivar name: the stored :class:`ConditionOperator` value
    :ivar label: a ``lazy_gettext`` string naming the operator for the editor
    :ivar apply: ``(actual, values) -> bool``, where *actual* is the value read
        from the request and *values* the stored list
    :ivar matches_missing: what this operator yields when the request carries no
        value at all. It follows from the operator rather than being configured,
        by treating a missing value as one that belongs to no set: it is in
        nothing (``IN`` -> False) and it is not in anything (``NOT_IN`` -> True).
        See the module docstring for why that is also the safe reading.
    :ivar sql: ``(column, values) -> ColumnElement`` - the same comparison as a SQL
        predicate, for scoping the counting query (see :func:`condition_sql_filters`).
        It must agree with :attr:`matches_missing` on a ``NULL`` column, which SQL
        does **not** give for free: ``col NOT IN (...)`` is *false* for ``NULL``
        under three-valued logic, so ``NOT_IN`` has to spell the null case out or
        the exemption would silently invert in SQL relative to Python.
    """
    name: str
    label: object
    apply: Callable[[Any, Any], bool]
    matches_missing: bool
    sql: Callable[[Any, list[str]], Any]


OPERATORS: dict[str, OperatorSpec] = {
    ConditionOperator.IN: OperatorSpec(
        name=ConditionOperator.IN,
        label=lazy_gettext("is one of"),
        apply=lambda actual, values: actual in values,
        matches_missing=False,
        # A NULL column is in nothing, and IN already excludes it.
        sql=lambda column, values: column.in_(values)),
    ConditionOperator.NOT_IN: OperatorSpec(
        name=ConditionOperator.NOT_IN,
        label=lazy_gettext("is not one of"),
        apply=lambda actual, values: actual not in values,
        matches_missing=True,
        # A NULL column is not in anything, so it must count, which plain NOT IN alone would not do (see the sql
        # docstring above).
        sql=lambda column, values: or_(column.is_(None), column.notin_(values))),
}


@dataclass(frozen=True)
class ConditionTypeSpec:
    """
    One value a condition can read from the request, and everything needed to
    evaluate, validate and display a condition on it.

    :ivar name: the stored ``condition_type`` value
    :ivar label: a ``lazy_gettext`` string naming the condition for the editor
    :ivar operators: the operators this type permits. Restricting them per type is
        what keeps a nonsensical pairing from ever being offered.
    :ivar choices: the currently valid values, for the editor's selection list and
        for write-time validation. Called per request rather than captured,
        because the vocabulary changes as realms are created and deleted.
        ``None`` for a type whose values cannot be enumerated.
    :ivar resolve: ``(context) -> value | None`` - reads this type's value
        from the request context, returning ``None`` when the request carries no
        usable value. There is no separate "absent" sentinel because there is
        nothing to distinguish it from: the request always carries a user object
        (an empty one when nothing resolved), so an unknown realm arrives as an
        empty string, not as an absent attribute - and both mean the same thing
        here. A future type whose value is legitimately falsy (a boolean) must
        return ``False`` rather than collapsing it, since the check below is
        ``is None`` and not a truthiness test. What a ``None`` then *means* is the
        operator's call, not the type's - see
        :attr:`OperatorSpec.matches_missing`.
    :ivar log_column: the ``authentication_log`` column holding the same value this
        type reads from the request, or ``None`` when there is none. It is what lets
        a condition scope the *counting* query and not just gate the request (see
        :func:`condition_sql_filters`); a type without one stays gate-only, which is
        the right default for a value the log does not record since a predicate cannot
        be written for it at all.
    """
    name: str
    label: object
    operators: frozenset[str]
    resolve: Callable[["CAContext"], Any]
    choices: Callable[[], list[str]] | None = None
    log_column: Any | None = None


class ConditionType(str, Enum):
    """The condition types shipped today. See :data:`CONDITION_TYPES` for their specs."""
    USER_REALM = "USER_REALM"
    USER_ROLE = "USER_ROLE"
    ENDPOINT = "ENDPOINT"

    def __str__(self) -> str:
        return self.value


def _resolve_user_realm(context: "CAContext") -> Any:
    """
    The realm of the authenticating user, or ``None`` when there is none to read.

    "No realm" reaches this in two shapes, both reported as ``None``: the context
    may carry no user at all (:func:`~privacyidea.api.lib.utils.build_ca_context`
    collapses an empty user object to ``None``), or a user whose realm is empty.
    Note a user is *not* empty merely because they could not be resolved - a login
    naming a realm that exists keeps that realm, which is what lets a realm
    condition still apply to an unknown username in a known realm.
    """
    user = context.user
    return user.realm if user and user.realm else None


def _resolve_user_role(context: "CAContext") -> Any:
    """The role of the authenticating principal, or ``None`` if it could not be determined."""
    return context.user_role or None


def _resolve_endpoint(context: "CAContext") -> Any:
    """The endpoint the request authenticates against, or ``None`` outside a request (see
    :func:`~privacyidea.api.lib.utils.request_endpoint`)."""
    return context.endpoint or None


# The endpoints an authentication can arrive at, i.e. the paths that record an authentication-log row. The vocabulary
# of an ENDPOINT condition and of the log's endpoint filter, so both offer a list instead of a path typed by hand that
# would silently never match.
#
# Hard-coded because it cannot be derived: whether a route authenticates is decided by it calling
# ``log_authentication``, which no registry records. **A new authenticating endpoint has to be added here**, and
# EndpointConditionChoicesTestCase asserts every path listed is a route this app actually serves, so a rename cannot
# leave a dead choice behind.
AUTHENTICATING_ENDPOINTS: tuple[str, ...] = (
    "/auth",
    "/validate/check",
    "/validate/radiuscheck",
    "/validate/triggerchallenge",
    "/validate/initialize",
    # The out-of-band push answer. The route is /ttype/<ttype>, but push is the only token type that authenticates
    # through it, so the path it is reached under is what an admin selects.
    "/ttype/push",
)


def _realm_choices() -> list[str]:
    """The currently configured realm names. Imported lazily to keep this module free of a config import cycle."""
    from privacyidea.lib.realm import get_realms
    return sorted(get_realms())


CONDITION_TYPES: dict[str, ConditionTypeSpec] = {
    ConditionType.USER_REALM: ConditionTypeSpec(
        name=ConditionType.USER_REALM,
        label=lazy_gettext("User realm"),
        operators=frozenset({ConditionOperator.IN, ConditionOperator.NOT_IN}),
        resolve=_resolve_user_realm,
        choices=_realm_choices,
        log_column=AuthenticationLog.realm),
    ConditionType.USER_ROLE: ConditionTypeSpec(
        name=ConditionType.USER_ROLE,
        label=lazy_gettext("User role"),
        operators=frozenset({ConditionOperator.IN, ConditionOperator.NOT_IN}),
        resolve=_resolve_user_role,
        choices=lambda: sorted(AuthLogUserRole),
        log_column=AuthenticationLog.user_role),
    ConditionType.ENDPOINT: ConditionTypeSpec(
        name=ConditionType.ENDPOINT,
        label=lazy_gettext("Endpoint"),
        operators=frozenset({ConditionOperator.IN, ConditionOperator.NOT_IN}),
        resolve=_resolve_endpoint,
        choices=lambda: sorted(AUTHENTICATING_ENDPOINTS),
        log_column=AuthenticationLog.endpoint),
}


def _values_are_well_formed(condition: "ConditionalAccessPolicyCondition", policy_name: str) -> bool:
    """
    Whether a stored condition's ``value`` has the shape its operator takes - today a list, for the two
    set-membership operators. Checked with the unknown-type/operator checks rather than at comparison
    time, because a malformed condition is malformed whatever the request or row carries.

    ``value`` is a JSON column, so its Python type is guaranteed by the CRUD layer and not by the schema.
    The shape accepted here is therefore exactly the one
    :func:`~privacyidea.lib.conditional_access.policy._validate_condition_value` writes - a
    **non-empty list of strings** - and nothing weaker: an empty list, or one holding non-strings,
    compares as cleanly as a well-formed one and so would pass a mere "is it a list?" test while meaning
    nothing.

    Every rejected shape has to fail the same way, and that way has to be "does not hold". The reason is
    the asymmetry of the operators: for a value no row can match, ``IN`` answers ``False`` on its own but
    ``NOT_IN`` answers ``True`` - so a corrupted exemption would silently apply to *everything* rather
    than to nothing, both gating every request and leaving every counted row in scope.

    When a scalar operator is added the accepted shape becomes operator-dependent, and this is where
    that branches - mirroring the same note on ``_validate_condition_value``.

    :param condition: the stored condition row
    :param policy_name: the owning policy's name, for the log message only
    :return: True if the value has a usable shape
    """
    value = condition.value
    if (isinstance(value, (list, tuple)) and len(value) > 0
            and all(isinstance(entry, str) for entry in value)):
        return True
    log.warning(f"Policy {policy_name!r} carries a condition whose value is not a non-empty list of "
                f"strings ({condition.condition_type!r} / {condition.operator!r}, value {value!r}); "
                f"treating it as not matching.")
    return False


def condition_matches(condition: "ConditionalAccessPolicyCondition", context: "CAContext",
                      policy_name: str = "") -> bool:
    """
    Whether a single condition holds for *context*.

    An unknown condition type or operator, or a resolver that raises, yields
    ``False`` (the policy does not apply) and is logged - see the module docstring
    for why this never raises. A value the request does not carry is answered by
    :attr:`OperatorSpec.matches_missing`, so the admin reasons about the operator
    they picked rather than a per-type rule they cannot see.

    :param condition: the stored condition row
    :param context: what is known about the request under evaluation
    :param policy_name: the owning policy's name, for log messages only
    :return: True if the condition holds
    """
    spec = CONDITION_TYPES.get(condition.condition_type)
    operator = OPERATORS.get(condition.operator)
    if spec is None or operator is None:
        log.warning(f"Policy {policy_name!r} carries a condition with an unknown type / operator "
                    f"({condition.condition_type!r} / {condition.operator!r}); treating it as not matching.")
        return False
    if not _values_are_well_formed(condition, policy_name):
        return False
    try:
        actual = spec.resolve(context)
        if actual is None:
            return operator.matches_missing
        return operator.apply(actual, condition.value)
    except Exception as ex:
        log.warning(f"Condition {condition.condition_type!r} of policy {policy_name!r} could not be "
                    f"evaluated: {ex!r}; treating it as not matching.")
        return False


def conditions_match_row(policy: "ConditionalAccessPolicy", row) -> bool:
    """
    Whether every condition of *policy* holds for a single ``authentication_log`` *row*.

    The row counterpart of :func:`policy_matches_context`, and the third place the same question is
    asked (gate: the request; scope: the counted rows). It exists for ``PER_ATTEMPT`` counting, which
    cannot use the SQL predicates of :func:`condition_sql_filters`: that counter reduces all rows
    sharing an ``attempt_id`` to the one event that classifies the attempt, and a ``WHERE`` clause
    filters rows *before* the reduction sees them. Dropping one row of an attempt corrupts the
    reduction rather than narrowing it - most sharply when the dropped row is the ``LOGIN_SUCCESS``
    that should have superseded the attempt's failures, which then counts as a failure. Applying the
    conditions to the reduced outcome row instead leaves the reduction whole and asks the question
    once, of the row that actually classifies the attempt.

    Each condition reads its own :attr:`ConditionTypeSpec.log_column` off the row, so this is the
    ``apply``/``matches_missing`` pair :func:`condition_matches` uses - not the ``sql`` pair. That is
    why ``NOT_IN`` needs no null-handling here: the missing-value rule is the operator's, applied
    directly, rather than something SQL's three-valued logic has to be talked into agreeing with.

    Fails closed like its siblings: an unknown type/operator, a type without a ``log_column``, or a
    raising comparison yields ``False`` (the row does not count) and is logged, never raises. A policy
    with no conditions matches every row.

    :param policy: the policy whose conditions are evaluated; only ``conditions`` is read
    :param row: the :class:`~privacyidea.models.AuthenticationLog` row to test
    :return: True if every condition holds for the row
    """
    for condition in policy.conditions:
        spec = CONDITION_TYPES.get(condition.condition_type)
        operator = OPERATORS.get(condition.operator)
        if spec is None or operator is None or spec.log_column is None:
            log.warning(f"Policy {policy.name!r} carries a condition that cannot be evaluated against an "
                        f"authentication-log row ({condition.condition_type!r} / {condition.operator!r}); "
                        f"treating it as not matching.")
            return False
        if not _values_are_well_formed(condition, policy.name):
            return False
        try:
            # log_column is a mapped column; .key is the attribute name holding the same value on the row.
            actual = getattr(row, spec.log_column.key)
            if actual is None:
                if not operator.matches_missing:
                    return False
                continue
            if not operator.apply(actual, condition.value):
                return False
        except Exception as ex:
            log.warning(f"Condition {condition.condition_type!r} of policy {policy.name!r} could not be "
                        f"evaluated against an authentication-log row: {ex!r}; treating it as not matching.")
            return False
    return True


def get_condition_types() -> dict[str, dict]:
    """
    Describe every available condition type, so the policy editor is built from
    server metadata instead of a hard-coded client-side list (mirroring
    :func:`~privacyidea.lib.conditional_access.policy.get_target_constraints`).

    Each entry carries the translated ``label``, the ``operators`` the type
    permits (each with its own label), and the currently valid ``choices``
    (``None`` when the values cannot be enumerated).

    ``choices`` is resolved on every call rather than cached: the realm list
    changes as realms are created and deleted, and a stale selection list would
    invite an admin to write a condition that can never match.
    """
    return {
        spec.name: {
            "label": str(spec.label),
            "operators": [{"name": OPERATORS[operator].name, "label": str(OPERATORS[operator].label)}
                          for operator in sorted(spec.operators)],
            "choices": spec.choices() if spec.choices else None,
        } for spec in CONDITION_TYPES.values()
    }


def policy_conditions_are_scopable(policy: "ConditionalAccessPolicy") -> bool:
    """
    Whether *every* condition of *policy* can be expressed as a predicate on the
    authentication log, so the policy's count can be narrowed to the rows its
    conditions describe instead of the policy merely being gated on the current
    request (see :func:`condition_sql_filters`).

    All or nothing, deliberately: a policy mixing a scopable condition with one
    that is not cannot have "half" of its conditions honoured by the query, and
    silently applying only the scopable half would count rows the admin excluded.
    Such a policy therefore stays on the gate-only path, which is the behaviour it
    had before scoping existed.

    A policy with no conditions is *not* scopable - there is nothing to scope, and
    the caller must not take the scoped path for it.

    :param policy: the policy whose conditions are inspected
    :return: True only if the policy has at least one condition and every one of
        them names a known type with a ``log_column`` and a known operator, i.e.
        :func:`condition_sql_filters` can express all of them. False means the
        count must be left unscoped.
    """
    if not policy.conditions:
        return False
    return all(
        (spec := CONDITION_TYPES.get(condition.condition_type)) is not None
        and spec.log_column is not None
        and condition.operator in OPERATORS
        for condition in policy.conditions
    )


def condition_sql_filters(policy: "ConditionalAccessPolicy") -> list:
    """
    The policy's conditions as SQL predicates on ``authentication_log``, for
    narrowing which rows a count considers.

    This is the *counting* half of a condition, applied in addition to - never
    instead of - the applicability half (:func:`policy_matches_context`). The two
    ask the same question of different subjects: gating asks it of the request in
    front of us, scoping asks it of each row of the subject's history. Both use the
    one missing-value rule, so they cannot disagree (see the module docstring).

    It is what a ``source_ip`` policy needs to count what its admin asked for: the
    subject is the IP, whose rows span many identities, realms and roles, so without
    a filter a narrowly scoped policy would still count the IP's entire history. For
    a ``user`` policy the predicates are redundant - the subject pins the realm, and
    with it the role - but harmless, which is why there is one rule for both.

    Only call this when :func:`policy_conditions_are_scopable` is true. A condition
    without a ``log_column`` is logged and skipped here rather than silently
    widening the count, but relying on that would count rows the admin excluded.

    :param policy: the policy whose conditions are translated; its ``conditions``
        relationship is read, nothing is written
    :return: one SQLAlchemy predicate per condition, to be ANDed into the counting
        query's ``WHERE``. Empty when the policy has no conditions, or when none of
        them can be expressed against the log.
    """
    filters = []
    for condition in policy.conditions:
        spec = CONDITION_TYPES.get(condition.condition_type)
        operator = OPERATORS.get(condition.operator)
        if spec is None or spec.log_column is None or operator is None:
            log.warning(f"Policy {policy.name!r} carries a condition that cannot scope a count "
                        f"({condition.condition_type!r} / {condition.operator!r}); it is not applied to the query.")
            continue
        values = condition.value if isinstance(condition.value, (list, tuple)) else []
        filters.append(operator.sql(spec.log_column, list(values)))
    return filters


def policy_matches_context(policy: "ConditionalAccessPolicy", context: "CAContext") -> bool:
    """
    Whether *policy* applies to the request described by *context* at all.

    Every condition must hold (AND); a policy with no conditions applies to
    everyone. The engine calls this before counting anything, so a policy that
    does not apply costs no database work.

    :param policy: the policy whose conditions are checked
    :param context: what is known about the request under evaluation
    :return: True if the policy applies to this request
    """
    return all(condition_matches(condition, context, policy.name)
               for condition in policy.conditions)
