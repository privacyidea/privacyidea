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
from ..lib.error import ParameterError, ResourceNotFoundError
from ..lib.params import get_optional, get_pagination_params, get_required
from ..lib.log import log_with
from ..lib.event import event
from ..lib.policies.actions import PolicyAction
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.clients import (get_client, get_clients, create_client, update_client,
                           rotate_client_key, delete_client, client_to_dict)
from ..lib.remembered_device import (get_client_device, get_client_devices,
                               revoke_client_devices, revoke_devices, devices_to_dicts, user_identity)
from ..lib.policies.helper import admin_granted_realms
from ..lib.realm import get_realm_id

log = logging.getLogger(__name__)


def _allowed_realm_ids(action):
    """
    The realm ids the acting admin may act on for ``action`` (a
    remembered-device admin action), or ``None`` when unrestricted.

    ``check_base_action`` realm-scopes the endpoints that carry a ``realm`` (or
    ``user``) in the request, but the list, single-device and unfiltered
    per-client revoke paths carry neither - so a realm-scoped admin would
    otherwise see or revoke across realms. This computes the admin's allowed
    realms for the given action (mirroring the tokenlist scoping) so those paths
    can enforce the same restriction. An empty set means "no realms".

    Those paths act on every device of a realm without looking at its user, so
    only the policies that grant every user of their realms count: a policy for
    some users or resolvers of a realm does not open all of that realm's devices.
    Such an admin revokes the devices of their users by naming the user, which
    ``check_base_action`` checks against the policy.
    """
    granted_realms = admin_granted_realms(action, whole_realms=True)
    if granted_realms is None:
        return None
    # An empty answer means the admin is restricted along a dimension a realm list cannot carry
    # (a policy scoped by user or resolver). An empty set of realm ids matches no row, which is
    # the refusal these paths express.
    realm_ids = {get_realm_id(name) for name in granted_realms}
    if None in realm_ids:
        # The policy engine matches the realm field with exclusions ("!realmb") and regular
        # expressions as well as plain names, and a plain name may also belong to a realm that has
        # since been deleted. None of those resolve to a realm id, so they cannot be part of the
        # filter and the boundary ends up narrower than the policy describes. Narrower is the safe
        # direction, but an administrator whose revoke then reports "0 revoked" has no other way to
        # find out why.
        unresolved = sorted(name for name in granted_realms if get_realm_id(name) is None)
        log.warning(f"The {action} policies grant realms that do not resolve to a realm: "
                    f"{', '.join(unresolved)}. They are left out of the boundary, so this request "
                    f"acts on fewer realms than the policies describe.")
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
    :jsonparam client_type: one of the API-client integrations from ``GET /info/integrations``,
        e.g. 'privacyidea-cp', 'privacyidea-keycloak', 'entraid-via-keycloak'.
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
        # request.User is the object check_base_action matched the policy against, and it carries the
        # request's `resolver`. Building a second user from login and realm alone drops it and lets
        # the realm's resolver priority pick a different one, so the policy would be checked for one
        # resolver and the rows deleted in another - and a login present in more than one resolver of
        # the realm would keep the devices held in the others.
        identity = user_identity(request.User)
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

    No part of the cookie is ever included; each entry carries only a non-secret
    ``device_id`` (used to target revocation) and metadata (user, IP, user agent,
    created / last used / expiry).

    The listing is paginated: a client shared across many browsers/devices per
    user can accumulate a very large number of remembered devices.

    Requires admin authentication and the policy action :ref:`policy_remembered_device_list`.

    :param client_id: path component, the id of the client.
    :query page: 1-indexed page number, default ``1``; values below 1 are treated as 1.
    :query pagesize: page size, default ``50``, capped at ``1000``.
    :query realm: optional realm name to narrow the listing to.
    :status 200: ``result.value`` is a dict with ``devices`` (this page),
        ``count`` (total matching devices), ``prev`` and ``next`` (page numbers,
        or ``null`` when there is no such page).
    :status 404: no client with that id exists, or ``realm`` does not exist.
    """
    # Ensure the client exists (404 otherwise).
    get_client(client_id)
    # The request carries no realm, so check_base_action could not realm-scope
    # it: restrict the listing to the admin's allowed realms so a realm-scoped
    # remembered_device_list admin does not see every realm's devices.
    allowed_realm_ids = _allowed_realm_ids(PolicyAction.REMEMBERED_DEVICE_LIST)
    page, page_size = get_pagination_params(request.all_data, default_page_size=50)
    realm = get_optional(request.all_data, "realm")
    realm_id = None
    if realm:
        realm_id = get_realm_id(realm)
        if realm_id is None:
            raise ParameterError(f"The realm {realm!r} does not exist.")

    result = get_client_devices(client_id, realm_ids=allowed_realm_ids, realm_id=realm_id,
                                page=page, page_size=page_size)

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    return send_result({
        "devices": devices_to_dicts(result["devices"]),
        "count": result["count"],
        "prev": result["prev"],
        "next": result["next"]
    })


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

    # A user is only unambiguous within a realm (and the realm is what
    # check_base_action scopes on), so filtering by user requires a realm.
    if user and not realm:
        raise ParameterError("A 'realm' is required when filtering by 'user'.")

    if user:
        # Narrow to one user's resolver-stable identity. If the user does not
        # resolve there is nothing to target by login (its devices, if any, are
        # already unrecognisable and reaped by expiry / realm deletion). This
        # request carries the realm, so check_base_action already realm-scoped it.
        # As in revoke_remembered_devices_api: resolve the user the policy was checked against,
        # rather than rebuilding one from a subset of the same parameters.
        identity = user_identity(request.User)
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
        allowed_realm_ids = _allowed_realm_ids(PolicyAction.REMEMBERED_DEVICE_REVOKE)
        if allowed_realm_ids is None:
            count = revoke_client_devices(client_id)
        else:
            # One atomic delete scoped to the admin's allowed realms (an empty
            # set revokes nothing), rather than a commit-per-realm loop.
            count = revoke_client_devices(client_id, realm_ids=list(allowed_realm_ids))

    g.audit_object.log({"success": True, "info": f"Client ID: {client_id}"})
    return send_result(count)


@clients_blueprint.route('/<client_id>/remembered_devices/<device_id>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.REMEMBERED_DEVICE_REVOKE)
@event("remembered_device_revoke", request, g)
@log_with(log)
def revoke_client_remembered_device_api(client_id, device_id):
    """
    Revoke a single remembered device of a client, targeted by its non-secret
    ``device_id``. The revocation is scoped to the client, so a client id cannot
    be used to revoke another client's device.

    Requires admin authentication and the policy action :ref:`policy_remembered_device_revoke`.

    :param client_id: path component, the id of the client.
    :param device_id: path component, the public device id (never the cookie's
        secret series id).
    :status 200: ``result.value`` is the device id of the revoked remembered device.
    :status 404: no such device exists for this client, or it belongs to a realm the acting admin
        may not revoke in - the two are deliberately indistinguishable.
    """
    # The request carries no realm, so check_base_action could not realm-scope it: enforce the
    # admin's realm restriction against the device's own realm. A device outside that restriction
    # answers as an absent one, because an admin who can tell the two apart can probe device ids of
    # realms they are not allowed to see.
    device = get_client_device(client_id, device_id)
    allowed_realm_ids = _allowed_realm_ids(PolicyAction.REMEMBERED_DEVICE_REVOKE)
    if not device or (allowed_realm_ids is not None and device.realm_id not in allowed_realm_ids):
        raise ResourceNotFoundError(f"The device {device_id!r} does not exist for this client.")

    # Delete the row already fetched above rather than re-querying it.
    device.delete()

    g.audit_object.log({"success": True, "info": f"{client_id}: revoked remembered device"})
    return send_result(device_id)


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
