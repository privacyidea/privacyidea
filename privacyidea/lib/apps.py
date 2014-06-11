# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
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
'''
It generates the URL for smartphone apps like
google authenticator
oath token
'''

import binascii
import base64

import logging
log = logging.getLogger(__name__)

from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.config import get_privacyIDEA_config
from pylons import request, config, tmpl_context as c
from urllib import quote
from privacyidea.lib.log import log_with


@log_with(log)
def create_google_authenticator_url(user, realm, key, type="hmac", serial=""):
    '''
    This creates the google authenticator URL.
    This url may only be 119 characters long.
    Otherwise we qrcode.js can not create the qrcode.
    If the URL would be longer, we shorten the username
    
    We expect the key to be hexlified!
    '''
    # policy depends on some lib.util

    if "hmac" == type.lower():
        type = "hotp"

    key_bin = binascii.unhexlify(key)
    # also strip the padding =, as it will get problems with the google app.
    otpkey = base64.b32encode(key_bin).strip('=')

    #'url' : "otpauth://hotp/%s?secret=%s&counter=0" % ( user@realm, otpkey )
    base_len = len("otpauth://%s/?secret=%s&counter=0" % (type, otpkey))
    max_len = 119
    allowed_label_len = max_len - base_len
    log.debug("we have got %s characters left for the token label" % str(allowed_label_len))

    Policy = PolicyClass(request, config, c,
                         get_privacyIDEA_config())
    label = Policy.get_tokenlabel(user, realm, serial)
    label = label[0:allowed_label_len]

    url_label = quote(label)

    return "otpauth://%s/%s?secret=%s&counter=0" % (type, url_label, otpkey)

@log_with(log)
def create_oathtoken_url(user, realm, otpkey, type="hmac", serial=""):
    #'url' : 'oathtoken:///addToken?name='+serial +
    #                '&key='+otpkey+
    #                '&timeBased=false&counter=0&numDigites=6&lockdown=true',

    timebased = ""
    if "totp" == type.lower():
        timebased = "&timeBased=true"

    Policy = PolicyClass(request, config, c,
                         get_privacyIDEA_config())
    label = Policy.get_tokenlabel(user, realm, serial)
    url_label = quote(label)

    url = "oathtoken:///addToken?name=%s&lockdown=true&key=%s%s" % (
                                                                  url_label,
                                                                  otpkey,
                                                                  timebased
                                                                  )
    return url

