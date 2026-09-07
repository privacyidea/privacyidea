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
lock state (locked users and blocked IPs), and switch off the policies that
produce it.

This is the operational escape hatch for the conditional-access engine: it works without
the WebUI, so an administrator who has been locked out (or who blocked a shared
proxy IP) can recover from the command line. Lifting a lock only undoes what a
policy has already done - a policy that keeps refusing requests (a ``DENY`` at
threshold 0, say) has to be disabled, put into dry run or deleted, which is what
the ``*-policy`` and ``*-dry-run`` commands are for.
"""
import click
from flask.cli import AppGroup
from sqlalchemy import select

from privacyidea.lib.conditional_access.policy import (delete_conditional_access_policy,
                                                       enable_conditional_access_policy,
                                                       list_conditional_access_policies,
                                                       update_conditional_access_policy)
from privacyidea.lib.conditional_access.state import (block_ip, list_blocklist,
                                                              list_locked_users, lock_user,
                                                              purge_expired_blocklist,
                                                              purge_expired_user_locks,
                                                              remove_blocklist_entry,
                                                              unlock_user_by_id, unlock_user_by_username)
from privacyidea.lib.user import User
from privacyidea.models import db
from privacyidea.models.conditional_access_policy import (BlockList, ConditionalAccessPolicy,
                                                          UserLockState)

conditional_access_cli = AppGroup("conditionalaccess",
                                  help="Manage conditional-access policies and clear the locks and IP "
                                       "blocks they produced")


def _format_expiry(expires_at):
    return expires_at.isoformat() if expires_at else "permanent"


def _yes_no(value) -> str:
    return "yes" if value else "no"


def _resolve_policy(identifier: str) -> ConditionalAccessPolicy:
    """
    Look a policy up by name, falling back to its id.

    The name is what an administrator reads off ``list-policies`` and is unique, so it
    wins; the numeric id is tried only when no policy carries that name, which keeps a
    policy whose name happens to be a number reachable by both.
    """
    policy = db.session.scalar(select(ConditionalAccessPolicy).where(ConditionalAccessPolicy.name == identifier))
    if not policy and identifier.isdigit():
        policy = db.session.get(ConditionalAccessPolicy, int(identifier))
    if not policy:
        raise click.ClickException(f"No conditional-access policy with the name or id '{identifier}'. "
                                   f"Run 'pi-manage conditionalaccess list-policies' to see them.")
    return policy


def _policy_label(policy: ConditionalAccessPolicy) -> str:
    return f"'{policy.name}' (id {policy.id})"


@conditional_access_cli.command("list-policies", help="List the conditional-access policies in evaluation order.")
def list_policies():
    # The same table shape as "pi-manage config policy list", listing what identifies a policy and what
    # the commands below change. The stages, conditions and everything else belong to the policy detail
    # view in the WebUI or the API, not to a one-line-per-policy overview.
    policies = list_conditional_access_policies()
    if not policies:
        click.echo("No conditional-access policies.")
        return
    click.echo(f"{'Name':30} {'ID':5} {'Enabled':8} {'Dry run':8} {'Priority':9} Target")
    click.echo(71 * "=")
    for policy in policies:
        # The id is listed next to the name because every command below takes either, and the id is the
        # shorter thing to type when the name is long or carries spaces.
        click.echo(f"{policy['name']:30} {policy['id']:<5} {_yes_no(policy['enabled']):8} "
                   f"{_yes_no(policy['dry_run']):8} {policy['priority']:<9} {policy['target']}")


@conditional_access_cli.command("enable-policy", help="Enable a single policy, given by its name or id.")
@click.argument("policy")
def enable_policy(policy):
    row = _resolve_policy(policy)
    label = _policy_label(row)
    if row.enabled:
        click.echo(f"Conditional-access policy {label} is already enabled.")
        return
    enable_conditional_access_policy(row.id, enable=True)
    click.echo(f"Enabled conditional-access policy {label}.")


@conditional_access_cli.command("disable-policy",
                                help="Disable a single policy, given by its name or id. The policy stops being "
                                     "evaluated; locks and blocks it already wrote stay in force.")
@click.argument("policy")
def disable_policy(policy):
    # The way back in from an over-strict policy: it is no longer evaluated, so it cannot refuse
    # the next request. What it already wrote is separate state - clear that with clear-locks/clear-blocks.
    row = _resolve_policy(policy)
    label = _policy_label(row)
    if not row.enabled:
        click.echo(f"Conditional-access policy {label} is already disabled.")
        return
    enable_conditional_access_policy(row.id, enable=False)
    click.echo(f"Disabled conditional-access policy {label}. Locks and blocks it already wrote stay in "
               f"force; clear them with clear-locks / clear-blocks.")


@conditional_access_cli.command("enable-dry-run",
                                help="Put a policy into dry run: it is still evaluated and logged, but nothing "
                                     "is enforced.")
@click.argument("policy")
def enable_dry_run(policy):
    row = _resolve_policy(policy)
    label = _policy_label(row)
    if row.dry_run:
        click.echo(f"Conditional-access policy {label} is already in dry run.")
        return
    update_conditional_access_policy(row.id, dry_run=True)
    click.echo(f"Conditional-access policy {label} is now in dry run: nothing it decides is enforced.")


@conditional_access_cli.command("disable-dry-run",
                                help="Take a policy out of dry run, so its actions are enforced again.")
@click.argument("policy")
def disable_dry_run(policy):
    row = _resolve_policy(policy)
    label = _policy_label(row)
    if not row.dry_run:
        click.echo(f"Conditional-access policy {label} is not in dry run.")
        return
    update_conditional_access_policy(row.id, dry_run=False)
    click.echo(f"Conditional-access policy {label} is no longer in dry run: its actions are enforced again.")


@conditional_access_cli.command("delete-policy",
                                help="Delete a single policy, given by its name or id, with all its stages and "
                                     "actions.")
@click.argument("policy")
@click.option("--yes", is_flag=True, help="Do not ask for confirmation.")
def delete_policy(policy, yes):
    row = _resolve_policy(policy)
    label = _policy_label(row)
    # The configuration is gone for good, so confirm by default; --yes is there for scripts.
    if not yes:
        click.confirm(f"Delete conditional-access policy {label}?", abort=True)
    delete_conditional_access_policy(row.id)
    click.echo(f"Deleted conditional-access policy {label}.")


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
        click.echo(f"  {entry['identifier']}\texpires={_format_expiry(entry['block_expires_at'])}\t"
                   f"cause={entry['block_cause']}")


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
                   f"expires={_format_expiry(user['lock_expires_at'])}\tcause={user['lock_cause']}")


@conditional_access_cli.command("lock-user", help="Lock a single user by hand.")
@click.argument("login")
@click.option("--realm", required=True, help="The realm of the user.")
@click.option("--resolver", help="The resolver of the user (only needed to disambiguate).")
@click.option("--duration", type=int, help="How long the lock lasts, in seconds. Omitted, it is permanent.")
def lock_user_cmd(login, realm, resolver, duration):
    # The escape hatch for the WebUI's Lock action: the same authoritative write, recorded as a manual lock
    # and enforced by the same pre-check as a policy lock.
    user = User(login=login, realm=realm, resolver=resolver or "")
    lock = lock_user(user, duration_seconds=duration)
    click.echo(f"Locked user {login}@{realm} (expires={_format_expiry(lock['lock_expires_at'])}).")


@conditional_access_cli.command("block-ip", help="Block a single IP by hand.")
@click.argument("ip")
@click.option("--duration", type=int, help="How long the block lasts, in seconds. Omitted, it is permanent.")
def block_ip_cmd(ip, duration):
    entry = block_ip(ip, duration_seconds=duration)
    click.echo(f"Blocked IP {ip} (expires={_format_expiry(entry['block_expires_at'])}).")


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
