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

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, Sequence, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateSequence

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

def create_sequence_if_supported(op, sequence_name):  # pragma: no cover
    """Emit ``CREATE SEQUENCE <sequence_name> IF NOT EXISTS`` on backends that
    support sequences (PostgreSQL, MariaDB 10.3+); a no-op elsewhere.

    Built through SQLAlchemy's :class:`CreateSequence` construct so the
    :func:`increment_by_zero` hook can append ``INCREMENT BY 0`` on MariaDB (a
    raw ``CREATE SEQUENCE`` string would bypass it and fail in a Galera cluster).

    Pairs with :func:`sequence_id_column` and :func:`restart_sequence_past_max`
    so migrations adding a sequence-backed table do not each re-implement the
    cross-dialect dance.
    """
    bind = op.get_bind()
    if bind.dialect.supports_sequences:
        op.execute(CreateSequence(Sequence(sequence_name), if_not_exists=True))


def sequence_id_column(op, sequence_name):  # pragma: no cover
    """Return the primary-key ``id`` :class:`~sqlalchemy.Column` for a table
    backed by ``sequence_name``.

    On PostgreSQL the column default is wired to ``nextval(...)`` so raw INSERTs
    (e.g. a data migration) still get an id; other backends use plain
    ``autoincrement``. Pass the result into :func:`alembic.op.create_table`.
    """
    if op.get_bind().dialect.name == "postgresql":
        return Column('id', Integer(), nullable=False,
                      server_default=text(f"nextval('{sequence_name}')"))
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
