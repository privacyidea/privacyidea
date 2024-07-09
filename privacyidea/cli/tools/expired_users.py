# SPDX-FileCopyrightText: (C) 2024 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-FileCopyrightText: (C) 2016 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
This script reads the users from the userstore and checks for the attribute
"accountExpires".

To add this attribute to the user details you need to add it to the attribute
mapping. For Microsoft Active Directory add

    "accountExpires": "accountExpires"

to the attribute mapping.

The script then checks if the account actually is expired. If the account is
expired, it deletes tokens of the account with the serial number matching
DELETE_SERIAL and unassigns tokens with the serial number matching
UNASSIGN_SERIAL.

You can call the script like this:

    privacyidea-expired-users expire --realm ad -d '^T.*'

This would check for all expired users in the realm "AD" and then unassign
all tokens and delete all the user's tokens, that start with a 'T',
which is indicated by the '-d' switch.

This script runs against the library level of privacyIDEA. I.e. the
webserver/API needs not to run. But the scripts needs to have access to
pi.cfg and the encryption keys.

accountExpires in Active Directory
https://msdn.microsoft.com/en-us/library/windows/desktop/ms675098(v=vs.85).aspx

    "The date when the account expires. This value represents the number of
     100-nanosecond intervals since January 1, 1601 (UTC). A value of 0 or
     0x7FFFFFFFFFFFFFFF (9223372036854775807) indicates that the account
     never expires."

Use the '-n' (noaction) switch, to verify if the script would do what you
expect.
"""
import click
import datetime
import re
from flask.cli import with_appcontext, ScriptInfo

from privacyidea.cli import create_silent_app
from privacyidea.lib.user import get_user_list, User
from privacyidea.lib.token import get_tokens, remove_token, unassign_token
from privacyidea.lib.utils import get_version_number

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-r", "--realm", default=None,
              help="The realm which should be checked")
@click.option("-a", "--attribute_name", default="accountExpires", show_default=True,
              help="The attribute name, that contains the expiration date.")
@click.option("-d", "--delete_serial", default=None,
              help="Regular expression to match serials which should be deleted "
                   "from an expired user")
@click.option("-u", "--unassign_serial", default=r".*", show_default=True,
              help="Regular expression to match serials which should be unassigned "
                   "from an expired user")
@click.option("-n", "--noaction", is_flag=True, default=False,
              help="If set, the script will only show, which accounts have "
                   "expired, but will do nothing.")
@with_appcontext
def expire(realm, attribute_name, delete_serial, unassign_serial, noaction):
    """
    Search for expired Users in the specified realm.
    """
    utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
    params = {attribute_name: "1"}
    if realm:
        params["realm"] = realm
    try:
        users = get_user_list(params)
    except KeyError as e:
        click.secho(f"Failed to get users: {e!r}", fg="red")
        click.secho(f"Does the attribute '{attribute_name}' exist in the "
                    f"attribute mapping of the resolver?", fg="yellow")
        users = []

    for user in users:
        username = user.get("username")
        account_expires = user.get(attribute_name)
        if account_expires:
            if account_expires.year == 9999:
                # We get a datetime object from ldap which equals
                # "9999-12-31 23:59:59.999999+00:00" when the account doesn't expire.
                # Our own LDAP Resolver does return only expired accounts.
                click.echo(f"Account '{username}' does not expire")
                continue
            click.echo(f"= User {username} has an expiration date.")
            click.echo(f"== UTC now : {utc_now}")
            click.echo(f"== expires : {account_expires}")
            if account_expires <= utc_now:
                click.echo(f"=== Account {username} has expired.")
                tokens = get_tokens(user=User(login=username, resolver=user['resolver']))
                if not tokens:
                    click.echo("=== The account has no tokens assigned.")
                for token in tokens:
                    if unassign_serial:
                        m = re.search(unassign_serial, token.token.serial)
                        if m:
                            if noaction:
                                click.echo(f"=== I WOULD unassign token {token.token.serial}")
                            else:
                                click.echo(f"=== Unassigning token {token.token.serial}")
                                unassign_token(token.token.serial)
                    if delete_serial:
                        m = re.search(delete_serial, token.token.serial)
                        if m:
                            if noaction:
                                click.echo(f"=== I WOULD delete token {token.token.serial}")
                            else:
                                click.echo(f"=== Deleting token {token.token.serial}")
                                remove_token(token.token.serial)


def expire_call():
    """Call the actual function with an initialized app"""
    click.echo(r"""
             _                    _______  _______
   ___  ____(_)  _____ _______ __/  _/ _ \/ __/ _ |
  / _ \/ __/ / |/ / _ `/ __/ // // // // / _// __ |
 / .__/_/ /_/|___/\_,_/\__/\_, /___/____/___/_/ |_|  Expired Users
/_/                       /___/
{0!s:>51}
    """.format('v{0!s}'.format(get_version_number())))
    # Add the ScriptInfo object to create the Flask-App when necessary
    s = ScriptInfo(create_app=create_silent_app)
    expire(obj=s)


if __name__ == '__main__':
    expire_call()
