# SPDX-FileCopyrightText: (C) 2023 Paul Lettich <paul.lettich@netknights.it>
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
from sqlalchemy import create_engine, desc, MetaData
from sqlalchemy.orm import sessionmaker

from privacyidea.lib.audit import getAudit
from privacyidea.lib.auditmodules.sqlaudit import LogEntry
from privacyidea.lib.sqlutils import delete_matching_rows
from privacyidea.lib.utils import parse_timedelta

audit_cli = AppGroup("audit", help="Manage Audit log")


@audit_cli.command("rotate")
@click.option('-hw', '--highwatermark', default=10000, show_default=True,
              help="If entries exceed this value, old entries are deleted.")
@click.option('-lw', '--lowwatermark', default=5000, show_default=True,
              help="Keep this number of entries.")
@click.option('--age', default=0,
              help="Delete audit entries older than these number of days.")
@click.option('--config', type=click.File('r'),
              help="Read config from the specified yaml file.")
@click.option('--dryrun', is_flag=True,
              help="Do not actually delete, only show what would be done.")
@click.option('--chunksize', type=int,
              help="Delete entries in chunks of the given size to avoid deadlocks")
def rotate_audit(highwatermark, lowwatermark, age, config,
                 dryrun, chunksize):
    """
    Clean the SQL audit log.

    You can either clean the audit log based on the number of entries of
    based on the age of the entries.

    Cleaning based on number of entries:

    If more than 'highwatermark' entries are in the audit log old entries
    will be deleted, so that 'lowwatermark' entries remain.

    Cleaning based on age:

    Entries older than the specified number of days are deleted.

    Cleaning based on config file:

    You can clean different type of entries with different ages or watermark.
    See the documentation for the format of the config file
    """
    metadata = MetaData()
    if chunksize is not None:
        chunksize = int(chunksize)

    default_module = "privacyidea.lib.auditmodules.sqlaudit"
    token_db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    audit_db_uri = current_app.config.get("PI_AUDIT_SQL_URI", token_db_uri)
    audit_module = current_app.config.get("PI_AUDIT_MODULE", default_module)
    if audit_module != default_module:
        click.secho(f"We only rotate SQL audit module. You are using {audit_module}",
                    fg="red")
    if config:
        click.echo("Cleaning up with config file.")
    elif age > 0:
        click.echo(f"Cleaning up with age: {age}.")
    else:
        click.echo(f"Cleaning up with high: {highwatermark}, low: {lowwatermark}.")

    engine = create_engine(audit_db_uri)
    # create a configured "Session" class
    session = sessionmaker(bind=engine)()
    # create a Session
    metadata.create_all(engine)
    if config:
        yml_config = yaml.safe_load(config)
        auditlogs = session.query(LogEntry).all()
        delete_list = []
        for log in auditlogs:
            click.echo("investigating log entry {0!s}".format(log.id))
            for rule in yml_config:
                age = int(rule.get("rotate"))
                rotate_date = datetime.datetime.now() - datetime.timedelta(days=age)

                match = False
                for key in rule.keys():
                    if key not in ["rotate"]:
                        search_value = str(rule.get(key))
                        click.echo(" + searching for {0!r} in {1!s}".format(search_value,
                                                                            getattr(LogEntry, key)))
                        audit_value = str(getattr(log, key, ""))
                        m = re.search(search_value, audit_value)
                        if m:
                            # it matches!
                            click.echo(" + -- found {0!r}".format(audit_value))
                            match = True
                        else:
                            # It does not match, we continue to next rule
                            click.echo(" + NO MATCH - SKIPPING rest of conditions!")
                            match = False
                            break

                if match:
                    if log.date < rotate_date:
                        # Delete it!
                        click.echo(" + Deleting {0!s} due to rule {1!s}".format(log.id, rule))
                        # Delete it
                        delete_list.append(log.id)
                    # skip all other rules and go to the next log entry
                    break
        if dryrun:
            click.echo("If you only would let me I would clean up "
                       "{0!s} entries!".format(len(delete_list)))
        else:
            click.echo("Cleaning up {0!s} entries.".format(len(delete_list)))
            delete_matching_rows(session, LogEntry.__table__,
                                 LogEntry.id.in_(delete_list), chunksize)
    elif age:
        now = datetime.datetime.now() - datetime.timedelta(days=age)
        click.echo("Deleting entries older than {0!s}".format(now))
        criterion = LogEntry.date < now
        if dryrun:
            r = LogEntry.query.filter(criterion).count()
            click.echo("Would delete {0!s} entries.".format(r))
        else:
            r = delete_matching_rows(session, LogEntry.__table__, criterion, chunksize)
            click.echo("{0!s} entries deleted.".format(r))
    else:
        count = session.query(LogEntry.id).count()
        last_id = 0
        for l in session.query(LogEntry.id).order_by(desc(LogEntry.id)).limit(1):
            last_id = l[0]
        click.echo("The log audit log has %i entries, the last one is %i" % (count,
                                                                             last_id))
        # deleting old entries
        if count > highwatermark:
            click.echo("More than %i entries, deleting..." % highwatermark)
            cut_id = last_id - lowwatermark
            # delete all entries less than cut_id
            click.echo("Deleting entries smaller than %i" % cut_id)
            criterion = LogEntry.id < cut_id
            if dryrun:
                r = LogEntry.query.filter(criterion).count()
                click.echo("Would delete {0!s} entries.".format(r))
            else:
                r = delete_matching_rows(session, LogEntry.__table__, criterion, chunksize)
                click.echo("{0!s} entries deleted.".format(r))


def _validate_timelimit(_ctx, _param, value):
    if value:
        try:
            tl = parse_timedelta(value)
            return tl
        except TypeError as e:
            raise click.BadParameter(f"Could not parse timelimit ({value}): {e}")
    return None


@audit_cli.command("dump")
@click.option('-t', '--timelimit', callback=_validate_timelimit,
              help="Limit the dumped audit entries to a certain period "
                   "(i.e. '5d' or '3h' for the entries from the last five days "
                   "or three hours. By default all audit entries will be dumped.")
@click.option('-f', '--filename', type=click.File('w'), default=sys.stdout,
              help="Name of the file to dump the audit entries into. "
                   "By default write to stdout.")
def dump_audit(filename, timelimit):
    """Dump the audit log in csv format."""
    audit = getAudit(current_app.config)
    for line in audit.csv_generator(timelimit=timelimit):
        filename.write(line)
