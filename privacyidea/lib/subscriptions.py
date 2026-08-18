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
import dataclasses
import datetime
import enum
import functools
import json
import logging
import os
import random
import traceback

import requests
from sqlalchemy import func, select, update

from privacyidea.lib import lazy_gettext
from privacyidea.lib.config import get_from_config, set_privacyidea_config
from privacyidea.lib.crypto import Sign
from privacyidea.lib.error import SubscriptionError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.token import get_tokens
from .log import log_with
from .utils import get_plugin_info_from_useragent, get_version_number, is_true
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
#                    *metered* against this application's subscription, so
#                    several distinct clients (e.g. privacyidea-pam and
#                    pam-passkey) can share one subscription. The application key
#                    itself is always implicitly one of its own user-agents.
#   ``clients``      optional list of client user-agents that belong to this
#                    application but are never metered. Their use is recorded and
#                    the dashboard shows them under this application's
#                    subscription, but they can always authenticate.
# The flat lookups below (:data:`APPLICATIONS`, :data:`METERED_APPLICATIONS`,
# :data:`SUBSCRIPTION_OWNERS`) are derived from this dict, so attaching a client to
# a subscription is a single edit here.
SUBSCRIPTIONS = {
    "demo_application": {"free_users": 0},
    "owncloud": {"free_users": 50},
    "privacyidea-nextcloud": {"free_users": 50},
    "privacyidea-ldap-proxy": {"free_users": 50},
    "privacyidea-cp": {"free_users": 50},
    # The PAM module identifies itself as "PAM"; privacyidea-pam stays an accepted alias
    # of the same subscription for anything that sends the older name.
    "privacyidea-pam": {"free_users": 10000, "user_agents": ["pam", "pam-passkey"]},
    "privacyidea-shibboleth": {"free_users": 10000},
    "privacyidea-adfs": {"free_users": 50},
    "privacyidea-keycloak": {"free_users": 10000, "user_agents": ["entraid-via-keycloak"]},
    "simplesamlphp": {"free_users": 10000},
    "privacyidea-simplesamlphp": {"free_users": 10000},
    # The Authenticator App is free to use: it is recorded and reported on the
    # dashboard, but its authentications never count against a subscription.
    "privacyidea authenticator": {"free_users": 10, "clients": ["privacyidea-app"]},
    # FreeRADIUS is covered by the server's own subscription and counts against the
    # same free tier, so RADIUS traffic is metered exactly like the server itself.
    "privacyidea": {"free_users": 50, "user_agents": ["FreeRADIUS"]},
}

# Application and user-agent names are matched case-insensitively: clients spell their
# user-agent however they like, so the lookups derived from SUBSCRIPTIONS are keyed and
# valued lower-case, and every name entering them is lower-cased first.

# Free-tier limit per subscription application. Derived from SUBSCRIPTIONS.
APPLICATIONS = {application.lower(): config["free_users"]
                for application, config in SUBSCRIPTIONS.items()}

# Maps a client user-agent to the application whose subscription and free tier it is
# metered against. Only the ``user_agents`` lists: a client missing here is never
# metered, whatever its application's free tier says.
METERED_APPLICATIONS = {user_agent.lower(): application.lower()
                        for application, config in SUBSCRIPTIONS.items()
                        for user_agent in config.get("user_agents", [])}

# Maps a client user-agent to the application whose subscription record describes it, for
# the dashboard overview. Unlike METERED_APPLICATIONS this includes the unmetered
# ``clients``, so an unmetered client still shows its application's subscription.
SUBSCRIPTION_OWNERS = {**METERED_APPLICATIONS,
                       **{client.lower(): application.lower()
                          for application, config in SUBSCRIPTIONS.items()
                          for client in config.get("clients", [])}}


def get_metered_application(plugin_name: str) -> str:
    """
    Map a client user-agent to the application whose subscription and free tier its
    authentications are counted against, following :data:`METERED_APPLICATIONS`. The
    result is always lower-case: a metered client resolves to its application, any other
    name is returned unchanged apart from the case — and a name that is no application
    of its own is not metered at all (see :func:`check_subscription`).

    :param plugin_name: the plugin name parsed from a request's user-agent
    :return: the application name to meter this client against
    """
    name = (plugin_name or "").lower()
    return METERED_APPLICATIONS.get(name, name)


def get_subscription_owner(plugin_name: str) -> str:
    """
    Map a client user-agent to the application whose subscription record describes it,
    following :data:`SUBSCRIPTION_OWNERS`. This is what the dashboard overview shows and
    it says nothing about metering: an unmetered client such as the Authenticator App
    still reports the state of its application's subscription.

    :param plugin_name: the client user-agent name
    :return: the application name whose subscription describes this client
    """
    name = (plugin_name or "").lower()
    return SUBSCRIPTION_OWNERS.get(name, name)


# Client user-agents shown on the dashboard subscription overview, each as its
# own row. These are the names the clients really send. A client that belongs to
# another application (e.g. pam-passkey, entraid-via-keycloak, or the Authenticator
# App) keeps its own row but reports that application's subscription, whether or not
# it is metered against it (see :func:`get_plugin_subscription_status`). The frontend
# groups these into sections and provides the display names (see the section
# layout and ``pluginDisplayName`` in dashboardControllers.js), so this list is
# just the set of rows the backend reports a status for; order is not
# significant.
DASHBOARD_PLUGINS = [
    "privacyidea-app",
    "freeradius",
    "privacyidea-nextcloud",
    "privacyidea-cp",
    "pam",
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
    "pam": "privacyidea/privacyidea-pam",
    "pam-passkey": "privacyidea/pam-passkey",
    "privacyidea-keycloak": "privacyidea/keycloak-provider",
    "entraid-via-keycloak": "privacyidea/keycloak-protocolmapper-entraid",
    "privacyidea-adfs": "privacyidea/adfs-provider",
    "privacyidea-shibboleth": "privacyidea/shibboleth-plugin",
    "freeradius": "privacyidea/FreeRADIUS",
    "privacyidea-nextcloud": "privacyidea/privacyidea-nextcloud-app",
}
# These clients are distributed via OS packages / app stores rather than a
# downloadable GitHub release, so report their latest version + date but no
# link to the release page.
RELEASE_LINK_SUPPRESSED = {"privacyidea", "privacyidea-app"}
# How long to cache the latest-release lookups, and the per-request timeout.
GITHUB_VERSION_TTL = datetime.timedelta(hours=6)
# A lookup that produced no release at all is kept for much less time: that is what a
# network problem or GitHub's rate limit looks like, and holding on to it for the full TTL
# would leave the column empty for hours after a single blip. A lookup that produced some
# releases is kept for the full TTL, so a client without a published release does not put
# the whole cache on a short retry cycle.
GITHUB_VERSION_FAILURE_TTL = datetime.timedelta(minutes=30)
GITHUB_FETCH_TIMEOUT = 3
# The lookups are also cached in the config table, so a worker with a cold cache picks up
# another worker's result instead of calling GitHub itself. Without that, every worker of
# every node looks the versions up on its own, which both repeats the fetch latency and
# runs a multi-worker installation into GitHub's unauthenticated rate limit.
GITHUB_VERSION_CONFIG_KEY = "subscription.latest_releases"
# Length of the config table's value column. The payload is about 1.6k for the clients
# reported today; should a future one push it past the limit, the shared cache is skipped
# instead of failing the request, and each worker falls back to its own lookup.
CONFIG_VALUE_LENGTH = 2000

log = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class GithubRelease:
    """The latest release of a client as published on GitHub."""
    # Release tag with any leading "v" stripped, e.g. "3.13.1".
    version: str
    # Release date as YYYY-MM-DD, None if GitHub did not report one.
    released: str | None = None
    # Release page, None for clients that are not downloaded from GitHub.
    url: str | None = None


def _releases_are_fresh(fetched_at: datetime.datetime | None,
                        releases: dict[str, GithubRelease | None],
                        now: datetime.datetime) -> bool:
    """
    Whether a lookup made at ``fetched_at`` may still be used: the full
    :data:`GITHUB_VERSION_TTL` once it found any release, the shorter
    :data:`GITHUB_VERSION_FAILURE_TTL` if it found none at all.
    """
    if fetched_at is None:
        return False
    ttl = GITHUB_VERSION_TTL if any(releases.values()) else GITHUB_VERSION_FAILURE_TTL
    return now - fetched_at < ttl


@dataclasses.dataclass
class _GithubVersionCache:
    """Process-local cache of the latest-release lookups, in front of the shared one."""
    fetched_at: datetime.datetime | None = None
    releases: dict[str, GithubRelease | None] = dataclasses.field(default_factory=dict)

    def is_valid(self, now: datetime.datetime) -> bool:
        return _releases_are_fresh(self.fetched_at, self.releases, now)

    def store(self, fetched_at: datetime.datetime, releases: dict[str, GithubRelease | None]) -> None:
        self.fetched_at = fetched_at
        self.releases = releases


_github_version_cache = _GithubVersionCache()


def invalidate_github_version_cache() -> None:
    """Drop the cached lookups, process-local and shared. For tests and a manual refresh."""
    _github_version_cache.store(None, {})
    set_privacyidea_config(GITHUB_VERSION_CONFIG_KEY, "")


def _store_shared_releases(fetched_at: datetime.datetime,
                           releases: dict[str, GithubRelease | None]) -> None:
    """
    Publish a lookup to the config table for the other workers. Best-effort: a payload
    that does not fit the value column is not stored, leaving every worker with its own
    process-local cache.
    """
    payload = json.dumps({"fetched_at": fetched_at.isoformat(),
                          "releases": {application: dataclasses.asdict(release) if release else None
                                       for application, release in releases.items()}},
                         separators=(",", ":"))
    if len(payload) > CONFIG_VALUE_LENGTH:
        log.debug(f"Not sharing the latest releases between workers: {len(payload)} characters "
                  f"exceed the {CONFIG_VALUE_LENGTH} the config value holds.")
        return
    set_privacyidea_config(GITHUB_VERSION_CONFIG_KEY, payload,
                           desc="Latest released client versions, cached from GitHub")


def _load_shared_releases() -> tuple[datetime.datetime | None, dict[str, GithubRelease | None]]:
    """
    Read the lookup another worker published, as ``(fetched_at, releases)``. Anything
    unreadable is treated as no cache at all, so it is fetched again.
    """
    payload = get_from_config(GITHUB_VERSION_CONFIG_KEY)
    if not payload:
        return None, {}
    try:
        stored = json.loads(payload)
        fetched_at = datetime.datetime.fromisoformat(stored["fetched_at"])
        releases = {application: GithubRelease(**release) if release else None
                    for application, release in stored["releases"].items()}
    except (ValueError, TypeError, KeyError) as error:
        log.debug(f"Ignoring the shared latest-release cache, it cannot be read: {error}")
        return None, {}
    return fetched_at, releases


def version_check_enabled() -> bool:
    """
    Whether the latest released versions of the clients may be looked up on GitHub. Set
    ``PI_SUBSCRIPTION_VERSION_CHECK = False`` in pi.cfg to switch the lookup off, e.g. in
    air-gapped installations where it can never succeed and would only cost the timeout.
    """
    return is_true(get_app_config_value("PI_SUBSCRIPTION_VERSION_CHECK", True))


def _fetch_latest_release(repo: str) -> GithubRelease | None:
    """
    Return the latest :class:`GithubRelease` of a GitHub ``owner/repo``, or None if it
    can't be determined. Failures are logged at debug level only: not reaching GitHub is
    an expected state in installations without internet access.
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
            return GithubRelease(version=version,
                                 released=(data.get("published_at") or "")[:10] or None,
                                 url=data.get("html_url"))
        log.debug(f"GitHub returned {response.status_code} for the latest release of {repo}")
    except (requests.RequestException, ValueError) as error:
        log.debug(f"Could not fetch the latest release for {repo}: {error}")
    return None


def get_latest_github_versions() -> dict[str, GithubRelease | None]:
    """
    Return ``{application: GithubRelease or None}`` for the clients in
    :data:`GITHUB_REPOS`. Results are fetched from GitHub concurrently and cached for
    :data:`GITHUB_VERSION_TTL`; this is best-effort, so unreachable or unknown
    repositories map to None.

    Results are cached twice: process-local, and in the config table so the other workers
    reuse the same lookup (see :data:`GITHUB_VERSION_CONFIG_KEY`). A failed lookup is
    cached too, so a server that cannot reach GitHub does not retry on every dashboard
    load, but only for :data:`GITHUB_VERSION_FAILURE_TTL` — see
    :func:`version_check_enabled` to switch the lookup off entirely.
    """
    if not version_check_enabled():
        return {application: None for application in GITHUB_REPOS}

    now = datetime.datetime.now()
    if _github_version_cache.is_valid(now):
        return _github_version_cache.releases

    # Another worker may have looked them up already.
    shared_fetched_at, shared_releases = _load_shared_releases()
    if _releases_are_fresh(shared_fetched_at, shared_releases, now):
        _github_version_cache.store(shared_fetched_at, shared_releases)
        return shared_releases

    unique_repos = set(GITHUB_REPOS.values())
    release_by_repo = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(unique_repos) or 1) as executor:
        future_to_repo = {executor.submit(_fetch_latest_release, repo): repo
                          for repo in unique_repos}
        for future in concurrent.futures.as_completed(future_to_repo):
            release_by_repo[future_to_repo[future]] = future.result()

    releases = {application: release_by_repo.get(repo)
                for application, repo in GITHUB_REPOS.items()}
    # Drop the release link for clients that are not downloaded from GitHub.
    for application in RELEASE_LINK_SUPPRESSED:
        release = releases.get(application)
        if release:
            releases[application] = dataclasses.replace(release, url=None)
    _github_version_cache.store(now, releases)
    _store_shared_releases(now, releases)
    return releases


def version_sort_key(version: str) -> tuple:
    """
    Sort key ordering version strings by number instead of by character, so that 1.10.0
    comes after 1.9.0. A part that is not a number sorts after any number in the same
    position, which keeps the order total for whatever a client puts in its user-agent.

    :param version: a version string such as "3.8.0.0"
    :return: a tuple to sort by
    """
    return tuple((0, int(part)) if part.isdigit() else (1, part)
                 for part in version.split("."))


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


class SubscriptionState(str, enum.Enum):
    """
    State of a subscription record, with the colour the dashboard maps it to. This is
    about the subscription itself, independent of how recently the client was used.
    Inherits from str so the members serialize as their value in an API response.
    """
    # No subscription on file.
    NONE = "none"                # grey
    # Subscription valid, not near expiry, within the token limit.
    VALID = "valid"              # green
    # Valid but ends within EXPIRING_THRESHOLD_DAYS days.
    EXPIRING = "expiring"        # yellow
    # Valid but more users with active tokens than the subscription allows.
    EXCEEDED = "exceeded"        # yellow
    # The subscription's date_till is in the past.
    EXPIRED = "expired"          # red


@dataclasses.dataclass(frozen=True)
class SubscriptionStateInfo:
    """How a subscription record was classified, plus the dates the dashboard shows."""
    # The classification, see SubscriptionState.
    state: SubscriptionState
    # End date of the subscription, None if none is on file.
    date_till: datetime.datetime | None = None
    # Days until date_till, negative once it has passed; None if none is on file.
    days_left: int | None = None


def _subscription_state(subscription: dict | None, now: datetime.datetime,
                        token_users: int) -> SubscriptionStateInfo:
    """
    Classify a subscription record into a dashboard :class:`SubscriptionState`.

    :param subscription: the subscription dict, or None if none is on file
    :param now: the reference "now" timestamp
    :param token_users: number of users with active tokens (for the token check)
    :return: the classification and the dates belonging to it
    """
    if not subscription:
        return SubscriptionStateInfo(SubscriptionState.NONE)
    date_till = subscription.get("date_till")
    if not date_till:
        # Subscription.date_till is nullable. Without an end date the record cannot be
        # said to cover anything, so it is reported like an expired one rather than
        # staying green forever.
        return SubscriptionStateInfo(SubscriptionState.EXPIRED)
    days_left = (date_till - now).days
    if date_till < now:
        return SubscriptionStateInfo(SubscriptionState.EXPIRED, date_till, days_left)
    allowed_tokens = subscription.get("num_tokens")
    if allowed_tokens is not None and token_users > allowed_tokens:
        return SubscriptionStateInfo(SubscriptionState.EXCEEDED, date_till, days_left)
    if days_left < EXPIRING_THRESHOLD_DAYS:
        return SubscriptionStateInfo(SubscriptionState.EXPIRING, date_till, days_left)
    return SubscriptionStateInfo(SubscriptionState.VALID, date_till, days_left)


def _is_in_use(has_subscription: bool, last_seen: datetime.datetime | None,
               now: datetime.datetime) -> bool:
    """
    Whether a client counts as actively used: it has a subscription on file or was seen
    within :data:`USAGE_RECENT_DAYS` days.
    """
    if has_subscription:
        return True
    return last_seen is not None and (now - last_seen).days < USAGE_RECENT_DAYS


def get_plugin_subscription_status(token_users: int | None = None) -> list[dict]:
    """
    Return a dashboard status entry for each plugin in :data:`DASHBOARD_PLUGINS`.

    Each entry carries two independent axes:

    * ``in_use`` — whether the plugin is actively used; see :func:`_is_in_use`.
    * ``subscription`` — the :class:`SubscriptionState` of its subscription record.

    A client belonging to another application (e.g. pam-passkey) keeps its own row and
    its own ``last_seen`` but resolves its subscription through that application, see
    :func:`get_subscription_owner`. Plugin usage is derived from the ``ClientApplication`` table by
    parsing each stored user-agent with
    :func:`~privacyidea.lib.utils.get_plugin_info_from_useragent`.

    :param token_users: number of users with active tokens, needed to decide whether a
        subscription is exceeded. Pass it when the caller already knows the count — a
        request rendering both this and :func:`get_server_subscription_status` should
        count once and hand the result to both. Counted here if not given.
    :return: list of dicts in the order of :data:`DASHBOARD_PLUGINS`. Each dict
        has the keys ``application``, ``in_use``, ``subscription``, ``last_seen``,
        ``date_till``, ``days_left`` and ``versions`` (the distinct client
        versions seen in the user-agents, newest first).
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

    if token_users is None:
        token_users = get_users_with_active_tokens()
    now = datetime.datetime.now()
    overview = []
    for plugin in DASHBOARD_PLUGINS:
        last_seen = last_seen_by_plugin.get(plugin.lower())
        # A client of another application keeps its own row and last_seen but shows
        # that application's subscription.
        owning_application = get_subscription_owner(plugin)
        subscription = subscriptions_by_app.get(owning_application)
        state_info = _subscription_state(subscription, now, token_users)
        overview.append({"application": plugin,
                         "in_use": _is_in_use(bool(subscription), last_seen, now),
                         "subscription": state_info.state,
                         "last_seen": last_seen,
                         "date_till": state_info.date_till,
                         "days_left": state_info.days_left,
                         # Versions seen in the user-agents, newest first.
                         "versions": sorted(versions_by_plugin.get(plugin.lower(), []),
                                            key=version_sort_key, reverse=True)})
    return overview


def get_server_subscription_status(token_users: int | None = None) -> dict:
    """
    Dashboard status entry for the privacyIDEA server itself. Same shape as
    entries from :func:`get_plugin_subscription_status` plus ``is_server: True``,
    so the frontend renders the server row without duplicating the
    classification rules.

    :param token_users: number of users with active tokens, see
        :func:`get_plugin_subscription_status`. Counted here if not given.
    """
    # Pick the row with the latest date_till for determinism when multiple
    # server subscriptions exist.
    subscriptions = sorted(get_subscription("privacyidea"),
                           key=lambda s: s.get("date_till") or datetime.datetime.min,
                           reverse=True)
    subscription = subscriptions[0] if subscriptions else None
    now = datetime.datetime.now()
    if token_users is None:
        token_users = get_users_with_active_tokens()
    state_info = _subscription_state(subscription, now, token_users)
    return {"application": "privacyidea",
            "is_server": True,
            # The server is the one answering this request, so it is in use by definition -
            # unlike a client, whose use is deduced from a subscription or recent activity.
            "in_use": True,
            "subscription": state_info.state,
            "last_seen": None,
            "date_till": state_info.date_till,
            "days_left": state_info.days_left,
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
    if not expire:
        # date_till is nullable. A record without an end date says nothing about being
        # valid, so it is always treated as expired.
        return True
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
    # Metered clients (e.g. pam-passkey, FreeRADIUS) count against another application's
    # subscription; resolve to that application before looking up its subscription and
    # free limit. A client that is not metered resolves to a name that is no application
    # of its own, falls through below and may always authenticate.
    application = get_metered_application(application)
    if application in APPLICATIONS:
        # date_till is nullable. A record without an end date says nothing about being
        # valid, so it is ignored here: the free tier then applies exactly as it would
        # without a subscription, rather than blocking the client outright.
        subscriptions = [subscription for subscription in get_subscription(application)
                         if subscription.get("date_till")]
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
