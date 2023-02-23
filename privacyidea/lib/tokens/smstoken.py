# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2019-01-14   Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               Allow different SMS gateways via "sms.identifier"
#  2018-10-31   Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               Let the client choose to get a HTTP 500 Error code if
#               SMS fails.
#  2018-02-16   Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               Allow to use a dynamic_phone
#  2016-06-20   Cornelius Kölbel <cornelius.koelbel@netkngihts.it>
#               Use sms.identifier, central SMS gateway definition, to send
#               the OTP value via SMS.
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
from privacyidea.api.lib.utils import required, optional
from privacyidea.lib.utils import is_true, create_tag_dict

from privacyidea.lib.config import get_from_config
from privacyidea.lib.policy import SCOPE, ACTION, GROUP, get_action_values_from_options
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import Match
from privacyidea.lib.crypto import safe_compare
from privacyidea.lib.smsprovider.SMSProvider import (get_sms_provider_class,
                                                     create_sms_instance,
                                                     get_smsgateway)
from privacyidea.lib.tokens.hotptoken import VERIFY_ENROLLMENT_MESSAGE, HotpTokenClass
from json import loads
from privacyidea.lib import _

from privacyidea.lib.tokenclass import CHALLENGE_SESSION, AUTHENTICATIONMODE
from privacyidea.models import Challenge
from privacyidea.lib.decorators import check_token_locked
import logging


log = logging.getLogger(__name__)

keylen = {'sha1': 20,
          'sha256': 32,
          'sha512': 64}


class SMSACTION(object):
    SMSTEXT = "smstext"
    SMSAUTO = "smsautosend"
    GATEWAYS = "sms_gateways"


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
    mode = [AUTHENTICATIONMODE.CHALLENGE]

    def __init__(self, db_token):
        HotpTokenClass.__init__(self, db_token)
        self.set_type("sms")
        self.hKeyRequired = True

    @staticmethod
    def get_class_type():
        """
        return the generic token class identifier
        """
        return "sms"

    @staticmethod
    def get_class_prefix():
        return "PISM"

    @staticmethod
    def get_class_info(key=None, ret='all'):
        """
        returns all or a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype : s.o.
        """
        sms_gateways = [gw.identifier for gw in get_smsgateway()]
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
                            'desc': _('The text that will be send via SMS for '
                                      'an SMS token. Use tags like {otp} and {serial} '
                                      'as parameters.')},
                        SMSACTION.SMSAUTO: {
                            'type': 'bool',
                            'desc': _('If set, a new SMS OTP will be sent '
                                      'after successful authentication with '
                                      'one SMS OTP.')},
                       ACTION.CHALLENGETEXT: {
                           'type': 'str',
                           'desc': _('Use an alternate challenge text for telling the '
                                     'user to enter the code from the SMS.')
                       }
                   },
                   SCOPE.ADMIN: {
                       SMSACTION.GATEWAYS: {
                           'type': 'str',
                           'desc': "{0!s} ({1!s})".format(
                               _('Choose the gateways the administrator is allowed to set.'),
                               " ".join(sms_gateways))
                       }
                   },
                   SCOPE.USER: {
                       SMSACTION.GATEWAYS: {
                           'type': 'str',
                           'desc': "{0!s} ({1!s})".format(
                               _('Choose the gateways the user is allowed to set.'),
                               " ".join(sms_gateways))
                       }
                   },
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of SMS tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _(
                               "The user may only have this maximum number of active SMS tokens assigned."),
                           'group': GROUP.TOKEN
                       }
                   }
               },
        }

        if key:
            ret = res.get(key, {})
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
        verify = getParam(param, "verify", optional=True)
        if not verify:
            if getParam(param, "dynamic_phone", optional):
                self.add_tokeninfo("dynamic_phone", True)
            else:
                # specific - phone
                phone = getParam(param, "phone", required)
                self.add_tokeninfo("phone", phone)

            # in case of the sms token, only the server must know the otpkey
            # thus if none is provided, we let create one (in the TokenClass)
            if "genkey" not in param and "otpkey" not in param:
                param['genkey'] = 1

        HotpTokenClass.update(self, param, reset_failcount)
        return

    @log_with(log)
    def is_challenge_request(self, passw, user=None, options=None):
        """
        check, if the request would start a challenge

        We need to define the function again, to get rid of the
        is_challenge_request-decorator of the HOTP-Token

        :param passw: password, which might be pin or pin+otp
        :param options: dictionary of additional request parameters

        :return: returns true or false
        """
        return self.check_pin(passw, user=user, options=options)

    @log_with(log)
    def create_challenge(self, transactionid=None, options=None):
        """
        create a challenge, which is submitted to the user

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
                You can pass exception=1 to raise an exception, if
                the SMS could not be sent.
        :return: tuple of (bool, message and data)
                 bool, if submit was successful
                 message is submitted to the user
                 data is preserved in the challenge
                 reply_dict - additional reply_dict, which is added to the response
        """
        success = False
        options = options or {}
        return_message = get_action_values_from_options(SCOPE.AUTH,
                                                        "{0!s}_{1!s}".format(self.get_class_type(),
                                                                             ACTION.CHALLENGETEXT),
                                                        options) or _("Enter the OTP from the SMS:")
        reply_dict = {'attributes': {'state': transactionid}}
        validity = self._get_sms_timeout()

        if self.is_active() is True:
            counter = self.get_otp_count()
            log.debug("counter={0!r}".format(counter))
            # At this point we must not bail out in case of an
            # Gateway error, since checkPIN is successful. A bail
            # out would cancel the checking of the other tokens
            try:
                data = None
                # Only if this is NOT a multichallenge enrollment, we try to send the sms
                if options.get("session") != CHALLENGE_SESSION.ENROLLMENT:
                    self.inc_otp_counter(counter, reset=False)
                    message_template = self._get_sms_text(options)
                    success, sent_message = self._send_sms(
                        message=message_template, options=options)

                    # Create the challenge in the database
                    if is_true(get_from_config("sms.concurrent_challenges")):
                        data = self.get_otp()[2]
                db_challenge = Challenge(self.token.serial,
                                         transaction_id=transactionid,
                                         challenge=options.get("challenge"),
                                         data=data,
                                         session=options.get("session"),
                                         validitytime=validity)
                db_challenge.save()
                transactionid = transactionid or db_challenge.transaction_id
            except Exception as e:
                info = _("The PIN was correct, but the "
                         "SMS could not be sent!")
                log.warning(info + " ({0!r})".format(e))
                log.debug("{0!s}".format(traceback.format_exc()))
                return_message = info
                if is_true(options.get("exception")):
                    raise Exception(info)

        expiry_date = datetime.datetime.now() + \
                                    datetime.timedelta(seconds=validity)
        reply_dict['attributes']['valid_until'] = "{0!s}".format(expiry_date)

        return success, return_message, transactionid, reply_dict

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
        if ret < 0 and is_true(get_from_config("sms.concurrent_challenges")):
            if safe_compare(options.get("data"), anOtpVal):
                # We authenticate from the saved challenge
                ret = 1
        if ret >= 0 and self._get_auto_sms(options):
            # get message template from user specific policies
            message = self._get_sms_text(options)
            self.inc_otp_counter(ret, reset=False)
            success, message = self._send_sms(message=message, options=options)
            log.debug("AutoSMS: send new SMS: {0!s}".format(success))
            log.debug("AutoSMS: {0!r}".format(message))
        return ret

    @log_with(log)
    def _send_sms(self, message="<otp>", options=None):
        """
        send sms

        :param message: the sms submit message - could contain placeholders
            like <otp> or <serial>
        :type message: string
        :param options: Additional options from the request
        :type options: dict

        :return: submitted message
        :rtype: string
        """
        if is_true(self.get_tokeninfo("dynamic_phone")):
            phone = self.user.get_user_phone("mobile")
            if type(phone) == list and phone:
                # if there is a non-empty list, we use the first entry
                phone = phone[0]
        else:
            phone = self.get_tokeninfo("phone")
        if not phone:  # pragma: no cover
            log.warning("Token {0!s} does not have a phone number!".format(self.token.serial))
        otp = self.get_otp()[2]
        serial = self.get_serial()
        User = options.get("user")

        log.debug(r"sending SMS with template text: {0!s}".format(message))
        message = message.replace("<otp>", otp)
        message = message.replace("<serial>", serial)
        tags = create_tag_dict(serial=serial,
                               tokenowner=User,
                               tokentype="sms",
                               recipient={"givenname": User.info.get("givenname") if User else "",
                                          "surname": User.info.get("surname") if User else ""},
                               challenge=options.get("challenge"))
        message = message.format(otp=otp, **tags)

        # First we try to get the new SMS gateway config style
        # The token specific identifier has priority over the system wide identifier
        sms_gateway_identifier = self.get_tokeninfo("sms.identifier") or get_from_config("sms.identifier")

        if sms_gateway_identifier:
            # New style
            sms = create_sms_instance(sms_gateway_identifier)

        else:
            # Old style
            (SMSProvider, SMSProviderClass) = self._get_sms_provider()
            log.debug("smsprovider: {0!s}, class: {1!s}".format(SMSProvider,
                                                      SMSProviderClass))

            try:
                sms = get_sms_provider_class(SMSProvider, SMSProviderClass)()
            except Exception as exc:
                log.error("Failed to load SMSProvider: {0!r}".format(exc))
                log.debug("{0!s}".format(traceback.format_exc()))
                raise exc

            try:
                # now we need the config from the env
                log.debug("loading SMS configuration for class {0!s}".format(sms))
                config = self._get_sms_provider_config()
                log.debug("config: {0!r}".format(config))
                sms.load_config(config)
            except Exception as exc:
                log.error("Failed to load sms.providerConfig: {0!r}".format(exc))
                log.debug("{0!s}".format(traceback.format_exc()))
                raise Exception("Failed to load sms.providerConfig: {0!r}".format(exc))

        log.debug("submitMessage: {0!r}, to phone {1!r}".format(message, phone))
        ret = sms.submit_message(phone, message)
        return ret, message

    @staticmethod
    @log_with(log)
    def _get_sms_provider():
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

    @staticmethod
    @log_with(log)
    def _get_sms_provider_config():
        """
        load the defined sms provider config definition

        :return: dict of the sms provider definition
        :rtype: dict
        """
        tConfig = get_from_config("sms.providerConfig", "{}")
        config = loads(tConfig)
        return config

    @staticmethod
    @log_with(log)
    def _get_sms_timeout():
        """
        get the challenge time is in the specified range

        :return: the defined validation timeout in seconds
        :rtype:  int
        """
        try:
            timeout = int(get_from_config("sms.providerTimeout", 5 * 60))
        except Exception as ex:  # pragma: no cover
            log.warning("SMSProviderTimeout: value error {0!r} - reset to 5*60".format((ex)))
            timeout = 5 * 60
        return timeout

    @staticmethod
    def _get_sms_text(options):
        """
        This returns the SMSTEXT from the policy "smstext"
        
        options contains data like clientip, g, user and also the Request 
        parameters like "challenge" or "pass".

        :param options: contains user and g object.
        :type options: dict
        :return: Message template
        :rtype: basestring
        """
        message = "<otp>"
        g = options.get("g")
        user_object = options.get("user")
        if g:
            messages = Match.user(g, scope=SCOPE.AUTH, action=SMSACTION.SMSTEXT,
                                  user_object=user_object if user_object else None).action_values(
                allow_white_space_in_action=True, unique=True)
            if len(messages) == 1:
                message = list(messages)[0]

        return message

    @staticmethod
    def _get_auto_sms(options):
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
        if g:
            autosmspol = Match.user(g, scope=SCOPE.AUTH, action=SMSACTION.SMSAUTO, user_object=user_object).policies()
            autosms = len(autosmspol) >= 1

        return autosms

    def prepare_verify_enrollment(self):
        """
        This is called, if the token should be enrolled in a way, that the user
        needs to provide a proof, that the server can verify, that the token
        was successfully enrolled.
        The email token needs to send an email with OTP.

        The returned dictionary is added to the response in "detail" -> "verify".

        :return: A dictionary with information that is needed to trigger the verification.
        """
        self.create_challenge()
        return {"message": VERIFY_ENROLLMENT_MESSAGE}

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
        from privacyidea.lib.token import init_token
        from privacyidea.lib.tokenclass import CLIENTMODE
        token_obj = init_token({"type": cls.get_class_type(),
                                "dynamic_phone": 1}, user=user_obj)
        content.get("result")["value"] = False
        content.get("result")["authentication"] = "CHALLENGE"

        detail = content.setdefault("detail", {})
        # Create a challenge!
        c = token_obj.create_challenge(options={"session": CHALLENGE_SESSION.ENROLLMENT})
        # get details of token
        init_details = token_obj.get_init_detail()
        detail["transaction_ids"] = [c[2]]
        chal = {"transaction_id": c[2],
                "image": None,
                "client_mode": CLIENTMODE.INTERACTIVE,
                "serial": token_obj.token.serial,
                "type": token_obj.type,
                "message": _("Please enter your new phone number!")}
        detail["multi_challenge"] = [chal]
        detail.update(chal)

    def enroll_via_validate_2nd_step(self, passw, options=None):
        """
        This method is the optional second step of ENROLL_VIA_MULTICHALLENGE.
        It is used in situations like the email token, sms token or push,
        when enrollment via challenge response needs two steps.

        The passw is entered during the first authentication step and it
        contains the email address.

        So we need to update the token with the email address and
        we need to create a new challenge for the final authentication.

        :param options:
        :return:
        """
        self.del_tokeninfo("dynamic_phone")
        self.add_tokeninfo("phone", passw)
        # Dynamically we remember that we need to do another challenge
        self.currently_in_challenge = True
