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
import importlib
import json
import logging
import os
from typing import Union

from sqlalchemy import func
from sqlalchemy.orm import Query

from privacyidea.api.lib.utils import send_result
from privacyidea.lib.challenge import delete_challenges
from privacyidea.lib.config import get_from_config
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.containers.container_info import PI_INTERNAL, TokenContainerInfoData
from privacyidea.lib.containertemplate.containertemplatebase import ContainerTemplateBase
from privacyidea.lib.error import ResourceNotFoundError, ParameterError, EnrollmentError, UserError, PolicyError
from privacyidea.lib.log import log_with
from privacyidea.lib.machine import is_offline_token
from privacyidea.lib.token import (get_tokens_from_serial_or_user, get_tokens,
                                   convert_token_objects_to_dicts, init_token)
from privacyidea.lib.user import User
from privacyidea.lib.utils import hexlify_and_unicode
from privacyidea.models import (TokenContainer, TokenContainerOwner, Token, TokenContainerToken,
                                Realm, TokenContainerTemplate)

log = logging.getLogger(__name__)


def delete_container_by_id(container_id: int) -> int:
    """
    Delete the container with the given id. If it does not exist, raises a ResourceNotFoundError.

    :param container_id: The id of the container to delete
    :return: ID of the deleted container on success
    """
    if not container_id:
        raise ParameterError("Unable to delete container without id.")

    container = find_container_by_id(container_id)

    # Delete challenges
    delete_challenges(serial=container.serial)

    return container.delete()


def delete_container_by_serial(serial: str) -> int:
    """
    Delete the container with the given serial. If it does not exist, raises a ResourceNotFoundError.

    :param serial: The serial of the container to delete
    :return: ID of the deleted container on success
    """
    if not serial:
        raise ParameterError("Unable to delete container without serial.")
    container = find_container_by_serial(serial)

    # Delete challenges
    delete_challenges(serial=serial)

    return container.delete()


def _gen_serial(container_type: str) -> str:
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


def create_container_from_db_object(db_container: TokenContainer) -> Union[TokenContainerClass, None]:
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
                log.warning(f"Error creating container from db object: {ex}")
                return None
            return container
    return None


@log_with(log)
def find_container_by_id(container_id: int) -> TokenContainerClass:
    """
    Returns the TokenContainerClass object for the given container id or raises a ResourceNotFoundError.

    :param container_id: ID of the container
    :return: container object
    """
    db_container = TokenContainer.query.filter(TokenContainer.id == container_id).first()
    if not db_container:
        raise ResourceNotFoundError(f"Unable to find container with id {container_id}.")

    return create_container_from_db_object(db_container)


def find_container_by_serial(serial: str) -> TokenContainerClass:
    """
    Returns the TokenContainerClass object for the given container serial or raises a ResourceNotFoundError.

    :param serial: Serial of the container
    :return: container object
    :rtype: privacyidea.lib.containerclass.TokenContainerClass
    """
    if serial:
        db_container = TokenContainer.query.filter(func.upper(TokenContainer.serial) == serial.upper()).first()
    else:
        db_container = None
    if not db_container:
        raise ResourceNotFoundError(f"Unable to find container with serial {serial}.")

    return create_container_from_db_object(db_container)


def _create_container_query(user: User = None, serial: str = None, ctype: str = None, token_serial: str = None,
                            realms: list = None, template: str = None, sortby: str = 'serial',
                            sortdir: str = 'asc') -> Query:
    """
    Generates a sql query to filter containers by the given parameters.

    :param user: container owner, optional
    :param serial: container serial, optional
    :param ctype: container type, optional
    :param token_serial: serial of a token which is assigned to the container, optional
    :param realms: list of realms to filter by, optional
    :param template: The name of the template the container was created with, optional
    :param sortby: column to sort by, default is the container serial
    :param sortdir: sort direction, default is ascending
    :return: sql query
    """
    sql_query = TokenContainer.query
    if user:
        sql_query = sql_query.join(TokenContainer.owners).filter(TokenContainerOwner.user_id == user.uid)

    if serial:
        sql_query = sql_query.filter(func.upper(TokenContainer.serial) == serial.upper())

    if ctype:
        sql_query = sql_query.filter(TokenContainer.type == ctype)

    if token_serial:
        sql_query = sql_query.join(TokenContainer.tokens).filter(Token.serial == token_serial)

    if realms:
        sql_query = sql_query.join(TokenContainer.realms).filter(Realm.name.in_(realms))

    if template:
        sql_query = sql_query.join(TokenContainer.template).filter(TokenContainerTemplate.name == template)

    if isinstance(sortby, str):
        # Check that the sort column exists and convert it to a container column
        cols = TokenContainer.__table__.columns
        if sortby in cols:
            sortby = cols.get(sortby)
        else:
            log.info(f'Unknown sort column "{sortby}". Using "serial" instead.')
            sortby = TokenContainer.serial

    if sortdir == "desc":
        sql_query = sql_query.order_by(sortby.desc())
    else:
        sql_query = sql_query.order_by(sortby.asc())

    return sql_query


def get_all_containers(user: User = None, serial: str = None, ctype: str = None, token_serial: str = None,
                       realms: list = None, sortby: str = 'serial', sortdir: str = 'asc', template: str = None,
                       page: int = 0, pagesize: int = 0) -> dict:
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
    :param realms: list of realms the container is assigned to, optional
    :param sortby: column to sort by, default is the container serial
    :param sortdir: sort direction, default is ascending
    :param template: The name of the template the container was created with, optional
    :param page: The number of the page to view. Starts with 1 ;-)
    :param pagesize: The size of the page
    :returns: A dictionary with a list of containers at the key 'containers' and optionally pagination entries ('prev',
              'next', 'current', 'count')
    """
    sql_query = _create_container_query(user=user, serial=serial, ctype=ctype, token_serial=token_serial, realms=realms,
                                        template=template, sortby=sortby, sortdir=sortdir)
    ret = {}
    # Paginate if requested
    if page > 0 or pagesize > 0:
        ret = create_pagination(page, pagesize, sql_query, "containers")
    else:  # No pagination
        ret["containers"] = sql_query.all()

    container_list = [create_container_from_db_object(db_container) for db_container in ret["containers"]]
    ret["containers"] = container_list

    return ret


def create_pagination(page: int, pagesize: int, sql_query: Query,
                      object_list_key: str) -> dict:
    """
        Creates the pagination of a sql query.

        :param page: The number of the page to view. Starts with 1
        :param pagesize: The number of objects that shall be shown on one page
        :param sql_query: The sql query to paginate
        :param object_list_key: The key used in the return dictionary for the list of objects
        :return: A dictionary with pagination information and a list of database objects
    """
    ret = {}
    if page < 1:
        page = 1
    if pagesize < 1:
        pagesize = 10

    pagination = sql_query.paginate(page=page, per_page=pagesize, error_out=False)
    db_objects = pagination.items

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
    ret[object_list_key] = db_objects
    return ret


def find_container_for_token(serial: str) -> TokenContainerClass:
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


def get_container_classes() -> dict:
    """
    Returns a dictionary of all available container classes in the format: { type: class }.
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
            log.warning(f"Error importing module {cls}: {ex}")

    return ret


def get_container_policy_info(container_type: Union[str, None] = None):
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


def init_container(params: dict) -> dict:
    """
    Create a new container with the given parameters. Requires at least the type.

    :param params: The parameters for the new container as dictionary like

        ::

            {
                "type": ...,
                "description": ..., (optional)
                "container_serial": ..., (optional)
                "user": ..., Name of the user (optional)
                "realm": ..., Name of the realm (optional)
                "template": {...}, Template as dictionary (optional)
                "template_name": ..., Name of the template (optional)
            }

        To assign a user to the container, the user and realm are required.

    :return: Dictionary containing the serial of the created container and a list of init details for tokens if the
        container is created from a template

        ::

            {
                "container_serial": "CONT0001",
                "template_tokens": [{"type": "hotp", ...}, ...]
            }
    """
    ctype = params.get("type")
    if not ctype:
        raise EnrollmentError("Type parameter is required!")
    if ctype.lower() not in get_container_classes().keys():
        raise EnrollmentError(f"Type '{ctype}' is not a valid type!")

    template_dict = params.get("template")
    template_name = params.get("template_name")
    if template_dict and template_name:
        raise ParameterError("Both template and template_name are given. Choose only one!")

    desc = params.get("description") or ""
    serial = params.get("container_serial")
    if serial:
        # Check if a container with this serial already exists
        containers = get_all_containers(serial=serial)["containers"]
        if len(containers) > 0:
            raise EnrollmentError(f"Container with serial {serial} already exists!")
    else:
        serial = _gen_serial(ctype)
    db_container = TokenContainer(serial=serial, container_type=ctype.lower(), description=desc)
    db_container.save()

    container = create_container_from_db_object(db_container)

    # Template handling
    template_tokens = []
    if template_name:
        # Use template from db
        try:
            template = get_template_obj(template_name)
        except ResourceNotFoundError as ex:
            template = None
            log.warning(f"Template {template_name} does not exists, create container without template: {ex}")

        if template:
            if template.container_type == ctype:
                template_options = template.get_template_options_as_dict()
                template_tokens = template_options.get("tokens", [])
                container.template = template_name
            else:
                log.warning(f"Template {template_name} is not of type {ctype}, create container without template.")
    elif template_dict:
        # Use template dictionary
        if template_dict.get("container_type") == ctype:
            # check if the template was modified, otherwise save the template name
            stored_templates = get_templates_by_query(name=template_dict["name"])["templates"]
            if len(stored_templates) > 0:
                original_template = stored_templates[0]
                original_template_used = compare_template_dicts(template_dict, original_template)
                if original_template_used:
                    container.template = original_template["name"]
            template_options = template_dict.get("template_options", {})
            # tokens from template
            template_tokens = template_options.get("tokens", [])
        else:
            log.warning(f"Template {template_name} is not of type {ctype}, create container without template.")


    user = params.get("user")
    realm = params.get("realm")
    realms = []
    if user and not realm:
        log.info(f"Assigning container {container.serial} to user {user} on "
                 f"creation requires both user and realm parameters!")
    elif realm and not user:
        realms.append(realm)
        container.set_realms(realms, add=True)
    elif user and realm:
        try:
            container.add_user(User(login=user, realm=realm))
        except UserError as ex:
            log.warning(f"Error setting user for container {serial}: {ex}")

    container.set_states(['active'])

    res = {"container_serial": serial, "template_tokens": template_tokens}
    return res


def create_container_tokens_from_template(container_serial: str, template_tokens: list, request,
                                          user_role: str) -> dict:
    """
    Create tokens for the container from the given template. The token policies are checked and the enroll information
    is read from the policies for each token. The tokens owner and the enroll information are added to the request
    object to check the corresponding policies. All errors are caught and logged to be able to create the remaining
    tokens.

    :param container_serial: The serial of the container
    :param template_tokens: The template to create the tokens from as list of dictionaries where each dictionary
        contains the details for a token to be enrolled
    :param request: The request object
    :param user_role: The role of the user ('admin' or 'user')
    :return: A dictionary containing the enroll details for each created token in the format:

    ::

        {
            <token_serial>: {"serial": <token_serial>,
                             "type": <token_type>,
                             "init_params": <params used for the enrollment>, ...},
        }
    """
    container = find_container_by_serial(container_serial)

    users = container.get_users()
    if len(users) > 0:
        container_owner = users[0]
    else:
        container_owner = User()
    realms = get_container_realms(container_serial)

    init_result = {}

    # Get policies for the token
    from privacyidea.api.lib.prepolicy import (check_max_token_realm, sms_identifiers,
                                               indexedsecret_force_attribute, pushtoken_add_config,
                                               tantoken_count, papertoken_count, init_token_length_contents,
                                               init_token_defaults, check_external, check_otp_pin, encrypt_pin,
                                               init_random_pin, twostep_enrollment_parameters,
                                               twostep_enrollment_activation, enroll_pin,
                                               init_tokenlabel, check_token_init, check_max_token_user,
                                               require_description)
    from privacyidea.api.lib.postpolicy import check_verify_enrollment, save_pin_change

    # Create each token defined in the template. The template contains the enroll information for each token.
    for token_info in template_tokens:
        token = None
        user = User()
        # If the user flag is set, the token is assigned to the container owner: set the full user information in the
        # enroll information
        if token_info.get("user"):
            if container_owner:
                token_info["user"] = container_owner.login
                token_info["realm"] = container_owner.realm
                token_info["resolver"] = container_owner.resolver
            elif realms:
                token_info["realm"] = realms[0]
                del token_info["user"]
            else:
                del token_info["user"]
            user = container_owner
        elif user_role == "user" and request.User:
            # Users are always assigned to the tokens, only admins can create tokens without a user
            user = request.User
            token_info["user"] = user.login
            token_info["realm"] = user.realm
            token_info["resolver"] = user.resolver
        elif token_info.get("user") is not None:
            del token_info["user"]

        # The pre-policy decorator functions require a request object containing the enroll information.
        # Hence, we need to clear the data in the request object from the previous token and set the new enroll
        # information for the current token.
        request.all_data = {}
        request.all_data.update(token_info)

        # Pre-policy checks
        # TODO: Refactor including original uses of these functions (decorators on token init endpoint)
        try:
            check_max_token_realm(request, None)
            require_description(request, None)
            check_max_token_user(request, None)
            check_token_init(request, None)
            init_tokenlabel(request, None)
            enroll_pin(request, None)
            twostep_enrollment_activation(request, None)
            twostep_enrollment_parameters(request, None)
            init_random_pin(request, None)
            encrypt_pin(request, None)
            check_otp_pin(request, None)
            check_external(request, None)
            init_token_defaults(request, None)
            init_token_length_contents(request, None)
            papertoken_count(request, None)
            sms_identifiers(request, None)
            tantoken_count(request, None)
            pushtoken_add_config(request, None)
            indexedsecret_force_attribute(request, None)
        except Exception as ex:
            log.warning(f"Error checking pre-policies for token {token_info} created from template: {ex}")
            continue

        init_params = request.all_data
        try:
            token = init_token(init_params, user)
            init_result[token.get_serial()] = {"type": token.get_type()}
            init_result[token.get_serial()].update(token.get_init_detail(init_params, user))
            container.add_token(token)
        except Exception as ex:
            log.warning(f"Error creating token {token_info} from template: {ex}")
            if token:
                if init_result.get(token.get_serial()):
                    del init_result[token.get_serial()]
                token.delete_token()
            continue

        # Post-policy checks
        try:
            # Post-policy decorators require a response object containing the result of the token creation.
            response = send_result(True, details=init_result[token.get_serial()])
            check_verify_enrollment(request, response)
            save_pin_change(request, response)
        except Exception as ex:
            log.warning(f"Error checking post-policy for token {token_info} created from template: {ex}")
            continue

        init_result[token.get_serial()].update(response.json["detail"])
        init_result[token.get_serial()]["init_params"] = init_params

    return init_result


def add_token_to_container(container_serial: str, token_serial: str) -> bool:
    """
    Add a single token to a container. If a token is already in a container it is removed from the old container.
    Raises a ResourceNotFoundError if either the container or token does not exist.

    :param container_serial: The serial of the container
    :param token_serial: The serial of the token
    :return: True on success
    """
    container = find_container_by_serial(container_serial)

    # Get the token object
    token = get_tokens_from_serial_or_user(token_serial, None)[0]

    # Check if the token is in a container
    old_container = find_container_for_token(token_serial)

    if old_container and old_container.serial != container.serial:
        # Remove token from old container
        remove_token_from_container(old_container.serial, token_serial)
        log.info(f"Adding token {token.get_serial()} to container {container_serial}: "
                 f"Token removed from previous container {old_container.serial}.")

    res = container.add_token(token)

    return res


def add_multiple_tokens_to_container(container_serial: str, token_serials: list) -> dict:
    """
    Add the given tokens to the container with the given serial. Raises a ResourceNotFoundError if the container does
    not exist. If a token is already in a container it is removed from the old container.

    :param container_serial: The serial of the container
    :param token_serials: A list of token serials to add
    :return: A dictionary in the format {<token_serial>: <success>}
    """
    # Raises ResourceNotFound if container does not exist
    find_container_by_serial(container_serial)

    ret = {}
    for token_serial in token_serials:
        try:
            res = add_token_to_container(container_serial, token_serial)
        except Exception as ex:
            # We are catching the exception here to be able to add the remaining tokens
            log.warning(f"Error adding token {token_serial} to container {container_serial}: {ex}")
            res = False
        ret[token_serial] = res

    return ret


def add_not_authorized_tokens_result(result: dict, not_authorized_serials: list) -> dict:
    """
    Add the result False for all tokens the user is not authorized to manage.

    :param result: The result dictionary in the format {token_serial: success}
    :param not_authorized_serials: A list of token serials the user is not authorized to manage
    :return: The result dictionary with the not authorized tokens added like {<token_serial>: False}
    """
    if not_authorized_serials:
        for serial in not_authorized_serials:
            result[serial] = False
    return result


def get_container_classes_descriptions() -> dict:
    """
    Returns a dictionary of {"type": "Type: description"} entries for all container types.
    Used to list the container types.
    """
    ret = {}
    classes = get_container_classes()
    for container_type, container_class in classes.items():
        ret[container_type] = f"{container_type.capitalize()}: {container_class.get_class_description()}"
    return ret


def get_container_token_types() -> dict:
    """
    Returns a dictionary of {"type": ["tokentype0", "tokentype1", ...]} entries for all container types.
    Used to list the supported token types for each container type.
    """
    ret = {}
    classes = get_container_classes()
    for container_type, container_class in classes.items():
        ret[container_type] = container_class.get_supported_token_types()
    return ret


def remove_token_from_container(container_serial: str, token_serial: str) -> bool:
    """
    Remove the given token from the container with the given serial.
    Raises a ResourceNotFoundError if the container or token does not exist.

    :param container_serial: The serial of the container
    :param token_serial: the serial of the token to remove
    :return: True on success
    """
    container = find_container_by_serial(container_serial)
    res = container.remove_token(token_serial)

    return res


def remove_multiple_tokens_from_container(container_serial: str, token_serials: str) -> dict:
    """
    Remove the given tokens from the container with the given serial.
    Raises a ResourceNotFoundError if no container for the given serial exist.
    Errors of removing tokens are caught and only logged, in order to be able to remove the remaining
    tokens in the list.

    :param container_serial: The serial of the container
    :param token_serials: A list of token serials to remove
    :return: A dictionary in the format {token_serial: success}
    """
    # Check that container exists
    find_container_by_serial(container_serial)

    ret = {}
    for token_serial in token_serials:
        try:
            res = remove_token_from_container(container_serial, token_serial)
        except Exception as ex:
            # We are catching the exception here to be able to remove the remaining tokens
            log.warning(f"Error removing token {token_serial} from container {container_serial}: {ex}")
            res = False
        ret[token_serial] = res
    return ret


def add_container_info(serial: str, ikey: str, ivalue) -> bool:
    """
    Add the given info to the container with the given serial.
    If the key already exists, the value is updated. However, if the entry is of type PI_INTERNAL, the value can not be
    modified.

    :param serial: The serial of the container
    :param ikey: The info key
    :param ivalue: The info value
    :returns: True on success
    """
    container = find_container_by_serial(serial)

    # Check if key already exists and if it is an internal key
    internal_keys = container.get_internal_info_keys()
    if ikey in internal_keys:
        raise PolicyError(f"The key {ikey} is an internal entry and can not be modified.")

    container.update_container_info([TokenContainerInfoData(key=ikey, value=ivalue)])
    return True


def set_container_info(serial, info: dict) -> dict:
    """
    Set the given info to the container with the given serial.
    Keys of type PI_INTERNAL can not be modified and will be ignored.

    :param serial: The serial of the container
    :param info: The info dictionary in the format {key: value}
    :returns: Dictionary with the success state for each info key
    """
    container = find_container_by_serial(serial)
    result = {}

    # Remove internal keys from the info dictionary, they can not be modified by the user
    internal_keys = container.get_internal_info_keys()
    not_internal_info = {}
    for key, value in info.items():
        if key not in internal_keys:
            not_internal_info[key] = value
            result[key] = True
        else:
            result[key] = False
            log.warning(f"The key {key} is an internal entry and can not be modified.")

    container.set_container_info(not_internal_info)
    return result


def get_container_info_dict(serial: str, ikey: str = None) -> dict:
    """
    Returns the info of the given key or all infos if no key is given for the container with the given serial.

    :param serial: The serial of the container
    :param ikey: The info key or None to get all info keys
    :return: The info dict
    """
    container = find_container_by_serial(serial)

    container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
    if ikey:
        if ikey in container_info.keys():
            container_info = {ikey: container_info[ikey]}
        else:
            container_info = {ikey: None}
            log.warning(f"Info key {ikey} not found in container {serial}.")
    return container_info


def delete_container_info(serial: str, ikey: str = None) -> dict:
    """
    Delete the info of the given key or all infos if no key is given.
    Internal infos are not deleted

    :param serial: The serial of the container
    :param ikey: The info key or None to delete all info keys
    :return: Dictionary with all info keys or only ikey if given and the value True on success, False otherwise
    """
    container = find_container_by_serial(serial)

    res = container.delete_container_info(ikey, keep_internal=True)
    return res


def assign_user(serial: str, user: User) -> bool:
    """
    Assign a user to a container.

    :param serial: container serial
    :param user: user to assign to the container
    :return: True on success, False otherwise
    """
    container = find_container_by_serial(serial)

    res = container.add_user(user)
    return res


def unassign_user(serial: str, user: User) -> bool:
    """
    Unassign a user from a container.

    :param serial: container serial
    :param user: user to unassign from the container
    :return: True on success, False otherwise
    """
    container = find_container_by_serial(serial)

    res = container.remove_user(user)
    return res


def set_container_description(serial: str, description: str):
    """
    Set the description of a container.

    :param serial: serial of the container
    :param description: new description
    """
    container = find_container_by_serial(serial)

    container.description = description


def set_container_states(serial: str, states: list) -> dict:
    """
    Set the states of a container.

    :param serial: serial of the container
    :param states: new states as list of str
    :returns: Dictionary in the format {state: success}
    """
    container = find_container_by_serial(serial)

    res = container.set_states(states)
    return res


def add_container_states(serial: str, states: list) -> dict:
    """
    Add the states to a container.

    :param serial: serial of the container
    :param states: additional states as list of str
    :returns: Dictionary in the format {state: success}
    """
    container = find_container_by_serial(serial)

    res = container.add_states(states)
    return res


def set_container_realms(serial: str, realms: list,
                         allowed_realms: Union[list, None] = []) -> dict:
    """
    Set the realms of a container.

    :param serial: serial of the container
    :param realms: new realms as list of str
    :param allowed_realms: A list of realms the admin is allowed to set (None if all realms are allowed), optional
    :returns: Dictionary in the format {realm: success}, the entry 'deleted' indicates whether existing realms were
              deleted.
    """
    container = find_container_by_serial(serial)
    old_realms = [realm.name for realm in container.realms]

    # Check if admin is allowed to set the realms
    matching_realms = realms
    res_failed = {}
    if allowed_realms:
        matching_realms = list(set(realms).intersection(allowed_realms))
        excluded_realms = list(set(realms) - set(matching_realms))
        if len(excluded_realms) > 0:
            log.info(f"User is not allowed to set realms {excluded_realms} for container {serial}.")
            res_failed = {realm: False for realm in excluded_realms}

        # Check if admin is allowed to remove the old realms
        not_allowed_realms = set(old_realms) - set(allowed_realms)
        # Add realms that are not allowed to be removed to the set list
        matching_realms = list(set(matching_realms).union(not_allowed_realms))

    # Set realms
    res = container.set_realms(matching_realms, add=False)
    res.update(res_failed)
    return res


def add_container_realms(serial: str, realms: list, allowed_realms: Union[list, None]) -> dict:
    """
    Add the realms to the container realms.

    :param serial: serial of the container
    :param realms: new realms as list of str
    :param allowed_realms: A list of realms the admin is allowed to set, optional
    :returns: Dictionary in the format {realm: success}, the entry 'deleted' indicates whether existing realms were
              deleted.
    """
    container = find_container_by_serial(serial)

    # Check if admin is allowed to set the realms
    matching_realms = realms
    res_failed = {}
    if allowed_realms:
        matching_realms = list(set(realms).intersection(allowed_realms))
        excluded_realms = list(set(realms) - set(matching_realms))
        if len(excluded_realms) > 0:
            log.info(f"User is not allowed to set realms {excluded_realms} for container {serial}.")
            res_failed = {realm: False for realm in excluded_realms}

    # Add realms
    res = container.set_realms(matching_realms, add=True)
    res.update(res_failed)
    return res


def get_container_realms(serial: str) -> list:
    """
    Get the realms of the container.

    :param serial: serial of the container
    :returns: List of realm names
    """
    container = find_container_by_serial(serial)
    return [realm.name for realm in container.realms]


def create_container_dict(container_list: list, no_token: bool = False, user: User = None,
                          logged_in_user_role: str = 'user', allowed_token_realms: Union[list, None] = [],
                          hide_token_info: list = None) -> list:
    """
    Create a dictionary for each container in the list.
    It contains the container properties, owners, realms, tokens and info.
    The information is only provided if the user is allowed to see it.

    :param container_list: List of container objects
    :param no_token: If True, the token information is not included
    :param user: The user object requesting the containers
    :param logged_in_user_role: The role of the logged-in user ('admin' or 'user')
    :param allowed_token_realms: A list of realms the admin is allowed to see tokens from
    :param hide_token_info: List of token info keys to hide in the response, optional
    :return: List of container dictionaries

    Example of a returned list:
        ::

            [
                {
                    "type": "generic",
                    "serial": "CONT0001",
                    "description": "Container description",
                    "last_authentication": "2021-06-01T12:00:00+00:00",
                    "last_synchronization": "2021-06-01T12:00:00+00:00",
                    "states": ["active"],
                    "users": [
                        {
                            "user_name": "user1",
                            "user_realm": "realm1",
                            "user_resolver": "resolver1",
                            "user_id": 1
                        }
                        ],
                    "tokens": [
                        {
                            "serial": "TOTP0001",
                            "type": "totp",
                            "active": true,
                            ...
                        }],
                    "info": {"hash_algorithm": "SHA256", ...},
                    "internal_info_keys": ["hash_algorithm"],
                    "realms": ["realm1", "realm2"],
                    "template": "template1"
                }, ...
            ]
    """
    res: list = []
    for container in container_list:
        container_dict = container.get_as_dict(include_tokens=not no_token, public_info=True)
        if not no_token:
            token_serials = ",".join(container_dict["tokens"])
            tokens_dict_list = []
            if len(token_serials) > 0:
                tokens = get_tokens(serial=token_serials)
                tokens_dict_list = convert_token_objects_to_dicts(tokens, user=user, user_role=logged_in_user_role,
                                                                  allowed_realms=allowed_token_realms,
                                                                  hidden_token_info=hide_token_info)
            container_dict["tokens"] = tokens_dict_list

        res.append(container_dict)

    return res


def create_endpoint_url(base_url: str, endpoint: str) -> str:
    """
    Creates the url for an endpoint. It concat the base_url and the endpoint if the endpoint is not already in the
    base_url. base_url and endpoint are separated by a slash.

    :param base_url: The base url of the host
    :param endpoint: The endpoint
    :return: The url for the endpoint
    :rtype: str
    """
    if endpoint not in base_url:
        if base_url[-1] != "/":
            base_url += "/"
        endpoint_url = base_url + endpoint
    else:
        endpoint_url = base_url
    return endpoint_url


def finalize_registration(container_serial: str, params: dict) -> dict:
    """
    Finalize the registration of a container if the challenge response is valid.
    If the container is in the registration_state `rollover`, it finalizes the container rollover.

    :param container_serial: The serial of the container
    :param params: The parameters for the registration as dictionary
    :return: dictionary with container specific information
    """
    # Get container
    container = find_container_by_serial(container_serial)
    container_info = container.get_container_info_dict()
    registration_state = container_info.get("registration_state")

    # Update params with registration url
    if registration_state == "rollover":
        server_url = container_info.get("rollover_server_url")
    else:
        server_url = container_info.get("server_url")
    if server_url is None:
        log.debug("Server url is not set in the container info. Ensure that registration/init is called first.")
        server_url = " "
    scope = create_endpoint_url(server_url, "container/register/finalize")
    params.update({'scope': scope})

    res = container.finalize_registration(params)

    if registration_state == "rollover":
        # container registration rolled over: set rollover info as correct info
        for key, value in container_info.items():
            if key.find("rollover_") == 0:
                original_key = key.replace("rollover_", "")
                container.update_container_info(
                    [TokenContainerInfoData(key=original_key, value=value, info_type=PI_INTERNAL)])
                container.delete_container_info(key, keep_internal=False)

        finalize_container_rollover(container)
        container.update_container_info(
            [TokenContainerInfoData(key="registration_state", value="rollover_completed", info_type=PI_INTERNAL)])

    return res


def finalize_container_rollover(container: TokenContainerClass):
    """
    Finalize the rollover of a container. For each token in the container a rollover is performed.
    All previous challenges are deleted.

    :param container: The container object
    """

    tokens = container.get_tokens()

    # Offline tokens can not be rolled over, that would invalidate the offline otp values
    offline_serials = [token.get_serial() for token in tokens if is_offline_token(token.get_serial())]
    online_tokens = [token for token in tokens if token.get_serial() not in offline_serials]
    if len(offline_serials) > 0:
        log.info(f"The following offline tokens are in the container: {offline_serials}. "
                 "They can not be rolled over.")

    for token in online_tokens:
        params = {"serial": token.get_serial(),
                  "type": token.get_type(),
                  "genkey": True,
                  "rollover": True}
        token_info = token.get_tokeninfo()
        params.update(token_info)
        try:
            token = init_token(params)
        except Exception as ex:
            # Do not block the rollover process
            log.debug(f"Error during rollover of token {token.get_serial()} in container rollover: {ex}")

    # Delete previous challenges of the container
    delete_challenges(container.serial)


def init_container_rollover(container: TokenContainerClass, server_url: str, challenge_ttl: int, registration_ttl: int,
                            ssl_verify: bool, params: dict) -> dict:
    """
    Initializes the rollover of a container.
    First the response to the challenge is validated. If it is valid, the registration is initialized.
    The new registration info is not finally set until the new container successfully finalized the registration.

    :param container: The container object
    :param server_url: The server url of the privacyIDEA server the client can contact
    :param challenge_ttl: The time to live of the challenge in minutes
    :param registration_ttl: The time to live of the challenge for the registration in minutes
    :param ssl_verify: If the client has to verify the ssl certificate of the server
    :param params: Container type specific parameters for the registration as dictionary
    :return: dictionary with container specific information for the client
    """
    # Check challenge if rollover is allowed
    rollover_scope = create_endpoint_url(server_url, "container/rollover")
    params.update({"scope": rollover_scope})
    container.check_challenge_response(params)

    registration_scope = create_endpoint_url(server_url, "container/register/finalize")
    params.update({"scope": registration_scope})

    # Get registration data
    res = container.init_registration(server_url, registration_scope, registration_ttl, ssl_verify, params)

    # Set registration state
    info = [TokenContainerInfoData(key="registration_state", value="rollover", info_type=PI_INTERNAL),
            TokenContainerInfoData(key="rollover_server_url", value=server_url, info_type=PI_INTERNAL),
            TokenContainerInfoData(key="rollover_challenge_ttl", value=str(challenge_ttl), info_type=PI_INTERNAL)]
    container.update_container_info(info)

    return res


def unregister(container: TokenContainerClass) -> bool:
    """
    Unregister a container from the synchronization and deletes all challenges for the container.

    :param container: The container object
    :return: True on success
    """
    # terminate registration
    container.terminate_registration()

    # Delete all challenges of the container
    delete_challenges(serial=container.serial)

    return True


def set_options(serial: str, options: dict):
    """
    Set the options of a container. The user has to be an admin or the owner of the container.

    :param serial: The serial of the container
    :param options: The options as dictionary
    """
    container = find_container_by_serial(serial)

    container.add_options(options)


def get_container_template_classes() -> dict:
    """
    Returns a dictionary of all available container template classes in the format: { type: class }.
    New container template types have to be added here.
    """
    # className: module
    classes = {
        "ContainerTemplateBase": "privacyidea.lib.containertemplate.containertemplatebase",
        "SmartphoneContainerTemplate": "privacyidea.lib.containertemplate.smartphonetemplate",
        "YubikeyContainerTemplate": "privacyidea.lib.containertemplate.yubikeytemplate"
    }

    ret = {}
    for cls, mod in classes.items():
        try:
            m = importlib.import_module(mod)
            c = getattr(m, cls)
            ret[c.get_class_type().lower()] = c
        except Exception as ex:  # pragma: no cover
            log.warning(f"Error importing module {cls}: {ex}")

    return ret


def create_container_template(container_type: str, template_name: str, options: dict, default: bool = False) -> int:
    """
    Create a new container template.

    :param container_type: The type of the container
    :param template_name: The name of the template
    :param options: The options for the template as dictionary
    :param default: If True, the template is set as default, optional

    Example for the options dictionary:
        ::

            {
                "tokens": [{"type": "hotp", "genkey": True, "hashlib": "sha256"}, ...]
            }

    :return: ID of the created template
    """
    # Check container type
    if container_type.lower() not in get_container_classes().keys():
        raise EnrollmentError(f"Type '{container_type}' is not a valid type!")

    TokenContainerTemplate(name=template_name, container_type=container_type).save()
    template = get_template_obj(template_name)
    try:
        if options:
            template.template_options = options
        if default:
            template.default = default
    except Exception as ex:
        # We need to delete the template on error, but still want to raise the original exception
        template.delete()
        raise ex

    return template.id


def create_container_template_from_db_object(db_template: TokenContainerTemplate) -> Union[ContainerTemplateBase, None]:
    """
    Create a TokenContainerTemplate object from the given db object.

    :param db_template: The DB object to create the container template from
    :return: The created container template object or None if the container template type is not supported
    """

    for ctypes, cls in get_container_template_classes().items():
        if ctypes.lower() == db_template.container_type.lower():
            try:
                template = cls(db_template)
            except Exception as ex:  # pragma: no cover
                log.warning(f"Error creating container template from db object: {ex}")
                return None
            return template
    return None


def get_all_templates_with_type():
    """
    Returns a list of display strings containing the name and type of all templates.
    """
    templates = TokenContainerTemplate.query.all()
    template_list = []
    for template in templates:
        template_list.append(f"{template.name}({template.container_type})")
    return template_list


def get_templates_by_query(name: str = None, container_type: str = None, default: bool = None, page: int = 0,
                           pagesize: int = 0, sortdir: str = "asc",
                           sortby: str = "name") -> dict:
    """
    Returns a list of all templates or a list filtered by the given parameters.

    :param name: The name of the template, optional
    :param container_type: The type of the container, optional
    :param default: Filters for default templates if True or non-default if False, optional
    :param page: The number of the page to view. 0 if no pagination shall be used
    :param pagesize: The size of the page. 0 if no pagination shall be used
    :param sortdir: The sort direction, either 'asc' or 'desc'
    :param sortby: The attribute to sort by
    :return: a dictionary with a list of templates at the key 'templates' and optionally pagination entries ('prev',
             'next', 'current', 'count')
    """
    sql_query = TokenContainerTemplate.query
    if name:
        sql_query = sql_query.filter(TokenContainerTemplate.name == name)
    if container_type:
        sql_query = sql_query.filter(TokenContainerTemplate.container_type == container_type)
    if default is not None:
        sql_query = sql_query.filter(TokenContainerTemplate.default == default)

    if isinstance(sortby, str):
        # Check that the sort column exists and convert it to a template column
        cols = TokenContainerTemplate.__table__.columns
        if sortby in cols:
            sortby = cols.get(sortby)
        else:
            log.info(f'Unknown sort column "{sortby}". Using "name" instead.')
            sortby = TokenContainerTemplate.name

    if sortdir == "desc":
        sql_query = sql_query.order_by(sortby.desc())
    else:
        sql_query = sql_query.order_by(sortby.asc())

    # paginate if requested
    if page > 0 or pagesize > 0:
        ret = create_pagination(page, pagesize, sql_query, "templates")
    else:
        ret = {"templates": sql_query.all()}

    # create class objects from db objects
    template_obj_list = [create_container_template_from_db_object(template) for template in ret["templates"]]

    # convert to dict
    template_list = []
    for template in template_obj_list:
        template_options = {}
        if template.template_options != "":
            template_options = json.loads(template.template_options)
        template_dict = {"name": template.name,
                         "container_type": template.container_type,
                         "template_options": template_options,
                         "default": template.default}
        template_list.append(template_dict)

    ret["templates"] = template_list

    return ret


def get_template_obj(template_name: str) -> ContainerTemplateBase:
    """
    Returns the template class object for the given template name.
    Raises a ResourceNotFoundError if no template with this name exists.

    :param template_name: The name of the template
    :return: The template class object
    """
    db_template = TokenContainerTemplate.query.filter(TokenContainerTemplate.name == template_name).first()
    if not db_template:
        raise ResourceNotFoundError(f"Template {template_name} does not exist.")
    template = create_container_template_from_db_object(db_template)
    return template


def set_default_template(name: str):
    """
    Sets the template of the given name as default and all other templates for the container type as non-default.

    :param name: The name of the template to be the new default template
    """
    default_template = get_template_obj(name)

    # Get all default templates for the container type and reset them to non-default
    old_default_templates = get_templates_by_query(container_type=default_template.container_type, default=True)
    for template in old_default_templates["templates"]:
        template_obj = get_template_obj(template["name"])
        template_obj.default = False

    default_template.default = True


def compare_template_dicts(template_a: dict, template_b: dict) -> bool:
    """
    Compares two template dictionaries for equal tokens.

    :param template_a: The first template dictionary
    :param template_b: The second template dictionary
    :return: True if the templates contain the same tokens, False otherwise.
    """
    if template_a is None or template_b is None:
        return False

    # get template options
    template_options_a = template_a.get("template_options", {})
    template_options_b = template_b.get("template_options", {})

    # compare tokens
    tokens_a = template_options_a.get("tokens", [])
    tokens_b = template_options_b.get("tokens", [])
    if len(tokens_a) != len(tokens_b):
        # different number of tokens, templates can not be equal
        return False

    unique_tokens_a = [token for token in tokens_a if token not in tokens_b]
    unique_tokens_b = [token for token in tokens_b if token not in tokens_a]
    if len(unique_tokens_a) > 0 or len(unique_tokens_b) > 0:
        return False

    return True


def compare_template_with_container(template: ContainerTemplateBase, container: TokenContainerClass) -> dict:
    """
    Compares the template with the container. It is only evaluated if the token types are equal.

    :param template: The template object
    :param container: The container object
    :return: A dictionary with the differences between the template and the container

    Example of a returned dictionary:
        ::

            {
                "tokens": {
                            "missing": ["hotp"],
                            "additional": ["totp"]
                            }
            }
    """
    result = {"tokens": {"missing": [], "additional": []}}
    template_options = json.loads(template.template_options)

    # compare tokens
    template_tokens = template_options.get("tokens", [])
    template_token_types = [token["type"] for token in template_tokens]
    template_token_count = {ttype: template_token_types.count(ttype) for ttype in template_token_types}
    container_token_types = [token.type for token in container.get_tokens()]
    container_token_count = {ttype: container_token_types.count(ttype) for ttype in container_token_types}

    for ttype, count_template in template_token_count.items():
        count_container = container_token_count.get(ttype, 0)
        if count_template > count_container:
            result["tokens"]["missing"].extend([ttype] * (count_template - count_container))

    for ttype, count_container in container_token_count.items():
        count_template = template_token_count.get(ttype, 0)
        if count_template < count_container:
            result["tokens"]["additional"].extend([ttype] * (count_container - count_template))

    # Check if container and template are equal
    if len(result["tokens"]["missing"]) == 0 and len(result["tokens"]["additional"]) == 0:
        result["tokens"]["equal"] = True
    else:
        result["tokens"]["equal"] = False

    return result


def get_offline_token_serials(container: TokenContainerClass) -> list:
    """
    Returns a list of serials of offline tokens in the container.

    :param container: A TokenContainerClass object
    :return: List of serials of offline tokens in the container
    """
    tokens = container.get_tokens()
    offline_serials = [token.get_serial() for token in tokens if is_offline_token(token.get_serial())]
    return offline_serials
