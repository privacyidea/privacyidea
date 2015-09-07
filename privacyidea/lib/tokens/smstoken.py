# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2015-05-24   Add more detailed description
#               Cornelius Kölbel <cornelius.koelbel@netknights.it>
#  2015-01-30   Adapt for migration to flask
#               Cornelius Kölbel <cornelius@privacyidea.org>
#
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
__doc__ = """The SMS token sends an SMS containing an OTP via some kind of
gateway. The gateways can be an SMTP or HTTP gateway or the special sipgate
protocol.
The Gateways are defined in the SMSProvider Modules.

This code is tested in tests/test_lib_tokens_sms
"""

import datetime
import traceback

from privacyidea.api.lib.utils import getParam
from privacyidea.api.lib.utils import required

from privacyidea.lib.config import get_from_config
from privacyidea.lib.policy import SCOPE
from privacyidea.lib.log import log_with
from privacyidea.lib.smsprovider.SMSProvider import get_sms_provider_class
from json import loads
from gettext import gettext as _

from privacyidea.lib.tokens.hotptoken import HotpTokenClass
from privacyidea.models import Challenge
from privacyidea.lib.decorators import check_token_locked


import logging
from privacyidea.lib.policydecorators import challenge_response_allowed
log = logging.getLogger(__name__)

keylen = {'sha1': 20,
          'sha256': 32,
          'sha512': 64}


class SMSACTION():
    SMSTEXT = "smstext"
    SMSAUTO = "smsautosend"


class SmsTokenClass(HotpTokenClass):
    """
    The SMS token sends an SMS containing an OTP via some kind of
    gateway. The gateways can be an SMTP or HTTP gateway or the special sipgate
    protocol. The Gateways are defined in the SMSProvider Modules.

    The SMS token is a challenge response token. I.e. the first request needs
    to contain the correct OTP PIN. If the OTP PIN is correct, the sending of
    the SMS is triggered. The second authentication must either contain the
    OTP PIN and the OTP value or the transaction_id and the OTP value.

      **Example 1st Authentication Request**:

        .. sourcecode:: http

           POST /validate/check HTTP/1.1
           Host: example.com
           Accept: application/json

           user=cornelius
           pass=otppin

      **Example 1st response**:

           .. sourcecode:: http

               HTTP/1.1 200 OK
               Content-Type: application/json

               {
                  "detail": {
                    "transaction_id": "xyz"
                  },
                  "id": 1,
                  "jsonrpc": "2.0",
                  "result": {
                    "status": true,
                    "value": false
                  },
                  "version": "privacyIDEA unknown"
                }

    After this, the SMS is triggered. When the SMS is received the second part
    of authentication looks like this:

      **Example 2nd Authentication Request**:

        .. sourcecode:: http

           POST /validate/check HTTP/1.1
           Host: example.com
           Accept: application/json

           user=cornelius
           transaction_id=xyz
           pass=otppin

      **Example 1st response**:

           .. sourcecode:: http

               HTTP/1.1 200 OK
               Content-Type: application/json

               {
                  "detail": {
                  },
                  "id": 1,
                  "jsonrpc": "2.0",
                  "result": {
                    "status": true,
                    "value": true
                  },
                  "version": "privacyIDEA unknown"
                }


    """
    def __init__(self, db_token):
        HotpTokenClass.__init__(self, db_token)
        self.set_type(u"sms")
        self.mode = ['challenge']
        self.hKeyRequired = True

    @classmethod
    def get_class_type(cls):
        """
        return the generic token class identifier
        """
        return "sms"

    @classmethod
    def get_class_prefix(cls):
        return "PISM"

    @classmethod
    def get_class_info(cls, key=None, ret='all'):
        """
        returns all or a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype : s.o.
        """

        res = {'type': 'sms',
               'title': _('SMS Token'),
               'description':
                    _('SMS: Send a One Time Password to the users mobile '
                      'phone.'),
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.AUTH: {
                        SMSACTION.SMSTEXT: {
                            'type': 'str',
                            'desc': _('The text that will be send via SMS for'
                                      ' an SMS token. Use <otp> and <serial> '
                                      'as parameters.')},
                        SMSACTION.SMSAUTO: {
                            'type': 'bool',
                            'desc': _('If set, a new SMS OTP will be sent '
                                      'after successful authentication with '
                                      'one SMS OTP.')},
                   }
               },
        }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret

    @log_with(log)
    def update(self, param, reset_failcount=True):
        """
        process initialization parameters

        :param param: dict of initialization parameters
        :type param: dict
        :return: nothing
        """
        # specific - phone
        phone = getParam(param, "phone", required)
        self.add_tokeninfo("phone", phone)

        # in case of the sms token, only the server must know the otpkey
        # thus if none is provided, we let create one (in the TokenClass)
        if "genkey" not in param and "otpkey" not in param:
            param['genkey'] = 1

        HotpTokenClass.update(self, param, reset_failcount)

    @log_with(log)
    @challenge_response_allowed
    def is_challenge_request(self, passw, user=None, options=None):
        """
        check, if the request would start a challenge

        if the passw contains only the pin, this request would
        trigger a challenge

        in this place as well the policy for a token is checked

        :param passw: password, which might be pin or pin+otp
        :param user: The authenticating user
        :param options: dictionary of additional request parameters

        :return: returns true or false
        """
        # Call the parents challenge request check
        is_challenge = HotpTokenClass.is_challenge_request(self,
                                                           passw, user,
                                                           options)

        return is_challenge

    @log_with(log)
    def create_challenge(self, transactionid=None, options=None):
        """
        create a challenge, which is submitted to the user

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
        :return: tuple of (bool, message and data)
                 bool, if submit was successful
                 message is submitted to the user
                 data is preserved in the challenge
                 attributes - additional attributes, which are displayed in the
                    output
        """
        success = False
        sms = ""
        options = options or {}
        return_message = "Enter the OTP from the SMS:"
        attributes = {'state': transactionid}
        validity = self._get_sms_timeout()

        if self.is_active() is True:
            counter = self.get_otp_count()
            log.debug("counter=%r" % counter)
            self.inc_otp_counter(counter, reset=False)
            # At this point we must not bail out in case of an
            # Gateway error, since checkPIN is successful. A bail
            # out would cancel the checking of the other tokens
            try:
                message_template = self._get_sms_text(options)
                success, sent_message = self._send_sms(
                    message=message_template)

                # Create the challenge in the database
                db_challenge = Challenge(self.token.serial,
                                         transaction_id=transactionid,
                                         challenge=options.get("challenge"),
                                         session=options.get("session"),
                                         validitytime=validity)
                db_challenge.save()
                transactionid = transactionid or db_challenge.transaction_id
            except Exception as e:
                info = ("The PIN was correct, but the "
                        "SMS could not be sent: %r" % e)
                log.warning(info)
                return_message = info

        validity = self._get_sms_timeout()
        expiry_date = datetime.datetime.now() + \
                                    datetime.timedelta(seconds=validity)
        attributes['valid_until'] = "%s" % expiry_date

        return success, return_message, transactionid, attributes

    @log_with(log)
    @check_token_locked
    def check_otp(self, anOtpVal, counter=None, window=None, options=None):
        """
        check the otpval of a token against a given counter
        and the window

        :param passw: the to be verified passw/pin
        :type passw: string

        :return: counter if found, -1 if not found
        :rtype: int
        """
        options = options or {}
        ret = HotpTokenClass.check_otp(self, anOtpVal, counter, window, options)
        if ret >= 0:
            if self._get_auto_sms(options):
                message = self._get_sms_text(options)
                self.inc_otp_counter(ret, reset=False)
                success, message = self._send_sms(message=message)
                log.debug("AutoSMS: send new SMS: %s" % success)
                log.debug("AutoSMS: %s" % message)
        return ret

    @log_with(log)
    def _send_sms(self, message="<otp>"):
        """
        send sms

        :param message: the sms submit message - could contain placeholders
         like <otp> or <serial>
        :type message: string

        :return: submitted message
        :rtype: string
        """
        ret = None

        phone = self.get_tokeninfo("phone")
        otp = self.get_otp()[2]
        serial = self.get_serial()

        message = message.replace("<otp>", otp)
        message = message.replace("<serial>", serial)

        log.debug("sending SMS to phone number %s " % phone)
        (SMSProvider, SMSProviderClass) = self._get_sms_provider()
        log.debug("smsprovider: %s, class: %s" % (SMSProvider,
                                                  SMSProviderClass))

        try:
            sms = get_sms_provider_class(SMSProvider, SMSProviderClass)()
        except Exception as exc:
            log.error("Failed to load SMSProvider: %r" % exc)
            log.error(traceback.format_exc())
            raise exc

        try:
            # now we need the config from the env
            log.debug("loading SMS configuration for class %s" % sms)
            config = self._get_sms_provider_config()
            log.debug("config: %r" % config)
            sms.load_config(config)
        except Exception as exc:
            log.error("Failed to load sms.providerConfig: %r" % exc)
            log.error(traceback.format_exc())
            raise Exception("Failed to load sms.providerConfig: %r" % exc)

        log.debug("submitMessage: %r, to phone %r" % (message, phone))
        ret = sms.submit_message(phone, message)
        return ret, message

    @log_with(log)
    def _get_sms_provider(self):
        """
        get the SMS Provider class definition

        :return: tuple of SMSProvider and Provider Class as string
        :rtype: tuple of (string, string)
        """
        smsProvider = get_from_config("sms.provider",
                                      default="privacyidea.lib.smsprovider."
                                              "HttpSMSProvider.HttpSMSProvider")
        (SMSProvider, SMSProviderClass) = smsProvider.rsplit(".", 1)
        return SMSProvider, SMSProviderClass

    @log_with(log)
    def _get_sms_provider_config(self):
        """
        load the defined sms provider config definition

        :return: dict of the sms provider definition
        :rtype: dict
        """
        tConfig = get_from_config("sms.providerConfig", "{}")
        config = loads(tConfig)
        return config

    @log_with(log)
    def _get_sms_timeout(self):
        """
        get the challenge time is in the specified range

        :return: the defined validation timeout in seconds
        :rtype:  int
        """
        try:
            timeout = int(get_from_config("sms.providerTimeout", 5 * 60))
        except Exception as ex:  # pragma: no cover
            log.warning("SMSProviderTimeout: value error %r - reset to 5*60"
                                                                        % (ex))
            timeout = 5 * 60
        return timeout

    def _get_sms_text(self, options):
        """
        This returns the SMSTEXT from the policy "smstext"

        :param options: contains user and g object.
        :optins type: dict
        :return: Message template
        :rtype: basestring
        """
        message = "<otp>"
        g = options.get("g")
        username = None
        realm = None
        user_object = options.get("user")
        if user_object:
            username = user_object.login
            realm = user_object.realm
        if g:
            clientip = options.get("clientip")
            policy_object = g.policy_object
            messages = policy_object.\
                get_action_values(action=SMSACTION.SMSTEXT,
                                  scope=SCOPE.AUTH,
                                  realm=realm,
                                  user=username,
                                  client=clientip,
                                  unique=True,
                                  allow_white_space_in_action=True)

            if len(messages) == 1:
                message = messages[0]

        return message

    def _get_auto_sms(self, options):
        """
        This returns the AUTOSMS setting.

        :param options: contains user and g object.
        :optins type: dict
        :return: True if an SMS should be sent automatically
        :rtype: bool
        """
        autosms = False
        g = options.get("g")
        user_object = options.get("user")
        username = None
        realm = None
        if user_object:
            username = user_object.login
            realm = user_object.realm
        if g:
            clientip = options.get("clientip")
            policy_object = g.policy_object
            autosmspol = policy_object.\
                get_policies(action=SMSACTION.SMSAUTO,
                             scope=SCOPE.AUTH,
                             realm=realm,
                             user=username,
                             client=clientip, active=True)
            autosms = len(autosmspol) >= 1

        return autosms
