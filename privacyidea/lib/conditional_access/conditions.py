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

from privacyidea.lib import lazy_gettext
from privacyidea.lib.conditional_access.authentication_log import AuthLogUserRole

if TYPE_CHECKING:
    from privacyidea.lib.conditional_access.context import CAContext
    from privacyidea.models.lockout_policy import LockoutPolicy, LockoutPolicyCondition

log = logging.getLogger(__name__)


class ConditionOperator(str, Enum):
    """
    How a condition compares the value read from the request against the value
    stored on the condition.

    Only set membership exists for now, which is deliberate rather than
    provisional: every condition type currently defined reads from a closed,
    enumerable vocabulary (realm names, roles), where a multi-select of known
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
    """
    name: str
    label: object
    apply: Callable[[Any, Any], bool]
    matches_missing: bool


OPERATORS: dict[str, OperatorSpec] = {
    ConditionOperator.IN: OperatorSpec(
        name=ConditionOperator.IN,
        label=lazy_gettext("is one of"),
        apply=lambda actual, values: actual in values,
        matches_missing=False),
    ConditionOperator.NOT_IN: OperatorSpec(
        name=ConditionOperator.NOT_IN,
        label=lazy_gettext("is not one of"),
        apply=lambda actual, values: actual not in values,
        matches_missing=True),
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
    """
    name: str
    label: object
    operators: frozenset[str]
    resolve: Callable[["CAContext"], Any]
    choices: Callable[[], list[str]] | None = None


class ConditionType(str, Enum):
    """The condition types shipped today. See :data:`CONDITION_TYPES` for their specs."""
    USER_REALM = "USER_REALM"
    USER_ROLE = "USER_ROLE"

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
        choices=_realm_choices),
    ConditionType.USER_ROLE: ConditionTypeSpec(
        name=ConditionType.USER_ROLE,
        label=lazy_gettext("User role"),
        operators=frozenset({ConditionOperator.IN, ConditionOperator.NOT_IN}),
        resolve=_resolve_user_role,
        choices=lambda: sorted(AuthLogUserRole)),
}


def condition_matches(condition: "LockoutPolicyCondition", context: "CAContext",
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
    try:
        actual = spec.resolve(context)
        if actual is None:
            return operator.matches_missing
        values = condition.value if isinstance(condition.value, (list, tuple)) else []
        return operator.apply(actual, values)
    except Exception as ex:
        log.warning(f"Condition {condition.condition_type!r} of policy {policy_name!r} could not be "
                    f"evaluated: {ex!r}; treating it as not matching.")
        return False


def get_condition_types() -> dict[str, dict]:
    """
    Describe every available condition type, so the policy editor is built from
    server metadata instead of a hard-coded client-side list (mirroring
    :func:`~privacyidea.lib.conditional_access.lockout_policy.get_target_constraints`).

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


def policy_matches_context(policy: "LockoutPolicy", context: "CAContext") -> bool:
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
