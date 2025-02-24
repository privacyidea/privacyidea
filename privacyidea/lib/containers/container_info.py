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

from dataclasses import dataclass

PI_INTERNAL = "pi_internal"

@dataclass
class TokenContainerInfoData:
    """
    Dataclass for token container info
    """
    key: str
    value: str
    type: str
    description: str

    def __init__(self, key: str, value: str, info_type: str = None, description: str = None):
        self.key = key
        self.value = value
        self.type = info_type
        self.description = description
