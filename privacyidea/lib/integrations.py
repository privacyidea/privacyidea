#  2026-08-27 Nils Behlen <nils.behlen@netknights.it>
#             Unify the client/integration vocabulary
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
__doc__ = """Single source of truth for the privacyIDEA ecosystem's integration vocabulary.

Before this module existed, the same "ecosystem integration" concept was expressed in at
least three independent, hardcoded lists that had already drifted out of sync: the
API-client type dropdown, the policy ``user_agents`` condition picker, and the
subscription-metering table. All three key off the same underlying wire-format agent
string, so unifying them requires three levels:

* :class:`Product` — what is licensed. Its ``id`` is the ``Subscription.application``
  value on a real, cryptographically signed subscription file, so it is NOT free to
  rename: every existing key here must stay byte-for-byte identical to what shipped in
  ``privacyidea.lib.subscriptions.SUBSCRIPTIONS`` before this module existed.
* :class:`Integration` — what an admin targets in a policy ``user_agents`` condition, or
  picks as an API client's ``client_type``. Owns 1..n wire-format agent names and belongs
  to exactly one product (or none, for an integration that is never licensed at all, e.g.
  the WebUI). ``Integration.id`` is a new concept with no released consumer yet, so it is
  free to be a clean internal key.
* agent name — the literal ``User-Agent`` string a client sends. Never shown in a UI,
  never stored as policy data; only used to resolve a live request to an integration.

One thing this module intentionally does not do, deliberate and explained on the product
it touches:

* It does not enforce a free-tier limit for the Authenticator App (``free_users=None`` on
  its product): the app's own requests were already excluded from request-based metering,
  and the one remaining enforcement path (a login-time push-token count nag) is being
  removed as part of the same change that introduced this module. The app keeps a real,
  subscribable product so the dashboard still reports its subscription state — it is just
  never counted or blocked.
"""

import dataclasses


@dataclasses.dataclass(frozen=True)
class Product:
    """
    A licensed product. ``id`` mirrors a real ``Subscription.application`` value and must
    never be renamed once released.

    :ivar id: canonical, lower-case product identifier.
    :ivar label: display label.
    :ivar free_users: the free-tier limit (users with active tokens) allowed without a
        subscription file, or None if this product is never counted or enforced against a
        limit at all (it can still be subscribed to and shown on the dashboard).
    """
    id: str
    label: str
    free_users: int | None = None


@dataclasses.dataclass(frozen=True)
class Integration:
    """
    Something an admin can target in a policy ``user_agents`` condition, or pick as an API
    client's ``client_type``. May also get its own row on the dashboard subscription
    overview.

    :ivar id: canonical internal key. Used for the API client ``client_type`` value and
        dashboard grouping/resolution. Free to design cleanly.
    :ivar label: display label only — the client_type dropdown, the policy condition
        dropdown, the dashboard row. Never stored, never matched against anything.
    :ivar agent_names: every raw ``User-Agent`` wire string this integration is known by,
        including old/renamed ones. Used only to resolve a *live request's* raw
        User-Agent to this integration, e.g. for subscription metering. Never stored as
        policy data. Matched case-insensitively (see :data:`AGENT_TO_INTEGRATION`), so
        list a name once regardless of the casing a given plugin version happens to send;
        include a second entry only for a genuinely different wire string (e.g. a rename).
    :ivar policy_value: the exact literal string the policy ``user_agents`` condition
        dropdown submits/stores. This must equal what the pre-catalog frontend lists
        (``USER_AGENT_OPTIONS`` / ``userAgentsMapping``) already submitted for this
        integration, unchanged — the storage format is frozen, already released. Existing
        stored policy values keep matching by literal string equality exactly as before;
        this field only lets the dropdown be generated from one shared place.
    :ivar product_id: the :class:`Product` this integration is licensed under, or None for
        an integration that is never licensed at all (currently only the WebUI).
    :ivar api_client: whether this integration is offered as an API client ``client_type``.
    :ivar dashboard: whether this integration gets its own row on the dashboard
        subscription overview.
    :ivar section: dashboard grouping key (e.g. ``"system_login"``), only meaningful when
        ``dashboard`` is True. A stable key rather than display text: the frontends
        translate it locally, since the backend has no access to the admin's UI locale.
    :ivar ptl_slug: slug of this integration's product-landing-page, only meaningful when
        ``dashboard`` is True.
    :ivar github_repo: ``owner/repo`` hosting this integration's releases, used to look up
        the latest published version. Only meaningful when ``dashboard`` is True; omitted
        for integrations with no GitHub-hosted releases (e.g. FreeRADIUS).
    :ivar release_link_suppressed: True for an integration distributed via OS packages or
        app stores rather than a downloadable GitHub release: the dashboard should show
        its latest version and date, but no link to a release page. A property of this one
        integration, not of the product it is licensed under — e.g. the Authenticator App
        is suppressed even though FreeRADIUS, sharing its licensing product with the
        server, is not.
    """
    id: str
    label: str
    agent_names: tuple[str, ...]
    policy_value: str
    product_id: str | None
    api_client: bool = False
    dashboard: bool = False
    section: str | None = None
    ptl_slug: str | None = None
    github_repo: str | None = None
    release_link_suppressed: bool = False


# The free-tier limit, in users with active tokens, allowed without a subscription file.
# `owncloud` / `demo_application` are legacy products with no current dashboard row or
# picker entry — they stay reachable only for a client whose own user-agent happens to
# equal one of these names, exactly as before.
PRODUCTS: dict[str, Product] = {
    product.id: product
    for product in (
        Product(id="demo_application", label="Demo Application", free_users=0),
        Product(id="owncloud", label="ownCloud", free_users=50),
        Product(id="privacyidea-nextcloud", label="Nextcloud", free_users=50),
        Product(id="privacyidea-ldap-proxy", label="LDAP Proxy", free_users=50),
        Product(id="privacyidea-cp", label="Windows Credential Provider", free_users=50),
        Product(id="privacyidea-pam", label="PAM", free_users=10000),
        Product(id="privacyidea-shibboleth", label="Shibboleth", free_users=10000),
        Product(id="privacyidea-adfs", label="AD FS", free_users=50),
        Product(id="privacyidea-keycloak", label="Keycloak", free_users=10000),
        # `simplesamlphp` and `privacyidea-simplesamlphp` were added as two separate,
        # identically-configured products in the same 2021 commit (8bca25e0), with no
        # explanation distinguishing them — unlike PAM's user_agents/pam-privacyidea
        # rename, there is no evidence they were ever meant to be different products. One
        # product now, named like every other real plugin (`privacyidea-*`); both wire
        # names alias into it, see the "simplesamlphp" integration below.
        # A real, already-signed subscription file for either product may still
        # carry the pre-merge id ("simplesamlphp") in its application field; that
        # id is not renamed here, only merged for the UI. See PRODUCT_ALIASES.
        Product(id="privacyidea-simplesamlphp", label="SimpleSAMLphp", free_users=10000),
        # Never counted or enforced, see the module docstring. Still a real, subscribable
        # product: the dashboard keeps reporting its subscription state.
        Product(id="privacyidea authenticator", label="privacyIDEA Authenticator", free_users=None),
        # The privacyIDEA server's own subscription. FreeRADIUS traffic is metered against
        # it, see the "freeradius" integration below.
        Product(id="privacyidea", label="privacyIDEA Server", free_users=50),
    )
}

# Legacy product ids merged into a current one for the UI (see the "simplesamlphp"
# Integration and the privacyidea-simplesamlphp Product above), mapped to the
# canonical id they were merged into. A real subscription file signed under a
# legacy id before the merge is still a valid file for the canonical product, so
# a subscription lookup must check both; see product_names().
PRODUCT_ALIASES: dict[str, str] = {
    "simplesamlphp": "privacyidea-simplesamlphp",
}

CATALOG: tuple[Integration, ...] = (
    Integration(
        id="privacyidea-app",
        label="privacyIDEA Authenticator App",
        agent_names=("privacyIDEA-App",),
        policy_value="privacyIDEA-App",
        product_id="privacyidea authenticator",
        dashboard=True,
        section="use_cases",
        ptl_slug="privacyidea-authenticator-app",
        github_repo="privacyidea/pi-authenticator",
        release_link_suppressed=True,
    ),
    Integration(
        id="freeradius",
        label="FreeRADIUS",
        agent_names=("FreeRADIUS",),
        policy_value="FreeRADIUS",
        product_id="privacyidea",
        api_client=True,
        dashboard=True,
        section="use_cases",
        ptl_slug="privacyidea-freeradius",
        github_repo="privacyidea/FreeRADIUS",
    ),
    Integration(
        id="privacyidea-nextcloud",
        label="Nextcloud",
        agent_names=("privacyidea-nextcloud",),
        policy_value="privacyidea-nextcloud",
        product_id="privacyidea-nextcloud",
        api_client=True,
        dashboard=True,
        section="use_cases",
        ptl_slug="privacyidea-nextcloud",
        github_repo="privacyidea/privacyidea-nextcloud-app",
    ),
    Integration(
        id="privacyidea-cp",
        label="Windows Credential Provider",
        agent_names=("privacyidea-cp",),
        policy_value="privacyidea-cp",
        product_id="privacyidea-cp",
        api_client=True,
        dashboard=True,
        section="system_login",
        ptl_slug="privacyidea-windows-credential-provider",
        github_repo="privacyidea/privacyidea-credential-provider",
    ),
    Integration(
        id="pam",
        label="PAM OTP & Push",
        agent_names=("PAM", "pam-privacyidea"),
        policy_value="PAM",
        product_id="privacyidea-pam",
        api_client=True,
        dashboard=True,
        section="system_login",
        ptl_slug="privacyidea-pam-otp-push",
        github_repo="privacyidea/privacyidea-pam",
    ),
    Integration(
        id="pam-passkey",
        label="PAM Passkey",
        agent_names=("pam-passkey",),
        policy_value="pam-passkey",
        api_client=True,
        product_id="privacyidea-pam",
        dashboard=True,
        section="system_login",
        ptl_slug="privacyidea-pam-passkey",
        github_repo="privacyidea/pam-passkey",
    ),
    Integration(
        id="privacyidea-keycloak",
        label="Keycloak",
        agent_names=("privacyIDEA-Keycloak",),
        policy_value="privacyIDEA-Keycloak",
        product_id="privacyidea-keycloak",
        api_client=True,
        dashboard=True,
        section="single_sign_on",
        ptl_slug="privacyidea-keycloak",
        github_repo="privacyidea/keycloak-provider",
    ),
    Integration(
        id="entraid-via-keycloak",
        label="EntraID via Keycloak",
        agent_names=("entraid-via-keycloak",),
        policy_value="entraid-via-keycloak",
        product_id="privacyidea-keycloak",
        api_client=True,
        dashboard=True,
        section="single_sign_on",
        ptl_slug="privacyidea-entraid-integration",
        github_repo="privacyidea/keycloak-protocolmapper-entraid",
    ),
    Integration(
        id="privacyidea-adfs",
        label="AD FS",
        agent_names=("PrivacyIDEA-ADFS",),
        policy_value="PrivacyIDEA-ADFS",
        product_id="privacyidea-adfs",
        api_client=True,
        dashboard=True,
        section="single_sign_on",
        ptl_slug="privacyidea-adfs",
        github_repo="privacyidea/adfs-provider",
    ),
    Integration(
        id="privacyidea-shibboleth",
        label="Shibboleth",
        agent_names=("privacyIDEA-Shibboleth",),
        policy_value="privacyIDEA-Shibboleth",
        product_id="privacyidea-shibboleth",
        api_client=True,
        dashboard=True,
        section="single_sign_on",
        ptl_slug="privacyidea-shibboleth",
        github_repo="privacyidea/shibboleth-plugin",
    ),
    # Policy-condition-only integrations below: no dashboard row, no API-client option.
    Integration(
        id="simplesamlphp",
        label="SimpleSAMLphp",
        agent_names=("simpleSAMLphp", "privacyidea-simplesamlphp"),
        policy_value="simpleSAMLphp",
        product_id="privacyidea-simplesamlphp",
    ),
    Integration(
        id="privacyidea-ldap-proxy",
        label="LDAP Proxy",
        agent_names=("privacyIDEA-LDAP-Proxy",),
        policy_value="privacyIDEA-LDAP-Proxy",
        product_id="privacyidea-ldap-proxy",
    ),
    Integration(
        id="privacyidea-webui",
        label="privacyIDEA WebUI",
        agent_names=("privacyIDEA-WebUI",),
        policy_value="privacyIDEA-WebUI",
        product_id=None,
    ),
)

# Every wire-format agent name this catalog knows about, lower-cased, mapped to the
# integration it belongs to. A name not in here is not known to any integration; callers
# fall back to treating the (lower-cased) name as its own product, exactly as an
# integration whose only agent name is its own id would resolve anyway.
AGENT_TO_INTEGRATION: dict[str, str] = {
    agent_name.lower(): integration.id
    for integration in CATALOG
    for agent_name in integration.agent_names
}

# Integration id -> product id, for every integration that belongs to one.
INTEGRATION_TO_PRODUCT: dict[str, str] = {
    integration.id: integration.product_id
    for integration in CATALOG
    if integration.product_id is not None
}

# Dashboard rows, in :data:`CATALOG` order (which already follows the section grouping).
DASHBOARD_INTEGRATIONS: tuple[Integration, ...] = tuple(i for i in CATALOG if i.dashboard)


def get_integration(integration_id: str) -> Integration | None:
    """Look up an integration by id, or None if unknown."""
    for integration in CATALOG:
        if integration.id == integration_id:
            return integration
    return None


def resolve_product(name: str) -> str:
    """
    Resolve a client user-agent (or an integration/product id) to the product id its
    authentications are counted and its subscription is reported against.

    A name matching a known agent name resolves through its integration to that
    integration's product. Any other name is returned unchanged apart from case, so a
    literal product id, or a legacy client whose own name equals a product id with no
    integration of its own (e.g. ``owncloud``), resolves to itself.

    :param name: a client user-agent, plugin name, or product/integration id
    :return: the lower-cased product id to look up in :data:`PRODUCTS`
    """
    key = (name or "").lower()
    integration_id = AGENT_TO_INTEGRATION.get(key)
    if integration_id is not None:
        return INTEGRATION_TO_PRODUCT.get(integration_id, key)
    return key


def product_names(product_id: str) -> tuple[str, ...]:
    """
    Every application name a subscription for ``product_id`` might be filed
    under: the canonical id itself, plus any legacy id that used to be its own
    product before being merged into it (see :data:`PRODUCT_ALIASES`). A
    subscription file signed under a legacy id before its merge is still a
    valid file for the canonical product, so a lookup must check both.

    :param product_id: a canonical product id
    :return: ``(product_id, *legacy_ids)``
    """
    legacy_ids = tuple(legacy for legacy, canonical in PRODUCT_ALIASES.items() if canonical == product_id)
    return (product_id, *legacy_ids)
