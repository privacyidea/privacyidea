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

from typing import Final

from privacyidea.models import db


# Constants for string column lengths
class ColumnLengths:
    __slots__ = ()

    class Audit:
        __slots__ = ()
        ACTION: Final[int] = 100
        SIGNATURE: Final[int] = 620

    class Realm:
        __slots__ = ()
        NAME: Final[int] = 255

    class Resolver:
        __slots__ = ()
        NAME: Final[int] = 255
        RTYPE: Final[int] = 255

    class Token:
        __slots__ = ()
        TOKENTYPE: Final[int] = 30
        DESCRIPTION: Final[int] = 80
        SERIAL: Final[int] = 40

    class TokenContainer:
        __slots__ = ()
        TYPE: Final[int] = 100
        DESCRIPTION: Final[int] = 1024
        SERIAL: Final[int] = 40


class MethodsMixin(object):
    """
    This class mixes in some common Class table functions like
    delete and save
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
