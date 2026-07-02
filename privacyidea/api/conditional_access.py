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

from privacyidea.api.lib.prepolicy import prepolicy, check_base_action
from privacyidea.api.lib.utils import send_result
from privacyidea.lib.conditional_access.lockout_policy import (list_lockout_policies,
                                                               get_lockout_policy,
                                                               create_lockout_policy,
                                                               update_lockout_policy,
                                                               delete_lockout_policy,
                                                               enable_lockout_policy)
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.params import get_optional, get_required
from privacyidea.lib.policies.actions import PolicyAction
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
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_READ)
@log_with(log)
def list_policies():
    """
    Return all conditional-access lockout policies with their stages and
    actions, ordered by descending priority (the engine's evaluation order).

    Requires the admin policy action :ref:`policy_conditional_access_read`.

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
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_READ)
@log_with(log)
def get_policy(policy_id):
    """
    Return a single conditional-access lockout policy with its stages and
    actions.

    Requires the admin policy action :ref:`policy_conditional_access_read`.

    :status 200: the policy dict in ``result.value``
    :status 404: no policy with this id exists
    """
    policy = get_lockout_policy(_int_policy_id(policy_id))
    g.audit_object.log({"success": True, "info": f"policy {policy_id}"})
    return send_result(policy)


@conditional_access_blueprint.route('policy', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_WRITE)
@log_with(log)
def create_policy():
    """
    Create a conditional-access lockout policy with its stages and actions.

    Requires the admin policy action :ref:`policy_conditional_access_write`.

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


@conditional_access_blueprint.route('policy/<policy_id>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_WRITE)
@log_with(log)
def update_policy(policy_id):
    """
    Update a conditional-access lockout policy. Only the given parameters are
    changed; ``counter_types_to_track`` and ``stages`` are replaced as a whole
    when given.

    Requires the admin policy action :ref:`policy_conditional_access_write`.
    Parameters are as for creating a policy, all optional.

    :status 200: the id of the updated policy in ``result.value``
    :status 400: invalid parameter
    :status 404: no policy with this id exists
    """
    params = request.all_data
    enabled = get_optional(params, "enabled")
    dry_run = get_optional(params, "dry_run")
    policy_id = _int_policy_id(policy_id)
    update_lockout_policy(
        policy_id,
        name=get_optional(params, "name"),
        time_window_seconds=get_optional(params, "time_window_seconds"),
        counter_types_to_track=_get_json_param(params, "counter_types_to_track"),
        stages=_get_json_param(params, "stages"),
        enabled=is_true(enabled) if enabled is not None else None,
        dry_run=is_true(dry_run) if dry_run is not None else None,
        priority=get_optional(params, "priority"))
    g.audit_object.log({"success": True, "info": f"updated policy {policy_id}"})
    return send_result(policy_id)


@conditional_access_blueprint.route('policy/<policy_id>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_WRITE)
@log_with(log)
def delete_policy(policy_id):
    """
    Delete a conditional-access lockout policy with all its stages and actions.
    Existing locks and blocks written by the policy stay in force.

    Requires the admin policy action :ref:`policy_conditional_access_write`.

    :status 200: the id of the deleted policy in ``result.value``
    :status 404: no policy with this id exists
    """
    delete_lockout_policy(_int_policy_id(policy_id))
    g.audit_object.log({"success": True, "info": f"deleted policy {policy_id}"})
    return send_result(policy_id)


@conditional_access_blueprint.route('policy/<policy_id>/enable', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_WRITE)
@log_with(log)
def enable_policy(policy_id):
    """
    Enable a conditional-access lockout policy.

    Requires the admin policy action :ref:`policy_conditional_access_write`.

    :status 200: the id of the policy in ``result.value``
    :status 404: no policy with this id exists
    """
    enable_lockout_policy(_int_policy_id(policy_id), enable=True)
    g.audit_object.log({"success": True, "info": f"enabled policy {policy_id}"})
    return send_result(policy_id)


@conditional_access_blueprint.route('policy/<policy_id>/disable', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.CONDITIONAL_ACCESS_WRITE)
@log_with(log)
def disable_policy(policy_id):
    """
    Disable a conditional-access lockout policy (it is no longer evaluated;
    locks and blocks it already wrote stay in force).

    Requires the admin policy action :ref:`policy_conditional_access_write`.

    :status 200: the id of the policy in ``result.value``
    :status 404: no policy with this id exists
    """
    enable_lockout_policy(_int_policy_id(policy_id), enable=False)
    g.audit_object.log({"success": True, "info": f"disabled policy {policy_id}"})
    return send_result(policy_id)
