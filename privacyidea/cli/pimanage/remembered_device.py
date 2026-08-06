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

from privacyidea.models import RememberedDevice
from privacyidea.models.utils import utc_now
from privacyidea.lib.remembered_device import cleanup_expired_remembered_devices

remembered_device_cli = AppGroup("remembered_device", help="Manage remembered devices")


@remembered_device_cli.command("cleanup",
                         help="Delete all expired remembered devices "
                              "from the database. Run periodically (see the packaged crontab).")
@click.option('--chunksize', type=int,
              help="Delete entries in chunks of the given size to avoid deadlocks")
@click.option('--dryrun', is_flag=True,
              help="Do not actually delete, only show what would be done.")
def cleanup_remembered_devices(chunksize: int, dryrun: bool = False) -> int:
    """
    Delete all expired remembered devices from the
    remembered_devices table.
    """
    criterion = RememberedDevice.expires_at < utc_now()
    if dryrun:
        row_count = RememberedDevice.query.filter(criterion).count()
        click.echo(f"Would delete {row_count!s} expired remembered-device entries.")
    else:
        row_count = cleanup_expired_remembered_devices(chunk_size=chunksize)
        click.echo(f"{row_count!s} entries deleted.")
    return row_count
