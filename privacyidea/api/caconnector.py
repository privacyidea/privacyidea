#  2015-05-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#
# License:  AGPLv3
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
#
__doc__ = """
The CA connector REST API manages connections to Certificate Authorities
that privacyIDEA uses when enrolling certificate tokens. See
:ref:`caconnectors` for the conceptual chapter that explains connector
types and their configuration.

All endpoints require admin authentication. Read access is gated by the
admin policy action :ref:`caconnectorread`, write access by
:ref:`caconnectorwrite`, and deletion by :ref:`caconnectordelete`.
"""

from flask import (Blueprint, request)
from .lib.utils import (send_result)
from ..lib.log import log_with
from flask import g
import logging
from privacyidea.lib.caconnector import (save_caconnector,
                                         delete_caconnector,
                                         get_caconnector_specific_options,
                                         get_caconnector_list)
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policies.actions import PolicyAction

log = logging.getLogger(__name__)

caconnector_blueprint = Blueprint('caconnector_blueprint', __name__)


@caconnector_blueprint.route('/<name>', methods=['GET'])
@caconnector_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.CACONNECTORREAD)
def get_caconnector_api(name=None):
    """
    Return CA connectors known to this server. If ``name`` is given as a
    path component, only the matching connector is returned; otherwise all
    connectors are listed. Each entry includes the connector configuration,
    but password-type values are not returned in clear text: they are replaced
    by the placeholder ``__CENSORED__``. When updating a connector, submit
    ``__CENSORED__`` for such a value to keep its stored secret unchanged, or an
    empty string to clear it.

    Requires admin authentication and the policy action :ref:`caconnectorread`.

    :param name: optional path component selecting a single connector by name.
    :status 200: list of connector dictionaries in ``result.value``.
    """
    g.audit_object.log({"detail": f"{name!s}"})
    res = get_caconnector_list(filter_caconnector_name=name,
                               return_config=True,
                               censor=True)
    g.audit_object.log({"success": True})
    return send_result(res)


@caconnector_blueprint.route('/specific/<catype>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.CACONNECTORREAD)
def get_caconnector_specific(catype):
    """
    Return the type-specific configuration options that are available for
    a given CA connector type and an in-progress configuration. The WebUI
    calls this after the admin has chosen a connector type and entered the
    mandatory fields, in order to discover further options whose values
    depend on the current configuration (for example: which CA templates
    are available for a local openSSL connector).

    Requires admin authentication and the policy action :ref:`caconnectorread`.

    :param catype: path component naming the connector type
        (e.g. ``local``, ``microsoft``).
    :query: any connector-specific configuration fields entered so far —
        they are passed verbatim to the connector class to compute the
        available options.
    :status 200: dict of available options in ``result.value``.
    """
    param = request.all_data
    # Create an object out of the type and the given request parameters.
    res = get_caconnector_specific_options(catype, param)
    g.audit_object.log({"success": True})
    return send_result(res)


@caconnector_blueprint.route('/<name>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.CACONNECTORWRITE)
def save_caconnector_api(name=None):
    """
    Create or update a CA connector. If a connector with the given ``name``
    already exists, it is updated; otherwise it is created. On update only
    fields that should be changed need to be supplied, but the connector
    ``type`` must not be changed (it is bound to the connector class).

    See :ref:`caconnectors` for the supported types and their attributes.

    Requires admin authentication and the policy action :ref:`caconnectorwrite`.

    :param name: path component, the connector name.
    :jsonparam type: connector type (e.g. ``local``); required on creation.
    :jsonparam: any connector-specific configuration fields.
    :status 200: database id of the connector in ``result.value``.
    """
    param = request.all_data
    param["caconnector"] = name
    g.audit_object.log({"detail": f"{name!s}"})
    res = save_caconnector(param)
    g.audit_object.log({"success": True})
    return send_result(res)


@caconnector_blueprint.route('/<name>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.CACONNECTORDELETE)
def delete_caconnector_api(name=None):
    """
    Delete the CA connector with the given name and all its configuration
    entries.

    Requires admin authentication and the policy action :ref:`caconnectordelete`.

    :param name: path component, the connector name.
    :status 200: id of the deleted connector in ``result.value``.
    :status 404: no connector with that name exists.
    """
    g.audit_object.log({"detail": f"{name!s}"})
    res = delete_caconnector(name)
    g.audit_object.log({"success": True})
    return send_result(res)
