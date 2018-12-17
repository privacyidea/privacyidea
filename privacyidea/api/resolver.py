# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2016-04-10 Cornelius Kölbel <cornelius@privacyidea.org>
#            Make route the outermost decorator
# 2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
#
# privacyIDEA is a fork of LinOTP. Some code is adapted from
# the system-controller from LinOTP, which is
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
The code of this module is tested in tests/test_api_system.py
"""
from flask import (Blueprint,
                   request)
from .lib.utils import (getParam,
                        optional,
                        required,
                        send_result)
from ..lib.log import log_with
from ..lib.resolver import (get_resolver_list,
                            save_resolver,
                            delete_resolver, pretestresolver)
from flask import g
import logging
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policy import ACTION


log = logging.getLogger(__name__)


resolver_blueprint = Blueprint('resolver_blueprint', __name__)


@resolver_blueprint.route('/', methods=['GET'])
@resolver_blueprint.route('/<resolver>', methods=['GET'])
@log_with(log)
def get_resolvers(resolver=None):
    """
    returns a json list of the specified resolvers.
    The passwords of resolvers (e.g. Bind PW of the LDAP resolver or password of the
    SQL resolver) will be returned as "__CENSORED__".
    You can run a POST request to update the data and privacyIDEA will ignore the "__CENSORED__"
    password or you can even run a testresolver.

    :param resolver: the name of the resolver
    :type resolver: str
    :param type: Only return resolvers of type (like passwdresolver..)
    :type type: str
    :param editable: Set to "1" if only editable resolvers should be returned.
    :type editable: str
    :return: a json result with the configuration of resolvers
    """
    typ = getParam(request.all_data, "type", optional)
    editable = getParam(request.all_data, "editable", optional)
    if editable == "1":
        editable = True
    elif editable == "0":
        editable = False

    res = get_resolver_list(filter_resolver_name=resolver,
                            filter_resolver_type=typ,
                            editable=editable,
                            censor=True)
    g.audit_object.log({"success": True,
                        "info": resolver})
    return send_result(res)


@resolver_blueprint.route('/<resolver>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.RESOLVERWRITE)
def set_resolver(resolver=None):
    """
    This creates a new resolver or updates an existing one.
    A resolver is uniquely identified by its name.

    If you update a resolver, you do not need to provide all parameters.
    Parameters you do not provide are left untouched.
    When updating a resolver you must not change the type!
    You do not need to specify the type, but if you specify a wrong type,
    it will produce an error.

    :param resolver: the name of the resolver.
    :type resolver: str
    :param type: the type of the resolver. Valid types are passwdresolver,
    ldapresolver, sqlresolver, scimresolver
    :type type: str
    :return: a json result with the value being the database id (>0)

    Additional parameters depend on the resolver type.

        LDAP:
            * LDAPURI
            * LDAPBASE
            * BINDDN
            * BINDPW
            * TIMEOUT
            * SIZELIMIT
            * LOGINNAMEATTRIBUTE
            * LDAPSEARCHFILTER
            * LDAPFILTER
            * USERINFO
            * NOREFERRALS        - True|False
            * EDITABLE           - True|False
        SQL:
            * Database
            * Driver
            * Server
            * Port
            * User
            * Password
            * Table
            * Map

        Passwd
            * Filename
    """
    param = request.all_data
    if resolver:
        # The resolver parameter was passed as a part of the URL
        param.update({"resolver": resolver})
    res = save_resolver(param)
    g.audit_object.log({"success": res,
                        "info": resolver})
    return send_result(res)


@resolver_blueprint.route('/<resolver>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.RESOLVERDELETE)
def delete_resolver_api(resolver=None):
    """
    This function deletes an existing resolver.
    A resolver can not be deleted, if it is contained in a realm

    :param resolver: the name of the resolver to delete.
    :return: json with success or fail
    """
    res = delete_resolver(resolver)
    g.audit_object.log({"success": res,
                        "info": resolver})

    return send_result(res)


@resolver_blueprint.route('/test', methods=["POST"])
@log_with(log)
@prepolicy(check_base_action, request, ACTION.RESOLVERWRITE)
def test_resolver():
    """
    Send the complete parameters of a resolver to the privacyIDEA server
    to test, if these settings will result in a successful connection.
    If you are testing existing resolvers, you can send the "__CENSORED__"
    password. privacyIDEA will use the already stored password from the
    database.

    :return: a json result with True, if the given values can create a
        working resolver and a description.
    """
    param = request.all_data
    rtype = getParam(param, "type", required)
    success, desc = pretestresolver(rtype, param)
    return send_result(success, details={"description": desc})

