#  privacyIDEA is a fork of LinOTP
#
#  2015-11-03   Cornelius Kölbel <cornelius@privacyidea.org>
#               Add memberfunction "exist"
#  2015-06-06   Cornelius Kölbel <cornelius@privacyidea.org>
#               Add the possibility to update the user data.
#  Nov 27, 2014 Cornelius Kölbel <cornelius@privacyidea.org>
#               Migration to flask
#               Rewrite of methods
#               100% test code coverage
#  May 08, 2014 Cornelius Kölbel
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# 2014-10-03 fix getUsername function
#            Cornelius Kölbel <cornelius@privcyidea.org>
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__doc__ = '''These are the library functions for user functions.
It depends on the lib.resolver and lib.realm.

There are and must be no dependencies to the token functions (lib.token)
or to webservices!

This code is tested in tests/test_lib_user.py
'''

import hashlib
import logging
import traceback

from sqlalchemy import select, delete

from privacyidea.lib.error import ParameterError, ResolverError, UserError
from privacyidea.models import CustomUserAttribute, db
from .config import get_from_config, SYSCONF
from .log import log_with
from .realm import (get_realms, realm_is_defined,
                    get_default_realm,
                    get_ordered_resolvers,
                    get_realm_id,
                    get_realms_of_resolver)
from .resolver import (get_resolver_object,
                       get_resolver_type)
from .usercache import (user_cache, cache_username, user_init, delete_user_cache)
from privacyidea.lib.params import get_optional, get_required

log = logging.getLogger(__name__)


class User:
    """
    The user has the attributes ``login``, ``realm`` and ``resolver``.

    Usually a user can be found via "login@realm".

    A user object with an empty login and realm should not exist,
    whereas a user object could have an empty resolver.
    """

    # In some test case the login attribute from a not
    # initialized user is requested. This is why we need
    # these dummy class attributes.
    login = ""
    realm = ""
    resolver = ""

    # NOTE: Directly decorating the class ``User`` breaks ``isinstance`` checks,
    # which is why we have to decorate __init__
    @log_with(log)
    def __init__(self, login="", realm="", resolver="", uid=None):
        self.login = login or ""
        self.used_login = self.login
        self.realm = (realm or "").lower()
        self.realm_id = None
        if resolver == "**":
            resolver = ""
        self.resolver = resolver or ""
        # We never specified the type of the UID, but internally we expect it to be a string (i.e. TokenOwner table)
        # To avoid confusion here if an uid parameter is passed we convert it to a string.
        self.uid = str(uid) if uid else None
        self.rtype = None
        # Hash of already checked passwords and their result. If a user has multiple token, it is not necessary to check
        # the same password multiple times. However, we can not differentiate between PIN+OTP and just PIN, so this dict
        # will have an entry for PIN+OTP (likely to fail) and then the OTP cut off to just PIN. In case the PIN was
        # given in the request, the dict will have only one entry.
        self._checked_passwords = {}
        if not self.login and not self.resolver and uid is not None:
            raise UserError("Can not create a user object from a uid without a resolver!")
        # Enrich user object with information from the userstore or from the
        # user cache
        if login or uid is not None:
            self._get_user_from_userstore()
            # Just store the resolver type
            self.rtype = get_resolver_type(self.resolver)
            # Add realm_id to User object
            self.realm_id = get_realm_id(self.realm)

    @user_cache(user_init)
    def _get_user_from_userstore(self):
        if not self.resolver:
            # set the resolver implicitly!
            self._get_resolvers()

        # Get Identifiers
        if self.resolver:
            resolver = get_resolver_object(self.resolver)
            if resolver is None:
                raise UserError(f"The resolver '{self.resolver!s}' does not exist!")
            if self.uid is None:
                # Determine the uid
                self.uid = resolver.getUserId(self.login)
            if not self.login:
                # Determine the login if it does not exist or
                self.used_login = self.login = resolver.getUsername(self.uid)
            if resolver.has_multiple_loginnames:
                # if the resolver has multiple logins the primary login might be another value!
                self.login = resolver.getUsername(self.uid)

    def is_empty(self) -> bool:
        # ignore if only resolver is set! as it makes no sense
        if len(self.login or "") + len(self.realm or "") == 0:
            return True
        else:
            return False

    def __eq__(self, other):
        """
        Compare two User Objects.

        :param other: The other User object, to which this very object is
        compared.
        :type other: User object
        :return: True or False
        :rtype: bool
        """
        if not isinstance(other, type(self)):
            log.info(f"Comparing a non-user object: {self!s} != {type(other)!s}.")
            return False
        if (self.resolver != other.resolver) or (self.realm != other.realm):
            log.info("Users are not in the same resolver and realm: "
                     f"{self!s} != {other!s}.")
            return False
        if self.uid and other.uid:
            log.debug(f"Comparing based on uid: {self.uid!s} vs {other.uid!s}")
            return self.uid == other.uid
        log.debug(f"Comparing based on login: {self.login!s} vs {other.login!s}")
        return self.login == other.login

    def __ne__(self, other):
        """
        Compare two user objects and return true, if they are not equal

        :param other: The other User object
        :return: True or False
        """
        return not self.__eq__(other)

    def __hash__(self):
        return hash((type(self), self.login, self.resolver, self.realm))

    def __str__(self):
        ret = "<empty user>"
        if not self.is_empty():
            # Realm and resolver should always be ASCII
            conf = ''
            if self.resolver:
                conf = f'.{self.resolver!s}'
            ret = f'<{self.login!s}{conf!s}@{self.realm!s}>'
        return ret

    def __repr__(self):
        ret = (f"User(login={self.login!r}, realm={self.realm!r}, resolver={self.resolver!r})")
        return ret

    def __bool__(self):
        return not self.is_empty()

    __nonzero__ = __bool__

    def _get_resolvers(self, all_resolvers=False) -> list[str]:
        """
        This returns the list of the resolvernames of the user.
        If no resolver attribute exists at the moment, the user is searched
        in the realm and according to this the resolver attribute is set.

        It will only return one resolver in the list for backward compatibility

        .. note:: If the user does not exist in the realm, then an empty
           list is returned!

        :param all_resolvers: return all resolvers (of a realm), in which
            the user is contained
        :return: list of resolvers for self.login
        """
        if self.resolver:
            return [self.resolver]

        resolvers = []
        for resolver_name in get_ordered_resolvers(self.realm):
            # test, if the user is contained in this resolver
            if self._locate_user_in_resolver(resolver_name):
                break
        if self.resolver:
            resolvers = [self.resolver]
        return resolvers

    def _locate_user_in_resolver(self, resolvername: str) -> bool:
        """
        Try to locate the user (by self.login) in the resolver with the given name.
        In case of success, this sets `self.resolver` as well as `self.uid`
        and returns True. If the resolver does not exist or the user does
        not exist in the resolver, False is returned.
        :param resolvername: string denoting the resolver name
        :return: boolean
        """
        resolver = get_resolver_object(resolvername)
        if resolver is None:  # pragma: no cover
            log.info(f"Resolver {resolvername!r} not found!")
            return False
        else:
            uid = resolver.getUserId(self.login)
            if uid not in ["", None]:
                log.info(f"user {self.login!r} found in resolver {resolvername!r}")
                log.info(f"userid resolved to {uid!r} ")
                self.resolver = resolvername
                self.uid = uid
                # We do not need to search other resolvers!
                return True
            else:
                log.debug(f"user {self.login!r} not found"
                          f" in resolver {resolvername!r}")
                return False

    def get_user_identifiers(self) -> tuple[str or int, str, str]:
        """
        This returns the UserId  information from the resolver object and
        the resolvertype and the resolvername
        (former: getUserId)
        (former: getUserResolverId)

        :return: The userid, the resolver type and the resolver name
                 like (1000, "passwdresolver", "resolver1")
        :rtype: tuple
        """
        if not self.resolver:
            raise UserError("The user can not be found in any resolver in "
                            "this realm!")
        return self.uid, self.rtype, self.resolver

    def exist(self) -> bool:
        """
        Check if the user object exists in the user store
        :return: True or False
        """
        # TODO: really check if user exist (ask user store and maybe re-evaluate realm)
        exist = self.uid and self.realm_id
        return exist

    @property
    def info(self) -> dict:
        """
        return the detailed information for the user

        :return: a dict with all the userinformation
        :rtype: dict
        """
        return self.get_specific_info()

    def get_specific_info(self, attributes: list[str] = None) -> dict:
        """
        returns the specified attributes for the user or all if attributes is None

        :return: a dict with the specified user information
        """
        if self.is_empty() or not self.exist():
            # An empty user has no info
            return {}
        (uid, _rtype, _resolver) = self.get_user_identifiers()
        if uid is None:
            return {}
        resolver = get_resolver_object(self.resolver)

        available_attributes = resolver.get_available_info_keys()
        # For now, only exclude groups if not requested as this one might be expensive to retrieve, but request all
        # others to not completely break the LDAP cache
        if attributes is not None and "groups" not in attributes and "groups" in available_attributes:
            available_attributes.remove("groups")
        full_user_info = resolver.get_user_info(uid, available_attributes)
        # only return requested attributes
        user_info = {key: value for key, value in full_user_info.items() if attributes is None or key in attributes}
        # Now add the custom attributes, this is used e.g. in ADDUSERINRESPONSE
        user_info.update(self.attributes)
        return user_info

    @property
    def available_info_keys(self) -> list[str]:
        """
        returns the possible keys for user information for this user

        :return: a list of possible keys for user information
        :rtype: list
        """
        if self.is_empty() or not self.exist():
            # An empty user has no info
            return []
        resolver = get_resolver_object(self.resolver)
        return resolver.get_available_info_keys()

    @log_with(log)
    def set_attribute(self, attribute_key: str, attribute_value: str, attribute_type: str = None) -> int:
        """
        Set a custom attribute for a user

        :param attribute_key: The key of the attribute
        :param attribute_value: The value of the attribute
        :return: The id of the attribute setting
        """
        stmt = select(CustomUserAttribute).filter_by(
            user_id=self.uid,
            resolver=self.resolver,
            realm_id=self.realm_id,
            Key=attribute_key
        )
        existing_attribute = db.session.execute(stmt).scalar_one_or_none()

        if existing_attribute:
            existing_attribute.Value = attribute_value
            existing_attribute.Type = attribute_type
            attribute_id = existing_attribute.id
        else:
            new_attribute = CustomUserAttribute(user_id=self.uid, resolver=self.resolver, realm_id=self.realm_id,
                                                Key=attribute_key, Value=attribute_value, Type=attribute_type)
            db.session.add(new_attribute)
            db.session.flush()
            attribute_id = new_attribute.id
        db.session.commit()
        return attribute_id

    @property
    def attributes(self) -> dict:
        """
        returns the custom attributes of a user
        :return: a dictionary of attributes with keys and values
        """
        return get_attributes(self.uid, self.resolver, self.realm_id)

    @log_with(log)
    def delete_attribute(self, attribute_key: str = None) -> int:
        """
        Delete the given key as custom user attribute.
        If no key is given, then all attributes are deleted

        :param attribute_key: The key to delete
        :return: The number of deleted rows
        """
        stmt = delete(CustomUserAttribute).filter_by(user_id=self.uid, resolver=self.resolver,
                                                     realm_id=self.realm_id)
        if attribute_key:
            stmt = stmt.filter_by(Key=attribute_key)
        result = db.session.execute(stmt)
        db.session.commit()
        return result.rowcount

    @log_with(log)
    def get_user_phone(self, phone_type: str = 'phone', index: int = None) -> str or list[str]:
        """
        Returns the phone number or a list of phone numbers of a user.

        :param phone_type: The type of the phone, i.e. either mobile or
                           phone (land line)
        :type phone_type: string
        :param index: The index of the selected phone number of list of the phones of the user.
            If the index is given, this phone number as string is returned.
            If the index is omitted, all phone numbers are returned.

        :returns: list with phone numbers of this user object
        """
        userinfo = self.get_specific_info([phone_type])
        if phone_type in userinfo:
            phone = userinfo[phone_type]
            log.debug(f"got user phone {phone!r} of type {phone_type!r}")
            if isinstance(phone, list) and index is not None:
                if len(phone) > index:
                    return phone[index]
                else:
                    log.warning(f"userobject ({self!r}) has not that much "
                                f"phone numbers ({index!r} of {phone!r}).")
                    return ""
            else:
                return phone
        else:
            log.warning(f"userobject ({self!r}) has no phone of type {phone_type!r}.")
            return ""

    @log_with(log)
    def get_user_realms(self) -> list[str]:
        """
        Returns a list of the realms, a user belongs to.
        Usually this will only be one realm.
        But if the user object has no realm but only a resolver,
        than all realms, containing this resolver are returned.
        This function is used for the policy module

        :return: realms of the user
        :rtype: list
        """
        all_realms = get_realms()
        user_realms = []
        if self.realm == "" and self.resolver == "":
            default_realm = get_default_realm().lower()
            user_realms.append(default_realm)
            self.realm = default_realm
        elif self.realm != "":
            user_realms.append(self.realm.lower())
        else:
            # User has no realm!
            # we have got a resolver and will get all realms
            # the resolver belongs to.
            for key, val in all_realms.items():
                log.debug(f"evaluating realm {key!r}: {val!r} ")
                for reso in val.get('resolver', []):
                    resoname = reso.get("name")
                    if resoname == self.resolver:
                        user_realms.append(key.lower())
                        log.debug(f"added realm {key!r} to Realms due to "
                                  f"resolver {self.resolver!r}")
        return user_realms

    @log_with(log, log_entry=False)
    def check_password(self, password: str) -> str or None:
        """
        The password of the user is checked against the user source

        :param password: The clear text password
        :return: the username of the authenticated user.
                 If unsuccessful, returns None
        """
        success = None

        # The password hash is used to avoid multiple password checks at the
        # resolver. It is not persisted in any way and only stored in memory for
        # the duration of the request.
        password_hash = hashlib.sha3_512(password.encode("utf-8")).hexdigest()

        try:
            log.info(f"User {self.login} from realm {self.realm} tries to authenticate")
            # If the password was already checked, return the known result
            if password_hash in self._checked_passwords.keys():
                if self._checked_passwords[password_hash]:
                    success = f"{self.login}@{self.realm}"
                    log.debug(f"Successfully authenticated user {self} from request cache.")
                else:
                    log.info(f"User {self} failed to authenticate from request cache.")
                return success
            res = self._get_resolvers()
            # Now we know, the resolvers of this user, and we can verify the password
            if len(res) == 1:
                from .resolvers.HTTPResolver import HTTPResolver
                resolver = get_resolver_object(self.resolver)
                uid, _rtype, _rname = self.get_user_identifiers()
                if isinstance(resolver, HTTPResolver):
                    valid_credentials = resolver.checkPass(uid, password, self.login)
                else:
                    valid_credentials = resolver.checkPass(uid, password)
                if valid_credentials:
                    success = f"{self.login}@{self.realm}"
                    log.debug(f"Successfully authenticated user {self}.")
                    self._checked_passwords[password_hash] = True
                else:
                    log.info(f"User {self} failed to authenticate.")
                    self._checked_passwords[password_hash] = False

            elif not res:
                log.error(f"The user {self!r} exists in NO resolver.")
        except UserError as e:  # pragma: no cover
            log.error(f"Error while trying to verify the username: {e}")
        except Exception as e:  # pragma: no cover
            log.error(f"Error checking password within module {e}")
            log.debug(f"{traceback.format_exc()}")

        return success

    @log_with(log)
    def get_search_fields(self) -> dict:
        """
        Return the valid search fields of a user.
        The search fields are defined in the UserIdResolver class.

        :return: searchFields with name (key) and type (value)
        :rtype: dict
        """
        search_fields = {}

        for reso in self._get_resolvers():
            # try to load the UserIdResolver Class
            try:
                y = get_resolver_object(reso)
                sf = y.get_search_fields()
                search_fields[reso] = sf

            except Exception as e:  # pragma: no cover
                log.warning(f"module {reso!r}: {e!r}")

        return search_fields

    # If passwords should not be logged, we hide it from the log entry
    @log_with(log, hide_kwargs=["password"])
    def update_user_info(self, attributes : dict, password: str = None) -> bool:
        """
        This updates the given attributes of a user.
        The attributes can be "username", "surname", "givenname", "email",
        "mobile", "phone", "password"

        :param attributes: A dictionary of the attributes to be updated
        :param password: The password of the user
        :return: True in case of success
        """
        if password is not None:
            attributes["password"] = password
        success = False
        try:
            log.info(f"User info for user {self.login!r}@{self.realm!r} about to "
                     "be updated.")
            res = self._get_resolvers()
            # Now we know, the resolvers of this user and we can update the
            # user
            if len(res) == 1:
                resolver = get_resolver_object(self.resolver)
                if not resolver.updateable:  # pragma: no cover
                    log.warning(f"The resolver {resolver!r} is not updateable.")
                else:
                    uid, _rtype, _rname = self.get_user_identifiers()
                    if resolver.update_user(uid, attributes):
                        success = True
                        # Delete entries corresponding to the old username from the user cache
                        delete_user_cache(username=self.login, resolver=self.resolver)
                        # If necessary, update the username
                        if attributes.get("username"):
                            self.login = attributes.get("username")
                        log.info(f"Successfully updated user {self!r}.")
                    else:  # pragma: no cover
                        log.info(f"user {self!r} failed to update.")

            elif not res:  # pragma: no cover
                log.error(f"The user {self!r} exists in NO resolver.")
        except UserError as exx:  # pragma: no cover
            log.error(f"Error while trying to verify the username: {exx!r}")

        return success

    @log_with(log)
    def delete(self) -> bool:
        """
        This deletes the user in the user store. I.e. the user in the SQL
        database or the LDAP gets deleted.

        Returns True in case of success
        """
        success = False
        try:
            log.info(f"User {self.login!r}@{self.realm!r} about to be deleted.")
            res = self._get_resolvers()
            # Now we know, the resolvers of this user and we can delete it
            if len(res) == 1:
                resolver = get_resolver_object(self.resolver)
                if not resolver.updateable:  # pragma: no cover
                    log.warning(f"The resolver {resolver!r} is not updateable.")
                else:
                    uid, _rtype, _rname = self.get_user_identifiers()
                    if resolver.delete_user(uid):
                        success = True
                        log.info(f"Successfully deleted user {self!r}.")
                        # Delete corresponding entry from the user cache
                        delete_user_cache(username=self.login, resolver=self.resolver)
                    else:  # pragma: no cover
                        log.info(f"user {self!r} failed to update.")

            elif not res:  # pragma: no cover
                log.error(f"The user {self!r} exists in NO resolver.")
        except UserError as exx:  # pragma: no cover
            log.error(f"Error while trying to verify the username: {exx!r}")
        except Exception as exx:  # pragma: no cover
            log.error(f"Error checking password within module {exx!r}")
            log.debug(f"{traceback.format_exc()!s}")

        return success

    def user_export_dict(self) -> dict:
        """
        Returns a dictionary with the user identifiers, which can be used to
        assign a token to the same user after import.

        :return: A dictionary with the user identifiers
        """
        return {
            "login": self.login,
            "realm": self.realm,
            "resolver": self.resolver,
            "uid": self.uid,
            "custom_attributes": self.attributes
        }

@log_with(log, hide_kwargs=["password"])
def create_user(resolvername: str, attributes: dict, password: str = None) -> int or str:
    """
    This creates a new user in the given resolver. The resolver must be
    editable to do so.

    The attributes is a dictionary containing the keys "username", "email",
    "phone",
    "mobile", "surname", "givenname", "password".

    We return the UID and not the user object, since the user could be located
    in several realms!

    :param resolvername: The name of the resolver, in which the user should
        be created
    :type resolvername: basestring
    :param attributes: Attributes of the user
    :type attributes: dict
    :param password: The password of the user
    :return: The uid of the user object
    """
    if password is not None:
        attributes["password"] = password
    resolver = get_resolver_object(resolvername)
    uid = resolver.add_user(attributes)
    return uid


@log_with(log)
def split_user(username: str) -> tuple[str, str]:
    """
    Split the username of the form user@realm into the username and the realm
    splitting myemail@emailprovider.com@realm is also possible and will
    return (myemail@emailprovider.com, realm).

    If for a user@domain the "domain" does not exist as realm, the name is
    not split, since it might be the user@domain in the default realm

    If the Split@Sign configuration is disabled, the username won't be split
    and the username and an empty realm will be returned.

    We can also split realm\\user to (user, realm)

    :param username: the username to split
    :type username: string
    :return: username and realm
    :rtype: tuple
    """
    user = username.strip()
    realm = ""

    split_at_sign = get_from_config(SYSCONF.SPLITATSIGN, return_bool=True)
    if split_at_sign:
        user_split = user.split('@')
        if len(user_split) >= 2:
            if realm_is_defined(user_split[-1]):
                # split the last only if the last part is really a realm
                (user, realm) = user.rsplit('@', 1)
        else:
            user_split = user.split('\\')
            if len(user_split) >= 2:
                (realm, user) = user.rsplit('\\', 1)

    return user, realm


@log_with(log, hide_args_keywords={0: ["pass", "password"]})
def get_user_from_param(param: dict, optional_or_required: bool = True) -> User:
    """
    Find the parameter user, realm and resolver and
    create a user object from these parameters.

    An exception is raised, if a user in a realm is found in more
    than one resolver.

    :param param: The dictionary of request parameters
    :param optional_or_required: ``True`` (default) if the user param is optional,
        ``False`` if it is required (raises ParameterError when absent).
    :return: User as found in the parameters
    """
    realm = ""
    if optional_or_required:
        username = get_optional(param, "user")
    else:
        username = get_required(param, "user")

    if username is None:
        username = ""
    else:
        username, realm = split_user(username)

    if "realm" in param:
        realm = param["realm"]

    if username != "":
        if realm is None or realm == "":
            realm = get_default_realm()

    user_object = User(login=username, realm=realm,
                       resolver=param.get("resolver"))

    return user_object


@log_with(log)
def get_user_list(param: dict = None, user: User = None, include_custom_attributes: bool = False,
                  requested_attributes: list[str] = None) -> list[dict]:
    """
    This function returns a list of user dictionaries. The user dict contains the resolver and custom user attributes,
    if requested.
    If no realm is given in the param, the users from all realms are returned.
    The ``realm``, ``resolver`` and ``editable`` keys are added on the lib layer and are only included in the
    returned user dictionaries when ``requested_attributes`` is None/empty or explicitly lists them.
    If only a resolver is given (no realm), the function looks up all realms containing that resolver and
    iterates through them, so users are always returned in a realm context with proper masking.

    Fixme: Please note: If a realm and a resolver is given, the resolver is currently ignored. So all users
    of this realm are returned. This is the old/current behaviour. When filtering for a resolver in a realm, we
    should probably take care, that masked users (in low priority resolvers) are not returned.

    :param param: search parameters
    :param user:  a specific user object to return
    :param include_custom_attributes:  Set to True, if you want to receive custom attributes of external users.
    :param requested_attributes: A list of attributes to return for each user. If None or empty, all
        attributes are returned.
    :return: list of user info as dictionaries
    """
    # The user dictionary, what we use to avoid duplicates in realms, while searching for users. The key will be the
    # tuple of (username, realm)
    users_dict = {}
    resolvers = []
    search_dict = {"username": "*"}
    param = param or {}

    # we have to recreate a new searchdict without the realm key
    # as delete does not work
    for key in param:
        lval = param[key]
        if key in ["realm", "resolver", "user", "username"]:
            continue
        search_dict[key] = lval
        log.debug(f"Parameter key:{key!r}={lval!r}")

    # update search_dict depending on existence of 'user' or 'username' in param
    # Since 'user' takes precedence over 'username' we have to check the order
    if 'username' in param:
        search_dict['username'] = param['username']
    if 'user' in param:
        search_dict['username'] = param['user']
    log.debug('Changed search key to username: %s.', search_dict['username'])

    # determine which scope we want to show
    param_resolver = get_optional(param, "resolver")
    param_realm = get_optional(param, "realm")
    user_resolver = None
    user_realm = None
    # list of realms to iterate through
    realm_iteration = []
    if user is not None:
        user_resolver = user.resolver
        user_realm = user.realm

    # Determine the realms to iterate through. Dedupe while preserving order in case param_realm == user_realm.
    if param_realm:
        realm_iteration.append(param_realm)
    if user_realm:
        realm_iteration.append(user_realm)
    realm_iteration = list(dict.fromkeys(realm_iteration))

    if not (param_resolver or user_resolver or param_realm or user_realm):
        # if no realm or resolver was specified, we search the resolvers in all realms
        log.debug("Seldom event: Calling get_user_list with absolutely no information on realms or resolvers!")
        all_realms = get_realms()
        realm_iteration = list(all_realms)

    if not realm_iteration:
        # No realm given but a resolver is given. Find all realms that contain this resolver.
        resolver_name = param_resolver or user_resolver
        realm_iteration = get_realms_of_resolver(resolver_name)
        if not realm_iteration:
            log.warning(f"Resolver '{resolver_name}' is not assigned to any realm.")
            return []

    # Determine some display values.
    remove_user_id = False
    if include_custom_attributes and requested_attributes and "userid" not in requested_attributes:
        # user id is required to later get the custom attributes for the user
        requested_attributes.append("userid")
        remove_user_id = True
    log.debug(f"With this search dictionary: {search_dict!r}")
    requested_pi_user_attributes = list({"realm", "resolver", "editable"}.intersection(requested_attributes or []))
    requested_user_store_attributes = list(set(requested_attributes or []) - set(requested_pi_user_attributes))

    for realm in realm_iteration:
        resolvers = get_ordered_resolvers(realm)
        realm_id = get_realm_id(realm)

        for resolver_name in resolvers:
            try:
                log.debug(f"Check for resolver class: {resolver_name!r}")
                resolver = get_resolver_object(resolver_name)
                # Continue if we couldn't find a resolver with the given name
                if not resolver:
                    log.info(f"Can not find a resolver with the name '{resolver_name}'")
                    continue
                user_list = resolver.getUserList(search_dict, requested_user_store_attributes)
                for user_info in user_list:
                    if not requested_attributes or "realm" in requested_pi_user_attributes:
                        user_info["realm"] = realm
                    if not requested_attributes or "resolver" in requested_pi_user_attributes:
                        user_info["resolver"] = resolver_name
                    if not requested_attributes or "editable" in requested_pi_user_attributes:
                        user_info["editable"] = resolver.editable
                    if include_custom_attributes and realm_id is not None:
                        # Add the custom attributes, by class method from User
                        # with uid, resolvername and realm_id, which we need to determine by the realm name
                        custom_attributes = get_attributes(user_info.get("userid"), resolver_name, realm_id,
                                                           requested_attributes)
                        user_info.update(custom_attributes)
                    if remove_user_id:
                        # Remove the userid if it is not requested, as it is only needed for the custom attributes
                        user_info.pop("userid", None)
                    # Add user to users_dict, if it is not contained, yet
                    user_tuple = (user_info.get("username"), realm)
                    if user_tuple not in users_dict:
                        users_dict[user_tuple] = user_info
                log.debug(f"Found this userlist: {user_list!r}")

            except (ResolverError, ParameterError) as ex:
                # In case of wrong search parameters or broken resolver we continue
                # All other errors will be passed down.
                # TODO: Reflect the broken resolver/query in the result data
                log.warning(f"Unable to get user list for resolver '{resolver_name}': {ex!r}")
                log.debug(f"{traceback.format_exc()!s}")
                continue

    users = list(users_dict.values())
    return users


@log_with(log)
@user_cache(cache_username)
def get_username(user_id: str, resolvername: str) -> str:
    """
    Determine the username for a given id and a resolvername.

    :param user_id: The id of the user in a resolver
    :type user_id: string
    :param resolvername: The name of the resolver
    :return: the username or "" if it does not exist
    :rtype: string
    """
    username = ""
    if user_id:
        resolver = get_resolver_object(resolvername)
        if resolver:
            username = resolver.getUsername(user_id)
    return username


def log_used_user(user: User, other_text: str = "") -> str:
    """
    This creates a log message combined of a user and another text.
    The user information is only added, if user.login != user.used_login

    :param user: A user to log
    :type user:  User object
    :param other_text: Some additional text
    :return: str
    """
    return f"logged in as {user.used_login}. {other_text}" if user.used_login != user.login else other_text


def get_attributes(uid: str, resolver: str, realm_id: int, requested_attributes: list[str] = None) -> dict:
    """
    Returns the attributes for the given user.

    :param uid: The UID of the user
    :param resolver: The name of the resolver
    :param realm_id: The realm_id
    :param requested_attributes: A list of attributes to return. If None, all attributes are returned.
    :return: A dictionary of key/values
    """
    stmt = select(CustomUserAttribute).filter_by(user_id=uid, resolver=resolver, realm_id=realm_id)
    if requested_attributes:
        stmt = stmt.filter(CustomUserAttribute.Key.in_(requested_attributes))
    attributes = db.session.scalars(stmt).all()
    custom_attributes = {attribute.Key: attribute.Value for attribute in attributes}
    return custom_attributes


def is_attribute_at_all() -> bool:
    """
    Check if there are custom user attributes at all
    """
    return bool(CustomUserAttribute.query.count())

