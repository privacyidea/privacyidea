"""v3.14: Add authentication log table

Revision ID: 0147d78cbace
Revises: b8c9d0e1f2a3
Create Date: 2026-06-01 08:37:51.884173

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql, oracle
from sqlalchemy.exc import OperationalError, ProgrammingError

# Same type the model uses: BigInteger everywhere, but INTEGER on SQLite so the
# primary key becomes "INTEGER PRIMARY KEY" and SQLite auto-assigns it via rowid.
from privacyidea.models.utils import BigIntegerType

# revision identifiers, used by Alembic.
revision = '0147d78cbace'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None

INDEXES = {
    'authentication_log': [
        ('ix_authlog_user_event_time', ['resolver', 'uid', 'realm', 'event_type', 'timestamp']),
        ('ix_authlog_ip_event_time', ['source_ip', 'event_type', 'timestamp']),
        # Serves PER_ATTEMPT counting (count_subject_attempts / count_ip_attempts): a subject's rows range-scanned
        # by time, no event_type predicate.
        ('ix_authlog_user_time', ['resolver', 'uid', 'realm', 'timestamp']),
        # The subject index for a local database admin, who has no resolver, uid or realm: their rows carry only
        # the login name, and the role is what separates them from a same-named user's. Both conditional-access
        # counts key on that pair, so without this every failed local-admin login scans the table.
        ('ix_authlog_admin_event_time', ['username', 'user_role', 'event_type', 'timestamp']),
        ('ix_authlog_ip_time', ['source_ip', 'timestamp']),
        # The TCP peer is the second pivot a forensic query starts from - "what came from this machine",
        # whatever it claimed to be forwarding for.
        ('ix_authlog_peer_ip_time', ['peer_ip', 'timestamp']),
        # The one index not scoped to a subject: the statistics query and the retention delete both range over
        # timestamp alone, and the indexes above cannot serve that.
        ('ix_authlog_time', ['timestamp']),
    ],
    'authentication_log_reason': [
        # The lookup that loads a log page's reasons and the one the delete paths use to remove an entry's
        # reasons with it.
        ('ix_authlog_reason_authlog', ['auth_log_id']),
        # The filter "every entry with this reason": reason first, so the EXISTS that matches it seeks rather than
        # scans, with auth_log_id alongside so it is answered from the index.
        ('ix_authlog_reason_reason', ['reason', 'auth_log_id']),
    ],
}


def _unicode_case_sensitive(length):
    """
    A case-sensitive string column type (mirrors models.utils.case_sensitive_unicode).

    On MySQL/MariaDB the server-default collation is typically case-insensitive (*_ci), which would make the
    authentication-log visibility boundary (realm/resolver/username) match case-insensitively -- a fail-open
    authorization risk. Pinning to utf8mb4_bin makes matching case-sensitive; SQLite, PostgreSQL and Oracle already
    compare case-sensitively by default.
    Kept self-contained here (not imported from the model) so the migration stays a stable snapshot.
    """
    return sa.Unicode(length).with_variant(mysql.VARCHAR(length, charset="utf8mb4", collation="utf8mb4_bin"),
                                           "mysql", "mariadb")


def _existing_tables() -> set[str]:
    """
    The names of the tables that already exist, lower-cased.

    Reflected once per migration rather than once per table: on a normal run nothing exists yet, so this
    single catalog read is all the guard below costs. Lower-cased because Oracle folds unquoted identifiers
    to upper case and the inspector reflects them back lower-cased (mirrors models.db.sequence_exists).
    """
    return {name.lower() for name in sa.inspect(op.get_bind()).get_table_names()}


def _create_table(existing_tables: set[str], table_name: str, *columns) -> None:
    """
    Create the table unless it is already there, then add each of its INDEXES that is absent.

    Presence is established by reflection rather than by swallowing an "already exists" error, which Oracle
    never says: it reports an existing object as ORA-00955 ("name is already used by an existing object").
    models.db.sequence_exists reflects for the same reason.

    The indexes are created by statements of their own and are deliberately not declared inline in the
    CREATE TABLE: every statement here autocommits (see migrations/env.py), so a run that created the table
    and then failed would leave the table behind, and a guard that keyed the indexes off the table's absence
    would skip them for good once Alembic stamped the revision. These indexes in particular are what keeps
    the conditional-access counting queries (engine._policy_count / _policy_count_ip) off a full table scan
    on every single authentication.
    """
    if table_name.lower() in existing_tables:
        print(f"Table '{table_name}' already exists.")
        existing_indexes = {(index["name"] or "").lower()
                            for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    else:
        op.create_table(table_name, *columns)
        existing_indexes = set()

    for index_name, index_columns in INDEXES.get(table_name, ()):
        if index_name.lower() in existing_indexes:
            print(f"Index '{index_name}' already exists.")
        else:
            op.create_index(index_name, table_name, index_columns)


def upgrade():
    existing_tables = _existing_tables()

    # The column lengths must match privacyidea.models.authentication_log.authentication_log_column_length.
    # The columns in the composite index below (resolver, uid, realm, event_type) are kept small enough that the
    # index stays below the 3072-byte InnoDB key limit of MySQL/MariaDB with utf8mb4:
    # (120+320+255+40)*4 + 8 (timestamp) = 2948 bytes. The non-indexed columns (client_label, serial) are sized
    # generously to avoid truncation. transaction_id matches the challenge table's 64 chars, and endpoint is sized
    # past the longest route privacyIDEA registers.
    _create_table(
        existing_tables,
        'authentication_log',
        sa.Column('id', BigIntegerType, sa.Identity(always=False), nullable=False),
        sa.Column('resolver', _unicode_case_sensitive(120), nullable=True),
        sa.Column('uid', _unicode_case_sensitive(320), nullable=True),
        sa.Column('realm', _unicode_case_sensitive(255), nullable=True),
        sa.Column('username', _unicode_case_sensitive(255), nullable=True),
        sa.Column('user_role', _unicode_case_sensitive(30), nullable=True),
        sa.Column('event_type', _unicode_case_sensitive(40), nullable=False),
        # Microseconds on every backend, because the attempt reduction in lib.conditional_access.engine orders
        # an attempt's rows by (timestamp, id).
        sa.Column('timestamp',
                  sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql", "mariadb")
                  .with_variant(oracle.TIMESTAMP(), "oracle"),
                  nullable=False),
        sa.Column('source_ip', _unicode_case_sensitive(50), nullable=True),
        sa.Column('peer_ip', _unicode_case_sensitive(50), nullable=True),
        sa.Column('source_ip_source', _unicode_case_sensitive(40), nullable=True),
        sa.Column('client_label', _unicode_case_sensitive(1024), nullable=True),
        sa.Column('client_label_source', _unicode_case_sensitive(40), nullable=True),
        sa.Column('ip_chain', sa.JSON(), nullable=True),
        sa.Column('endpoint', _unicode_case_sensitive(255), nullable=True),
        sa.Column('serial', _unicode_case_sensitive(1024), nullable=True),
        sa.Column('transaction_id', _unicode_case_sensitive(64), nullable=True),
        sa.Column('attempt_id', _unicode_case_sensitive(64), nullable=True),
        sa.Column('other_info', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Why an authentication rarely fails for exactly one reason is on AuthenticationLogReason itself. A table of
    # its own rather than a column on the parent: "every NO_USABLE_TOKEN caused by the failcounter" has to be a
    # plain indexed predicate, and a request can produce more than one reason.
    _create_table(
        existing_tables,
        'authentication_log_reason',
        sa.Column('id', BigIntegerType, sa.Identity(always=False), nullable=False),
        sa.Column('auth_log_id', BigIntegerType, nullable=False),
        sa.Column('reason', _unicode_case_sensitive(40), nullable=False),
        sa.ForeignKeyConstraint(['auth_log_id'], ['authentication_log.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    # Children before parents because of the foreign key. The indexes and identities go with their table.
    for table_name in ['authentication_log_reason', 'authentication_log']:
        try:
            op.drop_table(table_name)
        except (OperationalError, ProgrammingError) as ex:
            msg = str(ex.orig).lower()
            if "no such table" in msg or "unknown table" in msg or "does not exist" in msg:
                print(f"Table '{table_name}' already removed.")
            else:
                print(f"Could not remove table '{table_name}'.")
                raise
