# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from typing import TYPE_CHECKING

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, Sequence, inspect, text
from sqlalchemy.dialects.oracle.base import OracleDialect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateSequence, DropSequence

if TYPE_CHECKING:
    from alembic.operations import Operations

db = SQLAlchemy()

# Add fractions to the MySQL DataTime column type
@compiles(db.DateTime, "mysql")
def compile_datetime_mysql(type_, compiler, **kw):  # pragma: no cover
    return "DATETIME(6)"

# Fix creation of sequences on MariaDB (and MySQL, which does not support
# sequences anyway) with galera by adding INCREMENT BY 0 to CREATE SEQUENCE
@compiles(CreateSequence, 'mysql')
@compiles(CreateSequence, 'mariadb')
def increment_by_zero(element, compiler, **kw):  # pragma: no cover
    text = compiler.visit_create_sequence(element, **kw)
    text = text + " INCREMENT BY 0"
    return text


def build_restart_sequence_sql(name, restart_with, dialect_name):
    """Build an ``ALTER SEQUENCE`` statement that restarts ``name`` at
    ``restart_with``, using each dialect's accepted syntax.

    SQLAlchemy has no DDL construct for ``ALTER SEQUENCE ... RESTART``, so
    migrations build the statement through this helper instead of a raw string
    that would only be correct on one backend:

    * **MariaDB/MySQL** use ``RESTART WITH n`` and additionally require
      ``INCREMENT BY 0`` — a Galera cluster otherwise rejects ``RESTART`` on a
      cached sequence with "CACHE without INCREMENT BY 0 in Galera cluster", the
      same constraint the :func:`increment_by_zero` hook handles for
      ``CREATE SEQUENCE``. (MySQL has no sequences and never reaches this path.)
    * **Oracle** (19c+) uses ``RESTART START WITH n``; ``RESTART WITH n`` is a
      syntax error there, and ``INCREMENT BY 0`` is invalid.
    * **PostgreSQL** uses plain ``RESTART WITH n``.

    ``name`` must be a trusted, code-defined sequence identifier — it is
    interpolated verbatim.
    """
    if dialect_name == "oracle":
        return f"ALTER SEQUENCE {name} RESTART START WITH {restart_with}"
    sql = f"ALTER SEQUENCE {name} RESTART WITH {restart_with}"
    if dialect_name in ("mysql", "mariadb"):
        sql += " INCREMENT BY 0"
    return sql


def build_create_sequence_ddl(sequence_name: str, dialect_name: str, start: int | None = None) -> CreateSequence:
    """Return the :class:`~sqlalchemy.schema.CreateSequence` construct that creates
    ``sequence_name``, with the ``IF NOT EXISTS`` guard only where it is understood.

    ``IF NOT EXISTS`` is a MariaDB/PostgreSQL spelling. Oracle accepts it from 23c
    on only, so on the supported 19c+ baseline it fails with "ORA-00933: SQL command
    not properly ended" — there, absence has to be established by reflection instead
    (see :func:`sequence_exists`).

    A construct rather than a raw string because it is rewritten by the
    :func:`increment_by_zero` hook, which appends ``INCREMENT BY 0`` on MariaDB so a
    Galera cluster accepts the cached sequence.
    """
    return CreateSequence(Sequence(sequence_name, start=start), if_not_exists=dialect_name != "oracle")


def build_drop_sequence_ddl(sequence_name: str, dialect_name: str) -> DropSequence:
    """Return the :class:`~sqlalchemy.schema.DropSequence` construct that drops
    ``sequence_name``, with the ``IF EXISTS`` guard only where it is understood.

    The Oracle counterpart of :func:`build_create_sequence_ddl`: ``DROP SEQUENCE IF
    EXISTS`` is equally 23c-only, so on 19c+ the sequence has to be reflected first.
    """
    return DropSequence(Sequence(sequence_name), if_exists=dialect_name != "oracle")


def sequence_exists(bind: Connection, sequence_name: str) -> bool:  # pragma: no cover
    """Return True if ``sequence_name`` already exists in the database ``bind``
    is connected to.

    Oracle folds unquoted identifiers to upper case and reflects them that way,
    so the comparison is case-insensitive.
    """
    existing = {name.lower() for name in inspect(bind).get_sequence_names()}
    return sequence_name.lower() in existing


def create_sequence_if_supported(op: "Operations", sequence_name: str,
                                 start: int | None = None) -> None:  # pragma: no cover
    """Create ``sequence_name`` on backends that support sequences (PostgreSQL,
    MariaDB 10.3+, Oracle); a no-op elsewhere. Safe to re-run.

    On Oracle the sequence is reflected first because it has no ``IF NOT EXISTS``
    guard to lean on; see :func:`build_create_sequence_ddl`.

    Pairs with :func:`sequence_id_column`, :func:`restart_sequence_past_max` and
    :func:`drop_sequence_if_supported` so migrations adding a sequence-backed table
    do not each re-implement the cross-dialect dance.
    """
    bind = op.get_bind()
    if not bind.dialect.supports_sequences:
        return
    if bind.dialect.name == "oracle" and sequence_exists(bind, sequence_name):
        return
    op.execute(build_create_sequence_ddl(sequence_name, bind.dialect.name, start=start))


def drop_sequence_if_supported(op: "Operations", sequence_name: str) -> None:  # pragma: no cover
    """Drop ``sequence_name`` on backends that support sequences; a no-op elsewhere.
    Safe to re-run. The :func:`create_sequence_if_supported` counterpart for
    ``downgrade()``.
    """
    bind = op.get_bind()
    if not bind.dialect.supports_sequences:
        return
    if bind.dialect.name == "oracle" and not sequence_exists(bind, sequence_name):
        return
    op.execute(build_drop_sequence_ddl(sequence_name, bind.dialect.name))


def sequence_id_column(op, sequence_name):  # pragma: no cover
    """Return the primary-key ``id`` :class:`~sqlalchemy.Column` for a table
    backed by ``sequence_name``.

    On PostgreSQL and Oracle the column default is wired to the sequence so raw
    INSERTs (e.g. a data migration) still get an id — neither derives one from
    ``autoincrement`` alone, and on Oracle the insert would otherwise fail with
    "ORA-01400: cannot insert NULL into". MariaDB/MySQL use plain
    ``autoincrement``. Pass the result into :func:`alembic.op.create_table`.

    ``sequence_name`` must be a trusted, code-defined identifier — it is
    interpolated verbatim.
    """
    dialect_name = op.get_bind().dialect.name
    if dialect_name == "postgresql":
        return Column('id', Integer(), nullable=False,
                      server_default=text(f"nextval('{sequence_name}')"))
    if dialect_name == "oracle":
        return Column('id', Integer(), nullable=False,
                      server_default=text(f"{sequence_name}.nextval"))
    return Column('id', Integer(), nullable=False, autoincrement=True)


def restart_sequence_past_max(op, table_name, sequence_name):  # pragma: no cover
    """Advance ``sequence_name`` past ``MAX(id)`` in ``table_name`` on backends
    that support sequences; a no-op elsewhere.

    Covers the table-already-exists case where the sequence (newly created or
    pre-existing) would otherwise hand out a value ``<= MAX(id)`` and cause a
    duplicate-PK error on the next insert. Uses :func:`build_restart_sequence_sql`
    so MariaDB gets the Galera-required ``INCREMENT BY 0``.

    ``table_name`` and ``sequence_name`` must be trusted, code-defined
    identifiers — they are interpolated verbatim.
    """
    bind = op.get_bind()
    if bind.dialect.supports_sequences:
        max_id = bind.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")).scalar() or 0
        op.execute(build_restart_sequence_sql(sequence_name, max_id + 1, bind.dialect.name))


# Compile JSON type to CLOB for Oracle
@compiles(db.JSON, 'oracle')
def compile_json_oracle(type_, compiler, **kw):  # pragma: no cover
    return "CLOB"


# The hook above only settles the column type. SQLAlchemy's Oracle dialect implements
# no generic JSON support at all, so unlike every JSON-capable dialect it never sets
# the _json_serializer/_json_deserializer attributes that sqlalchemy.types.JSON reads
# when binding and fetching a value — writing to a JSON column raises
# "AttributeError: 'OracleDialect_oracledb' object has no attribute _json_serializer".
# Providing them as None selects the type's own json.dumps/json.loads fallback, which
# is exactly what the CLOB column needs. Guarded so a future SQLAlchemy that does
# support JSON on Oracle keeps its own implementation.
if not hasattr(OracleDialect, "_json_serializer"):
    OracleDialect._json_serializer = None
    OracleDialect._json_deserializer = None
