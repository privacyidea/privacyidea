# -*- coding: utf-8 -*-
#
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
import smtplib
import traceback
from privacyidea.lib.tokens.smstoken import HotpTokenClass
from privacyidea.lib.config import get_from_config
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.policy import SCOPE
from privacyidea.lib.log import log_with
from gettext import gettext as _
from privacyidea.models import Challenge
from privacyidea.lib.decorators import check_token_locked

log = logging.getLogger(__name__)


class EMAILACTION():
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
        # we support various hashlib methods, but only on create
        # which is effectively set in the update
        self.hashlibStr = get_from_config("hotp.hashlib", "sha1")


    @property
    def _email_address(self):
        return self.get_tokeninfo(self.EMAIL_ADDRESS_KEY)

    @_email_address.setter
    def _email_address(self, value):
        self.add_tokeninfo(self.EMAIL_ADDRESS_KEY, value)

    @classmethod
    def get_class_type(cls):
        """
        return the generic token class identifier
        """
        return "email"

    @classmethod
    def get_class_prefix(cls):
        return "PIEM"

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
                       'desc': _('The text that will be send via EMail for'
                                 ' an EMail token. Use <otp> and <serial> '
                                 'as parameters.')},
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
    def update(self, param, reset_failcount=True):
        """
        update - process initialization parameters

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing

        """
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
        options = options or {}
        return_message = "Enter the OTP from the Email:"
        attributes = {'state': transactionid}

        if self.is_active() is True:
            counter = self.get_otp_count()
            log.debug("counter=%r" % counter)
            self.inc_otp_counter(counter, reset=False)
            # At this point we must not bail out in case of an
            # Gateway error, since checkPIN is successful. A bail
            # out would cancel the checking of the other tokens
            try:
                message_template = self._get_email_text_or_subject(options)
                subject_template = self._get_email_text_or_subject(options,
                                                                   EMAILACTION.EMAILSUBJECT,
                                                                   "Your OTP")
                validity = int(get_from_config("email.validtime", 120))

                # Create the challenge in the database
                db_challenge = Challenge(self.token.serial,
                                         transaction_id=transactionid,
                                         challenge=options.get("challenge"),
                                         session=options.get("session"),
                                         validitytime=validity)
                db_challenge.save()
                transactionid = transactionid or db_challenge.transaction_id
                # We send the email after creating the challenge for testing.
                success, sent_message = self._send_email(
                    message=message_template,
                    subject=subject_template)

            except Exception as e:
                info = ("The PIN was correct, but the "
                        "EMail could not be sent: %r" % e)
                log.warning(info)
                log.warning(traceback.format_exc(e))
                return_message = info

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
            if self._get_auto_email(options):
                message = self._get_email_text_or_subject(options)
                subject = self._get_email_text_or_subject(options,
                                                          action=EMAILACTION.EMAILSUBJECT,
                                                          default="Your OTP")
                self.inc_otp_counter(ret, reset=False)
                success, message = self._send_email(message=message,
                                                    subject=subject)
                log.debug("AutoEmail: send new SMS: %s" % success)
                log.debug("AutoEmail: %s" % message)
        return ret

    def _get_email_text_or_subject(self, options,
                                   action=EMAILACTION.EMAILTEXT,
                                   default="<otp>"):
        """
        This returns the EMAILTEXT or EMAILSUBJECT from the policy
        "emailtext" or "emailsubject

        :param options: contains user and g object.
        :type options: dict
        :param action: The action - either emailtext or emailsubject
        :param default: If no policy can be found, this is the default text
        :return: Message template
        :rtype: basestring
        """
        message = default
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
                                  allow_white_space_in_action=True)

            if len(messages) == 1:
                message = messages[0]

        return message

    def _get_auto_email(self, options):
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
                             client=clientip, active=True)
            autosms = len(autoemailpol) >= 1

        return autosms

    @log_with(log)
    def _send_email(self, message="<otp>", subject="Your OTP"):
        """
        send email

        :param message: the email submit message - could contain placeholders
            like <otp> or <serial>
        :type message: string

        :return: submitted message
        :rtype: string
        """
        ret = None

        recipient = self._email_address
        otp = self.get_otp()[2]
        serial = self.get_serial()

        message = message.replace("<otp>", otp)
        message = message.replace("<serial>", serial)

        subject = subject.replace("<otp>", otp)
        subject = subject.replace("<serial>", serial)

        log.debug("sending Email to %s " % recipient)

        mailserver = get_from_config("email.mailserver", "localhost")
        port = int(get_from_config("email.port", 25))
        username = get_from_config("email.username")
        password = get_from_config("email.password")
        mail_from = get_from_config("email.mailfrom", "privacyidea@localhost")
        body = """From: %s
subject: %s

%s""" % (mail_from, subject, message)

        # Upper layer will catch exceptions
        mail = smtplib.SMTP(mailserver, port)
        mail.ehlo()
        # Start TLS if required
        if get_from_config("email.tls"):
            mail.starttls()
        # Authenticate, if a username is given.
        if username:
            mail.login(username, password)
        r = mail.sendmail(mail_from, recipient, body)
        mail.quit()
        ret = True

        return ret, message
