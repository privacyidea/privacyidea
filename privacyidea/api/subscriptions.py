# -*- coding: utf-8 -*-
#
# (c) Cornelius Kölbel, NetKnights GmbH
#
# 2016-10-23 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
#            Initial writeup
#
#
__doc__ = """This is the controller API for client componet
subscriptions like ownCloud plugin or RADIUS Credential Provider.
"""
from flask import (Blueprint, request, g)
from privacyidea.api.lib.utils import (send_result)
from privacyidea.lib.log import log_with
from privacyidea.lib.event import event
from privacyidea.lib.token import get_tokens
from privacyidea.api.lib.prepolicy import check_base_action, prepolicy
from privacyidea.lib.policy import ACTION
from privacyidea.lib.subscriptions import (get_subscription,
                                           get_users_with_active_tokens,
                                           delete_subscription,
                                           save_subscription,
                                           SUBSCRIPTION_DATE_FORMAT)
import logging
import datetime
import yaml


log = logging.getLogger(__name__)

subscriptions_blueprint = Blueprint('subscriptions_blueprint', __name__)

@subscriptions_blueprint.route('/', methods=['GET'])
@subscriptions_blueprint.route('/<application>', methods=['GET'])
@prepolicy(check_base_action, request, action=ACTION.MANAGESUBSCRIPTION)
@event("subscription_get", request, g)
@log_with(log)
def api_get(application=None):
    """
    Return the subscription object as JSON.
    """
    subscription = get_subscription()
    active_tokens = get_tokens(count=True, active=True, assigned=True)
    for sub in subscription:
        # If subscription is valid, we have a negative timedelta
        sub["timedelta"] = (datetime.datetime.now() - sub.get("date_till")).days
        sub["active_tokens"] = active_tokens
        sub["active_users"] = get_users_with_active_tokens()

    g.audit_object.log({'success': True})
    return send_result(subscription)


@subscriptions_blueprint.route('/', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.MANAGESUBSCRIPTION)
@event("subscription_save", request, g)
@log_with(log)
def api_set():
    """
    """
    subscription_file = request.files['file']
    file_contents = subscription_file.read()
    subscription = yaml.safe_load(file_contents)
    r = save_subscription(subscription)
    g.audit_object.log({'success': True})
    return send_result(r)


@subscriptions_blueprint.route('/<application>', methods=['DELETE'])
@prepolicy(check_base_action, request, action=ACTION.MANAGESUBSCRIPTION)
@event("subscription_delete", request, g)
@log_with(log)
def api_delete(application=None):
    """
    Create a subscription request.
    This request needs to be sent to NetKnights to create a subscription
    """
    r = delete_subscription(application)
    g.audit_object.log({'success': True})
    return send_result(r)

