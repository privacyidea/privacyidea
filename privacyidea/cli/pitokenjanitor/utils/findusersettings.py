# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2026 Nils Behlen <nils.behlen@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
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
Find and clean up orphaned rows in the ``usersetting`` table.

A user removed from the user store, or a local admin deleted from the DB,
leaves behind a ``usersetting`` row that the normal API can no longer reach.
(Realm deletion is already handled by the realm foreign key.) This command
surfaces those rows, and optionally deletes them.
"""
import click
from flask.cli import AppGroup

from privacyidea.lib.usersetting import (
    delete_orphaned_user_settings,
    find_orphaned_user_settings,
)


@click.group('user-settings', invoke_without_command=True, cls=AppGroup)
@click.option('--orphaned-on-error', is_flag=True, default=False,
              help="Treat a row as orphaned if the resolver raises while "
                   "looking up the user (e.g. resolver unreachable).")
@click.pass_context
def findusersettings(ctx, orphaned_on_error):
    """
    Find orphaned rows in the user-settings table.

    A row is orphaned when its principal no longer exists — a resolver user
    deleted from the store, or a local admin removed from the database.
    Without a subcommand the orphans are listed; pass ``delete`` to remove them.
    """
    ctx.ensure_object(dict)
    ctx.obj['orphans'] = find_orphaned_user_settings(orphaned_on_error=orphaned_on_error)
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_cmd)


@findusersettings.command('list')
@click.pass_context
def list_cmd(ctx):
    """List the orphaned user-settings rows."""
    orphans = ctx.obj['orphans']
    if not orphans:
        click.echo("No orphaned user settings found.")
        return
    click.echo(f"Found {len(orphans)} orphaned row(s) in usersetting:")
    for row in orphans:
        if row.subject_type == "local_admin":
            click.echo(f"  local_admin  username={row.username!r}")
        else:
            click.echo(f"  user  user_id={row.user_id!r}  resolver={row.resolver!r}  "
                       f"realm_id={row.realm_id!r}")


@findusersettings.command('delete')
@click.option('--yes', is_flag=True, default=False,
              help="Skip the interactive confirmation.")
@click.pass_context
def delete_cmd(ctx, yes):
    """Delete every usersetting row that belongs to an orphaned principal."""
    orphans = ctx.obj['orphans']
    if not orphans:
        click.echo("No orphaned user settings found.")
        return
    if not yes:
        click.confirm(f"Delete user settings for {len(orphans)} orphaned principal(s)?",
                      abort=True)
    deleted = delete_orphaned_user_settings(orphans)
    click.echo(f"Deleted {deleted} usersetting row(s).")
