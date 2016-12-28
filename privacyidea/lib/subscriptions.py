# -*- coding: utf-8 -*-
#
#  2016-09-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Save and delete subscriptions
#
# License:  AGPLv3
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
#
__doc__ = """Save and list subscription information.
Provide decorator to test the subscriptions.

The code is tested in tests/test_lib_subscriptions.py.
"""

import logging
import datetime
import random
from log import log_with
from ..models import Subscription
from privacyidea.lib.error import SubscriptionError
from privacyidea.lib.token import get_tokens
import functools
from flask import current_app
import os
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
import traceback


SUBSCRIPTION_DATE_FORMAT = "%Y-%m-%d"
SIGN_FORMAT = """{application}
{for_name}
{for_address}
{for_email}
{for_phone}
{for_url}
{for_comment}
{by_name}
{by_email}
{by_address}
{by_phone}
{by_url}
{date_from}
{date_till}
{num_users}
{num_tokens}
{num_clients}
{level}
"""


APPLICATIONS = {"demo_application": 0,
                "owncloud": 5,
                "privacyidea-cp": 0}

log = logging.getLogger(__name__)


@log_with(log)
def save_subscription(subscription):
    """
    Saves a subscription to the database. If the subscription already exists,
    it is updated.

    :param subscription: dictionary with all attributes of the
        subscription
    :type subscription: dict
    :return: True in case of success
    """
    if type(subscription.get("date_from")) == str:
        subscription["date_from"] = datetime.datetime.strptime(
            subscription.get("date_from"), SUBSCRIPTION_DATE_FORMAT)
    if type(subscription.get("date_till")) == str:
        subscription["date_till"] = datetime.datetime.strptime(
            subscription.get("date_till"), SUBSCRIPTION_DATE_FORMAT)

    # verify the signature of the subscriptions
    check_signature(subscription)

    s = Subscription(application=subscription.get("application"),
                     for_name=subscription.get("for_name"),
                     for_address=subscription.get("for_address"),
                     for_email=subscription.get("for_email"),
                     for_phone=subscription.get("for_phone"),
                     for_url=subscription.get("for_url"),
                     for_comment=subscription.get("for_comment"),
                     by_name=subscription.get("by_name"),
                     by_email=subscription.get("by_email"),
                     by_address=subscription.get("by_address"),
                     by_phone=subscription.get("by_phone"),
                     by_url=subscription.get("by_url"),
                     date_from=subscription.get("date_from"),
                     date_till=subscription.get("date_till"),
                     num_users=subscription.get("num_users"),
                     num_tokens=subscription.get("num_tokens"),
                     num_clients=subscription.get("num_clients"),
                     level=subscription.get("level"),
                     signature=subscription.get("signature")
                     ).save()
    return s


def get_subscription(application=None):
    """
    Return a list of subscriptions for a certai application
    If application is ommitted, all applications are returned.

    :param application: Name of the application
    :return: list of subscription dictionaries
    """
    subscriptions = []
    sql_query = Subscription.query
    if application:
        sql_query = sql_query.filter(Subscription.application == application)

    for sub in sql_query.all():
        subscriptions.append(sub.get())

    return subscriptions


@log_with(log)
def delete_subscription(application):
    """
    Delete the subscription for the given application

    :param application:
    :return: True in case of success
    """
    ret = -1
    sub = Subscription.query.filter(Subscription.application ==
                                  application).first()

    if sub:
        sub.delete()
        ret = sub.id
    return ret


def raise_exception_probability(subscription=None):
    """
    Depending on the subscription this will return True, so that an exception
    can be raised

    :param subscription: Subscription dictionary
    :return: Bool
    """
    if not subscription:
        # No subscription at all. We are in a kind of demo mode and return
        # True with a 50% chance
        return random.randrange(0, 2)

    expire = subscription.get("date_till")
    delta = datetime.datetime.now() - expire
    if delta.days > 0:
        # calculate a certain probability <1
        # After 44 days we get 50%
        # After 74 days we get 80%
        # After 94 days we get 100%
        p = 0.2 + ((delta.days-14.0)/30.0) * 0.3
        return random.random() < p

    return False


def check_subscription(application):
    """
    This checks if the subscription for the given application is valid.
    In case of a failure an Exception is raised.

    :param application: the name of the application to check
    :return: bool
    """
    subscriptions = get_subscription(application) or get_subscription(
        application.lower())
    if application.lower() in APPLICATIONS.keys():
        if len(subscriptions) == 0:
            # get the number of active assigned tokens
            num_tokens = get_tokens(assigned=True, active=True, count=True)
            if num_tokens > APPLICATIONS.get(application.lower()) \
                    and raise_exception_probability():
                raise SubscriptionError(description="No subscription for your client.",
                                        application=application)
        else:
            subscription = subscriptions[0]
            expire_date = subscription.get("date_till")
            if expire_date < datetime.datetime.now():
                # subscription has expired
                if raise_exception_probability(subscription):
                    raise SubscriptionError(description="Your subscription "
                                                        "expired.",
                                            application=application)
            else:
                # subscription is still valid, so check the signature.
                check_signature(subscription)

    return True


def check_signature(subscription):
    """
    This function checks the signature of a subscription. If the signature
    checking fails, a SignatureError / Exception is raised.

    :param subscription: The dict of the subscription
    :return: True
    """
    vendor = subscription.get("by_name").split()[0]
    enckey = current_app.config.get("PI_ENCFILE", "/etc/privacyidea/enckey")
    dirname = os.path.dirname(enckey)
    # In dirname we are searching for <vendor>.pem
    filename = "{0!s}/{1!s}.pem".format(dirname, vendor)
    with open(filename, "r") as file_handle:
        public = file_handle.read()

    r = False
    try:
        # remove the minutes 00:00:00
        subscription["date_from"] = subscription.get("date_from").strftime(SUBSCRIPTION_DATE_FORMAT)
        subscription["date_till"] = subscription.get("date_till").strftime(SUBSCRIPTION_DATE_FORMAT)
        sign_string = SIGN_FORMAT.format(**subscription)
        RSAkey = RSA.importKey(public)
        hashvalue = SHA256.new(sign_string).digest()
        signature = long(subscription.get("signature") or "100")
        r = RSAkey.verify(hashvalue, (signature,))
        subscription["date_from"] = datetime.datetime.strptime(
            subscription.get("date_from"),
            SUBSCRIPTION_DATE_FORMAT)
        subscription["date_till"] = datetime.datetime.strptime(
            subscription.get("date_till"),
            SUBSCRIPTION_DATE_FORMAT)
    except Exception as exx:
        log.debug(traceback.format_exc())
        raise SubscriptionError("Verifying the signature of your subscription "
                                "failed.",
                                application=subscription.get("application"))

    if not r:
        raise SubscriptionError("Signature of your subscription does not "
                                "match.",
                                application=subscription.get("application"))

    return r


class CheckSubscription(object):
    """
    Decorator to decorate an API request and check if the subscription is valid.
    For this, we evaluate the requesting client.
    If the subscription for this client is not valid, we raise an exception.
    """

    def __init__(self, request):
        self.request = request

    def __call__(self, func):
        @functools.wraps(func)
        def check_subscription_wrapper(*args, **kwds):
            request = self.request
            ua = request.user_agent
            ua_str = "{0!s}".format(ua) or "unknown"
            application = ua_str.split()[0]
            # check and raise if fails
            check_subscription(application)
            f_result = func(*args, **kwds)
            return f_result

        return check_subscription_wrapper
