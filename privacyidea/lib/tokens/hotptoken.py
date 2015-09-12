# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License: AGPLv3
#  contact: http://www.privacyidea.org
#
#  2014-10-03 Add getInitDetail
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
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
This is the HOTP implementation.
It is inherited from lib.tokenclass and is thus dependent on models.py

This code is tested in tests/test_lib_tokens_hotp
"""

import time
from .HMAC import HmacOtp
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.config import get_from_config
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.apps import create_google_authenticator_url as cr_google
from privacyidea.lib.apps import create_oathtoken_url as cr_oath
from privacyidea.lib.utils import create_img
from privacyidea.lib.utils import generate_otpkey
from privacyidea.lib.policydecorators import challenge_response_allowed
from privacyidea.lib.decorators import check_token_locked
import gettext
import traceback
import logging

optional = True
required = False
_ = gettext.gettext
log = logging.getLogger(__name__)

keylen = {'sha1': 20,
          'sha256': 32,
          'sha512': 64
          }


class HotpTokenClass(TokenClass):
    """
    hotp token class implementation
    """

    @classmethod
    def get_class_type(cls):
        """
        return the token type shortname

        :return: 'hotp'
        :rtype: string
        """
        return "hotp"

    @classmethod
    def get_class_prefix(cls):
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: oath
        """
        return "OATH"

    @classmethod
    @log_with(log)
    def get_class_info(cls, key=None, ret='all'):
        """
        returns a subtree of the token definition
        Is used by lib.token.get_token_info

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict
        """
        desc_self1 = _('Specify the hashlib to be used. '
                       'Can be sha1 (1) or sha2-256 (2).')
        desc_self2 = _('Specify the otplen to be used. Can be 6 or 8 digits.')
        res = {'type': 'hotp',
               'title': 'HOTP Event Token',
               'description': ('HOTP: Event based One Time Passwords.'),
               'init': {'page': {'html': 'hotptoken.mako',
                                 'scope': 'enroll', },
                        'title': {'html': 'hotptoken.mako',
                                  'scope': 'enroll.title', },
                        },
               'config': {'page': {'html': 'hotptoken.mako',
                                   'scope': 'config', },
                          'title': {'html': 'hotptoken.mako',
                                    'scope': 'config.title', },
                          },
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {'user': {'hotp_hashlib': {'type': 'int',
                                                           'value': ["sha1",
                                                                     "sha256",
                                                                     "sha512"],
                                                           'desc': desc_self1
                                                           },
                                          'hotp_otplen': {'type': 'int',
                                                          'value': [6, 8],
                                                          'desc': desc_self2
                                                          },
                                          }
                          }
               }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new HOTP Token object

        :param db_token: instance of the orm db object
        :type db_token: DB object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"hotp")
        self.hKeyRequired = True

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        to complete the token initialization some additional details
        should be returned, which are displayed at the end of
        the token initialization.
        This is the e.g. the enrollment URL for a Google Authenticator.
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        params = params or {}
        tokenlabel = params.get("tokenlabel", "<s>")
        # If the init_details contain an OTP key the OTP key
        # should be displayed as an enrollment URL
        otpkey = self.init_details.get('otpkey')
        if otpkey:
            tok_type = self.type.lower()
            if user is not None:
                try:
                    goo_url = cr_google(key=otpkey,
                                        user=user.login,
                                        realm=user.realm,
                                        tokentype=tok_type.lower(),
                                        serial=self.get_serial(),
                                        tokenlabel=tokenlabel,
                                        hash_algo=params.get("hashlib",
                                                             "sha1"),
                                        digits=params.get("otplen", 6))
                    response_detail["googleurl"] = {"description":
                                                    _("URL for google "
                                                      "Authenticator"),
                                                    "value": goo_url,
                                                    "img": create_img(goo_url,
                                                                      width=250)
                                                    }

                    oath_url = cr_oath(otpkey=otpkey,
                                       user=user.login,
                                       realm=user.realm,
                                       type=tok_type,
                                       serial=self.get_serial(),
                                       tokenlabel=tokenlabel)
                    response_detail["oathurl"] = {"description": _("URL for"
                                                                   " OATH "
                                                                   "token"),
                                                  "value": oath_url,
                                                  "img": create_img(oath_url,
                                                                    width=250)
                                                  }
                except Exception as ex:  # pragma: no cover
                    log.error("%r" % (traceback.format_exc()))
                    log.error('failed to set oath or google url: %r' % ex)
                    
        return response_detail

    @log_with(log)
    def update(self, param, reset_failcount=True):
        """
        process the initialization parameters

        Do we really always need an otpkey?
        ...the otpKey is handled in the parent class
        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing
        """
        # In case am Immutable MultiDict:
        upd_param = {}
        for k, v in param.items():
            upd_param[k] = v

        val = getParam(upd_param, "hashlib", optional)
        if val is not None:
            hashlibStr = val
        else:
            hashlibStr = 'sha1'

        # check if the key_size id provided
        # if not, we could derive it from the hashlib
        key_size = getParam(upd_param, 'key_size', optional)
        if key_size is None:
            upd_param['key_size'] = keylen.get(hashlibStr)
        otpKey = ''
        if self.hKeyRequired is True:
            genkey = int(getParam(upd_param, "genkey", optional) or 0)
            if 1 == genkey:
                # if hashlibStr not in keylen dict, this will
                # raise an Exception
                otpKey = generate_otpkey(upd_param['key_size'])
                del upd_param['genkey']
            else:
                # genkey not set: check otpkey is given
                # this will raise an exception if otpkey is not present
                otpKey = getParam(upd_param, "otpkey", required)
                # finally set the values for the update
            upd_param['otpkey'] = otpKey
        upd_param['hashlib'] = hashlibStr
        self.add_tokeninfo("hashlib", hashlibStr)
        val = getParam(upd_param, "otplen", optional)
        if val is not None:
            self.set_otplen(int(val))
        else:
            self.set_otplen(get_from_config("DefaultOtpLen", 6))

        TokenClass.update(self, upd_param, reset_failcount)

    @property
    def hashlib(self):
        hashlibStr = self.get_tokeninfo("hashlib") or \
                     get_from_config("hotp.hashlib", u'sha1')
        return hashlibStr

    # challenge interfaces starts here
    @log_with(log)
    @challenge_response_allowed
    def is_challenge_request(self, passw, user=None, options=None):
        """
        check, if the request would start a challenge

        - default: if the passw contains only the pin, this request would
        trigger a challenge

        - in this place as well the policy for a token is checked

        :param passw: password, which might be pin or pin+otp
        :param options: dictionary of additional request parameters

        :return: returns true or false
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
        check if the given OTP value is valid for this token.

        :param anOtpVal: the to be verified otpvalue
        :type anOtpVal: string
        :param counter: the counter state, that should be verified
        :type counter: int
        :param window: the counter +window, which should be checked
        :type window: int
        :param options: the dict, which could contain token specific info
        :type options: dict
        :return: the counter state or -1
        :rtype: int
        """
        otplen = int(self.token.otplen)
        secretHOtp = self.token.get_otpkey()

        if counter is None:
            counter = int(self.get_otp_count())
        if window is None:
            window = int(self.get_count_window())
        hmac2Otp = HmacOtp(secretHOtp,
                           counter,
                           otplen,
                           self.get_hashlib(self.hashlib))
        res = hmac2Otp.checkOtp(anOtpVal, window)

        if -1 == res:
            res = self._autosync(hmac2Otp, anOtpVal)
        else:
            # on success, we save the counter
            self.set_otp_count(res + 1)
            # We could also store it temporarily
            # self.auth_details["matched_otp_counter"] = res
            # and we reset the fail counter
            self.reset()

        return res

    @log_with(log)
    def check_otp_exist(self, otp, window=10, symetric=False, inc_counter=True):
        """
        checks if the given OTP value is/are values of this very token.
        This is used to autoassign and to determine the serial number of
        a token.

        :param otp: the to be verified otp value
        :type otp: string

        :param window: the lookahead window for the counter
        :type window: int

        :return: counter or -1 if otp does not exist
        :rtype:  int
        """
        res = -1
        otplen = int(self.token.otplen)
        counter = int(self.token.count)

        secretHOtp = self.token.get_otpkey()
        hmac2Otp = HmacOtp(secretHOtp, counter, otplen,
                           self.get_hashlib(self.hashlib))
        res = hmac2Otp.checkOtp(otp, window, symetric=symetric)

        if inc_counter and res >= 0:
            # As usually the counter is increased in lib.token.checkUserPass,
            # we need to do this manually here:
            self.inc_otp_counter(res)
        if res == -1:
            msg = "otp counter %r was not found" % otp
        else:
            msg = "otp counter %r was found" % otp
        log.debug("end. %r: res %r" % (msg, res))
        return res

    @log_with(log)
    def is_previous_otp(self, otp, window=10):
        """
        Check if the OTP values was previously used.

        :param otp:
        :param window:
        :return:
        """
        res = False
        r = self.check_otp_exist(otp, window=window, symetric=True,
                                 inc_counter=False)
        if 0 <= r < self.token.count:
            res = True
        return res

    @log_with(log)
    def _autosync(self, hmac2Otp, anOtpVal):
        """
        automatically sync the token based on two otp values
        internal method to implement the _autosync within the
        checkOtp method.

        :param hmac2Otp: the hmac object (with reference to the token secret)
        :type hmac2Otp: hmac object

        :param anOtpVal: the actual otp value
        :type anOtpVal: string

        :return: counter or -1 if otp does not exist
        :rtype:  int
        """
        res = -1
        autosync = False

        # get _autosync from config or use False as default
        async = get_from_config("AutoResync", False)
        # The SQLite database returns AutoResync as a boolean and not as a
        # string. So the boolean has no .lower()
        if isinstance(async, bool):
            autosync = async
        elif async.lower() == "true":
            autosync = True

        # if _autosync is not enabled
        if autosync is False:
            log.debug("end. _autosync is not enabled : res %r" % (res))
            return res

        info = self.get_tokeninfo()
        syncWindow = self.get_sync_window()

        # check if the otpval is valid in the sync scope
        res = hmac2Otp.checkOtp(anOtpVal, syncWindow)

        # If the otpval is valid in the big sync scope, we
        # either store the value in the tokeninfo
        # or see if already another value exists.
        if res != -1:
            # if former is defined
            if "otp1c" in info:
                # check if this is consecutive
                otp1c = int(info.get("otp1c"))
                otp2c = res

                if (otp1c + 1) != otp2c:
                    res = -1

                if "dueDate" in info:
                    dueDate = int(info.get("dueDate"))
                    now = int(time.time())
                    if dueDate <= now:
                        res = -1
                else:
                    # if by any reason the dueDate is missing!
                    res = -1  # pragma: no cover

                # now clean the resync data
                self.del_tokeninfo("dueDate")
                self.del_tokeninfo("otp1c")

            else:
                self.add_tokeninfo("otp1c", res)
                self.add_tokeninfo("dueDate", int(time.time()) +
                                   self.get_sync_timeout())

                res = -1

        return res

    @log_with(log)
    def resync(self, otp1, otp2, options=None):
        """
        resync the token based on two otp values

        :param otp1: the first otp value
        :type otp1: string

        :param otp2: the second otp value
        :type otp2: string

        :param options: optional token specific parameters
        :type options:  dict or None

        :return: counter or -1 if otp does not exist
        :rtype:  int
        """
        ret = False
        otplen = int(self.token.otplen)
        secretHOtp = self.token.get_otpkey()
        counter = self.token.count
        syncWindow = self.get_sync_window()
        # log.debug("serial: %s",serialNum)
        hmac2Otp = HmacOtp(secretHOtp, counter, otplen,
                           self.get_hashlib(self.hashlib))
        counter = hmac2Otp.checkOtp(otp1, syncWindow)

        if counter == -1:
            log.debug("exit. First counter (-1) not found  ret: %r" % (ret))
            return ret

        nextOtp = hmac2Otp.generate(counter + 1)

        if nextOtp != otp2:
            log.debug("exit. Failed to verify second otp: nextOtp: "
                      "%r != otp2: %r ret: %r" % (nextOtp, otp2, ret))
            return ret

        ret = True
        self.inc_otp_counter(counter + 1, True)

        log.debug("end. resync was successful: ret: %r" % (ret))
        return ret

    def get_sync_timeout(self):
        """
        get the token sync timeout value

        :return: timeout value in seconds
        :rtype:  int
        """
        try:
            timeOut = int(get_from_config("AutoResyncTimeout", 5 * 60))
        except Exception as ex:
            log.warning("AutoResyncTimeout: value error %r - reset to 5*60"
                        % (ex))
            timeOut = 5 * 60

        return timeOut

    @log_with(log)
    def get_otp(self, current_time=None):
        """
        return the next otp value

        :param curTime: Not Used in HOTP
        :return: next otp value and PIN if possible
        :rtype: tuple
        """
        otplen = int(self.token.otplen)
        secretHOtp = self.token.get_otpkey()

        hmac2Otp = HmacOtp(secretHOtp,
                           self.token.count,
                           otplen,
                           self.get_hashlib(self.hashlib))
        otpval = hmac2Otp.generate(inc_counter=False)

        pin = self.token.get_pin()
        combined = "%s%s" % (otpval, pin)

        if get_from_config("PrependPin") == "True":
            combined = "%s%s" % (pin, otpval)

        return 1, pin, otpval, combined

    @log_with(log)
    def get_multi_otp(self, count=0, epoch_start=0, epoch_end=0,
                        curTime=None, timestamp=None):
        """
        return a dictionary of multiple future OTP values of the
        HOTP/HMAC token

        WARNING: the dict that is returned contains a sequence number as key.
                 This it NOT the otp counter!

        :param count: how many otp values should be returned
        :type count: int
        :epoch_start: Not used in HOTP
        :epoch_end: Not used in HOTP
        :curTime: Not used in HOTP
        :timestamp: not used in HOTP
        :return: tuple of status: boolean, error: text and the OTP dictionary
        """
        otp_dict = {"type": "hotp", "otp": {}}
        ret = False
        error = "No count specified"
        otplen = int(self.token.otplen)

        secretHOtp = self.token.get_otpkey()
        hmac2Otp = HmacOtp(secretHOtp, self.token.count, otplen,
                           self.get_hashlib(self.hashlib))
        log.debug("retrieving %i OTP values for token %s" % (count, hmac2Otp))

        if count > 0:
            error = "OK"
            for i in range(count):
                otpval = hmac2Otp.generate(self.token.count + i,
                                           inc_counter=False)
                otp_dict["otp"][i] = otpval
            ret = True

        return ret, error, otp_dict
