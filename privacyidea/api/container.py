# (c) NetKnights GmbH 2024,  https://netknights.it
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
# SPDX-FileCopyrightText: 2024 Nils Behlen <nils.behlen@netknights.it>
# SPDX-FileCopyrightText: 2024 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
from flask_babel import _
import json
import logging

from flask import Blueprint, request, g

from privacyidea.api.auth import admin_required
from privacyidea.api.lib.prepolicy import (check_base_action, prepolicy, check_user_params, check_token_action,
                                           check_admin_tokenlist, check_container_action,
                                           check_container_register_rollover, container_registration_config,
                                           smartphone_config, check_client_container_action, hide_tokeninfo,
                                           check_client_container_disabled_action, hide_container_info)
from privacyidea.api.lib.utils import map_error_to_code, send_error, send_result, to_list_param
from privacyidea.lib.params import get_optional, get_required, get_required_one_of
from privacyidea.lib.container import (find_container_by_serial, init_container, get_container_classes_descriptions,
                                       get_container_token_types, get_all_containers, add_container_info,
                                       set_container_description, set_container_states, set_container_realms,
                                       delete_container_by_serial, assign_user, unassign_user, add_token_to_container,
                                       add_multiple_tokens_to_container, remove_token_from_container,
                                       remove_multiple_tokens_from_container,
                                       create_container_dict, create_endpoint_url,
                                       create_container_template,
                                       get_templates_by_query, create_container_tokens_from_template, get_template_obj,
                                       set_default_template, get_container_template_classes,
                                       create_container_from_db_object,
                                       compare_template_with_container, unregister,
                                       finalize_registration, init_container_rollover,
                                       get_container_realms,
                                       add_not_authorized_tokens_result, get_offline_token_serials,
                                       delete_container_info, init_registration)
from privacyidea.lib.containers.container_info import (TokenContainerInfoData, PI_INTERNAL, RegistrationState,
                                                       CHALLENGE_TTL, REGISTRATION_TTL, SERVER_URL, SSL_VERIFY)
from privacyidea.lib.containers.container_states import ContainerStates
from privacyidea.lib.error import ParameterError, ContainerNotRegistered, Error
from privacyidea.lib.event import event
from privacyidea.lib.log import log_with
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import Match, SCOPE
from privacyidea.lib.token import regenerate_enroll_url
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.utils import is_true

container_blueprint = Blueprint('container_blueprint', __name__)
log = logging.getLogger(__name__)

__doc__ = """
The container REST API manages token containers and the templates
they are created from. A container groups several tokens together for
joint enrollment, synchronization, rollover, and lifecycle management
— for example a smartphone holding several push and OTP tokens, or a
hardware key holding multiple WebAuthn credentials. See
:ref:`container` for the conceptual chapter.

The endpoints fall in three audiences:

* Admin / WebUI flows — listing, creation, assignment, realm and
  state management, template administration. These require admin
  authentication and are gated by the corresponding container
  :ref:`container_policies` (``container_create``,
  ``container_list``, ``container_assign_user``, ...).
* End-user self-service — a regular user with the matching user-scope
  policies can invoke the same endpoints on their own containers
  (e.g. assign a fresh smartphone to themselves, add a token to it).
* Client device flows — the registered container itself calls
  :http:post:`/container/register/finalize`,
  :http:post:`/container/register/terminate/client`,
  :http:post:`/container/challenge`,
  :http:post:`/container/synchronize` and
  :http:post:`/container/rollover` directly. These five endpoints are
  anonymous (no auth header); the request is authenticated by a
  cryptographic signature over a server-issued challenge that the
  device generated during registration.
"""


@container_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, action=PolicyAction.CONTAINER_LIST)
@prepolicy(check_admin_tokenlist, request, PolicyAction.CONTAINER_LIST)
@prepolicy(check_admin_tokenlist, request, PolicyAction.TOKENLIST)
@prepolicy(hide_container_info, request)
@prepolicy(hide_tokeninfo, request)
@log_with(log)
def list_containers():
    """
    Return containers, optionally filtered, paginated and sorted.
    Without ``page`` / ``pagesize`` all matching containers are
    returned at once.

    For admin callers, the response is restricted to containers in
    realms the calling admin's policies allow. For user callers, only
    the calling user's containers are returned. The ``hide_container_info``
    and ``hide_tokeninfo`` policies may strip configured info keys
    from the response.

    Requires authentication and the policy action ``container_list``.

    :query user: filter by the username of an assigned user.
    :query container_serial: filter by container serial
        (case-insensitive, ``*`` wildcard).
    :query type: filter by container type (case-insensitive, ``*``
        wildcard).
    :query type_list: comma-separated list of container types (e.g.
        ``type_list=generic,smartphone``). Entries are matched
        case-insensitively as exact values; wildcards are not honored
        inside the list. Takes precedence over ``type``.
    :query token_serial: filter to containers that hold a token with
        this serial (case-insensitive, ``*`` wildcard).
    :query template: filter by the name of the template the
        container was created from (case-sensitive, ``*`` wildcard).
    :query container_realm: filter by realm (case-insensitive, ``*``
        wildcard).
    :query description: filter by description (case-insensitive,
        ``*`` wildcard).
    :query resolver: filter by the resolver of the assigned user
        (case-insensitive, ``*`` wildcard).
    :query assigned: ``true`` or ``false`` to limit to assigned or
        unassigned containers.
    :query info_key: filter by container-info key (case-sensitive,
        ``*`` wildcard).
    :query info_value: filter by container-info value
        (case-insensitive, ``*`` wildcard).
    :query last_auth_delta: maximum age of the last authentication
        (e.g. ``1y``, ``14d``, ``1h``, ``5m``, ``30s``).
    :query last_sync_delta: maximum age of the last synchronization,
        same format as ``last_auth_delta``.
    :query state: state the container should be in (case-insensitive,
        ``*`` wildcard).
    :query sortby: column to sort by (``serial`` or ``type``).
    :query sortdir: ``asc`` (default) or ``desc``.
    :query pagesize: page size; omit for no pagination.
    :query page: 1-indexed page number.
    :query no_token: ``1`` to omit the token list from each container
        entry.
    :status 200: paginated container list in ``result.value`` with
        ``containers``, ``count``, ``current``, ``next``, ``prev``.
    """
    param = request.all_data
    user = request.User
    cserial = get_optional(param, "container_serial")
    # TODO(4.0.0): replace the separate "type" and "type_list" query params
    #   with a single list-only "types" param. They are kept separate here only
    #   for consistency with the token API on the 3.x line.
    ctype = get_optional(param, "type")
    ctype_exact = None
    ctype_list = get_optional(param, "type_list")
    if ctype_list:
        ctype_exact = to_list_param(ctype_list)
    token_serial = get_optional(param, "token_serial")
    template = get_optional(param, "template")
    realm = get_optional(param, "container_realm")
    description = get_optional(param, "description")
    resolver = get_optional(param, "resolver")
    assigned = get_optional(param, "assigned")
    if assigned is not None:
        assigned = is_true(assigned)
    info_key = get_optional(param, "info_key")
    info_value = get_optional(param, "info_value")
    last_auth_delta = get_optional(param, "last_auth_delta")
    last_sync_delta = get_optional(param, "last_sync_delta")
    state = get_optional(param, "state")
    sortby = get_optional(param, "sortby", default="serial")
    sortdir = get_optional(param, "sortdir", default="asc")
    psize = int(get_optional(param, "pagesize") or 0)
    page = int(get_optional(param, "page") or 0)
    no_token = get_optional(param, "no_token", default=False)
    logged_in_user_role = g.logged_in_user.get("role")
    allowed_container_realms = getattr(request, "pi_allowed_container_realms", None)
    allowed_token_realms = getattr(request, "pi_allowed_realms", None)
    hide_container_info = get_optional(param, "hide_container_info")
    hide_token_info = get_optional(param, "hidden_tokeninfo")

    # Set info dictionary (if either key or value is None, filter for all keys/values using * as wildcard)
    info = None
    if info_key or info_value:
        info = {info_key or "*": info_value or "*"}

    result = get_all_containers(user=user, serial=cserial, ctype=ctype, ctype_exact=ctype_exact,
                                token_serial=token_serial,
                                realm=realm, allowed_realms=allowed_container_realms, template=template,
                                description=description, resolver=resolver, assigned=assigned, info=info,
                                last_auth_delta=last_auth_delta, last_sync_delta=last_sync_delta, state=state,
                                sortby=sortby, sortdir=sortdir, pagesize=psize, page=page)

    containers = create_container_dict(result["containers"], no_token, user, logged_in_user_role, allowed_token_realms,
                                       hide_container_info=hide_container_info, hide_token_info=hide_token_info)
    result["containers"] = containers

    g.audit_object.log({"success": True,
                        "info": f"allowed_container_realms={allowed_container_realms}, "
                                f"allowed_token_realms={allowed_token_realms}"})
    return send_result(result)


@container_blueprint.route('<string:container_serial>/assign', methods=['POST'])
@prepolicy(check_user_params, request, action=PolicyAction.CONTAINER_ASSIGN_USER)
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_ASSIGN_USER)
@event('container_assign', request, g)
@log_with(log)
def assign(container_serial):
    """
    Assign a container to a user.

    Requires authentication and the policy action
    :ref:`policy_container_assign_user`.

    :param container_serial: path component, the container serial.
    :jsonparam user: login name of the user (required).
    :jsonparam realm: realm of the user (required if the user is not
        in the default realm).
    :status 200: ``True`` on success in ``result.value``.
    """
    user = get_user_from_param(request.all_data, False)
    res = assign_user(container_serial, user)

    container = find_container_by_serial(container_serial)
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('<string:container_serial>/unassign', methods=['POST'])
@prepolicy(check_user_params, request, action=PolicyAction.CONTAINER_UNASSIGN_USER)
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_UNASSIGN_USER)
@event('container_unassign', request, g)
@log_with(log)
def unassign(container_serial):
    """
    Unassign a user from a container. If the user no longer exists in
    the resolver (deleted user), supply ``user_id`` together with
    ``resolver`` so the assignment row can still be located.

    Requires authentication and the policy action
    :ref:`policy_container_unassign_user`.

    :param container_serial: path component, the container serial.
    :jsonparam user: login name of the user.
    :jsonparam realm: realm of the user.
    :jsonparam resolver: resolver of the user.
    :jsonparam user_id: user id (required for users that no longer
        resolve through their store).
    :status 200: ``True`` on success in ``result.value``.
    :status 400: neither ``user`` nor ``user_id`` was supplied, or
        the supplied identification is incomplete.
    """
    # Get user
    user = request.User
    # The user id is not set in before_request, but is required to remove users that do not exist (anymore)
    user_id = request.all_data.get("user_id", None)
    if user_id:
        user.uid = str(user_id)

    # Check if required parameter is present
    __ = get_required_one_of(request.all_data, ["user", "user_id"])
    if user.login and not user.realm and not user.resolver and not user.uid:
        raise ParameterError(_("Missing parameter 'realm', 'resolver', and/or 'user_id'"))

    res = unassign_user(container_serial, user)

    container = find_container_by_serial(container_serial)
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('init', methods=['POST'])
@prepolicy(check_admin_tokenlist, request, action=PolicyAction.CONTAINER_CREATE)
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_CREATE)
@event('container_init', request, g)
@log_with(log)
def init():
    """
    Create a new container.

    A container can optionally be created from a template, in which
    case the listed tokens are also created and added to the new
    container in the same call. The template may be supplied either
    inline as a dictionary (``template``) or by reference to an
    existing template (``template_name``); supplying both is an error.

    Requires authentication and the policy action
    :ref:`policy_container_create`. Realm-admins are restricted to
    realms their policies cover; if the caller does not specify a
    realm, the first realm allowed by the policy is used.

    :jsonparam type: container type (e.g. ``smartphone``, ``yubikey``,
        ``generic``). Required.
    :jsonparam description: free-form description.
    :jsonparam container_serial: optional unique serial. Stored
        case-normalized.
    :jsonparam user: optional login name of an initial assignee
        (requires ``realm``).
    :jsonparam realm: optional realm of the assignee (requires
        ``user``).
    :jsonparam template: optional template definition (dict) to use
        for token creation.
    :jsonparam template_name: optional name of an existing template
        to use.
    :status 200: ``{"container_serial": ..., "tokens": [...]}`` in
        ``result.value``; ``tokens`` is only present when a template
        was used.
    :status 400: invalid type, serial collision, or both ``template``
        and ``template_name`` supplied.
    """
    user_role = g.logged_in_user.get("role")
    allowed_realms = getattr(request, "pi_allowed_realms", None)
    if user_role == "admin" and allowed_realms:
        req_realm = get_optional(request.all_data, "realm")
        if not req_realm or req_realm == "":
            # The container has to be in one realm the admin is allowed to manage
            request.all_data["realm"] = allowed_realms[0]

    init_res = init_container(request.all_data)
    serial = init_res["container_serial"]
    res = {"container_serial": serial}
    container = find_container_by_serial(serial)

    # Template handling
    template_tokens = init_res["template_tokens"]
    if template_tokens:
        res["tokens"] = create_container_tokens_from_template(serial, template_tokens, request, user_role)

    # Audit log
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": serial,
                      "container_type": request.all_data.get("type") or "",
                      "success": True}
    if request.all_data.get("description"):
        audit_log_data["action_detail"] = f"description={request.all_data.get('description')}"
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('<string:container_serial>', methods=['DELETE'])
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_DELETE)
@event('container_delete', request, g)
@log_with(log)
def delete(container_serial):
    """
    Delete a container. The tokens assigned to the container are not
    deleted; they remain in the database and become un-attached.

    Requires authentication and the policy action
    :ref:`policy_container_delete`.

    :param container_serial: path component, the container serial.
    :status 200: ``True`` on success in ``result.value``.
    :status 404: no container with that serial exists.
    """
    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type}
    g.audit_object.log(audit_log_data)

    # Delete container
    res = delete_container_by_serial(container_serial)
    g.audit_object.log({"success": res > 0})

    return send_result(True)


@container_blueprint.route('<string:container_serial>/add', methods=['POST'])
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_ADD_TOKEN)
@prepolicy(check_token_action, request, action=PolicyAction.CONTAINER_ADD_TOKEN)
@event('container_add_token', request, g)
@log_with(log)
def add_token(container_serial):
    """
    Add a single token to a container.

    Requires authentication and the policy action
    :ref:`policy_container_add_token`.

    :param container_serial: path component, the container serial.
    :jsonparam serial: serial of the token to add (required).
    :status 200: ``True`` on success in ``result.value``.
    """
    token_serial = get_required(request.all_data, "serial", allow_empty=False)

    success = add_token_to_container(container_serial, token_serial)

    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "serial": token_serial,
                      "success": success}
    g.audit_object.log(audit_log_data)
    return send_result(success)


@container_blueprint.route('<string:container_serial>/addall', methods=['POST'])
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_ADD_TOKEN)
@prepolicy(check_token_action, request, action=PolicyAction.CONTAINER_ADD_TOKEN)
@event('container_add_token', request, g)
@log_with(log)
def add_all_tokens(container_serial):
    """
    Add several tokens to a container in a single call.

    Requires authentication and the policy action
    :ref:`policy_container_add_token`.

    :param container_serial: path component, the container serial.
    :jsonparam serial: comma-separated list of token serials
        (whitespace tolerated; required).
    :status 200: dict mapping each requested serial to a per-token
        success boolean in ``result.value``.
    """
    serial = get_required(request.all_data, "serial", allow_empty=False)
    token_serials = serial.replace(' ', '').split(',')

    res = add_multiple_tokens_to_container(container_serial, token_serials)

    not_authorized_serials = get_optional(request.all_data, "not_authorized_serials")
    res = add_not_authorized_tokens_result(res, not_authorized_serials)

    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    success = False not in res.values()
    result_str = ", ".join([f"{k}: {v}" for k, v in res.items()])
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "serial": serial,
                      "success": success,
                      "info": result_str}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('<string:container_serial>/remove', methods=['POST'])
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_REMOVE_TOKEN)
@prepolicy(check_token_action, request, action=PolicyAction.CONTAINER_REMOVE_TOKEN)
@event('container_remove_token', request, g)
@log_with(log)
def remove_token(container_serial):
    """
    Remove a single token from a container. The token itself is not
    deleted.

    Requires authentication and the policy action
    :ref:`policy_container_remove_token`.

    :param container_serial: path component, the container serial.
    :jsonparam serial: serial of the token to remove (required).
    :status 200: ``True`` on success in ``result.value``.
    """
    token_serial = get_required(request.all_data, "serial", allow_empty=False)

    success = remove_token_from_container(container_serial, token_serial)

    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "serial": token_serial,
                      "success": success}
    g.audit_object.log(audit_log_data)
    return send_result(success)


@container_blueprint.route('<string:container_serial>/removeall', methods=['POST'])
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_REMOVE_TOKEN)
@prepolicy(check_token_action, request, action=PolicyAction.CONTAINER_REMOVE_TOKEN)
@event('container_remove_token', request, g)
@log_with(log)
def remove_all_tokens(container_serial):
    """
    Remove several tokens from a container in a single call. The
    tokens themselves are not deleted.

    Requires authentication and the policy action
    :ref:`policy_container_remove_token`.

    :param container_serial: path component, the container serial.
    :jsonparam serial: comma-separated list of token serials
        (whitespace tolerated; required, but may be empty when a
        prepolicy is configured to remove all tokens).
    :status 200: dict mapping each requested serial to a per-token
        success boolean in ``result.value``.
    """
    # allow serial to be empty if the pre-policy removes all tokens
    serial = get_required(request.all_data, "serial", allow_empty=True)
    token_serials = serial.replace(' ', '').split(',')

    res = remove_multiple_tokens_from_container(container_serial, token_serials)

    not_authorized_serials = get_optional(request.all_data, "not_authorized_serials")
    res = add_not_authorized_tokens_result(res, not_authorized_serials)

    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    success = False not in res.values()
    result_str = ", ".join([f"{k}: {v}" for k, v in res.items()])
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "serial": serial,
                      "success": success,
                      "info": result_str}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('types', methods=['GET'])
@container_blueprint.route('tokentypes', methods=['GET'])
@log_with(log)
def get_types():
    """
    Return the container types known to this server with their
    descriptions and the token types each can hold. The route is
    available under both ``/container/types`` and the alias
    ``/container/tokentypes`` — same response.

    Requires authentication.

    :status 200: dict keyed by container type with
        ``description`` and ``token_types`` for each, in
        ``result.value``.

    Example response value::

        {
          "smartphone": {"description": "...",
                          "token_types": ["hotp", "totp", "push", "sms"]},
          "yubikey":    {"description": "...",
                          "token_types": ["hotp", "webauthn"]}
        }
    """
    descriptions = get_container_classes_descriptions()
    ttypes = get_container_token_types()
    res = {ctype: {"description": desc, "token_types": ttypes.get(ctype, [])} for ctype, desc in descriptions.items()}
    g.audit_object.log({"success": True})
    return send_result(res)


@container_blueprint.route('<string:container_serial>/description', methods=['POST'])
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_DESCRIPTION)
@event('container_set_description', request, g)
@log_with(log)
def set_description(container_serial):
    """
    Replace the free-form description of a container.

    Requires authentication and the policy action
    :ref:`policy_container_description`.

    :param container_serial: path component, the container serial.
    :jsonparam description: new description (required).
    :status 200: ``True`` on success in ``result.value``.
    """
    new_description = get_required(request.all_data, "description", allow_empty=True)
    set_container_description(container_serial, new_description)

    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "action_detail": f"description={new_description}",
                      "success": True}
    g.audit_object.log(audit_log_data)
    return send_result(True)


@container_blueprint.route('<string:container_serial>/states', methods=['POST'])
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_STATE)
@event('container_set_states', request, g)
@log_with(log)
def set_states(container_serial):
    """
    Set the states of a container. The full set of states is
    replaced by the provided list; mutually-exclusive states cancel
    each other out.

    Requires authentication and the policy action
    :ref:`policy_container_state`. See
    :http:get:`/container/statetypes` for the supported states and
    their exclusion rules.

    :param container_serial: path component, the container serial.
    :jsonparam states: comma-separated list of state names
        (whitespace tolerated; required, must be non-empty).
    :status 200: dict mapping each requested state to whether it was
        set, in ``result.value``.
    """
    states_value = get_required(request.all_data, "states", allow_empty=False)
    states = to_list_param(states_value)
    res = set_container_states(container_serial, states)

    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    success = False not in res.values()
    map_to_bool = ["False", "True"]
    result_str = ", ".join([f"{k}: {map_to_bool[v]}" for k, v in res.items()])
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "action_detail": f"states={states}",
                      "success": success,
                      "info": result_str}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('statetypes', methods=['GET'])
@log_with(log)
def get_state_types():
    """
    Return the supported container states with their mutual-exclusion
    map. The keys are the state names; the value for each state is
    the list of states that the key state excludes.

    Requires authentication.

    :status 200: dict of state-exclusion lists in ``result.value``.
    """
    state_types_exclusions_enums = ContainerStates.get_exclusive_states()
    # Get string representation from enums
    state_types_exclusions = {}
    for state_type, excluded_states in state_types_exclusions_enums.items():
        state_types_exclusions[state_type.value] = [state.value for state in excluded_states]

    g.audit_object.log({"success": True})
    return send_result(state_types_exclusions)


@container_blueprint.route('<string:container_serial>/realms', methods=['POST'])
@admin_required
@prepolicy(check_admin_tokenlist, request, action=PolicyAction.CONTAINER_REALMS)
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_REALMS)
@event('container_set_realms', request, g)
@log_with(log)
def set_realms(container_serial):
    """
    Replace the realms a container belongs to. Realms not listed in
    the request are removed; realms listed are added or kept. For
    realm-admin callers, the call is restricted to the realms the
    caller is allowed to manage.

    Requires admin authentication and the policy action
    :ref:`policy_container_realms`.

    :param container_serial: path component, the container serial.
    :jsonparam realms: comma-separated list of realm names
        (whitespace tolerated; pass an empty string to remove all
        realms).
    :status 200: dict mapping each realm to whether it was applied
        (plus a ``deleted`` entry counting removed realms), in
        ``result.value``.
    """
    # Get parameters
    container_realms = get_required(request.all_data, "realms", allow_empty=True)
    realm_list = to_list_param(container_realms)
    allowed_realms = getattr(request, "pi_allowed_realms", None)

    # Set realms
    result = set_container_realms(container_serial, realm_list, allowed_realms)
    success = False not in result.values()

    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "action_detail": f"realms={container_realms}",
                      "success": success}
    if not success:
        result_str = ", ".join([f"{k}: {v}" for k, v in result.items() if not k == "deleted"])
        audit_log_data["info"] = f"success = {result_str}"
    g.audit_object.log(audit_log_data)
    return send_result(result)


@container_blueprint.route('<string:container_serial>/info/<key>', methods=['POST'])
@admin_required
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_INFO)
@log_with(log)
def set_container_info(container_serial, key):
    """
    Set or update a container-info entry. If an entry with this key
    already exists it is overwritten — except entries marked
    ``PI_INTERNAL``, which are reserved for the server and cannot be
    modified through this endpoint.

    Requires admin authentication and the policy action
    :ref:`policy_container_info`.

    :param container_serial: path component, the container serial.
    :param key: path component, the info key to set.
    :jsonparam value: value to store (required).
    :status 200: ``True`` on success in ``result.value``.
    :status 403: the key is reserved as ``PI_INTERNAL``.
    """
    value = get_required(request.all_data, "value")
    res = add_container_info(container_serial, key, value)

    # Audit log
    g.audit_object.log({"container_serial": container_serial,
                        "key": key,
                        "value": value,
                        "success": res})
    return send_result(res)


@container_blueprint.route('<string:container_serial>/info/delete/<key>', methods=['DELETE'])
@admin_required
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_INFO)
@log_with(log)
def delete_container_info_entry(container_serial, key):
    """
    Delete a container-info entry. Entries marked ``PI_INTERNAL``
    are reserved for the server and cannot be removed through this
    endpoint.

    Requires admin authentication and the policy action
    :ref:`policy_container_info`.

    :param container_serial: path component, the container serial.
    :param key: path component, the info key to delete.
    :status 200: ``True`` on success in ``result.value``.
    :status 403: the key is reserved as ``PI_INTERNAL``.
    """
    res = delete_container_info(container_serial, key)

    # Audit log
    g.audit_object.log({"container_serial": container_serial,
                        "key": key,
                        "success": res[key]})
    return send_result(res[key])


@container_blueprint.route('register/initialize', methods=['POST'])
@prepolicy(check_container_register_rollover, request)
@prepolicy(container_registration_config, request)
@event('container_register_initialize', request, g)
@log_with(log)
def registration_init():
    """
    Step 1 of container registration: prepare a container for being
    paired with a client device. The response carries everything the
    client device needs to complete the second step at
    :http:post:`/container/register/finalize` — typically a deep link
    or QR code that encodes the server URL, the registration TTL,
    and a nonce.

    Server-side parameters (server URL, challenge TTL, registration
    TTL, TLS verification) are injected by the
    ``container_registration_config`` prepolicy from the corresponding
    container policies; pass ``rollover=1`` when re-pairing an
    already registered container with a new device.

    Requires authentication. The exact policy gate depends on the
    rollover state — see the ``container_register_rollover`` prepolicy.

    :jsonparam container_serial: container serial (required).
    :jsonparam rollover: ``1`` to initiate a rollover registration
        for an already-registered container; otherwise the container
        must not yet be registered.
    :status 200: container-type-specific registration payload in
        ``result.value``. Always includes ``offline_tokens`` listing
        any tokens already attached to the container for offline use.

    Example response for a smartphone container::

        {
          "container_url": {
            "description": "URL for privacyIDEA Container Registration",
            "img": "<QR code>",
            "value": "pia://container/SMPH0006D5BC?issuer=privacyIDEA&ttl=10..."
          },
          "nonce": "c238392af49250804c25bbd7d86408839e91fe97",
          "time_stamp": "2024-12-20T09:53:40.158319+00:00",
          "server_url": "https://pi.net",
          "ttl": 10,
          "ssl_verify": "True",
          "key_algorithm": "secp384r1",
          "hash_algorithm": "sha256",
          "offline_tokens": []
        }
    """
    params = request.all_data
    container_serial = get_required(params, "container_serial")
    container_rollover = get_optional(params, "rollover")
    container = find_container_by_serial(container_serial)
    # Params set by pre-policies
    server_url = get_optional(params, SERVER_URL)
    challenge_ttl = get_optional(params, CHALLENGE_TTL)
    registration_ttl = get_optional(params, REGISTRATION_TTL)
    ssl_verify = get_optional(params, SSL_VERIFY)

    # Audit log
    info_str = (f"server_url={server_url}, challenge_ttl={challenge_ttl}min, registration_ttl={registration_ttl}min, "
                f"ssl_verify={ssl_verify}")
    g.audit_object.log({"container_serial": container_serial,
                        "container_type": container.type,
                        "action_detail": f"rollover={container_rollover}",
                        "info": info_str})

    res = init_registration(container, container_rollover, server_url, registration_ttl, ssl_verify, challenge_ttl,
                            params)

    # Check for offline tokens
    res["offline_tokens"] = get_offline_token_serials(container)

    # Audit log
    g.audit_object.log({"success": True})

    return send_result(res)


@container_blueprint.route('register/finalize', methods=['POST'])
@event('container_register_finalize', request, g)
@prepolicy(smartphone_config, request)
@log_with(log)
def registration_finalize():
    """
    Step 2 of container registration. Called by the client device
    itself after it has consumed the registration payload from
    :http:post:`/container/register/initialize`. The exact set of
    parameters is container-type specific; for smartphone containers,
    the body typically carries the device's public key and the
    signed nonce.

    This endpoint is **anonymous** — no auth header is required. The
    request is authenticated by the container's signed challenge
    response. Failures may be masked by the container-scope
    ``hide_specific_error_message`` policy.

    :jsonparam container_serial: container serial (required).
    :status 200: container-type-specific registration result in
        ``result.value``, including the ``policies`` block with
        client-relevant settings.
    """
    params = request.all_data
    container_serial = get_required(params, "container_serial")

    try:
        res = finalize_registration(container_serial, params)

        # Add policy information to the response
        res["policies"] = request.all_data.get("client_policies", {})

        # Audit log
        container = find_container_by_serial(container_serial)

        g.audit_object.log({"container_serial": container_serial,
                            "container_type": container.type,
                            "success": res})
        return send_result(res)

    except Exception as e:
        if Match.user(
            g,
            scope=SCOPE.CONTAINER,
            action=PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE,
            user_object=request.User if hasattr(request, "User") else None,
        ).any():
            return (send_error("Failed finalizing container registration", error_code=Error.CONTAINER),
                    map_error_to_code(e))
        raise


@container_blueprint.route('register/<string:container_serial>/terminate', methods=['POST'])
@prepolicy(check_container_action, request, action=PolicyAction.CONTAINER_UNREGISTER)
@event('container_unregister', request, g)
@log_with(log)
def registration_terminate(container_serial: str):
    """
    Unregister a container from the server side. The client device
    is left in place but will no longer be able to synchronize with
    the server. Use the client-side counterpart at
    :http:post:`/container/register/terminate/client` for the
    device-initiated unregister.

    Requires authentication and the policy action
    :ref:`policy_container_unregister`.

    :param container_serial: path component, the container serial.
    :status 200: ``{"success": <bool>}`` in ``result.value``.
    """
    container = find_container_by_serial(container_serial)

    res = unregister(container)

    # Audit log
    g.audit_object.log({"container_serial": container_serial,
                        "container_type": container.type,
                        "success": res})

    return send_result({"success": res})


@container_blueprint.route('register/terminate/client', methods=['POST'])
@prepolicy(check_client_container_disabled_action, request, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
@event('container_unregister', request, g)
@log_with(log)
def registration_terminate_client():
    """
    Client-initiated unregister. Called by the registered container
    device itself when the user wants to drop the pairing from their
    end (e.g. removing the privacyIDEA account from the smartphone
    app).

    This endpoint is **anonymous** — no auth header is required. The
    caller authenticates by signing a challenge that the container
    knows about. The container-scope policy
    ``disable_client_container_unregister`` (see
    :ref:`container_policy_disable_client_unregister`) can disable
    this client-side path.

    :jsonparam container_serial: container serial (required).
    :jsonparam signature: client's signature over the challenge data
        (required).
    :status 200: ``{"success": <bool>}`` in ``result.value``.
    """
    params = request.all_data
    container_serial = get_required(params, "container_serial")

    try:
        container = find_container_by_serial(container_serial)
        server_url = container.get_container_info_dict().get("server_url")
        if server_url is None:
            log.debug("Server url is not set in the container info. Container might not be registered correctly.")
            server_url = " "
        scope = create_endpoint_url(server_url, "container/register/terminate/client")
        params.update({'scope': scope})
        container.check_challenge_response(params)

        res = unregister(container)

        # Audit log
        g.audit_object.log({"container_serial": container_serial,
                            "container_type": container.type,
                            "success": res})

        return send_result({"success": res})

    except Exception as e:
        if Match.user(
            g,
            scope=SCOPE.CONTAINER,
            action=PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE,
            user_object=request.User if hasattr(request, "User") else None,
        ).any():
            return (send_error("Failed terminating container registration", error_code=Error.CONTAINER),
                    map_error_to_code(e))
        raise


@container_blueprint.route('/challenge', methods=['POST'])
@event('container_create_challenge', request, g)
@log_with(log)
def create_challenge():
    """
    Issue a fresh challenge for a registered container. The client
    device requests this before any operation that requires a signed
    response (synchronize, client-side terminate). Only registered
    containers (in state ``REGISTERED``, ``ROLLOVER``, or
    ``ROLLOVER_COMPLETED``) may obtain a challenge.

    This endpoint is **anonymous** — no auth header is required.

    :jsonparam container_serial: container serial (required).
    :jsonparam scope: full URL of the operation the challenge will be
        bound to, e.g. ``https://pi.example.com/container/synchronize``
        (required).
    :status 200: challenge payload in ``result.value`` —
        ``server_url``, ``nonce``, ``time_stamp``, and any
        type-specific extras.
    :status 400: container is not in a registered state.

    Example response::

        {
          "server_url": "https://pi.net",
          "nonce": "123456",
          "time_stamp": "2024-10-23T05:45:02.484954+00:00"
        }
    """
    # Get params
    params = request.all_data
    scope = get_required(params, "scope")
    container_serial = get_required(params, "container_serial")

    try:
        container = find_container_by_serial(container_serial)

        # Audit log
        g.audit_object.log({"container_serial": container_serial,
                            "container_type": container.type,
                            "action_detail": f"scope={scope}"})

        container_info = container.get_container_info_dict()
        registration_state = RegistrationState(container_info.get(RegistrationState.get_key()))
        if registration_state not in [RegistrationState.REGISTERED, RegistrationState.ROLLOVER,
                                      RegistrationState.ROLLOVER_COMPLETED]:
            raise ContainerNotRegistered("Container is not registered.")

        # validity time for the challenge in minutes
        challenge_ttl = int(container_info.get(CHALLENGE_TTL, "2"))

        # Create challenge
        res = container.create_challenge(scope, challenge_ttl)

        # Audit log
        g.audit_object.log({"success": True})

        return send_result(res)

    except Exception as e:
        if Match.user(
            g,
            scope=SCOPE.CONTAINER,
            action=PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE,
            user_object=request.User if hasattr(request, "User") else None).any():
            return send_error("Failed creating container challenge", error_code=Error.CONTAINER), map_error_to_code(e)
        raise


@container_blueprint.route('/synchronize', methods=['POST'])
@prepolicy(smartphone_config, request)
@event('container_synchronize', request, g)
def synchronize():
    """
    Reconcile the token list of a registered container between client
    and server. The client supplies its current token inventory; the
    server returns the diff — tokens to add (with full enroll
    information so the client can materialize them) and tokens to
    update (with the updated token details). The response also
    carries the container-side policies the client must honor
    (``container_client_rollover``,
    ``initially_add_tokens_to_container``,
    ``disable_client_token_deletion``,
    ``disable_client_container_unregister``).

    Tokens that the client cannot identify by serial may be
    identified by submitting two consecutive OTP values for HOTP,
    TOTP, or daypassword tokens.

    Synchronization completes a rollover that was initiated via
    :http:post:`/container/rollover` — when the registration state
    is ``ROLLOVER_COMPLETED`` the server flips it back to
    ``REGISTERED`` here.

    This endpoint is **anonymous** — no auth header is required. The
    caller authenticates by signing the challenge previously obtained
    from :http:post:`/container/challenge`.

    :jsonparam container_serial: container serial (required).
    :jsonparam container_dict_client: JSON-encoded dict describing
        the client's container and its tokens; see the example below.
    :status 200: synchronization payload in ``result.value`` — see
        the example below; some fields are encrypted depending on
        the container type.

    Example ``container_dict_client``::

        {
          "serial": "SMPH001",
          "type": "smartphone",
          "tokens": [
            {"serial": "TOTP001", ...},
            {"otp": ["1234", "4567"], "tokentype": "hotp"}
          ]
        }

    Example response::

        {
          "container": {"type": "smartphone", "serial": "SMPH001"},
          "tokens": {
            "add": ["enroll_url1", "enroll_url2"],
            "update": [
              {"serial": "TOTP001", "tokentype": "totp"},
              {"serial": "HOTP001", "otp": ["1234", "9876"],
               "tokentype": "hotp", "counter": 2}
            ]
          },
          "policies": {
            "container_client_rollover": true,
            "initially_add_tokens_to_container": false,
            "disable_client_token_deletion": true,
            "disable_client_container_unregister": true
          },
          "server_url": "https://pi.net"
        }
    """
    params = request.all_data
    container_serial = get_required(params, "container_serial")
    container_client_str = get_optional(params, "container_dict_client")
    container_client = json.loads(container_client_str) if container_client_str else {}

    # write client token serials to audit log
    client_serials = ", ".join(
        [token.get("serial") or str(token.get("otp")) for token in container_client.get("tokens", [])])

    try:
        container = find_container_by_serial(container_serial)

        # Audit log
        g.audit_object.log({"container_serial": container_serial,
                            "container_type": container.type,
                            "action_detail": f"client_serials={client_serials}"})

        # Get server url
        server_url = container.get_container_info_dict().get("server_url")
        if server_url is None:
            log.debug("Server url is not set in the container info. Ensure the container is registered correctly.")
            server_url = " "
        scope = create_endpoint_url(server_url, "container/synchronize")
        params.update({'scope': scope})

        # 2nd synchronization step: Validate challenge and get container diff between client and server
        container.check_challenge_response(params)
        initially_add_tokens = request.all_data.get("client_policies").get(
            PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        container_dict = container.synchronize_container_details(container_client, initially_add_tokens)

        # Write token serials to audit log
        add_serials = ", ".join([serial for serial in container_dict["tokens"]["add"]])
        equal_serials = ", ".join([token.get("serial") for token in container_dict["tokens"]["update"]])
        audit_info = f"Client: add={add_serials}, update={equal_serials}"

        # Get enroll information for missing tokens
        enroll_info = []
        org_all_data = request.all_data
        for serial in container_dict["tokens"]["add"]:
            try:
                # token rollover + get enroll url
                request.all_data = org_all_data
                enroll_url = regenerate_enroll_url(serial, request, g)
                if enroll_url:
                    enroll_info.append(enroll_url)
                else:
                    log.debug(f"Could not regenerate the enroll url for the token {serial} during synchronization of "
                              f"container {container_serial}.")
            except Exception as e:
                log.error(f"Could not regenerate the enroll url for the token {serial} during synchronization of"
                          f"container {container_serial}: {e}")
        container_dict["tokens"]["add"] = enroll_info

        # Optionally encrypt dict
        res = container.encrypt_dict(container_dict, params)
        res.update({'server_url': server_url})

        # Add policy info
        res["policies"] = request.all_data.get("client_policies")

        # Update last sync time
        container.update_last_synchronization()

        # Rollover completed: Change registration state to registered
        registration_state = RegistrationState(container.get_container_info_dict().get(RegistrationState.get_key()))
        if registration_state == RegistrationState.ROLLOVER_COMPLETED:
            container.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                    value=RegistrationState.REGISTERED.value,
                                                                    info_type=PI_INTERNAL)])
        audit_info += f", rollover: {registration_state == RegistrationState.ROLLOVER}"

        # Audit log
        g.audit_object.log({"info": audit_info,
                            "success": True})

        return send_result(res)

    except Exception as e:
        if Match.user(
            g,
            scope=SCOPE.CONTAINER,
            action=PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE,
            user_object=request.User if hasattr(request, "User") else None).any():
            return send_error("Failed container synchronization", error_code=Error.CONTAINER), map_error_to_code(e)
        raise


@container_blueprint.route('/rollover', methods=['POST'])
@prepolicy(check_client_container_action, request, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
@prepolicy(container_registration_config, request)
@event('container_init_rollover', request, g)
def rollover():
    """
    Initiate a rollover for a registered container. Rollover
    generates new secrets for every token in the container and
    returns a fresh registration payload (deep link / QR code) the
    client must consume to complete the rollover via
    :http:post:`/container/synchronize`. Used to transfer a
    container to a new device.

    The container must be in a registered state (``REGISTERED``,
    ``ROLLOVER`` or ``ROLLOVER_COMPLETED``).

    This endpoint is **anonymous** — no auth header is required. The
    client-side ``container_client_rollover`` policy (see
    :ref:`container_policy_client_rollover`) governs whether a client
    is allowed to initiate this.

    :jsonparam container_serial: container serial (required).
    :status 200: rollover payload in ``result.value``; same shape as
        the registration payload returned from
        :http:post:`/container/register/initialize`.
    :status 400: container is not in a registered state.

    Example response for a smartphone container::

        {
          "container_url": {
            "description": "URL for privacyIDEA Container Registration",
            "img": "<QR code>",
            "value": "pia://container/SMPH0006D5BC?issuer=privacyIDEA&ttl=10..."
          },
          "nonce": "c238392af49250804c25bbd7d86408839e91fe97",
          "time_stamp": "2024-12-20T09:53:40.158319+00:00",
          "server_url": "https://pi.net",
          "ttl": 10,
          "ssl_verify": "True",
          "key_algorithm": "secp384r1",
          "hash_algorithm": "sha256",
          "passphrase_prompt": ""
        }
    """
    params = request.all_data
    container_serial = get_required(params, "container_serial")
    # Params set by pre-policies
    server_url = get_optional(params, SERVER_URL)
    challenge_ttl = get_optional(params, CHALLENGE_TTL)
    registration_ttl = get_optional(params, REGISTRATION_TTL)
    ssl_verify = get_optional(params, SSL_VERIFY)

    try:
        container = find_container_by_serial(container_serial)

        # Check registration state: rollover is only allowed for registered containers
        registration_state = RegistrationState(container.get_container_info_dict().get(RegistrationState.get_key()))
        if registration_state not in [RegistrationState.REGISTERED, RegistrationState.ROLLOVER,
                                      RegistrationState.ROLLOVER_COMPLETED]:
            raise ContainerNotRegistered("Container is not registered.")

        # Rollover
        res_rollover = init_container_rollover(container, server_url, challenge_ttl, registration_ttl,
                                               ssl_verify, params)

        # Audit log
        info_str = (f"server_url={server_url}, challenge_ttl={challenge_ttl}min, "
                    f"registration_ttl={registration_ttl}min, ssl_verify={ssl_verify}, "
                    f"registration_state={registration_state.value}")
        g.audit_object.log({"container_serial": container_serial,
                            "container_type": container.type,
                            "info": info_str,
                            "success": True})

        return send_result(res_rollover)

    except Exception as e:
        if Match.user(
            g,
            scope=SCOPE.CONTAINER,
            action=PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE,
            user_object=request.User if hasattr(request, "User") else None).any():
            return send_error("Failed container rollover", error_code=Error.CONTAINER), map_error_to_code(e)
        raise


# TEMPLATES
@container_blueprint.route('/templates', methods=['GET'])
@prepolicy(check_base_action, request, action=PolicyAction.CONTAINER_TEMPLATE_LIST)
@log_with(log)
def get_template():
    """
    Return container templates, optionally filtered, paginated and
    sorted. Without pagination parameters all matching templates are
    returned at once.

    Requires authentication and the policy action
    :ref:`policy_container_template_list`.

    :query name: filter by template name.
    :query container_type: filter by container type.
    :query page: 1-indexed page number.
    :query pagesize: page size; omit for no pagination.
    :query sortdir: ``asc`` (default) or ``desc``.
    :query sortby: column to sort by, default ``name``.
    :status 200: paginated dict with ``templates`` and pagination
        metadata in ``result.value``.

    Example response::

        {
          "templates": [
            {"name": "template1", "container_type": "smartphone",
             "template_options": {"tokens": [{"type": "hotp", "genkey": true}, ...]}},
            {"name": "template2", "container_type": "yubikey", ...}
          ],
          "count": 25,
          "current": 1,
          "prev": null,
          "next": 2
        }
    """
    params = request.all_data
    name = get_optional(params, "name")
    container_type = get_optional(params, "container_type")
    page = int(get_optional(params, "page", default=0) or 0)
    pagesize = int(get_optional(params, "pagesize", default=0) or 0)
    sortdir = get_optional(params, "sortdir", default="asc")
    sortby = get_optional(params, "sortby", default="name")

    templates_dict = get_templates_by_query(name=name, container_type=container_type, page=page, pagesize=pagesize,
                                            sortdir=sortdir, sortby=sortby)

    # Audit log
    g.audit_object.log({"success": True})

    return send_result(templates_dict)


@container_blueprint.route('<string:container_type>/template/<string:template_name>', methods=['POST'])
@prepolicy(check_base_action, request, action=PolicyAction.CONTAINER_TEMPLATE_CREATE)
@log_with(log)
def create_template_with_name(container_type, template_name):
    """
    Create or update a container template. If a template with the
    given name already exists its ``template_options`` are
    overwritten; otherwise a new template is created with the
    specified container type.

    Requires authentication and the policy action
    :ref:`policy_container_template_create`.

    :param container_type: path component, the container type the
        template applies to (e.g. ``smartphone``, ``yubikey``).
    :param template_name: path component, the unique template name.
    :jsonparam template_options: dict carrying the template options
        (most importantly ``tokens`` — the list of token specs to
        create when a container is built from this template).
        Defaults to an empty dict.
    :jsonparam default: ``True`` to mark this template as the default
        for the container type.
    :status 200: ``{"template_id": <id>}`` in ``result.value``.
    :status 400: ``template_options`` is not a dictionary.
    """
    params = request.all_data
    template_options = get_optional(params, "template_options") or {}
    default_template = get_optional(params, "default", default=False)

    # Audit log
    g.audit_object.log({"container_type": container_type,
                        "action_detail": f"template_name={template_name}, default={default_template}"})

    # Check parameters
    if not isinstance(template_options, dict):
        raise ParameterError(_("'template_options' must be a dictionary!"))

    # check if name already exists
    existing_templates = get_templates_by_query(template_name)["templates"]

    if len(existing_templates) > 0:
        # update existing template
        template = get_template_obj(template_name)
        template.template_options = template_options
        template_id = template.id
        log.debug(f"A template with the name '{template_name}' already exists. Updating template options.")
        audit_info = "Updated existing template"
    else:
        # create new template
        template_id = create_container_template(container_type, template_name, template_options, default_template)
        audit_info = "Created new template"

    # Set template as default for this container type
    if default_template:
        set_default_template(template_name)

    # Audit log
    g.audit_object.log({"success": True,
                        "info": audit_info})
    return send_result({"template_id": template_id})


@container_blueprint.route('template/<string:template_name>', methods=['DELETE'])
@prepolicy(check_base_action, request, action=PolicyAction.CONTAINER_TEMPLATE_DELETE)
@log_with(log)
def delete_template(template_name):
    """
    Delete a container template. Existing containers that were
    created from this template are not affected.

    Requires authentication and the policy action
    :ref:`policy_container_template_delete`.

    :param template_name: path component, the template name.
    :status 200: ``True`` on success in ``result.value``.
    :status 404: no template with that name exists.
    """
    # Audit log
    g.audit_object.log({"action_detail": f"template_name={template_name}"})

    template = get_template_obj(template_name)
    template.delete()

    # Audit log
    g.audit_object.log({"container_type": template.get_class_type(), "success": True})

    return send_result(True)


@container_blueprint.route('template/<string:template_name>/compare', methods=['GET'])
@prepolicy(check_base_action, request, action=PolicyAction.CONTAINER_TEMPLATE_LIST)
@prepolicy(check_base_action, request, action=PolicyAction.CONTAINER_LIST)
@prepolicy(check_admin_tokenlist, request, action=PolicyAction.CONTAINER_LIST)
@log_with(log)
def compare_template_with_containers(template_name):
    """
    Compare a template against the containers built from it. The
    response carries the per-container delta of missing and extra
    tokens compared to what the template currently specifies. Only
    containers the calling principal is allowed to manage (admin's
    realms or user's own) are included.

    If ``container_serial`` is supplied, the comparison is limited to
    that single container.

    Requires authentication and both the
    :ref:`policy_container_template_list` and
    :ref:`policy_container_list` policy actions.

    :param template_name: path component, the template name.
    :query container_serial: optional, restrict to a single
        container.
    :status 200: dict keyed by container serial with the per-token
        diff in ``result.value``.

    Example response value::

        {
          "SMPH0001": {
            "tokens": {
              "missing": ["hotp"],
              "additional": ["totp"]
            }
          }
        }
    """
    allowed_realms = getattr(request, "pi_allowed_container_realms", None)
    user = request.User
    user_role = g.logged_in_user.get("role")
    container_serial = get_optional(request.all_data, "container_serial")

    # Audit log
    g.audit_object.log({"container_serial": container_serial,
                        "action_detail": f"template_name={template_name}"})

    template = get_template_obj(template_name)
    if container_serial:
        container_list = [find_container_by_serial(container_serial)]
    else:
        container_list = [create_container_from_db_object(db_container) for db_container in template.containers]

    result = {}
    for container in container_list:
        authorized = False
        if user_role == "admin":
            if allowed_realms is None:
                authorized = True
            else:
                container_realms = get_container_realms(container.serial)
                matching_realms = list(set(container_realms).intersection(allowed_realms))
                authorized = len(matching_realms) > 0
        elif user_role == "user":
            container_owners = container.get_users()
            authorized = user in container_owners

        if authorized:
            result[container.serial] = compare_template_with_container(template, container)
        else:
            log.info(f"User {user} is not authorized to access the container {container.serial}.")

    # Audit log
    g.audit_object.log({"container_type": template.get_class_type(),
                        "info": f"allowed_realms={allowed_realms}",
                        "success": True})

    return send_result(result)


@container_blueprint.route('template/tokentypes', methods=['GET'])
@log_with(log)
def get_template_token_types():
    """
    Return the container types that support templates with their
    descriptions and the token types each can hold. The response
    shape is the same as :http:get:`/container/types`, but limited
    to template-capable container types.

    Requires authentication.

    :status 200: dict keyed by container type with
        ``description`` and ``token_types`` for each, in
        ``result.value``.
    """
    token_types = {}
    template_classes = get_container_template_classes()
    descriptions = get_container_classes_descriptions()

    for container_type in template_classes:
        token_types[container_type] = {"description": descriptions[container_type],
                                       "token_types": template_classes[container_type].get_supported_token_types()}

    g.audit_object.log({"success": True})
    return send_result(token_types)
