# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#
#  * 2015-07-01 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               Add SHA Algorithms to QR Code
#  * 2014-12-01 Cornelius Kölbel <cornelius@privacyidea.org>
#               Migrate to flask
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
import base64

import logging
log = logging.getLogger(__name__)
from urllib import quote
from privacyidea.lib.log import log_with

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
    #Policy = PolicyClass(request, config, c,
    #                     get_privacyidea_config())
    # label = Policy.get_tokenlabel(user, realm, serial)
    label = "mylabel"
    allowed_label_len = 20
    label = label[0:allowed_label_len]
    url_label = quote(label)
    
    return "motp://privacyidea:%s?secret=%s" % (url_label, otpkey)


@log_with(log)
def create_google_authenticator_url(key=None, user=None,
                                    realm=None, tokentype="hotp",
                                    serial="mylabel", tokenlabel="<s>",
                                    hash_algo="SHA1", digits="6",
                                    issuer="privacyIDEA"):
    """
    This creates the google authenticator URL.
    This url may only be 119 characters long.
    If the URL would be longer, we shorten the username

    We expect the key to be hexlified!
    """
    # policy depends on some lib.util

    if "hotp" == tokentype.lower():
        tokentype = "hotp"

    # We need realm und user to be a string
    realm = realm or ""
    user = user or ""

    key_bin = binascii.unhexlify(key)
    # also strip the padding =, as it will get problems with the google app.
    otpkey = base64.b32encode(key_bin).strip('=')

    base_len = len("otpauth://%s/?secret=%s&counter=1" % (tokentype, otpkey))
    max_len = 119
    allowed_label_len = max_len - base_len
    log.debug("we have got %s characters left for the token label" %
              str(allowed_label_len))
    label = tokenlabel.replace("<s>",
                               serial).replace("<u>",
                                               user).replace("<r>", realm)

    label = label[0:allowed_label_len]
    url_label = quote(label)

    if hash_algo.lower() != "sha1":
        hash_algo = "algorithm=%s&" % hash_algo
    else:
        # If the hash_algo is SHA1, we do not add it to the QR code to keep
        # the QR code simpler
        hash_algo = ""

    return ("otpauth://%s/%s?secret=%s&"
            "counter=1&%s"
            "digits=%s&"
            "issuer=%s" % (tokentype, url_label, otpkey,
                           hash_algo, digits, issuer))

@log_with(log)
def create_oathtoken_url(otpkey=None, user=None, realm=None,
                         type="hotp", serial="mylabel", tokenlabel="<s>"):
    timebased = ""
    if "totp" == type.lower():
        timebased = "&timeBased=true"
    # We need realm und user to be a string
    realm = realm or ""
    user = user or ""

    label = tokenlabel.replace("<s>",
                               serial).replace("<u>",
                                               user).replace("<r>", realm)
    url_label = quote(label)

    url = "oathtoken:///addToken?name=%s&lockdown=true&key=%s%s" % (
                                                                  url_label,
                                                                  otpkey,
                                                                  timebased
                                                                  )
    return url

