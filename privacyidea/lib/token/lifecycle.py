# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Token creation, import, assignment, copying and deletion."""

import datetime
import logging
import os
import random
import string
import traceback

from dateutil.tz import tzlocal
from sqlalchemy import func, select

from privacyidea.lib import _
from privacyidea.lib.config import (get_token_prefix,
                                    get_from_config,
                                    get_enrollable_token_types)
from privacyidea.lib.crypto import generate_password
from privacyidea.lib.decorators import (check_user_or_serial,
                                        check_copy_serials)
from privacyidea.lib.error import (TokenAdminError)
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.log import log_with
from privacyidea.lib.policydecorators import (libpolicy,
                                              config_lost_token)
from privacyidea.lib.tokenclass import DATE_FORMAT, Tokenkind, TokenClass
from privacyidea.lib.tokenrolloutstate import RolloutState
from privacyidea.lib.user import User
from privacyidea.lib.utils import (BASE58, hexlify_and_unicode, check_serial_valid)
from privacyidea.models import (db, Token, TokenOwner)

from privacyidea.lib.token.const import PI_TOKEN_SERIAL_RANDOM, B32_ALPHABET

from privacyidea.lib.token.attributes import enable_token, unassign_token
from privacyidea.lib.token.query import (create_tokenclass_object, get_one_token, get_token_owner, get_tokens,
                                         get_tokens_from_serial_or_user)

log = logging.getLogger(__name__)


@log_with(log)
def gen_serial(tokentype: str, prefix: str = None) -> str:
    """
    Generate a serial for a given token type.

    The serial consists of the token type prefix and a randomly generated string
    of characters. By default, the random string contains 8 characters.

    If no prefix is given, it is determined by the token class prefix.

    The generation of the random part of the serial is determined by the
    ``PI_TOKEN_SERIAL_RANDOM`` setting in :ref:`the config file <picfg_token_serial_random>`.
    The default is to calculate a two-part serial with the first 4 characters
    containing the current token count at the time of the generation and the
    next 4 characters containing a random hexadecimal value.
    This severely limits the number of generated serials since for every count
    value only 16\\ :sup:`4` possible values for the random part exist. Specific count
    values are only ever reused if tokens are deleted.

    Setting ``PI_TOKEN_SERIAL_RANDOM`` to ``True`` enables to completely generate
    the random string with 4 random digits and the rest using the Base32
    character table (See :rfc:`4648#section-6`) thus allowing more than
    10\\ :sup:`10` different serials.

    Due to the required uniqueness of the serial, each generated serial is
    checked if it already exists in the database. If the number of possibilities
    for generated serials decreases, this can lead to excessive queries on the
    database.

    :param tokentype: the token type prefix is done by a lookup on the tokens
    :type tokentype: str
    :param prefix: A prefix to the serial number
    :type prefix: str
    :return: serial number
    :rtype: str
    """
    random_serial = get_app_config_value(PI_TOKEN_SERIAL_RANDOM, False)
    # TODO: the serial length is currently not configurable through the UI
    serial_len = int(get_from_config("SerialLength") or 8)
    if not prefix:
        prefix = get_token_prefix(tokentype.lower(), tokentype.upper())

    if random_serial:
        def _gen_serial(_tokennum: int) -> str:
            digit_part = random.randrange(10000)  # nosec B311
            b32_part = "".join([random.choice(B32_ALPHABET) for _ in range(serial_len - 4)])  # nosec B311
            return f"{prefix}{digit_part:04}{b32_part}"
    else:
        def _gen_serial(_tokennum: int) -> str:
            h_serial = ''
            num_str = f'{_tokennum:04d}'
            h_len = serial_len - len(num_str)
            if h_len > 0:
                h_serial = hexlify_and_unicode(os.urandom(h_len)).upper()[0:h_len]
            return f"{prefix!s}{num_str!s}{h_serial!s}"

    # now search the number of tokens of tokentype in the token database
    session = db.session
    tokennum = session.execute(
        select(func.count()).select_from(Token).where(Token.tokentype == tokentype.lower())
    ).scalar_one()

    # Now create the serial
    serial = _gen_serial(tokennum)

    # now test if serial already exists
    while True:
        numtokens = session.execute(
            select(func.count()).select_from(Token).where(Token.serial == serial)
        ).scalar_one()
        if numtokens == 0:
            # ok, there is no such token, so we're done
            break
        serial = _gen_serial(tokennum + numtokens)  # pragma: no cover

    return serial


@log_with(log)
def import_token(serial: str, token_dict: dict, tokenrealms: list | None = None) -> TokenClass:
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
                       tokenkind=Tokenkind.HARDWARE)
    if token_dict.get("counter"):
        token.set_otp_count(token_dict.get("counter"))
    if token_dict.get("timeShift"):
        token.add_tokeninfo("timeShift", token_dict.get("timeShift"))
    return token


@log_with(log, hide_args_keywords={0: ['pin', 'otpkey', 'password', 'radius.secret',
                                       'enrollment_credential', 'sshkey']})
def init_token(param: dict, user: User = None, tokenrealms: list[str] = None, tokenkind: str = None) -> TokenClass:
    """
    Create a new token or update an existing token with the specified parameters.

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
    token_type = param.get("type") or "hotp"
    # Check for unsupported token type
    token_types = get_enrollable_token_types()
    if token_type.lower() not in token_types:
        log.error(f"type {token_type} not found in tokentypes: {token_types}")
        raise TokenAdminError(_("init token failed. Unknown token type:") + f" {token_type}", id=1610)

    serial = param.get("serial") or gen_serial(token_type, param.get("prefix"))
    check_serial_valid(serial)
    realms = []

    # Check if a token with this serial already exists and
    # create a list of the found tokens
    tokens = get_tokens(serial=serial)
    token_count = len(tokens)
    if token_count == 0:
        # A token with the serial was not found, so we create a new one
        db_token = Token(serial, tokentype=token_type.lower())

    else:
        # The token already exist, so we update the token
        db_token = tokens[0].token
        # Make sure the type is not changed between the initialization and the update
        old_type = db_token.tokentype
        if old_type.lower() != token_type.lower():
            msg = _("Token {serial} already exists with type {old_type}. "
                    "Can not initialize token with new type "
                    "{token_type}").format(serial=serial, old_type=old_type, token_type=token_type)
            log.error(msg)
            raise TokenAdminError(_("init token failed:") + " " + msg)

    # If there is a realm as parameter (and the realm is not empty), but no
    # user, we assign the token to this realm.
    if param.get("realm") and 'user' not in param:
        realms.append(param.get("realm"))

    # Assign the token to all tokenrealms and to the user realm
    if tokenrealms and isinstance(tokenrealms, list):
        realms.extend(tokenrealms)
    if user and user.realm:
        realms.append(user.realm)

    try:
        # Save the token to the database
        if token_count == 0:
            db_token.save()

        # The tokenclass object is created
        token = create_tokenclass_object(db_token)

        if token_count == 0:
            # If this token is a newly created one, we have to set up the defaults,
            # which later might be overwritten by the token.update(param)
            token.set_defaults()

        # Set the user of the token
        if user is not None and user.login != "":
            token.add_user(user)

        # Set the token realms (updates the TokenRealm table)
        if realms or user:
            token.set_realms(realms)

        token.update(param)

    except Exception as e:
        log.error(f"token create failed: {e}")
        log.debug(f"{traceback.format_exc()}")
        # Delete the newly created token from the db
        if token_count == 0:
            if token:
                token.delete_token()
            else:
                db_token.delete()
        raise

    # We only set the tokenkind here if it was explicitly set in the init_token call.
    # In all other cases it is set in the update method of the tokenclass.
    if tokenkind:
        token.add_tokeninfo("tokenkind", tokenkind)

    # Set the validity period
    validity_period_start = param.get("validity_period_start")
    validity_period_end = param.get("validity_period_end")
    if validity_period_end:
        token.set_validity_period_end(validity_period_end)
    if validity_period_start:
        token.set_validity_period_start(validity_period_start)

    # Creation Date
    token.add_tokeninfo("creation_date", datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))

    # If the token has no rollout_state, we set it to "enrolled"
    if not token.rollout_state:
        token.token.rollout_state = RolloutState.ENROLLED

    # Safe the token object to make sure all changes are persisted in the db
    token.save()
    return token


@log_with(log)
@check_user_or_serial
def remove_token(serial: str | None = None, user: User | None = None) -> int:
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
    tokens = get_tokens_from_serial_or_user(serial=serial, user=user)
    token_count = len(tokens)

    # Delete challenges of such a token
    for token in tokens:
        token.delete_token()

    return token_count


@log_with(log)
@check_copy_serials
def copy_token_pin(serial_from: str, serial_to: str) -> bool:
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
def copy_token_user(serial_from: str, serial_to: str) -> bool:
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
def copy_token_realms(serial_from: str, serial_to: str) -> None:
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
def lost_token(serial: str, new_serial: str | None = None, password: str | None = None,
               validity: int = 10, contents: str = "8", pw_len: int = 16,
               options: dict | None = None) -> dict:
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
    new_serial = new_serial or f"lost{serial!s}"
    user = get_token_owner(serial)

    log.debug(f"doing lost token for serial {serial!r} and user {user!r}")

    if user is None or user.is_empty():
        err = _("You can only define a lost token for an assigned token.")
        log.warning(f"{err!s}")
        raise TokenAdminError(err, id=2012)

    character_pool = f"{string.ascii_lowercase!s}{string.ascii_uppercase!s}{string.digits!s}"
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
