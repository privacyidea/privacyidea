# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2016-04-05 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add time to policies
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
The code of this module is tested in tests/test_api_system.py
"""
from flask import (Blueprint,
                   request,
                   url_for)
from .lib.utils import (getParam,
                        getLowerParams,
                        optional,
                        required,
                        send_result)
from ..lib.log import log_with
from ..lib.policy import (set_policy,
                          PolicyClass, ACTION,
                          export_policies, import_policies,
                          delete_policy, get_static_policy_definitions,
                          enable_policy)
from ..lib.token import get_dynamic_policy_definitions
from ..lib.error import (ParameterError)
from ..api.lib.prepolicy import prepolicy, check_base_action

from flask import (g,
                    make_response)
from flask_babel import gettext as _
from werkzeug.datastructures import FileStorage
from cgi import FieldStorage

import logging
import re


log = logging.getLogger(__name__)


policy_blueprint = Blueprint('policy_blueprint', __name__)


# -------------------------------------------------------------------
#
# POLICY functions
#

@policy_blueprint.route('/enable/<name>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.POLICYWRITE)
def enable_policy_api(name):
    """
    Enable a given policy by its name.

    :jsonparam name: Name of the policy
    :return: ID in the database
    """
    p = enable_policy(name)
    g.audit_object.log({"success": True})
    return send_result(p)


@policy_blueprint.route('/disable/<name>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.POLICYWRITE)
def disable_policy_api(name):
    """
    Disable a given policy by its name.

    :jsonparam name: The name of the policy
    :return: ID in the database
    """
    p = enable_policy(name, False)
    g.audit_object.log({"success": True})
    return send_result(p)


@policy_blueprint.route('/<name>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.POLICYWRITE)
def set_policy_api(name=None):
    """
    Creates a new policy that defines access or behaviour of different
    actions in privacyIDEA

    :jsonparam basestring name: name of the policy
    :jsonparam scope: the scope of the policy like "admin", "system",
        "authentication" or "selfservice"
    :jsonparam adminrealm: Realm of the administrator. (only for admin scope)
    :jsonparam action: which action may be executed
    :jsonparam realm: For which realm this policy is valid
    :jsonparam resolver: This policy is valid for this resolver
    :jsonparam user: The policy is valid for these users.
        string with wild cards or list of strings
    :jsonparam time: on which time does this policy hold
    :jsonparam client: for which requesting client this should be
    :jsontype client: IP address with subnet
    :jsonparam active: bool, whether this policy is active or not
    :jsonparam check_all_resolvers: bool, whether all all resolvers in which
        the user exists should be checked with this policy.

    :return: a json result with success or error

    :status 200: Policy created or modified.
    :status 401: Authentication failed

    **Example request**:

    In this example a policy "pol1" is created.

    .. sourcecode:: http

       POST /policy/pol1 HTTP/1.1
       Host: example.com
       Accept: application/json

       scope=admin
       realm=realm1
       action=enroll, disable

    **Example response**:

    .. sourcecode:: http

       HTTP/1.0 200 OK
       Content-Length: 354
       Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": {
              "setPolicy pol1": 1
            }
          },
          "version": "privacyIDEA unknown"
        }
    """
    res = {}
    param = request.all_data
    if not re.match('^[a-zA-Z0-9_.]*$', name):
        raise ParameterError(_("The name of the policy may only contain "
                               "the characters a-zA-Z0-9_."))

    if name.lower() == "check":
        raise ParameterError(_("T'check' is an invalid policy name."))

    action = getParam(param, "action", required)
    scope = getParam(param, "scope", required)
    realm = getParam(param, "realm", required)
    resolver = getParam(param, "resolver", optional)
    user = getParam(param, "user", optional)
    time = getParam(param, "time", optional)
    client = getParam(param, "client", optional)
    active = getParam(param, "active", optional)
    check_all_resolvers = getParam(param, "check_all_resolvers", optional)
    admin_realm = getParam(param, "adminrealm", optional)

    g.audit_object.log({'action_detail': name,
                        'info': u"{0!s}".format(param)})
    ret = set_policy(name=name, scope=scope, action=action, realm=realm,
                     resolver=resolver, user=user, client=client, time=time,
                     active=active or True, adminrealm=admin_realm,
                     check_all_resolvers=check_all_resolvers or False)
    log.debug("policy {0!s} successfully saved.".format(name))
    string = "setPolicy " + name
    res[string] = ret
    g.audit_object.log({"success": True})

    return send_result(res)


@policy_blueprint.route('/', methods=['GET'])
@policy_blueprint.route('/<name>', methods=['GET'])
@policy_blueprint.route('/export/<export>', methods=['GET'])
@log_with(log)
def get_policy(name=None, export=None):
    """
    this function is used to retrieve the policies that you
    defined.
    It can also be used to export the policy to a file.

    :query name: will only return the policy with the given name
    :query export: The filename needs to be specified as the
        third part of the URL like policy.cfg. It
        will then be exported to this file.
    :query realm: will return all policies in the given realm
    :query scope: will only return the policies within the given scope
    :query active: Set to true or false if you only want to display
        active or inactive policies.

    :return: a json result with the configuration of the specified policies
    :rtype: json

    :status 200: Policy created or modified.
    :status 401: Authentication failed

    **Example request**:

    In this example a policy "pol1" is created.

    .. sourcecode:: http

       GET /policy/pol1 HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.0 200 OK
       Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": {
              "pol_update_del": {
                "action": "enroll",
                "active": true,
                "client": "1.1.1.1",
                "name": "pol_update_del",
                "realm": "r1",
                "resolver": "test",
                "scope": "selfservice",
                "time": "",
                "user": "admin"
              }
            }
          },
          "version": "privacyIDEA unknown"
        }
    """
    param = getLowerParams(request.all_data)
    realm = getParam(param, "realm")
    scope = getParam(param, "scope")
    active = getParam(param, "active")

    P = g.policy_object
    if not export:
        log.debug("retrieving policy name: {0!s}, realm: {1!s}, scope: {2!s}".format(name, realm, scope))

        pol = P.get_policies(name=name, realm=realm, scope=scope,
                             active=active, all_times=True)
        ret = send_result(pol)
    else:
        # We want to export all policies
        pol = P.get_policies()
        response = make_response(export_policies(pol))
        response.headers["Content-Disposition"] = ("attachment; "
                                                   "filename=%s" % export)
        ret = response

    g.audit_object.log({"success": True,
                        'info': u"name = {0!s}, realm = {1!s}, scope = {2!s}".format(name, realm, scope)})
    return ret


@policy_blueprint.route('/<name>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.POLICYDELETE)
def delete_policy_api(name=None):
    """
    This deletes the policy of the given name.

    :jsonparam name: the policy with the given name
    :return: a json result about the delete success.
             In case of success value > 0

    :status 200: Policy created or modified.
    :status 401: Authentication failed

    **Example request**:

    In this example a policy "pol1" is created.

    .. sourcecode:: http

       DELETE /policy/pol1 HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.0 200 OK
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
    ret = delete_policy(name)
    g.audit_object.log({'success': ret,
                        'info': name})
    return send_result(ret)


@policy_blueprint.route('/import/<filename>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.POLICYWRITE)
def import_policy_api(filename=None):
    """
    This function is used to import policies from a file.

    :jsonparam filename: The name of the file in the request

    :formparam file: The uploaded file contents

    :return: A json response with the number of imported policies.

    :status 200: Policy created or modified.
    :status 401: Authentication failed

    **Example request**:

    .. sourcecode:: http

       POST /policy/import/backup-policy.cfg HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.0 200 OK
       Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": 2
          },
          "version": "privacyIDEA unknown"
        }


    """
    policy_file = request.files['file']
    file_contents = ""
    # In case of form post requests, it is a "instance" of FieldStorage
    # i.e. the Filename is selected in the browser and the data is
    # transferred
    # in an iframe. see: http://jquery.malsup.com/form/#sample4
    #
    if type(policy_file) == FieldStorage:  # pragma: no cover
        log.debug("Field storage file: %s", policy_file)
        file_contents = policy_file.value
    elif type(policy_file) == FileStorage:
        log.debug("Werkzeug File storage file: %s", policy_file)
        file_contents = policy_file.read()
    else:  # pragma: no cover
        file_contents = policy_file

    if file_contents == "":
        log.error("Error loading/importing policy file. file {0!s} empty!".format(
                  filename))
        raise ParameterError("Error loading policy. File empty!")

    policy_num = import_policies(file_contents=file_contents)
    g.audit_object.log({"success": True,
                        'info': u"imported {0:d} policies from file {1!s}".format(
                            policy_num, filename)})

    return send_result(policy_num)


@policy_blueprint.route('/check', methods=['GET'])
@log_with(log)
def check_policy_api():
    """
    This function checks, if the given parameters would match a defined policy
    or not.

    :query user: the name of the user
    :query realm: the realm of the user or the realm the administrator
        want to do administrative tasks on.
    :query resolver: the resolver of a user
    :query scope: the scope of the policy
    :query action: the action that is done - if applicable
    :query IP_Address client: the client, from which this request would be
        issued

    :return: a json result with the keys allowed and policy in the value key
    :rtype: json

    :status 200: Policy created or modified.
    :status 401: Authentication failed

    **Example request**:

    .. sourcecode:: http

       GET /policy/check?user=admin&realm=r1&client=172.16.1.1 HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.0 200 OK
       Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": {
              "pol_update_del": {
                "action": "enroll",
                "active": true,
                "client": "172.16.0.0/16",
                "name": "pol_update_del",
                "realm": "r1",
                "resolver": "test",
                "scope": "selfservice",
                "time": "",
                "user": "admin"
              }
            }
          },
          "version": "privacyIDEA unknown"
        }

    """
    res = {}
    param = getLowerParams(request.all_data)

    user = getParam(param, "user", required)
    realm = getParam(param, "realm", required)
    scope = getParam(param, "scope", required)
    action = getParam(param, "action", required)
    client = getParam(param, "client", optional)
    resolver = getParam(param, "resolver", optional)

    P = g.policy_object
    policies = P.get_policies(user=user, realm=realm, resolver=resolver,
                              scope=scope, action=action, client=client,
                              active=True)
    if policies:
        res["allowed"] = True
        res["policy"] = policies
        policy_names = []
        for pol in policies:
            policy_names.append(pol.get("name"))
        g.audit_object.log({'info': u"allowed by policy {0!s}".format(policy_names)})
    else:
        res["allowed"] = False
        res["info"] = "No policies found"

    g.audit_object.log({"success": True,
                        'action_detail': "action = %s, realm = %s, scope = "
                                         "%s" % (action, realm, scope)
                        })

    return send_result(res)


@policy_blueprint.route('/defs', methods=['GET'])
@policy_blueprint.route('/defs/<scope>', methods=['GET'])
@log_with(log)
def get_policy_defs(scope=None):
    """
    This is a helper function that returns the POSSIBLE policy
    definitions, that can
    be used to define your policies.

    :query scope: if given, the function will only return policy
                  definitions for the given scope.

    :return: The policy definitions of the allowed scope with the actions and
        action types. The top level key is the scope.
    :rtype: dict
    """
    pol = {}
    static_pol = get_static_policy_definitions()
    dynamic_pol = get_dynamic_policy_definitions()

    # combine static and dynamic policies
    keys = static_pol.keys() + dynamic_pol.keys()
    pol = {k: dict(static_pol.get(k, {}).items()
                   + dynamic_pol.get(k, {}).items()) for k in keys}

    if scope:
        pol = pol.get(scope)

    g.audit_object.log({"success": True,
                        'info': scope})
    return send_result(pol)
