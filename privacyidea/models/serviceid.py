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
from sqlalchemy import Sequence

from privacyidea.lib.log import log_with
from privacyidea.models import db

from privacyidea.models.config import TimestampMethodsMixin

log = logging.getLogger(__name__)


class Serviceid(TimestampMethodsMixin, db.Model):
    """
    The serviceid table contains the defined service IDs. These service ID
    describe services like "webservers" or "dbservers" which e.g. request SSH keys
    from the privacyIDEA system.
    """
    __tablename__ = 'serviceid'
    id = db.Column(db.Integer, Sequence("serviceid_seq"), primary_key=True,
                   nullable=False)
    name = db.Column(db.Unicode(255), default='',
                     unique=True, nullable=False)
    Description = db.Column(db.Unicode(2000), default='')

    @log_with(log)
    def __init__(self, servicename, description=None):
        self.name = servicename
        self.Description = description

    def save(self):
        si = Serviceid.query.filter_by(name=self.name).first()
        if si is None:
            return TimestampMethodsMixin.save(self)
        else:
            # update
            Serviceid.query.filter_by(id=si.id).update({'Description': self.Description})
            ret = si.id
            db.session.commit()
        return ret
