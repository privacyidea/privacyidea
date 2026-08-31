# (c) NetKnights GmbH 2025,  https://netknights.it
#
#  2016-04-08 Cornelius Kölbel <cornelius@privacyidea.org>
#             Avoid consecutive if statements
#
#  privacyIDEA
#  May 11, 2014 Cornelius Kölbel, info@privacyidea.org
#  http://www.privacyidea.org
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
# SPDX-FileCopyrightText: 2025 Paul Lettich <paul.lettich@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
"""The SQL Audit Module is used to write audit entries to an SQL
database.
The SQL Audit Module is configured like this::

    PI_AUDIT_MODULE = "privacyidea.lib.auditmodules.sqlaudit"
    PI_AUDIT_KEY_PRIVATE = "tests/testdata/private.pem"
    PI_AUDIT_KEY_PUBLIC = "tests/testdata/public.pem"
    PI_AUDIT_SERVERNAME = "your choice"

Optional::

    PI_AUDIT_SQL_URI = "sqlite://"
    PI_AUDIT_SQL_COLUMN_LENGTH = {"user": 60, "info": 10 ...}

If the PI_AUDIT_SQL_URI is omitted the Audit data is written to the
token database.
"""

import datetime
import inspect
import logging
import traceback
from collections import OrderedDict

from sqlalchemy import asc, desc, and_, or_, select, delete, text
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql.expression import FunctionElement

from privacyidea.config import ConfigKey
from privacyidea.lib.auditmodules.base import Audit as AuditBase, Paginate
from privacyidea.lib.crypto import Sign
from privacyidea.lib.lifecycle import register_finalizer
from privacyidea.lib.pooling import get_engine
from privacyidea.lib.utils import censor_connect_string
from privacyidea.lib.utils import (is_true, convert_wildcard_to_sql_like, SQL_LIKE_ESCAPE)
from privacyidea.models import Audit as LogEntry
from privacyidea.models.audit import AUDIT_TABLE_NAME
from privacyidea.models import audit_column_length as column_length

log = logging.getLogger(__name__)


def _pool_accepts_pool_size(connect_string, engine_kwargs):
    """
    Check whether the connection pool that ``create_engine()`` will use for this
    connect string takes a ``pool_size``.

    ``NullPool`` and ``StaticPool`` do not, and they can be requested for any database
    through the ``poolclass`` engine option, so the database type alone does not answer
    this. Passing ``pool_size`` to a pool that does not know it is a ``TypeError``.

    :param connect_string: The connect string the engine will be created with
    :param engine_kwargs: The keyword arguments for ``create_engine()``
    :return: True if the pool takes a pool_size
    """
    pool_class = engine_kwargs.get("poolclass")
    if pool_class is None:
        url = make_url(connect_string)
        pool_class = url.get_dialect().get_pool_class(url)
    return "pool_size" in inspect.signature(pool_class).parameters


# Define function to convert SQL DateTime objects to an ISO-format string
# By using <https://docs.sqlalchemy.org/en/14/core/compiler.html> we can
# differentiate between different dialects.
class to_isodate(FunctionElement):
    name = 'to_isodate'
    inherit_cache = True


@compiles(to_isodate, 'oracle')
@compiles(to_isodate, 'postgresql')
def fn_to_isodate_oracle_pg(element, compiler, **kw):
    return f"to_char({compiler.process(element.clauses, **kw)}, 'IYYY-MM-DD HH24:MI:SS')"


@compiles(to_isodate, 'sqlite')
def fn_to_isodate_sqlite(element, compiler, **kw):
    # sqlite does not have a DateTime type, they are already in ISO format
    return f"{compiler.process(element.clauses, **kw)}"


@compiles(to_isodate)
def fn_to_isodate_default(element, compiler, **kw):
    # %% escapes a literal % past the DBAPI driver's pyformat paramstyle.
    return "date_format({}, '%%Y-%%m-%%d %%H:%%i:%%s')".format(compiler.process(
        element.clauses, **kw))


def _now():
    """
    Returns the current local date and time.
    This function is required to be able to mock datetime.now() in tests.
    """
    return datetime.datetime.now()


# The audit table is introspected once per process and database: an Audit object is created
# for every request, and the schema does not change underneath a running process.
_live_column_length = {}


def get_live_column_length(engine) -> dict:
    """
    Return the length of every length-restricted column of the audit table as it really is
    in the database, so that values can be shortened to what the table accepts rather than
    to what the model declares. The result is cached per database.

    An unreachable database or a missing audit table yields an empty mapping, in which case
    the model and the configuration decide alone.

    :param engine: the SQLAlchemy engine of the audit database
    :return: a dict mapping column name to its length
    """
    cache_key = str(engine.url)
    if cache_key not in _live_column_length:
        lengths = {}
        try:
            for column in sqlalchemy_inspect(engine).get_columns(AUDIT_TABLE_NAME):
                # A type without a length, e.g. TEXT, holds a value of any length. It is
                # reported as None so that nothing is cut for such a column.
                lengths[column.get("name")] = getattr(column.get("type"), "length", None)
        except Exception as exx:  # noqa: BLE001 - the table may not exist yet
            # The values are sized to the model instead, which is what the table has unless
            # somebody changed it. A database that has narrower columns rejects the entries,
            # so this needs to be visible.
            log.warning(f"Could not read the columns of the table {AUDIT_TABLE_NAME}, audit "
                        f"entries are sized to the model instead: {exx!r}")
        _live_column_length[cache_key] = lengths
    return _live_column_length[cache_key]


class Audit(AuditBase):
    """
    This is the SQLAudit module, which writes the audit entries
    to an SQL database table.

    It requires the following configuration parameters in :ref:`cfgfile`:

    * ``PI_AUDIT_KEY_PUBLIC``
    * ``PI_AUDIT_KEY_PRIVATE``

    If you want to host the SQL Audit database in another DB than the
    token DB, you can use:

    * ``PI_AUDIT_SQL_URI`` and
    * ``PI_AUDIT_SQL_OPTIONS``

    With ``PI_AUDIT_SQL_OPTIONS = {}`` You can pass options to the DB engine
    creation. If ``PI_AUDIT_SQL_OPTIONS`` is not set,
    ``SQLALCHEMY_ENGINE_OPTIONS`` will be used.

    This module also takes the following optional parameters:

    * ``PI_AUDIT_POOL_SIZE``
    * ``PI_AUDIT_POOL_RECYCLE``
    * ``PI_AUDIT_NO_SIGN``
    * ``PI_CHECK_OLD_SIGNATURES``

    You can use ``PI_AUDIT_NO_SIGN = True`` to avoid signing of the audit log.

    If ``PI_CHECK_OLD_SIGNATURES = True`` old style signatures (text-book RSA) will
    be checked as well, otherwise they will be marked as ``FAIL``.
    """

    is_readable = True

    def __init__(self, config=None, startdate=None):
        super().__init__(config, startdate)
        self.name = "sqlaudit"
        self.sign_data = not self.config.get(ConfigKey.AUDIT_NO_SIGN)
        self.sign_object = None
        self.verify_old_sig = self.config.get(ConfigKey.CHECK_OLD_SIGNATURES)
        # Disable the costly checking of private RSA keys when loading them.
        self.check_private_key = not self.config.get(ConfigKey.AUDIT_NO_PRIVATE_KEY_CHECK, False)
        if self.sign_data:
            self.read_keys(self.config.get(ConfigKey.AUDIT_KEY_PUBLIC),
                           self.config.get(ConfigKey.AUDIT_KEY_PRIVATE))
            self.sign_object = Sign(self.private, self.public,
                                    check_private_key=self.check_private_key)
        # Read column_length from the config file
        config_column_length = self.config.get(ConfigKey.AUDIT_SQL_COLUMN_LENGTH, {})
        # fill the missing parts with the default from the models
        self.custom_column_length = {k: (v if k not in config_column_length else config_column_length[k])
                                     for k, v in column_length.items()}
        # Filled on first use from the columns the audit table really has
        self._effective_column_length = None
        # We can use "sqlaudit" as the key because the SQLAudit connection
        # string is fixed for a running privacyIDEA instance.
        # In other words, we will not run into any problems with changing connect strings.
        self.engine = get_engine(self.name, self._create_engine)
        # create a configured "Session" class. ``scoped_session`` is not
        # necessary because we do not share session objects among threads.
        # We use it anyway as a safety measure.
        Session = scoped_session(sessionmaker(bind=self.engine))
        self.session = Session()
        # Ensure that the connection gets returned to the pool when the request has
        # been handled. This may close an already-closed session, but this is not a problem.
        register_finalizer(self._finalize_session)
        self.session._model_changes = {}
        # Lazily determined by _get_id_stride(), cached per instance since a single
        # instance serves an entire request (e.g. one page of audit entries).
        self._id_stride = None

    def _create_engine(self):
        """
        :return: a new SQLAlchemy engine connecting to the database specified in PI_AUDIT_SQL_URI.
        """
        # an Engine, which the Session will use for connection
        # resources
        connect_string = self.config.get(ConfigKey.AUDIT_SQL_URI, self.config.get(
            ConfigKey.SQLALCHEMY_DATABASE_URI))
        log.debug(f"using the connect string {censor_connect_string(connect_string)!s}")
        # if no specific audit engine options are given, use the default from
        # SQLALCHEMY_ENGINE_OPTIONS or none
        sqa_options = self.config.get(ConfigKey.AUDIT_SQL_OPTIONS,
                                      self.config.get(ConfigKey.SQLALCHEMY_ENGINE_OPTIONS, {}))
        log.debug(f"Using Audit SQLAlchemy engine options: {sqa_options!s}")
        # The engine options are merged over the pool defaults instead of being passed
        # alongside them, because a key present in both would raise a TypeError about
        # duplicate keyword arguments and take the whole pool configuration down with it.
        # The merge comes first, since the poolclass may be configured here as well.
        engine_kwargs = {"pool_recycle": self.config.get(ConfigKey.AUDIT_POOL_RECYCLE, 600)}
        engine_kwargs.update(sqa_options)
        if _pool_accepts_pool_size(connect_string, engine_kwargs):
            engine_kwargs.setdefault("pool_size", self.config.get(ConfigKey.AUDIT_POOL_SIZE, 20))
            log.debug(f"Using SQL pool size of {engine_kwargs['pool_size']}")
        else:
            log.debug("The configured connection pool takes no pool size, using none.")
        return create_engine(connect_string, **engine_kwargs)

    def _finalize_session(self):
        """ Close current session and dispose connections of db engine"""
        self.session.close()
        self.engine.dispose()

    @property
    def column_length(self) -> dict:
        """
        The length every value has to fit into, which is the configured length of a column
        capped by the length the column really has in the database. A database whose audit
        table has not been migrated yet rejects a longer value and the entry would be lost,
        so the actual table always wins over the configuration.
        """
        if self._effective_column_length is None:
            live_length = get_live_column_length(self.engine)
            effective = {}
            for key, length in self.custom_column_length.items():
                if key not in live_length:
                    # The column is unknown, e.g. because the table could not be read
                    effective[key] = length
                elif live_length[key] is None:
                    # The column holds a value of any length, so nothing has to be cut
                    continue
                else:
                    effective[key] = min(length, live_length[key])
            self._effective_column_length = effective
        return self._effective_column_length

    def _truncate_data(self):
        """
        Shorten every value of self.audit_data to the length the table can hold.

        :return: None
        """
        # ``log()`` already shortens what it is given, but a value can still grow past the
        # column afterwards: ``finalize_log`` joins list values into one comma separated
        # string. So every value is checked once more before it is written.
        for column in self.column_length:
            if column in self.audit_data:
                self.audit_data[column] = self.fit_to_store(column, self.audit_data[column])

    @staticmethod
    def _create_filter(param: dict, admin_params: dict | None = None,
                       timelimit: datetime.timedelta | None = None):
        """
        create a filter condition for the logentry

        :param param: Filter parameters that are concatenated with a logical AND
        :param admin_params: Optional admin parameters containing the admin name, admin realm and a list of realms the
            admin is allowed to see, such as ::

                {"admin": "admin_name",
                 "admin_realm": "realm_of_the_admin",
                 "allowed_audit_realms": ["realm1", "realm2"]}

        :param timelimit: Only audit entries newer than this timedelta
        """
        conditions = []
        param = param or {}

        # For admins, only get audit entries of their allowed realms and their own realm
        filter_realm = None
        if admin_params:
            admin = admin_params.get("admin")
            admin_realm = admin_params.get("admin_realm")
            allowed_audit_realms = admin_params.get("allowed_audit_realms", [])
            if allowed_audit_realms:
                # search condition
                realm_conditions = []
                for realm in allowed_audit_realms:
                    realm_conditions.append(LogEntry.realm == realm)
                # If the admin is limited to some realms, we need to additionally filter for their own audit entries
                if admin and admin_realm:
                    realm_conditions.append(and_(LogEntry.administrator == admin, LogEntry.realm == admin_realm))
                elif admin:
                    realm_conditions.append(LogEntry.administrator == admin)
                filter_realm = or_(*realm_conditions)

        for search_key in param.keys():
            search_value = param.get(search_key)
            if search_key == "allowed_audit_realm":
                # Add each realm in the allowed_audit_realm list to the search condition
                realm_conditions = []
                for realm in search_value:
                    realm_conditions.append(LogEntry.realm == realm)
                filter_realm = or_(*realm_conditions)
                conditions.append(filter_realm)
            # Any other filter value is compared as a string. Coerce non-string
            # scalars so a meaningful filter is never silently dropped, which would
            # widen the audit result set. An empty value or a bare '*' wildcard means
            # "no filter" for this key.
            elif search_value is not None:
                if not isinstance(search_value, str):
                    search_value = str(search_value)
                if search_value.strip() == '' or search_value.strip('*') == '':
                    continue
                try:
                    if search_key == "success":
                        # "success" is the only integer.
                        search_value = search_value.strip("*")
                        conditions.append(getattr(LogEntry, search_key) ==
                                          int(is_true(search_value)))
                    else:
                        # All other keys are compared as strings. Only '*' is a wildcard; literal '%' and '_' are
                        # matched literally. A leading '!' negates the condition.
                        raw_column = getattr(LogEntry, search_key)
                        column = raw_column
                        if search_key in ["date", "startdate"]:
                            # but we cast a column with a DateTime type to an
                            # ISO-format string first
                            column = to_isodate(column)
                        negate = search_value.startswith("!")
                        if negate:
                            search_value = search_value[1:]
                        if "*" in search_value:
                            pattern = convert_wildcard_to_sql_like(search_value)
                            if negate:
                                conditions.append(or_(raw_column.is_(None),
                                                      column.notlike(pattern, escape=SQL_LIKE_ESCAPE)))
                            else:
                                conditions.append(column.like(pattern, escape=SQL_LIKE_ESCAPE))
                        else:
                            if negate:
                                conditions.append(or_(raw_column.is_(None), column != search_value))
                            else:
                                conditions.append(column == search_value)
                except Exception as exx:
                    # The search_key was no search key but some
                    # bullshit stuff in the param
                    log.debug(f"Not a valid searchkey: {exx!s}")

        if timelimit:
            conditions.append(LogEntry.date >= datetime.datetime.now() -
                              timelimit)
        # Combine them with or to a BooleanClauseList
        if conditions:
            filter_condition = and_(*conditions)
        else:
            filter_condition = and_(True, *conditions)
        if filter_realm is not None:
            filter_condition = and_(filter_condition, filter_realm)
        return filter_condition

    def get_total(self, param: dict, admin_params: dict | None = None, AND: bool = True, display_error: bool = True,
                  timelimit: datetime.timedelta | None = None) -> int:
        """
        This method returns the total number of audit entries
        in the audit store
        """
        count = 0
        # if param contains search filters, we build the search filter
        # to only return the number of those entries
        filter_condition = self._create_filter(param, admin_params, timelimit=timelimit)

        try:
            count = self.session.query(LogEntry.id).filter(filter_condition).count()
        finally:
            self.session.close()
        return count

    def finalize_log(self):
        """
        This method is used to log the data.
        It should hash the data and do a hash chain and sign the data
        """
        try:
            for entry, value in self.audit_data.items():
                if isinstance(value, list):
                    self.audit_data[entry] = ",".join(value)
            # A value that does not fit into its column makes the database reject the whole
            # entry, which would lose it. Shortening is therefore not optional.
            self._truncate_data()
            if "tokentype" in self.audit_data:
                log.warning("We have a wrong 'tokentype' key. This should not happen. Fix it!. "
                            "Error occurs in action: {!r}.".format(self.audit_data.get("action")))
                if "token_type" not in self.audit_data:
                    self.audit_data["token_type"] = self.audit_data.get("tokentype")
            end_date = _now()
            if self.audit_data.get("startdate"):
                duration = end_date - self.audit_data.get("startdate")
            else:
                duration = None
            le = LogEntry(action=self.audit_data.get("action"),
                          success=int(self.audit_data.get("success", 0)),
                          authentication=self.audit_data.get("authentication"),
                          serial=self.audit_data.get("serial"),
                          token_type=self.audit_data.get("token_type"),
                          container_serial=self.audit_data.get("container_serial"),
                          container_type=self.audit_data.get("container_type"),
                          user=self.audit_data.get("user"),
                          realm=self.audit_data.get("realm"),
                          resolver=self.audit_data.get("resolver"),
                          administrator=self.audit_data.get("administrator"),
                          action_detail=self.audit_data.get("action_detail"),
                          info=self.audit_data.get("info"),
                          privacyidea_server=self.audit_data.get("privacyidea_server"),
                          client=self.audit_data.get("client", ""),
                          user_agent=self.audit_data.get("user_agent"),
                          user_agent_version=self.audit_data.get("user_agent_version"),
                          loglevel=self.audit_data.get("log_level"),
                          clearance_level=self.audit_data.get("clearance_level"),
                          policies=self.audit_data.get("policies"),
                          startdate=self.audit_data.get("startdate"),
                          duration=duration,
                          date=end_date,
                          thread_id=self.audit_data.get("thread_id")
                          )
            self.session.add(le)
            self.session.commit()
            # Add the signature
            if self.sign_data and self.sign_object:
                s = self._log_to_string(le)
                sign = self.sign_object.sign(s)
                le.signature = sign
                self.session.merge(le)
                self.session.commit()
        except Exception as exx:  # pragma: no cover
            # in case of a Unicode Error in _log_to_string() we won't have
            # a signature, but the log entry is available
            log.error(f"exception {exx!r}")
            log.error(f"DATA: {self.audit_data!s}")
            log.debug(f"{traceback.format_exc()!s}")
            self.session.rollback()

        finally:
            self.session.close()
            # clear the audit data
            self.audit_data = {}

    def _get_id_stride(self):
        """
        Determine the step between the ids of two consecutively written audit log
        entries.

        This is normally 1. However, a Galera cluster with ``wsrep_auto_increment_control``
        enabled (the default) raises ``auto_increment_increment`` to the cluster size and
        gives each node its own offset, so that concurrently writing nodes cannot generate
        the same id. Entries written through a single node then land ``auto_increment_increment``
        ids apart instead of 1 apart, even though nothing was deleted.

        This is a heuristic, not a guarantee: it assumes one node is the steady writer for
        a given offset (true for a single-writer setup in front of Galera), and it reflects
        the increment at the time this instance was created, not at the time older entries
        were written, so a cluster resize can make the stride wrong for entries predating it.

        :rtype: int
        """
        if self._id_stride is None:
            self._id_stride = 1
            if self.engine.dialect.name in ("mysql", "mariadb"):
                try:
                    row = self.session.execute(
                        text("SHOW VARIABLES LIKE 'auto_increment_increment'")).fetchone()
                    if row:
                        self._id_stride = max(1, int(row[1]))
                except Exception as exx:  # pragma: no cover
                    log.debug(f"Could not determine auto_increment_increment: {exx!r}")
                    self.session.rollback()
        return self._id_stride

    def _check_missing(self, audit_id):
        """
        Check if the audit log contains the entries before and after
        the given id.

        TODO: We can not check at the moment if the first or the last entries
              were deleted. If we want to do this, we need to store some signed
              meta information:
              1. Which one was the first entry. (use initialize_log)
              2. Which one was the last entry.
        """
        res = False
        try:
            stride = self._get_id_stride()
            neighbour_ids = (int(audit_id) - stride, int(audit_id) + stride)
            found = self.session.query(LogEntry.id).filter(LogEntry.id.in_(neighbour_ids)).count()
            # We may not do a commit!
            # self.session.commit()
            if found == len(neighbour_ids):
                res = True
        except Exception as exx:  # pragma: no cover
            log.error(f"exception {exx!r}")
            log.debug(f"{traceback.format_exc()!s}")
            # self.session.rollback()
        finally:
            # self.session.close()
            pass

        return res

    @staticmethod
    def _log_to_string(le):
        """
        This function creates a string from the logentry so
        that this string can be signed.

        Note: Not all elements of the LogEntry are used to generate the
        string (the Signature is not!), otherwise we could have used pickle

        :param le: LogEntry object containing the data
        :type le: LogEntry
        :rtype str
        """
        # TODO: Add thread_id. We really should add a versioning to identify which audit data is signed.
        s = f"id={le.id},date={le.date},action={le.action},succ={le.success},serial={le.serial}," \
            f"t={le.token_type},u={le.user},r={le.realm},adm={le.administrator},ad={le.action_detail}," \
            f"i={le.info},ps={le.privacyidea_server},c={le.client},l={le.loglevel},cl={le.clearance_level}"
        # If we have the new log entries, we also add them for signing and verification.
        if le.startdate:
            s += f",{le.startdate!s}"
        if le.duration:
            s += f",{le.duration!s}"
        if le.container_serial:
            s += f",c_serial={le.container_serial}"
        if le.container_type:
            s += f",ct={le.container_type}"
        return s

    @staticmethod
    def _get_logentry_attribute(key):
        """
        This function returns the LogEntry attribute for the given key value
        """
        sortname = {'number': LogEntry.id,
                    'action': LogEntry.action,
                    'success': LogEntry.success,
                    'serial': LogEntry.serial,
                    'date': LogEntry.date,
                    'startdate': LogEntry.startdate,
                    'duration': LogEntry.duration,
                    'token_type': LogEntry.token_type,
                    'user': LogEntry.user,
                    'realm': LogEntry.realm,
                    'administrator': LogEntry.administrator,
                    'action_detail': LogEntry.action_detail,
                    'info': LogEntry.info,
                    'privacyidea_server': LogEntry.privacyidea_server,
                    'client': LogEntry.client,
                    'log_level': LogEntry.loglevel,
                    'policies': LogEntry.policies,
                    'clearance_level': LogEntry.clearance_level,
                    'thread_id': LogEntry.thread_id,
                    'container_serial': LogEntry.container_serial,
                    'container_type': LogEntry.container_type}
        return sortname.get(key)

    def csv_generator(self, param: dict | None = None, admin_params: dict | None = None, user=None,
                      timelimit: datetime.timedelta | None = None):
        """
        Returns the audit log as csv file.

        :param timelimit: Limit the number of dumped entries by time
        :param param: The request parameters
        :param admin_params: Optional admin parameters containing the admin name, admin realm and a list of realms the
            admin is allowed to see, such as ::

                {"admin": "admin_name",
                 "admin_realm": "realm_of_the_admin",
                 "allowed_audit_realms": ["realm1", "realm2"]}

        :param user: The user, who issued the request
        :return: None. It yields results as a generator
        """
        filter_condition = self._create_filter(param, admin_params=admin_params, timelimit=timelimit)
        stmt = select(LogEntry).where(filter_condition).order_by(LogEntry.date)
        logentries = self.session.scalars(stmt).all()

        for le in logentries:
            audit_dict = self.audit_entry_to_dict(le)
            yield ",".join([f"'{x!s}'" for x in audit_dict.values()]) + "\n"

    def get_count(self, search_dict, timedelta=None, success=None):
        # create filter condition
        filter_condition = self._create_filter(search_dict)
        conditions = [filter_condition]
        if success is not None:
            conditions.append(LogEntry.success == int(is_true(success)))

        if timedelta is not None:
            conditions.append(LogEntry.date >= datetime.datetime.now() -
                              timedelta)

        if conditions:
            filter_condition = and_(*conditions)
        else:
            filter_condition = and_(True, *conditions)
        log_count = self.session.query(LogEntry).filter(filter_condition).count()

        return log_count

    def search(self, search_dict: dict, admin_params: dict | None = None, page_size: int = 15, page: int = 1,
               sortorder: str = "asc", timelimit: datetime.timedelta | None = None):
        """
        This function returns the audit log as a Pagination object.

        :param search_dict: Filter parameters that are concatenated with a logical AND
        :param admin_params: Optional admin parameters containing the admin name, admin realm and a list of realms the
            admin is allowed to see, such as ::

                {"admin": "admin_name",
                 "admin_realm": "realm_of_the_admin",
                 "allowed_audit_realms": ["realm1", "realm2"]}

        :param page_size: Number of entries per page
        :param page: The page number
        :param sortorder: "asc" - ascending or "desc" - descending
        :param timelimit: Only audit entries newer than this timedelta will be searched
        """
        page = page
        page_size = page_size
        paging_object = Paginate()
        paging_object.page = page
        paging_object.total = self.get_total(search_dict, admin_params=admin_params, timelimit=timelimit)
        if page > 1:
            paging_object.prev = page - 1
        if paging_object.total > (page_size * page):
            paging_object.next = page + 1

        auditIter = self.search_query(search_dict, admin_params=admin_params, page_size=page_size,
                                      page=page, sortorder=sortorder,
                                      timelimit=timelimit)
        while True:
            try:
                le = next(auditIter)
                # Fill the list
                paging_object.auditdata.append(self.audit_entry_to_dict(le))
            except StopIteration as _e:
                log.debug("Iteration stopped.")
                break
            except UnicodeDecodeError as _e:
                # Unfortunately if one of the audit entries fails, the whole
                # iteration stops and we return an empty paging_object.
                # TODO: Check if we can return the other entries in the auditIter
                #  or some meaningful error for the user.
                log.warning('Could not read audit log entry! '
                            'Possible database encoding mismatch.')
                log.debug(f"{traceback.format_exc()!s}")

        return paging_object

    def search_query(self, search_dict: dict, admin_params: dict | None = None, page_size: int = 15, page: int = 1,
                     sortorder: str = "asc", sortname: str = "number", timelimit: datetime.timedelta | None = None):
        """
        This function returns the audit log as an iterator on the result

        :param search_dict: Filter parameters that are concatenated with a logical AND
        :param admin_params: Optional admin parameters containing the admin name, admin realm and a list of realms the
            admin is allowed to see, such as ::

                {"admin": "admin_name",
                 "admin_realm": "realm_of_the_admin",
                 "allowed_audit_realms": ["realm1", "realm2"]}

        :param page_size: Number of entries per page
        :param page: The page number
        :param sortorder: "asc" - ascending or "desc" - descending
        :param sortname: The column name to sort after. E.g. "number", "date", "user", ...
        :param timelimit: Only audit entries newer than this timedelta will
            be searched
        :type timelimit: timedelta
        """
        logentries = None
        try:
            limit = page_size
            offset = (page - 1) * limit

            # create filter condition
            filter_condition = self._create_filter(search_dict, admin_params, timelimit=timelimit)
            stmt = select(LogEntry).where(filter_condition)

            if sortorder == "desc":
                stmt = stmt.order_by(
                    desc(self._get_logentry_attribute("number")))
            else:
                stmt = stmt.order_by(
                    asc(self._get_logentry_attribute("number")))
            stmt = stmt.limit(limit).offset(offset)
            logentries = self.session.scalars(stmt).all()

        except Exception as exx:  # pragma: no cover
            log.error(f"exception {exx!r}")
            log.debug(f"{traceback.format_exc()!s}")
            self.session.rollback()
        finally:
            self.session.close()

        if logentries is None:
            return iter([])
        else:
            return iter(logentries)

    def clear(self):
        """
        Deletes all entries in the database table.
        This is only used for test cases!
        :return:
        """
        stmt = delete(LogEntry)
        self.session.execute(stmt)
        self.session.commit()

    def audit_entry_to_dict(self, audit_entry):
        sig = None
        if self.sign_data:
            try:
                sig = self.sign_object.verify(self._log_to_string(audit_entry),
                                              audit_entry.signature,
                                              self.verify_old_sig)
            except UnicodeDecodeError as _e:
                # TODO: Unless we trace and eliminate the broken unicode in the
                #  audit_entry, we will get issues when packing the response.
                log.warning('Could not verify log entry! We get invalid values '
                            'from the database, please check the encoding.')
                log.debug(f'{traceback.format_exc()!s}')

        is_not_missing = self._check_missing(int(audit_entry.id))
        # is_not_missing = True
        audit_dict = OrderedDict()
        audit_dict['number'] = audit_entry.id
        audit_dict['date'] = audit_entry.date.isoformat()
        audit_dict['sig_check'] = "OK" if sig else "FAIL"
        audit_dict['missing_line'] = "OK" if is_not_missing else "FAIL"
        audit_dict['action'] = audit_entry.action
        audit_dict['authentication'] = audit_entry.authentication
        audit_dict['success'] = audit_entry.success
        audit_dict['serial'] = audit_entry.serial
        audit_dict['token_type'] = audit_entry.token_type
        audit_dict['container_serial'] = audit_entry.container_serial
        audit_dict['container_type'] = audit_entry.container_type
        audit_dict['user'] = audit_entry.user
        audit_dict['realm'] = audit_entry.realm
        audit_dict['resolver'] = audit_entry.resolver
        audit_dict['administrator'] = audit_entry.administrator
        audit_dict['action_detail'] = audit_entry.action_detail
        audit_dict['info'] = audit_entry.info
        audit_dict['privacyidea_server'] = audit_entry.privacyidea_server
        audit_dict['policies'] = audit_entry.policies
        audit_dict['client'] = audit_entry.client
        audit_dict['user_agent'] = audit_entry.user_agent
        audit_dict['user_agent_version'] = audit_entry.user_agent_version
        audit_dict['log_level'] = audit_entry.loglevel
        audit_dict['clearance_level'] = audit_entry.clearance_level
        audit_dict['startdate'] = audit_entry.startdate.isoformat() if audit_entry.startdate else None
        audit_dict['duration'] = audit_entry.duration.total_seconds() if audit_entry.duration else None
        audit_dict['thread_id'] = audit_entry.thread_id
        return audit_dict
