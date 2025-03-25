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
from privacyidea.lib.containers.smartphone import SmartphoneContainer
from privacyidea.lib.containertemplate.containertemplatebase import ContainerTemplateBase


class SmartphoneContainerTemplate(ContainerTemplateBase):

    def __init__(self, db_template):
        super().__init__(db_template)

    @classmethod
    def get_template_class_options(cls) -> dict:
        custom_option_values = SmartphoneContainer.get_class_options()

        template_option_values = ContainerTemplateBase.get_template_class_options()
        custom_option_values.update(template_option_values)
        return custom_option_values

    @classmethod
    def get_class_type(cls) -> str:
        """
        Returns the type of the container template class.
        """
        return "smartphone"

    @classmethod
    def get_supported_token_types(cls) -> list:
        """
        Returns the supported token types for this container template.
        """
        return SmartphoneContainer.get_supported_token_types()
