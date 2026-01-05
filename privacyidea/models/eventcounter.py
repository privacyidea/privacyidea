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
from typing import Optional

from sqlalchemy import (
    Sequence,
    Unicode,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db


class EventCounter(db.Model):
    """
    This table stores counters of the event handler "Counter".

    Note that an event counter name does *not* correspond to just one,
    but rather *several* table rows, because we store event counters
    for each privacyIDEA node separately.
    This is intended to improve the performance of replicated setups,
    because each privacyIDEA node then only writes to its own "private"
    table row. This way, we avoid locking issues that would occur
    if all nodes write to the same table row.
    """
    __tablename__ = 'eventcounter'
    id: Mapped[int] = mapped_column(Integer, Sequence("eventcounter_seq"), primary_key=True)
    counter_name: Mapped[str] = mapped_column(Unicode(80), nullable=False)
    counter_value: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    node: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    __table_args__ = (UniqueConstraint('counter_name', 'node', name='evctr_1'),)

    def __init__(self, name, value=0, node=""):
        self.counter_value = value
        self.counter_name = name
        self.node = node

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        ret = self.counter_name
        db.session.delete(self)
        db.session.commit()
        return ret

    def increase(self):
        self.counter_value = self.counter_value + 1

    def decrease(self):
        self.counter_value = self.counter_value - 1
