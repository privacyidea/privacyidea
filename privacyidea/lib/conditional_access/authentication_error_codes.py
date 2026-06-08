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
import logging
from enum import Enum

log = logging.getLogger(__name__)

# Key under which the classified AuthEventType is carried from lib to api layer
AUTH_EVENT_TYPE_KEY = "authentication_event_type"


class AuthEventType(str, Enum):
    """
    Event types written to the authentication log.

    ``str`` is used instead of ``StrEnum`` (3.11+) for compatibility with Python 3.10. The ``__str__`` override
    normalizes ``str()``/f-string output to the value across all supported versions (3.10-3.14); without it the
    output would differ between versions.
    """
    PASSWORD_FAIL = "PASSWORD_FAIL"
    PIN_FAIL = "PIN_FAIL"
    OTP_FAIL = "OTP_FAIL"
    MFA_FAIL = "MFA_FAIL"
    USER_UNKNOWN = "USER_UNKNOWN"
    NO_TOKEN = "NO_TOKEN"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    CHALLENGE_TRIGGERED = "CHALLENGE_TRIGGERED"
    CHALLENGE_ANSWERED_OK = "CHALLENGE_ANSWERED_OK"
    CHALLENGE_ANSWERED_FAIL = "CHALLENGE_ANSWERED_FAIL"
    CHALLENGE_DECLINED = "CHALLENGE_DECLINED"

    def __str__(self) -> str:
        return self.value


# Request-level precedence, highest signal first.
REQUEST_EVENT_PRECEDENCE: list[AuthEventType] = [
    AuthEventType.LOGIN_SUCCESS,
    AuthEventType.CHALLENGE_ANSWERED_OK,
    AuthEventType.CHALLENGE_TRIGGERED,
    AuthEventType.CHALLENGE_ANSWERED_FAIL,
    AuthEventType.CHALLENGE_DECLINED,
    AuthEventType.MFA_FAIL,
    AuthEventType.OTP_FAIL,
    AuthEventType.PASSWORD_FAIL,
    AuthEventType.PIN_FAIL,
    AuthEventType.NO_TOKEN,
    AuthEventType.USER_UNKNOWN,
]

# Precedence rank of each event.
_EVENT_RANK: dict[AuthEventType, int] = {event: rank for rank, event in enumerate(REQUEST_EVENT_PRECEDENCE)}


def reduce_request_events(events: list[AuthEventType]) -> AuthEventType | None:
    """
    Reduce the per-token outcomes of one authentication request to the single event that classifies the whole request,
    by the fixed :data:`REQUEST_EVENT_PRECEDENCE`.

    Events without a defined precedence (e.g. a new :class:`AuthEventType` member that was not added to
    :data:`REQUEST_EVENT_PRECEDENCE`) are logged and ignored, so an oversight degrades the classification rather than
    breaking the authentication.

    :param events: an iterable of :class:`AuthEventType` members
    :return: the highest-precedence known event, or ``None`` if *events* holds no known event
    """
    winner = None
    winner_rank: int | None = None
    for event in events:
        rank = _EVENT_RANK.get(event)
        if rank is None:
            log.debug(
                f"Ignoring authentication event {event!r} without a defined precedence in REQUEST_EVENT_PRECEDENCE.")
            continue
        if winner_rank is None or rank < winner_rank:
            winner = event
            winner_rank = rank
    return winner
