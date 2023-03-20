# -*- coding: utf-8 -*-
#
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

from privacyidea.lib.policy import Match
from privacyidea.lib.policy import ACTION, SCOPE, check_pin, SCOPE
from privacyidea.lib.config import get_from_config
from privacyidea.lib.crypto import pass_hash, verify_pass_hash, get_rand_digit_str
from privacyidea.models import Challenge
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib import _
from privacyidea.lib.tokenclass import CLIENTMODE


log = logging.getLogger(__name__)


SEED_LENGTH = 16


class CHALLENGE_TYPE(object):
    PIN_RESET = "generic_pin_reset"
    RESYNC = "generic_resync"


def _create_challenge(token_obj, challenge_type, message, challenge_data=None):
    validity = int(get_from_config('DefaultChallengeValidityTime', 120))
    if challenge_type == CHALLENGE_TYPE.PIN_RESET:
        validity = int(get_from_config('PinResetChallengeValidityTime', validity))
    db_challenge = Challenge(token_obj.token.serial,
                             challenge=challenge_type,
                             data=challenge_data,
                             validitytime=validity)
    db_challenge.save()
    token_obj.challenge_janitor()
    reply_dict = {}
    reply_dict["multi_challenge"] = [{"transaction_id": db_challenge.transaction_id,
                                      "client_mode": CLIENTMODE.INTERACTIVE,
                                      "message": message,
                                      "attributes": None,
                                      "serial": token_obj.token.serial,
                                      "type": token_obj.token.tokentype}]
    reply_dict["message"] = message
    reply_dict["messages"] = [message]
    reply_dict["transaction_id"] = db_challenge.transaction_id
    # TODO: This line is deprecated: Add the information for the old administrative triggerchallenge
    reply_dict["transaction_ids"] = [db_challenge.transaction_id]

    return reply_dict


def generic_challenge_response_reset_pin(wrapped_function, *args, **kwds):
    """
    Check if the authentication was successful, but if the token needs to reset
    its PIN.

    Conditions: To do so we check for "next_pin_change" in the tokeninfo data. This
    is however easily done using token.is_pin_change().

    Policies: A policy defines, if this PIN reset functionality should be active
    at all. scope=AUTH, action=CHANGE_PIN_VIA_VALIDATE

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
            # check if challenge matches a token and if it is valid
            token_obj = next(t for t in args[0] if t.token.serial == challenge.serial)
            if token_obj:
                # Then either verify the PIN or set the PIN the first time. The
                # PIN from the 1st response is stored in challenge.data
                if challenge.data:
                    # Verify the password
                    if verify_pass_hash(args[1], challenge.data):
                        g = options.get("g")
                        challenge.set_otp_status(True)
                        token_obj.challenge_janitor()
                        # Success, set new PIN and return success
                        token_obj.set_pin(args[1])
                        pinpol = Match.token(g, scope=SCOPE.ENROLL, action=ACTION.CHANGE_PIN_EVERY,
                                             token_obj=token_obj).action_values(unique=True)
                        # Set a new next_pin_change
                        if pinpol:
                            # Set a new next pin change
                            token_obj.set_next_pin_change(diff=list(pinpol)[0])
                        else:
                            # Obviously the admin removed the policy for changing pins,
                            # so we will not require to change the PIN again
                            token_obj.del_tokeninfo("next_pin_change")
                        return True, {"message": "PIN successfully set.",
                                      "serial": token_obj.token.serial}
                    else:
                        return False, {"serial": token_obj.token.serial,
                                       "message": "PINs do not match"}
                else:
                    # The PIN is presented the first time.
                    # Verify if the PIN adheres to the PIN policies. This is always in the normal user context
                    g = options.get("g")
                    g.logged_in_user = {"role": SCOPE.USER}
                    if user_obj:
                        # check_pin below originally works for logged in users, since only logged in users
                        # are allowed to change the pin. So we need to construct a logged_in_user object, otherwise
                        # check_pin would fail.
                        g.logged_in_user["username"] = user_obj.login
                        g.logged_in_user["realm"] = user_obj.realm
                    check_pin(g, args[1], token_obj.token.tokentype, user_obj)
                    # We need to ask for a 2nd time
                    challenge.set_otp_status(True)
                    seed = get_rand_digit_str(SEED_LENGTH)
                    reply_dict = _create_challenge(token_obj, CHALLENGE_TYPE.PIN_RESET,
                                                   _("Please enter the new PIN again"),
                                                   pass_hash(args[1]))
                    return False, reply_dict

    success, reply_dict = wrapped_function(*args, **kwds)

    # After a successful authentication, we might start the PIN change process
    if success and reply_dict.get("pin_change"):
        g = options.get("g")
        # Determine the realm by the serial
        serial = reply_dict.get("serial")
        # The tokenlist can contain more than one token. So we get the matching token object
        token_obj = next(t for t in args[0] if t.token.serial == serial)
        if g and Match.token(g, scope=SCOPE.AUTH, action=ACTION.CHANGE_PIN_VIA_VALIDATE, token_obj=token_obj).any():
            reply_dict = _create_challenge(token_obj, CHALLENGE_TYPE.PIN_RESET, _("Please enter a new PIN"))
            return False, reply_dict

    return success, reply_dict


def generic_challenge_response_resync(wrapped_function, *args, **kwds):
    """
    Check if the authentication request results in an autosync

    Conditions: To do so we check for "otp1c" in the tokeninfo data.

    Policies: A policy defines that the token resync should be allowed this way.
    Note: The general config "autoresync" needs to be set anyways.

    args are:
    :param tokenobject_list: The list of all the tokens of the user, that will be checked
    :param passw: The password presented in the authentication.

    kwds are:
    :param options: options dictionary containing g
    :param user: The user_obj
    """
    success, reply_dict = wrapped_function(*args, **kwds)

    options = kwds.get("options") or {}
    # After a failed authentication, we check if the token has an otp1c
    if not success and reply_dict.get("serial"):
        # FIXME: Only works if the one token has a unique PIN
        serial = reply_dict.get("serial")
        g = options.get("g")
        # The tokenlist can contain more than one token. So we get the matching token object
        token_obj = next(t for t in args[0] if t.token.serial == serial)
        if token_obj and token_obj.get_tokeninfo("otp1c"):
            # We have an entry for resync
            if g and Match.token(g, scope=SCOPE.AUTH, action=ACTION.RESYNC_VIA_MULTICHALLENGE,
                                 token_obj=token_obj).any():
                reply_dict = _create_challenge(token_obj, CHALLENGE_TYPE.RESYNC,
                                               _("To resync your token, please enter the next OTP value"))

    return success, reply_dict
