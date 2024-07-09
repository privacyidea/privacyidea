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
from privacyidea.lib.auth import (create_db_admin, list_db_admin,
                                  delete_db_admin)

admin_cli = AppGroup("admin", help="Manage local administrators")


@admin_cli.command("add")
@click.argument('username')
@click.option("-e", "--email", "email")
@click.password_option()
def add_admin(username, email, password):
    """
    Register a new administrator in the database.
    """
    create_db_admin(username, email, password)
    click.echo('Admin {0} was registered successfully.'.format(username))


@admin_cli.command("list")
def list_admin():
    """
    List all administrators.
    """
    admins = list_db_admin()
    click.echo("Name \t email")
    click.echo(30 * "=")
    for admin in admins:
        click.echo(f"{admin.username} \t {admin.email}")


@admin_cli.command("delete")
@click.argument("username")
def delete_admin(username):
    """
    Delete an existing administrator.
    """
    delete_db_admin(username)


@admin_cli.command("change")
@click.argument('username')
@click.option("-e", "--email", "email")
@click.password_option()
def change_admin(username, email, password):
    """
    Change the email address or the password of an existing administrator USERNAME.
    """
    create_db_admin(username, email, password)
