# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2016-01-01 Cornelius Kölbel <cornelius@privacyidea.org>
#            Password recovery
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

__doc__ = """This module provides the REST API for th password recovery for a
user managed in privacyIDEA.

The methods are also tested in the file tests/test_api_register.py
"""
from flask import (Blueprint, request, g, current_app)
from lib.utils import send_result, getParam
from lib.utils import required
from privacyidea.lib.user import get_user_from_param
import logging
from privacyidea.lib.policy import ACTION, SCOPE
from privacyidea.lib.user import create_user
from privacyidea.lib.user import User
from privacyidea.lib.token import init_token
from privacyidea.lib.realm import get_default_realm
from privacyidea.lib.error import RegistrationError
from privacyidea.api.lib.prepolicy import required_email, prepolicy
from privacyidea.lib.smtpserver import get_smtpserver, send_email_identifier


log = logging.getLogger(__name__)

recover_blueprint = Blueprint('recover_blueprint', __name__)


# The before and after methods are the same as in the validate endpoint

@recover_blueprint.route('', methods=['POST'])
def get_recover_code():
    """
    This method requests a recover code for a user. The recover code it sent
    via email to the user.

    :queryparam user: username of the user
    :queryparam realm: realm of the user
    :queryparam email: email of the user
    :return: JSON with value=True or value=False
    """
    param = request.all_data
    user = get_user_from_param(param, required)
    email = getParam(param, "email", required)
    # create recoverytoken for the user.
    from privacyidea.lib.token import init_token
    token = init_token({"type": "recovery"}, user=user)
    log.debug("Created recovery token %s for user %s" % (token, user))
    result = True
    return send_result(result)


@recover_blueprint.route('reset', methods=['POST'])
def reset_password():
    """
    reset the password with a given recovery code.
    The recovery code was sent by get_recover_code and is bound to a certain
    user.

    :jsonparam recovercode: The recoverycode sent the the user
    :jsonparam password: The new password of the user

    :return: a json result with a boolean "result": true
    """
    r = True
    user = get_user_from_param(request.all_data, required)
    recovercode = getParam(request.all_data, "recovercode", required)
    password = getParam(request.all_data, "password", required)

    return send_result(r)
