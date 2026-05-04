# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2017-07-11 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Allow to return GPG keys
# 2015-12-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Remove the complete before and after logic
# 2015-10-12 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add a call for testing token config
# 2015-09-25 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add HSM interface
# 2015-06-26 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add system config documentation API
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
__doc__ = """
This is the REST API for system calls to create and read system configuration.

The code of this module is tested in tests/test_api_system.py
"""

from flask_babel import _
import datetime
import logging
import re
import socket
from urllib.parse import urlsplit

from flask import (Blueprint,
                   request)
from flask import (g, current_app, render_template)

from privacyidea.lib.auth import get_all_db_admins
from privacyidea.lib.crypto import geturandom, set_hsm_password, get_hsm
from privacyidea.lib.importotp import GPGImport
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.health import get_certificate_status
from privacyidea.lib.metrics import get_metrics, cleanup_old_metrics
from privacyidea.lib.usercache import delete_user_cache
from privacyidea.lib.utils import hexlify_and_unicode, b64encode_and_unicode, is_true
from .auth import admin_required
from .lib.utils import (getLowerParams,
                        send_result, send_file)
from ..lib.params import get_optional, get_required
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.caconnector import get_caconnector_list
from ..lib.config import (get_token_class,
                          set_privacyidea_config,
                          delete_privacyidea_config,
                          get_from_config,
                          get_privacyidea_nodes)
from ..lib.error import ParameterError
from ..lib.log import log_with
from ..lib.policies.actions import PolicyAction
from ..lib.radiusserver import get_radiusservers

log = logging.getLogger(__name__)

system_blueprint = Blueprint('system_blueprint', __name__)


@system_blueprint.route('/documentation', methods=['GET'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.CONFIGDOCUMENTATION)
def get_config_documentation():
    """
    returns an restructured text document, that describes the complete
    configuration.
    """
    P = PolicyClass()

    config = get_from_config()
    resolvers = get_resolver_list()
    realms = get_realms()
    policies = P.list_policies()
    admins = get_all_db_admins()
    context = {"system": socket.getfqdn(socket.gethostname()),
               "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
               "systemconfig": config,
               "appconfig": current_app.config,
               "resolverconfig": resolvers,
               "realmconfig": realms,
               "policyconfig": policies,
               "admins": admins}

    g.audit_object.log({"success": True})
    # Three or more line breaks will be changed to two.
    return send_file(re.sub("\n{3,}", "\n\n", render_template("documentation.rst",
                                                              context=context)),
                     'documentation.rst', content_type='text/plain')


@system_blueprint.route('/gpgkeys', methods=['GET'])
def get_gpg_keys():
    """
    Returns the GPG keys in the config directory specified by PI_GNUPG_HOME.

    :return: A json list of the public GPG keys
    """
    GPG = GPGImport(current_app.config)
    keys = GPG.get_publickeys()
    g.audit_object.log({"success": True})
    return send_result(keys)


@system_blueprint.route('/<key>', methods=['GET'])
@system_blueprint.route('/', methods=['GET'])
def get_config(key=None):
    """
    This endpoint either returns all config entries or only the value of the
    one config key.

    This endpoint can be called by the administrator but also by the normal
    user, so that the normal user gets necessary information about the system
    config

    :param key: (optional) The key to return
    :>json bool status: Status of the request
    :>json value: JSON object with a key-value pair of the config entries or
    :>json value: The value of the specified config entry
    :reqheader PI-Authorization: The authorization token

    **Example request 1**:

    .. sourcecode:: http

       GET /system/ HTTP/1.1
       Host: example.com
       Content-Type: application/json

    **Example response 1**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": {
              "AutoResync": "False",
              "splitAtSign": "True",
              "PrependPin": "True",
              "DefaultCountWindow": "10"
            }
          },
          "version": "privacyIDEA unknown"
        }

    **Example request 2**:
    Querying a specific system-configuration value

    .. sourcecode:: http

       GET /system/totp.hashlib HTTP/1.1
       Host: example.com
       Content-Type: application/json

    **Example response 2**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": "sha1"
          },
          "version": "privacyIDEA unknown"
        }
    """
    if not key:
        result = get_from_config(role=g.logged_in_user.get("role"))
    else:
        result = get_from_config(key, role=g.logged_in_user.get("role"))

    g.audit_object.log({"success": True,
                        "info": key})
    return send_result(result)


@system_blueprint.route('/setConfig', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.SYSTEMWRITE)
def set_config():
    """
    set a configuration key or a set of configuration entries

    parameter are generic ``keyname=value`` pairs.

    **remark** In case of key-value pairs the type information could be
        provided by an additional parameter with same keyname with the
        postfix ".type". Value could then be 'password' to trigger the
        storing of the value in an encrypted form

    :<json key-value-pairs: a list of ``keyname=value`` pairs
    :<json <keyname>.type: type of the value: int or string/text or password.
        password will trigger to store the encrypted value
    :<json <keyname>.desc: additional information for this config entry
    :>json bool status: Status of the request
    :>json value: JSON object with a list of key-value pairs of the requested
        config entry changes with the value of ``update`` or ``insert``
    :reqheader PI-Authorization: The authorization token

    **Example request**:

    .. sourcecode:: http

        POST /system/setConfig HTTP/1.1
        Host: example.com
        Content-Type: application/json

        "splitAtSign": true
        "totp.hashlib": "sha1"
        "totp.hashlib.desc": "The hash algorithm used for TOTP tokens"

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": {
              "splitAtSign": "update",
              "totp.hashlib": "update"
            }
          },
          "version": "privacyIDEA unknown"
        }
    """
    param = request.all_data
    result = {}
    for key in param:
        if key.split(".")[-1] not in ["type", "desc"]:
            # Only store base values, not type or desc
            value = get_optional(param, key)
            typ = get_optional(param, key + ".type")
            desc = get_optional(param, key + ".desc")
            res = set_privacyidea_config(key, value, typ, desc)
            result[key] = res
            g.audit_object.add_to_log({"info": f"{key!s}={value!s}, "})
    g.audit_object.log({"success": True})
    return send_result(result)


@system_blueprint.route('/setDefault', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.SYSTEMWRITE)
def set_default():
    """
    define default settings for tokens. These default settings
    are used when new tokens are generated. The default settings will
    not affect already enrolled tokens.

    :jsonparam DefaultMaxFailCount: Default value for the maximum allowed
        authentication failures
    :jsonparam DefaultSyncWindow: Default value for the synchronization window
    :jsonparam DefaultCountWindow: Default value for the counter window
    :jsonparam DefaultOtpLen: Default value for the OTP value length --
        usually 6 or 8
    :jsonparam DefaultResetFailCount: Default value, if the FailCounter should
        be reset on successful authentication [True|False]

    :return: a json result with a boolean "result": true

    """
    keys = ["DefaultMaxFailCount",
            "DefaultSyncWindow",
            "DefaultCountWindow",
            "DefaultOtpLen",
            "DefaultResetFailCount"]

    description = "parameters are: {!s}".format(", ".join(keys))
    param = getLowerParams(request.all_data)
    result = {}
    for k in keys:
        if k.lower() in param:
            value = get_required(param, k.lower())
            res = set_privacyidea_config(k, value)
            result[k] = res
            g.audit_object.log({"success": True})
            g.audit_object.add_to_log({"info": f"{k!s}={value!s}, "})

    if not result:
        log.warning("Failed saving config. Could not find any "
                    f"known parameter. {description}")
        raise ParameterError(_("Usage: {0!s}").format(description), id=77)

    return send_result(result)


@system_blueprint.route('/<key>', methods=['DELETE'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.SYSTEMDELETE)
@log_with(log)
def delete_config(key=None):
    """
    delete a configuration key

    :param string key: configuration key name
    :returns: a json result with the deleted value

    """
    if not key:
        raise ParameterError(_("You need to provide the config key to delete."))
    res = delete_privacyidea_config(key)
    g.audit_object.log({'success': res,
                        'info': key})
    return send_result(res)


@system_blueprint.route('/hsm', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.SETHSM)
@log_with(log)
def set_security_module():
    """
    Set the password for the security module
    """
    password = get_required(request.all_data, "password")
    is_ready = set_hsm_password(password)
    res = {"is_ready": is_ready}
    g.audit_object.log({'success': res})
    return send_result(res)


@system_blueprint.route('/hsm', methods=['GET'])
@admin_required
@log_with(log)
def get_security_module():
    """
    Get the status of the security module.
    """
    hsm = get_hsm(require_ready=False)
    is_ready = hsm.is_ready
    res = {"is_ready": is_ready}
    g.audit_object.log({'success': res})
    return send_result(res)


@system_blueprint.route('/random', methods=['GET'])
@admin_required
@prepolicy(check_base_action, request, action=PolicyAction.GETRANDOM)
@log_with(log)
def rand():
    """
    This endpoint can be used to retrieve random keys from privacyIDEA.
    In certain cases the client might need random data to initialize tokens
    on the client side. E.g. the command line client when initializing the
    yubikey or the WebUI when creating Client API keys for the yubikey.

    In this case, privacyIDEA can create the random data/keys.

    :queryparam len: The length of a symmetric key (byte)
    :queryparam encode: The type of encoding. Can be "hex" or "b64".

    :return: key material
    """
    length = int(get_optional(request.all_data, "len") or 20)
    encode = get_optional(request.all_data, "encode")

    r = geturandom(length=length)
    if encode == "b64":
        res = b64encode_and_unicode(r)
    else:
        res = hexlify_and_unicode(r)

    g.audit_object.log({'success': res})
    return send_result(res)


@system_blueprint.route('/test/<tokentype>', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, action=PolicyAction.SYSTEMWRITE)
@log_with(log)
def test(tokentype=None):
    """
    The call /system/test/email tests the configuration of the email token.
    """
    tokenc = get_token_class(tokentype)
    res, description = tokenc.test_config(request.all_data)
    g.audit_object.log({"success": 1,
                        "token_type": tokentype})
    return send_result(res, details={"message": description})


@system_blueprint.route('/names/radius', methods=['GET'])
@prepolicy(check_base_action, request, action="enrollRADIUS")
def list_radius_servers():
    """
    Return the list of identifiers of all defined RADIUS servers.
    This endpoint requires the enrollRADIUS right.
    """
    server_list = get_radiusservers()
    res = [server.config.identifier for server in server_list]
    g.audit_object.log({'success': True})
    return send_result(res)


@system_blueprint.route('/names/caconnector', methods=['GET'])
@prepolicy(check_base_action, request, action="enrollCERTIFICATE")
def list_ca_connectors():
    """
    Return a list of defined CA connectors. Each item of the list is
    a dictionary with the CA connector information, including the
    name and defined templates, but excluding the CA connector data.
    This endpoint requires the enrollCERTIFICATE right.
    """
    ca_list = get_caconnector_list(return_config=False)
    g.audit_object.log({"success": True})
    return send_result(ca_list)


@system_blueprint.route("/nodes", methods=['GET'])
@admin_required
def list_nodes():
    """
    Return a list of nodes, that are known to the system.

    :>json list nodes: A list of JSON objects with the node name and uuid
    :reqheader PI-Authorization: The authorization token

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": [
                {
                    "name": "node1",
                    "uuid": "12345678-1234-1234-1234-1234567890ab"
                },
                {
                    "name": "node2",
                    "uuid": "12345678-4321-1234-1234-1234567890ac"
                }
            ]
          },
          "version": "privacyIDEA unknown"
        }
    .. versionadded:: 3.10 Return node information with names and UUIDs
    """
    nodes = get_privacyidea_nodes()
    g.audit_object.log({"success": True})
    return send_result(nodes)


@system_blueprint.route("/health/certificates", methods=['GET'])
@admin_required
@log_with(log)
def get_health_certificates():
    """
    Return certificate expiry information for all configured LDAP resolvers
    (where the resolver uses ldaps:// or START_TLS) and for the privacyIDEA
    server certificate.

    The privacyIDEA server certificate is probed by opening a TLS connection
    back to the host/port the admin used to reach this endpoint (Flask's
    ``request.host``, which honors ``X-Forwarded-Host`` when configured).
    This works uniformly for apache+uwsgi, nginx+gunicorn and the flask dev
    server, since the actual cert is whatever is terminating TLS in front
    of privacyIDEA.

    The result is cached for ``PI_CERT_CHECK_CACHE_SECONDS`` seconds
    (default 3600). Pass ``?refresh=1`` to bypass the cache.

    Each entry has a ``status`` of ``ok`` (>30 days), ``warning`` (<=30 days),
    ``critical`` (<=7 days), ``expired`` (<=0 days), ``error`` (could not
    fetch), or ``not_configured`` (server cert can only be checked over HTTPS).

    :queryparam refresh: If truthy, bypass the cache and re-check.
    :>json list value: List of certificate status entries.
    :reqheader PI-Authorization: The authorization token
    """
    refresh = is_true(get_optional(request.all_data, "refresh"))
    https = request.scheme == "https"
    # Werkzeug exposes parsed forms; falls back to defaults if the header was
    # malformed. Handles IPv6 ("[::1]:443") and hostnames-with-colons safely.
    server_host = request.host_url and urlsplit(request.host_url).hostname
    server_port = request.host_url and urlsplit(request.host_url).port
    if not server_host:
        server_host = request.host.split(":")[0].strip("[]")
    if not server_port:
        server_port = 443 if https else 80
    result = get_certificate_status(server_host=server_host, server_port=server_port,
                                    https=https, refresh=refresh)
    g.audit_object.log({"success": True})
    return send_result(result)


@system_blueprint.route("/health/resolver_timing", methods=['GET'])
@admin_required
@log_with(log)
def get_health_resolver_timing():
    """
    Return rolling resolver-operation timing aggregates per resolver and op.

    Reads pre-aggregated counters/buckets stored by
    :func:`privacyidea.lib.metrics.observe` calls wrapped around every
    ``UserIdResolver`` public method (``get_user_info``, ``get_user_list``,
    ``check_pass``, ``add_user``, ``update_user``, ``delete_user``,
    ``get_user_id``, ``get_username``). Covers all resolver types
    uniformly (LDAP, SQL, HTTP, EntraID, Keycloak, passwd).

    The returned ``count``, ``avg``, ``p50``, ``p95``, ``max`` are summed
    across all privacyIDEA nodes and 5-minute windows that fall within
    the requested window.

    :queryparam since_seconds: Window length in seconds. Default 3600 (1h).
    :>json list value: One entry per ``(resolver, resolver_type, op)`` triple.
    :reqheader PI-Authorization: The authorization token
    """
    try:
        since_seconds = int(get_optional(request.all_data, "since_seconds") or 3600)
    except (TypeError, ValueError):
        since_seconds = 3600
    raw = get_metrics(name="resolver_op_duration_seconds", since_seconds=since_seconds)
    g.audit_object.log({"success": True})
    return send_result(raw)


def _aggregate_delivery_channel(counter_name, duration_name, key_label, since_seconds):
    """Fold counter rows by their key label into one entry per key.

    Counter rows are grouped by the value of ``key_label`` (e.g. ``"provider"``,
    ``"gateway"``, ``"identifier"``). Each group's outcome counts (ok / failed /
    error) come from ``counter_name``; latency stats come from
    ``duration_name`` rows with the same key.
    """
    counters = get_metrics(name=counter_name, since_seconds=since_seconds)
    durations = get_metrics(name=duration_name, since_seconds=since_seconds)

    by_key = {}
    for c in counters:
        labels = c.get("labels") or {}
        key = labels.get(key_label, "?")
        result = labels.get("result", "?")
        entry = by_key.setdefault(key, {
            "key": key, "ok": 0, "failed": 0, "error": 0, "total": 0,
        })
        cnt = c.get("count") or 0
        if result in ("ok", "failed", "error"):
            entry[result] += cnt
        entry["total"] += cnt

    for d in durations:
        labels = d.get("labels") or {}
        key = labels.get(key_label, "?")
        entry = by_key.setdefault(key, {
            "key": key, "ok": 0, "failed": 0, "error": 0, "total": 0,
        })
        entry["avg"] = d.get("avg")
        entry["p50"] = d.get("p50")
        entry["p95"] = d.get("p95")
        entry["max"] = d.get("max")
        entry["duration_count"] = d.get("count") or 0

    return sorted(by_key.values(), key=lambda e: e["total"], reverse=True)


@system_blueprint.route("/health/notification_delivery", methods=['GET'])
@admin_required
@log_with(log)
def get_health_notification_delivery():
    """
    Return rolling delivery counters and latency for the three notification
    channels (push, SMS, email).

    Each channel folds rows by its primary label dimension:

    * push: ``gateway`` (the SMS gateway identifier configured for Firebase)
    * sms: ``gateway`` (the SMS gateway identifier)
    * email: ``identifier`` (the SMTP server identifier)

    :queryparam since_seconds: Window length in seconds. Default 3600 (1h).
    :reqheader PI-Authorization: The authorization token
    """
    try:
        since_seconds = int(get_optional(request.all_data, "since_seconds") or 3600)
    except (TypeError, ValueError):
        since_seconds = 3600

    result = {
        "push": _aggregate_delivery_channel(
            "push_delivery_total", "push_delivery_duration_seconds",
            "gateway", since_seconds),
        "sms": _aggregate_delivery_channel(
            "sms_send_total", "sms_send_duration_seconds",
            "gateway", since_seconds),
        "email": _aggregate_delivery_channel(
            "email_send_total", "email_send_duration_seconds",
            "identifier", since_seconds),
        "since_seconds": since_seconds,
    }
    g.audit_object.log({"success": True})
    return send_result(result)


@system_blueprint.route("/user-cache", methods=['DELETE'])
@admin_required
def delete_user_cache_api():
    """
    Delete all entries from the user cache.

    :>json bool status: Status of the request
    :reqheader PI-Authorization: The authorization token

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "deleted": 42
          },
          "version": "privacyIDEA unknown"
        }
    """
    row_count = delete_user_cache()
    g.audit_object.log({"success": True, "info": f"Deleted {row_count} entries from user cache"})
    return send_result({"status": True, "deleted": row_count})


@system_blueprint.route("/metricscleanup", methods=['POST'])
@admin_required
@log_with(log)
def metricscleanup_api():
    """
    Delete metric_aggregate rows older than ``older_than_hours`` hours.
    Mirrors what the ``MetricsCleanup`` periodic task does, but on demand.

    :jsonparam older_than_hours: retention threshold in hours. Default 24.
                                 Values < 1 are clamped to 1 to prevent wiping
                                 the live (in-progress) bucket.
    :reqheader PI-Authorization: The authorization token
    """
    try:
        hours = int(get_optional(request.all_data, "older_than_hours") or 24)
    except (TypeError, ValueError):
        hours = 24
    if hours < 1:
        hours = 1
    deleted = cleanup_old_metrics(older_than_seconds=hours * 3600)
    g.audit_object.log({"success": True,
                        "info": f"Deleted {deleted} metric_aggregate row(s) older than {hours}h"})
    return send_result({"status": True, "deleted": deleted, "older_than_hours": hours})
