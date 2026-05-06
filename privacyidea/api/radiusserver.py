# http://www.privacyidea.org
# (c) Cornelius Kölbel
#
# 2016-02-20 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Implement REST API, create, update, delete, list
#            for RADIUS server definitions
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
The RADIUS-server REST API manages definitions of remote RADIUS servers.
These definitions are referenced by the :ref:`radius_token` token type
and by the :ref:`passthru_policy` to forward authentication to a RADIUS
backend. See :ref:`radiusserver_config` for the conceptual chapter.

All endpoints require admin authentication. Read access is gated by the
admin policy action :ref:`policy_radiusserver_read`; create, update,
delete and the test request are gated by :ref:`policy_radiusserver_write`.
"""
from flask import (Blueprint, request)

from privacyidea.lib.resolver import CENSORED
from .lib.utils import (getParam,
                        required,
                        send_result)
from ..lib.log import log_with
from ..lib.policies.actions import PolicyAction
from ..api.lib.prepolicy import prepolicy, check_base_action
from flask import g
import logging
from privacyidea.lib.radiusserver import (add_radius, list_radiusservers,
                                          delete_radius, test_radius)


log = logging.getLogger(__name__)

radiusserver_blueprint = Blueprint('radiusserver_blueprint', __name__)


@radiusserver_blueprint.route('/<identifier>', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.RADIUSSERVERWRITE)
@log_with(log)
def create(identifier=None):
    """
    Create or update a RADIUS server definition. If a definition with the
    given ``identifier`` already exists it is updated; otherwise it is
    created. Spaces in ``identifier`` are replaced with underscores.

    Requires admin authentication and the policy action
    :ref:`policy_radiusserver_write`.

    :param identifier: path component, the unique name of the definition.
    :jsonparam server: hostname or IP of the RADIUS server (required).
    :jsonparam port: UDP port of the RADIUS server, default ``1812``.
    :jsonparam secret: shared RADIUS secret (required).
    :jsonparam retries: number of retries on timeout, default ``3``.
    :jsonparam timeout: per-attempt timeout in seconds, default ``5``.
    :jsonparam dictionary: server-side filesystem path to the FreeRADIUS
        dictionary file, default ``/etc/privacyidea/dictionary``.
    :jsonparam description: free-form description.
    :jsonparam options: optional dictionary of additional connection options.
    :status 200: ``True`` on success.
    """
    param = request.all_data
    identifier = identifier.replace(" ", "_")
    server = getParam(param, "server", required)
    port = int(getParam(param, "port", default=1812))
    secret = getParam(param, "secret", required)
    retries = int(getParam(param, "retries", default=3))
    timeout = int(getParam(param, "timeout", default=5))
    description = getParam(param, "description", default="")
    dictionary = getParam(param, "dictionary",
                          default="/etc/privacyidea/dictionary")
    options = getParam(param, "options", default=None)

    r = add_radius(identifier, server, secret, port=port,
                   description=description, dictionary=dictionary,
                   retries=retries, timeout=timeout, options=options)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@radiusserver_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RADIUSSERVERREAD)
def list_radius():
    """
    Return all RADIUS server definitions known to this server. The shared
    secret of each definition is redacted in the response.

    The result is a dictionary keyed by ``identifier``; each value contains
    ``id``, ``server``, ``port``, ``secret`` (always ``"__CENSORED__"``),
    ``retries``, ``timeout``, ``dictionary``, ``description``.

    Requires admin authentication and the policy action
    :ref:`policy_radiusserver_read`.

    :status 200: dict of definitions in ``result.value``.
    """
    res = list_radiusservers()
    # We do not add the secret!
    for identifier, data in res.items():
        data["secret"] = CENSORED
    g.audit_object.log({'success': True})
    return send_result(res)


@radiusserver_blueprint.route('/<identifier>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.RADIUSSERVERWRITE)
@log_with(log)
def delete_server(identifier=None):
    """
    Delete the RADIUS server definition with the given identifier.

    Requires admin authentication and the policy action
    :ref:`policy_radiusserver_write`.

    :param identifier: path component, the name of the definition.
    :status 200: ``True`` if a definition was deleted, ``False`` otherwise.
    """
    r = delete_radius(identifier)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@radiusserver_blueprint.route('/test_request', methods=['POST'])
@prepolicy(check_base_action, request, PolicyAction.RADIUSSERVERWRITE)
@log_with(log)
def test():
    """
    Test a RADIUS server definition by performing an Access-Request against
    it with the supplied credentials. The definition does not need to be
    saved first — all parameters are taken from the request body.

    Requires admin authentication and the policy action
    :ref:`policy_radiusserver_write`.

    :jsonparam identifier: identifier under which the definition would be
        saved (used for logging/audit only).
    :jsonparam server: hostname or IP of the RADIUS server (required).
    :jsonparam port: UDP port, default ``1812``.
    :jsonparam secret: shared RADIUS secret (required).
    :jsonparam retries: number of retries on timeout, default ``3``.
    :jsonparam timeout: per-attempt timeout in seconds, default ``5``.
    :jsonparam dictionary: server-side filesystem path to the FreeRADIUS
        dictionary file, default ``/etc/privacyidea/dictionary``.
    :jsonparam options: optional dictionary of additional connection options.
    :jsonparam username: user name to test (required).
    :jsonparam password: password / OTP to test (required).
    :status 200: ``True`` if the RADIUS server accepted the credentials,
        ``False`` otherwise.
    """
    param = request.all_data
    identifier = getParam(param, "identifier", required)
    server = getParam(param, "server", required)
    port = int(getParam(param, "port", default=1812))
    secret = getParam(param, "secret", required)
    retries = int(getParam(param, "retries", default=3))
    timeout = int(getParam(param, "timeout", default=5))
    user = getParam(param, "username", required)
    password = getParam(param, "password", required)
    dictionary = getParam(param, "dictionary",
                          default="/etc/privacyidea/dictionary")
    options = getParam(param, "options", default=None)

    r = test_radius(identifier, server, secret, user, password, port=port,
                    dictionary=dictionary, retries=retries, timeout=timeout, options=options)
    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)
