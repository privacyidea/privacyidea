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


class ContainerTemplateBase:
    template_option_values = {}

    def __init__(self, db_template):
        self._db_template = db_template

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
        supported_token_types = ["hotp", "remote", "daypassword", "spass", "totp", "4eyes", "paper", "push",
                                 "indexedsecret", "webauthn", "tan", "applspec", "registration", "sms", "email", "tiqr"]
        supported_token_types.sort()
        return supported_token_types

    @property
    def name(self):
        return self._db_template.name

    @property
    def container_type(self):
        return self._db_template.container_type

    @classmethod
    def get_template_class_options(cls):
        return cls.template_option_values

    @classmethod
    def get_template_option_keys(cls):
        return cls.template_option_values.keys()

    @classmethod
    def get_type_specific_options(cls):
        return []

    @property
    def template_options(self):
        return self._db_template.options

    def get_template_options_as_dict(self):
        return json.loads(self.template_options) if self.template_options else {}

    @template_options.setter
    def template_options(self, options):
        if not isinstance(options, dict):
            raise ParameterError("options must be a dict")
        validated_options = {}

        # Validates token types in options
        supported_token_types = self.get_supported_token_types()
        tokens = options.get("tokens", [])
        for token in tokens:
            token_type = token.get("type", None)
            if token.get("type", None) not in supported_token_types:
                raise ParameterError(f"Unsupported token type {token_type} for {self.get_class_type()} templates!")
        validated_options["tokens"] = tokens

        # Validates other options
        allowed_options = self.get_template_class_options()
        container_options = options.get("options", {})
        validated_container_options = {}
        for option in list(container_options.keys()):
            if option not in allowed_options.keys():
                raise ParameterError(f"Unsupported option {option} for {self.get_class_type()} templates!")
            if container_options[option] not in allowed_options[option]:
                raise ParameterError(
                    f"Unsupported value {container_options[option]} for option {option} in {self.get_class_type()} templates!")
            validated_container_options[option] = container_options[option]
        validated_options["options"] = validated_container_options

        self._db_template.options = json.dumps(validated_options)
        self._db_template.save()

    @property
    def id(self):
        return self._db_template.id

    @property
    def default(self):
        return self._db_template.default

    @default.setter
    def default(self, value: bool):
        if not isinstance(value, bool):
            raise ParameterError("Default must be a boolean")
        self._db_template.default = value
        self._db_template.save()

    @property
    def containers(self):
        return self._db_template.containers

    def delete(self):
        self._db_template.delete()
