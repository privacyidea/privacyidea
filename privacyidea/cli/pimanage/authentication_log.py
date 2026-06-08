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

from datetime import timedelta

import click
from flask.cli import AppGroup

from privacyidea.lib.conditional_access.authentication_log import cleanup_authentication_log
from privacyidea.models import AuthenticationLog
from privacyidea.models.utils import utc_now

authentication_log_cli = AppGroup("authlog", help="Manage authentication log data")


@authentication_log_cli.command("cleanup", help="Clean up old authentication log entries.")
@click.option('--age', type=int, required=True,
              help="Delete authentication log entries older than this number of days.")
@click.option('--chunksize', type=int,
              help="Delete entries in chunks of the given size to avoid deadlocks.")
@click.option('--dryrun', is_flag=True,
              help="Do not actually delete, only show what would be done.")
def cleanup(age, chunksize, dryrun):
    """
    Delete authentication log entries older than the given number of days.

    The authentication log grows with every authentication request and is not pruned automatically. Schedule this
    command (e.g. via cron) to enforce your retention period.
    """
    cutoff = utc_now() - timedelta(days=age)
    if dryrun:
        row_count = AuthenticationLog.query.filter(AuthenticationLog.timestamp < cutoff).count()
        click.echo(f"Would delete {row_count} authentication log entries older than {age} days.")
    else:
        row_count = cleanup_authentication_log(older_than=cutoff, chunk_size=chunksize)
        click.echo(f"Deleted {row_count} authentication log entries older than {age} days.")