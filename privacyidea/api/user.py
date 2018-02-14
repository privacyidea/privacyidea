# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
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
from ..api.lib.prepolicy import prepolicy, check_base_action, realmadmin
from ..lib.policy import ACTION
from privacyidea.api.auth import admin_required, user_required
from privacyidea.lib.user import create_user, get_user_from_param, User

from flask import (g)
from ..lib.user import get_user_list
import logging


log = logging.getLogger(__name__)


user_blueprint = Blueprint('user_blueprint', __name__)


@user_blueprint.route('/', methods=['GET'])
@prepolicy(realmadmin, request, ACTION.USERLIST)
@prepolicy(check_base_action, request, ACTION.USERLIST)
@user_required
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
    users = get_user_list(request.all_data)

    g.audit_object.log({'success': True,
                        'info': "realm: {0!s}".format(realm)})
    
    return send_result(users)


@user_blueprint.route('/<resolvername>/<username>', methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.DELETEUSER)
@admin_required
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
    user_obj = User(login=username, resolver=resolvername)
    res = user_obj.delete()
    g.audit_object.log({"success": res,
                        "info": u"{0!s}".format(user_obj)})
    return send_result(res)


@user_blueprint.route('', methods=['POST'])
@user_blueprint.route('/', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.ADDUSER)
@admin_required
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
    del attributes["password"]
    r = create_user(resolvername, attributes, password=password)
    g.audit_object.log({"success": True,
                        "info": u"{0!s}: {1!s}/{2!s}".format(r, username,
                                                            resolvername)})
    return send_result(r)


@user_blueprint.route('', methods=['PUT'])
@user_blueprint.route('/', methods=['PUT'])
@prepolicy(check_base_action, request, ACTION.UPDATEUSER)
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
    user_obj = User(login=username, resolver=resolvername)
    # Remove the password from the attributes, so that we can hide it in the
    # logs
    password = attributes.get("password")
    if password:
        del attributes["password"]
    r = user_obj.update_user_info(attributes, password=password)
    g.audit_object.log({"success": True,
                        "info": u"{0!s}: {1!s}/{2!s}".format(r, username, resolvername)})
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
