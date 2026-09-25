# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
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

import click
from flask.cli import AppGroup

from privacyidea.lib.metrics import cleanup_old_metrics, count_old_metrics

metrics_cli = AppGroup("metrics", help="Manage the internal metrics")


@metrics_cli.command("cleanup",
                     help="Delete metric rows older than the given number of hours. "
                          "Run periodically (see the packaged crontab).")
@click.option('--older-than-hours', type=click.IntRange(min=1), default=24, show_default=True,
              help="Delete metric rows whose 5-minute window started more than this many hours ago. "
                   "The dashboard shows at most the last 24 hours.")
@click.option('--dryrun', is_flag=True,
              help="Do not actually delete, only show what would be done.")
def cleanup_metrics(older_than_hours: int, dryrun: bool = False) -> int:
    """
    Delete aged-out rows from the metric_aggregate table, which backs the
    resolver-timing and notification-delivery dashboard panels.
    """
    older_than_seconds = older_than_hours * 3600
    if dryrun:
        row_count = count_old_metrics(older_than_seconds=older_than_seconds)
        click.echo(f"Would delete {row_count} metric rows older than {older_than_hours} hours.")
    else:
        row_count = cleanup_old_metrics(older_than_seconds=older_than_seconds)
        click.echo(f"Deleted {row_count} metric rows older than {older_than_hours} hours.")
    return row_count
