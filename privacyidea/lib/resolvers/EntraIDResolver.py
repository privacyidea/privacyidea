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
# SPDX-FileCopyrightText: 2025 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

import copy
import json
import logging
import msal
from enum import Enum
from typing import Union, Optional

from requests import Response

from privacyidea.api.lib.utils import get_required, get_optional
from privacyidea.lib.error import ResolverError, ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.resolvers.HTTPResolver import (HTTPResolver, METHOD, ENDPOINT,
                                                    CONFIG_GET_USER_BY_NAME, CONFIG_GET_USER_LIST,
                                                    CONFIG_GET_USER_BY_ID, RequestConfig, ADVANCED,
                                                    CONFIG_CREATE_USER, CONFIG_EDIT_USER,
                                                    CONFIG_DELETE_USER, REQUEST_MAPPING, HEADERS, CONFIG_USER_AUTH,
                                                    Error)
from privacyidea.lib.resolvers.util import delete_user_error_handling_no_content

CLIENT_ID = "client_id"
CLIENT_CREDENTIAL_TYPE = "client_credential_type"
CLIENT_SECRET = "client_secret"
CLIENT_CERTIFICATE = "client_certificate"
PRIVATE_KEY_FILE = "private_key_file"
PRIVATE_KEY_PASSWORD = "private_key_password"
CERTIFICATE_FINGERPRINT = "certificate_fingerprint"
TENANT = "tenant"
AUTHORITY = "authority"

log = logging.getLogger(__name__)


class ClientCredentialType(Enum):
    SECRET = "secret"
    CERTIFICATE = "certificate"


class EntraIDResolver(HTTPResolver):

    @log_with(log)
    def __init__(self):
        super(EntraIDResolver, self).__init__()
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.attribute_mapping_pi_to_user_store = {"username": "userPrincipalName",
                                                   "userid": "id",
                                                   "givenname": "givenName",
                                                   "surname": "surname",
                                                   "email": "mail",
                                                   "mobile": "mobilePhone",
                                                   "phone": "businessPhones"}
        self.attribute_mapping_user_store_to_pi = {entra_key: pi_key for pi_key, entra_key in
                                                   self.attribute_mapping_pi_to_user_store.items()}
        self.config_get_user_by_id = {METHOD: "GET", ENDPOINT: "/users/{userid}"}
        self.config.update({CONFIG_GET_USER_BY_ID: self.config_get_user_by_id,
                            CONFIG_GET_USER_BY_NAME: {METHOD: "GET", ENDPOINT: "/users/{username}"},
                            CONFIG_GET_USER_LIST: {METHOD: "GET", ENDPOINT: "/users",
                                                   HEADERS: '{"ConsistencyLevel": "eventual"}'},
                            CONFIG_CREATE_USER: {METHOD: "POST", ENDPOINT: "/users",
                                                 REQUEST_MAPPING: '{"accountEnabled": true, '
                                                                  '"displayName": "{givenname} {surname}", '
                                                                  '"mailNickname": "{givenname}", '
                                                                  '"passwordProfile": {"password": "{password}"}}'},
                            CONFIG_EDIT_USER: {METHOD: "PATCH", ENDPOINT: "/users/{userid}"},
                            CONFIG_DELETE_USER: {METHOD: "DELETE", ENDPOINT: "/users/{userid}"},
                            CONFIG_USER_AUTH: {METHOD: "POST",
                                               HEADERS: '{"Content-Type": "application/x-www-form-urlencoded"}',
                                               ENDPOINT: "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                                               REQUEST_MAPPING: "client_id={client_id}&scope=https://graph.microsoft.com"
                                                                "/.default&username={username}&password={password}&"
                                                                "grant_type=password&client_secret={client_credential}"}})
        self.wildcard = ""  # No wildcards supported

        # Custom attributes
        self.ms_graph_app = None
        self.authority = "https://login.microsoftonline.com/{tenant}"
        self.client_id = None
        self.client_credential = None
        self.client_credential_type = ClientCredentialType.SECRET
        self.tenant = None

    def loadConfig(self, config: dict):
        """
        loadConfig - load the configuration from the database.

        :param config: the config dictionary
        """
        self.config.update(config)
        super().loadConfig(self.config)
        self.client_id = get_required(self.config, CLIENT_ID)
        self.tenant = get_required(self.config, TENANT)
        authority = get_optional(self.config, AUTHORITY, default=self.authority)
        self.authority = authority.replace("{tenant}", self.tenant)

        # Client credential
        credential_type = get_required(self.config, CLIENT_CREDENTIAL_TYPE)
        self.client_credential_type = ClientCredentialType(credential_type)
        if self.client_credential_type == ClientCredentialType.CERTIFICATE:
            # check if all required parameters are set
            client_certificate = get_required(self.config, CLIENT_CERTIFICATE)
            path_to_private_key = get_required(client_certificate, PRIVATE_KEY_FILE)
            private_key_password = get_optional(client_certificate, PRIVATE_KEY_PASSWORD, default=None)
            fingerprint = get_required(client_certificate, CERTIFICATE_FINGERPRINT)
            try:
                with open(path_to_private_key) as file:
                    private_key = file.read()
            except Exception as e:
                raise ParameterError(f"Could not read client certificate file '{path_to_private_key}': {e}")
            self.client_credential = {"private_key": private_key, "thumbprint": fingerprint}
            if private_key_password:
                self.client_credential["passphrase"] = private_key_password
        else:
            self.client_credential = get_required(self.config, CLIENT_SECRET)

        try:
            self.ms_graph_app = msal.ConfidentialClientApplication(self.client_id, authority=self.authority,
                                                                   client_credential=self.client_credential)
        except ValueError as error:
            raise ParameterError(f"Invalid Authorization Configuration: {error}")

        user_auth_config = get_optional(self.config, CONFIG_USER_AUTH)
        if user_auth_config:
            self.config_user_auth = copy.deepcopy(user_auth_config)
            tags = {"{tenant}": self.tenant, "{client_id}": self.client_id}
            if self.client_credential_type == ClientCredentialType.SECRET:
                tags["{client_credential}"] = self.client_credential
            for tag, value in tags.items():
                if self.config_user_auth.get(ENDPOINT):
                    self.config_user_auth[ENDPOINT] = self.config_user_auth[ENDPOINT].replace(tag, value)
                if self.config_user_auth.get(REQUEST_MAPPING):
                    self.config_user_auth[REQUEST_MAPPING] = self.config_user_auth[REQUEST_MAPPING].replace(tag, value)

    def get_config(self) -> dict:
        """
        Returns the configuration of the resolver.
        """
        censored_config = super().get_config()
        censored_config[ADVANCED] = True
        censored_config[AUTHORITY] = self.authority
        censored_config[CLIENT_CREDENTIAL_TYPE] = self.client_credential_type.value
        # Censor sensitive information
        if CLIENT_SECRET in censored_config:
            censored_config[CLIENT_SECRET] = "__CENSORED__"
        if CLIENT_CERTIFICATE in censored_config and PRIVATE_KEY_PASSWORD in censored_config[CLIENT_CERTIFICATE]:
            censored_config[CLIENT_CERTIFICATE][PRIVATE_KEY_PASSWORD] = "__CENSORED__"
        return censored_config

    @staticmethod
    def getResolverClassType():
        """
        Provide the resolver type for registration.
        """
        return 'entraidresolver'

    @staticmethod
    def getResolverType():
        """
        Returns the type of the resolver
        """
        return EntraIDResolver.getResolverClassType()

    @classmethod
    def getResolverClassDescriptor(cls) -> dict:
        """
        Returns the class descriptor which is a dictionary with the resolver type as key and a dictionary containing
        the data type for each configuration parameter as value.
        """
        descriptor = super().getResolverClassDescriptor()
        resolver_type = cls.getResolverType()
        descriptor[resolver_type]["clazz"] = "useridresolver.EntraIDResolver.EntraIDResolver"
        descriptor[resolver_type]["config"].update({CLIENT_ID: "string",
                                                    CLIENT_CREDENTIAL_TYPE: "string",
                                                    CLIENT_SECRET: "password",
                                                    CLIENT_CERTIFICATE: "dict_with_password",
                                                    f"{CLIENT_CERTIFICATE}.{PRIVATE_KEY_PASSWORD}": "password",
                                                    TENANT: "string",
                                                    AUTHORITY: "string"})
        return descriptor

    @staticmethod
    def getResolverDescriptor() -> dict:
        """
        Returns the descriptor of the resolver, which is the class name and the config description.
        """
        return EntraIDResolver.getResolverClassDescriptor()

    @log_with(log, hide_args=[2])
    def checkPass(self, uid: str, password: str, username: Optional[str] = None) -> bool:
        """
        This function checks the password for a given user. The user can either be identified by the uid or the
        username. EntraID provides the OAuth 2.0 ROPC flow to check the password. This flow only supports using
        client secrets and does not support client certificates. If the resolver is configured to use a client
        certificate, this function will raise a ResolverError.

        :param uid: The uid in the resolver
        :param password: the password to check. Usually in cleartext
        :param username: The username of the user
        :return: True or False
        """
        if self.config_user_auth and self.client_credential_type == ClientCredentialType.CERTIFICATE:
            raise ResolverError("User authentication with password is not supported when using a certificate for the "
                                "client!")
        else:
            return super().checkPass(uid, password, username)

    def _get_auth_header(self) -> dict:
        """
        Creates the authorization header containing the access token for the Microsoft Graph API requests. First it
        tries to get the access token from the cache, and if it is not available or expired, it will request a new one.
        Raises a ResolverError if the access token cannot be obtained.
        """
        result = self.ms_graph_app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" in result:
            access_token = result["access_token"]
        else:
            log.warning(
                f"Failed to get access token with error {result.get('error')} {result.get('error_description')}")
            raise ResolverError(f"Failed to get access token to resolve users from EntraID: {result.get('error')}")

        header = {"Authorization": f"Bearer {access_token}"}
        return header

    def _get_search_params(self, search_dict: dict) -> dict:
        """
        Returns a dictionary containing the search parameters in the format expected by the user store API.
        All search parameters are mapped to the EntraID attributes according to the attribute mapping and concatenated
        to a single query string. If the search value does not contain any wildcard, the syntax is
        ``<entra_key> eq '<value>'``. If wildcards are contained in the value, we use the syntax
        ``startswith(<entra_key>, '<value>')`` where all '*' characters are removed from the value as entraID does not
        support advanced wildcard searches. If advanced query capabilities are activated, it also searches for values
        that ends with the substring. Syntax: ``(startswith(<entra_key>, '<value>') or endswith(<entra_key>, '<value>'))``
        Multiple search attributes are concatenated with `` and ``.
        The complete search query is stored und the key ``$filer`` in the request parameters dictionary.
        """
        request_parameters = {}
        if not search_dict:
            return request_parameters

        filter_values = []
        for key, value in search_dict.items():
            entra_key = self.attribute_mapping_pi_to_user_store.get(key)
            if not entra_key:
                log.debug(f"Search parameter '{key}' not found in attribute mapping. Search without this parameter.")
                continue

            if value == "*":
                # If the value is "*", we do not filter by this attribute
                continue
            elif "*" in value:
                # Advanced query capabilities (endswith) can only be used if the Consistency Header is set
                # If it is not configured we use basic queries (only startswith)
                user_list_config = self.config.get(CONFIG_GET_USER_LIST, {})
                headers = user_list_config.get(HEADERS, "{}")
                try:
                    headers = json.loads(headers)
                    advanced_query = headers.get("ConsistencyLevel", "") == "eventual"
                except json.JSONDecodeError:
                    advanced_query = False

                # EntraID does not support advanced wildcard searches. We can only filter for attributes
                # that start (or end) with the given value.
                value = value.replace("*", self.wildcard)
                if advanced_query:
                    filter_values.append(
                        f"(startswith({entra_key}, '{value}') or endswith({entra_key}, '{value}'))")
                else:
                    filter_values.append(f"startswith({entra_key}, '{value}')")
            else:
                filter_values.append(f"{entra_key} eq '{value.replace('*', self.wildcard)}'")

        if filter_values:
            request_parameters["$filter"] = " and ".join(filter_values)

        return request_parameters

    def _pi_user_to_user_store_user(self, pi_user: dict) -> dict:
        """
        Maps the attributes used in privacyidea to the attributes from the user store.

        :param pi_user: Dictionary containing user attributes from privacyidea
        :return: Dictionary containing user attributes mapped to the user store
        """
        user = super()._pi_user_to_user_store_user(pi_user)
        if "businessPhones" in user:
            # EntraID uses "businessPhones" as a list of phone numbers
            user["businessPhones"] = [user["businessPhones"]]
        return user

    def _get_user_list_from_response(self, response: Union[dict, list]) -> list[dict]:
        """
        Extracts the user attributes dictionary from the response body.

        :param response: The response body from the HTTP request
        :return: List of dictionaries containing user attributes
        """
        users = response.get("value", [])
        return users

    # Error Handling
    @staticmethod
    def get_error(response: Response) -> Error:
        """
        Extracts a potential error from the response.
        EntraID usually returns errors in the format:
        ``{"error": "code": "ErrorCode", "message": "Error message"}``

        :param response: Response object
        :return: Error dataclass containing the error info
        """
        error_data = response.json().get("error")
        if error_data:
            error = Error(True, error_data.get("code", ""), error_data.get("message", ""))
        else:
            error = Error(False, "", "")
        return error

    def _get_user_list_error_handling(self, response: Response, config: RequestConfig):
        """
        Handles the error response from the user store

        :param response: The response object from the HTTP request
        """
        if response.status_code != 200:
            error = self.get_error(response)
            if error.error:
                success = False
                log.info(f"Failed to get the user list: {error.code} - {error.message}")
            else:
                # There is no error message in the expected format. Execute generic error handling.
                success = super()._get_user_list_error_handling(response, config)
        else:
            # Custom errors can also occur in successful responses
            success = self._custom_error_handling(response, config)

        if not success:
            raise ResolverError(f"Failed to get the user list!")

    def _get_user_error_handling(self, response: Response, config: RequestConfig, user_identifier: str) -> bool:
        """
        Handles the error response from the user store

        :param response: The response object from the HTTP request
        :return: True on success, False otherwise
        """
        if response.status_code == 202:
            success = False
            log.info("Failed to resolve user: Entra ID server is busy.")
        elif response.status_code != 200:
            # extract error code and messages
            error = self.get_error(response)
            if error.error:
                success = False
                log.info(f"Failed to resolve user: {error.code} - {error.message}")
                if response.status_code == 404:
                    log.info(f"User '{user_identifier}' does not exist!")
            else:
                success = super()._get_user_error_handling(response, config, user_identifier)
        else:
            # Custom errors can also occur in successful responses
            success = self._custom_error_handling(response, config)

        return success

    def _create_user_error_handling(self, response: Response, config: RequestConfig) -> bool:
        """
        Handles the error response from the user store when creating a user

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        """
        if not response.status_code == 201:
            # extract error code and messages
            error = self.get_error(response)
            if error.error:
                log.info(f"Failed to create user: {error.code} - {error.message}")
                raise ResolverError(f"Failed to create user: {error.code} - {error.message}")
            else:
                # There is no error message in the expected format. Execute generic error handling.
                success = super()._create_user_error_handling(response, config)
        else:
            success = self._custom_error_handling(response, config)

        if not success:
            raise ResolverError("Failed to create user!")

        return success

    def _update_user_error_handling(self, response: Response, config: RequestConfig, user_identifier: str) -> bool:
        """
        Handles the error response from the user store when updating a user.
        Does not raise an exception, as this is handled from the API function.

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        """
        if response.status_code == 204:
            return True

        # extract error code and messages
        error = self.get_error(response)
        if error.error:
            success = False
            log.info(f"Failed to update user {user_identifier}: {error.code} - {error.message}")
        else:
            # There is no error message in the expected format. Execute generic error handling.
            success = super()._update_user_error_handling(response, config, user_identifier)
        return success

    def _delete_user_error_handling(self, response: Response, config: RequestConfig, user_identifier: str) -> bool:
        """
        Handles the error response from the user store when deleting a user.
        Does not raise an exception, as this is handled from the API function.

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :param user_identifier: The identifier of the user to be deleted
        :return: True if the user was deleted successfully, False otherwise
        """
        return delete_user_error_handling_no_content(self, response, config, user_identifier)

    def _user_auth_error_handling(self, response: Response, config: RequestConfig, user_identifier: str) -> bool:
        """
        Handles the error response from the user store when checking a user's password.

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :param user_identifier: The user identifier (username or user id)
        :return: True if the password check was successful, False otherwise
        """
        if not response.status_code == 200:
            # extract error code and messages
            response_data = response.json()
            error = response_data.get("error", {})
            error_message = response_data.get("error_description", "")
            if error:
                success = False
                log.debug(f"Failed to authenticate user {user_identifier}: {error} - {error_message}")
            else:
                success = super()._delete_user_error_handling(response, config, user_identifier)
        else:
            # Custom errors can also occur in successful responses
            success = self._custom_error_handling(response, config)
        return success
