# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
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
                   request,
                   url_for)
from lib.utils import (getParam,
                       getLowerParams,
                       optional,
                       required,
                       send_result)
from ..lib.log import log_with
from ..lib.realm import get_realms
from ..lib.resolver import (get_resolver_list,
                            create_resolver,
                            delete_resolver)
from ..lib.realm import (set_default_realm,
                         get_default_realm,
                         set_realm,
                         delete_realm)
from ..lib.config import (get_privacyidea_config,
                          set_privacyidea_config,
                          delete_privacyidea_config,
                          get_from_config)
from ..lib.policy import (set_policy,
                          get_policies, PolicyClass,
                          export_policies, import_policies,
                          delete_policy, get_static_policy_definitions)
from ..lib.error import (ParameterError,
                         AuthError,
                         PolicyError)
from ..lib.token import get_dynamic_policy_definitions

from .auth import (check_auth_token,
                   auth_required)
from flask import (g,
                    make_response,
                    current_app)
from gettext import gettext as _
from werkzeug.datastructures import FileStorage
from cgi import FieldStorage

import logging
import traceback
import re


log = logging.getLogger(__name__)


resolver_blueprint = Blueprint('resolver_blueprint', __name__)


# ----------------------------------------------------------------------
#
#   Resolver methods
#

@log_with(log)
@resolver_blueprint.route('/', methods=['GET'])
def get_resolvers():
    """
    returns a json list of all resolver.

    :param type: Only return resolvers of type (like passwdresolver..)
    """
    typ = getParam(request.all_data, "type", optional)
    res = get_resolver_list(filter_resolver_type=typ)
    g.audit['success'] = True
    return send_result(res)


@log_with(log)
@resolver_blueprint.route('/<resolver>', methods=['POST'])
def set_resolver(resolver=None):
    """
    This creates a new resolver or updates an existing one.
    A resolver is uniquely identified by its name.

    :param resolver: the name of the resolver.
    :type resolver: basestring
    :param type: the type of the resolver. Valid types are passwdresolver,
    ldapresolver, sqlresolver, scimresolver
    :type type: string
    :return: a json result with the value being the database id (>0)

    Additional parameters depend on the resolver type.

        LDAP:
            LDAPURI
            LDAPBASE
            BINDDN
            BINDPW
            TIMEOUT
            SIZELIMIT
            LOGINNAMEATTRIBUTE
            LDAPSEARCHFILTER
            LDAPFILTER
            USERINFO
            NOREFERRALS        - True|False
        SQL:
            Database
            Driver
            Server
            Port
            User
            Password
            Table
            Map

        Passwd
            Filename
    """
    param = request.all_data
    if resolver:
        # The resolver parameter was passed as a part of the URL
        param.update({"resolver": resolver})
    res = create_resolver(param)
    return send_result(res)


@log_with(log)
@resolver_blueprint.route('/<resolver>', methods=['DELETE'])
def delete_resolver_api(resolver=None):
    """
    this function deletes an existing resolver
    A resolver can not be deleted, if it is contained in a realm

    :param resolver: the name of the resolver to delete.
    :return: json with success or fail
    """
    res = delete_resolver(resolver)
    g.audit['success'] = res
    g.audit['info'] = resolver

    return send_result(res)


@log_with(log)
@resolver_blueprint.route('/<resolver>', methods=['GET'])
def get_resolver(resolver=None):
    """
    This function retrieves the definition of a single resolver.
    If can be called via /system/getResolver?resolver=
    or via /resolver/<resolver>

    :param resolver: the name of the resolver
    :returns: a json result with the configuration of a specified resolver
    """
    res = get_resolver_list(filter_resolver_name=resolver)

    g.audit['success'] = True
    g.audit['info'] = resolver

    return send_result(res)


