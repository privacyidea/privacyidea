# SPDX-FileCopyrightText: (C) 2024 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-FileCopyrightText: (C) 2017 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
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
"""
This script searches tokens that have not been used for a while.
To do so, it checks for the tokeninfo field "last_auth".
If the last authentication is to old, the script can delete, disable or mark
these tokens.

You can call the script like this:

    privacyidea-get-unused-tokens list 10h|7d|2y
    privacyidea-get-unused-tokens disable 10h|7d|2y
    privacyidea-get-unused-tokens delete 10h|7d|2y
    privacyidea-get-unused-tokens mark 10h|7d|2y --description="new
    value"

"""
import click
from flask.cli import with_appcontext
from privacyidea.lib.utils import get_version_number
from privacyidea.lib.token import get_tokens, remove_token, enable_token
from privacyidea.lib.policy import ACTION
from privacyidea.cli import NoPluginsFlaskGroup, create_silent_app

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(cls=NoPluginsFlaskGroup, create_app=create_silent_app,
             context_settings=CONTEXT_SETTINGS, add_default_commands=False,
             epilog='Check out our docs at https://privacyidea.readthedocs.io/ for more details')
def cli():
    """
\b
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \\/ __/ _ |
  / _ \\/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\\_,_/\\__/\\_, /___/____/___/_/ |_|  Get unused tokens
/_/                       /___/

   Search for tokens that have not been used for a while"""
    click.echo(r"""
                 _                    _______  _______
       ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
      / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
     / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|  Get unused tokens
    /_/                       /___/
    {0!s:>51}
        """.format('v{0!s}'.format(get_version_number())))


def _get_tokenlist(age):
    tlist = []
    tokenobj_list = get_tokens()
    try:
        for token_obj in tokenobj_list:
            if not token_obj.check_last_auth_newer(age):
                tlist.append(token_obj)
    except TypeError as e:
        click.secho(str(e), fg="red")

    return tlist


@click.command()
@click.argument('age')
@with_appcontext
def list_tokens(age):
    """
    Find all tokens where the last_auth is greater than AGE.

    AGE can be a value like 10h, 7d or 2y.
    """
    # TODO: bad performance, we have to look at *ALL* tokens!
    #       We can use get_tokens_paginate() here
    tlist = _get_tokenlist(age)
    if tlist:
        click.echo("Token serial\tLast authentication")
        click.echo("=" * 50)
        for token_obj in tlist:
            click.echo(f"{token_obj.token.serial}\t{token_obj.get_tokeninfo(ACTION.LASTAUTH)}")


@click.command()
@click.argument('age')
@click.option('-d', '--description', help='The description that will be set.')
@click.option('-t', '--tokeninfo',
              help='The tokeninfo that will be set. It needs a key and a '
                   'value and should be specified like key=value.')
@with_appcontext
def mark(age, description=None, tokeninfo=None):
    """
    Find unused tokens and mark them.
    They can be marked either by setting a description or by
    setting a tokeninfo.

    AGE can be a value like 10h, 7d or 2y.
    """
    tlist = _get_tokenlist(age)
    for token_obj in tlist:
        if description:
            click.echo("Setting description for token {0!s}: {1!s}".format(
                token_obj.token.serial, description))
            token_obj.set_description(description)
            token_obj.save()
        if tokeninfo:
            key, value = tokeninfo.split("=")
            click.echo("Setting tokeninfo for token {0!s}: {1!s}={2!s}".format(
                token_obj.token.serial, key, value))
            token_obj.add_tokeninfo(key, value)
            token_obj.save()


@click.command()
@click.argument('age')
@with_appcontext
def delete(age):
    """
    Find unused tokens and delete them.

    AGE can be a value like 10h, 7d or 2y.
    """
    tlist = _get_tokenlist(age)
    for token_obj in tlist:
        serial = token_obj.token.serial
        remove_token(serial)
        click.echo("Token {0!s} deleted.".format(serial))


@click.command()
@click.argument('age')
@with_appcontext
def disable(age):
    """
    Find unused tokens and disable them.

    AGE can be a value like 10h, 7d or 2y.
    """
    tlist = _get_tokenlist(age)
    for token_obj in tlist:
        serial = token_obj.token.serial
        enable_token(serial, enable=False)
        click.echo("Token {0!s} disabled.".format(serial))


cli.add_command(list_tokens, "list")
cli.add_command(disable)
cli.add_command(delete)
cli.add_command(mark)

if __name__ == '__main__':
    cli()
