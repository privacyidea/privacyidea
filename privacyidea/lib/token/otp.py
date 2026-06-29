# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""OTP value retrieval and reverse lookup of tokens by OTP."""

import logging


from privacyidea.lib import _
from privacyidea.lib.error import (TokenAdminError)
from privacyidea.lib.log import log_with

from privacyidea.lib.token.query import get_one_token


log = logging.getLogger(__name__)



@log_with(log)
def get_otp(serial, current_time=None):
    """
    This function returns the current OTP value for a given Token.
    The tokentype needs to support this function.
    if the token does not support getting the OTP value, a -2 is returned.
    If the token could not be found, ResourceNotFoundError is raised.

    :param serial: serial number of the token
    :param current_time: a fake servertime for testing of TOTP token
    :type current_time: datetime.datetime
    :return: tuple with (result, pin, otpval, passw)
    :rtype: tuple
    """
    token = get_one_token(serial=serial)
    return token.get_otp(current_time=current_time)


@log_with(log)
def get_multi_otp(serial, count=0, epoch_start=0, epoch_end=0, current_time=None, timestamp=None):
    """
    This function returns a list of OTP values for the given Token.
    Please note, that the tokentype needs to support this function.

    :param serial: the serial number of the token
    :type serial: basestring
    :param count: number of the next otp values (to be used with event or
        time based tokens)
    :param epoch_start: unix time start date (used with time based tokens)
    :param epoch_end: unix time end date (used with time based tokens)
    :param current_time: Simulate the servertime
    :type current_time: datetime
    :param timestamp: Simulate the servertime (unix time in seconds)
    :type timestamp: int

    :return: dictionary of otp values
    :rtype: dictionary
    """
    ret = {"result": False}
    token = get_one_token(serial=serial)
    log.debug(f"Getting multiple otp values for token {token}. curTime={current_time}")

    res, error, otp_dict = token.get_multi_otp(count=count,
                                               epoch_start=epoch_start,
                                               epoch_end=epoch_end,
                                               curTime=current_time,
                                               timestamp=timestamp)
    log.debug(f"Received {res!r}, {error!r}, and {len(otp_dict)} otp values")

    if res:
        ret = otp_dict
        ret["result"] = True
    else:
        ret["error"] = error

    return ret


@log_with(log)
def get_token_by_otp(token_list, otp="", window=10):
    """
    Search the token in the token_list, that creates the given OTP value.

    :param token_list: the list of token objects to be investigated
    :type token_list: list of token objects
    :param otp: the otp value, that needs to be found
    :type otp: basestring
    :param window: the window of search
    :type window: int

    :return: The token, that creates this OTP value
    :rtype: TokenClass
    """
    result_token = None
    result_list = []

    for token in token_list:
        log.debug(f"Checking token {token.get_serial()}")
        try:
            r = token.check_otp_exist(otp=otp, window=window)
            log.debug(f"Result = {int(r):d}")
            if r >= 0:
                result_list.append(token)
        except Exception as err:
            # A flaw in a single token should not stop privacyidea from finding the right token
            log.warning(f"Error calculating OTP for token {token.get_serial()}: {err}")

    if len(result_list) == 1:
        result_token = result_list[0]
    elif result_list:
        raise TokenAdminError(_('multiple tokens are matching this OTP value!'), id=1200)

    return result_token


@log_with(log)
def get_serial_by_otp(token_list, otp="", window=10):
    """
    Returns the serial for a given OTP value
    The token_list would be created by get_tokens()

    :param token_list: the list of token objects to be investigated
    :type token_list: list of token objects
    :param otp: the otp value, that needs to be found
    :param window: the window of search
    :type window: int

    :return: the serial for a given OTP value and the user
    :rtype: basestring
    """
    serial = None
    token = get_token_by_otp(token_list, otp=otp, window=window)

    if token is not None:
        serial = token.get_serial()

    return serial


@log_with(log)
def get_serial_by_otp_list(token_list: list, otp_list: list, window: int = 10, counter: int = None) -> list[str]:
    """
    Returns a list of serials for a given list of OTP values
    The tokenobject_list would be created by get_tokens()

    :param token_list: the list of token objects to be investigated
    :param otp_list: a list of otp values, that need to be found
    :param window: the window of search
    :param counter: the counter value to be used for the OTP calculation,
        if None the actual counter of the token is used

    :return: a list of serials for the given OTP values and the user
    """
    result_list = []

    for otp in otp_list:
        for token in token_list:
            log.debug(f"checking token {token.get_serial()}")
            try:
                if token.type == "hotp":
                    r = token.check_otp_exist(otp=otp, window=window, inc_counter=False, counter=counter)
                else:
                    r = token.check_otp_exist(otp=otp, window=window, inc_counter=False)
                log.debug(f"otp_exists = {r > 0}")
                if r >= 0:
                    result_list.append(token)
            except Exception as err:
                # A flaw in a single token should not stop privacyidea from finding
                # the right token
                log.warning(f"error in calculating OTP for token {token.get_serial()}: {err}")
        token_list = result_list
        result_list = []

    serials = [token.get_serial() for token in token_list]

    return serials
