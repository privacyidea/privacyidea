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
from privacyidea.lib.containers.yubikey import YubikeyContainer
from privacyidea.lib.containertemplate.containertemplatebase import ContainerTemplateBase


class YubikeyContainerTemplate(ContainerTemplateBase):

    def __init__(self, db_template):
        super().__init__(db_template)

    @classmethod
    def get_template_class_options(cls):
        _custom_option_values = YubikeyContainer.get_class_options()
        template_option_values = ContainerTemplateBase.template_option_values.copy()
        template_option_values.update(_custom_option_values)
        return template_option_values

    @classmethod
    def get_type_specific_options(cls):
        return [x for x in cls.template_option_values.keys()
                if x not in ContainerTemplateBase.template_option_values.keys()]

    @classmethod
    def get_class_type(cls):
        """
        Returns the type of the container template class.
        """
        return "yubikey"

    @classmethod
    def get_supported_token_types(cls):
        """
        Returns the supported token types for this container template.
        """
        supported_token_types = ["hotp", "webauthn"]
        supported_token_types.sort()
        return supported_token_types
