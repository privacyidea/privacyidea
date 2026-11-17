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
import logging
import smtplib
import time
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import parseaddr
from time import gmtime, strftime
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from flask import current_app
from sqlalchemy import select

from privacyidea.lib.crypto import (decryptPassword, encryptPassword,
                                    FAILED_TO_DECRYPT_PASSWORD, is_censored, censor_dict)
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.metrics import inc, observe
from privacyidea.lib.queue import job, wrap_job, has_job_queue
from privacyidea.lib.utils import check_stored_secret_settings, fetch_one_resource, to_unicode, validate_path_identifier
from privacyidea.lib.utils.export import (register_import, register_export, get_import_names, import_entries)
from privacyidea.models import SMTPServer as SMTPServerDB, db

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


def parse_server_address(server: str, port) -> tuple[str, str | None, int]:
    """
    Determine the scheme, host and port an SMTP server definition connects to.

    The server can be a host name, an IP address or a URL like ``smtp://host:port`` or
    ``smtps://host:port``. A port in the URL takes precedence over the port parameter.

    :param server: the server as configured
    :param port: the configured port, used if the server URL does not contain one
    :return: the scheme ("smtp" or "smtps"), the host name (None if the URL has none) and the port
    :raises ValueError: if the port in the server URL is not a number between 0 and 65535
    """
    # urllib looks for a '//' to identify the host in the string. If it is
    # missing we add one.
    url = urlparse(server if "//" in server else f"//{server}", scheme="smtp")
    return url.scheme, url.hostname, url.port or int(port)


def check_number(value, name: str, minimum: int, maximum: int) -> int:
    """
    Convert a numeric setting to an int and check its range.

    :param value: the value, an int, a float without fraction or a string
    :param name: the name of the setting, used in the error message
    :param minimum: the smallest allowed value
    :param maximum: the largest allowed value
    :return: the value as int
    :raises ParameterError: if the value is not a whole number between minimum and maximum
    """
    # int() would also accept True as 1 and cut off the fraction of a float
    if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
        raise ParameterError(f"The {name} must be a whole number, not {value!r}.")
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        raise ParameterError(f"The {name} must be a whole number, not {value!r}.")
    if not minimum <= number <= maximum:
        raise ParameterError(f"The {name} must be between {minimum} and {maximum}, not {number}.")
    return number


def check_server_address(server: str, port) -> tuple[str, int]:
    """
    Determine host and port with :func:`parse_server_address` and make sure an email can be sent to them.

    :param server: the server as configured
    :param port: the configured port, used if the server URL does not contain one
    :return: the host name and the port
    :raises ParameterError: if the server URL has no host name or no valid port
    """
    try:
        _scheme, host, port = parse_server_address(server, port)
    except ValueError:
        raise ParameterError(f"The port in the server {server!r} must be a number between 1 and 65535.")
    if not host:
        raise ParameterError(f"The server {server!r} does not contain a host name.")
    return host, port


def check_email_address(address: str, name: str) -> None:
    """
    Reject an email address that can not be put into the message header or the SMTP envelope.

    :param address: the email address, optionally with a display name like ``Name <user@example.com>``
    :param name: the name of the setting, used in the error message
    :raises ParameterError: if the address contains control characters, or if the address or the display name
        contains non-ASCII characters
    """
    if any(ord(character) < 32 or ord(character) == 127 for character in address):
        raise ParameterError(f"The {name} must not contain line breaks or other control characters.")
    if not address.isascii():
        # parseaddr() returns two empty strings for a value it can not parse, e.g. a list of two addresses
        display_name, mail_address = parseaddr(address)
        if not display_name.isascii() and mail_address.isascii():
            raise ParameterError(f"The display name {display_name!r} of the {name} contains non-ASCII characters. "
                                 f"privacyIDEA can only send emails with an ASCII display name.")
        raise ParameterError(f"The {name} {address!r} contains non-ASCII characters. "
                             f"privacyIDEA can only send emails from and to ASCII addresses.")


def _get_mail_debug_level():
    try:
        return int(current_app.config.get("PI_MAIL_DEBUG_LEVEL", 0))
    except (RuntimeError, ValueError, TypeError):
        return 0


class SMTPServer:
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
        :type recipient: list or str
        :param subject: The subject of the email
        :type subject: basestring
        :param body: The body of the email
        :type body: email.mime.base.MIMEBase or str
        :param sender: An optional sender of the email. The SMTP database
            object has its own sender. This parameter can be used to override
            the internal sender.
        :type sender: basestring
        :param reply_to: The Reply-To parameter
        :type reply_to: basestring
        :param mimetype: The type of the email to send. Can by plain or html
        :return: True or False
        """
        if not isinstance(recipient, list):
            recipient = [recipient]
        mail_from = sender or config['sender']
        reply_to = reply_to or mail_from
        if isinstance(body, MIMEBase):
            msg = body
        else:
            msg = MIMEText(to_unicode(body), mimetype, 'utf-8')
        msg['Subject'] = subject
        msg['From'] = mail_from
        msg['To'] = ",".join(recipient)
        msg['Date'] = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        msg['Reply-To'] = reply_to

        scheme, host, port = parse_server_address(config['server'], config['port'])
        if scheme == 'smtps':
            mail = smtplib.SMTP_SSL(host, port=port, timeout=config.get('timeout', TIMEOUT))
        else:
            mail = smtplib.SMTP(host, port=port, timeout=config.get('timeout', TIMEOUT))
        debug_level = _get_mail_debug_level()
        if debug_level:
            mail.set_debuglevel(debug_level)
        log.debug(f"submitting message to {msg['To']!s}")
        log.debug(f"Saying EHLO to mailserver {config['server']!s}")
        r = mail.ehlo()
        log.debug(f"mailserver responded with {r!s}")
        # Start TLS if required
        if not scheme == 'smtps' and config.get('tls', False):
            log.debug("Trying to STARTTLS: {!s}".format(config['tls']))
            mail.starttls()
        # Authenticate, if a username is given.
        if config.get('username', ''):
            log.debug("Doing authentication with {!s}".format(config['username']))
            password = decryptPassword(config['password'])
            if password == FAILED_TO_DECRYPT_PASSWORD:
                password = config['password']
            mail.login(config['username'], password)
        msg = msg.as_string()
        if config.get('smime', False):
            try:
                msg = msg.encode("utf-8")
                with open(config['private_key'], "rb") as key_file:
                    private_key = key_file.read()
                with open(config['certificate'], "rb") as cert_file:
                    certificate = cert_file.read()
                key_password = config.get('private_key_password')
                if key_password:
                    key_password_decrypted = decryptPassword(key_password)
                    if key_password_decrypted == FAILED_TO_DECRYPT_PASSWORD:
                        key_password_decrypted = key_password
                    if isinstance(key_password_decrypted, str):
                        key_password_bytes = key_password_decrypted.encode("utf-8")
                    else:
                        key_password_bytes = key_password_decrypted
                else:
                    key_password_bytes = None
                key = serialization.load_pem_private_key(private_key, key_password_bytes)
                cert = x509.load_pem_x509_certificate(certificate)
                options = [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.NoAttributes]
                msg = pkcs7.PKCS7SignatureBuilder().set_data(msg).add_signer(cert, key, hashes.SHA256()).sign(
                    serialization.Encoding.SMIME, options)
            except Exception as ex:
                abort = config.get('dont_send_on_error')
                action = "not be sent" if abort else "be sent anyway"
                log.error(f"Can't create S/MIME signature: {ex}. Email will {action}")
                if abort:
                    return False
        r = mail.sendmail(mail_from, recipient, msg)
        log.info(f"Mail sent: {r!s}")
        # r is a dictionary like {"recp@destination.com": (200, 'OK')}
        # we change this to True or False
        success = True
        for one_recipient in recipient:
            res_id, res_text = r.get(one_recipient, (200, "OK"))
            if res_id != 200 and res_text != "OK":
                success = False
                log.error(f"Failed to send email to {one_recipient!r}: {res_id!r}, {res_text!r}")
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


def _record_email_send(identifier, start, success, error=False):
    labels = {"identifier": identifier}
    observe("email_send_duration_seconds", time.monotonic() - start, labels)
    if error:
        result = "error"
    else:
        result = "ok" if success else "failed"
    inc("email_send_total", {**labels, "result": result})


# The subject and the body can hold an OTP, a registration code or the link to reset a password
@log_with(log, hide_args=["subject", "body"])
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
    start = time.monotonic()
    try:
        success = smtp_server.send_email(recipient, subject, body, sender, reply_to,
                                         mimetype)
    except Exception:
        _record_email_send(identifier, start, False, error=True)
        raise
    _record_email_send(identifier, start, success)
    return success


@log_with(log, hide_args=["subject", "message"])
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
    start = time.monotonic()
    try:
        success = smtpserver.send_email(recipient, subject, message)
    except Exception:
        _record_email_send("emailtoken", start, False, error=True)
        raise
    _record_email_send("emailtoken", start, success)
    return success


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
    stmt = select(SMTPServerDB)
    if identifier:
        stmt = stmt.filter(SMTPServerDB.identifier == identifier)
    if server:
        stmt = stmt.filter(SMTPServerDB.server == server)

    for row in db.session.scalars(stmt).all():
        res.append(SMTPServer(row))

    return res


@log_with(log, log_exit=False)
def list_smtpservers(identifier=None, server=None):
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
    :return: list of SMTPServer configuration dicts.
    """
    res = {}
    # get list of smtpserver objects
    server_obj_list = get_smtpservers(identifier=identifier, server=server)
    # transfer the definitions to a dictionary
    for server_obj in server_obj_list:
        decrypted_password = decryptPassword(server_obj.config.password)
        # If the database contains garbage, use the empty password as fallback
        if decrypted_password == FAILED_TO_DECRYPT_PASSWORD:
            decrypted_password = ""  # nosec B105 # reset password in case of error
        res[server_obj.config.identifier] = server_obj.config.get()
        res[server_obj.config.identifier].pop('id')
        res[server_obj.config.identifier].pop('identifier')
        res[server_obj.config.identifier].update({"password": decrypted_password})

    return res


@log_with(log)
def check_censored_password(identifier: str, saved: dict, action: str, server: str | None = None,
                            port: int | None = None, username: str | None = None, tls: bool | None = None) -> None:
    """
    Make sure a stored password is only used for the server it was saved for.

    A client that never received the password sends the ``__CENSORED__`` placeholder instead, which
    means "use the stored password". The stored password is only used if the request keeps the server,
    the port, the username and the TLS flag of the saved configuration. A value of ``None`` means the
    setting is not changed. If no password is stored, any setting can be changed.

    :param identifier: the identifier of the saved SMTP server
    :param saved: the saved configuration, as returned by ``SMTPServerDB.get()``
    :param action: what the password is needed for, used in the error message (e.g. "save")
    :param server: the requested server
    :param port: the requested port
    :param username: the requested username
    :param tls: the requested TLS flag
    :raises ParameterError: if one of the settings differs from the saved configuration
    """
    if not saved.get("password") or decryptPassword(saved["password"]) == "":
        return
    saved_settings = {"server": saved.get("server"), "port": saved.get("port"),
                      "username": saved.get("username") or "", "tls": bool(saved.get("tls"))}
    requested = {"server": server, "port": port, "username": username, "tls": tls}
    check_stored_secret_settings("SMTP server", identifier, saved_settings, requested, "password", action)


def add_smtpserver(identifier, server: str = None, port: int = 25, username: str = "", password: str = "",
                   sender: str = "", description: str = "", tls: bool = False, timeout: int = TIMEOUT,
                   enqueue_job: bool = False, smime: bool = False, dont_send_on_error: bool = False,
                   private_key: str = "", private_key_password: str | None = None, certificate: str = ""):
    """
    This adds an smtp server to the smtp server database table.

    If the "identifier" already exists, the database entry is updated.

    :param identifier: The identifier or the name of the SMTPServer definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no smtpserver
    :type identifier: basestring
    :param server: The FQDN or IP address of the smtpserver
    :type server: basestring
    :param password: The password. ``__CENSORED__`` keeps the stored password, but only if
        server, port, username and tls stay the same.
    :return: The Id of the database object
    :raises ParameterError: if the password is ``__CENSORED__`` and server, port, username or
        tls differ from the saved configuration, or if server, port, timeout or sender can not be
        used to send an email
    """
    # POST /smtpserver/send_test_email is the test endpoint, not the server of that name
    validate_path_identifier(identifier, "SMTP server", reserved=("send_test_email",))
    # A definition that can not be used to send an email is not saved. None keeps the stored value.
    if port is not None:
        port = check_number(port, "port", 1, 65535)
    if timeout is not None:
        timeout = check_number(timeout, "timeout", 1, 3600)
    if server is not None:
        check_server_address(server, port if port is not None else 25)
    if sender:
        check_email_address(sender, "sender")

    stmt = select(SMTPServerDB).filter(SMTPServerDB.identifier == identifier)
    smtp_server = db.session.execute(stmt).scalar_one_or_none()

    # The CENSORED placeholder (what the API returned for the password) means
    # "keep the stored password unchanged" -> leave encrypted_password = None so
    # the update below skips the column. An empty string clears the password, any
    # other value sets it.
    if is_censored(password):
        if smtp_server:
            check_censored_password(identifier, smtp_server.get(), "save", server=server, port=port,
                                    username=username, tls=tls)
        encrypted_password = None
    else:
        encrypted_password = encryptPassword(password)
    if is_censored(private_key_password):
        private_key_password = None

    # private_key_password could be empty string or None, which have a different effect later.
    # here we only care if it has an actual value that we should encrypt, otherwise leave it at empty string or None
    encrypted_private_key_password = private_key_password
    if private_key_password:
        encrypted_private_key_password = encryptPassword(private_key_password)

    if smtp_server:
        # Update existing entry
        if server is not None:
            smtp_server.server = server
        if port is not None:
            smtp_server.port = port
        if username is not None:
            smtp_server.username = username
        if encrypted_password is not None:
            smtp_server.password = encrypted_password
        if sender is not None:
            smtp_server.sender = sender
        if tls is not None:
            smtp_server.tls = tls
        if description is not None:
            smtp_server.description = description
        if timeout is not None:
            smtp_server.timeout = timeout
        if enqueue_job is not None:
            smtp_server.enqueue_job = enqueue_job
        if smime is not None:
            smtp_server.smime = smime
        if dont_send_on_error is not None:
            smtp_server.dont_send_on_error = dont_send_on_error
        if private_key is not None:
            smtp_server.private_key = private_key
        if encrypted_private_key_password is not None:
            smtp_server.private_key_password = encrypted_private_key_password
        if certificate is not None:
            smtp_server.certificate = certificate
    else:
        # Create new entry
        smtp_server = SMTPServerDB(identifier=identifier, server=server, port=port, username=username,
                                   password=encrypted_password, sender=sender, description=description, tls=tls,
                                   timeout=timeout, enqueue_job=enqueue_job, smime=smime,
                                   dont_send_on_error=dont_send_on_error, private_key=private_key,
                                   private_key_password=encrypted_private_key_password, certificate=certificate)
        db.session.add(smtp_server)
    db.session.commit()
    return smtp_server.id


def replace_censored_secrets(identifier: str, password: str, private_key_password: str, *,
                             server: str | None = None, port: int | None = None, username: str | None = None,
                             tls: bool | None = None) -> tuple[str, str]:
    """
    Replace the CENSORED placeholder of the password and of the S/MIME key password with the stored, encrypted value
    of the SMTP server definition *identifier*, as saving the definition keeps it. The sending code decrypts a stored
    value. A placeholder for a definition that does not exist becomes an empty value.

    The stored password is only used if server, port, username and tls match the definition, see
    :func:`check_censored_password`.

    :param identifier: the identifier of the SMTP server definition
    :param password: the password as the request sent it
    :param private_key_password: the S/MIME key password as the request sent it
    :param server: the server the password is sent to
    :param port: the port the password is sent to
    :param username: the username the password is sent with
    :param tls: whether the password is sent with STARTTLS
    :return: the password and the S/MIME key password to send with
    :raises ParameterError: if the password is censored and one of the settings differs from the definition
    """
    if not (is_censored(password) or is_censored(private_key_password)):
        return password, private_key_password
    stored_servers = get_smtpservers(identifier=identifier)
    stored = stored_servers[0].config if stored_servers else None
    if is_censored(password):
        if stored:
            check_censored_password(identifier, stored.get(), "test", server=server, port=port,
                                    username=username, tls=tls)
        password = stored.password if stored else ""
    if is_censored(private_key_password):
        private_key_password = (stored.private_key_password or "") if stored else ""
    return password, private_key_password


@log_with(log)
def delete_smtpserver(identifier):
    """
    Delete the given server from the database.
    Raise a ResourceNotFoundError if it couldn't be found.
    :param identifier: The identifier/name of the server
    :return: The ID of the database entry, that was deleted
    """
    return fetch_one_resource(SMTPServerDB, identifier=identifier).delete()


@register_export('smtpserver')
def export_smtpserver(name=None, censor=False):
    """ Export given or all SMTP server configuration

    :param censor: If True, the password and private key password are replaced
        with the ``__CENSORED__`` placeholder instead of being returned in
        clear text.
    """
    res = list_smtpservers(identifier=name)
    for identifier, server in res.items():
        if censor:
            # The secret values are about to be replaced by the placeholder, so
            # there is no point decrypting private_key_password first.
            secret_keys = [key for key in ("password", "private_key_password") if server.get(key)]
            res[identifier] = censor_dict(server, secret_keys)
            continue
        # list_smtpservers() decrypts 'password' but returns 'private_key_password'
        # still encrypted. Decrypt it here so that a (non-censored) export can be
        # re-imported without add_smtpserver() encrypting it a second time.
        if server.get("private_key_password"):
            decrypted = decryptPassword(server["private_key_password"])
            server["private_key_password"] = "" if decrypted == FAILED_TO_DECRYPT_PASSWORD else decrypted
    return res


@register_import('smtpserver')
def import_smtpserver(data, name=None):
    """Import SMTP server configuration

    Each SMTP server is imported independently. If a single server cannot be
    imported (e.g. because its identifier is not valid), the remaining servers
    are still imported and a ``ConfigAdminError`` summarizing the failures is
    raised after all servers have been processed.
    """
    log.debug(f'Import SMTP server config: {get_import_names(data)}')
    entries = [(res_name, res_data) for res_name, res_data in data.items() if not name or name == res_name]
    import_entries(entries, lambda res_name, res_data: add_smtpserver(res_name, **res_data), "SMTP servers")
