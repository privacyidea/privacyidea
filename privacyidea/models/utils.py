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

from datetime import datetime, timezone

from sqlalchemy.dialects import sqlite, mysql
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.sqltypes import BigInteger, Unicode
from sqlalchemy.types import TypeDecorator, TypeEngine

from privacyidea.models import db

# SQLite cannot auto-increment a BigInteger column, so the type is declared as a variant that maps to INTEGER there.
# https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#allowing-autoincrement-behavior-sqlalchemy-types-other-than-integer-integer  # noqa: E501
BigIntegerType = BigInteger()
BigIntegerType = BigIntegerType.with_variant(sqlite.INTEGER(), "sqlite")


def utc_now() -> datetime:
    """
    Return the current UTC time as a naive datetime object.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_isoformat(value: "datetime | None") -> "str | None":
    """
    Render a naive-UTC timestamp (as produced by :func:`utc_now`) as an
    explicitly UTC-aware ISO-8601 string (``…+00:00``), or ``None``.

    Serialising a naive timestamp without a zone lets a client that assumes local
    time (e.g. the WebUI's AngularJS ``date`` filter) misread it and show a
    shifted value, so attach the UTC zone on the way out.
    """
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def case_sensitive_unicode(length: int):
    """
    A ``Unicode`` column pinned to a case-sensitive collation on MySQL/MariaDB.

    Used to match **case-sensitive by default on every backend**, giving one uniform rule: an unflagged query matches
    case-sensitively, and the ``case_insensitive`` filter flag / the ``user_case_insensitive`` policy option opt into
    case-insensitive matching via ``LOWER()``.
    This is important if you need exact matches for security operations / visibility boundaries.

    ``utf8mb4_bin`` makes equality case-sensitive on MySQL/MariaDB; SQLite, PostgreSQL and Oracle already compare
    case-sensitively by default. The migration declares the same collation on the table columns.

    ``utf8mb4_bin`` is a *binary* collation, so it is accent- and normalization-sensitive as well: ``jose`` and
    ``josé`` differ, and so do the NFC and NFD spellings of ``josé``. That is not a divergence but the point -
    equality on SQLite, PostgreSQL and Oracle is byte-wise too, while MySQL's own default (``utf8mb4_general_ci``
    and friends) is case- *and* accent-insensitive, which is the fail-open this pin exists to close. A boundary
    that has to distinguish two spellings therefore does so on every backend, and one that must treat them alike
    needs the explicit case-insensitive path rather than the collation.
    """
    return Unicode(length).with_variant(mysql.VARCHAR(length, charset="utf8mb4", collation="utf8mb4_bin"),
                                        "mysql", "mariadb")


#: What a column made by :func:`keep_empty_string_on_oracle` stores on Oracle in place of an empty string.
ORACLE_EMPTY_STRING = "\x00"


class _OracleEmptyString(TypeDecorator):
    """
    The Oracle variant of a string column that has to hold an empty string.

    Oracle stores ``''`` as NULL, so an empty string cannot be written to a NOT NULL or primary key column there,
    reads back as None and is not found by ``== ''``. This type writes :data:`ORACLE_EMPTY_STRING` instead and reads
    it back as ``''``. A compared value is converted the same way, because SQLAlchemy binds it with the column's
    type; literal SQL is not converted. The DDL is that of the wrapped type.
    """
    impl = Unicode
    cache_ok = True

    def __init__(self, column_type: TypeEngine):
        super().__init__()
        self.column_type = column_type
        self.impl = column_type

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        return ORACLE_EMPTY_STRING if value == "" else value

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        return "" if value == ORACLE_EMPTY_STRING else value


def keep_empty_string_on_oracle(column_type: TypeEngine) -> TypeEngine:
    """
    Let a string column hold ``''`` on Oracle as well, see :class:`_OracleEmptyString`. Every other database uses
    *column_type* unchanged.

    Meant for columns where the empty string is a value of its own, such as part of a key or a NOT NULL column.
    Elsewhere Oracle's NULL simply reads back as None.
    """
    return column_type.with_variant(_OracleEmptyString(column_type), "oracle")


class MethodsMixin:
    """
    This class mixes in some common Class table functions like delete and save
    """

    def save(self):
        db.session.add(self)
        db.session.commit()
        if hasattr(self, 'id'):
            return self.id
        return None

    def delete(self):
        ret = self.id if hasattr(self, 'id') else None
        db.session.delete(self)
        db.session.commit()
        return ret
