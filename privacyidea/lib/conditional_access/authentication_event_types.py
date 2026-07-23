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
    # An authorization policy blocked the authentication
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    # Wrong user store password
    PASSWORD_FAIL = "PASSWORD_FAIL"
    # Wrong token pin
    PIN_FAIL = "PIN_FAIL"
    # PIN skipped (otppin=none / otponly=1) but the OTP itself is wrong.
    TOKEN_ONLY_FAIL = "TOKEN_ONLY_FAIL"
    # Correct first factor (pin / password), but the second factor failed, e.g. wrong otp
    # Note: We also log this for a failed passkey authentication, even thought we can not be sure what exactly failed
    # there.
    MFA_FAIL = "MFA_FAIL"
    # Username not found in any resolver, or the resolved user is empty.
    USER_UNKNOWN = "USER_UNKNOWN"
    # User is known but has no tokens assigned, or the requested token does not exist.
    NO_TOKEN = "NO_TOKEN"
    # Tokens exist but every one is unusable (revoked, locked, disabled, expired, or over max-fail).
    NO_USABLE_TOKEN = "NO_USABLE_TOKEN"
    # Authentication fully succeeded.
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    # Challenge answered correctly, but the token requires at least one further challenge.
    CHALLENGE_CONTINUED = "CHALLENGE_CONTINUED"
    # A challenge was created and sent to the client (push notification, trigger_challenge, passkey, …).
    CHALLENGE_TRIGGERED = "CHALLENGE_TRIGGERED"
    # Push challenge approved on the smartphone (out-of-band, signature verified).
    CHALLENGE_ANSWERED_OUT_OF_BAND = "CHALLENGE_ANSWERED_OUT_OF_BAND"
    # Challenge response is wrong, expired, or the transaction_id is unknown.
    CHALLENGE_ANSWERED_FAIL = "CHALLENGE_ANSWERED_FAIL"
    # Push challenge explicitly rejected on the smartphone.
    CHALLENGE_DECLINED = "CHALLENGE_DECLINED"
    # a successful authentication triggered the enrollment of a new token type to complete the authentication
    ENROLLMENT_TRIGGERED = "ENROLLMENT_TRIGGERED"
    # cancelling the enrollment failed (unknown or already-consumed transaction_id).
    ENROLLMENT_CANCELED_FAIL = "ENROLLMENT_CANCELED_FAIL"
    # Default fallback, if no auth event was set somewhere, but authentication failed we log this to have failed attempt
    UNKNOWN_FAIL_REASON = "UNKNOWN_FAIL_REASON"

    def __str__(self) -> str:
        return self.value


class AuthEventOutcome(str, Enum):
    """
    Outcome class of an :class:`AuthEventType`: did the authentication ``SUCCESS`` (succeed), ``FAILURE`` (fail/get
    denied), or is it ``PENDING`` (still in flight -- a challenge was sent/continued/approved out of band, or an
    enrollment was triggered).

    This is a domain classification, not a presentation/severity choice: it lets callers group events by result --
    e.g. a conditional-access policy condition selecting all failed events, or the WebUI coloring a row -- without
    enumerating each event type. ``str``/``Enum`` (not ``StrEnum``) for 3.10 compatibility, like :class:`AuthEventType`.
    """
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"

    def __str__(self) -> str:
        return self.value


# Outcome of each event type. Every AuthEventType must be classified here; EventTypeOutcomeTestCase asserts
# completeness so a new event type cannot be added without giving it an outcome.
EVENT_TYPE_OUTCOME: dict[AuthEventType, AuthEventOutcome] = {
    AuthEventType.LOGIN_SUCCESS: AuthEventOutcome.SUCCESS,
    AuthEventType.CHALLENGE_TRIGGERED: AuthEventOutcome.PENDING,
    AuthEventType.CHALLENGE_CONTINUED: AuthEventOutcome.PENDING,
    AuthEventType.CHALLENGE_ANSWERED_OUT_OF_BAND: AuthEventOutcome.PENDING,
    AuthEventType.ENROLLMENT_TRIGGERED: AuthEventOutcome.PENDING,
    AuthEventType.NOT_AUTHORIZED: AuthEventOutcome.FAILURE,
    AuthEventType.PASSWORD_FAIL: AuthEventOutcome.FAILURE,
    AuthEventType.PIN_FAIL: AuthEventOutcome.FAILURE,
    AuthEventType.TOKEN_ONLY_FAIL: AuthEventOutcome.FAILURE,
    AuthEventType.MFA_FAIL: AuthEventOutcome.FAILURE,
    AuthEventType.USER_UNKNOWN: AuthEventOutcome.FAILURE,
    AuthEventType.NO_TOKEN: AuthEventOutcome.FAILURE,
    AuthEventType.NO_USABLE_TOKEN: AuthEventOutcome.FAILURE,
    AuthEventType.CHALLENGE_ANSWERED_FAIL: AuthEventOutcome.FAILURE,
    AuthEventType.CHALLENGE_DECLINED: AuthEventOutcome.FAILURE,
    AuthEventType.ENROLLMENT_CANCELED_FAIL: AuthEventOutcome.FAILURE,
    AuthEventType.UNKNOWN_FAIL_REASON: AuthEventOutcome.FAILURE,
}


def outcome_of(event_type: AuthEventType) -> AuthEventOutcome:
    """Return the :class:`AuthEventOutcome` of *event_type* (see :data:`EVENT_TYPE_OUTCOME`)."""
    return EVENT_TYPE_OUTCOME[event_type]


# Request-level precedence, highest signal first.
REQUEST_EVENT_PRECEDENCE: list[AuthEventType] = [
    AuthEventType.NOT_AUTHORIZED,
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
    AuthEventType.USER_UNKNOWN,
    AuthEventType.UNKNOWN_FAIL_REASON
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
