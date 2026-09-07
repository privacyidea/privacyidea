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
import configparser
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from typing import IO, NoReturn

import click
from dateutil.tz import tzlocal
from flask import current_app
from flask.cli import AppGroup
from flask.config import Config
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import ArgumentError

SQLITE = "sqlite"
MYSQL = "mysql"
POSTGRESQL = "postgresql"

# Backup implementation per SQLAlchemy backend name (the part of the URI before
# the "+"), so every driver of a supported engine is recognised.
BACKEND_FAMILIES = {
    "sqlite": SQLITE,
    "mysql": MYSQL,
    "mariadb": MYSQL,
    "postgresql": POSTGRESQL,
    "postgres": POSTGRESQL,
}

FAMILY_NAMES = {SQLITE: "SQLite", MYSQL: "MySQL/MariaDB", POSTGRESQL: "PostgreSQL"}

# The client packages providing the dump/restore commands, used in error messages.
CLIENT_PACKAGES = {MYSQL: "mariadb-client (or mysql-client)", POSTGRESQL: "postgresql-client"}

# Suffix of the database dump inside the backup archive. The suffix records which
# engine wrote the dump, so a restore can refuse to feed it to a different one.
# ".sql" and ".sqlite" are the names earlier versions wrote and stay unchanged.
DUMP_SUFFIXES = {SQLITE: ".sqlite", MYSQL: ".sql", POSTGRESQL: ".pgsql"}
DUMP_FAMILIES = {suffix: family for family, suffix in DUMP_SUFFIXES.items()}
DUMP_FILE_PATTERN = re.compile(r"dbdump-\d{8}-\d{4}(?P<suffix>\.sqlite|\.pgsql|\.sql)$")

# The connection parameters that pg_dump and psql take as a command line
# option; everything else has to reach them through the environment.
POSTGRESQL_COMMAND_LINE_PARAMS = frozenset(["host", "port", "user", "password", "dbname"])

# libpq environment variables for the connection parameters that have no
# command line option. Parameters outside this mapping are reported as ignored
# instead of being dropped silently.
POSTGRESQL_ENV_PARAMS = {
    "sslmode": "PGSSLMODE",
    "sslrootcert": "PGSSLROOTCERT",
    "sslcert": "PGSSLCERT",
    "sslkey": "PGSSLKEY",
    "sslcrl": "PGSSLCRL",
    "gssencmode": "PGGSSENCMODE",
    "channel_binding": "PGCHANNELBINDING",
    "application_name": "PGAPPNAME",
    "connect_timeout": "PGCONNECT_TIMEOUT",
    "options": "PGOPTIONS",
    "target_session_attrs": "PGTARGETSESSIONATTRS",
}

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

    SQLite, MySQL/MariaDB and PostgreSQL databases are supported. Dumping a
    MySQL/MariaDB or a PostgreSQL database requires the client commands of the
    respective engine (mysqldump, or pg_dump) to be installed.
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

    url = _database_url(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
    family = _backend_family(url)

    backup_file = directory.joinpath(f"{base_name}-{cur_date}.tgz")
    sqlfile = directory.joinpath(f"dbdump-{cur_date}{DUMP_SUFFIXES[family]}")

    if family == SQLITE:
        _dump_sqlite(url, sqlfile)
    elif family == MYSQL:
        _report_obsolete_mysql_defaults(conf_dir)
        _dump_mysql(url, sqlfile)
    else:
        _dump_postgresql(url, sqlfile)

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
@click.option("--keep-db-uri", is_flag=True, default=False,
              help="Keep the current SQLALCHEMY_DATABASE_URI from the live config "
                   "instead of overwriting it with the one stored in the backup.")
def backup_restore(backup_file, keep_db_uri):
    """Restore a previously made backup from the BACKUP_FILE

    The contents of the target database are overwritten. The database itself is
    not created: the database and the role connecting to it have to exist
    already, as they do on a regular privacyIDEA installation.
    """
    # TODO: Also allow to specify a target directory, otherwise it will always
    #  extract to the base /
    # TODO: extracting the SQLite file does not work if there are other SQLite
    #  files in the archive

    config_file = None
    sqlfile = None
    dump_family = None
    enckey_contained = False

    try:
        with tarfile.open(backup_file, "r:gz") as tf:
            for member in tf:
                member_name = member.name
                dump_match = DUMP_FILE_PATTERN.search(member_name)
                if re.search(r"/pi.cfg$", member_name):
                    config_file = f"/{member_name}"
                elif dump_match:
                    sqlfile = f"/{member_name}"
                    dump_family = DUMP_FAMILIES[dump_match.group("suffix")]
                elif re.search(r"/enc[kK]ey", member_name):
                    enckey_contained = True
    except (tarfile.TarError, OSError) as e:
        click.secho(f"Unable to open backup file {backup_file}: {e}", fg="red")
        sys.exit(2)

    if not config_file:
        click.secho("Missing config file pi.cfg in backup file.", fg="red")
        sys.exit(2)
    if not sqlfile:
        click.secho("Missing database dump in backup file.", fg="red")
        sys.exit(2)

    config_file = pathlib.Path(config_file)
    sqlfile = pathlib.Path(sqlfile)
    if enckey_contained:
        click.echo("Also restoring the encryption key")
    else:
        click.secho("NO FILE 'enckey' CONTAINED! BE SURE TO RESTORE THE ENCRYPTION "
                    "KEY MANUALLY!", fg='yellow')
    click.echo(f"Restoring to {config_file} with data from {sqlfile}")

    # If requested, capture the current DB URI before extraction overwrites pi.cfg.
    current_sqluri = None
    read_success = False
    if keep_db_uri and config_file.exists():
        try:
            current_cfg = Config(config_file.parent)
            current_cfg.from_pyfile(config_file)
            read_success = True
            current_sqluri = current_cfg.get("SQLALCHEMY_DATABASE_URI")
        except Exception as e:
            click.secho(f"--keep-db-uri: could not read live config ({e}). "
                        "Using database URI from backup.",
                        fg="yellow")
        if read_success:
            if current_sqluri:
                click.echo("--keep-db-uri: using database URI from live config.")
            else:
                click.secho(
                    "--keep-db-uri: no SQLALCHEMY_DATABASE_URI found in live config. "
                    "Using database URI from backup.",
                    fg="yellow",
                )

    with tarfile.open(backup_file, "r:gz") as tf:
        if sys.version_info >= (3, 12):
            tf.extractall(path="/", filter="data")
        else:
            tf.extractall(path="/", members=_safe_members(tf, "/"))
    click.echo(60 * "=")

    # use Flask config to read in the config file (now restored from backup)
    cfg = Config(config_file.parent)
    cfg.from_pyfile(config_file)

    if keep_db_uri and current_sqluri:
        # Patch the restored pi.cfg to keep the original DB URI in-place.
        # repr() ensures the value is a properly escaped Python string literal,
        # so URIs containing quotes, backslashes or other special characters
        # cannot corrupt the config file syntax.
        cfg_text = config_file.read_text()
        new_line = f'SQLALCHEMY_DATABASE_URI = {repr(current_sqluri)}'
        if re.search(r'^SQLALCHEMY_DATABASE_URI\s*=', cfg_text, re.MULTILINE):
            cfg_text = re.sub(
                r'^SQLALCHEMY_DATABASE_URI\s*=.*$',
                new_line,
                cfg_text,
                flags=re.MULTILINE,
            )
        else:
            cfg_text += f'\n{new_line}\n'
        config_file.write_text(cfg_text)
        sqluri = current_sqluri
    else:
        sqluri = cfg["SQLALCHEMY_DATABASE_URI"]

    if sqluri is None:
        click.secho(f"No SQLALCHEMY_DATABASE_URI found in {config_file}",
                    fg="red")
        sys.exit(2)

    url = _database_url(sqluri)
    family = _backend_family(url)
    if family != dump_family:
        # A dump replayed against another engine fails with syntax errors at
        # best and writes a partial schema at worst.
        click.secho(f"The backup contains a {FAMILY_NAMES[dump_family]} dump, but the database URI "
                    f"points to {FAMILY_NAMES[family]}. Restoring across database engines is not "
                    f"supported. The configuration was restored and the dump was kept at {sqlfile}; "
                    "the database was not touched.", fg="red")
        sys.exit(2)

    if family == SQLITE:
        _restore_sqlite(url, sqlfile)
    elif family == MYSQL:
        _report_obsolete_mysql_defaults(config_file.parent)
        _restore_mysql(url, sqlfile)
    else:
        _restore_postgresql(url, sqlfile)


def _database_url(sqluri: str | None) -> URL:
    """Parse a database URI into a SQLAlchemy URL, or exit if it is unusable.

    SQLAlchemy is used instead of ``urlparse`` because it knows the driver
    syntax and percent-decodes username, password and database name.
    """
    if not sqluri:
        click.secho("No database URI configured (SQLALCHEMY_DATABASE_URI).", fg="red")
        sys.exit(2)
    try:
        url = make_url(sqluri)
    except ArgumentError as e:
        click.secho(f"Cannot parse the database URI: {e}", fg="red")
        sys.exit(2)
    if not url.database:
        click.secho(f"The database URI contains no database: {url.render_as_string(hide_password=True)}",
                    fg="red")
        sys.exit(2)
    if url.database == ":memory:":
        click.secho("An in-memory database cannot be backed up or restored.", fg="red")
        sys.exit(2)
    return url


def _backend_family(url: URL) -> str:
    """Return the backup implementation to use for a database URL, or exit.

    The backend name is the part of the URI scheme before the "+", so all
    drivers of an engine (mysql+pymysql, postgresql+psycopg, ...) map to the
    same family.
    """
    family = BACKEND_FAMILIES.get(url.get_backend_name())
    if not family:
        click.secho(f"Unsupported database: {url.get_backend_name()}. Backup and restore support "
                    f"{', '.join(FAMILY_NAMES[f] for f in (SQLITE, MYSQL, POSTGRESQL))}.", fg="red")
        sys.exit(2)
    return family


def _run_client(cmd: list[str], family: str, env: dict[str, str] | None = None,
                stdin: IO[bytes] | None = None) -> subprocess.CompletedProcess:
    """Run a database client command, turning a missing binary into a clear error.

    Without this, an installation lacking the client package fails with a
    FileNotFoundError traceback instead of telling the admin what to install.

    ``stdin`` is an open binary file the client reads the dump from. Handing
    over the file itself keeps the dump out of the memory of this process and
    away from any text decoding, so the size of the database and the encoding
    the dump was written in do not matter.
    """
    try:
        return subprocess.run(cmd, env=env, stdin=stdin)  # nosec B603 - fixed argv, no shell
    except FileNotFoundError:
        click.secho(f"Could not find the '{cmd[0]}' command, which is needed to dump and restore a "
                    f"{FAMILY_NAMES[family]} database. Install the {CLIENT_PACKAGES[family]} package.",
                    fg="red")
        sys.exit(2)


def _dump_failed(binary: str, returncode: int, sqlfile: pathlib.Path, hint: str | None = None) -> NoReturn:
    """Report a failed database dump and exit.

    A partial dump is removed, so it can never be packaged and reported as a
    successful backup.
    """
    if sqlfile.exists():
        sqlfile.unlink()
    message = (f"Database dump failed ({binary} exit code {returncode}); "
               "no backup file was written.")
    if hint:
        message = f"{message} {hint}"
    click.secho(message, fg="red")
    sys.exit(2)


def _restore_failed(binary: str, returncode: int, sqlfile: pathlib.Path) -> NoReturn:
    """Report a failed database restore and exit, keeping the dump file."""
    click.secho(f"Database restore failed ({binary} exit code {returncode}). "
                f"The dump file was kept at {sqlfile} for inspection/retry.",
                fg="red")
    sys.exit(2)


def _dump_sqlite(url: URL, sqlfile: pathlib.Path) -> None:
    click.echo(f"Backup SQLite file {url.database}")
    shutil.copyfile(url.database, sqlfile)


def _restore_sqlite(url: URL, sqlfile: pathlib.Path) -> None:
    click.echo(f"Restore SQLite {url.database}")
    shutil.copyfile(sqlfile, url.database)
    os.unlink(sqlfile)


def _mysql_connection_args(url: URL) -> list[str]:
    """Host and port options shared by mysqldump and mysql.

    Both are omitted for a URI without a host, which connects via the local
    socket.
    """
    args = []
    if url.host:
        args.extend(["-h", url.host])
    if url.port:
        args.extend(["-P", str(url.port)])
    return args


def _dump_mysql(url: URL, sqlfile: pathlib.Path) -> None:
    # call mysqldump to get a copy of the database.
    # --single-transaction dumps a consistent InnoDB snapshot without taking
    # table locks. The default (LOCK TABLES) path fails on a MariaDB Galera
    # cluster, which rejects locking the SEQUENCE objects privacyIDEA creates
    # ("This version of MariaDB doesn't yet support 'LOCK TABLE on SEQUENCES
    # in Galera cluster'"). --skip-lock-tables is already implied by
    # --single-transaction and is passed only as an explicit safeguard.
    with tempfile.TemporaryDirectory() as defaults_dir:
        defaults_file = pathlib.Path(defaults_dir).joinpath("mysql.cnf")
        _write_mysql_defaults(defaults_file, url)
        cmd = ["mysqldump", f"--defaults-file={defaults_file!s}",
               "--single-transaction", "--skip-lock-tables"]
        cmd.extend(_mysql_connection_args(url))
        # -B emits CREATE DATABASE IF NOT EXISTS and DROP TABLE IF EXISTS, which
        # is what makes the dump replayable into a database that still holds the
        # old schema. It also writes the name of the dumped database into the
        # dump itself (CREATE DATABASE followed by USE), so a restore always
        # writes into a database of that name, whatever the target URI says.
        cmd.extend(["-B", url.database, "-r", str(sqlfile)])
        result = _run_client(cmd, MYSQL)
    if result.returncode != 0:
        _dump_failed("mysqldump", result.returncode, sqlfile)


def _restore_mysql(url: URL, sqlfile: pathlib.Path) -> None:
    # Rewriting database
    click.echo("Restoring database.")
    with tempfile.TemporaryDirectory() as defaults_dir:
        defaults_file = pathlib.Path(defaults_dir).joinpath("mysql.cnf")
        _write_mysql_defaults(defaults_file, url)
        cmd = ["mysql", f"--defaults-file={defaults_file!s}"]
        cmd.extend(_mysql_connection_args(url))
        # -B here is the client's --batch, not mysqldump's --databases. The
        # database it selects is only a default: the dump's own USE statement
        # takes over.
        cmd.extend(["-B", url.database])
        with open(sqlfile, "rb") as sql_file:
            p = _run_client(cmd, MYSQL, stdin=sql_file)
    if p.returncode != 0:
        _restore_failed("mysql", p.returncode, sqlfile)
    os.unlink(sqlfile)


def _postgresql_driver_parameters(url: URL) -> dict:
    """The connection parameters psycopg2 would use for this URI.

    Asking the dialect instead of reading the fields of the URI keeps the client
    on the database privacyIDEA itself talks to, whatever shape the URI has: the
    query part can override the host and the port of the URI, and a host given
    more than once turns into the comma separated multi-host list of libpq,
    together with the matching list of ports. Both are assembled here by the
    same code that builds the connection of the application.

    The keys are libpq connection keywords; host, port, user, password and
    dbname become command line options, the rest are passed in the environment.
    """
    return url.get_dialect()().create_connect_args(url)[1]


def _postgresql_connection_args(parameters: dict) -> list[str]:
    """Connection options shared by pg_dump and psql.

    Host and port are omitted for a URI that has neither, which connects over
    the local socket.

    --no-password makes libpq fail instead of asking for a password, so a
    missing or wrong password cannot leave a scheduled backup waiting on a
    prompt forever.
    """
    args = []
    if parameters.get("host"):
        args.extend(["--host", str(parameters["host"])])
    if parameters.get("port"):
        args.extend(["--port", str(parameters["port"])])
    if parameters.get("user"):
        args.extend(["--username", str(parameters["user"])])
    args.append("--no-password")
    return args


def _postgresql_env(parameters: dict) -> dict[str, str]:
    """Environment for pg_dump and psql.

    The password is passed in the environment rather than on the command line,
    where it would be visible in the process list, and rather than in a file in
    the config directory, which would end up inside the backup archive. The
    remaining connection parameters have no command line option and reach the
    client as the libpq variable of the same meaning.
    """
    env = dict(os.environ)
    if parameters.get("password"):
        env["PGPASSWORD"] = str(parameters["password"])
    ignored = []
    for parameter, value in parameters.items():
        if parameter in POSTGRESQL_COMMAND_LINE_PARAMS or value is None:
            continue
        env_name = POSTGRESQL_ENV_PARAMS.get(parameter)
        if env_name:
            env[env_name] = str(value)
        else:
            ignored.append(parameter)
    if ignored:
        click.secho("The following connection parameters of the database URI are not applied when "
                    f"dumping or restoring the database: {', '.join(sorted(ignored))}", fg="yellow")
    return env


def _dump_postgresql(url: URL, sqlfile: pathlib.Path) -> None:
    # --clean --if-exists drops every object before recreating it, which is what
    # makes the dump replayable into a database that still holds the old schema.
    # A plain dump without it only applies to an empty database.
    # --no-owner/--no-privileges/--no-comments keep the restore working when the
    # role running it differs from the one the backup was taken with: owners,
    # privileges and comments are not part of what privacyIDEA manages, but
    # restoring them requires ownership. A comment on the public schema in
    # particular is dumped whenever it differs from the server default, and
    # applying it as a role that does not own the schema fails - which would
    # abort the whole restore.
    parameters = _postgresql_driver_parameters(url)
    cmd = ["pg_dump", "--format=plain", "--clean", "--if-exists",
           "--no-owner", "--no-privileges", "--no-comments"]
    cmd.extend(_postgresql_connection_args(parameters))
    cmd.extend(["--dbname", str(parameters["dbname"]), "--file", str(sqlfile)])
    result = _run_client(cmd, POSTGRESQL, env=_postgresql_env(parameters))
    if result.returncode != 0:
        _dump_failed("pg_dump", result.returncode, sqlfile,
                     hint="pg_dump has to be at least as new as the PostgreSQL server it dumps.")


def _restore_postgresql(url: URL, sqlfile: pathlib.Path) -> None:
    click.echo("Restoring database.")
    # ON_ERROR_STOP together with --single-transaction makes the restore
    # all-or-nothing, instead of leaving a half-restored schema behind on the
    # first failing statement. --no-psqlrc keeps a psqlrc file in the home
    # directory of the calling user from changing settings mid-restore.
    # The query results psql would print are the return values of the set_config
    # and setval calls in the dump, one table per sequence; they are discarded,
    # while errors and warnings still reach the terminal on stderr.
    parameters = _postgresql_driver_parameters(url)
    cmd = ["psql", "--quiet", "--no-psqlrc", "--set", "ON_ERROR_STOP=on", "--single-transaction",
           f"--output={os.devnull}"]
    cmd.extend(_postgresql_connection_args(parameters))
    cmd.extend(["--dbname", str(parameters["dbname"]), "--file", str(sqlfile)])
    result = _run_client(cmd, POSTGRESQL, env=_postgresql_env(parameters))
    if result.returncode != 0:
        _restore_failed("psql", result.returncode, sqlfile)
    os.unlink(sqlfile)


def _safe_members(tf, dest):
    """Fallback member filter for Python < 3.12, which lacks ``tarfile``'s
    ``filter='data'`` option.

    Skips special files (devices, fifos, character/block specials) so a
    malicious or corrupted archive can't create them on extraction. Only
    regular files, directories, symlinks and hardlinks are yielded.

    The path-traversal and link-target checks below are no-ops when ``dest``
    is ``/`` (every resolved absolute path is contained in ``/``), but are
    kept so the helper stays correct if a non-root extraction target is
    introduced later (see TODOs in ``backup_restore``).
    """
    dest = pathlib.Path(dest).resolve()
    for member in tf.getmembers():
        member_path = (dest / member.name).resolve()
        if not str(member_path).startswith(str(dest)):
            click.secho(f"Skipping unsafe path: {member.name}", fg="yellow")
            continue
        if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
            click.secho(f"Skipping special file: {member.name}", fg="yellow")
            continue
        if member.issym() or member.islnk():
            link_target = pathlib.Path(member.linkname)
            if not link_target.is_absolute():
                link_target = (member_path.parent / link_target).resolve()
            else:
                link_target = link_target.resolve()
            if not str(link_target).startswith(str(dest)):
                click.secho(f"Skipping link escaping destination: {member.name} -> {member.linkname}", fg="yellow")
                continue
        yield member


def _quote_mysql_option(value: str) -> str:
    """Quote a value for a MySQL option file.

    An unquoted value ends at a '#', which would silently truncate a password
    containing one, and the option file parser expands backslash escapes inside
    the value, so a literal backslash has to be doubled. A '"' has to be escaped
    as well: it would end the quoted part of the value, and a '#' behind it
    would start a comment again.
    """
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _report_obsolete_mysql_defaults(conf_dir: pathlib.Path) -> None:
    """Point out the mysql.cnf earlier versions left in the config directory.

    It holds the database password in cleartext and is not used any more, but
    removing someone else's file in the config directory is not this command's
    call to make.
    """
    obsolete = conf_dir.joinpath("mysql.cnf")
    if obsolete.exists():
        click.secho(f"{obsolete} was written by an earlier version, is not used any more and "
                    "contains the database password in cleartext. You can delete it.", fg="yellow")


def _write_mysql_defaults(defaults_file: pathlib.Path, url: URL) -> None:
    # create a mysql config file to avoid adding username and password to the command
    sql_defaults = configparser.ConfigParser(interpolation=None)
    sql_defaults['client'] = {
        "user": _quote_mysql_option(url.username or ""),
        "password": _quote_mysql_option(url.password or "")
    }
    sql_defaults['mysqldump'] = {"no-tablespaces": "True"}
    with defaults_file.open(mode="w") as f:
        sql_defaults.write(f)
    defaults_file.chmod(0o600)
    # set correct owner, if possible
    if os.geteuid() == 0:
        dir_stat = defaults_file.parent.stat()
        shutil.chown(defaults_file, dir_stat.st_uid, dir_stat.st_gid)
