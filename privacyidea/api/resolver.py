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
The resolver REST API manages user-id resolver definitions. A resolver
points privacyIDEA at a user store (LDAP/AD, SQL, /etc/passwd, SCIM, ...);
realms are then composed of one or more resolvers. See
:ref:`useridresolvers` for the conceptual chapter.

All endpoints require admin authentication. Read access is gated by the
admin policy action :ref:`resolverread`, write access by
:ref:`resolverwrite`, and deletion by :ref:`resolverdelete`.
"""
from flask import Blueprint, request
from .lib.utils import send_result
from ..lib.params import get_optional, get_required
from ..lib.log import log_with
from ..lib.resolver import get_resolver_list, save_resolver, delete_resolver, pretestresolver, get_resolver_class
from flask import g
import logging
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policies.actions import PolicyAction
from ..lib.utils import is_true

log = logging.getLogger(__name__)


resolver_blueprint = Blueprint('resolver_blueprint', __name__)


@resolver_blueprint.route('/', methods=['GET'])
@resolver_blueprint.route('/<resolver>', methods=['GET'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RESOLVERREAD)
def get_resolvers(resolver=None):
    """
    Return user-id resolver definitions. Without a path component all
    resolvers are listed; with ``<resolver>`` only the matching one is
    returned. Passwords (LDAP bind passwords, SQL passwords, ...) are
    returned as the literal string ``__CENSORED__``. A subsequent
    :http:post:`/resolver/(resolver)` request that includes the censored
    value will leave the stored password untouched, and so will a
    :http:post:`/resolver/test` call.

    Requires admin authentication and the policy action :ref:`resolverread`.

    :param resolver: optional path component selecting a single resolver.
    :query type: filter by resolver type (e.g. ``ldapresolver``,
        ``sqlresolver``, ``passwdresolver``, ``scimresolver``).
    :query editable: pass ``1`` to return only editable resolvers.
    :status 200: dict of resolver definitions keyed by name in
        ``result.value``.
    """
    typ = get_optional(request.all_data, "type")
    editable = get_optional(request.all_data, "editable")
    if editable is not None:
        editable = is_true(editable)

    res = get_resolver_list(filter_resolver_name=resolver,
                            filter_resolver_type=typ,
                            editable=editable,
                            censor=True)
    g.audit_object.log({"success": True,
                        "info": resolver})
    return send_result(res)


@resolver_blueprint.route('/<resolver>', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RESOLVERWRITE)
def set_resolver(resolver=None):
    """
    Create or update a user-id resolver. If a resolver with the given name
    already exists it is updated; otherwise it is created. On update only
    fields that should be changed need to be supplied, but the resolver
    ``type`` must not be changed (it is bound to the resolver class).

    When updating a resolver, password fields submitted as the literal
    ``__CENSORED__`` are ignored — the stored password is kept. This lets
    the WebUI round-trip a redacted ``GET`` response without leaking or
    losing the secret.

    Requires admin authentication and the policy action :ref:`resolverwrite`.

    :param resolver: path component, the name of the resolver.
    :jsonparam type: resolver type. Required on creation. The set of
        supported types is determined by the resolver classes installed
        on the server (currently shipped: LDAP, SQL, passwd, SCIM, HTTP,
        Keycloak, Entra ID). Use
        :http:get:`/resolver/(resolvertype)/default` to discover the
        fields each type accepts.
    :jsonparam: any resolver-type-specific configuration fields.
    :status 200: database id of the resolver in ``result.value``.

    Resolver-type fields:

    * ``ldapresolver`` — ``LDAPURI``, ``LDAPBASE``, ``AUTHTYPE``, ``BINDDN``,
      ``BINDPW``, ``TIMEOUT``, ``CACHE_TIMEOUT``, ``SIZELIMIT``,
      ``LOGINNAMEATTRIBUTE``, ``LDAPSEARCHFILTER``, ``LDAPFILTER``,
      ``MULTIVALUEATTRIBUTES``, ``USERINFO``, ``UIDTYPE``, ``NOREFERRALS``,
      ``NOSCHEMAS``, ``EDITABLE``, ``START_TLS``, ``TLS_VERIFY``,
      ``TLS_VERSION``.
    * ``sqlresolver`` — ``Database``, ``Driver``, ``Server``, ``Port``,
      ``User``, ``Password``, ``Table``, ``Map``.
    * ``passwdresolver`` — ``Filename``.

    Other resolver types accept their own fields; query
    :http:get:`/resolver/(resolvertype)/default` to discover them.
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
@prepolicy(check_base_action, request, PolicyAction.RESOLVERDELETE)
def delete_resolver_api(resolver=None):
    """
    Delete the user-id resolver with the given name. A resolver that is
    still part of a realm cannot be deleted — remove it from all realms
    first.

    Requires admin authentication and the policy action :ref:`resolverdelete`.

    :param resolver: path component, the name of the resolver.
    :status 200: id of the deleted resolver in ``result.value``.
    :status 400: the resolver is still in use by one or more realms.
    """
    res = delete_resolver(resolver)
    g.audit_object.log({"success": res,
                        "info": resolver})

    return send_result(res)


@resolver_blueprint.route('/test', methods=["POST"])
@log_with(log)
@prepolicy(check_base_action, request, PolicyAction.RESOLVERWRITE)
def test_resolver():
    """
    Test whether the supplied parameters yield a working resolver,
    including network connectivity to the underlying user store. The
    resolver class itself performs the verification; nothing is persisted.

    When testing an existing resolver, password fields may be submitted as
    the literal ``__CENSORED__`` and privacyIDEA will substitute the stored
    password from the database.

    Requires admin authentication and the policy action :ref:`resolverwrite`.

    :jsonparam type: resolver type (required).
    :jsonparam: any type-specific configuration fields.
    :status 200: ``result.value`` is ``True`` if the test succeeded,
        ``False`` otherwise; ``detail.description`` carries a human-readable
        message.
    """
    param = request.all_data
    rtype = get_required(param, "type")
    success, desc = pretestresolver(rtype, param)
    return send_result(success, details={"description": desc})


@resolver_blueprint.route('/<resolvertype>/default', methods=['GET'])
@log_with(log)
def get_default_resolver_config(resolvertype):
    """
    Return the default configuration for a resolver type. The WebUI calls
    this when an admin starts creating a new resolver, in order to populate
    the form with sensible defaults and discover the field set the chosen
    resolver class accepts.

    Requires admin authentication.

    .. note::
       Unlike the other resolver endpoints, this one is **not** gated by a
       specific policy action — admin auth is the only check.

    :param resolvertype: path component, the resolver type
        (e.g. ``ldapresolver``, ``sqlresolver``).
    :status 200: dict of default configuration values in ``result.value``.
    """
    resolver = get_resolver_class(resolvertype)()
    config = resolver.get_config()
    return send_result(config)
