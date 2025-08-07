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
# SPDX-FileCopyrightText: 2025 Agustin Prediger
# SPDX-FileCopyrightText: 2025 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import logging
from typing import Union

from requests import Response

from privacyidea.lib.error import ResolverError
from privacyidea.lib.resolvers.HTTPResolver import (HTTPResolver, METHOD, ENDPOINT, CONFIG_GET_USER_BY_ID,
                                                    CONFIG_GET_USER_BY_NAME, CONFIG_GET_USER_LIST, REQUEST_MAPPING,
                                                    RequestConfig, HEADERS, ADVANCED, RESPONSE_MAPPING,
                                                    CONFIG_CREATE_USER, CONFIG_DELETE_USER, CONFIG_EDIT_USER,
                                                    CONFIG_USER_AUTH, Error)
from privacyidea.lib.resolvers.util import delete_user_error_handling_no_content

log = logging.getLogger(__name__)

REALM = "realm"


class KeycloakResolver(HTTPResolver):

    def __init__(self):
        super(KeycloakResolver, self).__init__()

        self.config_get_user_by_id = {METHOD: "GET", ENDPOINT: "/admin/realms/{realm}/users/{userid}"}
        self.config.update({CONFIG_GET_USER_BY_ID: self.config_get_user_by_id,
                            CONFIG_GET_USER_BY_NAME: {METHOD: "GET", ENDPOINT: "/admin/realms/{realm}/users",
                                                      REQUEST_MAPPING: '{"username": "{username}", "exact": true}'},
                            CONFIG_GET_USER_LIST: {METHOD: "GET", ENDPOINT: "/admin/realms/{realm}/users"},
                            CONFIG_CREATE_USER: {METHOD: "POST", ENDPOINT: "/admin/realms/{realm}/users", REQUEST_MAPPING: '{"enabled": true}'},
                            CONFIG_EDIT_USER: {METHOD: "PUT", ENDPOINT: "/admin/realms/{realm}/users/{userid}"},
                            CONFIG_DELETE_USER: {METHOD: "DELETE", ENDPOINT: "/admin/realms/{realm}/users/{userid}"},
                            CONFIG_USER_AUTH: {METHOD: "POST",
                                               HEADERS: '{"Content-Type": "application/x-www-form-urlencoded"}',
                                               ENDPOINT: "/realms/{realm}/protocol/openid-connect/token",
                                               REQUEST_MAPPING: "grant_type=password&client_id=admin-cli&"
                                                                "username={username}&password={password}"}
                            })
        self.attribute_mapping_pi_to_user_store = {"username": "username",
                                                   "userid": "id",
                                                   "givenname": "firstName",
                                                   "surname": "lastName",
                                                   "email": "email", }
        self.attribute_mapping_user_store_to_pi = {rh_sso_key: pi_key for pi_key, rh_sso_key in
                                                   self.attribute_mapping_pi_to_user_store.items()}
        self.base_url = "http://localhost:8080"
        self.authorization_config = {METHOD: "POST",
                                     ENDPOINT: "/realms/{realm}/protocol/openid-connect/token",
                                     REQUEST_MAPPING: "grant_type=password&client_id=admin-cli&username={username}&password={password}",
                                     RESPONSE_MAPPING: '{"Authorization": "Bearer {access_token}"}',
                                     HEADERS: '{"Content-Type": "application/x-www-form-urlencoded"}'}
        # No wildcard required
        self.wildcard = ""

        # custom attributes
        self.realm = None

    def loadConfig(self, config: dict):
        """
        Load the configuration for the resolver.
        """
        self.config.update(config)
        super().loadConfig(self.config)
        self.realm = self.config.get(REALM)

    def get_config(self) -> dict:
        """
        Returns the configuration of the resolver.
        """
        censored_config = super().get_config()
        censored_config[ADVANCED] = True
        return censored_config

    @staticmethod
    def getResolverClassType() -> str:
        """
        provide the resolver type for registration
        """
        return "keycloakresolver"

    @staticmethod
    def getResolverType() -> str:
        """
        Returns the type of the resolver
        """
        return KeycloakResolver.getResolverClassType()

    @classmethod
    def getResolverClassDescriptor(cls) -> dict:
        """
        Returns the class descriptor which is a dictionary with the resolver type as key and a dictionary containing
        the data type for each configuration parameter as value.
        """
        resolver_type = cls.getResolverType()
        descriptor = super().getResolverClassDescriptor()[resolver_type]
        descriptor['clazz'] = "useridresolver.KeycloakResolver.KeycloakResolver"
        descriptor['config'].update({REALM: "string"})
        return {resolver_type: descriptor}

    @staticmethod
    def getResolverDescriptor() -> dict:
        """
        Returns the descriptor of the resolver, which is the class name and the config description.
        """
        return KeycloakResolver.getResolverClassDescriptor()

    def getUserId(self, login_name: str) -> str:
        """
        Searches for a user by its name. Keycloak does not have an explicit endpoint for this purpose. Hence, we use
        the endpoint to get all users but filter for the username.
        """
        config_get_user_by_name = self.config.get(CONFIG_GET_USER_BY_NAME)
        config = RequestConfig(config_get_user_by_name, self.headers, {"username": login_name}, "")
        try:
            users = self._get_user_list({}, config)
        except ResolverError as error:
            log.info(f"Failed to resolve user '{login_name}': {error}")
            return ""

        if len(users) == 1:
            user_id = users[0].get("userid")
        elif len(users) > 1:
            raise ResolverError(f"Multiple users found for username '{login_name}'")
        else:
            user_id = ""
            log.info(f"No user found for username '{login_name}'")
        return user_id

    def _replace_resolver_specific_tags(self, config: RequestConfig):
        """
        Replaces resolver-specific tags in the configuration with their actual values.

        :param config: The configuration dictionary for the request
        :return: The configuration dictionary with tags replaced
        """
        if self.realm:
            config.endpoint = config.endpoint.replace("{realm}", self.realm)
        return config

    # Error Handling

    @staticmethod
    def get_error(response: Response) -> Union[Error, None]:
        """
        Extracts the error message from the response if available.
        It tries to get the error message under the key "errorMessage" or "error".

        :param response: The response object from the HTTP request
        :return: The error message if available, otherwise None
        """
        error = Error(False, "", "")
        try:
            data = response.json()
            error_message = data.get("errorMessage")
            if not error_message:
                error_code = data.get("error", "")
                error_message = data.get("error_description", "")
                if error_code or error_message:
                    error = Error(True, error_code, error_message)
            else:
                error = Error(True, "", error_message)
        except ValueError:
            error = None
        return error

    def _get_user_list_error_handling(self, response: Response, config: RequestConfig):
        """
        Handles the error response from the user store

        :param response: The response object from the HTTP request
        :param config: The configuration for the user list request
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
        :param config: Configuration for the endpoint containing information about special error handling
        :param user_identifier: Either the username or user id (used for logging)
        :return: True if the request was successful, False otherwise
        """
        if not response.status_code == 200:
            # extract error messages
            error = self.get_error(response)
            if error.error:
                success = False
                log.info(f"Failed to resolve user: {error.code} - {error.message}")
                if response.status_code == 404:
                    log.info(f"User '{user_identifier}' does not exist!")
            else:
                # There is no error message in the expected format. Execute generic error handling.
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
        :return: True on success, False otherwise
        """
        if not response.status_code == 201:
            # extract error messages
            error = self.get_error(response)
            if error.error:
                log.info(f"Failed to create user: {error.code} - {error.message}")
                raise ResolverError(f"Failed to create user: {error.message}")
            else:
                # There is no error message in the expected format. Execute generic error handling.
                success = super()._create_user_error_handling(response, config)
        else:
            # Custom errors can also occur in successful responses
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
        :return: True on success, False otherwise
        """
        if response.status_code == 204:
            return True

        # extract error messages
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
        Handles the error response from the user store when deleting a user

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :param user_identifier: The identifier of the user to be deleted#
        :return: True on success, False otherwise
        """
        return delete_user_error_handling_no_content(self, response, config, user_identifier)

    def _auth_header_error_handling(self, response: Response, config: RequestConfig) -> bool:
        """
        Handles the error response from the user store when trying to get the authorization header.

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :return: True if the password check was successful, False otherwise
        """
        if not response.status_code == 200:
            # extract error code and messages
            error = self.get_error(response)
            if error.error:
                success = False
                log.debug(f"Failed to get authorization header: {error.code} - {error.message}")
            else:
                success = super()._auth_header_error_handling(response, config)
        else:
            # Custom errors can also occur in successful responses
            success = self._custom_error_handling(response, config)
        return success

    def _user_auth_error_handling(self, response: Response, config: RequestConfig, user_identifier: str) -> bool:
        """
        Handles the error response from the user store when checking a user's password

        :param response: The response object from the HTTP request
        :param config: Configuration for the endpoint containing information about special error handling
        :param user_identifier: The user identifier (username or user id)
        :return: True if the password check was successful, False otherwise
        """
        if not response.status_code == 200:
            # extract error code and messages
            error = self.get_error(response)
            if error.error:
                success = False
                log.debug(f"Failed to authenticate user {user_identifier}: {error.code} - {error.message}")
            else:
                success = super()._user_auth_error_handling(response, config, user_identifier)
        else:
            # Custom errors can also occur in successful responses
            success = self._custom_error_handling(response, config)
        return success
