# -*- coding: utf-8 -*-
#
#  2015-12-27 Cornelius Kölbel <cornelius@privacyidea.org>
#             SMTP Server implementation
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
#
from privacyidea.lib.queue import job, wrap_job, has_job_queue
from privacyidea.models import SMTPServer as SMTPServerDB
from privacyidea.lib.crypto import (decryptPassword, encryptPassword,
                                    FAILED_TO_DECRYPT_PASSWORD)
from privacyidea.lib.utils import fetch_one_resource
import logging
from privacyidea.lib.log import log_with
from time import gmtime, strftime
import smtplib
from email.mime.text import MIMEText
from privacyidea.lib.error import ConfigAdminError
__doc__ = """
This is the library for creating, listing and deleting SMTPServer objects in
the Database.

It depends on the SMTPServer in the database model models.py. This module can
be tested standalone without any webservices.
This module is tested in tests/test_lib_smtpserver.py
"""

log = logging.getLogger(__name__)
TIMEOUT = 10

SEND_EMAIL_JOB_NAME = "smtpserver.send_email"


class SMTPServer(object):
    """
    SMTP Object that holds a SMTP Database Object but can also send emails.
    """

    def __init__(self, db_smtpserver_object):
        """
        Creates a new SMTPServer instance from a DB Server Object

        :param db_smtpserver_object: A DB STMTPserver object
        :return: A SMTP Server Object
        """
        self.config = db_smtpserver_object

    def send_email(self, recipient, subject, body, sender=None,
                   reply_to=None, mimetype="plain"):
        return send_or_enqueue_email(self.config.get(), recipient, subject, body, sender,
                                     reply_to, mimetype)

    @staticmethod
    @job(SEND_EMAIL_JOB_NAME)
    def test_email(config, recipient, subject, body, sender=None,
                   reply_to=None, mimetype="plain"):
        """
        Sends an email via the configuration.

        :param config: The email configuration
        :type config: dict
        :param recipient: The recipients of the email
        :type recipient: list
        :param subject: The subject of the email
        :type subject: basestring
        :param body: The body of the email
        :type body: basestring
        :param sender: An optional sender of the email. The SMTP database
            object has its own sender. This parameter can be used to override
            the internal sender.
        :type sender: basestring
        :param reply_to: The Reply-To parameter
        :type reply_to: basestring
        :param mimetype: The type of the email to send. Can by plain or html
        :return: True or False
        """
        if type(recipient) != list:
            recipient = [recipient]
        mail_from = sender or config['sender']
        reply_to = reply_to or mail_from
        msg = MIMEText(body.encode('utf-8'), mimetype, 'utf-8')
        msg['Subject'] = subject
        msg['From'] = mail_from
        msg['To'] = ",".join(recipient)
        msg['Date'] = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        msg['Reply-To'] = reply_to

        mail = smtplib.SMTP(config['server'], port=int(config['port']),
                            timeout=config.get('timeout', TIMEOUT))
        log.debug(u"submitting message to {0!s}".format(msg["To"]))
        log.debug("Saying EHLO to mailserver {0!s}".format(config['server']))
        r = mail.ehlo()
        log.debug("mailserver responded with {0!s}".format(r))
        # Start TLS if required
        if config.get('tls', False):
            log.debug("Trying to STARTTLS: {0!s}".format(config['tls']))
            mail.starttls()
        # Authenticate, if a username is given.
        if config.get('username', ''):
            log.debug("Doing authentication with {0!s}".format(config['username']))
            password = decryptPassword(config['password'])
            if password == FAILED_TO_DECRYPT_PASSWORD:
                password = config['password']
            mail.login(config['username'], password)
        r = mail.sendmail(mail_from, recipient, msg.as_string())
        log.info("Mail sent: {0!s}".format(r))
        # r is a dictionary like {"recp@destination.com": (200, 'OK')}
        # we change this to True or False
        success = True
        for one_recipient in recipient:
            res_id, res_text = r.get(one_recipient, (200, "OK"))
            if res_id != 200 and res_text != "OK":
                success = False
                log.error("Failed to send email to {0!r}: {1!r}, {2!r}".format(one_recipient,
                                                                  res_id,
                                                                  res_text))
        mail.quit()
        log.debug("I am done sending your email.")
        return success


def send_or_enqueue_email(config, recipient, subject, body, sender=None, reply_to=None, mimetype="plain"):
    """
    According to the value of ``config["enqueue_job"]``, send the email directly or send a job
    to the queue (if a queue is configured).
    See ``SMTPServer.test_email`` for parameters.
    :return: True if the job is sent to the queue, return value of ``SMTPServer.test_email`` otherwise
    """
    if has_job_queue() and config.get("enqueue_job", False):
        send = wrap_job(SEND_EMAIL_JOB_NAME, True)
    else:
        send = SMTPServer.test_email
    return send(config, recipient, subject, body, sender, reply_to, mimetype)


@log_with(log)
def send_email_identifier(identifier, recipient, subject, body, sender=None,
                          reply_to=None, mimetype="plain"):
    """
    Send the an email via the specified SMTP server configuration.

    :param identifier: The identifier of the SMTP server configuration
    :param recipient: The recipient of the email
    :param subject: The subject of the email
    :param body: The body of the email
    :type body: plain text
    :param sender: The optional sender of the email. The SMTP server
        configuration has its own sender. You can use this to override it.
    :param reply_to: Reply-To header
    :return: True or False
    """
    smtp_server = get_smtpserver(identifier)
    return smtp_server.send_email(recipient, subject, body, sender, reply_to,
                                  mimetype)


@log_with(log)
def send_email_data(mailserver, subject, message, mail_from,
                    recipient, username=None,
                    password=None, port=25, email_tls=False, timeout=TIMEOUT):
    """
    Send an email via the given email configuration data.

    :param mailserver: The mailserver
    :param subject: The subject of the email
    :param message: The body of the email
    :param mail_from: The sender of the email
    :param recipient: The recipient of the email
    :param username: The mailuser, if the SMTP server requires authentication
    :param password: The password, if the SMTP server requires authentication
    :param port: The mail server port
    :param email_tls: If the mailserver requires TLS
    :type email_tls: bool
    :return: True or False
    """
    dbserver = SMTPServerDB(identifier="emailtoken", server=mailserver,
                            sender=mail_from, username=username,
                            password=password, port=port, tls=email_tls, timeout=timeout,
                            enqueue_job=False)
    smtpserver = SMTPServer(dbserver)
    return smtpserver.send_email(recipient, subject, message)


@log_with(log)
def get_smtpserver(identifier):
    """
    This returns the SMTP Server object of the SMTP Server definition
    "identifier".
    In case the identifier does not exist, a ResourceNotFoundError is raised.

    :param identifier: The name of the SMTP server definition
    :return: A SMTP Server Object
    """
    return SMTPServer(fetch_one_resource(SMTPServerDB, identifier=identifier))


@log_with(log)
def get_smtpservers(identifier=None, server=None):
    """
    This returns a list of all smtpservers matching the criterion.
    If no identifier or server is provided, it will return a list of all smtp
    server definitions.

    :param identifier: The identifier or the name of the SMTPServer definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no smtpserver
    :type identifier: basestring
    :param server: The FQDN or IP address of the smtpserver
    :type server: basestring
    :return: list of SMTPServer Objects.
    """
    res = []
    sql_query = SMTPServerDB.query
    if identifier:
        sql_query = sql_query.filter(SMTPServerDB.identifier == identifier)
    if server:
        sql_query = sql_query.filter(SMTPServerDB.server == server)

    for row in sql_query.all():
        res.append(SMTPServer(row))

    return res


@log_with(log)
def add_smtpserver(identifier, server, port=25, username="", password="",
                   sender="", description="", tls=False, timeout=TIMEOUT,
                   enqueue_job=False):
    """
    This adds an smtp server to the smtp server database table.

    If the "identifier" already exists, the database entry is updated.

    :param identifier: The identifier or the name of the SMTPServer definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no smtpserver
    :type identifier: basestring
    :param server: The FQDN or IP address of the smtpserver
    :type server: basestring
    :return: The Id of the database object
    """
    cryptedPassword = encryptPassword(password)
    r = SMTPServerDB(identifier=identifier, server=server, port=port,
                     username=username, password=cryptedPassword, sender=sender,
                     description=description, tls=tls, timeout=timeout,
                     enqueue_job=enqueue_job).save()
    return r


@log_with(log)
def delete_smtpserver(identifier):
    """
    Delete the given server from the database.
    Raise a ResourceNotFoundError if it couldn't be found.
    :param identifier: The identifier/name of the server
    :return: The ID of the database entry, that was deleted
    """
    return fetch_one_resource(SMTPServerDB, identifier=identifier).delete()
