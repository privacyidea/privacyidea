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
from flask import Blueprint, request, current_app
from .lib.utils import (getParam,
                        getLowerParams,
                        optional,
                        required,
                        send_result,
                        check_policy_name, send_file, get_required)
from ..lib.log import log_with
from ..lib.policies.policy_conditions import ConditionHandleMissingData
from ..lib.policy import (set_policy, ACTION, rename_policy,
                          export_policies, import_policies,
                          delete_policy, get_static_policy_definitions,
                          enable_policy, get_policy_condition_sections,
                          get_policy_condition_comparators, Match, validate_values)
from ..lib.token import get_dynamic_policy_definitions
from ..lib.error import (ParameterError)
from privacyidea.lib.utils import is_true
from privacyidea.lib.config import get_privacyidea_node_names
from ..api.lib.prepolicy import prepolicy, check_base_action

from flask import g
from werkzeug.datastructures import FileStorage

import logging


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

@policy_blueprint.route('/<old_name>', methods=['PATCH'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.POLICYWRITE)
def patch_policy_name_api(old_name):
    """
    Rename an existing policy.

    Only the policy’s name is modified; all other attributes remain unchanged.

    :param old_name: Current name of the policy (from the URL).
    :jsonparam name: New name to assign to the policy (in the JSON body).
    :return: Database ID of the renamed policy.
    """
    new_name = get_required(request.all_data, "name")
    result = rename_policy(name=old_name, new_name=new_name)
    g.audit_object.log({"success": True, "action_detail": f"{old_name} renamed to {new_name}"})
    return send_result(result)

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
    :jsonparam priority: the priority of the policy
    :jsonparam description: a description of the policy
    :jsonparam adminrealm: Realm of the administrator. (only for admin scope)
    :jsonparam adminuser: Username of the administrator. (only for admin scope)
    :jsonparam action: which action may be executed
    :jsonparam realm: For which realm this policy is valid
    :jsonparam resolver: This policy is valid for this resolver
    :jsonparam user: The policy is valid for these users.
        string with wild cards or list of strings
    :jsonparam time: on which time does this policy hold
    :jsonparam pinode: The privacyIDEA node (or list of nodes) for which this policy is valid
    :jsonparam client: for which requesting client this should be
    :jsontype client: IP address with subnet
    :jsonparam user_agents: List of user agents for which this policy is valid.
    :jsonparam active: bool, whether this policy is active or not
    :jsonparam check_all_resolvers: bool, whether all all resolvers in which
        the user exists should be checked with this policy.
    :jsonparam conditions: a (possibly empty) list of conditions of the policy.
        Each condition is encoded as a list with 5 elements:
        ``[section (string), key (string), comparator (string), value (string), active (boolean)]``
        Hence, the ``conditions`` parameter expects a list of lists.
        When privacyIDEA checks if a defined policy should take effect,
        *all* conditions of the policy must be fulfilled for the policy to match.
        Note that the order of conditions is not guaranteed to be preserved.

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

    The policy POST request can also take the parameter of conditions. This is a list of conditions sets:
    [ [ "userinfo", "memberOf", "equals", "groupA", "true" ], [ ... ] ]
    With the entries being the ``section``, the ``key``, the ``comparator``, the ``value`` and ``active``.
    For more on conditions see :ref:`policy_conditions`.


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
    check_policy_name(name)

    action = get_required(param, "action")
    scope = get_required(param, "scope")
    realm = param.get("realm")
    resolver = param.get("resolver")
    pinode = param.get("pinode")
    user = param.get("user")
    time = param.get("time")
    client = param.get("client")
    active = param.get("active")
    check_all_resolvers = param.get("check_all_resolvers")
    admin_realm = param.get("adminrealm")
    admin_user = param.get("adminuser")
    priority = int(param.get("priority", 1))
    conditions = param.get("conditions")
    description = param.get("description")
    user_agents = param.get("user_agents", None)

    # Validate admin realms here, because the allowed realms need to be read from the config file
    # (avoid flask imports on lib level)
    valid_admin_realms = current_app.config.get("SUPERUSER_REALM", [])
    validate_values(admin_realm, valid_admin_realms, "Admin Realms")

    g.audit_object.log({'action_detail': name,
                        'info': "{0!s}".format(param)})
    ret = set_policy(name=name, scope=scope, action=action, realm=realm,
                     resolver=resolver, user=user, client=client, time=time,
                     active=active or True, adminrealm=admin_realm,
                     adminuser=admin_user, pinode=pinode,
                     check_all_resolvers=check_all_resolvers or False,
                     priority=priority, conditions=conditions,
                     description=description, user_agents=user_agents)
    log.debug("policy {0!s} successfully saved.".format(name))
    string = "setPolicy " + name
    res[string] = ret
    g.audit_object.log({"success": True})

    return send_result(res)


@policy_blueprint.route('/', methods=['GET'])
@policy_blueprint.route('/<name>', methods=['GET'])
@policy_blueprint.route('/export/<export>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.POLICYREAD)
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
    if active is not None:
        active = is_true(active)

    P = g.policy_object
    if not export:
        log.debug("retrieving policy name: {0!s}, realm: {1!s}, scope: {2!s}".format(name, realm, scope))

        pol = P.list_policies(name=name, realm=realm, scope=scope, active=active)
        ret = send_result(pol)
    else:
        # We want to export all policies
        pol = P.list_policies()
        ret = send_file(export_policies(pol), export, content_type='text/plain')

    g.audit_object.log({"success": True,
                        'info': "name = {0!s}, realm = {1!s}, scope = {2!s}".format(name, realm, scope)})
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
    g.audit_object.log({'success': True,
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
    if isinstance(policy_file, FileStorage):
        log.debug(f"Werkzeug File storage file: {policy_file}")
        file_contents = policy_file.read()
    else:  # pragma: no cover
        # TODO: is this even possible?
        file_contents = policy_file

    # The policy file should contain readable characters
    try:
        if isinstance(file_contents, bytes):
            file_contents = file_contents.decode()
    except UnicodeDecodeError as e:
        log.error(f"Unable to convert contents of file '{filename}' to unicode: {e}")
        raise ParameterError("Unable to convert file contents. Binary data is not supported")

    if file_contents == "":
        log.error("Error loading/importing policy file. file {0!s} empty!".format(
                  filename))
        raise ParameterError("Error loading policy. File empty!")

    policy_num = import_policies(file_contents=file_contents)
    g.audit_object.log({"success": True,
                        'info': "imported {0:d} policies from file {1!s}".format(
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

    policies = Match.generic(g, scope=scope, user=user, resolver=resolver, realm=realm,
                             action=action, client=client, active=True).policies()
    if policies:
        res["allowed"] = True
        res["policy"] = policies
        policy_names = []
        for pol in policies:
            policy_names.append(pol.get("name"))
        g.audit_object.log({'info': "allowed by policy {0!s}".format(policy_names)})
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

    If the given scope is "conditions", this returns a dictionary with the following keys:
     * ``"sections"``, containing a dictionary mapping each condition section name to a dictionary with
       the following keys:
         * ``"description"``, a human-readable description of the section
     * ``"comparators"``, containing a dictionary mapping each comparator to a dictionary with the following keys:
         * ``"description"``, a human-readable description of the comparator
     * ``"handle_missing_data"``, containing a dictionary mapping each handle_missing_data to a dictionary with the
        following keys:
            * ``"display_value"``, a human-readable name of the behaviour to be displayed in the webUI
            * ``"description"``, a short description of the behaviour

    if the scope is "pinodes", it returns a list of the configured privacyIDEA nodes.

    :query scope: if given, the function will only return policy
                  definitions for the given scope.

    :return: The policy definitions of the allowed scope with the actions and
        action types. The top level key is the scope.
    :rtype: dict
    """

    if scope == 'conditions':
        # special treatment: get descriptions of conditions
        section_descriptions = get_policy_condition_sections()
        comparator_descriptions = get_policy_condition_comparators()
        handle_missing_data = ConditionHandleMissingData.get_selection_dict()
        result = {
            "sections": section_descriptions,
            "comparators": comparator_descriptions,
            "handle_missing_data": handle_missing_data
        }
    elif scope == 'pinodes':
        result = get_privacyidea_node_names()
    else:
        static_pol = get_static_policy_definitions()
        dynamic_pol = get_dynamic_policy_definitions()

        # combine static and dynamic policies
        keys = list(static_pol) + list(dynamic_pol)
        result = {k: dict(list(static_pol.get(k, {}).items())
                          + list(dynamic_pol.get(k, {}).items())) for k in keys}

        if scope:
            result = result.get(scope)

    g.audit_object.log({"success": True,
                        'info': scope})
    return send_result(result)
