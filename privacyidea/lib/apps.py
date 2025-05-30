#  2017-07-13 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add period to key uri for TOTP token
#  2016-05-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             urlencode token isuuer.
#  2015-07-01 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add SHA Algorithms to QR Code
#  2014-12-01 Cornelius Kölbel <cornelius@privacyidea.org>
#             Migrate to flask
#
#  * May 08, 2014 Cornelius Kölbel
#  * 2014-09-12 added Motp URL. Cornelius Kölbel
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
It generates the URL for smartphone apps like
google authenticator
oath token

This only depends on the ConfigPolicy.
"""

import binascii
import logging

from urllib.parse import quote

from privacyidea.lib.log import log_with
from privacyidea.lib.user import User
from privacyidea.lib.utils import to_byte_string, b32encode_and_unicode, parse_time_sec_int

log = logging.getLogger(__name__)
MAX_QRCODE_LEN = 180


def _construct_extra_parameters(extra_data):
    """
    Given a dictionary of extra key-value pairs (all str),
    return a string that may be appended to a google authenticator / oathtoken URL.
    Values that are non-strings will be converted to str.
    Keys and values are converted to UTF-8 and urlquoted.
    :return: a string (may be empty if ``extra_data`` is empty)
    """
    extra_data_list = []
    for key, value in extra_data.items():
        encoded_key = quote(to_byte_string(key))
        encoded_value = quote(to_byte_string(value))
        extra_data_list.append('{key}={value}'.format(key=encoded_key, value=encoded_value))
    return ('&' if extra_data_list else '') + '&'.join(extra_data_list)


@log_with(log)
def create_motp_url(key, user=None, realm=None, serial=""):
    """
    This creates the motp url as described at
    http://huseynov.com/index.php?post=motp-vs-google-authenticator-and-a-new-otp-app
    
    The format is:
    motp://SecureSite:alice@wonder.land?secret=JBSWY3DPEHPK3PXP
    """
    # For Token2 the OTPKEY is hexencoded, not base32!
    otpkey = key
    # TODO: Migration: Policy
    # Policy = PolicyClass(request, config, c,
    #                     get_privacyidea_config())
    # label = Policy.get_tokenlabel(user, realm, serial)
    label = "mylabel"
    allowed_label_len = 20
    label = label[0:allowed_label_len]
    url_label = quote(label)

    return "motp://privacyidea:{0!s}?secret={1!s}".format(url_label, otpkey)


@log_with(log)
def create_google_authenticator_url(key=None, user=None,
                                    realm=None, tokentype="hotp", period="30",
                                    serial="mylabel", tokenlabel="<s>",
                                    hash_algo="SHA1", digits="6",
                                    issuer="privacyIDEA", user_obj=None,
                                    creator="privacyidea", extra_data=None):
    """
    This creates the google authenticator URL.
    This url may only be 119 characters long.
    If the URL would be longer, we shorten the username

    We expect the key to be hexlified!
    """
    extra_data = extra_data or {}
    tokentype = tokentype.lower()

    # policy depends on some lib.util

    user_obj = user_obj or User()
    if tokentype == "hotp":
        counter = "counter=1&"
    else:
        counter = ""

    # We need realm und user to be a string
    realm = realm or ""
    user = user or ""

    key_bin = binascii.unhexlify(key)
    # also strip the padding =, as it will get problems with the google app.
    otpkey = b32encode_and_unicode(key_bin).strip('=')

    base_len = len("otpauth://{0!s}/?secret={1!s}&counter=1".format(tokentype, otpkey))
    allowed_label_len = MAX_QRCODE_LEN - base_len
    log.debug("we have got {0!s} characters left for the token label".format(
        str(allowed_label_len)))
    # Deprecated
    label = tokenlabel.replace("<s>",
                               serial).replace("<u>",
                                               user).replace("<r>", realm)
    label = label.format(serial=serial, user=user, realm=realm,
                         givenname=user_obj.info.get("givenname", ""),
                         surname=user_obj.info.get("surname", ""))

    issuer = issuer.format(serial=serial, user=user, realm=realm,
                           givenname=user_obj.info.get("givenname", ""),
                           surname=user_obj.info.get("surname", ""))

    label = label[0:allowed_label_len]
    url_label = quote(label.encode("utf-8"))
    url_issuer = quote(issuer.encode("utf-8"))
    url_serial = quote(serial.encode("utf-8"))

    if hash_algo.lower() != "sha1":
        hash_algo = "algorithm={0!s}&".format(hash_algo.upper())
    else:
        # If the hash_algo is SHA1, we do not add it to the QR code to keep
        # the QR code simpler
        hash_algo = ""

    if tokentype == "totp":
        period = f"period={period}&"
    elif tokentype == "daypassword":
        period = f"period={parse_time_sec_int(period)}&"
    else:
        period = ""

    url = (f"otpauth://{tokentype}/{url_label}?secret={otpkey}&"
           f"{counter}{hash_algo}{period}"
           f"digits={digits}&"
           f"creator={creator}&"
           f"issuer={url_issuer}&"
           f"serial={url_serial}{_construct_extra_parameters(extra_data)}")

    return url


@log_with(log)
def create_oathtoken_url(otpkey=None, user=None, realm=None,
                         type="hotp", serial="mylabel", tokenlabel="<s>",
                         extra_data=None):
    timebased = ""
    if "totp" == type.lower():
        timebased = "&timeBased=true"
    # We need realm und user to be a string
    realm = realm or ""
    user = user or ""
    extra_data = extra_data or {}

    label = tokenlabel.replace("<s>",
                               serial).replace("<u>",
                                               user).replace("<r>", realm)
    url_label = quote(label)

    extra_parameters = _construct_extra_parameters(extra_data)
    url = f"oathtoken:///addToken?name={url_label}&lockdown=true&key={otpkey}{timebased}{extra_parameters}"

    return url
