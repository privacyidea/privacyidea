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
from log import log_with
from ..models import Subscription
from privacyidea.lib.error import SubscriptionError
import functools

SUBSCRIPTION_DATE_FORMAT = "%Y-%m-%d"

log = logging.getLogger(__name__)


@log_with
def save_subscription(subscription):
    """
    Saves a subscription to the database. If the subscription already exists,
    it is updated.

    :param subscription: dictionary with all attributes of the
        subscription
    :type subscription: dict
    :return: True in case of success
    """
    # TODO verify the signature of the subscriptions
    if type(subscription.get("date_from")) == str:
        subscription["date_from"] = datetime.datetime.strptime(
            subscription.get("date_from"), SUBSCRIPTION_DATE_FORMAT)
    if type(subscription.get("date_till")) == str:
        subscription["date_till"] = datetime.datetime.strptime(
            subscription.get("date_till"), SUBSCRIPTION_DATE_FORMAT)

    s = Subscription(application=subscription.get("application"),
                     for_name=subscription.get("for_name"),
                     for_address=subscription.get("for_address"),
                     for_email=subscription.get("for_email"),
                     for_phone=subscription.get("for_phone"),
                     for_url=subscription.get("for_url"),
                     for_comment=subscription.get("for_comment"),
                     by_name=subscription.get("by_name"),
                     by_email=subscription.get("by_email"),
                     by_address=subscription.get("by_addresss"),
                     by_phone=subscription.get("by_phone"),
                     by_url=subscription.get("by_url"),
                     date_from=subscription.get("date_from"),
                     date_till=subscription.get("date_till"),
                     num_users=subscription.get("num_users"),
                     num_tokens=subscription.get("num_tokens"),
                     num_clients=subscription.get("num_clients"),
                     level=subscription.get("level"),
                     signature=subscription.get("signatue")
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


@log_with
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


def check_subscription(application):
    """
    This checks if the subscription for the given application is valid.
    In case of a failure an Exception is raised.

    :param application: the name of the application to check
    :return: bool
    """
    subscriptions = get_subscription(application) or get_subscription(
        application.lower())
    if application.lower() in ["owncloud",
                               "privacyidea_credential_provider"]:
        if len(subscriptions) == 0:
            raise SubscriptionError(description="No subscription for your client.",
                                    application=application)
        else:
            subscription = subscriptions[0]
            expire = subscription.get("date_till")
            expire_date = datetime.datetime.strptime(expire, SUBSCRIPTION_DATE_FORMAT)
            if expire_date > datetime.datetime.now():
                raise SubscriptionError(description="Your subscription "
                                                    "expired.",
                                        application=application)

    return True


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
            ua_str = "{0!s}".format(ua)
            application = ua_str.split()[0]
            # check and raise if fails
            check_subscription(application)
            f_result = func(*args, **kwds)
            return f_result

        return check_subscription_wrapper
