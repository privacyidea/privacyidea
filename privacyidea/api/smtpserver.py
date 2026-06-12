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

import logging

from flask import (Blueprint,
                   request)
from flask import g

from privacyidea.lib.smtpserver import (add_smtpserver, list_smtpservers,
                                        delete_smtpserver, send_or_enqueue_email)
from .lib.utils import (send_result)
from ..lib.params import get_optional, get_required
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.log import log_with
from ..lib.policies.actions import PolicyAction
from ..lib.crypto import censor_dict
from ..lib.utils import is_true

#: SMTP server fields that must never be returned in clear text by the API.
SMTPSERVER_SECRET_KEYS = {"password", "private_key_password"}

log = logging.getLogger(__name__)

smtpserver_blueprint = Blueprint('smtpserver_blueprint', __name__)


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
    :jsonparam password: SMTP auth password (stored encrypted).
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
    """
    param = request.all_data
    server = get_required(param, "server")
    port = int(get_optional(param, "port", default=25))
    username = get_optional(param, "username", default="")
    password = get_optional(param, "password", default="")
    sender = get_optional(param, "sender", default="")
    tls = is_true(get_optional(param, "tls", default=False))
    description = get_optional(param, "description", default="")
    timeout = int(get_optional(param, "timeout") or 10)
    enqueue_job = is_true(get_optional(param, "enqueue_job", default=False))
    smime = is_true(get_optional(param, "smime", default=False))
    dont_send_on_error = is_true(get_optional(param, "dont_send_on_error", default=False))
    private_key = get_optional(param, "private_key", default="")
    private_key_password = get_optional(param, "private_key_password")
    certificate = get_optional(param, "certificate", default="")

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
    :jsonparam password: SMTP auth password.
    :jsonparam sender: ``From:`` address used for the test message.
    :jsonparam tls: ``True`` to use STARTTLS, default ``False``.
    :jsonparam timeout: socket timeout in seconds, default ``10``.
    :jsonparam enqueue_job: if ``True``, the test mail is queued via the
        job queue instead of being sent inline. Default ``False``.
    :jsonparam smime: if ``True``, the test message is S/MIME-signed.
    :jsonparam dont_send_on_error: if ``True`` and S/MIME signing fails,
        the message is dropped instead of being sent unsigned.
    :jsonparam private_key: PEM-encoded S/MIME private key.
    :jsonparam private_key_password: passphrase for the S/MIME private key.
    :jsonparam certificate: PEM-encoded S/MIME certificate.
    :status 200: ``True`` if the message was delivered (or queued)
        successfully, ``False`` otherwise.
    """
    param = request.all_data
    identifier = get_required(param, "identifier")
    server = get_required(param, "server")
    port = int(get_optional(param, "port", default=25))
    username = get_optional(param, "username", default="")
    password = get_optional(param, "password", default="")
    sender = get_optional(param, "sender", default="")
    tls = is_true(get_optional(param, "tls", default=False))
    recipient = get_required(param, "recipient")
    timeout = int(get_optional(param, "timeout") or 10)
    enqueue_job = is_true(get_optional(param, "enqueue_job", default=False))
    smime = is_true(get_optional(param, "smime", default=False))
    dont_send_on_error = is_true(get_optional(param, "dont_send_on_error", default=False))
    private_key = get_optional(param, "private_key", default="")
    private_key_password = get_optional(param, "private_key_password", default="")
    certificate = get_optional(param, "certificate", default="")

    s = dict(identifier=identifier, server=server, port=port,
             username=username, password=password, sender=sender,
             tls=tls, timeout=timeout, enqueue_job=enqueue_job,
             smime=smime, dont_send_on_error=dont_send_on_error,
             private_key=private_key, private_key_password=private_key_password,
             certificate=certificate)
    r = send_or_enqueue_email(s, recipient,
                              "Test Email from privacyIDEA",
                              "This is a test email from privacyIDEA. "
                              f"The configuration {identifier} is working.")

    g.audit_object.log({'success': r > 0,
                        'info': r})
    return send_result(r > 0)
