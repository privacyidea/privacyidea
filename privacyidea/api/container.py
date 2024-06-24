import logging

from flask import Blueprint, jsonify, request, g

from privacyidea.api.lib.utils import send_result, getParam, required
from privacyidea.lib.container import get_container_classes, create_container_template, \
    find_container_by_serial, init_container, get_container_classes_descriptions, \
    get_container_token_types, get_all_containers, remove_tokens_from_container, add_tokens_to_container
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.error import ParameterError
from privacyidea.lib.event import event
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
@event('container_list', request, g)
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
    cserial = getParam(param, "container_serial", optional=True)
    ctype = getParam(param, "type", optional=True)
    token_serial = getParam(param, "token_serial", optional=True)
    sortby = getParam(param, "sortby", optional=True, default="serial")
    sortdir = getParam(param, "sortdir", optional=True, default="asc")
    psize = int(getParam(param, "pagesize", optional=True) or 0)
    page = int(getParam(param, "page", optional=True) or 0)
    no_token = getParam(param, "no_token", optional=True, default=False)

    result = get_all_containers(user=user, serial=cserial, ctype=ctype, token_serial=token_serial,
                                sortby=sortby, sortdir=sortdir,
                                pagesize=psize, page=page)

    res: list = []
    for container in result["containers"]:
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

        if not no_token:
            token_serials = [token.get_serial() for token in container.get_tokens()]
            tokens_dict_list = []
            if len(token_serials) > 0:
                tokens = get_tokens(serial_list=token_serials)
                tokens_dict_list = convert_token_objects_to_dicts(tokens)
            tmp["tokens"] = tokens_dict_list

        tmp["states"] = [token_container_states.state for token_container_states in container.get_states()]

        infos: dict = {}
        for info in container.get_containerinfo():
            if info.type:
                infos[info.key + ".type"] = info.type
            infos[info.key] = info.value
        tmp["info"] = infos

        realms = []
        for realm in container.realms:
            realms.append(realm.name)
        tmp["realms"] = realms

        res.append(tmp)
    result["containers"] = res

    g.audit_object.log({"success": True})
    return send_result(result)


@container_blueprint.route('<string:container_serial>/assign', methods=['POST'])
@event('container_assign', request, g)
@log_with(log)
def assign(container_serial):
    """
    Assign a container to a user

    :param: container_serial: serial of the container
    :jsonparam user: Username of the user
    :jsonparam realm: Realm of the user
    """
    user = get_user_from_param(request.all_data, required)
    container = find_container_by_serial(container_serial)
    res = container.add_user(user)

    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('<string:container_serial>/unassign', methods=['POST'])
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
    container = find_container_by_serial(container_serial)
    res = container.remove_user(user)

    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('init', methods=['POST'])
@event('container_init', request, g)
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
@event('container_delete', request, g)
@log_with(log)
def delete(container_serial):
    """
    Delete a container.
    :param: container_serial: serial of the container
    """
    container = find_container_by_serial(container_serial)
    container.delete()

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


@container_blueprint.route('<string:container_serial>/add', methods=['POST'])
@log_with(log)
@event('container_add_token', request, g)
def add_token(container_serial):
    """
    Add one or multiple tokens to a container
    :param: container_serial: serial of the container
    :jsonparam: serial: Serial of the token to add. Multiple serials can be passed comma separated.
    """
    serial = getParam(request.all_data, "serial", optional=False, allow_empty=False)
    token_serials = serial.replace(' ', '').split(',')
    res = add_tokens_to_container(container_serial, token_serials)

    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "serial": serial,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('<string:container_serial>/remove', methods=['POST'])
@event('container_remove_token', request, g)
@log_with(log)
def remove_token(container_serial):
    """
    Remove a token from a container
    :param: container_serial: serial of the container
    :jsonparam: serial: Serial of the token to remove. Multiple serials can be passed comma separated.
    """
    serial = getParam(request.all_data, "serial", optional=False, allow_empty=False)
    token_serials = serial.replace(' ', '').split(',')
    res = remove_tokens_from_container(container_serial, token_serials)

    # Audit log
    container = find_container_by_serial(container_serial)
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "serial": serial,
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('types', methods=['GET'])
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
    g.audit_object.log({"success": True})
    return send_result(res)


@container_blueprint.route('<container_serial>/description', methods=['POST'])
@event('container_set_description', request, g)
@log_with(log)
def set_description(container_serial):
    """
    Set the description of a container
    :param: container_serial: Serial of the container
    :jsonparam: description: New description to be set
    """
    container = find_container_by_serial(container_serial)
    new_description = getParam(request.all_data, "description", optional=required, allow_empty=False)
    res = False
    if new_description:
        container.description = new_description
        res = True

    # Audit log
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "action_detail": f"description={new_description}",
                      "success": res}
    g.audit_object.log(audit_log_data)
    return send_result(res)


@container_blueprint.route('<container_serial>/states', methods=['POST'])
@event('container_set_states', request, g)
@log_with(log)
def set_states(container_serial):
    """
    Set the states of a container
    :param: container_serial: Serial of the container
    :jsonparam: states: string list
    """
    states = getParam(request.all_data, "states", required, allow_empty=False)
    container = find_container_by_serial(container_serial)

    res = False
    if states:
        container.set_states(states)
        res = True

    # Audit log
    owners = container.get_users()
    if len(owners) == 1:
        g.audit_object.log({"user": owners[0].login,
                            "realm": owners[0].realm,
                            "resolver": owners[0].resolver})
    audit_log_data = {"container_serial": container_serial,
                      "container_type": container.type,
                      "action_detail": f"states={states}",
                      "success": res}
    g.audit_object.log(audit_log_data)
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
    g.audit_object.log({"success": True})
    return send_result(state_types_exclusions)


@container_blueprint.route('<container_serial>/realms', methods=['POST'])
@event('container_set_realms', request, g)
@log_with(log)
def set_realms(container_serial):
    """
    Set the realms of a container. Old realms will be deleted.
    :param: container_serial: Serial of the container
    :jsonparam: realms: comma separated string of realms, e.g. "realm1,realm2"
    """
    container_realms = getParam(request.all_data, "realms", required, allow_empty=True)
    realm_list = [r.strip() for r in container_realms.split(",")]
    container = find_container_by_serial(container_serial)
    result = container.set_realms(realm_list, add=False)

    success = False not in result.values()

    # Audit log
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


@container_blueprint.route('<container_serial>/lastseen', methods=['POST'])
@event('container_update_last_seen', request, g)
@log_with(log)
def update_last_seen(container_serial):
    """
    Updates the date and time for the last_seen property
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


# TEMPLATES
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
        g.audit_object.log({"success": True})
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

    audit_log_data = {"container_type": container_type,
                      "success": True}
    g.audit_object.log(audit_log_data)


@container_blueprint.route('<string:container_type>/template/<string:template_name>', methods=['POST'])
@log_with(log)
def create_template_with_name(container_type, template_name):
    """
    Set the template for the given container type
    """
    json = request.json
    template_id = create_container_template(container_type, template_name, json)

    audit_log_data = {"container_type": container_type,
                      "action_detail": f"template_name={template_name}",
                      "success": True}
    g.audit_object.log(audit_log_data)
    return template_id
