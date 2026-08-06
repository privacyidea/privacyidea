# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Token lookup and retrieval helpers (read-only queries)."""

import logging
import traceback
from collections.abc import Iterator, Sequence
from typing import Any

from flask_sqlalchemy.session import Session
from sqlalchemy import and_, func, or_, select
from sqlalchemy.sql import Select

from privacyidea.lib import _
from privacyidea.lib.config import get_token_class
from privacyidea.lib.error import (TokenAdminError, ParameterError,
                                   PrivacyIDEAError, ResourceNotFoundError, UserError)
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.log import log_with
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_object
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.lib.utils import SQL_LIKE_ESCAPE, convert_wildcard_to_sql_like
from privacyidea.models import (db, Token, Realm, TokenRealm, TokenInfo,
                                TokenOwner, TokenContainer, TokenContainerToken)
from privacyidea.models.utils import clob_to_varchar

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _like_or_eq(column, value: str):
    """Return a LIKE clause if *value* contains ``*``, else an ``==`` clause."""
    if "*" in value:
        return column.like(convert_wildcard_to_sql_like(value), escape=SQL_LIKE_ESCAPE)
    return column == value


def _like_or_eq_ci(column, value: str):
    """Case-insensitive variant of :func:`_like_or_eq`."""
    if "*" in value:
        return func.lower(column).like(
            convert_wildcard_to_sql_like(value.lower()), escape=SQL_LIKE_ESCAPE)
    return func.lower(column) == value.lower()


def _has_content(value: str | None) -> bool:
    """Return *True* if *value* is a non-empty string that is not purely wildcards."""
    return bool(value and value.strip("*"))


_MAX_SERIAL_LIST_SIZE = 500  # Hard cap to prevent SQL IN-clause DoS.


def _parse_serial(serial: str | None):
    """Split a serial parameter into (exact, list) components.

    If *serial* contains commas but no ``*`` wildcards it is treated as a
    comma-separated list of exact serial numbers.  Otherwise it is returned
    as a single exact serial.

    The list is capped at :data:`_MAX_SERIAL_LIST_SIZE` entries to prevent
    denial-of-service via excessively large SQL ``IN (…)`` clauses.

    Returns ``(serial_exact, serial_list)`` — at most one of them is set.
    """
    if serial and "*" not in serial and "," in serial:
        parts = serial.replace(" ", "").split(",")
        if len(parts) > _MAX_SERIAL_LIST_SIZE:
            raise ParameterError(
                _("Too many serials in comma-separated list (max {0}).").format(
                    _MAX_SERIAL_LIST_SIZE))
        return None, parts
    return serial, None


def _db_tokens_to_objects(db_tokens: Sequence[Token]) -> list[TokenClass]:
    """Convert an iterable of DB Token rows to TokenClass instances.

    Rows whose token type is unknown are silently skipped.
    """
    result = []
    for db_token in db_tokens:
        obj = create_tokenclass_object(db_token)
        if isinstance(obj, TokenClass):
            result.append(obj)
    return result


# ---------------------------------------------------------------------------
# TokenClass object factory
# ---------------------------------------------------------------------------

@log_with(log)
def create_tokenclass_object(db_token: Token) -> TokenClass | None:
    """Wrap a database *Token* row in the matching :class:`TokenClass` subclass.

    Returns ``None`` if no token-class implementation is registered for the
    token's type.

    :param db_token: A database token row.
    :return: The token-class instance, or ``None``.
    """
    tokentype = db_token.tokentype.lower()
    token_class = get_token_class(tokentype)
    if not token_class:
        log.error(f"type {tokentype!r} not found in tokenclasses")
        return None
    try:
        return token_class(db_token)
    except Exception as exc:  # pragma: no cover
        log.error(f"create_tokenclass_object failed for type {tokentype!r}: {exc!r}")
        raise TokenAdminError(
            _("create_tokenclass_object failed for token type '{0}'.").format(tokentype),
            id=1609)


# ---------------------------------------------------------------------------
# Core query builder
# ---------------------------------------------------------------------------

def _create_token_query(
    tokentype: str | None = None,
    token_type_list: list[str] | None = None,
    realm: str | None = None,
    assigned: bool | None = None,
    user: User | None = None,
    serial_exact: str | None = None,
    serial_wildcard: str | None = None,
    serial_list: list[str] | None = None,
    active: bool | None = None,
    resolver: str | None = None,
    userid: str | None = None,
    rollout_state: str | None = None,
    description: str | None = None,
    revoked: bool | None = None,
    locked: bool | None = None,
    tokeninfo: dict | None = None,
    maxfail: bool | None = None,
    allowed_realms: list[str] | None = None,
    container_serial: str | None = None,
    all_nodes: bool = False,
) -> Select:
    """Build a SQLAlchemy ``SELECT`` for :class:`Token` rows.

    Every parameter is optional.  When given, it adds a corresponding
    ``WHERE`` clause (all conditions are combined with ``AND``).

    This is an internal building block — callers should use :func:`get_tokens`,
    :func:`get_tokens_paginate`, or :func:`get_tokens_paginated_generator`.
    """
    db.session.expire_all()

    sql_query = select(Token)

    # -- JOIN TokenOwner (only when needed) ---------------------------------
    needs_owner = (
        _has_content(userid)
        or _has_content(resolver)
        or bool(user)
        or assigned is not None
        or not all_nodes
    )
    if needs_owner:
        sql_query = sql_query.outerjoin(TokenOwner, Token.id == TokenOwner.token_id)

    # -- Realm filters ------------------------------------------------------
    sql_query = _apply_realm_filter(sql_query, realm)
    sql_query = _apply_allowed_realms_filter(sql_query, allowed_realms)

    # -- Token-type filters -------------------------------------------------
    if _has_content(tokentype):
        sql_query = sql_query.where(_like_or_eq_ci(Token.tokentype, tokentype))
    if token_type_list:
        sql_query = sql_query.where(
            Token.tokentype.in_([t.lower() for t in token_type_list]))

    # -- Description filter -------------------------------------------------
    if _has_content(description):
        sql_query = sql_query.where(_like_or_eq_ci(Token.description, description))

    # -- Serial filters -----------------------------------------------------
    if serial_wildcard and serial_wildcard.strip("*"):
        sql_query = sql_query.where(_like_or_eq(Token.serial, serial_wildcard))
    if serial_exact:
        sql_query = sql_query.where(Token.serial == serial_exact)
    if serial_list:
        sql_query = sql_query.where(Token.serial.in_(serial_list))

    # -- Assignment filter --------------------------------------------------
    if assigned is not None:
        if assigned:
            sql_query = sql_query.where(TokenOwner.id.is_not(None))
        else:
            sql_query = sql_query.where(TokenOwner.id.is_(None))

    # -- User-object filter -------------------------------------------------
    sql_query = _apply_user_filter(sql_query, user)

    # -- Standalone resolver / userid filters -------------------------------
    if _has_content(resolver):
        sql_query = sql_query.where(_like_or_eq(TokenOwner.resolver, resolver))
    if _has_content(userid):
        sql_query = sql_query.where(_like_or_eq(TokenOwner.user_id, userid))

    # -- Boolean status flags -----------------------------------------------
    if active is not None:
        sql_query = sql_query.where(Token.active == active)
    if revoked is not None:
        sql_query = sql_query.where(Token.revoked == revoked)
    if locked is not None:
        sql_query = sql_query.where(Token.locked == locked)
    if maxfail is not None:
        if maxfail:
            sql_query = sql_query.where(Token.failcount >= Token.maxfail)
        else:
            sql_query = sql_query.where(Token.failcount < Token.maxfail)

    # -- Rollout state ------------------------------------------------------
    if _has_content(rollout_state):
        sql_query = sql_query.where(_like_or_eq_ci(Token.rollout_state, rollout_state))

    # -- Token info ---------------------------------------------------------
    if tokeninfo is not None:
        sql_query = _apply_tokeninfo_filter(sql_query, tokeninfo)

    # -- Container serial ---------------------------------------------------
    if container_serial is not None:
        sql_query = _apply_container_filter(sql_query, container_serial)

    # -- Node-specific resolver / realm configuration -----------------------
    if not all_nodes:
        sql_query = _apply_node_filter(sql_query)

    return sql_query


# -- Private filter helpers used by _create_token_query ---------------------

def _token_ids_in_realms(realm_names: list[str]) -> Select:
    """Return a subquery of token IDs that belong to any of *realm_names*.

    Each entry may be an exact name or a ``*``-wildcard pattern.
    All comparisons are case-insensitive.
    """
    exact = [r.lower() for r in realm_names if "*" not in r]
    wildcards = [r for r in realm_names if "*" in r]

    conditions = []
    if exact:
        conditions.append(func.lower(Realm.name).in_(exact))
    for pattern in wildcards:
        conditions.append(
            func.lower(Realm.name).like(
                convert_wildcard_to_sql_like(pattern.lower()), escape=SQL_LIKE_ESCAPE))

    realm_ids = select(Realm.id).where(or_(*conditions))
    return select(TokenRealm.token_id).where(TokenRealm.realm_id.in_(realm_ids))


def _apply_realm_filter(sql_query: Select, realm: str | None) -> Select:
    """Restrict to tokens that are a member of the requested realm(s).

    *realm* may be a single name, a ``*``-wildcard pattern, or a
    comma-separated list (each entry may contain wildcards).  Entries that
    consist solely of wildcards (``*``, ``**``) are stripped so they don't
    accidentally exclude tokens with *no* realm.
    """
    realm_list = [r.strip() for r in realm.split(",") if r.strip()] if realm else None
    if realm_list:
        # Drop catch-all wildcard-only entries.
        realm_list = [r for r in realm_list if r.strip("*")]
    if not realm_list:
        return sql_query

    return sql_query.where(Token.id.in_(_token_ids_in_realms(realm_list)))


def _apply_allowed_realms_filter(sql_query: Select, allowed_realms: list[str] | None) -> Select:
    """Restrict to tokens whose realm is in *allowed_realms*."""
    if allowed_realms is None:
        return sql_query
    return sql_query.where(Token.id.in_(_token_ids_in_realms(allowed_realms)))


def _apply_user_filter(sql_query: Select, user: User | None) -> Select:
    """Restrict to tokens owned by *user*."""
    if not user or user.is_empty():
        return sql_query

    if user.login and not user.resolver:
        raise UserError("The user can not be found in any resolver in this realm!")

    if user.realm:
        # User.realm_id is resolved during User.__init__; no extra DB lookup needed.
        if not user.realm_id:
            raise ResourceNotFoundError(f"Realm '{user.realm}' does not exist.")
        sql_query = sql_query.where(TokenOwner.realm_id == user.realm_id)

    if user.resolver:
        sql_query = sql_query.where(TokenOwner.resolver == user.resolver)
        uid, _rtype, _resolver = user.get_user_identifiers()
        if uid:
            sql_query = sql_query.where(TokenOwner.user_id == str(uid))

    return sql_query


def _apply_tokeninfo_filter(sql_query: Select, tokeninfo: dict) -> Select:
    """Restrict to tokens whose token-info contains the given key/value pair."""
    if len(tokeninfo) != 1:
        raise PrivacyIDEAError(
            _("I can only create SQL filters from tokeninfo of length 1."))
    key, value = next(iter(tokeninfo.items()))
    return (sql_query
            .join(TokenInfo, TokenInfo.token_id == Token.id)
            .where(TokenInfo.Key == key)
            .where(clob_to_varchar(TokenInfo.Value) == value))


def _apply_container_filter(sql_query: Select, container_serial: str) -> Select:
    """Restrict to tokens inside (or outside) a container."""
    if not container_serial:
        # Empty string → tokens that are NOT in any container.
        return (sql_query
                .outerjoin(TokenContainerToken, TokenContainerToken.token_id == Token.id)
                .where(TokenContainerToken.container_id.is_(None)))

    sub = (select(TokenContainerToken.token_id)
           .join(TokenContainer, TokenContainer.id == TokenContainerToken.container_id)
           .where(func.upper(TokenContainer.serial) == container_serial.upper()))
    return sql_query.where(Token.id.in_(sub))


def _apply_node_filter(sql_query: Select) -> Select:
    """Only return tokens whose resolver is configured for the local node."""
    local_node_uuid = get_app_config_value("PI_NODE_UUID")
    realms = get_realms()

    local_resolvers: list[str] = []
    excluded_realms: list[str] = []

    for realm_name, realm_data in realms.items():
        has_local_resolver = False
        for res in realm_data.get("resolver", []):
            if res.get("name") and (not res.get("node") or res["node"] == local_node_uuid):
                local_resolvers.append(res["name"])
                has_local_resolver = True
        if not has_local_resolver:
            excluded_realms.append(realm_name)

    resolver_ok = or_(
        TokenOwner.id.is_(None),
        TokenOwner.resolver.in_(local_resolvers),
    )

    sql_query = sql_query.outerjoin(Realm, TokenOwner.realm_id == Realm.id)
    realm_ok = or_(
        TokenOwner.realm_id.is_(None),
        func.lower(Realm.name).not_in([r.lower() for r in excluded_realms]),
    )

    return sql_query.where(and_(resolver_ok, realm_ok))


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------

@log_with(log)
def get_tokens(
    tokentype: str | None = None,
    token_type_list: list[str] | None = None,
    realm: str | None = None,
    assigned: bool | None = None,
    user: User | None = None,
    serial: str | None = None,
    serial_wildcard: str | None = None,
    active: bool | None = None,
    resolver: str | None = None,
    rollout_state: str | None = None,
    count: bool = False,
    revoked: bool | None = None,
    locked: bool | None = None,
    tokeninfo: dict | None = None,
    maxfail: bool | None = None,
    all_nodes: bool = False,
) -> list[TokenClass] | int:
    """Return token objects (or a count) matching the given filters.

    All filter parameters are optional.  When omitted the corresponding
    condition is not applied.

    :param tokentype: Single token type, may contain ``*`` wildcards.
    :param token_type_list: List of exact token types.
    :param realm: Realm name, ``*``-wildcard pattern, or comma-separated
        list of realm names (each entry may contain wildcards).
    :param assigned: ``True`` → assigned only, ``False`` → unassigned only.
    :param user: Filter by token owner.
    :param serial: Exact serial, or a comma-separated list of exact serials
        (e.g. ``"SER1,SER2"``).  If the string contains commas but no ``*``
        it is split automatically.
    :param serial_wildcard: A ``*``-wildcard pattern to match serials.
    :param active: ``True`` → active only, ``False`` → inactive only.
    :param resolver: Filter by resolver name (exact match).
    :param rollout_state: Filter by rollout state.
    :param count: If ``True`` return the number of matching tokens instead
        of the list.
    :param revoked: Filter by revocation status.
    :param locked: Filter by lock status.
    :param tokeninfo: Single-entry ``{key: value}`` dict.
    :param maxfail: ``True`` → only tokens whose fail-counter reached the
        maximum; ``False`` → only tokens below the maximum.
    :param all_nodes: If ``True``, ignore node-specific resolver config.
    :return: A list of :class:`TokenClass` objects, or an ``int`` when
        *count* is ``True``.
    """
    serial_exact, serial_list = _parse_serial(serial)

    sql_query = _create_token_query(
        tokentype=tokentype, token_type_list=token_type_list, realm=realm,
        assigned=assigned, user=user,
        serial_exact=serial_exact, serial_wildcard=serial_wildcard,
        serial_list=serial_list,
        active=active, resolver=resolver, rollout_state=rollout_state,
        revoked=revoked, locked=locked, tokeninfo=tokeninfo,
        maxfail=maxfail, all_nodes=all_nodes)

    session: Session = db.session

    if count:
        return session.execute(
            select(func.count()).select_from(sql_query.subquery())
        ).scalar_one()

    db_tokens = session.execute(sql_query).unique().scalars().all()
    return _db_tokens_to_objects(db_tokens)


@log_with(log)
def get_tokens_paginate(
    tokentype: str | None = None,
    token_type_list: list[str] | None = None,
    realm: str | None = None,
    assigned: bool | None = None,
    user: User | None = None,
    serial: str | None = None,
    active: bool | None = None,
    resolver: str | None = None,
    rollout_state: str | None = None,
    sortby: Any = Token.serial,
    sortdir: str = "asc",
    psize: int = 15,
    page: int = 1,
    description: str | None = None,
    userid: str | None = None,
    allowed_realms: list[str] | None = None,
    tokeninfo: dict | None = None,
    hidden_tokeninfo: list[str] | None = None,
    container_serial: str | None = None,
) -> dict:
    """Return a paginated dict of token information for the Web UI.

    *serial* is treated as a wildcard pattern (``*``-matching) by default.
    If it contains commas but no ``*`` it is interpreted as a comma-separated
    list of exact serial numbers.

    :param tokentype: Single token type (may contain ``*``).
    :param token_type_list: List of exact token types.
    :param realm: Realm name / wildcard / comma-separated list.
    :param assigned: ``True`` → assigned, ``False`` → unassigned.
    :param user: Filter by token owner.
    :param serial: Wildcard serial pattern, or comma-separated exact serials.
    :param active: ``True`` → active, ``False`` → inactive.
    :param resolver: Resolver name (may contain ``*``).
    :param userid: User-id string (may contain ``*``).
    :param rollout_state: Rollout state (may contain ``*``).
    :param sortby: A :class:`Token` DB column or column name string.
    :param sortdir: ``"asc"`` (default) or ``"desc"``.
    :param psize: Number of tokens per page.
    :param page: 1-based page number.
    :param description: Token description filter (may contain ``*``).
    :param allowed_realms: Restrict results to these realms (admin policy).
    :param tokeninfo: Single-entry ``{key: value}`` dict.
    :param hidden_tokeninfo: Token-info keys to strip from output.
    :param container_serial: Container serial filter.
    :return: ``{"tokens": [...], "prev": int|None, "next": int|None, "count": int}``
    """
    # A comma-separated serial without wildcards → list of exact serials.
    # In paginate, bare serial is treated as a wildcard pattern.
    serial_wildcard = serial
    serial_list = None
    if serial and "*" not in serial and "," in serial:
        _, serial_list = _parse_serial(serial)
        serial_wildcard = None

    session: Session = db.session

    sql_query = _create_token_query(
        tokentype=tokentype, token_type_list=token_type_list,
        realm=realm, assigned=assigned, user=user,
        serial_wildcard=serial_wildcard, serial_list=serial_list,
        active=active, resolver=resolver, userid=userid,
        rollout_state=rollout_state, description=description,
        tokeninfo=tokeninfo, allowed_realms=allowed_realms,
        container_serial=container_serial,
    )

    # Resolve string column name → DB column.
    if isinstance(sortby, str):
        cols = Token.__table__.columns
        if sortby in cols:
            sortby = cols.get(sortby)
        else:
            log.warning(f'Unknown sort column "{sortby}". Using "serial" instead.')
            sortby = Token.serial

    sql_query = sql_query.order_by(sortby.desc() if sortdir == "desc" else sortby.asc())

    # Total count (before pagination).
    total_count = session.execute(
        select(func.count()).select_from(sql_query.subquery())
    ).scalar_one()

    # Fetch the requested page.
    offset = (page - 1) * psize
    db_tokens = session.scalars(
        sql_query.limit(psize).offset(offset)
    ).unique().all()

    token_objects = _db_tokens_to_objects(db_tokens)

    token_dicts = convert_token_objects_to_dicts(
        token_objects, user=None, user_role="admin",
        allowed_realms=allowed_realms,
        hidden_token_info=hidden_tokeninfo,
    )

    return {
        "tokens": token_dicts,
        "prev": page - 1 if page > 1 else None,
        "next": page + 1 if offset + psize < total_count else None,
        "count": total_count,
    }


def get_tokens_paginated_generator(
    tokentype: str | None = None,
    realm: str | None = None,
    assigned: bool | None = None,
    user: User | None = None,
    serial_wildcard: str | None = None,
    active: bool | None = None,
    resolver: str | None = None,
    rollout_state: str | None = None,
    revoked: bool | None = None,
    locked: bool | None = None,
    tokeninfo: dict | None = None,
    maxfail: bool | None = None,
    psize: int = 1000,
) -> Iterator[list[TokenClass]]:
    """Yield successive chunks of matching :class:`TokenClass` objects.

    Each yielded list contains at most *psize* elements (may be fewer when
    some DB rows have unknown token types).  Only non-empty lists are yielded.

    Uses keyset pagination (``Token.id > last_id``) for stable, efficient
    iteration over large result sets.

    See :func:`get_tokens` for the filter parameter documentation.
    """
    session = db.session

    base_query = _create_token_query(
        tokentype=tokentype, realm=realm, assigned=assigned, user=user,
        serial_wildcard=serial_wildcard, active=active, resolver=resolver,
        rollout_state=rollout_state, revoked=revoked, locked=locked,
        tokeninfo=tokeninfo, maxfail=maxfail,
    ).order_by(Token.id)

    last_id = None
    while True:
        page_query = base_query
        if last_id is not None:
            page_query = page_query.where(Token.id > last_id)
        page_query = page_query.limit(psize)

        db_tokens = session.scalars(page_query).unique().all()
        if not db_tokens:
            break

        token_objects = _db_tokens_to_objects(db_tokens)
        if token_objects:
            yield token_objects

        if len(db_tokens) < psize:
            break
        last_id = db_tokens[-1].id


# ---------------------------------------------------------------------------
# Token-to-dict conversion
# ---------------------------------------------------------------------------

def convert_token_objects_to_dicts(
    tokens: list[TokenClass],
    user: User | None,
    user_role: str = "user",
    allowed_realms: list[str] | None = None,
    hidden_token_info: list[str] | None = None,
) -> list[dict]:
    """Convert a list of :class:`TokenClass` objects to display dictionaries.

    Each dict is enriched with owner information (``username``,
    ``user_realm``, ``user_editable``) and ``container_serial``.

    Visibility rules:

    * Non-admin users only see the full dict for tokens they own; all
      other tokens are reduced to ``{"serial": …}``.
    * Admins with *allowed_realms* only see the full dict for tokens that
      share at least one realm with *allowed_realms*.

    :param tokens: Token objects to convert.
    :param user: The *requesting* user (for ownership checks).
    :param user_role: ``"admin"`` or ``"user"``.
    :param allowed_realms: Realms the admin is allowed to see (``None`` = all).
    :param hidden_token_info: Token-info keys to strip from the output.
    """
    # Lazy import to avoid circular dependency.
    from privacyidea.lib.container import find_container_for_token

    result: list[dict] = []
    for token in tokens:
        if not isinstance(token, TokenClass):
            continue

        token_dict = token.get_as_dict()

        # -- Owner information ----------------------------------------------
        token_dict["username"] = ""
        token_dict["user_realm"] = ""
        try:
            owner = token.user
            if owner:
                token_dict["username"] = owner.login
                token_dict["user_realm"] = owner.realm
                resolver_obj = get_resolver_object(owner.resolver)
                token_dict["user_editable"] = (
                    resolver_obj.editable if resolver_obj else False)
        except Exception as exc:
            log.error(f"User information can not be retrieved: {exc!s}")
            log.debug(traceback.format_exc())
            token_dict["username"] = "**resolver error**"

        # -- Hidden token info ----------------------------------------------
        if hidden_token_info:
            for key in hidden_token_info:
                token_dict.get("info", {}).pop(key, None)

        # -- Container membership -------------------------------------------
        container = find_container_for_token(token.get_serial())
        token_dict["container_serial"] = container.serial if container else ""

        # -- Visibility reduction -------------------------------------------
        if user_role != "admin":
            is_owner = (user
                        and user.login == token_dict["username"]
                        and user.realm == token_dict["user_realm"])
            if not is_owner:
                token_dict = {"serial": token_dict["serial"]}
        elif allowed_realms is not None:
            if not set(token_dict.get("realms", [])).intersection(allowed_realms):
                token_dict = {"serial": token_dict["serial"]}

        result.append(token_dict)

    return result


# ---------------------------------------------------------------------------
# Single-token convenience helpers
# ---------------------------------------------------------------------------

def get_one_token(
    *,
    silent_fail: bool = False,
    **kwargs: Any,
) -> TokenClass | None:
    """Return exactly one token matching the given filters.

    Raises :class:`ResourceNotFoundError` when no token matches and
    :class:`ParameterError` when more than one matches — unless
    *silent_fail* is ``True``, in which case ``None`` is returned instead.

    All keyword arguments are forwarded to :func:`get_tokens`.
    """
    kwargs.pop("count", None)  # get_one_token never counts
    tokens = get_tokens(**kwargs)
    assert isinstance(tokens, list)  # count is stripped, so result is always a list
    if not tokens:
        if silent_fail:
            return None
        raise ResourceNotFoundError(_("The requested token could not be found."))
    if len(tokens) > 1:
        if silent_fail:
            log.warning("More than one matching token was found.")
            return None
        raise ParameterError(_("More than one matching token was found."))
    return tokens[0]


def get_tokens_from_serial_or_user(
    serial: str | None,
    user: User | None,
    **kwargs: Any,
) -> list[TokenClass]:
    """Fetch tokens by exact *serial* or by *user*.

    When *serial* is given, exactly one token must exist (otherwise
    :class:`ResourceNotFoundError` is raised) and the result is a
    single-element list.  When only *user* is given, the result may be
    empty.

    Additional keyword arguments are forwarded to :func:`get_tokens`.
    """
    if serial:
        token = get_one_token(serial=serial, user=user, **kwargs)
        assert token is not None  # get_one_token raises on not-found when silent_fail is False
        return [token]
    kwargs.pop("count", None)
    tokens = get_tokens(serial=serial, user=user, **kwargs)
    assert isinstance(tokens, list)
    return tokens


# ---------------------------------------------------------------------------
# Simple look-up helpers
# ---------------------------------------------------------------------------

@log_with(log)
def get_token_type(serial: str) -> str:
    """Return the token type for *serial*, or ``""`` if not found.

    Wildcard serials (containing ``*``) always return ``""``.
    """
    if not serial or "*" in serial:
        return ""
    try:
        return get_one_token(serial=serial).type
    except ResourceNotFoundError:
        return ""


@log_with(log)
def check_serial(serial: str) -> tuple[bool, str]:
    """Check whether *serial* is available for a new token.

    Returns ``(True, serial)`` if the serial does not exist yet.
    Returns ``(False, new_serial)`` with a suggested alternative otherwise.
    """
    new_serial = serial
    i = 0
    while get_tokens(serial=new_serial):
        i += 1
        new_serial = f"{serial!s}_{i:02d}"
    return (i == 0), new_serial


@log_with(log)
def get_num_tokens_in_realm(realm: str, active: bool = True) -> int:
    """Return the number of (optionally active-only) tokens in *realm*."""
    return get_tokens(realm=realm, active=active, count=True)


@log_with(log)
def get_realms_of_token(serial: str) -> list[str]:
    """Return the list of realm names a token belongs to.

    Returns an empty list when the token does not exist, has no realms, or
    *serial* contains a ``*`` wildcard.
    """
    if not serial or "*" in serial:
        return []
    try:
        realms = get_one_token(serial=serial).get_realms()
    except ResourceNotFoundError:
        return []
    if len(realms) > 1:
        log.debug(f"Token {serial} in more than one realm: {realms}")
    return realms


@log_with(log)
def token_exist(serial: str) -> bool:
    """Return ``True`` if a token with the exact *serial* exists."""
    if not serial:
        return False
    return get_tokens(serial=serial, count=True) > 0


@log_with(log)
def get_token_owner(serial: str) -> User | None:
    """Return the owner of the token identified by *serial*.

    Returns ``None`` when the token has no owner.  Raises
    :class:`ResourceNotFoundError` when the token itself does not exist.
    """
    return get_one_token(serial=serial).user


@log_with(log)
def is_token_owner(serial: str, user: User) -> bool:
    """Return ``True`` if *user* is the owner of the token with *serial*."""
    owner = get_token_owner(serial)
    return owner is not None and owner == user


@log_with(log)
def get_tokens_in_resolver(resolver: str) -> list[TokenClass]:
    """Return all tokens whose owner is in *resolver*."""
    return get_tokens(resolver=resolver)


@log_with(log)
def get_tokenclass_info(tokentype: str, section: str | None = None) -> dict:
    """Return the class-info / config definition for *tokentype*.

    Returns an empty dict when the token type is unknown.
    """
    token_class = get_token_class(tokentype)
    if token_class:
        return token_class.get_class_info(section)
    return {}
