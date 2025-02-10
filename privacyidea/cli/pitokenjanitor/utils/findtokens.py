# SPDX-FileCopyrightText: (C) 2024 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
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
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys

from dateutil import parser
import re
from flask.cli import AppGroup

import click
from collections import defaultdict
from dateutil.tz import tzlocal, tzutc
from yaml import safe_dump as yaml_safe_dump

from privacyidea.lib.container import find_container_for_token
from privacyidea.lib.error import ResolverError
from privacyidea.lib.importotp import export_pskc
from privacyidea.lib.policy import ACTION
from privacyidea.lib.utils import parse_legacy_time, is_true

from privacyidea.models import Token, TokenContainer
from privacyidea.lib.token import unassign_token, enable_token, remove_token, get_tokens_paginated_generator

allowed_tokenattributes = [col.key for col in Token.__table__.columns]


def _try_convert_to_integer(given_value_string):
    try:
        return int(given_value_string)
    except ValueError:
        raise click.ClickException(f'Not an integer: {given_value_string}')


def _try_convert_to_datetime(given_value_string):
    try:
        parsed = parser.parse(given_value_string, dayfirst=False)
        if not parsed.tzinfo:
            # If not timezone is given we assume the timestamp is given in local time
            parsed = parsed.replace(tzinfo=tzlocal())
        return parsed
    except ValueError:
        raise


def _compare_regex_or_equal(_key, given_regex):
    def comparator(value):
        if type(value) in (int, bool):
            # If the value from the database is an integer, we compare "equals integer"
            given_value = _try_convert_to_integer(given_regex)
            return given_value == value
        else:
            # if the value from the database is a string, we compare regex
            return re.search(given_regex, value)

    return comparator


def _compare_not(_key, given_regex):
    def comparator(value):
        if type(value) in (int, bool):
            # If the value from the database is an integer, we compare "equals integer"
            given_value = _try_convert_to_integer(given_regex)
            return given_value != value
        else:
            # if the value from the database is a string, we compare regex
            return not re.search(given_regex, value)

    return comparator


def _parse_datetime(key, value):
    # TODO: Rewrite this function after #1586 is merged
    if key == ACTION.LASTAUTH:
        # Special case for last_auth: Legacy values are given in UTC time!
        last_auth = parser.parse(value)
        if not last_auth.tzinfo:
            last_auth = last_auth.replace(tzinfo=tzutc())
        return last_auth
    else:
        # Other values are given in local time
        return parser.parse(parse_legacy_time(value))


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


def build_tokenvalue_filter(m):
    """
    Build and return a token value filter, which is a list of comparator functions.
    Each comparator function takes a tokeninfo value and returns True if the
    user-defined criterion matches.
    The filter matches a record if *all* comparator functions return True, i.e.
    if the conjunction of all comparators returns True.

    :param: m: a matching object from a regular expression which contains the key, the operator and the value
    :return: a list of comparator functions
    """
    tv_filter = []
    if m.group(2) == '=':
        tv_filter.append(_compare_regex_or_equal(m.group(1), m.group(3)))
    elif m.group(2) == '<':
        try:  # try to convert the given value to datetime
            given_value = _try_convert_to_datetime(m.group(3))
            tv_filter.append(_compare_before(m.group(1), given_value))
        except ValueError:
            tv_filter.append(_compare_greater_than(m.group(1), m.group(3)))
    elif m.group(2) == '>':
        try:  # try to convert the given value to datetime
            given_value = _try_convert_to_datetime(m.group(3))
            tv_filter.append(_compare_after(m.group(1), given_value))
        except ValueError:
            tv_filter.append(_compare_less_than(m.group(1), m.group(3)))
    elif m.group(2) == '!':
        tv_filter.append(_compare_not(m.group(1), m.group(3)))
    else:
        raise click.ClickException("Invalid matching operator. Use =, >, <, or !")
    return tv_filter


def build_tokenattribute_filter(m):
    """
    Build and return a token attribute filter, which is a list of comparator functions.
    Each comparator function takes a tokenattribute value and returns True if the
    user-defined criterion matches.

    :param: m: a matching object from a regular expression which contains the key, the operator and the value
    :type m: re.Matcher
    :return: a comparator function
    :rtype: func
    """
    filter_func = {"=": _compare_regex_or_equal,
                   "<": _compare_less_than,
                   ">": _compare_greater_than,
                   "!": _compare_not}
    try:
        ta_filter = filter_func[m.group(2)](m.group(1), m.group(3))
    except KeyError:
        raise click.ClickException("Invalid matching operator. Use =, >, <, or !")

    return ta_filter


def export_token_data(token_list, token_attributes=None, user_attributes=None):
    """
    Returns a list of tokens. Each token again is a dictionary of the requested
    token attributes, tokeninfo and user attributes

    :param token_list: List of token objects to export
    :param token_attributes: add additional token attributes
    :param user_attributes: add additional user attributes
    :return: a list of token dictionaries with the requested attributes
    :rtype: list
    """
    tokens = []
    for token_obj in token_list:
        token_data = {"serial": f'{token_obj.token.serial}',
                      "tokentype": f'{token_obj.token.tokentype}'}
        token_info = token_obj.get_tokeninfo()
        export_ti = {}
        if token_attributes:
            for att in token_attributes:
                if att in allowed_tokenattributes:
                    token_data[att] = f'{token_obj.token.get(att)}'
                else:
                    if att in token_info:
                        export_ti[att] = f'{token_info[att]}'
            token_data["info"] = export_ti
        else:
            # Return all token attributes/tokeninfo
            token_data["info"] = token_info

        if user_attributes:
            try:
                user_data = {}
                user = token_obj.user
                if user:
                    for att in user_attributes:
                        if att == "uid":
                            user_data[att] = f'{user.uid}'
                        elif att == "resolver":
                            user_data[att] = f'{user.resolver}'
                        elif att == "realm":
                            user_data[att] = f'{user.realm}'
                        else:
                            if att in user.info:
                                user_data[att] = f'{user.info[att]}'
                token_data["user"] = user_data
            except Exception as e:
                token_data["user"] = {"error": f"failed to resolve user: {e}"}
        tokens.append(token_data)
    return tokens


def export_user_data(token_list, user_attributes=None):
    """
    Returns a list of users with the information how many tokens this user has assigned

    :param token_list:
    :param user_attributes: display additional user attributes
    :return:
    :rtype: dict
    """
    users = {}
    for token_obj in token_list:
        try:
            user = token_obj.user
        except Exception:
            sys.stderr.write(f"Failed to determine user for token {token_obj.token.serial}.\n")
            user = None
        if user:
            uid = (f"'{user.info.get('username', '')}','{user.info.get('givenname', '')}',"
                   f"'{user.info.get('surname', '')}','{user.uid}','{user.resolver}','{user.realm}'")
            if user_attributes:
                for att in user_attributes:
                    uid += f",'{user.info.get(att, '')}'"
        else:
            uid = "N/A" + ", " * 5

        if uid in users.keys():
            users[uid].append(token_obj.token.serial)
        else:
            users[uid] = [token_obj.token.serial]

    return users


def _get_tokenlist(assigned, active, range_of_seriel, tokeninfo_filter, tokenattribute_filter,
                   tokenowner_filter, tokencontaner_filter, tokentype, realm, resolver, rollout_state,
                   orphaned, chunksize, has_not_tokeninfo_key, has_tokeninfo_key,
                   orphaned_on_error=False):
    if assigned is not None:
        assigned = is_true(assigned)
    if active is not None:
        active = is_true(active)

    iterable = get_tokens_paginated_generator(tokentype=tokentype,
                                              realm=realm,
                                              resolver=resolver,
                                              rollout_state=rollout_state,
                                              active=active,
                                              assigned=assigned,
                                              psize=chunksize)

    for token_object_list in iterable:
        filtered_list = []
        token_count = 0
        token_found = 0
        for token_obj in token_object_list:
            add = True
            token_count += 1
            # TODO: We could do this with regex and the tokeninfo filter
            if has_not_tokeninfo_key:
                if has_not_tokeninfo_key in token_obj.get_tokeninfo():
                    add = False
            if has_tokeninfo_key:
                if has_tokeninfo_key not in token_obj.get_tokeninfo():
                    add = False
            if range_of_seriel:
                if not range_of_seriel[0] <= token_obj.token.serial <= range_of_seriel[1]:
                    add = False
            if tokeninfo_filter:
                for att in tokeninfo_filter:
                    value = token_obj.get_tokeninfo(att[0])
                    # if the tokeninfo key is not even set, it does not match the filter
                    if value is None:
                        add = False
                    # suppose not all comparator functions return True
                    # => at least one comparator function returns False
                    # => at least one user-supplied criterion does not match
                    # => the token object does not match the user-supplied criteria
                    elif not all(comparator(value) for comparator in att[1]):
                        add = False
            if tokenattribute_filter:
                for att in tokenattribute_filter:
                    value = token_obj.token.get(att[0])
                    if value is None:
                        add = False
                    elif not att[1](value):
                        add = False
            if tokenowner_filter:
                for att in tokenowner_filter:
                    user = token_obj.user
                    if user is not None:
                        value = user.info.get(att[0])
                        if value is None:
                            add = False
                        elif not all(comparator(value) for comparator in att[1]):
                            add = False
                    else:
                        add = False
            if tokencontaner_filter:
                for att in tokencontaner_filter:
                    container = find_container_for_token(token_obj.token.serial)
                    if container is not None:
                        container_info = vars(container)
                        container_info["serial"] = container.serial
                        container_info["type"] = container.type
                        container_info["description"] = container.description
                        container_info["realm"] = container.realms
                        container_info["last_seen"] = container.last_seen
                        container_info["last_update"] = container.last_updated
                        value = container_info.get(att[0])
                        if value is None:
                            add = False
                        elif not all(comparator(value) for comparator in att[1]):
                            add = False
                    else:
                        add = False
            if orphaned is not None:
                if is_true(orphaned):
                    try:
                        if token_obj.user is None or token_obj.user.exist():
                            # Either the token has no user assigned or the
                            # assigned user exists in the resolver
                            add = False
                    except ResolverError as e:
                        # Could not resolve user due to errors in the resolver.
                        # Don't mark the token as orphaned.
                        add = is_true(orphaned_on_error)
                else:
                    try:
                        if token_obj.user is not None and not token_obj.user.exist():
                            add = False
                    except ResolverError as e:
                        pass

            if add:
                token_found += 1
                # if everything matched, we append the token object
                filtered_list.append(token_obj)

        yield filtered_list


@click.group('find', invoke_without_command=True, cls=AppGroup)
@click.option('--chunksize', default=1000, help='The number of tokens to fetch in one request.')
# TODO: Maby remove has-not-tokeninfo-key and has-tokeninfo-key and use regex instead
@click.option('--has-not-tokeninfo-key', help='filters for tokens that have not given the specified tokeninfo-key')
@click.option('--has-tokeninfo-key', help='filters for tokens that have given the specified tokeninfo-key.')
@click.option('--tokeninfo', 'tokeninfos', multiple=True, help='Match for a certain tokeninfo from the database.')
@click.option('--tokenattribute', 'tokenattributes', multiple=True,
              help='Match for a certain token attribute from the database. You can use the following operators: '
                   '=, >, <, ! for you matching. For example: "rollout_state=clientwait" or "failcount>3".')
@click.option('--tokenowner', 'tokenowners', multiple=True,
              help='Match for certain information of the token owner from the database. '
                   'Example: user_id=642cf598-d9cf-1037-8083-a1df7d38c897.')
@click.option('--tokencontainer', 'tokencontainers', multiple=True,
              help='Match for certain information of tokencontainer from the database. Example: type=smartphone.')
@click.option('--assigned',
              help='Whether the token is assigned to a user. Can be "True" or "False"')
@click.option('--active', help='True|False|None')
@click.option('--orphaned',
              help='Whether the token is an orphaned token. Can be "True" or "False"')
@click.option('--orphaned-on-error', is_flag=True, default=False,
              help="Mark token as orphaned if an error occurred when resolving user.")
@click.option('--range-of-serial', help='A range of serial numbers to search for. '
                                        'For Example HOTP10000000-HOTP20000000')
@click.pass_context
def findtokens(ctx, chunksize, has_not_tokeninfo_key, has_tokeninfo_key,
               tokenattributes, tokeninfos, tokenowners, tokencontainers,
               assigned, active, orphaned, range_of_serial, orphaned_on_error):
    """
    Find all tokens which match the given conditions.
    """
    if range_of_serial:
        range_of_serial = range_of_serial.split("-")
    tafilter = []
    if tokenattributes:
        for tokenattribute in tokenattributes:
            m = re.match(r"\s*([^!=<>]+)\s*([!=<>])\s*([^!=<>]+)\s*$", tokenattribute)
            if not m:
                raise click.ClickException(f'The tokenattribute option requires '
                                           f'an operator like "=", "<", ">" or "!"!')
            if m.group(1) not in allowed_tokenattributes:
                raise click.ClickException(f"Tokenattribute {m.group(1)} not allowed. "
                                           f"Allowed tokenattributes are: {allowed_tokenattributes}")
            else:
                tafilter.append((m.group(1), build_tokenattribute_filter(m)))

    tvfilter = []
    if tokeninfos:
        for tokeninfo in tokeninfos:
            m = re.match(r"\s*([^!=<>]+)\s*([!=<>])\s*([^!=<>]+)\s*$", tokeninfo)
            tvfilter.append((m.group(1), build_tokenvalue_filter(m)))

    tofilter = []
    if tokenowners:
        for owner in tokenowners:
            m = re.match(r"\s*([^!=<>]+)\s*([!=<>])\s*([^!=<>]+)\s*$", owner)
            tofilter.append((m.group(1), build_tokenvalue_filter(m)))

    tcfilter = []
    if tokencontainers:
        allowed_containers = [col.key for col in TokenContainer.__table__.columns]
        allowed_containers = allowed_containers + ["serial", "type", "description", "realm", "last_seen", "last_update"]
        for container in tokencontainers:
            m = re.match(r"\s*([^!=<>]+)\s*([!=<>])\s*([^!=<>]+)\s*$", container)
            if m.group(1) not in allowed_containers:
                raise click.ClickException(f"Tokencontaner {m.group(1)} not allowed. "
                                           f"Allowed container attributes are: {allowed_containers}")
            else:
                tcfilter.append((m.group(1), build_tokenvalue_filter(m)))

    ctx.obj = dict()

    ctx.obj['tokens'] = _get_tokenlist(assigned=assigned, active=active, range_of_seriel=range_of_serial,
                                       tokeninfo_filter=tvfilter, tokenattribute_filter=tafilter,
                                       tokenowner_filter=tofilter, tokencontaner_filter=tcfilter,
                                       tokentype=None, realm=None, resolver=None,
                                       rollout_state=None, orphaned=orphaned,
                                       chunksize=chunksize, has_not_tokeninfo_key=has_not_tokeninfo_key,
                                       has_tokeninfo_key=has_tokeninfo_key,
                                       orphaned_on_error=orphaned_on_error)

    sys.stderr.write(f"+ Reading tokens from database in chunks of {chunksize}...\n")

    if ctx.invoked_subcommand is None:
        ctx.invoke(list_cmd)


@findtokens.command('list')
@click.option('-u', '--show-user-attribute', 'user_attributes', multiple=True,
              help='Show additional user attributes (can be given multiple times).')
@click.option('-t', '--show-token-attribute', 'token_attributes', multiple=True,
              help='Show additional token attributes/tokeninfo values (can be given '
                   'multiple times). The default is to show all tokeninfo values.')
@click.option('-s', '--summarize', 'sum_tokens', is_flag=True, default=False,
              help='Reduce the output to show only the number of tokens owned by each user.')
@click.pass_context
def list_cmd(ctx, user_attributes, token_attributes, sum_tokens):
    """
    List all found tokens.
    """
    users_sum = defaultdict(int)
    for tlist in ctx.obj['tokens']:
        if not sum_tokens:
            tokens = export_token_data(tlist, token_attributes=token_attributes,
                                       user_attributes=user_attributes)
            for token in tokens:
                click.echo(token)
        else:
            users = export_user_data(tlist, user_attributes)
            for user, tokens in users.items():
                users_sum[user] += len(tokens)
    if sum_tokens:
        for user, count in users_sum.items():
            click.echo(f"{user},{count}")


@findtokens.command('export')
@click.option('--format', 'export_format',
              type=click.Choice(['csv', 'yaml', 'xml'], case_sensitive=False),
              default='xml', help='Please specify the format of the output. Possible values are: csv, yaml, xml. '
                                  'Default is xml.')
@click.option('--b32', is_flag=True,
              help='In case of exporting found tokens to CSV the seed is written base32 encoded instead of hex.')
# TODO: check if there is a better way
@click.pass_context
def export(ctx, export_format, b32):
    """
    Export found tokens.
    """
    for tlist in ctx.obj['tokens']:
        if export_format == "csv":
            for tokenobj in tlist:
                if tokenobj.type.lower() not in ["totp", "hotp"]:
                    continue
                token_dict = tokenobj._to_dict(b32=b32)
                owner = f"{tokenobj.user.login}@{tokenobj.user.realm}" if tokenobj.user else "n/a"
                export = (f"{owner}, {token_dict.get('serial')}, {token_dict.get('otpkey')}, {token_dict.get('type')}, "
                          f"{token_dict.get('otplen')}")
                if type == "totp":
                    print(export + "{token_dict.get('info_list', {}).get('timeStep')}")
                else:
                    print(export)
        elif export_format == "yaml":
            token_list = []
            for tokenobj in tlist:
                try:
                    token_dict = tokenobj._to_dict(b32=b32)
                    token_dict["owner"] = f"{tokenobj.user.login}@{tokenobj.user.realm}" if tokenobj.user else "n/a"
                    token_list.append(token_dict)
                except Exception as e:
                    sys.stderr.write(f"\nFailed to export token {tokenobj.get('serial')}.\n")
            print(yaml_safe_dump(token_list))
        else:
            key, token_num, soup = export_pskc(tlist)
            sys.stderr.write(f"\n{token_num} tokens exported.\n")
            sys.stderr.write(f"\nThis is the AES encryption key of the token seeds.\n"
                             "You need this key to import the "
                             "tokens again:\n\n\t{key}\n\n")
            print(f"{soup}")


@findtokens.command('set_tokenrealms')
@click.option('--tokenrealms', multiple=True, required=True, type=str)
@click.pass_context
def set_tokenrealms(ctx, tokenrealms):
    """
    Sets the realms of the found tokens.
    """
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            trealms = [r.strip() for r in tokenrealms if r]
            token_obj.set_realms(trealms)
            click.echo(f"Setting realms of token {token_obj.token.serial} to {trealms}.")


@findtokens.command('disable')
@click.pass_context
def disable(ctx):
    """
    Disable the found tokens.
    """
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            token_obj.enable(enable=False)
            token_obj.save()
            click.echo(f"Disabled token {token_obj.token.serial}")


@findtokens.command('enable')
@click.pass_context
def enable(ctx):
    """
    Disable the found tokens.
    """
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            token_obj.enable(enable=True)
            token_obj.save()
            click.echo(f"Enabled token {token_obj.token.serial}")


@findtokens.command('delete')
@click.pass_context
def delete(ctx):
    """
    Delete the found tokens.
    """
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            remove_token(serial=token_obj.token.serial)
            click.echo(f"Deleted token {token_obj.token.serial}")


@findtokens.command('unassign')
@click.pass_context
def unassign(ctx):
    """
    Unassigns the found tokens from their owners.
    """
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            unassign_token(serial=token_obj.token.serial)
            click.echo(f"Unassigned token {token_obj.token.serial}")


@findtokens.command('set_description')
@click.option('--description', required=True, type=str)
@click.pass_context
def set_description(ctx, description):
    """
    Sets the description of the found tokens.
    """
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            token_obj.set_description(description)
            token_obj.save()
            click.echo(f"Set description for token {token_obj.token.serial}: {description}")


@findtokens.command('set_tokeninfo')
@click.option('--tokeninfo', required=True, type=str)
@click.pass_context
def set_tokeninfo(ctx, tokeninfo):
    """
    Sets the tokeninfo of the found tokens.
    """
    m = re.match(r"\s*(\w+)\s*(=)\s*(\w+)\s*$", tokeninfo)
    tokeninfo_key = m.group(1)
    tokeninfo_value = m.group(3)
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            print(f"Setting tokeninfo for token {token_obj.token.serial}: {tokeninfo_key}={tokeninfo_value}")
            token_obj.add_tokeninfo(tokeninfo_key, tokeninfo_value)
            token_obj.save()


@findtokens.command('remove_tokeninfo')
@click.option('--tokeninfo_key', required=True, type=str)
@click.pass_context
def remove_tokeninfo(ctx, tokeninfo_key):
    """
    Remove the tokeninfo of the found tokens.
    """
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            print(f"Removing tokeninfo for token {token_obj.token.serial}: {tokeninfo_key}")
            token_obj.del_tokeninfo(tokeninfo_key)
            token_obj.save()
