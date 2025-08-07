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

from sqlalchemy import Sequence
from sqlalchemy.exc import IntegrityError

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin

log = logging.getLogger(__name__)


class ClientApplication(MethodsMixin, db.Model):
    """
    This table stores the clients, which sent an authentication request to
    privacyIDEA.
    This table is filled automatically by authentication requests.
    """
    __tablename__ = 'clientapplication'
    id = db.Column(db.Integer, Sequence("clientapp_seq"), primary_key=True)
    ip = db.Column(db.Unicode(255), nullable=False, index=True)
    hostname = db.Column(db.Unicode(255))
    clienttype = db.Column(db.Unicode(255), nullable=False, index=True)
    lastseen = db.Column(db.DateTime, index=True, default=datetime.utcnow())
    node = db.Column(db.Unicode(255), nullable=False)
    __table_args__ = (db.UniqueConstraint('ip',
                                          'clienttype',
                                          'node',
                                          name='caix'),)

    def save(self):
        clientapp = ClientApplication.query.filter(
            ClientApplication.ip == self.ip,
            ClientApplication.clienttype == self.clienttype,
            ClientApplication.node == self.node).first()
        self.lastseen = datetime.now()
        if clientapp is None:
            # create a new one
            db.session.add(self)
        else:
            # update
            values = {"lastseen": self.lastseen}
            if self.hostname is not None:
                values["hostname"] = self.hostname
            ClientApplication.query.filter(ClientApplication.id == clientapp.id).update(values)
        try:
            db.session.commit()
        except IntegrityError as e:  # pragma: no cover
            log.info('Unable to write ClientApplication entry to db: {0!s}'.format(e))
            log.debug(traceback.format_exc())

    def __repr__(self):
        return "<ClientApplication [{0!s}][{1!s}:{2!s}] on {3!s}>".format(
            self.id, self.ip, self.clienttype, self.node)


class Subscription(MethodsMixin, db.Model):
    """
    This table stores the imported subscription files.
    """
    __tablename__ = 'subscription'
    id = db.Column(db.Integer, Sequence("subscription_seq"), primary_key=True)
    application = db.Column(db.Unicode(80), index=True)
    for_name = db.Column(db.Unicode(80), nullable=False)
    for_address = db.Column(db.Unicode(128))
    for_email = db.Column(db.Unicode(128), nullable=False)
    for_phone = db.Column(db.Unicode(50), nullable=False)
    for_url = db.Column(db.Unicode(80))
    for_comment = db.Column(db.Unicode(255))
    by_name = db.Column(db.Unicode(50), nullable=False)
    by_email = db.Column(db.Unicode(128), nullable=False)
    by_address = db.Column(db.Unicode(128))
    by_phone = db.Column(db.Unicode(50))
    by_url = db.Column(db.Unicode(80))
    date_from = db.Column(db.DateTime)
    date_till = db.Column(db.DateTime)
    num_users = db.Column(db.Integer)
    num_tokens = db.Column(db.Integer)
    num_clients = db.Column(db.Integer)
    level = db.Column(db.Unicode(80))
    signature = db.Column(db.Unicode(640))

    def save(self):
        subscription = Subscription.query.filter(
            Subscription.application == self.application).first()
        if subscription is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            values = self.get()
            Subscription.query.filter(
                Subscription.id == subscription.id).update(values)
            ret = subscription.id
        db.session.commit()
        return ret

    def __repr__(self):
        return "<Subscription [{0!s}][{1!s}:{2!s}:{3!s}]>".format(
            self.id, self.application, self.for_name, self.by_name)

    def get(self):
        """
        Return the database object as dict
        :return:
        """
        d = {}
        for attr in Subscription.__table__.columns.keys():
            if getattr(self, attr) is not None:
                d[attr] = getattr(self, attr)
        return d
