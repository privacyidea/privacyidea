# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
pi-tokenjanitor subcommand: ``deprecated``.

Lists and deletes tokens whose original type has been removed from
privacyIDEA and which have been migrated to ``tokentype='deprecated'``
by an alembic data migration. See ``dev/token-deprecation-strategy.md``.

Usage::

    pi-tokenjanitor deprecated list                 # list all deprecated tokens
    pi-tokenjanitor deprecated list u2f             # list only tokens originally of type u2f
    pi-tokenjanitor deprecated delete u2f           # delete only u2f-origin deprecated tokens
    pi-tokenjanitor deprecated delete all           # delete every deprecated token
    pi-tokenjanitor deprecated delete all --yes     # skip confirmation prompt
"""
from collections import defaultdict
from collections.abc import Iterable

import click
from flask.cli import AppGroup

from privacyidea.lib.token import get_tokens_paginated_generator, remove_token
from privacyidea.lib.tokenclass import TokenClass

# Page size for the paginated token fetch. Keeps memory bounded on
# installs with thousands of deprecated rows.
_CHUNKSIZE = 1000


def _iter_deprecated_tokens(original_type: str) -> Iterable[TokenClass]:
    """
    Yield every deprecated token. If ``original_type`` is ``"all"`` the
    filter is disabled; otherwise only tokens whose
    ``tokeninfo['original_tokentype']`` matches are yielded.
    """
    want = None if original_type == "all" else original_type
    for batch in get_tokens_paginated_generator(tokentype="deprecated", psize=_CHUNKSIZE):
        for token in batch:
            if want is None or token.get_tokeninfo("original_tokentype") == want:
                yield token


def _summarise(tokens: list[TokenClass]) -> dict[str, list[TokenClass]]:
    """Group tokens by ``tokeninfo['original_tokentype']`` (fallback ``'unknown'``)."""
    groups: dict[str, list[TokenClass]] = defaultdict(list)
    for token in tokens:
        origin = token.get_tokeninfo("original_tokentype") or "unknown"
        groups[origin].append(token)
    return groups


@click.group("deprecated", cls=AppGroup)
def deprecated():
    """
    List or delete tokens whose original type has been removed.

    Tokens are marked deprecated by a schema migration at upgrade time.
    They remain visible in the token list but cannot authenticate. Use
    this command to inspect or bulk-delete them.
    """


@deprecated.command("list")
@click.argument("original_type", required=False, default="all")
def list_deprecated(original_type: str):
    """
    List deprecated tokens, grouped by original type.

    ORIGINAL_TYPE defaults to "all". Pass a specific original type (e.g.
    "u2f") to restrict the listing.
    """
    tokens = list(_iter_deprecated_tokens(original_type))
    if not tokens:
        if original_type == "all":
            click.echo("No deprecated tokens found.")
        else:
            click.echo(f"No deprecated tokens with original_tokentype={original_type!r} found.")
        return

    groups = _summarise(tokens)
    click.echo(f"Found {len(tokens)} deprecated token(s):")
    for origin in sorted(groups):
        bucket = groups[origin]
        deprecated_in = bucket[0].get_tokeninfo("deprecated_in") or "?"
        click.echo(f"  {origin} (removed in {deprecated_in}): {len(bucket)} token(s)")
        for token in bucket:
            click.echo(f"    {token.token.serial}")


@deprecated.command("delete")
@click.argument("original_type")
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt.")
def delete_deprecated(original_type: str, yes: bool):
    """
    Delete deprecated tokens.

    ORIGINAL_TYPE must be either a specific original type (e.g. "u2f") or
    the literal "all" to delete every deprecated token regardless of
    origin.
    """
    tokens = list(_iter_deprecated_tokens(original_type))
    if not tokens:
        if original_type == "all":
            click.echo("No deprecated tokens to delete.")
        else:
            click.echo(f"No deprecated tokens with original_tokentype={original_type!r} to delete.")
        return

    groups = _summarise(tokens)
    click.echo(f"About to delete {len(tokens)} deprecated token(s):")
    for origin in sorted(groups):
        click.echo(f"  {origin}: {len(groups[origin])} token(s)")

    if not yes:
        click.confirm("Continue?", abort=True)

    deleted = 0
    failed = 0
    for token in tokens:
        serial = token.token.serial
        origin = token.get_tokeninfo("original_tokentype") or "unknown"
        try:
            remove_token(serial=serial)
            deleted += 1
            click.echo(f"Deleted {serial} (was: {origin})")
        except Exception as exc:  # noqa: BLE001 — report-and-continue is intentional
            failed += 1
            click.echo(f"FAILED to delete {serial} (was: {origin}): {exc}", err=True)

    summary = f"Deleted {deleted} token(s)."
    if failed:
        summary += f" {failed} failed — see messages above."
    click.echo(summary)
