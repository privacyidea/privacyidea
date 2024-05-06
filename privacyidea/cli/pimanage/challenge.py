# SPDX-FileCopyrightText: (C) 2024 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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

import datetime
import re
import sys
import click
import yaml
from flask import current_app
from flask.cli import AppGroup
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

from privacyidea.lib.audit import getAudit
from privacyidea.models import Challenge
from privacyidea.lib.sqlutils import delete_matching_rows
from privacyidea.lib.utils import parse_timedelta

challenge_cli = AppGroup("challenge", help="Manage challenge data")


@challenge_cli.command("cleanup",
                       help="Clean up all expired challenges.")
@click.option('--chunksize', type=int,
              help="Delete entries in chunks of the given size to avoid deadlocks")
@click.option('--age', type=int,
              help="Instead of deleting expired challenges "
                   "delete challenge entries older than these number of minutes.")
@click.option('--dryrun', is_flag=True,
              help="Do not actually delete, only show what would be done.")
def cleanup_challenge(chunksize, age, dryrun=False):
    """
    Delete all expired challenges from the challenge table
    """
    metadata = MetaData()
    if chunksize is not None:
        chunksize = int(chunksize)

    token_db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    engine = create_engine(token_db_uri)
    # create a configured "Session" class
    session = sessionmaker(bind=engine)()
    # create a Session
    metadata.create_all(engine)

    if age:
        # Delete challenges created earlier than age minutes ago
        now = datetime.datetime.now() - datetime.timedelta(minutes=age)
        click.echo("Deleting challenges older than {0!s}".format(now))
        criterion = Challenge.timestamp < now
    else:
        # Delete expired challenges
        click.echo("Deleting expired challenges.")
        now = datetime.datetime.now()
        criterion = Challenge.expiration < now

    if dryrun:
        r = Challenge.query.filter(criterion).count()
        click.echo("Would delete {0!s} challenge entries.".format(r))
    else:
        r = delete_matching_rows(session, Challenge.__table__, criterion, chunksize)
        click.echo("{0!s} entries deleted.".format(r))
