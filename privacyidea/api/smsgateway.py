# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2016-06-15 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Initial writeup
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
"""
The SMS-gateway REST API manages SMS gateway definitions used to send
SMS messages (for SMS-token OTP delivery, notifications, and event
handlers). See :ref:`sms_gateway_config` for the conceptual chapter
covering the supported provider modules and their options.

All endpoints require admin authentication. Read access is gated by
the admin policy action :ref:`policy_smsgateway_read`; create, update
and delete are gated by :ref:`policy_smsgateway_write`.
"""
from flask import (Blueprint,
                   request)
from .lib.utils import send_result
from ..lib.params import get_optional, get_required
from ..lib.log import log_with
from flask import g
import logging
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policies.actions import PolicyAction
from ..lib.crypto import censor_dict
from privacyidea.lib.smsprovider.SMSProvider import (SMS_PROVIDERS,
                                                     get_smsgateway,
                                                     set_smsgateway,
                                                     delete_smsgateway_key_generic,
                                                     delete_smsgateway,
                                                     get_sms_provider_class)

log = logging.getLogger(__name__)

smsgateway_blueprint = Blueprint('smsgateway_blueprint', __name__)


@smsgateway_blueprint.route('/', methods=['GET'])
@smsgateway_blueprint.route('/<gwid>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.SMSGATEWAYREAD)
def get_gateway(gwid=None):
    """
    Return SMS gateway information. The behavior depends on the path:

    * ``/smsgateway/`` — return all configured gateway definitions as a
      list of dictionaries.
    * ``/smsgateway/<gwid>`` — return the gateway with the given numeric
      id (still wrapped in a single-element list).
    * ``/smsgateway/providers`` — return a dictionary keyed by provider
      class name, where each value describes the configuration parameters
      the class accepts. This special path is used by the WebUI to render
      the gateway-creation form; it does not look up a gateway with the
      literal id ``providers``.

    Secret options and headers (those whose name contains ``PASSWORD`` or
    ``SECRET``) are not returned in clear text; they are replaced by the
    placeholder ``__CENSORED__``. When updating a gateway, submit
    ``__CENSORED__`` for such a value to keep it unchanged, an empty string to
    clear it, or a new value to replace it.

    Requires admin authentication and the policy action
    :ref:`policy_smsgateway_read`.

    :param gwid: optional path component, the numeric id of a gateway,
        or the literal string ``providers`` for the schema lookup.
    :status 200: list of gateway dictionaries, or a dictionary of provider
        schemas, in ``result.value``.
    """
    res = {}
    if gwid == "providers":
        for classname in SMS_PROVIDERS:
            smsclass = get_sms_provider_class(classname.rsplit(".", 1)[0],
                                              classname.rsplit(".", 1)[1])
            res[classname] = smsclass.parameters()
    else:
        res = []
        for gw in get_smsgateway(id=gwid):
            gw_dict = gw.as_dict()
            # Censor secret-looking options AND headers (e.g. auth headers) so they
            # are not returned in clear text. NOTE: this is still a key-name
            # heuristic; secrets in differently-named keys (e.g. an Authorization
            # header or a Firebase credentials option) are not detected. A robust
            # fix needs the provider classes to declare which fields are secret.
            for section in ("options", "headers"):
                secret_keys = [key for key in gw_dict.get(section, {})
                               if "PASSWORD" in key.upper() or "SECRET" in key.upper()]
                gw_dict[section] = censor_dict(gw_dict.get(section, {}), secret_keys)
            res.append(gw_dict)

    g.audit_object.log({"success": True})
    return send_result(res)


@smsgateway_blueprint.route('', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.SMSGATEWAYWRITE)
def set_gateway():
    """
    Create or update an SMS gateway definition. If a definition with the
    given ``name`` already exists it is updated; otherwise it is created.

    Requires admin authentication and the policy action
    :ref:`policy_smsgateway_write`.

    :jsonparam name: unique identifier for the gateway (required).
    :jsonparam module: dotted Python path of the SMS provider class to
        use (required, e.g.
        ``privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider``).
    :jsonparam description: free-form description.
    :jsonparam option.*: provider-specific options. Field names are taken
        after the ``option.`` prefix (e.g. ``option.URL`` becomes the
        ``URL`` option).
    :jsonparam header.*: HTTP headers to send with provider requests, same
        naming scheme as ``option.*``.
    :status 200: database id of the gateway in ``result.value``.
    """
    param = request.all_data
    identifier = get_required(param, "name")
    providermodule = get_required(param, "module")
    description = get_optional(param, "description")
    options = {}
    headers = {}
    for k, v in param.items():
        if k.startswith("option."):
            options[k[7:]] = v
        elif k.startswith("header."):
            headers[k[7:]] = v

    res = set_smsgateway(identifier, providermodule, description,
                         options=options, headers=headers)
    g.audit_object.log({"success": True,
                        "info": res})
    return send_result(res)


@smsgateway_blueprint.route('/<identifier>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.SMSGATEWAYWRITE)
def delete_gateway(identifier=None):
    """
    Delete the SMS gateway definition with the given identifier and all
    its options and headers.

    Requires admin authentication and the policy action
    :ref:`policy_smsgateway_write`.

    :param identifier: path component, the gateway name.
    :status 200: number of deleted rows in ``result.value``
        (``0`` if no gateway with that name existed).
    """
    res = delete_smsgateway(identifier=identifier)
    g.audit_object.log({"success": res,
                        "info": identifier})

    return send_result(res)


@smsgateway_blueprint.route('/option/<gwid>/<key>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.SMSGATEWAYWRITE)
def delete_gateway_option(gwid=None, key=None):
    """
    Delete a single option (or header) from an SMS gateway definition.

    Requires admin authentication and the policy action
    :ref:`policy_smsgateway_write`.

    :param gwid: path component, the numeric id of the gateway.
    :param key: path component, the option name to delete. Prefix with
        ``header.`` to remove a header instead of an option (e.g. pass
        ``header.X-Foo`` to delete the ``X-Foo`` header).
    :status 200: number of deleted rows in ``result.value``.
    """
    type = "option"
    if "." in key:
        type, key = key.split(".", 1)

    res = delete_smsgateway_key_generic(gwid, key, Type=type)
    g.audit_object.log({"success": res,
                        "info": f"{gwid!s}/{key!s}"})

    return send_result(res)
