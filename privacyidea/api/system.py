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
The system REST API exposes the server's configuration store and a
handful of operational endpoints: the HSM unlock, an entropy source,
per-token configuration tests, the rendered system documentation, and
listings of configured RADIUS servers, CA connectors and nodes. See
:ref:`system_config` for the conceptual chapter.

Most endpoints require admin authentication. Create/update and the
``setDefault`` shortcut are gated by the policy action
:ref:`configwrite`; deletion by :ref:`configdelete`. The rendered
documentation requires :ref:`policy_system_documentation`, the HSM
unlock requires :ref:`policy_set_hsm_password`, and the entropy
endpoint requires :ref:`policy_getrandom`. ``GET /system/`` /
``GET /system/<key>`` may be called by any authenticated user;
non-admin callers only see configuration entries flagged as ``public``.
"""

from flask_babel import _
import datetime
import logging
import re
import socket

from flask import (Blueprint,
                   request)
from flask import (g, current_app, render_template)

from privacyidea.lib.auth import get_all_db_admins
from privacyidea.lib.crypto import geturandom, set_hsm_password, get_hsm
from privacyidea.lib.importotp import GPGImport
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_list, CENSORED
from privacyidea.lib.health import get_certificate_status
from privacyidea.lib.metrics import get_metrics, cleanup_old_metrics
from privacyidea.lib.usercache import delete_user_cache
from privacyidea.lib.utils import hexlify_and_unicode, b64encode_and_unicode, is_true
from .auth import admin_required
from .lib.utils import (getLowerParams,
                        send_result, send_file)
from ..lib.params import get_optional, get_required
from ..api.lib.prepolicy import prepolicy, check_base_action, check_admin_base_action
from ..lib.caconnector import get_caconnector_list
from ..lib.config import (get_token_class,
                          set_privacyidea_config,
                          delete_privacyidea_config,
                          get_from_config,
                          get_config_object,
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
    Render the current server configuration (system config, app config,
    resolvers, realms, policies, admin accounts) into a single
    reStructuredText document. The response is ``text/plain``; consumers
    typically pipe it through Sphinx to produce a rendered status report.

    Requires admin authentication and the policy action
    :ref:`policy_system_documentation`.

    :status 200: ``text/plain`` body containing the rendered document.
    """
    P = PolicyClass()

    config = get_from_config()
    # Do not expose decrypted password-typed values in the exported report
    config_object = get_config_object()
    for config_key, config_entry in config_object.config.items():
        if config_entry.get("Type") == "password" and config_key in config:
            config[config_key] = CENSORED
    resolvers = get_resolver_list(censor=True)
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
    Return the public GPG keys held in the directory configured via
    ``PI_GNUPG_HOME``. These keys are used to verify imported token
    seed files.

    Requires admin authentication.

    :status 200: dict of public GPG keys (keyed by fingerprint) in
        ``result.value``.
    """
    GPG = GPGImport(current_app.config)
    keys = GPG.get_publickeys()
    g.audit_object.log({"success": True})
    return send_result(keys)


@system_blueprint.route('/<key>', methods=['GET'])
@system_blueprint.route('/', methods=['GET'])
@prepolicy(check_admin_base_action, request, PolicyAction.SYSTEMREAD)
def get_config(key=None):
    """
    Return system configuration.

    Without a path component, returns all configuration entries as a
    dictionary. With ``<key>`` in the path, returns only that entry's
    value.

    Both admins and authenticated users may call this endpoint, but
    non-admins only see configuration entries that are flagged as
    ``public``. Querying a non-public key as a regular user returns
    ``null``. Admin access is gated by the policy action
    :ref:`policy_configread` when at least one ``configread`` policy
    is defined.

    :param key: optional path component, the configuration key to fetch.
    :reqheader PI-Authorization: authentication token.
    :status 200: configuration dictionary or single value in
        ``result.value``.

    **Example request**:

    .. sourcecode:: http

       GET /system/ HTTP/1.1
       Host: example.com
       Accept: application/json

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
             "AutoResync": "False",
             "splitAtSign": "True",
             "PrependPin": "True",
             "DefaultCountWindow": "10"
           }
         },
         "version": "privacyIDEA unknown"
       }

    **Example request (single key)**:

    .. sourcecode:: http

       GET /system/totp.hashlib HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response (single key)**:

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
    Set one or more system configuration entries. The body is a flat
    dictionary of ``keyname: value`` pairs; per-entry metadata may be
    supplied using ``keyname.type`` and ``keyname.desc`` companion keys.
    Setting ``keyname.type`` to ``password`` causes the value to be
    stored encrypted.

    Requires admin authentication and the policy action :ref:`configwrite`.

    :jsonparam <keyname>: configuration value to store.
    :jsonparam <keyname>.type: optional type tag — ``int``, ``string``,
        ``text``, or ``password`` (encrypted at rest).
    :jsonparam <keyname>.desc: optional human-readable description.
    :reqheader PI-Authorization: authentication token.
    :status 200: dict mapping each set key to ``"insert"`` or
        ``"update"`` in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       POST /system/setConfig HTTP/1.1
       Host: example.com
       Content-Type: application/json

       {
         "splitAtSign": true,
         "totp.hashlib": "sha1",
         "totp.hashlib.desc": "The hash algorithm used for TOTP tokens"
       }

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
            # Do not write password-typed values to the audit log in cleartext
            audit_value = CENSORED if typ == "password" else value
            g.audit_object.add_to_log({"info": f"{key!s}={audit_value!s}, "})
    g.audit_object.log({"success": True})
    return send_result(result)


@system_blueprint.route('/setDefault', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, PolicyAction.SYSTEMWRITE)
def set_default():
    """
    Set token default values that apply to newly enrolled tokens.
    Existing tokens are not affected. At least one of the listed
    parameters must be supplied.

    Requires admin authentication and the policy action :ref:`configwrite`.

    :jsonparam DefaultMaxFailCount: maximum allowed authentication
        failures before a token is locked.
    :jsonparam DefaultSyncWindow: synchronization window size.
    :jsonparam DefaultCountWindow: counter window size.
    :jsonparam DefaultOtpLen: OTP value length (typically ``6`` or ``8``).
    :jsonparam DefaultResetFailCount: whether the fail counter should be
        reset on successful authentication (``True`` / ``False``).
    :status 200: dict mapping each updated key to ``"insert"`` or
        ``"update"`` in ``result.value``.
    :status 400: none of the listed parameters was supplied.
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
    Delete a system configuration entry.

    Requires admin authentication and the policy action :ref:`configdelete`.

    :param key: path component, the configuration key to delete.
    :status 200: ``True`` on success in ``result.value``.
    """
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
    Provide the password for the configured security module (HSM /
    PKCS#11) so privacyIDEA can unlock its encryption key. Until the
    HSM is unlocked, tokens whose secrets are protected by the HSM
    cannot be used.

    Requires admin authentication and the policy action
    :ref:`policy_set_hsm_password`.

    :jsonparam password: the security-module password (required).
    :status 200: ``{"is_ready": <bool>}`` in ``result.value``;
        ``True`` if the HSM is now unlocked.
    """
    password = get_required(request.all_data, "password")
    is_ready = set_hsm_password(password)
    res = {"is_ready": is_ready}
    g.audit_object.log({'success': is_ready})
    return send_result(res)


@system_blueprint.route('/hsm', methods=['GET'])
@admin_required
@log_with(log)
def get_security_module():
    """
    Return the readiness state of the configured security module.

    Requires admin authentication.

    :status 200: ``{"is_ready": <bool>}`` in ``result.value``;
        ``True`` if the HSM is unlocked and usable.
    """
    hsm = get_hsm(require_ready=False)
    is_ready = hsm.is_ready
    res = {"is_ready": is_ready}
    g.audit_object.log({'success': is_ready})
    return send_result(res)


@system_blueprint.route('/random', methods=['GET'])
@admin_required
@prepolicy(check_base_action, request, action=PolicyAction.GETRANDOM)
@log_with(log)
def rand():
    """
    Return cryptographically random bytes from the server's RNG. Clients
    use this when seeding tokens (CLI initializing a Yubikey, WebUI
    creating a token secret) so that the secret material is sourced
    from a trusted, centrally audited generator — and, when privacyIDEA
    is configured against an HSM, from the HSM's hardware RNG.

    Requires admin authentication and the policy action
    :ref:`policy_getrandom`.

    :query len: number of random bytes to return; default ``20``.
    :query encode: encoding for the result — ``hex`` (default) or
        ``b64``.
    :status 200: the encoded random bytes in ``result.value``.
    """
    length = int(get_optional(request.all_data, "len") or 20)
    encode = get_optional(request.all_data, "encode")

    r = geturandom(length=length)
    if encode == "b64":
        res = b64encode_and_unicode(r)
    else:
        res = hexlify_and_unicode(r)

    g.audit_object.log({'success': True, 'info': f"len={length}"})
    return send_result(res)


@system_blueprint.route('/test/<tokentype>', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, action=PolicyAction.SYSTEMWRITE)
@log_with(log)
def test(tokentype=None):
    """
    Probe the server-side configuration of a given token type by
    invoking that token class' ``test_config`` classmethod with the
    request body. The shape of the body and what the test actually does
    are token-type specific (the email token, for example, sends a test
    email through the configured SMTP server).

    Requires admin authentication and the policy action :ref:`configwrite`.

    :param tokentype: path component, the token type to test
        (e.g. ``email``).
    :jsonparam: any token-type-specific configuration fields.
    :status 200: ``True`` if the configuration is valid, ``False``
        otherwise; ``detail.message`` carries a human-readable
        description.
    """
    tokenc = get_token_class(tokentype)
    res, description = tokenc.test_config(request.all_data)
    g.audit_object.log({"success": True,
                        "token_type": tokentype})
    return send_result(res, details={"message": description})


@system_blueprint.route('/names/radius', methods=['GET'])
@prepolicy(check_base_action, request, action="enrollRADIUS")
def list_radius_servers():
    """
    Return the identifiers of all configured RADIUS servers (only the
    names, not the full configurations). The WebUI uses this when
    enrolling a RADIUS token to populate the server-selection dropdown.

    Requires the enrollment policy action ``enrollRADIUS``.

    :status 200: list of RADIUS-server identifiers in ``result.value``.
    """
    server_list = get_radiusservers()
    res = [server.config.identifier for server in server_list]
    g.audit_object.log({'success': True})
    return send_result(res)


@system_blueprint.route('/names/caconnector', methods=['GET'])
@prepolicy(check_base_action, request, action="enrollCERTIFICATE")
def list_ca_connectors():
    """
    Return the configured CA connectors with their templates but
    without their connection configuration (no secrets are included).
    The WebUI uses this when enrolling a certificate token to populate
    the CA-selection dropdown and the per-CA template list.

    Requires the enrollment policy action ``enrollCERTIFICATE``.

    :status 200: list of CA-connector dictionaries (name, type,
        templates) in ``result.value``.
    """
    ca_list = get_caconnector_list(return_config=False)
    g.audit_object.log({"success": True})
    return send_result(ca_list)


@system_blueprint.route("/nodes", methods=['GET'])
@admin_required
def list_nodes():
    """
    Return the privacyIDEA nodes declared in the server configuration.
    Each entry carries the node ``name`` and ``uuid`` and is used by
    multi-node features (per-node periodic tasks, per-node resolver
    visibility, ...).

    Requires admin authentication.

    :reqheader PI-Authorization: authentication token.
    :status 200: list of ``{"name", "uuid"}`` dictionaries in
        ``result.value``.

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
             {"name": "node1", "uuid": "12345678-1234-1234-1234-1234567890ab"},
             {"name": "node2", "uuid": "12345678-4321-1234-1234-1234567890ac"}
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

    Server-certificate sources are admin-configured via two pi.cfg keys:

    * ``PI_SERVER_CERT_FILE`` - path to a cert file on disk to read.
    * ``PI_HEALTH_CERT_PROBES`` - list of ``{"host": "...", "port": int}``
      dicts naming TLS endpoints to probe over the network.

    Both are opt-in. With neither configured, only LDAP resolver entries
    are returned. The endpoint never derives probe targets from request
    headers - that would be an SSRF primitive.

    The result is cached for ``PI_CERT_CHECK_CACHE_SECONDS`` seconds
    (default 3600). Pass ``?refresh=1`` to bypass the cache.

    Each entry has a ``status`` of ``ok`` (>30 days), ``warning`` (<=30 days),
    ``critical`` (<=7 days), ``expired`` (<=0 days), or ``error`` (probe failed).

    :queryparam refresh: If truthy, bypass the cache and re-check.
    :>json list value: List of certificate status entries.
    :reqheader PI-Authorization: The authorization token
    """
    refresh = is_true(get_optional(request.all_data, "refresh"))
    # Server-cert sources are admin-configured (PI_SERVER_CERT_FILE /
    # PI_HEALTH_CERT_PROBES); never derived from the request, so a crafted
    # Host header can't be used as an SSRF primitive.
    result = get_certificate_status(refresh=refresh)
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
    Flush the user cache. The user cache speeds up repeated user-store
    lookups; flushing it forces the next lookups to hit the backing
    resolvers again. Useful after a resolver configuration change.

    Requires admin authentication.

    :reqheader PI-Authorization: authentication token.
    :status 200: ``{"status": True, "deleted": <n>}`` in ``result.value``,
        where ``n`` is the number of cache entries removed.

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": {"status": true, "deleted": 42}
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
