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
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement
from privacyidea.models import db


def utc_now() -> datetime:
    """
    Return the current UTC time as a naive datetime object.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Define a function to convert Oracle CLOBs to VARCHAR before using them in a
# compare operation. (See https://docs.sqlalchemy.org/en/20/core/compiler.html)
class clob_to_varchar(FunctionElement):
    name = 'clob_to_varchar'
    inherit_cache = True


@compiles(clob_to_varchar)
def fn_clob_to_varchar_default(element, compiler, **kw):
    return compiler.process(element.clauses, **kw)


@compiles(clob_to_varchar, 'oracle')
def fn_clob_to_varchar_oracle(element, compiler, **kw):
    return f"to_char({compiler.process(element.clauses, **kw)})"


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
