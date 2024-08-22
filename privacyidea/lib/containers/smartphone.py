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
#
import logging

from privacyidea.lib.containerclass import TokenContainerClass

log = logging.getLogger(__name__)


class SmartphoneContainer(TokenContainerClass):

    def __init__(self, db_container):
        super().__init__(db_container)

    @classmethod
    def get_class_type(cls):
        """
        Returns the type of the container class.
        """
        return "smartphone"

    @classmethod
    def get_supported_token_types(cls):
        """
        Returns the token types that are supported by the container class.
        """
        return ["hotp", "totp", "push", "daypassword", "sms"]

    @classmethod
    def get_class_prefix(cls):
        """
        Returns the container class specific prefix for the serial.
        """
        return "SMPH"

    @classmethod
    def get_class_description(cls):
        """
        Returns a description of the container class.
        """
        return "A smartphone that uses an authenticator app."
