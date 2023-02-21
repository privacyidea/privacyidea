# -*- coding: utf-8 -*-
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

from flask import (Blueprint,
                   request)
from .lib.utils import (getParam,
                        send_result)
from ..api.lib.prepolicy import (prepolicy, check_base_action, realmadmin,
                                 check_custom_user_attributes)
from ..lib.policy import ACTION, get_allowed_custom_attributes
from privacyidea.api.auth import admin_required, user_required
from privacyidea.lib.user import create_user, User, is_attribute_at_all
from privacyidea.lib.event import event


from flask import (g)
from ..lib.user import get_user_list
import logging


log = logging.getLogger(__name__)


user_blueprint = Blueprint('user_blueprint', __name__)


@user_blueprint.route('/', methods=['GET'])
@prepolicy(realmadmin, request, ACTION.USERLIST)
@prepolicy(check_base_action, request, ACTION.USERLIST)
@user_required
@event("user_list", request, g)
def get_users():
    """
    list the users in a realm

    A normal user can call this endpoint and will get information about his
    own account.

    :param realm: a realm that contains several resolvers. Only show users
                  from this realm
    :param resolver: a distinct resolvername
    :param <searchexpr>: a search expression, that depends on the ResolverClass
    
    :return: json result with "result": true and the userlist in "value".

    **Example request**:

    .. sourcecode:: http

       GET /user?realm=realm1 HTTP/1.1
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
                "description": "Cornelius K\u00f6lbel,,+49 151 2960 1417,+49 561 3166797,cornelius.koelbel@netknights.it",
                "email": "cornelius.koelbel@netknights.it",
                "givenname": "Cornelius",
                "mobile": "+49 151 2960 1417",
                "phone": "+49 561 3166797",
                "surname": "K\u00f6lbel",
                "userid": "1009",
                "username": "cornelius",
                "resolver": "name-of-resolver"
              }
            ]
          },
          "version": "privacyIDEA unknown"
        }
    """
    realm = getParam(request.all_data, "realm")
    attr = is_attribute_at_all()
    users = get_user_list(request.all_data, custom_attributes=attr)

    g.audit_object.log({'success': True,
                        'info': "realm: {0!s}".format(realm)})
    
    return send_result(users)


@user_blueprint.route('/attribute', methods=['POST'])
@prepolicy(check_custom_user_attributes, request, "set")
@user_required
@event("set_custom_user_attribute", request, g)
def set_user_attribute():
    """
    Set a custom attribute for a user.
    The user is specified by the usual parameters user, resolver and realm.
    When a user is calling the endpoint the parameters will be implicitly set.

    :httpparam user: The username of the user, for whom the attribute should be set
    :httpparam resolver: The resolver of the user (optional)
    :httpparam realm: The realm of the user (optional)
    :httpparam key: The name of the attributes
    :httpparam value: The value of the attribute
    :httpparam type: an optional type of the attribute

    The database id of the attribute is returned. The return
    value thus should be >=0.
    """
    # We basically need a user, otherwise we will fail, but the
    # user object is later simply used from request.User. We only
    # need to avoid an empty User object.
    _user = getParam(request.all_data, "user", optional=False)
    attrkey = getParam(request.all_data, "key", optional=False)
    attrvalue = getParam(request.all_data, "value", optional=False)
    attrtype = getParam(request.all_data, "type", optional=True)
    r = request.User.set_attribute(attrkey, attrvalue, attrtype)
    g.audit_object.log({"success": True,
                        "info": "{0!s}".format(attrkey)})
    return send_result(r)


@user_blueprint.route('/attribute', methods=['GET'])
@user_required
@event("get_user_attribute", request, g)
def get_user_attribute():
    """
    Return the *custom* attribute of the given user.
    This does *not* return the user attributes which are contained in the user store!
    The user is specified by the usual parameters user, resolver and realm.
    When a user is calling the endpoint the parameters will be implicitly set.

    :httpparam user: The username of the user, for whom the attribute should be set
    :httpparam resolver: The resolver of the user (optional)
    :httpparam realm: The realm of the user (optional)
    :httpparam key: The optional name of the attribute. If it is not specified
         all custom attributes of the user are returned.

    """
    _user = getParam(request.all_data, "user", optional=False)
    attrkey = getParam(request.all_data, "key", optional=True)
    r = request.User.attributes
    if attrkey:
        r = r.get(attrkey)
    g.audit_object.log({"success": True,
                        "info": "{0!s}".format(attrkey)})
    return send_result(r)


@user_blueprint.route('/editable_attributes/', methods=['GET'])
@user_required
@event("get_editable_attributes", request, g)
def get_editable_attributes():
    """
    The resulting editable custom attributes according to the policies
    are returned. This can be a user specific result.
    When a user is calling the endpoint the parameters will be implicitly set.

    :httpparam user: The username of the user, for whom the attribute should be set
    :httpparam resolver: The resolver of the user (optional)
    :httpparam realm: The realm of the user (optional)

    Works for admins and normal users.
    :return:
    """
    _user = getParam(request.all_data, "user", optional=False)
    r = get_allowed_custom_attributes(g, request.User)
    g.audit_object.log({"success": True})
    return send_result(r)


@user_blueprint.route('/attribute/<attrkey>/<username>/<realm>', methods=['DELETE'])
@prepolicy(check_custom_user_attributes, request, "delete")
@user_required
@event("delete_custom_user_attribute", request, g)
def delete_user_attribute(attrkey, username, realm=None):
    """
    Delete a specified custom attribute from the user.
    The user is specified by the positional parameters user and realm.

    :httpparam user: The username of the user, for whom the attribute should be set
    :httpparam realm: The realm of the user
    :httpparam key: The name of the attribute that should be deleted from the user.

    Returns the number of deleted attributes.
    """
    user = User(username, realm)
    r = user.delete_attribute(attrkey)
    g.audit_object.log({"success": True,
                        "info": "{0!s}".format(attrkey)})
    return send_result(r)


@user_blueprint.route('/<resolvername>/<username>', methods=['DELETE'])
@admin_required
@prepolicy(check_base_action, request, ACTION.DELETEUSER)
@event("user_delete", request, g)
def delete_user(resolvername=None, username=None):
    """
    Delete a User in the user store.
    The resolver must have the flag editable, so that the user can be deleted.
    Only administrators are allowed to delete users.

    Delete a user object in a user store by calling

    **Example request**:

    .. sourcecode:: http

       DELETE /user/<resolvername>/<username>
       Host: example.com
       Accept: application/json

    """
    user_obj = request.User
    res = user_obj.delete()
    g.audit_object.log({"success": res,
                        "info": "{0!s}".format(user_obj)})
    return send_result(res)


@user_blueprint.route('', methods=['POST'])
@user_blueprint.route('/', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, ACTION.ADDUSER)
@event("user_add", request, g)
def create_user_api():
    """
    Create a new user in the given resolver.

    **Example request**:

    .. sourcecode:: http

       POST /user
       user=new_user
       resolver=<resolvername>
       surname=...
       givenname=...
       email=...
       mobile=...
       phone=...
       password=...
       description=...

       Host: example.com
       Accept: application/json

    """
    # We can not use "get_user_from_param", since this checks the existence
    # of the user.
    attributes = _get_attributes_from_param(request.all_data)
    username = getParam(request.all_data, "user", optional=False)
    resolvername = getParam(request.all_data, "resolver", optional=False)
    # Remove the password from the attributes, so that we can hide it in the
    # logs
    password = attributes.get("password")
    if "password" in attributes:
        del attributes["password"]
    r = create_user(resolvername, attributes, password=password)
    g.audit_object.log({"success": True,
                        "info": "{0!s}: {1!s}/{2!s}".format(r, username,
                                                            resolvername)})
    return send_result(r)


@user_blueprint.route('', methods=['PUT'])
@user_blueprint.route('/', methods=['PUT'])
@prepolicy(check_base_action, request, ACTION.UPDATEUSER)
@event("user_update", request, g)
def update_user():
    """
    Edit a user in the user store.
    The resolver must have the flag editable, so that the user can be deleted.
    Only administrators are allowed to edit users.

    **Example request**:

    .. sourcecode:: http

       PUT /user
       user=existing_user
       resolver=<resolvername>
       surname=...
       givenname=...
       email=...
       mobile=...
       phone=...
       password=...
       description=...

       Host: example.com
       Accept: application/json

    .. note:: Also a user can call this function to e.g. change his password.
       But in this case the parameter "user" and "resolver" get overwritten
       by the values of the authenticated user, even if he specifies another
       username.
    """
    attributes = _get_attributes_from_param(request.all_data)
    username = getParam(request.all_data, "user", optional=False)
    resolvername = getParam(request.all_data, "resolver", optional=False)
    userid = getParam(request.all_data, "userid")
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
    r = user_obj.update_user_info(attributes, password=password)
    g.audit_object.log({"success": True,
                        "info": "{0!s}: {1!s}/{2!s}".format(r, username, resolvername)})
    return send_result(r)


def _get_attributes_from_param(param):
    from privacyidea.lib.resolver import get_resolver_object
    map = get_resolver_object(getParam(param, "resolver", optional=False)).map
    username = getParam(param, "user", optional=False)

    # Add attributes
    attributes = {"username": username}
    for attribute in map.keys():
        value = getParam(param, attribute)
        if value:
            attributes[attribute] = getParam(param, attribute)

    return attributes
