import importlib
import logging
import os

from privacyidea.lib.config import get_from_config
from privacyidea.lib.error import ResourceNotFoundError, ParameterError, EnrollmentError
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import Match
from privacyidea.lib.token import create_tokenclass_object
from privacyidea.lib.user import User
from privacyidea.lib.utils import hexlify_and_unicode
from privacyidea.models import TokenContainer, TokenContainerTemplate, TokenContainerOwner, Token, \
    TokenContainerToken

log = logging.getLogger(__name__)


def delete_container_by_id(container_id: int):
    """
    Delete the container with the given id. If it does not exist, raise a ResourceNotFoundError.
    Returns the id of the deleted container on success
    """
    if not container_id:
        raise ParameterError("Unable to delete container without id.")

    container = find_container_by_id(container_id)
    return container.delete()


def delete_container_by_serial(serial: str):
    """
    Delete the container with the given serial. If it does not exist, raise a ResourceNotFoundError.
    Returns the id of the deleted container on success
    """
    container = find_container_by_serial(serial)
    return container.delete()


def _gen_serial(container_type: str):
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
    Create a TokenContainerClass object from the given db object
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
    Returns the TokenContainerClass object for the given container id or raises a ResourceNotFoundError
    """
    db_container = TokenContainer.query.filter(TokenContainer.id == container_id).first()
    if not db_container:
        raise ResourceNotFoundError(f"Unable to find container with id {container_id}.")

    return create_container_from_db_object(db_container)


def find_container_by_serial(serial: str):
    """
    Returns the TokenContainerClass object for the given container serial or raises a ResourceNotFoundError
    """
    db_container = TokenContainer.query.filter(TokenContainer.serial == serial).first()
    if not db_container:
        raise ResourceNotFoundError(f"Unable to find container with serial {serial}.")

    return create_container_from_db_object(db_container)


def _create_container_query(user: User = None, serial=None, ctype=None, token_serial=None, sortby='serial',
                            sortdir='asc'):
    """
    Returns a sql query for getting containers
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
    the next or previous page. If either does not exist, it is None.

    :param user: The user for which to retrieve the containers
    :param serial: Filter by container serial
    :param ctype: Filter by container type
    :param token_serial: Filter by token serial
    :param sortby: A Token column or a string. Default is "serial"
    :param sortdir: "asc" or "desc". Default is "asc"
    :param page: The number of the page to view. Starts with 1 ;-)
    :type page: int
    :param pagesize: The size of the page
    :type pagesize: int
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
    Create a TokenContainerClass object from the given db object
    """
    container = None
    container_classes = get_container_classes()
    for ctype, cls in container_classes.items():
        if ctype.lower() == db_container.type.lower():
            container = cls(db_container)
    return container


def find_container_for_token(serial):
    """
    Returns a TokenContainerClass object for the given token
    """
    token_id = Token.query.filter(Token.serial == serial).one().id
    row = TokenContainerToken.query.filter(
        TokenContainerToken.token_id == token_id).first()
    if row:
        container_id = row.container_id
        return find_container_by_id(container_id)
    return None


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
    Returns the policy info for the given container type or for all container types
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
    Create a new container template
    """
    return TokenContainerTemplate(name=template_name, container_type=container_type, options=options).save()


def init_container(params):
    """
    Create a new container with the given parameters. Requires at least the type.
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
        container.add_user(User(login=user, realm=realm))

    container.set_states(['active'])
    return serial


def add_tokens_to_container(container_serial, token_serials):
    """
    Add the given tokens to the container with the given serial.
    If a token is already in a container it is removed from the old container.
    """
    container = find_container_by_serial(container_serial)
    db_tokens = Token.query.filter(Token.serial.in_(token_serials)).all()
    tokens = [create_tokenclass_object(db_token) for db_token in db_tokens]
    ret = {}
    for token in tokens:
        # check if the token is in a container
        old_container = find_container_for_token(token.get_serial())
        if old_container:
            # remove token from old container
            remove_tokens_from_container(old_container.serial, [token.get_serial()])
        res = container.add_token(token)
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


def remove_tokens_from_container(container_serial, token_serials):
    """
    Remove the given tokens from the container with the given serial
    """
    container = find_container_by_serial(container_serial)
    ret = {}
    for token_serial in token_serials:
        res = container.remove_token(token_serial)
        ret[token_serial] = res
    return ret


def add_container_info(serial, ikey, ivalue):
    """
    Add the given info to the container with the given serial
    """
    container = find_container_by_serial(serial)
    container.add_container_info(ikey, ivalue)
