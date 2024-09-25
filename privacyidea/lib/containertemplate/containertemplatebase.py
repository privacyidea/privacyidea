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
import json

from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.error import ParameterError


class TemplateOptionsBase:
    TOKEN_COUNT = "token_count"
    TOKEN_TYPES = "token_types"
    TOKENS = "tokens"
    USER_MODIFIABLE = "user_modifiable"


class ContainerTemplateBase:
    template_option_values = {
        TemplateOptionsBase.TOKEN_COUNT: int,
        TemplateOptionsBase.TOKEN_TYPES: ["any"],
        TemplateOptionsBase.USER_MODIFIABLE: bool
    }

    def __init__(self, db_template):
        self._db_template = db_template

    def get_template_options(self):
        return self.template_option_values.keys()

    def get_template_option_value(self, option):
        return self.template_option_values[option]

    def get_type_specific_options(self):
        return []

    @classmethod
    def get_class_type(cls):
        """
        Returns the type of the container template class.
        """
        return "generic"

    @classmethod
    def get_supported_token_types(cls):
        """
        Returns the supported token types for this container template.
        """
        return TokenContainerClass.get_supported_token_types()

    @property
    def name(self):
        return self._db_template.name

    @name.setter
    def name(self, value):
        self._db_template.name = value
        self._db_template.save()

    @property
    def container_type(self):
        return self._db_template.container_type

    @container_type.setter
    def container_type(self, value):
        self._db_template.type = value
        self._db_template.save()

    @property
    def template_options(self):
        return self._db_template.options

    @template_options.setter
    def template_options(self, options):
        if not isinstance(options, dict):
            raise ParameterError("options must be a dict")

        # Validates token types in options
        supported_token_types = self.get_supported_token_types()
        tokens = options.get("tokens", [])
        for token in tokens:
            token_type = token.get("type", None)
            if token.get("type", None) not in supported_token_types:
                raise ParameterError(f"Unsupported token type {token_type} for {self.get_class_type()} templates!")

        options = json.dumps(options)
        self._db_template.options = options
        self._db_template.save()

    @property
    def id(self):
        return self._db_template.id

    def delete(self):
        self._db_template.delete()
