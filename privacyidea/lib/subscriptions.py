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

import concurrent.futures
import datetime
import functools
import logging
import os
import random
import traceback

import requests
from sqlalchemy import func, select, update

from privacyidea.lib import lazy_gettext
from privacyidea.lib.crypto import Sign
from privacyidea.lib.error import SubscriptionError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.token import get_tokens
from .log import log_with
from .utils import get_plugin_info_from_useragent, get_version_number
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

# Single source of truth for subscription applications. Each entry maps an
# application name to its configuration:
#   ``free_users``   the free-tier limit (users with active tokens) allowed
#                    without a subscription file.
#   ``user_agents``  optional list of additional client user-agents that are
#                    counted against this application's subscription. This lets
#                    several distinct clients (e.g. privacyidea-pam and
#                    pam-passkey) share one subscription. The application key
#                    itself is always implicitly one of its own user-agents.
# The flat lookups below (:data:`APPLICATIONS`, :data:`APPLICATION_ALIASES`)
# are derived from this dict, so adding a client to a subscription is a single
# edit here.
SUBSCRIPTIONS = {
    "demo_application": {"free_users": 0},
    "owncloud": {"free_users": 50},
    "privacyidea-nextcloud": {"free_users": 50},
    "privacyidea-ldap-proxy": {"free_users": 50},
    "privacyidea-cp": {"free_users": 50},
    "privacyidea-pam": {"free_users": 10000, "user_agents": ["pam-passkey"]},
    "privacyidea-shibboleth": {"free_users": 10000},
    "privacyidea-adfs": {"free_users": 50},
    "privacyidea-keycloak": {"free_users": 10000, "user_agents": ["entraid-via-keycloak"]},
    "simplesamlphp": {"free_users": 10000},
    "privacyidea-simplesamlphp": {"free_users": 10000},
    "privacyidea authenticator": {"free_users": 10, "user_agents": ["privacyidea-app"]},
    "privacyidea": {"free_users": 50, "user_agents": ["privacyidea-radius"]},
}

# Free-tier limit per subscription application. Derived from SUBSCRIPTIONS.
APPLICATIONS = {application: config["free_users"]
                for application, config in SUBSCRIPTIONS.items()}

# Maps a client user-agent name to the application whose subscription it counts
# against, so multiple user-agents can count towards the same subscription.
# Derived from the ``user_agents`` lists in SUBSCRIPTIONS. Keys are lower-case.
APPLICATION_ALIASES = {user_agent.lower(): application
                       for application, config in SUBSCRIPTIONS.items()
                       for user_agent in config.get("user_agents", [])}


def get_subscription_application(plugin_name):
    """
    Map a plugin user-agent name to the application whose subscription it
    counts against, following :data:`APPLICATION_ALIASES`. Names that are not
    aliases are returned lower-cased and otherwise unchanged.

    :param plugin_name: the plugin name parsed from a request's user-agent
    :type plugin_name: str
    :return: the canonical application name for subscription counting
    :rtype: str
    """
    name = (plugin_name or "").lower()
    return APPLICATION_ALIASES.get(name, name)


# Client user-agents shown on the dashboard subscription overview, each as its
# own row. Aliased user-agents (e.g. pam-passkey, entraid-via-keycloak) stay
# separate rows but resolve their subscription and free limit through their
# owning application (see :func:`get_plugin_subscription_status`). The frontend
# groups these into sections and provides the display names (see the section
# layout and ``pluginDisplayName`` in dashboardControllers.js), so this list is
# just the set of rows the backend reports a status for; order is not
# significant.
DASHBOARD_PLUGINS = [
    "privacyidea-app",
    "privacyidea-radius",
    "privacyidea-cp",
    "privacyidea-pam",
    "pam-passkey",
    "privacyidea-keycloak",
    "entraid-via-keycloak",
    "privacyidea-adfs",
    "privacyidea-shibboleth",
]

# A subscription within this many days of its end date is flagged "expiring".
EXPIRING_THRESHOLD_DAYS = 60
# A plugin seen within this many days counts as actively used.
USAGE_RECENT_DAYS = 7

# GitHub repository (``owner/repo``) hosting each dashboard client, used to look
# up the latest released version. Keyed by the dashboard application/user-agent.
# An unknown/unreachable repository or one without a published release simply
# yields no "current version" (None) — e.g. FreeRADIUS currently has no release.
GITHUB_REPOS = {
    "privacyidea": "privacyidea/privacyidea",
    "privacyidea-app": "privacyidea/pi-authenticator",
    "privacyidea-cp": "privacyidea/privacyidea-credential-provider",
    "privacyidea-pam": "privacyidea/privacyidea-pam",
    "pam-passkey": "privacyidea/pam-passkey",
    "privacyidea-keycloak": "privacyidea/keycloak-provider",
    "entraid-via-keycloak": "privacyidea/keycloak-protocolmapper-entraid",
    "privacyidea-adfs": "privacyidea/adfs-provider",
    "privacyidea-shibboleth": "privacyidea/shibboleth-plugin",
    "privacyidea-radius": "privacyidea/FreeRADIUS",
}
# These clients are distributed via OS packages / app stores rather than a
# downloadable GitHub release, so report their latest version + date but no
# link to the release page.
RELEASE_LINK_SUPPRESSED = {"privacyidea", "privacyidea-app"}
# How long to cache the latest-release lookups, and the per-request timeout.
GITHUB_VERSION_TTL = datetime.timedelta(hours=6)
GITHUB_FETCH_TIMEOUT = 3
_github_version_cache = {"fetched_at": None, "versions": {}}

log = logging.getLogger(__name__)


def _fetch_latest_release(repo):
    """
    Return ``{"version": ..., "released": ..., "url": ...}`` for the latest
    release of a GitHub ``owner/repo`` — the release tag with any leading ``v``
    stripped, the release date (``YYYY-MM-DD``) and the release page URL — or
    None if it can't be determined.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        response = requests.get(url, timeout=GITHUB_FETCH_TIMEOUT,
                                headers={"Accept": "application/vnd.github+json"})
        if response.status_code == 200:
            data = response.json()
            version = (data.get("tag_name") or "").lstrip("v")
            if not version:
                return None
            return {"version": version,
                    "released": (data.get("published_at") or "")[:10] or None,
                    "url": data.get("html_url")}
        log.info(f"GitHub returned {response.status_code} for the latest release of {repo}")
    except (requests.RequestException, ValueError) as error:
        log.info(f"Could not fetch the latest release for {repo}: {error}")
    return None


def get_latest_github_versions():
    """
    Return ``{application: {"version": ..., "released": ...} or None}`` for the
    clients in :data:`GITHUB_REPOS`. Results are fetched from GitHub
    concurrently and cached for :data:`GITHUB_VERSION_TTL`; this is best-effort,
    so unreachable or unknown repositories map to None.

    :rtype: dict
    """
    now = datetime.datetime.now()
    if (_github_version_cache["fetched_at"]
            and now - _github_version_cache["fetched_at"] < GITHUB_VERSION_TTL):
        return _github_version_cache["versions"]

    unique_repos = set(GITHUB_REPOS.values())
    version_by_repo = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(unique_repos) or 1) as executor:
        future_to_repo = {executor.submit(_fetch_latest_release, repo): repo
                          for repo in unique_repos}
        for future in concurrent.futures.as_completed(future_to_repo):
            version_by_repo[future_to_repo[future]] = future.result()

    versions = {application: version_by_repo.get(repo)
                for application, repo in GITHUB_REPOS.items()}
    # Drop the release link for clients that are not downloaded from GitHub.
    for application in RELEASE_LINK_SUPPRESSED:
        release = versions.get(application)
        if release:
            versions[application] = {**release, "url": None}
    _github_version_cache["versions"] = versions
    _github_version_cache["fetched_at"] = now
    return versions


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


def _subscription_state(subscription, now, token_users):
    """
    Classify a subscription record into a dashboard subscription state. This is
    about the subscription itself, independent of how recently the plugin was
    used (see :func:`_usage_state`).

    Possible values, with the colour the frontend maps them to:

    * ``none`` (grey) — no subscription on file.
    * ``valid`` (green) — subscription valid, not near expiry, within token limit.
    * ``expiring`` (yellow) — subscription valid but ends within
      :data:`EXPIRING_THRESHOLD_DAYS` days.
    * ``exceeded`` (yellow) — subscription valid but more users with active
      tokens than the subscription allows (``num_tokens``).
    * ``expired`` (red) — subscription ``date_till`` is in the past.

    :param subscription: the subscription dict, or None if none is on file
    :param now: the reference "now" timestamp
    :param token_users: number of users with active tokens (for the token check)
    :return: ``(state, date_till, days_left)`` — ``date_till``/``days_left`` are
        None when no subscription is on file.
    :rtype: tuple
    """
    if not subscription:
        return "none", None, None
    date_till = subscription.get("date_till")
    days_left = (date_till - now).days if date_till else None
    if date_till and date_till < now:
        return "expired", date_till, days_left
    allowed_tokens = subscription.get("num_tokens")
    if allowed_tokens is not None and token_users > allowed_tokens:
        return "exceeded", date_till, days_left
    if days_left is not None and days_left < EXPIRING_THRESHOLD_DAYS:
        return "expiring", date_till, days_left
    return "valid", date_till, days_left


def _usage_state(has_subscription, last_seen, now):
    """
    Classify whether a plugin is actively used: ``"yes"`` (green) if it has a
    subscription on file or was seen within :data:`USAGE_RECENT_DAYS` days,
    otherwise ``"no"`` (blue).

    :rtype: str
    """
    if has_subscription:
        return "yes"
    if last_seen is not None and (now - last_seen).days < USAGE_RECENT_DAYS:
        return "yes"
    return "no"


def get_plugin_subscription_status() -> list[dict]:
    """
    Return a dashboard status entry for each plugin in :data:`DASHBOARD_PLUGINS`.

    Each entry carries two independent axes:

    * ``usage`` — ``"yes"``/``"no"``; see :func:`_usage_state`.
    * ``subscription`` — one of ``none``/``valid``/``expiring``/``exceeded``/
      ``expired``; see :func:`_subscription_state`.

    Aliased user-agents (e.g. pam-passkey) keep their own row and their own
    ``last_seen`` but resolve their subscription through their owning
    application. Plugin usage is derived from the ``ClientApplication`` table by
    parsing each stored user-agent with
    :func:`~privacyidea.lib.utils.get_plugin_info_from_useragent`.

    :return: list of dicts in the order of :data:`DASHBOARD_PLUGINS`. Each dict
        has the keys ``application``, ``usage``, ``subscription``, ``last_seen``,
        ``date_till``, ``days_left`` and ``versions`` (the distinct client
        versions seen in the user-agents, newest first).
    :rtype: list[dict]
    """
    stmt = (
        select(ClientApplication.clienttype,
               func.max(ClientApplication.lastseen).label("max_lastseen"))
        .group_by(ClientApplication.clienttype)
    )
    last_seen_by_plugin: dict[str, datetime.datetime] = {}
    # Distinct client versions seen per plugin, parsed from the user-agents.
    versions_by_plugin: dict[str, set] = {}
    for clienttype, max_lastseen in db.session.execute(stmt).all():
        # MAX() can return NULL when every row for a clienttype has a NULL
        # lastseen; skip those so a later real timestamp doesn't compare
        # against None.
        if max_lastseen is None:
            continue
        plugin, version, _comment = get_plugin_info_from_useragent(clienttype)
        if not plugin:
            continue
        key = plugin.lower()
        current = last_seen_by_plugin.get(key)
        if current is None or max_lastseen > current:
            last_seen_by_plugin[key] = max_lastseen
        if version:
            versions_by_plugin.setdefault(key, set()).add(version)

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

    token_users = get_users_with_active_tokens()
    now = datetime.datetime.now()
    overview = []
    for plugin in DASHBOARD_PLUGINS:
        last_seen = last_seen_by_plugin.get(plugin.lower())
        # Aliased user-agents keep their own panel/last_seen but share the
        # owning application's subscription.
        owning_application = get_subscription_application(plugin)
        subscription = subscriptions_by_app.get(owning_application)
        state, date_till, days_left = _subscription_state(subscription, now, token_users)
        overview.append({"application": plugin,
                         "usage": _usage_state(bool(subscription), last_seen, now),
                         "subscription": state,
                         "last_seen": last_seen,
                         "date_till": date_till,
                         "days_left": days_left,
                         # Versions seen in the user-agents, newest first.
                         "versions": sorted(versions_by_plugin.get(plugin.lower(), []),
                                            reverse=True)})
    return overview


def get_server_subscription_status() -> dict:
    """
    Dashboard status entry for the privacyIDEA server itself. Same shape as
    entries from :func:`get_plugin_subscription_status` plus ``is_server: True``,
    so the frontend renders the server row without duplicating the
    classification rules.

    :rtype: dict
    """
    # Pick the row with the latest date_till for determinism when multiple
    # server subscriptions exist.
    subscriptions = sorted(get_subscription("privacyidea"),
                           key=lambda s: s.get("date_till") or datetime.datetime.min,
                           reverse=True)
    subscription = subscriptions[0] if subscriptions else None
    now = datetime.datetime.now()
    state, date_till, days_left = _subscription_state(
        subscription, now, get_users_with_active_tokens())
    return {"application": "privacyidea",
            "is_server": True,
            "usage": _usage_state(bool(subscription), None, now),
            "subscription": state,
            "last_seen": None,
            "date_till": date_till,
            "days_left": days_left,
            # The running server version (there is no user-agent for the
            # server). Truncate any PEP 440 local/dev suffix (e.g.
            # "3.13.1+gc6d73eab6.d20260602" -> "3.13.1").
            "versions": [get_version_number().split("+")[0]]}


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
    # Alias user-agents (e.g. pam-passkey) count against another application's
    # subscription; normalize before looking up the subscription and free limit.
    application = get_subscription_application(application)
    if application in APPLICATIONS:
        subscriptions = get_subscription(application)
        # get the number of users with active tokens
        token_users = get_users_with_active_tokens()
        free_subscriptions = max_free_subscriptions or APPLICATIONS.get(application)
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
