# (c) NetKnights GmbH 2024,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2024 Henrik Falk <henrik.falk@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
"""
The healthcheck REST API exposes liveness, readiness and resolver
connectivity probes intended for orchestrators (Kubernetes, Docker
health checks, monitoring systems).

Endpoints:
    - :http:get:`/healthz/` : Combined health check for liveness and readiness.
    - :http:get:`/healthz/startupz` : Startup check to confirm if the app has started.
    - :http:get:`/healthz/livez` : Liveness check to verify if the app is running.
    - :http:get:`/healthz/readyz` : Readiness check to confirm if the app is ready to serve requests.
    - :http:get:`/healthz/resolversz` : Resolver check that tests the connection to all LDAP and SQL resolvers.

The endpoints are anonymous so that orchestrators can probe them without
credentials. ``/healthz/resolversz`` returns the overall resolver-connectivity
``status`` to anyone, but reveals the individual resolver names only to an
authenticated administrator. Because the ``/healthz`` endpoints expose
information about this server without authentication, they should be reachable
only from a trusted network and not exposed to untrusted clients.
"""
from flask import Blueprint, current_app, g

from privacyidea.api.auth import check_auth_token
from privacyidea.api.lib.utils import send_result
from privacyidea.lib.auth import ROLE
from privacyidea.lib.crypto import get_hsm
from privacyidea.lib.error import AuthError, Error
from privacyidea.lib.policy import Match, SCOPE, PolicyAction
from privacyidea.lib.resolver import get_resolver_list, get_resolver_class
import logging
import time

log = logging.getLogger(__name__)

healthz_blueprint = Blueprint('healthz_blueprint', __name__)


@healthz_blueprint.route('/', methods=['GET'])
def healthz():
    """
    Combined health check endpoint for liveness and readiness.

    The health check verifies the liveness of the app, ensuring it is running,
    and the readiness, ensuring the app and its dependencies are ready to serve
    requests.

    :resheader Content-Type: application/json
    :status 200: Application is live and ready.
    :status 503: Application is live but not ready.

   **Example Request**:

   .. sourcecode:: http

      GET /healthz HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "status": "ready",
          "hsm": "OK"
      }
    """
    livez_status, livez_code = livez()
    if livez_code != 200:
        return livez_status, livez_code

    readyz_status, readyz_code = readyz()
    return readyz_status, readyz_code


@healthz_blueprint.route('/startupz', methods=['GET'])
def startupz():
    """
    Startup check endpoint that indicates if the app has started.

    This endpoint returns a status of "started" if the app is initialized and
    running, otherwise it returns "not started" with an HTTP status code of 503.

    :resheader Content-Type: application/json
    :status 200: Application has started.
    :status 503: Application has not started yet.

   **Example Request**:

   .. sourcecode:: http

      GET /healthz/startupz HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "status": "started"
      }
    """
    if current_app.config.get('APP_READY'):
        return send_result({"status": "started"}), 200
    else:
        return send_result({"status": "not started"}), 503


@healthz_blueprint.route('/livez', methods=['GET'])
def livez():
    """
    Liveness check endpoint that indicates if the app is running.

    This endpoint returns an HTTP status 200 and a JSON object indicating that
    the application is live and running.

    :resheader Content-Type: application/json
    :status 200: Application is live.

   **Example Request**:

   .. sourcecode:: http

      GET /healthz/livez HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "status": "OK"
      }
    """
    return send_result({"status": "OK"}), 200


@healthz_blueprint.route('/readyz', methods=['GET'])
def readyz():
    """
    Readiness check endpoint that indicates if the app is ready to serve requests.

    The endpoint checks the readiness of the app, ensuring that the app has started
    and the HSM (Hardware Security Module) is in a ready state. If any condition is
    not met, a 503 status is returned with appropriate information.

    :resheader Content-Type: application/json
    :status 200: Application is ready.
    :status 503: Application is not ready or HSM is not ready.

   **Example Request**:

   .. sourcecode:: http

      GET /healthz/readyz HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "status": "ready",
          "hsm": "OK"
      }
    """
    if not current_app.config.get('APP_READY'):
        return send_result({"status": "not ready",
                            "hsm": "unchecked"}), 503
    elif not get_hsm().is_ready:
        return send_result({"status": "not ready",
                            "hsm": "fail"}), 503
    else:
        return send_result({"status": "ready",
                            "hsm": "OK"}), 200


# Probing every resolver opens a connection to each configured LDAP/SQL backend,
# so the result is cached for PI_HEALTHZ_RESOLVER_CACHE_SECONDS (default 10; 0
# disables). This bounds how often repeated probe hits — or abusive anonymous
# requests — re-connect to every backend.
_resolver_probe_cache = {"snapshot": None}  # snapshot = (monotonic_ts, status, details)


def _probe_resolvers():
    """Probe every LDAP and SQL resolver, with a short result cache.

    :return: a tuple ``(total_status, details)`` where ``total_status`` is
        ``"OK"``/``"fail"`` and ``details`` maps each resolver type to
        ``{resolver_name: "OK"/"fail"}``. Recomputed at most once per
        ``PI_HEALTHZ_RESOLVER_CACHE_SECONDS``.
    """
    cache_seconds = int(current_app.config.get("PI_HEALTHZ_RESOLVER_CACHE_SECONDS", 10))
    snapshot = _resolver_probe_cache["snapshot"]
    if snapshot is not None and (time.monotonic() - snapshot[0]) < cache_seconds:
        return snapshot[1], snapshot[2]

    details = {}
    total_status = "OK"
    for resolver_type in ("ldapresolver", "sqlresolver"):
        resolver_status = {}
        for resolver_name, resolver_data in get_resolver_list(filter_resolver_type=resolver_type).items():
            if resolver_data:
                success, _ = get_resolver_class(resolver_type).testconnection(resolver_data.get("data"))
                if not success:
                    total_status = "fail"
                resolver_status[resolver_name] = "OK" if success else "fail"
            else:
                resolver_status[resolver_name] = "fail"
        details[resolver_type] = resolver_status

    _resolver_probe_cache["snapshot"] = (time.monotonic(), total_status, details)
    return total_status, details


@healthz_blueprint.route('/resolversz', methods=['GET'])
def resolversz():
    """
    Test connectivity to every configured LDAP and SQL resolver.

    The endpoint tries to open a connection to each resolver, returning
    ``OK`` for resolvers that respond and ``fail`` for those that don't.
    The top-level ``status`` field is ``OK`` if every resolver responded,
    ``fail`` if any resolver failed, or ``error`` if an unexpected
    exception aborted the probe.

    The endpoint is anonymous so that orchestrators (Kubernetes, Docker,
    monitoring) can poll it without credentials: an unauthenticated caller
    receives the overall ``status`` only. The individual resolver names are
    returned solely to an authenticated administrator, so they are never
    disclosed to anonymous callers. If the
    ``require_auth_for_resolver_details`` policy (scope ``authz``) is set, a
    *present* but invalid or non-admin token is rejected with ``401`` instead of
    being treated as anonymous; a request without an Authorization header is
    still served the status. The probe result is cached for
    ``PI_HEALTHZ_RESOLVER_CACHE_SECONDS`` seconds (default 10; set to 0 to
    disable), so frequent or repeated calls do not re-open a connection to every
    backend each time.

    .. note::
       The ``/healthz`` endpoints expose information about this server without
       authentication, so they should be reachable only from a trusted network
       (the orchestrator / monitoring network) and not exposed to untrusted
       clients. A dedicated operational guide for deploying and securing these
       probes is planned.

    :resheader Content-Type: application/json
    :status 200: probe completed; result in the body — the per-resolver names
        are included only for an authenticated administrator.
    :status 401: the ``require_auth_for_resolver_details`` policy is set and the
        request carried a present but invalid or non-admin token.
    :status 503: an unexpected exception aborted the probe.

    **Example Request**:

    .. sourcecode:: http

       GET /healthz/resolversz HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example Response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "status": "OK",
         "ldapresolver": {
           "ldapresolver1": "OK",
           "ldapresolver2": "OK"
         },
         "sqlresolver": {
           "sqlresolver1": "OK",
           "sqlresolver2": "OK"
         }
       }
    """
    # Resolver NAMES are only ever returned to an authenticated admin; everyone
    # else gets the overall status only. The require_auth_for_resolver_details
    # policy (SCOPE.AUTHZ) additionally controls whether a *present* but invalid
    # token is rejected with 401 (legacy behavior). All combinations:
    #
    #   caller                 policy off          policy on
    #   valid admin token      200 + names         200 + names
    #   no Authorization hdr   200, status only    200, status only
    #   invalid/expired token  200, status only    401
    #   valid non-admin token  200, status only    401
    #
    # So names are always admin-only (the secure default, no policy needed); the
    # policy only re-adds the 401 for a present-but-unusable token, while a
    # header-less probe stays anonymous (status only) either way.
    require_auth = Match.action_only(g, scope=SCOPE.AUTHZ,
                                     action=PolicyAction.REQUIRE_AUTH_FOR_RESOLVER_DETAILS).any()
    authenticated = False
    try:
        check_auth_token(required_role=[ROLE.ADMIN])
        authenticated = True
    except AuthError as e:
        # With the policy on, reject a present-but-invalid / non-admin token (401)
        # but still treat a missing Authorization header as anonymous — this is the
        # pre-3.13.2 behavior. With the policy off, any failure is anonymous.
        if require_auth and e.id != Error.AUTHENTICATE_AUTH_HEADER:
            raise
        authenticated = False

    try:
        total_status, resolver_details = _probe_resolvers()
        result = {"status": total_status}
        if authenticated:
            result.update(resolver_details)
        return send_result(result), 200

    except Exception as e:
        log.debug(f"Exception in /resolversz endpoint: {e}")
        return send_result({"status": "error"}), 503
