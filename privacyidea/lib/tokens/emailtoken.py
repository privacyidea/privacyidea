# -*- coding: utf-8 -*-
#  2018-10-31 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Let the client choose to get a HTTP 500 Error code if
#             SMS fails.
#  2018-02-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add dynamic email address. Dynamically read from user source.
#  2018-01-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add email templates
#  2015-12-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Use privacyidea.lib.smtpserver instead of smtplib
#  2015-10-12 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add test config function
#  2015-04-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Adapt code to work with privacyIDEA 2 (Flask)
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
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
__doc__ = """This is the implementation of an Email-Token, that sends OTP
values via SMTP.

The following config entries are used:

 * email.validtime
 * email.identifier

The identifier points to a system wide SMTP server configuration.
See :ref:`rest_smtpserver`.

The system wide SMTP server configuration was introduced in version 2.10.
In privacyIDEA up to version 2.9 the following config entries were used:

 * email.validtime
 * email.mailserver
 * email.port
 * email.username
 * email.password
 * email.mailfrom
 * email.subject
 * email.tls

policy: action: emailtext

The code is tested in tests/test_lib_tokens_email
"""

import logging
import traceback
import datetime
from privacyidea.lib.tokens.smstoken import HotpTokenClass
from privacyidea.lib.config import get_from_config
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.utils import is_true
from privacyidea.lib.policy import (SCOPE, ACTION, get_action_values_from_options)
from privacyidea.lib.log import log_with
from privacyidea.lib import _
from privacyidea.models import Challenge
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.smtpserver import send_email_data, send_email_identifier


log = logging.getLogger(__name__)
TEST_SUCCESSFUL = "Successfully sent email. Please check your inbox."


class EMAILACTION(object):
    EMAILTEXT = "emailtext"
    EMAILSUBJECT = "emailsubject"
    EMAILAUTO = "emailautosend"


class EmailTokenClass(HotpTokenClass):
    """
    Implementation of the EMail Token Class, that sends OTP values via SMTP.
    (Similar to SMSTokenClass)
    """

    EMAIL_ADDRESS_KEY = "email"

    def __init__(self, aToken):
        HotpTokenClass.__init__(self, aToken)
        self.set_type(u"email")
        self.mode = ['challenge']
        # we support various hashlib methods, but only on create
        # which is effectively set in the update
        self.hashlibStr = get_from_config("hotp.hashlib", "sha1")

    @property
    def _email_address(self):
        if is_true(self.get_tokeninfo("dynamic_email")):
            email = self.user.info.get(self.EMAIL_ADDRESS_KEY)
            if type(email) == list and email:
                # If there is a non-empty list, we use the first entry
                email = email[0]
        else:
            email = self.get_tokeninfo(self.EMAIL_ADDRESS_KEY)
        if not email:  # pragma: no cover
            log.warning("Token {0!s} does not have an email address!".format(self.token.serial))
        return email

    @_email_address.setter
    def _email_address(self, value):
        self.add_tokeninfo(self.EMAIL_ADDRESS_KEY, value)

    @staticmethod
    def get_class_type():
        """
        return the generic token class identifier
        """
        return "email"

    @staticmethod
    def get_class_prefix():
        return "PIEM"

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
        res = {'type': 'email',
               'title': _('EMail Token'),
               'description':
                   _('EMail: Send a One Time Password to the users email '
                     'address.'),
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {SCOPE.AUTH: {
                   EMAILACTION.EMAILTEXT: {
                       'type': 'str',
                       'desc': _('The text that will be sent via EMail for'
                                 ' an EMail token. Use <otp> and <serial> '
                                 'as parameters. You may also specify a filename '
                                 'as email template starting with "file:".')},
                   EMAILACTION.EMAILSUBJECT: {
                       'type': 'str',
                       'desc': _('The subject of the EMail for'
                                 ' an EMail token. Use <otp> and <serial> '
                                 'as parameters.')},
                   EMAILACTION.EMAILAUTO: {
                       'type': 'bool',
                       'desc': _('If set, a new EMail OTP will be sent '
                                 'after successful authentication with '
                                 'one EMail OTP.')},
                   ACTION.CHALLENGETEXT: {
                       'type': 'str',
                       'desc': _('Use an alternate challenge text for telling the '
                                 'user to enter the code from the eMail.')
                   }
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
    def update(self, param, reset_failcount=True):
        """
        update - process initialization parameters

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing

        """
        if getParam(param, "dynamic_email", optional=True):
            self.add_tokeninfo("dynamic_email", True)
        else:
            # specific - e-mail
            self._email_address = getParam(param,
                                           self.EMAIL_ADDRESS_KEY,
                                           optional=False)

        # in case of the e-mail token, only the server must know the otpkey
        # thus if none is provided, we let create one (in the TokenClass)
        if 'genkey' not in param and 'otpkey' not in param:
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
                the SMS could not be sent. Otherwise the message is contained in the response.
        :return: tuple of (bool, message and data)
                 bool, if submit was successful
                 message is submitted to the user
                 data is preserved in the challenge
                 attributes - additional attributes, which are displayed in the
                    output
        """
        success = False
        options = options or {}
        return_message = get_action_values_from_options(SCOPE.AUTH,
                                                        "{0!s}_{1!s}".format(self.get_class_type(),
                                                                             ACTION.CHALLENGETEXT),
                                                        options) or _("Enter the OTP from the Email:")
        attributes = {'state': transactionid}
        validity = int(get_from_config("email.validtime", 120))

        if self.is_active() is True:
            counter = self.get_otp_count()
            log.debug("counter={0!r}".format(counter))
            self.inc_otp_counter(counter, reset=False)
            # At this point we must not bail out in case of an
            # Gateway error, since checkPIN is successful. A bail
            # out would cancel the checking of the other tokens
            try:
                message_template, mimetype = self._get_email_text_or_subject(options)
                subject_template, _n = self._get_email_text_or_subject(options,
                                                                   EMAILACTION.EMAILSUBJECT,
                                                                   "Your OTP")

                # Create the challenge in the database
                if is_true(get_from_config("email.concurrent_challenges")):
                    data = self.get_otp()[2]
                else:
                    data = None
                db_challenge = Challenge(self.token.serial,
                                         transaction_id=transactionid,
                                         challenge=options.get("challenge"),
                                         data=data,
                                         session=options.get("session"),
                                         validitytime=validity)
                db_challenge.save()
                transactionid = transactionid or db_challenge.transaction_id
                # We send the email after creating the challenge for testing.
                success, sent_message = self._compose_email(
                    message=message_template,
                    subject=subject_template,
                    mimetype=mimetype)

            except Exception as e:
                info = ("The PIN was correct, but the "
                        "EMail could not be sent: %r" % e)
                log.warning(info)
                log.debug(u"{0!s}".format(traceback.format_exc()))
                return_message = info
                if is_true(options.get("exception")):
                    raise Exception(info)

        expiry_date = datetime.datetime.now() + \
                                    datetime.timedelta(seconds=validity)
        attributes['valid_until'] = "{0!s}".format(expiry_date)

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
        if ret < 0 and is_true(get_from_config("email.concurrent_challenges")):
            if options.get("data") == anOtpVal:
                # We authenticate from the saved challenge
                ret = 1
        if ret >= 0 and self._get_auto_email(options):
            message, mimetype = self._get_email_text_or_subject(options)
            subject, _ = self._get_email_text_or_subject(options,
                                                      action=EMAILACTION.EMAILSUBJECT,
                                                      default="Your OTP")
            self.inc_otp_counter(ret, reset=False)
            success, message = self._compose_email(message=message,
                                                   subject=subject,
                                                   mimetype=mimetype)
            log.debug("AutoEmail: send new SMS: {0!s}".format(success))
            log.debug("AutoEmail: {0!r}".format(message))
        return ret

    @staticmethod
    def _get_email_text_or_subject(options,
                                   action=EMAILACTION.EMAILTEXT,
                                   default="<otp>"):
        """
        This returns the EMAILTEXT or EMAILSUBJECT from the policy
        "emailtext" or "emailsubject

        :param options: contains user and g object.
        :type options: dict
        :param action: The action - either emailtext or emailsubject
        :param default: If no policy can be found, this is the default text
        :return: Message template, MIME type (one of "plain", "html")
        :rtype: (basestring, basestring)
        """
        message = default
        mimetype = "plain"
        g = options.get("g")
        username = None
        realm = None
        user_object = options.get("user")
        if user_object:  # pragma: no cover
            username = user_object.login
            realm = user_object.realm
        if g:
            clientip = options.get("clientip")
            policy_object = g.policy_object
            messages = policy_object.\
                get_action_values(action=action,
                                  scope=SCOPE.AUTH,
                                  realm=realm,
                                  user=username,
                                  client=clientip,
                                  unique=True,
                                  allow_white_space_in_action=True,
                                  audit_data=g.audit_object.audit_data)

            if len(messages) == 1:
                message = list(messages)[0]

        message = message.format(challenge=options.get("challenge"))
        if message.startswith("file:"):
            # We read the template from the file.
            try:
                with open(message[5:], "r") as f:
                    message = f.read()
                    mimetype = "html"
            except Exception as e:  # pragma: no cover
                message = default
                log.warning(u"Failed to read email template: {0!r}".format(e))
                log.debug(u"{0!s}".format(traceback.format_exc()))

        return message, mimetype

    @staticmethod
    def _get_auto_email(options):
        """
        This returns the AUTOEMAIL setting.

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
        if user_object:  # pragma: no cover
            username = user_object.login
            realm = user_object.realm
        if g:
            clientip = options.get("clientip")
            policy_object = g.policy_object
            autoemailpol = policy_object.\
                get_policies(action=EMAILACTION.EMAILAUTO,
                             scope=SCOPE.AUTH,
                             realm=realm,
                             user=username,
                             client=clientip, active=True,
                             audit_data=g.audit_object.audit_data)
            autosms = len(autoemailpol) >= 1

        return autosms

    @log_with(log)
    def _compose_email(self, message="<otp>", subject="Your OTP", mimetype="plain"):
        """
        send email

        :param message: the email submit message - could contain placeholders
            like <otp> or <serial>
        :type message: string
        :param mimetype: the message MIME type - one of "plain", "html"
        :type mimetype: basestring

        :return: submitted message
        :rtype: string
        """
        ret = None

        recipient = self._email_address
        otp = self.get_otp()[2]
        serial = self.get_serial()

        message = message.replace("<otp>", otp)
        message = message.replace("<serial>", serial)

        message = message.format(otp=otp, serial=serial)

        subject = subject.replace("<otp>", otp)
        subject = subject.replace("<serial>", serial)

        subject = subject.format(otp=otp, serial=serial)

        log.debug("sending Email to {0!r}".format(recipient))

        identifier = get_from_config("email.identifier")
        if identifier:
            # New way to send email
            ret = send_email_identifier(identifier, recipient, subject, message,
                                        mimetype=mimetype)
        else:
            # old way to send email / DEPRECATED
            mailserver = get_from_config("email.mailserver", "localhost")
            port = int(get_from_config("email.port", 25))
            username = get_from_config("email.username")
            password = get_from_config("email.password")
            mail_from = get_from_config("email.mailfrom", "privacyidea@localhost")
            email_tls = get_from_config("email.tls", default=False,
                                        return_bool=True)
            ret = send_email_data(mailserver, subject, message, mail_from,
                                  recipient, username, password, port,
                                  email_tls)
        return ret, message

    @classmethod
    def test_config(cls, params=None):
        mailserver = getParam(params, "email.mailserver", optional=False)
        subject = "Your TEST OTP"
        message = "This is a test."
        mail_from = getParam(params, "email.mailfrom", optional=False)
        recipient = getParam(params, "email.recipient", optional=False)
        password = getParam(params, "email.password")
        username = getParam(params, "email.username")
        port = getParam(params, "email.port", default=25)
        email_tls = getParam(params, "email.tls", default=False)
        r = send_email_data(mailserver, subject, message, mail_from,
                            recipient, username=username,
                            password=password, port=port, email_tls=email_tls)

        description = "Could not send email."
        if r:
            description = TEST_SUCCESSFUL

        return r, description
