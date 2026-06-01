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
Find and clean up orphaned rows in the ``internaluserattribute`` table.

privacyIDEA does not own the user store, so when a user is deleted upstream
the rows keyed on ``(user_id, resolver, realm_id)`` for that user become
unreachable. This command surfaces them, and optionally deletes them.
"""
import click
from flask.cli import AppGroup

from privacyidea.lib.user import (
    delete_orphaned_internal_attributes,
    find_orphaned_internal_attributes,
)


@click.group('internal-attributes', invoke_without_command=True, cls=AppGroup)
@click.option('--orphaned-on-error', is_flag=True, default=False,
              help="Treat a row as orphaned if the resolver raises while "
                   "looking up the user (e.g. resolver unreachable).")
@click.pass_context
def findinternalattributes(ctx, orphaned_on_error):
    """
    Find orphaned rows in the internal user-attribute table.

    A row is orphaned when its user can no longer be resolved — typically
    because the user was deleted from the user store. Without a subcommand
    the orphans are listed; pass ``delete`` to remove them.
    """
    ctx.ensure_object(dict)
    ctx.obj['orphans'] = find_orphaned_internal_attributes(orphaned_on_error=orphaned_on_error)
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_cmd)


@findinternalattributes.command('list')
@click.pass_context
def list_cmd(ctx):
    """List the orphaned (user_id, resolver, realm_id) tuples."""
    orphans = ctx.obj['orphans']
    if not orphans:
        click.echo("No orphaned internal user attributes found.")
        return
    click.echo(f"Found {len(orphans)} orphaned user(s) in internaluserattribute:")
    for user_id, resolver, realm_id in orphans:
        click.echo(f"  user_id={user_id!r}  resolver={resolver!r}  realm_id={realm_id!r}")


@findinternalattributes.command('delete')
@click.option('--yes', is_flag=True, default=False,
              help="Skip the interactive confirmation.")
@click.pass_context
def delete_cmd(ctx, yes):
    """Delete every internaluserattribute row that belongs to an orphaned user."""
    orphans = ctx.obj['orphans']
    if not orphans:
        click.echo("No orphaned internal user attributes found.")
        return
    if not yes:
        click.confirm(f"Delete all internal attributes for {len(orphans)} orphaned user(s)?",
                      abort=True)
    deleted = delete_orphaned_internal_attributes(orphans)
    click.echo(f"Deleted {deleted} internaluserattribute row(s).")
