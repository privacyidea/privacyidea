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

import datetime
import functools
import logging
import os
import random
import time
import traceback

from sqlalchemy import func, select, update

from privacyidea.lib import lazy_gettext
from privacyidea.lib.crypto import Sign
from privacyidea.lib.error import SubscriptionError
from privacyidea.lib.framework import get_app_config_value, get_app_local_store
from privacyidea.lib.token import get_tokens
from .log import log_with
from .utils import get_plugin_info_from_useragent
from ..models import Subscription, db

EXPIRE_MESSAGE = lazy_gettext("My subscription has expired.")
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
                "owncloud": 50,
                "privacyidea-nextcloud": 50,
                "privacyidea-ldap-proxy": 50,
                "privacyidea-cp": 50,
                "privacyidea-pam": 10000,
                "privacyidea-shibboleth": 10000,
                "privacyidea-adfs": 50,
                "privacyidea-keycloak": 10000,
                "simplesamlphp": 10000,
                "privacyidea-simplesamlphp": 10000,
                "privacyidea authenticator": 10,
                "privacyidea": 50}

log = logging.getLogger(__name__)


def get_users_with_active_tokens():
    """
    Returns the numbers of users (userId, Resolver) with active tokens.

    :return: Number of users
    :rtype: int
    """
    from privacyidea.models import Token, TokenOwner
    stmt = (
        select(TokenOwner.resolver, TokenOwner.user_id)
        .select_from(TokenOwner)
        .join(Token, Token.id == TokenOwner.token_id)
        .where(Token.active.is_(True))
        .distinct()
    )
    result = db.session.execute(stmt)
    rows = result.all()
    return len(rows)


# ``check_subscription`` runs on every authentication that carries a known
# plugin's user agent, and counting the users costs a DISTINCT over the whole
# tokenowner and token tables every time. The number it produces moves only when
# tokens are assigned or deactivated, and it is used to decide whether a
# subscription is exceeded - a decision that is deliberately probabilistic
# already. A short-lived count per worker is accurate enough for that and takes
# the scan off the authentication path.
_USER_COUNT_KEY = '_subscription_user_count'
_DEFAULT_COUNT_INTERVAL_SECONDS = 60


def _count_interval_seconds() -> int:
    """
    Return how many seconds the counted number of users may be reused for, or 0
    to count on every check.
    """
    raw = get_app_config_value('PI_SUBSCRIPTION_COUNT_INTERVAL', _DEFAULT_COUNT_INTERVAL_SECONDS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        log.warning(f"PI_SUBSCRIPTION_COUNT_INTERVAL is not a number ({raw!r}), "
                    f"using {_DEFAULT_COUNT_INTERVAL_SECONDS}s.")
        return _DEFAULT_COUNT_INTERVAL_SECONDS
    return max(value, 0)


def _users_with_active_tokens_for_check(allowed_users: int = None) -> int:
    """
    Return the number of users with active tokens, as the subscription check
    needs it.

    Only for the check on the authentication path. Everything that shows the
    number to somebody - the subscription overview, the statistics task - calls
    :py:func:`get_users_with_active_tokens` and gets an exact answer.

    A number kept from a previous check is only handed out while it stays within
    ``allowed_users``. The moment it would say the subscription is exceeded, the
    users are counted again, because that answer denies authentications and must
    never rest on a number that may be out of date - tokens deleted a moment ago
    would otherwise keep users locked out for the rest of the interval. Counting
    is skipped exactly when the answer is "everything is fine", which is what
    almost every request gets.

    The opposite direction is the accepted trade: a user who was given a token
    within the interval may not be counted yet. Subscription enforcement is
    probabilistic and about compliance over time, so noticing seconds later
    changes nothing.

    :param allowed_users: the number of users the subscription allows, if known
    :return: the number of users with active tokens
    """
    interval = _count_interval_seconds()
    if not interval:
        return get_users_with_active_tokens()
    store = get_app_local_store()
    counted = store.get(_USER_COUNT_KEY)
    now = time.monotonic()
    if counted is not None and now - counted[0] < interval:
        if allowed_users is None or counted[1] <= allowed_users:
            return counted[1]
    user_count = get_users_with_active_tokens()
    store[_USER_COUNT_KEY] = (now, user_count)
    return user_count


def subscription_status(component="privacyidea", tokentype=None):
    """
    Return the status of the subscription

    0: Token count <= 50
    1: Token count > 50, no subscription at all
    2: subscription expired
    3: subscription OK

    :return: subscription state
    """
    token_count = get_tokens(assigned=True, active=True, count=True, tokentype=tokentype, all_nodes=True)
    if token_count <= APPLICATIONS.get(component, 50):
        return 0

    subscriptions = get_subscription(component)
    if len(subscriptions) == 0:
        return 1

    try:
        check_subscription(component)
    except SubscriptionError as exx:
        log.warning(f"{exx}")
        return 2

    return 3


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
    if isinstance(subscription.get("date_from"), str):
        subscription["date_from"] = datetime.datetime.strptime(
            subscription.get("date_from"), SUBSCRIPTION_DATE_FORMAT)
    if isinstance(subscription.get("date_till"), str):
        subscription["date_till"] = datetime.datetime.strptime(
            subscription.get("date_till"), SUBSCRIPTION_DATE_FORMAT)

    # verify the signature of the subscriptions
    check_signature(subscription)

    stmt = select(Subscription).filter(
        Subscription.application == subscription.get("application")
    )
    subscription_db = db.session.execute(stmt).scalar_one_or_none()

    if subscription_db:
        # update existing subscription
        update_stmt = (
            update(Subscription)
            .where(Subscription.id == subscription_db.id)
            .values(**subscription)
        )
        db.session.execute(update_stmt)
    else:
        # create new subscription
        subscription_db = Subscription(application=subscription.get("application"),
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
                                       )
        db.session.add(subscription_db)
    db.session.commit()
    return subscription_db.save()


def get_subscription(application=None):
    """
    Return a list of subscriptions for a certain application
    If application is omitted, all applications are returned.

    :param application: Name of the application
    :return: list of subscription dictionaries
    """
    subscriptions = []
    stmt = select(Subscription)
    if application:
        stmt = stmt.filter(func.lower(Subscription.application) == application.lower())

    for sub in db.session.scalars(stmt).all():
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
    stmt = select(Subscription).where(Subscription.application == application)
    subscription = db.session.scalar(stmt)

    if subscription:
        subscription.delete()
        ret = subscription.id
        db.session.commit()
    return ret


def raise_exception_probability(subscription=None):
    """
    Depending on the subscription expiration data this will return True,
    so that an exception can be raised

    :param subscription: Subscription dictionary
    :return: Bool
    """
    if not subscription:
        # No subscription at all. We are in a kind of demo mode and return
        # True with a 50% chance
        # This is only for probability, so we use the less secure but faster random module
        return random.randrange(0, 2)  # nosec B311

    expire = subscription.get("date_till")
    delta = datetime.datetime.now() - expire
    if delta.days > 0:
        # calculate a certain probability <1
        # After 44 days we get 50%
        # After 74 days we get 80%
        # After 94 days we get 100%
        p = 0.2 + ((delta.days - 14.0) / 30.0) * 0.3
        # This is only for probability, so we use the less secure but faster random module
        return random.random() < p  # nosec B311

    return False


def subscription_exceeded_probability(active_tokens, allowed_tokens):
    """
    Depending on the subscription token numbers, this will return True,
    so that an exception can be raised.

    Returns true if a Subscription Exception is to be raised.

    :param active_tokens: The number of the active tokens
    :param allowed_tokens: The number of the allowed tokens
    :return:
    """
    # old, hard behaviour
    # return active_tokens > allowed_tokens
    if active_tokens > allowed_tokens:
        # This is only for probability, so we use the less secure but faster random module
        prob_check = random.randrange(active_tokens + 1)  # nosec B311
        return prob_check > allowed_tokens
    else:
        return False


def check_subscription(application, max_free_subscriptions=None):
    """
    This checks if the subscription for the given application is valid.
    In case of a failure an Exception is raised.

    :param application: the name of the application to check
    :param max_free_subscriptions: the maximum number of subscriptions
        without a subscription file. If not given, the default is used.
    :return: bool
    """
    if application.lower() in APPLICATIONS:
        subscriptions = get_subscription(application) or get_subscription(
            application.lower())
        free_subscriptions = max_free_subscriptions or APPLICATIONS.get(application.lower())
        if len(subscriptions) == 0:
            # get the number of users with active tokens
            token_users = _users_with_active_tokens_for_check(free_subscriptions)
            if subscription_exceeded_probability(token_users, free_subscriptions):
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
                allowed_tokennums = subscription.get("num_tokens")
                token_users = _users_with_active_tokens_for_check(allowed_tokennums)
                if subscription_exceeded_probability(token_users, allowed_tokennums):
                    # subscription is exceeded
                    raise SubscriptionError(description="Too many users "
                                                        "with assigned tokens. "
                                                        "Subscription exceeded.",
                                            application=application)

    return True


def check_signature(subscription):
    """
    This function checks the signature of a subscription. If the signature
    checking fails, a SignatureError / Exception is raised.

    :param subscription: The dict of the subscription
    :return: True
    """
    vendor = subscription.get("by_name").split()[0]
    enckey = get_app_config_value("PI_ENCFILE", "/etc/privacyidea/enckey")
    dirname = os.path.dirname(enckey)
    # In dirname we are searching for <vendor>.pem
    filename = f"{dirname!s}/{vendor!s}.pem"

    try:
        # remove the minutes 00:00:00
        subscription["date_from"] = subscription.get("date_from").strftime(SUBSCRIPTION_DATE_FORMAT)
        subscription["date_till"] = subscription.get("date_till").strftime(SUBSCRIPTION_DATE_FORMAT)
        sign_string = SIGN_FORMAT.format(**subscription)
        with open(filename, 'rb') as key_file:
            sign_obj = Sign(private_key=None, public_key=key_file.read())

        signature = subscription.get('signature', '100')
        r = sign_obj.verify(sign_string, signature, verify_old_sigs=True)
        subscription["date_from"] = datetime.datetime.strptime(
            subscription.get("date_from"),
            SUBSCRIPTION_DATE_FORMAT)
        subscription["date_till"] = datetime.datetime.strptime(
            subscription.get("date_till"),
            SUBSCRIPTION_DATE_FORMAT)
    except Exception as _e:
        log.debug(traceback.format_exc())
        raise SubscriptionError("Verifying the signature of your subscription "
                                "failed.",
                                application=subscription.get("application"))

    if not r:
        raise SubscriptionError("Signature of your subscription does not "
                                "match.",
                                application=subscription.get("application"))

    return r


class CheckSubscription:
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
            ua_str = str(request.user_agent.string)
            plugin_name = get_plugin_info_from_useragent(ua_str)[0]
            # check and raise if fails
            check_subscription(plugin_name)
            f_result = func(*args, **kwds)
            return f_result

        return check_subscription_wrapper
