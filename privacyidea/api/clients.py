# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
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
The clients REST API manages API clients. An API client authenticates against
privacyIDEA with an API key sent in the ``X-API-Key`` header.

The plaintext API key is returned to the administrator exactly once, in the
response of the creation and the rotation endpoints. It is never stored and can
never be retrieved again; if it is lost, the key must be rotated.

All endpoints require admin authentication. Listing is gated by the admin policy
action :ref:`policy_clients_list`, creation/modification by
:ref:`policy_clients_add`, deletion by :ref:`policy_clients_delete` and key
rotation by :ref:`policy_clients_rotate`.
"""
import logging

from flask import Blueprint, request, g

from .lib.utils import send_result
from ..lib.params import get_optional, get_required
from ..lib.log import log_with
from ..lib.event import event
from ..lib.policies.actions import PolicyAction
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.clients import (get_client, get_clients, create_client, update_client,
                           rotate_client_key, delete_client, client_to_dict)
from ..lib.authsession import get_client_sessions, revoke_client_session, session_to_dict

log = logging.getLogger(__name__)

clients_blueprint = Blueprint('clients_blueprint', __name__)


@clients_blueprint.route('/', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.CLIENTS_ADD)
@event("clients_add", request, g)
@log_with(log)
def create_client_api():
    """
    Create a new API client and generate its API key.

    The freshly generated plaintext API key is returned in
    ``result.value.api_key``. This is the only time the key is exposed, so it
    must be shown to the administrator and cannot be retrieved later.

    Requires admin authentication and the policy action :ref:`policy_clients_add`.

    :jsonparam display_name: a human readable name for the client.
    :jsonparam client_type: the type of client, e.g. 'windows_cp', 'keycloak', 'entraid'.
    :jsonparam config: optional JSON object for future remote configuration.
    :status 200: the client (including ``api_key``) in ``result.value``.
    """
    param = request.all_data
    display_name = get_required(param, "display_name")
    client_type = get_required(param, "client_type")
    config = get_optional(param, "config")

    client, api_key = create_client(display_name, client_type, config=config)

    g.audit_object.log({"success": True, "info": f"{client_type}: {display_name}"})
    result = client_to_dict(client)
    result["api_key"] = api_key
    return send_result(result)


@clients_blueprint.route('/<client_id>', methods=['GET'])
@clients_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CLIENTS_LIST)
@event("clients_list", request, g)
@log_with(log)
def list_clients_api(client_id=None):
    """
    List API clients. If ``client_id`` is given, only the matching client is
    returned; otherwise all clients are listed.

    The API key is never included; only the non-sensitive ``key_id`` is.

    Requires admin authentication and the policy action :ref:`policy_clients_list`.

    :param client_id: optional path component selecting a single client.
    :status 200: a list of clients in ``result.value``.
    """
    if client_id:
        clients = [get_client(client_id)]
    else:
        clients = get_clients()

    g.audit_object.log({"success": True})
    return send_result([client_to_dict(client) for client in clients])


@clients_blueprint.route('/<client_id>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.CLIENTS_ADD)
@event("clients_update", request, g)
@log_with(log)
def update_client_api(client_id):
    """
    Update the metadata of an existing client (display name, status or config).
    The API key is not affected; use the rotate endpoint to replace it.

    Requires admin authentication and the policy action :ref:`policy_clients_add`.

    :param client_id: path component, the id of the client.
    :jsonparam display_name: the new display name.
    :jsonparam status: the new status ('active' or 'suspended').
    :jsonparam config: the new config object.
    :status 200: the updated client in ``result.value``.
    """
    param = request.all_data
    display_name = get_optional(param, "display_name")
    status = get_optional(param, "status")
    config = get_optional(param, "config")

    client = update_client(client_id, display_name=display_name, status=status, config=config)

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    return send_result(client_to_dict(client))


@clients_blueprint.route('/<client_id>/rotate', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.CLIENTS_ROTATE)
@event("clients_rotate", request, g)
@log_with(log)
def rotate_client_api(client_id):
    """
    Rotate the API key of a client. The previous key is invalidated immediately
    and a new plaintext key is returned in ``result.value.api_key``. As with
    creation, this is the only time the new key is exposed.

    Requires admin authentication and the policy action :ref:`policy_clients_rotate`.

    :param client_id: path component, the id of the client.
    :status 200: the client (including the new ``api_key``) in ``result.value``.
    """
    client, api_key = rotate_client_key(client_id)

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    result = client_to_dict(client)
    result["api_key"] = api_key
    return send_result(result)


@clients_blueprint.route('/<client_id>/sessions', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.CLIENTS_LIST)
@event("clients_sessions_list", request, g)
@log_with(log)
def list_client_sessions_api(client_id):
    """
    List the persistent "remember device" sessions of a client.

    The rotating token is never included; each entry carries only the
    ``series_id`` (used to target revocation) and non-sensitive metadata
    (user, IP, user agent, created / last used / expiry).

    Requires admin authentication and the policy action :ref:`policy_clients_list`.

    :param client_id: path component, the id of the client.
    :status 200: a list of sessions in ``result.value``.
    :status 404: no client with that id exists.
    """
    # Ensure the client exists (404 otherwise).
    get_client(client_id)
    sessions = get_client_sessions(client_id)

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    return send_result([session_to_dict(session) for session in sessions])


@clients_blueprint.route('/<client_id>/sessions/<series_id>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.CLIENTS_DELETE)
@event("clients_sessions_revoke", request, g)
@log_with(log)
def revoke_client_session_api(client_id, series_id):
    """
    Revoke a single persistent session of a client. The revocation is scoped to
    the client, so a client id cannot be used to revoke another client's session.

    Requires admin authentication and the policy action :ref:`policy_clients_delete`.

    :param client_id: path component, the id of the client.
    :param series_id: path component, the series id of the session.
    :status 200: ``result.value`` is the series id of the revoked session.
    :status 404: no such session exists for this client.
    """
    r = revoke_client_session(client_id, series_id)

    g.audit_object.log({"success": True, "info": f"{client_id}: revoked session"})
    return send_result(r)


@clients_blueprint.route('/<client_id>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.CLIENTS_DELETE)
@event("clients_delete", request, g)
@log_with(log)
def delete_client_api(client_id):
    """
    Delete the client with the given id.

    Requires admin authentication and the policy action :ref:`policy_clients_delete`.

    :param client_id: path component, the id of the client.
    :status 200: ``result.value`` is the id of the deleted client.
    :status 404: no client with that id exists.
    """
    r = delete_client(client_id)

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    return send_result(r)
