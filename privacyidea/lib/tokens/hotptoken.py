# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License: AGPLv3
#  contact: http://www.privacyidea.org
#
#  2022-02-03 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add verified enrollment
#  2018-06-06 Michael Becker <michael.becker@hs-niederrhein.de>
#             Add get_setting_type to make hotp.hashlib public and
#             therefore recognised in token enrollment with role user.
#  2018-01-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Set Yubikeys to be hardware tokenkind
#  2017-07-13 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add period to key uri for TOTP token
#
#  2016-04-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add get_default_settings to change the parameters before
#             the token is created
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
import binascii

from .HMAC import HmacOtp
from privacyidea.api.lib.utils import getParam
from privacyidea.api.lib.policyhelper import get_init_tokenlabel_parameters
from privacyidea.lib.config import get_from_config
from privacyidea.lib.tokenclass import (TokenClass,
                                        TWOSTEP_DEFAULT_DIFFICULTY,
                                        TWOSTEP_DEFAULT_CLIENTSIZE,
                                        TOKENKIND, ROLLOUTSTATE)
from privacyidea.lib.log import log_with
from privacyidea.lib.apps import create_google_authenticator_url as cr_google
from privacyidea.lib.error import ParameterError
from privacyidea.lib.apps import create_oathtoken_url as cr_oath
from privacyidea.lib.utils import (create_img, is_true, b32encode_and_unicode,
                                   hexlify_and_unicode, determine_logged_in_userparams)
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.policy import SCOPE, ACTION, GROUP, Match
from privacyidea.lib.token import init_token
from privacyidea.lib.tokenclass import CLIENTMODE
from privacyidea.lib import _
import traceback
import logging

from passlib.crypto.digest import pbkdf2_hmac

optional = True
required = False
log = logging.getLogger(__name__)

keylen = {'sha1': 20,
          'sha256': 32,
          'sha512': 64
          }

VERIFY_ENROLLMENT_MESSAGE = _("Please enter a valid OTP value of the new token.")


class HotpTokenClass(TokenClass):
    """
    hotp token class implementation
    """

    previous_otp_offset = 1

    # The HOTP token provides means to verify the enrollment
    can_verify_enrollment = True
    # If the token is enrollable via multichallenge
    is_multichallenge_enrollable = True

    desc_hash_func = _('Specify the hashing function to be used. '
                       'Can be SHA1, SHA256 or SHA512.')
    desc_otp_len = _('Specify the OTP length to be used. Can be 6 or 8 digits.')
    desc_key_gen = _("Force the key to be generated on the server.")
    desc_two_step_user = _('Specify whether users are allowed or forced to use '
                           'two-step enrollment.')
    desc_two_step_admin = _('Specify whether admins are allowed or forced to '
                            'use two-step enrollment.')

    @staticmethod
    def get_class_type():
        """
        return the token type shortname

        :return: 'hotp'
        :rtype: string
        """
        return "hotp"

    @staticmethod
    def get_class_prefix():
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: oath
        """
        return "OATH"

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
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
        res = {'type': 'hotp',
               'title': 'HOTP Event Token',
               'description': _('HOTP: Event based One Time Passwords.'),
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of HOTP tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of active HOTP tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       'hotp_2step_clientsize': {
                           'type': 'int',
                           'desc': _("The size of the OTP seed part contributed "
                                     "by the client (in bytes)")
                       },
                       'hotp_2step_serversize': {
                           'type': 'int',
                           'desc': _("The size of the OTP seed part contributed "
                                     "by the server (in bytes)")
                       },
                       'hotp_2step_difficulty': {
                           'type': 'int',
                           'desc': _("The difficulty factor used for the OTP "
                                     "seed generation (should be at least 10000)")
                       },
                       'hotp_' + ACTION.FORCE_APP_PIN: {
                           'type': 'bool',
                           'desc': _('Enforce setting an app pin for the privacyIDEA '
                                     'Authenticator App')
                       }
                   },
                   SCOPE.USER: {
                       'hotp_hashlib': {'type': 'str',
                                        'value': ["sha1",
                                                  "sha256",
                                                  "sha512"],
                                        'desc': HotpTokenClass.desc_hash_func},
                       'hotp_otplen': {'type': 'int',
                                       'value': [6, 8],
                                       'desc': HotpTokenClass.desc_otp_len},
                       'hotp_force_server_generate': {
                           'type': 'bool',
                           'desc': HotpTokenClass.desc_key_gen},
                       'hotp_2step': {'type': 'str',
                                      'value': ['allow', 'force'],
                                      'desc': HotpTokenClass.desc_two_step_user}
                   },
                   SCOPE.ADMIN: {
                       'hotp_hashlib': {'type': 'str',
                                        'value': ["sha1",
                                                  "sha256",
                                                  "sha512"],
                                        'desc': HotpTokenClass.desc_hash_func},
                       'hotp_otplen': {'type': 'int',
                                       'value': [6, 8],
                                       'desc': HotpTokenClass.desc_otp_len},
                       'hotp_2step': {'type': 'str',
                                      'value': ['allow', 'force'],
                                      'desc': HotpTokenClass.desc_two_step_admin}
                   }
               }
               }

        if key:
            ret = res.get(key, {})
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
        self.set_type("hotp")
        self.hKeyRequired = True
        self.currently_in_challenge = False

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
        tokenissuer = params.get("tokenissuer", "privacyIDEA")
        # If the init_details contain an OTP key the OTP key
        # should be displayed as an enrollment URL
        otpkey = self.init_details.get('otpkey')
        # Add rollout state the response
        response_detail['rollout_state'] = self.token.rollout_state
        # Add two-step initialization parameters to response and QR code
        extra_data = {}
        if is_true(params.get("2stepinit")):
            twostep_parameters = self._get_twostep_parameters()
            extra_data.update(twostep_parameters)
            response_detail.update(twostep_parameters)
        imageurl = params.get("appimageurl")
        if imageurl:
            extra_data.update({"image": imageurl})
        force_app_pin = params.get(ACTION.FORCE_APP_PIN)
        if force_app_pin:
            extra_data.update({'pin': True})
        if otpkey:
            tok_type = self.type.lower()
            if user is not None:                               
                try:
                    key_bin = binascii.unhexlify(otpkey)
                    # also strip the padding =, as it will get problems with the google app.
                    value_b32_str = b32encode_and_unicode(key_bin).strip('=')
                    response_detail["otpkey"]["value_b32"] = value_b32_str
                    goo_url = cr_google(key=otpkey,
                                        user=user.login,
                                        realm=user.realm,
                                        tokentype=tok_type.lower(),
                                        serial=self.get_serial(),
                                        tokenlabel=tokenlabel,
                                        hash_algo=params.get("hashlib", "sha1"),
                                        digits=params.get("otplen", 6),
                                        period=params.get("timeStep", 30),
                                        issuer=tokenissuer,
                                        user_obj=user,
                                        extra_data=extra_data)
                    response_detail["googleurl"] = {"description":
                                                    _("URL for google "
                                                      "Authenticator"),
                                                    "value": goo_url,
                                                    "img": create_img(goo_url)
                                                    }

                    oath_url = cr_oath(otpkey=otpkey,
                                       user=user.login,
                                       realm=user.realm,
                                       type=tok_type,
                                       serial=self.get_serial(),
                                       tokenlabel=tokenlabel,
                                       extra_data=extra_data)
                    response_detail["oathurl"] = {"description": _("URL for"
                                                                   " OATH "
                                                                   "token"),
                                                  "value": oath_url,
                                                  "img": create_img(oath_url)
                                                  }
                except Exception as ex:  # pragma: no cover
                    log.error("{0!s}".format((traceback.format_exc())))
                    log.error('failed to set oath or google url: {0!r}'.format(ex))

        return response_detail

    def _get_twostep_parameters(self):
        """
        :return: A dictionary with the keys ``2step_salt``,
        ``2step_difficulty``, ``2step_output``, mapping each key to an integer.
        """
        return {'2step_salt': int(self.get_tokeninfo('2step_clientsize')),
                '2step_output': int(keylen[self.hashlib]),
                '2step_difficulty': int(self.get_tokeninfo('2step_difficulty'))}

    @log_with(log)
    def update(self, param, reset_failcount=True):
        """
        process the initialization parameters

        Do we really always need an otpkey?
        the otpKey is handled in the parent class
        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing
        """
        # In case am Immutable MultiDict:
        upd_param = {}
        for k, v in param.items():
            upd_param[k] = v

        # Special handling of 2-step enrollment
        if is_true(getParam(param, "2stepinit", optional)):
            # Use the 2step_serversize setting for the size of the server secret
            # (if it is set)
            if "2step_serversize" in upd_param:
                upd_param["keysize"] = int(getParam(upd_param, "2step_serversize", required))
            # Add twostep settings to the tokeninfo
            for key, default in [
                ("2step_difficulty", TWOSTEP_DEFAULT_DIFFICULTY),
                ("2step_clientsize", TWOSTEP_DEFAULT_CLIENTSIZE)]:
                self.add_tokeninfo(key, getParam(param, key, optional, default))

        val = getParam(upd_param, "hashlib", optional)
        if val is not None:
            hashlibStr = val
        else:
            hashlibStr = self.hashlib

        # check if the key_size is provided
        # if not, we could derive it from the hashlib
        key_size = getParam(upd_param, 'key_size', optional) \
                   or getParam(upd_param, 'keysize', optional)
        if key_size is None:
            upd_param['keysize'] = keylen.get(hashlibStr)

        otpKey = getParam(upd_param, "otpkey", optional)
        genkey = is_true(getParam(upd_param, "genkey", optional))
        if genkey and otpKey:
            # The Base TokenClass does not allow otpkey and genkey at the
            # same time
            del upd_param['otpkey']
        upd_param['hashlib'] = hashlibStr
        # We first need to call the parent class. Since exceptions would be
        # raised here.
        TokenClass.update(self, upd_param, reset_failcount)

        self.add_tokeninfo("hashlib", hashlibStr)

        # check the tokenkind
        if self.token.serial.startswith("UB"):
            self.add_tokeninfo("tokenkind", TOKENKIND.HARDWARE)

    @property
    def hashlib(self):
        hashlibStr = self.get_tokeninfo("hashlib") or \
                     get_from_config("hotp.hashlib", 'sha1')
        return hashlibStr

    def _calc_otp(self, counter):
        """
        Helper function to calculate the OTP value for the given counter
        :param counter: The OTP counter
        :return: OTP value as string
        """
        otplen = int(self.token.otplen)
        secretHOtp = self.token.get_otpkey()
        hmac2Otp = HmacOtp(secretHOtp,
                           self.get_otp_count(),
                           otplen,
                           self.get_hashlib(self.hashlib))

        otpval = hmac2Otp.generate(counter=counter,
                                   inc_counter=False,
                                   do_truncation=True)
        return otpval

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

        if res == -1:
            res = self._autosync(hmac2Otp, anOtpVal)
        if res != -1:
            # on success, we save the counter
            self.set_otp_count(res + 1)
            # We could also store it temporarily
            # self.auth_details["matched_otp_counter"] = res

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
            msg = "otp counter {0!r} was not found".format(otp)
        else:
            msg = "otp counter {0!r} was found".format(otp)
        log.debug("end. {0!r}: res {1!r}".format(msg, res))
        return res

    @log_with(log)
    def is_previous_otp(self, otp):
        """
        Check if the OTP values was previously used.

        :param otp:
        :param window:
        :return:
        """
        counter = int(self.get_otp_count())
        if counter > 0:
            previous_otp = self._calc_otp(counter - self.previous_otp_offset)
            res = previous_otp == otp
            if res:
                log.info("Previous OTP used again. "
                         "Serial {0!s} with counter {1!s}.".format(self.token.serial, counter))
            return res
        else:
            # The internal counter is 0, the token was not used, yet.
            return False

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
        # get _autosync from config or use False as default
        autosync = get_from_config("AutoResync", False, return_bool=True)

        # if _autosync is not enabled
        if autosync is False:
            log.debug("end. _autosync is not enabled : res {0!r}".format((res)))
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
            log.debug("exit. First counter (-1) not found  ret: {0!r}".format((ret)))
            return ret

        nextOtp = hmac2Otp.generate(counter + 1)

        if nextOtp != otp2:
            log.debug("exit. Failed to verify second otp: nextOtp: "
                      "%r != otp2: %r ret: %r" % (nextOtp, otp2, ret))
            return ret

        ret = True
        self.inc_otp_counter(counter + 1, reset=True)

        log.debug("end. resync was successful: ret: {0!r}".format((ret)))
        return ret

    @staticmethod
    def get_sync_timeout():
        """
        get the token sync timeout value

        :return: timeout value in seconds
        :rtype:  int
        """
        try:
            timeOut = int(get_from_config("AutoResyncTimeout", 5 * 60))
        except Exception as ex:
            log.warning("AutoResyncTimeout: value error {0!r} - reset to 5*60".format((ex)))
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

        if get_from_config("PrependPin") == "True":
            combined = "{0!s}{1!s}".format(pin, otpval)
        else:
            combined = "{0!s}{1!s}".format(otpval, pin)

        return 1, pin, otpval, combined

    @log_with(log)
    def get_multi_otp(self, count=0, epoch_start=0, epoch_end=0,
                      curTime=None, timestamp=None,
                      counter_index=False):
        """
        return a dictionary of multiple future OTP values of the
        HOTP/HMAC token

        WARNING: the dict that is returned contains a sequence number as key.
                 This it NOT the otp counter!

        :param count: how many otp values should be returned
        :type count: int
        :param epoch_start: Not used in HOTP
        :param epoch_end: Not used in HOTP
        :param curTime: Not used in HOTP
        :param timestamp: not used in HOTP
        :param counter_index: whether the counter should be used as index
        :return: tuple of status: boolean, error: text and the OTP dictionary
        """
        otp_dict = {"type": "hotp", "otp": {}}
        ret = False
        error = "No count specified"
        otplen = int(self.token.otplen)

        secretHOtp = self.token.get_otpkey()
        hmac2Otp = HmacOtp(secretHOtp, self.token.count, otplen,
                           self.get_hashlib(self.hashlib))
        log.debug("retrieving {0:d} OTP values for token {1!s}".format(count, hmac2Otp))

        if count > 0:
            error = "OK"
            for i in range(count):
                otpval = hmac2Otp.generate(self.token.count + i,
                                           inc_counter=False)
                if counter_index:
                    otp_dict["otp"][self.token.count + i] = otpval
                else:
                    otp_dict["otp"][i] = otpval
            ret = True

        return ret, error, otp_dict

    @staticmethod
    def get_setting_type(key):
        settings = {"hotp.hashlib": "public"}
        return settings.get(key, "")

    @classmethod
    def get_default_settings(cls, g, params):
        """
        This method returns a dictionary with default settings for token
        enrollment.
        These default settings are defined in SCOPE.USER or SCOPE.ADMIN and are
        hotp_hashlib, hotp_otplen.
        If these are set, the user or admin will only be able to enroll tokens
        with these values.

        The returned dictionary is added to the parameters of the API call.
        :param g: context object, see documentation of ``Match``
        :param params: The call parameters
        :type params: dict
        :return: default parameters
        """
        ret = {}
        if not g.logged_in_user:
            return ret
        (role, username, userrealm, adminuser, adminrealm) = determine_logged_in_userparams(g.logged_in_user,
                                                                                            params)
        hashlib_pol = Match.generic(g, scope=role,
                                    action="hotp_hashlib",
                                    user=username,
                                    realm=userrealm,
                                    adminrealm=adminrealm,
                                    adminuser=adminuser).action_values(unique=True)
        if hashlib_pol:
            ret["hashlib"] = list(hashlib_pol)[0]

        otplen_pol = Match.generic(g, scope=role,
                                   action="hotp_otplen",
                                   user=username,
                                   realm=userrealm,
                                   adminrealm=adminrealm,
                                   adminuser=adminuser).action_values(unique=True)
        if otplen_pol:
            ret["otplen"] = list(otplen_pol)[0]

        return ret

    def generate_symmetric_key(self, server_component, client_component,
                               options=None):
        """
        Generate a composite key from a server and client component
        using a PBKDF2-based scheme.

        :param server_component: The component usually generated by privacyIDEA
        :type server_component: hex string
        :param client_component: The component usually generated by the
            client (e.g. smartphone)
        :type client_component: hex string
        :param options:
        :return: the new generated key as hex string
        :rtype: str
        """
        # As /token/init has already been called before, self.hashlib
        # is already set.
        keysize = keylen[self.hashlib]
        rounds = int(self.get_tokeninfo('2step_difficulty'))
        decoded_client_component = binascii.unhexlify(client_component)
        expected_client_size = int(self.get_tokeninfo('2step_clientsize'))
        if expected_client_size != len(decoded_client_component):
            raise ParameterError('Client Secret Size is expected to be {}, but is {}'.format(
                expected_client_size, len(decoded_client_component)
            ))
        # Based on the two components, we generate a symmetric key using PBKDF2
        # We pass the hex-encoded server component as the password and the
        # client component as the salt.
        secret = pbkdf2_hmac(digest='sha1',
                             secret=server_component.lower(),
                             salt=decoded_client_component,
                             rounds=rounds,
                             keylen=keysize)
        return hexlify_and_unicode(secret)

    @staticmethod
    def get_import_csv(l):
        """
        Read the list from a csv file and return a dictionary, that can be used
        to do a token_init.

        :param l: The list of the line of a csv file
        :type l: list
        :return: A dictionary of init params
        """
        params = TokenClass.get_import_csv(l)
        # get Counter
        if len(l) >= 5:
            params["counter"] = int(l[4].strip())
        return params

    def prepare_verify_enrollment(self):
        """
        This is called, if the token should be enrolled in a way, that the user
        needs to provide a proof, that the server can verify, that the token
        was successfully enrolled. E.g. with HOTP tokens the user might need to provide
        a correct OTP value.

        The returned dictionary is added to the response in "detail" -> "verify".

        :return: A dictionary with information that is needed to trigger the verification.
        """
        return {"message": VERIFY_ENROLLMENT_MESSAGE}

    def verify_enrollment(self, verify):
        """
        This is called during the 2nd step of the verified enrollment.
        This method verifies the actual response from the user.
        Returns true, if the verification was successful.

        :param verify: The response given by the user
        :return: True
        """
        r = self.check_otp(verify)
        log.debug("Enrollment verified: {0!s}".format(r))
        return r >= 0

    @classmethod
    def enroll_via_validate(cls, g, content, user_obj):
        """
        This class method is used in the policy ENROLL_VIA_MULTICHALLENGE.
        It enrolls a new token of this type and returns the necessary information
        to the client by modifying the content.

        :param g: context object
        :param content: The content of a response
        :param user_obj: A user object
        :return: None, the content is modified
        """
        message = _("Please scan the QR code!")
        token_obj = init_token({"type": cls.get_class_type(),
                                "genkey": 1}, user=user_obj)
        content.get("result")["value"] = False
        content.get("result")["authentication"] = "CHALLENGE"

        detail = content.setdefault("detail", {})
        # Create a challenge!
        c = token_obj.create_challenge()
        # get details of token
        enroll_params = get_init_tokenlabel_parameters(g, user_object=user_obj,
                                                       token_type=cls.get_class_type())
        init_details = token_obj.get_init_detail(params=enroll_params,
                                                 user=user_obj)
        detail["transaction_ids"] = [c[2]]
        detail["messages"] = [ message ]
        chal = {"transaction_id": c[2],
                "image": init_details.get("googleurl").get("img"),
                "client_mode": CLIENTMODE.INTERACTIVE,
                "serial": token_obj.token.serial,
                "type": token_obj.type,
                "message": message}
        detail["multi_challenge"] = [chal]
        detail.update(chal)

    def has_further_challenge(self, options=None):
        """

        :param options:
        :return:
        """
        try:
            return self.currently_in_challenge
        except AttributeError:
            # Certain from HOTP inherited tokenclasses might not set currently_in_challenge
            return False
