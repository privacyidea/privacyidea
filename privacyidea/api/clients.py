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
action :ref:`policy_api_client_list`, creation by :ref:`policy_api_client_add`,
modification by :ref:`policy_api_client_edit`, deletion by
:ref:`policy_api_client_delete` and key rotation by
:ref:`policy_api_client_rotate`. The remembered-device endpoints are gated by
:ref:`policy_remembered_device_list` and :ref:`policy_remembered_device_revoke`.
"""
import logging

from flask import Blueprint, request, g

from .lib.utils import send_result
from ..lib.error import ParameterError, PolicyError, ResourceNotFoundError
from ..lib.params import get_optional, get_required
from ..lib.log import log_with
from ..lib.event import event
from ..lib.policies.actions import PolicyAction
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.clients import (get_client, get_clients, create_client, update_client,
                           rotate_client_key, delete_client, client_to_dict)
from ..lib.remembered_device import (get_client_device, get_client_devices, revoke_client_device,
                               revoke_client_devices, revoke_devices, device_to_dict, user_identity)
from ..lib.realm import get_realm_id
from ..lib.user import User

log = logging.getLogger(__name__)


def _allowed_revoke_realm_ids():
    """
    The realm ids the acting admin may revoke remembered devices in, or ``None``
    when unrestricted.

    ``check_base_action`` realm-scopes the revoke endpoints that carry a ``realm``
    (or ``user``) in the request, but the single-device and unfiltered per-client
    revokes carry neither - so a realm-scoped admin would otherwise revoke across
    realms. This computes the admin's allowed realms (mirroring the tokenlist
    scoping) so those two paths can enforce the same restriction.
    """
    from ..lib.policy import Match, SCOPE
    if not g.policy_object.list_policies(scope=SCOPE.ADMIN, active=True):
        return None
    realm_ids = set()
    for pol in Match.admin(g, action=PolicyAction.REMEMBERED_DEVICE_REVOKE).policies():
        if not pol.get("realm"):
            return None
        realm_ids.update(get_realm_id(name) for name in pol.get("realm"))
    realm_ids.discard(None)
    return realm_ids

clients_blueprint = Blueprint('clients_blueprint', __name__)


@clients_blueprint.route('/', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.API_CLIENT_ADD)
@event("api_client_add", request, g)
@log_with(log)
def create_client_api():
    """
    Create a new API client and generate its API key.

    The freshly generated plaintext API key is returned in
    ``result.value.api_key``. This is the only time the key is exposed, so it
    must be shown to the administrator and cannot be retrieved later.

    Requires admin authentication and the policy action :ref:`policy_api_client_add`.

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
@prepolicy(check_base_action, request, PolicyAction.API_CLIENT_LIST)
@event("api_client_list", request, g)
@log_with(log)
def list_clients_api(client_id=None):
    """
    List API clients. If ``client_id`` is given, only the matching client is
    returned; otherwise all clients are listed.

    The API key is never included; only the non-sensitive ``key_id`` is.

    Requires admin authentication and the policy action :ref:`policy_api_client_list`.

    :param client_id: optional path component selecting a single client.
    :status 200: a list of clients in ``result.value``.
    """
    if client_id:
        clients = [get_client(client_id)]
    else:
        clients = get_clients()

    g.audit_object.log({"success": True})
    return send_result([client_to_dict(client) for client in clients])


@clients_blueprint.route('/<client_id>', methods=['PATCH'])
@prepolicy(check_base_action, request, PolicyAction.API_CLIENT_EDIT)
@event("api_client_edit", request, g)
@log_with(log)
def update_client_api(client_id):
    """
    Partially update the metadata of an existing client (display name, status or
    config); only the fields present in the request are changed. The API key is
    not affected; use the rotate endpoint to replace it.

    Requires admin authentication and the policy action :ref:`policy_api_client_edit`.

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
@prepolicy(check_base_action, request, PolicyAction.API_CLIENT_ROTATE)
@event("api_client_rotate", request, g)
@log_with(log)
def rotate_client_api(client_id):
    """
    Rotate the API key of a client. The previous key is invalidated immediately
    and a new plaintext key is returned in ``result.value.api_key``. As with
    creation, this is the only time the new key is exposed.

    Requires admin authentication and the policy action :ref:`policy_api_client_rotate`.

    :param client_id: path component, the id of the client.
    :status 200: the client (including the new ``api_key``) in ``result.value``.
    """
    client, api_key = rotate_client_key(client_id)

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    result = client_to_dict(client)
    result["api_key"] = api_key
    return send_result(result)


@clients_blueprint.route('/remembered_devices', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.REMEMBERED_DEVICE_REVOKE)
@event("remembered_device_revoke_bulk", request, g)
@log_with(log)
def revoke_remembered_devices_api():
    """
    Revoke remembered devices across **all** clients, scoped to a realm or to a
    single user. This is the client-independent bulk revoke,
    for realm-wide incident response or offboarding a single user.

    A ``realm`` is always required (a user is identified within a realm), so this
    can never wipe every device on the system at once. The acting
    administrator's realm restrictions apply: the :ref:`policy_remembered_device_revoke`
    action is matched against the requested ``realm``, so a realm-scoped admin
    cannot revoke another realm's devices.

    Requires admin authentication and the policy action :ref:`policy_remembered_device_revoke`.

    :query realm: the realm whose devices to revoke (required).
    :query user: optional login to restrict the revocation to a single user
        within the realm.
    :status 200: ``result.value`` is the number of revoked remembered devices.
    """
    realm = get_required(request.all_data, "realm")
    realm_id = get_realm_id(realm)
    if realm_id is None:
        raise ParameterError(f"The realm {realm!r} does not exist.")

    user = get_optional(request.all_data, "user")
    resolver = user_id = None
    if user:
        identity = user_identity(User(login=user, realm=realm))
        if not identity:
            raise ParameterError(f"The user {user!r} does not resolve in realm {realm!r}.")
        resolver, user_id, realm_id = identity

    count = revoke_devices(realm_id=realm_id, resolver=resolver, user_id=user_id)

    info = f"realm: {realm}, user: {user}" if user else f"realm: {realm}"
    g.audit_object.log({"success": True, "info": info})
    return send_result(count)


@clients_blueprint.route('/<client_id>/remembered_devices', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.REMEMBERED_DEVICE_LIST)
@event("remembered_device_list", request, g)
@log_with(log)
def list_client_remembered_devices_api(client_id):
    """
    List the remembered devices of a client.

    The rotating token is never included; each entry carries only the
    ``series_id`` (used to target revocation) and non-sensitive metadata
    (user, IP, user agent, created / last used / expiry).

    Requires admin authentication and the policy action :ref:`policy_remembered_device_list`.

    :param client_id: path component, the id of the client.
    :status 200: a list of devices in ``result.value``.
    :status 404: no client with that id exists.
    """
    # Ensure the client exists (404 otherwise).
    get_client(client_id)
    devices = get_client_devices(client_id)

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    return send_result([device_to_dict(device) for device in devices])


@clients_blueprint.route('/<client_id>/remembered_devices', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.REMEMBERED_DEVICE_REVOKE)
@event("remembered_device_revoke_all", request, g)
@log_with(log)
def revoke_client_remembered_devices_api(client_id):
    """
    Revoke remembered devices of a client in bulk. Without a filter this revokes
    **all** of the client's remembered devices; it can be narrowed to one realm
    (``realm``) or to one user (``user`` together with ``realm``).

    The delete is a single atomic, server-side operation scoped to the client, so
    a client id cannot revoke another client's devices, and devices created
    between listing and revoking are still caught.

    Requires admin authentication and the policy action :ref:`policy_remembered_device_revoke`.

    :param client_id: path component, the id of the client.
    :query realm: optional, restrict the revocation to this realm.
    :query user: optional, restrict the revocation to this user (login); requires
        ``realm`` so the user resolves unambiguously.
    :status 200: ``result.value`` is the number of revoked remembered devices.
    :status 404: no client with that id exists.
    """
    # Ensure the client exists (404 otherwise).
    get_client(client_id)
    realm = get_optional(request.all_data, "realm")
    user = get_optional(request.all_data, "user")

    if user:
        # Narrow to one user's resolver-stable identity. If the user does not
        # resolve there is nothing to target by login (its devices, if any, are
        # already unrecognisable and reaped by expiry / realm deletion). This
        # request carries the realm, so check_base_action already realm-scoped it.
        identity = user_identity(User(login=user, realm=realm))
        if not identity:
            raise ParameterError(f"The user {user!r} does not resolve in realm {realm!r}.")
        resolver, user_id, realm_id = identity
        count = revoke_client_devices(client_id, realm_id=realm_id, resolver=resolver, user_id=user_id)
    elif realm:
        # Also realm-scoped by check_base_action. A mistyped realm must not
        # silently widen the scope: an unknown realm would drop the filter and
        # revoke *all* of the client's devices instead of none.
        realm_id = get_realm_id(realm)
        if realm_id is None:
            raise ParameterError(f"The realm {realm!r} does not exist.")
        count = revoke_client_devices(client_id, realm_id=realm_id)
    else:
        # Unfiltered "revoke all": no realm in the request, so check_base_action
        # could not realm-scope it. Enforce the admin's realm restriction here so
        # a realm-scoped admin revokes only within their allowed realms rather
        # than wiping every realm's devices on the client.
        allowed_realm_ids = _allowed_revoke_realm_ids()
        if allowed_realm_ids is None:
            count = revoke_client_devices(client_id)
        else:
            count = sum(revoke_client_devices(client_id, realm_id=realm_id)
                        for realm_id in allowed_realm_ids)

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    return send_result(count)


@clients_blueprint.route('/<client_id>/remembered_devices/<series_id>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.REMEMBERED_DEVICE_REVOKE)
@event("remembered_device_revoke", request, g)
@log_with(log)
def revoke_client_remembered_device_api(client_id, series_id):
    """
    Revoke a single remembered device of a client. The revocation is scoped to
    the client, so a client id cannot be used to revoke another client's device.

    Requires admin authentication and the policy action :ref:`policy_remembered_device_revoke`.

    :param client_id: path component, the id of the client.
    :param series_id: path component, the series id of the device.
    :status 200: ``result.value`` is the series id of the revoked remembered device.
    :status 403: the acting admin may not revoke in the device's realm.
    :status 404: no such device exists for this client.
    """
    # The request carries no realm, so check_base_action could not realm-scope it:
    # enforce the admin's realm restriction against the device's own realm.
    device = get_client_device(client_id, series_id)
    if not device:
        raise ResourceNotFoundError(f"The device {series_id!r} does not exist for this client.")
    allowed_realm_ids = _allowed_revoke_realm_ids()
    if allowed_realm_ids is not None and device.realm_id not in allowed_realm_ids:
        raise PolicyError("You are not allowed to revoke remembered devices in this device's realm.")

    r = revoke_client_device(client_id, series_id)

    g.audit_object.log({"success": True, "info": f"{client_id}: revoked remembered device"})
    return send_result(r)


@clients_blueprint.route('/<client_id>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.API_CLIENT_DELETE)
@event("api_client_delete", request, g)
@log_with(log)
def delete_client_api(client_id):
    """
    Delete the client with the given id.

    Requires admin authentication and the policy action :ref:`policy_api_client_delete`.

    :param client_id: path component, the id of the client.
    :status 200: ``result.value`` is the id of the deleted client.
    :status 404: no client with that id exists.
    """
    r = delete_client(client_id)

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    return send_result(r)
