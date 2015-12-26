# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2015-12-23 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add this register endpoint for new users to create a new user
#            account.
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

__doc__ = """This module contains the REST API for registering as a new user.
This endpoint can be used without any authentication, since a new user can
register.

The methods are tested in the file tests/test_api_register.py
"""
from flask import (Blueprint, request, g, current_app)
from lib.utils import send_result, getParam
from lib.utils import required
import logging
from privacyidea.lib.policy import ACTION, SCOPE
from privacyidea.lib.user import create_user
from privacyidea.lib.user import User
from privacyidea.lib.token import init_token
from privacyidea.lib.realm import get_default_realm
from privacyidea.lib.error import RegistrationError


log = logging.getLogger(__name__)

register_blueprint = Blueprint('register_blueprint', __name__)


# The before and after methods are the same as in the validate endpoint

@register_blueprint.route('', methods=['POST'])
def register_post():
    """
    Register a new user in the realm/userresolver. To do so, the user
    resolver must be writeable like an SQLResolver.

    Registering a user in fact creates a new user and also creates the first
    token for the user. The following values are needed to register the user:

    * username (mandatory)
    * givenname (mandatory)
    * surname (mandatory)
    * email address (mandatory)
    * password (mandatory)
    * mobile phone (optional)
    * telephone (optional)

    The user receives a registration token via email to be able to login with
    his self chosen password and the registration token.

    :jsonparam username: The login name of the new user. Check if it already
        exists
    :jsonparam givenname: The givenname of the new user
    :jsonparam surname: The surname of the new user
    :jsonparam email: The email address of the new user
    :jsonparam password: The password of the new user. This is the resolver
        password of the new user.
    :jsonparam mobile: The mobile phone number
    :jsonparam phone: The phone number (land line) of the new user

    :return: a json result with a boolean "result": true
    """
    username = getParam(request.all_data, "username", required)
    surname = getParam(request.all_data, "surname", required)
    givenname = getParam(request.all_data, "givenname", required)
    email = getParam(request.all_data, "email", required)
    password = getParam(request.all_data, "password", required)
    mobile = getParam(request.all_data, "mobile")
    phone = getParam(request.all_data, "phone")
    options = {"g": g,
               "clientip": request.remote_addr}
    # Add all params to the options
    for key, value in request.all_data.items():
            if value and key not in ["g", "clientip"]:
                options[key] = value

    result = False
    details = {}

    # 1. determine, in which resolver/realm the user should be created
    realm = g.policy_object.get_action_values(ACTION.REALM,
                                              scope=SCOPE.REGISTER,
                                              unique=True)
    if not realm:
        # No policy for realm, so we use the default realm
        realm = get_default_realm
    else:
        # we use the first realm in the list
        realm = realm[0]
    resolvername = g.policy_object.get_action_values(ACTION.RESOLVER,
                                                     scope=SCOPE.REGISTER,
                                                     unique=True)
    if not resolvername:
        raise RegistrationError("No resolver specified to register in!")
    resolvername = resolvername[0]
    # Check if the user exists
    user = User(username, realm=realm, resolver=resolvername)
    if user.exist():
        raise RegistrationError("The username is already registered!")
    # Create user
    uid = create_user(resolvername, {"username": username,
                                     "email": email,
                                     "phone": phone,
                                     "mobile": mobile,
                                     "surname": surname,
                                     "givenname": givenname,
                                     "password": password})

    # 3. create a registration token for this user
    user = User(username, realm=realm, resolver=resolvername)
    token = init_token({"type": "registration"}, user=user)
    # 4. send the registration token to the users email
    # TODO: send the registration key
    registration_key = token.init_details.get("otpkey")
    g.audit_object.log({"info": details.get("message"),
                        "success": result})
    return send_result(result, details=details)
