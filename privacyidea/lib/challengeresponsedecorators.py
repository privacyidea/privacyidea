#  2020-08-03 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writeup
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNE7SS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
These are the decorator functions for generic challenge response mechanisms:

* PIN change

Currently the decorator is only tested in tests/test_lib_token.py
"""
import logging
from typing import Any

from privacyidea.lib.policy import Match
from privacyidea.lib.policy import check_pin, SCOPE
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.config import get_from_config
from privacyidea.lib.conditional_access.authentication_event_types import (AUTH_EVENT_REASON_DETAIL_KEY,
                                                                           AUTH_EVENT_REASON_KEY,
                                                                           AUTH_EVENT_SERIALS_KEY,
                                                                           AUTH_EVENT_TYPE_KEY, AuthEventReason,
                                                                           AuthEventType, build_reason_detail,
                                                                           order_request_reasons)
from privacyidea.lib.crypto import pass_hash, verify_pass_hash
from privacyidea.lib.challenge import consume_challenge, get_challenges
from privacyidea.lib import _
from privacyidea.lib.tokenclass import ClientMode, TokenClass
from privacyidea.lib.autoresync import LOG_AUTORESYNC_KEY
from privacyidea.lib.utils import is_true


log = logging.getLogger(__name__)

# Key that check_token_list sets in the reply of a successful authentication that continues with the PIN change via
# /validate/check. generic_challenge_response_reset_pin removes it from the reply and starts the PIN change.
PIN_CHANGE_FOLLOWS_KEY = "pin_change_via_validate_follows"


class CHALLENGE_TYPE:
    PIN_RESET = "generic_pin_reset"
    RESYNC = "generic_resync"


def pin_change_via_validate_follows(token: TokenClass, options: dict) -> bool:
    """
    Check if the PIN change via /validate/check follows a successful authentication with the token: the PIN of the
    token is due for a change and the policy change_pin_via_validate applies to the token.

    :param token: The token of the successful authentication
    :param options: The options of the request, with the request context g
    :return: True if the authentication continues with the PIN change
    """
    g = options.get("g")
    return bool(g and token.get_tokeninfo("next_pin_change") and token.is_pin_change()
                and Match.token(g, scope=SCOPE.AUTH, action=PolicyAction.CHANGE_PIN_VIA_VALIDATE,
                                token=token).any())


def _failed_pin_change_reply(message: str, event_type: AuthEventType, reason: AuthEventReason | str | None,
                             token: TokenClass | None = None) -> dict:
    """
    The reply to an answer of the PIN change that fails, with the event type and the reason for the authentication
    log, as check_token_list sets them.

    :param message: The message of the reply
    :param event_type: The event type of the failure
    :param reason: The reason of the failure, None if the event type says it all
    :param token: The token the answer was made for, None if the challenge is not one of the tokens of the request
    :return: The reply
    """
    reply_dict = {"message": message, AUTH_EVENT_TYPE_KEY: event_type}
    if reason:
        reply_dict[AUTH_EVENT_REASON_KEY] = order_request_reasons([reason])
    if token:
        serial = token.token.serial
        reply_dict["serial"] = serial
        reply_dict[AUTH_EVENT_SERIALS_KEY] = [serial]
        if reason:
            reply_dict[AUTH_EVENT_REASON_DETAIL_KEY] = build_reason_detail(reasons={serial: str(reason)})
    return reply_dict


def _create_challenge(token_obj, challenge_type, message, challenge_data=None):
    validity = int(get_from_config('DefaultChallengeValidityTime', 120))
    if challenge_type == CHALLENGE_TYPE.PIN_RESET:
        validity = int(get_from_config('PinResetChallengeValidityTime', validity))
    from privacyidea.lib.token import create_challenge
    db_challenge = create_challenge(serial=token_obj.token.serial,
                                    challenge=challenge_type,
                                    data=challenge_data,
                                    validitytime=validity)
    token_obj.challenge_janitor()
    reply_dict = {}
    reply_dict["multi_challenge"] = [{"transaction_id": db_challenge.transaction_id,
                                      "client_mode": ClientMode.INTERACTIVE,
                                      "message": message,
                                      "attributes": None,
                                      "serial": token_obj.token.serial,
                                      "type": token_obj.token.tokentype}]
    reply_dict["message"] = message
    reply_dict["messages"] = [message]
    reply_dict["transaction_id"] = db_challenge.transaction_id
    # Like a challenge of check_token_list, the reply names the token, so that the audit and the authentication log
    # name it for a request with a serial as well
    reply_dict["serial"] = token_obj.token.serial
    # TODO: This line is deprecated: Add the information for the old administrative triggerchallenge
    reply_dict["transaction_ids"] = [db_challenge.transaction_id]

    return reply_dict


def _keep_autoresync_info(reply_dict: dict, challenge_reply: dict) -> None:
    """
    Carry the audit-only autoresync outcome of the authentication over to the challenge replacing its reply.

    :param reply_dict: The reply of the authentication
    :param challenge_reply: The reply of the challenge, changed in place
    """
    if LOG_AUTORESYNC_KEY in reply_dict:
        challenge_reply[LOG_AUTORESYNC_KEY] = reply_dict[LOG_AUTORESYNC_KEY]


def generic_challenge_response_reset_pin(wrapped_function, *args, **kwds):
    """
    Check if the authentication was successful, but if the token needs to reset
    its PIN.

    Conditions: check_token_list decides if the PIN change follows the successful authentication of a token (see
    pin_change_via_validate_follows) and sets PIN_CHANGE_FOLLOWS_KEY in its reply.

    Policies: A policy defines, if this PIN reset functionality should be active
    at all. scope=AUTH, action=CHANGE_PIN_VIA_VALIDATE

    The authentication that starts the PIN change is not counted as a successful one. The confirmation of the new
    PIN completes it and counts it. Each reply carries the event type for the authentication log.

    args are:
    :param tokenobject_list: The list of all the tokens of the user, that will be checked
    :param passw: The password presented in the authentication. We need this for the PIN reset.

    kwds are:
    :param options: options dictionary containing g
    :param user: The user_obj
    """

    # Before we call the wrapped function, we need to check, if we have a generic challenge
    # for the given transaction_id and if the token serial matches a given token
    options = kwds.get("options") or {}
    user_obj = kwds.get("user")
    transaction_id = options.get("transaction_id") or options.get("state")
    if transaction_id:
        challenges = get_challenges(transaction_id=transaction_id, challenge=CHALLENGE_TYPE.PIN_RESET)
        if len(challenges) == 1:
            challenge = challenges[0]
            # As in check_token_list: an answer to a challenge of one of the tokens of the request belongs to the
            # attempt that triggered the challenge
            from privacyidea.lib.conditional_access.request_context import confirm_attempt_for_serials
            confirm_attempt_for_serials(t.token.serial for t in args[0])
            # The challenge has to belong to one of the tokens of the request and still be open, i.e. neither
            # expired nor answered
            token = next((t for t in args[0] if t.token.serial == challenge.serial), None)
            if not token:
                return False, _failed_pin_change_reply(_("Response did not match the challenge."),
                                                       AuthEventType.CHALLENGE_ANSWERED_FAIL,
                                                       AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION)
            if not challenge.is_open():
                reason = (AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION if challenge.is_valid()
                          else AuthEventReason.CHALLENGE_EXPIRED)
                return False, _failed_pin_change_reply(_("Response did not match the challenge."),
                                                       AuthEventType.CHALLENGE_ANSWERED_FAIL, reason, token)
            # Like for any other answer to a challenge, the token has to be usable for an authentication: the second
            # answer ends in one. So the policies and the token itself have to allow it for this request, for
            # example for its type and its service_id.
            from privacyidea.lib.token.auth import check_token_state, keep_tokens_usable_for_request
            token_reasons = {}
            if not keep_tokens_usable_for_request([token], options, token_reasons):
                return False, _failed_pin_change_reply(_("No suitable token found for authentication."),
                                                       AuthEventType.NO_USABLE_TOKEN,
                                                       token_reasons.get(token.token.serial), token)
            # And the token has to pass the checks of a login: revoked, authentication counters, fail counter with
            # its reset timeout, active, validity period and rollout state
            token_state = check_token_state(token)
            if not token_state.usable:
                return False, _failed_pin_change_reply(token_state.message, AuthEventType.NO_USABLE_TOKEN,
                                                       token_state.reason, token)
            # Then either verify the PIN or set the PIN the first time. The
            # PIN from the 1st response is stored in challenge.data
            challenge_data = challenge.get_data()
            pin_hash = challenge_data.get("pin_hash")
            if pin_hash:
                # Verify the password
                if not verify_pass_hash(args[1], pin_hash):
                    # The PIN change has to be started again, and the attempt counts as a failed one. Only the request
                    # that removes the challenge counts it: another one answered the challenge already.
                    if not consume_challenge(challenge):
                        return False, _failed_pin_change_reply(_("Response did not match the challenge."),
                                                               AuthEventType.CHALLENGE_ANSWERED_FAIL,
                                                               AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION, token)
                    token.inc_failcount()
                    return False, _failed_pin_change_reply(_("PINs do not match"),
                                                           AuthEventType.CHALLENGE_ANSWERED_FAIL,
                                                           AuthEventReason.CHALLENGE_WRONG_RESPONSE, token)
                # Each challenge can be answered once: of several requests with the same answer only the one that
                # removes the challenge sets the PIN
                if not consume_challenge(challenge):
                    return False, _failed_pin_change_reply(_("Response did not match the challenge."),
                                                           AuthEventType.CHALLENGE_ANSWERED_FAIL,
                                                           AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION, token)
                g = options.get("g")
                token.challenge_janitor()
                # Success, set new PIN and return success
                token.set_pin(args[1])
                pinpol = Match.token(g, scope=SCOPE.ENROLL, action=PolicyAction.CHANGE_PIN_EVERY,
                                     token=token).action_values(unique=True)
                # Set a new next_pin_change
                if pinpol:
                    # Set a new next pin change
                    token.set_next_pin_change(diff=list(pinpol)[0])
                else:
                    # Obviously the admin removed the policy for changing pins,
                    # so we will not require to change the PIN again
                    token.remove_tokeninfo("next_pin_change")
                # The confirmation completes the authentication that started the PIN change: like the last answer
                # to a challenge in check_token_list, it counts the authentication and resets the fail counter
                if not is_true(get_from_config(key="no_auth_counter")):
                    token.inc_count_auth_success()
                token.reset()
                return True, {"message": _("PIN successfully set."),
                              "serial": token.token.serial,
                              AUTH_EVENT_TYPE_KEY: AuthEventType.LOGIN_SUCCESS}
            else:
                # The PIN is presented the first time.
                # Verify if the PIN adheres to the PIN policies. This is always in the normal user context
                g = options.get("g")
                request_logged_in_user = getattr(g, "logged_in_user", None)
                g.logged_in_user = {"role": SCOPE.USER}
                if user_obj:
                    # check_pin below originally works for logged in users, since only logged in users
                    # are allowed to change the pin. So we need to construct a logged_in_user object, otherwise
                    # check_pin would fail.
                    g.logged_in_user["username"] = user_obj.login
                    g.logged_in_user["realm"] = user_obj.realm
                try:
                    check_pin(g, args[1], token.token.tokentype, user_obj)
                finally:
                    # The logged in user is only for check_pin: the rest of the request, for example the policy
                    # hide_version, has to see the request as it is
                    if request_logged_in_user is None:
                        delattr(g, "logged_in_user")
                    else:
                        g.logged_in_user = request_logged_in_user
                # The first challenge is used up, the new PIN has to be confirmed with a second one
                if not consume_challenge(challenge):
                    return False, _failed_pin_change_reply(_("Response did not match the challenge."),
                                                           AuthEventType.CHALLENGE_ANSWERED_FAIL,
                                                           AuthEventReason.CHALLENGE_UNKNOWN_TRANSACTION, token)
                reply_dict = _create_challenge(token, CHALLENGE_TYPE.PIN_RESET,
                                               _("Please enter the new PIN again"),
                                               {"pin_hash": pass_hash(args[1])})
                reply_dict[AUTH_EVENT_TYPE_KEY] = AuthEventType.CHALLENGE_CONTINUED
                return False, reply_dict

    success, reply_dict = wrapped_function(*args, **kwds)

    # After a successful authentication, check_token_list marks the reply if the PIN change follows. The key is
    # internal and is always removed. The token list can contain more than one token, so the reply names the token.
    pin_change_follows = reply_dict.pop(PIN_CHANGE_FOLLOWS_KEY, False)
    if success and pin_change_follows:
        serial = reply_dict.get("serial")
        token = next(t for t in args[0] if t.token.serial == serial)
        challenge_reply = _create_challenge(token, CHALLENGE_TYPE.PIN_RESET, _("Please enter a new PIN"))
        # check_token_list classified the authentication as the start of the PIN change
        challenge_reply[AUTH_EVENT_TYPE_KEY] = reply_dict.get(AUTH_EVENT_TYPE_KEY)
        _keep_autoresync_info(reply_dict, challenge_reply)
        return False, challenge_reply

    return success, reply_dict


def generic_challenge_response_resync(wrapped_function, *args, **kwds):
    """
    Check if the authentication request results in an autosync

    Conditions: The token has a pending autoresync (has_pending_autoresync): it stored the first OTP value of an
    autoresync in "otp1c" and waits for the next one. For HOTP the AutoResyncTimeout ("dueDate") must not have passed
    yet, as the next value can no longer complete the autoresync afterwards; TOTP has no AutoResyncTimeout. Token types
    without an autoresync never have a pending one.

    Policies: A policy defines that the token resync should be allowed this way.
    Note: The general config "autoresync" needs to be set anyway.

    A failed authentication of a token waiting for the next OTP value of an autoresync is answered with a challenge
    for that value. If the authentication triggered challenges, they are kept and the challenge of such a token asks
    for the next OTP value.

    args are:
    :param tokenobject_list: The list of all the tokens of the user, that will be checked
    :param passw: The password presented in the authentication.

    kwds are:
    :param options: options dictionary containing g
    :param user: The user_obj
    """
    success, reply_dict = wrapped_function(*args, **kwds)
    if success:
        return success, reply_dict

    g = (kwds.get("options") or {}).get("g")
    if reply_dict.get("multi_challenge"):
        _ask_for_resync_in_challenges(reply_dict, args[0], g)
    # After a failed authentication, we check if the token waits for the next OTP value
    elif reply_dict.get("serial"):
        # FIXME: Only works if the one token has a unique PIN
        serial = reply_dict.get("serial")
        # The tokenlist can contain more than one token. So we get the matching token object
        token = next((t for t in args[0] if t.token.serial == serial), None)
        if token and _resync_pending(token, g):
            challenge_reply = _create_challenge(token, CHALLENGE_TYPE.RESYNC, _resync_message())
            _keep_autoresync_info(reply_dict, challenge_reply)
            reply_dict = challenge_reply

    return success, reply_dict


def _resync_message() -> str:
    return _("To resync your token, please enter the next OTP value")


def _resync_pending(token: TokenClass, g: Any) -> bool:
    """
    Check if the token waits for the next OTP value of an autoresync and a policy allows to ask for it.

    :param token: The token to check
    :param g: The request context to match the policy with, None if there is none
    :return: True if the challenge of the token should ask for the next OTP value
    """
    return bool(token.has_pending_autoresync() and g and
                Match.token(g, scope=SCOPE.AUTH, action=PolicyAction.RESYNC_VIA_MULTICHALLENGE, token=token).any())


def _ask_for_resync_in_challenges(reply_dict: dict, tokens: list[TokenClass], g: Any) -> None:
    """
    Ask for the next OTP value in the challenges of the tokens that wait for it. Answering their challenge with that
    value already resyncs the token, so the other challenges of the reply stay.

    :param reply_dict: The reply with the triggered challenges, changed in place
    :param tokens: The tokens that were checked
    :param g: The request context to match the policy with, None if there is none
    """
    messages = reply_dict["messages"]
    changed = False
    for challenge in reply_dict["multi_challenge"]:
        token = next((t for t in tokens if t.token.serial == challenge.get("serial")), None)
        if token and _resync_pending(token, g):
            if challenge.get("message") in messages:
                messages[messages.index(challenge["message"])] = _resync_message()
            challenge["message"] = _resync_message()
            changed = True
    if changed:
        reply_dict["message"] = ", ".join(set(messages))
