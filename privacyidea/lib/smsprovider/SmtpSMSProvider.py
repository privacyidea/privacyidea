# -*- coding: utf-8 -*-
#
#   2016-06-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#              Add allowed parameters to the SMS Provider
#
#    privacyIDEA is a fork of LinOTP
#    May 28, 2014 Cornelius Kölbel
#    E-mail: info@privacyidea.org
#    Contact: www.privacyidea.org
#
#    2015-01-30 Rewrite for flask migration
#               Cornelius Kölbel <cornelius@privacyidea.org>
#
#
#    Copyright (C) LinOTP: 2010 - 2014 LSE Leading Security Experts GmbH
#
#    This program is free software: you can redistribute it and/or
#    modify it under the terms of the GNU Affero General Public
#    License, version 3, as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the
#               GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

__doc__="""This is the SMSClass to send SMS via SMTP Gateway.
i.e. a Mail is sent to an Gateway/Emailserver and dependig on the
address, subject and body this gateway will trigger the sending of the SMS.

The code is tested in tests/test_lib_smsprovider
"""
from privacyidea.lib.smsprovider.SMSProvider import ISMSProvider, SMSError
from privacyidea.lib.smtpserver import send_email_identifier, send_email_data
import string
import logging
log = logging.getLogger(__name__)

PHONE_TAG = "<phone>"
MSG_TAG = "<otp>"


class SmtpSMSProvider(ISMSProvider):

    def submit_message(self, phone, message):
        """
        Submits the message for phone to the email gateway.

        Returns true in case of success

        In case of a failure an exception is raised
        """
        if self.smsgateway:
            identifier = self.smsgateway.option_dict.get("SMTPIDENTIFIER")
            recipient = self.smsgateway.option_dict.get("MAILTO").format(
                otp=message, phone=phone)
            subject = self.smsgateway.option_dict.get("SUBJECT",
                                                      "{phone}").format(
                otp=message, phone=phone)
            body = self.smsgateway.option_dict.get("BODY", "{otp}").format(
                otp=message, phone=phone)
        else:
            identifier = self.config.get("IDENTIFIER")
            server = self.config.get("MAILSERVER")
            sender = self.config.get("MAILSENDER")
            recipient = self.config.get("MAILTO")
            subject = self.config.get("SUBJECT", PHONE_TAG)
            body = self.config.get("BODY", MSG_TAG)

            if not (server and recipient and sender) and not (identifier and \
                    recipient):
                log.error("incomplete config: %s. MAILTO and (IDENTIFIER or "
                          "MAILSERVER and MAILSENDER) needed" % self.config)
                raise SMSError(-1, "Incomplete SMS config.")

            log.debug("submitting message {0!r} to {1!s}".format(body, phone))
            recipient = string.replace(recipient, PHONE_TAG, phone)
            subject = string.replace(subject, PHONE_TAG, phone)
            subject = string.replace(subject, MSG_TAG, message)
            body = string.replace(body, PHONE_TAG, phone)
            body = string.replace(body, MSG_TAG, message)

        if identifier:
            r = send_email_identifier(identifier, recipient, subject, body)
        else:
            username = self.config.get("MAILUSER")
            password = self.config.get("MAILPASSWORD")
            r = send_email_data(server, subject, body, sender, recipient,
                                username, password)
        if not r:
            raise SMSError(500, "Failed to deliver SMS to SMTP Gateway.")

        return True

    @classmethod
    def parameters(cls):
        """
        Return a dictionary, that describes the parameters and options for the
        SMS provider.
        Parameters are required keys to values.

        :return: dict
        """
        from privacyidea.lib.smtpserver import get_smtpservers
        params = {"options_allowed": False,
                  "parameters": {
                      "MAILTO": {
                          "required": True,
                          "description": "The recipient of the email. "
                                         "Use tags {phone} and {otp}."},
                      "SMTPIDENTIFIER": {
                          "required": True,
                          "description": "Your SMTP configuration, "
                                         "that should be used to send the "
                                         "email.",
                          "values": [
                              provider.config.identifier for
                              provider in get_smtpservers()]},
                      "SUBJECT": {
                          "description": "The optional subject of the email. "
                                         "Use tags {phone} and {otp}."},
                      "BODY": {
                          "description": "The optional body of the email. "
                                         "Use tags {phone} and {otp}.",
                          "type": "text" }
                  }
                  }
        return params
