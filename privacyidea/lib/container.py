import importlib
import logging
import os

from privacyidea.lib.config import get_from_config
from privacyidea.lib.error import ResourceNotFoundError, ParameterError, EnrollmentError, UserError, PolicyError
from privacyidea.lib.log import log_with
from privacyidea.lib.token import create_tokenclass_object, get_token_owner
from privacyidea.lib.user import User
from privacyidea.lib.utils import hexlify_and_unicode
from privacyidea.models import TokenContainer, TokenContainerTemplate, TokenContainerOwner, Token, \
    TokenContainerToken

log = logging.getLogger(__name__)


def delete_container_by_id(container_id: int, user: User, user_role="user"):
    """
    Delete the container with the given id. If it does not exist, raise a ResourceNotFoundError.

    :param container_id: The id of the container to delete
    :param user: The user deleting the container
    :param user_role: The role of the user ('admin' or 'user')
    :return: ID of the deleted container on success
    """
    if not container_id:
        raise ParameterError("Unable to delete container without id.")

    container = find_container_by_id(container_id)

    # Check user rights: Throws error if user is not allowed to modify the container
    _check_user_access_on_container(container, user, user_role)

    return container.delete()


def delete_container_by_serial(serial: str, user: User, user_role="user"):
    """
    Delete the container with the given serial. If it does not exist, raise a ResourceNotFoundError.

    :param serial: The serial of the container to delete
    :param user: The user deleting the container
    :param user_role: The role of the user ('admin' or 'user')
    :return: ID of the deleted container on success
    """
    if not serial:
        raise ParameterError("Unable to delete container without serial.")
    container = find_container_by_serial(serial)

    # Check user rights: Throws error if user is not allowed to modify the container
    _check_user_access_on_container(container, user, user_role)

    return container.delete()


def _gen_serial(container_type: str):
    """
    Generate a new serial for a container of the given type

    :param container_type: The type of the container
    :return: The generated serial
    """
    serial_len = int(get_from_config("SerialLength") or 8)
    prefix = "CONT"
    for ctype, cls in get_container_classes().items():
        if ctype.lower() == container_type.lower():
            prefix = cls.get_class_prefix()

    container_num = TokenContainer.query.filter(TokenContainer.type == container_type).count()
    while True:
        rnd = ""
        count = '{:04d}'.format(container_num)
        rnd_len = serial_len - len(count)
        if rnd_len > 0:
            rnd = hexlify_and_unicode(os.urandom(rnd_len)).upper()[0:rnd_len]
        serial = f"{prefix}{count}{rnd}"
        if not TokenContainer.query.filter(TokenContainer.serial == serial).first():
            break

    return serial


def create_container_from_db_object(db_container: TokenContainer):
    """
    Create a TokenContainerClass object from the given db object.

    :param db_container: The db object to create the container from
    :return: The created container object or None if the container type is not supported
    """
    for ctypes, cls in get_container_classes().items():
        if ctypes.lower() == db_container.type.lower():
            try:
                container = cls(db_container)
            except Exception as ex:  # pragma: no cover
                log.error(f"Error creating container from db object: {ex}")
                return None
            return container
    return None


@log_with(log)
def find_container_by_id(container_id: int):
    """
    Returns the TokenContainerClass object for the given container id or raises a ResourceNotFoundError.

    :param container_id: ID of the container
    :return: container object
    """
    db_container = TokenContainer.query.filter(TokenContainer.id == container_id).first()
    if not db_container:
        raise ResourceNotFoundError(f"Unable to find container with id {container_id}.")

    return create_container_from_db_object(db_container)


def find_container_by_serial(serial: str):
    """
    Returns the TokenContainerClass object for the given container serial or raises a ResourceNotFoundError.

    :param serial: Serial of the container
    :return: container object
    """
    db_container = TokenContainer.query.filter(TokenContainer.serial == serial).first()
    if not db_container:
        raise ResourceNotFoundError(f"Unable to find container with serial {serial}.")

    return create_container_from_db_object(db_container)


def _create_container_query(user: User = None, serial=None, ctype=None, token_serial=None, sortby='serial',
                            sortdir='asc'):
    """
    Generates a sql query to filter containers by the given parameters.

    :param user: container owner, optional
    :param serial: container serial, optional
    :param ctype: container type, optional
    :param token_serial: serial of a token which is assigned to the container, optional
    :param sortby: column to sort by, default is the container serial
    :param sortdir: sort direction, default is ascending
    :return: sql query
    """
    sql_query = TokenContainer.query
    if user:
        # Get all containers for the given user
        sql_query = sql_query.join(TokenContainer.owners).filter(TokenContainerOwner.user_id == user.uid)
    if serial:
        sql_query = sql_query.filter(TokenContainer.serial == serial)

    if ctype:
        sql_query = sql_query.filter(TokenContainer.type == ctype)
    if token_serial:
        token = Token.query.filter(Token.serial == token_serial).first()
        if token:
            token_container_token = TokenContainerToken.query.filter(TokenContainerToken.token_id == token.id).all()
            container_ids = [t.container_id for t in token_container_token]
            sql_query = sql_query.filter(TokenContainer.id.in_(container_ids))
        else:
            log.warning(f'Unknown token serial {token_serial}. Containers are not filtered by "token_serial".')

    if isinstance(sortby, str):
        # check that the sort column exists and convert it to a Token column
        cols = TokenContainer.__table__.columns
        if sortby in cols:
            sortby = cols.get(sortby)
        else:
            log.warning(f'Unknown sort column "{sortby}". Using "serial" instead.')
            sortby = TokenContainer.serial

    if sortdir == "desc":
        sql_query = sql_query.order_by(sortby.desc())
    else:
        sql_query = sql_query.order_by(sortby.asc())

    return sql_query


def get_all_containers(user: User = None, serial=None, ctype=None, token_serial=None, sortby='serial',
                       sortdir='asc', page=0, pagesize=0):
    """
    This function is used to retrieve a container list, that can be displayed in
    the Web UI. It supports pagination if either page or pagesize is given (e.g. >0).
    Each retrieved page will also contain a "next" and a "prev", indicating
    the next or previous page. If page and pagesize are both smaller than 0, no pagination is used.
    The containers are filtered by the given parameters.

    :param user: container owner, optional
    :param serial: container serial, optional
    :param ctype: container type, optional
    :param token_serial: serial of a token which is assigned to the container, optional
    :param sortby: column to sort by, default is the container serial
    :param sortdir: sort direction, default is ascending
    :param page: The number of the page to view. Starts with 1 ;-)
    :param pagesize: The size of the page
    """
    # TODO add user role policy

    sql_query = _create_container_query(user=user, serial=serial, ctype=ctype, token_serial=token_serial,
                                        sortby=sortby, sortdir=sortdir)
    ret = {}
    # paginate if requested
    if page > 0 or pagesize > 0:
        if page < 1:
            page = 1
        if pagesize < 1:
            pagesize = 10

        pagination = sql_query.paginate(page, per_page=pagesize, error_out=False)
        db_containers = pagination.items

        prev = None
        if pagination.has_prev:
            prev = page - 1
        nxt = None
        if pagination.has_next:
            nxt = page + 1

        ret["prev"] = prev
        ret["next"] = nxt
        ret["current"] = page
        ret["count"] = pagination.total
    else:  # no pagination
        db_containers = sql_query.all()

    container_list = [create_container_class_object(db_container) for db_container in db_containers]
    ret["containers"] = container_list

    return ret


def create_container_class_object(db_container):
    """
    Create a TokenContainerClass object from the given db object.

    :param db_container: The db object to create the container from
    :return: The created container object or None if the container type is not supported
    """
    container = None
    container_classes = get_container_classes()
    for ctype, cls in container_classes.items():
        if ctype.lower() == db_container.type.lower():
            container = cls(db_container)
    return container


def find_container_for_token(serial):
    """
    Returns a TokenContainerClass object for the given token or raises a ResourceNotFoundError
    if the token does not exist.

    :param serial: Serial of the token
    :return: container object or None if the token is not in a container
    """
    container = None
    db_token = Token.query.filter(Token.serial == serial).first()
    if not db_token:
        raise ResourceNotFoundError(f"Unable to find token with serial {serial}.")
    token_id = db_token.id
    row = TokenContainerToken.query.filter(TokenContainerToken.token_id == token_id).first()
    if row:
        container_id = row.container_id
        container = find_container_by_id(container_id)
    return container


def get_container_classes():
    """
    Returns a dictionary of all available container classes in the format:
    { type: class }
    New container types have to be added here.
    """
    # className: module
    classes = {
        "TokenContainerClass": "privacyidea.lib.containerclass",
        "SmartphoneContainer": "privacyidea.lib.containers.smartphone",
        "YubikeyContainer": "privacyidea.lib.containers.yubikey"
    }

    ret = {}
    for cls, mod in classes.items():
        try:
            m = importlib.import_module(mod)
            c = getattr(m, cls)
            ret[c.get_class_type().lower()] = c
        except Exception as ex:  # pragma: no cover
            log.error(f"Error importing module {cls}: {ex}")

    return ret


def get_container_policy_info(container_type=None):
    """
    Returns the policy info for the given container type or for all container types if no type is defined.

    :param container_type: The type of the container, optional
    :return: The policy info for the given container type or for all container types
    """
    classes = get_container_classes()
    if container_type:
        if container_type in classes.keys():
            return classes[container_type].get_container_policy_info()
        else:
            raise ResourceNotFoundError(f"Unable to find container type {container_type}.")
    else:
        ret = {}
        for container_type, container_class in classes.items():
            ret[container_type] = container_class.get_container_policy_info()
        return ret


def create_container_template(container_type, template_name, options):
    """
    Create a new container template.

    :param container_type: The type of the container
    :param template_name: The name of the template
    :param options: The options for the template
    :return: The created template object
    """
    return TokenContainerTemplate(name=template_name, container_type=container_type, options=options).save()


def init_container(params):
    """
    Create a new container with the given parameters. Requires at least the type.

    :jsonparam type: The type of the container
    :jsonparam description: The description of the container, optional
    :jsonparam container_serial: The serial of the container, optional
    :jsonparam user: The user to assign the container to (requires the realm), optional
    :jsonparam realm: The realm to assign the container to, optional
    :return: The serial of the created container
    """
    ctype = params.get("type")
    if not ctype:
        raise EnrollmentError("Type parameter is required!")
    if ctype.lower() not in get_container_classes().keys():
        raise EnrollmentError(f"Type '{ctype}' is not a valid type!")

    desc = params.get("description") or ""
    serial = params.get("container_serial") or _gen_serial(ctype)
    db_container = TokenContainer(serial=serial, container_type=ctype.lower(), description=desc)
    db_container.save()

    container = create_container_from_db_object(db_container)
    user = params.get("user")
    realm = params.get("realm")
    realms = []
    if user and not realm:
        log.error(f"Assigning a container to user on creation requires both user and realm parameters!")
    elif realm and not user:
        realms.append(realm)
        container.set_realms(realms, add=True)
    elif user and realm:
        try:
            container.add_user(User(login=user, realm=realm))
        except UserError as ex:
            log.error(f"Error setting user for container {serial}: {ex}")

    container.set_states(['active'])
    return serial


def add_tokens_to_container(container_serial, token_serials, user, user_role="user"):
    """
    Add the given tokens to the container with the given serial.
    If a token is already in a container it is removed from the old container.
    A user is only allowed to add a token to a container if the user is an admin or the owner of both. If the token is
    already in a container, the user also has to be the owner of the old container.

    :param container_serial: The serial of the container
    :param token_serials: A list of token serials to add
    :param user: The user adding the tokens
    :param user_role: The role of the user ('admin' or 'user')
    :return: A dictionary of type {token_serial: success}
    """
    container = find_container_by_serial(container_serial)
    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    # Get the token objects
    db_tokens = Token.query.filter(Token.serial.in_(token_serials)).all()
    tokens = [create_tokenclass_object(db_token) for db_token in db_tokens]
    ret = {}
    for token in tokens:
        # check if the token is in a container
        old_container = find_container_for_token(token.get_serial())
        user_is_owner_of_old_container = False
        if old_container:
            old_container_owners = old_container.get_users()
            if len(old_container_owners) == 0 or user == old_container_owners[0]:
                # Either the token is not in a container or the user is the owner of the old container
                user_is_owner_of_old_container = True
        # Check if the user is allowed to add the token to the container
        token_owner = token.user
        if not user_role == "admin" and not user == token_owner and not user_is_owner_of_old_container:
            ret[token.get_serial()] = False
            log.error(f"User {user} is not allowed to add token {token.get_serial()} to container {container_serial}.")
            continue
        try:
            res = container.add_token(token)
        except ParameterError as ex:
            log.error(f"Error adding token {token.get_serial()} to container {container_serial}: {ex}")
            res = False
        if res and old_container:
            # remove token from old container
            remove_tokens_from_container(old_container.serial, [token.get_serial()], user, user_role)
            log.info(f"Adding token {token.get_serial()} to container {container_serial}: "
                     f"Token removed from previous container {old_container.serial}.")
        ret[token.get_serial()] = res
    return ret


def get_container_classes_descriptions():
    """
    Returns a dictionary of {"type": "Type: description"} entries for all container types.
    Used to list the container types.
    """
    ret = {}
    classes = get_container_classes()
    for container_type, container_class in classes.items():
        ret[container_type] = f"{container_type.capitalize()}: {container_class.get_class_description()}"
    return ret


def get_container_token_types():
    """
    Returns a dictionary of {"type": ["tokentype0, tokentype1, ..."]} entries for all container types.
    Used to list the supported token types for each container type.
    """
    ret = {}
    classes = get_container_classes()
    for container_type, container_class in classes.items():
        ret[container_type] = container_class.get_supported_token_types()
    return ret


def remove_tokens_from_container(container_serial, token_serials, user, user_role="user"):
    """
    Remove the given tokens from the container with the given serial.
    Raises a ResourceNotFoundError if no container for the given serial exist.
    Errors of removing tokens are caught and only logged, in order to be able to remove the remaining
    tokens in the list.
    A user is only allowed to remove a token from a container if it is an admin or the owner of both,
    the token and the container.

    :param container_serial: The serial of the container
    :param token_serials: A list of token serials to remove
    :param user: The user adding the tokens
    :param user_role: The role of the user ('admin' or 'user')
    :return: A dictionary of type {token_serial: success}
    """
    container = find_container_by_serial(container_serial)

    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    if not container:
        raise ResourceNotFoundError(f"Container with serial {container_serial} does not exist.")
    ret = {}
    for token_serial in token_serials:
        token_owner = get_token_owner(token_serial)
        if user_role == "admin" or user == token_owner:
            try:
                res = container.remove_token(token_serial)
            except Exception as ex:
                log.error(f"Error removing token {token_serial} from container {container_serial}: {ex}")
                res = False
        else:
            log.error(f"User {user} is not allowed to remove token {token_serial} from container {container_serial}.")
            res = False
        ret[token_serial] = res
    return ret


def add_container_info(serial, ikey, ivalue, user, user_role="user"):
    """
    Add the given info to the container with the given serial.

    :param serial: The serial of the container
    :param ikey: The info key
    :param ivalue: The info value
    :param user: The user adding the info
    :param user_role: The role of the user ('admin' or 'user')
    """
    container = find_container_by_serial(serial)

    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    container.add_container_info(ikey, ivalue)
    return True


def set_container_info(serial, info, user, user_role="user"):
    """
    Set the given info to the container with the given serial.

    :param serial: The serial of the container
    :param info: The info dictionary of type {key: value}
    :param user: The user adding the info
    :param user_role: The role of the user ('admin' or 'user')
    """
    container = find_container_by_serial(serial)

    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    container.set_container_info(info)
    return True


def get_container_info_dict(serial, ikey=None, user=None, user_role="user"):
    """
    Returns the info of the given key or all infos if no key is given for the container with the given serial.

    :param serial: The serial of the container
    :param ikey: The info key or None to get all info keys
    :param user: The user getting the info
    :param user_role: The role of the user ('admin' or 'user')
    :return: The info dict
    """
    container = find_container_by_serial(serial)

    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
    if ikey:
        if ikey in container_info.keys():
            container_info = {ikey: container_info[ikey]}
        else:
            container_info = {ikey: None}
            log.error(f"Info key {ikey} not found in container {serial}.")
    return container_info


def delete_container_info(serial, ikey=None, user=None, user_role="user"):
    """
    Delete the info of the given key or all infos if no key is given.

    :param serial: The serial of the container
    :param ikey: The info key or None to delete all info keys
    :param user: The user adding the info
    :param user_role: The role of the user ('admin' or 'user')
    """
    container = find_container_by_serial(serial)

    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    res = container.delete_container_info(ikey)
    return res


def assign_user(serial, user: User, logged_in_user, user_role="user"):
    """
    Assign a user to a container.

    :param serial: container serial
    :param user: user to assign to the container
    :param logged_in_user: user performing this action
    :param user_role: role of the logged-in user ("admin" or "user")
    :return:
    """
    container = find_container_by_serial(serial)

    # Check user rights on container
    if not user_role == "admin" and user != logged_in_user:
        raise PolicyError(f"User {logged_in_user} is not allowed to assign user {user} to container {serial}!")

    res = container.add_user(user)
    return res


def unassign_user(serial, user: User, logged_in_user: User, user_role="user"):
    """
    Unassign a user from a container.

    :param serial: container serial
    :param user: user to unassign from the container
    :param logged_in_user: user performing this action
    :param user_role: role of the logged-in user ("admin" or "user")
    :return:
    """
    container = find_container_by_serial(serial)

    # Check user rights on container
    _check_user_access_on_container(container, logged_in_user, user_role)

    res = container.remove_user(user)
    return res


def set_container_description(serial, description, user: User = None, user_role="user"):
    """
    Set the description of a container.
    :param serial: serial of the container
    :param description: new description
    :param user: user setting the description
    :param user_role: role of the logged-in user ("admin" or "user")
    """
    container = find_container_by_serial(serial)

    # Check user rights on container
    _check_user_access_on_container(container, user, user_role)

    container.description = description


def set_container_states(serial, states, user: User = None, user_role="user"):
    """
    Set the states of a container.
    :param serial: serial of the container
    :param states: new states as list of str
    :param user: user setting the states
    :param user_role: role of the logged-in user ("admin" or "user")
    """
    container = find_container_by_serial(serial)

    # Check user rights on container
    _check_user_access_on_container(container, user, user_role)

    res = container.set_states(states)
    return res


def add_container_states(serial, states, user: User = None, user_role="user"):
    """
    Add the states to a container.
    :param serial: serial of the container
    :param states: additional states as list of str
    :param user: user setting the states
    :param user_role: role of the logged-in user ("admin" or "user")
    """
    container = find_container_by_serial(serial)

    # Check user rights on container
    _check_user_access_on_container(container, user, user_role)

    res = container.add_states(states)
    return res


def set_container_realms(serial, realms, user: User, user_role="user"):
    """
    Set the realms of a container.
    :param serial: serial of the container
    :param realms: new realms as list of str
    :param user: user setting the realms
    :param user_role: role of the logged-in user ("admin" or "user")
    """
    container = find_container_by_serial(serial)

    # Check user rights on container
    _check_user_access_on_container(container, user, user_role)

    res = container.set_realms(realms, add=False)
    return res


def add_container_realms(serial, realms, user: User, user_role="user"):
    """
    Add the realms to the realms of a container.
    :param serial: serial of the container
    :param realms: new realms as list of str
    :param user: user setting the realms
    :param user_role: role of the logged-in user ("admin" or "user")
    """
    container = find_container_by_serial(serial)

    # Check user rights on container
    _check_user_access_on_container(container, user, user_role)

    res = container.set_realms(realms, add=True)
    return res


def _check_user_access_on_container(container, user, user_role):
    """
    Check if the given user is the owner of the given container or an admin.

    :param container: The container object
    :param user: The user object
    :return: True if the user is the owner or admin, False otherwise
    """
    if user_role == "admin":
        return True
    elif user_role == "user":
        owners = container.get_users()
        for owner in owners:
            if owner == user:
                return True

        raise PolicyError(f"User {user} is not allowed to modify container {container.serial}.")

    else:
        raise ParameterError(f"Unknown user role {user_role}!")
