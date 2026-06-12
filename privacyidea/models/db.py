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

# Compile JSON type to CLOB for Oracle
@compiles(db.JSON, 'oracle')
def compile_json_oracle(type_, compiler, **kw):  # pragma: no cover
    return "CLOB"
