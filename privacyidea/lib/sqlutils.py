# -*- coding: utf-8 -*-
#  2018-10-02 Friedrich Weber <friedrich.weber@netknights.it>
#             Add chunked deletions
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

from sqlalchemy import select, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import ClauseElement, Delete


class DeleteLimit(Delete, ClauseElement):
    """
    A modified DELETE clause element that allows to specify a limit
    for the number of rows that should be deleted.

    Deleting a large number of rows via just one SQL statement
    may cause deadlocks in a replicated setup. This clause can
    be used to split the one big DELETE statement into multiple
    smaller statements ("chunks") which reduces the probability
    of deadlocks.

    A dedicated clause element is needed because different
    databases use different notation for limits on DELETE statements.
    """
    def __init__(self, table, filter, limit=1000):
        Delete.__init__(self, table)
        self.table = table
        self.filter = filter
        if not isinstance(limit, int):
            raise RuntimeError('limit must be an integer')
        if limit <= 0:
            raise RuntimeError('limit must be positive')
        self.limit = limit


@compiles(DeleteLimit)
def visit_delete_limit(element, compiler, **kw):
    """
    Default compiler for the DeleteLimit clause element.
    This compiles to a DELETE statement with a SELECT subquery which
    has a limit set::

        DELETE FROM ... WHERE id IN
        (SELECT id FROM ... WHERE ... LIMIT ...)

    However, this syntax is not supported by MySQL.
    """
    select_stmt = select([element.table.c.id]).where(element.filter).limit(element.limit)
    delete_stmt = element.table.delete().where(element.table.c.id.in_(select_stmt))
    return compiler.process(delete_stmt)


@compiles(DeleteLimit, 'mysql')
def visit_delete_limit_mysql(element, compiler, **kw):
    """
    Special compiler for the DeleteLimit clause element
    for MySQL dialects. This compiles to a DELETE element
    with a LIMIT::

        DELETE FROM pidea_audit WHERE ... LIMIT ...
    """
    return 'DELETE FROM {} WHERE {} LIMIT {:d}'.format(
        compiler.process(element.table, asfrom=True),
        compiler.process(element.filter), element.limit)


def delete_chunked(session, table, filter, limit=1000):
    """
    Delete all rows matching a given filter criterion from a table,
    but only delete *limit* rows at a time. Commit after each DELETE.

    :param session: SQLAlchemy session object
    :param table: SQLAlchemy table object (e.g. ``LogEntry.__table__``)
    :param filter: A filter criterion (e.g. ``LogEntry.age < now``)
    :param limit: Number of rows to delete in one chunk
    :return: total number of deleted rows
    """
    deleted = 0
    statement = DeleteLimit(table, filter, limit)
    while True:
        result = session.execute(statement)
        deleted += result.rowcount
        session.commit()
        if result.rowcount < limit:
            return deleted


def delete_matching_rows(session, table, filter, chunksize=None):
    """
    Delete all rows matching a given filter criterion from a table,
    using chunked deletes if *chunksize* is not None.

    :param session: session object
    :param table: table object
    :param filter: filter criterion
    :param chunksize: An integer (a chunksize), or None.
    :return: total number of deleted rows
    """
    if chunksize is None:
        result = session.execute(table.delete().where(filter))
        session.commit()
        return result.rowcount
    else:
        return delete_chunked(session, table, filter, chunksize)
