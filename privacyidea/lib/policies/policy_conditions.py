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
from enum import Enum

from privacyidea.lib import _
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.utils.compare import COMPARATORS

log = logging.getLogger(__name__)


class CONDITION_SECTION(object):
    __doc__ = """This is a list of available sections for conditions of policies """
    USERINFO = "userinfo"
    TOKENINFO = "tokeninfo"
    TOKEN = "token"  # nosec B105 # section name
    HTTP_REQUEST_HEADER = "HTTP Request header"
    HTTP_ENVIRONMENT = "HTTP Environment"

    @classmethod
    def get_all_sections(cls) -> list[str]:
        """
        Return all available sections for conditions of policies as a list.
        """
        sections = [cls.USERINFO, cls.TOKENINFO, cls.TOKEN, cls.HTTP_REQUEST_HEADER, cls.HTTP_ENVIRONMENT]
        return sections


class CONDITION_CHECK(object):
    __doc__ = """The available check methods for extended conditions"""
    # TODO: Use the same datatype for all checks
    DO_NOT_CHECK_AT_ALL = 1
    ONLY_CHECK_USERINFO = [CONDITION_SECTION.USERINFO]
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


class PolicyConditionClass:
    _pass_if_inactive = False

    @log_with(log)
    def __init__(self, section: str, key: str, comparator: str, value: str, active: bool,
                 handle_missing_data: str = None, pass_if_inactive: bool = False):
        self.active = active
        self._pass_if_inactive = pass_if_inactive
        self.section = section
        self.key = key
        self.comparator = comparator
        self.value = value
        self.handle_missing_data = handle_missing_data

    @property
    def _allow_invalid_parameters(self):
        return self._pass_if_inactive and not self.active

    @property
    def section(self):
        return self._section

    @section.setter
    def section(self, section):
        if section in CONDITION_SECTION.get_all_sections() or self._allow_invalid_parameters:
            self._section = section
        else:
            log.error(f"Unknown section '{section}' set in condition. Valid sections are: "
                      f"{CONDITION_SECTION.get_all_sections()}")
            raise ParameterError(f"Unknown section '{section}' set in condition.")

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        if (isinstance(key, str) and len(key) > 0) or self._allow_invalid_parameters:
            self._key = key
        else:
            raise ParameterError(f"Key must be a non-empty string. Got '{key}' of type '{type(key)}' instead.")

    @property
    def comparator(self):
        return self._comparator

    @comparator.setter
    def comparator(self, comparator):
        if comparator in COMPARATORS.get_all_comparators() or self._allow_invalid_parameters:
            self._comparator = comparator
        else:
            log.error(f"Unknown comparator '{comparator}' set in condition. Valid comparators are: "
                      f"{COMPARATORS.get_all_comparators()}")
            raise ParameterError(f"Unknown comparator '{comparator}'.")

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if (isinstance(value, str) and len(value) > 0)  or self._allow_invalid_parameters:
            self._value = value
        else:
            raise ParameterError(f"Value must be a non-empty string. Got '{value}' of type '{type(value)}' instead.")

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
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
    def handle_missing_data(self):
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
