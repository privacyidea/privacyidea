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
from privacyidea.lib.tokens.hotptoken import VERIFY_ENROLLMENT_MESSAGE
from privacyidea.lib.tokenclass import CHALLENGE_SESSION, AUTHENTICATIONMODE
from privacyidea.lib.config import get_from_config
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.utils import is_true, create_tag_dict
from privacyidea.lib.policy import SCOPE, ACTION, GROUP, get_action_values_from_options
from privacyidea.lib.policy import Match
from privacyidea.lib.log import log_with
from privacyidea.lib import _
from privacyidea.models import Challenge
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.smtpserver import send_email_data, send_email_identifier
from privacyidea.lib.crypto import safe_compare


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
    # The HOTP token provides means to verify the enrollment
    can_verify_enrollment = True
    mode = [AUTHENTICATIONMODE.CHALLENGE]

    def __init__(self, aToken):
        HotpTokenClass.__init__(self, aToken)
        self.set_type("email")
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
        :rtype: dict
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
                       'desc': _('The text that will be sent via EMail for '
                                 'an EMail-token. Several tags like {otp} and '
                                 '{serial} can be used as parameters. You may '
                                 'also specify a filename as email template '
                                 'starting with "file:".')},
                   EMAILACTION.EMAILSUBJECT: {
                       'type': 'str',
                       'desc': _('The subject of the EMail for '
                                 'an EMail token. Use tags like {otp} and {serial} '
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
                   },
               },
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of email tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of active email tokens assigned."),
                           'group': GROUP.TOKEN
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
        verify = getParam(param, "verify", optional=True)
        if not verify:
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
            You can pass ``exception=1`` to raise an exception, if
            the Email could not be sent.
        :return: tuple
            of (success, message, transactionid, attributes)

                * success: if submit was successful
                * message: the text submitted to the user
                * transactionid: the given or generated transactionid
                * reply_dict: additional dictionary, which is added to the response
        :rtype: tuple(bool, str, str, dict)
        """
        success = False
        options = options or {}
        return_message = get_action_values_from_options(SCOPE.AUTH,
                                                        "{0!s}_{1!s}".format(self.get_class_type(),
                                                                             ACTION.CHALLENGETEXT),
                                                        options) or _("Enter the OTP from the Email:")
        reply_dict = {'attributes': {'state': transactionid}}
        validity = int(get_from_config("email.validtime", 120))

        if self.is_active() is True:
            counter = self.get_otp_count()
            log.debug("counter={0!r}".format(counter))

            # At this point we must not bail out in case of an
            # Gateway error, since checkPIN is successful. A bail
            # out would cancel the checking of the other tokens
            try:
                data = None
                if options.get("session") != CHALLENGE_SESSION.ENROLLMENT:
                    # Only if this is NOT an multichallenge enrollment, we try to send the email
                    self.inc_otp_counter(counter, reset=False)
                    message_template, mimetype = self._get_email_text_or_subject(options)
                    subject_template, _n = self._get_email_text_or_subject(options,
                                                                       EMAILACTION.EMAILSUBJECT,
                                                                       "Your OTP")
                    success, sent_message = self._compose_email(
                        options=options,
                        message=message_template,
                        subject=subject_template,
                        mimetype=mimetype)

                # Create the challenge in the database
                if is_true(get_from_config("email.concurrent_challenges")):
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
                         "EMail could not be sent!")
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
        if ret < 0 and is_true(get_from_config("email.concurrent_challenges")):
            if safe_compare(options.get("data"), anOtpVal):
                # We authenticate from the saved challenge
                ret = 1
        if ret >= 0 and self._get_auto_email(options):
            message, mimetype = self._get_email_text_or_subject(options)
            subject, _ = self._get_email_text_or_subject(options,
                                                      action=EMAILACTION.EMAILSUBJECT,
                                                      default="Your OTP")
            self.inc_otp_counter(ret, reset=False)
            success, message = self._compose_email(options=options,
                                                   message=message,
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
        user_object = options.get("user")
        if g:
            messages = Match.user(g, scope=SCOPE.AUTH, action=action, user_object=user_object if user_object else None)\
                .action_values(unique=True, allow_white_space_in_action=True)
            if len(messages) == 1:
                message = list(messages)[0]

        if message.startswith("file:"):
            # We read the template from the file.
            try:
                with open(message[5:], "r") as f:
                    message = f.read()
                    mimetype = "html"
            except Exception as e:  # pragma: no cover
                message = default
                log.warning("Failed to read email template: {0!r}".format(e))
                log.debug("{0!s}".format(traceback.format_exc()))

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
        if g:
            autoemailpol = Match.user(g, scope=SCOPE.AUTH, action=EMAILACTION.EMAILAUTO, user_object=user_object).policies()
            autosms = len(autoemailpol) >= 1

        return autosms

    @log_with(log)
    def _compose_email(self, message="<otp>", subject="Your OTP", mimetype="plain", options=None):
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
        options = options or {}
        challenge = options.get("challenge")

        message = message.replace("<otp>", otp)
        message = message.replace("<serial>", serial)

        tags = create_tag_dict(serial=serial,
                               tokenowner=self.user,
                               tokentype=self.get_tokentype(),
                               recipient={"givenname": self.user.info.get("givenname") if self.user else "",
                                          "surname": self.user.info.get("surname") if self.user else ""},
                               escape_html=mimetype.lower() == "html",
                               challenge=challenge)

        message = message.format(otp=otp, **tags)

        subject = subject.replace("<otp>", otp)
        subject = subject.replace("<serial>", serial)

        subject = subject.format(otp=otp, **tags)

        log.debug("sending Email to {0!r}".format(recipient))

        # The token specific identifier has priority over the system wide identifier
        identifier = self.get_tokeninfo("email.identifier") or get_from_config("email.identifier")
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
                                "dynamic_email": 1}, user=user_obj)
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
                "message": _("Please enter your new email address!")}
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
        self.del_tokeninfo("dynamic_email")
        self.add_tokeninfo(self.EMAIL_ADDRESS_KEY, passw)
        # Dynamically we remember that we need to do another challenge
        self.currently_in_challenge = True
