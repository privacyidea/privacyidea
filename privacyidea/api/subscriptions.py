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
from flask import (Blueprint, request)
from privacyidea.api.lib.utils import (send_result)
from privacyidea.lib.log import log_with
from privacyidea.lib.clientapplication import (get_subscription,
                                               delete_subscription,
                                               save_subscription)
import logging
import yaml


log = logging.getLogger(__name__)

subscriptions_blueprint = Blueprint('subscriptions_blueprint', __name__)

@subscriptions_blueprint.route('/', methods=['GET'])
@subscriptions_blueprint.route('/<application>', methods=['GET'])
@log_with(log)
def api_get(application=None):
    """
    Return the subscription object as JSON.
    """
    subscription = get_subscription()
    return send_result(subscription)


@subscriptions_blueprint.route('/', methods=['POST'])
@log_with(log)
def api_set():
    """
    """
    subscription_file = request.files['file']
    file_contents = subscription_file.read()
    subscription = yaml.load(file_contents)
    r = save_subscription(subscription)
    return send_result(r)


@subscriptions_blueprint.route('/<application>', methods=['DELETE'])
@log_with(log)
def api_delete(application=None):
    """
    Create a subscription request.
    This request needs to be sent to NetKnights to create a subscription
    """
    r = delete_subscription(application)
    return send_result(r)

