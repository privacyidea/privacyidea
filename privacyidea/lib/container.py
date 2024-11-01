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

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import get_from_config
from privacyidea.lib.containers.smartphone import SmartphoneOptions
from privacyidea.lib.error import (ResourceNotFoundError, ParameterError, EnrollmentError, UserError, PolicyError,
                                   ContainerRollover)
from privacyidea.lib.log import log_with
from privacyidea.lib.token import (get_token_owner, get_tokens_from_serial_or_user, get_realms_of_token, get_tokens,
                                   convert_token_objects_to_dicts, init_token)
from privacyidea.lib.user import User
from privacyidea.lib.utils import hexlify_and_unicode
from privacyidea.models import (TokenContainer, TokenContainerOwner, Token, TokenContainerToken,
                                Realm, TokenContainerTemplate)

log = logging.getLogger(__name__)


def delete_container_by_id(container_id: int, user: User, user_role="user"):
    """
    Delete the container with the given id. If it does not exist, raises a ResourceNotFoundError.

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
    Delete the container with the given serial. If it does not exist, raises a ResourceNotFoundError.

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

    # Delete challenges
    challenge_list = get_challenges(serial=serial)
    for challenge in challenge_list:
        challenge.delete()

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
                log.warning(f"Error creating container from db object: {ex}")
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
    :rtype: privacyidea.lib.containerclass.TokenContainerClass
    """
    db_container = TokenContainer.query.filter(TokenContainer.serial == serial).first()
    if not db_container:
        raise ResourceNotFoundError(f"Unable to find container with serial {serial}.")

    return create_container_from_db_object(db_container)


def _create_container_query(user: User = None, serial=None, ctype=None, token_serial=None, realms=None,
                            template=None, sortby='serial', sortdir='asc'):
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
        sql_query = sql_query.filter(TokenContainer.serial == serial)

    if ctype:
        sql_query = sql_query.filter(TokenContainer.type == ctype)

    if token_serial:
        sql_query = sql_query.join(TokenContainer.tokens).filter(Token.serial == token_serial)

    if realms:
        sql_query = sql_query.join(TokenContainer.realms).filter(Realm.name.in_(realms))

    if template:
        sql_query = sql_query.join(TokenContainer.template).filter(TokenContainerTemplate.name == template)

    if isinstance(sortby, str):
        # Check that the sort column exists and convert it to a Token column
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


def get_all_containers(user: User = None, serial=None, ctype=None, token_serial=None, realms=None, sortby='serial',
                       sortdir='asc', template=None, page=0, pagesize=0):
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
        ret, db_containers = create_pagination(page, pagesize, sql_query)
    else:  # No pagination
        db_containers = sql_query.all()

    container_list = [create_container_from_db_object(db_container) for db_container in db_containers]
    ret["containers"] = container_list

    return ret


def create_pagination(page, pagesize, sql_query):
    """
        Creates the pagination of a sql query.

        :param page: The number of the page to view. Starts with 1
        :param pagesize: The number of objects that shall be shown on one page
        :param sql_query: The sql query to paginate
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
    return ret, db_objects


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


def init_container(params):
    """
    Create a new container with the given parameters. Requires at least the type.

    :param params: The parameters for the new container as dictionary like

        ::

            {
                "type":...,
                "description": ..., (optional)
                "container_serial": ..., (optional)
                "user": ..., Name of the user (optional)
                "realm": ... Name of the realm (optional)
            }

        To assign a user to the container, the user and realm are required.

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

    # Template handling
    template = params.get("template") or {}
    template_tokens = []
    # Check if a template of a valid type is used
    if template.get("container_type") == ctype:
        # check if the template was modified, otherwise save the template name
        stored_templates = get_templates_by_query(name=template["name"])["templates"]
        if len(stored_templates) > 0:
            original_template = stored_templates[0]
            original_template_used = compare_template_dicts(template, original_template)
            if original_template_used:
                container.template = original_template["name"]
        template_options = template.get("template_options", {})
        # set container options from template
        options = template_options.get("options", {})
        container.add_options(options)
        # tokens from template
        template_tokens = template_options.get("tokens", [])

    # container options
    options = params.get("options")
    if options and not template:
        container.add_options(options)

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
    return serial, template_tokens


def create_container_tokens_from_template(container_serial: str, template_tokens: list, request):
    """
    Create tokens for the container from the given template.

    :param container_serial: The serial of the container
    :param template_tokens: The template to create the tokens from as list of dictionaries where each dictionary
    contains the details for a token to be enrolled
    :param request: The request object
    """
    container = find_container_by_serial(container_serial)

    users = container.get_users()
    if len(users) > 0:
        container_owner = users[0]
    else:
        container_owner = User()

    for token_info in template_tokens:

        user = None
        if token_info.get("user"):
            token_info["user"] = container_owner.login
            token_info["realm"] = container_owner.realm
            token_info["resolver"] = container_owner.resolver
            user = container_owner

        request.all_data = {}
        request.all_data.update(token_info)

        # Get policies for the token
        from privacyidea.api.lib.prepolicy import (check_max_token_realm, verify_enrollment, required_piv_attestation,
                                                   webauthntoken_enroll, webauthntoken_request, webauthntoken_allowed,
                                                   indexedsecret_force_attribute, pushtoken_add_config,
                                                   u2ftoken_verify_cert, u2ftoken_allowed, tantoken_count,
                                                   sms_identifiers, papertoken_count, init_token_length_contents,
                                                   init_token_defaults, check_external, check_otp_pin, encrypt_pin,
                                                   init_random_pin, twostep_enrollment_parameters,
                                                   twostep_enrollment_activation, enroll_pin, init_subject_components,
                                                   init_ca_template, init_ca_connector, init_tokenlabel,
                                                   check_token_init, check_max_token_user, require_description)
        try:
            verify_enrollment(request)
            required_piv_attestation(request)
            webauthntoken_enroll(request, None)
            webauthntoken_request(request, None)
            webauthntoken_allowed(request, None)
            indexedsecret_force_attribute(request, None)
            pushtoken_add_config(request, None)
            u2ftoken_verify_cert(request, None)
            u2ftoken_allowed(request, None)
            tantoken_count(request, None)
            sms_identifiers(request, None)
            papertoken_count(request, None)
            init_token_length_contents(request, None)
            init_token_defaults(request, None)
            check_external(request, None)
            check_otp_pin(request, None)
            encrypt_pin(request, None)
            init_random_pin(request, None)
            twostep_enrollment_parameters(request, None)
            twostep_enrollment_activation(request, None)
            enroll_pin(request, None)
            init_subject_components(request, None)
            init_ca_template(request, None)
            init_ca_connector(request, None)
            init_tokenlabel(request, None)
            check_token_init(request, None)
            check_max_token_user(request, None)
            require_description(request, None)
            check_max_token_realm(request, None)
        except PolicyError as ex:
            log.warning(f"Error creating token {token_info} from template: {ex}")
            continue

        init_params = request.all_data
        try:
            token = init_token(init_params, user)
        except Exception as ex:
            log.warning(f"Error creating token {token_info} from template: {ex}")
            continue
        container.add_token(token)


def add_token_to_container(container_serial, token_serial, user: User = None, user_role="user"):
    """
    Add a single token to a container. If a token is already in a container it is removed from the old container.
    Raises a ResourceNotFoundError if either the container or token does not exist.
    Raises a PolicyError if the user is not allowed to add the token to the container. The user/admin needs the rights
    to edit the container, the token and if the token is already in a container, also the rights for this container.

    :param container_serial: The serial of the container
    :param token_serial: The serial of the token
    :param user: The user adding the token
    :param user_role: The role of the user ('admin' or 'user')
    :return: True on success
    """
    container = find_container_by_serial(container_serial)
    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    # Get the token object
    token = get_tokens_from_serial_or_user(token_serial, None)[0]

    # Check if the token is in a container
    old_container = find_container_for_token(token_serial)

    # Check if admin/user is allowed to add the token to the container
    if user_role == "admin" or token.user == user:
        if old_container:
            # Remove token from old container (raises PolicyError if user is not allowed to edit the old container)
            remove_token_from_container(old_container.serial, token_serial, user, user_role)
            log.info(f"Adding token {token.get_serial()} to container {container_serial}: "
                     f"Token removed from previous container {old_container.serial}.")
        res = container.add_token(token)

    else:
        raise PolicyError(f"User {user} is not allowed to add token {token.get_serial()} "
                          f"to container {container_serial}.")
    return res


def add_multiple_tokens_to_container(container_serial, token_serials, user: User = None, user_role="user",
                                     allowed_realms=[]):
    """
    Add the given tokens to the container with the given serial. Raises a ResourceNotFoundError if the container does
    not exist. If a token is already in a container it is removed from the old container.
    A user is only allowed to add a token to a container if the user is an admin or the owner of both. If the token is
    already in a container, the user also has to be the owner of the old container.

    :param container_serial: The serial of the container
    :param token_serials: A list of token serials to add
    :param user: The user adding the tokens
    :param user_role: The role of the user ('admin' or 'user')
    :param allowed_realms: A list of realms the admin is allowed to add tokens to, optional
    :return: A dictionary in the format {token_serial: success}
    """
    # Raises ResourceNotFound if container does not exist
    find_container_by_serial(container_serial)

    ret = {}
    for token_serial in token_serials:
        # Check if admin is allowed to add the token to the container
        if user_role == "admin" and allowed_realms:
            token_realms = get_realms_of_token(token_serial)
            matching_realms = list(set(token_realms).intersection(allowed_realms))
            if len(matching_realms) == 0:
                ret[token_serial] = False
                log.info(
                    f"User {user} is not allowed to add token {token_serial} to container {container_serial}.")
                continue
        try:
            res = add_token_to_container(container_serial, token_serial, user, user_role)
        except Exception as ex:
            # We are catching the exception here to be able to add the remaining tokens
            log.warning(f"Error adding token {token_serial} to container {container_serial}: {ex}")
            res = False
        ret[token_serial] = res

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
    Returns a dictionary of {"type": ["tokentype0", "tokentype1", ...]} entries for all container types.
    Used to list the supported token types for each container type.
    """
    ret = {}
    classes = get_container_classes()
    for container_type, container_class in classes.items():
        ret[container_type] = container_class.get_supported_token_types()
    return ret


def remove_token_from_container(container_serial, token_serial, user: User = None, user_role="user"):
    """
    Remove the given token from the container with the given serial.
    Raises a ResourceNotFoundError if the container or token does not exist. Raises a PolicyError if the user is not
    allowed to remove the token from the container. The user/admin needs the rights to edit the container, the token and
    if the token is already in a container, also the rights for this container.

    :param container_serial: The serial of the container
    :param token_serial: the serial of the token to remove
    :param user: The user adding the token
    :param user_role: The role of the user ('admin' or 'user')
    :return: True on success
    """
    container = find_container_by_serial(container_serial)

    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    token_owner = get_token_owner(token_serial)
    if user_role == "admin" or user == token_owner:
        res = container.remove_token(token_serial)
    else:
        raise PolicyError(
            f"User {user} is not allowed to remove token {token_serial} from container {container_serial}.")
    return res


def remove_multiple_tokens_from_container(container_serial, token_serials, user: User = None, user_role="user",
                                          allowed_realms=[]):
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
    :param allowed_realms: A list of realms the user is allowed to remove tokens from (only for admins), optional
    :return: A dictionary in the format {token_serial: success}
    """
    # Raises ResourceNotFound if container does not exist
    find_container_by_serial(container_serial)

    ret = {}
    for token_serial in token_serials:
        # Check if admin is allowed to remove the token from the container
        if user_role == "admin" and allowed_realms:
            token_realms = get_realms_of_token(token_serial)
            matching_realms = list(set(token_realms).intersection(allowed_realms))
            if len(matching_realms) == 0:
                ret[token_serial] = False
                log.info(
                    f"User {user} is not allowed to remove token {token_serial} from container {container_serial}.")
                continue
        try:
            res = remove_token_from_container(container_serial, token_serial, user, user_role)
        except Exception as ex:
            # We are catching the exception here to be able to remove the remaining tokens
            log.warning(f"Error removing token {token_serial} from container {container_serial}: {ex}")
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
    :returns: True on success
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
    :param info: The info dictionary in the format {key: value}
    :param user: The user adding the info
    :param user_role: The role of the user ('admin' or 'user')
    :returns: True on success
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
            log.warning(f"Info key {ikey} not found in container {serial}.")
    return container_info


def delete_container_info(serial, ikey=None, user=None, user_role="user"):
    """
    Delete the info of the given key or all infos if no key is given.

    :param serial: The serial of the container
    :param ikey: The info key or None to delete all info keys
    :param user: The user adding the info
    :param user_role: The role of the user ('admin' or 'user')
    :return: True on success, False otherwise
    """
    container = find_container_by_serial(serial)

    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    res = container.delete_container_info(ikey)
    return res


def assign_user(serial, user: User, logged_in_user: User = None, user_role="user"):
    """
    Assign a user to a container.

    :param serial: container serial
    :param user: user to assign to the container
    :param logged_in_user: user performing this action
    :param user_role: role of the logged-in user ("admin" or "user")
    :return: True on success, False otherwise
    """
    container = find_container_by_serial(serial)

    # Check user rights on container
    if not user_role == "admin" and user != logged_in_user:
        raise PolicyError(f"User {logged_in_user} is not allowed to assign user {user} to container {serial}!")

    res = container.add_user(user)
    return res


def unassign_user(serial, user: User, logged_in_user: User = None, user_role="user"):
    """
    Unassign a user from a container.

    :param serial: container serial
    :param user: user to unassign from the container
    :param logged_in_user: user performing this action
    :param user_role: role of the logged-in user ("admin" or "user")
    :return: True on success, False otherwise
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
    :returns: Dictionary in the format {state: success}
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
    :returns: Dictionary in the format {state: success}
    """
    container = find_container_by_serial(serial)

    # Check user rights on container
    _check_user_access_on_container(container, user, user_role)

    res = container.add_states(states)
    return res


def set_container_realms(serial, realms, allowed_realms=[]):
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


def add_container_realms(serial, realms, allowed_realms):
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


def get_container_realms(serial):
    """
    Get the realms of the container.

    :param serial: serial of the container
    :returns: List of realm names
    """
    container = find_container_by_serial(serial)
    return [realm.name for realm in container.realms]


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


def create_container_dict(container_list, no_token=False, user=None, logged_in_user_role='user',
                          allowed_token_realms=[]):
    """
    Create a dictionary for each container in the list.
    It contains the container properties, owners, realms, tokens and info.
    The information is only provided if the user is allowed to see it.

    :param container_list: List of container objects
    :param no_token: If True, the token information is not included
    :param user: The user object requesting the containers
    :param logged_in_user_role: The role of the logged-in user ('admin' or 'user')
    :param allowed_token_realms: A list of realms the admin is allowed to see tokens from
    :return: List of container dictionaries like

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
                    "realms": ["realm1", "realm2"],
                    "template": "template1"
                }, ...
            ]
    """
    res: list = []
    for container in container_list:
        container_dict = container.get_as_dict()

        if no_token:
            del container_dict["tokens"]
        else:
            token_serials = ",".join(container_dict["tokens"])
            tokens_dict_list = []
            if len(token_serials) > 0:
                tokens = get_tokens(serial=token_serials)
                tokens_dict_list = convert_token_objects_to_dicts(tokens, user=user, user_role=logged_in_user_role,
                                                                  allowed_realms=allowed_token_realms)
            container_dict["tokens"] = tokens_dict_list

        infos: dict = {}
        black_key_list = ["private_key_server", "public_key_server", "public_key_container", "rollover_server_url",
                          "rollover_challenge_ttl"]
        for info in container.get_container_info():
            if info.key not in black_key_list:
                infos[info.key] = info.value
        container_dict["info"] = infos

        res.append(container_dict)

    return res


def create_endpoint_url(base_url, endpoint):
    """
    Creates the url for an endpoint.

    :param base_url: The base url of the host
    :param endpoint: The endpoint
    :return: The url for the endpoint
    """
    if endpoint not in base_url:
        if base_url[-1] != "/":
            base_url += "/"
        endpoint_url = base_url + endpoint
    else:
        endpoint_url = base_url
    return endpoint_url


def finalize_registration(container_serial: str, params: dict):
    """
    Finalize the registration of a container if the challenge response is valid.
    It also finalizes a container rollover.
    """
    # Get container
    container = find_container_by_serial(container_serial)
    container_info = container.get_container_info_dict()
    registration_state = container_info.get("registration_state")

    # Update params with registration url
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
            if "rollover" in key:
                original_key = key.replace("rollover_", "")
                container.add_container_info(original_key, value)
                container.delete_container_info(key)

        finalize_container_rollover(container)

    return res


def finalize_container_rollover(container: TokenContainer):
    tokens = container.get_tokens()
    for token in tokens:
        params = {"serial": token.get_serial(),
                  "type": token.get_type(),
                  "genkey": True,
                  "rollover": True}
        try:
            token = init_token(params)
        except Exception as ex:
            # Do not block the rollover process
            log.debug(f"Error during rollover of token {token.get_serial()} in container rollover: {ex}")
        # token.enable(False)


def init_container_rollover(container: TokenContainer, server_url: str, challenge_ttl: int, registration_ttl: int,
                            ssl_verify: str, params: dict):
    # Check if rollover is allowed
    rollover_right = container.get_container_info_dict().get(SmartphoneOptions.ALLOW_ROLLOVER)
    if rollover_right != 'True':
        raise ContainerRollover("Rollover is not allowed for this container.")

    # Check challenge if rollover is allowed
    container.check_challenge_response(params)

    scope = create_endpoint_url(server_url, "container/register/finalize")

    # Get registration data
    res = container.init_registration(server_url, scope, registration_ttl, ssl_verify, params)

    # Set registration state
    container.add_container_info("registration_state", "rollover")
    container.add_container_info("rollover_server_url", server_url)
    container.add_container_info("rollover_challenge_ttl", challenge_ttl)

    return res


def unregister(container: TokenContainer):
    """
    Unregister a container from the synchronization. The user has to be an admin or the owner of the container.

    :param container: The container object
    :return: True on success
    """
    # terminate registration
    res_registration = container.terminate_registration()

    # Delete all challenges of the container
    challenge_list = get_challenges(serial=container.serial)
    for challenge in challenge_list:
        challenge.delete()

    return res_registration


def set_options(serial: str, options: dict, user: User = None, user_role="user"):
    """
    Set the options of a container. The user has to be an admin or the owner of the container.

    :param serial: The serial of the container
    :param options: The options as dictionary
    :param user: The user object
    :param user_role: The role of the user ('admin' or 'user')
    """
    container = find_container_by_serial(serial)

    # Check if user is admin or owner of container
    _check_user_access_on_container(container, user, user_role)

    container.add_options(options)


def get_container_template_classes():
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


def create_container_template(container_type: str, template_name: str, options: dict, default: bool = False):
    """
    Create a new container template.
    :param container_type: The type of the container
    :param template_name: The name of the template
    :param options: The options for the template as dictionary
    :param default: If True, the template is set as default
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


def create_container_template_from_db_object(db_template: TokenContainerTemplate):
    """
    Create a TokenContainerTemplate object from the given db object.

    :param db_template: The db object to create the container template from
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


def get_templates_by_query(name: str = None, container_type: str = None, default: bool = None, page: int = 0,
                           pagesize: int = 0):
    """
    Returns a list of all templates or a list filtered by the given parameters.

    :param name: The name of the template, optional
    :param container_type: The type of the container, optional
    :param default: Filters for default templates if True or non-default if False, optional
    :param page: The number of the page to view. 0 if no pagination shall be used
    :param pagesize: The size of the page. 0 if no pagination shall be used
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

    # paginate if requested
    if page > 0 or pagesize > 0:
        ret, db_templates = create_pagination(page, pagesize, sql_query)
    else:
        ret = {}
        db_templates = sql_query.all()

    # create class objects from db objects
    template_obj_list = [create_container_template_from_db_object(template) for template in db_templates]

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


def get_template_obj(template_name: str):
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

    # Set new default template
    default_template.default = True


def compare_template_dicts(template_a: dict, template_b: dict):
    """
    Compares two template dictionaries for equality.
    Returns True if the templates contain the same content, False otherwise.
    """
    equal = True

    if template_a is None or template_b is None:
        return False

    # get template options
    template_options_a = template_a.get("template_options", {})
    template_options_b = template_b.get("template_options", {})

    # TODO compare options

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

    return equal


def compare_template_with_container(template: TokenContainerTemplate, container: TokenContainer):
    """
    Compares the template with the container.

    :param template: The template object
    :param container: The container object
    :return A dictionary with the differences between the template and the container in the format:

        ::
            {
                "tokens": {
                            "missing": ["hotp"],
                            "additional": ["totp"]
                            },
                "options": {
                            "missing": ["hash_algorithm"],
                            "different": ["encryption_algorithm"],
                            "additional": ["key_algorithm"]
                            }
            }
    """
    result = {"tokens": {"missing": [], "additional": []},
              "options": {"missing": [], "different": [], "additional": []}}
    template_options = json.loads(template.template_options)

    # compare template options with container info
    container_info = container.get_container_info_dict()
    for template_key, template_value in template_options.get("options", {}).items():
        if template_key not in container_info.keys():
            result["options"]["missing"].append(template_key)
        elif container_info[template_key] != template_value:
            result["options"]["different"].append(template_key)
    for container_key, value in container_info.items():
        if container_key not in template_options.get("options", {}).keys():
            result["options"]["additional"].append(container_key)

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

    return result
