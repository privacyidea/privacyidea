# (c) Cornelius Kölbel, NetKnights GmbH
#
# 2016-10-23 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
#            Initial writeup
#
#
__doc__ = """
The subscriptions REST API manages subscription files for licensed
client components (e.g. RADIUS Credential Provider, Keycloak provider,
ownCloud plugin). Subscription files are YAML-encoded and cryptographically
signed by the subscription issuer; uploading them registers the
subscription, and the GET endpoint reports the current state including
remaining validity and how many tokens/users are in use.

All endpoints require admin authentication and the policy action
:ref:`policy_managesubscription`.
"""
from flask import (Blueprint, request, g)
from privacyidea.api.lib.utils import (send_result)
from privacyidea.lib.log import log_with
from privacyidea.lib.event import event
from privacyidea.lib.token import get_tokens
from privacyidea.api.lib.prepolicy import check_base_action, prepolicy
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.subscriptions import (get_subscription,
                                           get_users_with_active_tokens,
                                           delete_subscription,
                                           save_subscription)
import logging
import datetime
import yaml


log = logging.getLogger(__name__)

subscriptions_blueprint = Blueprint('subscriptions_blueprint', __name__)

@subscriptions_blueprint.route('/', methods=['GET'])
@subscriptions_blueprint.route('/<application>', methods=['GET'])
@prepolicy(check_base_action, request, action=PolicyAction.MANAGESUBSCRIPTION)
@event("subscription_get", request, g)
@log_with(log)
def api_get(application=None):
    """
    Return all subscriptions stored on this server. Each subscription is
    enriched with usage information at request time:

    * ``timedelta`` — integer, days between today and ``date_till``.
      Negative while the subscription is still valid, positive after expiry.
    * ``active_tokens`` — number of currently assigned active tokens on
      this server.
    * ``active_users`` — number of users with at least one active token.

    Requires the admin policy action :ref:`policy_managesubscription`.

    :param application: optional path component naming a single application
        (e.g. ``privacyIDEA RADIUS``); when given, the response is filtered
        to that application only.
    :status 200: list of subscription dictionaries in ``result.value``.
    """
    subscription = get_subscription(application=application)
    active_tokens = get_tokens(count=True, active=True, assigned=True)
    for sub in subscription:
        # ``timedelta`` is negative while ``date_till`` is in the future
        # (subscription still valid) and positive once it has passed.
        sub["timedelta"] = (datetime.datetime.now() - sub.get("date_till")).days
        sub["active_tokens"] = active_tokens
        sub["active_users"] = get_users_with_active_tokens()

    g.audit_object.log({'success': True})
    return send_result(subscription)


@subscriptions_blueprint.route('/', methods=['POST'])
@prepolicy(check_base_action, request, action=PolicyAction.MANAGESUBSCRIPTION)
@event("subscription_save", request, g)
@log_with(log)
def api_set():
    """
    Upload a subscription file. The request body must be ``multipart/form-data``
    with a single field named ``file`` carrying the YAML-encoded, signed
    subscription document. The signature is verified before the subscription
    is persisted; if a subscription already exists for the same
    ``application``, it is replaced.

    Requires the admin policy action :ref:`policy_managesubscription`.

    :reqheader Content-Type: must be ``multipart/form-data``.
    :formparam file: signed YAML subscription document.
    :status 200: ``True`` on success.
    """
    subscription_file = request.files['file']
    file_contents = subscription_file.read()
    subscription = yaml.safe_load(file_contents)
    r = save_subscription(subscription)
    g.audit_object.log({'success': True})
    return send_result(r)


@subscriptions_blueprint.route('/<application>', methods=['DELETE'])
@prepolicy(check_base_action, request, action=PolicyAction.MANAGESUBSCRIPTION)
@event("subscription_delete", request, g)
@log_with(log)
def api_delete(application=None):
    """
    Delete the subscription for the given application.

    Requires the admin policy action :ref:`policy_managesubscription`.

    :param application: path component naming the application whose
        subscription should be removed.
    :status 200: id of the deleted subscription, or ``-1`` if no
        subscription existed for ``application``.
    """
    r = delete_subscription(application)
    g.audit_object.log({'success': True})
    return send_result(r)

