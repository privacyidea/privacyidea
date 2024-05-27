import logging

from flask import Blueprint, jsonify, request

from privacyidea.api.lib.utils import send_result, getParam, required
from privacyidea.lib.container import get_container_classes, create_container_template, \
    find_container_by_serial, init_container, get_container_classes_descriptions, \
    get_container_token_types, get_all_containers_paginate, remove_tokens_from_container
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.token import get_one_token, get_tokens, \
    convert_token_objects_to_dicts
from privacyidea.lib.user import get_user_from_param, get_username

container_blueprint = Blueprint('container_blueprint', __name__)
log = logging.getLogger(__name__)

__doc__ = """
API for managing token containers
"""


@container_blueprint.route('/', methods=['GET'])
@log_with(log)
def list_containers():
    """
    Get all containers
    """
    param = request.all_data
    user = request.User
    serial = getParam(param, "serial", optional=True)
    type = getParam(param, "type", optional=True)
    token_serial = getParam(param, "token_serial", optional=True)
    sortby = getParam(param, "sortby", optional=True, default="serial")
    sortdir = getParam(param, "sortdir", optional=True, default="asc")
    psize = int(getParam(param, "pagesize", optional=True, default=15))
    page = int(getParam(param, "page", optional=True, default=1))
    containers_paginated = get_all_containers_paginate(user=user, serial=serial, type=type, token_serial=token_serial,
                                                       sortby=sortby, sortdir=sortdir,
                                                       pagesize=psize, page=page)

    res: list = []
    for container in containers_paginated["containers"]:
        tmp: dict = {"type": container.type,
                     "serial": container.serial,
                     "description": container.description,
                     "last_seen": container.last_seen,
                     "last_updated": container.last_updated}
        tmp_users: dict = {}
        users: list = []
        for user in container.get_users():
            tmp_users["user_name"] = get_username(user.uid, user.resolver)
            tmp_users["user_realm"] = user.realm
            tmp_users["user_resolver"] = user.resolver
            tmp_users["user_id"] = user.login
            users.append(tmp_users)
        tmp["users"] = users

        token_serials = [token.get_serial() for token in container.get_tokens()]
        tokens_dict_list = []
        if len(token_serials) > 0:
            tokens = get_tokens(serial_list=token_serials)
            tokens_dict_list = convert_token_objects_to_dicts(tokens)
        tmp["tokens"] = tokens_dict_list

        states: list = []
        for token_container_state in container.get_states():
            states.append(token_container_state.state)
        tmp["states"] = states

        infos: dict = {}
        for info in container.get_containerinfo():
            if info.type:
                infos[info.key + ".type"] = info.type
            infos[info.key] = info.value
        tmp["info"] = infos

        res.append(tmp)
    containers_paginated["containers"] = res
    return send_result(containers_paginated)


@container_blueprint.route('assign', methods=['POST'])
@log_with(log)
def assign():
    """
    Assign a container to a user

    :jsonparam serial: Serial of the container
    :jsonparam user: Username of the user
    :jsonparam realm: Realm of the user
    """
    user = get_user_from_param(request.all_data, required)
    serial = getParam(request.all_data, "serial", required, allow_empty=False)
    container = find_container_by_serial(serial)
    res = container.add_user(user)
    return send_result(res)


@container_blueprint.route('unassign', methods=['POST'])
@log_with(log)
def unassign():
    """
    Unassign a user from a container

    :jsonparam serial: Serial of the container
    :jsonparam user: Username of the user
    :jsonparam realm: Realm of the user
    """
    user = get_user_from_param(request.all_data, required)
    serial = getParam(request.all_data, "serial", required, allow_empty=False)
    container = find_container_by_serial(serial)
    res = container.remove_user(user)
    return send_result(res)


@container_blueprint.route('init', methods=['POST'])
@log_with(log)
def init():
    """
    Create a new container

    :jsonparam: description: Description for the container
    :jsonparam: type: Type of the container. If the type is unknown, an error will be returned
    :jsonparam: serial: Optional serial
    :jsonparam: user: Optional username to assign the container to. Requires realm param to be present as well.
    :jsonparam: realm: Optional realm to assign the container to. Requires user param to be present as well.
    """
    serial = init_container(request.all_data)
    res = {"serial": serial}
    return send_result(res)


@container_blueprint.route('<string:container_serial>', methods=['DELETE'])
@log_with(log)
def delete(container_serial):
    """
    Delete a container.
    """
    container = find_container_by_serial(container_serial)
    container.delete()
    return send_result(True)


@container_blueprint.route('<string:container_serial>/add', methods=['POST'])
@log_with(log)
def add_token(container_serial):
    """
    Add a token to a container
    :jsonparam: serial: Serial of the token to add
    """
    container = find_container_by_serial(container_serial)
    serial = getParam(request.all_data, "serial", required, allow_empty=False)
    token = get_one_token(serial=serial)
    res = False
    if token:
        container.add_token(token)
        res = True
    return send_result(res)


@container_blueprint.route('<string:container_serial>/remove', methods=['POST'])
@log_with(log)
def remove_token(container_serial):
    """
    Remove a token from a container
    :jsonparam: serial: Serial of the token to remove
    """
    serial = getParam(request.all_data, "serial", optional=True, allow_empty=True)
    serials = getParam(request.all_data, "serial_list", optional=True, allow_empty=True)
    if not serial and not serials:
        raise ParameterError("Either serial or serial_list is required")
    token_serials = []
    if serials:
        token_serials = serials
    if serial:
        token_serials.append(serial)

    res = remove_tokens_from_container(container_serial, token_serials)
    return send_result(res)


@container_blueprint.route('types', methods=['GET'])
@log_with(log)
def get_types():
    descriptions = get_container_classes_descriptions()
    return send_result(descriptions)


@container_blueprint.route('tokentypes', methods=['GET'])
@log_with(log)
def get_token_types():
    """
    Get the supported token types for each container type
    """
    res = get_container_token_types()
    return send_result(res)


@container_blueprint.route('/description/<serial>', methods=['POST'])
@log_with(log)
def set_description(serial):
    """
    Set the description of a container
    :jsonparam: serial: Serial of the container
    :jsonparam: description: New description to be set
    """
    container = find_container_by_serial(serial)
    new_description = getParam(request.all_data, "description", optional=required, allow_empty=False)
    res = False
    if new_description:
        container.description = new_description
        res = True
    return send_result(res)


@container_blueprint.route('/states', methods=['POST'])
@log_with(log)
def set_states():
    """
    Set the states of a container
    :jsonparam: serial: Serial of the container
    :jsonparam: states: string list
    """
    serial = getParam(request.all_data, "serial", required, allow_empty=False)
    states = getParam(request.all_data, "states", required, allow_empty=False)
    container = find_container_by_serial(serial)

    res = False
    if states:
        container.set_states(states)
        res = True

    return send_result(res)


@container_blueprint.route('statetypes', methods=['GET'])
@log_with(log)
def get_state_types():
    """
    Get the supported state types as dictionary
    The types are the keys and the value is a list containing all states that are excluded when the key state is
    selected
    """
    state_types_exclusions = TokenContainerClass.get_state_types()
    return send_result(state_types_exclusions)


@container_blueprint.route('/lastSeen/<serial>', methods=['POST'])
@log_with(log)
def update_last_seen(serial):
    """
    Updates the date and time for the last_seen property
    :jsonparam: serial: Serial of the container
    """
    container = find_container_by_serial(serial)
    container.update_last_seen()
    return send_result(True)


######################## vvv TEMPLATES vvv ##########################
@container_blueprint.route('<string:container_type>/template', methods=['GET'])
@log_with(log)
def get_template(container_type):
    """
    Get the template for the given container type
    """
    return ""


@container_blueprint.route('<string:container_type>/template/options', methods=['GET'])
@log_with(log)
def get_template_options(container_type):
    """
    Get the options for the given container type
    """
    classes = get_container_classes()
    if classes and container_type.lower() in classes.keys():
        return jsonify(classes[container_type.lower()].get_container_policy_info())
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
    print(json)
    template_id = json.get('template_id')


@container_blueprint.route('<string:container_type>/template/<string:template_name>', methods=['POST'])
@log_with(log)
def create_template_with_name(container_type, template_name):
    """
    Set the template for the given container type
    """
    json = request.json
    print(json)
    template_id = create_container_template(container_type, template_name, json)
    return template_id
