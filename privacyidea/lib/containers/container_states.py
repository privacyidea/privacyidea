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
from enum import Enum


class ContainerStates(Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    LOST = "lost"
    DAMAGED = "damaged"

    @classmethod
    def get_exclusive_states(cls) -> dict["ContainerStates", list["ContainerStates"]]:
        """
        Returns a list of exclusive states.
        """
        state_types_exclusions = {
            cls.ACTIVE: [cls.DISABLED],
            cls.DISABLED: [cls.ACTIVE],
            cls.LOST: [],
            cls.DAMAGED: []
        }
        return state_types_exclusions

    @classmethod
    def check_excluded_states(cls, states: list["ContainerStates"]) -> bool:
        """
        Validates whether the state list contains states that excludes each other

        :param states: list of states
        :returns: True if the state list contains exclusive states, False otherwise
        """
        state_types = cls.get_exclusive_states()
        for state_name in states:
            state = cls(state_name)
            if state in state_types:
                excluded_states = state_types[state]
                same_states = list(set(states).intersection(excluded_states))
                if len(same_states) > 0:
                    return True
        return False

    @classmethod
    def get_supported_states(cls) -> list[str]:
        """
        Returns a list of the values for all supported states.
        """
        return [state.value for state in cls.__members__.values()]