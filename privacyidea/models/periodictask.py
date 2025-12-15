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

from datetime import datetime
from typing import Optional

from dateutil.tz import tzutc
from sqlalchemy import Sequence, Integer, Unicode, Boolean, DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.testing.schema import mapped_column

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin
from privacyidea.lib.utils import convert_column_to_unicode


class PeriodicTask(MethodsMixin, db.Model):
    """
    This class stores tasks that should be run periodically.
    """
    __tablename__ = 'periodictask'
    id: Mapped[int] = mapped_column(Integer, Sequence("periodictask_seq"), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(64), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    retry_if_failed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    interval: Mapped[str] = mapped_column(Unicode(256), nullable=False)
    nodes: Mapped[str] = mapped_column(Unicode(256), nullable=False)
    taskmodule: Mapped[str] = mapped_column(Unicode(256), nullable=False)
    ordering: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    options = db.relationship('PeriodicTaskOption', lazy='dynamic', backref='periodictask')
    last_runs = db.relationship('PeriodicTaskLastRun', lazy='dynamic', backref='periodictask')

    def __init__(self, name, active, interval, node_list, taskmodule, ordering, options=None, id=None,
                 retry_if_failed=True):
        """
        :param name: Unique name of the periodic task as Unicode
        :param active: a boolean
        :param retry_if_failed:
        :param interval: a Unicode specifying the periodicity of the task
        :param node_list: a list of unicodes, denoting the node names that should execute that task.
                          If we update an existing PeriodicTask entry, PeriodicTaskLastRun entries
                          referring to nodes that are not present in ``node_list`` anymore will be deleted.
        :param taskmodule: a Unicode
        :param ordering: an integer. Lower tasks are executed first.
        :param options: a dictionary of options, mapping Unicode keys to values. Values will be converted to Unicode.
                        If we update an existing PeriodicTask entry, all options that have been set previously
                        but are not present in ``options`` will be deleted.
        :param id: the ID of an existing entry, if any
        """
        self.id = id
        self.name = name
        self.active = active
        self.retry_if_failed = retry_if_failed
        self.interval = interval
        self.nodes = ", ".join(node_list)
        self.taskmodule = taskmodule
        self.ordering = ordering
        self.save()
        # add the options to the periodic task
        options = options or {}
        for k, v in options.items():
            PeriodicTaskOption(periodictask_id=self.id, key=k, value=v)
        # remove all leftover options
        all_options = PeriodicTaskOption.query.filter_by(periodictask_id=self.id).all()
        for option in all_options:
            if option.key not in options:
                PeriodicTaskOption.query.filter_by(id=option.id).delete()
        # remove all leftover last_runs
        all_last_runs = PeriodicTaskLastRun.query.filter_by(periodictask_id=self.id).all()
        for last_run in all_last_runs:
            if last_run.node not in node_list:
                PeriodicTaskLastRun.query.filter_by(id=last_run.id).delete()
        db.session.commit()

    @property
    def aware_last_update(self):
        """
        Return self.last_update with attached UTC tzinfo
        """
        return self.last_update.replace(tzinfo=tzutc())

    def get(self):
        """
        Return the serialized periodic task object including the options and last runs.
        The last runs are returned as timezone-aware UTC datetimes.

        :return: complete dict
        """
        return {"id": self.id,
                "name": self.name,
                "active": self.active,
                "interval": self.interval,
                "nodes": [node.strip() for node in self.nodes.split(",")],
                "taskmodule": self.taskmodule,
                "retry_if_failed": self.retry_if_failed,
                "last_update": self.aware_last_update,
                "ordering": self.ordering,
                "options": dict((option.key, option.value) for option in self.options),
                "last_runs": dict((last_run.node, last_run.aware_timestamp) for last_run in self.last_runs)}

    def save(self):
        """
        If the entry has an ID set, update the entry. If not, create one.
        Set ``last_update`` to the current time.

        :return: the entry ID
        """
        self.last_update = datetime.utcnow()
        if self.id is None:
            # create a new one
            db.session.add(self)
        else:
            # update
            PeriodicTask.query.filter_by(id=self.id).update({
                "name": self.name,
                "active": self.active,
                "interval": self.interval,
                "nodes": self.nodes,
                "taskmodule": self.taskmodule,
                "ordering": self.ordering,
                "retry_if_failed": self.retry_if_failed,
                "last_update": self.last_update,
            })
        db.session.commit()
        return self.id

    def delete(self):
        ret = self.id
        # delete all PeriodicTaskOptions and PeriodicTaskLastRuns before deleting myself
        db.session.query(PeriodicTaskOption).filter_by(periodictask_id=ret).delete()
        db.session.query(PeriodicTaskLastRun).filter_by(periodictask_id=ret).delete()
        db.session.delete(self)
        db.session.commit()
        return ret

    def set_last_run(self, node, timestamp):
        """
        Store the information that the last run of the periodic job occurred on ``node`` at ``timestamp``.

        :param node: Node name as a string
        :param timestamp: Timestamp as UTC datetime (without timezone information)
        :return:
        """
        PeriodicTaskLastRun(self.id, node, timestamp)


class PeriodicTaskOption(db.Model):
    """
    Each PeriodicTask entry can have additional options according to the
    task module.
    """
    __tablename__ = 'periodictaskoption'
    id: Mapped[int] = mapped_column(Integer, Sequence("periodictaskopt_seq"), primary_key=True)
    periodictask_id: Mapped[Optional[int]] = mapped_column(Integer, db.ForeignKey('periodictask.id'))
    key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')

    __table_args__ = (db.UniqueConstraint('periodictask_id',
                                          'key',
                                          name='ptoix_1'),)

    def __init__(self, periodictask_id, key, value):
        self.periodictask_id = periodictask_id
        self.key = key
        self.value = convert_column_to_unicode(value)
        self.save()

    def save(self):
        """
        Create or update a PeriodicTaskOption entry, depending on the value of ``self.id``

        :return: the entry ID
        """
        option = PeriodicTaskOption.query.filter_by(
            periodictask_id=self.periodictask_id, key=self.key
        ).first()
        if option is None:
            # create a new one
            db.session.add(self)
            ret = self.id
        else:
            # update
            PeriodicTaskOption.query.filter_by(periodictask_id=self.periodictask_id, key=self.key).update({
                'value': self.value,
            })
            ret = option.id
        db.session.commit()
        return ret


class PeriodicTaskLastRun(db.Model):
    """
    Each PeriodicTask entry stores, for each node, the timestamp of the last successful run.
    """
    __tablename__ = 'periodictasklastrun'
    id: Mapped[int] = mapped_column(Integer, Sequence("periodictasklastrun_seq"), primary_key=True)
    periodictask_id: Mapped[Optional[int]] = mapped_column(Integer, db.ForeignKey('periodictask.id'))
    node: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    __table_args__ = (db.UniqueConstraint('periodictask_id',
                                          'node',
                                          name='ptlrix_1'),)

    def __init__(self, periodictask_id, node, timestamp):
        """
        :param periodictask_id: ID of the periodic task we are referring to
        :param node: Node name as unicode
        :param timestamp: Time of the last run as a datetime. A timezone must not be set!
                          We require the time to be given in UTC.
        """
        self.periodictask_id = periodictask_id
        self.node = node
        self.timestamp = timestamp
        self.save()

    @property
    def aware_timestamp(self):
        """
        Return self.timestamp with attached UTC tzinfo
        """
        return self.timestamp.replace(tzinfo=tzutc())

    def save(self):
        """
        Create or update a PeriodicTaskLastRun entry, depending on the value of ``self.id``.

        :return: the entry id
        """
        last_run = PeriodicTaskLastRun.query.filter_by(
            periodictask_id=self.periodictask_id, node=self.node,
        ).first()
        if last_run is None:
            # create a new one
            db.session.add(self)
            ret = self.id
        else:
            # update
            PeriodicTaskLastRun.query.filter_by(periodictask_id=self.periodictask_id, node=self.node).update({
                'timestamp': self.timestamp,
            })
            ret = last_run.id
        db.session.commit()
        return ret
