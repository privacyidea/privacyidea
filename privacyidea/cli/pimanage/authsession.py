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

from privacyidea.models import AuthSession
from privacyidea.models.utils import utc_now
from privacyidea.lib.authsession import cleanup_expired_auth_sessions

authsession_cli = AppGroup("authsession", help="Manage persistent 'remember device' sessions")


@authsession_cli.command("cleanup",
                         help="Delete all expired persistent 'remember device' sessions "
                              "from the database. Run periodically (see the packaged crontab).")
@click.option('--chunksize', type=int,
              help="Delete entries in chunks of the given size to avoid deadlocks")
@click.option('--dryrun', is_flag=True,
              help="Do not actually delete, only show what would be done.")
def cleanup_auth_sessions(chunksize: int, dryrun: bool = False) -> int:
    """
    Delete all expired persistent authentication sessions from the
    auth_sessions table.
    """
    criterion = AuthSession.expires_at < utc_now()
    if dryrun:
        row_count = AuthSession.query.filter(criterion).count()
        click.echo(f"Would delete {row_count!s} expired session entries.")
    else:
        row_count = cleanup_expired_auth_sessions(chunk_size=chunksize)
        click.echo(f"{row_count!s} entries deleted.")
    return row_count
