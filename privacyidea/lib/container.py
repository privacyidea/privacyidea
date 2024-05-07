import importlib
import inspect
import logging
import os

from typing import List

from privacyidea.lib.config import get_from_config
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.error import ResourceNotFoundError, ParameterError, EnrollmentError
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.lib.utils import hexlify_and_unicode
from privacyidea.models import TokenContainer, TokenContainerTemplate, TokenContainerOwner, Token, \
    TokenContainerToken

log = logging.getLogger(__name__)


def delete_container_by_id(container_id):
    """
    Delete the container with the given id. If it does not exist, raise a ResourceNotFoundError.
    Returns the id of the deleted container on success
    """
    if not container_id:
        raise ParameterError("Unable to delete container without id.")

    container = find_container_by_id(container_id)
    return container.delete()


def delete_container_by_serial(serial):
    """
    Delete the container with the given serial. If it does not exist, raise a ResourceNotFoundError.
    Returns the id of the deleted container on success
    """
    container = find_container_by_serial(serial)
    return container.delete()


def _gen_serial(container_type):
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


def create_container(container_type: str, serial=None, tokens: List[TokenClass] = None,
                     users: List[User] = None, description=""):
    """
    Create a new container with the given params.
    Returns the container
    """
    classes = get_container_classes()
    if container_type.lower() not in classes.keys():
        raise ParameterError(f"Unknown container type {container_type}. It must be one of {classes.keys()}.")

    if serial is None:
        serial = _gen_serial(container_type)

    db_container = TokenContainer(serial=serial, container_type=container_type.lower(),
                                  tokens=tokens, description=description)
    db_container.save()
    container = create_container_from_db_object(db_container)
    if users:
        for u in users:
            container.add_user(u)
    return container


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
def find_container_by_id(container_id):
    """
    Returns the TokenContainerClass object for the given container id or raises a ResourceNotFoundError
    """
    db_container = TokenContainer.query.filter(TokenContainer.id == container_id).first()
    if not db_container:
        raise ResourceNotFoundError(f"Unable to find container with id {container_id}.")

    return TokenContainerClass(db_container)


def find_container_by_serial(serial):
    """
    Returns the TokenContainerClass object for the given container serial or raises a ResourceNotFoundError
    """
    db_container = TokenContainer.query.filter(TokenContainer.serial == serial).first()
    if not db_container:
        raise ResourceNotFoundError(f"Unable to find container with serial {serial}.")

    return TokenContainerClass(db_container)


def get_all_containers(user=None):
    db_containers = TokenContainer.query.all()
    containers: List[TokenContainerClass] = []
    container_classes = get_container_classes()
    for db_container in db_containers:
        for ctype, cls in container_classes.items():
            if ctype.lower() == db_container.type.lower():
                containers.append(cls(db_container))
    return containers


def find_containers_for_user(user: User):
    """
    Returns a list of TokenContainerClass objects for the given user
    """
    containers = TokenContainer.query.join(TokenContainer.owners).filter(TokenContainerOwner.user_id == user.id).all()
    return [TokenContainerClass(c) for c in containers]


def find_container_for_token(serial):
    """
    Returns a list of TokenContainerClass objects for the given token
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
    serial = params.get("serial") or _gen_serial(ctype)
    db_container = TokenContainer(serial=serial, container_type=ctype.lower(), description=desc)
    db_container.save()

    user = params.get("user")
    realm = params.get("realm")
    if user and not realm or realm and not user:
        log.error(f"Assigning a container to user on creation requires both user and realm parameters!")
    elif user and realm:
        container = create_container_from_db_object(db_container)
        container.add_user(User(login=user, realm=realm))

    return serial


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
