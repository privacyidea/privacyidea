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
"""This module is intended to ensure the application can be monitored effectively
and provide insights into whether the application and its dependencies are operational.
A primary intention was to create a way for Kubernetes to check on containers.

Endpoints:
    - `/healthz` : Combined health check for liveness and readiness.
    - `/healthz/startupz` : Startup check to confirm if the app has started.
    - `/healthz/livez` : Liveness check to verify if the app is running.
    - `/healthz/readyz` : Readiness check to confirm if the app is ready to serve requests.
    - `/healthz/resolversz` : Resolver check to test the connection to all LDAP and SQL resolvers.

The corresponding code is tested in tests/test_api_healthcheck.py.
"""
from flask import Blueprint, current_app

from privacyidea.api.lib.utils import send_result
from privacyidea.lib.crypto import get_hsm
from privacyidea.lib.resolver import get_resolver_list, get_resolver_class
import logging

log = logging.getLogger(__name__)

healthz_blueprint = Blueprint('healthz_blueprint', __name__)


@healthz_blueprint.route('/', methods=['GET'])
def healthz():
    """
    Combined health check endpoint for liveness and readiness.

    The health check verifies the liveness of the app, ensuring it is running,
    and the readiness, ensuring the app and its dependencies are ready to serve
    requests.

    :return: A tuple containing the readiness status and HTTP response code.
    :rtype: tuple
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

    :return: A tuple containing the startup status and HTTP response code.
    :rtype: tuple
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

    :return: A tuple containing the liveness status and HTTP response code.
    :rtype: tuple
    """
    return send_result({"status": "OK"}), 200


@healthz_blueprint.route('/readyz', methods=['GET'])
def readyz():
    """
    Readiness check endpoint that indicates if the app is ready to serve requests.

    The endpoint checks the readiness of the app, ensuring that the app has started
    and the HSM (Hardware Security Module) is in a ready state. If any condition is
    not met, a 503 status is returned with appropriate information.

    :return: A tuple containing the readiness status and HTTP response code.
    :rtype: tuple
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


@healthz_blueprint.route('/resolversz', methods=['GET'])
def resolversz():
    """
    Resolver check endpoint that tests the connection to all resolvers types defined in resolver_types.
    For now LDAP and SQL resolvers are tested.

    The endpoint returns a JSON object with the status of each resolver (either "OK"
    or "fail"). It attempts to establish a connection to each resolver, and if any
    exception occurs during the check, a 503 status is returned.

    :return: A tuple containing the resolver status and HTTP response code.
    :rtype: tuple
    """
    result = {}
    resolver_types = ["ldapresolver", "sqlresolver"]
    total_status = "OK"

    try:
        for resolver_type in resolver_types:
            result[resolver_type] = {}
            resolvers_list = get_resolver_list(filter_resolver_type=resolver_type)
            for resolver_name, resolver_data in resolvers_list.items():
                if resolver_data:
                    resolver_class = get_resolver_class(resolver_type)
                    success, _ = resolver_class.testconnection(resolver_data.get("data"))
                    if not success:
                        total_status = "fail"
                    result[resolver_type][resolver_name] = "OK" if success else "fail"
                else:
                    result[resolver_type][resolver_name] = "fail"

        result["status"] = total_status
        return send_result(result), 200
    except Exception as e:
        log.debug(f"Exception in /resolversz endpoint: {e}")
        return send_result({"status": "error"}), 503
