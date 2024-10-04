from flask import Blueprint, current_app

from privacyidea.api.lib.utils import send_result
from privacyidea.lib.resolver import get_resolver_list, get_resolver_class
import logging

log = logging.getLogger(__name__)

healthz_blueprint = Blueprint('healthz_blueprint', __name__)


@healthz_blueprint.route('/', methods=['GET'])
def healthz():
    """
    Health check endpoint that indicates if the app is healthy (running and ready to serve requests).
    """
    app = current_app._get_current_object()
    if app.config.get('APP_READY'):
        return send_result({"status": "healthy"}), 200
    else:
        return send_result({"status": "not healthy"}), 503


@healthz_blueprint.route('/livez', methods=['GET'])
def livez():
    """
    Liveness check endpoint that indicates if the app is running.
    """
    return send_result("OK"), 200


@healthz_blueprint.route('/readyz', methods=['GET'])
def readyz():
    """
    Readiness check endpoint that indicates if the app is ready to serve requests.
    """
    app = current_app._get_current_object()
    if app.config.get('APP_READY'):
        return send_result({"status": "ready"}), 200
    else:
        return send_result({"status": "not ready"}), 503


@healthz_blueprint.route('/resolversz', methods=['GET'])
def resolversz():
    """
    Resolver check endpoint that tests if params will create a working resolver.
    """
    result = {
        "status": "fail",
        "ldapresolvers": {},
        "sqlresolvers": {}
    }

    try:
        ldapresolvers_list = get_resolver_list(filter_resolver_type="ldapresolver")
        sqlresolvers_list = get_resolver_list(filter_resolver_type="sqlresolver")

        result["ldapresolvers"] = check_resolvers(ldapresolvers_list)
        result["sqlresolvers"] = check_resolvers(sqlresolvers_list)
        result["status"] = "OK"
        return send_result(result), 200
    except Exception as e:
        log.debug(f"Exception in /resolversz endpoint: {e}")
        return send_result({"status": "error"}), 500


def check_resolvers(resolvers_list):
    """
    Test the connections for the given resolver list.
    Args:
        resolvers_list (list): List of resolvers to be tested.
    Returns:
        dict: Dictionary with resolver names and their statuses ("OK" or "fail").
    """
    resolvers_stats = {}

    for i, resolver_name in enumerate(resolvers_list):
        resolver_data = resolvers_list.get(resolver_name)
        resolver_class = get_resolver_class(resolver_data.get("type"))
        success, _ = resolver_class.testconnection(resolver_data.get("data"))

        resolver_status = "OK" if success else "fail"
        resolvers_stats[f"{resolver_name}"] = resolver_status

    return resolvers_stats
