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
lock state (locked users and blocked IPs).

This is the operational escape hatch for the conditional-access engine: it works without
the WebUI, so an administrator who has been locked out (or who blocked a shared
proxy IP) can recover from the command line.
"""
import click
from flask.cli import AppGroup

from privacyidea.lib.conditional_access.state import (list_blocklist,
                                                              list_locked_users,
                                                              purge_expired_blocklist,
                                                              purge_expired_user_locks,
                                                              remove_blocklist_entry,
                                                              unlock_user_by_id, unlock_user_by_username)
from privacyidea.models import db
from privacyidea.models.conditional_access_policy import BlockList, UserLockState

conditional_access_cli = AppGroup("conditionalaccess",
                                  help="Inspect and clear conditional-access locks and IP blocks")


def _format_expiry(expires_at):
    return expires_at.isoformat() if expires_at else "permanent"


@conditional_access_cli.command("list-blocked-ips", help="List the currently blocked IPs.")
def list_blocked_ips():
    # "currently blocked" = permanent + still-running timed blocks; stale expired rows are excluded here
    # (clear them with purge-expired-blocks), mirroring list-locked-users.
    entries = list_blocklist(include_expired=False)
    if not entries:
        click.echo("No blocked IPs.")
        return
    click.echo(f"{len(entries)} blocked IP(s):")
    for entry in entries:
        click.echo(f"  {entry['identifier']}\texpires={_format_expiry(entry['block_expires_at'])}")


@conditional_access_cli.command("unblock-ip", help="Remove the block for a single IP.")
@click.argument("ip")
def unblock_ip(ip):
    if remove_blocklist_entry(ip):
        click.echo(f"Removed the block for IP {ip}.")
    else:
        click.echo(f"No block found for IP {ip}.")


@conditional_access_cli.command("clear-blocks", help="Remove ALL IP blocks.")
@click.confirmation_option(prompt="Remove all IP blocks?")
def clear_blocks():
    count = BlockList.query.delete()
    db.session.commit()
    click.echo(f"Removed {count} IP block(s).")


@conditional_access_cli.command("purge-expired-blocks",
                                help="Remove only stale IP blocks (expired or lifted); keep the ones "
                                     "still in force.")
def purge_expired_blocks():
    count = purge_expired_blocklist()
    click.echo(f"Removed {count} stale IP block(s).")


@conditional_access_cli.command("list-locked-users", help="List the currently locked users.")
def list_locked_users_cmd():
    # "currently locked" = permanent + temporary; expired stale records are excluded here (clear them with
    # purge-expired-locks).
    users = list_locked_users(states=["permanent", "temporary"])
    if not users:
        click.echo("No locked users.")
        return
    click.echo(f"{len(users)} locked user(s):")
    for user in users:
        click.echo(f"  resolver={user['resolver']}\tuid={user['uid']}\trealm={user['realm']}\t"
                   f"expires={_format_expiry(user['lock_expires_at'])}")


@conditional_access_cli.command("unlock-user", help="Remove the lock for a single user.")
@click.argument("login")
@click.option("--realm", required=True, help="The realm of the user.")
@click.option("--resolver", help="The resolver of the user (only needed to disambiguate).")
def unlock_user_cmd(login, realm, resolver):
    target = f"{login}@{realm}" + (f" (resolver={resolver})" if resolver else "")
    if unlock_user_by_username(login, realm, resolver):
        click.echo(f"Unlocked user {target}.")
    else:
        click.echo(f"No lock found for user {target}.")


@conditional_access_cli.command("unlock-by-id",
                                help="Remove a user lock by its (uid, realm). Pass --resolver to disambiguate a shared "
                                     "uid.")
@click.option("--uid", required=True)
@click.option("--realm", required=True)
@click.option("--resolver", help="The resolver of the user.")
def unlock_by_id(uid, realm, resolver):
    target = f"uid={uid}, realm={realm}" + (f", resolver={resolver}" if resolver else "")
    if unlock_user_by_id(uid, realm, resolver):
        click.echo(f"Unlocked ({target}).")
    else:
        click.echo(f"No lock found for ({target}).")


@conditional_access_cli.command("clear-locks",
                                help="Remove ALL user locks, or only those of a given realm.")
@click.option("--realm", help="Only clear locks of users in this realm.")
@click.confirmation_option(prompt="Remove the matching user locks?")
def clear_locks(realm):
    query = UserLockState.query
    if realm:
        query = query.filter_by(realm=realm)
    count = query.delete()
    db.session.commit()
    scope = f" in realm '{realm}'" if realm else ""
    click.echo(f"Removed {count} user lock(s){scope}.")


@conditional_access_cli.command("purge-expired-locks",
                                help="Remove only stale user locks (expired or unlocked); keep the ones "
                                     "still in force.")
def purge_expired_locks():
    count = purge_expired_user_locks()
    click.echo(f"Removed {count} stale user lock(s).")
