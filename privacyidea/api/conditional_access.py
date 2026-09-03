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
REST API for conditional-access policies (admin only).

These endpoints are the write path for the policies evaluated by
:mod:`privacyidea.lib.conditional_access.engine`. All business logic and
validation lives in :mod:`privacyidea.lib.conditional_access.policy`;
this module only parses the request and writes the audit log.

The blueprint is registered under ``/conditionalaccess`` and runs behind
``admin_required`` (see :mod:`privacyidea.api.before_after`), so the live
lock/block state managed by ``pi-manage conditionalaccess`` stays reachable
even if these endpoints are locked down by policy.
"""
import json
import logging

from flask import Blueprint, request, g

from privacyidea.api.auth import admin_required
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.api.lib.utils import send_result, to_list_param
from privacyidea.lib.conditional_access.authentication_event_types import TRACKABLE_EVENT_TYPES
from privacyidea.lib.conditional_access.engine import ConditionalAccessAction
from privacyidea.lib.conditional_access.policy import (list_conditional_access_policies,
                                                               get_conditional_access_policy,
                                                               create_conditional_access_policy,
                                                               update_conditional_access_policy,
                                                               delete_conditional_access_policy,
                                                               reorder_conditional_access_policies,
                                                               get_target_constraints,
                                                               get_default_error_messages)
from privacyidea.lib.conditional_access.conditions import get_condition_types
from privacyidea.lib.conditional_access.policy_template import list_conditional_access_policy_templates
from privacyidea.lib.conditional_access.state import (list_locked_users_paginate, DEFAULT_PAGE_SIZE,
                                                              user_matches_scopes, get_user_lock_dict,
                                                              purge_expired_user_locks, unlock_user_by_id,
                                                              unlock_user_by_username, lock_user, block_ip,
                                                              list_blocklist, purge_expired_blocklist,
                                                              remove_blocklist_entry)
from privacyidea.lib.error import ParameterError, PolicyError
from privacyidea.lib.log import log_with
from privacyidea.lib.params import get_optional, get_required, get_required_one_of
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.helper import get_policy_visibility_scopes
from privacyidea.lib.user import User
from privacyidea.lib.utils import is_true

log = logging.getLogger(__name__)

conditional_access_blueprint = Blueprint('conditional_access_blueprint', __name__)


def _get_json_param(params: dict, name: str, required: bool = False):
    """
    Read a structured parameter (list/dict) from the request data.

    With a JSON request body the value already arrives as a list/dict; with a
    form-encoded request it arrives as a JSON string, which is decoded here. A
    malformed string raises :class:`ParameterError` naming the parameter.
    """
    value = get_required(params, name) if required else get_optional(params, name)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ParameterError(f"'{name}' must be valid JSON.")
    return value


def _duration_param(params: dict) -> int | None:
    """
    Parse the optional ``duration_seconds`` of a manual lock or block, or ``None`` when it is absent.

    A form-encoded request delivers the duration as a string, so a string is cast here. Anything else is
    passed through untouched, so that whether a value is an acceptable duration is decided in exactly one
    place: the positive-integer check in
    :func:`~privacyidea.lib.conditional_access.state._restriction_expiry`. Casting first would defeat it -
    ``int()`` turns JSON's ``true`` into a one-second restriction and truncates ``3.9`` to three seconds,
    both of which that check refuses when it gets to see the original value.
    """
    value = get_optional(params, "duration_seconds")
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            raise ParameterError("'duration_seconds' must be a positive number of seconds.")
    return value


def _int_param(value, default: int) -> int:
    """Parse an optional integer query parameter, falling back to *default* when
    it is absent or not a valid integer (lenient — pagination should not 400)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _int_policy_id(policy_id) -> int:
    """
    Parse the policy id route parameter. A string route converter is used
    (matching the other privacyIDEA APIs) because ``get_all_params`` unquotes
    all view args as strings; a non-numeric id is a clean ParameterError.
    """
    try:
        return int(policy_id)
    except (TypeError, ValueError):
        raise ParameterError(f"Invalid policy id '{policy_id}'.")


@conditional_access_blueprint.route('eventtypes', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_READ)
@log_with(log)
def list_event_types():
    """
    Return the authoritative list of authentication event types a policy can
    track, so the WebUI does not duplicate the list and automatically picks up
    newly added types.

    This is the **trackable** subset of :class:`AuthEventType`: the types
    conditional access writes for its own rejections are left out, because a
    policy counting them would let a lock feed itself (see
    :data:`~privacyidea.lib.conditional_access.authentication_event_types.CA_ENFORCEMENT_EVENT_TYPES`).
    The authentication log's own ``/authentication_log/eventtypes`` still lists
    every type, since an admin must be able to filter for a rejection.

    Requires the admin policy action :ref:`policy_conditional_access_policy_read`.

    :status 200: list of event-type name strings in ``result.value``, in definition order
    """
    event_types = [event_type.value for event_type in TRACKABLE_EVENT_TYPES]
    g.audit_object.log({"success": True, "info": f"{len(event_types)} event types"})
    return send_result(event_types)


@conditional_access_blueprint.route('actiontypes', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_READ)
@log_with(log)
def list_action_types():
    """
    Return the authoritative list of stage action types (the
    :class:`ConditionalAccessAction` values), so the WebUI does not duplicate the list and
    automatically picks up newly added actions.

    Requires the admin policy action :ref:`policy_conditional_access_policy_read`.

    :status 200: list of action-type name strings in ``result.value``, in definition order
    """
    action_types = [action.value for action in ConditionalAccessAction]
    g.audit_object.log({"success": True, "info": f"{len(action_types)} action types"})
    return send_result(action_types)


@conditional_access_blueprint.route('defaulterrormessages', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_READ)
@log_with(log)
def list_default_error_messages():
    """
    Return the suggested error message for a stage's ``error_message``, per stage action, as
    ``[{"action_type": ..., "message": ...}]`` **ordered most severe first** (see
    :func:`~privacyidea.lib.conditional_access.policy.get_default_error_messages`).

    An authoring aid for the policy editor, which composes one suggestion for a stage carrying several actions:
    one sentence per action, kept in the order given. The order is the whole rule, because it is the same
    concatenation the runtime performs - a request reports one sentence per thing that happened to it, ranked the
    same way - so a client needs nothing beyond this list to offer the wording a user would be shown. An action
    that rejects nothing has no entry, there being nothing to say for it.

    The same wording is what the ``show_default_ca_error_message`` policy falls back to at runtime for a stage
    that carries no ``error_message`` of its own, so an admin who edits a suggestion is editing the thing they
    would otherwise have got by default. Without that policy a stage without an ``error_message`` reveals
    nothing to the user, whatever its actions.

    Requires the admin policy action :ref:`policy_conditional_access_policy_read`.

    :status 200: list of ``{"action_type", "message"}`` objects, most severe first
    """
    default_error_messages = get_default_error_messages()
    g.audit_object.log({"success": True})
    return send_result(default_error_messages)


@conditional_access_blueprint.route('conditiontypes', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_READ)
@log_with(log)
def list_condition_types():
    """
    Return the available policy condition types with, for each, its translated
    label, the operators it permits and the currently valid values - so the policy
    editor is built from server metadata rather than a duplicated client-side list.

    ``choices`` is resolved per call, so a realm created or deleted since the last
    request is reflected immediately.

    Requires the admin policy action :ref:`policy_conditional_access_policy_read`.

    :status 200: mapping of condition type to its metadata in ``result.value``
    """
    condition_types = get_condition_types()
    g.audit_object.log({"success": True, "info": f"{len(condition_types)} condition types"})
    return send_result(condition_types)


@conditional_access_blueprint.route('targets', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_READ)
@log_with(log)
def list_targets():
    """
    Return the policy targets and, for each, the constraints that depend on the target - the stage actions it allows
    and the count modes it supports - as ``{target: {"actions": [...], "count_modes": [...]}}`` (both sorted; see
    :func:`~privacyidea.lib.conditional_access.policy.get_target_constraints`).

    Requires the admin policy action :ref:`policy_conditional_access_policy_read`.

    :status 200: mapping of target name to its allowed actions and supported count modes
    """
    target_constraints = get_target_constraints()
    g.audit_object.log({"success": True, "info": f"{len(target_constraints)} targets"})
    return send_result(target_constraints)


@conditional_access_blueprint.route('policy', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_READ)
@log_with(log)
def list_policies():
    """
    Return all conditional-access policies with their stages and
    actions, ordered by ascending priority (the engine's evaluation order: a
    lower priority number means higher precedence).

    Requires the admin policy action :ref:`policy_conditional_access_policy_read`.

    :query enabled: if given, only return policies whose enabled state matches
        this boolean.
    :status 200: list of policy dicts in ``result.value``
    """
    enabled = get_optional(request.all_data, "enabled")
    if enabled is not None:
        enabled = is_true(enabled)
    policies = list_conditional_access_policies(enabled=enabled)
    g.audit_object.log({"success": True, "info": f"{len(policies)} policies"})
    return send_result(policies)


@conditional_access_blueprint.route('policy/<policy_id>', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_READ)
@log_with(log)
def get_policy(policy_id):
    """
    Return a single conditional-access policy with its stages and
    actions.

    Requires the admin policy action :ref:`policy_conditional_access_policy_read`.

    :status 200: the policy dict in ``result.value``
    :status 404: no policy with this id exists
    """
    policy = get_conditional_access_policy(_int_policy_id(policy_id))
    g.audit_object.log({"success": True, "info": f"policy {policy_id}"})
    return send_result(policy)


@conditional_access_blueprint.route('template', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_READ)
@log_with(log)
def list_templates():
    """
    Return the whole shipped conditional-access policy template catalog in one call. Each
    entry is ``{"key", "description", "policy"}`` where ``policy`` is a payload
    ready to be prefilled, edited and POSTed to
    :http:post:`/conditionalaccess/policy`.

    Requires the admin policy action :ref:`policy_conditional_access_policy_read`.

    :status 200: the list of template entries in ``result.value``
    """
    templates = list_conditional_access_policy_templates()
    g.audit_object.log({"success": True, "info": f"{len(templates)} templates"})
    return send_result(templates)


@conditional_access_blueprint.route('policy', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_WRITE)
@log_with(log)
def create_policy():
    """
    Create a conditional-access policy with its stages and actions.

    Requires the admin policy action :ref:`policy_conditional_access_policy_write`.

    :jsonparam name: unique policy name. Required.
    :jsonparam time_window_seconds: sliding window (in seconds) over which the
        tracked failures are counted. Required, positive integer.
    :jsonparam count_mode: how the tracked counters are counted against the
        thresholds; valid values depend on ``target`` - a ``user`` policy uses
        ``PER_REQUEST`` (per authentication_log row) or ``PER_ATTEMPT`` (per whole
        authentication attempt), a ``source_ip`` policy uses ``DISTINCT_USERS``
        (distinct targeted accounts). Optional; defaults to the target's default
        (``PER_REQUEST`` for ``user``, ``DISTINCT_USERS`` for ``source_ip``).
    :jsonparam counter_types_to_track: non-empty list of authentication event
        types (e.g. ``["PIN_FAIL", "MFA_FAIL"]``) counted together against the
        stage thresholds. Required.
    :jsonparam stages: non-empty list of stage definitions, each
        ``{"failure_threshold": <int>, "name": <str, optional>,
        "actions": [{"action_type": <ConditionalAccessAction>, "action_value": <per action type>}]}``.
        Thresholds must be unique within the policy and are the evaluation order
        (highest first). A threshold starts at 1, except on a stage whose every
        action is ``DENY``, where 0 means "always". Required. ``action_value`` is checked against what the
        action can actually do: ``LOCK_USER``/``BLOCK_IP`` need a positive number of seconds (an integer, a
        numeric string, or an object with ``duration_seconds``), ``EMAIL_ADMIN``/``EMAIL_USER`` an object with
        a non-empty ``subject`` and ``body``, and the ``PERMANENT_*``/``DENY`` actions no value at all.
    :jsonparam enabled: whether the policy is evaluated (default true).
    :jsonparam dry_run: log-only mode, nothing is enforced (default false).
    :jsonparam reset_on_success: whether a completed login clears the events
        counted for this policy, so the thresholds apply to consecutive failures
        since that login (default true), including for the pre-auth DENY
        decision. Only a ``user`` target resets: a ``source_ip`` policy
        aggregates across accounts and never does, so sending it as true with
        that target is a 400.
    :jsonparam priority: evaluation priority; lower numbers are evaluated first.
        Required and must be unique across policies (no default).
    :jsonparam target: the identity the policy counts and acts on - ``user``
        (per-user brute force) or ``source_ip`` (password spraying). Required.
    :jsonparam conditions: list of conditions restricting which requests the
        policy applies to, each ``{"condition_type": <ConditionType>,
        "operator": "IN"|"NOT_IN", "value": [<str>, ...]}``. All of them must
        hold. Optional; omitted or empty, the policy applies to every request.
        See :http:get:`/conditionalaccess/conditiontypes` for the available types
        and their valid values.
    :status 200: the id of the new policy in ``result.value``
    :status 400: invalid or missing parameter, including an ``action_value`` the named action
        could not act on
    """
    params = request.all_data
    name = get_required(params, "name")
    enabled = get_optional(params, "enabled")
    dry_run = get_optional(params, "dry_run")
    reset_on_success = get_optional(params, "reset_on_success")
    policy_id = create_conditional_access_policy(
        name=name,
        time_window_seconds=get_required(params, "time_window_seconds"),
        counter_types_to_track=_get_json_param(params, "counter_types_to_track", required=True),
        stages=_get_json_param(params, "stages", required=True),
        conditions=_get_json_param(params, "conditions"),
        enabled=is_true(enabled) if enabled is not None else True,
        dry_run=is_true(dry_run) if dry_run is not None else False,
        reset_on_success=is_true(reset_on_success) if reset_on_success is not None else None,
        priority=get_required(params, "priority"),
        count_mode=get_optional(params, "count_mode"),
        target=get_required(params, "target"))
    g.audit_object.log({"success": True, "info": f"created policy '{name}' (id {policy_id})"})
    return send_result(policy_id)


@conditional_access_blueprint.route('policy/<policy_id>', methods=['PATCH'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_WRITE)
@log_with(log)
def update_policy(policy_id):
    """
    Partially update a conditional-access policy. Only the given
    parameters are changed and all others are left untouched;
    ``counter_types_to_track``, ``stages`` and ``conditions`` are replaced as a
    whole when given - sending ``{"conditions": []}`` therefore removes every
    condition and widens the policy to all requests. Enabling or disabling a
    policy is done through this endpoint by sending ``{"enabled": true}`` /
    ``{"enabled": false}``.

    Requires the admin policy action :ref:`policy_conditional_access_policy_write`.
    Parameters are as for creating a policy, all optional. ``target`` may be
    changed, but the resulting target/action combination must stay compatible
    (otherwise a 400).

    :status 200: the id of the updated policy in ``result.value``
    :status 400: invalid parameter
    :status 404: no policy with this id exists
    """
    params = request.all_data
    enabled = get_optional(params, "enabled")
    dry_run = get_optional(params, "dry_run")
    reset_on_success = get_optional(params, "reset_on_success")
    policy_id = _int_policy_id(policy_id)
    policy_id, changed_fields = update_conditional_access_policy(
        policy_id,
        name=get_optional(params, "name"),
        time_window_seconds=get_optional(params, "time_window_seconds"),
        counter_types_to_track=_get_json_param(params, "counter_types_to_track"),
        stages=_get_json_param(params, "stages"),
        conditions=_get_json_param(params, "conditions"),
        enabled=is_true(enabled) if enabled is not None else None,
        dry_run=is_true(dry_run) if dry_run is not None else None,
        reset_on_success=is_true(reset_on_success) if reset_on_success is not None else None,
        priority=get_optional(params, "priority"),
        target=get_optional(params, "target"),
        count_mode=get_optional(params, "count_mode"))
    g.audit_object.log({"success": True,
                        "info": f"updated policy {policy_id} "
                                f"({', '.join(changed_fields) or 'no fields'})"})
    return send_result(policy_id)


@conditional_access_blueprint.route('policy/order', methods=['PUT'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_WRITE)
@log_with(log)
def reorder_policies():
    """
    Rearrange the evaluation order of conditional-access policies.

    The listed policies take the priority values this same set of policies
    already holds, in ascending order: the first id gets the lowest of those
    values (highest precedence), the last the highest. Only the ownership of the
    values changes, so no policy is renumbered and whatever numbering scheme the
    admin uses is preserved.

    Any subset may be sent and unlisted policies keep their priority, so a swap
    sends two ids and a full rearrangement sends all of them. Sending an
    already-sorted order is a no-op, so the request is idempotent.

    Requires the admin policy action :ref:`policy_conditional_access_policy_write`.

    :jsonparam policy_ids: the policies to rearrange, as a list of ids in the
        wanted evaluation order (highest precedence first). Required, non-empty
        and without duplicates.
    :jsonparam expected_priorities: optional per-policy assertion, one entry per
        id in the same order: the priority the client last saw that policy hold.
        Given it, a concurrent rearrangement is reported as a 409 instead of
        silently overwriting the other admin's order. Since it covers only the
        submitted policies, it conflicts solely when a policy this request moves
        was changed elsewhere.
    :status 200: ``true`` in ``result.value``; fetch ``GET /policy`` for the new order
    :status 400: ``policy_ids`` is missing, empty or contains a duplicate, or
        ``expected_priorities`` does not have one entry per id
    :status 404: one of the ids does not exist
    :status 409: a policy no longer holds its asserted priority
    """
    params = request.all_data
    policy_ids = _get_json_param(params, "policy_ids", required=True)
    old_priorities = _get_json_param(params, "expected_priorities")
    reorder_conditional_access_policies(policy_ids, old_priorities)
    g.audit_object.log({"success": True})
    return send_result(True)


@conditional_access_blueprint.route('policy/<policy_id>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_POLICY_WRITE)
@log_with(log)
def delete_policy(policy_id):
    """
    Delete a conditional-access policy with all its stages and actions.
    Existing locks and blocks written by the policy stay in force.

    Requires the admin policy action :ref:`policy_conditional_access_policy_write`.

    :status 200: the id of the deleted policy in ``result.value``
    :status 404: no policy with this id exists
    """
    delete_conditional_access_policy(_int_policy_id(policy_id))
    g.audit_object.log({"success": True, "info": f"deleted policy {policy_id}"})
    return send_result(policy_id)


@conditional_access_blueprint.route('lock/users', methods=['GET'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.USER_LOCK_READ)
@log_with(log)
def get_locked_users():
    """
    List the locked users, paginated. By default every record is returned — locks still in
    force *and* stale rows whose timed lock has already expired; each row carries the expiry
    fields so the caller can tell them apart, and ``states`` narrows to a subset. Results are
    constrained to the admin's policy visibility scope (the realm / resolver / user
    conditions on the ``user_lock_read`` policies), mirroring the authentication log.

    Requires the admin policy action :ref:`policy_user_lock_read`.

    The ``realms`` / ``resolvers`` / ``usernames`` / ``error_messages`` filters accept a comma-separated list
    and a ``*`` wildcard per value (matched with ``LIKE``); with ``case_insensitive``
    the plain values match case-insensitively too. These search filters are applied on
    top of — and never widen — the visibility scope.

    :query realms: realm(s) to filter by
    :query resolvers: resolver(s) to filter by
    :query usernames: login(s) to filter by
    :query error_messages: message text to filter by - the error message stored on the lock, i.e. what those users
        are actually shown
    :query states: lock state(s) to include — any of ``permanent``, ``temporary``,
        ``expired`` (comma-separated). Any other value is a ``ParameterError``.
    :query causes: lock cause(s) to include — any of ``POLICY``, ``MANUAL``
        (comma-separated). Any other value is a ``ParameterError``.
    :query case_insensitive: match the filter values case-insensitively
    :query page: page number, 1-indexed (default 1)
    :query page_size: entries per page (default 15)
    :query sort_column: one of username, realm, resolver, lock_expires_at, lock_cause, locked_at
    :query sort_order: ``asc`` or ``desc`` (default desc)
    :status 200: ``{locked_users, count, current, prev, next}`` in ``result.value``
    """
    params = request.all_data
    visibility_scopes = get_policy_visibility_scopes(PolicyAction.USER_LOCK_READ)
    page = list_locked_users_paginate(
        realms=to_list_param(get_optional(params, "realms")),
        resolvers=to_list_param(get_optional(params, "resolvers")),
        usernames=to_list_param(get_optional(params, "usernames")),
        error_messages=to_list_param(get_optional(params, "error_messages")),
        states=to_list_param(get_optional(params, "states")),
        causes=to_list_param(get_optional(params, "causes")),
        case_insensitive=is_true(get_optional(params, "case_insensitive")),
        visibility_scopes=visibility_scopes,
        page=_int_param(get_optional(params, "page"), 1),
        page_size=_int_param(get_optional(params, "page_size"), DEFAULT_PAGE_SIZE),
        sort_column=get_optional(params, "sort_column") or "locked_at",
        sort_order=get_optional(params, "sort_order") or "desc")
    g.audit_object.log({"success": True, "info": f"{page['count']} locked user(s)"})
    return send_result(page)


@conditional_access_blueprint.route('lock/user', methods=['GET'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.USER_LOCK_READ)
@log_with(log)
def get_user_lock():
    """
    Return the current lock of a single user (or ``null`` if not locked).
    Constrained to the admin's policy visibility scope.

    Requires the admin policy action :ref:`policy_user_lock_read`.

    One user identifier is required: user or user_id

    :query user: login of the user to look up.
    :query user_id: user id of the user to look up. Requires ``resolver``: a uid is only
        unique within its resolver, so a user object cannot be built from a uid alone.
    :query realm: realm of the user
    :query resolver: resolver of the user; optional alongside ``user``, required with ``user_id``
    :status 200: the user's lock dict, or ``null``, in ``result.value``
    """
    get_required_one_of(request.all_data, ["user", "user_id"])
    user_id = get_optional(request.all_data, "user_id")
    username = get_optional(request.all_data, "user")
    realm = get_required(request.all_data, "realm")
    resolver = get_optional(request.all_data, "resolver")
    if user_id is not None and not resolver:
        # User() refuses a uid without a resolver (a uid is only unique per resolver), even when a username is
        # also given: the two are not cross-checked against each other, so the uid alone still needs its
        # resolver to be unambiguous. Reject it here so the caller gets a ParameterError instead of a
        # UserError from deep inside the resolver lookup.
        raise ParameterError("The parameter 'resolver' is required when looking a user up by 'user_id'.")
    visibility_scopes = get_policy_visibility_scopes(PolicyAction.USER_LOCK_READ)

    user = User(uid=user_id, login=username, realm=realm, resolver=resolver)

    value = None
    if not user.is_empty() and user.exist() and user_matches_scopes(user, visibility_scopes):
        value = get_user_lock_dict(user)
    g.audit_object.log({"success": True, "user": user.login, "realm": user.realm, "resolver": user.resolver})
    return send_result(value)


@conditional_access_blueprint.route('lock/user', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.USER_LOCK_SET)
@log_with(log)
def set_user_lock():
    """
    Lock a single user by administrator decision, replacing whatever lock is currently on record, and return
    the new lock.

    This is the manual counterpart of what a ``LOCK_USER`` policy action does, and it is enforced by exactly
    the same pre-check: the lock is recorded with the cause ``MANUAL`` so the two can be told apart on the
    Locked Users page, but nothing in the authentication path treats it differently. Unlike a policy lock it
    is authoritative - it replaces a stronger lock rather than declining as a weakening.

    Requires the admin policy action :ref:`policy_user_lock_set`, which is deliberately separate from
    ``user_lock_reset``: clearing a restriction is recoverable, imposing one is not.

    One user identifier is required: user or user_id

    :jsonparam user: login of the user to lock.
    :jsonparam user_id: user id of the user to lock. Requires ``resolver``: a uid is only unique within its
        resolver, so a user object cannot be built from a uid alone.
    :jsonparam realm: realm of the user. Required.
    :jsonparam resolver: resolver of the user; optional alongside ``user``, required with ``user_id``
    :jsonparam duration_seconds: how long the lock lasts. Omitted, the lock is permanent and lifts only when
        an admin unlocks the user - which is the usual intent when locking by hand.
    :status 200: the new lock dict in ``result.value``
    :status 400: invalid or missing parameter, or an unresolvable user
    :status 403: the user is outside the admin's policy visibility scope
    """
    params = request.all_data
    get_required_one_of(params, ["user", "user_id"])
    user_id = get_optional(params, "user_id")
    username = get_optional(params, "user")
    realm = get_required(params, "realm")
    resolver = get_optional(params, "resolver")
    if user_id is not None and not resolver:
        # User() refuses a uid without a resolver (a uid is only unique per resolver), even when a username is
        # also given: the two are not cross-checked against each other, so the uid alone still needs its
        # resolver to be unambiguous. Reject it here so the caller gets a ParameterError instead of a
        # UserError from deep inside the resolver lookup.
        raise ParameterError("The parameter 'resolver' is required when looking a user up by 'user_id'.")
    duration_seconds = _duration_param(params)

    # Build a minimal User object from request parameters only; scope authorization must not disclose
    # whether the user exists. Perform the scope check before attempting to resolve existence.
    user = User(uid=user_id, login=username, realm=realm, resolver=resolver)
    if not user_matches_scopes(user, get_policy_visibility_scopes(PolicyAction.USER_LOCK_SET)):
        # Do not include resolved identifiers; echo only the provided parameters. `username` and
        # `user_id` are checked with `is not None`, not truthiness, so a uid of 0 is not mistaken for
        # "neither was given".
        target = username if username is not None else (user_id if user_id is not None else "<unspecified>")
        raise PolicyError(f"You are not allowed to lock the requested user '{target}' in realm '{realm}'.")

    # Now it is safe to resolve and validate the user existence
    if user.is_empty() or not user.exist():
        raise ParameterError("The requested user does not exist.")

    lock = lock_user(user, duration_seconds=duration_seconds)
    g.audit_object.log({"success": True,
                        "user": user.login, "realm": user.realm, "resolver": user.resolver,
                        "info": f"locked {user.login}@{user.realm} "
                                f"({'permanent' if duration_seconds is None else f'{duration_seconds}s'})"})
    return send_result(lock)


@conditional_access_blueprint.route('lock/users/purge', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.USER_LOCK_RESET)
@log_with(log)
def purge_user_locks():
    """
    Delete stale user-lock records (expired or already-unlocked rows).

    Requires the admin policy action :ref:`policy_user_lock_reset`. Constrained to
    the admin's policy visibility scope: a scoped admin only purges the stale rows
    inside their realm / resolver / user boundary.

    :status 200: the number of rows removed, in ``result.value``
    """
    visibility_scopes = get_policy_visibility_scopes(PolicyAction.USER_LOCK_RESET)
    count = purge_expired_user_locks(visibility_scopes=visibility_scopes)
    g.audit_object.log({"success": True, "info": f"purged {count} stale user lock(s)"})
    return send_result(count)


@conditional_access_blueprint.route('lock/user', methods=['DELETE'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.USER_LOCK_RESET)
@log_with(log)
def reset_user_lock():
    """
    Reset (unlock) a user's conditional-access lock. Identified by either the
    login (``user``) or the resolver-local id (``user_id``); ``realm`` is
    required and ``resolver`` is optional — it only narrows the match.
    Omitting it clears every matching lock in the realm.

    Requires the admin policy action :ref:`policy_user_lock_reset`. Constrained to
    the admin's policy visibility scope (the realm / resolver / user conditions on the
    ``user_lock_reset`` policies), mirroring the read endpoints. The boundary is part
    of the delete criterion, so a call that matches several rows only clears the ones
    inside the scope, and a target outside it is indistinguishable from an absent lock
    (both return ``false``).

    One user identifier is required: user or user_id

    :jsonparam user: login of the user to unlock.
    :jsonparam realm: realm of the user (required)
    :jsonparam resolver: resolver of the user (optional; only disambiguates)
    :jsonparam user_id: resolver-local user id
    :status 200: ``true`` if a lock was removed, ``false`` if none existed or it is
        outside the admin's visibility scope
    """
    params = request.all_data
    get_required_one_of(params, ["user", "user_id"])
    user_id = get_optional(params, "user_id")
    login = get_optional(params, "user")
    realm = get_required(params, "realm")
    resolver = get_optional(params, "resolver")
    visibility_scopes = get_policy_visibility_scopes(PolicyAction.USER_LOCK_RESET)
    resolver_suffix = f", resolver={resolver}" if resolver else ""
    # `is not None`, not truthiness: a resolver-local uid of 0 is a valid identifier, not "none given".
    # unlock_user_by_id compares directly against the stored (string) column, so a JSON integer is cast.
    if user_id is not None:
        removed = unlock_user_by_id(str(user_id), realm, resolver, visibility_scopes=visibility_scopes)
        target = f"uid={user_id}, realm={realm}{resolver_suffix}"
    else:
        removed = unlock_user_by_username(login, realm, resolver, visibility_scopes=visibility_scopes)
        target = f"{login}@{realm}{resolver_suffix}"
    # Name the boundary in the audit log so a scoped-out attempt is distinguishable from a missing lock.
    scope_suffix = "" if visibility_scopes is None else ", within visibility scope"
    g.audit_object.log({"success": removed, "user": login if login is not None else str(user_id),
                        "realm": realm, "resolver": resolver or "",
                        "info": f"reset lock ({target}{scope_suffix})"})
    return send_result(removed)


@conditional_access_blueprint.route('blocklist', methods=['GET'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.BLOCKLIST_READ)
@log_with(log)
def get_blocklist():
    """
    List the blocklist entries (IP addresses). By default this returns all
    entries — currently-enforced blocks *and* stale (expired) rows; pass
    ``include_expired=false`` to return only the entries still in force. Each row
    carries the expiry fields so the caller can tell the two apart.

    Requires the admin policy action :ref:`policy_blocklist_read`.

    :query include_expired: include stale (expired) entries as well as
        currently-enforced ones (default ``true``)
    :status 200: a list of blocklist-entry dicts in ``result.value``
    """
    include_expired = is_true(get_optional(request.all_data, "include_expired", True))
    entries = list_blocklist(include_expired=include_expired)
    g.audit_object.log({"success": True, "info": f"{len(entries)} blocklist entr(y/ies)"})
    return send_result(entries)


@conditional_access_blueprint.route('blocklist', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.BLOCKLIST_SET)
@log_with(log)
def add_blocklist_entry():
    """
    Block a source IP by administrator decision, replacing whatever block is currently on record, and return
    the new entry. The IP counterpart of ``POST lock/user``.

    A never-block address (loopback, or one covered by ``CONDITIONAL_ACCESS_NEVER_BLOCK``) is refused with a
    400 rather than silently skipped: the engine skips one so an automatic action cannot lock everyone out
    behind a shared proxy, but an admin asking for a block needs to be told it did not happen.

    Requires the admin policy action :ref:`policy_blocklist_set`. The blocklist is IP-keyed and has no
    realm/resolver dimension, so no visibility scoping applies - as for reading and clearing it.

    :jsonparam ip: the source IP to block. Required.
    :jsonparam duration_seconds: how long the block lasts. Omitted, the block is permanent.
    :status 200: the new blocklist entry in ``result.value``
    :status 400: the IP is unparsable or on the never-block list, or the duration is not positive
    """
    params = request.all_data
    ip = get_required(params, "ip")
    duration_seconds = _duration_param(params)
    entry = block_ip(ip, duration_seconds=duration_seconds)
    g.audit_object.log({"success": True,
                        "info": f"blocked IP {ip} "
                                f"({'permanent' if duration_seconds is None else f'{duration_seconds}s'})"})
    return send_result(entry)


@conditional_access_blueprint.route('blocklist/purge', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.BLOCKLIST_RESET)
@log_with(log)
def purge_blocklist():
    """
    Delete stale blocklist records (expired or already-unblocked rows). Permanent
    and currently-enforced blocks are kept.

    Requires the admin policy action :ref:`policy_blocklist_reset`.

    :status 200: the number of rows removed, in ``result.value``
    """
    count = purge_expired_blocklist()
    g.audit_object.log({"success": True, "info": f"purged {count} stale blocklist entr(y/ies)"})
    return send_result(count)


@conditional_access_blueprint.route('blocklist/<entry>', methods=['DELETE'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.BLOCKLIST_RESET)
@log_with(log)
def remove_blocklist(entry):
    """
    Remove a single blocklist entry by its identifier (a source IP today).

    Requires the admin policy action :ref:`policy_blocklist_reset`.

    :status 200: ``true`` if an entry was removed, ``false`` if none existed
    """
    removed = remove_blocklist_entry(entry)
    g.audit_object.log({"success": removed, "info": f"removed blocklist entry {entry}"})
    return send_result(removed)
