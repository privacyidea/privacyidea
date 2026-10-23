#!/usr/bin/env python3
"""
Create the migration test seed of a privacyIDEA release: a database that "pi-manage setup create_tables" of the release
created and that the code of the release filled, dumped as SQL.

    python tools/generate_release_seed.py <git revision> <version> <engine>

    engine: postgresql | mariadb | mysql | oracle

Example:

    python tools/generate_release_seed.py v3.13.4 3.13.4 postgresql

writes tests/testdata/migrations/seed_v3.13.4_<head revision of the release>_postgresql.sql.

The script extracts the release with "git archive" into a temporary directory and runs its "pi-manage setup
create_tables" and the fill step of this script with the Python interpreter that runs this script, against an empty
database "pi_release_seed" on the database containers of compose-dev.yml. The values are encrypted with
tests/testdata/enckey, the key of the test configuration. It then dumps the database with the dump tool of the engine
(pg_dump, mariadb-dump, mysqldump), or on Oracle with DBMS_METADATA and generated INSERT statements, and drops it.
"""
import argparse
import datetime
import decimal
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import oracledb

REPOSITORY = pathlib.Path(__file__).resolve().parent.parent
SEED_DIRECTORY = REPOSITORY / "tests" / "testdata" / "migrations"
DATABASE = "pi_release_seed"
ORACLE_USER = "PI_RELEASE_SEED"
ORACLE_PASSWORD = "PiReleaseSeed1"
ORACLE_DSN = "127.0.0.1:1521/XEPDB1"
ENGINES = {
    "postgresql": {"url": f"postgresql+psycopg2://privacyidea:privacyidea@127.0.0.1:5432/{DATABASE}",
                   "container": "privacyidea-postgres"},
    "mariadb": {"url": f"mysql+pymysql://privacyidea:privacyidea@127.0.0.1:3306/{DATABASE}?charset=utf8mb4",
                "container": "pi-mariadb-test", "port": 3306},
    "mysql": {"url": f"mysql+pymysql://privacyidea:privacyidea@127.0.0.1:3308/{DATABASE}?charset=utf8mb4",
              "container": "pi-mysql-test", "port": 3308},
    "oracle": {"url": f"oracle+oracledb://{ORACLE_USER}:{ORACLE_PASSWORD}@127.0.0.1:1521/?service_name=XEPDB1"},
}
# The longest string literal Oracle accepts is 4000 bytes, longer values are joined from pieces
ORACLE_LITERAL_PIECE = 1000


def create_database(engine: str) -> None:
    if engine == "postgresql":
        import psycopg2
        connection = psycopg2.connect(host="127.0.0.1", port=5432, user="privacyidea", password="privacyidea",
                                      dbname="postgres")
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS "{DATABASE}" WITH (FORCE)')
            cursor.execute(f'CREATE DATABASE "{DATABASE}"')
        connection.close()
    elif engine in ("mariadb", "mysql"):
        import pymysql
        connection = pymysql.connect(host="127.0.0.1", port=ENGINES[engine]["port"], user="root", password="root",
                                     autocommit=True)
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{DATABASE}`")
            cursor.execute(f"CREATE DATABASE `{DATABASE}` CHARACTER SET utf8mb4")
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{DATABASE}`.* TO 'privacyidea'@'%'")
        connection.close()
    else:
        import oracledb
        connection = oracledb.connect(user="SYSTEM", password="root", dsn=ORACLE_DSN)
        cursor = connection.cursor()
        _drop_oracle_user(cursor)
        cursor.execute(f'CREATE USER {ORACLE_USER} IDENTIFIED BY "{ORACLE_PASSWORD}" QUOTA UNLIMITED ON USERS')
        cursor.execute(f"GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE TO {ORACLE_USER}")
        connection.close()


def _drop_oracle_user(cursor: "oracledb.Cursor") -> None:
    cursor.execute("SELECT sid, serial# FROM v$session WHERE username = :name", name=ORACLE_USER)
    for session_id, serial in cursor.fetchall():
        cursor.execute(f"ALTER SYSTEM KILL SESSION '{session_id},{serial}' IMMEDIATE")
    cursor.execute("SELECT COUNT(*) FROM dba_users WHERE username = :name", name=ORACLE_USER)
    if cursor.fetchone()[0]:
        cursor.execute(f"DROP USER {ORACLE_USER} CASCADE")


def drop_database(engine: str) -> None:
    if engine == "postgresql":
        import psycopg2
        connection = psycopg2.connect(host="127.0.0.1", port=5432, user="privacyidea", password="privacyidea",
                                      dbname="postgres")
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS "{DATABASE}" WITH (FORCE)')
        connection.close()
    elif engine in ("mariadb", "mysql"):
        import pymysql
        connection = pymysql.connect(host="127.0.0.1", port=ENGINES[engine]["port"], user="root", password="root",
                                     autocommit=True)
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{DATABASE}`")
        connection.close()
    else:
        import oracledb
        connection = oracledb.connect(user="SYSTEM", password="root", dsn=ORACLE_DSN)
        _drop_oracle_user(connection.cursor())
        connection.close()


def write_config(directory: pathlib.Path, engine: str) -> pathlib.Path:
    testdata = REPOSITORY / "tests" / "testdata"
    config = directory / "pi.cfg"
    config.write_text(f"SQLALCHEMY_DATABASE_URI = '{ENGINES[engine]['url']}'\n"
                      "SECRET_KEY = 'release-seed-secret-key'\n"
                      "PI_PEPPER = ''\n"
                      f"PI_ENCFILE = '{testdata / 'enckey'}'\n"
                      f"PI_AUDIT_KEY_PRIVATE = '{testdata / 'private.pem'}'\n"
                      f"PI_AUDIT_KEY_PUBLIC = '{testdata / 'public.pem'}'\n"
                      f"PI_LOGFILE = '{directory / 'privacyidea.log'}'\n"
                      "PI_LOGLEVEL = 20\n"
                      "PI_NODE = 'seednode'\n"
                      "PI_NODE_UUID = '8e4e2a5c-0b5f-4f7e-9d43-6a1c2f3b4d5e'\n")
    return config


def run_release_code(source: pathlib.Path, config: pathlib.Path) -> None:
    environment = dict(os.environ, PI_SOURCE=str(source), PRIVACYIDEA_CONFIGFILE=str(config), FLASK_SKIP_DOTENV="1")
    create_tables = ("import sys; sys.path.insert(0, '.'); from privacyidea.cli.pimanage import cli; "
                     "sys.argv = ['pi-manage', 'setup', 'create_tables']; cli()")
    subprocess.run([sys.executable, "-I", "-c", create_tables], cwd=source, env=environment, check=True)
    subprocess.run([sys.executable, "-I", str(pathlib.Path(__file__).resolve()), "fill"], cwd=source,
                   env=environment, check=True)


def stamped_revision(engine: str) -> str:
    """The revision that create_tables stamped, the head of the release."""
    import sqlalchemy
    database = sqlalchemy.create_engine(ENGINES[engine]["url"])
    try:
        with database.connect() as connection:
            revisions = connection.execute(sqlalchemy.text("SELECT version_num FROM alembic_version")).scalars().all()
    finally:
        database.dispose()
    if len(revisions) != 1:
        raise SystemExit(f"create_tables stamped {revisions}, expected one revision")
    return revisions[0]


def _run(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def _server_version(engine: str) -> str:
    if engine == "postgresql":
        return _run(["docker", "exec", ENGINES[engine]["container"], "postgres", "--version"]).strip()
    if engine in ("mariadb", "mysql"):
        import pymysql
        connection = pymysql.connect(host="127.0.0.1", port=ENGINES[engine]["port"], user="root", password="root")
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        connection.close()
        return f"{'MariaDB' if engine == 'mariadb' else 'MySQL'} {version}"
    import oracledb
    connection = oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)
    version = connection.version
    connection.close()
    return f"Oracle {version}"


def dump_postgresql() -> list[str]:
    output = _run(["docker", "exec", "-e", "PGPASSWORD=privacyidea", ENGINES["postgresql"]["container"], "pg_dump",
                   "-U", "privacyidea", "-d", DATABASE, "--no-owner", "--no-privileges", "--no-comments",
                   "--column-inserts", "--quote-all-identifiers"])
    lines = []
    for line in output.splitlines():
        # Session settings and the psql meta commands of the dump would change the connection that loads the seed
        if line.startswith(("SET ", "SELECT pg_catalog.set_config", "\\")) or line.startswith("--"):
            continue
        lines.append(line)
    return _statements("\n".join(lines))


def dump_mysql_family(engine: str) -> list[str]:
    tool = "mariadb-dump" if engine == "mariadb" else "mysqldump"
    options = ["--skip-comments", "--skip-dump-date", "--compact", "--no-tablespaces", "--skip-extended-insert",
               "--order-by-primary"]
    if engine == "mysql":
        options.append("--set-gtid-purged=OFF")
    output = _run(["docker", "exec", ENGINES[engine]["container"], tool, "-uroot", "-proot", *options, DATABASE])
    # The sandbox line is for the mariadb client, and the dump saves and restores the client character set per table
    lines = [line for line in output.splitlines()
             if not re.match(r"/\*M!999999|/\*!\d+ SET (@saved_cs_client|character_set_client)", line)]
    return ["SET FOREIGN_KEY_CHECKS = 0", *_statements("\n".join(lines)), "SET FOREIGN_KEY_CHECKS = 1"]


def _statements(sql: str) -> list[str]:
    return [statement.strip() for statement in re.split(r";[ \t]*$", sql, flags=re.MULTILINE) if statement.strip()]


def _oracle_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, decimal.Decimal)):
        return str(value)
    if isinstance(value, datetime.datetime):
        return f"TIMESTAMP '{value.isoformat(sep=' ')}'"
    if isinstance(value, datetime.timedelta):
        return f"NUMTODSINTERVAL({value.total_seconds()}, 'SECOND')"
    if isinstance(value, bytes):
        return f"HEXTORAW('{value.hex()}')"
    text = str(value)
    if len(text.encode("utf-8")) <= 4000:
        return "'" + text.replace("'", "''") + "'"
    pieces = [text[start:start + ORACLE_LITERAL_PIECE] for start in range(0, len(text), ORACLE_LITERAL_PIECE)]
    return " || ".join("TO_CLOB('" + piece.replace("'", "''") + "')" for piece in pieces)


def _oracle_ddl(cursor: "oracledb.Cursor", object_type: str, name: str) -> str:
    cursor.execute("SELECT DBMS_METADATA.GET_DDL(:object_type, :name) FROM dual", object_type=object_type, name=name)
    ddl = cursor.fetchone()[0].strip()
    # Oracle names the constraints that were created without a name itself; the seed leaves that to the database that
    # loads it, so the names cannot collide with the ones that database gives later
    return re.sub(r'CONSTRAINT "SYS_C\d+" ', "", ddl)


def dump_oracle() -> list[str]:
    import oracledb
    oracledb.defaults.fetch_lobs = False
    connection = oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)
    cursor = connection.cursor()
    transform_parameters = {"SEGMENT_ATTRIBUTES": "FALSE", "STORAGE": "FALSE", "TABLESPACE": "FALSE",
                            "EMIT_SCHEMA": "FALSE", "REF_CONSTRAINTS": "FALSE", "SQLTERMINATOR": "FALSE",
                            "PRETTY": "TRUE"}
    cursor.execute("BEGIN " + " ".join(f"DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, "
                                       f"'{name}', {value});" for name, value in transform_parameters.items())
                   + " END;")
    statements = []
    # The sequences of identity columns are part of the columns
    cursor.execute("SELECT sequence_name FROM user_sequences WHERE sequence_name NOT IN "
                   "(SELECT sequence_name FROM user_tab_identity_cols) ORDER BY sequence_name")
    for (name,) in cursor.fetchall():
        statements.append(_oracle_ddl(cursor, "SEQUENCE", name))
    cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
    tables = [name for (name,) in cursor.fetchall()]
    for table in tables:
        statements.append(_oracle_ddl(cursor, "TABLE", table))
    for table in tables:
        cursor.execute(f'SELECT * FROM "{table}" ORDER BY 1')
        columns = ", ".join(f'"{description[0]}"' for description in cursor.description)
        for row in cursor.fetchall():
            values = ", ".join(_oracle_literal(value) for value in row)
            statements.append(f'INSERT INTO "{table}" ({columns}) VALUES ({values})')
    # An identity column starts again where its definition says, the rows above were inserted with their ids
    cursor.execute("SELECT table_name, column_name FROM user_tab_identity_cols ORDER BY table_name")
    for table, column in cursor.fetchall():
        statements.append(f'ALTER TABLE "{table}" MODIFY ("{column}" GENERATED BY DEFAULT AS IDENTITY '
                          f'(START WITH LIMIT VALUE))')
    cursor.execute("SELECT index_name FROM user_indexes WHERE index_type <> 'LOB' AND index_name NOT IN "
                   "(SELECT index_name FROM user_constraints WHERE index_name IS NOT NULL) ORDER BY index_name")
    for (name,) in cursor.fetchall():
        statements.append(_oracle_ddl(cursor, "INDEX", name))
    cursor.execute("SELECT constraint_name FROM user_constraints WHERE constraint_type = 'R' ORDER BY constraint_name")
    for (name,) in cursor.fetchall():
        statements.append(_oracle_ddl(cursor, "REF_CONSTRAINT", name))
    connection.close()
    return statements


def generate(revision: str, version: str, engine: str, keep_database: bool) -> pathlib.Path:
    with tempfile.TemporaryDirectory(prefix="release-seed-") as temporary:
        source = pathlib.Path(temporary) / "source"
        source.mkdir()
        archive = subprocess.run(["git", "-C", str(REPOSITORY), "archive", revision], check=True,
                                 capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", str(source)], input=archive, check=True)
        commit = _run(["git", "-C", str(REPOSITORY), "rev-parse", f"{revision}^{{commit}}"]).strip()
        create_database(engine)
        try:
            run_release_code(source, write_config(pathlib.Path(temporary), engine))
            head = stamped_revision(engine)
            if engine == "postgresql":
                statements = dump_postgresql()
            elif engine == "oracle":
                statements = dump_oracle()
            else:
                statements = dump_mysql_family(engine)
            server = _server_version(engine)
        finally:
            if not keep_database:
                drop_database(engine)
    for statement in statements:
        if ";" in statement:
            raise SystemExit(f"A statement of the dump contains a semicolon, which the seed reader of the tests "
                             f"cannot split: {statement[:200]}")
    path = SEED_DIRECTORY / f"seed_v{version}_{head}_{engine}.sql"
    header = [f"-- privacyIDEA {version} (git commit {commit}), alembic revision {head}, {server}",
              "-- Generated by tools/generate_release_seed.py: \"pi-manage setup create_tables\" of the release",
              "-- created the tables, the code of the release wrote the rows. Do not edit it, generate it again.", ""]
    path.write_text("\n".join(header) + "\n".join(f"{statement};\n" for statement in statements), encoding="utf-8")
    return path


def fill() -> None:
    """
    Write the rows of the seed through the code of the release in the current directory. Runs in the interpreter
    that run_release_code starts.
    """
    import base64
    import importlib.util
    import traceback

    sys.path.insert(0, os.getcwd())
    from privacyidea.app import create_app
    import privacyidea
    if not pathlib.Path(privacyidea.__file__).resolve().is_relative_to(pathlib.Path.cwd().resolve()):
        raise SystemExit(f"The code of the release was not imported, privacyidea comes from {privacyidea.__file__}")

    app = create_app("production", config_file=os.environ["PRIVACYIDEA_CONFIGFILE"], silent=True)
    has_u2f = importlib.util.find_spec("privacyidea.lib.tokens.u2ftoken") is not None
    failed = []

    def step(name: str) -> Callable[[Callable[[], None]], Callable[[], None]]:
        def run(function: Callable[[], None]) -> Callable[[], None]:
            try:
                with app.test_request_context("/"):
                    from flask import g
                    from privacyidea.lib.audit import getAudit
                    from privacyidea.lib.config import get_config_object
                    from privacyidea.models import db
                    g.audit_object = getAudit(app.config)
                    g.config_object = get_config_object()
                    g.policy_object = None
                    function()
                    db.session.commit()
                print(f"filled: {name}")
            except Exception as exception:
                failed.append(name)
                print(f"FAILED: {name}: {exception!r}")
                traceback.print_exc()
            return function
        return run

    def ssh_key(number: int, comment: str) -> str:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
        public_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes([number]) * 32).public_key()
        key = public_key.public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH).decode()
        return f"{key} {comment}"

    @step("administrators")
    def _() -> None:
        from privacyidea.lib.auth import create_db_admin
        create_db_admin("admin", "admin@example.com", "Test1234!")
        create_db_admin("helpdesk", "helpdesk@example.com", "Test1234!")

    @step("system configuration")
    def _() -> None:
        from privacyidea.lib.config import set_privacyidea_config
        set_privacyidea_config("splitAtSign", "1")
        set_privacyidea_config("PrependPin", "True")
        set_privacyidea_config("IncFailCountOnFalsePin", "True")
        set_privacyidea_config("seed.secret.option", "hidden value", typ="password")

    @step("resolvers and realms")
    def _() -> None:
        from privacyidea.lib.realm import set_default_realm, set_realm
        from privacyidea.lib.resolver import save_resolver
        save_resolver({"resolver": "passwd1", "type": "passwdresolver", "fileName": "tests/testdata/passwords"})
        save_resolver({"resolver": "ldap1", "type": "ldapresolver", "LDAPURI": "ldap://127.0.0.1:1389",
                       "LDAPBASE": "dc=example,dc=org", "BINDDN": "cn=admin,dc=example,dc=org", "BINDPW": "admin",
                       "LOGINNAMEATTRIBUTE": "uid", "LDAPSEARCHFILTER": "(uid=*)",
                       "USERINFO": '{"username": "uid", "email": "mail", "givenname": "givenName"}',
                       "UIDTYPE": "DN", "AUTHTYPE": "Simple", "TIMEOUT": "5", "SIZELIMIT": "500",
                       "NOREFERRALS": "True", "CACHE_TIMEOUT": "120", "TLS_VERIFY": "False",
                       "type.BINDPW": "password"})
        set_realm("realm1", [{"name": "passwd1"}])
        set_realm("realm2", [{"name": "passwd1", "priority": 1}, {"name": "ldap1", "priority": 2}])
        set_default_realm("realm1")

    @step("policies")
    def _() -> None:
        from privacyidea.lib.policy import set_policy
        set_policy("admin_tokens", scope="admin", action="tokenlist, enable, disable, enrollHOTP, enrollTOTP")
        set_policy("authentication_pin", scope="authentication",
                   action="otppin=userstore, challenge_response=hotp totp", realm="realm1", priority=2,
                   description="PIN from the user store")
        set_policy("webui_login", scope="webui", action="login_mode=privacyIDEA")
        if has_u2f:
            set_policy("enrollment_u2f", scope="enrollment",
                       action="u2f_req=subject/.*Yubico.*/, u2f_no_verify_certificate, "
                              "webauthn_relying_party_id=example.com")
        set_policy("container_client", scope="container",
                   action="disable_client_token_deletion=false, initially_add_tokens_to_container=True")
        set_policy("user_tokens", scope="user", action="enrollHOTP=true, disable=false, setpin")

    @step("event handlers")
    def _() -> None:
        from privacyidea.lib.event import set_event
        set_event("notify_failed", event=["validate_check"], handlermodule="UserNotification", action="sendmail",
                  conditions={"result_value": "False", "realm": "realm1"},
                  options={"emailconfig": "smtp1", "To": "tokenowner", "body": "Failed login of {user}"})
        set_event("set_user", event=["validate_check"], handlermodule="RequestMangler", action="set",
                  options={"parameter": "user", "value": "cornelius"}, position="pre")
        set_event("remove_message", event=["validate_check"], handlermodule="ResponseMangler", action="delete",
                  options={"JSON pointer": "/detail/message"})
        set_event("count_fails", event=["validate_check"], handlermodule="Counter", action="increase_counter",
                  options={"counter_name": "fails"}, conditions={"result_value": "False"})

    @step("SMTP, RADIUS and privacyIDEA servers and SMS gateways")
    def _() -> None:
        from privacyidea.lib.privacyideaserver import add_privacyideaserver
        from privacyidea.lib.radiusserver import add_radius
        from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
        from privacyidea.lib.smtpserver import add_smtpserver
        add_smtpserver("smtp1", "mail.example.com", port=587, username="mailer", password="smtp-secret",
                       sender="privacyidea@example.com", tls=True)
        add_radius("radius1", "radius.example.com", secret="radius-secret", dictionary="/etc/privacyidea/dictionary")
        add_privacyideaserver("remote1", url="https://remote.example.com", tls=True)
        set_smsgateway("http_gateway", "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
                       options={"URL": "https://sms.example.com", "HTTP_METHOD": "POST", "USERNAME": "smsuser",
                                "PASSWORD": "gateway-password", "TEXT": "{otp}", "PHONE": "{phone}",
                                "RETURN_SUCCESS": "ID"},
                       headers={"Authorization": "Bearer header-secret"})
        set_smsgateway("smtp_gateway", "privacyidea.lib.smsprovider.SmtpSMSProvider.SmtpSMSProvider",
                       options={"SMTPIDENTIFIER": "smtp1", "MAILTO": "{phone}@sms.example.com"})

    @step("tokens")
    def _() -> None:
        from privacyidea.lib.token import add_tokeninfo, enable_token, init_token, set_realms
        from privacyidea.lib.user import User
        from privacyidea.models import Token, TokenInfo, TokenOwner, TokenRealm
        cornelius = User("cornelius", "realm1")
        hans = User("hans", "realm1")
        selfservice = User("selfservice", "realm2")
        # The key of RFC 4226, the first OTP value is 755224
        init_token({"type": "hotp", "serial": "HOTP0001", "otpkey": "3132333435363738393031323334353637383930",
                    "pin": "pin1"}, user=cornelius)
        add_tokeninfo("HOTP0001", "comment", "value with ümlaut")
        init_token({"type": "totp", "serial": "TOTP0001", "otpkey": "3132333435363738393031323334353637383930",
                    "timeStep": "30", "pin": "pin2"}, user=hans)
        init_token({"type": "spass", "serial": "SPASS001", "pin": "spasspin"}, user=selfservice)
        init_token({"type": "pw", "serial": "PW000001", "otpkey": "static-password"})
        init_token({"type": "sshkey", "serial": "SSHK0001", "sshkey": ssh_key(1, "cornelius@host")},
                   user=cornelius)
        init_token({"type": "registration", "serial": "REG00001", "registrationcode": "registration-code"},
                   user=hans)
        init_token({"type": "email", "serial": "EMAIL001", "email": "cornelius@example.com"}, user=cornelius)
        init_token({"type": "sms", "serial": "SMS00001", "phone": "+49123456"}, user=cornelius)
        init_token({"type": "indexedsecret", "serial": "IDXS0001", "otpkey": "abcdefghijklmnop"}, user=hans)
        init_token({"type": "hotp", "serial": "HOTP0002", "otpkey": "3132333435363738393031323334353637383931"},
                   user=selfservice)
        enable_token("HOTP0002", False)
        set_realms("HOTP0002", ["realm1", "realm2"], add=True)
        # Token types that need a client to enroll are written as rows
        types = [("WAN00001", "webauthn", True, ""), ("PUSH0001", "push", True, "clientwait"),
                 ("TIQR0001", "tiqr", True, "")]
        if has_u2f:
            types += [("U2F00001", "u2f", True, ""), ("U2F00002", "u2f", False, None),
                      ("U2F00003", "u2f", True, "clientwait")]
        for serial, token_type, active, rollout_state in types:
            token = Token(serial, tokentype=token_type, isactive=active)
            token.rollout_state = rollout_state
            token.save()
            TokenInfo(token.id, "tokenkind", "hardware" if token_type in ("u2f", "webauthn") else "software").save()
            if token_type in ("u2f", "webauthn"):
                TokenInfo(token.id, "pubKey", "BEj5tT3w5Q0w0q2").save()
                TokenInfo(token.id, "appId", "https://privacyidea.example.com").save()
            TokenOwner(token_id=token.id, user_id="1000", resolver="passwd1", realmname="realm1").save()
            TokenRealm(token_id=token.id, realmname="realm1").save()

    @step("custom and internal user attributes")
    def _() -> None:
        from privacyidea.lib.user import User
        cornelius = User("cornelius", "realm1")
        hans = User("hans", "realm1")
        fido2_user_id = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
        if hasattr(User, "set_internal_attribute"):
            cornelius.set_internal_attribute("fido2_user_id", fido2_user_id)
            cornelius.set_internal_attribute("last_used_token", {"privacyidea-cp": "hotp",
                                                                 "privacyidea-keycloak": "webauthn"})
            hans.set_internal_attribute("last_used_token", {"privacyidea-cp": "totp"})
        else:
            from privacyidea.lib.users.custom_user_attributes import INTERNAL_USAGE
            cornelius.set_attribute("fido2_user_id", fido2_user_id)
            cornelius.set_attribute("last_used_token_privacyidea-cp", "hotp", INTERNAL_USAGE)
            cornelius.set_attribute("last_used_token_privacyidea-keycloak", "webauthn", INTERNAL_USAGE)
            hans.set_attribute("last_used_token_privacyidea-cp", "totp", INTERNAL_USAGE)
        hans.set_attribute("department", "sales")

    @step("challenges")
    def _() -> None:
        from privacyidea.models import Challenge
        Challenge("HOTP0001", transaction_id="01234567890123456789", challenge="please enter otp",
                  data="", validitytime=600).save()
        Challenge("PUSH0001", transaction_id="98765432109876543210", challenge="nonce", data="sslverify",
                  validitytime=600).save()

    @step("audit")
    def _() -> None:
        from privacyidea.lib.audit import getAudit
        for number in range(10):
            audit = getAudit(app.config)
            audit.log({"action": "POST /validate/check", "success": bool(number % 2), "serial": "HOTP0001",
                       "user": "cornelius", "realm": "realm1", "resolver": "passwd1", "token_type": "hotp",
                       "info": f"entry {number}", "client": "10.0.0.1",
                       "authentication": "ACCEPT" if number % 2 else "REJECT"})
            audit.finalize_log()

    @step("containers, templates, token groups and service ids")
    def _() -> None:
        from privacyidea.lib.container import (add_token_to_container, create_container_template,
                                               init_container)
        from privacyidea.lib.serviceid import set_serviceid
        from privacyidea.lib.token import set_tokengroups
        from privacyidea.lib.tokengroup import set_tokengroup
        init_container({"type": "generic", "container_serial": "CONT0001", "description": "first container",
                        "user": "cornelius", "realm": "realm1"})
        add_token_to_container("CONT0001", "HOTP0001")
        init_container({"type": "smartphone", "container_serial": "SMPH0001", "description": "phone"})
        create_container_template("smartphone", "template1", {"tokens": [{"type": "hotp", "genkey": True}]},
                                  default=True)
        set_tokengroup("group1", "first group")
        set_serviceid("service1", "first service")
        set_tokengroups("TOTP0001", ["group1"])

    @step("periodic task, machine resolver and event counter")
    def _() -> None:
        from privacyidea.lib.machineresolver import save_resolver as save_machine_resolver
        from privacyidea.lib.periodictask import set_periodic_task
        from privacyidea.models import EventCounter
        set_periodic_task("statistics", "*/5 * * * *", ["seednode"], "SimpleStats", options={"total_tokens": "True"})
        save_machine_resolver({"name": "hosts1", "type": "hosts", "filename": "/etc/hosts"})
        EventCounter("fails", 3, node="seednode").save()

    if failed:
        raise SystemExit(f"Could not fill: {', '.join(failed)}")


def main() -> None:
    if sys.argv[1:] == ["fill"]:
        fill()
        return
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("revision", help="git revision of the release, e.g. v3.13.4")
    parser.add_argument("version", help="version of the release for the file name, e.g. 3.13.4")
    parser.add_argument("engine", choices=sorted(ENGINES))
    parser.add_argument("--keep-database", action="store_true", help="do not drop the database afterwards")
    arguments = parser.parse_args()
    print(generate(arguments.revision, arguments.version, arguments.engine, arguments.keep_database))


if __name__ == "__main__":
    main()
