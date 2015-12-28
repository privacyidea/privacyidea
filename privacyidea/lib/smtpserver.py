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
from privacyidea.models import SMTPServer as SMTPServerDB
from privacyidea.lib.crypto import decryptPassword, encryptPassword
import logging
from privacyidea.lib.log import log_with
import datetime
import smtplib
from privacyidea.lib.error import ConfigAdminError
__doc__ = """
This is the library for creating, listing and deleting SMTPServer objects in
the Database.

It depends on the SMTPServer in the database model models.py. This module can
be tested standalone without any webservices.
This module is tested in tests/test_lib_smtpserver.py
"""

log = logging.getLogger(__name__)


class SMTPServer(object):
    """
    SMTP Object that holds a SMTP Database Object but can also send emails.
    """

    def __init__(self, dbSMTPServer):
        """
        Creates a new SMTPServer instance from a DB Server Object

        :param dbSMTPServer:
        :return: A SMTP Server Object
        """
        self.config = dbSMTPServer

    def send_email(self, recipient, subject, body, sender=None):
        return self.test_email(self.config, recipient, subject, body, sender)

    @staticmethod
    def test_email(config, recipient, subject, body, sender=None):
        """
        Sends an email via the SMTP Database Object

        :param config: The email configuration
        :type config: SMTPServer Database Model
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
        :return: A dictionary of recipients and tuples like
            {"recp@destination.com": (200, 'OK')}
        """
        mail_from = sender or config.sender
        date = datetime.datetime.utcnow().strftime("%c")
        body = """From: %s
Subject: %s
Date: %s

%s""" % (mail_from, subject, date, body)

        mail = smtplib.SMTP(config.server, port=int(config.port))
        mail.ehlo()
        # Start TLS if required
        if config.tls:
            mail.starttls()
        # Authenticate, if a username is given.
        if config.username:
            password = decryptPassword(config.password)
            mail.login(config.username, password)
        r = mail.sendmail(mail_from, recipient, body)
        mail.quit()
        return r


@log_with(log)
def get_smtpserver(identifier):
    """
    This returns the SMTP Server object of the SMTP Server definition
    "identifier".
    In case the identifier does not exist, an exception is raised.

    :param identifier: The name of the SMTP server definition
    :return: A SMTP Server Object
    """
    server_list = get_smtpservers(identifier=identifier)
    if not server_list:
        raise ConfigAdminError("The specified SMTP server configuration does "
                               "not exist.")
    return server_list[0]

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
                    sender="", description="", tls=False):
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
                     description=description, tls=tls).save()
    return r

@log_with(log)
def delete_smtpserver(identifier):
    """
    Delete the given server from the database
    :param identifier: The identifier/name of the server
    :return: The ID of the database entry, that was deleted
    """
    ret = -1
    smtp = SMTPServerDB.query.filter(SMTPServerDB.identifier ==
                                     identifier).first()
    if smtp:
        smtp.delete()
        ret = smtp.id
    return ret

