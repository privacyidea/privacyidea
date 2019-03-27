# -*- coding: utf-8 -*-
#
#  2016-04-04 Cornelius Kölbel <cornelius@privacyidea.org>
#             Move the API signature static methods to functions.
#  2016-03-23 Jochen Hein <jochen@jochen.org>
#             Fix signature verification/generation
#  2016-03-15 Cornelius Kölbel <cornelius@privacyidea.org>
#             Keep backward compatibility
#  2016-03-08 Jochen Hein <jochen@jochen.org>
#             Add the yubikey prefix to work with pam_yubikey/Yubico
#             Authentication Protocol.
#  2015-12-01 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add yubico validation protocol
#  2014-12-15 Cornelius Kölbel <cornelius@privacyidea.org>
#             Adapt during flask migration
#  2014-05-08 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  LSE
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
__doc__ = """
This token type provides the functionality for the Yubikey AES mode.

You can authenticate the Yubikeys in AES mode against the normal
validate/check API.
In addition you can also use the Yubico Validation Protocol to authenticate
the Yubikey managed by privacyIDEA. To use the Yubico Validation Protocol you
need to use the endpoint /ttype/yubikey.

Using the Yubico Validation Protocol you can run the
`Yubico PAM module <https://github.com/Yubico/yubico-pam>`_ with privacyIDEA
as the backend server.

This code is tested in tests/test_lib_tokens_yubikey.py
"""

import logging
from privacyidea.lib.log import log_with
from privacyidea.lib.policydecorators import challenge_response_allowed
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.utils import (modhex_decode, hexlify_and_unicode, checksum,
                                   to_bytes, b64encode_and_unicode)
import binascii
from privacyidea.lib.decorators import check_token_locked
from privacyidea.api.lib.utils import getParam
import datetime
import base64
import hmac
from hashlib import sha1
from privacyidea.lib.config import get_from_config
from privacyidea.lib.tokenclass import TOKENKIND
from privacyidea.lib import _

optional = True
required = False


log = logging.getLogger(__name__)


def yubico_api_signature(data, api_key):
    """
    Get a dictionary "data", sort the dictionary by the keys
    and sign it HMAC-SHA1 with the api_key

    :param data: The data to be signed
    :type data: dict
    :param api_key: base64 encoded API key
    :type api_key: basestring
    :return: base64 encoded signature
    """
    r = dict(data)
    if 'h' in r:
        del r['h']
    keys = sorted(r.keys())
    data_string = ""
    for key in keys:
        data_string += "{0!s}={1!s}&".format(key, r.get(key))
    data_string = data_string.strip("&")
    api_key_bin = base64.b64decode(api_key)
    # generate the signature
    h = hmac.new(api_key_bin, to_bytes(data_string), sha1).digest()
    h_b64 = b64encode_and_unicode(h)
    return h_b64


def yubico_check_api_signature(data, api_key, signature=None):
    """
    Verfiy the signature of the data.
    Either provide the signature as parameter or take it from the data

    :param data: The data to be signed
    :type data: dict
    :param api_key: base64 encoded API key
    :type api_key: basestring
    :param signature: the signature to be verified
    :type signature: base64 encoded string
    :return: base64 encoded signature
    """
    if not signature:
        signature = data.get('h')
    return signature == yubico_api_signature(data, api_key)


class YubikeyTokenClass(TokenClass):
    """
    The Yubikey Token in the Yubico AES mode
    """

    def __init__(self, db_token):
        TokenClass.__init__(self, db_token)
        self.set_type(u"yubikey")
        self.hKeyRequired = True


    @staticmethod
    def get_class_type():
        return "yubikey"

    @staticmethod
    def get_class_prefix():
        return "UBAM"

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
        """
        returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string

        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype: s.o.

        """
        res = {'type': 'yubikey',
               'title': 'Yubikey in AES mode',
               'description': _('Yubikey AES mode: One Time Passwords with '
                                'Yubikey.'),
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {}
        }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log)
    def check_otp_exist(self, otp, window=None):
        """
        checks if the given OTP value is/are values of this very token.
        This is used to autoassign and to determine the serial number of
        a token.
        """
        if window is None:
            window = self.get_otp_count_window()
        counter = self.get_otp_count()

        res = self.check_otp(otp, counter=counter, window=window, options=None)

        if res >= 0:
            # As usually the counter is increased in lib.token.checkUserPass, we
            # need to do this manually here:
            self.inc_otp_counter(res)

        return res

    @log_with(log)
    @challenge_response_allowed
    def is_challenge_request(self, passw, user=None, options=None):
        """
        This method checks, if this is a request, that triggers a challenge.

        :param passw: password, which might be pin or pin+otp
        :type passw: string
        :param user: The user from the authentication request
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict

        :return: true or false
        """
        trigger_challenge = False
        options = options or {}
        pin_match = self.check_pin(passw, user=user, options=options)
        if pin_match is True:
            trigger_challenge = True

        return trigger_challenge


    @log_with(log)
    @check_token_locked
    def check_otp(self, anOtpVal, counter=None, window=None, options=None):
        """
        validate the token otp against a given otpvalue

        :param anOtpVal: the to be verified otpvalue
        :type anOtpVal:  string

        :param counter: the counter state. It is not used by the Yubikey
            because the current counter value is sent encrypted inside the
            OTP value
        :type counter: int

        :param window: the counter +window, which is not used in the Yubikey
            because the current counter value is sent encrypted inside the
            OTP, allowing a simple comparison between the encrypted counter
            value and the stored counter value
        :type window: int

        :param options: the dict, which could contain token specific info
        :type options: dict

        :return: the counter state or an error code (< 0):
        -1 if the OTP is old (counter < stored counter)
        -2 if the private_uid sent in the OTP is wrong (different from the one stored with the token)
        -3 if the CRC verification fails
        :rtype: int

        """
        res = -1

        serial = self.token.serial
        secret = self.token.get_otpkey()

        # The prefix is the characters in front of the last 32 chars
        yubi_prefix = anOtpVal[:-32]
        # The variable otp val is the last 32 chars
        yubi_otp = anOtpVal[-32:]

        try:
            otp_bin = modhex_decode(yubi_otp)
        except KeyError:
            # The OTP value is no yubikey aes otp value and can not be decoded
            return -4

        msg_bin = secret.aes_ecb_decrypt(otp_bin)
        msg_hex = hexlify_and_unicode(msg_bin)

        # The checksum is a CRC-16 (16-bit ISO 13239 1st complement) that
        # occupies the last 2 bytes of the decrypted OTP value. Calculating the
        # CRC-16 checksum of the whole decrypted OTP should give a fixed
        # residual
        # of 0xf0b8 (see Yubikey-Manual - Chapter 6: Implementation details).
        crc16 = checksum(msg_bin)
        log.debug("calculated checksum (61624): {0!r}".format(crc16))
        if crc16 != 0xf0b8:  # pragma: no cover
            log.warning("CRC checksum for token {0!r} failed".format(serial))
            return -3

        uid = msg_hex[0:12]
        log.debug("uid: {0!r}".format(uid))
        log.debug("prefix: {0!r}".format(binascii.hexlify(modhex_decode(yubi_prefix))))
        # usage_counter can go from 1 – 0x7fff
        usage_counter = msg_hex[12:16]
        timestamp = msg_hex[16:22]
        # session counter can go from 00 to 0xff
        session_counter = msg_hex[22:24]
        random = msg_hex[24:28]
        crc = msg_hex[28:]
        log.debug("decrypted: usage_count: {0!r}, session_count: {1!r}".format(usage_counter, session_counter))

        # create the counter as integer
        # Note: The usage counter is stored LSB!

        count_hex = usage_counter[2:4] + usage_counter[0:2] + session_counter
        count_int = int(count_hex, 16)
        log.debug('decrypted counter: {0!r}'.format(count_int))

        tokenid = self.get_tokeninfo("yubikey.tokenid")
        if not tokenid:
            log.debug("Got no tokenid for {0!r}. Setting to {1!r}.".format(serial, uid))
            tokenid = uid
            self.add_tokeninfo("yubikey.tokenid", tokenid)

        prefix = self.get_tokeninfo("yubikey.prefix")
        if not prefix:
            log.debug("Got no prefix for {0!r}. Setting to {1!r}.".format(serial, yubi_prefix))
            self.add_tokeninfo("yubikey.prefix", yubi_prefix)

        if tokenid != uid:
            # wrong token!
            log.warning("The wrong token was presented for %r. "
                        "Got %r, expected %r."
                        % (serial, uid, tokenid))
            return -2

        # TODO: We also could check the timestamp
        # see http://www.yubico.com/wp-content/uploads/2013/04/YubiKey-Manual-v3_1.pdf
        log.debug('compare counter to database counter: {0!r}'.format(self.token.count))
        if count_int >= self.token.count:
            res = count_int
            # on success we save the used counter
            self.inc_otp_counter(res)

        return res

    @staticmethod
    def _get_api_key(api_id):
        """
        Return the symmetric key for the given apiId.

        :param api_id: The base64 encoded API ID
        :return: the base64 encoded API Key or None
        """
        api_key = get_from_config("yubikey.apiid.{0!s}".format(api_id))
        return api_key

    @classmethod
    def api_endpoint(cls, request, g):
        """
        This provides a function to be plugged into the API endpoint
        /ttype/yubikey which is defined in api/ttype.py

        The endpoint /ttype/yubikey is used for the Yubico validate request
        according to
        https://developers.yubico.com/yubikey-val/Validation_Protocol_V2.0.html

        :param request: The Flask request
        :param g: The Flask global object g
        :return: Flask Response or text

        Required query parameters

        :query id: The id of the client to identify the correct shared secret
        :query otp: The OTP from the yubikey in the yubikey mode
        :query nonce: 16-40 bytes of random data

        Optional parameters h, timestamp, sl, timeout are not supported at the
        moment.
        """
        id = getParam(request.all_data, "id")
        otp = getParam(request.all_data, "otp")
        nonce = getParam(request.all_data, "nonce")
        signature = getParam(request.all_data, "h")
        status = "MISSING_PARAMETER"

        timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ%f")
        data = {'otp': otp,
                'nonce': nonce,
                'status': status,
                'timestamp': timestamp}

        api_key = cls._get_api_key(id)
        if api_key is None:
            data['status'] = "NO_SUCH_CLIENT"
            data['h'] = ""
        elif otp and id and nonce:
            if signature and not yubico_check_api_signature(request.all_data,
                                                            api_key, signature):
                # yubico server don't send nonce and otp back. Do we want that?
                data['status'] = "BAD_SIGNATURE"
            else:
                res, opt = cls.check_yubikey_pass(otp)
                if res:
                    data['status'] = "OK"
                else:
                    # Do we want REPLAYED_OTP too?
                    data['status'] = "BAD_OTP"

            data["h"] = yubico_api_signature(data, api_key)
        response = """nonce={nonce}
otp={otp}
status={status}
timestamp={timestamp}
h={h}
""".format(**data)

        return "plain", response

    @staticmethod
    def check_yubikey_pass(passw):
        """
        if the Token has set a PIN the user must also enter the PIN for
        authentication!

        This checks the output of a yubikey in AES mode without providing
        the serial number.
        The first 12 (of 44) or 16 of 48) characters are the tokenid, which is
        stored in the tokeninfo yubikey.tokenid or the prefix yubikey.prefix.

        :param passw: The password that consist of the static yubikey prefix and
            the otp
        :type passw: string

        :return: True/False and the User-Object of the token owner
        :rtype: dict
        """
        opt = {}
        res = False

        token_list = []

        # strip the yubico OTP and the PIN
        prefix = passw[:-32][-16:]

        from privacyidea.lib.token import get_tokens
        from privacyidea.lib.token import check_token_list

        # See if the prefix matches the serial number
        if prefix[:2] != "vv" and prefix[:2] != "cc":
            try:
                # Keep the backward compatibility
                serialnum = "UBAM" + modhex_decode(prefix)
                for i in range(1, 3):
                    s = "{0!s}_{1!s}".format(serialnum, i)
                    toks = get_tokens(serial=s, tokentype='yubikey')
                    token_list.extend(toks)
            except TypeError as exx:  # pragma: no cover
                log.error("Failed to convert serialnumber: {0!r}".format(exx))

        # Now, we see, if the prefix matches the new version
        if not token_list:
            # If we did not find the token via the serial number, we also
            # search for the yubikey.prefix in the tokeninfo.
            token_candidate_list = get_tokens(tokentype='yubikey',
                                              tokeninfo={"yubikey.prefix":
                                                             prefix})
            token_list.extend(token_candidate_list)

        if not token_list:
            opt['action_detail'] = ("The prefix {0!s} could not be found!".format(
                                    prefix))
            return res, opt

        (res, opt) = check_token_list(token_list, passw, allow_reset_all_tokens=True)
        return res, opt

    @log_with(log)
    def update(self, param, reset_failcount=True):
        TokenClass.update(self, param, reset_failcount)
        self.add_tokeninfo("tokenkind", TOKENKIND.HARDWARE)