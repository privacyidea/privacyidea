# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mutating a single token's attributes, info, PIN, counters and state."""

import logging

from sqlalchemy.sql.expression import delete

from privacyidea.lib import _
from privacyidea.lib.config import (get_from_config)
from privacyidea.lib.decorators import (check_user_or_serial)
from privacyidea.lib.error import (TokenAdminError,
                                   ParameterError)
from privacyidea.lib.log import log_with
from privacyidea.lib.realm import realm_is_defined
from privacyidea.models import (db, TokenOwner)

from privacyidea.lib.token.query import get_one_token, get_tokens_from_serial_or_user


log = logging.getLogger(__name__)



@log_with(log)
def set_realms(serial, realms=None, add=False, allowed_realms: list = None):
    """
    Set all realms of a token. This sets the realms new. I.e. it does not add
    realms. So realms that are not contained in the list will not be assigned
    to the token anymore.

    If the token could not be found, a ResourceNotFoundError is raised.

    Thus, setting ``realms=[]`` clears all realms assignments.

    :param serial: the serial number of the token (exact)
    :type serial: basestring
    :param realms: A list of realm names
    :type realms: list
    :param add: if the realms should be added and not replaced
    :type add: bool
    :param allowed_realms: A list of realms, that the admin is allowed to manage
    """
    realms = realms or []
    corrected_realms = []

    # get rid of non-defined realms
    for realm in realms:
        if realm_is_defined(realm):
            corrected_realms.append(realm)

    token = get_one_token(serial=serial)

    # Check if admin is allowed to set the realms
    old_realms = token.get_realms()

    matching_realms = corrected_realms
    if allowed_realms:
        matching_realms = list(set(corrected_realms).intersection(allowed_realms))
        excluded_realms = list(set(corrected_realms) - set(matching_realms))
        if len(excluded_realms) > 0:
            log.info(f"User is not allowed to set realms {excluded_realms} for token {serial}.")

        # Check if admin is allowed to remove the old realms
        not_allowed_realms = set(old_realms) - set(allowed_realms)
        # Add realms that are not allowed to be removed to the set list
        matching_realms = list(set(matching_realms).union(not_allowed_realms))

    token.set_realms(matching_realms, add=add)
    token.save()


@log_with(log)
def set_defaults(serial):
    """
    Set the default values for the token with the given serial number (exact)

    :param serial: token serial
    :type serial: basestring
    :return: None
    """
    db_token = get_one_token(serial=serial).token
    db_token.otplen = int(get_from_config("DefaultOtpLen", 6))
    db_token.count_window = int(get_from_config("DefaultCountWindow", 15))
    db_token.maxfail = int(get_from_config("DefaultMaxFailCount", 15))
    db_token.sync_window = int(get_from_config("DefaultSyncWindow", 1000))
    db_token.tokentype = "hotp"
    db_token.save()


@log_with(log)
def assign_token(serial, user, pin=None, encrypt_pin=False, error_message=None):
    """
    Assign token to a user.
    If the PIN is given, the PIN is reset.

    :param serial: The serial number of the token
    :type serial: basestring
    :param user: The user, to whom the token should be assigned.
    :type user: User object
    :param pin: The PIN for the newly assigned token.
    :type pin: basestring
    :param encrypt_pin: Whether the PIN should be stored in an encrypted way
    :type encrypt_pin: bool
    :param error_message: The error message, that is displayed in case the token is already assigned
    :type error_message: basestring
    """
    token = get_one_token(serial=serial)

    # Check if the token already belongs to another user
    old_user = token.user
    if old_user:
        log.warning(f"token already assigned to user: {old_user!r}")
        error_message = error_message or _("Token already assigned to user {old_user!r}").format(old_user=old_user)
        raise TokenAdminError(error_message, id=1103)

    token.add_user(user)
    if pin is not None:
        token.set_pin(pin, encrypt=encrypt_pin)

    # reset the OtpFailCounter
    token.set_failcount(0)

    try:
        token.save()
    except Exception as e:  # pragma: no cover
        log.error('update Token DB failed')
        raise TokenAdminError(_("Token assign failed for {0!r}/{1!s} : {2!r}").format(user, serial, e), id=1105)

    log.debug("successfully assigned token with serial "
              f"{serial!r} to user {user!r}")
    return True


@log_with(log)
@check_user_or_serial
def unassign_token(serial, user=None):
    """
    unassign the user from the token, or all tokens of a user

    :param serial: The serial number of the token to unassign (exact). Can be None
    :param user: A user whose tokens should be unassigned
    :return: number of unassigned tokens
    """
    tokens = get_tokens_from_serial_or_user(serial=serial, user=user)
    for token in tokens:
        token.set_pin("")
        token.set_failcount(0)

        try:
            # Delete the tokenowner entry
            session = db.session
            stmt = delete(TokenOwner).where(TokenOwner.token_id == token.token.id)
            session.execute(stmt)
            session.commit()
        except Exception as e:  # pragma: no cover
            log.error('update token DB failed')
            raise TokenAdminError(_("Token unassign failed for") + f" {serial!r}/{user!r}: {e!r}", id=1105)

        log.debug(f"successfully unassigned token with serial {token.get_serial()!r}")
    # TODO: test with more than 1 token
    return len(tokens)


@log_with(log)
def resync_token(serial, otp1, otp2, options=None, user=None):
    """
    Resynchronize the token of the given serial number and user by searching the
    otp1 and otp2 in the future otp values.

    :param serial: token serial number (exact)
    :type serial: str
    :param otp1: first OTP value
    :type otp1: str
    :param otp2: second OTP value, directly after the first
    :type otp2: str
    :param options: additional options like the servertime for TOTP token
    :type options: dict
    :param user: The user, who's token should be resynced
    :type user: User object
    :return: result of the resync
    :rtype: bool
    """
    ret = False

    tokens = get_tokens_from_serial_or_user(serial=serial, user=user)

    for token in tokens:
        ret = token.resync(otp1, otp2, options)
        token.save()

    return ret


@log_with(log)
@check_user_or_serial
def reset_token(serial, user=None):
    """
    Reset the failcounter of a single token, or of all tokens of one user.

    :param serial: serial number (exact)
    :param user:
    :return: The number of tokens, that were reset
    :rtype: int
    """
    tokens = get_tokens_from_serial_or_user(serial=serial, user=user)

    for token in tokens:
        token.reset()
        token.save()

    return len(tokens)


@log_with(log)
@check_user_or_serial
def set_pin(serial, pin, user=None, encrypt_pin=False):
    """
    Set the token PIN of the token. This is the static part that can be used
    to authenticate.

    :param pin: The pin of the token
    :type pin: str
    :param user: If the user is specified, the pins for all tokens of this
        user will be set
    :type user: User object
    :param serial: If the serial is specified, the PIN for this very token
        will be set. (exact)
    :param encrypt_pin: Whether the PIN should be stored in an encrypted way
    :type encrypt_pin: bool
    :return: The number of PINs set (usually 1)
    :rtype: int
    """
    if isinstance(user, str):
        # check if by accident the wrong parameter (like PIN)
        # is put into the user attribute
        log.warning(f"Parameter user must not be a string: {user!r}")
        raise ParameterError(_("Parameter user must not be a string:") + f" {user!r}", id=1212)

    tokens = get_tokens_from_serial_or_user(serial=serial, user=user)

    for token in tokens:
        token.set_pin(pin, encrypt=encrypt_pin)
        token.save()

    return len(tokens)


@log_with(log)
def set_pin_user(serial, user_pin, user=None):
    """
    This sets the user pin of a token. This just stores the information of
    the user pin for (e.g. an eTokenNG, Smartcard) in the database

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param user_pin: The user PIN
    :type user_pin: str
    :param user: The user, for who's token the PIN should be set
    :type user: User object
    :return: The number of PINs set (usually 1)
    :rtype: int
    """
    tokens = get_tokens_from_serial_or_user(serial=serial, user=user)

    for token in tokens:
        token.set_user_pin(user_pin)
        token.save()

    return len(tokens)


@log_with(log)
def set_pin_so(serial, so_pin, user=None):
    """
    Set the SO PIN of a smartcard. The SO Pin can be used to reset the
    PIN of a smartcard. The SO PIN is stored in the database, so that it
    could be used for automatic processes for User PIN resetting.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param so_pin: The Security Officer PIN
    :type so_pin: basestring
    :param user: The user, for who's token the SO PIN should be set
    :type user: User object
    :return: The number of SO PINs set. (usually 1)
    :rtype: int
    """
    tokens = get_tokens_from_serial_or_user(serial=serial, user=user)

    for token in tokens:
        token.set_so_pin(so_pin)
        token.save()

    return len(tokens)


@log_with(log)
@check_user_or_serial
def revoke_token(serial, user=None):
    """
    Revoke a token, or all tokens of a single user.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param user: all tokens of the user will be enabled or disabled
    :type user: User object
    :return: Number of tokens that were enabled/disabled
    :rtype: int
    """
    tokens = get_tokens_from_serial_or_user(user=user, serial=serial)

    for token in tokens:
        token.revoke()
        token.save()

    return len(tokens)


@log_with(log)
@check_user_or_serial
def enable_token(serial, enable=True, user=None):
    """
    Enable or disable a token, or all tokens of a single user.
    This can be checked with is_token_active.

    Enabling an already active token will return 0.

    :param serial: The serial number of the token
    :type serial: basestring
    :param enable: False is the token should be disabled
    :type enable: bool
    :param user: all tokens of the user will be enabled or disabled
    :type user: User object
    :return: Number of tokens that were enabled/disabled
    :rtype:
    """
    # We search for all matching tokens first, in case the user has
    # provided a wrong serial number. Then we filter for the desired tokens.
    tokens = get_tokens_from_serial_or_user(user=user, serial=serial)
    count = 0

    for token in tokens:
        if token.is_active() == (not enable):
            token.enable(enable)
            token.save()
            count += 1

    return count


def is_token_active(serial):
    """
    Return True if the token is active, otherwise false
    Raise ResourceError if the token could not be found.

    :param serial: The serial number of the token
    :type serial: basestring
    :return: True or False
    :rtype: bool
    """
    token = get_one_token(serial=serial)
    return token.token.active


@log_with(log)
@check_user_or_serial
def set_otplen(serial, otplen=6, user=None):
    """
    Set the otp length of the token defined by serial or for all tokens of
    the user.
    The OTP length is usually 6 or 8.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param otplen: The length of the OTP value
    :type otplen: int
    :param user: The owner of the tokens
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokens = get_tokens_from_serial_or_user(serial=serial, user=user)

    for token in tokens:
        token.set_otplen(otplen)
        token.save()

    return len(tokens)


@log_with(log)
@check_user_or_serial
def set_hashlib(serial, hashlib="sha1", user=None):
    """
    Set the hashlib in the tokeninfo.
    Can be something like sha1, sha256...

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param hashlib: The hashlib of the token
    :type hashlib: basestring
    :param user: The User, for who's token the hashlib should be set
    :type user: User object
    :return: the number of token infos set
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_hashlib(hashlib)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_count_auth(serial, count, user=None, max=False, success=False):
    """
    The auth counters are stored in the token info database field.
    There are different counters that can be set::

        count_auth -> max=False, success=False
        count_auth_max -> max=True, success=False
        count_auth_success -> max=False, success=True
        count_auth_success_max -> max=True, success=True

    :param count: The counter value
    :type count: int
    :param user: The user owner of the tokens to modify
    :type user: User object
    :param serial: The serial number of the one token to modify (exact)
    :type serial: basestring
    :param max: True, if either count_auth_max or count_auth_success_max are
        to be modified
    :type max: bool
    :param success: True, if either ``count_auth_success`` or
        ``count_auth_success_max`` are to be modified
    :type success: bool
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        if max:
            if success:
                tokenobject.set_count_auth_success_max(count)
            else:
                tokenobject.set_count_auth_max(count)
        else:
            if success:
                tokenobject.set_count_auth_success(count)
            else:
                tokenobject.set_count_auth(count)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def get_tokeninfo(serial, info):
    """
    get a token info field in the database.

    :param serial: The serial number of the token
    :type serial: basestring
    :param info: The key of the info in the dict
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=None)

    if len(tokenobject_list) == 1:
        return tokenobject_list[0].get_tokeninfo(info)


@log_with(log)
@check_user_or_serial
def add_tokeninfo(serial, info, value=None, value_type=None, user=None):
    """
    Sets a token info field in the database. The info is a dict for each
    token of key/value pairs.

    :param serial: The serial number of the token
    :type serial: basestring
    :param info: The key of the info in the dict
    :param value: The value of the info
    :param value_type: The type of the value. If set to "password" the value
        is stored encrypted
    :type value_type: basestring
    :param user: The owner of the tokens, that should be modified
    :type user: User object
    :return: the number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.add_tokeninfo(info, value)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def delete_tokeninfo(serial, key, user=None):
    """
    Delete a specific token info field in the database.

    :param serial: The serial number of the token
    :type serial: basestring
    :param key: The key of the info in the dict
    :param user: The owner of the tokens, that should be modified
    :type user: User object
    :return: the number of tokens matching the serial and user. This number also includes tokens that did not have
        the token info *key* set in the first place!
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)
    for tokenobject in tokenobject_list:
        tokenobject.delete_tokeninfo(key)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_validity_period_start(serial, user, start):
    """
    Set the validity period for the given token.

    :param serial: serial number (exact)
    :param user:
    :param start: Timestamp in the format DD/MM/YY HH:MM
    :type start: basestring
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)
    for tokenobject in tokenobject_list:
        tokenobject.set_validity_period_start(start)
        tokenobject.save()
    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_validity_period_end(serial, user, end):
    """
    Set the validity period for the given token.

    :param serial: serial number (exact)
    :param user:
    :param end: Timestamp in the format DD/MM/YY HH:MM
    :type end: basestring
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)
    for tokenobject in tokenobject_list:
        tokenobject.set_validity_period_end(end)
        tokenobject.save()
    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_sync_window(serial, syncwindow=1000, user=None):
    """
    The sync window is the window that is used during resync of a token.
    Such many OTP values are calculated ahead, to find the matching otp value
    and counter.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param syncwindow: The size of the sync window
    :type syncwindow: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_sync_window(syncwindow)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_count_window(serial, countwindow=10, user=None):
    """
    The count window is used during authentication to find the matching OTP
    value. This sets the count window per token.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param countwindow: the size of the window
    :type countwindow: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_count_window(countwindow)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_description(serial, description, user=None, token=None):
    """
    Set the description of a token

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param description: The description for the token
    :type description: str
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: True. In case of an error raise an exception
    :rtype: int
    """
    if token is None:
        token = get_one_token(serial=serial, user=user)
    token.set_description(description)
    token.save()

    return True


@log_with(log)
@check_user_or_serial
def set_failcounter(serial, counter, user=None):
    """
    Set the fail counter of a  token.

    :param serial: The serial number of the token (exact)
    :param counter: THe counter to which the fail counter should be set
    :param user: An optional user
    :return: Number of tokens, where the fail counter was set.
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_failcount(counter)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_max_failcount(serial, maxfail, user=None):
    """
    Set the maximum fail counts of tokens. This is the maximum number a
    failed authentication is allowed.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param maxfail: The maximum allowed failed authentications
    :type maxfail: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_maxfail(maxfail)
        tokenobject.save()

    return len(tokenobject_list)
