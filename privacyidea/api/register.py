# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2015-12-28 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add sending of email via smtp config
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
from .lib.utils import send_result, getParam
from .lib.utils import required
import logging
from privacyidea.lib.policy import ACTION, SCOPE
from privacyidea.lib.user import create_user
from privacyidea.lib.user import User
from privacyidea.lib.token import init_token
from privacyidea.lib.realm import get_default_realm
from privacyidea.lib.error import RegistrationError
from privacyidea.api.lib.prepolicy import required_email, prepolicy
from privacyidea.lib.smtpserver import get_smtpserver, send_email_identifier

DEFAULT_BODY="""
Your registration token is {regkey}.
"""

log = logging.getLogger(__name__)

register_blueprint = Blueprint('register_blueprint', __name__)


# The before and after methods are the same as in the validate endpoint

@register_blueprint.route('', methods=['GET'])
def register_status():
    """
    This endpoint returns the information if registration is allowed or not.
    This is used by the UI to either display the registration button or not.

    :return: JSON with value=True or value=False
    """
    resolvername = g.policy_object.get_action_values(ACTION.RESOLVER,
                                                     scope=SCOPE.REGISTER,
                                                     unique=True,
                                                     audit_data=g.audit_object.audit_data)

    result = bool(resolvername)
    g.audit_object.log({"info": result,
                        "success": True})
    return send_result(result)


@register_blueprint.route('', methods=['POST'])
@prepolicy(required_email, request=request)
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
               "clientip": g.client_ip}
    g.audit_object.log({"info": username})
    # Add all params to the options
    for key, value in request.all_data.items():
            if value and key not in ["g", "clientip"]:
                options[key] = value

    # 0. check, if we can do the registration at all!
    smtpconfig = g.policy_object.get_action_values(ACTION.EMAILCONFIG,
                                                   scope=SCOPE.REGISTER,
                                                   unique=True,
                                                   audit_data=g.audit_object.audit_data)
    if not smtpconfig:
        raise RegistrationError("No SMTP server configuration specified!")

    # 1. determine, in which resolver/realm the user should be created
    realm = g.policy_object.get_action_values(ACTION.REALM,
                                              scope=SCOPE.REGISTER,
                                              unique=True,
                                              audit_data=g.audit_object.audit_data)
    if not realm:
        # No policy for realm, so we use the default realm
        realm = get_default_realm
    else:
        # we use the first realm in the list
        realm = list(realm)[0]
    resolvername = g.policy_object.get_action_values(ACTION.RESOLVER,
                                                     scope=SCOPE.REGISTER,
                                                     unique=True,
                                                     audit_data=g.audit_object.audit_data)
    if not resolvername:
        raise RegistrationError("No resolver specified to register in!")
    resolvername = list(resolvername)[0]
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
    registration_key = token.init_details.get("otpkey")

    smtpconfig = list(smtpconfig)[0]
    # Send the registration key via email
    body = g.policy_object.get_action_values(ACTION.REGISTERBODY,
                                             scope=SCOPE.REGISTER,
                                             unique=True,
                                             audit_data=g.audit_object.audit_data)
    body = body or DEFAULT_BODY
    email_sent = send_email_identifier(
        smtpconfig, email,
        "Your privacyIDEA registration",
        body.format(regkey=registration_key))
    if not email_sent:
        log.warning("Failed to send registration email to {0!r}".format(email))
        # delete registration token
        token.delete()
        # delete user
        user.delete()
        raise RegistrationError("Failed to send email!")

    log.debug("Registration email sent to {0!r}".format(email))

    g.audit_object.log({"success": email_sent})
    return send_result(email_sent)
