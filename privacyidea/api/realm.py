# -*- coding: utf-8 -*-
#
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
from flask import (Blueprint,
                   request, current_app)
from lib.utils import (getParam,
                       required,
                       send_result, get_priority_from_param)
from ..lib.log import log_with
from ..lib.realm import get_realms

from ..lib.realm import (set_default_realm,
                         get_default_realm,
                         set_realm,
                         delete_realm)
from ..lib.policy import ACTION
from ..api.lib.prepolicy import prepolicy, check_base_action
from flask import g
from gettext import gettext as _
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

    :param realm: The unique name of the realm
    :param resolvers: A comma separated list of unique resolver names or a
        list object
    :type resolvers: string or list
    :param priority: Additional parameters priority.<resolvername> define the
        priority of the resolvers within this realm.
    :return: a json result with a list of Realms

    **Example request**:

    To create a new realm "newrealm", that consists of the resolvers
    "reso1_with_realm" and "reso2_with_realm" call:

    .. sourcecode:: http

       POST /realm/newrealm HTTP/1.1
       Host: example.com
       Accept: application/json
       Content-Length: 26
       Content-Type: application/x-www-form-urlencoded

       resolvers=reso1_with_realm, reso2_with_realm
       priority.reso1_with_realm=1
       priority.reso2_with_realm=2


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

    if type(resolvers) == "list":
        Resolvers = resolvers
    else:
        Resolvers = resolvers.split(',')
    (added, failed) = set_realm(realm, Resolvers, priority=priority)
    g.audit_object.log({'success': len(added) == len(Resolvers),
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


    **Example request**:

    .. sourcecode:: http

       GET / HTTP/1.1
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
                    "type": "passwdresolver"
                  }
                ]
              }
            }
          },
          "version": "privacyIDEA unknown"
        }
    """
    realms = get_realms()
    g.audit_object.log({"success": True})

    # If the admin is not allowed to see all realms,
    # (policy scope=system, action=read)
    # the realms, where he has no administrative rights need,
    # to be stripped.
    '''
        polPost = self.Policy.checkPolicyPost('system',
                                              'getRealms',
                                              {'realms': realms})
        res = polPost['realms']
    '''
    return send_result(realms)


@realm_blueprint.route('/superuser', methods=['GET'])
@log_with(log)
def get_super_user_realms():
    """
    This call returns the list of all superuser realms
    as they are defined in *pi.cfg*.
    See :ref:`cfgfile` for more information about this.

    :return: a json result with a list of realms


    **Example request**:

    .. sourcecode:: http

       GET /superuser HTTP/1.1
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
            "value": ["superuser",
                      "realm2"]
            }
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

    :return: a json result with either 1 (success) or 0 (fail)
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

    :return: a json result with either 1 (success) or 0 (fail)

    **Example response**:

    .. sourcecode:: http

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
    g.audit_object.log({"success": r,
                        "info": ""})
    return send_result(r)


@defaultrealm_blueprint.route('', methods=['GET'])
@log_with(log)
def get_default_realm_api():
    """
    This call returns the default realm

    :return: a json description of the default realm with the resolvers

    **Example response**:

    .. sourcecode:: http

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": {
              "defrealm": {
                "default": true,
                "resolver": [
                  {
                    "name": "defresolver",
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
#@system_blueprint.route('/delRealm', methods=['POST', 'DELETE'])
@prepolicy(check_base_action, request, ACTION.RESOLVERDELETE)
def delete_realm_api(realm=None):
    """
    This call deletes the given realm.

    :param realm: The name of the realm to delete

    :return: a json result with value=1 if deleting the realm was successful

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
    g.audit_object.log({"success": ret,
                        "info": realm})

    return send_result(ret)

