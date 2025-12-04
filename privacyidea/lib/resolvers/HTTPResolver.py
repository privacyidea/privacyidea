# (c) NetKnights GmbH 2025,  https://netknights.it
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
# SPDX-FileCopyrightText: 2020 Bruno Cascio
# SPDX-FileCopyrightText: 2025 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
import time
import copy
from dataclasses import dataclass
from enum import Enum
from typing import Union, Optional

from requests import Response, HTTPError

from .UserIdResolver import UserIdResolver
import requests
import logging
import json
from urllib.parse import urlencode
from pydash import get

from ..error import ParameterError, ResolverError
from ..log import log_with
from ..utils import is_true
from ...api.lib.utils import get_required

ENCODING = "utf-8"
EDITABLE = "Editable"
ATTRIBUTE_MAPPING = "attribute_mapping"
CONFIG_GET_USER_LIST = "config_get_user_list"
CONFIG_GET_USER_BY_ID = "config_get_user_by_id"
CONFIG_GET_USER_BY_NAME = "config_get_user_by_name"
CONFIG_CREATE_USER = "config_create_user"
CONFIG_EDIT_USER = "config_edit_user"
CONFIG_DELETE_USER = "config_delete_user"
CONFIG_AUTHORIZATION = "config_authorization"
CONFIG_USER_AUTH = "config_user_auth"
METHOD = "method"
ENDPOINT = "endpoint"
PARAMS = "params"
HEADERS = "headers"
REQUEST_MAPPING = "requestMapping"
RESPONSE_MAPPING = "responseMapping"
HAS_ERROR_HANDLER = "hasSpecialErrorHandler"
ERROR_RESPONSE = "errorResponse"
BASE_URL = "base_url"
ADVANCED = "advanced"
USERNAME = "username"
PASSWORD = "password"
VERIFY_TLS = "verify_tls"
TLS_CA_PATH = "tls_ca_path"
TIMEOUT = "timeout"

log = logging.getLogger(__name__)


@dataclass
class Error:
    """
    Represents an error that occurred during the resolver operation.
    Contains the error code and message.
    """
    error: bool
    code: str
    message: str


class HTTPMethod(Enum):
    GET = "get"
    POST = "post"
    PATCH = "patch"
    PUT = "put"
    DELETE = "delete"

    @classmethod
    def is_valid(cls, method: str) -> bool:
        return method.lower() in [member.value for member in cls]

    @classmethod
    def methods_with_body(cls) -> list:
        """
        Returns a list of HTTP methods that typically include a body in the request.
        """
        return [cls.POST, cls.PATCH, cls.PUT]


class RequestConfig:

    def __init__(self, config: dict, default_headers: dict, tags: Optional[dict] = None, wildcard: str = "*"):
        config = copy.deepcopy(config)
        self._method = HTTPMethod.GET
        self.method = get_required(config, METHOD)
        self.endpoint = get_required(config, ENDPOINT)

        self._header = {}
        headers = config.get(HEADERS)
        if not headers:
            headers = default_headers
        self.headers = copy.deepcopy(headers)

        self.has_error_handler = is_true(config.get(HAS_ERROR_HANDLER, False))
        self._error_response = {}
        if self.has_error_handler:
            self.error_response = config.get(ERROR_RESPONSE, {})

        self._response_mapping = {}
        self.response_mapping = config.get(RESPONSE_MAPPING, {})

        request_mapping = config.get(REQUEST_MAPPING, {})
        if isinstance(request_mapping, dict):
            request_mapping = json.dumps(request_mapping)

        # replace tags in endpoint and request mapping
        if tags:
            for tag, value in tags.items():
                self.endpoint = self.endpoint.replace(f"{{{tag}}}", str(value).replace("*", wildcard))
                request_mapping = request_mapping.replace(f"{{{tag}}}", str(value).replace("*", wildcard))
        content_type = self.headers.get("Content-Type", "application/json")
        if content_type == "application/json":
            try:
                self.request_mapping = self.get_as_dict(request_mapping)
            except json.JSONDecodeError as error:
                raise ParameterError(f"Invalid JSON format for '{REQUEST_MAPPING}' '{request_mapping}': {error}")
        else:
            self.request_mapping = request_mapping

    @staticmethod
    def get_as_dict(value: Union[str, dict]) -> dict:
        """
        Convert the given value to a dictionary.
        """
        if isinstance(value, str):
            if value:
                value_dict = json.loads(value)
            else:
                # Empty strings are handled as empty dict
                value_dict = {}
        elif isinstance(value, dict):
            value_dict = value
        else:
            raise ParameterError(f"Datatype '{type(value)}' can not be converted to dict!")
        return value_dict

    @property
    def method(self) -> HTTPMethod:
        return self._method

    @method.setter
    def method(self, value: str):
        value = value.lower()
        if not HTTPMethod.is_valid(value):
            log.debug(
                f"Invalid method '{value}'. Allowed methods are {', '.join([method.value for method in HTTPMethod])}.")
            raise ParameterError(f"Invalid method '{value}'!")
        self._method = HTTPMethod(value)

    @property
    def headers(self) -> dict:
        return self._headers

    @headers.setter
    def headers(self, value: Union[dict, str]):
        if isinstance(value, str):
            try:
                self._headers = json.loads(value)
            except json.JSONDecodeError:
                raise ParameterError(f"Invalid JSON format for '{HEADERS}': {value}")
        else:
            self._headers = value

    @property
    def response_mapping(self) -> dict:
        return self._response_mapping

    @response_mapping.setter
    def response_mapping(self, value: Union[dict, str]):
        try:
            self._response_mapping = self.get_as_dict(value)
        except json.JSONDecodeError:
            raise ParameterError(f"Invalid JSON format for '{RESPONSE_MAPPING}': {value}")
        except ParameterError:
            raise ParameterError(f"Invalid datatype '{type(value)}' for '{RESPONSE_MAPPING}'!")

    @property
    def error_response(self) -> dict:
        return self._error_response

    @error_response.setter
    def error_response(self, value: Union[dict, str]):
        try:
            self._error_response = self.get_as_dict(value)
        except json.JSONDecodeError:
            raise ParameterError(f"Invalid JSON format for '{ERROR_RESPONSE}': {value}")
        except ParameterError:
            raise ParameterError(f"Invalid datatype '{type(value)}' for '{ERROR_RESPONSE}'!")


class HTTPResolver(UserIdResolver):

    fields = {
        "endpoint": 1,
        "method": 1,
        "requestMapping": 1,
        "headers": 1,
        "responseMapping": 1,
        "hasSpecialErrorHandler": 0,
        "errorResponse": 0
    }

    def __init__(self):
        super(HTTPResolver, self).__init__()
        self.config = {}
        self.headers = {}
        self.config_get_user_by_id = {}
        self.config_user_auth = {}
        self.attribute_mapping_pi_to_user_store = {}
        self.attribute_mapping_user_store_to_pi = {}
        self._editable = False
        self.base_url = ""
        self.wildcard = "*"
        self.authorization_config = {}
        self.username = None
        self.password = None
        self._verify_tls = True
        self._tls_ca = None
        self.tls = self._verify_tls
        self.timeout = 60  # Default timeout for requests
        self._map = self.attribute_mapping_pi_to_user_store
        self.updateable = True

    @staticmethod
    def getResolverClassType() -> str:
        """
        provide the resolver type for registration
        """
        return 'httpresolver'

    @staticmethod
    def getResolverType() -> str:
        """
        getResolverType - return the type of the resolver

        :return: returns the string 'ldapresolver'
        :rtype:  string
        """
        return HTTPResolver.getResolverClassType()

    @classmethod
    def getResolverClassDescriptor(cls) -> dict:
        """
        return the descriptor of the resolver, which is
        - the class name and
        - the config description

        :return: resolver description dict
        """
        descriptor = {}
        typ = cls.getResolverClassType()
        descriptor['clazz'] = "useridresolver.HTTPResolver.HTTPResolver"
        descriptor['config'] = {
            'endpoint': 'string',
            'method': 'string',
            'headers': 'string',
            'requestMapping': 'string',
            'responseMapping': 'string',
            'hasSpecialErrorHandler': 'bool',
            'errorResponse': 'string',
            BASE_URL: 'string',
            ATTRIBUTE_MAPPING: 'dict',
            EDITABLE: 'bool',
            CONFIG_GET_USER_LIST: 'dict',
            CONFIG_GET_USER_BY_ID: 'dict',
            CONFIG_GET_USER_BY_NAME: 'dict',
            CONFIG_CREATE_USER: 'dict',
            CONFIG_EDIT_USER: 'dict',
            CONFIG_DELETE_USER: 'dict',
            CONFIG_AUTHORIZATION: 'dict',
            CONFIG_USER_AUTH: 'dict',
            ADVANCED: 'bool',
            USERNAME: 'string',
            PASSWORD: 'password',
            VERIFY_TLS: 'bool',
            TLS_CA_PATH: 'string',
            TIMEOUT: 'int'
        }
        return {typ: descriptor}

    def get_config(self) -> dict:
        """
        Returns the configuration of the resolver.
        """
        censored_config = copy.deepcopy(self.config)
        # Explicitly set values for which default configurations (in subclasses) exist
        censored_config[HEADERS] = self.headers
        censored_config[EDITABLE] = self.editable
        censored_config[VERIFY_TLS] = self._verify_tls
        censored_config["type"] = self.getResolverType()
        censored_config[TIMEOUT] = self.timeout
        if self.base_url:
            censored_config[BASE_URL] = self.base_url
        if self.attribute_mapping_pi_to_user_store:
            censored_config[ATTRIBUTE_MAPPING] = self.attribute_mapping_pi_to_user_store
        if self.authorization_config:
            censored_config[CONFIG_AUTHORIZATION] = self.authorization_config
        if PASSWORD in censored_config:
            # Remove password from config
            censored_config[PASSWORD] = "__CENSORED__"
        return censored_config

    @staticmethod
    def getResolverDescriptor() -> dict:
        """
        return the descriptor of the resolver, which is
        - the class name and
        - the config description

        :return: resolver description dict
        :rtype:  dict
        """
        return HTTPResolver.getResolverClassDescriptor()

    @property
    def editable(self) -> bool:
        """
        Return true, if the Instance! of this resolver is configured editable.
        :return:
        """
        return is_true(self._editable)

    @property
    def map(self) -> dict:
        """
        Return the attribute mapping from privacyidea to the user store.
        This is used to get the relevant attributes from the request parameters.

        :return: attribute mapping pi to user store
        """
        mapping = copy.deepcopy(self.attribute_mapping_pi_to_user_store)
        if "password" not in mapping:
            # Add the password field which is usually no attribute, but can be used in the request mapping
            mapping["password"] = "password"
        return mapping

    def getUserId(self, login_name: str) -> str:
        """
        Returns the user ID for the given username. If the user does not exist, an empty string is returned.
        If the endpoint to get the user by its username is not configured, only the username is echoed.

        :param login_name: The username to resolve
        :return: The user ID for the given username or an empty string if the user does not exist.
        """
        config_get_user_by_name = self.config.get(CONFIG_GET_USER_BY_NAME)
        if not config_get_user_by_name:
            # No endpoint configured to get user by name
            log.debug("No configuration to get user by name available.")
            return login_name

        config = RequestConfig(config_get_user_by_name, self.headers, {"username": login_name}, "")
        user_info = self._get_user(login_name, config)
        user_id = user_info.get("userid", "")
        return user_id

    def getUsername(self, userid: str) -> str:
        """
        Returns the username for the given user ID.
        """
        user_info = self.getUserInfo(userid)
        user_name = user_info.get("username", "")
        return user_name

    def getUserInfo(self, userid: str) -> dict:
        """
        This function returns all user information for a given user object
        identified by UserID.

        :param userid: ID of the user in the resolver
        :return:  dictionary, if no object is found, the dictionary is empty
        """
        config = RequestConfig(self.config_get_user_by_id, self.headers, {"userid": userid}, "")
        user_info = self._get_user(userid, config)
        return user_info

    def getUserList(self, search_dict: Optional[dict] = None) -> list[dict]:
        """
        Fetches all users from the user store according to the search dictionary.
        If the endpoint is not configured to list all users, an empty list is returned.
        """
        config_get_user_list = self.config.get(CONFIG_GET_USER_LIST)
        if not config_get_user_list:
            log.debug("No configuration to list users available.")
            return []

        config = RequestConfig(config_get_user_list, self.headers, search_dict, self.wildcard)
        user_list = self._get_user_list(search_dict, config)
        return user_list

    def add_user(self, attributes: Optional[dict] = None) -> str:
        """
        Add a new user in the useridresolver.
        This is only possible, if the UserIdResolver supports this and if
        we have write access to the user store.

        :param attributes: Attributes according to the attribute mapping
        :return: The new UID of the user.
        """
        uid = ""
        config_create_user = self.config.get(CONFIG_CREATE_USER)
        if not config_create_user:
            # No create user config available
            log.debug("No configuration to create users available.")
            return uid

        # Prepare request
        config = RequestConfig(config_create_user, self.headers, attributes, self.wildcard)
        config.headers.update(self._get_auth_header())
        request_params = config.request_mapping if config.request_mapping else {}
        request_params.update(self._pi_user_to_user_store_user(attributes))

        # Request
        response = self._do_request(config, request_params)

        # Handle Response
        success = self._create_user_error_handling(response, config)
        if success:
            if 'application/json' in response.headers.get('content-type', ""):
                # Try to get the user id from the response
                data = response.json()
                data = self._apply_response_mapping(config, data)
                uid = data.get(self.attribute_mapping_pi_to_user_store['userid'])
            if not uid:
                uid = self.getUserId(attributes.get('username', ''))
        return uid

    def delete_user(self, uid: str) -> bool:
        """
        Delete a user from the useridresolver.
        The user is referenced by the user id.

        :param uid: The uid of the user object, that should be deleted.
        :return: Returns True in case of success
        """
        success = False
        config_delete_user = self.config.get(CONFIG_DELETE_USER)
        if not config_delete_user:
            # No delete user config available
            log.debug("No delete user configuration available.")
            return success

        # Prepare Request
        config = RequestConfig(config_delete_user, self.headers, {"userid": uid}, "")
        config.headers.update(self._get_auth_header())
        params = config.request_mapping if config.request_mapping else {}

        # Request
        response = self._do_request(config, params)

        # Handle Response
        success = self._delete_user_error_handling(response, config, uid)

        return success

    def update_user(self, uid: str, attributes: Optional[dict] = None) -> bool:
        """
        Update an existing user.
        This function can also be used to update the password.
        Attributes that are not contained in the dict attributes are not
        modified.

        :param uid: The uid of the user object in the resolver.
        :param attributes: Attributes to be updated.
        :return: True in case of success
        """
        success = False
        config_edit_user = self.config.get(CONFIG_EDIT_USER)
        if not config_edit_user:
            # No edit user config available
            log.debug("No edit user configuration available.")
            return success

        # Prepare Request
        config = RequestConfig(config_edit_user, self.headers, {"userid": uid}, "")
        config.headers.update(self._get_auth_header())
        request_params = config.request_mapping if config.request_mapping else {}
        request_params.update(self._pi_user_to_user_store_user(attributes))

        # Request
        response = self._do_request(config, request_params)

        # Handle Request
        success = self._update_user_error_handling(response, config, uid)

        return success

    @log_with(log, hide_args=[2])
    def checkPass(self, uid: str, password: str, username: Optional[str] = None) -> bool:
        """
        This function checks the password for a given user. The user can either be identified by the uid or the
        username.

        :param uid: The uid in the resolver
        :param password: the password to check. Usually in cleartext
        :param username: The username of the user
        :return: True or False
        """
        if not self.config_user_auth:
            # No user auth config available
            log.debug("No user authentication configuration available.")
            return False

        # Prepare Request
        config = RequestConfig(self.config_user_auth, self.headers,
                               {"userid": uid, "username": username, "password": password}, self.wildcard)
        config.headers.update(self._get_auth_header())
        request_params = config.request_mapping if config.request_mapping else {}

        # Request
        response = self._do_request(config, request_params)

        # Handle Response
        success = self._user_auth_error_handling(response, config, uid)
        return success

    def getResolverId(self) -> str:
        """
        get resolver specific information
        :return: the resolver identifier string - empty string if not exist
        """
        return self.config['endpoint'] if 'endpoint' in self.config else ''

    def loadConfig(self, config: dict):
        """
        Load the configuration from the dict into the Resolver object.
        If attributes are missing, need to set default values.
        If required attributes are missing, this should raise an
        Exception.

        For the basic http resolver the config dict must contain the following entries:
        * endpoint: str
        * method: str (e.g. "get" or "post")
        * requestMapping: str (JSON) or dict
        * responseMapping: str (JSON) or dict
        * hasSpecialErrorHandler: bool or str (e.g. "true" or "false")
        * errorResponse: str (JSON) or dict

        For the advanced http resolver the config can contain the following entries:
        * base_url: str
        * headers: dict or str (JSON)
        * attribute_mapping: dict (or JSON str)
        * Editable: bool or str (e.g. "true" or "false")
        * config_authorization: dict
        * config_user_auth: dict
        * username: str
        * password: str
        * verify_tls: bool or str (e.g. "true" or "false")
        * tls_certificate_path: str
        * timeout: int (seconds) or str e.g. "10"
        * config_get_user_by_id: dict
            - method: str (e.g. "get" or "post")
            - endpoint: str
            - headers: str (JSON) or dict
            - requestMapping: str (JSON) or dict
            - responseMapping: str (JSON) or dict
            - hasSpecialErrorHandler: bool or str (e.g. "true" or "false")
            - errorResponse: str (JSON) or dict
        * config_get_user_by_name: dict
            - see config_get_user_by_id
        * config_get_user_list: dict
            - see config_get_user_by_id
        * config_create_user
            - see config_get_user_by_id
        * config_edit_user
            - see config_get_user_by_id
        * config_delete_user
            - see config_get_user_by_id

        :param config: The configuration values of the resolver
        :type config: dict
        """
        self.config = config
        self.base_url = copy.deepcopy(config.get(BASE_URL, self.base_url))
        self.headers = config.get(HEADERS, {})
        if isinstance(self.headers, str):
            if self.headers:
                try:
                    self.headers = json.loads(self.headers)
                except json.JSONDecodeError:
                    raise ParameterError(f"Invalid JSON format for headers: {self.headers}")
            else:
                self.headers = {}
        if not self.config.get(CONFIG_GET_USER_BY_ID):
            # Basic HTTP Resolver config only contains config for getUserInfo
            self.config_get_user_by_id[ENDPOINT] = get_required(config, ENDPOINT)
            self.config_get_user_by_id[METHOD] = get_required(config, METHOD)
            self.config_get_user_by_id[HEADERS] = config.get(HEADERS)
            self.config_get_user_by_id[REQUEST_MAPPING] = config.get(REQUEST_MAPPING)
            self.config_get_user_by_id[RESPONSE_MAPPING] = get_required(config, RESPONSE_MAPPING)
            self.config_get_user_by_id[HAS_ERROR_HANDLER] = config.get(HAS_ERROR_HANDLER, False)
            self.config_get_user_by_id[ERROR_RESPONSE] = config.get(ERROR_RESPONSE)
        else:
            self.config_get_user_by_id = config.get(CONFIG_GET_USER_BY_ID, self.config_get_user_by_id)

        self._editable = is_true(config.get(EDITABLE, False))
        attribute_mapping = config.get(ATTRIBUTE_MAPPING)
        if isinstance(attribute_mapping, str):
            try:
                attribute_mapping = json.loads(attribute_mapping)
            except json.JSONDecodeError:
                raise ParameterError(f"Invalid JSON format for '{ATTRIBUTE_MAPPING}': {attribute_mapping}")
        if attribute_mapping:
            self.attribute_mapping_pi_to_user_store = attribute_mapping
            self.attribute_mapping_user_store_to_pi = {store_key: pi_key for pi_key, store_key in
                                                       self.attribute_mapping_pi_to_user_store.items()}
        self.authorization_config = config.get(CONFIG_AUTHORIZATION, self.authorization_config)
        if self.authorization_config:
            self.username = config.get(USERNAME)
            self.password = config.get(PASSWORD)
        self.config_user_auth = config.get(CONFIG_USER_AUTH, self.config_user_auth)
        if isinstance(self.config_user_auth, str):
            try:
                self.config_user_auth = json.loads(self.config_user_auth)
            except json.JSONDecodeError:
                raise ParameterError(f"Invalid JSON format for '{CONFIG_USER_AUTH}': {self.config_user_auth}")

        # TLS
        self._verify_tls = is_true(config.get(VERIFY_TLS, True))
        self._tls_ca = config.get(TLS_CA_PATH)
        if self._verify_tls and self._tls_ca:
            self.tls = self._tls_ca
        else:
            self.tls = self._verify_tls
        try:
            self.timeout = int(config.get(TIMEOUT, self.timeout))
        except ValueError as e:
            log.debug(f"Invalid value for '{TIMEOUT}': {config.get(TIMEOUT)}. {e}")
            raise ParameterError(f"Invalid value for '{TIMEOUT}': {config.get(TIMEOUT)}.")
        return self

    @classmethod
    def testconnection(cls, param: dict) -> tuple[bool, str]:
        """
        This function lets you test if the parameters can be used to create a
        working resolver. Also, you can use it anytime you see if the API is
        running as expected.
        The implementation should try to make a request to the HTTP API and verify
        if user can be retrieved.
        In case of success it should return a list of all tested functions.

        The following functions are tested (if configured):
            * loading the configuration
            * authorization endpoint: Retrieve an access token to use the users API
            * Resolve a test user by the user ID ("test_username" must be provided in param)
            * Resolve a test user by the username ("test_username" must be provided in param)
            * List all users
            * Evaluate config to check a users password
            * Evaluate config to create a user
            * Evaluate config to edit a user
            * Evaluate config to delete a user

        :param param: The parameters that should be saved as the resolver
        :return: returns True in case of success and a raw response
        """
        success = False
        description = ""
        tested_configs = []
        try:
            resolver = cls()
            resolver.loadConfig(param)
            # backward compatibility: only sends username in testUser
            test_user = param.get("testUser")
            # But for a full test we need both, username und user id of a test user
            test_username = param.get("test_username", test_user)
            test_userid = param.get("test_userid")

            try:
                if resolver._get_auth_header():
                    tested_configs.append("Authorization")
            except Exception as e:
                description = f"Failed to get authorization header: {e}"
                return False, description

            if test_userid:
                # First try to get the user by id
                try:
                    user_name = resolver.getUsername(test_userid)
                    if user_name:
                        if user_name == test_username or not test_username:
                            success = True
                            tested_configs.append("Get user by ID")
                        else:
                            description = (
                                f"Defined username '{test_username}' does not match resolved username '{user_name}' "
                                f"for the user id '{test_userid}'.")
                    else:
                        description = f"No user found for user ID '{test_userid}'."
                except Exception as e:
                    description = f"Failed to get user by ID '{test_userid}': {e}"
                if not success:
                    return success, description

            if test_username:
                # Try to get the user by name
                success = False
                try:
                    user_id = resolver.getUserId(test_username)
                    if user_id:
                        if user_id == test_userid or not test_userid:
                            success = True
                            tested_configs.append("Get user by name")
                        else:
                            description = (
                                f"Defined user id '{test_userid}' does not match resolved user id '{user_id}' "
                                f"for the username '{test_username}'.")
                    else:
                        description = f"No user found for username '{test_username}'."
                except Exception as e:
                    description = f"Failed to get user by name: {e}"
                if not success:
                    return success, description

            # Try to get the user list
            success = False
            try:
                resolver.getUserList()
            except Exception as e:
                description = f"Failed to get user list: {e}"
                return success, description
            success = True

            tested_configs.append("User List")
            description = f"Resolver config seems to be OK. Tested configurations: {', '.join(tested_configs)}."

            # Load config to check the users password
            if param.get(CONFIG_USER_AUTH):
                try:
                    RequestConfig(param.get(CONFIG_USER_AUTH), resolver.headers, {"username": test_username,
                                                                                  "password": "test"}, "")
                except Exception as e:
                    description = f"Failed to load config to check user password: {e}"
                    return False, description

            # Load the config for the write functions, but not call them
            if param.get(EDITABLE):
                if param.get(CONFIG_CREATE_USER):
                    try:
                        RequestConfig(param.get(CONFIG_CREATE_USER), resolver.headers, {})
                    except Exception as e:
                        description = f"Failed to load create user config: {e}"
                        return False, description
                if param.get(CONFIG_EDIT_USER):
                    try:
                        RequestConfig(param.get(CONFIG_EDIT_USER), resolver.headers, {"userid": "0000-0000-0000-0000"})
                    except Exception as e:
                        description = f"Failed to load edit user config: {e}"
                        return False, description
                if param.get(CONFIG_DELETE_USER):
                    try:
                        RequestConfig(param.get(CONFIG_DELETE_USER), resolver.headers,
                                      {"userid": "0000-0000-0000-0000"})
                    except Exception as e:
                        description = f"Failed to load delete user config: {e}"
                        return False, description

        except Exception as e:
            success = False
            description = f"Failed: {e}"

        return success, description

    #
    #   Private methods
    #

    def _user_store_user_to_pi_user(self, user: dict) -> dict:
        """
        Maps the attributes from the user store to the attributes used in privacyidea.

        :param user: Dictionary containing user attributes from the user store
        :return: Dictionary containing user attributes mapped to privacyidea
        """
        pi_user = {}
        for key, value in user.items():
            if key in self.attribute_mapping_user_store_to_pi:
                pi_user[self.attribute_mapping_user_store_to_pi[key]] = value
        return pi_user

    def _pi_user_to_user_store_user(self, pi_user: dict) -> dict:
        """
        Maps the attributes used in privacyidea to the attributes from the user store.

        :param pi_user: Dictionary containing user attributes from privacyidea
        :return: Dictionary containing user attributes mapped to the user store
        """
        user = {}
        for key, value in pi_user.items():
            if key in self.attribute_mapping_pi_to_user_store:
                user[self.attribute_mapping_pi_to_user_store[key]] = value
        return user

    def _replace_resolver_specific_tags(self, config: RequestConfig):
        """
        Replaces resolver-specific tags in the configuration with their actual values.

        :param config: The configuration dictionary for the request
        :return: The configuration dictionary with tags replaced
        """
        return config

    def _get_auth_header(self) -> dict:
        """
        Returns the auth header for the request. Typically, this requests an access token for a service account.
        The resulting authorization header can be used to access the user endpoints of the API.
        If the authorization is not configure an empty dict is returned.
        """
        # TODO: Cache implementation

        auth_header = {}
        if not self.authorization_config:
            return auth_header

        config = RequestConfig(self.authorization_config, {"Content-Type": "application/x-www-form-urlencode"},
                               {"username": self.username, "password": self.password}, "")

        response = self._do_request(config, config.request_mapping)

        success = self._auth_header_error_handling(response, config)
        if success:
            json_result = response.json()
            auth_header = self._apply_response_mapping(config, json_result)
        else:
            raise ResolverError("Failed to get authorization header.")

        return auth_header

    @staticmethod
    def _apply_response_mapping(config: RequestConfig, result: dict) -> dict:
        """
        Applies the response mapping defined in the configuration to the result dictionary. Only keys defined in the
        response mapping are included in the returned dictionary. The tags are replaced with the corresponding values
        from the result dictionary.
        If not response mapping is defined the original result is returned.

        :param config: Configuration containing the response mapping
        :param result: The original result dictionary from the HTTP response
        :return: A dictionary containing the mapped response
        """
        mapped_response = result if not config.response_mapping else {}
        for key, value in config.response_mapping.items():
            reg_str = "\\{(.+?)\\}"
            all_tags = re.findall(reg_str, value)
            if len(all_tags) == 1 and value.startswith('{') and value.endswith('}'):
                # If the value only consists of the tag, we allow different datatypes
                value = get(result, all_tags[0])
            else:
                # Multiple tags or the value contains further text: tag values are handled as strings
                for tag in all_tags:
                    value = value.replace(f"{{{tag}}}", str(get(result, tag, "")))
            mapped_response[key] = value
        return mapped_response

    def _do_request(self, config: RequestConfig, params: Union[dict, str]) -> Response:
        """
        Performs the HTTP request based on the provided configuration and parameters.

        :param config: Configuration for the HTTP request
        :param params: Request parameters
        :return: The response object from the HTTP request
        """
        if config.endpoint.startswith("http"):
            config.endpoint = config.endpoint
        else:
            config.endpoint = self.base_url + config.endpoint
        config = self._replace_resolver_specific_tags(config)

        json_params = None
        if isinstance(params, dict) and config.method in HTTPMethod.methods_with_body():
            # params are dict than we can pass them as json parameters to be formatted correctly
            json_params = params
            params = None

        start_time = time.time()
        if config.method == HTTPMethod.GET:
            response = requests.get(config.endpoint, params=urlencode(params or {}), headers=config.headers,
                                    timeout=self.timeout,
                                    verify=self.tls)
        elif config.method == HTTPMethod.POST:
            response = requests.post(config.endpoint, json=json_params, data=params, headers=config.headers,
                                     timeout=self.timeout,
                                     verify=self.tls)
        elif config.method == HTTPMethod.PUT:
            response = requests.put(config.endpoint, json=json_params, data=params, headers=config.headers,
                                    timeout=self.timeout,
                                    verify=self.tls)
        elif config.method == HTTPMethod.PATCH:
            response = requests.patch(config.endpoint, json=json_params, data=params, headers=config.headers,
                                      timeout=self.timeout,
                                      verify=self.tls)
        elif config.method == HTTPMethod.DELETE:
            response = requests.delete(config.endpoint, params=urlencode(params or {}), headers=config.headers,
                                       timeout=self.timeout, verify=self.tls)
        else:  # pragma: no cover
            # Should not happen as the method is already checked in the config object
            raise ResolverError(f"Unsupported HTTP method: {config.method}")
        end_time = time.time()
        log.debug(f"Request took {end_time - start_time:.2f} seconds: {config.method.value.upper()} {config.endpoint}")

        return response

    def _get_user(self, user_identifier: str, config: RequestConfig) -> dict:
        """
        Fetches a single user from the user store

        :param user_identifier: Either the UID or the username
        :param config: Configuration to fetch the user
        :return: Dictionary containing pi conform user attributes
        """
        # Request
        config.headers.update(self._get_auth_header())
        params = config.request_mapping if config.request_mapping else {}
        response = self._do_request(config, params)

        # Error handling
        success = self._get_user_error_handling(response, config, user_identifier)

        # Map user store attributes to pi attributes
        user_info = {}
        if success:
            user_info = response.json()
            if config.response_mapping:
                # Apply custom response mapping
                user_info = self._apply_response_mapping(config, user_info)
            if self.attribute_mapping_user_store_to_pi:
                # Apply general attribute mapping
                user_info = self._user_store_user_to_pi_user(user_info)

        return user_info

    def _get_user_list_from_response(self, response: Union[dict, list]) -> list[dict]:
        """
        Extracts the user list from the response body.
        By default, we expect that there is no further nesting.

        :param response: The response body from the HTTP request
        :return: List of dictionaries containing user attributes
        """
        return response

    def _get_search_params(self, search_dict: dict) -> dict:
        """
        Returns a dictionary containing the search parameters in the format expected by the user store API.
        The values in the search_dict are mapped to the user store attributes using the attribute mapping and the
        default wildcard '*' is replaced with the configured wildcard.
        """
        request_parameters = {}
        if not search_dict:
            # If no search parameters are provided, return an empty dict
            return request_parameters

        for key, value in search_dict.items():
            user_store_key = self.attribute_mapping_pi_to_user_store.get(key)
            if user_store_key:
                value = value.replace("*", self.wildcard)
                if value:
                    request_parameters[user_store_key] = value
            else:
                log.debug(
                    f"Search parameter '{key}' not found in attribute mapping. Searching without this parameter.")
        return request_parameters

    def _get_user_list(self, search_dict: dict, config: RequestConfig) -> list[dict]:
        """
        Fetches a list of users from the user store.

        :param search_dict: Dictionary containing search parameters that are added as query to the endpoint url
        :param config: Configuration contains all information of the api endpoint to fetch the users.
        :return: List of dictionaries containing pi conform user attributes
        """
        request_params = config.request_mapping if config.request_mapping else {}
        request_params.update(self._get_search_params(search_dict))
        config.headers.update(self._get_auth_header())

        response = self._do_request(config, request_params)

        self._get_user_list_error_handling(response, config)

        # Map user store attributes to pi attributes
        json_result = response.json()
        json_result = self._apply_response_mapping(config, json_result)
        user_store_users = self._get_user_list_from_response(json_result)
        users = [self._user_store_user_to_pi_user(user) for user in user_store_users]

        return users

    # Error Handling

    @staticmethod
    def get_error(response: Response) -> Error:
        """
        Extracts a potential error from the response.

        :param response: Response object
        :return: Error dataclass containing the error info
        """
        return Error(False, "", "")

    @staticmethod
    def _custom_error_handling(response: Response, config: RequestConfig) -> bool:
        """
        Checks if all entries of the custom error response are contained in the response.
        """
        success = True
        if response.status_code == 204:
            return success

        # If the response is not empty, we can check for custom error handling
        if not config.has_error_handler:
            return success
        json_result = response.json()
        # verify if error response mapping is a subset of the json http response
        if isinstance(json_result, dict) and config.error_response is not None:
            if all([x in json_result.items() for x in config.error_response.items()]):
                log.error(json_result)
                success = False
        return success

    def default_error_handling(self, response: Response, config: RequestConfig) -> bool:
        """
        Checks if an HTTP error occurred and raise it or if the custom error handling fits the response.

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :return: True if the request was successful, False otherwise
        """
        try:
            # Raises HTTPError, if one occurred.
            response.raise_for_status()
        except HTTPError as error:
            log.info(f"HTTP error occurred: {error}")
            return False

        success = self._custom_error_handling(response, config)
        return success

    def _get_user_list_error_handling(self, response: Response, config: RequestConfig):
        """
        Handles the error response from the user store

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :return: True if the request was successful, False otherwise
        """
        success = self.default_error_handling(response, config)
        if not success:
            raise ResolverError("Failed to get the user list!")
        return success

    def _get_user_error_handling(self, response: Response, config: RequestConfig, user_identifier: str) -> bool:
        """
        Handles the error response from the user store.
        We do not raise an error here, as this would block many other functionalities, e.g. listing tokens with a token
        for a user that does not exist.

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :param user_identifier: Either the username or user id (used for logging)
        :return: True if the request was successful, False otherwise
        """
        success = self.default_error_handling(response, config)
        return success

    def _create_user_error_handling(self, response: Response, config: RequestConfig):
        """
        Handles the error response from the user store when creating a user

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        """
        success = self.default_error_handling(response, config)
        if not success:
            raise ResolverError("Failed to create a user in the user store.")
        return success

    def _update_user_error_handling(self, response: Response, config: RequestConfig, user_identifier: str) -> bool:
        """
        Handles the error response from the user store when updating a user.
        Does not raise an exception, as this is handled from the API function.

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        """
        success = self.default_error_handling(response, config)
        return success

    def _delete_user_error_handling(self, response: Response, config: RequestConfig, user_identifier: str) -> bool:
        """
        Handles the error response from the user store when deleting a user.
        Does not raise an exception, as this is handled from the API function.

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        """
        success = self.default_error_handling(response, config)
        return success

    def _auth_header_error_handling(self, response: Response, config: RequestConfig) -> bool:
        """
        Handles the error response from the user store when trying to get the authorization header.

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :return: True if the password check was successful, False otherwise
        """
        success = self.default_error_handling(response, config)
        return success

    def _user_auth_error_handling(self, response: Response, config: RequestConfig, user_identifier: str) -> bool:
        """
        Handles the error response from the user store when checking a user's password

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :param user_identifier: The user identifier (username or user id)
        :return: True if the password check was successful, False otherwise
        """
        success = self.default_error_handling(response, config)
        return success
