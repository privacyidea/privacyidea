# 2024-05-08 Cornelius Kölbel <cornelius.koelbel@netknights.it>
# SPDX-FileCopyrightText: (C) 2024 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.

import logging
import re

log = logging.getLogger(__name__)


def validate_email(email):
    """
    Verify if the email is valid format
    :param email: email address
    :return: True if valid, False otherwise
    """
    # regular expression for email validation
    regex = r'^[-\w\.]+@([\w-]+\.)+[\w-]{2,4}$'
    if re.search(regex, email):
        return True
    else:
        return False
