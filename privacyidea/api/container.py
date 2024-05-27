import logging

from flask import Blueprint, jsonify, request

from privacyidea.api.lib.utils import send_result, getParam, required
from privacyidea.lib.container import get_container_classes, create_container_template, \
    find_container_by_serial, init_container, get_container_classes_descriptions, \
    get_container_token_types, get_all_containers, add_tokens_to_container
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
    Get containers depending on the query parameters. If pagesize and page are not provided, all containers are returned
    at once.

    :query user: Username of a user assigned to the containers
    :query serial: Serial of a single the container
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
    serial = getParam(param, "serial", optional=True)
    ctype = getParam(param, "type", optional=True)
    token_serial = getParam(param, "token_serial", optional=True)
    sortby = getParam(param, "sortby", optional=True, default="serial")
    sortdir = getParam(param, "sortdir", optional=True, default="asc")
    psize = int(getParam(param, "pagesize", optional=True) or 0)
    page = int(getParam(param, "page", optional=True) or 0)
    no_token = getParam(param, "no_token", optional=True, default=False)

    result = get_all_containers(user=user, serial=serial, ctype=ctype, token_serial=token_serial,
                                sortby=sortby, sortdir=sortdir,
                                pagesize=psize, page=page)

    res: list = []
    for container in result["containers"]:
        tmp: dict = {"type": container.type, "serial": container.serial, "description": container.description}
        tmp_users: dict = {}
        users: list = []
        for user in container.get_users():
            tmp_users["user_name"] = get_username(user.login, user.resolver)
            tmp_users["user_realm"] = user.realm
            tmp_users["user_resolver"] = user.resolver
            tmp_users["user_id"] = user.login
            users.append(tmp_users)
        tmp["users"] = users

        if not no_token:
            token_serials = [token.get_serial() for token in container.get_tokens()]
            tokens_dict_list = []
            if len(token_serials) > 0:
                tokens = get_tokens(serial_list=token_serials)
                tokens_dict_list = convert_token_objects_to_dicts(tokens)
            tmp["tokens"] = tokens_dict_list

        res.append(tmp)
    result["containers"] = res
    return send_result(result)


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
    res = container.remove(user)
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
    :jsonparam: serial_list: List of serials of the tokens to add. Comma separated.
    """
    serial = getParam(request.all_data, "serial", True, allow_empty=True)
    serials = getParam(request.all_data, "serial_list")
    if not serial and not serials:
        raise ParameterError("Either serial or serial_list is required")
    token_serials = []
    if serials:
        token_serials = serials
    if serial:
        token_serials.append(serial)
    res = add_tokens_to_container(container_serial, token_serials)
    return send_result(res)


@container_blueprint.route('<string:container_serial>/remove', methods=['POST'])
@log_with(log)
def remove_token(container_serial):
    """
    Remove a token from a container
    :jsonparam: serial: Serial of the token to remove
    :jsonparam: serial_list: List of serials of the tokens to remove. Comma separated.
    """
    container = find_container_by_serial(container_serial)
    serial = getParam(request.all_data, "serial", required, allow_empty=True)
    serials = request.args.getlist("serial_list")
    if not serial and not serials:
        raise ParameterError("Either serial or serial_list is required")

    serials.append(serial)

    token = get_one_token(serial=serial)
    res = False
    if token:
        container.remove_token(token.get_serial())
        res = True
    return send_result(res)


@container_blueprint.route('types', methods=['GET'])
@container_blueprint.route('tokentypes', methods=['GET'])
@log_with(log)
def get_types():
    """
    {
        type: { description: "Description", token_types: ["hotp", "totp", "push", "daypassword", "sms"] },
        type: { description: "Description", token_types: ["hotp", "totp", "push", "daypassword", "sms"] }
    }
    """
    descriptions = get_container_classes_descriptions()
    ttypes = get_container_token_types()
    res = {ctype: {"description": desc, "token_types": ttypes.get(ctype, [])} for ctype, desc in descriptions.items()}
    return send_result(res)


# @container_blueprint.route('tokentypes', methods=['GET'])
# @log_with(log)
# def get_token_types():
#     """
#     Get the supported token types for each container type
#     """
#     ttypes = get_container_token_types()
#     return send_result(res)


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
    template_id = json.get('template_id')


@container_blueprint.route('<string:container_type>/template/<string:template_name>', methods=['POST'])
@log_with(log)
def create_template_with_name(container_type, template_name):
    """
    Set the template for the given container type
    """
    json = request.json
    template_id = create_container_template(container_type, template_name, json)
    return template_id
