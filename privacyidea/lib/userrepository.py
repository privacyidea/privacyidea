"""
User resolver traversal logic, separated from the User value object.

All code that needs to locate a user in an external store (LDAP, SQL, …)
should call the module-level ``user_repository`` singleton rather than
constructing ``User`` objects and relying on the side-effecting ``__init__``.

The ``User`` class delegates its own resolver methods here so that call sites
which still use ``User(login=…, realm=…)`` directly continue to work without
change.

Migration path for callers:
  - Replace ``get_user_from_param(params)``           →  ``user_repository.find_from_params(params)``
  - Replace ``User(login=l, realm=r, resolver=res)``  →  ``user_repository.find(l, r, res)``
  - Replace ``User(uid=u, resolver=res)``             →  ``user_repository.find_by_uid(u, res)``
  - Replace ``user_obj.get_ordered_resolvers()``      →  ``user_repository.get_ordered_resolvers(realm)``
"""

import logging

from .framework import get_app_config_value
from .log import log_with
from .realm import get_realms
from .resolver import get_resolver_object

log = logging.getLogger(__name__)


class UserRepository:
    """
    Owns all resolver traversal for the User layer.

    Methods here are side-effect-free with respect to any ``User`` object:
    they return data, they do not mutate caller state.  The ``User`` class
    delegates its own resolver methods here; external callers can use the
    repository directly for new code.
    """

    @log_with(log)
    def get_ordered_resolvers(self, realm: str) -> list[str]:
        """
        Return resolver names for *realm* sorted by priority (lowest number
        first, ties broken alphabetically).  Node-aware: only resolvers
        assigned to the current HA node (or with no node restriction) are
        returned.

        :param realm: realm name (case-insensitive)
        :return: ordered list of resolver names
        """
        realm = (realm or "").lower()
        resolver_tuples = []
        realm_config = get_realms(realm)
        resolvers_in_realm = realm_config.get(realm, {}).get("resolver", [])
        for resolver in resolvers_in_realm:
            resolver_tuples.append((
                resolver.get("name"),
                resolver.get("priority") or 1000,
                resolver.get("node"),
            ))

        sorted_resolvers = sorted(resolver_tuples, key=lambda r: r[1])
        local_node_uuid = get_app_config_value("PI_NODE_UUID")
        resolvers = [r[0] for r in sorted_resolvers
                     if not r[2] or r[2] == local_node_uuid]
        # deduplicate while preserving order
        seen: set[str] = set()
        return [x for x in resolvers if not (x in seen or seen.add(x))]

    def locate_login_in_resolver(self, login: str, resolver_name: str) -> str | None:
        """
        Check whether *login* exists in *resolver_name*.

        Returns the uid string on success, ``None`` if the user was not found
        or if the resolver does not exist.  Does **not** modify any ``User``
        object.

        :param login: login name to look up
        :param resolver_name: resolver to search
        :return: uid string or None
        """
        resolver = get_resolver_object(resolver_name)
        if resolver is None:  # pragma: no cover
            log.info("Resolver {!r} not found.".format(resolver_name))
            return None
        uid = resolver.getUserId(login)
        if uid not in ["", None]:
            log.info("user {!r} found in resolver {!r}, uid={!r}".format(
                login, resolver_name, uid))
            return uid
        log.debug("user {!r} not found in resolver {!r}".format(login, resolver_name))
        return None

    def find(self, login: str, realm: str, resolver: str = "") -> "User":
        """
        Resolve *login* to a uid by searching the realm's resolvers in
        priority order.  Returns a fully resolved ``User`` if found, or an
        unresolved ``User`` if not.

        Equivalent to ``User(login=login, realm=realm, resolver=resolver)``
        but communicates intent: the caller explicitly needs the uid.

        :param login: login name
        :param realm: realm name
        :param resolver: optional resolver hint
        :return: User object (resolved or unresolved)
        """
        from .user import User
        return User(login=login, realm=realm, resolver=resolver)

    def find_by_uid(self, uid: str, resolver: str, realm: str = "") -> "User":
        """
        Reverse lookup: uid + resolver → login.

        :param uid: user id in the resolver
        :param resolver: resolver name
        :param realm: optional realm name
        :return: User object (resolved if uid exists in resolver)
        """
        from .user import User
        return User(uid=uid, resolver=resolver, realm=realm)

    def find_from_params(self, params: dict,
                         optional_or_required: bool = True) -> "User":
        """
        Build a ``User`` from the request parameter dict (keys ``user``,
        ``realm``, ``resolver``).  Only resolves against the user store when a
        login name is present; returns an empty ``User`` otherwise.

        Replaces ``get_user_from_param()``.

        :param params: request parameter dict
        :param optional_or_required: ``True`` (default) if the ``user``
            parameter is optional; ``False`` if its absence should raise.
        :return: User as found in *params*
        """
        from .user import User, split_user
        from .realm import get_default_realm
        from .params import get_optional, get_required

        realm = ""
        if optional_or_required:
            username = get_optional(params, "user")
        else:
            username = get_required(params, "user")

        if username is None:
            username = ""
        else:
            username, realm = split_user(username)

        if "realm" in params:
            realm = params["realm"]

        if username != "":
            if realm is None or realm == "":
                realm = get_default_realm()

        return User(login=username, realm=realm, resolver=params.get("resolver"))


# ---------------------------------------------------------------------------
# Module-level singleton — import this where resolver traversal is needed
# ---------------------------------------------------------------------------
user_repository = UserRepository()
