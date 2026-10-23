# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
__doc__ = """
The webhook REST API manages webhook definitions: reusable HTTP endpoints
that privacyIDEA can call from an event handler or a Conditional Access
stage action.

A webhook object owns the *endpoint* -- URL, HTTP method, authentication,
static headers, TLS and proxy settings, timeout. The *call site* owns the
payload and references the webhook by its identifier.

All endpoints require admin authentication. Read access is gated by the
admin policy action :ref:`policy_webhook_read`; create, update, delete and
the test request are gated by :ref:`policy_webhook_write`.

.. warning::
   :ref:`policy_webhook_write` is a sensitive right. The URL is freely
   choosable, so an administrator holding it can make the privacyIDEA
   server issue requests to any host it can reach, including hosts on
   internal networks.
"""

import logging

from flask import Blueprint, g, request

from .lib.utils import send_result
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.error import ParameterError
from ..lib.log import log_with
from ..lib.params import get_optional
from ..lib.policies.actions import PolicyAction
from ..lib.utils import is_true
from ..lib.webhook import (get_webhook, get_webhooks, set_webhook,
                           delete_webhook, test_webhook)

log = logging.getLogger(__name__)

webhook_blueprint = Blueprint('webhook_blueprint', __name__)

#: Prefix marking a request parameter as a static HTTP header.
HEADER_PREFIX = "header."
#: Prefix marking a header as secret, i.e. to be stored encrypted.
SECRET_HEADER_PREFIX = "secret.header."
#: Prefix naming the header a header is being renamed from.
RENAME_HEADER_PREFIX = "rename.header."


def _parse_headers(param):
    """
    Extract the ``header.*`` and ``secret.header.*`` parameters.

    ``header.X-Api-Key=abc`` configures the header ``X-Api-Key``;
    ``secret.header.X-Api-Key=1`` marks its value as secret so it is stored
    encrypted.

    A ``secret.header.*`` names a header of the set the request is sending, so it needs a
    ``header.*`` of the same name. Without one the request describes no state the server could
    produce, and read as "headers were sent, here are none" it would delete the stored set --
    which is what a client flipping only the encryption flag used to do.

    :param param: the request parameters
    ``rename.header.X-API-Key=X-Api-key`` says that the header now called ``X-API-Key`` is the one
    stored as ``X-Api-key``. A header is addressed by its name here, so without saying so a rename
    is a delete plus a create - and a secret header's value is one the client does not have, only
    the ``__CENSORED__`` placeholder, which means "keep what is stored under this name". The
    identity has to come from the client because only the client knows a rename happened.

    :param param: the request parameters
    :return: a ``(headers, secret_headers, renames, given)`` tuple. ``given`` is True if the
        request carried the header set, which is what distinguishes "replace the headers" from
        "leave them alone". Only a ``header.*`` sets it: a flag or a rename is a property of a
        header, not a header, so neither can express "these are all of them".
    :raises ParameterError: if a ``secret.header.*`` or ``rename.header.*`` has no ``header.*`` of
        the same name, or if a rename names the header it renames to
    """
    headers = {}
    # Every name seen with the secret prefix, whether it was flagged on or off: a
    # ``secret.header.X=0`` for a header that is not being sent is as meaningless as one set to 1.
    secret_flags = set()
    secret_headers = set()
    renames = {}
    given = False

    for key, value in param.items():
        if key.startswith(SECRET_HEADER_PREFIX):
            # Check the longer prefixes first: "secret.header.X" and "rename.header.X" also start
            # with neither "header." nor anything else we care about, but being explicit keeps the
            # branches independent.
            name = key[len(SECRET_HEADER_PREFIX):]
            secret_flags.add(name)
            if is_true(value):
                secret_headers.add(name)
        elif key.startswith(RENAME_HEADER_PREFIX):
            renames[key[len(RENAME_HEADER_PREFIX):]] = value
        elif key.startswith(HEADER_PREFIX):
            given = True
            headers[key[len(HEADER_PREFIX):]] = value

    # Named as the parameters the client actually sent, not as bare header names: a name can
    # arrive under either prefix, and "X-Api-Key is orphaned" does not say which line to fix.
    orphaned = sorted(
        [f"{SECRET_HEADER_PREFIX}{name}" for name in secret_flags - set(headers)]
        + [f"{RENAME_HEADER_PREFIX}{name}" for name in set(renames) - set(headers)])
    if orphaned:
        raise ParameterError(
            f"Parameter(s) naming a header that is not part of the request: "
            f"{', '.join(orphaned)}. Sending any '{HEADER_PREFIX}*' parameter replaces the whole "
            f"header set, so send every header you want to keep, each with its own flag.")

    # Renaming a header to the name it already has says nothing; renaming it to a name that is
    # also being sent as a header of its own would have two rows claim one name.
    conflicting = sorted(new for new, old in renames.items() if new == old or old in headers)
    if conflicting:
        raise ParameterError(
            f"Rename(s) naming a header that is also being sent, or renaming a header to itself: "
            f"{', '.join(f'{RENAME_HEADER_PREFIX}{name}' for name in conflicting)}.")

    return headers, secret_headers, renames, given


@webhook_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.WEBHOOKREAD)
def list_webhooks():
    """
    Return all configured webhook definitions as a list, ordered by
    identifier.

    Secrets are never returned in clear text: the basic-auth ``password``,
    the ``client_key_password`` and the values of headers marked as secret
    are replaced by the placeholder ``__CENSORED__``. Each entry also
    carries ``secret_headers``, the list of header names whose values are
    stored encrypted, so the UI can restore the "secret" checkbox state --
    and so a configuration read here can be written back unchanged.

    .. note::
       When updating a webhook, send ``__CENSORED__`` for a secret to keep
       its stored value, an empty string to clear it, or a new value to
       replace it. Send ``secret_headers`` back as ``secret.header.*``
       parameters, otherwise a header that is currently encrypted would be
       rewritten in clear text.

    Requires admin authentication and the policy action
    :ref:`policy_webhook_read`.

    :status 200: list of webhook dictionaries in ``result.value``.
    """
    res = get_webhooks(censor=True)
    g.audit_object.log({"success": True})
    return send_result(res)


@webhook_blueprint.route('/<identifier>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.WEBHOOKREAD)
def get_webhook_api(identifier=None):
    """
    Return a single webhook definition.

    Secrets are censored exactly as in the list endpoint.

    Requires admin authentication and the policy action
    :ref:`policy_webhook_read`.

    :param identifier: path component, the unique name of the webhook.
    :status 200: the webhook dictionary in ``result.value``.
    :status 404: no webhook with this identifier exists.
    """
    res = get_webhook(identifier, censor=True)
    g.audit_object.log({"success": True, "info": identifier})
    return send_result(res)


@webhook_blueprint.route('/<identifier>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.WEBHOOKWRITE)
def set_webhook_api(identifier=None):
    """
    Create or update a webhook definition. If a webhook with the given
    ``identifier`` exists it is updated, otherwise it is created.

    Every parameter that is omitted keeps its stored value, so a partial
    update is possible. ``url`` is only required when creating.

    Requires admin authentication and the policy action
    :ref:`policy_webhook_write`.

    :param identifier: path component, the unique name of the webhook.
    :jsonparam url: the target URL, must start with ``http://`` or
        ``https://`` (required when creating).
    :jsonparam description: free-form description.
    :jsonparam http_method: ``GET``, ``POST`` (default), ``PUT`` or ``PATCH``.
    :jsonparam content_type: MIME type of the request body, default
        ``application/json``. The legacy shorthands ``json`` and
        ``urlencoded`` are rejected; send a real MIME type.
    :jsonparam default_payload: body template used when the call site
        supplies no payload of its own.
    :jsonparam auth_type: ``none`` (default), ``basic``, ``header`` or
        ``mtls``.
    :jsonparam username: username for basic authentication.
    :jsonparam password: password for basic authentication (stored
        encrypted). ``__CENSORED__`` keeps the stored value, an empty
        string clears it.
    :jsonparam verify_tls: whether to verify the server certificate.
        Omitting it keeps the stored setting -- it never silently defaults
        to disabled.
    :jsonparam tls_ca_bundle: path to a CA bundle used for verification.
        Ignored while ``verify_tls`` is false.
    :jsonparam client_certificate: path to the client certificate (mTLS).
    :jsonparam client_key: path to the client key (mTLS).
    :jsonparam client_key_password: password of the client key (stored
        encrypted), same ``__CENSORED__`` semantics as ``password``.
    :jsonparam http_proxy: proxy URL for ``http://`` requests.
    :jsonparam https_proxy: proxy URL for ``https://`` requests.
    :jsonparam timeout: request timeout in seconds, default ``3``.
    :jsonparam header.*: a static HTTP header, e.g. ``header.X-Api-Key``
        sets the ``X-Api-Key`` header. Sending any ``header.*`` parameter
        replaces the stored header set entirely, so send them all.
    :jsonparam secret.header.*: mark a header as secret so its value is
        stored encrypted, e.g. ``secret.header.X-Api-Key=1``. It is a
        property of a header of the set being sent, so it requires a
        ``header.*`` of the same name; a flag on its own results in a 400.
    :jsonparam rename.header.*: the name a header is currently stored under,
        e.g. ``rename.header.X-API-Key=X-Api-key`` renames ``X-Api-key`` to
        ``X-API-Key`` and the row keeps its value. Without it a rename is a
        delete plus a create, which loses the value of a secret header - the
        client only ever holds ``__CENSORED__`` for it, and that means "keep
        what is stored under this name". Requires a ``header.*`` of the new
        name; re-sending a rename that has already been applied is a no-op.
    :jsonparam clear_headers: set to true to remove all headers. Needed
        because "no ``header.*`` parameters" means "leave the headers
        alone", so there would otherwise be no way to delete the last one.
    :status 200: database id of the webhook in ``result.value``.
    :status 400: a parameter is missing or invalid.
    """
    param = request.all_data

    headers, secret_headers, header_renames, headers_given = _parse_headers(param)
    if not headers_given and is_true(get_optional(param, "clear_headers")):
        headers_given = True

    # Booleans and numbers must only be converted when they were actually
    # sent. Defaulting an absent verify_tls to False would silently turn off
    # certificate verification on every partial update; None means "keep".
    verify_tls = get_optional(param, "verify_tls")
    if verify_tls is not None:
        verify_tls = is_true(verify_tls)

    # The remaining values are passed through untouched: set_webhook()
    # validates and normalises them, and it is the single place that knows
    # the rules (URL scheme, known method/auth type, positive timeout,
    # auth-type specific requirements). Duplicating them here would let the
    # two drift apart.
    webhook_id = set_webhook(
        identifier,
        url=get_optional(param, "url"),
        description=get_optional(param, "description"),
        http_method=get_optional(param, "http_method"),
        content_type=get_optional(param, "content_type"),
        default_payload=get_optional(param, "default_payload"),
        auth_type=get_optional(param, "auth_type"),
        username=get_optional(param, "username"),
        password=get_optional(param, "password"),
        verify_tls=verify_tls,
        tls_ca_bundle=get_optional(param, "tls_ca_bundle"),
        client_certificate=get_optional(param, "client_certificate"),
        client_key=get_optional(param, "client_key"),
        client_key_password=get_optional(param, "client_key_password"),
        http_proxy=get_optional(param, "http_proxy"),
        https_proxy=get_optional(param, "https_proxy"),
        timeout=get_optional(param, "timeout"),
        headers=headers if headers_given else None,
        secret_headers=secret_headers if headers_given else None,
        header_renames=header_renames if headers_given else None,
    )

    # Log the identifier, never the URL: it may embed a token.
    g.audit_object.log({"success": True, "info": identifier})
    return send_result(webhook_id)


@webhook_blueprint.route('/<identifier>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.WEBHOOKWRITE)
def delete_webhook_api(identifier=None):
    """
    Delete the webhook definition with the given identifier, including its
    headers.

    Requires admin authentication and the policy action
    :ref:`policy_webhook_write`.

    .. note::
       An event handler or Conditional Access action still referencing this
       webhook is not updated. It will log a delivery failure the next time
       it fires, which is the same behaviour as for a webhook that has
       become unreachable.

    :param identifier: path component, the unique name of the webhook.
    :status 200: database id of the deleted webhook in ``result.value``.
    :status 404: no webhook with this identifier exists.
    """
    webhook_id = delete_webhook(identifier)
    g.audit_object.log({"success": True, "info": identifier})
    return send_result(webhook_id)


@webhook_blueprint.route('/<identifier>/test', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.WEBHOOKWRITE)
def test_webhook_api(identifier=None):
    """
    Fire the stored webhook once and report what the endpoint answered.
    This is what the "Test" button of the configuration UI calls.

    The request really is sent, using the stored configuration, so a test
    against a production endpoint has real side effects.

    A webhook that fails is **not** an API error: the response is still
    HTTP 200 and carries ``success: false`` together with the reason. Only
    a missing webhook or a missing right fails the request itself.

    Requires admin authentication and the policy action
    :ref:`policy_webhook_write`.

    :param identifier: path component, the unique name of the webhook.
    :jsonparam payload: an optional body overriding the webhook's
        ``default_payload``.
    :status 200: a dictionary in ``result.value`` with the keys ``success``
        (the endpoint answered 2xx), ``status_code``, ``response`` (the
        response body, truncated) and ``error``.
    :status 404: no webhook with this identifier exists.
    """
    # Fail with 404 before sending anything if the webhook does not exist.
    # fire_webhook() deliberately swallows that into a result dict, which is
    # right for an event handler but unhelpful for an explicit test request.
    get_webhook(identifier)

    payload = get_optional(request.all_data, "payload")
    result = test_webhook(identifier, payload=payload)

    g.audit_object.log({"success": result["success"],
                        "info": f"{identifier}: {result['error'] or 'ok'}"})
    return send_result(result)
