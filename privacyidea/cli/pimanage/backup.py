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
"""Create/Restore database backup"""
import os
import sys
import shutil
import shlex
import pathlib
import configparser
import subprocess
import tarfile
from datetime import datetime
import re

import click
from dateutil.tz import tzlocal
from urllib.parse import urlparse
from flask import current_app
from flask.config import Config
from flask.cli import AppGroup

MYSQL_DIALECTS = ["mysql", "pymysql", "mysql+pymysql", "mariadb+pymysql"]

backup_cli = AppGroup("backup", help="Create/Restore database backup of privacyIDEA installation")


@backup_cli.command("create", short_help="Create a new backup of the database and configuration")
@click.option("-d", "--directory", "backup_dir",
              type=click.Path(file_okay=False, writable=True),
              default="/var/lib/privacyidea/backup/",
              show_default=True,
              help="Path to the backup directory")
@click.option("-c", "--config_dir",
              type=click.Path(exists=True, file_okay=False, writable=True),
              default="/etc/privacyidea/",
              show_default=True,
              help="Path to privacyIDEA config directory")
@click.option("-r", "--radius_dir",
              type=click.Path(exists=True, file_okay=False, readable=True),
              default=None,
              show_default=True,
              help="Path to FreeRADIUS config directory")
@click.option("-e", "--enckey", is_flag=True,
              help="Add the encryption key to the backup")
def backup_create(backup_dir, config_dir, radius_dir, enckey):
    """
    Create a new backup of the database and the configuration. By default,
    the encryption key is not included. Use the 'enckey' option to also
    add the encryption key to the backup. In this case make sure, that the
    backups are stored securely.

    You can also include a given FreeRADIUS configuration into the backup.
    Just specify a directory using 'radius_dir'.
    """
    # TODO: Add requirement for the config file and remove app initialization.
    #  Currently, when calling this function, the Flask app gets initialized
    #  (either from /etc/privacyidea/pi.cfg or from the environment variable)
    #  regardless of the given config directory (so they can differ).
    #  Since all the necessary paths are given in the config file, we should
    #  just use that for the gathering the files for backup.
    # TODO: Remove generated/copied file in case of an error. Maybe create a
    #  temporary folder where the data is collected
    cur_date = datetime.now(tz=tzlocal()).strftime("%Y%m%d-%H%M")
    base_name = "privacyidea-backup"

    conf_dir = pathlib.Path(config_dir).absolute()
    directory = pathlib.Path(backup_dir).absolute()
    directory.mkdir(parents=True, exist_ok=True)

    enc_file = pathlib.Path(current_app.config.get("PI_ENCFILE"))

    # set correct owner, if possible
    if os.geteuid() == 0:
        enc_file_stat = enc_file.stat()
        shutil.chown(directory, user=enc_file_stat.st_uid, group=enc_file_stat.st_gid)

    sqlfile = directory.joinpath(f"dbdump-{cur_date}.sql")
    backup_file = directory.joinpath(f"{base_name}-{cur_date}.tgz")

    parsed_sqluri = urlparse(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
    sqltype = parsed_sqluri.scheme

    if sqltype == "sqlite":
        productive_file = parsed_sqluri.path
        click.echo(f"Backup SQLite file {productive_file}")
        sqlfile = directory.joinpath(f"dbdump-{cur_date}.sqlite")
        shutil.copyfile(productive_file, sqlfile)
    elif sqltype in MYSQL_DIALECTS:
        database = parsed_sqluri.path[1:]
        defaults_file = conf_dir.joinpath("mysql.cnf")
        _write_mysql_defaults(defaults_file, parsed_sqluri)
        # call mysqldump to get a copy of the database
        cmd = ['mysqldump', '--defaults-file={!s}'.format(defaults_file), '-h',
               shlex.quote(parsed_sqluri.hostname)]
        if parsed_sqluri.port:
            cmd.extend(['-P', str(parsed_sqluri.port)])
        cmd.extend(['-B', shlex.quote(database), '-r', sqlfile])
        subprocess.run(cmd)
    else:
        click.echo(f"unsupported SQL syntax: {sqltype}")
        sys.exit(2)

    with tarfile.open(backup_file, "x:gz") as tf:
        tf.add(sqlfile)
        if radius_dir:
            # Simply append the radius directory to the backup command
            tf.add(radius_dir, recursive=True)

        if not enckey:
            # Exclude enckey from backup

            def exclude_encfile(t):
                if enc_file.match(t.name):
                    return None
                return t

            tf.add(conf_dir, recursive=True, filter=exclude_encfile)
        else:
            click.secho("Including encryption key in backup", fg="yellow")
            tf.add(conf_dir, recursive=True)

    sqlfile.unlink()
    backup_file.chmod(0o600)
    click.echo(f"Backup written to file {backup_file}")


@backup_cli.command("restore")
@click.argument("backup_file", type=str)
def backup_restore(backup_file):
    """Restore a previously made backup from the BACKUP_FILE"""
    # TODO: Use tarfile package
    # TODO: Also allow to specify a target directory, otherwise it will always
    #  extract to the base /
    # TODO: extracting the SQLite file does not work if there are other SQLite
    #  files in the archive
    sqluri = None
    config_file = None
    sqlfile = None
    enckey_contained = False

    p = subprocess.run(["tar", "-ztf", backup_file], capture_output=True,
                       text=True)
    if p.returncode != 0:
        click.secho(f"Unable to open backup file {backup_file}", fg="red")
        sys.exit(2)
    for line in p.stdout.split("\n"):
        if re.search(r"/pi.cfg$", line):
            config_file = "/{0!s}".format(line.strip())
        elif re.search(r"dbdump-\d{8}-\d{4}\.sql", line):
            sqlfile = "/{0!s}".format(line.strip())
        elif re.search(r"/enc[kK]ey", line):
            enckey_contained = True

    if not config_file:
        click.secho("Missing config file pi.cfg in backup file.", fg="red")
    if not sqlfile:
        click.secho("Missing database dump in backup file.", fg="red")

    config_file = pathlib.Path(config_file)
    sqlfile = pathlib.Path(sqlfile)
    if enckey_contained:
        click.echo("Also restoring the encryption key")
    else:
        click.secho("NO FILE 'enckey' CONTAINED! BE SURE TO RESTORE THE ENCRYPTION "
                    "KEY MANUALLY!", fg='yellow')
    click.echo(f"Restoring to {config_file} with data from {sqlfile}")

    subprocess.run(["tar", "-zxf", backup_file, "-C", "/"])
    click.echo(60 * "=")
    # use Flask config to read in the config file
    cfg = Config(config_file.parent)
    cfg.from_pyfile(config_file)
    sqluri = cfg["SQLALCHEMY_DATABASE_URI"]

    if sqluri is None:
        click.secho(f"No SQLALCHEMY_DATABASE_URI found in {config_file}",
                    fg="red")
        sys.exit(2)
    parsed_sqluri = urlparse(sqluri)
    sqltype = parsed_sqluri.scheme
    if sqltype == "sqlite":
        productive_file = parsed_sqluri.path
        click.echo(f"Restore SQLite {productive_file}")
        shutil.copyfile(sqlfile, productive_file)
        os.unlink(sqlfile)
    elif sqltype in MYSQL_DIALECTS:
        database = parsed_sqluri.path[1:]
        defaults_file = pathlib.Path(config_file).parent.joinpath("mysql.cnf")
        _write_mysql_defaults(defaults_file, parsed_sqluri)
        # Rewriting database
        click.echo("Restoring database.")
        cmd = ["mysql", f"--defaults-file={defaults_file}",
               "-h", parsed_sqluri.hostname]
        if parsed_sqluri.port:
            cmd.extend(['-P', str(parsed_sqluri.port)])
        cmd.extend(['-B', shlex.quote(database)])
        with open(sqlfile, "r") as sql_file:
            p = subprocess.run(cmd, input=sql_file.read())
            if p.returncode == 0:
                os.unlink(sqlfile)
    else:
        print("unsupported SQL syntax: %s" % sqltype)
        sys.exit(2)


def _write_mysql_defaults(defaults_file, parsed_sqluri):
    # create a mysql config file to avoid adding username and password to the command
    sql_defaults = configparser.ConfigParser()
    sql_defaults['client'] = {
        "user": parsed_sqluri.username,
        "password": parsed_sqluri.password
    }
    sql_defaults['mysqldump'] = {"no-tablespaces": "True"}
    with defaults_file.open(mode="w") as f:
        sql_defaults.write(f)
    defaults_file.chmod(0o600)
    # set correct owner, if possible
    if os.geteuid() == 0:
        dir_stat = defaults_file.parent.stat()
        shutil.chown(defaults_file, dir_stat.st_uid, dir_stat.st_gid)
