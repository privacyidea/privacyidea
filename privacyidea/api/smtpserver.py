# http://www.privacyidea.org
# (c) Cornelius Kölbel
#
# 2015-12-27 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Implement REST API, create, update, delete, list
#            for SMTP server definitions
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
__doc__ = """
The SMTP-server REST API manages mail server definitions used by
privacyIDEA to send email — for the :ref:`email_token`, for SMS tokens
with an SMTP-to-SMS gateway, for the password recovery flow, for event
notifications, and for the user-self-registration flow. See
:ref:`smtpserver` for the conceptual chapter.

All endpoints require admin authentication. Read access is gated by the
admin policy action :ref:`policy_smtpserver_read`; create, update,
delete and the test send are gated by :ref:`policy_smtpserver_write`.
"""

import email.errors
import logging
import smtplib
import socket
import ssl

from flask import (Blueprint,
                   request)
from flask import g

from privacyidea.lib.smtpserver import (add_smtpserver, list_smtpservers,
                                        delete_smtpserver, send_or_enqueue_email, replace_censored_secrets,
                                        parse_server_address)
from .lib.utils import (send_result)
from ..lib.params import get_optional, get_required
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.log import log_with
from ..lib.policies.actions import PolicyAction
from ..lib.crypto import censor_dict
from ..lib.error import ConfigAdminError, ParameterError
from ..lib.utils import is_true

#: SMTP server fields that must never be returned in clear text by the API.
SMTPSERVER_SECRET_KEYS = {"password", "private_key_password"}

log = logging.getLogger(__name__)

smtpserver_blueprint = Blueprint('smtpserver_blueprint', __name__)


def _parse_number(value, name: str, default: int, minimum: int, maximum: int) -> int:
    """
    Parse a numeric request parameter.

    :raises ParameterError: if the value is not a whole number between minimum and maximum
    """
    if value in (None, ""):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ParameterError(f"The {name} must be a number, not {value!r}.")
    if not minimum <= number <= maximum:
        raise ParameterError(f"The {name} must be between {minimum} and {maximum}, not {number}.")
    return number


def _server_address(server: str, port: int) -> tuple[str, int]:
    """
    Determine host and port with :func:`parse_server_address`, which the sending code uses as well.

    :raises ParameterError: if the server URL has no host name or no valid port
    """
    try:
        _scheme, host, port = parse_server_address(server, port)
    except ValueError:
        raise ParameterError(f"The port in the server {server!r} must be a number between 1 and 65535.")
    if not host:
        raise ParameterError(f"The server {server!r} does not contain a host name.")
    return host, port


def _check_email_address(address: str, name: str) -> None:
    """
    Reject an email address that can not be put into the message header or the SMTP envelope.

    :raises ParameterError: if the address contains control characters or non-ASCII characters
    """
    if any(ord(character) < 32 or ord(character) == 127 for character in address):
        raise ParameterError(f"The {name} must not contain line breaks or other control characters.")
    if not address.isascii():
        raise ParameterError(f"The {name} {address!r} contains non-ASCII characters. "
                             f"privacyIDEA can only send emails from and to ASCII addresses.")


def _smtp_reply(error: smtplib.SMTPResponseException) -> str:
    """Format the SMTP reply of an error as "<code> <text>"."""
    text = error.smtp_error
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    return f"{error.smtp_code} {text}"


def _describe_smtp_error(error: Exception, server: str, port: int, username: str, timeout: int) -> str:
    """
    Turn an exception raised while talking to a mail server into a message an administrator can act on.

    :param error: the exception raised by smtplib, the socket layer or the email package
    :param server: the server as configured, possibly with an ``smtp://`` or ``smtps://`` scheme
    :param port: the configured port, used if the server does not contain one
    :param username: the SMTP user
    :param timeout: the socket timeout in seconds
    :return: the message
    """
    host, port = _server_address(server, port)
    address = f"{host}:{port}"
    tls_hint = "Check whether port and TLS mode (smtps:// or STARTTLS) match."

    if isinstance(error, smtplib.SMTPAuthenticationError):
        return f"Authentication failed for user '{username}': {_smtp_reply(error)}"
    if isinstance(error, smtplib.SMTPNotSupportedError):
        if "STARTTLS" in str(error):
            return "The server does not support STARTTLS."
        if "AUTH" in str(error):
            return ("The server does not support authentication (SMTP AUTH). "
                    "Check whether TLS must be enabled.")
        return f"The server does not support a required extension: {error}"
    if isinstance(error, smtplib.SMTPSenderRefused):
        return f"The server refused the sender '{error.sender}': {_smtp_reply(error)}"
    if isinstance(error, smtplib.SMTPRecipientsRefused):
        refused = ", ".join(f"'{recipient}': {_smtp_reply(smtplib.SMTPResponseException(*reply))}"
                            for recipient, reply in error.recipients.items())
        return f"The server refused the recipient {refused}"
    if isinstance(error, smtplib.SMTPDataError):
        return f"The server rejected the message: {_smtp_reply(error)}"
    if isinstance(error, smtplib.SMTPServerDisconnected):
        return f"The server closed the connection unexpectedly. {tls_hint}"
    if isinstance(error, smtplib.SMTPResponseException):
        return f"SMTP error {_smtp_reply(error)}"
    if isinstance(error, smtplib.SMTPException):
        return f"SMTP error: {error}"
    if isinstance(error, socket.gaierror):
        return f"Could not resolve the host name '{host}'."
    if isinstance(error, ConnectionRefusedError):
        return f"Could not connect to {address}: connection refused."
    if isinstance(error, TimeoutError):
        return f"Connection to {address} timed out after {timeout} seconds."
    if isinstance(error, ssl.SSLCertVerificationError):
        return f"TLS error: certificate verify failed: {error.verify_message}"
    if isinstance(error, ssl.SSLError):
        hint = f" {tls_hint}" if error.reason == "WRONG_VERSION_NUMBER" else ""
        return f"TLS error: {error.reason or error}.{hint}"
    if isinstance(error, email.errors.MessageError):
        return f"The email could not be created: {error}"
    if isinstance(error, OSError):
        return f"Could not connect to {address}: {error.strerror or error}"
    return f"The email could not be sent: {error}"


@smtpserver_blueprint.route('/<identifier>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.SMTPSERVERWRITE)
@log_with(log)
def create(identifier=None):
    """
    Create or update an SMTP server definition. If a definition with the
    given ``identifier`` already exists it is updated; otherwise it is
    created.

    Requires admin authentication and the policy action
    :ref:`policy_smtpserver_write`.

    :param identifier: path component, the unique name of the definition.
    :jsonparam server: hostname or IP of the mail server (required).
    :jsonparam port: TCP port of the mail server, default ``25``.
    :jsonparam username: SMTP auth user. Empty string disables auth.
    :jsonparam password: SMTP auth password (stored encrypted). The
        ``__CENSORED__`` placeholder returned by ``GET /smtpserver/`` keeps the
        stored password, but only if ``server``, ``port``, ``username`` and
        ``tls`` stay the same. Otherwise the password has to be entered again.
    :jsonparam sender: ``From:`` address used when sending mail through
        this server.
    :jsonparam tls: ``True`` to use STARTTLS, ``False`` (default) for plain.
    :jsonparam timeout: socket timeout in seconds, default ``10``.
    :jsonparam enqueue_job: if ``True``, mail is queued via the privacyIDEA
        job queue instead of being sent inline. Default ``False``.
    :jsonparam description: free-form description.
    :jsonparam smime: if ``True``, outgoing mail is S/MIME-signed using the
        configured key/certificate.
    :jsonparam dont_send_on_error: if ``True`` and S/MIME signing fails,
        the mail is dropped instead of being sent unsigned.
    :jsonparam private_key: PEM-encoded private key for S/MIME signing.
    :jsonparam private_key_password: passphrase for the S/MIME private key.
    :jsonparam certificate: PEM-encoded certificate for S/MIME signing.
    :status 200: ``True`` on success.
    :status 400: a parameter is invalid (e.g. a port outside 1-65535 or a
        sender with a line break or non-ASCII characters), or the password is
        censored, but the connection settings differ from the saved definition.
    """
    param = request.all_data
    server = get_required(param, "server")
    port = _parse_number(get_optional(param, "port"), "port", 25, 1, 65535)
    # Not passed, the user name, the sender, the description, the private key and the certificate of an existing
    # server keep their stored values
    username = get_optional(param, "username")
    password = get_optional(param, "password", default="")
    sender = get_optional(param, "sender")
    tls = is_true(get_optional(param, "tls", default=False))
    description = get_optional(param, "description")
    timeout = _parse_number(get_optional(param, "timeout"), "timeout", 10, 1, 3600)
    enqueue_job = is_true(get_optional(param, "enqueue_job", default=False))
    smime = is_true(get_optional(param, "smime", default=False))
    dont_send_on_error = is_true(get_optional(param, "dont_send_on_error", default=False))
    private_key = get_optional(param, "private_key")
    private_key_password = get_optional(param, "private_key_password")
    certificate = get_optional(param, "certificate")

    # A definition that can not be used to send an email is not saved.
    _server_address(server, port)
    if sender:
        _check_email_address(sender, "sender")

    r = add_smtpserver(identifier, server, port=port, username=username,
                       password=password, tls=tls, description=description,
                       sender=sender, timeout=timeout, enqueue_job=enqueue_job,
                       smime=smime, dont_send_on_error=dont_send_on_error,
                       private_key=private_key, private_key_password=private_key_password,
                       certificate=certificate)

    g.audit_object.log({'success': r > 0,
                        'info': r})
    return send_result(r > 0)


@smtpserver_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.SMTPSERVERREAD)
def list_smtpservers_api():
    """
    Return all SMTP server definitions known to this server.

    The result is a dictionary keyed by ``identifier``; each value contains
    ``server``, ``port``, ``username``, ``password``, ``sender``, ``tls``,
    ``timeout``, ``enqueue_job``, ``description``, ``smime``,
    ``dont_send_on_error``, ``private_key``, ``private_key_password`` and
    ``certificate``.

    Secret values are not returned in clear text: ``password`` and
    ``private_key_password`` are replaced by the placeholder ``__CENSORED__``.
    (``private_key`` holds the *path* to the S/MIME key file, not key material,
    so it is returned unchanged.) When updating a server, submit ``__CENSORED__``
    for a secret to keep its stored value, an empty string to clear it, or a new
    value to change it.

    Requires admin authentication and the policy action
    :ref:`policy_smtpserver_read`.

    :status 200: dict of definitions in ``result.value``.
    """
    res = list_smtpservers()
    # Do not expose secrets in the API response
    for identifier, data in res.items():
        res[identifier] = censor_dict(data, SMTPSERVER_SECRET_KEYS)
    g.audit_object.log({'success': True})
    return send_result(res)


@smtpserver_blueprint.route('/<identifier>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.SMTPSERVERWRITE)
@log_with(log)
def delete_server(identifier=None):
    """
    Delete the SMTP server definition with the given identifier.

    Requires admin authentication and the policy action
    :ref:`policy_smtpserver_write`.

    :param identifier: path component, the name of the definition.
    :status 200: ``True`` if a definition was deleted, ``False`` otherwise.
    """
    r = delete_smtpserver(identifier)

    g.audit_object.log({'success': r > 0,
                        'info': r})
    return send_result(r > 0)


@smtpserver_blueprint.route('/send_test_email', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.SMTPSERVERWRITE)
@log_with(log)
def test():
    """
    Send a real test email through the supplied SMTP configuration. The
    configuration does not need to be saved first — all connection
    parameters are taken from the request body, and a fixed test message
    is delivered to ``recipient``.

    Requires admin authentication and the policy action
    :ref:`policy_smtpserver_write`.

    :jsonparam identifier: identifier under which the definition would be
        saved (used in the test message body and in the audit log).
    :jsonparam recipient: email address to deliver the test message to
        (required).
    :jsonparam server: hostname or IP of the mail server (required).
    :jsonparam port: TCP port, default ``25``.
    :jsonparam username: SMTP auth user.
    :jsonparam password: SMTP auth password. ``__CENSORED__``, as ``GET /smtpserver/`` returns it, uses the stored
        password of the definition ``identifier``, but only if ``server``, ``port``, ``username`` and ``tls``
        match the definition. Otherwise the password has to be entered again.
    :jsonparam sender: ``From:`` address used for the test message.
    :jsonparam tls: ``True`` to use STARTTLS, default ``False``.
    :jsonparam timeout: socket timeout in seconds, default ``10``.
    :jsonparam enqueue_job: if ``True``, the test mail is queued via the
        job queue instead of being sent inline. Default ``False``.
    :jsonparam smime: if ``True``, the test message is S/MIME-signed.
    :jsonparam dont_send_on_error: if ``True`` and S/MIME signing fails,
        the message is dropped instead of being sent unsigned.
    :jsonparam private_key: PEM-encoded S/MIME private key.
    :jsonparam private_key_password: passphrase for the S/MIME private key. ``__CENSORED__`` uses the stored
        passphrase of the definition ``identifier``.
    :jsonparam certificate: PEM-encoded S/MIME certificate.
    :status 200: ``True`` if the message was delivered (or queued)
        successfully. A queued message is sent by the job queue worker, which
        only logs a failure.
    :status 400: the message could not be sent, a parameter is invalid (e.g.
        a port outside 1-65535 or an address with a line break or non-ASCII
        characters), or the password is censored but the connection settings
        differ from the saved configuration. The error message says why.
    """
    param = request.all_data
    identifier = get_required(param, "identifier")
    server = get_required(param, "server")
    port = _parse_number(get_optional(param, "port"), "port", 25, 1, 65535)
    username = get_optional(param, "username", default="")
    password = get_optional(param, "password", default="")
    sender = get_optional(param, "sender", default="")
    tls = is_true(get_optional(param, "tls", default=False))
    recipient = get_required(param, "recipient")
    timeout = _parse_number(get_optional(param, "timeout"), "timeout", 10, 1, 3600)
    enqueue_job = is_true(get_optional(param, "enqueue_job", default=False))
    smime = is_true(get_optional(param, "smime", default=False))
    dont_send_on_error = is_true(get_optional(param, "dont_send_on_error", default=False))
    private_key = get_optional(param, "private_key", default="")
    private_key_password = get_optional(param, "private_key_password", default="")
    certificate = get_optional(param, "certificate", default="")

    # Reject what smtplib and the email package would fail on with an exception of their own.
    _server_address(server, port)
    _check_email_address(recipient, "recipient")
    if sender:
        _check_email_address(sender, "sender")

    # The edit dialog sends back the placeholder that GET /smtpserver/ returned for a stored secret
    password, private_key_password = replace_censored_secrets(identifier, password, private_key_password,
                                                              server=server, port=port, username=username, tls=tls)

    s = dict(identifier=identifier, server=server, port=port,
             username=username, password=password, sender=sender,
             tls=tls, timeout=timeout, enqueue_job=enqueue_job,
             smime=smime, dont_send_on_error=dont_send_on_error,
             private_key=private_key, private_key_password=private_key_password,
             certificate=certificate)
    try:
        r = send_or_enqueue_email(s, recipient,
                                  "Test Email from privacyIDEA",
                                  "This is a test email from privacyIDEA. "
                                  f"The configuration {identifier} is working.")
    except (smtplib.SMTPException, OSError, ValueError, email.errors.MessageError) as error:
        message = _describe_smtp_error(error, server, port, username, timeout)
        log.warning(f"Sending the test email via {identifier!r} failed: {message}")
        raise ConfigAdminError(message)
    if not r:
        if smime and dont_send_on_error:
            raise ConfigAdminError("The S/MIME signature could not be created, so the email was not sent. "
                                   "See the server log for details.")
        raise ConfigAdminError(f"The server did not accept the message for {recipient}.")

    g.audit_object.log({'success': True,
                        'info': r})
    return send_result(True)
