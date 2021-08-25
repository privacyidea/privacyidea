# -*- coding: utf-8 -*-
#
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
__doc__ = """This endpoint is used to create, update, list and delete 
privacyIDEA server definitions. privacyIDEA server definitions can be used for 
Remote-Tokens and for Federation-Events.

The code of this module is tested in tests/test_api_privacyideaserver.py
"""
from flask import (Blueprint, request)
from .lib.utils import (getParam,
                        required,
                        send_result)
from ..lib.log import log_with
from ..lib.policy import ACTION
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
@prepolicy(check_base_action, request, ACTION.PRIVACYIDEASERVERWRITE)
@log_with(log)
def create(identifier=None):
    """
    This call creates or updates a privacyIDEA Server definition

    :param identifier: The unique name of the privacyIDEA server definition
    :param url: The URL of the privacyIDEA server
    :param tls: Set this to 0, if tls should not be checked
    :param description: A description for the definition
    """
    param = request.all_data
    identifier = identifier.replace(" ", "_")
    url = getParam(param, "url", required)
    tls = is_true(getParam(param, "tls", default="1"))
    description = getParam(param, "description", default="")

    r = add_privacyideaserver(identifier, url=url, tls=tls,
                              description=description)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@privacyideaserver_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.PRIVACYIDEASERVERREAD)
def list_privacyidea():
    """
    This call gets the list of privacyIDEA server definitions
    """
    res = list_privacyideaservers()

    g.audit_object.log({'success': True})
    return send_result(res)


@privacyideaserver_blueprint.route('/<identifier>', methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.PRIVACYIDEASERVERWRITE)
@log_with(log)
def delete_server(identifier=None):
    """
    This call deletes the specified privacyIDEA server configuration

    :param identifier: The unique name of the privacyIDEA server definition
    """
    r = delete_privacyideaserver(identifier)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)


@privacyideaserver_blueprint.route('/test_request', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.PRIVACYIDEASERVERWRITE)
@log_with(log)
def test():
    """
    Test the privacyIDEA definition
    :return:
    """
    param = request.all_data
    identifier = getParam(param, "identifier", required)
    url = getParam(param, "url", required)
    tls = is_true(getParam(param, "tls", default="1"))
    user = getParam(param, "username", required)
    password = getParam(param, "password", required)


    s = PrivacyIDEAServerDB(identifier=identifier, url=url, tls=tls)
    r = PrivacyIDEAServer.request(s, user, password)

    g.audit_object.log({'success': r > 0,
                        'info':  r})
    return send_result(r > 0)
