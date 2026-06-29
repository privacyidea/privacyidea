# (c) NetKnights GmbH 2026,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
``pi-manage conditionalaccess`` — inspect and clear the conditional-access
lockout state (locked users and blocked IPs).

This is the operational escape hatch for the lockout engine: it works without
the WebUI, so an administrator who has been locked out (or who blocked a shared
proxy IP) can recover from the command line.
"""
import click
from flask.cli import AppGroup

from privacyidea.lib.user import User
from privacyidea.models import db
from privacyidea.models.lockout_policy import BlockList, UserLockoutState

conditional_access_cli = AppGroup("conditionalaccess",
                                  help="Inspect and clear conditional-access locks and IP blocks")


def _format_expiry(expires_at):
    return expires_at.isoformat() if expires_at else "permanent"


@conditional_access_cli.command("list-blocks", help="List the currently blocked IPs.")
def list_blocks():
    rows = BlockList.query.filter_by(is_blocked=True).all()
    if not rows:
        click.echo("No blocked IPs.")
        return
    click.echo(f"{len(rows)} blocked IP(s):")
    for row in rows:
        click.echo(f"  {row.ip}\texpires={_format_expiry(row.block_expires_at)}\treason={row.reason or ''}")


@conditional_access_cli.command("unblock-ip", help="Remove the block for a single IP.")
@click.argument("ip")
def unblock_ip(ip):
    row = BlockList.query.filter_by(ip=ip).first()
    if not row:
        click.echo(f"No block found for IP {ip}.")
        return
    db.session.delete(row)
    db.session.commit()
    click.echo(f"Removed the block for IP {ip}.")


@conditional_access_cli.command("clear-blocks", help="Remove ALL IP blocks.")
@click.confirmation_option(prompt="Remove all IP blocks?")
def clear_blocks():
    count = BlockList.query.delete()
    db.session.commit()
    click.echo(f"Removed {count} IP block(s).")


@conditional_access_cli.command("list-locks", help="List the currently locked users.")
def list_locks():
    rows = UserLockoutState.query.filter_by(is_locked=True).all()
    if not rows:
        click.echo("No locked users.")
        return
    click.echo(f"{len(rows)} locked user(s):")
    for row in rows:
        click.echo(f"  resolver={row.resolver}\tuid={row.uid}\trealm={row.realm}\t"
                   f"expires={_format_expiry(row.lock_expires_at)}")


@conditional_access_cli.command("unlock-user", help="Remove the lock for a single user.")
@click.argument("login")
@click.option("--realm", required=True, help="The realm of the user.")
@click.option("--resolver", help="The resolver of the user (only needed to disambiguate).")
def unlock_user(login, realm, resolver):
    user = User(login=login, realm=realm, resolver=resolver or "")
    if user.is_empty() or not user.exist():
        click.echo(f"User {login}@{realm} could not be resolved. Use 'list-locks' and "
                   f"'unlock-by-id' if the user no longer exists in the resolver.")
        return
    row = UserLockoutState.query.filter_by(resolver=user.resolver, uid=user.uid, realm=user.realm).first()
    if not row:
        click.echo(f"No lock found for user {login}@{realm}.")
        return
    db.session.delete(row)
    db.session.commit()
    click.echo(f"Unlocked user {login}@{realm}.")


@conditional_access_cli.command("unlock-by-id",
                                help="Remove a user lock by its raw (resolver, uid, realm) — for users "
                                     "that no longer resolve.")
@click.option("--resolver", required=True)
@click.option("--uid", required=True)
@click.option("--realm", required=True)
def unlock_by_id(resolver, uid, realm):
    row = UserLockoutState.query.filter_by(resolver=resolver, uid=uid, realm=realm).first()
    if not row:
        click.echo(f"No lock found for (resolver={resolver}, uid={uid}, realm={realm}).")
        return
    db.session.delete(row)
    db.session.commit()
    click.echo(f"Unlocked (resolver={resolver}, uid={uid}, realm={realm}).")


@conditional_access_cli.command("clear-locks", help="Remove ALL user locks.")
@click.confirmation_option(prompt="Remove all user locks?")
def clear_locks():
    count = UserLockoutState.query.delete()
    db.session.commit()
    click.echo(f"Removed {count} user lock(s).")
