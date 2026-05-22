# SPDX-FileCopyrightText: 2025 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2019-09-04 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add decorators for event handling
# 2016-07-12 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add decorator for checking realmadmin realms during userlist
# 2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
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

"""
The user REST API exposes the user records held by the configured
user resolvers (LDAP, SQL, ...). Endpoints fall in three groups:

* listing / lookup — :http:get:`/user/`.
* user-store CRUD against editable resolvers — admin-only:
  :http:post:`/user/`, :http:put:`/user/`,
  :http:delete:`/user/(resolvername)/(username)`.
* custom user attributes — small key/value records that privacyIDEA
  attaches to a user independent of the user store:
  :http:get:`/user/attribute`, :http:post:`/user/attribute`,
  :http:delete:`/user/attribute/(attrkey)/(username)/(realm)`,
  :http:get:`/user/editable_attributes/`.

CRUD on user-store records requires admin authentication and the
respective policy action (:ref:`policy_adduser`,
:ref:`policy_updateuser`, :ref:`policy_deleteuser`); the underlying
resolver must also have the ``editable`` flag set. Listing is gated
by :ref:`policy_userlist` and is realm-scoped for realm-admins. The
custom-attribute write/delete endpoints are gated by the
:ref:`policy_set_custom_user_attributes` and
:ref:`policy_delete_custom_user_attributes` policies and may be
invoked by users on themselves as well as by admins on other users.
"""
from flask_babel import _
import logging

from flask import g, Blueprint, request

from privacyidea.api.auth import admin_required
from privacyidea.api.lib.prepolicy import prepolicy, check_base_action, realmadmin, check_custom_user_attributes
from privacyidea.api.lib.utils import send_result
from privacyidea.lib.params import get_optional, get_required
from privacyidea.lib.error import ParameterError, PolicyError
from privacyidea.lib.event import event
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import get_allowed_custom_attributes
from privacyidea.lib.user import get_user_list, create_user, User, is_attribute_at_all
from privacyidea.lib.utils import is_true

log = logging.getLogger(__name__)

user_blueprint = Blueprint('user_blueprint', __name__)


@user_blueprint.route('/', methods=['GET'])
@prepolicy(realmadmin, request, PolicyAction.USERLIST)
@prepolicy(check_base_action, request, PolicyAction.USERLIST)
@event("user_list", request, g)
def get_users():
    """
    Return users from the configured resolvers.

    When called by a regular user the response is restricted to that
    user's own record \u2014 the ``user`` / ``realm`` / ``resolver``
    parameters are bound to the calling user before the search runs.

    Requires admin authentication and the policy action
    :ref:`policy_userlist` to list other users.

    Realm and resolver scoping is additive: ``realm=R`` queries every
    resolver in ``R``, ``resolver=X`` queries ``X``, and combining both
    queries the union. With neither parameter all resolvers across all
    realms are queried.

    :query realm: query every resolver in this realm.
    :query resolver: query this resolver.
    :query user / username: filter by login name; supports the ``*``
        wildcard.
    :query <resolver-attr>: any other key is forwarded to each
        resolver's ``getUserList`` as a search field. Wildcard support
        is resolver-class-specific.
    :query attributes: comma-separated list of attribute names to
        return per user. In addition to user-store attributes,
        ``resolver`` and ``editable`` are privacyIDEA-managed extras.
        If omitted, all attributes are returned.
    :query include_custom_attributes: ``True`` (default) merges
        privacyIDEA custom user attributes into the response. Custom
        attributes are only merged when a single realm is in scope.
    :status 200: list of user dictionaries in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       GET /user/?realm=realm1 HTTP/1.1
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
             {
               "username": "alice",
               "userid": "1009",
               "givenname": "Alice",
               "surname": "Liddell",
               "email": "alice@example.com",
               "mobile": "+44 12345",
               "phone": "+44 67890",
               "description": "Alice Liddell,...",
               "resolver": "ldap-corp"
             }
           ]
         },
         "version": "privacyIDEA unknown"
       }
    """
    realm = get_optional(request.all_data, "realm")
    search_parameters = dict(request.all_data)
    requested_attributes = request.all_data.get("attributes")
    if requested_attributes:
        requested_attributes = [attr.strip() for attr in requested_attributes.split(",")]
        del search_parameters['attributes']

    include_custom_attributes = (is_true(request.all_data.get("include_custom_attributes", True))
                                 and is_attribute_at_all())
    if "include_custom_attributes" in search_parameters:
        del search_parameters["include_custom_attributes"]
    users = get_user_list(search_parameters, include_custom_attributes=include_custom_attributes,
                          requested_attributes=requested_attributes)

    g.audit_object.log({'success': True,
                        'info': f"realm: {realm!s}"})

    return send_result(users)


@user_blueprint.route('/attribute', methods=['POST'])
@prepolicy(check_custom_user_attributes, request, "set")
@event("set_custom_user_attribute", request, g)
def set_user_attribute():
    """
    Set a custom user attribute. Custom attributes are key/value records
    privacyIDEA stores alongside a user, independent of the user store.

    When invoked by a regular user the ``user`` / ``resolver`` / ``realm``
    body fields are bound to the calling user.

    Authorization is gated by the :ref:`policy_set_custom_user_attributes`
    policy. The policy value whitelists allowed key/value combinations
    (the ``*`` wildcard is allowed for keys or values). Attribute keys
    starting with an internal privacyIDEA prefix are rejected.

    :jsonparam user: user name (required).
    :jsonparam resolver: resolver name.
    :jsonparam realm: realm name.
    :jsonparam key: attribute name (required).
    :jsonparam value: attribute value (required).
    :jsonparam type: optional attribute type identifier.
    :status 200: database id of the attribute row in ``result.value``.
    :status 400: attribute name uses a reserved internal prefix.
    :status 403: the active policy does not allow this key/value
        combination.
    """
    # We basically need a user, otherwise we will fail, but the
    # user object is later simply used from request.User. We only
    # need to avoid an empty User object.
    _user = get_required(request.all_data, "user")
    attrkey = get_required(request.all_data, "key")
    attrvalue = get_required(request.all_data, "value")
    attrtype = get_optional(request.all_data, "type")

    r = request.User.set_attribute(attrkey, attrvalue, attrtype)
    g.audit_object.log({"success": True,
                        "info": f"{attrkey!s}"})
    return send_result(r)


@user_blueprint.route('/attribute', methods=['GET'])
@event("get_user_attribute", request, g)
def get_user_attribute():
    """
    Return custom user attributes. This does **not** include attributes
    from the user store (those come back via :http:get:`/user/`); only
    the privacyIDEA-managed custom attributes are returned.

    When invoked by a regular user the ``user`` / ``resolver`` / ``realm``
    parameters are bound to the calling user.

    :query user: user name (required to identify the target).
    :query resolver: resolver name.
    :query realm: realm name.
    :query key: attribute name. If omitted, all custom attributes are
        returned as a dict; if given, the value of that single attribute
        is returned (or ``null`` if it is not set).
    :status 200: attribute value or dict of attributes in ``result.value``.
    """
    _user = get_required(request.all_data, "user")
    attrkey = get_optional(request.all_data, "key")
    r = request.User.attributes
    if attrkey:
        r = r.get(attrkey)
    g.audit_object.log({"success": True,
                        "info": f"{attrkey!s}"})
    return send_result(r)


@user_blueprint.route('/editable_attributes/', methods=['GET'])
@event("get_editable_attributes", request, g)
def get_editable_attributes():
    """
    Return the custom user attributes that the calling principal is
    allowed to set or delete on the given user, computed from the
    active :ref:`policy_set_custom_user_attributes` and
    :ref:`policy_delete_custom_user_attributes` policies. The WebUI
    uses this to decide which fields to render as editable.

    When invoked by a regular user the ``user`` / ``resolver`` / ``realm``
    parameters are bound to the calling user.

    The result is a dict with two keys:

    * ``"delete"`` — list of attribute names that may be deleted; ``*``
      means any attribute name.
    * ``"set"`` — dict of ``key: [allowed_values]``; ``*`` may appear
      as a key (any key allowed) or in the value list (any value
      allowed).

    :query user: user name (required to identify the target).
    :query resolver: resolver name.
    :query realm: realm name.
    :status 200: editable-attributes dict in ``result.value``.
    """
    _user = get_required(request.all_data, "user")
    r = get_allowed_custom_attributes(g, request.User)
    g.audit_object.log({"success": True})
    return send_result(r)


@user_blueprint.route('/attribute/<attrkey>/<username>/<realm>', methods=['DELETE'])
@prepolicy(check_custom_user_attributes, request, "delete")
@event("delete_custom_user_attribute", request, g)
def delete_user_attribute(attrkey, username, realm=None):
    """
    Delete a single custom user attribute from the named user.

    Authorization is gated by the
    :ref:`policy_delete_custom_user_attributes` policy: a
    whitespace-separated list of allowed attribute names; ``*`` matches
    any name.

    :param attrkey: path component, the attribute name to remove.
    :param username: path component, the target user.
    :param realm: path component, the target realm.
    :status 200: number of attribute rows removed in ``result.value``.
    :status 403: the active policy does not allow deleting this
        attribute name, or a non-admin caller targeted a different user.
    """
    # Non-admin callers may only delete attributes on themselves. The
    # ``check_custom_user_attributes`` prepolicy evaluates the policy
    # against ``request.User`` (which the request rewrite binds to the
    # caller for role=user), but the path components below are not
    # rewritten — without this check a user with a self-scoped policy
    # could target a different user via the URL.
    if g.logged_in_user.get("role") == "user":
        caller_user = g.logged_in_user.get("username")
        caller_realm = g.logged_in_user.get("realm")
        if username != caller_user or (realm or "") != (caller_realm or ""):
            raise PolicyError("User is not allowed to delete attributes of other users.")
    user = User(username, realm)
    r = user.delete_attribute(attrkey)
    g.audit_object.log({"success": True,
                        "info": f"{attrkey!s}"})
    return send_result(r)


@user_blueprint.route('/<resolvername>/<username>', methods=['DELETE'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.DELETEUSER)
@event("user_delete", request, g)
def delete_user(resolvername=None, username=None):
    """
    Delete a user from the user store. The resolver must have the
    ``editable`` flag set.

    Requires admin authentication and the policy action
    :ref:`policy_deleteuser`.

    :param resolvername: path component, the resolver the user lives in.
    :param username: path component, the user name to delete.
    :status 200: ``True`` on success in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       DELETE /user/<resolvername>/<username> HTTP/1.1
       Host: example.com
       Accept: application/json
    """
    user_obj = request.User
    res = user_obj.delete()
    g.audit_object.log({"success": res,
                        "info": f"{user_obj!s}"})
    return send_result(res)


@user_blueprint.route('', methods=['POST'])
@user_blueprint.route('/', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.ADDUSER)
@event("user_add", request, g)
def create_user_api():
    """
    Create a new user in an editable resolver. The set of fields read
    from the request is determined by the resolver's attribute map —
    fields outside that map are ignored.

    Requires admin authentication and the policy action :ref:`policy_adduser`.

    :jsonparam user: user name of the new user (required).
    :jsonparam resolver: resolver to create the user in (required).
    :jsonparam password: password the user will authenticate with.
    :jsonparam: any other attribute name in the resolver's map
        (``surname``, ``givenname``, ``email``, ``mobile``, ``phone``,
        ``description``, ...).
    :status 200: id of the new user in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       POST /user/ HTTP/1.1
       Host: example.com
       Content-Type: application/x-www-form-urlencoded

       user=new_user&resolver=local-sql&surname=Doe&givenname=Jane
       &email=jane@example.com&password=...
    """
    # We can not use "get_user_from_param", since this checks the existence
    # of the user.
    attributes = _get_attributes_from_param(request.all_data)
    username = get_required(request.all_data, "user")
    resolvername = get_required(request.all_data, "resolver")
    # Remove the password from the attributes, so that we can hide it in the
    # logs
    password = attributes.get("password")
    if "password" in attributes:
        del attributes["password"]
    uid = create_user(resolvername, attributes, password=password)
    g.audit_object.log({"success": True if uid else False,
                        "info": f"{uid!s}: {username!s}/{resolvername!s}"})
    return send_result(uid)


@user_blueprint.route('', methods=['PUT'])
@user_blueprint.route('/', methods=['PUT'])
@prepolicy(check_base_action, request, PolicyAction.UPDATEUSER)
@event("user_update", request, g)
def update_user():
    """
    Update a user in an editable resolver.

    Admins may update any user the ``updateuser`` policy permits. An
    authenticated user without admin role may update only themselves —
    the ``user`` / ``resolver`` / ``realm`` body fields are bound to
    the calling user (typical use: a user changing their own password).

    Requires the policy action :ref:`policy_updateuser`. The resolver
    must have the ``editable`` flag set.

    :jsonparam user: user name (required).
    :jsonparam resolver: resolver name (required).
    :jsonparam userid: optional user id; if given, identifies the
        record by uid instead of by login.
    :jsonparam password: new password (sent through ``password=``
        rather than as an attribute field).
    :jsonparam: any other attribute name in the resolver's map.
    :status 200: ``True`` on success in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       PUT /user/ HTTP/1.1
       Host: example.com
       Content-Type: application/x-www-form-urlencoded

       user=existing_user&resolver=local-sql&password=...&email=...
    """
    attributes = _get_attributes_from_param(request.all_data)
    username = get_required(request.all_data, "user")
    resolvername = get_required(request.all_data, "resolver")
    userid = get_optional(request.all_data, "userid")
    if userid is not None:
        # Create the user object by uid
        user_obj = User(resolver=resolvername, uid=userid)
    else:
        user_obj = User(login=username, resolver=resolvername)
    # Remove the password from the attributes, so that we can hide it in the
    # logs
    password = attributes.get("password")
    if password:
        del attributes["password"]
    success = user_obj.update_user_info(attributes, password=password)
    g.audit_object.log({"success": success,
                        "info": f"{success!s}: {username!s}/{resolvername!s}"})
    return send_result(success)


def _get_attributes_from_param(param):
    from privacyidea.lib.resolver import get_resolver_object
    map = get_resolver_object(get_required(param, "resolver")).map
    username = get_required(param, "user")

    # Add attributes
    attributes = {"username": username}
    for attribute in map.keys():
        value = get_optional(param, attribute)
        if value:
            attributes[attribute] = get_optional(param, attribute)

    return attributes
