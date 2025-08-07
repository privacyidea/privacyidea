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
# SPDX-FileCopyrightText: 2025 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import logging
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import Union, Optional

from werkzeug.datastructures import EnvironHeaders

from privacyidea.lib import _
from privacyidea.lib.error import ParameterError, PolicyError, ResourceNotFoundError
from privacyidea.lib.log import log_with
from privacyidea.lib.user import User
from privacyidea.lib.utils.compare import PrimaryComparators, compare_values

log = logging.getLogger(__name__)

# TODO: Change this to an Enum or StrEnum (Python 3.11+) and remove subclass Section
class ConditionSection:
    __doc__ = """This is a list of available sections for conditions of policies """
    class Section(Enum):
        USERINFO = "userinfo"
        TOKENINFO = "tokeninfo"
        TOKEN = "token"  # nosec B105 # section name
        HTTP_REQUEST_HEADER = "HTTP Request header"
        HTTP_ENVIRONMENT = "HTTP Environment"
        CONTAINER = "container"
        CONTAINER_INFO = "container_info"
        REQUEST_DATA = "Request Data"

    USERINFO = Section.USERINFO.value
    TOKENINFO = Section.TOKENINFO.value
    TOKEN = Section.TOKEN.value
    HTTP_REQUEST_HEADER = Section.HTTP_REQUEST_HEADER.value
    HTTP_ENVIRONMENT = Section.HTTP_ENVIRONMENT.value
    CONTAINER = Section.CONTAINER.value
    CONTAINER_INFO = Section.CONTAINER_INFO.value
    REQUEST_DATA = Section.REQUEST_DATA.value

    @classmethod
    def get_all_sections(cls) -> list[str]:
        """
        Return all available sections for conditions of policies as a list.
        """
        return [section.value for section in cls.Section]


class ConditionCheck:
    __doc__ = """The available check methods for extended conditions"""
    # TODO: Use the same datatype for all checks
    DO_NOT_CHECK_AT_ALL = 1
    ONLY_CHECK_USERINFO = [ConditionSection.USERINFO]
    CHECK_AND_HANDLE_MISSING_DATA = None


class ConditionHandleMissingData(Enum):
    __doc__ = """The possible behaviours if the data that is required to check a condition is missing."""
    RAISE_ERROR = "raise_error"
    IS_TRUE = "condition_is_true"
    IS_FALSE = "condition_is_false"

    @classmethod
    def default(cls) -> 'ConditionHandleMissingData':
        """
        Return the default value for the condition handling of missing data.
        """
        return cls.RAISE_ERROR

    @classmethod
    def get_selection_dict(cls) -> dict:
        """
        Returns a dictionary mapping the values of the enum to dictionaries with the following keys:
        * ``"display_value"``, a human-readable name of the behaviour to be displayed in the webUI
        * ``"description"``, a short description of the behaviour
        This can be used for a selection in the webUI.
        """
        selection_dict = {
            cls.RAISE_ERROR.value: {
                "display_value": "Raise an error",
                "description": _("Raise an error if the data that is required to check the condition is not available.")
            },
            cls.IS_TRUE.value: {
                "display_value": "Condition is true",
                "description": _(
                    "If the required data is not available, the condition is considered to be true. Hence, "
                    "the policy is applied.")
            },
            cls.IS_FALSE.value: {
                "display_value": "Condition is false",
                "description": _(
                    "If the required data is not available, the condition is considered to be false. Hence, "
                    "the policy is not applied.")
            }
        }
        return selection_dict

    @classmethod
    def get_valid_values(cls) -> list[str]:
        """
        Returns a list of all valid values for the enum.
        """
        return [name.value for name in cls.__members__.values()]

    @classmethod
    def get_from_value(cls, value: str) -> 'ConditionHandleMissingData':
        """
        Get the enum from the given string.
        """
        valid_handle_missing_data = cls.get_valid_values()
        if value not in valid_handle_missing_data:
            log.error(f"Unknown handle missing data '{value}'. Valid values are: {valid_handle_missing_data}")
            raise ParameterError(f"Unknown handle missing data value '{value}'!")
        return cls(value)


@dataclass
class ConditionSectionData:
    object_name: str
    object_available: bool = False
    value: any = None
    available_keys: list[str] = None


class PolicyConditionClass:

    @log_with(log)
    def __init__(self, section: str, key: str, comparator: str, value: str, active: bool,
                 handle_missing_data: str = None, pass_if_inactive: bool = False):
        self._pass_if_inactive = pass_if_inactive
        # Active setter methods requires that _active already exists
        self._active = None
        self.active = active
        self.section = section
        self.key = key
        self.comparator = comparator
        self.value = value
        self.handle_missing_data = handle_missing_data

    @property
    def _allow_invalid_parameters(self) -> bool:
        return self._pass_if_inactive and self.active is False

    @property
    def section(self) -> str:
        return self._section

    @section.setter
    def section(self, section: str):
        if section in ConditionSection.get_all_sections() or self._allow_invalid_parameters:
            self._section = section
        else:
            log.error(f"Unknown section '{section}' set in condition. Valid sections are: "
                      f"{ConditionSection.get_all_sections()}")
            raise ParameterError(f"Unknown section '{section}' set in condition.")

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, key: str):
        if (isinstance(key, str) and len(key) > 0) or self._allow_invalid_parameters:
            self._key = key
        else:
            raise ParameterError(f"Key must be a non-empty string. Got '{key}' of type '{type(key)}' instead.")

    @property
    def comparator(self) -> str:
        return self._comparator

    @comparator.setter
    def comparator(self, comparator: str):
        if comparator in PrimaryComparators.get_all_comparators() or self._allow_invalid_parameters:
            self._comparator = comparator
        else:
            log.error(f"Unknown comparator '{comparator}' set in condition. Valid comparators are: "
                      f"{PrimaryComparators.get_all_comparators()}")
            raise ParameterError(f"Unknown comparator '{comparator}'.")

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str):
        if (isinstance(value, str) and len(value) > 0) or self._allow_invalid_parameters:
            self._value = value
        else:
            raise ParameterError(f"Value must be a non-empty string. Got '{value}' of type '{type(value)}' instead.")

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, active: bool):
        if isinstance(active, bool):
            evaluate_parameters = self._allow_invalid_parameters and active
            self._active = active
            if evaluate_parameters:
                # Condition is activated and invalid parameters were allowed: Re-evaluate all parameters
                try:
                    self.section = self.section
                    self.key = self.key
                    self.comparator = self.comparator
                    self.value = self.value
                    self.handle_missing_data = self.handle_missing_data
                except ParameterError as e:
                    self._active = False
                    raise ParameterError(f"Invalid condition can not be activated: {e}")
        else:
            raise ParameterError(f"Active must be a boolean. Got '{active}' of type '{type(active)}' instead.")

    @property
    def handle_missing_data(self) -> ConditionHandleMissingData:
        return self._handle_missing_data

    @handle_missing_data.setter
    def handle_missing_data(self, handle_missing_data: str):
        if handle_missing_data is None:
            self._handle_missing_data = ConditionHandleMissingData.default()
        else:
            # raises an error if the value is not valid
            try:
                self._handle_missing_data = ConditionHandleMissingData.get_from_value(handle_missing_data)
            except ParameterError as e:
                if self._allow_invalid_parameters:
                    self._handle_missing_data = handle_missing_data
                else:
                    raise e

    def _do_handle_missing_data(self, policy_name: str, missing: str, object_name: str,
                                available_keys: list = None) -> bool:
        """
        This function handles the behaviour of the system if the data that is required to check a policy condition is
        missing. There are three valid options: raise an error (default), evaluate the condition to True or evaluate
        the condition to False.

        :param policy_name: The name of the policy
        :param missing: The missing data, either equal to the object_name or the condition key
        :param object_name: The name of the object that should be evaluated in the condition
        :param available_keys: The available keys of the object (if it is available), optional
        :return: True if handle_missing_data is CONDITION_IS_TRUE
                 False if handle_missing_data is CONDITION_IS_FALSE
                 raise PolicyError if handle_missing_data is RAISE_ERROR or is None
        """
        # Define log / error message according to the missing data
        log_available_keys = None
        if missing == object_name:
            # the full object is not available
            log_message = (f"Policy '{policy_name}' has a condition on the section '{self.section}' with key "
                           f"'{self.key}', but a {object_name} is unavailable. This should not happen! Please "
                           f"check/reduce the policy actions or disable the policy."
                           f"\n{''.join(traceback.format_stack())}.")
            error_message = (f"Policy '{policy_name}' has a condition on the section '{self.section}' with key "
                             f"'{self.key}', but a {object_name} is unavailable!")
        elif missing == self.key:
            # the object is available, but it does not contain the key
            log_message = (f"Unknown {self.section} key '{self.key}' referenced in condition of policy "
                           f"'{policy_name}'.")
            if available_keys:
                log_available_keys = f"Available {self.section} keys: {available_keys}"
            error_message = (f"Unknown {self.section} key '{self.key}' referenced in condition of policy "
                             f"'{policy_name}'!")
        else:
            # We should never reach this point, but if we do, some parameters seem to be not consistent. Hence, we
            # log a more imprecise message
            log_message = (f"Policy '{policy_name}' has a condition on the section '{self.section}' with key "
                           f"'{self.key}', but '{missing}' is unavailable: {''.join(traceback.format_stack())}.")
            error_message = (f"Policy '{policy_name}' has a condition on the section '{self.section}' with key "
                             f"'{self.key}', but some required data is unavailable!")

        if self.handle_missing_data is ConditionHandleMissingData.RAISE_ERROR:
            # default is error
            log.error(log_message)
            if log_available_keys:
                log.debug(log_available_keys)
            raise PolicyError(error_message)
        elif self.handle_missing_data is ConditionHandleMissingData.IS_TRUE:
            log.debug(log_message + " Evaluating condition as True, according to the policy definition.")
            if log_available_keys:
                log.debug(log_available_keys)
            return True
        elif self.handle_missing_data is ConditionHandleMissingData.IS_FALSE:
            log.debug(log_message + " Evaluating condition as False, according to the policy definition.")
            if log_available_keys:
                log.debug(log_available_keys)
            return False
        else:
            # raise error for undefined behaviour
            log.error(f"Unknown handle missing data {self.handle_missing_data} defined in condition of policy "
                      f"{policy_name} for {object_name} and key '{self.key}'. Allowed values are: "
                      f"{[ConditionHandleMissingData.get_valid_values()]}")
            raise PolicyError(f"Unknown handle missing data {self.handle_missing_data} defined in condition of "
                              f"policy {policy_name}.")

    def get_token_data(self, serial: Union[str, None]) -> ConditionSectionData:
        """
        Get the token data for the condition.

        :param serial: The serial of the token
        :return: The value from token data and further information if it is not available
        """
        data = ConditionSectionData("token")
        token = None
        if serial:
            try:
                from privacyidea.lib.token import get_one_token
                token = get_one_token(serial=serial)
            except ResourceNotFoundError:
                # The error for a missing token will be handled later
                log.debug(f"Token with serial '{serial}' not found.")
        data.object_available = token is not None

        if data.object_available:
            if self.section == ConditionSection.TOKEN:
                token_dict = token.get_as_dict()
                data.value = token_dict.get(self.key)
                if data.value is None:
                    data.available_keys = list(token_dict.keys())
            elif self.section == ConditionSection.TOKENINFO:
                token_info = token.get_tokeninfo()
                data.value = token_info.get(self.key)
                if data.value is None:
                    data.available_keys = list(token_info.keys())
        return data

    def get_container_data(self, container_serial: Union[str, None]) -> ConditionSectionData:
        """
        Get the container data for the condition.

        :param container_serial: The serial of the container
        :return: The value from container data and further information if it is not available
        """
        data = ConditionSectionData("container")
        container = None
        if container_serial:
            try:
                from privacyidea.lib.container import find_container_by_serial
                container = find_container_by_serial(container_serial)
            except ResourceNotFoundError:
                # The error for a missing container will be handled later
                log.debug(f"Container with serial '{container_serial}' not found.")
        data.object_available = container is not None

        if data.object_available:
            if self.section == ConditionSection.CONTAINER:
                container_dict = container.get_as_dict(include_tokens=False)
                data.value = container_dict.get(self.key)
                if data.value is None:
                    data.available_keys = list(container_dict.keys())
            elif self.section == ConditionSection.CONTAINER_INFO:
                container_info = container.get_container_info_dict()
                data.value = container_info.get(self.key)
                if data.value is None:
                    data.available_keys = list(container_info.keys())
        return data

    def get_user_data(self, user: Union[User, None]) -> ConditionSectionData:
        """
        Get the user data for the condition.

        :param user: The user to check
        :return: The value from user data and further information if it is not available
        """
        data = ConditionSectionData("user")
        data.object_available = user is not None
        if data.object_available:
            user_info = user.info
            data.value = user_info.get(self.key)
            if data.value is None:
                data.available_keys = list(user_info.keys())
        return data

    def get_request_header_data(self, request_header: Union[EnvironHeaders, None]) -> ConditionSectionData:
        """
        Get the request header data for the condition.

        :param request_header: The request header to check
        :return: The value from request header and further information if it is not available
        """
        data = ConditionSectionData(self.section)
        data.object_available = request_header is not None

        if data.object_available:
            if self.section == ConditionSection.HTTP_REQUEST_HEADER:
                data.value = request_header.get(self.key)
                if data.value is None:
                    data.available_keys = list(request_header.keys())
            elif self.section == ConditionSection.HTTP_ENVIRONMENT:
                request_environment = request_header.environ
                data.value = request_environment.get(self.key)
                if data.value is None:
                    data.available_keys = list(request_environment.keys())
        return data

    def get_data_from_dict(self, dictionary: Optional[dict]) -> ConditionSectionData:
        """
        Get the value from the request data for the condition.

        :param dictionary: The dict from which to get the data value
        :return: The value from request data and further information if it is not available
        """
        data = ConditionSectionData(self.section)
        data.object_available = isinstance(dictionary, dict)

        if data.object_available:
            data.value = dictionary.get(self.key)
            if data.value is None:
                data.available_keys = list(dictionary.keys())
        return data

    def match(self, policy_name: str, user: Union[User, None], serial: Union[str, None],
              request_header: Union[EnvironHeaders, None], container_serial: Union[str, None] = None,
              request_data: Optional[dict] = None) -> bool:
        """
        Check if the condition matches the given user, token, or request header.

        :param policy_name: The name of the corresponding policy (for logging and error messages)
        :param user: The user to check
        :param serial: The serial number of the token
        :param request_header: The request header to check
        :param container_serial: The serial number of the container
        :param request_data: The request data
        :return: True if the condition matches, False otherwise
        """
        condition_matches = True
        if self.active:
            # Get required data from the section
            if self.section == ConditionSection.USERINFO:
                section_data = self.get_user_data(user)
            elif self.section in [ConditionSection.TOKEN, ConditionSection.TOKENINFO]:
                section_data = self.get_token_data(serial)
            elif self.section in [ConditionSection.HTTP_REQUEST_HEADER, ConditionSection.HTTP_ENVIRONMENT]:
                section_data = self.get_request_header_data(request_header)
            elif self.section in [ConditionSection.CONTAINER, ConditionSection.CONTAINER_INFO]:
                section_data = self.get_container_data(container_serial)
            elif self.section == ConditionSection.REQUEST_DATA:
                section_data = self.get_data_from_dict(request_data)
            else:  # pragma no cover
                # We should never reach this case as the section is already evaluated in the setter
                log.warning(f"Policy '{policy_name}' has condition with unknown section: '{self.section}'")
                raise PolicyError(f"Policy '{policy_name}' has condition with unknown section")

            # Compare values
            if section_data.object_available:
                if section_data.value is not None:
                    try:
                        condition_matches = compare_values(section_data.value, self.comparator, self.value)
                    except Exception as e:
                        log.warning(f"Error during handling the condition on {self.section} '{self.key}' "
                                    f"of policy \'{policy_name}\': {e}")
                        raise PolicyError(f"Invalid comparison in the {self.section} conditions of policy "
                                          f"\'{policy_name}\'")
                else:
                    condition_matches = self._do_handle_missing_data(policy_name, missing=self.key,
                                                                     object_name=section_data.object_name,
                                                                     available_keys=section_data.available_keys)
            else:
                condition_matches = self._do_handle_missing_data(policy_name, missing=section_data.object_name,
                                                                 object_name=section_data.object_name)
        return condition_matches
