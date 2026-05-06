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
The machine-resolver REST API manages machine resolver definitions.
A machine resolver fetches information about machines (host name, IP,
identifier) from a backing store such as a local hosts file or an LDAP
directory; the resolved machines are then targets for token attachments
and machine applications (see :ref:`rest_machine`).

All endpoints require admin authentication. Read access is gated by the
admin policy action :ref:`mresolverread`, write access by
:ref:`mresolverwrite`, and deletion by :ref:`mresolverdelete`.
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
from ..lib.policies.actions import PolicyAction

log = logging.getLogger(__name__)


machineresolver_blueprint = Blueprint('machineresolver_blueprint', __name__)


@machineresolver_blueprint.route('/', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.MACHINERESOLVERREAD)
def get_resolvers():
    """
    Return all machine resolvers known to this server. The result is a
    dictionary keyed by resolver name; each value contains the resolver
    type and its configuration.

    Requires admin authentication and the policy action :ref:`mresolverread`.

    :query type: optional filter — return only resolvers of the given type
        (``hosts``, ``ldap``, ...).
    :status 200: dict of resolver definitions in ``result.value``.
    """
    typ = getParam(request.all_data, "type", optional)
    res = get_resolver_list(filter_resolver_type=typ)
    g.audit_object.log({"success": True})
    return send_result(res)


@machineresolver_blueprint.route('/<resolver>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.MACHINERESOLVERWRITE)
def set_resolver(resolver=None):
    """
    Create or update a machine resolver. If a resolver with the given name
    already exists it is updated; otherwise it is created. On update,
    parameters that are not supplied are left unchanged, but the resolver
    ``type`` must not be changed (it is bound to the resolver class).

    Requires admin authentication and the policy action :ref:`mresolverwrite`.

    :param resolver: path component, the name of the resolver.
    :jsonparam type: resolver type (``hosts``, ``ldap``, ...). Required on
        creation.
    :jsonparam: any resolver-type-specific configuration fields. For example
        a ``hosts`` resolver expects ``filename`` (the path to a hosts-style
        file on the server).
    :status 200: database id of the resolver in ``result.value``.
    """
    param = request.all_data
    if resolver:
        # The resolver parameter was passed as a part of the URL
        param.update({"name": resolver})
    res = save_resolver(param)
    return send_result(res)


@machineresolver_blueprint.route('/<resolver>', methods=['DELETE'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.MACHINERESOLVERDELETE)
def delete_resolver_api(resolver=None):
    """
    Delete the machine resolver with the given name.

    Requires admin authentication and the policy action :ref:`mresolverdelete`.

    :param resolver: path component, the name of the resolver.
    :status 200: id of the deleted resolver in ``result.value``.
    """
    res = delete_resolver(resolver)
    g.audit_object.log({"success": res,
                        "info": resolver})

    return send_result(res)


@machineresolver_blueprint.route('/<resolver>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.MACHINERESOLVERREAD)
def get_resolver(resolver=None):
    """
    Return the configuration of a single machine resolver.

    The result is a dictionary keyed by resolver name (single entry), with
    the resolver's type and configuration.

    Requires admin authentication and the policy action :ref:`mresolverread`.

    :param resolver: path component, the name of the resolver.
    :status 200: dict containing the resolver's configuration in ``result.value``.
    """
    res = get_resolver_list(filter_resolver_name=resolver)

    g.audit_object.log({"success": True,
                        "info": resolver})

    return send_result(res)


@machineresolver_blueprint.route('/test', methods=["POST"])
@log_with(log)
def test_resolver():
    """
    Test whether the supplied parameters yield a working machine resolver,
    including network connectivity to the underlying store. The resolver
    class itself performs the verification; nothing is persisted.

    Requires admin authentication.

    .. note::
       Unlike the other write endpoints in this module, this endpoint is
       **not** gated by a specific policy action — admin auth is the only
       check.

    :jsonparam type: resolver type (required).
    :jsonparam: any type-specific configuration fields.
    :status 200: ``result.value`` is ``True`` if the test succeeded,
        ``False`` otherwise; ``detail.description`` carries a human-readable
        message.
    """
    param = request.all_data
    rtype = getParam(param, "type", required)
    success, desc = pretestresolver(rtype, param)
    return send_result(success, details={"description": desc})

