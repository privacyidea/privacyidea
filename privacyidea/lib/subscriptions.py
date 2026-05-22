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
import traceback

from sqlalchemy import func, select, update

from privacyidea.lib import lazy_gettext
from privacyidea.lib.crypto import Sign
from privacyidea.lib.error import SubscriptionError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.token import get_tokens
from .log import log_with
from .utils import get_plugin_info_from_useragent
from ..models import ClientApplication, Subscription, db

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
                "pam-passkey": 10000,
                "privacyidea-shibboleth": 10000,
                "privacyidea-adfs": 50,
                "privacyidea-keycloak": 10000,
                "simplesamlphp": 10000,
                "privacyidea-simplesamlphp": 10000,
                "privacyidea authenticator": 10,
                "privacyidea": 50}

# Plugins shown on the dashboard subscription overview. The API response
# preserves this order; the frontend re-sorts by status and uses this as
# the per-bucket tiebreaker. Display names live on the frontend (see
# ``pluginDisplayName`` in dashboardControllers.js).
DASHBOARD_PLUGINS = [
    "privacyidea-cp",
    "privacyidea-adfs",
    "privacyidea-pam",
    "pam-passkey",
    "privacyidea-shibboleth",
    "privacyidea-keycloak",
]

EXPIRING_THRESHOLD_DAYS = 30

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


def _classify_subscription_date(
        date_till: datetime.datetime,
        now: datetime.datetime) -> tuple[str, int]:
    """
    Map a subscription's ``date_till`` to a dashboard status. The caller is
    responsible for handling the "no subscription on file" case before
    calling this helper.

    :return: ``(status, days_left)`` where status is one of ``"active"``,
        ``"expiring"`` or ``"expired"``, and ``days_left`` is the integer
        day delta (negative when expired).
    """
    days_left = (date_till - now).days
    if date_till < now:
        return "expired", days_left
    if days_left < EXPIRING_THRESHOLD_DAYS:
        return "expiring", days_left
    return "active", days_left


def get_plugin_subscription_status() -> list[dict]:
    """
    Return a dashboard status entry for each plugin in :data:`DASHBOARD_PLUGINS`.

    Each entry has a ``status`` field. Possible values, with the colour the
    frontend dashboard maps them to:

    * ``active`` (green) — used, valid subscription, at least
      :data:`EXPIRING_THRESHOLD_DAYS` days left.
    * ``expiring`` (orange) — used, valid subscription, within
      :data:`EXPIRING_THRESHOLD_DAYS` days of expiry.
    * ``expired`` (red) — used, subscription exists but ``date_till`` is in
      the past. Distinct from ``no_subscription`` so the dashboard can
      surface former customers whose subscription lapsed.
    * ``no_subscription`` (orange) — used, no subscription on file, token-user
      count still within the free limit from :data:`APPLICATIONS`.
    * ``exceeded`` (red) — used, no subscription on file, token-user count
      exceeds the free limit.
    * ``unused`` (grey) — plugin has not contacted this server.

    Plugin usage is derived from the ``ClientApplication`` table by parsing
    each stored user-agent string with
    :func:`~privacyidea.lib.utils.get_plugin_info_from_useragent`.

    :return: list of dicts in the order of :data:`DASHBOARD_PLUGINS`. Each
        dict has the keys ``application``, ``status``, ``last_seen``,
        ``date_till`` and ``days_left``.
    :rtype: list[dict]
    """
    stmt = (
        select(ClientApplication.clienttype,
               func.max(ClientApplication.lastseen).label("max_lastseen"))
        .group_by(ClientApplication.clienttype)
    )
    last_seen_by_plugin: dict[str, datetime.datetime] = {}
    for clienttype, max_lastseen in db.session.execute(stmt).all():
        # MAX() can return NULL when every row for a clienttype has a NULL
        # lastseen; skip those so a later real timestamp doesn't compare
        # against None.
        if max_lastseen is None:
            continue
        plugin = get_plugin_info_from_useragent(clienttype)[0]
        if not plugin:
            continue
        key = plugin.lower()
        current = last_seen_by_plugin.get(key)
        if current is None or max_lastseen > current:
            last_seen_by_plugin[key] = max_lastseen

    # Batch-load every subscription once instead of per-plugin lookups.
    # Sort by date_till ascending so that, when multiple rows exist for the
    # same application, the dict ends up keyed to the row with the latest
    # date_till — deterministic regardless of DB iteration order.
    all_subscriptions = sorted(get_subscription(),
                               key=lambda s: s.get("date_till") or datetime.datetime.min)
    # Subscription.application is nullable and Subscription.get() omits None
    # fields, so a row with application=NULL has no "application" key.
    subscriptions_by_app = {sub["application"].lower(): sub
                            for sub in all_subscriptions
                            if sub.get("application")}

    # Lazily computed — only the no_subscription/exceeded branch needs it.
    token_users: int | None = None
    now = datetime.datetime.now()
    overview = []
    for plugin in DASHBOARD_PLUGINS:
        entry = {"application": plugin,
                 "last_seen": last_seen_by_plugin.get(plugin.lower()),
                 "date_till": None,
                 "days_left": None,
                 "status": "unused"}
        if entry["last_seen"] is None:
            overview.append(entry)
            continue

        subscription = subscriptions_by_app.get(plugin.lower())
        date_till = subscription.get("date_till") if subscription else None
        if date_till:
            status, days_left = _classify_subscription_date(date_till, now)
            entry["date_till"] = date_till
            entry["days_left"] = days_left
            entry["status"] = status
        else:
            if token_users is None:
                token_users = get_users_with_active_tokens()
            free_limit = APPLICATIONS[plugin.lower()]
            entry["status"] = "exceeded" if token_users > free_limit else "no_subscription"
        overview.append(entry)
    return overview


def get_server_subscription_status() -> dict:
    """
    Dashboard status entry for the privacyIDEA server itself. Same shape as
    entries from :func:`get_plugin_subscription_status` plus ``is_server: True``.
    Lets the frontend render the server row without duplicating the
    :data:`EXPIRING_THRESHOLD_DAYS` rule.

    :rtype: dict
    """
    entry = {"application": "privacyidea",
             "is_server": True,
             "last_seen": None,
             "date_till": None,
             "days_left": None,
             "status": "no_subscription"}
    # Pick the row with the latest date_till for determinism when multiple
    # server subscriptions exist.
    subscriptions = sorted(get_subscription("privacyidea"),
                           key=lambda s: s.get("date_till") or datetime.datetime.min,
                           reverse=True)
    subscription = subscriptions[0] if subscriptions else None
    date_till = subscription.get("date_till") if subscription else None
    if date_till:
        status, days_left = _classify_subscription_date(date_till, datetime.datetime.now())
        entry["date_till"] = date_till
        entry["days_left"] = days_left
        entry["status"] = status
    return entry


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
        # get the number of users with active tokens
        token_users = get_users_with_active_tokens()
        free_subscriptions = max_free_subscriptions or APPLICATIONS.get(application.lower())
        if len(subscriptions) == 0:
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
