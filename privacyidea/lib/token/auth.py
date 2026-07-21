# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Authentication and validation against tokens (the check_* family)."""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from privacyidea.lib import _
from privacyidea.lib.challengeresponsedecorators import (generic_challenge_response_reset_pin,
                                                         generic_challenge_response_resync)
from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType, AUTH_EVENT_TYPE_KEY,
                                                                           NO_FIRST_FACTOR_KEY, reduce_request_events,
                                                                           SUPPRESS_TERMINAL_EVENT_KEY)
from privacyidea.lib.config import (get_from_config,
                                    get_inc_fail_count_on_false_pin, SYSCONF)
from privacyidea.lib.error import (TokenAdminError, Error)
from privacyidea.lib.log import log_with
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policydecorators import (libpolicy,
                                              auth_user_does_not_exist,
                                              auth_user_has_no_token,
                                              auth_user_passthru,
                                              auth_user_timelimit,
                                              auth_lastauth,
                                              auth_cache,
                                              reset_all_user_tokens, force_challenge_response)
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.lib.utils import (is_true, create_tag_dict,
                                   redacted_phone_number, redacted_email)

from privacyidea.lib.token.query import get_one_token, get_tokens

if TYPE_CHECKING:
    from privacyidea.models import Challenge


log = logging.getLogger(__name__)



@log_with(log)
def check_realm_pass(realm: str, passw: str, options: dict | None = None,
                     include_types: list | str | None = None,
                     exclude_types: list | str | None = None) -> tuple[bool, dict]:
    """
    This function checks, if the given passw matches any token in the given
    realm. This can be used for the 4-eyes token.
    Only tokens that are assigned are tested.

    The options dictionary may contain a key/value pair 'exclude_types' or
    'include_types' with the value containing a list of token types to
    exclude/include from/in the search.

    It returns the res True/False and a reply_dict, which contains the
    serial number of the matching token.

    :param realm: The realm of the user
    :param passw: The password containing PIN+OTP
    :param options: Additional options that are passed to the tokens
    :type options: dict
    :param include_types: List of token types to use
    :type include_types: list or str
    :param exclude_types: List to token types *not* to use
    :type exclude_types: list or str
    :return: tuple of bool and dict
    """
    reply_dict = {}
    # since an attacker does not know, which token is tested, we restrict to
    # only active tokens. He would not guess that the given OTP value is that
    #  of an inactive token.
    tokenobject_list = get_tokens(realm=realm, assigned=True, active=True)
    if not tokenobject_list:
        reply_dict["message"] = _("There is no active and assigned token in this realm")
        return False, reply_dict
    else:
        # reduce tokens by type
        if include_types:
            incl = include_types if isinstance(include_types, list) else [include_types]
            tokenobject_list = [tok for tok in tokenobject_list if tok.type in incl]
        elif exclude_types:
            excl = exclude_types if isinstance(exclude_types, list) else [exclude_types]
            tokenobject_list = [tok for tok in tokenobject_list if tok.type not in excl]

        if not tokenobject_list:
            reply_dict["message"] = _('There is no active and assigned token in '
                                      'this realm, included types: {0!s}, excluded '
                                      'types: {1!s}').format(include_types, exclude_types)
            return False, reply_dict

        return check_token_list(tokenobject_list, passw, options=options,
                                allow_reset_all_tokens=False)


@log_with(log, hide_args=[1])
@libpolicy(auth_lastauth)
def check_serial_pass(serial: str, passw: str, options: dict | None = None) -> tuple[bool, dict]:
    """
    This function checks the otp for a given serial

    If the OTP matches, True is returned and the otp counter is increased.

    The function tries to determine the user (token owner), to derive possible
    additional policies from the user.

    :param serial: The serial number of the token
    :type serial: basestring
    :param passw: The password usually consisting of pin + otp
    :type passw: basestring
    :param options: Additional options. Token specific.
    :type options: dict
    :return: tuple of result (True, False) and additional dict
    :rtype: tuple
    """
    token_object = get_one_token(serial=serial)
    res, reply_dict = check_token_list([token_object], passw,
                                       user=token_object.user,
                                       options=options,
                                       allow_reset_all_tokens=True)

    return res, reply_dict


@log_with(log)
def check_otp(serial: str, otpval: str) -> tuple[bool, dict]:
    """
    This function checks the OTP for a given serial number

    :param serial:
    :param otpval:
    :return: tuple of result and dictionary containing a message if the
        verification failed
    :rtype: tuple(bool, dict)
    """
    reply_dict = {}
    token_object = get_one_token(serial=serial)
    res = token_object.check_otp(otpval) >= 0
    if not res:
        reply_dict["message"] = _("OTP verification failed.")
    return res, reply_dict


@libpolicy(auth_cache)
@libpolicy(auth_user_does_not_exist)
@libpolicy(auth_user_has_no_token)
@libpolicy(auth_user_timelimit)
@libpolicy(auth_lastauth)
@libpolicy(auth_user_passthru)
@libpolicy(force_challenge_response)
@log_with(log, hide_kwargs=["passw"])
def check_user_pass(user: User, passw: str, options: dict | None = None) -> tuple[bool, dict]:
    """
    This function checks the otp for a given user.
    It is called by the API /validate/check

    If the OTP matches, True is returned and the otp counter is increased.

    :param user: The user who is trying to authenticate
    :type user: User object
    :param passw: The password usually consisting of pin + otp
    :type passw: basestring
    :param options: Additional options. Token specific.
    :type options: dict
    :return: tuple of result (True, False) and additional dict
    :rtype: tuple
    """
    options = dict(options) if options else {}
    token_type = options.pop("token_type", None)
    token_objects = get_tokens(user=user, tokentype=token_type)
    reply_dict = {}
    if not token_objects:
        # The user has no tokens assigned
        res = False
        reply_dict["message"] = _("The user has no tokens assigned")
        reply_dict[AUTH_EVENT_TYPE_KEY] = (
            AuthEventType.USER_UNKNOWN if not user or user.is_empty() else AuthEventType.NO_TOKEN)
    else:
        token_object = token_objects[0]
        res, reply_dict = check_token_list(token_objects, passw,
                                           user=token_object.user,
                                           options=options,
                                           allow_reset_all_tokens=True)

    return res, reply_dict


def create_challenges_from_tokens(token_list: list[TokenClass], reply_dict: dict,
                                  options: dict | None = None) -> None:
    """
    Get a list of active tokens and create challenges for these tokens.
    The reply_dict is modified accordingly. The transaction_id and
    the messages are added to the reply_dict.

    :param token_list: The list of the token objects, that can do challenge response
    :param reply_dict: The dictionary that is passed to the API response
    :param options: Additional options. Passed from the upper layer
    :return: None
    """
    options = options or {}
    options["push_triggered"] = False
    options["passkey_nonce"] = None
    reply_dict["multi_challenge"] = []
    transaction_id = None
    message_list = []
    for token in token_list:
        # Check if the max auth is succeeded
        if token.check_all(message_list):
            challenge_created, message, new_transaction_id, challenge_info = token.create_challenge(
                transactionid=transaction_id, options=options)

            if message:
                # We need to pass the info if a push token has been triggered, so that require presence can reuse the
                # challenge instead of creating a new one with a different answer
                # Also check the challenge info if the presence answer is returned to pass it on for tag replacement
                additional_tags = {}
                if token.get_type() == "push":
                    options["push_triggered"] = True
                    if "presence_answer" in challenge_info:
                        additional_tags["presence_answer"] = challenge_info["presence_answer"]
                # Add the reply to the response
                message = challenge_text_replace(message, user=token.user, token_obj=token,
                                                 additional_tags=additional_tags)
                message_list.append(message)

            if challenge_created:
                if new_transaction_id:
                    transaction_id = new_transaction_id
                challenge_info = challenge_info or {}
                challenge_info["transaction_id"] = transaction_id
                challenge_info["serial"] = token.token.serial
                token_type = token.get_tokentype()
                challenge_info["type"] = token_type
                # Only set client_mode if it has not been returned by the tokenclass creating the challenge
                challenge_info["client_mode"] = challenge_info.get("client_mode") or token.client_mode
                challenge_info["message"] = message
                # If they exist, add next pin and next password change
                next_pin = token.get_tokeninfo("next_pin_change")
                if next_pin:
                    challenge_info["next_pin_change"] = next_pin
                    challenge_info["pin_change"] = token.is_pin_change()
                next_passw = token.get_tokeninfo("next_password_change")
                if next_passw:
                    challenge_info["next_password_change"] = next_passw
                    challenge_info["password_change"] = token.is_pin_change(password=True)

                # If a passkey challenge has been triggered, reuse the nonce for all other passkey challenges
                # Normally, you would use allowCredentials, but we do one challenge per one token
                if token_type == "passkey":
                    passkey_nonce = challenge_info["challenge"]
                    options["passkey_nonce"] = passkey_nonce

                reply_dict["multi_challenge"].append(challenge_info)
                reply_dict.update(challenge_info)  # FIXME: This is deprecated and should be removed one day

    if message_list:
        unique_messages = set(message_list)
        reply_dict["message"] = ", ".join(unique_messages)
    # The "messages" element is needed by some decorators
    reply_dict["messages"] = message_list
    # TODO: This line is deprecated: Add the information for the old administrative triggerchallenge
    reply_dict["transaction_ids"] = [challenge.get("transaction_id") for challenge in
                                     reply_dict.get("multi_challenge", [])]


def weigh_token_type(token_obj: TokenClass) -> int:
    """
    This method returns a weight of a token type, which is used
    to sort the tokentype list. Other weighing functions can be implemented.

    The Push token weighs the most, so that it will be sorted to the end.

    :param token_obj: token object
    :return: weight of the tokentype
    :rtype: int
    """
    if token_obj.type.upper() == "PUSH":
        return 1000
    else:
        return ord(token_obj.type[0])


def _token_event(token: TokenClass, default_event: AuthEventType) -> AuthEventType:
    """
    Return the outcome a token classified for itself, if any, else *default_event*.

    A policy decorator (e.g. ``auth_otppin`` marking a wrong userstore password as PASSWORD_FAIL) records its more
    specific reason in ``token.auth_details[AUTH_EVENT_TYPE_KEY]``; this lets such a token override the default reason
    the orchestrator derived from the (pin_match, otp_count) tuple.
    """
    return token.auth_details.get(AUTH_EVENT_TYPE_KEY) or default_event


@log_with(log, hide_args=[1])
@libpolicy(reset_all_user_tokens)
@libpolicy(generic_challenge_response_reset_pin)
@libpolicy(generic_challenge_response_resync)
def check_token_list(token_object_list: list[TokenClass], passw: str, user: User | None = None,
                     options: dict | None = None, allow_reset_all_tokens: bool = False) -> tuple[bool, dict]:
    """
    Takes a list of token objects and tries to find the matching token for the given passw. It also tests
    * if the token is active or
    * the max fail count is reached,
    * if the validity period is ok...

    This function is called by check_serial_pass, check_user_pass and
    check_yubikey_pass.

    :param token_object_list: list of identified tokens
    :param passw: the provided password, can be just the PIN or PIN+OTP
    :param user: the identified use - as class object
    :param options: additional parameters, which are passed to the token
    :param allow_reset_all_tokens: If set to True, the policy reset_all_user_tokens is evaluated to
        reset all user tokens accordingly. Note: This parameter is used in the decorator. # TODO not good

    :return: tuple of success and optional response
    :rtype: (bool, dict)
    """
    res = False
    reply_dict = {}
    increase_auth_counters = not is_true(get_from_config(key="no_auth_counter"))

    # Add the user to the options, so that every token with access to options can see the user
    if options:
        options = options.copy()
    else:
        options = {}
    options.update({'user': user})

    # If there has been one token in challenge mode, we only handle challenges
    challenge_response_token_list = []
    challenge_request_token_list = []
    pin_matching_token_list = []
    invalid_token_list = []
    valid_token_list = []
    messages = []
    # Per-token outcomes for the authentication log
    request_events: list[AuthEventType] = []
    # Set when a token logged its own outcome and no terminal event should be added (push_wait timeout).
    terminal_event_suppressed = False
    num_all_tokens = len(token_object_list)

    # Remove locked tokens from token_object_list
    if len(token_object_list) > 0:
        token_object_list = [token for token in token_object_list if not token.is_revoked()]

        if len(token_object_list) == 0:
            # If there is no unlocked token left.
            raise TokenAdminError(_("This action is not possible, since the token is locked"),
                                  id=Error.TOKEN_LOCKED)

    # Remove disabled token types from token_object_list
    if PolicyAction.DISABLED_TOKEN_TYPES in options and options[PolicyAction.DISABLED_TOKEN_TYPES]:
        token_object_list = [token for token in token_object_list if
                             token.type not in options[PolicyAction.DISABLED_TOKEN_TYPES]]

    # Remove certain disabled tokens from token_object_list
    if len(token_object_list) > 0:
        token_object_list = [token for token in token_object_list if token.use_for_authentication(options)]

    for token_object in sorted(token_object_list, key=weigh_token_type):
        if log.isEnabledFor(logging.DEBUG):
            # Avoid a SQL query triggered by ``token_object.user`` in case the log level is not DEBUG
            log.debug(f"Found user with loginId {token_object.user}: {token_object.get_serial()}")

        # Reset exceeded fail counter if reset timeout is reached
        token_object.check_reset_failcount()

        if not token_object.check_all(messages):
            # token can not be used for authentication (e.g. maxfail exceeded, disabled, not within validity period)
            pass
        elif token_object.is_challenge_response(passw, user=user, options=options):
            # This is a challenge response, and it still has a challenge DB entry
            if token_object.has_db_challenge_response(passw, user=user, options=options):
                challenge_response_token_list.append(token_object)
            else:
                # This is a transaction_id, that either never existed or has expired or is not for this token.
                # We add this to the invalid_token_list
                invalid_token_list.append(token_object)
                request_events.append(AuthEventType.CHALLENGE_ANSWERED_FAIL)
        elif token_object.is_challenge_request(passw, user=user, options=options):
            # This is a challenge request
            challenge_request_token_list.append(token_object)
        else:
            if not (PolicyAction.FORCE_CHALLENGE_RESPONSE in options and is_true(
                    options[PolicyAction.FORCE_CHALLENGE_RESPONSE])):
                # This is a normal authentication attempt
                try:
                    # Pass the length of the valid_token_list to ``authenticate`` so that
                    # the push token can react accordingly
                    options["valid_token_num"] = len(valid_token_list)
                    pin_match, otp_count, repl = token_object.authenticate(passw, user, options=options)
                except TokenAdminError as tae:
                    # Token is locked
                    pin_match = False
                    otp_count = -1
                    repl = {'message': tae.message}
                repl = repl or {}
                reply_dict.update(repl)
                if otp_count >= 0:
                    # This is a successful authentication. LOGIN_SUCCESS is classified
                    # once, later, in the final valid_token_list block (which re-checks
                    # check_all before confirming success), so it is deliberately not
                    # appended here as well - it would be a redundant duplicate.
                    valid_token_list.append(token_object)
                elif pin_match:
                    # The PIN (first factor) of the token matches, but the OTP did not. For logging check if a pin was
                    # required / checked at all.
                    pin_matching_token_list.append(token_object)
                    if token_object.auth_details.get(SUPPRESS_TERMINAL_EVENT_KEY):
                        # The token logged its own outcome (push_wait timeout); do not add a terminal event on top.
                        terminal_event_suppressed = True
                    else:
                        default_event = (AuthEventType.TOKEN_ONLY_FAIL
                                         if token_object.auth_details.get(NO_FIRST_FACTOR_KEY)
                                         else AuthEventType.MFA_FAIL)
                        request_events.append(_token_event(token_object, default_event))
                else:
                    # Nothing matches at all: a wrong first factor (PIN_FAIL, or PASSWORD_FAIL with otppin=userstore).
                    # This stays PIN_FAIL even with otppin=none, if a pin was given unexpectedly
                    invalid_token_list.append(token_object)
                    request_events.append(_token_event(token_object, AuthEventType.PIN_FAIL))
            else:
                invalid_token_list.append(token_object)
                request_events.append(AuthEventType.PIN_FAIL)
                log.info(f"Skipping authentication try for token {token_object.get_serial()}"
                         f" because policy force_challenge_response is set.")

    """
    There might be
    2 in pin_matching_token_list
    0 in valid_token_list
    10 in invalid_token_list
    0 in challenge_token_list.

    in this case, the failcounter of the 2 tokens in pin_matching_token_list
    needs to be increased. And return False

    If there is
    0 pin_matching
    0 valid
    10 invalid
    0 challenge

    AND incFailCountOnFalsePin is True, then the failcounter of the
    10 invalid tokens need to be increased. And return False

    If there is
    X pin_matching
    1+ valid
    X invalid
    0 challenge

    Then the authentication with the valid tokens was successful and the
    <count> of the valid tokens need to be increased to the new count.
    """
    if valid_token_list:
        # One or more successfully authenticating tokens found
        # We need to return success
        message_list = [_("matching {0:d} tokens").format(len(valid_token_list))]
        # write serial numbers or something to audit log
        for token_obj in valid_token_list:
            # Reset the failcounter, if there is a timeout set
            token_obj.check_reset_failcount()
            # Check if the max auth is succeeded.
            # We need to set the offsets, since we are in the n+1st authentication.
            if token_obj.check_all(message_list):
                if increase_auth_counters:
                    token_obj.inc_count_auth_success()

                # The token is active and the auth counters are ok.
                res = True
                request_events.append(AuthEventType.LOGIN_SUCCESS)
                if not reply_dict.get("type"):
                    reply_dict["type"] = token_obj.token.tokentype
                if reply_dict["type"] != token_obj.token.tokentype:
                    reply_dict["type"] = "undetermined"
                # reset the failcounter of valid token
                token_obj.reset()
                # Run the token post method. e.g. registration token deletes itself.
                token_obj.post_success()
        if len(valid_token_list) == 1:
            # If only one token was found, we add the serial number,
            # the token type and the OTP length
            reply_dict["serial"] = valid_token_list[0].token.serial
            reply_dict["type"] = valid_token_list[0].token.tokentype
            reply_dict["otplen"] = valid_token_list[0].token.otplen
            # If they exist, add next pin and next password change
            next_pin = valid_token_list[0].get_tokeninfo("next_pin_change")
            if next_pin:
                reply_dict["next_pin_change"] = next_pin
                reply_dict["pin_change"] = valid_token_list[0].is_pin_change()
            next_passw = valid_token_list[0].get_tokeninfo("next_password_change")
            if next_passw:
                reply_dict["next_password_change"] = next_passw
                reply_dict["password_change"] = valid_token_list[0].is_pin_change(password=True)
        reply_dict["message"] = ", ".join(message_list)

    elif challenge_response_token_list:
        # The RESPONSE for a previous request of a challenge response token was found.
        matching_challenge = False
        further_challenge = False
        for token_object in challenge_response_token_list:
            if token_object.check_challenge_response(passw=passw, options=options) >= 0:
                reply_dict["serial"] = token_object.token.serial
                matching_challenge = True
                messages = []
                if not token_object.is_fit_for_challenge(messages, options=options):
                    messages.insert(0, _("Challenge matches, but token is not fit for challenge"))
                    reply_dict["message"] = ". ".join(messages)
                    log.info("Received a valid response to a "
                             "challenge for a non-fit token {!s}. {!s}".format(token_object.token.serial,
                                                                               reply_dict["message"]))
                else:
                    # Challenge matches, token is active and token is fit for challenge
                    res = True
                    if increase_auth_counters:
                        token_object.inc_count_auth_success()
                    reply_dict["message"] = _("Found matching challenge")
                    # If they exist, add next pin and next password change
                    next_pin = token_object.get_tokeninfo("next_pin_change")
                    if next_pin:
                        reply_dict["next_pin_change"] = next_pin
                        reply_dict["pin_change"] = token_object.is_pin_change()
                    next_passw = token_object.get_tokeninfo("next_password_change")
                    if next_passw:
                        reply_dict["next_password_change"] = next_passw
                        reply_dict["password_change"] = token_object.is_pin_change(password=True)
                    token_object.challenge_janitor()
                    if token_object.has_further_challenge(options):
                        # The token creates further challenges, so create the new challenge
                        # and new transaction_id
                        create_challenges_from_tokens([token_object], reply_dict, options)
                        further_challenge = True
                        res = False
                        request_events.append(AuthEventType.CHALLENGE_CONTINUED)
                    else:
                        # This was the last successful challenge, so
                        # reset the fail counter of the challenge response token
                        token_object.reset()
                        token_object.post_success()
                        request_events.append(_token_event(token_object, AuthEventType.LOGIN_SUCCESS))

                    # Clean up all challenges with this transaction_id from
                    # both Redis (when active) and the DB.
                    from privacyidea.lib.challenge import cancel_challenge
                    transaction_id = options.get("transaction_id") or options.get("state")
                    cancel_challenge(str(transaction_id))
                    # Authentication is successful, stop here
                    break

        if not res and not further_challenge:
            # We did not find any successful response, so we need to increase the failcounters
            for token_obj in challenge_response_token_list:
                if not token_obj.is_outofband():
                    token_obj.inc_failcount()
                request_events.append(AuthEventType.CHALLENGE_ANSWERED_FAIL)
            if not matching_challenge:
                if len(challenge_response_token_list) == 1:
                    reply_dict["serial"] = challenge_response_token_list[0].token.serial
                    reply_dict["type"] = challenge_response_token_list[0].token.tokentype
                    reply_dict["message"] = _("Response did not match the challenge.")
                else:
                    reply_dict["message"] = _("Response did not match for "
                                              "{0!s} tokens.").format(len(challenge_response_token_list))

    elif challenge_request_token_list:
        # This is the initial REQUEST of a challenge response token
        active_challenge_token = [t for t in challenge_request_token_list if t.token.active]
        if len(active_challenge_token) == 0:
            reply_dict["message"] = _("No active challenge response token found")
        else:
            for token_obj in challenge_request_token_list:
                token_obj.check_reset_failcount()
                if is_true(options.get("increase_failcounter_on_challenge")):
                    token_obj.inc_failcount()
            create_challenges_from_tokens(active_challenge_token, reply_dict, options)
            request_events.append(AuthEventType.CHALLENGE_TRIGGERED)

    elif pin_matching_token_list:
        # We did not find a valid token and no challenge.
        # But there are tokens, with a matching pin.
        # So we increase the failcounter. Return failure.
        for token_object in pin_matching_token_list:
            token_object.inc_failcount()
            if get_from_config(SYSCONF.RESET_FAILCOUNTER_ON_PIN_ONLY, False, return_bool=True):
                token_object.check_reset_failcount()
            reply_dict["message"] = _("wrong otp value")
            if len(pin_matching_token_list) == 1:
                # If there is only one pin matching token, we look if it was
                # a previous OTP value
                token = pin_matching_token_list[0]
                _r, pin, otp = token.split_pin_pass(passw)
                if token.is_previous_otp(otp):
                    reply_dict["message"] += _(". previous otp used again")
            if increase_auth_counters:
                for token_obj in pin_matching_token_list:
                    token_obj.inc_count_auth()
            # write the serial numbers to the audit log
            if len(pin_matching_token_list) == 1:
                reply_dict["serial"] = pin_matching_token_list[0].token.serial
                reply_dict["type"] = pin_matching_token_list[0].token.tokentype
                reply_dict["otplen"] = pin_matching_token_list[0].token.otplen

    elif invalid_token_list:
        # There were only tokens, that did not match the OTP value and
        # not even the PIN.
        # Depending on IncFailCountOnFalsePin, we increase the failcounter.
        reply_dict["message"] = _("wrong otp pin")
        if get_inc_fail_count_on_false_pin():
            for token_object in invalid_token_list:
                token_object.inc_failcount()
                if increase_auth_counters:
                    token_object.inc_count_auth()

    elif messages:
        reply_dict["message"] = ", ".join(set(messages))

    else:
        # There is no suitable token for authentication
        reply_dict["message"] = _("No suitable token found for authentication.")

    # Classify the request outcome for the authentication log by reducing the per-token events collected during the
    # walk to the single highest-precedence one. If no token contributed an event, the user either owns tokens that
    # were all unusable (revoked, disabled, disabled type, max-fail exceeded, out of validity) -> NO_USABLE_TOKEN, or
    # owns no token at all -> NO_TOKEN.
    reduced_event = reduce_request_events(request_events)
    # When a token suppressed its terminal event (push_wait timeout), leave the classification empty instead of
    # falling back, so no terminal row is logged on top of the one the token logged itself.
    if reduced_event is None and not terminal_event_suppressed:
        reduced_event = AuthEventType.NO_USABLE_TOKEN if num_all_tokens else AuthEventType.NO_TOKEN
    reply_dict[AUTH_EVENT_TYPE_KEY] = reduced_event

    return res, reply_dict


def challenge_text_replace(message: str, user: User | None, token_obj: TokenClass,
                           additional_tags: dict | None = None) -> str:
    # TODO this function should be a token function since most of the info is from that token anyway, optionally pass
    # TODO environment stuff into that function
    serial = token_obj.token.serial if token_obj.token.serial else None
    tokenowner = user if user else None
    token_type = token_obj.token.tokentype if token_obj.token.tokentype else ""
    tags = create_tag_dict(serial=serial, tokenowner=tokenowner, tokentype=token_type)
    if additional_tags:
        tags.update(additional_tags)

    if token_type == "sms":
        if is_true(token_obj.get_tokeninfo("dynamic_phone")):
            phone = token_obj.user.get_user_phone("mobile")
            if isinstance(phone, list) and phone:
                # if there is a non-empty list, we use the first entry
                phone = phone[0]
        else:
            phone = token_obj.get_tokeninfo("phone")
        if phone:
            tags["phone"] = phone
            tags["phone_redacted"] = redacted_phone_number(phone)

    if token_type == "email":
        if is_true(TokenClass.get_tokeninfo(token_obj, "dynamic_email")):
            email = token_obj.user.get_specific_info([token_obj.EMAIL_ADDRESS_KEY]).get(token_obj.EMAIL_ADDRESS_KEY)
            if isinstance(email, list) and email:
                # If there is a non-empty list, we use the first entry
                email = email[0]
        else:
            email = TokenClass.get_tokeninfo(token_obj, token_obj.EMAIL_ADDRESS_KEY)
        if email:
            tags["email"] = email
            tags["email_redacted"] = redacted_email(email)

    # If the message is for a pushtoken and the presence_answer is set, but there is no tag for placing that answer,
    # Append the answer to the message
    presence_answer = tags.get("presence_answer", None)
    if presence_answer and token_type == "push" and "{presence_answer}" not in message:
        # PyBabel gettext and f-strings don't like each other
        message += _(f" Please press: {presence_answer}")

    message = message.format_map(defaultdict(str, tags))

    return message


def create_challenge(serial: str, transaction_id: str = None, challenge: str = '',
                     data=None, session: str = '',
                     validitytime: int = 120) -> "Challenge":
    """
    Create a new challenge and persist it - to Redis if available, to the DB otherwise.

    This is the single entry point for challenge creation. When the challenge
    cache is enabled (PI_REDIS_URL set *and* PI_REDIS_CACHE_CHALLENGES on), the
    challenge is written to Redis only and the SQL INSERT is skipped. If the
    cache is off or Redis fails, the challenge falls back to the database so it
    is never silently lost.

    Always returns a ``Challenge`` instance. On the cache path that instance is
    the in-memory object used to build the Redis payload; it is not added to the
    SQL session, so its ``.id`` is ``None`` and it must not be ``save()``-ed or
    mutated by the caller. Use ``transaction_id`` for identity - it's the only
    stable identifier across both backends. To read the challenge back (from
    whichever backend holds it) use ``get_challenges()``.

    :param serial: Serial number of the token this challenge belongs to
    :param transaction_id: Transaction id of the challenge. A new one is generated if None.
    :param challenge: The challenge string
    :param data: Optional data to store with the challenge (str, dict, or None)
    :param session: Session string
    :param validitytime: Validity period in seconds (default: 120)
    :return: The created Challenge object
    """
    from privacyidea.lib.cache import cache_challenge, redis_feature_enabled
    from privacyidea.models import Challenge
    db_challenge = Challenge(serial,
                             transaction_id=transaction_id,
                             challenge=challenge,
                             data=data if data is not None else '',
                             session=session if session is not None else '',
                             validitytime=validitytime)
    if redis_feature_enabled("challenges"):
        # Cache only, skip the DB write. Redis TTL handles expiry;
        # challenges are ephemeral by nature.
        cache_challenge(
            serial=db_challenge.serial,
            transaction_id=db_challenge.transaction_id,
            challenge=db_challenge.challenge,
            data=db_challenge.data,
            session=db_challenge.session,
            timestamp=db_challenge.timestamp,
            expiration=db_challenge.expiration,
        )
        # If cache_challenge() failed it called _disable_redis(), so the flag
        # check now returns False. Fall back to DB so the challenge is not lost.
        if not redis_feature_enabled("challenges"):
            db_challenge.save()
    else:
        db_challenge.save()
    return db_challenge
