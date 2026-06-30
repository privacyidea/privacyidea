# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
#
# privacyIDEA is a fork of LinOTP. Some code is adapted from
# the system-controller from LinOTP, which is
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
The realm REST API manages realms. A realm composes one or more
:ref:`useridresolvers` into a single user space; tokens and policies
are scoped against realms, and only users that belong to a realm are
visible to privacyIDEA. The same blueprint also exposes the
``/defaultrealm`` endpoints that read, set and clear which realm new
users are looked up in when no realm is supplied explicitly.

All endpoints require admin authentication. Listing realms is allowed
for any admin but the response is filtered by the calling admin's
policy match — realm-admins only see realms their policies cover.
Create / update / delete are gated by :ref:`resolverwrite` and
:ref:`resolverdelete`.
"""
from flask_babel import _
from flask import Blueprint, request, current_app, g
from .lib.utils import (send_result,
                        get_priority_from_param)
from ..lib.params import get_required
from ..lib.log import log_with
from ..lib.realm import (set_default_realm,
                         get_default_realm,
                         set_realm,
                         get_realms,
                         delete_realm)
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.utils import reduce_realms
from privacyidea.lib.auth import ROLE
from privacyidea.lib.config import check_node_uuid_exists
from privacyidea.lib.error import ParameterError
from privacyidea.lib.policy import ConditionCheck, Match
from ..lib.policies.actions import PolicyAction
import logging

log = logging.getLogger(__name__)

realm_blueprint = Blueprint('realm_blueprint', __name__)
defaultrealm_blueprint = Blueprint('defaultrealm_blueprint', __name__)


# ----------------------------------------------------------------
#
#  REALM functions
#
#

@realm_blueprint.route('/<realm>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RESOLVERWRITE)
def set_realm_api(realm=None):
    """
    Create or reconfigure a realm. The realm is defined as a list of
    resolvers, optionally with a per-resolver priority used to
    disambiguate when the same login name resolves in more than one
    resolver. Resolvers attached to specific nodes are preserved
    across this call (use :http:post:`/realm/(realm)/node/(nodeid)`
    to manage them).

    Requires admin authentication and the policy action :ref:`resolverwrite`.

    :param realm: path component, the unique name of the realm.
    :jsonparam resolvers: comma-separated string or JSON list of
        resolver names that should make up this realm (required).
    :jsonparam priority.<resolvername>: integer priority for the
        named resolver (optional).
    :reqheader PI-Authorization: authentication token.
    :status 200: ``{"added": [...], "failed": [...]}`` in
        ``result.value``.

    **Example request**:

    .. sourcecode:: http

       POST /realm/newrealm HTTP/1.1
       Host: example.com
       Content-Type: application/json

       {
         "resolvers": "reso1_with_realm,reso2_with_realm",
         "priority.reso1_with_realm": 1,
         "priority.reso2_with_realm": 2
       }

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": {
             "added": ["reso1_with_realm", "reso2_with_realm"],
             "failed": []
           }
         },
         "version": "privacyIDEA unknown"
       }
    """
    param = request.all_data
    resolvers = get_required(param, "resolvers")
    priority = get_priority_from_param(param)

    if isinstance(resolvers, list):
        resolver_list = resolvers
    else:
        resolver_list = resolvers.split(',')
    resolvers = [{'name': res,
                  'priority': priority.get(res, None)
                  } for res in resolver_list]
    # since this endpoint is not node-specific, we would delete all other resolvers
    # which are specified for a different node.
    # We need to add all the other resolvers to the dictionary to avoid deleting them
    orig_resolvers = get_realms(realm).get(realm, {}).get("resolver", [])
    for res in orig_resolvers:
        if res.get("node", ""):
            resolvers.append({'name': res["name"],
                              'priority': res.get("priority"),
                              "node": res.get("node")})
    (added, failed) = set_realm(realm, resolvers=resolvers)
    g.audit_object.log({'success': not failed,
                        'info':  f"realm: {realm!r}, resolvers: {resolvers!r}"})
    return send_result({"added": added,
                        "failed": failed})


@realm_blueprint.route('/', methods=['GET'])
@log_with(log)
def get_realms_api():
    """
    Return all realms visible to the calling admin. The response is
    a dictionary keyed by realm name; each entry carries the
    ``default`` flag and a list of resolver records with
    ``name``, ``type``, ``node`` and ``priority``.

    The result is filtered against the calling admin's policy match —
    realm-admins only see realms their policies cover.

    Requires admin authentication.

    :reqheader PI-Authorization: authentication token.
    :status 200: dict of realm definitions in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       GET /realm/ HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": {
             "realm1_with_resolver": {
               "default": true,
               "resolver": [
                 {
                   "name": "reso1_with_realm",
                   "node": "",
                   "priority": null,
                   "type": "passwdresolver"
                 }
               ]
             }
           }
         },
         "version": "privacyIDEA unknown"
       }

    .. versionchanged:: 3.10 The response contains the node and priority of the resolver
    """
    all_realms = get_realms()
    g.audit_object.log({"success": True})
    # This endpoint is called by admins anyway
    luser = g.logged_in_user
    policies = Match.generic(g, scope=luser.get("role", ROLE.ADMIN),
                             adminrealm=luser.get("realm"),
                             adminuser=luser.get("username"),
                             active=True,
                             extended_condition_check=ConditionCheck.DO_NOT_CHECK_AT_ALL).policies()
    realms = reduce_realms(all_realms, policies)

    return send_result(realms)


@realm_blueprint.route('/superuser', methods=['GET'])
@log_with(log)
def get_super_user_realms():
    """
    Return the list of superuser realms — the realms whose users are
    treated as administrators. The list is taken from the
    ``SUPERUSER_REALM`` setting in ``pi.cfg``; see :ref:`cfgfile`.

    Requires admin authentication.

    :reqheader PI-Authorization: authentication token.
    :status 200: list of superuser-realm names in ``result.value``.

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": ["superuser", "realm2"]
         },
         "version": "privacyIDEA unknown"
       }
    """
    superuser_realms = current_app.config.get("SUPERUSER_REALM", [])
    g.audit_object.log({"success": True})
    return send_result(superuser_realms)


@defaultrealm_blueprint.route('/<realm>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RESOLVERWRITE)
def set_default_realm_api(realm=None):
    """
    Set the default realm. The previous default (if any) is cleared
    in the same transaction.

    Requires admin authentication and the policy action :ref:`resolverwrite`.

    :param realm: path component, the name of the realm to make the
        default. Lower-cased and stripped before lookup.
    :reqheader PI-Authorization: authentication token.
    :status 200: database id of the new default realm in
        ``result.value``.
    :status 404: no realm with the given name exists.

    **Example request**:

    .. sourcecode:: http

       POST /defaultrealm/new_default_realm HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": 1
         },
         "version": "privacyIDEA unknown"
       }
    """
    realm = realm.lower().strip()
    r = set_default_realm(realm)
    g.audit_object.log({"success": True,
                        "info": realm})
    return send_result(r)


@defaultrealm_blueprint.route('', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RESOLVERDELETE)
def delete_default_realm_api(realm=None):
    """
    Clear the default realm. The realm definitions themselves are not
    touched; only the ``default`` flag is removed from whichever realm
    currently carries it. After this call, requests that omit the
    realm parameter will no longer resolve a default and must specify
    ``realm`` explicitly.

    Requires admin authentication and the policy action :ref:`resolverdelete`.

    :reqheader PI-Authorization: authentication token.
    :status 200: database id of the realm that was the default in
        ``result.value``, or ``0`` if no default was set.

    **Example request**:

    .. sourcecode:: http

       DELETE /defaultrealm HTTP/1.1
       Host: example.com

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": 1
         },
         "version": "privacyIDEA unknown"
       }
    """
    r = set_default_realm("")
    g.audit_object.log({"success": True,
                        "info": ""})
    return send_result(r)


@defaultrealm_blueprint.route('', methods=['GET'])
@log_with(log)
def get_default_realm_api():
    """
    Return the default realm with its resolver list. If no realm is
    currently flagged as default, the response value is an empty
    dictionary.

    Requires admin authentication.

    :reqheader PI-Authorization: authentication token.
    :status 200: single-entry dict keyed by the default-realm name,
        or ``{}`` when no default is set.

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": {
             "defrealm": {
               "default": true,
               "id": 1,
               "resolver": [
                 {
                   "name": "defresolver",
                   "node": "",
                   "priority": null,
                   "type": "passwdresolver"
                 }
               ]
             }
           }
         },
         "version": "privacyIDEA unknown"
       }
    """
    res = {}
    defRealm = get_default_realm()
    if defRealm:
        res = get_realms(defRealm)

    g.audit_object.log({"success": True,
                        "info": defRealm})

    return send_result(res)


@realm_blueprint.route('/<realm>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RESOLVERDELETE)
def delete_realm_api(realm=None):
    """
    Delete a realm. The realm can only be deleted if no user from
    this realm is still attached to a token or a container.

    If the deleted realm was the default realm and exactly one realm
    remains afterwards, that remaining realm is automatically promoted
    to default.

    Requires admin authentication and the policy action :ref:`resolverdelete`.

    :param realm: path component, the name of the realm to delete.
    :reqheader PI-Authorization: authentication token.
    :status 200: database id of the deleted realm in ``result.value``.
    :status 400: a token or container in this realm still has a user
        assigned, or a user in this realm still has custom user attributes.
    :status 404: no realm with the given name exists.

    **Example request**:

    .. sourcecode:: http

       DELETE /realm/realm_to_delete HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": 1
         },
         "version": "privacyIDEA unknown"
       }
    """
    ret = delete_realm(realm)
    g.audit_object.log({"success": ret > 0,
                        "info": realm})

    return send_result(ret)


# TODO: Flask supports conversion of the nodeid to a UUID, but in get_all_params()
#  we put everything (including the viewargs) in the param dict and try to "unquote"
#  all entries. This fails for the UUID type. We should probably remove the viewargs from
#  the param dict and handle them separately in the corresponding API function.
@realm_blueprint.route('/<string:realm>/node/<string:nodeid>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RESOLVERWRITE)
def set_realm_node_api(realm, nodeid):
    """
    Create or reconfigure the resolver assignment for a realm on a
    specific privacyIDEA node. Resolvers attached to *other* nodes
    (and node-less resolvers in this realm) are preserved across the
    call; only the resolvers bound to ``nodeid`` are replaced.

    The body must be JSON (``Content-Type: application/json``) and
    contain a ``resolver`` list of ``{name, priority}`` objects.

    Requires admin authentication and the policy action :ref:`resolverwrite`.

    :param realm: path component, the unique name of the realm.
    :param nodeid: path component, the UUID of the node.
    :reqheader Content-Type: ``application/json`` (required).
    :reqheader PI-Authorization: authentication token.
    :<json list resolver: list of objects, each with ``name`` (string,
        required) and ``priority`` (integer, optional).
    :status 200: ``{"added": [...], "failed": [...]}`` in
        ``result.value``.
    :status 400: the node UUID is unknown, the body is missing the
        ``resolver`` key, or a resolver entry could not be parsed.

    **Example request**:

    Replace the resolvers of realm ``newrealm`` on the node with UUID
    ``8e4272a9-9037-40df-8aa3-976e4a04b5a9`` with ``resolver1`` and
    ``resolver2``:

    .. sourcecode:: http

       POST /realm/newrealm/node/8e4272a9-9037-40df-8aa3-976e4a04b5a9 HTTP/1.1
       Host: example.com
       Content-Type: application/json

       {
         "resolver": [
           {"name": "resolver1", "priority": 1},
           {"name": "resolver2", "priority": 2}
         ]
       }

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": {
             "added": ["resolver1", "resolver2"],
             "failed": []
           }
         },
         "version": "privacyIDEA unknown"
       }

    .. versionadded:: 3.10 Node specific realm configuration
    """
    if not check_node_uuid_exists(nodeid):
        log.warning(f"Node with UUID {nodeid} does not exist in the database!")
        raise ParameterError(_("The given node does not exist!"))

    data = request.get_json(silent=True) or {}
    resolvers = []
    if "resolver" not in data:
        log.warning("Missing resolver data in request")
        raise ParameterError(_("Could not verify data in request!"))

    for res in data["resolver"]:
        try:
            resolvers.append({"name": res["name"],
                              "priority": int(res.get("priority")) if res.get("priority") else None,
                              "node": nodeid})
        except (KeyError, ValueError) as e:
            log.warning(f"Could not parse resolver data {res}: {e}")
            log.debug(e.__traceback__)
            raise ParameterError(_("Could not verify data in request!"))

    # since this endpoint is node-specific, we would delete all other resolvers
    # which are specified for a different node or no node at all. We need to
    # add all the other resolvers to the dictionary to avoid deleting them
    orig_resolvers = get_realms(realm).get(realm, {}).get("resolver", [])
    for res in orig_resolvers:
        if res.get("node", "") != nodeid:
            resolvers.append({'name': res["name"],
                              'priority': res.get("priority"),
                              "node": res.get("node")})
    (added, failed) = set_realm(realm, resolvers=resolvers)

    g.audit_object.log({
        'success': not failed,
        # Overwrite resolver entry in audit log since `before_after` added a dict
        'resolver': ", ".join([r["name"] for r in resolvers]),
        'info': "realm: {!r}, resolvers: {!r}".format(realm,
                                                        [r["name"] for r in resolvers])})
    return send_result({"added": added,
                        "failed": failed})
