# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel
#
# 2016-03-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Implement REST API, create, update, delete, list
#            for SAML IdP definitions
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
__doc__ = """This endpoint is used to create, update, list and delete
SAML IdP definitions. privacyIDEA can act as an SP. So if you authenticated
to a SAML IdP you can do Single Sign-On to the WebUI.

The code of this module is tested in tests/test_api_samlidp.py
"""
from flask import (Blueprint, request)
from lib.utils import (getParam,
                       required,
                       send_result)
from ..lib.log import log_with
from ..lib.policy import ACTION
from ..api.lib.prepolicy import prepolicy, check_base_action
from flask import g
import logging
from privacyidea.lib.samlidp import (add_samlidp, delete_samlidp,
                                     fetch_metadata, get_samlidp_list)

log = logging.getLogger(__name__)

samlidp_blueprint = Blueprint('samlidp_blueprint', __name__)


@samlidp_blueprint.route('/<identifier>', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.SAMLIDPWRITE)
@log_with(log)
def create(identifier=None):
    """
    This call creates or updates a SAML IdP definition.

    :param identifier: The unique name of the SAML IdP
    :param metadata_url: The URL where to fetch the metadata
    :param acs_url: The URL where the IdP returns to
    :param https_acs_url: The URL where the IdP returns to
    :param active: whether the SAML config should be active
    :param allow_unsolicited:
    :param authn_requests_signed:
    :param logout_requests_signed:
    :param want_response_signed:
    :param want_assertions_signed:
    :param entityid:
    """
    param = request.all_data
    identifier = identifier.replace(" ", "_")
    metadata_url = getParam(param, "metadata_url", optional=required)
    active = getParam(param, "active", default=True)
    allow_unsolicited = getParam(param, "allow_unsolicited", default=True)
    authn_requests_signed = getParam(param, "authn_requests_signed",
                                     default=False)
    logout_requests_signed = getParam(param, "logout_requests_signed",
                                      default=True)
    want_assertions_signed = getParam(param, "want_assertions_signed",
                                      default=True)
    want_response_signed = getParam(param, "want_response_signed",
                                    default=False)
    acs_url = getParam(param, "acs_url", optional=required)
    https_acs_url = getParam(param, "https_acs_url", optional=required)
    entityid = getParam(param, "entityid", default="privacyIDEA_SP")
    r = add_samlidp(identifier, metadata_url, acs_url, https_acs_url,
                    active=active, allow_unsolicited=allow_unsolicited,
                    authn_requests_signed=authn_requests_signed,
                    logout_requests_signed=logout_requests_signed,
                    want_assertions_signed=want_assertions_signed,
                    want_response_signed=want_response_signed,
                    entityid=entityid)
    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@samlidp_blueprint.route('/', methods=['GET'])
@log_with(log)
def list_saml():
    """
    This call gets the list of SAML IdP definitions
    """
    res = {}
    server_list = get_samlidp_list()
    for server in server_list:
        res[server.identifier] = {
            "metadata_url": server.metadata_url,
            "metadata": server.metadata_cache,
            "entityid": server.entityid,
            "acs_url": server.acs_url,
            "https_acs_url": server.https_acs_url,
            "active": server.active,
            "allow_unsolicited": server.allow_unsolicited,
            "authn_requests_signed": server.authn_requests_signed,
            "logout_requests_signed": server.logout_requests_signed,
            "want_response_signed": server.want_response_signed,
            "want_assertions_signed": server.want_assertions_signed
        }
    g.audit_object.log({'success': True})
    return send_result(res)


@samlidp_blueprint.route('/<identifier>', methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.SAMLIDPWRITE)
@log_with(log)
def delete_server(identifier=None):
    """
    This call deletes the specified SAML IdP configuration

    :param identifier: The unique name of the SAML IdP definition
    """
    r = delete_samlidp(identifier)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@samlidp_blueprint.route('/fetch/<identifier>', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.SAMLIDPWRITE)
@log_with(log)
def fetch(identifier):
    """
    Fetch the SAML IdP Metadata and cache it in the database
    :return:
    """
    metadata = fetch_metadata(identifier)
    r = len(metadata)
    g.audit_object.log({'success': r > 0})
    return send_result(r > 0)
