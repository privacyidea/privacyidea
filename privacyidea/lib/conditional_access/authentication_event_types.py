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
    # Correct first factor (pin / password), but the second factor failed, e.g. wrong OTP.
    # Also used for a failed passkey authentication, since the exact cause of failure cannot be determined there.
    MFA_FAIL = "MFA_FAIL"
    # Username not found in any resolver, or the resolved user is empty.
    USER_UNKNOWN = "USER_UNKNOWN"
    # User is known but has no tokens assigned, or the requested token does not exist.
    NO_TOKEN = "NO_TOKEN"
    # Tokens exist but every one is unusable (revoked, locked, disabled, expired, or over max-fail).
    NO_USABLE_TOKEN = "NO_USABLE_TOKEN"
    # The request named no token type the endpoint can start an authentication for: the type parameter is missing, or
    # names a type this endpoint does not support. About the *request*, not about the tokens a user owns - which is what
    # NO_TOKEN / NO_USABLE_TOKEN above are for.
    INVALID_TOKEN_TYPE = "INVALID_TOKEN_TYPE"
    # Authentication fully succeeded.
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    # Challenge answered correctly, but the token requires at least one further challenge.
    CHALLENGE_CONTINUED = "CHALLENGE_CONTINUED"
    # A challenge was created and sent to the client (push notification, trigger_challenge, passkey, …).
    CHALLENGE_TRIGGERED = "CHALLENGE_TRIGGERED"
    # A challenge was asked for but the server could not produce one - a required policy is missing, or creating it
    # failed. The failure counterpart of CHALLENGE_TRIGGERED, as CHALLENGE_ANSWERED_FAIL is of the ANSWERED pair.
    # E.g. used for /validate/initialize where a challenge is NOT triggered by a password / pin.
    CHALLENGE_TRIGGER_FAIL = "CHALLENGE_TRIGGER_FAIL"
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
    # Fallback used when authentication fails but no other event type was set, so the failure is still recorded.
    UNKNOWN_FAIL_REASON = "UNKNOWN_FAIL_REASON"

    # --- written by conditional access itself, before any credential check ---------------------------------------
    # These three classify a request the conditional-access pre-check turned away, which is why they are the only
    # members no token flow ever produces (see CA_ENFORCEMENT_EVENT_TYPES). Each names the condition that ended the
    # request, like USER_UNKNOWN or NO_TOKEN above.
    #
    # A user lock in force turned the request away. Note the word order: USER_LOCKED is the rejection, while the
    # LOCK_USER action (in conditional_access_outcome.action_type) is the lock being created.
    USER_LOCKED = "USER_LOCKED"
    # A source-IP block in force turned the request away.
    IP_BLOCKED = "IP_BLOCKED"
    # A conditional-access policy's DENY action decided this single request. Named after the effect rather than the
    # action, because DENY is a ConditionalAccessAction value stored in the adjacent outcome table.
    ACCESS_DENIED = "ACCESS_DENIED"

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
    AuthEventType.INVALID_TOKEN_TYPE: AuthEventOutcome.FAILURE,
    AuthEventType.CHALLENGE_ANSWERED_FAIL: AuthEventOutcome.FAILURE,
    AuthEventType.CHALLENGE_TRIGGER_FAIL: AuthEventOutcome.FAILURE,
    AuthEventType.CHALLENGE_DECLINED: AuthEventOutcome.FAILURE,
    AuthEventType.ENROLLMENT_CANCELED_FAIL: AuthEventOutcome.FAILURE,
    AuthEventType.UNKNOWN_FAIL_REASON: AuthEventOutcome.FAILURE,
    AuthEventType.USER_LOCKED: AuthEventOutcome.FAILURE,
    AuthEventType.IP_BLOCKED: AuthEventOutcome.FAILURE,
    AuthEventType.ACCESS_DENIED: AuthEventOutcome.FAILURE,
}


# The event types conditional access writes itself, when its pre-check rejects a request before any credential check.
#
# They are deliberately not trackable by any policy: counting one would let a lock feed itself, since a locked
# user's own rejections would hold a retriggering LOCK_USER's count at or above threshold, and since_last_success
# can never reset it either because a locked user never succeeds. A DENY policy tracking ACCESS_DENIED would
# likewise be judging its own prior denials. The legitimate escalation - blocking an IP after repeated failures -
# is a second, higher-threshold stage on the underlying failure events.
#
# Excluding them from the vocabulary makes that structural rather than a warning: the policy-selection join in
# evaluate_conditional_access_policies can then never match one.
CA_ENFORCEMENT_EVENT_TYPES: frozenset[AuthEventType] = frozenset({
    AuthEventType.USER_LOCKED,
    AuthEventType.IP_BLOCKED,
    AuthEventType.ACCESS_DENIED,
})

# The event types a conditional-access policy may count, i.e. everything an authentication attempt itself can produce.
# This is what the policy CRUD validates against and what the policy editor offers; the authentication log's own
# event-type endpoint still lists *all* types, because an admin must be able to filter for a rejection.
TRACKABLE_EVENT_TYPES: list[AuthEventType] = [event_type for event_type in AuthEventType
                                              if event_type not in CA_ENFORCEMENT_EVENT_TYPES]


def outcome_of(event_type: AuthEventType) -> AuthEventOutcome:
    """Return the :class:`AuthEventOutcome` of *event_type* (see :data:`EVENT_TYPE_OUTCOME`)."""
    return EVENT_TYPE_OUTCOME[event_type]


class CountMode(str, Enum):
    """
    How a conditional-access policy counts the tracked :class:`AuthEventType`\\ s against its stage thresholds. The
    valid modes depend on the policy target (see ``_COUNT_MODES_BY_TARGET`` in the CRUD layer): both targets support the
    volume modes; :attr:`DISTINCT_USERS` is additionally available for a ``source_ip`` target (and its default).

    :attr:`PER_REQUEST` counts individual ``authentication_log`` rows. :attr:`PER_ATTEMPT` counts whole
    authentication *attempts*: the rows sharing one ``attempt_id`` are collapsed into a single attempt, so a
    multi-request challenge / multichallenge login counts once. Both are volume modes and track the same vocabulary
    (:class:`AuthEventType` names); the mode only changes the unit that is counted. For a ``source_ip`` target they
    give plain per-IP rate limiting (raw request / attempt volume from one IP).

    :attr:`DISTINCT_USERS` counts the number of distinct accounts a subject targeted rather than the volume of events
    -- the password-spraying / enumeration signal for a ``source_ip`` policy (one IP hitting many accounts). It is
    specific to the ``source_ip`` target (there is no distinct-accounts notion for a single-user policy).

    ``str``/``Enum`` (not ``StrEnum``) for Python 3.10, like :class:`AuthEventType`.
    """
    PER_REQUEST = "PER_REQUEST"
    PER_ATTEMPT = "PER_ATTEMPT"
    DISTINCT_USERS = "DISTINCT_USERS"

    def __str__(self) -> str:
        return self.value


# Request-level precedence, highest signal first. Only the event types a token flow can produce appear here: the
# CA_ENFORCEMENT_EVENT_TYPES classify a request the pre-check rejected before any token logic ran, so they never reach
# reduce_request_events.
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
    # Ranked lowest of the real failures, above the UNKNOWN_FAIL_REASON fallback: both describe the *request* the
    # endpoint refused rather than an outcome one of the request's tokens reached, so whenever a token did reach one it
    # is the better classification. In practice neither reduces against anything - the endpoints that emit them
    # classify a request with a single event - and they are listed here because every non-enforcement type must be.
    AuthEventType.CHALLENGE_TRIGGER_FAIL,
    AuthEventType.INVALID_TOKEN_TYPE,
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
