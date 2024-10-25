import sys

from dateutil import parser
import re
from flask.cli import AppGroup

import click
from dateutil.tz import tzlocal, tzutc
from yaml import safe_dump as yaml_safe_dump
from privacyidea.lib.importotp import export_pskc
from privacyidea.lib.policy import ACTION
from privacyidea.lib.utils import parse_legacy_time

from privacyidea.models import Token, TokenOwner, TokenContainer
from privacyidea.lib.token import unassign_token, enable_token, remove_token, get_tokens_paginated_generator

find_cli = AppGroup("find")


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
    #TODO: Rewrite this function after #1586 is merged
    if key == ACTION.LASTAUTH:
        # Special case for last_auth: Legacy values are given in UTC time!
        last_auth = parser.parse(value)
        if not last_auth.tzinfo:
            last_auth = parser.parse(value, tzinfos=tzutc)
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
    filter = []
    if m.group(2) == '=':
        filter.append(_compare_regex_or_equal(m.group(1), m.group(3)))
    elif m.group(2) == '>':
        try: # try to convert the given value to datetime
            given_value = _try_convert_to_datetime(m.group(3))
            filter.append(_compare_before(m.group(1), given_value))
        except:
            filter.append(_compare_greater_than(m.group(1), m.group(3)))
    elif m.group(2) == '<':
        try: # try to convert the given value to datetime
            given_value = _try_convert_to_datetime(m.group(3))
            filter.append(_compare_after(m.group(1), given_value))
        except:
            filter.append(_compare_less_than(m.group(1), m.group(3)))
    elif m.group(2) == '!':
        filter.append(_compare_not(m.group(1), m.group(3)))
    else:
        raise click.ClickException("Invalid matching operator. Use =, >, <, or !")
    return filter


def export_token_data(token_list, attributes=None):
    """
    Returns a list of tokens. Each token again is a simple list of data

    :param token_list:
    :param attributes: display additional user attributes
    :return:
    """
    tokens = []
    for token_obj in token_list:
        token_data = [f'{token_obj.token.serial}',
                      f'{token_obj.token.tokentype}']
        try:
            user = token_obj.user
            if user:
                token_data.append(f'{user.info.get("username", "")}')
                token_data.append(f'{user.info.get("givenname", "")}')
                token_data.append(f'{user.info.get("surname", "")}')
                token_data.append(f'{user.uid}')
                token_data.append(f'{user.resolver}')
                token_data.append(f'{user.realm}')

            if attributes:
                for att in attributes.split(","):
                    token_data.append(f'{user.info.get(att, "")}')
        except Exception:
            sys.stderr.write(f'Failed to determine user for token {token_obj.token.serial}.\n')
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
            sys.stderr.write(f"Failed to determine user for token {token_obj.token.serial}.\n")
        if user:
            uid = (f"'{user.info.get("username", "")}','{user.info.get("givenname", "")}',"
                   f"'{ user.info.get("surname", "")}','{user.uid}','{user.resolver}','{user.realm}'")
            if attributes:
                for att in attributes.split(","):
                    uid += f",'{user.info.get(att, "")}'"
        else:
            uid = "N/A" + ", " * 5

        if uid in users.keys():
            users[uid].append(token_obj.token.serial)
        else:
            users[uid] = [token_obj.token.serial]

    return users


def _get_tokenlist(assigned, active, range_of_seriel, tokeninfo_filter, tokenattribute_filter,
                   tokenowner_filter, tokencontaner_filter, tokentype, realm, resolver, rollout_state,
                   orphaned, chunksize, has_not_tokeninfo_key, has_tokeninfo_key):
    filter_active = None
    filter_assigned = None
    orphaned = orphaned or ""

    if assigned is not None:
        filter_assigned = assigned.lower() == "true"
    if active is not None:
        filter_active = active.lower() == "true"


    iterable = get_tokens_paginated_generator(tokentype=tokentype,
                                              realm=realm,
                                              resolver=resolver,
                                              rollout_state=rollout_state,
                                              active=filter_active,
                                              assigned=filter_assigned,
                                              psize=chunksize)

    for tokenobj_list in iterable:
        filtered_list = []
        sys.stderr.write("++ Creating token object list.\n")
        tok_count = 0
        tok_found = 0
        for token_obj in tokenobj_list:
            sys.stderr.write(f'{tok_count} Tokens processed / {tok_found} Tokens found\r')
            sys.stderr.flush()
            tok_count += 1
            #TODO: We could do this with regex and the tokeninfo filter
            if has_not_tokeninfo_key:
                if has_not_tokeninfo_key in token_obj.get_tokeninfo():
                    continue
            if has_tokeninfo_key:
                if has_tokeninfo_key not in token_obj.get_tokeninfo():
                    continue
            if not range_of_seriel(0) <= token_obj.token.serial <= range_of_seriel(1):
                continue
            if tokeninfo_filter:
                for tokeninfo_key, tokeninfo_value_filter in tokeninfo_filter.items():
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
            if tokenattribute_filter:
                for tokenattribute, tokenattribute_filter in tokenattribute_filter.items():
                    value = token_obj.token.get(tokenattribute)
                    if value is None:
                        continue
                    if not all(comparator(value) for comparator in tokenattribute_filter):
                        continue
            if tokenowner_filter:
                for tokenowner, tokenowner_filter in tokenowner_filter.items():
                    value = token_obj.user.get(tokenowner)
                    if value is None:
                        continue
                    if not all(comparator(value) for comparator in tokenowner_filter):
                        continue
            if tokencontaner_filter:
                for tokencontaner, tokencontaner_filter in tokencontaner_filter.items():
                    value = token_obj.token.get(tokencontaner)
                    if value is None:
                        continue
                    if not all(comparator(value) for comparator in tokencontaner_filter):
                        continue
            if orphaned.upper() in ["1", "TRUE"] and not token_obj.is_orphaned():
                continue
            if orphaned.upper() in ["0", "FALSE"] and token_obj.is_orphaned():
                continue

            tok_found += 1
            # if everything matched, we append the token object
            filtered_list.append(token_obj)

        sys.stderr.write(f'{tok_count} Tokens processed / {tok_found} Tokens found\r\n')
        sys.stderr.write("++ Token object list created.\n")
        sys.stderr.flush()
        yield filtered_list


@find_cli.group('find')
#TODO: Maby remove has-not-tokeninfo-key and has-tokeninfo-key and use regex instead
@click.option('--has-not-tokeninfo-key', help='filters for tokens that have not given the specified tokeninfo-key')
@click.option('--has-tokeninfo-key', help='filters for tokens that have given the specified tokeninfo-key.')
@click.option('--tokeninfo', help='Match for a certain tokeninfo from the database.')
@click.option('--tokenattribute', help='Match for a certain token attribute from the database. '
                                        'You can use the following operators: =, >, <, ! for you matching. For example: '
                                        '"rollout_state=clientwait" or "failcount>3".')
@click.option('--tokenowner', help='Match for certain information of the token owner from the database. '
                                   'Exemple: user_id=642cf598-d9cf-1037-8083-a1df7d38c897.')
@click.option('--tokencontaner', help='A comma separated list of contaner, to which the tokens should be assigned.')
@click.option('--assigned', help='True|False|None')
@click.option('--active', help='True|False|None')
@click.option('--orphaned', help='Whether the token is an orphaned token. Set to 1')
@click.option('--range-of-serial', help='A range of serial numbers to search for. For Example HOTP10000000-HOTP20000000')
@click.pass_context
def findtokens(ctx, has_not_tokeninfo_key, has_tokeninfo_key, tokenattribute, tokeninfo, tokenowner,
               tokencontaner, assigned, active, orphaned, range_of_serial):
    """
    Finds all tokens which match the conditions.
    """
    if range_of_serial:
        range_of_serial = range_of_serial.split("-")
    chunksize = ctx.obj['chunksize']
    tafilter = []
    tokentype = None
    realm = None
    token_owner = None
    resolver = None
    rollout_state = None
    if tokenattribute:
        allowed_tokenattributes = [col.key for col in Token.__table__.columns]
        tokenattributes = tokenattribute.split(',')
        attribute_map = {"tokentype": "tokentype",
                         "realm": "realm",
                         "resolver": "resolver",
                         "rollout_state": "rollout_state"}
        for tokenattribute in tokenattributes:
            m = re.match(r"\s*(\w+)\s*([!=<>])\s*(\w+)\s*$", tokenattribute)
            if m.group(1) not in allowed_tokenattributes:
                raise click.ClickException(f"Tokenattribute {m.group(1)} not allowed. "
                                           f"Allowed tokenattributes are: {allowed_tokenattributes}")
            elif m.group(2) == "=" and m.group(1) in attribute_map:
                locals()[attribute_map[m.group(1)]] = m.group(3)
            else:
                tafilter.append(build_tokenvalue_filter(m))

    tvfilter = []
    if tokeninfo:
        tokeninfos = tokeninfo.split(',')
        for tokeninfo in tokeninfos:
            m = re.match(r"\s*(\w+)\s*([!=<>])\s*(\w+)\s*$", tokeninfo)
            tvfilter.append(build_tokenvalue_filter(m))

    tofilter = []
    if tokenowner:
        allowed_tokenowner = [col.key for col in TokenOwner.__table__.columns]
        tokenowners = tokenowner.split(',') if tokenowner else None
        for owner in tokenowners:
            m = re.match(r"\s*(\w+)\s*([!=<>])\s*(\w+)\s*$", owner)
            if m.group(1) not in allowed_tokenowner:
                raise click.ClickException(f"Tokenowner {m.group(1)} not allowed. "
                                           f"Allowed tokenowner attributes are: {allowed_tokenowner}")
            else:
                tofilter.append(build_tokenvalue_filter(m))

    tcfilter = []
    if tokencontaner:
        tokencontainers = tokencontaner.split(',')
        allowed_containers = [col.key for col in TokenContainer.__table__.columns]
        for container in tokencontainers:
            m = re.match(r"\s*(\w+)\s*([!=<>])\s*(\w+)\s*$", container)
            if m.group(1) not in allowed_containers:
                raise click.ClickException(f"Tokencontaner {m.group(1)} not allowed. "
                                           f"Allowed container attributes are: {allowed_containers}")
            else:
                tcfilter.append(build_tokenvalue_filter(m))

    generator = _get_tokenlist(assigned=assigned, active=active, range_of_seriel=range_of_serial,
                               tokeninfo_filter=tvfilter, tokenattribute_filter=tafilter,
                               tokenowner_filter=tofilter, tokencontaner_filter=tcfilter,
                               orphaned=orphaned, tokentype=tokentype, realm=realm,
                               token_owner=token_owner, resolver=resolver, rollout_state=rollout_state,
                               chunksize=chunksize, has_not_tokeninfo_key=has_not_tokeninfo_key,
                               has_tokeninfo_key=has_tokeninfo_key)

    ctx.obj['tokens'] = generator
    sys.stderr.write(f"+ Reading tokens from database in chunks of {chunksize}...\n")


@findtokens.command('listuser')
@click.option('--sum', 'sum_tokens', is_flag=True,
              help='You can use this to reduce the output to show only the number of tokens owned by the user.')
@click.option('--attributes', help='Extends the "listuser" function to display additional user attributes')

@click.pass_context
def listuser(ctx, sum_tokens, attributes):
    """
    List all users and the number of tokens they own.
    """
    tlist = ctx.obj['tokens']
    if not sum_tokens:
        tokens = export_token_data(tlist, attributes)
        for token in tokens:
            print(",".join([f"'{x}'" for x in token]))
    else:
        users = export_user_data(tlist, attributes)
        for user, tokens in users.items():
            print(f"{user},{len(tokens)}")


@findtokens.command('listtoken')
@click.option('--csv', is_flag=True,
              help='The output is written as CSV instead of the formatted output.')
@click.pass_context
def listtoken(ctx, csv):
    """"
    List all found tokens.
    """
    tlist = ctx.obj['tokens']
    if not csv:
        print("Token serial\tTokeninfo")
        print("=" * 42)
        for token_obj in tlist:
            print(f"{token_obj.token.serial} ({token_obj.token.tokentype})\n\t\t{token_obj.token.description}"
                  f"\n\t\t{token_obj.get_tokeninfo()}")
    else:
        for token_obj in tlist:
            print(f"'{token_obj.token.serial}','{token_obj.token.tokentype}','{token_obj.token.description}',"
                  f"'{token_obj.get_tokeninfo()}'")


@findtokens.command('export')
@click.option('--format', type=click.Choice(['csv', 'yaml', 'xml'], case_sensitive=False),
              default='xml', help='Please specify the format of the output. Possible values are: csv, yaml, xml. '
                                  'Default is xml.')
@click.option('--b32', is_flag=True,
              help='In case of exporting found tokens to CSV the seed is written base32 encoded instead of hex.') #TODO: check if there is a better way
@click.pass_context
def export(ctx, format, b32):
    """
    Exports the found tokens.
    """
    tlist = ctx.obj['tokens']
    if format == "csv":
        for tokenobj in tlist:
            if tokenobj.type.lower() not in ["totp", "hotp"]:
                continue
            token_dict = tokenobj._to_dict(b32=b32)
            owner = f"{tokenobj.user.login}@{tokenobj.user.realm}" if tokenobj.user else "n/a"
            if type == "totp":
                print(f"{owner}, {token_dict.get("serial")}, {token_dict.get("otpkey")}, {token_dict.get("type")}, "
                      f"{token_dict.get("otplen")}, {token_dict.get("info_list", {}).get("timStep")}")
            else:
                print(f"{owner}, {token_dict.get("serial")}, {token_dict.get("otpkey")}, {token_dict.get("type")}, "
                      f"{token_dict.get("otplen")}")
    elif format == "yaml":
        token_list = []
        for tokenobj in tlist:
            try:
                token_dict = tokenobj._to_dict(b32=b32)
                token_dict["owner"] = f"{tokenobj.user.login}@{tokenobj.user.realm}" if tokenobj.user else "n/a"
                token_list.append(token_dict)
            except Exception as e:
                sys.stderr.write(f"\nFailed to export token {tokenobj.get("serial")}.\n")
        print(yaml_safe_dump(token_list))
    else:
        key, token_num, soup = export_pskc(tlist)
        sys.stderr.write(f"\n{token_num} tokens exported.\n")
        sys.stderr.write(f"\nThis is the AES encryption key of the token seeds.\n"
                         "You need this key to import the "
                         "tokens again:\n\n\t{key}\n\n")
        print(f"{soup}")


@findtokens.command('set_tokenrealms')
@click.argument('--tokenrealms')
@click.pass_context
def set_tokenrealms(ctx, tokenrealms):
    """
    Sets the realms of the found tokens.
    """
    for token_obj in ctx.obj['tokens']:
        trealms = [r.strip() for r in tokenrealms.split(",") if r]
        token_obj.set_realms(trealms)
        print(f"Setting realms of token {token_obj.token.serial} to {trealms}.")


@findtokens.command('disable')
@click.pass_context
def disable(ctx):
    """
    Disables the found tokens.
    """
    for token_obj in ctx.obj['tokens']:
        enable_token(serial=token_obj.token.serial, enable=False)
        print(f"Disabling token {token_obj.token.serial}")


@findtokens.command('delete')
@click.pass_context
def delete(ctx):
    """
    Deletes the found tokens.
    """
    for token_obj in ctx.obj['tokens']:
        remove_token(serial=token_obj.token.serial)
        print(f"Deleting token {token_obj.token.serial}")


@findtokens.command('unassign')
@click.pass_context
def unassign(ctx):
    """
    Unassigns the found tokens from their owners.
    """
    for token_obj in ctx.obj['tokens']:
        unassign_token(serial=token_obj.token.serial)
        print(f"Unassigning token {token_obj.token.serial}")


@findtokens.command('set_description')
@click.argument('--description')
@click.pass_context
def set_description(ctx, description):
    """
    Sets the description of the found tokens.
    """
    for token_obj in ctx.obj['tokens']:
        print(f"Setting description for token {token_obj.token.serial}: {description}")
        token_obj.set_description(description)
        token_obj.save()


@findtokens.command('set_tokeninfo')
@click.argument('--tokeninfo')
@click.pass_context
def set_tokeninfo(ctx, tokeninfo):
    """
    Sets the tokeninfo of the found tokens.
    """
    m = re.match(r"\s*(\w+)\s*([=])\s*(\w+)\s*$", tokeninfo)
    tokeninfo_key = m.group(1)
    tokeninfo_value = m.group(3)
    for token_obj in ctx.obj['tokens']:
        print(f"Setting tokeninfo for token {token_obj.token.serial}: {tokeninfo_key}={tokeninfo_value}")
        token_obj.add_tokeninfo(tokeninfo_key, tokeninfo_value)
        token_obj.save()


@findtokens.command('remove_tokeninfo')
@click.argument('--tokeninfo_key')
@click.pass_context
def remove_tokeninfo(ctx, tokeninfo_key):
    """
    Remove the tokeninfo of the found tokens.
    """
    for token_obj in ctx.obj['tokens']:
        print(f"Removing tokeninfo for token {token_obj.token.serial}: {tokeninfo_key}")
        token_obj.remove_tokeninfo(tokeninfo_key)
        token_obj.save()

