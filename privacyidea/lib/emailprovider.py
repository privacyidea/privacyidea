# -*- coding: utf-8 -*-

import smtplib
from email.mime.text import MIMEText
from privacyidea.lib.log import log_with
import logging
LOG = logging.getLogger(__name__)


class IEmailProvider:
    """
    An abstract class that has to be implemented by every e-mail provider class.
    """
    def __init__(self):
        pass

    def submitMessage(self, email_to, message):
        """
        This method has to be implemented by every subclass of IEmailProvider.
        It will be called to send out the e-mail.

        :param email_to: The e-mail address of the recipient
        :type email_to: string

        :param message: The message sent to the recipient
        :type message: string

        :return: A tuple of success and a message
        :rtype: bool, string
        """
        raise NotImplementedError("Every subclass of IEmailProvider has to implement this method.")

    def loadConfig(self, configDict):
        """
        If you implement an e-mail provider that does not require configuration entries,
        then you may leave this method unimplemented.

        :param configDict: A dictionary that contains all configuration entries you defined
            (e.g. in the privacyidea.ini file)
        :type configDict: dict
        """
        pass


class SMTPEmailProvider(IEmailProvider):
    """
    Sends e-mail over a SMTP server.
    """

    DEFAULT_EMAIL_FROM = "privacyidea@example.com"
    DEFAULT_EMAIL_SUBJECT = "Your OTP"

    def __init__(self):
        self.smtp_server = None
        self.smtp_user = None
        self.smtp_password = None
        self.email_from = None
        self.email_subject = None

    def loadConfig(self, configDict):
        """
        Loads the configuration for this e-mail e-mail provider

        :param configDict: A dictionary that contains all configuration entries you defined
            (e.g. in the privacyidea.ini file)
        :type configDict: dict

        """
        self.smtp_server = configDict.get('SMTP_SERVER')
        self.smtp_user = configDict.get('SMTP_USER')
        self.smtp_password = configDict.get('SMTP_PASSWORD')
        self.email_from = configDict.get('EMAIL_FROM')
        self.email_subject = configDict.get('EMAIL_SUBJECT')

    @log_with(LOG)
    def submitMessage(self, email_to, message):
        """
        Sends out the e-mail.

        :param email_to: The e-mail address of the recipient
        :type email_to: string

        :param message: The message sent to the recipient
        :type message: string

        :return: A tuple of success and a message
        :rtype: bool, string
        """
        if not self.smtp_server:
            raise Exception("Invalid EmailProviderConfig. SMTP_SERVER is required")
        if not self.email_from:
            self.email_from = self.DEFAULT_EMAIL_FROM
        if not self.email_subject:
            self.email_subject = self.DEFAULT_EMAIL_SUBJECT

        status_message = "e-mail sent successfully"
        success = True

        # Create a text/plain message
        msg = MIMEText(message)
        msg['Subject'] = self.email_subject
        msg['From'] = self.email_from
        msg['To'] = email_to

        s = smtplib.SMTP(self.smtp_server)
        if self.smtp_user:
            s.login(self.smtp_user, self.smtp_password)
        try:
            errors = s.sendmail(self.email_from, email_to, msg.as_string())
            if len(errors) > 0:
                LOG.error("error(s) sending e-mail %r" % errors)
                success, status_message = False, "error sending e-mail %s" % errors
        except (smtplib.SMTPHeloError, smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused,
                smtplib.SMTPDataError) as smtplib_exception:
            LOG.error("error(s) sending e-mail. Caught exception: %r" %
                      smtplib_exception)
            success, status_message = False, "error sending e-mail %s" % smtplib_exception
        s.quit()
        return success, status_message
