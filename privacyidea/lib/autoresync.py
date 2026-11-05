# (c) NetKnights GmbH 2026,  https://netknights.it
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
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
The vocabulary of the token autoresync outcome, which is recorded in the audit log. It imports nothing from
privacyIDEA, so that the token classes and the response stripping of the conditional access can both use it.
"""
from enum import Enum

# Key set on token.auth_details when the OTP value was checked by the autoresync, holding an AutoResyncResult
AUTORESYNC_KEY = "autoresync"

# Key carrying the autoresync outcome of the checked tokens to the audit log without exposing it in the response: a
# client learning that its OTP value hit the sync window would learn more than "wrong otp value" tells it.
LOG_AUTORESYNC_KEY = "log_autoresync"


class AutoResyncResult(str, Enum):
    """
    Outcome of the autoresync step an OTP value triggered. The ``__str__`` override keeps f-string output to the value
    on all supported Python versions, as for AuthEventType.
    """
    # The OTP value is in the sync window and is stored to wait for the next one
    STARTED = 'started'
    SUCCESSFUL = 'successful'
    FAILED = 'failed'

    def __str__(self) -> str:
        return self.value
