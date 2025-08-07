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
import json
import logging

from flask import Blueprint, request, g

from privacyidea.api.auth import admin_required
from privacyidea.api.lib.prepolicy import (check_base_action, prepolicy, check_user_params, check_token_action,
                                           check_admin_tokenlist, check_container_action, check_token_list_action,
                                           check_container_register_rollover, container_registration_config,
                                           smartphone_config, check_client_container_action, hide_tokeninfo,
                                           check_client_container_disabled_action, hide_container_info)
from privacyidea.api.lib.utils import send_result, getParam, required, get_required_one_of
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
from privacyidea.lib.error import ParameterError, ContainerNotRegistered
from privacyidea.lib.event import event
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import ACTION
from privacyidea.lib.token import regenerate_enroll_url
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.utils import is_true

container_blueprint = Blueprint('container_blueprint', __name__)
log = logging.getLogger(__name__)

__doc__ = """
API for managing token containers
"""


@container_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, action=ACTION.CONTAINER_LIST)
@prepolicy(check_admin_tokenlist, request, ACTION.CONTAINER_LIST)
@prepolicy(check_admin_tokenlist, request, ACTION.TOKENLIST)
@prepolicy(hide_container_info, request)
@prepolicy(hide_tokeninfo, request)
@log_with(log)
def list_containers():
    """
    Get containers depending on the query parameters. If pagesize and page are not provided, all containers are returned
    at once.

    :query user: Username of a user assigned to the containers
    :query container_serial: Serial of a single container (case-insensitive, can contain '*' as wildcards)
    :query type: Type of the containers to return (case-insensitive, can contain '*' as wildcards)
    :query token_serial: Serial of a token assigned to the container (case-insensitive, can contain '*' as wildcards)
    :query template: Name of the template the container is created from (case-sensitive, can contain '*' as wildcards)
    :query container_realm: Name of the realm the container is assigned to (case-insensitive, can contain '*' as
        wildcards)
    :query description: Description of the container (case-insensitive, can contain '*' as wildcards)
    :query resolver: Resolver of the user assigned to the container  (case-insensitive, can contain '*' as wildcards)
    :query assigned: Filter for assigned or unassigned containers (True or False)
    :query info_key: Key of the container info (case-sensitive, can contain '*' as wildcards)
    :query info_value: Value of the container info (case-insensitive, can contain '*' as wildcards)
    :query last_auth_delta: The maximum time difference the last authentication may have to now, e.g. "1y", "14d", "1h"
        The following units are supported: y (years), d (days), h (hours), m (minutes), s (seconds)
    :query last_sync_delta: The maximum time difference the last synchronization may have to now, e.g. "1y", "14d", "1h"
        The following units are supported: y (years), d (days), h (hours), m (minutes), s (seconds)
    :query state: State the container should have (case-insensitive and allows "*" as wildcard), optional
    :query sortby: Sort by a container attribute (serial or type)
    :query sortdir: Sort direction (asc or desc)
    :query pagesize: Number of containers per page
    :query page: Page number
    :query no_token: no_token=1: Do not return tokens assigned to the container
    """
    param = request.all_data
    user = request.User
    cserial = getParam(param, "container_serial", optional=True)
    ctype = getParam(param, "type", optional=True)
    token_serial = getParam(param, "token_serial", optional=True)
    template = getParam(param, "template", optional=True)
    realm = getParam(param, "container_realm", optional=True)
    description = getParam(param, "description", optional=True)
    resolver = getParam(param, "resolver", optional=True)
    assigned = getParam(param, "assigned", optional=True)
    if assigned is not None:
        assigned = is_true(assigned)
    info_key = getParam(param, "info_key", optional=True)
    info_value = getParam(param, "info_value", optional=True)
    last_auth_delta = getParam(param, "last_auth_delta", optional=True)
    last_sync_delta = getParam(param, "last_sync_delta", optional=True)
    state = getParam(param, "state", optional=True)
    sortby = getParam(param, "sortby", optional=True, default="serial")
    sortdir = getParam(param, "sortdir", optional=True, default="asc")
    psize = int(getParam(param, "pagesize", optional=True) or 0)
    page = int(getParam(param, "page", optional=True) or 0)
    no_token = getParam(param, "no_token", optional=True, default=False)
    logged_in_user_role = g.logged_in_user.get("role")
    allowed_container_realms = getattr(request, "pi_allowed_container_realms", None)
    allowed_token_realms = getattr(request, "pi_allowed_realms", None)
    hide_container_info = getParam(param, "hide_container_info", optional=True)
    hide_token_info = getParam(param, "hidden_tokeninfo", optional=True)

    # Set info dictionary (if either key or value is None, filter for all keys/values using * as wildcard)
    info = None
    if info_key or info_value:
        info = {info_key or "*": info_value or "*"}

    result = get_all_containers(user=user, serial=cserial, ctype=ctype, token_serial=token_serial,
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
@prepolicy(check_user_params, request, action=ACTION.CONTAINER_ASSIGN_USER)
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_ASSIGN_USER)
@event('container_assign', request, g)
@log_with(log)
def assign(container_serial):
    """
    Assign a container to a user.

    :param container_serial: serial of the container
    :jsonparam user: Username of the user
    :jsonparam realm: Name of the realm of the user
    """
    user = get_user_from_param(request.all_data, required)
    res = assign_user(container_serial, user)

    container = find_container_by_serial(container_serial)
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('<string:container_serial>/unassign', methods=['POST'])
@prepolicy(check_user_params, request, action=ACTION.CONTAINER_UNASSIGN_USER)
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_UNASSIGN_USER)
@event('container_unassign', request, g)
@log_with(log)
def unassign(container_serial):
    """
    Unassign a user from a container
    In case the user does not exist anymore, the user_id is required.

    :param container_serial: serial of the container
    :jsonparam user: Username of the user
    :jsonparam realm: Realm of the user
    :jsonparam resolver: Resolver of the user
    :jsonparam user_id: User ID of the user, to be able to unassign non-existing users
    """
    # Get user
    user = request.User
    # The user id is not set in before_request, but is required to remove users that do not exist (anymore)
    user_id = request.all_data.get("user_id", None)
    if user_id:
        user.uid = str(user_id)

    # Check if required parameter is present
    _ = get_required_one_of(request.all_data, ["user", "user_id"])
    if user.login and not user.realm and not user.resolver and not user.uid:
        raise ParameterError("Missing parameter 'realm', 'resolver', and/or 'user_id'")

    res = unassign_user(container_serial, user)

    container = find_container_by_serial(container_serial)
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('init', methods=['POST'])
@prepolicy(check_admin_tokenlist, request, action=ACTION.CONTAINER_CREATE)
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_CREATE)
@event('container_init', request, g)
@log_with(log)
def init():
    """
    Create a new container.
    Raises an EnrollmentError if an invalid type or an already existing serial is provided.

    To create a container from a template, the template can either be passed as a dictionary, containing all necessary
    information for all tokens or only the name of an already existing template in the db. If both are given, a
    ParameterError is raised.

    :jsonparam description: Description for the container
    :jsonparam type: Type of the container. If the type is unknown, an error will be returned
    :jsonparam container_serial: Optional unique serial (not case-sensitive)
    :jsonparam user: Optional username to assign the container to. Requires realm param to be present as well.
    :jsonparam realm: Optional realm to assign the container to. Requires user param to be present as well.
    :jsonparam template: The template to create the container from (dictionary), optional
    :jsonparam template_name: The name of the template to create the container from, optional
    :jsonparam options: Options for the container if no template is used (dictionary), optional
    """
    user_role = g.logged_in_user.get("role")
    allowed_realms = getattr(request, "pi_allowed_realms", None)
    if user_role == "admin" and allowed_realms:
        req_realm = getParam(request.all_data, "realm", optional=True)
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
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_DELETE)
@event('container_delete', request, g)
@log_with(log)
def delete(container_serial):
    """
    Delete a container.

    :param container_serial: serial of the container
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
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_ADD_TOKEN)
@prepolicy(check_token_action, request, action=ACTION.CONTAINER_ADD_TOKEN)
@event('container_add_token', request, g)
@log_with(log)
def add_token(container_serial):
    """
    Add a single token to a container.

    :param container_serial: serial of the container
    :jsonparam serial: Serial of the token to add.
    """
    token_serial = getParam(request.all_data, "serial", optional=False, allow_empty=False)

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
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_ADD_TOKEN)
@prepolicy(check_token_list_action, request, action=ACTION.CONTAINER_ADD_TOKEN)
@event('container_add_token', request, g)
@log_with(log)
def add_all_tokens(container_serial):
    """
    Add multiple tokens to a container.

    :param container_serial: serial of the container
    :jsonparam serial: Comma separated list of token serials
    """
    serial = getParam(request.all_data, "serial", optional=False, allow_empty=False)
    token_serials = serial.replace(' ', '').split(',')

    res = add_multiple_tokens_to_container(container_serial, token_serials)

    not_authorized_serials = getParam(request.all_data, "not_authorized_serials", optional=True)
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
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_REMOVE_TOKEN)
@prepolicy(check_token_action, request, action=ACTION.CONTAINER_REMOVE_TOKEN)
@event('container_remove_token', request, g)
@log_with(log)
def remove_token(container_serial):
    """
    Remove a single token from a container.

    :param container_serial: serial of the container
    :jsonparam serial: Serial of the token to remove.
    """
    token_serial = getParam(request.all_data, "serial", optional=False, allow_empty=False)

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
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_REMOVE_TOKEN)
@prepolicy(check_token_list_action, request, action=ACTION.CONTAINER_REMOVE_TOKEN)
@event('container_remove_token', request, g)
@log_with(log)
def remove_all_tokens(container_serial):
    """
    Remove multiple tokens from a container.

    :param container_serial: serial of the container
    :jsonparam serial: Comma separated list of token serials.
    """
    # allow serial to be empty if the pre-policy removes all tokens
    serial = getParam(request.all_data, "serial", optional=False, allow_empty=True)
    token_serials = serial.replace(' ', '').split(',')

    res = remove_multiple_tokens_from_container(container_serial, token_serials)

    not_authorized_serials = getParam(request.all_data, "not_authorized_serials", optional=True)
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
    Returns a dictionary with the container types as keys and their descriptions and supported token types as values.

    ::

        {
            type: { description: "Description", token_types: ["hotp", "totp", "push", "daypassword", "sms"] },
            type: { description: "Description", token_types: ["hotp", "totp", "push", "daypassword", "sms"] }
        }
    """
    descriptions = get_container_classes_descriptions()
    ttypes = get_container_token_types()
    res = {ctype: {"description": desc, "token_types": ttypes.get(ctype, [])} for ctype, desc in descriptions.items()}
    g.audit_object.log({"success": True})
    return send_result(res)


@container_blueprint.route('<string:container_serial>/description', methods=['POST'])
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_DESCRIPTION)
@event('container_set_description', request, g)
@log_with(log)
def set_description(container_serial):
    """
    Set the description of a container.

    :param container_serial: Serial of the container
    :jsonparam description: New description to be set
    """
    new_description = getParam(request.all_data, "description", optional=required)
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
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_STATE)
@event('container_set_states', request, g)
@log_with(log)
def set_states(container_serial):
    """
    Set the states of a container.

    :jsonparam states: string of comma separated states
    """
    states_string = getParam(request.all_data, "states", required, allow_empty=False)
    states_string = states_string.replace(" ", "")
    states = states_string.split(",")
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
    Get the supported state types as dictionary.
    The types are the keys and the value is a list containing all states that are excluded when the key state is
    selected.
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
@prepolicy(check_admin_tokenlist, request, action=ACTION.CONTAINER_REALMS)
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_REALMS)
@event('container_set_realms', request, g)
@log_with(log)
def set_realms(container_serial):
    """
    Set the realms of a container. Old realms will be deleted.

    :param container_serial: Serial of the container
    :jsonparam realms: comma separated string of realms, e.g. "realm1,realm2"
    """
    # Get parameters
    container_realms = getParam(request.all_data, "realms", required, allow_empty=True)
    realm_list = [r.strip() for r in container_realms.split(",")]
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
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_INFO)
@log_with(log)
def set_container_info(container_serial, key):
    """
    Set the value of a container info key. Overwrites the old value if the key already exists.
    However, existing entries of type PI_INTERNAL are not overwritten and a PolicyError is raised.

    :param container_serial: Serial of the container
    :param key: Key of the container info
    :jsonparam value: Value to set
    """
    value = getParam(request.all_data, "value", required)
    res = add_container_info(container_serial, key, value)

    # Audit log
    g.audit_object.log({"container_serial": container_serial,
                        "key": key,
                        "value": value,
                        "success": res})
    return send_result(res)


@container_blueprint.route('<string:container_serial>/info/delete/<key>', methods=['DELETE'])
@admin_required
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_INFO)
@log_with(log)
def delete_container_info_entry(container_serial, key):
    """
    Deletes the container info for the given key. Entries of type PI_INTERNAL can not be deleted.

    :param container_serial: Serial of the container
    :param key: Key of the container info
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
    Prepares the registration of a container. It returns all information required for the container to register.

    :jsonparam container_serial: Serial of the container
    :return: Result of the registration process as dictionary. The information may differ depending on the container
        type.

    An example response for smartphones looks like this:
        ::

            {
                "container_url": {"description": "URL for privacyIDEA Container Registration",
                                  "img": <QR code>,
                                  "value": "pia://container/SMPH0006D5BC?issuer=privacyIDEA&ttl=10..."},
                "nonce": "c238392af49250804c25bbd7d86408839e91fe97",
                "time_stamp": "2024-12-20T09:53:40.158319+00:00",
                "server_url": "https://pi.net",
                "ttl": 10,
                "ssl_verify": "True",
                "key_algorithm": "secp384r1",
                "hash_algorithm": "sha256"
            }
    """
    params = request.all_data
    container_serial = getParam(params, "container_serial", required)
    container_rollover = getParam(params, "rollover", optional=True)
    container = find_container_by_serial(container_serial)
    # Params set by pre-policies
    server_url = getParam(params, SERVER_URL)
    challenge_ttl = getParam(params, CHALLENGE_TTL)
    registration_ttl = getParam(params, REGISTRATION_TTL)
    ssl_verify = getParam(params, SSL_VERIFY)

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
    This endpoint is called from a container as second step for the registration process.
    At least the container serial has to be passed in the parameters. Further parameters might be required depending on
    the container type.

    :jsonparam container_serial: Serial of the container
    :return: Result of the registration process as dictionary. The information may differ depending on the container
        type.
    """
    params = request.all_data
    container_serial = getParam(params, "container_serial", required)

    res = finalize_registration(container_serial, params)

    # Add policy information to the response
    res["policies"] = request.all_data.get("client_policies", {})

    # Audit log
    container = find_container_by_serial(container_serial)
    g.audit_object.log({"container_serial": container_serial,
                        "container_type": container.type,
                        "success": res})
    return send_result(res)


@container_blueprint.route('register/<string:container_serial>/terminate', methods=['POST'])
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_UNREGISTER)
@event('container_unregister', request, g)
@log_with(log)
def registration_terminate(container_serial: str):
    """
    Terminates the synchronization of a container with privacyIDEA.

    :param container_serial: Serial of the container
    :return: dictionary with success information such as
        ::

            {"success": True}
    """
    container = find_container_by_serial(container_serial)

    res = unregister(container)

    # Audit log
    g.audit_object.log({"container_serial": container_serial,
                        "container_type": container.type,
                        "success": res})

    return send_result({"success": res})


@container_blueprint.route('register/terminate/client', methods=['POST'])
@prepolicy(check_client_container_disabled_action, request, action=ACTION.DISABLE_CLIENT_CONTAINER_UNREGISTER)
@event('container_unregister', request, g)
@log_with(log)
def registration_terminate_client():
    """
    Terminates the synchronization of a container with privacyIDEA.
    This endpoint can only be called from clients that are registered at the container, providing a valid signature.

    :jsonparam container_serial: Serial of the container
    :jsonparam signature: Signature of the client
    :return: dictionary with success information such as
        ::

            {"success": True}
    """
    params = request.all_data
    container_serial = getParam(params, "container_serial", required)
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


@container_blueprint.route('/challenge', methods=['POST'])
@event('container_create_challenge', request, g)
@log_with(log)
def create_challenge():
    """
    Creates a challenge for a container.

    :jsonparam container_serial: Serial of the container
    :jsonparam scope: Scope of the challenge, e.g. 'https://pi.com/container/synchronize'
    :return: dictionary with the challenge information

    An example response looks like this:

    ::

        {
            "server_url": "https://pi.net"
            "nonce": "123456",
            "time_stamp": "2024-10-23T05:45:02.484954+00:00",
        }

    """
    # Get params
    params = request.all_data
    scope = getParam(params, "scope", optional=False)
    container_serial = getParam(params, "container_serial", optional=False)
    container = find_container_by_serial(container_serial)

    # Audit log
    g.audit_object.log({"container_serial": container_serial,
                        "container_type": container.type,
                        "action_detail": f"scope={scope}"})

    container_info = container.get_container_info_dict()
    registration_state = RegistrationState(container_info.get(RegistrationState.get_key()))
    if registration_state not in [RegistrationState.REGISTERED, RegistrationState.ROLLOVER,
                                  RegistrationState.ROLLOVER_COMPLETED]:
        raise ContainerNotRegistered(f"Container is not registered.")

    # validity time for the challenge in minutes
    challenge_ttl = int(container_info.get(CHALLENGE_TTL, "2"))

    # Create challenge
    res = container.create_challenge(scope, challenge_ttl)

    # Audit log
    g.audit_object.log({"success": True})

    return send_result(res)


@container_blueprint.route('/synchronize', methods=['POST'])
@prepolicy(smartphone_config, request)
@event('container_synchronize', request, g)
def synchronize():
    """
    Compares the client tokens with the server tokens and returns the differences. Returns a dictionary with the
    container properties and the tokens to be added or updated. For the tokens to be added, the enroll information is
    provided containing the tokens secret. For the tokens to be updated, the token details are returned as dictionary.
    Additionally, the container rights read from the policies are included in the response.
    Additional parameters and entries in the response are possible, depending on the container type.
    The container is only authorized to synchronize if the challenge is valid.

    :jsonparam container_serial: Serial of the container
    :jsonparam container_dict_client: container data with included tokens from the client. The provided information
        may differ for different container and token types. To identify tokens at least the serial shall be provided.
        However, some clients might not have the serial. In this case, the client can provide a list of at least two
        otp values for hotp, totp and daypassword tokens.

    An example container_dict_client looks like this:
        ::

            {
                "serial": "SMPH001",
                "type": "smartphone",
                "tokens": [{"serial": "TOTP001", ...},
                           {"otp": ["1234", "4567"], "tokentype": "hotp"}]
            }

    :return: dictionary including the container properties, the tokens and the container policies.
        The provided enroll information depends on the token type as well as the returned information for the tokens to
        be updated.

    Example response:
        ::

            {
                "container": {"type": "smartphone", "serial": "SMPH001"},
                    "tokens": {"add": ["enroll_url1", "enroll_url2"],
                               "update": [{"serial": "TOTP001", "tokentype": "totp"},
                                          {"serial": "HOTP001", "otp": ["1234", "9876"],
                                           "tokentype": "hotp", "counter": 2}]}
                "policies": {"container_client_rollover": True,
                             "initially_add_tokens_to_container": False,
                             "disable_client_token_deletion": True,
                             "disable_client_container_unregister": True}
            }

    """
    params = request.all_data
    container_serial = getParam(params, "container_serial", optional=False)
    container_client_str = getParam(params, "container_dict_client", optional=True)
    container_client = json.loads(container_client_str) if container_client_str else {}

    # write client token serials to audit log
    client_serials = ", ".join(
        [token.get("serial") or str(token.get("otp")) for token in container_client.get("tokens", [])])

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
    initially_add_tokens = request.all_data.get("client_policies").get(ACTION.INITIALLY_ADD_TOKENS_TO_CONTAINER)
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


@container_blueprint.route('/rollover', methods=['POST'])
@prepolicy(check_client_container_action, request, action=ACTION.CONTAINER_CLIENT_ROLLOVER)
@prepolicy(container_registration_config, request)
@event('container_init_rollover', request, g)
def rollover():
    """
    Initiate a rollover for a container which will generate new token secrets for all tokens in the container.
    The data or QR code is returned for the container to re-register.
    This endpoint can be used to transfer a container from one device to another.
    Parameters and entries in the returned dictionary are container type specific.

    :jsonparam container_serial: Serial of the container
    :return: Result of the rollover process as dictionary. The information may differ depending on the container
        type.

    An example response for smartphones looks like this:
        ::

            {
                "container_url": {"description": "URL for privacyIDEA Container Registration",
                                  "img": <QR code>,
                                  "value": "pia://container/SMPH0006D5BC?issuer=privacyIDEA&ttl=10..."},
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
    container_serial = getParam(params, "container_serial", optional=False)
    container = find_container_by_serial(container_serial)
    # Params set by pre-policies
    server_url = getParam(params, SERVER_URL)
    challenge_ttl = getParam(params, CHALLENGE_TTL)
    registration_ttl = getParam(params, REGISTRATION_TTL)
    ssl_verify = getParam(params, SSL_VERIFY)

    # Check registration state: rollover is only allowed for registered containers
    registration_state = RegistrationState(container.get_container_info_dict().get(RegistrationState.get_key()))
    if registration_state not in [RegistrationState.REGISTERED, RegistrationState.ROLLOVER,
                                  RegistrationState.ROLLOVER_COMPLETED]:
        raise ContainerNotRegistered(f"Container is not registered.")

    # Rollover
    res_rollover = init_container_rollover(container, server_url, challenge_ttl, registration_ttl, ssl_verify, params)

    # Audit log
    info_str = (f"server_url={server_url}, challenge_ttl={challenge_ttl}min, registration_ttl={registration_ttl}min, "
                f"ssl_verify={ssl_verify}, registration_state={registration_state.value}")
    g.audit_object.log({"container_serial": container_serial,
                        "container_type": container.type,
                        "info": info_str,
                        "success": True})

    return send_result(res_rollover)


# TEMPLATES
@container_blueprint.route('/templates', methods=['GET'])
@prepolicy(check_base_action, request, action=ACTION.CONTAINER_TEMPLATE_LIST)
@log_with(log)
def get_template():
    """
    Get all container templates filtered by the given parameters.

    :query name: Name of the template, optional
    :query container_type: Type of the container, optional
    :query page: Number of the page (starts with 1), optional
    :query pagesize: Number of templates displayed per page, optional
    :query sortdir: Sort direction, optional, default is "asc"
    :query sortby: column name to sort by, optional, default is "name"

    :return: Dictionary with at least an entry "templates" and further entries if pagination is used.

    An example response looks like this:
    ::

        {
            "templates": [{"name": "template1", "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}, ...]}, ...},
                           {"name": "template2", "container_type": "yubikey", ...},
                           ...],
            "count": 25,
            "current": 1,
            "prev": null,
            "next": 2,
        }
    """
    params = request.all_data
    name = getParam(params, "name", optional=True)
    container_type = getParam(params, "container_type", optional=True)
    page = int(getParam(params, "page", optional=True, default=0) or 0)
    pagesize = int(getParam(params, "pagesize", optional=True, default=0) or 0)
    sortdir = getParam(params, "sortdir", optional=True, default="asc")
    sortby = getParam(params, "sortby", optional=True, default="name")

    templates_dict = get_templates_by_query(name=name, container_type=container_type, page=page, pagesize=pagesize,
                                            sortdir=sortdir, sortby=sortby)

    # Audit log
    g.audit_object.log({"success": True})

    return send_result(templates_dict)


@container_blueprint.route('<string:container_type>/template/<string:template_name>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.CONTAINER_TEMPLATE_CREATE)
@log_with(log)
def create_template_with_name(container_type, template_name):
    """
    Creates a template for the given name. If a template with this name already exists, the template options will be
    updated.

    :param container_type: Type of the container
    :param template_name: Name of the template
    :jsonparam template_options: Dictionary with the template options
    :jsonparam default: Set this template as default for the container type
    :return: ID of the created template or the template that was updated as dictionary such as
        ::

            {
                "template_id": 1
            }
    """
    params = request.all_data
    template_options = getParam(params, "template_options", optional=True) or {}
    default_template = getParam(params, "default", optional=True, default=False)

    # Audit log
    g.audit_object.log({"container_type": container_type,
                        "action_detail": f"template_name={template_name}, default={default_template}"})

    # Check parameters
    if not isinstance(template_options, dict):
        raise ParameterError("'template_options' must be a dictionary!")

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
@prepolicy(check_base_action, request, action=ACTION.CONTAINER_TEMPLATE_DELETE)
@log_with(log)
def delete_template(template_name):
    """
    Deletes the template of the given name.

    :return: True if the template was deleted successfully, raises an exception otherwise
    """
    # Audit log
    g.audit_object.log({"action_detail": f"template_name={template_name}"})

    template = get_template_obj(template_name)
    template.delete()

    # Audit log
    g.audit_object.log({"container_type": template.get_class_type(),
                        "success": True})

    return send_result(True)


@container_blueprint.route('template/<string:template_name>/compare', methods=['GET'])
@prepolicy(check_base_action, request, action=ACTION.CONTAINER_TEMPLATE_LIST)
@prepolicy(check_base_action, request, action=ACTION.CONTAINER_LIST)
@prepolicy(check_admin_tokenlist, request, action=ACTION.CONTAINER_LIST)
@log_with(log)
def compare_template_with_containers(template_name):
    """
    Compares a template with its created containers.
    Only containers the user is allowed to manage are included in the comparison.

    If a container serial is provided, only this container will be compared to the template.

    :param template_name: Name of the template
    :jsonparam container_serial: Serial of the container to compare with the template, optional
    :return: A dictionary with the differences between the template and each container in the format:

        ::

            {"SMPH0001": {
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
    container_serial = getParam(request.all_data, "container_serial", optional=True)

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
    Returns a dictionary with the template container types as keys and their description and supported token types as
    values.

    ::

        {
            <type>: { description: "Description", token_types: ["hotp", "totp", "push", "daypassword", "sms"] },
            <type>: { description: "Description", token_types: ["hotp", "totp", "push", "daypassword", "sms"] }
        }

    """
    token_types = {}
    template_classes = get_container_template_classes()
    descriptions = get_container_classes_descriptions()

    for container_type in template_classes:
        token_types[container_type] = {"description": descriptions[container_type],
                                       "token_types": template_classes[container_type].get_supported_token_types()}

    g.audit_object.log({"success": True})
    return send_result(token_types)
