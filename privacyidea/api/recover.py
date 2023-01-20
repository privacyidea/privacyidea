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

__doc__ = """This module provides the REST API for the password recovery for a
user managed in privacyIDEA.

The methods are also tested in the file tests/test_api_register.py
"""
from flask import (Blueprint, request, g, current_app)
from .lib.utils import send_result, getParam
from .lib.utils import required
from privacyidea.lib.user import get_user_from_param
import logging
from privacyidea.lib.passwordreset import (create_recoverycode,
                                           check_recoverycode)
from privacyidea.lib.policy import ACTION
from privacyidea.api.lib.prepolicy import prepolicy, check_anonymous_user


log = logging.getLogger(__name__)

recover_blueprint = Blueprint('recover_blueprint', __name__)


# The before and after methods are the same as in the validate endpoint

@recover_blueprint.route('', methods=['POST'])
@prepolicy(check_anonymous_user, request, action=ACTION.PASSWORDRESET)
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
    user_obj = get_user_from_param(param, required)
    email = getParam(param, "email", required)
    r = create_recoverycode(user_obj, email, base_url=request.base_url)
    g.audit_object.log({"success": r,
                        "info": "{0!s}".format(user_obj)})
    return send_result(r)


@recover_blueprint.route('/reset', methods=['POST'])
@prepolicy(check_anonymous_user, request, action=ACTION.PASSWORDRESET)
def reset_password():
    """
    reset the password with a given recovery code.
    The recovery code was sent by get_recover_code and is bound to a certain
    user.

    :jsonparam recoverycode: The recoverycode sent the the user
    :jsonparam password: The new password of the user

    :return: a json result with a boolean "result": true
    """
    r = False
    user_obj = get_user_from_param(request.all_data, required)
    recoverycode = getParam(request.all_data, "recoverycode", required)
    password = getParam(request.all_data, "password", required)
    if check_recoverycode(user_obj, recoverycode):
        # set password
        r = user_obj.update_user_info({"password": password})
        g.audit_object.log({"success": r,
                            "info": "{0!s}".format(user_obj)})
    return send_result(r)
