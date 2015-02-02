# -*- coding: utf-8 -*-
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

import string
import smtplib

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
        server = self.config.get("MAILSERVER")
        fromaddr = self.config.get("MAILSENDER")
        toaddr = self.config.get("MAILTO")

        if not (server and fromaddr and toaddr):
            log.error("incomplete config: %s. MAILSERVER, MAILSENDER "
                      "and MAILTO needed." % self.config)
            raise SMSError(-1, "Incomplete SMS config.")

        subject = self.config.get("SUBJECT", PHONE_TAG)
        body = self.config.get("BODY", MSG_TAG)

        # optional
        user = self.config.get("MAILUSER")
        password = self.config.get("MAILPASSWORD")

        log.debug("submitting message %s to %s" % (message, phone))

        toaddr = string.replace(toaddr, PHONE_TAG, phone)
        subject = string.replace(subject, PHONE_TAG, phone)
        subject = string.replace(subject, MSG_TAG, message)
        body = string.replace(body, PHONE_TAG, phone)
        body = string.replace(body, MSG_TAG, message)

        msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s"
               % (fromaddr,
                  toaddr,
                  subject,
                  body))

        try:
            serv = smtplib.SMTP(server)
            serv.set_debuglevel(1)
            if user:
                log.debug("authenticating to mailserver, "
                          "user: %s, pass: %s" % (user, password))
                serv.login(user, password)
            # returns a dictionary of replies for all recients, that failed
            senders = serv.sendmail(fromaddr, toaddr, msg)
            failed_recepients = senders.get(toaddr)
            serv.quit()
        except Exception as e:
            log.error("An error occurred during sending of the email: %s" %
                      str(e))
            raise Exception(e)

        if failed_recepients:
            log.error("some error occurred for recipient "
                      "%s: %s" % (toaddr, failed_recepients[0]))
            raise SMSError(failed_recepients[0],
                           "Failed to deliver SMS to SMTP Gateway.")

        return True
