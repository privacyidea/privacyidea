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
The policy REST API manages privacyIDEA policies — the rule
definitions that decide what an admin or user is allowed to do, what
defaults apply, and how authentication and enrollment behave. See
:ref:`policies` for the conceptual chapter and :ref:`policy_conditions`
for the policy-condition feature.

All endpoints require admin authentication. Reading is gated by the
admin policy action :ref:`policyread`; create, update, enable,
disable, rename and import by :ref:`policywrite`; deletion by
:ref:`policydelete`. The introspection helpers under ``/policy/defs``
and ``/policy/check`` are admin-only.
"""
from flask_babel import _
from flask import Blueprint, request, current_app
from .lib.utils import (getParam,
                        getLowerParams,
                        optional,
                        required,
                        send_result,
                        check_policy_name, send_file, get_required)
from ..lib.log import log_with
from ..lib.policies.actions import PolicyAction
from ..lib.policies.conditions import ConditionHandleMissingData
from ..lib.policy import (set_policy, rename_policy,
                          export_policies, import_policies,
                          delete_policy, get_static_policy_definitions,
                          enable_policy, get_policy_condition_sections,
                          get_policy_condition_comparators, Match, validate_values, get_policies, SCOPE)
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
@prepolicy(check_base_action, request, PolicyAction.POLICYWRITE)
def enable_policy_api(name):
    """
    Enable a policy. The policy definition is preserved; only the
    ``active`` flag is set to ``True``.

    Requires admin authentication and the policy action :ref:`policywrite`.

    :param name: path component, the name of the policy.
    :status 200: database id of the policy in ``result.value``.
    :status 404: no policy with that name exists.
    """
    p = enable_policy(name)
    g.audit_object.log({"success": True})
    return send_result(p)


@policy_blueprint.route('/disable/<name>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.POLICYWRITE)
def disable_policy_api(name):
    """
    Disable a policy. The policy definition is preserved; only the
    ``active`` flag is set to ``False``.

    Requires admin authentication and the policy action :ref:`policywrite`.

    :param name: path component, the name of the policy.
    :status 200: database id of the policy in ``result.value``.
    :status 404: no policy with that name exists.
    """
    p = enable_policy(name, False)
    g.audit_object.log({"success": True})
    return send_result(p)

@policy_blueprint.route('/<old_name>', methods=['PATCH'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.POLICYWRITE)
def patch_policy_name_api(old_name):
    """
    Rename a policy. Only the policy's name is modified; all other
    attributes are preserved. The new name must satisfy the same
    character/prefix rules as a freshly-created policy
    (``a-zA-Z0-9_.-`` plus space; ``check`` and the
    ``pi-update-policy-`` prefix are reserved).

    Requires admin authentication and the policy action :ref:`policywrite`.

    :param old_name: path component, the current name of the policy.
    :jsonparam name: the new name to assign (required).
    :status 200: database id of the renamed policy in ``result.value``.
    :status 400: ``old_name`` does not exist, ``name`` already exists,
        or ``name`` violates the character/prefix rules.
    """
    new_name = get_required(request.all_data, "name")
    result = rename_policy(name=old_name, new_name=new_name)
    g.audit_object.log({"success": True, "action_detail": f"{old_name} renamed to {new_name}"})
    return send_result(result)

@policy_blueprint.route('/<name>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.POLICYWRITE)
def set_policy_api(name=None):
    """
    Create or update a policy. If a policy with the given ``name``
    already exists, it is updated; otherwise it is created.

    Policies in privacyIDEA gate what an admin or user is allowed to do,
    define defaults, and shape authentication and enrollment behavior.
    See :ref:`policies` for the conceptual model and the available
    actions per scope, and :ref:`policy_conditions` for the optional
    condition mechanism.

    Requires admin authentication and the policy action :ref:`policywrite`.

    :param name: path component, the policy name. Allowed characters
        are ``a-zA-Z0-9_.-``; whitespace is rejected. The literal
        ``check`` and any name starting with ``pi-update-policy-``
        are reserved.
    :jsonparam scope: scope of the policy — one of ``admin``,
        ``user``, ``authentication``, ``authorization``, ``enrollment``,
        ``webui``, ``register``, ``token``, ``container`` (required).
    :jsonparam action: scope-specific action or comma-separated list.
        Required for every scope except ``user`` (where it may be
        empty).
    :jsonparam priority: integer priority; lower values bind first.
        Must be ``>= 1``. Default ``1``.
    :jsonparam description: free-form description.
    :jsonparam adminrealm: admin realm the policy applies to (admin
        scope only). Validated against ``SUPERUSER_REALM`` from
        ``pi.cfg``.
    :jsonparam adminuser: comma-separated list of admin user names
        (admin scope only).
    :jsonparam realm: user realm(s) for which the policy is valid.
        Validated against the configured realms.
    :jsonparam resolver: resolver(s) for which the policy is valid.
        Validated against the configured resolvers.
    :jsonparam user: user(s) the policy applies to — string with
        wildcards or list of strings.
    :jsonparam time: time-of-day window during which the policy is
        active (see the policy reference for the format).
    :jsonparam pinode: privacyIDEA node or list of nodes the policy
        applies to. Validated against the configured nodes.
    :jsonparam client: client IP, optionally with a subnet
        (e.g. ``172.16.0.0/16``).
    :jsonparam user_agents: list of user-agent identifiers the policy
        applies to.
    :jsonparam active: boolean, whether the policy starts out active.
        Default ``True``.
    :jsonparam check_all_resolvers: if ``True``, the policy is checked
        against every resolver in which the user exists.
    :jsonparam conditions: list of policy conditions. Each entry is a
        5- or 6-element list
        ``[section, key, comparator, value, active(, handle_missing_data)]``.
        All conditions must match for the policy to take effect.
        The order of conditions is not guaranteed to be preserved.
    :status 200: ``{"setPolicy <name>": <db-id>}`` in ``result.value``.
    :status 400: invalid scope, invalid policy name, priority below
        1, invalid time format, or unknown realm / resolver / pinode /
        admin realm.

    **Example request**:

    .. sourcecode:: http

       POST /policy/pol1 HTTP/1.1
       Host: example.com
       Content-Type: application/json

       {
         "scope": "admin",
         "realm": "realm1",
         "action": "enroll, disable",
         "conditions": [
           ["userinfo", "memberOf", "equals", "groupA", true]
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
           "value": {"setPolicy pol1": 1}
         },
         "version": "privacyIDEA unknown"
       }
    """
    res = {}
    param = request.all_data
    check_policy_name(name)

    scope = get_required(param, "scope")
    if scope == SCOPE.USER:
        action = param.get("action")
    else:
        action = get_required(param, "action")
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
@prepolicy(check_base_action, request, PolicyAction.POLICYREAD)
def get_policy(name=None, export=None):
    """
    Return policy definitions, or export them to a file. The behavior
    depends on the URL shape:

    * ``/policy/`` — return all policies (subject to the query
      filters) as a dictionary keyed by policy name.
    * ``/policy/<name>`` — return the named policy as a single-entry
      dictionary.
    * ``/policy/export/<filename>`` — export every policy to a
      ``.cfg`` file; the response Content-Type is ``text/plain`` and
      the filename in the path is suggested as the download name.

    Requires admin authentication and the policy action :ref:`policyread`.

    :param name: path component, the name of a single policy.
    :param export: path component, the suggested filename for the
        export download (e.g. ``policies.cfg``).
    :query realm: return only policies that apply to this realm.
    :query scope: return only policies in the given scope.
    :query active: ``true`` / ``false`` to filter by the active flag.
    :status 200: dictionary of policy definitions in ``result.value``,
        or — for the export URL — a ``text/plain`` response body.

    **Example request**:

    .. sourcecode:: http

       GET /policy/pol1 HTTP/1.1
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

    if not export:
        log.debug("retrieving policy name: {0!s}, realm: {1!s}, scope: {2!s}".format(name, realm, scope))

        policies = get_policies(name=name, realm=realm, scope=scope, active=active)
        ret = send_result(policies)
    else:
        # We want to export all policies
        policies = get_policies()
        ret = send_file(export_policies(policies), export, content_type='text/plain')

    g.audit_object.log({"success": True,
                        'info': "name = {0!s}, realm = {1!s}, scope = {2!s}".format(name, realm, scope)})
    return ret


@policy_blueprint.route('/<name>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.POLICYDELETE)
def delete_policy_api(name=None):
    """
    Delete the named policy.

    Requires admin authentication and the policy action :ref:`policydelete`.

    :param name: path component, the name of the policy to delete.
    :status 200: database id of the deleted policy in ``result.value``.
    :status 404: no policy with that name exists.

    **Example request**:

    .. sourcecode:: http

       DELETE /policy/pol1 HTTP/1.1
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
    ret = delete_policy(name)
    g.audit_object.log({'success': True,
                        'info': name})
    return send_result(ret)


@policy_blueprint.route('/import/<filename>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.POLICYWRITE)
def import_policy_api(filename=None):
    """
    Import policies from a previously-exported ``.cfg`` file. The
    request body must be ``multipart/form-data`` with a single field
    named ``file`` carrying the file contents. The path component
    ``filename`` is used only for logging — it does not have to match
    the uploaded file's actual name.

    Requires admin authentication and the policy action :ref:`policywrite`.

    :param filename: path component, used as a log/audit label for
        the imported file.
    :reqheader Content-Type: ``multipart/form-data`` (required).
    :formparam file: the file contents (required).
    :status 200: number of imported policies in ``result.value``.
    :status 400: the file is empty or its contents are not valid
        text.

    **Example request**:

    .. sourcecode:: http

       POST /policy/import/backup-policy.cfg HTTP/1.1
       Host: example.com
       Content-Type: multipart/form-data; boundary=...

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
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
        raise ParameterError(_("Unable to convert file contents. Binary data is not supported"))

    if file_contents == "":
        log.error("Error loading/importing policy file. file {0!s} empty!".format(
                  filename))
        raise ParameterError(_("Error loading policy. File empty!"))

    policy_num = import_policies(file_contents=file_contents)
    g.audit_object.log({"success": True,
                        'info': "imported {0:d} policies from file {1!s}".format(
                            policy_num, filename)})

    return send_result(policy_num)


@policy_blueprint.route('/check', methods=['GET'])
@log_with(log)
def check_policy_api():
    """
    Probe whether a given (user, realm, scope, action, client,
    resolver) tuple would match any active policy. Used by the WebUI
    "Test policy" feature and as a self-check tool.

    Requires admin authentication.

    :query user: user name (required).
    :query realm: realm name (required).
    :query scope: policy scope to check (required).
    :query action: action to check (required).
    :query client: client IP, optionally with a subnet.
    :query resolver: resolver name.
    :status 200: ``result.value`` is ``{"allowed": true, "policy":
        <dict-of-matching-policies>}`` if at least one active policy
        matches, otherwise
        ``{"allowed": false, "info": "No policies found"}``.
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
    Return the catalogue of possible policy definitions — the
    actions, types and metadata that the WebUI uses to render the
    policy editor. Two literal scope values produce introspection
    output instead of policy actions:

    * ``conditions`` — return ``{"sections": ..., "comparators": ...,
      "handle_missing_data": ...}`` describing the policy-condition
      vocabulary. Each map carries per-entry ``description`` and (for
      ``handle_missing_data``) a WebUI-facing ``display_value``.
    * ``pinodes`` — return the list of privacyIDEA node names
      declared in the server configuration.

    Without ``scope``, the response is a dictionary keyed by every
    known scope (admin, user, authentication, authorization,
    enrollment, webui, ...) with the static + dynamically-discovered
    actions for each. With a regular scope name, only that scope's
    entry is returned.

    Requires admin authentication.

    :param scope: optional path component — a scope name
        (``admin``, ``user``, ...) or one of the literals
        ``conditions`` / ``pinodes``.
    :status 200: dict (or list, for ``pinodes``) of definitions in
        ``result.value``.
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
