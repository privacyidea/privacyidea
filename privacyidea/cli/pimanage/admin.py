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

from flask.cli import AppGroup
import click
from privacyidea.lib.auth import (create_db_admin, get_all_db_admins,
                                  delete_db_admin)
from privacyidea.lib.error import ResourceNotFoundError

admin_cli = AppGroup("admin", help="Manage local administrators")


@admin_cli.command("add")
@click.argument('username')
@click.option("-e", "--email", "email")
@click.password_option('-p', '--password')
@click.pass_context
def add_admin(ctx, username, email, password):
    """
    Register a new administrator in the database.
    """
    if not password:
        click.secho("Error: The password of an administrator must not be empty.", fg="red", err=True)
        ctx.exit(1)
    create_db_admin(username, email, password)
    click.echo(f'Admin {username} was registered successfully.')


@admin_cli.command("list")
def list_admin():
    """
    List all administrators.
    """
    admins = get_all_db_admins()
    click.echo("Name \t email")
    click.echo(30 * "=")
    for admin in admins:
        click.echo(f"{admin.username} \t {admin.email}")


@admin_cli.command("delete")
@click.argument("username")
@click.pass_context
def delete_admin(ctx, username):
    """
    Delete an existing administrator.
    """
    try:
        delete_db_admin(username)
    except ResourceNotFoundError:
        click.secho(f"Error: The administrator {username} does not exist.", fg="red", err=True)
        ctx.exit(1)


@admin_cli.command("change")
@click.argument('username')
@click.option("-e", "--email", "email")
@click.password_option()
def change_admin(username, email, password):
    """
    Change the email address or the password of an existing administrator USERNAME.
    """
    create_db_admin(username, email, password)
