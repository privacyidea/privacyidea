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
# SPDX-License-Identifier: AGPL-3.0-or-later

from privacyidea.lib.error import ParameterError
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.realm import get_realms

"""
This defines functions to evaluate the value for each action.
"""

def check_realm_list(realms: str):
    """
    Evaluates if the realms in a space separated list exist. If at least one realm not exist a Parameter error is
    raised containing a list of all invalid realms.

    :param realms: Space separate list of realms
    """
    if not realms:
        raise ParameterError("No realms specified!")
    realms = realms.split(" ")
    valid_realms = list(get_realms().keys())
    invalid_realms = list(set(realms) - set(valid_realms))
    if invalid_realms:
        raise ParameterError(f"The following realms do not exist: {invalid_realms}!")

EVALUATOR_FUNCTIONS = {
    PolicyAction.REALMDROPDOWN: check_realm_list,
}
