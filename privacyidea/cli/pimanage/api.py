# SPDX-FileCopyrightText: (C) 2023 Paul Lettich <paul.lettich@netknights.it>
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

import datetime
import click
from flask import current_app
from flask.cli import AppGroup
import jwt

from privacyidea.lib.auth import ROLE
from privacyidea.lib.crypto import geturandom


api_cli = AppGroup("api", help="Manage API keys")


@api_cli.command("createtoken")
@click.option('-r', '--role',
              help="The role of the API key can either be "
                   "'admin' or 'validate' to access the admin "
                   "API or the validate API.",
              type=click.Choice([ROLE.ADMIN, ROLE.VALIDATE]),
              default=ROLE.ADMIN, show_default=True)
@click.option('-d', '--days',
              help='The number of days the access token should be valid.',
              default=365, show_default=True, type=int)
@click.option('-R', '--realm',
              help='The realm of the admin.',
              default="API", type=str, show_default=True)
@click.option('-u', '--username', type=str, required=True,
              help='The username of the admin.')
@click.pass_context
def api_createtoken(ctx, role, days, realm, username):
    """
    Create an API authentication token
    for administrative or validate use.
    Possible roles are "admin" or "validate".
    """
    if role not in ["admin", "validate"]:
        click.secho("ERROR: The role must be 'admin' or 'validate'!", fg="red")
        ctx.exit(1)
    username = username or geturandom(hex=True)
    secret = current_app.config.get("SECRET_KEY")
    authtype = "API"
    validity = datetime.timedelta(days=int(days))
    token = jwt.encode({
        "username": username,
        "realm": realm,
        "nonce": geturandom(hex=True),
        "role": role,
        "authtype": authtype,
        "exp": datetime.datetime.utcnow() + validity,
        "rights": "TODO"},
        secret)
    click.echo(f"Username:   {username}")
    click.echo(f"Realm:      {realm}")
    click.echo(f"Role:       {role}")
    click.echo(f"Validity:   {days} days")
    click.echo(f"Auth-Token: {token}")
