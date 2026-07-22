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
REST API for conditional-access lockout policies (admin only).

These endpoints are the write path for the policies evaluated by
:mod:`privacyidea.lib.conditional_access.engine`. All business logic and
validation lives in :mod:`privacyidea.lib.conditional_access.lockout_policy`;
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
from privacyidea.lib.conditional_access.lockout_policy import (list_lockout_policies,
                                                               get_lockout_policy,
                                                               create_lockout_policy,
                                                               update_lockout_policy,
                                                               delete_lockout_policy)
from privacyidea.lib.conditional_access.lockout_state import (DEFAULT_PAGE_SIZE,
                                                              list_locked_users_paginate,
                                                              get_user_lockout_dict,
                                                              user_matches_scopes,
                                                              unlock_user_by_id,
                                                              purge_expired_user_lockouts,
                                                              list_blocklist,
                                                              remove_blocklist_entry,
                                                              purge_expired_blocklist, unlock_user_by_username)
from privacyidea.lib.error import ParameterError
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


@conditional_access_blueprint.route('policy', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.LOCKOUT_POLICY_READ)
@log_with(log)
def list_policies():
    """
    Return all conditional-access lockout policies with their stages and
    actions, ordered by descending priority (the engine's evaluation order).

    Requires the admin policy action :ref:`policy_lockout_policy_read`.

    :query enabled: if given, only return policies whose enabled state matches
        this boolean.
    :status 200: list of policy dicts in ``result.value``
    """
    enabled = get_optional(request.all_data, "enabled")
    if enabled is not None:
        enabled = is_true(enabled)
    policies = list_lockout_policies(enabled=enabled)
    g.audit_object.log({"success": True, "info": f"{len(policies)} policies"})
    return send_result(policies)


@conditional_access_blueprint.route('policy/<policy_id>', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.LOCKOUT_POLICY_READ)
@log_with(log)
def get_policy(policy_id):
    """
    Return a single conditional-access lockout policy with its stages and
    actions.

    Requires the admin policy action :ref:`policy_lockout_policy_read`.

    :status 200: the policy dict in ``result.value``
    :status 404: no policy with this id exists
    """
    policy = get_lockout_policy(_int_policy_id(policy_id))
    g.audit_object.log({"success": True, "info": f"policy {policy_id}"})
    return send_result(policy)


@conditional_access_blueprint.route('policy', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.LOCKOUT_POLICY_WRITE)
@log_with(log)
def create_policy():
    """
    Create a conditional-access lockout policy with its stages and actions.

    Requires the admin policy action :ref:`policy_lockout_policy_write`.

    :jsonparam name: unique policy name. Required.
    :jsonparam time_window_seconds: sliding window (in seconds) over which the
        tracked failures are counted. Required, positive integer.
    :jsonparam counter_types_to_track: non-empty list of authentication event
        types (e.g. ``["PIN_FAIL", "MFA_FAIL"]``) counted together against the
        stage thresholds. Required.
    :jsonparam stages: non-empty list of stage definitions, each
        ``{"failure_threshold": <int>, "priority": <int, optional>,
        "actions": [{"action_type": <LockoutAction>, "action_value": <any>}]}``.
        Required.
    :jsonparam enabled: whether the policy is evaluated (default true).
    :jsonparam dry_run: log-only mode, nothing is enforced (default false).
    :jsonparam priority: evaluation priority, higher first (default 1).
    :status 200: the id of the new policy in ``result.value``
    :status 400: invalid or missing parameter
    """
    params = request.all_data
    name = get_required(params, "name")
    enabled = get_optional(params, "enabled")
    dry_run = get_optional(params, "dry_run")
    policy_id = create_lockout_policy(
        name=name,
        time_window_seconds=get_required(params, "time_window_seconds"),
        counter_types_to_track=_get_json_param(params, "counter_types_to_track", required=True),
        stages=_get_json_param(params, "stages", required=True),
        enabled=is_true(enabled) if enabled is not None else True,
        dry_run=is_true(dry_run) if dry_run is not None else False,
        priority=get_optional(params, "priority", default=1))
    g.audit_object.log({"success": True, "info": f"created policy '{name}' (id {policy_id})"})
    return send_result(policy_id)


@conditional_access_blueprint.route('policy/<policy_id>', methods=['PATCH'])
@prepolicy(check_base_action, request, PolicyAction.LOCKOUT_POLICY_WRITE)
@log_with(log)
def update_policy(policy_id):
    """
    Partially update a conditional-access lockout policy. Only the given
    parameters are changed and all others are left untouched;
    ``counter_types_to_track`` and ``stages`` are replaced as a whole when
    given. Enabling or disabling a policy is done through this endpoint by
    sending ``{"enabled": true}`` / ``{"enabled": false}``.

    Requires the admin policy action :ref:`policy_lockout_policy_write`.
    Parameters are as for creating a policy, all optional.

    :status 200: the id of the updated policy in ``result.value``
    :status 400: invalid parameter
    :status 404: no policy with this id exists
    """
    params = request.all_data
    enabled = get_optional(params, "enabled")
    dry_run = get_optional(params, "dry_run")
    policy_id = _int_policy_id(policy_id)
    policy_id, changed_fields = update_lockout_policy(
        policy_id,
        name=get_optional(params, "name"),
        time_window_seconds=get_optional(params, "time_window_seconds"),
        counter_types_to_track=_get_json_param(params, "counter_types_to_track"),
        stages=_get_json_param(params, "stages"),
        enabled=is_true(enabled) if enabled is not None else None,
        dry_run=is_true(dry_run) if dry_run is not None else None,
        priority=get_optional(params, "priority"))
    g.audit_object.log({"success": True,
                        "info": f"updated policy {policy_id} "
                                f"({', '.join(changed_fields) or 'no fields'})"})
    return send_result(policy_id)


@conditional_access_blueprint.route('policy/<policy_id>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.LOCKOUT_POLICY_WRITE)
@log_with(log)
def delete_policy(policy_id):
    """
    Delete a conditional-access lockout policy with all its stages and actions.
    Existing locks and blocks written by the policy stay in force.

    Requires the admin policy action :ref:`policy_lockout_policy_write`.

    :status 200: the id of the deleted policy in ``result.value``
    :status 404: no policy with this id exists
    """
    delete_lockout_policy(_int_policy_id(policy_id))
    g.audit_object.log({"success": True, "info": f"deleted policy {policy_id}"})
    return send_result(policy_id)


@conditional_access_blueprint.route('lockout/users', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.USER_LOCKOUT_READ)
@admin_required
@log_with(log)
def get_locked_users():
    """
    List the locked users, paginated. "Currently locked" excludes stale rows whose
    lock has already expired (mirrors the authentication pre-check). Results are
    constrained to the admin's policy visibility scope (the realm / resolver / user
    conditions on the ``user_lockout_read`` policies), mirroring the authentication log.

    Requires the admin policy action :ref:`policy_user_lockout_read`.

    The ``realm`` / ``resolver`` / ``username`` filters accept a comma-separated list
    and a ``*`` wildcard per value (matched with ``LIKE``); with ``case_insensitive``
    the plain values match case-insensitively too. These search filters are applied on
    top of — and never widen — the visibility scope.

    :query realms: realm(s) to filter by
    :query resolvers: resolver(s) to filter by
    :query usernames: login(s) to filter by
    :query case_insensitive: match the filter values case-insensitively
    :query include_expired: also list stale (expired) locks
    :query page: page number, 1-indexed (default 1)
    :query page_size: entries per page (default 15)
    :query sort_column: one of username, realm, resolver, lock_expires_at, last_updated
    :query sort_order: ``asc`` or ``desc`` (default desc)
    :status 200: ``{locked_users, count, current, prev, next}`` in ``result.value``
    """
    params = request.all_data
    visibility_scopes = get_policy_visibility_scopes(PolicyAction.USER_LOCKOUT_READ)
    page = list_locked_users_paginate(
        realms=to_list_param(get_optional(params, "realms")),
        resolvers=to_list_param(get_optional(params, "resolvers")),
        usernames=to_list_param(get_optional(params, "usernames")),
        include_expired=is_true(get_optional(params, "include_expired")),
        case_insensitive=is_true(get_optional(params, "case_insensitive")),
        visibility_scopes=visibility_scopes,
        page=_int_param(get_optional(params, "page"), 1),
        page_size=_int_param(get_optional(params, "page_size"), DEFAULT_PAGE_SIZE),
        sort_column=get_optional(params, "sort_column") or "last_updated",
        sort_order=get_optional(params, "sort_order") or "desc")
    g.audit_object.log({"success": True, "info": f"{page['count']} locked user(s)"})
    return send_result(page)


@conditional_access_blueprint.route('lockout/user', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.USER_LOCKOUT_READ)
@admin_required
@log_with(log)
def get_user_lockout():
    """
    Return the current lock of a single user (or ``null`` if not locked).
    Constrained to the admin's policy visibility scope.

    Requires the admin policy action :ref:`policy_user_lockout_read`.

    One user identifier is required: user or user_id

    :query user: login of the user to look up.
    :query user_id: user id of the user to look up.
    :query realm: realm of the user
    :query resolver: resolver of the user (optional)
    :status 200: the user's lock dict, or ``null``, in ``result.value``
    """
    get_required_one_of(request.all_data, ["user", "user_id"])
    user_id = get_optional(request.all_data, "user_id")
    username = get_optional(request.all_data, "user")
    realm = get_required(request.all_data, "realm")
    resolver = get_optional(request.all_data, "resolver")
    visibility_scopes = get_policy_visibility_scopes(PolicyAction.USER_LOCKOUT_READ)

    # User is already resolved in before request, but only for the login, realm, resolver triplet. If the uid is given
    # instead we need to resolve the user here
    user = getattr(request, "user", None)
    if not user or not user.exist():
        user = User(uid=user_id, login=username, realm=realm, resolver=resolver)

    value = None
    if not user.is_empty() and user.exist() and user_matches_scopes(user, visibility_scopes):
        value = get_user_lockout_dict(user)
    g.audit_object.log({"success": True})
    return send_result(value)


@conditional_access_blueprint.route('lockout/users/purge', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.USER_LOCKOUT_RESET)
@admin_required
@log_with(log)
def purge_user_lockouts():
    """
    Delete stale user-lockout records (expired or already-unlocked rows).

    Requires the admin policy action :ref:`policy_user_lockout_reset`.

    :status 200: the number of rows removed, in ``result.value``
    """
    count = purge_expired_user_lockouts()
    g.audit_object.log({"success": True, "info": f"purged {count} stale user lockout(s)"})
    return send_result(count)


@conditional_access_blueprint.route('lockout/user', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.USER_LOCKOUT_RESET)
@admin_required
@log_with(log)
def reset_user_lockout():
    """
    Reset (unlock) a user's conditional-access lockout. Accepts either a
    resolvable user (``user`` + ``realm`` [+ ``resolver``]) or the raw identity
    tuple (``resolver`` + ``user_id`` + ``realm``).

    Requires the admin policy action :ref:`policy_user_lockout_reset`.

    One of user or user_id is required.

    :jsonparam user: login of the user to unlock
    :jsonparam realm: realm of the user
    :jsonparam resolver: resolver of the user
    :jsonparam user_id: resolver-local user id
    :status 200: ``true`` if a lock was removed, ``false`` if none existed
    :status 400: the user could not be resolved and no raw identity was given
    """
    params = request.all_data
    get_required_one_of(params, ["user", "user_id"])
    user_id = get_optional(params, "user_id")
    login = get_optional(params, "user")
    realm = get_required(params, "realm")
    resolver = get_required(params, "resolver")
    if user_id:
        removed = unlock_user_by_id(resolver, user_id, realm)
        target = f"resolver={resolver}, uid={user_id}, realm={realm}"
    else:
        removed = unlock_user_by_username(login, realm, resolver)
        target = f"{login}@{realm}"
    g.audit_object.log({"success": removed, "info": f"reset lockout ({target})"})
    return send_result(removed)


@conditional_access_blueprint.route('blocklist', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.BLOCKLIST_READ)
@admin_required
@log_with(log)
def get_blocklist():
    """
    List the currently blocked entries (a source IP is the only entry type for
    now). "Currently blocked" excludes stale rows whose block has already expired.

    Requires the admin policy action :ref:`policy_blocklist_read`.

    :query include_expired: also list stale (expired) entries, each marked ``is_expired=true``
    :status 200: a list of blocklist-entry dicts in ``result.value``
    """
    include_expired = is_true(get_optional(request.all_data, "include_expired"))
    entries = list_blocklist(include_expired=include_expired)
    g.audit_object.log({"success": True, "info": f"{len(entries)} blocklist entr(y/ies)"})
    return send_result(entries)


@conditional_access_blueprint.route('blocklist/purge', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.BLOCKLIST_RESET)
@admin_required
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
@prepolicy(check_base_action, request, PolicyAction.BLOCKLIST_RESET)
@admin_required
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
