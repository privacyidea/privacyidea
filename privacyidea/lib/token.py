# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#
#  2018-12-10 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add Base58
#  2018-01-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add tokenkind
#  2017-08-11 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add auth_cache
#  2017-04-19 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add support for multiple challenge response token
#  2016-08-31 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Reset failcounter of all user tokens.
#  2016-06-21 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add next pin change response
#  2016-06-13 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add otp length to detail response
#  2015-10-14 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add timelimit to user auth.
#  2015-08-31 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add check_realm_pass for 4-eyes policy
#  2015-03-20 Cornelius Kölbel, <cornelius@privacyidea.org>
#             Add policy decorator for encryption
#  2015-03-15 Cornelius Kölbel, <cornelius@privacyidea.org>
#             Add policy decorator for lost_token password
#  2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#             Rewrite the module for operation with flask
#             assure >95% code coverage
#  2014-07-02 Cornelius Kölbel, <cornelius@privacyidea.org>
#             remove references to machines, when a token is deleted
#  2014-05-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
"""
This module contains all top level token functions.
It depends on the models, lib.user and lib.tokenclass (which depends on the
tokenclass implementations like lib.tokens.hotptoken)

This is the middleware/glue between the HTTP API and the database
"""

import traceback
import string
import datetime
import os
import logging

from sqlalchemy import (and_, func)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement
from privacyidea.lib.error import (TokenAdminError,
                                   ParameterError,
                                   privacyIDEAError, ResourceNotFoundError)
from privacyidea.lib.decorators import (check_user_or_serial,
                                        check_copy_serials)
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.utils import is_true, BASE58, hexlify_and_unicode, check_serial_valid
from privacyidea.lib.crypto import generate_password
from privacyidea.lib.log import log_with
from privacyidea.models import (Token, Realm, TokenRealm, Challenge,
                                MachineToken, TokenInfo, TokenOwner, TokenTokengroup, Tokengroup)
from privacyidea.lib.config import (get_token_class, get_token_prefix,
                                    get_token_types, get_from_config,
                                    get_inc_fail_count_on_false_pin, SYSCONF)
from privacyidea.lib.user import User
from privacyidea.lib import _
from privacyidea.lib.realm import realm_is_defined
from privacyidea.lib.resolver import get_resolver_object
from privacyidea.lib.policydecorators import (libpolicy,
                                              auth_user_does_not_exist,
                                              auth_user_has_no_token,
                                              auth_user_passthru,
                                              auth_user_timelimit,
                                              auth_lastauth,
                                              auth_cache,
                                              config_lost_token,
                                              reset_all_user_tokens)
from privacyidea.lib.challengeresponsedecorators import (generic_challenge_response_reset_pin,
                                                         generic_challenge_response_resync)
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.tokenclass import TOKENKIND
from dateutil.tz import tzlocal

log = logging.getLogger(__name__)

optional = True
required = False

ENCODING = "utf-8"


# Define function to convert Oracle CLOBs to VARCHAR before using them in a
# compare operation.
# By using <https://docs.sqlalchemy.org/en/13/core/compiler.html> we can
# differentiate between different dialects.
class clob_to_varchar(FunctionElement):
    name = 'clob_to_varchar'
    inherit_cache = True


@compiles(clob_to_varchar)
def fn_clob_to_varchar_default(element, compiler, **kw):
    return compiler.process(element.clauses, **kw)


@compiles(clob_to_varchar, 'oracle')
def fn_clob_to_varchar_oracle(element, compiler, **kw):
    return "to_char(%s)" % compiler.process(element.clauses, **kw)

@log_with(log)
def create_tokenclass_object(db_token):
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
            raise TokenAdminError(_("create_tokenclass_object failed:  {0!r}").format(e),
                                  id=1609)
    else:
        log.error('type {0!r} not found in tokenclasses'.format(tokentype))

    return token_object


def _create_token_query(tokentype=None, realm=None, assigned=None, user=None,
                        serial_exact=None, serial_wildcard=None, active=None, resolver=None,
                        rollout_state=None, description=None, revoked=None,
                        locked=None, userid=None, tokeninfo=None, maxfail=None, allowed_realms=None):
    """
    This function create the sql query for getting tokens. It is used by
    get_tokens and get_tokens_paginate.
    :return: An SQLAlchemy sql query
    """
    sql_query = Token.query
    if user is not None and not user.is_empty():
        # extract the realm from the user object:
        realm = user.realm

    if tokentype is not None and tokentype.strip("*"):
        # filter for type
        if "*" in tokentype:
            # match with "like"
            sql_query = sql_query.filter(Token.tokentype.like(
                tokentype.lower().replace("*", "%")))
        else:
            # exact match
            sql_query = sql_query.filter(func.lower(Token.tokentype) == tokentype.lower())

    if description is not None and description.strip("*"):
        # filter for Description
        if "*" in description:
            # match with "like"
            sql_query = sql_query.filter(func.lower(Token.description).like(
                description.lower().replace("*", "%")))
        else:
            # exact match
            sql_query = sql_query.filter(func.lower(Token.description) == description.lower())

    if assigned is not None:
        # filter if assigned or not
        if assigned is False:
            sql_query = sql_query.filter(Token.owners == None)
        elif assigned is True:
            sql_query = sql_query.filter(Token.owners)
        else:
            log.warning("assigned value not in [True, False] {0!r}".format(assigned))

    stripped_realm = None if realm is None else realm.strip("*")
    if stripped_realm:
        # filter for the realm
        if "*" in realm:
            sql_query = sql_query.filter(and_(func.lower(Realm.name).like(realm.replace("*", "%").lower()),
                                              TokenRealm.realm_id == Realm.id,
                                              TokenRealm.token_id == Token.id)).distinct()
        else:
            # exact matching
            sql_query = sql_query.filter(and_(func.lower(Realm.name) == realm.lower(),
                                              TokenRealm.realm_id == Realm.id,
                                              TokenRealm.token_id == Token.id)).distinct()

    if allowed_realms is not None:
        sql_query = sql_query.filter(and_(func.lower(Realm.name).in_([r.lower() for r in allowed_realms]),
                                          TokenRealm.realm_id == Realm.id,
                                          TokenRealm.token_id == Token.id)).distinct()

    stripped_resolver = None if resolver is None else resolver.strip("*")
    stripped_userid = None if userid is None else userid.strip("*")
    if stripped_userid or stripped_resolver:
        # Join the search with the token owner
        sql_query = sql_query.filter(TokenOwner.token_id == Token.id)

    if stripped_resolver:
        # filter for given resolver
        if "*" in resolver:
            # match with "like"
            sql_query = sql_query.filter(TokenOwner.resolver.like(resolver.replace(
                "*", "%")))
        else:
            sql_query = sql_query.filter(TokenOwner.resolver == resolver)

    if stripped_userid:
        # filter for given userid
        if "*" in userid:
            # match with "like"
            sql_query = sql_query.filter(TokenOwner.user_id.like(userid.replace(
                "*", "%")))
        else:
            sql_query = sql_query.filter(TokenOwner.user_id == userid)

    if serial_wildcard is not None and serial_wildcard.strip("*"):
        # filter for serial
        # match with "like"
        sql_query = sql_query.filter(Token.serial.like(serial_wildcard.replace(
            "*", "%")))

    if serial_exact is not None:
        # exact match for serial
        sql_query = sql_query.filter(Token.serial == serial_exact)

    if user is not None and not user.is_empty():
        # filter for the rest of the user.
        if user.resolver:
            sql_query = sql_query.filter(TokenOwner.token_id == Token.id)
            sql_query = sql_query.filter(TokenOwner.resolver == user.resolver)
        (uid, _rtype, _resolver) = user.get_user_identifiers()
        if uid:
            if type(uid) == int:
                uid = str(uid)
            sql_query = sql_query.filter(TokenOwner.token_id == Token.id)
            sql_query = sql_query.filter(TokenOwner.user_id == uid)

    if active is not None:
        # Filter active or inactive tokens
        if active is True:
            sql_query = sql_query.filter(Token.active == True)
        else:
            sql_query = sql_query.filter(Token.active == False)

    if revoked is not None:
        # Filter revoked or not revoked tokens
        if revoked is True:
            sql_query = sql_query.filter(Token.revoked == True)
        else:
            sql_query = sql_query.filter(Token.revoked == False)

    if locked is not None:
        # Filter revoked or not revoked tokens
        if locked is True:
            sql_query = sql_query.filter(Token.locked == True)
        else:
            sql_query = sql_query.filter(Token.locked == False)

    if maxfail is not None:
        # Filter tokens, that reached maxfail
        if maxfail is True:
            sql_query = sql_query.filter(Token.maxfail <= Token.failcount)
        else:
            sql_query = sql_query.filter(Token.maxfail > Token.failcount)

    if rollout_state is not None:
        # Filter for tokens with the given rollout state
        if "*" in rollout_state:
            # match with "like"
            sql_query = sql_query.filter(func.lower(Token.rollout_state).like(
                rollout_state.lower().replace("*", "%")))
        else:
            # exact match
            sql_query = sql_query.filter(func.lower(Token.rollout_state) == rollout_state.lower())

    if tokeninfo is not None:
        # Filter for tokens with token token.info.<key> and token.info.<value>
        if len(tokeninfo) != 1:
            raise privacyIDEAError(_("I can only create SQL filters from "
                                   "tokeninfo of length 1."))
        sql_query = sql_query.filter(TokenInfo.Key == list(tokeninfo)[0])
        sql_query = sql_query.filter(clob_to_varchar(TokenInfo.Value) == list(tokeninfo.values())[0])
        sql_query = sql_query.filter(TokenInfo.token_id == Token.id)

    return sql_query


def get_tokens_paginated_generator(tokentype=None, realm=None, assigned=None, user=None,
                                   serial_wildcard=None, active=None, resolver=None, rollout_state=None,
                                   revoked=None, locked=None, tokeninfo=None, maxfail=None, psize=1000):
    """
    Fetch chunks of ``psize`` tokens that match the filter criteria from the database and generate
    lists of token objects.
    See ``get_tokens`` for information on the arguments.

    Note that individual lists may contain less than ``psize`` elements if
    a token entry has an invalid type.

    :param psize: Maximum size of chunks that are fetched from the database
    :return: This is a generator that generates non-empty lists of token objects.
    """
    main_sql_query = _create_token_query(tokentype=tokentype, realm=realm,
                                         assigned=assigned, user=user,
                                         serial_wildcard=serial_wildcard,
                                         active=active, resolver=resolver,
                                         rollout_state=rollout_state,
                                         revoked=revoked, locked=locked,
                                         tokeninfo=tokeninfo, maxfail=maxfail).order_by(Token.id)
    # Fetch the first ``psize`` tokens
    sql_query = main_sql_query.limit(psize)
    while True:
        entries = sql_query.all()
        if entries:
            token_objects = []
            for token in entries:
                token_obj = create_tokenclass_object(token)
                if isinstance(token_obj, TokenClass):
                    token_objects.append(token_obj)
            yield token_objects
            if len(entries) < psize:
                break
            # Fetch the next ``psize`` tokens, starting with the ID *after* the ID of the last returned token.
            # ``token`` is defined because we have ensured that ``entries`` has at least one entry.
            sql_query = main_sql_query.filter(Token.id > token.id).limit(psize)
        else:
            break

@log_with(log)
#@cache.memoize(10)
def get_tokens(tokentype=None, realm=None, assigned=None, user=None,
               serial=None, serial_wildcard=None, active=None, resolver=None, rollout_state=None,
               count=False, revoked=None, locked=None, tokeninfo=None,
               maxfail=None):
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
    :param realm: get tokens of a realm. If None, all tokens are returned.
    :type realm: basestring
    :param assigned: Get either assigned (True) or unassigned (False) tokens.
        If None get all tokens.
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
    :return: A list of tokenclasses (lib.tokenclass).
    :rtype: list
    """
    token_list = []
    sql_query = _create_token_query(tokentype=tokentype, realm=realm,
                                    assigned=assigned, user=user,
                                    serial_exact=serial, serial_wildcard=serial_wildcard,
                                    active=active, resolver=resolver,
                                    rollout_state=rollout_state,
                                    revoked=revoked, locked=locked,
                                    tokeninfo=tokeninfo, maxfail=maxfail)

    # Warning for unintentional exact serial matches
    if serial is not None and "*" in serial:
        log.info("Exact match on a serial containing a wildcard: {!r}".format(serial))
    # Warning for unintentional wildcard serial matches
    if serial_wildcard is not None and "*" not in serial_wildcard:
        log.info("Wildcard match on serial without a wildcard: {!r}".format(serial_wildcard))

    # Decide, what we are supposed to return
    if count is True:
        ret = sql_query.count()
    else:
        # Return a simple, flat list of tokenobjects
        for token in sql_query.all():
            # the token is the database object, but we want an instance of the
            # tokenclass!
            tokenobject = create_tokenclass_object(token)
            if isinstance(tokenobject, TokenClass):
                # A database token, that has a non existing type, will
                # return None, and not a TokenClass. We do not want to
                # add None to our list
                token_list.append(tokenobject)
        ret = token_list

    return ret


@log_with(log)
def get_tokens_paginate(tokentype=None, realm=None, assigned=None, user=None,
                        serial=None, active=None, resolver=None, rollout_state=None,
                        sortby=Token.serial, sortdir="asc", psize=15,
                        page=1, description=None, userid=None, allowed_realms=None,
                        tokeninfo=None, hidden_tokeninfo=None):
    """
    This function is used to retrieve a token list, that can be displayed in
    the Web UI. It supports pagination.
    Each retrieved page will also contain a "next" and a "prev", indicating
    the next or previous page. If either does not exist, it is None.

    :param tokentype:
    :param realm:
    :param assigned: Returns assigned (True) or not assigned (False) tokens
    :type assigned: bool
    :param user: The user, whose token should be displayed
    :type user: User object
    :param serial: a pattern for matching the serial
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
    :return: dict with tokens, prev, next and count
    :rtype: dict
    """
    sql_query = _create_token_query(tokentype=tokentype, realm=realm,
                                assigned=assigned, user=user,
                                serial_wildcard=serial, active=active,
                                resolver=resolver, tokeninfo=tokeninfo,
                                rollout_state=rollout_state,
                                description=description, userid=userid,
                                allowed_realms=allowed_realms)

    if isinstance(sortby, str):
        # check that the sort column exists and convert it to a Token column
        cols = Token.__table__.columns
        if sortby in cols:
            sortby = cols.get(sortby)
        else:
            log.warning('Unknown sort column "{0!s}". Using "serial" '
                        'instead.'.format(sortby))
            sortby = Token.serial

    if sortdir == "desc":
        sql_query = sql_query.order_by(sortby.desc())
    else:
        sql_query = sql_query.order_by(sortby.asc())

    pagination = sql_query.paginate(page, per_page=psize,
                                    error_out=False)
    tokens = pagination.items
    prev = None
    if pagination.has_prev:
        prev = page-1
    next = None
    if pagination.has_next:
        next = page + 1
    token_list = []
    for token in tokens:
        tokenobject = create_tokenclass_object(token)
        if isinstance(tokenobject, TokenClass):
            token_dict = tokenobject.get_as_dict()
            # add user information
            # In certain cases the LDAP or SQL server might not be reachable.
            # Then an exception is raised
            token_dict["username"] = ""
            token_dict["user_realm"] = ""
            try:
                userobject = tokenobject.user
                if userobject:
                    token_dict["username"] = userobject.login
                    token_dict["user_realm"] = userobject.realm
                    token_dict["user_editable"] = get_resolver_object(
                        userobject.resolver).editable
            except Exception as exx:
                log.error("User information can not be retrieved: {0!s}".format(exx))
                log.debug(traceback.format_exc())
                token_dict["username"] = "**resolver error**"

            if hidden_tokeninfo:
                for key in list(token_dict['info']):
                    if key in hidden_tokeninfo:
                        token_dict['info'].pop(key)

            token_list.append(token_dict)

    ret = {"tokens": token_list,
           "prev": prev,
           "next": next,
           "current": page,
           "count": pagination.total}
    return ret


def get_one_token(*args, silent_fail=False, **kwargs):
    """
    Fetch exactly one token according to the given filter arguments, which are passed to
    ``get_tokens``. Raise ``ResourceNotFoundError`` if no token was found. Raise
    ``ParameterError`` if more than one token was found.

    :param silent_fail: Instead of raising an exception we return None silently
    :returns: Token object
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


def get_tokens_from_serial_or_user(serial, user, **kwargs):
    """
    Fetch tokens, either by (exact) serial, or all tokens of a single user.
    In case a serial number is given, check that exactly one token is returned
    and raise a ResourceNotFoundError if that is not the case.
    In case a user is given, the result can also be empty.

    :param serial: exact serial number or None
    :param user: a user object or None
    :param kwargs: additional argumens to ``get_tokens``
    :return: a (possibly empty) list of tokens
    :rtype: list
    """
    if serial:
        return [get_one_token(serial=serial, user=user, **kwargs)]
    else:
        return get_tokens(serial=serial, user=user, **kwargs)


@log_with(log)
def get_token_type(serial):
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
def check_serial(serial):
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
        new_serial = "{0!s}_{1:02d}".format(serial, i)

    return result, new_serial


@log_with(log)
def get_num_tokens_in_realm(realm, active=True):
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
def get_realms_of_token(serial, only_first_realm=False):
    """
    This function returns a list of the realms of a token

    :param serial: the exact serial number of the token
    :type serial: basestring

    :param only_first_realm: Wheather we should only return the first realm
    :type only_first_realm: bool

    :return: list of the realm names
    :rtype: list
    """
    if serial and "*" in serial:
        return []

    try:
        tokenobject = get_one_token(serial=serial)
        realms = tokenobject.get_realms()
    except ResourceNotFoundError:
        realms = []

    if len(realms) > 1:
        log.debug(
            "Token {0!s} in more than one realm: {1!s}".format(serial, realms))

    if only_first_realm:
        if realms:
            realms = realms[0]
        else:
            realms = None

    return realms


@log_with(log)
def token_exist(serial):
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
def get_token_owner(serial):
    """
    returns the user object, to which the token is assigned.
    the token is identified and retrieved by it's serial number

    If the token has no owner, None is returned

    Wildcards in the serial number are ignored. This raises
    ``ResourceNotFoundError`` if the token could not be found.

    :param serial: serial number of the token
    :type serial: basestring

    :return: The owner of the token
    :rtype: User object or None
    """
    tokenobject = get_one_token(serial=serial)
    return tokenobject.user


@log_with(log)
def is_token_owner(serial, user):
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
def get_tokens_in_resolver(resolver):
    """
    Return a list of the token ojects, that contain this very resolver

    :param resolver: The resolver, the tokens should be in
    :type resolver: basestring

    :return: list of tokens with this resolver
    :rtype: list of token objects
    """
    ret = get_tokens(resolver=resolver)
    return ret


@log_with(log)
def get_tokenclass_info(tokentype, section=None):
    """
    return the config definition of a dynamic token

    :param tokentype: the tokentype of the token like "totp" or "hotp"
    :type tokentype: basestring
    :param section: subsection of the token definition - optional
    :type section: basestring

    :return: dict - if nothing found an empty dict
    :rtype:  dict
    """
    res = {}
    Tokenclass = get_token_class(tokentype)
    if Tokenclass:
        res = Tokenclass.get_class_info(section)

    return res


@log_with(log)
def get_otp(serial, current_time=None):
    """
    This function returns the current OTP value for a given Token.
    The tokentype needs to support this function.
    if the token does not support getting the OTP value, a -2 is returned.
    If the token could not be found, ResourceNotFoundError is raised.

    :param serial: serial number of the token
    :param current_time: a fake servertime for testing of TOTP token
    :type current_time: datetime
    :return: tuple with (result, pin, otpval, passw)
    :rtype: tuple
    """
    tokenobject = get_one_token(serial=serial)
    return tokenobject.get_otp(current_time=current_time)



@log_with(log)
def get_multi_otp(serial, count=0, epoch_start=0, epoch_end=0,
                    curTime=None,
                    timestamp=None):
    """
    This function returns a list of OTP values for the given Token.
    Please note, that the tokentype needs to support this function.

    :param serial: the serial number of the token
    :type serial: basestring
    :param count: number of the next otp values (to be used with event or
        time based tokens)
    :param epoch_start: unix time start date (used with time based tokens)
    :param epoch_end: unix time end date (used with time based tokens)
    :param curTime: Simulate the servertime
    :type curTime: datetime
    :param timestamp: Simulate the servertime (unix time in seconds)
    :type timestamp: int

    :return: dictionary of otp values
    :rtype: dictionary
    """
    ret = {"result": False}
    tokenobject = get_one_token(serial=serial)
    log.debug("getting multiple otp values for token {0!r}. curTime={1!r}".format(tokenobject, curTime))

    res, error, otp_dict = tokenobject.\
        get_multi_otp(count=count,
                      epoch_start=epoch_start,
                      epoch_end=epoch_end,
                      curTime=curTime,
                      timestamp=timestamp)
    log.debug("received {0!r}, {1!r}, and {2!r} otp values".format(res, error,
                                                      len(otp_dict)))

    if res is True:
        ret = otp_dict
        ret["result"] = True
    else:
        ret["error"] = error

    return ret




@log_with(log)
def get_token_by_otp(token_list, otp="", window=10):
    """
    search the token in the token_list, that creates the given OTP value.
    The tokenobject_list would be created by get_tokens()

    :param token_list: the list of token objects to be investigated
    :type token_list: list of token objects
    :param otp: the otp value, that needs to be found
    :type otp: basestring
    :param window: the window of search
    :type window: int

    :return: The token, that creates this OTP value
    :rtype: Tokenobject
    """
    result_token = None
    result_list = []

    for token in token_list:
        log.debug("checking token {0!r}".format(token.get_serial()))
        try:
            r = token.check_otp_exist(otp=otp, window=window)
            log.debug("result = {0:d}".format(int(r)))
            if r >= 0:
                result_list.append(token)
        except Exception as err:
            # A flaw in a single token should not stop privacyidea from finding
            # the right token
            log.warning("error in calculating OTP for token {0!s}: "
                        "{1!s}".format(token.token.serial, err))

    if len(result_list) == 1:
        result_token = result_list[0]
    elif result_list:
        raise TokenAdminError(_('multiple tokens are matching this OTP value!'),
                              id=1200)

    return result_token


@log_with(log)
def get_serial_by_otp(token_list, otp="", window=10):
    """
    Returns the serial for a given OTP value
    The tokenobject_list would be created by get_tokens()

    :param token_list: the list of token objects to be investigated
    :type token_list: list of token objects
    :param otp: the otp value, that needs to be found
    :param window: the window of search
    :type window: int

    :return: the serial for a given OTP value and the user
    :rtype: basestring
    """
    serial = None
    token = get_token_by_otp(token_list, otp=otp, window=window)

    if token is not None:
        serial = token.get_serial()

    return serial


@log_with(log)
def gen_serial(tokentype=None, prefix=None):
    """
    generate a serial for a given tokentype

    :param tokentype: the token type prefix is done by a lookup on the tokens
    :type tokentype: str
    :param prefix: A prefix to the serial number
    :type prefix: str
    :return: serial number
    :rtype: str
    """
    serial_len = int(get_from_config("SerialLength") or 8)

    def _gen_serial(_prefix, _tokennum):
        h_serial = ''
        num_str = '{:04d}'.format(_tokennum)
        h_len = serial_len - len(num_str)
        if h_len > 0:
            h_serial = hexlify_and_unicode(os.urandom(h_len)).upper()[0:h_len]
        return "{0!s}{1!s}{2!s}".format(_prefix, num_str, h_serial)

    if not tokentype:
        tokentype = 'PIUN'
    if not prefix:
        prefix = get_token_prefix(tokentype.lower(), tokentype.upper())

    # now search the number of tokens of tokenytype in the token database
    tokennum = Token.query.filter(Token.tokentype == tokentype).count()

    # Now create the serial
    serial = _gen_serial(prefix, tokennum)

    # now test if serial already exists
    while True:
        numtokens = Token.query.filter(Token.serial == serial).count()
        if numtokens == 0:
            # ok, there is no such token, so we're done
            break
        serial = _gen_serial(prefix, tokennum + numtokens)  # pragma: no cover

    return serial


@log_with(log)
def import_token(serial, token_dict, tokenrealms=None):
    """
    This function is used during the import of a PSKC file.

    :param serial: The serial number of the token
    :type serial: str
    :param token_dict: A dictionary describing the token like

        ::

            {
              "type": ...,
              "description": ...,
              "otpkey": ...,
              "counter: ...,
              "timeShift": ...
            }

    :type token_dict: dict
    :param tokenrealms: List of realms to set as realms of the token
    :type tokenrealms: list
    :return: the token object
    """
    init_param = {'serial': serial,
                  'description': token_dict.get("description",
                                                "imported")}
    for p in ['type', 'otpkey', 'otplen', 'timeStep', 'hashlib', 'tans']:
        if p in token_dict:
            init_param[p] = token_dict[p]

    user_obj = None
    if token_dict.get("user"):
        user_obj = User(token_dict.get("user").get("username"),
                        token_dict.get("user").get("realm"),
                        token_dict.get("user").get("resolver"))

    # Imported tokens are usually hardware tokens
    token = init_token(init_param, user=user_obj,
                       tokenrealms=tokenrealms,
                       tokenkind=TOKENKIND.HARDWARE)
    if token_dict.get("counter"):
        token.set_otp_count(token_dict.get("counter"))
    if token_dict.get("timeShift"):
        token.add_tokeninfo("timeShift", token_dict.get("timeShift"))
    return token


@log_with(log)
def init_token(param, user=None, tokenrealms=None,
               tokenkind=None):
    """
    create a new token or update an existing token

    :param param: initialization parameters like

        ::

            {
                "serial": ..., (optional)
                "type": ...., (optional, default=hotp)
                "otpkey": ...
            }

    :type param: dict
    :param user: the token owner
    :type user: User Object
    :param tokenrealms: the realms, to which the token should belong
    :type tokenrealms: list
    :param tokenkind: The kind of the token, can be "software",
        "hardware" or "virtual"
    :return: token object or None
    :rtype: TokenClass
    """
    db_token = None
    tokenobject = None

    tokentype = param.get("type") or "hotp"
    serial = param.get("serial") or gen_serial(tokentype, param.get("prefix"))
    check_serial_valid(serial)
    realms = []

    # unsupported tokentype
    tokentypes = get_token_types()
    if tokentype.lower() not in tokentypes:
        log.error('type {0!r} not found in tokentypes: {1!r}'.format(tokentype, tokentypes))
        raise TokenAdminError(_("init token failed: unknown token type {0!r}").format(tokentype), id=1610)

    # Check, if a token with this serial already exist
    # create a list of the found tokens
    tokenobject_list = get_tokens(serial=serial)
    token_count = len(tokenobject_list)
    if token_count == 0:
        # A token with the serial was not found, so we create a new one
        db_token = Token(serial, tokentype=tokentype.lower())

    else:
        # The token already exist, so we update the token
        db_token = tokenobject_list[0].token
        # prevent from changing the token type
        old_typ = db_token.tokentype
        if old_typ.lower() != tokentype.lower():
            msg = ('token %r already exist with type %r. '
                   'Can not initialize token with new type %r' % (serial,
                                                                  old_typ,
                                                                  tokentype))
            log.error(msg)
            raise TokenAdminError(_("initToken failed: {0!s}").format(msg))

    # if there is a realm as parameter (and the realm is not empty), but no
    # user, we assign the token to this realm.
    if param.get("realm") and 'user' not in param:
        realms.append(param.get("realm"))
    # Assign the token to all tokenrealms
    if tokenrealms and isinstance(tokenrealms, list):
        realms.extend(tokenrealms)
    # and to the user realm
    if user and user.realm:
        realms.append(user.realm)

    try:
        # Save the token to the database
        if token_count == 0:
            db_token.save()

        # the tokenclass object is created
        tokenobject = create_tokenclass_object(db_token)

        if token_count == 0:
            # if this token is a newly created one, we have to setup the defaults,
            # which later might be overwritten by the tokenobject.update(param)
            tokenobject.set_defaults()

        # Set the user of the token
        if user is not None and user.login != "":
            tokenobject.add_user(user)

        # Set the token realms (updates the TokenRealm table)
        if realms or user:
            db_token.set_realms(realms)

        tokenobject.update(param)

    except Exception as e:
        log.error('token create failed: {0!s}'.format(e))
        log.debug("{0!s}".format(traceback.format_exc()))
        # delete the newly created token from the db
        if token_count == 0:
            db_token.delete()
        raise

    # We only set the tokenkind here, if it was explicitly set in the
    # init_token call.
    # In all other cases it is set in the update method of the tokenclass.
    if tokenkind:
        tokenobject.add_tokeninfo("tokenkind", tokenkind)

    # Set the validity period
    validity_period_start = param.get("validity_period_start")
    validity_period_end = param.get("validity_period_end")
    if validity_period_end:
        tokenobject.set_validity_period_end(validity_period_end)
    if validity_period_start:
        tokenobject.set_validity_period_start(validity_period_start)

    # Safe the token object to make sure all changes are persisted in the db
    tokenobject.save()
    return tokenobject


@log_with(log)
@check_user_or_serial
def remove_token(serial=None, user=None):
    """
    remove the token that matches the serial number or
    all tokens of the given user and also remove the realm associations and
    all its challenges

    :param user: The user, who's tokens should be deleted.
    :type user: User object
    :param serial: The serial number of the token to delete (exact)
    :type serial: basestring
    :return: The number of deleted token
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)
    token_count = len(tokenobject_list)

    # Delete challenges of such a token
    for tokenobject in tokenobject_list:
        tokenobject.delete_token()

    return token_count


@log_with(log)
def set_realms(serial, realms=None, add=False):
    """
    Set all realms of a token. This sets the realms new. I.e. it does not add
    realms. So realms that are not contained in the list will not be assigned
    to the token anymore.

    If the token could not be found, a ResourceNotFoundError is raised.

    Thus, setting ``realms=[]`` clears all realms assignments.

    :param serial: the serial number of the token (exact)
    :type serial: basestring
    :param realms: A list of realm names
    :type realms: list
    :param add: if the realms should be added and not replaced
    :type add: bool
    """
    realms = realms or []
    corrected_realms = []

    # get rid of non-defined realms
    for realm in realms:
        if realm_is_defined(realm):
            corrected_realms.append(realm)

    tokenobject = get_one_token(serial=serial)
    tokenobject.set_realms(corrected_realms, add=add)
    tokenobject.save()


@log_with(log)
def set_defaults(serial):
    """
    Set the default values for the token with the given serial number (exact)

    :param serial: token serial
    :type serial: basestring
    :return: None
    """
    db_token = get_one_token(serial=serial).token
    db_token.otplen = int(get_from_config("DefaultOtpLen", 6))
    db_token.count_window = int(get_from_config("DefaultCountWindow", 15))
    db_token.maxfail = int(get_from_config("DefaultMaxFailCount", 15))
    db_token.sync_window = int(get_from_config("DefaultSyncWindow", 1000))
    db_token.tokentype = "hotp"
    db_token.save()


@log_with(log)
def assign_token(serial, user, pin=None, encrypt_pin=False, err_message=None):
    """
    Assign token to a user.
    If the PIN is given, the PIN is reset.

    :param serial: The serial number of the token
    :type serial: basestring
    :param user: The user, to whom the token should be assigned.
    :type user: User object
    :param pin: The PIN for the newly assigned token.
    :type pin: basestring
    :param encrypt_pin: Whether the PIN should be stored in an encrypted way
    :type encrypt_pin: bool
    :param err_message: The error message, that is displayed in case the token is already assigned
    :type err_message: basestring
    """
    tokenobject = get_one_token(serial=serial)

    # Check if the token already belongs to another user
    old_user = tokenobject.user
    if old_user:
        log.warning("token already assigned to user: {0!r}".format(old_user))
        err_message = err_message or _("Token already assigned to user {0!r}").format(old_user)
        raise TokenAdminError(err_message, id=1103)

    tokenobject.add_user(user)
    if pin is not None:
        tokenobject.set_pin(pin, encrypt=encrypt_pin)

    # reset the OtpFailCounter
    tokenobject.set_failcount(0)

    try:
        tokenobject.save()
    except Exception as e:  # pragma: no cover
        log.error('update Token DB failed')
        raise TokenAdminError(_("Token assign failed for {0!r}/{1!s} : {2!r}").format(user, serial, e), id=1105)

    log.debug("successfully assigned token with serial "
              "{0!r} to user {1!r}".format(serial, user))
    return True


@log_with(log)
@check_user_or_serial
def unassign_token(serial, user=None):
    """
    unassign the user from the token, or all tokens of a user

    :param serial: The serial number of the token to unassign (exact). Can be None
    :param user: A user whose tokens should be unassigned
    :return: number of unassigned tokens
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)
    for tokenobject in tokenobject_list:
        tokenobject.set_pin("")
        tokenobject.set_failcount(0)

        try:
            # Delete the tokenowner entry
            TokenOwner.query.filter(TokenOwner.token_id == tokenobject.token.id).delete()
            tokenobject.save()
        except Exception as e:  # pragma: no cover
            log.error('update token DB failed')
            raise TokenAdminError(_("Token unassign failed for {0!r}/{1!r}: {2!r}").format(serial, user, e), id=1105)

        log.debug("successfully unassigned token with serial {0!r}".format(tokenobject))
    # TODO: test with more than 1 token
    return len(tokenobject_list)


@log_with(log)
def resync_token(serial, otp1, otp2, options=None, user=None):
    """
    Resynchronize the token of the given serial number and user by searching the
    otp1 and otp2 in the future otp values.

    :param serial: token serial number (exact)
    :type serial: str
    :param otp1: first OTP value
    :type otp1: str
    :param otp2: second OTP value, directly after the first
    :type otp2: str
    :param options: additional options like the servertime for TOTP token
    :type options: dict
    :return: result of the resync
    :rtype: bool
    """
    ret = False

    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        ret = tokenobject.resync(otp1, otp2, options)
        tokenobject.save()

    return ret


@log_with(log)
@check_user_or_serial
def reset_token(serial, user=None):
    """
    Reset the failcounter of a single token, or of all tokens of one user.

    :param serial: serial number (exact)
    :param user:
    :return: The number of tokens, that were reset
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.reset()
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_pin(serial, pin, user=None, encrypt_pin=False):
    """
    Set the token PIN of the token. This is the static part that can be used
    to authenticate.

    :param pin: The pin of the token
    :type pin: str
    :param user: If the user is specified, the pins for all tokens of this
        user will be set
    :type user: User object
    :param serial: If the serial is specified, the PIN for this very token
        will be set. (exact)
    :return: The number of PINs set (usually 1)
    :rtype: int
    """
    if isinstance(user, str):
        # check if by accident the wrong parameter (like PIN)
        # is put into the user attribute
        log.warning("Parameter user must not be a string: {0!r}".format(user))
        raise ParameterError(_("Parameter user must not be a string: {0!r}").format(
                             user), id=1212)

    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_pin(pin, encrypt=encrypt_pin)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
def set_pin_user(serial, user_pin, user=None):
    """
    This sets the user pin of a token. This just stores the information of
    the user pin for (e.g. an eTokenNG, Smartcard) in the database

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param user_pin: The user PIN
    :type user_pin: str
    :return: The number of PINs set (usually 1)
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_user_pin(user_pin)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
def set_pin_so(serial, so_pin, user=None):
    """
    Set the SO PIN of a smartcard. The SO Pin can be used to reset the
    PIN of a smartcard. The SO PIN is stored in the database, so that it
    could be used for automatic processes for User PIN resetting.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param so_pin: The Security Officer PIN
    :type so_pin: basestring
    :return: The number of SO PINs set. (usually 1)
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_so_pin(so_pin)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def revoke_token(serial, user=None):
    """
    Revoke a token, or all tokens of a single user.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param user: all tokens of the user will be enabled or disabled
    :type user: User object
    :return: Number of tokens that were enabled/disabled
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(user=user, serial=serial)

    for tokenobject in tokenobject_list:
        tokenobject.revoke()
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def enable_token(serial, enable=True, user=None):
    """
    Enable or disable a token, or all tokens of a single user.
    This can be checked with is_token_active.

    Enabling an already active token will return 0.

    :param serial: The serial number of the token
    :type serial: basestring
    :param enable: False is the token should be disabled
    :type enable: bool
    :param user: all tokens of the user will be enabled or disabled
    :type user: User object
    :return: Number of tokens that were enabled/disabled
    :rtype:
    """
    # We search for all matching tokens first, in case the user has
    # provided a wrong serial number. Then we filter for the desired tokens.
    tokenobject_list = get_tokens_from_serial_or_user(user=user, serial=serial)
    count = 0

    for tokenobject in tokenobject_list:
        if tokenobject.is_active() == (not enable):
            tokenobject.enable(enable)
            tokenobject.save()
            count += 1

    return count


def is_token_active(serial):
    """
    Return True if the token is active, otherwise false
    Raise ResourceError if the token could not be found.

    :param serial: The serial number of the token
    :type serial: basestring
    :return: True or False
    :rtype: bool
    """
    tokenobject = get_one_token(serial=serial)
    return tokenobject.token.active


@log_with(log)
@check_user_or_serial
def set_otplen(serial, otplen=6, user=None):
    """
    Set the otp length of the token defined by serial or for all tokens of
    the user.
    The OTP length is usually 6 or 8.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param otplen: The length of the OTP value
    :type otplen: int
    :param user: The owner of the tokens
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_otplen(otplen)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_hashlib(serial, hashlib="sha1", user=None):
    """
    Set the hashlib in the tokeninfo.
    Can be something like sha1, sha256...

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param hashlib: The hashlib of the token
    :type hashlib: basestring
    :param user: The User, for who's token the hashlib should be set
    :type user: User object
    :return: the number of token infos set
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_hashlib(hashlib)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_count_auth(serial, count, user=None, max=False, success=False):
    """
    The auth counters are stored in the token info database field.
    There are different counters, that can be set::

        count_auth -> max=False, success=False
        count_auth_max -> max=True, success=False
        count_auth_success -> max=False, success=True
        count_auth_success_max -> max=True, success=True

    :param count: The counter value
    :type count: int
    :param user: The user owner of the tokens tokens to modify
    :type user: User object
    :param serial: The serial number of the one token to modify (exact)
    :type serial: basestring
    :param max: True, if either count_auth_max or count_auth_success_max are
        to be modified
    :type max: bool
    :param success: True, if either ``count_auth_success`` or
        ``count_auth_success_max`` are to be modified
    :type success: bool
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        if max:
            if success:
                tokenobject.set_count_auth_success_max(count)
            else:
                tokenobject.set_count_auth_max(count)
        else:
            if success:
                tokenobject.set_count_auth_success(count)
            else:
                tokenobject.set_count_auth(count)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def add_tokeninfo(serial, info, value=None,
                  value_type=None,
                  user=None):
    """
    Sets a token info field in the database. The info is a dict for each
    token of key/value pairs.

    :param serial: The serial number of the token
    :type serial: basestring
    :param info: The key of the info in the dict
    :param value: The value of the info
    :param value_type: The type of the value. If set to "password" the value
        is stored encrypted
    :type value_type: basestring
    :param user: The owner of the tokens, that should be modified
    :type user: User object
    :return: the number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.add_tokeninfo(info, value)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def delete_tokeninfo(serial, key, user=None):
    """
    Delete a specific token info field in the database.

    :param serial: The serial number of the token
    :type serial: basestring
    :param key: The key of the info in the dict
    :param user: The owner of the tokens, that should be modified
    :type user: User object
    :return: the number of tokens matching the serial and user. This number also includes tokens that did not have
        the token info *key* set in the first place!
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)
    for tokenobject in tokenobject_list:
        tokenobject.del_tokeninfo(key)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_validity_period_start(serial, user, start):
    """
    Set the validity period for the given token.

    :param serial: serial number (exact)
    :param user:
    :param start: Timestamp in the format DD/MM/YY HH:MM
    :type start: basestring
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)
    for tokenobject in tokenobject_list:
        tokenobject.set_validity_period_start(start)
        tokenobject.save()
    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_validity_period_end(serial, user, end):
    """
    Set the validity period for the given token.

    :param serial: serial number (exact)
    :param user:
    :param end: Timestamp in the format DD/MM/YY HH:MM
    :type end: basestring
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)
    for tokenobject in tokenobject_list:
        tokenobject.set_validity_period_end(end)
        tokenobject.save()
    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_sync_window(serial, syncwindow=1000, user=None):
    """
    The sync window is the window that is used during resync of a token.
    Such many OTP values are calculated ahead, to find the matching otp value
    and counter.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param syncwindow: The size of the sync window
    :type syncwindow: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_sync_window(syncwindow)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_count_window(serial, countwindow=10, user=None):
    """
    The count window is used during authentication to find the matching OTP
    value. This sets the count window per token.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param countwindow: the size of the window
    :type countwindow: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_count_window(countwindow)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_description(serial, description, user=None):
    """
    Set the description of a token

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param description: The description for the token
    :type description: str
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_description(description)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_failcounter(serial, counter, user=None):
    """
    Set the fail counter of a  token.

    :param serial: The serial number of the token (exact)
    :param counter: THe counter to which the fail counter should be set
    :param user: An optional user
    :return: Number of tokens, where the fail counter was set.
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_failcount(counter)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_max_failcount(serial, maxfail, user=None):
    """
    Set the maximum fail counts of tokens. This is the maximum number a
    failed authentication is allowed.

    :param serial: The serial number of the token (exact)
    :type serial: basestring
    :param maxfail: The maximum allowed failed authentications
    :type maxfail: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens_from_serial_or_user(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_maxfail(maxfail)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_copy_serials
def copy_token_pin(serial_from, serial_to):
    """
    This function copies the token PIN from one token to the other token.
    This can be used for workflows like lost token.

    In fact the PinHash and the PinSeed are transferred

    :param serial_from: The token to copy from
    :type serial_from: basestring
    :param serial_to: The token to copy to
    :type serial_to: basestring

    :return: True. In case of an error raise an exception
    :rtype: bool
    """
    tokenobject_from = get_one_token(serial=serial_from)
    tokenobject_to = get_one_token(serial=serial_to)
    pinhash, seed = tokenobject_from.get_pin_hash_seed()
    tokenobject_to.set_pin_hash_seed(pinhash, seed)
    tokenobject_to.save()
    return True


@check_copy_serials
def copy_token_user(serial_from, serial_to):
    """
    This function copies the user from one token to the other token.
    In fact the user_id, resolver and resolver type are transferred.

    :param serial_from: The token to copy from
    :type serial_from: basestring
    :param serial_to: The token to copy to
    :type serial_to: basestring

    :return: True. In case of an error raise an exception
    :rtype: bool
    """
    tokenobject_from = get_one_token(serial=serial_from)
    tokenobject_to = get_one_token(serial=serial_to)

    # For backward compatibility we remove the potentially old users from the token.
    # TODO: Later we probably want to be able to "add" new users to a token.
    unassign_token(serial_to)
    TokenOwner(token_id=tokenobject_to.token.id,
               user_id=tokenobject_from.token.first_owner.user_id,
               realm_id=tokenobject_from.token.first_owner.realm_id,
               resolver=tokenobject_from.token.first_owner.resolver).save()
    # Also copy other assigned realms of the token.
    copy_token_realms(serial_from, serial_to)
    return True


@check_copy_serials
def copy_token_realms(serial_from, serial_to):
    """
    Copy the realms of one token to the other token

    :param serial_from: The token to copy from
    :param serial_to: The token to copy to
    :return: None
    """
    tokenobject_from = get_one_token(serial=serial_from)
    tokenobject_to = get_one_token(serial=serial_to)
    realm_list = tokenobject_from.token.get_realms()
    tokenobject_to.set_realms(realm_list)


@log_with(log)
@libpolicy(config_lost_token)
def lost_token(serial, new_serial=None, password=None,
               validity=10, contents="8", pw_len=16, options=None):
    """
    This is the workflow to handle a lost token.
    The token <serial> is lost and will be disabled. A new token of type
    password token will be created and assigned to the user.
    The PIN of the lost token will be copied to the new token.
    The new token will have a certain validity period.

    :param serial: Token serial number
    :param new_serial: new serial number
    :param password: new password
    :param validity: Number of days, the new token should be valid
    :type validity: int
    :param contents: The contents of the generated
        password. Can be a string like ``"Ccn"``.

            * "C": upper case characters
            * "c": lower case characters
            * "n": digits
            * "s": special characters
            * "8": base58
    :type contents: str
    :param pw_len: The length of the generated password
    :type pw_len: int
    :param options: optional values for the decorator passed from the upper
        API level
    :type options: dict
    :return: result dictionary
    :rtype: dict
    """
    res = {}
    new_serial = new_serial or "lost{0!s}".format(serial)
    user = get_token_owner(serial)

    log.debug("doing lost token for serial {0!r} and user {1!r}".format(serial, user))

    if user is None or user.is_empty():
        err = _("You can only define a lost token for an assigned token.")
        log.warning("{0!s}".format(err))
        raise TokenAdminError(err, id=2012)

    character_pool = "{0!s}{1!s}{2!s}".format(string.ascii_lowercase,
                                 string.ascii_uppercase, string.digits)
    if contents != "":
        character_pool = ""
        if "c" in contents:
            character_pool += string.ascii_lowercase
        if "C" in contents:
            character_pool += string.ascii_uppercase
        if "n" in contents:
            character_pool += string.digits
        if "s" in contents:
            character_pool += "!#$%&()*+,-./:;<=>?@[]^_"
        if "8" in contents:
            character_pool += BASE58

    if password is None:
        password = generate_password(size=pw_len, characters=character_pool)

    res['serial'] = new_serial

    tokenobject = init_token({"otpkey": password, "serial": new_serial,
                              "type": "pw",
                              "description": _("temporary replacement for {0!s}").format(
                                             serial)})

    res['init'] = tokenobject is not None
    if res['init']:
        res['user'] = copy_token_user(serial, new_serial)
        res['pin'] = copy_token_pin(serial, new_serial)

        # set validity period
        end_date = (datetime.datetime.now(tzlocal())
                    + datetime.timedelta(days=validity)).strftime(DATE_FORMAT)
        tokenobject_list = get_tokens(serial=new_serial)
        for tokenobject in tokenobject_list:
            tokenobject.set_validity_period_end(end_date)

        # fill results
        res['valid_to'] = "xxxx"
        res['password'] = password
        res['end_date'] = end_date
        # disable token
        res['disable'] = enable_token(serial, enable=False)

    return res


@log_with(log)
def check_realm_pass(realm, passw, options=None,
                     include_types=None, exclude_types=None):
    """
    This function checks, if the given passw matches any token in the given
    realm. This can be used for the 4-eyes token.
    Only tokens that are assigned are tested.

    The options dictionary may contain a key/value pair 'exclude_types' or
    'include_types' with the value containing a list of token types to
    exclude/include from/in the search.

    It returns the res True/False and a reply_dict, which contains the
    serial number of the matching token.

    :param realm: The realm of the user
    :param passw: The password containing PIN+OTP
    :param options: Additional options that are passed to the tokens
    :type options: dict
    :param include_types: List of token types to use for the check
    :type include_types: list or str
    :param exclude_types: List to token types *not* to use for the check
    :type exclude_types: list or str
    :return: tuple of bool and dict
    """
    reply_dict = {}
    # since an attacker does not know, which token is tested, we restrict to
    # only active tokens. He would not guess that the given OTP value is that
    #  of an inactive token.
    tokenobject_list = get_tokens(realm=realm, assigned=True, active=True)
    if not tokenobject_list:
        reply_dict["message"] = _("There is no active and assigned token in this realm")
        return False, reply_dict
    else:
        # reduce tokens by type
        if include_types:
            incl = include_types if isinstance(include_types, list) else [include_types]
            tokenobject_list = [tok for tok in tokenobject_list if tok.type in incl]
        elif exclude_types:
            excl = exclude_types if isinstance(exclude_types, list) else [exclude_types]
            tokenobject_list = [tok for tok in tokenobject_list if tok.type not in excl]

        if not tokenobject_list:
            reply_dict["message"] = _('There is no active and assigned token in '
                                      'this realm, included types: {0!s}, excluded '
                                      'types: {1!s}').format(include_types, exclude_types)
            return False, reply_dict

        return check_token_list(tokenobject_list, passw, options=options,
                                allow_reset_all_tokens=False)


@log_with(log)
@libpolicy(auth_lastauth)
def check_serial_pass(serial, passw, options=None):
    """
    This function checks the otp for a given serial

    If the OTP matches, True is returned and the otp counter is increased.

    The function tries to determine the user (token owner), to derive possible
    additional policies from the user.

    :param serial: The serial number of the token
    :type serial: basestring
    :param passw: The password usually consisting of pin + otp
    :type passw: basestring
    :param options: Additional options. Token specific.
    :type options: dict
    :return: tuple of result (True, False) and additional dict
    :rtype: tuple
    """
    reply_dict = {}
    tokenobject = get_one_token(serial=serial)
    res, reply_dict = check_token_list([tokenobject], passw,
                                       user=tokenobject.user,
                                       options=options,
                                       allow_reset_all_tokens=True)

    return res, reply_dict


@log_with(log)
def check_otp(serial, otpval):
    """
    This function checks the OTP for a given serial number

    :param serial:
    :param otpval:
    :return: tuple of result and dictionary containing a message if the
        verification failed
    :rtype: tuple(bool, dict)
    """
    reply_dict = {}
    tokenobject = get_one_token(serial=serial)
    res = tokenobject.check_otp(otpval) >= 0
    if not res:
        reply_dict["message"] = _("OTP verification failed.")
    return res, reply_dict


@libpolicy(auth_cache)
@libpolicy(auth_user_does_not_exist)
@libpolicy(auth_user_has_no_token)
@libpolicy(auth_user_timelimit)
@libpolicy(auth_lastauth)
@libpolicy(auth_user_passthru)
@log_with(log, hide_kwargs=["passw"])
def check_user_pass(user, passw, options=None):
    """
    This function checks the otp for a given user.
    It is called by the API /validate/check

    If the OTP matches, True is returned and the otp counter is increased.

    :param user: The user who is trying to authenticate
    :type user: User object
    :param passw: The password usually consisting of pin + otp
    :type passw: basestring
    :param options: Additional options. Token specific.
    :type options: dict
    :return: tuple of result (True, False) and additional dict
    :rtype: tuple
    """
    token_type = options.pop("token_type", None)
    tokenobject_list = get_tokens(user=user, tokentype=token_type)
    reply_dict = {}
    if not tokenobject_list:
        # The user has no tokens assigned
        res = False
        reply_dict["message"] = _("The user has no tokens assigned")
    else:
        tokenobject = tokenobject_list[0]
        res, reply_dict = check_token_list(tokenobject_list, passw,
                                           user=tokenobject.user,
                                           options=options,
                                           allow_reset_all_tokens=True)

    return res, reply_dict


def create_challenges_from_tokens(token_list, reply_dict, options=None):
    """
    Get a list of active tokens and create challenges for these tokens.
    The reply_dict is modified accordingly. The transaction_id and
    the messages are added to the reply_dict.

    :param token_list: The list of the token objects, that can do challenge response
    :param reply_dict: The dictionary that is passed to the API response
    :param options: Additional options. Passed from the upper layer
    :return: None
    """
    options = options or {}
    reply_dict["multi_challenge"] = []
    transaction_id = None
    message_list = []
    for token_obj in token_list:
        # Check if the max auth is succeeded
        if token_obj.check_all(message_list):
            r_chal, message, transaction_id, challenge_info = \
                token_obj.create_challenge(
                    transactionid=transaction_id, options=options)
            # Add the reply to the response
            message_list.append(message)
            if r_chal:
                challenge_info = challenge_info or {}
                challenge_info["transaction_id"] = transaction_id
                challenge_info["serial"] = token_obj.token.serial
                challenge_info["type"] = token_obj.get_tokentype()
                challenge_info["client_mode"] = token_obj.client_mode
                challenge_info["message"] = message
                # If exist, add next pin and next password change
                next_pin = token_obj.get_tokeninfo(
                        "next_pin_change")
                if next_pin:
                    challenge_info["next_pin_change"] = next_pin
                    challenge_info["pin_change"] = \
                        token_obj.is_pin_change()
                next_passw = token_obj.get_tokeninfo(
                        "next_password_change")
                if next_passw:
                    challenge_info["next_password_change"] = next_passw
                    challenge_info["password_change"] = \
                        token_obj.is_pin_change(
                            password=True)
                # FIXME: This is deprecated and should be remove one day
                reply_dict.update(challenge_info)
                reply_dict["multi_challenge"].append(challenge_info)
    if message_list:
        reply_dict["message"] = ", ".join(message_list)
    # The "messages" element is needed by some decorators
    reply_dict["messages"] = message_list
    # TODO: This line is deprecated: Add the information for the old administrative triggerchallenge
    reply_dict["transaction_ids"] = [chal.get("transaction_id") for chal in reply_dict.get("multi_challenge", [])]


def weigh_token_type(token_obj):
    """
    This method returns a weight of a token type, which is used
    to sort the tokentype list. Other weighing functions can be implemented.

    The Push token weighs the most, so that it will be sorted to the end.

    :param token_obj: token object
    :return: weight of the tokentype
    :rtype: int
    """
    if token_obj.type.upper() == "PUSH":
        return 1000
    else:
        return ord(token_obj.type[0])


@log_with(log, hide_args=[1])
@libpolicy(reset_all_user_tokens)
@libpolicy(generic_challenge_response_reset_pin)
@libpolicy(generic_challenge_response_resync)
def check_token_list(tokenobject_list, passw, user=None, options=None, allow_reset_all_tokens=False):
    """
    this takes a list of token objects and tries to find the matching token
    for the given passw. It also tests,
    * if the token is active or
    * the max fail count is reached,
    * if the validity period is ok...

    This function is called by check_serial_pass, check_user_pass and
    check_yubikey_pass.

    :param tokenobject_list: list of identified tokens
    :param passw: the provided passw (mostly pin+otp)
    :param user: the identified use - as class object
    :param options: additional parameters, which are passed to the token
    :param allow_reset_all_tokens: If set to True, the policy reset_all_user_tokens is evaluated to
        reset all user tokens accordingly. Note: This parameter is used in the decorator.

    :return: tuple of success and optional response
    :rtype: (bool, dict)
    """
    res = False
    reply_dict = {}
    increase_auth_counters = not is_true(get_from_config(key="no_auth_counter"))

    # add the user to the options, so that every token, that get passed the
    # options can see the user
    if options:
        options = options.copy()
    else:
        options = {}
    options.update({'user': user})

    # if there has been one token in challenge mode, we only handle challenges
    challenge_response_token_list = []
    challenge_request_token_list = []
    pin_matching_token_list = []
    invalid_token_list = []
    valid_token_list = []

    # Remove locked tokens from tokenobject_list
    if len(tokenobject_list) > 0:
        tokenobject_list = [token for token in tokenobject_list if not token.is_revoked()]

        if len(tokenobject_list) == 0:
            # If there is no unlocked token left.
            raise TokenAdminError(_("This action is not possible, since the "
                                    "token is locked"), id=1007)

    # Remove certain disabled tokens from tokenobject_list
    if len(tokenobject_list) > 0:
        tokenobject_list = [token for token in tokenobject_list if token.use_for_authentication(options)]

    for tokenobject in sorted(tokenobject_list, key=weigh_token_type):
        if log.isEnabledFor(logging.DEBUG):
            # Avoid a SQL query triggered by ``tokenobject.user`` in case
            # the log level is not DEBUG
            log.debug("Found user with loginId {0!r}: {1!r}".format(
                      tokenobject.user, tokenobject.get_serial()))

        if tokenobject.is_challenge_response(passw, user=user, options=options):
            # This is a challenge response and it still has a challenge DB entry
            if tokenobject.has_db_challenge_response(passw, user=user, options=options):
                challenge_response_token_list.append(tokenobject)
            else:
                # This is a transaction_id, that either never existed or has expired.
                # We add this to the invalid_token_list
                invalid_token_list.append(tokenobject)
        elif tokenobject.is_challenge_request(passw, user=user,
                                              options=options):
            # This is a challenge request
            challenge_request_token_list.append(tokenobject)
        else:
            # This is a normal authentication attempt
            try:
                # pass the length of the valid_token_list to ``authenticate`` so that
                # the push token can react accordingly
                options["valid_token_num"] = len(valid_token_list)
                pin_match, otp_count, repl = \
                    tokenobject.authenticate(passw, user, options=options)
            except TokenAdminError as tae:
                # Token is locked
                pin_match = False
                otp_count = -1
                repl = {'message': tae.message}
            repl = repl or {}
            reply_dict.update(repl)
            if otp_count >= 0:
                # This is a successful authentication
                valid_token_list.append(tokenobject)
            elif pin_match:
                # The PIN of the token matches
                pin_matching_token_list.append(tokenobject)
            else:
                # Nothing matches at all
                invalid_token_list.append(tokenobject)

    """
    There might be
    2 in pin_matching_token_list
    0 in valid_token_list
    10 in invalid_token_list
    0 in challenge_token_list.

    in this case, the failcounter of the 2 tokens in pin_matchting_token_list
    needs to be increased. And return False

    If there is
    0 pin_matching
    0 valid
    10 invalid
    0 challenge

    AND incFailCountOnFalsePin is True, then the failcounter of the
    10 invalid tokens need to be increased. And return False

    If there is
    X pin_matching
    1+ valid
    X invalid
    0 challenge

    Then the authentication with the valid tokens was successful and the
    <count> of the valid tokens need to be increased to the new count.
    """
    if valid_token_list:
        # One ore more successfully authenticating tokens found
        # We need to return success
        message_list = [_("matching {0:d} tokens").format(len(valid_token_list))]
        # write serial numbers or something to audit log
        for token_obj in valid_token_list:
            # Reset the failcounter, if there is a timeout set
            token_obj.check_reset_failcount()
            # Check if the max auth is succeeded.
            # We need to set the offsets, since we are in the n+1st authentication.
            if token_obj.check_all(message_list):
                if increase_auth_counters:
                    token_obj.inc_count_auth_success()

                # The token is active and the auth counters are ok.
                res = True
                if not reply_dict.get("type"):
                    reply_dict["type"] = token_obj.token.tokentype
                if reply_dict["type"] != token_obj.token.tokentype:
                    reply_dict["type"] = "undetermined"
                # reset the failcounter of valid token
                token_obj.reset()
                # Run the token post method. e.g. registration token deletes itself.
                token_obj.post_success()
        if len(valid_token_list) == 1:
            # If only one token was found, we add the serial number,
            # the token type and the OTP length
            reply_dict["serial"] = valid_token_list[0].token.serial
            reply_dict["type"] = valid_token_list[0].token.tokentype
            reply_dict["otplen"] = valid_token_list[0].token.otplen
            # If exist, add next pin and next password change
            next_pin = valid_token_list[0].get_tokeninfo("next_pin_change")
            if next_pin:
                reply_dict["next_pin_change"] = next_pin
                reply_dict["pin_change"] = valid_token_list[0].is_pin_change()
            next_passw = valid_token_list[0].get_tokeninfo(
                "next_password_change")
            if next_passw:
                reply_dict["next_password_change"] = next_passw
                reply_dict["password_change"] = valid_token_list[
                    0].is_pin_change(password=True)
        reply_dict["message"] = ", ".join(message_list)

    elif challenge_response_token_list:
        # The RESPONSE for a previous request of a challenge response token was
        # found.
        matching_challenge = False
        further_challenge = False
        for tokenobject in challenge_response_token_list:
            if tokenobject.check_challenge_response(passw=passw,
                                                    options=options) >= 0:
                reply_dict["serial"] = tokenobject.token.serial
                matching_challenge = True
                messages = []
                if not tokenobject.is_fit_for_challenge(messages, options=options):
                    messages.insert(0, _("Challenge matches, but token is not fit for challenge"))
                    reply_dict["message"] = ". ".join(messages)
                    log.info("Received a valid response to a "
                             "challenge for a non-fit token {0!s}. {1!s}".format(tokenobject.token.serial,
                                                                                 reply_dict["message"]))
                else:
                    # Challenge matches, token is active and token is fit for challenge
                    res = True
                    if increase_auth_counters:
                        tokenobject.inc_count_auth_success()
                    reply_dict["message"] = _("Found matching challenge")
                    # If exist, add next pin and next password change
                    next_pin = tokenobject.get_tokeninfo("next_pin_change")
                    if next_pin:
                        reply_dict["next_pin_change"] = next_pin
                        reply_dict["pin_change"] = tokenobject.is_pin_change()
                    next_passw = tokenobject.get_tokeninfo("next_password_change")
                    if next_passw:
                        reply_dict["next_password_change"] = next_passw
                        reply_dict["password_change"] = tokenobject.is_pin_change(password=True)
                    tokenobject.challenge_janitor()
                    if tokenobject.has_further_challenge(options):
                        # The token creates further challenges, so create the new challenge
                        # and new transaction_id
                        create_challenges_from_tokens([tokenobject], reply_dict, options)
                        further_challenge = True
                        res = False
                    else:
                        # This was the last successful challenge, so
                        # reset the fail counter of the challenge response token
                        tokenobject.reset()
                        tokenobject.post_success()

                    # clean up all challenges from this and other tokens. I.e.
                    # all challenges with this very transaction_id!
                    transaction_id = options.get("transaction_id") or \
                                     options.get("state")
                    Challenge.query.filter(Challenge.transaction_id == '' +
                                           transaction_id).delete()
                    # We have one successful authentication, so we bail out
                    break

        if not res and not further_challenge:
            # We did not find any successful response, so we need to increase the
            # failcounters
            for token_obj in challenge_response_token_list:
                if not token_obj.is_outofband():
                    token_obj.inc_failcount()
            if not matching_challenge:
                if len(challenge_response_token_list) == 1:
                    reply_dict["serial"] = challenge_response_token_list[0].token.serial
                    reply_dict["type"] = challenge_response_token_list[0].token.tokentype
                    reply_dict["message"] = _("Response did not match the challenge.")
                else:
                    reply_dict["message"] = _("Response did not match for "
                                              "{0!s} tokens.").format(len(challenge_response_token_list))

    elif challenge_request_token_list:
        # This is the initial REQUEST of a challenge response token
        active_challenge_token = [t for t in challenge_request_token_list
                                  if t.token.active]
        if len(active_challenge_token) == 0:
            reply_dict["message"] = _("No active challenge response token found")
        else:
            for token_obj in challenge_request_token_list:
                token_obj.check_reset_failcount()
                if is_true(options.get("increase_failcounter_on_challenge")):
                    token_obj.inc_failcount()
            create_challenges_from_tokens(active_challenge_token, reply_dict, options)

    elif pin_matching_token_list:
        # We did not find a valid token and no challenge.
        # But there are tokens, with a matching pin.
        # So we increase the failcounter. Return failure.
        for tokenobject in pin_matching_token_list:
            tokenobject.inc_failcount()
            if get_from_config(SYSCONF.RESET_FAILCOUNTER_ON_PIN_ONLY, False, return_bool=True):
                tokenobject.check_reset_failcount()
            reply_dict["message"] = _("wrong otp value")
            if len(pin_matching_token_list) == 1:
                # If there is only one pin matching token, we look if it was
                # a previous OTP value
                token = pin_matching_token_list[0]
                _r, pin, otp = token.split_pin_pass(passw)
                if token.is_previous_otp(otp):
                    reply_dict["message"] += _(". previous otp used again")
            if increase_auth_counters:
                for token_obj in pin_matching_token_list:
                    token_obj.inc_count_auth()
            # write the serial numbers to the audit log
            if len(pin_matching_token_list) == 1:
                reply_dict["serial"] = pin_matching_token_list[0].token.serial
                reply_dict["type"] = pin_matching_token_list[0].token.tokentype
                reply_dict["otplen"] = pin_matching_token_list[0].token.otplen

    elif invalid_token_list:
        # There were only tokens, that did not match the OTP value and
        # not even the PIN.
        # Depending of IncFailCountOnFalsePin, we increase the failcounter.
        reply_dict["message"] = _("wrong otp pin")
        if get_inc_fail_count_on_false_pin():
            for tokenobject in invalid_token_list:
                tokenobject.inc_failcount()
                if increase_auth_counters:
                    tokenobject.inc_count_auth()
    else:
        # There is no suitable token for authentication
        reply_dict["message"] = _("No suitable token found for authentication.")

    return res, reply_dict


def get_dynamic_policy_definitions(scope=None):
    """
    This returns the dynamic policy definitions that come with the new loaded
    token classes.

    :param scope: an optional scope parameter. Only return the policies of
        this scope.
    :return: The policy definition for the token or only for the scope.
    """
    from privacyidea.lib.policy import SCOPE, MAIN_MENU, GROUP

    pol = {SCOPE.ADMIN: {},
           SCOPE.USER: {},
           SCOPE.AUTH: {},
           SCOPE.ENROLL: {},
           SCOPE.WEBUI: {},
           SCOPE.AUTHZ: {}}
    for ttype in get_token_types():
        pol[SCOPE.ADMIN]["enroll{0!s}".format(ttype.upper())] \
            = {'type': 'bool',
               'desc': _("Admin is allowed to initialize {0!s} tokens.").format(ttype.upper()),
               'mainmenu': [MAIN_MENU.TOKENS],
               'group': GROUP.ENROLLMENT}

        conf = get_tokenclass_info(ttype, section='user')
        if 'enroll' in conf:
            pol[SCOPE.USER]["enroll{0!s}".format(ttype.upper())] = {
                'type': 'bool',
                'desc': _("The user is allowed to enroll a {0!s} token.").format(ttype.upper()),
                'mainmenu': [MAIN_MENU.TOKENS],
                'group': GROUP.ENROLLMENT}

        # now merge the dynamic Token policy definition
        # into the global definitions
        policy = get_tokenclass_info(ttype, section='policy')

        # get all policy sections like: admin, user, enroll, auth, authz
        pol_keys = list(pol)

        for pol_section in policy.keys():
            # if we have a dyn token definition of this section type
            # add this to this section - and make sure, that it is
            # then token type prefixed
            if pol_section in pol_keys:
                pol_entry = policy.get(pol_section)
                for pol_def in pol_entry:
                    set_def = pol_def
                    if pol_def.startswith(ttype) is not True:
                        set_def = '{0!s}_{1!s}'.format(ttype, pol_def)

                    pol[pol_section][set_def] = pol_entry.get(pol_def)

        # If the token class should provide specific PIN policies, now merge
        # PIN policies
        pin_scopes = get_tokenclass_info(ttype, section='pin_scopes') or []
        for pin_scope in pin_scopes:
            pol[pin_scope]['{0!s}_otp_pin_maxlength'.format(ttype.lower())] = {
                'type': 'int',
                'value': list(range(0, 32)),
                "desc": _("Set the maximum allowed PIN length of the {0!s}"
                          " token.").format(ttype.upper()),
                'group': GROUP.PIN
            }
            pol[pin_scope]['{0!s}_otp_pin_minlength'.format(ttype.lower())] = {
                'type': 'int',
                'value': list(range(0, 32)),
                "desc": _("Set the minimum required PIN length of the {0!s}"
                          " token.").format(ttype.upper()),
                'group': GROUP.PIN
            }
            pol[pin_scope]['{0!s}_otp_pin_contents'.format(ttype.lower())] = {
                'type': 'str',
                "desc": _("Specifiy the required PIN contents of the "
                          "{0!s} token. "
                          "(c)haracters, (n)umeric, "
                          "(s)pecial, (o)thers. [+/-]!").format(ttype.upper()),
                'group': GROUP.PIN
            }

    # return sub section, if scope is defined
    # make sure that scope is in the policy key
    # e.g. scope='_' is undefined and would break
    if scope and scope in pol:
        pol = pol[scope]

    return pol


def set_tokengroups(serial, tokengroups=None, add=False):
    """
    Set a list of tokengroups for one token

    :param serial: The serial of the token
    :param tokengroups: The list of tokengroups (names)
    :param add: Whether the list of tokengropus should be added
    :return:
    """
    tokengroups = tokengroups or []

    tokenobject = get_one_token(serial=serial)
    tokenobject.set_tokengroups(tokengroups, add=add)
    tokenobject.save()


def assign_tokengroup(serial, tokengroup=None, tokengroup_id=None):
    """
    Assign a new tokengroup to a token

    :param serial: The serial number of the token
    :param tokengroup: The name of the tokengroup
    :param tokengroup_id: alternatively the id of the tokengroup
    :return: True
    """
    tokenobject = get_one_token(serial=serial)
    try:
        return tokenobject.add_tokengroup(tokengroup, tokengroup_id)
    except Exception:
        raise ResourceNotFoundError(_("The tokengroup does not exist."))


def unassign_tokengroup(serial, tokengroup=None, tokengroup_id=None):
    """
    Removes a tokengroup from a token

    :param serial: The serial number of the token
    :param tokengroup: The name of the tokengroup
    :param tokengroup_id: alternatively the id of the tokengroup
    :return: True
    """
    try:
        tokenobject = get_one_token(serial=serial)
        return tokenobject.del_tokengroup(tokengroup, tokengroup_id)
    except Exception:
        raise ResourceNotFoundError(_("The tokengroup does not exist."))


def list_tokengroups(tokengroup=None):
    """
    Return a list of tokens that are assigned to a certain tokengroup
    If no tokengroup is specified, all groups/tokens are returned.

    :param tokengroup. The name of the token group
    :return:
    """
    tg = None
    if tokengroup:
        tg = Tokengroup.query.filter_by(name=tokengroup).first()
    if tg:
        tgs = TokenTokengroup.query.filter_by(tokengroup_id=tg.id).all()
    else:
        tgs = TokenTokengroup.query.all()

    return tgs
