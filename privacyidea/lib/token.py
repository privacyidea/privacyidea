# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#
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
import binascii
import os
import logging

from sqlalchemy import (and_, func)
from privacyidea.lib.error import TokenAdminError
from privacyidea.lib.error import ParameterError
from privacyidea.lib.decorators import (check_user_or_serial,
                                        check_copy_serials)
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.utils import generate_password
from privacyidea.lib.log import log_with
from privacyidea.models import (Token, Realm, TokenRealm, Challenge,
                                MachineToken)
from privacyidea.lib.config import get_from_config
from privacyidea.lib.config import (get_token_class, get_token_prefix,
                                    get_token_types,
                                    get_inc_fail_count_on_false_pin)
from privacyidea.lib.user import get_user_info
from gettext import gettext as _
from privacyidea.lib.realm import realm_is_defined
from privacyidea.lib.policydecorators import (libpolicy,
                                              auth_user_does_not_exist,
                                              auth_user_has_no_token,
                                              auth_user_passthru,
                                              config_lost_token)

log = logging.getLogger(__name__)

optional = True
required = False

ENCODING = "utf-8"


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
            raise TokenAdminError("create_tokenclass_object failed:  %r" % e,
                                  id=1609)
    else:
        log.error('type %r not found in tokenclasses' % tokentype)

    return token_object


def _create_token_query(tokentype=None, realm=None, assigned=None, user=None,
                        serial=None, active=None, resolver=None,
                        rollout_state=None, description=None, revoked=None,
                        locked=None):
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
            sql_query = sql_query.filter(func.lower(Token.tokentype) ==
                                         tokentype.lower())

    if description is not None and tokentype.strip("*"):
        # filter for Description
        if "*" in description:
            # match with "like"
            sql_query = sql_query.filter(Token.description.like(
                description.lower().replace("*", "%")))
        else:
            # exact match
            sql_query = sql_query.filter(func.lower(Token.description) ==
                                         description.lower())

    if assigned is not None:
        # filter if assigned or not
        if assigned is False:
            sql_query = sql_query.filter(Token.user_id == "")
        elif assigned is True:
            sql_query = sql_query.filter(Token.user_id != "")
        else:
            log.warning("assigned value not in [True, False] %r" % assigned)

    if realm is not None:
        # filter for the realm
        sql_query = sql_query.filter(and_(func.lower(Realm.name) ==
                                          realm.lower(),
                                          TokenRealm.realm_id == Realm.id,
                                          TokenRealm.token_id ==
                                          Token.id)).distinct()

    if resolver is not None:
        # filter for given resolver
        sql_query = sql_query.filter(Token.resolver == resolver)

    if serial is not None and serial.strip("*"):
        # filter for serial
        if "*" in serial:
            # match with "like"
            sql_query = sql_query.filter(Token.serial.like(serial.replace(
                "*", "%")))
        else:
            # exact match
            sql_query = sql_query.filter(Token.serial == serial)

    if user is not None and not user.is_empty():
        # filter for the rest of the user.
        if user.resolver:
            sql_query = sql_query.filter(Token.resolver == user.resolver)
        (uid, _rtype, _resolver) = user.get_user_identifiers()
        if uid:
            sql_query = sql_query.filter(Token.user_id == uid)

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

    if rollout_state is not None:
        # Filter for tokens with the given rollout state
        sql_query = sql_query.filter(Token.rollout_state == rollout_state)
    return sql_query


@log_with(log)
#@cache.memoize(10)
def get_tokens(tokentype=None, realm=None, assigned=None, user=None,
               serial=None, active=None, resolver=None, rollout_state=None,
               count=False, revoked=None, locked=None):
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
    :param serial: The serial number of the token
    :type serial: basestring
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

    :return: A list of tokenclasses (lib.tokenclass)
    :rtype: list
    """
    token_list = []
    sql_query = _create_token_query(tokentype=tokentype, realm=realm,
                                    assigned=assigned, user=user,
                                    serial=serial, active=active,
                                    resolver=resolver,
                                    rollout_state=rollout_state,
                                    revoked=revoked, locked=locked)

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
                page=1, description=None):
    """
    This function is used to retrieve a token list, that can be displayed in
    the Web UI. It supports pagination.
    Each retrieved page will also contain a "next" and a "prev", indicating
    the next or previous page. If either does not exist, it is None.

    :param tokentype:
    :param realm:
    :param assigned: Returns assigned (True) or not assigned (False) tokens
    :type assigned: bool
    :param user: The user, whos token should be displayed
    :type user: User object
    :param serial:
    :param active:
    :param resolver:
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
    :return: dict with tokens, prev, next and count
    :rtype: dict
    """
    sql_query = _create_token_query(tokentype=tokentype, realm=realm,
                                assigned=assigned, user=user,
                                serial=serial, active=active,
                                resolver=resolver,
                                rollout_state=rollout_state,
                                description=description)

    if type(sortby) in [str, unicode]:
        # convert the string to a Token column
        cols = Token.__table__.columns
        sortby = cols.get(sortby)

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
                userobject = tokenobject.get_user()
                if userobject:
                    token_dict["username"] = userobject.login
                    token_dict["user_realm"] = userobject.realm
            except Exception as exx:
                log.error("User information can not be retrieved: %s" % exx)
                token_dict["username"] = "**resolver error**"

            token_list.append(token_dict)

    ret = {"tokens": token_list,
           "prev": prev,
           "next": next,
           "current": page,
           "count": pagination.total}
    return ret


@log_with(log)
def get_token_type(serial):
    """
    Returns the tokentype of a given serial number

    :param serial: the serial number of the to be searched token
    :type serial: string
    :return: tokentype
    :rtype: string
    """
    tokenobject_list = get_tokens(serial=serial)

    tokentype = ""
    for tokenobject in tokenobject_list:
        tokentype = tokenobject.type

    return tokentype

@log_with(log)
def check_serial(serial):
    """
    This checks, if the given serial number can be used for a new token.
    it returns a tuple (result, new_serial)
    result being True if the serial does not exist, yet.
    new_serial is a suggestion for a new serial number, that does not
    exist, yet.

    :param serial: Seral number that is to be checked, if it can be used for
    a new token.
    :type serial: string
    :result: bool and serial number
    :rtype: tuple
    """
    # serial does not exist, yet
    result = True
    new_serial = serial

    i = 0
    while len(get_tokens(serial=new_serial)) > 0:
        # as long as we find a token, modify the serial:
        i += 1
        result = False
        new_serial = "%s_%02i" % (serial, i)

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
def get_realms_of_token(serial):
    """
    This function returns a list of the realms of a token

    :param serial: the serial number of the token
    :type serial: basestring

    :return: list of the realm names
    :rtype: list
    """
    tokenobject_list = get_tokens(serial=serial)

    realms = []
    for tokenobject in tokenobject_list:
        realms = tokenobject.get_realms()

    return realms


@log_with(log)
def token_exist(serial):
    """
    returns true if the token with the given serial number exists

    :param serial: the serial number of the token
    """
    if serial:
        return get_tokens(serial=serial, count=True) > 0
    else:
        # If we have no serial we return false anyway!
        return False


@log_with(log)
def token_has_owner(serial):
    """
    returns true if the token is owned by any user
    """
    return get_tokens(serial=serial, count=True, assigned=True) > 0


@log_with(log)
def get_token_owner(serial):
    """
    returns the user object, to which the token is assigned.
    the token is identified and retrieved by it's serial number

    If the token has no owner, None is returned

    :param serial: serial number of the token
    :type serial: basestring

    :return: The owner of the token
    :rtype: User object or None
    """
    user = None

    tokenobject_list = get_tokens(serial=serial)

    if len(tokenobject_list) > 0:
        if token_has_owner(serial):
            tokenobject = tokenobject_list[0]
            user = tokenobject.get_user()

    return user


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
def get_all_token_users():
    """
    return a dictionary with all tokens, that are assigned to users.
    This returns a dictionary with the key being the serial number of
    the token and the user information as dict.

    :return: dictionary of serial numbers
    :rtype: dict
    """
    tokens = {}
    tokenobject_list = get_tokens(assigned=True)

    for tokenobject in tokenobject_list:
        user_info = {}
        if len(tokenobject.token.user_id) > 0 and len(
                tokenobject.token.resolver) > 0:
            user_info = get_user_info(tokenobject.token.user_id,
                                      tokenobject.token.resolver)

        if len(tokenobject.token.user_id) > 0 and len(user_info) == 0:
            user_info['username'] = u'/:no user info:/'

        if len(user_info) > 0:
            tokens[tokenobject.token.serial] = user_info

    return tokens


@log_with(log)
def get_otp(serial, current_time=None):
    """
    This function returns the current OTP value for a given Token.
    The tokentype needs to support this function.
    if the token does not support getting the OTP value, a -2 is returned.

    :param serial: serial number of the token
    :param current_time: a fake servertime for testing of TOTP token
    :type current_time: datetime
    :return: tuple with (result, pin, otpval, passw)
    :rtype: tuple
    """
    tokenobject_list = get_tokens(serial=serial)

    if len(tokenobject_list) == 0:
        log.warning("there is no token with serial %r" % serial)
        return -1, "", "", ""

    tokenobject = tokenobject_list[0]

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
    tokenobject_list = get_tokens(serial=serial)
    if len(tokenobject_list) == 0:
        log.warning("there is no token with serial %r" % serial)
        ret["error"] = "No token with serial %s found." % serial

    else:
        tokenobject = tokenobject_list[0]
        log.debug("getting multiple otp values for token %r. curTime=%r" %
                  (tokenobject, curTime))

        res, error, otp_dict = tokenobject.\
            get_multi_otp(count=count,
                          epoch_start=epoch_start,
                          epoch_end=epoch_end,
                          curTime=curTime,
                          timestamp=timestamp)
        log.debug("received %r, %r, and %r otp values" % (res, error,
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
        log.debug("checking token %r" % token.get_serial())
        r = token.check_otp_exist(otp=otp, window=window)
        log.debug("result = %d" % int(r))
        if r >= 0:
            result_list.append(token)

    if len(result_list) == 1:
        result_token = result_list[0]
    elif len(result_list) > 1:
        raise TokenAdminError('multiple tokens are matching this OTP value!',
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
def get_tokenserial_of_transaction(transaction_id):
    """
    get the serial number of a token from a challenge state / transaction

    :param transaction_id: the state / transaction id
    :type transaction_id: basestring
    :return: the serial number or None
    :rtype: basestring
    """
    serial = None

    challenge = Challenge.query.filter(Challenge.transaction_id == u'' +
                                      transaction_id).first()

    if challenge:
        serial = challenge.serial
    else:
        log.info('no challenge found for transaction_id %r' % transaction_id)

    return serial


@log_with(log)
def gen_serial(tokentype=None, prefix=None):
    """
    generate a serial for a given tokentype

    :param tokentype: the token type prefix is done by a lookup on the tokens
    :param prefix: A prefix to the serial number
    :return: serial number
    :rtype: string
    """
    def _gen_serial(_prefix, _tokennum):
        h_serial = ''
        num_str = '%.4d' % _tokennum
        h_len = 8 - len(num_str)
        if h_len > 0:
            h_serial = binascii.hexlify(os.urandom(h_len)).upper()[0:h_len]
        return "%s%s%s" % (_prefix, num_str, h_serial)

    if not tokentype:
        tokentype = 'PIUN'
    if not prefix:
        prefix = get_token_prefix(tokentype.lower(), tokentype.upper())

    # now search the number of tokens of tokenytype in the token database
    tokennum = Token.query.filter(Token.tokentype == u'' + tokentype).count()

    # Now create the serial
    serial = _gen_serial(prefix, tokennum)

    # now test if serial already exists
    while True:
        numtokens = Token.query.filter(Token.serial == u'' + serial).count()
        if numtokens == 0:
            # ok, there is no such token, so we're done
            break
        serial = _gen_serial(prefix, tokennum + numtokens)  # pragma: no cover

    return serial


@log_with(log)
def init_token(param, user=None, tokenrealms=None):
    """
    create a new token or update an existing token

    :param param: initialization parameters like:
                  serial (optional)
                  type (optionl, default=hotp)
                  otpkey
    :type param: dict
    :param user: the token owner
    :type user: User Object
    :param tokenrealms: the realms, to which the token should belong
    :type tokenrealms: list

    :return: token object or None
    :rtype: TokenClass object
    """
    db_token = None
    tokenobject = None

    tokentype = param.get("type") or "hotp"
    serial = param.get("serial") or gen_serial(tokentype, param.get("prefix"))
    realms = []

    # unsupported tokentype
    tokentypes = get_token_types()
    if tokentype.lower() not in tokentypes:
        log.error('type %r not found in tokentypes: %r' %
                  (tokentype, tokentypes))
        raise TokenAdminError("init token failed: unknown token type %r"
                               % tokentype, id=1610)

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
            raise TokenAdminError("initToken failed: %s" % msg)

    # if there is a realm as parameter, but no user, we assign the token to
    # this realm.
    if 'realm' in param and 'user' not in param:
        realms.append(param.get("realm"))
    # Assign the token to all tokenrealms
    if tokenrealms and isinstance(tokenrealms, list):
        realms.extend(tokenrealms)
    # and to the user realm
    if user and user.realm:
        realms.append(user.realm)
    if realms:
        # We need to save the token to the DB, otherwise the Token
        # has no id!
        db_token.save()
        db_token.set_realms(realms)

    # the tokenclass object is created
    tokenobject = create_tokenclass_object(db_token)

    if token_count == 0:
        # if this token is a newly created one, we have to setup the defaults,
        # which later might be overwritten by the tokenobject.update(param)
        tokenobject.set_defaults()

    upd_params = param
    tokenobject.update(upd_params)

    # Set the user of the token
    if user is not None and user.login != "":
        tokenobject.set_user(user)

    try:
        # Save the token to the database
        db_token.save()
    except Exception as e:  # pragma: no cover
        log.error('token create failed!')
        log.error("%r" % (traceback.format_exc()))
        raise TokenAdminError("token create failed %r" % e, id=1112)

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
    :param serial: The serial number of the token to delete
    :type serial: basestring
    :return: The number of deleted token
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)
    token_count = len(tokenobject_list)

    # Delete challenges of such a token
    for tokenobject in tokenobject_list:
        # delete the challenge
        Challenge.query.filter(Challenge.serial == tokenobject.get_serial(

        )).delete()

        # due to legacy SQLAlchemy it could happen that the
        # foreign key relation could not be deleted
        # so we do this manualy

        # delete references to client machines
        MachineToken.query.filter(MachineToken.token_id ==
                                  tokenobject.token.id).delete()
        TokenRealm.query.filter(TokenRealm.token_id ==
                                tokenobject.token.id).delete()

        tokenobject.token.delete()

    return token_count


@log_with(log)
def set_realms(serial, realms=None):
    """
    Set all realms of a token. This sets the realms new. I.e. it does not add
    realms. So realms that are not contained in the list will not be assigned
    to the token anymore.

    Thus, setting realms=[] clears all realms assignments.

    :param serial: the serial number of the token
    :type serial: basestring
    :param realms: A list of realm names
    :type realms: list
    :return: the number of tokens, to which realms where added. As a serial
    number should be unique, this is either 1 or 0.
    :rtype: int
    """
    realms = realms or []
    corrected_realms = []

    # get rid of non-defined realms
    for realm in realms:
        if realm_is_defined(realm):
            corrected_realms.append(realm)

    tokenobject_list = get_tokens(serial=serial)

    for tokenobject in tokenobject_list:
        tokenobject.set_realms(corrected_realms)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
def set_defaults(serial):
    """
    Set the default values for the token with the given serial number
    :param serial: token serial
    :type serial: basestring
    :return: None
    """
    tokenobject_list = get_tokens(serial=serial)
    if len(tokenobject_list) > 0:
        db_token = tokenobject_list[0].token
        db_token.otplen = int(get_from_config("DefaultOtpLen", 6))
        db_token.count_window = int(get_from_config("DefaultCountWindow", 15))
        db_token.maxfail = int(get_from_config("DefaultMaxFailCount", 15))
        db_token.sync_window = int(get_from_config("DefaultSyncWindow", 1000))
        db_token.tokentype = u"hotp"
        db_token.save()



@log_with(log)
def assign_token(serial, user, pin=None, encrypt_pin=False):
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

    :return: True if the token was assigned, in case of an error an exception
    is thrown
    :rtype: bool
    """
    tokenobject_list = get_tokens(serial=serial)

    if len(tokenobject_list) == 0:
        log.warning("no tokens found with serial: %r" % serial)
        raise TokenAdminError("no token found!", id=1102)

    tokenobject = tokenobject_list[0]

    # Check if the token already belongs to another user
    old_user = tokenobject.get_user()
    if old_user:
        log.warning("token already assigned to user: %r" % old_user)
        raise TokenAdminError("Token already assigned to user %r" %
                              old_user, id=1103)

    tokenobject.set_user(user)
    if pin is not None:
        tokenobject.set_pin(pin, encrypt=encrypt_pin)

    # reset the OtpFailCounter
    tokenobject.set_failcount(0)

    try:
        tokenobject.save()
    except Exception as e:  # pragma: no cover
        log.error('update Token DB failed')
        raise TokenAdminError("Token assign failed for %r/%s : %r"
                              % (user, serial, e), id=1105)

    log.debug("successfully assigned token with serial "
              "%r to user %r" % (serial, user))
    return True


@log_with(log)
@check_user_or_serial
def unassign_token(serial, user=None):
    """
    unassign the user from the token

    :param serial: The serial number of the token to unassign
    :return: True
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

    if len(tokenobject_list) == 0:
        log.warning("no tokens found with serial: %r" % serial)
        raise TokenAdminError("no token found!", id=1102)

    tokenobject = tokenobject_list[0]
    tokenobject.token.user_id = ""
    tokenobject.token.resolver = ""
    tokenobject.token.resolver_type = ""
    tokenobject.set_pin("")
    tokenobject.set_failcount(0)

    try:
        tokenobject.save()
    except Exception as e:  # pragma: no cover
        log.error('update token DB failed')
        raise TokenAdminError("Token unassign failed for %r: %r"
                              % (serial, e), id=1105)

    log.debug("successfully unassigned token with serial %r" % serial)
    return True


@log_with(log)
def resync_token(serial, otp1, otp2, options=None, user=None):
    """
    Resyncronize the token of the given serial number by searching the
    otp1 and otp2 in the future otp values.

    :param serial: token serial number
    :type serial: basestring
    :param otp1: first OTP value
    :type otp1: basestring
    :param otp2: second OTP value, directly after the first
    :type otp2: basestring
    :param options: additional options like the servertime for TOTP token
    :type options: dict
    :return:
    """
    ret = False

    tokenobject_list = get_tokens(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        ret = tokenobject.resync(otp1, otp2, options)
        tokenobject.save()

    return ret

@log_with(log)
@check_user_or_serial
def reset_token(serial, user=None):
    """
    Reset the failcounter
    :param serial:
    :param user:
    :return: The number of tokens, that were resetted
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

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
    :type pin: basestring
    :param user: If the user is specified, the pins for all tokens of this
    user will be set
    :type used: User object
    :param serial: If the serial is specified, the PIN for this very token
    will be set.
    :return: The number of PINs set (usually 1)
    :rtype: int
    """
    if isinstance(user, basestring):
        # check if by accident the wrong parameter (like PIN)
        # is put into the user attribute
        log.warning("Parameter user must not be a string: %r" % user)
        raise ParameterError("Parameter user must not be a string: %r" %
                             user, id=1212)

    tokenobject_list = get_tokens(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_pin(pin, encrypt=encrypt_pin)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
def set_pin_user(serial, user_pin, user=None):
    """
    This sets the user pin of a token. This just stores the information of
    the user pin for (e.g. an eTokenNG, Smartcard) in the database

    :param serial: The serial number of the token
    :type serial: basestring
    :param user_pin: The user PIN
    :type user_pin: basestring
    :return: The number of PINs set (usually 1)
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

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

    :param serial: The serial number of the token
    :type serial: basestring
    :param so_pin: The Security Officer PIN
    :type so_ping: basestring
    :return: The number of SO PINs set. (usually 1)
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_so_pin(so_pin)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def revoke_token(serial, user=None):
    """
    Revoke a token.

    :param serial: The serial number of the token
    :type serial: basestring
    :param enable: False is the token should be disabled
    :type enable: bool
    :param user: all tokens of the user will be enabled or disabled
    :type user: User object
    :return: Number of tokens that were enabled/disabled
    :rtype:
    """
    tokenobject_list = get_tokens(user=user, serial=serial)

    for tokenobject in tokenobject_list:
        tokenobject.revoke()
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def enable_token(serial, enable=True, user=None):
    """
    Enable or disable a token. This can be checked with is_token_active

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
    # We only search for those tokens, that need action.
    # Tokens that are already active, do not need to be enabled, tokens
    # that are inactive do not need to be disabled.
    tokenobject_list = get_tokens(user=user, serial=serial, active=not enable)

    for tokenobject in tokenobject_list:
        tokenobject.enable(enable)
        tokenobject.save()

    return len(tokenobject_list)


def is_token_active(serial):
    """
    Return True if the token is active, otherwise false
    Returns None, if the token does not exist.

    :param serial: The serial number of the token
    :type serial: basestring
    :return: True or False
    :rtype: bool
    """
    ret = None
    tokenobject_list = get_tokens(serial=serial)
    for tokenobject in tokenobject_list:
        ret = tokenobject.token.active

    return ret


@log_with(log)
@check_user_or_serial
def set_otplen(serial, otplen=6, user=None):
    """
    Set the otp length of the token defined by serial or for all tokens of
    the user.
    The OTP length is usually 6 or 8.

    :param serial: The serial number of the token
    :type serial: basestring
    :param otplen: The length of the OTP value
    :type otplen: int
    :param user: The owner of the tokens
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

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

    :param serial: The serial number of the token
    :type serial: basestring
    :param hashlib: The hashlib of the token
    :type hashlib: basestring
    :param user: The User, for who's token the hashlib should be set
    :type user: User object
    :return: the number of token infos set
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_hashlib(hashlib)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_count_auth(serial, count, user=None, max=False, success=False):
    """
    The auth counters are stored in the token info database field.
    There are different counters, that can be set
        count_auth -> max=False, success=False
        count_auth_max -> max=True, success=False
        count_auth_success -> max=False, success=True
        count_auth_success_max -> max=True, success=True

    :param count: The counter value
    :type count: int
    :param user: The user owner of the tokens tokens to modify
    :type user: User object
    :param serial: The serial number of the one token to modifiy
    :type serial: basestring
    :param max: True, if either count_auth_max or count_auth_success_max are
    to be modified
    :type max: bool
    :param success: True, if either count_auth_success or
    count_auth_success_max are to be modified
    :type success: bool
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

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
    tokenobject_list = get_tokens(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.add_tokeninfo(info, value)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_validity_period_start(serial, user, start):
    """
    Set the validity period for the given token.

    :param serial:
    :param user:
    :param start: Timestamp in the format DD/MM/YY HH:MM
    :type start: basestring
    """
    tokenobject_list = get_tokens(serial=serial, user=user)
    for tokenobject in tokenobject_list:
        tokenobject.set_validity_period_start(start)
        tokenobject.save()
    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_validity_period_end(serial, user, end):
    """
    Set the validity period for the given token.

    :param serial:
    :param user:
    :param end: Timestamp in the format DD/MM/YY HH:MM
    :type end: basestring
    """
    tokenobject_list = get_tokens(serial=serial, user=user)
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

    :param serial: The serial number of the token
    :type serial: basestring
    :param syncwindow: The size of the sync window
    :type syncwindow: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

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

    :param serial: The serial number of the token
    :type serial: basestring
    :param countwindow: the size of the window
    :type countwindow: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_count_window(countwindow)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_description(serial, description, user=None):
    """
    Set the description of a token

    :param serial: The serial number of the token
    :type serial: basestring
    :param description: The description for the token
    :type description: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

    for tokenobject in tokenobject_list:
        tokenobject.set_description(description)
        tokenobject.save()

    return len(tokenobject_list)


@log_with(log)
@check_user_or_serial
def set_max_failcount(serial, maxfail, user=None):
    """
    Set the maximum fail counts of tokens. This is the maximum number a
    failed authentication is allowed.

    :param serial: The serial number of the token
    :type serial: basestring
    :param maxfail: The maximum allowed failed authentications
    :type maxfail: int
    :param user: The owner of the tokens, which should be modified
    :type user: User object
    :return: number of modified tokens
    :rtype: int
    """
    tokenobject_list = get_tokens(serial=serial, user=user)

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
    tokenobject_list_from = get_tokens(serial=serial_from)
    tokenobject_list_to = get_tokens(serial=serial_to)
    pinhash, seed = tokenobject_list_from[0].get_pin_hash_seed()
    tokenobject_list_to[0].set_pin_hash_seed(pinhash, seed)
    tokenobject_list_to[0].save()
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
    tokenobject_list_from = get_tokens(serial=serial_from)
    tokenobject_list_to = get_tokens(serial=serial_to)
    user_id = tokenobject_list_from[0].token.user_id
    resolver = tokenobject_list_from[0].token.resolver
    resolver_type = tokenobject_list_from[0].token.resolver_type
    tokenobject_list_to[0].set_user_identifiers(user_id, resolver,
                                                resolver_type)
    copy_token_realms(serial_from, serial_to)
    tokenobject_list_to[0].save()
    return True

@check_copy_serials
def copy_token_realms(serial_from, serial_to):
    """
    Copy the realms of one token to the other token

    :param serial_from: The token to copy from
    :param serial_to: The token to copy to
    :return: None
    """
    tokenobject_list_from = get_tokens(serial=serial_from)
    tokenobject_list_to = get_tokens(serial=serial_to)
    realm_list = tokenobject_list_from[0].token.get_realms()
    tokenobject_list_to[0].set_realms(realm_list)


@log_with(log)
@libpolicy(config_lost_token)
def lost_token(serial, new_serial=None, password=None,
               validity=10, contents="Ccns", pw_len=16, options=None):
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
    :param contents: The contents of the generated password. "C": upper case
    characters, "c": lower case characters, "n": digits and "s": special
    characters
    :type contents: A string like "Ccn"
    :param pw_len: The length of the generated password
    :type pw_len: int
    :param options: optional values for the decorator passed from the upper
    API level
    :type options: dict

    :return: result dictionary
    """
    res = {}
    new_serial = new_serial or "lost%s" % serial
    user = get_token_owner(serial)

    log.debug("doing lost token for serial %r and user %r" % (serial, user))

    if user is None or user.is_empty():
        err = "You can only define a lost token for an assigned token."
        log.warning("%s" % err)
        raise TokenAdminError(err, id=2012)

    character_pool = "%s%s%s" % (string.ascii_lowercase,
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

    if password is None:
        password = generate_password(size=pw_len, characters=character_pool)

    res['serial'] = new_serial

    tokenobject = init_token({"otpkey": password, "serial": new_serial,
                              "type": "pw",
                              "description": "temporary replacement for %s" %
                                             serial})

    res['init'] = tokenobject is not None
    if res['init']:
        res['user'] = copy_token_user(serial, new_serial)
        res['pin'] = copy_token_pin(serial, new_serial)

        # set validity period
        end_date = (datetime.date.today()
                    + datetime.timedelta(days=validity)).strftime("%d/%m/%y")

        end_date = "%s 23:59" % end_date
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
def check_realm_pass(realm, passw, options=None):
    """
    This function checks, if the given passw matches any token in the given
    realm. This can be used for the 4-eyes token.
    Only tokens that are assigned are tested.

    It returns the res True/False and a reply_dict, which contains the
    serial number of the matching token.

    :param realm: The realm of the user
    :param passw: The password containing PIN+OTP
    :param options: Additional options that are passed to the tokens
    :type options: dict
    :return: tuple of bool and dict
    """
    res = False
    reply_dict = {}
    # since an attacker does not know, which token is tested, we restrict to
    # only active tokens. He would not guess that the given OTP value is that
    #  of an inactive token.
    tokenobject_list = get_tokens(realm=realm, assigned=True, active=True)
    if len(tokenobject_list) == 0:
        res = False
        reply_dict["message"] = "There is no active and assigned token in " \
                                "this realm"
    else:
        res, reply_dict = check_token_list(tokenobject_list, passw,
                                           options=options)
    return res, reply_dict


@log_with(log)
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
    tokenobject_list = get_tokens(serial=serial)
    if len(tokenobject_list) == 0:
        # The serial does not exist
        res = False
        reply_dict["message"] = "The token with this serial does not exist"
    else:
        tokenobject = tokenobject_list[0]
        res, reply_dict = check_token_list(tokenobject_list, passw,
                                           user=tokenobject.get_user(),
                                           options=options)

    return res, reply_dict


@libpolicy(auth_user_passthru)
@libpolicy(auth_user_has_no_token)
@libpolicy(auth_user_does_not_exist)
@log_with(log)
def check_user_pass(user, passw, options=None):
    """
    This function checks the otp for a given user.
    It is called by the API /validate/check and simplecheck

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
    tokenobject_list = get_tokens(user=user)
    reply_dict = {}
    if len(tokenobject_list) == 0:
        # The user has no tokens assigned
        res = False
        reply_dict["message"] = "The user has no tokens assigned"
    else:
        tokenobject = tokenobject_list[0]
        res, reply_dict = check_token_list(tokenobject_list, passw,
                                           user=tokenobject.get_user(),
                                           options=options)

    return res, reply_dict

@log_with(log)
def check_token_list(tokenobject_list, passw, user=None, options=None):
    """
    this takes a list of token objects and tries to find the matching token
    for the given passw. In also tests,
    * if the token is active or
    * the max fail count is reached,
    * if the validity period is ok...

    This function is called by check_serial_pass, check_user_pass and
    check_yubikey_pass.

    :param tokenobject_list: list of identified tokens
    :param passw: the provided passw (mostly pin+otp)
    :param user: the identified use - as class object
    :param options: additional parameters, which are passed to the token

    :return: tuple of success and optional response
    :rtype: (bool, dict)
    """
    res = False
    reply_dict = {}

    # add the user to the options, so that every token, that get passed the
    # options can see the user
    options = options or {}
    options = dict(options.items() + {'user': user}.items())

    # if there has been one token in challenge mode, we only handle challenges
    challenge_response_token_list = []
    challenge_request_token_list = []
    pin_matching_token_list = []
    invalid_token_list = []
    valid_token_list = []

    for tokenobject in tokenobject_list:
        audit = {'serial': tokenobject.get_serial(),
                 'token_type': tokenobject.get_type(),
                 'weight': 0}

        log.debug("Found user with loginId %r: %r" % (
                  tokenobject.get_user(), tokenobject.get_serial()))

        if tokenobject.is_challenge_response(passw, user=user, options=options):
            # This is a challenge response
            challenge_response_token_list.append(tokenobject)
        elif tokenobject.is_challenge_request(passw, user=user,
                                              options=options):
            # This is a challenge request
            challenge_request_token_list.append(tokenobject)
        else:
            # This is a normal authentication attempt
            pin_match, otp_count, repl = tokenobject.authenticate(passw, user,
                                                                  options=options)
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

    AND incFailCountOnFalsePin is True, then the failcounter off the
    10 invalid tokens need to be increased. And return False

    If there is
    X pin_matching
    1+ valid
    X invalid
    0 challenge

    Then the authentication with the valid tokens was successful and the
    <count> of the valid tokens need to be increased to the new count.
    """
    if len(valid_token_list) > 0:
        # One ore more successfully authenticating tokens found
        # We need to return success
        message_list = ["matching %i tokens" % len(valid_token_list)]
        # write serial numbers or something to audit log
        for token_obj in valid_token_list:
            token_obj.inc_count_auth()
            token_obj.inc_count_auth_success()
            # Check if the max auth is succeeded
            if not token_obj.check_auth_counter():
                message_list.append("Authentication counter exceeded")
            # Check if the token is disabled
            elif not token_obj.is_active():
                message_list.append("Token is disabled")
            elif not token_obj.check_failcount():
                message_list.append("Failcounter exceeded")
            elif not token_obj.check_validity_period():
                message_list.append("Outside validity period")
            else:
                # The token is active and the auth counters are ok.
                res = True
        if len(valid_token_list) == 1:
            # If only one token was found, we add the serial number and token
            #  type
            reply_dict["serial"] = valid_token_list[0].token.serial
            reply_dict["type"] = valid_token_list[0].token.tokentype
        reply_dict["message"] = ", ".join(message_list)

    elif len(challenge_response_token_list) > 0:
        # A challenge token was found.
        for tokenobject in challenge_response_token_list:
            if tokenobject.check_challenge_response(passw=passw,
                                                    options=options) >= 0:
                # OTP matches
                res = True
                tokenobject.inc_count_auth()
                tokenobject.inc_count_auth_success()
                reply_dict["message"] = "Found matching challenge"
                tokenobject.challenge_janitor()

    elif len(challenge_request_token_list) > 0:
        # A challenge token was found.
        if len(challenge_request_token_list) == 1:
            # One token that can create challenge
            tokenobject = challenge_request_token_list[0]
            r_chal, message, transaction_id, \
            attributes = tokenobject.create_challenge(options=options)
            # Add the reply to the response
            reply_dict = {"message": message}
            if r_chal:
                reply_dict["transaction_id"] = transaction_id
                reply_dict["attributes"] = attributes
        else:
            reply_dict["message"] = "Multiple tokens to create a challenge " \
                                    "found!"

    elif len(pin_matching_token_list) > 0:
        # We did not find a valid token and no challenge.
        # But there are tokens, with a matching pin.
        # So we increase the failcounter. Return failure.
        for tokenobject in pin_matching_token_list:
            tokenobject.inc_failcount()
            reply_dict["message"] = "wrong otp value"
            if len(pin_matching_token_list) == 1:
                # If there is only one pin matching token, we look if it was
                # a previous OTP value
                token = pin_matching_token_list[0]
                _r, pin, otp = token.split_pin_pass(passw)
                if token.is_previous_otp(otp):
                    reply_dict["message"] += ". previous otp used again"
            for token_obj in pin_matching_token_list:
                token_obj.inc_count_auth()
            # write the serial numbers to the audit log
            if len(pin_matching_token_list) == 1:
                reply_dict["serial"] = pin_matching_token_list[0].token.serial
                reply_dict["type"] = pin_matching_token_list[0].token.tokentype

    elif len(invalid_token_list) > 0:
        # There were only tokens, that did not match the OTP value and
        # not even the PIN.
        # Depending of IncFailCountOnFalsePin, we increase the failcounter.
        reply_dict["message"] = "wrong otp pin"
        if get_inc_fail_count_on_false_pin():
            for tokenobject in invalid_token_list:
                tokenobject.inc_failcount()
                tokenobject.inc_count_auth()

    return res, reply_dict


def get_dynamic_policy_definitions(scope=None):
    """
    This returns the dynamic policy definitions that come with the new loaded
    token classes.

    :param scope: an optional scope parameter. Only return the policies of
    this scope.
    :return: The policy definition for the token or only for the scope.
    """
    from privacyidea.lib.policy import SCOPE

    pol = {SCOPE.ADMIN: {},
           SCOPE.USER: {},
           SCOPE.AUTH: {},
           SCOPE.ENROLL: {},
           SCOPE.AUTHZ: {}}
    for ttype in get_token_types():
        pol[SCOPE.ADMIN]["enroll%s" % ttype.upper()] \
            = {'type': 'bool',
               'desc': _('Admin is allowed to initalize %s tokens.') %
                       ttype.upper()}

        conf = get_tokenclass_info(ttype, section='user')
        if 'enroll' in conf:
            pol[SCOPE.USER]["enroll%s" % ttype.upper()] = {
                'type': 'bool',
                'desc': _("The user is allowed to enroll a %s token.") % ttype}

        # now merge the dynamic Token policy definition
        # into the global definitions
        policy = get_tokenclass_info(ttype, section='policy')

        # get all policy sections like: admin, user, enroll, auth, authz
        pol_keys = pol.keys()

        for pol_section in policy.keys():
            # if we have a dyn token definition of this section type
            # add this to this section - and make sure, that it is
            # then token type prefixed
            if pol_section in pol_keys:
                pol_entry = policy.get(pol_section)
                for pol_def in pol_entry:
                    set_def = pol_def
                    if pol_def.startswith(ttype) is not True:
                        set_def = '%s_%s' % (ttype, pol_def)

                    pol[pol_section][set_def] = pol_entry.get(pol_def)

    # return sub section, if scope is defined
    # make sure that scope is in the policy key
    # e.g. scope='_' is undefined and would break
    if scope and scope in pol:
        pol = pol[scope]

    return pol
