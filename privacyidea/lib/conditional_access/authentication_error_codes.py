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

# Key set on token.auth_details when the token is verified without a first factor (knowledge factor), i.e. otppin=none.
NO_FIRST_FACTOR_KEY = "no_first_factor"

# Key set on token.auth_details when the token logged its own outcome and no terminal event should be added on top.
# A push_wait timeout sets this: the unanswered challenge is recorded only as CHALLENGE_TRIGGERED, not an MFA_FAIL.
SUPPRESS_TERMINAL_EVENT_KEY = "suppress_terminal_authentication_event"

# Key a token sets in its reply to carry the challenge transaction_id to the terminal authentication-log row without
# exposing it in the response. push_wait uses it so its LOGIN_SUCCESS row correlates with the trigger and out-of-band
# answer; the API layer pops it from the response details before sending.
LOG_TRANSACTION_ID_KEY = "log_transaction_id"


class AuthEventType(str, Enum):
    """
    Event types written to the authentication log.

    ``str`` is used instead of ``StrEnum`` (3.11+) for compatibility with Python 3.10. The ``__str__`` override
    normalizes ``str()``/f-string output to the value across all supported versions (3.10-3.14); without it the
    output would differ between versions.
    """
    PASSWORD_FAIL = "PASSWORD_FAIL"
    PIN_FAIL = "PIN_FAIL"
    TOKEN_ONLY_FAIL = "TOKEN_ONLY_FAIL"
    MFA_FAIL = "MFA_FAIL"
    USER_UNKNOWN = "USER_UNKNOWN"
    NO_TOKEN = "NO_TOKEN"
    NO_USABLE_TOKEN = "NO_USABLE_TOKEN"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    CHALLENGE_CONTINUED = "CHALLENGE_CONTINUED"
    CHALLENGE_TRIGGERED = "CHALLENGE_TRIGGERED"
    CHALLENGE_ANSWERED_OUT_OF_BAND = "CHALLENGE_ANSWERED_OUT_OF_BAND"
    CHALLENGE_ANSWERED_FAIL = "CHALLENGE_ANSWERED_FAIL"
    CHALLENGE_DECLINED = "CHALLENGE_DECLINED"
    ENROLLMENT_TRIGGERED = "ENROLLMENT_TRIGGERED"
    ENROLLMENT_CANCELED_FAIL = "ENROLLMENT_CANCELED_FAIL"

    def __str__(self) -> str:
        return self.value


# Request-level precedence, highest signal first.
REQUEST_EVENT_PRECEDENCE: list[AuthEventType] = [
    AuthEventType.ENROLLMENT_TRIGGERED,
    AuthEventType.LOGIN_SUCCESS,
    AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND,
    AuthEventType.CHALLENGE_CONTINUED,
    AuthEventType.CHALLENGE_TRIGGERED,
    AuthEventType.CHALLENGE_ANSWERED_FAIL,
    AuthEventType.CHALLENGE_DECLINED,
    AuthEventType.ENROLLMENT_CANCELED_FAIL,
    AuthEventType.MFA_FAIL,
    AuthEventType.TOKEN_ONLY_FAIL,
    AuthEventType.PASSWORD_FAIL,
    AuthEventType.PIN_FAIL,
    AuthEventType.NO_USABLE_TOKEN,
    AuthEventType.NO_TOKEN,
    AuthEventType.USER_UNKNOWN
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
