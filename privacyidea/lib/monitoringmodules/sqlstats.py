#  2018-11-22 Initial create
#             Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
__doc__ = """This module writes statistics data to the SQL database table "monitoringstats".
"""
import logging
from privacyidea.lib.monitoringmodules.base import Monitoring as MonitoringBase
from privacyidea.lib.pooling import get_engine, engines_are_shared
from privacyidea.lib.framework import is_request_context
from privacyidea.lib.utils import censor_connect_string, convert_timestamp_to_utc
from privacyidea.lib.lifecycle import register_finalizer
from sqlalchemy import MetaData, delete, select, distinct
from sqlalchemy import and_
from privacyidea.models import MonitoringStats
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import traceback
from dateutil.tz import tzutc

log = logging.getLogger(__name__)

metadata = MetaData()


class Monitoring(MonitoringBase):

    def __init__(self, config=None):
        self.name = "sqlstats"
        self.config = config or {}
        self.engine = get_engine(self.name, self._create_engine)
        # A shared engine is still in use elsewhere when this request ends, so only an engine
        # this object has to itself may have its connections closed on teardown.
        self._owns_engine = not engines_are_shared()
        # create a configured "Session" class. ``scoped_session`` is not
        # necessary because we do not share session objects among threads.
        # We use it anyway as a safety measure.
        Session = scoped_session(sessionmaker(bind=self.engine))
        self.session = Session()
        # Ensure that the connection gets returned to the pool when the request has
        # been handled. This may close an already-closed session, but this is not a problem.
        # Outside a request (pi-manage, a cron job, a background thread) nothing tears the
        # application context down, so a finalizer registered there would never run and would
        # only keep this object - and with it an open database connection - alive for the
        # lifetime of the process.
        if is_request_context():
            register_finalizer(self._finalize_session)
        self.session._model_changes = {}

    def _finalize_session(self) -> None:
        """Close the current session and, if the engine is this object's alone, its
        connections too."""
        self.session.close()
        if self._owns_engine:
            self.engine.dispose()

    def _create_engine(self):
        """
        :return: a new SQLAlchemy engine connecting to the database specified in PI_MONITORING_SQL_URI.
        """
        # an Engine, which the Session will use for connection
        # resources
        connect_string = self.config.get("PI_MONITORING_SQL_URI", self.config.get(
            "SQLALCHEMY_DATABASE_URI"))
        log.debug(f"using the connect string {censor_connect_string(connect_string)!s}")
        try:
            pool_size = self.config.get("PI_MONITORING_POOL_SIZE", 20)
            engine = create_engine(
                connect_string,
                pool_size=pool_size,
                pool_recycle=self.config.get("PI_MONITORING_POOL_RECYCLE", 600))
            log.debug(f"Using SQL pool size of {pool_size}")
        except TypeError:
            # SQLite does not support pool_size
            engine = create_engine(connect_string)
            log.debug("Using no SQL pool_size.")
        return engine

    def add_value(self, stats_key, stats_value, timestamp, reset_values=False):
        utc_timestamp = convert_timestamp_to_utc(timestamp)
        try:
            ms = MonitoringStats(utc_timestamp, stats_key, stats_value)
            self.session.add(ms)
            self.session.commit()
            if reset_values:
                # Successfully saved the new stats entry, so remove old entries
                delete_stmt = delete(MonitoringStats).where(MonitoringStats.stats_key == stats_key,
                                                            MonitoringStats.timestamp < utc_timestamp)
                self.session.execute(delete_stmt)
                self.session.commit()
        except Exception as exx:  # pragma: no cover
            log.error(f"exception {exx!r}")
            log.error(f"DATA: {stats_key!s} -> {stats_value!s}")
            log.debug(f"{traceback.format_exc()!s}")
            self.session.rollback()

        finally:
            self.session.close()

    def delete(self, stats_key, start_timestamp, end_timestamp):
        r = None
        conditions = [MonitoringStats.stats_key == stats_key]
        if start_timestamp:
            utc_start_timestamp = convert_timestamp_to_utc(start_timestamp)
            conditions.append(MonitoringStats.timestamp >= utc_start_timestamp)
        if end_timestamp:
            utc_end_timestamp = convert_timestamp_to_utc(end_timestamp)
            conditions.append(MonitoringStats.timestamp <= utc_end_timestamp)
        try:
            delete_stmt = delete(MonitoringStats).where(and_(*conditions))
            result = self.session.execute(delete_stmt)
            r = result.rowcount
            self.session.commit()
        except Exception as exx:  # pragma: no cover
            log.error(f"exception {exx!r}")
            log.error(f"could not delete statskeys {stats_key!s}")
            log.debug(f"{traceback.format_exc()!s}")
            self.session.rollback()

        finally:
            self.session.close()

        return r

    def get_keys(self):
        """
        Return a list of all stored keys.
        :return:
        """
        keys = []
        try:
            stmt = select(distinct(MonitoringStats.stats_key))
            monitoring_stats_keys = self.session.scalars(stmt).all()
            for stat_key in monitoring_stats_keys:
                keys.append(stat_key)
        except Exception as exx:  # pragma: no cover
            log.error(f"exception {exx!r}")
            log.error("could not fetch list of keys")
            log.debug(f"{traceback.format_exc()!s}")
            self.session.rollback()

        finally:
            self.session.close()
        return keys

    def get_values(self, stats_key, start_timestamp=None, end_timestamp=None, date_strings=False):
        values = []
        try:
            conditions = [MonitoringStats.stats_key == stats_key]
            if start_timestamp:
                utc_start_timestamp = convert_timestamp_to_utc(start_timestamp)
                conditions.append(MonitoringStats.timestamp >= utc_start_timestamp)
            if end_timestamp:
                utc_end_timestamp = convert_timestamp_to_utc(end_timestamp)
                conditions.append(MonitoringStats.timestamp <= utc_end_timestamp)
            stmt = select(MonitoringStats).where(and_(*conditions)).order_by(MonitoringStats.timestamp.asc())
            monitoring_states = self.session.scalars(stmt)
            for ms in monitoring_states:
                aware_timestamp = ms.timestamp.replace(tzinfo=tzutc())
                values.append((aware_timestamp, ms.stats_value))
        except Exception as exx:  # pragma: no cover
            log.error(f"exception {exx!r}")
            log.error("could not fetch list of keys")
            log.debug(f"{traceback.format_exc()!s}")
            self.session.rollback()
        finally:
            self.session.close()
        return values

    def get_last_value(self, stats_key):
        val = None
        try:
            stmt = (select(MonitoringStats).where(MonitoringStats.stats_key == stats_key)
                    .order_by(MonitoringStats.timestamp.desc()))
            monitoring_stat = self.session.scalars(stmt).first()
            if monitoring_stat:
                val = monitoring_stat.stats_value
        except Exception as exx:  # pragma: no cover
            log.error(f"exception {exx!r}")
            log.error("could not fetch list of keys")
            log.debug(f"{traceback.format_exc()!s}")
            self.session.rollback()
        finally:
            self.session.close()
        return val
