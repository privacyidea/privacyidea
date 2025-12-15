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
import logging
import traceback
from datetime import datetime
from typing import Optional

from sqlalchemy import Sequence, Unicode, Integer, DateTime, UniqueConstraint, select, update, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin

log = logging.getLogger(__name__)


class ClientApplication(MethodsMixin, db.Model):
    """
    This table stores the clients, which sent an authentication request to privacyIDEA.
    This table is filled automatically by authentication requests.
    """
    __tablename__ = 'clientapplication'
    id: Mapped[int] = mapped_column(Integer, Sequence("clientapp_seq"), primary_key=True)
    ip: Mapped[str] = mapped_column(Unicode(255), nullable=False, index=True)
    hostname: Mapped[Optional[str]] = mapped_column(Unicode(255))
    clienttype: Mapped[str] = mapped_column(Unicode(255), nullable=False, index=True)
    lastseen: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    node: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    __table_args__ = (UniqueConstraint('ip',
                                       'clienttype',
                                       'node',
                                       name='caix'),)

    def save(self):
        stmt = select(ClientApplication).filter(
            and_(
                ClientApplication.ip == self.ip,
                ClientApplication.clienttype == self.clienttype,
                ClientApplication.node == self.node
            )
        )
        clientapp = db.session.execute(stmt).scalar_one_or_none()
        self.lastseen = datetime.now()
        if clientapp is None:
            # create a new one
            db.session.add(self)
        else:
            # update
            values = {"lastseen": self.lastseen}
            if self.hostname is not None:
                values["hostname"] = self.hostname
            update_stmt = (
                update(ClientApplication)
                .where(ClientApplication.id == clientapp.id)
                .values(**values)
            )
            db.session.execute(update_stmt)
        try:
            db.session.commit()
        except IntegrityError as e:  # pragma: no cover
            log.info(f'Unable to write ClientApplication entry to db: {e}')
            log.debug(traceback.format_exc())

    def __repr__(self):
        return f"<ClientApplication [{self.id}][{self.ip}:{self.clienttype}] on {self.node}>"


class Subscription(MethodsMixin, db.Model):
    """
    This table stores the imported subscription files.
    """
    __tablename__ = 'subscription'
    id: Mapped[int] = mapped_column(Integer, Sequence("subscription_seq"), primary_key=True)
    application: Mapped[str] = mapped_column(Unicode(80), index=True)
    for_name: Mapped[str] = mapped_column(Unicode(80), nullable=False)
    for_address: Mapped[Optional[str]] = mapped_column(Unicode(128))
    for_email: Mapped[str] = mapped_column(Unicode(128), nullable=False)
    for_phone: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    for_url: Mapped[Optional[str]] = mapped_column(Unicode(80))
    for_comment: Mapped[Optional[str]] = mapped_column(Unicode(255))
    by_name: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    by_email: Mapped[str] = mapped_column(Unicode(128), nullable=False)
    by_address: Mapped[Optional[str]] = mapped_column(Unicode(128))
    by_phone: Mapped[Optional[str]] = mapped_column(Unicode(50))
    by_url: Mapped[Optional[str]] = mapped_column(Unicode(80))
    date_from: Mapped[Optional[datetime]] = mapped_column(DateTime)
    date_till: Mapped[Optional[datetime]] = mapped_column(DateTime)
    num_users: Mapped[Optional[int]] = mapped_column(Integer)
    num_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    num_clients: Mapped[Optional[int]] = mapped_column(Integer)
    level: Mapped[Optional[str]] = mapped_column(Unicode(80))
    signature: Mapped[Optional[str]] = mapped_column(Unicode(640))

    def save(self):
        stmt = select(Subscription).filter(
            Subscription.application == self.application
        )
        subscription = db.session.execute(stmt).scalar_one_or_none()
        if subscription is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            values = self.get()
            update_stmt = (
                update(Subscription)
                .where(Subscription.id == subscription.id)
                .values(**values)
            )
            db.session.execute(update_stmt)
            ret = subscription.id
        db.session.commit()
        return ret

    def __repr__(self):
        return f"<Subscription [{self.id}][{self.application}:{self.for_name}:{self.by_name}]>"

    def get(self):
        return {attr: getattr(self, attr) for attr in self.__table__.columns.keys() if getattr(self, attr) is not None}
