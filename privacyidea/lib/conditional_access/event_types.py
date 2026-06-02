# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from enum import Enum
from typing import Iterable, Optional


class AuthenticationEventType(str, Enum):
    __doc__ = """The event type codes written to the authentication log.

    They encode the precise, machine-readable reason of an authentication
    outcome, so that conditional access policies can distinguish e.g. a
    compromised password (password/PIN correct, second factor wrong) from a
    brute force attempt (wrong password).

    One user request produces one log entry: a single /validate/check call
    may walk multiple tokens, and the per-token outcomes are reduced to a
    single event for the whole request via :func:`reduce_request_events`.
    Correlation of the multiple requests of one logical authentication
    attempt (challenge-response, push) is done via the transaction_id at
    query time instead.
    """
    # Successful authentication. Logged so the same table powers SSO-style
    # policies and the future dashboard.
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    # A challenge-response token (push, passkey, ...) was asked to issue
    # a challenge.
    CHALLENGE_TRIGGERED = "CHALLENGE_TRIGGERED"
    # The user-side response to a previously triggered challenge was correct.
    CHALLENGE_ANSWERED_OK = "CHALLENGE_ANSWERED_OK"
    # The user-side response to a previously triggered challenge was wrong.
    CHALLENGE_ANSWERED_FAIL = "CHALLENGE_ANSWERED_FAIL"
    # The user actively declined a previously triggered challenge
    # (e.g. denied a push request).
    CHALLENGE_DECLINED = "CHALLENGE_DECLINED"
    # Composite: the password/PIN was correct, but the second factor was
    # wrong. This is the highest-signal failure type and the basis of the
    # MFA brute-force detection.
    MFA_FAIL = "MFA_FAIL"
    # The OTP value was wrong (the PIN was correct, or not applicable)
    OTP_FAIL = "OTP_FAIL"
    # The static token PIN was wrong (but the OTP was correct, or not yet
    # evaluated)
    PIN_FAIL = "PIN_FAIL"
    # The userstore password was wrong (used with otppin=userstore)
    PASSWORD_FAIL = "PASSWORD_FAIL"
    # The user exists, but has no usable token for this request
    NO_TOKEN = "NO_TOKEN"
    # The user could not be resolved in any resolver
    USER_UNKNOWN = "USER_UNKNOWN"


# The fixed precedence (highest first) that classifies a whole request from
# its per-token outcomes. The ranking
#   LOGIN_SUCCESS > CHALLENGE_TRIGGERED > MFA_FAIL > PIN_FAIL
#     > NO_TOKEN > USER_UNKNOWN
# is set by the conditional access design: success wins; if no token
# authenticated but at least one had the password/PIN correct and only the
# second factor wrong, the request is MFA_FAIL (the high-signal case).
# The remaining codes are slotted pragmatically: a positive challenge answer
# ranks like a success, a wrong/declined challenge answer is a failed second
# factor and therefore ranks directly below MFA_FAIL, and PASSWORD_FAIL is
# the userstore sibling of PIN_FAIL.
REQUEST_EVENT_PRECEDENCE = (
    AuthenticationEventType.LOGIN_SUCCESS,
    AuthenticationEventType.CHALLENGE_ANSWERED_OK,
    AuthenticationEventType.CHALLENGE_TRIGGERED,
    AuthenticationEventType.MFA_FAIL,
    AuthenticationEventType.CHALLENGE_ANSWERED_FAIL,
    AuthenticationEventType.CHALLENGE_DECLINED,
    AuthenticationEventType.OTP_FAIL,
    AuthenticationEventType.PIN_FAIL,
    AuthenticationEventType.PASSWORD_FAIL,
    AuthenticationEventType.NO_TOKEN,
    AuthenticationEventType.USER_UNKNOWN,
)


def reduce_request_events(
        events: Iterable["AuthenticationEventType | str"]) -> Optional[AuthenticationEventType]:
    """
    Reduce the per-token outcomes of one HTTP request to the single event
    that classifies the whole request.

    A user may have multiple tokens and a single /validate/check call walks
    the token list. To avoid generating N events for one fumbled password on
    a user with N tokens, only the highest-precedence outcome (see
    ``REQUEST_EVENT_PRECEDENCE``) is logged.

    This reduces across tokens within *one* request only. Correlating the
    multiple requests of one logical authentication attempt is a query
    concern (via the transaction_id), not a logging concern.

    :param events: The per-token outcomes of the request, as
        ``AuthenticationEventType`` or string codes
    :return: The highest-precedence event, or None if *events* is empty
    :raises ValueError: if an unknown event code is passed
    """
    present = {AuthenticationEventType(event) for event in events}
    for event in REQUEST_EVENT_PRECEDENCE:
        if event in present:
            return event
    return None
