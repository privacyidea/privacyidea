#!/usr/bin/env python
#
# 2023-11-03 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#            Migrate to click
# 2020-11-11 Timo Sturm <timo.sturm@netknights.it>
#            Select how to validate PSKC imports
# 2018-02-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Allow to import PSKC file
# 2017-11-21 Cornelius Kölbel <corenlius.koelbel@netknights.it>
#            export to CSV including usernames
# 2017-10-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add token export (HOTP and TOTP) to PSKC
# 2017-05-02 Friedrich Weber <friedrich.weber@netknights.it>
#            Improve token matching
# 2017-04-25 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# Copyright (c) 2017, Cornelius Kölbel
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import click
from click import ClickException
from flask.cli import AppGroup
from dateutil import parser
from dateutil.tz import tzlocal, tzutc

from privacyidea.lib.policy import ACTION
from privacyidea.lib.utils import parse_legacy_time
from privacyidea.lib.importotp import export_pskc
from privacyidea.lib.token import (get_tokens, remove_token, enable_token,
                                   unassign_token,
                                   get_tokens_paginated_generator)
from privacyidea.models import Token
import re
import sys
from yaml import safe_dump as yaml_safe_dump

find_cli = AppGroup("find")

__doc__ = """
This script can be used to clean up the token database.

It can list, disable, delete or edit tokens based on

Conditions:

* last_auth
* orphaned tokens
* any tokeninfo
* unassigned token / token has no user
* tokentype

Actions:

* list
* unassign
* mark
* disable
* delete


    privacyidea-token-janitor find
        --last_auth=10h|7d|2y
        --tokeninfo= 'token_info_key == token_info_value' or 'token_info_key >= token_info_value'
                        or 'token_info_key <= token_info_value'
        --has-not-tokeninfo-key<key>
        --has-tokeninfo-key<key>
        --assigned false
        --orphaned true
        --tokentype=<type>
        --serial=<regexp>
        --description=<regexp>


.. note:: If you fail to redirect the output of this command at the commandline
   to e.g. a file with a UnicodeEncodeError, you need to set the environment
   variable like this:
       export PYTHONIOENCODING=UTF-8
   Here is a good read about it:
   https://stackoverflow.com/questions/4545661/unicodedecodeerror-when-redirecting-to-file

"""

ALLOWED_ACTIONS = ["disable", "delete", "unassign", "mark", "export", "listuser", "tokenrealms"]


def _try_convert_to_integer(given_value_string):
    try:
        return int(given_value_string)
    except ValueError:
        raise ClickException('Not an integer: {}'.format(given_value_string))


def _compare_greater_than(_key, given_value_string):
    """
    :return: a function which returns True if its parameter (converted to an integer)
             is greater than *given_value_string* (converted to an integer).
    """
    given_value = _try_convert_to_integer(given_value_string)

    def comparator(value):
        try:
            return int(value) > given_value
        except ValueError:
            return False

    return comparator


def _compare_less_than(_key, given_value_string):
    """
    :return: a function which returns True if its parameter (converted to an integer)
             is less than *given_value_string* (converted to an integer).
    """
    given_value = _try_convert_to_integer(given_value_string)

    def comparator(value):
        try:
            return int(value) < given_value
        except ValueError:
            return False

    return comparator


def _parse_datetime(key, value):
    if key == ACTION.LASTAUTH:
        # Special case for last_auth: Legacy values are given in UTC time!
        last_auth = parser.parse(value)
        if not last_auth.tzinfo:
            last_auth = parser.parse(value, tzinfos=tzutc)
        return last_auth
    else:
        # Other values are given in local time
        return parser.parse(parse_legacy_time(value))


def _try_convert_to_datetime(given_value_string):
    try:
        parsed = parser.parse(given_value_string, dayfirst=False)
        if not parsed.tzinfo:
            # If not timezone is given we assume the timestamp is given in local time
            parsed = parsed.replace(tzinfo=tzlocal())
        return parsed
    except ValueError:
        raise ClickException('Not a valid datetime format: {}'.format(given_value_string))


def _compare_after(key, given_value_string):
    """
    :return: a function which returns True if its parameter (converted to a datetime) occurs after
             *given_value_string* (converted to a datetime).
    """

    def comparator(value):
        try:
            return _parse_datetime(key, value) > given_value_string
        except ValueError:
            return False

    return comparator


def _compare_before(key, given_value_string):
    """
    :return: a function which returns True if its parameter (converted to a datetime) occurs before
             *given_value_string* (converted to a datetime).
    """

    def comparator(value):
        try:
            return _parse_datetime(key, value) < given_value_string
        except ValueError:
            return False

    return comparator


def _compare_regex_or_equal(_key, given_regex):
    def comparator(value):
        if type(value) in (int, bool):
            # If the value from the database is an integer, we compare "euqals integer"
            given_value = _try_convert_to_integer(given_regex)
            return given_value == value
        else:
            # if the value from the database is a string, we compare regex
            return re.search(given_regex, value)

    return comparator


def build_tokenvalue_filter(key,
                            tokeninfo_value,
                            tokeninfo_value_greater_than,
                            tokeninfo_value_less_than,
                            tokeninfo_value_after,
                            tokeninfo_value_before):
    """
    Build and return a token value filter, which is a list of comparator functions.
    Each comparator function takes a tokeninfo value and returns True if the
    user-defined criterion matches.
    The filter matches a record if *all* comparator functions return True, i.e.
    if the conjunction of all comparators returns True.

    :param key: user-supplied --tokeninfo-key= value
    :param has_tokeninfo_key: user-supplied --has_tokeninfo_key= value
    :param has_not_tokeninfo_key: user-supplied --has_not_tokeninfo_key= value
    :param tokeninfo_value: user-supplied --tokeninfo-value= value
    :param tokeninfo_value_greater_than: user-supplied --tokeninfo-value-greater-than= value
    :param tokeninfo_value_less_than: user-supplied --tokeninfo-value-less-than= value
    :param tokeninfo_value_after: user-supplied --tokeninfo-value-after= value
    :param tokeninfo_value_before: user-supplied --tokeninfo-value-before= value
    :return: list of functions
    """
    tvfilter = []
    if tokeninfo_value:
        tvfilter.append(_compare_regex_or_equal(key, tokeninfo_value))
    if tokeninfo_value_greater_than:
        tvfilter.append(_compare_greater_than(key, tokeninfo_value_greater_than))
    if tokeninfo_value_less_than:
        tvfilter.append(_compare_less_than(key, tokeninfo_value_less_than))
    if tokeninfo_value_after:
        tvfilter.append(_compare_after(key, tokeninfo_value_after))
    if tokeninfo_value_before:
        tvfilter.append(_compare_before(key, tokeninfo_value_before))
    return tvfilter


def _get_tokenlist(last_auth, assigned, active, tokeninfo_key,
                   tokeninfo_value_filter, tokenattribute, tokenattribute_filter,
                   orphaned, tokentype, serial, description, chunksize, has_not_tokeninfo_key, has_tokeninfo_key):
    filter_active = None
    filter_assigned = None
    orphaned = orphaned or ""

    if assigned is not None:
        filter_assigned = assigned.lower() == "true"
    if active is not None:
        filter_active = active.lower() == "true"

    if chunksize is not None:
        iterable = get_tokens_paginated_generator(tokentype=tokentype,
                                                  active=filter_active,
                                                  assigned=filter_assigned,
                                                  psize=chunksize)
    else:
        iterable = [get_tokens(tokentype=tokentype,
                               active=filter_active,
                               assigned=filter_assigned)]
    for tokenobj_list in iterable:
        filtered_list = []
        sys.stderr.write("++ Creating token object list.\n")
        tok_count = 0
        tok_found = 0
        for token_obj in tokenobj_list:
            sys.stderr.write('{0} Tokens processed / {1} Tokens found\r'.format(tok_count, tok_found))
            sys.stderr.flush()
            tok_count += 1
            if last_auth and token_obj.check_last_auth_newer(last_auth):
                continue
            if serial and not re.search(serial, token_obj.token.serial):
                continue
            if description and not re.search(description,
                                             token_obj.token.description):
                continue
            if has_not_tokeninfo_key:
                if has_not_tokeninfo_key in token_obj.get_tokeninfo():
                    continue
            if has_tokeninfo_key:
                if has_tokeninfo_key not in token_obj.get_tokeninfo():
                    continue
            if tokeninfo_value_filter and tokeninfo_key:
                value = token_obj.get_tokeninfo(tokeninfo_key)
                # if the tokeninfo key is not even set, it does not match the filter
                if value is None:
                    continue
                # suppose not all comparator functions return True
                # => at least one comparator function returns False
                # => at least one user-supplied criterion does not match
                # => the token object does not match the user-supplied criteria
                if not all(comparator(value) for comparator in tokeninfo_value_filter):
                    continue
            if tokenattribute_filter and tokenattribute:
                value = token_obj.token.get(tokenattribute)
                if value is None:
                    continue
                if not all(comparator(value) for comparator in tokenattribute_filter):
                    continue
            if orphaned.upper() in ["1", "TRUE"] and not token_obj.is_orphaned():
                continue
            if orphaned.upper() in ["0", "FALSE"] and token_obj.is_orphaned():
                continue

            tok_found += 1
            # if everything matched, we append the token object
            filtered_list.append(token_obj)

        sys.stderr.write('{0} Tokens processed / {1} Tokens found\r\n'.format(tok_count, tok_found))
        sys.stderr.write("++ Token object list created.\n")
        sys.stderr.flush()
        yield filtered_list


def export_token_data(token_list, attributes=None):
    """
    Returns a list of tokens. Each token again is a simple list of data

    :param token_list:
    :param attributes: display additional user attributes
    :return:
    """
    tokens = []
    for token_obj in token_list:
        token_data = ["{0!s}".format(token_obj.token.serial),
                      "{0!s}".format(token_obj.token.tokentype)]
        try:
            user = token_obj.user
            if user:
                token_data.append("{0!s}".format(user.info.get("username", "")))
                token_data.append("{0!s}".format(user.info.get("givenname", "")))
                token_data.append("{0!s}".format(user.info.get("surname", "")))
                token_data.append("{0!s}".format(user.uid))
                token_data.append("{0!s}".format(user.resolver))
                token_data.append("{0!s}".format(user.realm))

            if attributes:
                for att in attributes.split(","):
                    token_data.append("{0!s}".format(
                        user.info.get(att, ""))
                    )
        except Exception:
            sys.stderr.write("Failed to determine user for token {0!s}.\n".format(
                token_obj.token.serial
            ))
            token_data.append("**failed to resolve user**")
        tokens.append(token_data)
    return tokens


def export_user_data(token_list, attributes=None):
    """
    Returns a list of users with the information how many tokens this user has assigned

    :param token_list:
    :param attributes: display additional user attributes
    :return:
    """
    users = {}
    for token_obj in token_list:
        try:
            user = token_obj.user
        except Exception:
            sys.stderr.write("Failed to determine user for token {0!s}.\n".format(
                token_obj.token.serial
            ))
        if user:
            uid = "'{0!s}','{1!s}','{2!s}','{3!s}','{4!s}','{5!s}'".format(
                user.info.get("username", ""),
                user.info.get("givenname", ""),
                user.info.get("surname", ""),
                user.uid,
                user.resolver,
                user.realm
            )
            if attributes:
                for att in attributes.split(","):
                    uid += ",'{0!s}'".format(
                        user.info.get(att, "")
                    )
        else:
            uid = "N/A" + ", " * 5

        if uid in users.keys():
            users[uid].append(token_obj.token.serial)
        else:
            users[uid] = [token_obj.token.serial]

    return users


@find_cli.command("find")
@click.option('--set-description', help='set a new description')
@click.option('--set-tokeninfo-key', help='set a new tokeninfo-key')
@click.option('--set-tokeninfo-value', help='set a new tokeninfo-value')
@click.option('--tokeninfo-value-before', metavar='DATETIME',
              help='Interpret tokeninfo values as datetimes,'
                   ' match only if they occur before the given ISO 8601 datetime')
@click.option('--tokeninfo-value-after', metavar='DATETIME',
              help='Interpret tokeninfo values as datetimes,'
                   ' match only if they occur after the given ISO 8601 datetime')
@click.option('--tokeninfo-value-greater-than', metavar='INTEGER',
              help='Interpret tokeninfo values as integers and match only if they are '
                   'greater than the given integer')
@click.option('--tokeninfo-value-less-than', metavar='INTEGER',
              help='Interpret tokeninfo values as integers and match only if they are '
                   'smaller than the given integer')
@click.option('--tokeninfo-value', metavar='REGEX|INTEGER', help='The tokeninfo value to match')
@click.option('--has-not-tokeninfo-key', help='filters for tokens that have not given the specified tokeninfo-key')
@click.option('--has-tokeninfo-key', help='filters for tokens that have given the specified tokeninfo-key.')
@click.option('--tokeninfo-key', help='The tokeninfo key to match. ')
@click.option('--tokenattribute-value-greater-than', metavar='INTEGER',
              help="Match if the value of the token attribute is greater than the given value.")
@click.option('--tokenattribute-value-less-than', metavar='INTEGER',
              help="Match if the value of the token attribute is less than the given value.")
@click.option('--tokenattribute-value', metavar='REGEX|INTEGER',
              help='The value of the token attribute which should match.')
@click.option('--tokenattribute', help='Match for a certain token attribute from the database.')
@click.option('--tokentype', help='The tokentype to search.')
@click.option('--serial', help='A regular expression on the serial')
@click.option('--description', help='A regular expression on the description')
@click.option('--attributes', help='Extends the "listuser" function to display additional user attributes')
@click.option('--tokenrealms', help='A comma separated list of realms, to which the tokens should be assigned.')
@click.option('--sum', 'sum_tokens', is_flag=True,
              help='In case of the action "listuser", this switch specifies if'
                   ' the output should only contain the number of tokens owned by the user.')
@click.option('--action', help='Which action should be performed on the '
                               'found tokens. {0!s}. Exporting to PSKC only supports '
                               'HOTP, TOTP and PW tokens!'.format("|".join(ALLOWED_ACTIONS)))
@click.option('--csv', is_flag=True,
              help='In case of a simple find, the output is written as CSV instead of the '
                   'formatted output.')
@click.option('--yaml', is_flag=True,
              help='In case of a simple find, the output is written as YAML instead of the '
                   'formatted output.')
@click.option('--last_auth', help='Can be something like 10h, 7d, or 2y')
@click.option('--assigned', help='True|False|None')
@click.option('--active', help='True|False|None')
@click.option('--orphaned',
              help='Whether the token is an orphaned token. Set to 1')
@click.option('--b32', is_flag=True,
              help='In case of exporting found tokens to CSV the seed is written base32 encoded instead of hex.')
@click.option('--chunksize', default=None,
              help='Read tokens from the database in smaller chunks to perform operations.')
def findtokens(last_auth, assigned, active, tokeninfo_key, tokeninfo_value,
               tokeninfo_value_greater_than, tokeninfo_value_less_than,
               tokeninfo_value_after, tokeninfo_value_before,
               orphaned, tokentype, serial, description, action, set_description,
               set_tokeninfo_key, set_tokeninfo_value, sum_tokens, tokenrealms, csv,
               chunksize, attributes, b32, has_not_tokeninfo_key, has_tokeninfo_key,
               tokenattribute, tokenattribute_value, tokenattribute_value_greater_than,
               tokenattribute_value_less_than, yaml):
    """
    Finds all tokens which match the conditions.
    """
    tokenattributes = [col.key for col in Token.__table__.columns]
    if tokenattribute and tokenattribute not in tokenattributes:
        sys.stderr.write("Unknown token attribute. Allowed attributes are {0!s}\n".format(
            ", ".join(tokenattributes)
        ))
        sys.exit(1)
    if action and action not in ALLOWED_ACTIONS:
        sys.stderr.write("Unknown action. Allowed actions are {0!s}\n".format(
            ", ".join(["'{0!s}'".format(x) for x in ALLOWED_ACTIONS])
        ))
        sys.exit(1)
    if chunksize is not None:
        chunksize = int(chunksize)
    # filter for tokeninfo values
    tvfilter = build_tokenvalue_filter(tokeninfo_key,
                                       tokeninfo_value,
                                       tokeninfo_value_greater_than,
                                       tokeninfo_value_less_than,
                                       tokeninfo_value_after,
                                       tokeninfo_value_before)
    # filter for token attribute
    tafilter = build_tokenvalue_filter(tokenattribute,
                                       tokenattribute_value,
                                       tokenattribute_value_greater_than,
                                       tokenattribute_value_less_than,
                                       None, None)
    generator = _get_tokenlist(last_auth, assigned, active,
                               tokeninfo_key, tvfilter,
                               tokenattribute, tafilter,
                               orphaned, tokentype, serial,
                               description, chunksize, has_not_tokeninfo_key,
                               has_tokeninfo_key)
    if chunksize is not None:
        sys.stderr.write("+ Reading tokens from database in chunks of {}...\n".format(chunksize))
    else:
        sys.stderr.write("+ Reading tokens from database...\n")
    for tlist in generator:
        sys.stderr.write("+ Tokens read. Starting action.\n")
        if not action:
            if not csv:
                print("Token serial\tTokeninfo")
                print("=" * 42)
                for token_obj in tlist:
                    print("{0!s} ({1!s})\n\t\t{2!s}\n\t\t{3!s}".format(
                        token_obj.token.serial,
                        token_obj.token.tokentype,
                        token_obj.token.description,
                        token_obj.get_tokeninfo()))
            else:
                for token_obj in tlist:
                    print("'{!s}','{!s}','{!s}','{!s}'".format(
                        token_obj.token.serial,
                        token_obj.token.tokentype,
                        token_obj.token.description,
                        token_obj.get_tokeninfo()
                    ))

        elif action == "listuser":
            if not sum_tokens:
                tokens = export_token_data(tlist, attributes)
                for token in tokens:
                    print(",".join(["'{0!s}'".format(x) for x in token]))
            else:
                users = export_user_data(tlist, attributes)
                for user, tokens in users.items():
                    print("{0!s},{1!s}".format(user, len(tokens)))

        elif action == "export":
            if csv:
                for tokenobj in tlist:
                    if tokenobj.type.lower() not in ["totp", "hotp"]:
                        continue
                    token_dict = tokenobj._to_dict(b32=b32)
                    owner = "{!s}@{!s}".format(tokenobj.user.login, tokenobj.user.realm)if tokenobj.user else "n/a"
                    if type == "totp":
                        print("{!s}, {!s}, {!s}, {!s}, {!s}, {!s}".format(owner, token_dict.get("serial"),
                                                                          token_dict.get("otpkey"),
                                                                          token_dict.get("type"),
                                                                          token_dict.get("otplen"),
                                                                          token_dict.get("timestep")))
                    else:
                        print("{!s}, {!s}, {!s}, {!s}, {!s}".format(owner, token_dict.get("serial"),
                                                                    token_dict.get("otpkey"),
                                                                    token_dict.get("type"),
                                                                    token_dict.get("otplen")))
            elif yaml:
                token_list = []
                for tokenobj in tlist:
                    try:
                        token_dict = tokenobj._to_dict(b32=b32)
                        token_dict["owner"] = "{!s}@{!s}".format(tokenobj.user.login,
                                                                 tokenobj.user.realm) if tokenobj.user else "n/a"
                        token_list.append(token_dict)
                    except Exception as e:
                        sys.stderr.write("\nFailed to export token {0!s}.\n".format(token_dict.get("serial")))
                print(yaml_safe_dump(token_list))
            else:
                key, token_num, soup = export_pskc(tlist)
                sys.stderr.write("\n{0!s} tokens exported.\n".format(token_num))
                sys.stderr.write("\nThis is the AES encryption key of the token seeds.\n"
                                 "You need this key to import the "
                                 "tokens again:\n\n\t{0!s}\n\n".format(key))
                print("{0!s}".format(soup))
        else:
            for token_obj in tlist:
                try:
                    if action == "tokenrealms":
                        trealms = [r.strip() for r in tokenrealms.split(",") if r]
                        token_obj.set_realms(trealms)
                        print("Setting realms of token {0!s} to {1!s}.".format(token_obj.token.serial, trealms))
                    if action == "disable":
                        enable_token(serial=token_obj.token.serial, enable=False)
                        print("Disabling token {0!s}".format(token_obj.token.serial))
                    elif action == "delete":
                        remove_token(serial=token_obj.token.serial)
                        print("Deleting token {0!s}".format(token_obj.token.serial))
                    elif action == "unassign":
                        unassign_token(serial=token_obj.token.serial)
                        print("Unassigning token {0!s}".format(token_obj.token.serial))
                    elif action == "mark":
                        if set_description:
                            print("Setting description for token {0!s}: {1!s}".format(
                                token_obj.token.serial, set_description))
                            token_obj.set_description(set_description)
                            token_obj.save()
                        if set_tokeninfo_value and set_tokeninfo_key:
                            print("Setting tokeninfo for token {0!s}: {1!s}={2!s}".format(
                                token_obj.token.serial, set_tokeninfo_key, set_tokeninfo_value))
                            token_obj.add_tokeninfo(set_tokeninfo_key, set_tokeninfo_value)
                            token_obj.save()
                except Exception as exx:
                    print("Failed to process token {0}.".format(
                        token_obj.token.serial))
                    print("{0}".format(exx))
