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
__doc__ = """The realm endpoints are used to define realms.
A realm groups together many users. Administrators can manage the tokens of
the users in such a realm. Policies and tokens can be assigned to realms.

A realm consists of several resolvers. Thus you can create a realm and gather
users from LDAP and flat file source into one realm or you can pick resolvers
that collect users from different points from your vast LDAP directory and
group these users into a realm.

You will only be able to see and use user object, that are contained in a realm.

The code of this module is tested in tests/test_api_system.py
"""
from flask import Blueprint, request, current_app, g
from .lib.utils import (getParam,
                        required,
                        send_result,
                        get_priority_from_param)
from ..lib.log import log_with
from ..lib.realm import (set_default_realm,
                         get_default_realm,
                         set_realm,
                         get_realms,
                         delete_realm)
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.utils import reduce_realms
from privacyidea.lib import _
from privacyidea.lib.auth import ROLE
from privacyidea.lib.config import check_node_uuid_exists
from privacyidea.lib.error import ParameterError
from privacyidea.lib.policy import CONDITION_CHECK, ACTION, Match
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
@prepolicy(check_base_action, request, ACTION.RESOLVERWRITE)
def set_realm_api(realm=None):
    """
    This call creates a new realm or reconfigures a realm.
    The realm contains a list of resolvers.

    In the result it returns a list of added resolvers and a list of
    resolvers, that could not be added.

    :arg realm: The unique name of the realm
    :<json string/list resolvers: A comma separated list of unique resolver
        names or a list object
    :<json integer priority: Additional priority parameters ``priority.<resolvername>``
        to define the priority of the resolvers within this realm
    :>json bool status: Status of the request
    :>json value: object with a list of added and failed resolvers
    :reqheader PI-Authorization: The authorization token

    **Example request**:

    To create a new realm ``newrealm``, that consists of the resolvers
    ``reso1_with_realm`` and ``reso2_with_realm`` call:

    .. sourcecode:: http

       POST /realm/newrealm HTTP/1.1
       Host: example.com
       Accept: application/json
       Content-Type: application/json

       "resolvers": "reso1_with_realm, reso2_with_realm"
       "priority.reso1_with_realm": 1
       "priority.reso2_with_realm": 2

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
          }
          "version": "privacyIDEA unknown"
       }
    """
    param = request.all_data
    resolvers = getParam(param, "resolvers", required)
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
                        'info':  "realm: {0!r}, resolvers: {1!r}".format(realm,
                                                                         resolvers)})
    return send_result({"added": added,
                        "failed": failed})


@realm_blueprint.route('/', methods=['GET'])
@log_with(log)
def get_realms_api():
    """
    This call returns the list of all defined realms.
    It takes no arguments.

    :return: a json result with a list of realms
    :reqheader PI-Authorization: The authorization token

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
                             extended_condition_check=CONDITION_CHECK.DO_NOT_CHECK_AT_ALL).policies()
    realms = reduce_realms(all_realms, policies)

    return send_result(realms)


@realm_blueprint.route('/superuser', methods=['GET'])
@log_with(log)
def get_super_user_realms():
    """
    This call returns the list of all superuser realms
    as they are defined in *pi.cfg*.
    See :ref:`cfgfile` for more information about this.

    :return: a json result with a list of superuser realms
    :reqheader PI-Authorization: The authorization token

    **Example request**:

    .. sourcecode:: http

       GET /realm/superuser HTTP/1.1
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
            "value": [
              "superuser",
              "realm2"
            ]
          },
          "version": "privacyIDEA unknown"
        }
    """
    superuser_realms = current_app.config.get("SUPERUSER_REALM", [])
    g.audit_object.log({"success": True})
    return send_result(superuser_realms)


@defaultrealm_blueprint.route('/<realm>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.RESOLVERWRITE)
def set_default_realm_api(realm=None):
    """
    This call sets the default realm.

    :param realm: the name of the realm, that should be the default realm
    :>json bool status: Status of the request
    :>json integer value: The id of the new default realm
    :reqheader PI-Authorization: The authorization token

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
    g.audit_object.log({"success": r,
                        "info": realm})
    return send_result(r)


@defaultrealm_blueprint.route('', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.RESOLVERDELETE)
def delete_default_realm_api(realm=None):
    """
    This call deletes the default realm.

    :>json bool status: Status of the request
    :>json integer value: The id of the realm which used to be default
        or ``0`` in case no default realm was found
    :reqheader PI-Authorization: The authorization token

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
    This call returns the default realm

    :return: a json description of the default realm with the resolvers
    :reqheader PI-Authorization: The authorization token

    **Example request**:

    .. sourcecode:: http

       GET /defaultrealm HTTP/1.1
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
@prepolicy(check_base_action, request, ACTION.RESOLVERDELETE)
def delete_realm_api(realm=None):
    """
    This call deletes the given realm.

    :param realm: The name of the realm to delete
    :>json bool status: Status of the request
    :>json integer value: The id of the deleted realm
    :reqheader PI-Authorization: The authorization token

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
@prepolicy(check_base_action, request, ACTION.RESOLVERWRITE)
def set_realm_node_api(realm, nodeid):
    """
    This call creates or reconfigures a realm with node specific settings.

    The realm contains a list of resolvers and corresponding priorities per node.
    If the node UUID can not be found in the database, the realm will be
    configured without a specific node.
    In the result it returns a list of added resolvers and a list of
    resolvers, that could not be added.

    :arg string realm: The unique name of the realm
    :arg string nodeid: The UUID of the node
    :<json resolver: A JSON object with a list consisting of objects with the
      resolver name and priority
    :reqheader PI-Authorization: The authorization token
    :statuscode 200: no error
    :statuscode 400:
      - The given node UUID does not exist
      - Could not verify data in request

    **Example request**:

    Create a new realm ``newrealm``, that consists of the resolvers
    ``resolver1`` and ``resolver2`` on the node with
    UUID ``8e4272a9-9037-40df-8aa3-976e4a04b5a9``:

    .. sourcecode:: http

      POST /realm/newrealm/node/8e4272a9-9037-40df-8aa3-976e4a04b5a9 HTTP/1.1
      Host: example.com
      Accept: application/json
      Content-Type: application/json

      {
        "resolver": [
          {
            "name": "resolver1",
            "priority": 1
          },
          {
            "name": "resolver2",
            "priority": 2
          }
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
          }
          "version": "privacyIDEA unknown"
       }

    .. versionadded:: 3.10 Node specific realm configuration
    """
    if not check_node_uuid_exists(nodeid):
        log.warning(f"Node with UUID {nodeid} does not exist in the database!")
        raise ParameterError(_("The given node does not exist!"))

    data = request.json
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
        'info': "realm: {0!r}, resolvers: {1!r}".format(realm,
                                                        [r["name"] for r in resolvers])})
    return send_result({"added": added,
                        "failed": failed})
