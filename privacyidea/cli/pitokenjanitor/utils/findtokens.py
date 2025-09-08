# SPDX-FileCopyrightText: (C) 2024 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# 2024-11-11 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#            New pi-token-janitor script
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
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Generator, Callable, Union

import click
from cryptography.fernet import Fernet
from dateutil import parser
from dateutil.tz import tzlocal
from flask.cli import AppGroup
from yaml import safe_dump as yaml_safe_dump

from privacyidea.lib.container import find_container_for_token
from privacyidea.lib.error import ResolverError
from privacyidea.lib.importotp import export_pskc
from privacyidea.lib.token import unassign_token, remove_token, get_tokens_paginated_generator, export_tokens
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.utils import parse_legacy_time, is_true
from privacyidea.models import Token, TokenContainer

allowed_tokenattributes = [col.key for col in Token.__table__.columns]

comparator_pattern = re.compile(r"^\s*([^!=<>]+?)\s*([!=<>])\s*([^!=<>]+?)\s*$")


def _try_convert_to_integer(given_value_string: str) -> int:
    try:
        return int(given_value_string)
    except ValueError:
        raise click.ClickException(f'Not an integer: {given_value_string}')


def _try_convert_to_datetime(given_value_string: str) -> datetime:
    try:
        parsed = parser.parse(given_value_string, dayfirst=False)
        if not parsed.tzinfo:
            # If not timezone is given we assume the timestamp is given in local time
            parsed = parsed.replace(tzinfo=tzlocal())
        return parsed
    except ValueError:
        raise


def _compare_regex_or_equal(given_regex: str) -> Callable[[Union[int, bool, str]], bool]:
    def comparator(value: Union[int, bool, str]) -> bool:
        if type(value) in (int, bool):
            # If the value from the database is an integer, we compare "equals integer"
            given_value = _try_convert_to_integer(given_regex)
            return given_value == value
        else:
            # if the value from the database is a string, we compare regex
            return bool(re.search(given_regex, value))

    return comparator


def _compare_not(given_regex: str) -> Callable[[Union[int, bool, str]], bool]:
    def comparator(value: Union[int, bool, str]) -> bool:
        if type(value) in (int, bool):
            # If the value from the database is an integer, we compare "equals integer"
            given_value = _try_convert_to_integer(given_regex)
            return given_value != value
        else:
            # if the value from the database is a string, we compare regex
            return not re.search(given_regex, value)

    return comparator


def _compare_greater_than(given_value: Union[int, str]) -> Callable[[int], bool]:
    """
    :return: a function which returns True if its parameter (converted to an integer)
             is greater than *given_value_string* (converted to an integer).
    """
    given_value = int(given_value)

    def comparator(value: int) -> bool:
        try:
            return int(value) > given_value
        except ValueError:
            return False

    return comparator


def _compare_less_than(given_value: Union[int, str]) -> Callable[[int], bool]:
    """
    :return: a function which returns True if its parameter (converted to an integer)
             is less than *given_value_string* (converted to an integer).
    """
    given_value = int(given_value)

    def comparator(value: int) -> bool:
        try:
            return int(value) < given_value
        except ValueError:
            return False

    return comparator


def _compare_after(given_value: datetime) -> Callable[[str], bool]:
    """
    :return: a function which returns True if its parameter (converted to a datetime) occurs after
             given_value.
    """

    def comparator(value: str):
        try:
            return parse_legacy_time(value, return_date=True) > given_value
        except ValueError:
            return False

    return comparator


def _compare_before(given_value: datetime) -> Callable[[str], bool]:
    """
    :return: a function which returns True if its parameter (converted to a datetime) occurs before
             given_value.
    """

    def comparator(value: str):
        try:
            return parse_legacy_time(value, return_date=True) < given_value
        except ValueError:
            return False

    return comparator


def build_filter(filter_string: str, allowed_keys: list[str] = None) -> tuple[str, Callable]:
    """
    Build and return a filter closure, which is based on the given filter_string.
    The filter closure takes a value and returns True if the user-defined criterion matches.

    :param: filter_string: a filter string which contains the key, the operator and the value
    :type filter_string: str
    :param allowed_keys: list of allowed values for keys
    :type allowed_keys: list
    :return: a tuple with the given key and comparator closure with the given value
    :rtype: func
    """
    match = comparator_pattern.match(filter_string)
    if not match:
        raise click.ClickException(f'The option requires a filter '
                                   f'syntax like: "<key> = <value>" with '
                                   f'possible comparators "=", "<", ">" and "!". '
                                   f'(given: "{filter_string}")')
    if allowed_keys and match.group(1) not in allowed_keys:
        raise click.ClickException(f"Key '{match.group(1)}' not allowed. "
                                   f"Allowed values for keys are '{allowed_keys}'")
    if match.group(2) == '=':
        return match.group(1), _compare_regex_or_equal(match.group(3))
    elif match.group(2) == '<':
        try:  # first try to convert the given value to an integer
            given_value = int(match.group(3))
            return match.group(1), _compare_less_than(given_value)
        except ValueError:
            try:  # then we try to parse as a datetime object
                given_value = _try_convert_to_datetime(match.group(3))
                return match.group(1), _compare_before(given_value)
            except ValueError:
                raise click.ClickException(f"Unable to find a comparator for {filter_string}")
    elif match.group(2) == '>':
        try:  # first try to convert the given value to an integer
            given_value = int(match.group(3))
            return match.group(1), _compare_greater_than(given_value)
        except ValueError:
            try:  # try to convert the given value to datetime
                given_value = _try_convert_to_datetime(match.group(3))
                return match.group(1), _compare_after(given_value)
            except ValueError:
                raise click.ClickException(f"Unable to find a comparator for {filter_string}")
    elif match.group(2) == '!':
        return match.group(1), _compare_not(match.group(3))
    else:
        raise click.ClickException('Invalid matching operator. Use "=", ">", "<" or "!"')


filter_funcs = {"=": _compare_regex_or_equal,
                "<": _compare_less_than,
                ">": _compare_greater_than,
                "!": _compare_not}


def build_token_attribute_filter(tokenattribute: str) -> tuple[str, Callable]:
    """
    Build and return a token attribute filter.
    The tokenattribute is separated into its components and the appropriate
    filter closure is returned with the parsed value.

    :param: tokenattribute: a string which contains the key, the operator and the value
    :type tokenattribute: str
    :return: tuple of the parsed attribute and a comparator function
    :rtype: tuple
    """
    match = comparator_pattern.match(tokenattribute)
    if not match:
        raise click.ClickException(f'The tokenattribute option requires a filter '
                                   f'syntax like: "<attribute> = <value>" with '
                                   f'possible comparators "=", "<", ">" and "!". '
                                   f'(given: "{tokenattribute}")')
    if match.group(1) not in allowed_tokenattributes:
        raise click.ClickException(f"Token attribute {match.group(1)} not allowed! "
                                   f"Allowed token attributes are: {allowed_tokenattributes}")
    else:
        return match.group(1), filter_funcs[match.group(2)](match.group(3))


def export_token_data(token_list: list, token_attributes: list = None,
                      user_attributes: list = None) -> list[dict]:
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
                      "tokentype": f'{token_obj.token.tokentype}',
                      "realms": f'{token_obj.get_realms()}'}
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


def export_user_data(token_list: list, user_attributes: list = None) -> dict:
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
        except Exception as e:
            sys.stderr.write(f"Failed to determine user for token {token_obj.token.serial} ({e}.\n")
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


def _get_tokenlist(assigned: Union[bool, None], active: Union[bool, None], range_of_serial: str,
                   tokeninfo_filter, tokenattribute_filter: list[tuple[str, Callable]],
                   tokenowner_filter, tokencontaner_filter, tokentype, realm, resolver, rollout_state,
                   orphaned: Union[bool, None], chunksize: int, has_not_tokeninfo_key, has_tokeninfo_key,
                   orphaned_on_error: bool = False) -> Generator[TokenClass, None, None]:
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
        for token_obj in token_object_list:
            add = True
            # TODO: We could do this with regex and the tokeninfo filter
            if has_not_tokeninfo_key:
                if has_not_tokeninfo_key in token_obj.get_tokeninfo():
                    add = False
            if has_tokeninfo_key:
                if has_tokeninfo_key not in token_obj.get_tokeninfo():
                    add = False
            if range_of_serial:
                if not range_of_serial[0] <= token_obj.token.serial <= range_of_serial[1]:
                    add = False
            if tokeninfo_filter:
                for tokeninfo_key, tokeninfo_comparator in tokeninfo_filter:
                    value = token_obj.get_tokeninfo(tokeninfo_key)
                    # if the tokeninfo key is not even set, it does not match the filter
                    if value is None:
                        add = False
                    elif not tokeninfo_comparator(value):
                        add = False
            if tokenattribute_filter:
                for tokenattribute_key, tokenattribute_comparator in tokenattribute_filter:
                    value = token_obj.token.get(tokenattribute_key)
                    if value is None:
                        add = False
                    elif not tokenattribute_comparator(value):
                        add = False
            if tokenowner_filter:
                try:
                    user = token_obj.user
                    if user is not None:
                        # First check for attributes of the user object
                        for tokenowner_key, tokenowner_comparator in tokenowner_filter:
                            if tokenowner_key in ["uid", "resolver", "realm", "login"]:
                                value = getattr(user, tokenowner_key)
                            else:
                                value = user.info.get(tokenowner_key)
                            if value is None:
                                add = False
                            elif not tokenowner_comparator(value):
                                add = False
                    else:
                        add = False
                except ResolverError:
                    # Unable to resolve user, no filter applicable
                    add = False
            if tokencontaner_filter:
                for tokenowner_key in tokencontaner_filter:
                    container = find_container_for_token(token_obj.token.serial)
                    if container is not None:
                        container_info = vars(container)
                        container_info["serial"] = container.serial
                        container_info["type"] = container.type
                        container_info["description"] = container.description
                        container_info["realm"] = container.realms
                        container_info["last_seen"] = container.last_seen
                        container_info["last_update"] = container.last_updated
                        value = container_info.get(tokenowner_key[0])
                        if value is None:
                            add = False
                        elif not all(comparator(value) for comparator in tokenowner_key[1]):
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
                    except ResolverError:
                        # Could not resolve user due to errors in the resolver.
                        # Don't mark the token as orphaned.
                        add = orphaned_on_error
                else:
                    try:
                        if token_obj.user is not None and not token_obj.user.exist():
                            add = False
                    except ResolverError:
                        add = not orphaned_on_error

            if add:
                # if everything matched, we append the token object
                filtered_list.append(token_obj)

        yield filtered_list


@click.group('find', invoke_without_command=True, cls=AppGroup)
@click.option('--chunksize', default=1000, show_default=True,
              help='The number of tokens to fetch in one request.')
# TODO: Maby remove has-not-tokeninfo-key and has-tokeninfo-key and use regex instead
@click.option('--has-not-tokeninfo-key',
              help='filters for tokens that have not given the specified tokeninfo-key')
@click.option('--has-tokeninfo-key',
              help='filters for tokens that have given the specified tokeninfo-key.')
@click.option('--tokeninfo', 'tokeninfos', multiple=True,
              help='Match for a certain tokeninfo from the database.')
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
@click.option('--active',
              help='Whether to token is active/enabled. Can be "True" or "False"')
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
    ta_filter = []
    if tokenattributes:
        for tokenattribute in tokenattributes:
            ta_filter.append(build_token_attribute_filter(tokenattribute))

    ti_filter = []
    if tokeninfos:
        for tokeninfo in tokeninfos:
            ti_filter.append(build_filter(tokeninfo))

    to_filter = []
    if tokenowners:
        for owner in tokenowners:
            to_filter.append(build_filter(owner))

    tc_filter = []
    if tokencontainers:
        allowed_container_keys = [col.key for col in TokenContainer.__table__.columns]
        for container in tokencontainers:
            tc_filter.append(build_filter(container, allowed_container_keys))

    ctx.obj = dict()

    ctx.obj['tokens'] = _get_tokenlist(assigned=assigned, active=active, range_of_serial=range_of_serial,
                                       tokeninfo_filter=ti_filter, tokenattribute_filter=ta_filter,
                                       tokenowner_filter=to_filter, tokencontaner_filter=tc_filter,
                                       tokentype=None, realm=None, resolver=None,
                                       rollout_state=None, orphaned=orphaned,
                                       chunksize=chunksize, has_not_tokeninfo_key=has_not_tokeninfo_key,
                                       has_tokeninfo_key=has_tokeninfo_key,
                                       orphaned_on_error=orphaned_on_error)

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
              type=click.Choice(['csv', 'yaml', 'pskc', 'pi'], case_sensitive=False),
              default='pi', show_default=True,
              help="The output format of the token export. CSV export only "
                   "allows TOTP and HOTP token types")
@click.option('--b32', is_flag=True,
              help="In case of exporting tokens to CSV or YAML, the seed is "
                   "written as base32 encoded instead of hex.")
@click.option('--file', required=False, type=click.File('w'), default=sys.stdout,
              show_default="<stdout>",
              help='The file to export the tokens to.')
@click.option('--user/--no-user', default=True,
              help='Include user information.')
@click.pass_context
def export(ctx, export_format, b32, file, user):
    """
    Export found tokens.
    """
    if export_format == "pskc":
        all_tokens = []
        for token_list in ctx.obj['tokens']:
            all_tokens.extend(token_list)
        key, token_num, soup = export_pskc(all_tokens)
        sys.stderr.write(f"\n{token_num} tokens exported.\n")
        sys.stderr.write(f"\nThis is the AES encryption key of the token seeds.\n"
                         f"You need this key to import the "
                         f"tokens again:\n\n\t{key}\n\n")
        file.write(str(soup))

    elif export_format == "csv":
        exported_tokens = []
        for token_list in ctx.obj['tokens']:
            for token in token_list:
                if token.type.lower() not in ["totp", "hotp"]:
                    continue
                token_dict = token._to_dict(b32=b32)
                owner = f"{token.user.login}@{token.user.realm}" if (token.user and user) else "n/a"
                export_string = (f"{owner}, {token_dict.get('serial')}, {token_dict.get('otpkey')}, "
                                 f"{token_dict.get('type')}, {token_dict.get('otplen')}")
                if token.type.lower() == "totp":
                    exported_tokens.append(
                        export_string + f", {token_dict.get('info_list', {}).get('timeStep')}")
                else:
                    exported_tokens.append(export_string)
        file.write('\n'.join(exported_tokens))

    elif export_format == "yaml":
        token_list = []
        for token_list in ctx.obj['tokens']:
            for token in token_list:
                try:
                    token_dict = token._to_dict(b32=b32)
                    token_dict["owner"] = f"{token.user.login}@{token.user.realm}" if (
                            token.user and user) else "n/a"
                    token_list.append(token_dict)
                except Exception as e:
                    sys.stderr.write(f"\nFailed to export token {token.get_serial()} ({e}).\n")
        file.write(yaml_safe_dump(token_list))

    elif export_format == "pi":
        key = Fernet.generate_key().decode()
        exported_tokens = []
        failed_exports = []
        for token_list in ctx.obj['tokens']:
            result = export_tokens(token_list, export_user=user)
            exported_tokens.extend(result.successful_tokens)
            failed_exports.extend(result.failed_tokens)
        list_of_exported_tokens = json.dumps(exported_tokens, default=repr, indent=2)
        f = Fernet(key)
        file.write(f.encrypt(list_of_exported_tokens.encode()).decode())
        if file == sys.stdout:
            click.echo("\n\n")
        click.echo(f"Successfully exported {len(exported_tokens)} tokens.")
        if failed_exports:
            click.echo(f"Failed to export {len(failed_exports)} tokens:")
            for serial in failed_exports:
                click.echo(f"{serial}")
            click.echo(f"Check the logfile for the cause of the failures.")

        click.secho(f'\nThe key to import the tokens is:\n\n\t{key}\n\n', fg='red', err=True)
        if file != sys.stdout:
            click.echo(f'You can use this key to import the tokens with the command:\n'
                       f'pi-tokenjanitor import privacyidea {file.name} --key {key}\n', err=True)
        if click.confirm('Do you want to save the key to a file?', default=False, err=True):
            key_file = click.prompt('Please enter the file name to save the key to',
                                    type=click.File('w'), err=True)
            key_file.write(key)
            click.echo(f'The export encryption key has been saved to "{key_file.name}"', err=True)

    if file != sys.stdout:
        click.echo(f'The tokens have been exported to "{file.name}".\n')


@findtokens.command('set_tokenrealms')
@click.option('--tokenrealm', 'tokenrealms', multiple=True, required=True, type=str)
@click.pass_context
def set_tokenrealms(ctx, tokenrealms):
    """
    Set the realms of the found tokens.
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
    Disable found tokens.
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
    Enable found tokens.
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
    Delete found tokens.
    """
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            remove_token(serial=token_obj.token.serial)
            click.echo(f"Deleted token {token_obj.token.serial}")


@findtokens.command('unassign')
@click.pass_context
def unassign(ctx):
    """
    Unassign the found tokens from their owners.
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
    match = re.match(r"\s*(\w+)\s*(=)\s*(\w+)\s*$", tokeninfo)
    if not match:
        raise click.ClickException(f"Can not parse tokeninfo to set. It should "
                                   f"be given as \"<key> = <value>\". (actual: {tokeninfo})")
    tokeninfo_key = match.group(1)
    tokeninfo_value = match.group(3)
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            token_obj.add_tokeninfo(tokeninfo_key, tokeninfo_value)
            token_obj.save()
            click.echo(f"Set tokeninfo for token {token_obj.token.serial}: {tokeninfo_key}={tokeninfo_value}")


@findtokens.command('remove_tokeninfo')
@click.option('--tokeninfo_key', required=True, type=str)
@click.pass_context
def remove_tokeninfo(ctx, tokeninfo_key):
    """
    Remove the tokeninfo of the found tokens.
    """
    for tlist in ctx.obj['tokens']:
        for token_obj in tlist:
            token_obj.del_tokeninfo(tokeninfo_key)
            token_obj.save()
            click.echo(f"Removed tokeninfo '{tokeninfo_key}' for token {token_obj.token.serial}")
