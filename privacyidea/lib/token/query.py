# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Token lookup and retrieval helpers (read-only queries)."""

import logging
import traceback
from collections.abc import Iterator
from typing import Any

from flask_sqlalchemy.session import Session
from sqlalchemy import and_, func, or_, select
from sqlalchemy.sql import Select

from privacyidea.lib import _
from privacyidea.lib.config import (get_token_class)
from privacyidea.lib.error import (TokenAdminError,
                                   ParameterError,
                                   PrivacyIDEAError, ResourceNotFoundError, UserError)
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.log import log_with
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_object
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import (db, Token, Realm, TokenRealm, TokenInfo, TokenOwner, TokenContainer,
                                TokenContainerToken)
from privacyidea.models.utils import clob_to_varchar


log = logging.getLogger(__name__)



@log_with(log)
def create_tokenclass_object(db_token: Token) -> TokenClass | None:
    """
    (was createTokenClassObject)
    create a token class object from a given type
    If a tokenclass for this type does not exist,
    the function returns None.

    :param db_token: the database referenced token
    :type db_token: database token object
    :return: instance of the token class object
    :rtype: tokenclass object
    """
    # We use the tokentype from the database
    tokentype = db_token.tokentype.lower()
    token_object = None
    token_class = get_token_class(tokentype)
    if token_class:
        try:
            token_object = token_class(db_token)
        except Exception as e:  # pragma: no cover
            raise TokenAdminError(_("create_tokenclass_object failed: {0!r}").format(e),
                                  id=1609)
    else:
        log.error(f'type {tokentype!r} not found in tokenclasses')

    return token_object


def _create_token_query(tokentype: str | None = None, token_type_list: list[str] | None = None,
                        realm: str | None = None, assigned: bool | None = None, user: User | None = None,
                        serial_exact: str | None = None, serial_wildcard: str | None = None,
                        serial_list: list[str] | None = None, active: bool | None = None,
                        resolver: str | None = None, rollout_state: str | None = None,
                        description: str | None = None, revoked: bool | None = None,
                        locked: bool | None = None, userid: str | None = None, tokeninfo: dict | None = None,
                        maxfail: bool | None = None, allowed_realms: list[str] | None = None,
                        container_serial: str | None = None, all_nodes: bool = False) -> Select:
    session = db.session
    session.expire_all()

    sql_query = select(Token)

    # Conditional Joins at the top to avoid re-joining
    should_join_token_realm = (bool(realm and realm.strip("*")) or
                               allowed_realms is not None)
    should_join_token_owner = (bool(userid and userid.strip("*")) or
                               bool(resolver and resolver.strip("*")) or
                               bool(user) or
                               assigned is not None or
                               not all_nodes)

    if should_join_token_realm:
        sql_query = sql_query.outerjoin(TokenRealm, TokenRealm.token_id == Token.id)

    if should_join_token_owner:
        sql_query = sql_query.outerjoin(TokenOwner, Token.id == TokenOwner.token_id)

        # Filtering by realm and allowed_realms with exclusion logic
        if realm and realm.strip("*") and allowed_realms is not None:
            # Step 1: Find all realms that should be excluded (the intersection)
            # This subquery finds all token_ids that are in both the specified realm
            # and one of the allowed_realms.
            realm_id_subquery = select(Realm.id).where(
                func.lower(Realm.name) == realm.lower()
            )
            allowed_realms_ids = select(Realm.id).where(
                func.lower(Realm.name).in_([r.lower() for r in allowed_realms])
            )

            excluded_token_ids = (
                select(TokenRealm.token_id)
                .where(TokenRealm.realm_id.in_(realm_id_subquery))
                .intersect(
                    select(TokenRealm.token_id)
                    .where(TokenRealm.realm_id.in_(allowed_realms_ids))
                )
            )

            # Step 2: Apply the filters, excluding the intersection
            sql_query = sql_query.where(
                and_(
                    TokenRealm.realm_id.in_(realm_id_subquery),
                    TokenRealm.realm_id.in_(allowed_realms_ids),
                    Token.id.notin_(excluded_token_ids)
                )
            )
        else:
            # Fallback to existing logic if the specific condition is not met
            if realm and realm.strip("*"):
                if "*" in realm:
                    sql_query = sql_query.where(
                        TokenRealm.realm_id.in_(
                            select(Realm.id).where(func.lower(Realm.name).like(realm.lower().replace("*", "%")))
                        )
                    )
                else:
                    sql_query = sql_query.where(
                        TokenRealm.realm_id == select(Realm.id).where(
                            func.lower(Realm.name) == realm.lower()).scalar_subquery())

            if allowed_realms is not None:
                sql_query = sql_query.where(
                    TokenRealm.realm_id.in_(
                        select(Realm.id).where(func.lower(Realm.name).in_(allowed_realms))
                    )
                )

    # Filtering by tokentype
    if tokentype and tokentype.strip("*"):
        if "*" in tokentype:
            sql_query = sql_query.where(
                Token.tokentype.like(tokentype.lower().replace("*", "%"))
            )
        else:
            sql_query = sql_query.where(
                func.lower(Token.tokentype) == tokentype.lower()
            )

    # Filtering by token_type_list
    if token_type_list:
        sql_query = sql_query.where(
            Token.tokentype.in_([t.lower() for t in token_type_list])
        )

    # Filtering by description
    if description and description.strip("*"):
        if "*" in description:
            sql_query = sql_query.where(
                func.lower(Token.description).like(
                    description.lower().replace("*", "%")
                )
            )
        else:
            sql_query = sql_query.where(
                func.lower(Token.description) == description.lower()
            )

    # Filtering by assigned status
    if assigned is not None:
        if assigned:
            sql_query = sql_query.where(TokenOwner.id.is_not(None))
        else:
            sql_query = sql_query.where(TokenOwner.id.is_(None))

    # Filtering by serial
    if serial_wildcard and serial_wildcard.strip("*"):
        sql_query = sql_query.where(
            Token.serial.like(serial_wildcard.replace("*", "%"))
        )

    if serial_exact:
        sql_query = sql_query.where(Token.serial == serial_exact)

    if serial_list:
        sql_query = sql_query.where(Token.serial.in_(serial_list))

    # Filtering by user object
    if user and not user.is_empty():
        if user.login and not user.resolver:
            # A specific username was requested but could not be found in any
            # resolver. Raise the user error here instead of in the user class. The condition is the same.
            raise UserError("The user can not be found in any resolver in this realm!")
        else:
            if user.realm:
                realm_db = select(Realm).where(func.lower(Realm.name) == user.realm.lower())
                # Execute the subquery using the provided session
                realm_db_result = session.execute(realm_db).scalars().first()
                if realm_db_result:
                    sql_query = sql_query.where(TokenOwner.realm_id == realm_db_result.id)
                else:
                    raise ResourceNotFoundError(f"Realm '{user.realm}' does not exist.")
            if user.resolver:
                sql_query = sql_query.where(TokenOwner.resolver == user.resolver)
                (uid, _rtype, _resolver) = user.get_user_identifiers()
                if uid:
                    uid_str = str(uid) if isinstance(uid, int) else uid
                    sql_query = sql_query.where(TokenOwner.user_id == uid_str)

    # Filtering by token status flags
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

    # Filtering by rollout state
    if rollout_state and rollout_state.strip("*"):
        if "*" in rollout_state:
            sql_query = sql_query.where(
                func.lower(Token.rollout_state).like(
                    rollout_state.lower().replace("*", "%")
                )
            )
        else:
            sql_query = sql_query.where(
                func.lower(Token.rollout_state) == rollout_state.lower()
            )

    # Filtering by tokeninfo
    if tokeninfo is not None:
        if len(tokeninfo) != 1:
            raise PrivacyIDEAError(_("I can only create SQL filters from tokeninfo of length 1."))
        key, value = list(tokeninfo.items())[0]
        sql_query = sql_query.join(TokenInfo, TokenInfo.token_id == Token.id)
        sql_query = sql_query.where(TokenInfo.Key == key)
        sql_query = sql_query.where(clob_to_varchar(TokenInfo.Value) == value)

    # Filtering by container_serial
    if container_serial is not None:
        if not container_serial:
            sql_query = sql_query.outerjoin(
                TokenContainerToken,
                TokenContainerToken.token_id == Token.id
            ).where(TokenContainerToken.container_id.is_(None))
        else:
            subquery = select(TokenContainerToken.token_id).join(
                TokenContainer,
                TokenContainer.id == TokenContainerToken.container_id
            ).where(
                func.upper(TokenContainer.serial) == container_serial.upper()
            )
            sql_query = sql_query.where(Token.id.in_(subquery))

    # Node-specific resolver and realm configuration.
    if not all_nodes:
        local_node_uuid = get_app_config_value("PI_NODE_UUID")
        realms = get_realms()
        resolvers = []
        realms_to_filter = []

        for realm_name, realm_data in realms.items():
            added = False
            for res in realm_data.get("resolver", []):
                if res.get("name"):
                    if not res.get("node") or res["node"] == local_node_uuid:
                        resolvers.append(res["name"])
                        added = True
            if not added:
                realms_to_filter.append(realm_name)

        # Build the resolver filter condition
        resolver_filter = or_(
            TokenOwner.id.is_(None),
            TokenOwner.resolver.in_(resolvers),
        )

        # Re-join realm and explicitly include the join conditions in the filter to handle unassigned tokens
        # The realm join is now correctly placed within the `if not all_nodes` block.
        sql_query = sql_query.outerjoin(Realm, TokenOwner.realm_id == Realm.id)
        realm_filter = or_(
            TokenOwner.realm_id.is_(None),
            and_(
                func.lower(Realm.name).not_in([r.lower() for r in realms_to_filter]),
                TokenOwner.realm_id == Realm.id,
                TokenOwner.token_id == Token.id,
            )
        )

        # Combine all filters with the existing query using and_()
        sql_query = sql_query.where(and_(resolver_filter, realm_filter))

    # print(f"----------------------------- CREATE TOKEN QUERY -----------------------------")
    # from sqlalchemy.dialects import postgresql
    # print(sql_query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    # print("-------------------------------------------------------------------------------")
    return sql_query


def get_tokens_paginated_generator(tokentype: str | None = None, realm: str | None = None,
                                   assigned: bool | None = None, user: User | None = None,
                                   serial_wildcard: str | None = None, active: bool | None = None,
                                   resolver: str | None = None, rollout_state: str | None = None,
                                   revoked: bool | None = None, locked: bool | None = None,
                                   tokeninfo: dict | None = None, maxfail: bool | None = None,
                                   psize: int = 1000) -> Iterator[list[TokenClass]]:
    """
    Fetch chunks of ``psize`` tokens that match the filter criteria from the database and generate
    lists of token objects.
    See ``get_tokens`` for information on the arguments.

    Note that individual lists may contain less than ``psize`` elements if
    a token entry has an invalid type.

    :param psize: Maximum size of chunks that are fetched from the database
    :param assigned: Whether the token is assigned to a user
    :type assigned: bool or None
    :return: This is a generator that generates non-empty lists of token objects.
    """
    session = db.session
    main_sql_query = _create_token_query(
        tokentype=tokentype, realm=realm, assigned=assigned, user=user,
        serial_wildcard=serial_wildcard, active=active, resolver=resolver,
        rollout_state=rollout_state, revoked=revoked, locked=locked,
        tokeninfo=tokeninfo, maxfail=maxfail
    ).order_by(Token.id)

    last_id = None
    while True:
        sql_query = main_sql_query
        if last_id is not None:
            sql_query = sql_query.where(Token.id > last_id)
        sql_query = sql_query.limit(psize)
        tokens = session.scalars(sql_query).unique().all()
        if tokens:
            token_objects = []
            for token in tokens:
                token_obj = create_tokenclass_object(token)
                if isinstance(token_obj, TokenClass):
                    token_objects.append(token_obj)
            yield token_objects
            if len(tokens) < psize:
                break
            last_id = tokens[-1].id
        else:
            break


def convert_token_objects_to_dicts(tokens: list[TokenClass], user: User | None, user_role: str = "user",
                                   allowed_realms: list[str] | None = None,
                                   hidden_token_info: list[str] | None = None) -> list[dict]:
    """
    Convert a list of token objects to a list of dictionaries.
    Additionally, checks whether the requesting user is allowed to see the token information.
    If not it is reduced to the tokens serial.

    :param tokens: A list of token objects
    :type tokens: list
    :param user: The user object performing the request
    :type user: User object
    :param user_role: The role of the logged-in user
    :type user_role: str
    :param allowed_realms: A list of the realms the admin is allowed to see, None if the admin is allowed to see all
                           realms
    :param hidden_token_info: List of token-info keys to remove from the results
    :return: A list of dictionaries
    :rtype: list
    """
    token_dict_list = []
    for token in tokens:
        if isinstance(token, TokenClass):
            token_dict = token.get_as_dict()
            # add user information
            # In certain cases the LDAP or SQL server might not be reachable.
            # Then an exception is raised
            token_dict["username"] = ""
            token_dict["user_realm"] = ""
            try:
                token_owner = token.user
                if token_owner:
                    token_dict["username"] = token_owner.login
                    token_dict["user_realm"] = token_owner.realm
                    token_dict["user_editable"] = get_resolver_object(token_owner.resolver).editable
            except Exception as exx:
                log.error(f"User information can not be retrieved: {exx!s}")
                log.debug(traceback.format_exc())
                token_dict["username"] = "**resolver error**"

            if hidden_token_info:
                for key in list(token_dict['info']):
                    if key in hidden_token_info:
                        token_dict['info'].pop(key)

            # check if token is in a container
            token_dict["container_serial"] = ""
            from privacyidea.lib.container import find_container_for_token
            container = find_container_for_token(token.get_serial())
            if container:
                token_dict["container_serial"] = container.serial

            # Reduce token info if the user is not the owner
            if user_role != "admin":
                if not user or user.login != token_dict["username"] or user.realm != token_dict["user_realm"]:
                    token_dict = {"serial": token_dict["serial"]}
            elif user_role == "admin" and allowed_realms is not None:
                same_realms = list(set(token_dict["realms"]).intersection(allowed_realms))
                if len(same_realms) == 0:
                    # The token is in no realm the admin is allowed to see
                    token_dict = {"serial": token_dict["serial"]}

            token_dict_list.append(token_dict)

    return token_dict_list


@log_with(log)
# @cache.memoize(10)
def get_tokens(tokentype: str | None = None, token_type_list: list[str] | None = None, realm: str | None = None,
               assigned: bool | None = None, user: User | None = None,
               serial: str | None = None, serial_wildcard: str | None = None, active: bool | None = None,
               resolver: str | None = None, rollout_state: str | None = None,
               count: bool = False, revoked: bool | None = None, locked: bool | None = None,
               tokeninfo: dict | None = None,
               maxfail: bool | None = None, all_nodes: bool = False) -> list[TokenClass] | int:
    """
    (was getTokensOfType)
    This function returns a list of token objects of a
    * given type,
    * of a realm
    * or tokens with assignment or not
    * for a certain serial number or
    * for a User

    E.g. thus you can get all assigned tokens of type totp.

    :param tokentype: The type of the token. If None, all tokens are returned.
    :type tokentype: basestring
    :param token_type_list: A list of token types. If None or empty, all token types are returned.
    :type token_type_list: list
    :param realm: get tokens of a realm. If None, all tokens are returned. If allowed_realms is not None, it must
        contain this realm, otherwise no matching tokens will be found.
    :type realm: basestring
    :param assigned: Get either assigned (True) or unassigned (False) tokens. If None, gets all tokens.
    :type assigned: bool
    :param user: Filter for the Owner of the token
    :type user: User Object
    :param serial: The exact serial number of a token
    :type serial: basestring
    :param serial_wildcard: A wildcard to match token serials
    :type serial_wildcard: basestring
    :param active: Whether only active (True) or inactive (False) tokens
        should be returned
    :type active: bool
    :param resolver: filter for the given resolver name
    :type resolver: basestring
    :param rollout_state: returns a list of the tokens in the certain rollout
        state. Some tokens are not enrolled in a single step but in multiple
        steps. These tokens are then identified by the DB-column rollout_state.
    :param count: If set to True, only the number of the result and not the
        list is returned.
    :type count: bool
    :param revoked: Only search for revoked tokens or only for not revoked
        tokens
    :type revoked: bool
    :param locked: Only search for locked tokens or only for not locked tokens
    :type locked: bool
    :param tokeninfo: Return tokens with the given tokeninfo. The tokeninfo
        is a key/value dictionary
    :type tokeninfo: dict
    :param maxfail: If only tokens should be returned, which failcounter
        reached maxfail
    :param all_nodes: If True, ignore node specific realm configurations (default: False)
    :type all_nodes: bool
    :return: A list of lib.tokenclass objects.
    :rtype: list or int
    """
    serial_list = None
    if serial and "*" not in serial and "," in serial:
        serial_list = serial.replace(" ", "").split(",")
        serial = None

    sql_query = _create_token_query(tokentype=tokentype, token_type_list=token_type_list, realm=realm,
                                    assigned=assigned, user=user,
                                    serial_exact=serial, serial_wildcard=serial_wildcard, serial_list=serial_list,
                                    active=active, resolver=resolver,
                                    rollout_state=rollout_state,
                                    revoked=revoked, locked=locked,
                                    tokeninfo=tokeninfo, maxfail=maxfail, all_nodes=all_nodes)

    # Warning for unintentional exact serial matches
    if serial is not None and "*" in serial:
        log.info(f"Exact match on a serial containing a wildcard: {serial!r}")
    # Warning for unintentional wildcard serial matches
    if serial_wildcard is not None and "*" not in serial_wildcard:
        log.info(f"Wildcard match on serial without a wildcard: {serial_wildcard!r}")

    session: Session = db.session

    if count:
        ret = session.execute(
            select(func.count()).select_from(sql_query.subquery())
        ).scalar_one()
    else:
        tokens = session.execute(sql_query).unique().scalars().all()
        token_list = []
        for token in tokens:
            token = create_tokenclass_object(token)
            if isinstance(token, TokenClass):
                token_list.append(token)
        ret = token_list
    return ret


@log_with(log)
def get_tokens_paginate(tokentype: str | None = None, token_type_list: list[str] | None = None,
                        realm: str | None = None, assigned: bool | None = None, user: User | None = None,
                        serial: str | None = None, active: bool | None = None, resolver: str | None = None,
                        rollout_state: str | None = None,
                        sortby: Any = Token.serial, sortdir: str = "asc", psize: int = 15,
                        page: int = 1, description: str | None = None, userid: str | None = None,
                        allowed_realms: list[str] | None = None,
                        tokeninfo: dict | None = None, hidden_tokeninfo: list[str] | None = None,
                        container_serial: str | None = None) -> dict:
    """
    This function is used to retrieve a token list, that can be displayed in
    the Web UI. It supports pagination.
    Each retrieved page will also contain a "next" and a "prev", indicating
    the next or previous page. If either does not exist, it is None.

    :param tokentype:
    :param token_type_list: A list of token types
    :param realm: A realm the token is assigned to (if allowed_realms is not None, it must contain this realm,
        otherwise no matching tokens will be found)
    :param assigned: Returns assigned (True) or not assigned (False) tokens
    :type assigned: bool
    :param user: The user, whose token should be displayed
    :type user: User object
    :param serial: a pattern for matching the serial or a comma separated list of exact serials
    :param active: Returns active (True) or inactive (False) tokens
    :param resolver: A resolver name, which may contain "*" for filtering.
    :type resolver: basestring
    :param userid: A userid, which may contain "*" for filtering.
    :type userid: basestring
    :param rollout_state:
    :param sortby: Sort by a certain Token DB field. The default is
        Token.serial. If a string like "serial" is provided, we try to convert
        it to the DB column.
    :type sortby: A Token column or a string.
    :param sortdir: Can be "asc" (default) or "desc"
    :type sortdir: basestring
    :param psize: The size of the page
    :type psize: int
    :param page: The number of the page to view. Starts with 1 ;-)
    :type page: int
    :param allowed_realms: A list of realms, that the admin is allowed to see
    :type allowed_realms: list
    :param tokeninfo: Return tokens with the given tokeninfo. The tokeninfo
        is a key/value dictionary
    :param description: Take the description of the token into the query
    :type description: str
    :param hidden_tokeninfo: List of token-info keys to remove from the results
    :type hidden_tokeninfo: list
    :param container_serial: The serial number of a container
    :type container_serial: basestring
    :return: dict with tokens, prev, next and count
    :rtype: dict
    """
    serial_list = None
    if serial and "*" not in serial and "," in serial:
        serial_list = serial.replace(" ", "").split(",")
        serial = None
    session: Session = db.session
    session.commit()
    sql_query: Select = _create_token_query(tokentype=tokentype, token_type_list=token_type_list, realm=realm,
                                            assigned=assigned, user=user,
                                            serial_wildcard=serial, serial_list=serial_list, active=active,
                                            resolver=resolver, tokeninfo=tokeninfo,
                                            rollout_state=rollout_state,
                                            description=description, userid=userid,
                                            allowed_realms=allowed_realms, container_serial=container_serial)

    if isinstance(sortby, str):
        cols = Token.__table__.columns
        if sortby in cols:
            sortby = cols.get(sortby)
        else:
            log.warning(f'Unknown sort column "{sortby}". Using "serial" instead.')
            sortby = Token.serial

    if sortdir == "desc":
        sql_query = sql_query.order_by(sortby.desc())
    else:
        sql_query = sql_query.order_by(sortby.asc())

    session: Session = db.session

    # Get the total count from a query without limit/offset
    total_count = session.execute(
        select(func.count()).select_from(sql_query.subquery())
    ).scalar_one()

    # Now apply the limit and offset for the current page
    offset = (page - 1) * psize
    tokens = session.scalars(sql_query.limit(psize).offset(offset)).unique().all()

    token_list = []
    for token in tokens:
        # TODO first creating the object and then converting it to a dict, probably not efficient
        token = create_tokenclass_object(token)
        if isinstance(token, TokenClass):
            token_dict = token.get_as_dict()
            # add user information
            # In certain cases the LDAP or SQL server might not be reachable.
            # Then an exception is raised
            token_dict["username"] = ""
            token_dict["user_realm"] = ""
            try:
                user = token.user
                if user:
                    token_dict["username"] = user.login
                    token_dict["user_realm"] = user.realm
                    token_dict["user_editable"] = get_resolver_object(
                        user.resolver).editable
            except Exception as ex:
                log.error(f"User information can not be retrieved: {ex!r}")
                log.debug(traceback.format_exc())
                token_dict["username"] = "**resolver error**"

            if hidden_tokeninfo:
                for key in list(token_dict['info']):
                    if key in hidden_tokeninfo:
                        token_dict['info'].pop(key)

            # check if token is in a container
            token_dict["container_serial"] = ""
            from privacyidea.lib.container import find_container_for_token
            container = find_container_for_token(token.get_serial())
            if container:
                token_dict["container_serial"] = container.serial

            token_list.append(token_dict)

    previous_page = page - 1 if page > 1 else None
    next_page = page + 1 if offset + psize < total_count else None

    ret = {
        "tokens": token_list,
        "prev": previous_page,
        "next": next_page,
        "count": total_count
    }
    return ret


def get_one_token(*args: Any, silent_fail: bool = False, **kwargs: Any) -> TokenClass | None:
    """
    Fetch exactly one token according to the given filter arguments, which are passed to
    ``get_tokens``. Raise ``ResourceNotFoundError`` if no token was found. Raise
    ``ParameterError`` if more than one token was found.

    :param silent_fail: Instead of raising an exception we return None silently
    :returns: Token object
    :rtype: privacyidea.lib.tokenclass.TokenClass
    """
    result = get_tokens(*args, **kwargs)
    if not result:
        if silent_fail:
            return None
        raise ResourceNotFoundError(_("The requested token could not be found."))
    elif len(result) > 1:
        if silent_fail:
            log.warning("More than one matching token was found.")
            return None
        raise ParameterError(_("More than one matching token was found."))
    else:
        return result[0]


def get_tokens_from_serial_or_user(serial: str | None, user: User | None, **kwargs: Any) -> list[TokenClass]:
    """
    Fetch tokens, either by (exact) serial, or all tokens of a single user.
    In case a serial number is given, check that exactly one token is returned
    and raise a ResourceNotFoundError if that is not the case.
    In case a user is given, the result can also be empty.

    :param serial: exact serial number or None
    :param user: a user object or None
    :param kwargs: additional arguments to ``get_tokens``
    :return: a (possibly empty) list of tokens
    :rtype: list
    """
    if serial:
        return [get_one_token(serial=serial, user=user, **kwargs)]
    else:
        return get_tokens(serial=serial, user=user, **kwargs)


@log_with(log)
def get_token_type(serial: str) -> str:
    """
    Returns the tokentype of a given serial number. If the token does
    not exist or can not be determined, an empty string is returned.

    :param serial: the serial number of the to be searched token
    :type serial: string
    :return: tokentype
    :rtype: string
    """
    if serial and "*" in serial:
        return ""
    try:
        return get_one_token(serial=serial).type
    except ResourceNotFoundError:
        return ""


@log_with(log)
def check_serial(serial: str) -> tuple[bool, str]:
    """
    This checks, if the given serial number can be used for a new token.
    it returns a tuple (result, new_serial)
    result being True if the serial does not exist, yet.
    new_serial is a suggestion for a new serial number, that does not
    exist, yet.

    :param serial: Serial number to check if it can be used for
        a new token.
    :type serial: str
    :result: result of check and (new) serial number
    :rtype: tuple(bool, str)
    """
    # serial does not exist, yet
    result = True
    new_serial = serial

    i = 0
    while get_tokens(serial=new_serial):
        # as long as we find a token, modify the serial:
        i += 1
        result = False
        new_serial = f"{serial!s}_{i:02d}"

    return result, new_serial


@log_with(log)
def get_num_tokens_in_realm(realm: str, active: bool = True) -> int:
    """
    This returns the number of tokens in one realm.

    :param realm: The name of the realm
    :type realm: basestring
    :param active: If only active tokens should be taken into account
    :type active: bool
    :return: The number of tokens in the realm
    :rtype: int
    """
    return get_tokens(realm=realm, active=active, count=True)


@log_with(log)
def get_realms_of_token(serial: str, only_first_realm: bool = False) -> list[str] | str | None:
    """
    This function returns a list of the realms of a token

    :param serial: the exact serial number of the token
    :type serial: basestring

    :param only_first_realm: Whether we should only return the first realm
    :type only_first_realm: bool

    :return: list of the realm names
    :rtype: list
    """
    if serial and "*" in serial:
        return []

    try:
        token = get_one_token(serial=serial)
        realms = token.get_realms()
    except ResourceNotFoundError:
        realms = []

    if len(realms) > 1:
        log.debug(f"Token {serial} in more than one realm: {realms}")

    if only_first_realm:
        if realms:
            realms = realms[0]
        else:
            realms = None

    return realms


@log_with(log)
def token_exist(serial: str) -> bool:
    """
    returns true if the token with the exact given serial number exists

    :param serial: the serial number of the token
    """
    if serial:
        return get_tokens(serial=serial, count=True) > 0
    else:
        # If we have no serial we return false anyway!
        return False


@log_with(log)
def get_token_owner(serial: str) -> User | None:
    """
    returns the user object, to which the token is assigned.
    the token is identified and retrieved by its serial number

    If the token has no owner, None is returned

    Wildcards in the serial number are ignored. This raises
    ``ResourceNotFoundError`` if the token could not be found.

    :param serial: serial number of the token
    :type serial: basestring

    :return: The owner of the token
    :rtype: User object or None
    """
    token = get_one_token(serial=serial)
    return token.user


@log_with(log)
def is_token_owner(serial: str, user: User) -> bool:
    """
    Check if the given user is the owner of the token with the given serial
    number

    :param serial: The serial number of the token
    :type serial: str
    :param user: The user that needs to be checked
    :type user: User object
    :return: Return True or False
    :rtype: bool
    """
    ret = False
    token_owner = get_token_owner(serial)
    if token_owner is not None:
        ret = token_owner == user
    return ret


@log_with(log)
def get_tokens_in_resolver(resolver: str) -> list[TokenClass]:
    """
    Return a list of the token objects, that contain this very resolver

    :param resolver: The resolver, the tokens should be in
    :type resolver: basestring

    :return: list of tokens with this resolver
    :rtype: list of token objects
    """
    ret = get_tokens(resolver=resolver)
    return ret


@log_with(log)
def get_tokenclass_info(tokentype: str, section: str | None = None) -> dict:
    """
    return the config definition of a dynamic token

    :param tokentype: the tokentype of the token like "totp" or "hotp"
    :type tokentype: basestring
    :param section: subsection of the token definition - optional
    :type section: basestring

    :return: dictionary with the configuration definition of the token.
      If the token type is not found, an empty dictionary is returned
    :rtype: dict
    """
    res = {}
    tokenclass = get_token_class(tokentype)
    if tokenclass:
        res = tokenclass.get_class_info(section)

    return res
