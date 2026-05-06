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

__doc__ = """
The password recovery REST API lets a user request and consume a one-time
recovery code in order to reset their password. It is only useful for users
in editable user stores; the user-scope policy :ref:`policy_password_reset`
must be active for the user.

Sending the recovery code requires a working email transport: the server
config key ``recovery.identifier`` must point to a configured SMTP server
(see :ref:`smtpserver`).

The endpoints are anonymous (no auth header).
"""
from flask import (Blueprint, request, g, current_app)
from .lib.utils import send_result, getParam
from .lib.utils import required
from privacyidea.lib.user import get_user_from_param
import logging
from privacyidea.lib.passwordreset import (create_recoverycode,
                                           check_recoverycode)
from ..lib.policies.actions import PolicyAction
from privacyidea.api.lib.prepolicy import prepolicy, check_anonymous_user


log = logging.getLogger(__name__)

recover_blueprint = Blueprint('recover_blueprint', __name__)


# The before and after methods are the same as in the validate endpoint

@recover_blueprint.route('', methods=['POST'])
@prepolicy(check_anonymous_user, request, action=PolicyAction.PASSWORDRESET)
def get_recover_code():
    """
    Request a one-time password recovery code for a user. The recovery code
    is sent by email to the address stored for that user; it expires after
    one hour.

    The server must have ``recovery.identifier`` configured to a working
    SMTP server, the user must live in an editable user store, and the
    user-scope policy :ref:`policy_password_reset` must be active. The
    ``email`` form field has to match the user's stored email address
    (case-insensitive); otherwise the request is rejected.

    This endpoint is anonymous — no authentication header is required.

    :jsonparam user: login name of the user (required).
    :jsonparam realm: realm of the user (required if the user is not in
        the default realm).
    :jsonparam email: the user's email address (required).
    :status 200: ``True`` on success; failures raise a JSON error response.
    """
    param = request.all_data
    user_obj = get_user_from_param(param, required)
    email = getParam(param, "email", required)
    r = create_recoverycode(user_obj, email, base_url=request.base_url)
    g.audit_object.log({"success": r,
                        "info": "{0!s}".format(user_obj)})
    return send_result(r)


@recover_blueprint.route('/reset', methods=['POST'])
@prepolicy(check_anonymous_user, request, action=PolicyAction.PASSWORDRESET)
def reset_password():
    """
    Consume a recovery code (previously obtained via :http:post:`/recover`)
    and set a new password for the user. The recovery code is bound to a
    specific user, so the request must identify the same user that requested
    the code.

    The user-scope policy :ref:`policy_password_reset` must be active. This
    endpoint is anonymous — no authentication header is required.

    :jsonparam user: login name of the user (required).
    :jsonparam realm: realm of the user (required if the user is not in
        the default realm).
    :jsonparam recoverycode: the one-time code that was emailed to the
        user (required).
    :jsonparam password: the new password to set for the user (required).
    :status 200: ``result.value`` is ``True`` if the password was changed,
        ``False`` if the recovery code was invalid or expired.
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
