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

from sqlalchemy import Sequence

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin


class MonitoringStats(MethodsMixin, db.Model):
    """
    This is the table that stores measured, arbitrary statistic points in time.

    This could be used to store time series but also to store current values,
    by simply fetching the last value from the database.
    """
    __tablename__ = 'monitoringstats'
    id = db.Column(db.Integer, Sequence("monitoringstats_seq"),
                   primary_key=True)
    # We store this as a naive datetime in UTC
    timestamp = db.Column(db.DateTime(False), nullable=False, index=True)
    stats_key = db.Column(db.Unicode(128), nullable=False)
    stats_value = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (db.UniqueConstraint('timestamp',
                                          'stats_key',
                                          name='msix_1'),)

    def __init__(self, timestamp, key, value):
        """
        Create a new database entry in the monitoring stats table
        :param timestamp: The time of the measurement point
        :type timestamp: timezone-naive datetime
        :param key: The key of the measurement
        :type key: basestring
        :param value: The value of the measurement
        :type value: Int
        """
        self.timestamp = timestamp
        self.stats_key = key
        self.stats_value = value
        # self.save()
