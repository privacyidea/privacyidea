# http://www.privacyidea.org
# (c) Cornelius Kölbel
#
# 2017-08-24 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
#            REST API to add and delete remote privacyIDEA servers.
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
The privacyIDEA-server REST API manages definitions of remote privacyIDEA
servers. These definitions are referenced by the :ref:`remote_token` token
type to forward authentication requests, and by the :ref:`federationhandler`
event handler to chain privacyIDEA instances. See
:ref:`privacyideaserver_config` for the conceptual chapter.

All endpoints require admin authentication. Read access is gated by the
admin policy action :ref:`policy_privacyideaserver_read`; create, update,
delete and the test request are gated by :ref:`policy_privacyideaserver_write`.
"""
from flask import (Blueprint, request)
from .lib.utils import (send_result)
from ..lib.params import get_optional, get_required
from ..lib.log import log_with
from ..lib.policies.actions import PolicyAction
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.utils import is_true
from flask import g
import logging
from privacyidea.lib.privacyideaserver import (add_privacyideaserver,
                                               PrivacyIDEAServer,
                                               delete_privacyideaserver,
                                               list_privacyideaservers)
from privacyidea.models import PrivacyIDEAServer as PrivacyIDEAServerDB


log = logging.getLogger(__name__)

privacyideaserver_blueprint = Blueprint('privacyideaserver_blueprint', __name__)


@privacyideaserver_blueprint.route('/<identifier>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.PRIVACYIDEASERVERWRITE)
@log_with(log)
def create(identifier=None):
    """
    Create or update a privacyIDEA server definition. If a definition with
    the given ``identifier`` already exists it is updated; otherwise it is
    created. Spaces in ``identifier`` are replaced with underscores.

    Requires admin authentication and the policy action
    :ref:`policy_privacyideaserver_write`.

    :param identifier: path component, the unique name of the definition.
    :jsonparam url: URL of the remote privacyIDEA server (required).
    :jsonparam tls: ``1`` (default) to verify the TLS certificate of the
        remote server, ``0`` to skip verification.
    :jsonparam description: free-form description.
    :status 200: ``True`` on success.
    """
    param = request.all_data
    identifier = identifier.replace(" ", "_")
    url = get_required(param, "url")
    tls = is_true(get_optional(param, "tls", default="1"))
    description = get_optional(param, "description", default="")

    r = add_privacyideaserver(identifier, url=url, tls=tls,
                              description=description)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@privacyideaserver_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.PRIVACYIDEASERVERREAD)
def list_privacyidea():
    """
    Return all privacyIDEA server definitions known to this server.

    The result is a dictionary keyed by ``identifier``; each value contains
    ``id``, ``url``, ``tls`` and ``description``.

    Requires admin authentication and the policy action
    :ref:`policy_privacyideaserver_read`.

    :status 200: dict of definitions in ``result.value``.
    """
    res = list_privacyideaservers()

    g.audit_object.log({'success': True})
    return send_result(res)


@privacyideaserver_blueprint.route('/<identifier>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.PRIVACYIDEASERVERWRITE)
@log_with(log)
def delete_server(identifier=None):
    """
    Delete the privacyIDEA server definition with the given identifier.

    Requires admin authentication and the policy action
    :ref:`policy_privacyideaserver_write`.

    :param identifier: path component, the name of the definition.
    :status 200: ``True`` if a definition was deleted, ``False`` otherwise.
    """
    r = delete_privacyideaserver(identifier)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@privacyideaserver_blueprint.route('/test_request', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.PRIVACYIDEASERVERWRITE)
@log_with(log)
def test():
    """
    Test a privacyIDEA server definition by sending an authentication
    request to it. The handler issues ``POST /validate/check`` against the
    supplied ``url`` using the given ``username`` and ``password``, with TLS
    verification controlled by ``tls``. The definition does not need to be
    saved first — all parameters are taken from the request body.

    Requires admin authentication and the policy action
    :ref:`policy_privacyideaserver_write`.

    :jsonparam identifier: identifier under which the definition would be
        saved (used for logging/audit only).
    :jsonparam url: URL of the remote privacyIDEA server (required).
    :jsonparam tls: ``1`` (default) to verify the TLS certificate of the
        remote server, ``0`` to skip verification.
    :jsonparam username: user name to test (required).
    :jsonparam password: password / OTP to test (required).
    :status 200: ``True`` if the remote server accepted the credentials,
        ``False`` otherwise.
    """
    param = request.all_data
    identifier = get_required(param, "identifier")
    url = get_required(param, "url")
    tls = is_true(get_optional(param, "tls", default="1"))
    user = get_required(param, "username")
    password = get_required(param, "password")


    s = PrivacyIDEAServerDB(identifier=identifier, url=url, tls=tls)
    r = PrivacyIDEAServer.request(s, user, password)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)
