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
from privacyidea.api.lib.policyhelper import get_pushtoken_add_config_soft
from privacyidea.api.lib.prepolicy import (check_base_action, prepolicy,
                                           check_admin_tokenlist, check_container_action)
from privacyidea.api.lib.utils import send_result, getParam, required
from privacyidea.lib.container import (find_container_by_serial, init_container, get_container_classes_descriptions,
                                       get_container_token_types, get_all_containers, add_container_info,
                                       set_container_description, set_container_states, set_container_realms,
                                       delete_container_by_serial, assign_user, unassign_user, add_token_to_container,
                                       add_multiple_tokens_to_container, remove_token_from_container,
                                       remove_multiple_tokens_from_container,
                                       create_container_dict, create_endpoint_url, get_container_classes,
                                       create_container_template, create_container_template_from_db_object,
                                       get_templates_by_query)
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.error import PolicyError, ParameterError
from privacyidea.lib.event import event
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import ACTION, Match, SCOPE
from privacyidea.lib.user import get_user_from_param
from privacyidea.models import TokenContainerTemplate

container_blueprint = Blueprint('container_blueprint', __name__)
log = logging.getLogger(__name__)

__doc__ = """
API for managing token containers
"""


@container_blueprint.route('/', methods=['GET'])
@prepolicy(check_admin_tokenlist, request, ACTION.TOKENLIST)
@prepolicy(check_admin_tokenlist, request, ACTION.CONTAINER_LIST)
@prepolicy(check_base_action, request, action=ACTION.CONTAINER_LIST)
@log_with(log)
def list_containers():
    """
    Get containers depending on the query parameters. If pagesize and page are not provided, all containers are returned
    at once.

    :query user: Username of a user assigned to the containers
    :query serial: Serial of a single container
    :query type: Type of the containers to return
    :query token_serial: Serial of a token assigned to the container
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
    sortby = getParam(param, "sortby", optional=True, default="serial")
    sortdir = getParam(param, "sortdir", optional=True, default="asc")
    psize = int(getParam(param, "pagesize", optional=True) or 0)
    page = int(getParam(param, "page", optional=True) or 0)
    no_token = getParam(param, "no_token", optional=True, default=False)
    logged_in_user_role = g.logged_in_user.get("role")
    allowed_container_realms = getattr(request, "pi_allowed_container_realms", None)
    allowed_token_realms = getattr(request, "pi_allowed_realms", None)

    result = get_all_containers(user=user, serial=cserial, ctype=ctype, token_serial=token_serial,
                                realms=allowed_container_realms,
                                sortby=sortby, sortdir=sortdir,
                                pagesize=psize, page=page)

    containers = create_container_dict(result["containers"], no_token, user, logged_in_user_role, allowed_token_realms)
    result["containers"] = containers

    g.audit_object.log({"success": True})
    return send_result(result)


@container_blueprint.route('<string:container_serial>/assign', methods=['POST'])
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_ASSIGN_USER)
@event('container_assign', request, g)
@log_with(log)
def assign(container_serial):
    """
    Assign a container to a user.

    :param: container_serial: serial of the container
    :jsonparam user: Username of the user
    :jsonparam realm: Name of the realm of the user
    """
    user = get_user_from_param(request.all_data, required)
    logged_in_user = request.User
    user_role = g.logged_in_user.get("role")
    res = assign_user(container_serial, user, logged_in_user, user_role)

    container = find_container_by_serial(container_serial)
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('<string:container_serial>/unassign', methods=['POST'])
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_UNASSIGN_USER)
@event('container_unassign', request, g)
@log_with(log)
def unassign(container_serial):
    """
    Unassign a user from a container

    :param: container_serial: serial of the container
    :jsonparam user: Username of the user
    :jsonparam realm: Realm of the user
    """
    user = get_user_from_param(request.all_data, required)
    logged_in_user = request.User
    user_role = g.logged_in_user.get("role")
    res = unassign_user(container_serial, user, logged_in_user, user_role)

    container = find_container_by_serial(container_serial)
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('init', methods=['POST'])
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_CREATE)
@event('container_init', request, g)
@log_with(log)
def init():
    """
    Create a new container.

    :jsonparam: description: Description for the container
    :jsonparam: type: Type of the container. If the type is unknown, an error will be returned
    :jsonparam: serial: Optional serial
    :jsonparam: user: Optional username to assign the container to. Requires realm param to be present as well.
    :jsonparam: realm: Optional realm to assign the container to. Requires user param to be present as well.
    """
    user_role = g.logged_in_user.get("role")
    allowed_realms = getattr(request, "pi_allowed_realms", None)
    if user_role == "admin" and allowed_realms:
        req_realm = getParam(request.all_data, "realm", optional=True)
        if not req_realm or req_realm == "":
            # The container has to be in one realm the admin is allowed to manage
            request.all_data["realm"] = allowed_realms[0]

    serial = init_container(request.all_data)
    res = {"container_serial": serial}

    # Audit log
    container = find_container_by_serial(serial)
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

    :param: container_serial: serial of the container
    """
    # Get parameters
    user = request.User
    user_role = g.logged_in_user.get("role")

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
    res = delete_container_by_serial(container_serial, user, user_role)
    g.audit_object.log({"success": res > 0})

    return send_result(True)


@container_blueprint.route('<string:container_serial>/add', methods=['POST'])
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_ADD_TOKEN)
@event('container_add_token', request, g)
@log_with(log)
def add_token(container_serial):
    """
    Add a single token to a container.

    :param: container_serial: serial of the container
    :jsonparam: serial: Serial of the token to add.
    """
    token_serial = getParam(request.all_data, "serial", optional=False, allow_empty=False)
    user = request.User
    user_role = g.logged_in_user.get("role")

    success = add_token_to_container(container_serial, token_serial, user, user_role)

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
@event('container_add_token', request, g)
@log_with(log)
def add_all_tokens(container_serial):
    """
    Add multiple tokens to a container.

    :param: container_serial: serial of the container
    :jsonparam: serial: Comma separated list of token serials
    """
    serial = getParam(request.all_data, "serial", optional=False, allow_empty=False)
    token_serials = serial.replace(' ', '').split(',')
    user = request.User
    user_role = g.logged_in_user.get("role")
    allowed_realms = getattr(request, "pi_allowed_realms", None)

    res = add_multiple_tokens_to_container(container_serial, token_serials, user, user_role, allowed_realms)

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
@event('container_remove_token', request, g)
@log_with(log)
def remove_token(container_serial):
    """
    Remove a single token from a container.

    :param: container_serial: serial of the container
    :jsonparam: serial: Serial of the token to remove.
    """
    token_serial = getParam(request.all_data, "serial", optional=False, allow_empty=False)
    user = request.User
    user_role = g.logged_in_user.get("role")

    success = remove_token_from_container(container_serial, token_serial, user, user_role)

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
@event('container_remove_token', request, g)
@log_with(log)
def remove_all_tokens(container_serial):
    """
    Remove multiple tokens from a container.

    :param: container_serial: serial of the container
    :jsonparam: serial: Comma separated list of token serials.
    """
    serial = getParam(request.all_data, "serial", optional=False, allow_empty=False)
    token_serials = serial.replace(' ', '').split(',')
    user = request.User
    user_role = g.logged_in_user.get("role")
    allowed_realms = getattr(request, "pi_allowed_realms", None)

    res = remove_multiple_tokens_from_container(container_serial, token_serials, user, user_role, allowed_realms)

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

    :param: container_serial: Serial of the container
    :jsonparam: description: New description to be set
    """
    new_description = getParam(request.all_data, "description", optional=required)
    user = request.User
    user_role = g.logged_in_user.get("role")
    set_container_description(container_serial, new_description, user, user_role)

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

    :jsonparam: states: string of comma separated states
    """
    states_string = getParam(request.all_data, "states", required, allow_empty=False)
    states_string = states_string.replace(" ", "")
    states = states_string.split(",")
    user = request.User
    user_role = g.logged_in_user.get("role")
    res = set_container_states(container_serial, states, user, user_role)

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
    state_types_exclusions = TokenContainerClass.get_state_types()
    g.audit_object.log({"success": True})
    return send_result(state_types_exclusions)


@container_blueprint.route('<string:container_serial>/realms', methods=['POST'])
@admin_required
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_REALMS)
@event('container_set_realms', request, g)
@log_with(log)
def set_realms(container_serial):
    """
    Set the realms of a container. Old realms will be deleted.

    :param: container_serial: Serial of the container
    :jsonparam: realms: comma separated string of realms, e.g. "realm1,realm2"
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


@container_blueprint.route('<string:container_serial>/lastseen', methods=['POST'])
@event('container_update_last_seen', request, g)
@log_with(log)
def update_last_seen(container_serial):
    """
    Updates the date and time for the last_seen property.

    :param: container_serial: Serial of the container
    """
    container = find_container_by_serial(container_serial)
    container.update_last_seen()

    # Audit log
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "success": True}
    g.audit_object.log(audit_log_data)
    return send_result(True)


@container_blueprint.route('<string:container_serial>/info/<key>', methods=['POST'])
@admin_required
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_INFO)
@log_with(log)
def set_container_info(container_serial, key):
    """
    Set the value of a container info key. Overwrites the old value if the key already exists.

    :param: container_serial: Serial of the container
    :param: key: Key of the container info
    :jsonparam: value: Value to set
    """
    value = getParam(request.all_data, "value", required)
    user = request.User
    user_role = g.logged_in_user.get("role")
    res = add_container_info(container_serial, key, value, user, user_role)

    # Audit log
    g.audit_object.log({"container_serial": container_serial,
                        "key": key,
                        "value": value,
                        "success": res})
    return send_result(res)


@container_blueprint.route('register/initialize', methods=['POST'])
@prepolicy(check_container_action, request, action=ACTION.CONTAINER_REGISTER)
@event('container_register_initialize', request, g)
@log_with(log)
def registration_init():
    """
    Prepares the registration of a container. It returns all information required for the container to register.

    :param: container_serial: Serial of the container
    :return: Result of the registration process as dictionary. At least the registration url for the second step is
        provided.

    An example response looks like this:
        ::

            {
                "container_registration_url": "http://test/container/register/finalize"
            }
    Further information might be provided depending on the container type.
    """
    params = request.all_data
    container_serial = getParam(params, "container_serial", required)
    container = find_container_by_serial(container_serial)
    res = {"container_serial": container_serial}

    # Get registration url for the second step
    server_url_policies = Match.generic(g, scope=SCOPE.ENROLL, action=ACTION.PI_SERVER_URL).policies()
    if len(server_url_policies) == 0:
        raise PolicyError(f"Missing enrollment policy {ACTION.PI_SERVER_URL}. Cannot register container.")
    server_url = server_url_policies[0]["action"][ACTION.PI_SERVER_URL]
    registration_url = create_endpoint_url(server_url, "container/register/finalize")
    params.update({'container_registration_url': registration_url})

    # Get validity time for the registration
    server_url_policies = Match.generic(g, scope=SCOPE.ENROLL, action=ACTION.CONTAINER_REGISTRATION_TIMEOUT).policies()
    if len(server_url_policies) > 0:
        params.update({'registration_timeout': server_url_policies[0]["action"][ACTION.CONTAINER_REGISTRATION_TIMEOUT]})

    # Initialize registration
    res_registration = container.init_registration(params)
    res.update(res_registration)
    return send_result(res)


@container_blueprint.route('register/finalize', methods=['POST'])
@event('container_register_finalize', request, g)
@log_with(log)
def registration_finalize():
    """
    This endpoint is called from a container as second step for the registration process.
    At least the container serial has to be passed in the parameters. Further parameters might be required, depending on
    the container type.

    :param: container_serial: Serial of the container
    :return: Result of the registration process as dictionary

    An example response looks like this:
        ::

            {
                "container_sync_url": "http://pi/container/sync/SMP001/init"
            }

    Depending on the container type, more information might be provided.
    """
    params = request.all_data
    container_serial = getParam(params, "container_serial", required)

    # Get container
    container = find_container_by_serial(container_serial)

    # Update params with registration url
    server_url_policies = Match.generic(g, scope=SCOPE.ENROLL, action=ACTION.PI_SERVER_URL).policies()
    if len(server_url_policies) == 0:
        raise PolicyError(f"Missing enrollment policy {ACTION.PI_SERVER_URL}. Cannot register container.")
    server_url = server_url_policies[0]["action"][ACTION.PI_SERVER_URL]
    registration_url = create_endpoint_url(server_url, "container/register/finalize")
    sync_url = create_endpoint_url(server_url, f"container/sync/{container_serial}/init")
    params.update({'container_registration_url': registration_url})

    # Validate registration
    res = container.finalize_registration(params)
    res.update({'container_sync_url': sync_url})

    # Update last seen
    container.update_last_seen()

    return send_result(res)


@container_blueprint.route('register/<string:container_serial>/terminate', methods=['DELETE'])
@event('container_register_terminate', request, g)
@log_with(log)
def registration_terminate(container_serial: str):
    """
    Terminates the synchronization of a container with privacyIDEA.

    :param container_serial: Serial of the container
    """
    container = find_container_by_serial(container_serial)
    res = container.terminate_registration()

    return send_result(res)


@container_blueprint.route('sync/<string:container_serial>/init', methods=['GET'])
@event('container_create_challenge', request, g)
@log_with(log)
def sync_init(container_serial: str):
    """
    Creates a challenge for a container to synchronize with privacyIDEA.

    :param container_serial: Serial of the container
    :return: dictionary with the required information for the synchronization

    An example response looks like this:

    ::

        {
            "container_sync_url": "http://pi/container/sync/SMP001/finalize"
        }

    Further entries are possible depending on the container type.
    """
    # Get synchronization url for the second step
    server_url_policies = Match.generic(g, scope=SCOPE.ENROLL, action=ACTION.PI_SERVER_URL).policies()
    if len(server_url_policies) == 0:
        raise PolicyError(f"Missing enrollment policy {ACTION.PI_SERVER_URL}. Cannot register container.")
    server_url = server_url_policies[0]["action"][ACTION.PI_SERVER_URL]
    synchronize_url = create_endpoint_url(server_url, f"container/sync/{container_serial}/finalize")

    # Create challenge
    container = find_container_by_serial(container_serial)
    params = request.all_data
    params.update({'scope': synchronize_url})
    res = container.init_sync(request.all_data)
    res.update({'container_sync_url': synchronize_url})

    return send_result(res)


@container_blueprint.route('sync/<string:container_serial>/finalize', methods=['POST'])
def sync_finalize(container_serial: str):
    """
    Validates the challenge if the container is authorized to synchronize. If successful, the server returns the
    container's state, including all attributes and tokens. The token secrets are also included.
    The full data is encrypted.
    Additional parameters and entries in the response are possible, depending on the container type.

    :param container_serial: Serial of the container
    :jsonparam: container_dict_client: container data with included tokens from the client like

        ::

            {
                "container": {...},
                "tokens": [{"serial": "TOTP001", "active": True,...},
                           {"otp": ["1234", "4567"], "type": "hotp"}]
            }

        The provided information may differ for different container and token types. To identify tokens at least the
        serial shall be provided. However, some clients might not have the serial. In this case, the client can provide
        a list of at least two otp values for hotp, totp and daypassword tokens.

    :return: dictionary including the container properties and the tokens like

        ::

            {
                "container":   {"states": ["active]},
                "tokens": {"add": [<enroll information token1>, <enroll information token2>, ...],
                           "update": [{"serial": "TOTP001", "active": True},
                                      {"serial": "HOTP001", "active": False,
                                       "otp": ["1234", "9876"], "type": "hotp"}]}
            }

        The provided enroll information depends on the token type as well as the returned information for the tokens
        to be updated.
    """
    request.all_data = get_pushtoken_add_config_soft(g, request.all_data)
    params = request.all_data

    # Get synchronization url for the second step
    server_url_policies = Match.generic(g, scope=SCOPE.ENROLL, action=ACTION.PI_SERVER_URL).policies()
    if len(server_url_policies) == 0:
        raise PolicyError(f"Missing enrollment policy {ACTION.PI_SERVER_URL}. Cannot register container.")
    server_url = server_url_policies[0]["action"][ACTION.PI_SERVER_URL]
    synchronize_url = create_endpoint_url(server_url, f"container/sync/{container_serial}/finalize")
    params.update({'scope': synchronize_url})

    # # Get push configuration
    # push_policy = Match.generic(g, scope=SCOPE.ENROLL, action=PUSH_ACTION.REGISTRATION_URL).policies()
    # if len(push_policy) > 0:
    #     push_registration_url = push_policy[0]["action"][PUSH_ACTION.REGISTRATION_URL]
    #     push_firebase_configuration = push_policy[0]["action"].get(PUSH_ACTION.FIREBASE_CONFIG, None)
    #     params.update({PUSH_ACTION.REGISTRATION_URL: push_registration_url,
    #                    PUSH_ACTION.FIREBASE_CONFIG: push_firebase_configuration})

    # 2nd synchronize step
    container = find_container_by_serial(container_serial)
    res = container.finalize_sync(params)
    res.update({'container_sync_url': synchronize_url})

    # Update last seen & last updated
    # Should we also update the last seen here or only if a token is used to authenticate?
    container.update_last_seen()
    container.update_last_updated()

    return send_result(res)


# TEMPLATES
@container_blueprint.route('/templates', methods=['GET'])
@log_with(log)
def get_template():
    """
    Get all container templates
    """
    # TODO: Add pagination
    params = request.all_data
    name = getParam(params, "name", optional=True)
    container_type = getParam(params, "container_type", optional=True)
    page = int(getParam(params, "page", optional=True, default=0) or 0)
    pagesize = int(getParam(params, "pagesize", optional=True, default=0) or 0)

    templates_dict = get_templates_by_query(name, container_type, page, pagesize)

    return send_result(templates_dict)


@container_blueprint.route('<string:container_type>/template/options', methods=['GET'])
@log_with(log)
def get_template_options(container_type):
    """
    Get the options for the given container type
    """
    classes = get_container_classes()
    if classes and container_type.lower() in classes.keys():
        g.audit_object.log({"success": True})
        return send_result(classes[container_type.lower()].get_container_policy_info())
    else:
        raise ParameterError("Invalid container type")


@container_blueprint.route('<string:container_type>/template', methods=['POST'])
@log_with(log)
def set_template(container_type):
    """
    Set the template for the given container type
    """
    if container_type.lower() not in ["generic", "yubikey", "smartphone"]:
        raise ParameterError("Invalid container type")

    json = request.json
    template_id = json.get('template_id')

    audit_log_data = {"container_type": container_type,
                      "success": True}
    g.audit_object.log(audit_log_data)


@container_blueprint.route('<string:container_type>/template/<string:template_name>', methods=['POST'])
@log_with(log)
def create_template_with_name(container_type, template_name):
    """
    Set the template for the given container type
    """
    params = request.all_data
    template_options = json.dumps(getParam(params, "template_options", required))
    if container_type.lower() not in ["generic", "yubikey", "smartphone"]:
        raise ParameterError("Invalid container type")

    # check if name already exists
    existing_templates = get_templates_by_query(template_name)["templates"]

    if len(existing_templates) > 0:
        # update existing template
        template_db = TokenContainerTemplate.query.filter(TokenContainerTemplate.name == template_name).first()
        template_db = create_container_template_from_db_object(template_db)
        template_db.container_type = container_type
        template_db.template_options = template_options
        template_id = template_db.id

    else:
        # create new template
        template_id = create_container_template(container_type, template_name, template_options)

    audit_log_data = {"container_type": container_type,
                      "action_detail": f"template_name={template_name}",
                      "success": True}
    g.audit_object.log(audit_log_data)
    return send_result(template_id)
