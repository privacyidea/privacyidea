# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2015-02-26 Cornelius Kölbel, <cornelius@privacyidea.org>
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
This endpoint is used to create, modify, list and delete Machine Resolvers.
Machine Resolvers fetch machine information from remote machine stores like a
hosts file or an Active Directory.

The code of this module is tested in tests/test_api_machineresolver.py
"""
from flask import (Blueprint,
                   request)
from .lib.utils import (getParam,
                        optional,
                        required,
                        send_result)
from ..lib.log import log_with
from ..lib.machineresolver import (get_resolver_list, save_resolver, delete_resolver,
                           pretestresolver)
from flask import g
import logging
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policy import ACTION


log = logging.getLogger(__name__)


machineresolver_blueprint = Blueprint('machineresolver_blueprint', __name__)


@machineresolver_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.MACHINERESOLVERREAD)
def get_resolvers():
    """
    returns a json list of all machine resolver.

    :param type: Only return resolvers of type (like "hosts"...)
    """
    typ = getParam(request.all_data, "type", optional)
    res = get_resolver_list(filter_resolver_type=typ)
    g.audit_object.log({"success": True})
    return send_result(res)


@machineresolver_blueprint.route('/<resolver>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.MACHINERESOLVERWRITE)
def set_resolver(resolver=None):
    """
    This creates a new machine resolver or updates an existing one.
    A resolver is uniquely identified by its name.

    If you update a resolver, you do not need to provide all parameters.
    Parameters you do not provide are left untouched.
    When updating a resolver you must not change the type!
    You do not need to specify the type, but if you specify a wrong type,
    it will produce an error.

    :param resolver: the name of the resolver.
    :type resolver: basestring
    :param type: the type of the resolver. Valid types are... "hosts"
    :type type: string
    :return: a json result with the value being the database id (>0)

    Additional parameters depend on the resolver type.

    hosts:
     * filename
    """
    param = request.all_data
    if resolver:
        # The resolver parameter was passed as a part of the URL
        param.update({"name": resolver})
    res = save_resolver(param)
    return send_result(res)


@machineresolver_blueprint.route('/<resolver>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.MACHINERESOLVERDELETE)
def delete_resolver_api(resolver=None):
    """
    this function deletes an existing machine resolver

    :param resolver: the name of the resolver to delete.
    :return: json with success or fail
    """
    res = delete_resolver(resolver)
    g.audit_object.log({"success": res,
                        "info": resolver})

    return send_result(res)


@machineresolver_blueprint.route('/<resolver>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.MACHINERESOLVERREAD)
def get_resolver(resolver=None):
    """
    This function retrieves the definition of a single machine resolver.

    :param resolver: the name of the resolver
    :return: a json result with the configuration of a specified resolver
    """
    res = get_resolver_list(filter_resolver_name=resolver)

    g.audit_object.log({"success": True,
                        "info": resolver})

    return send_result(res)


@machineresolver_blueprint.route('/test', methods=["POST"])
@log_with(log)
def test_resolver():
    """
    This function tests, if the given parameter will create a working
    machine resolver. The Machine Resolver Class itself verifies the
    functionality. This can also be network connectivity to a Machine Store.

    :return: a json result with bool
    """
    param = request.all_data
    rtype = getParam(param, "type", required)
    success, desc = pretestresolver(rtype, param)
    return send_result(success, details={"description": desc})

