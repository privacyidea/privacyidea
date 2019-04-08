# -*- coding: utf-8 -*-
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
#
__doc__ = """The SQL Audit Module is used to write audit entries to an SQL
database.
The SQL Audit Module is configured like this:

    PI_AUDIT_MODULE = "privacyidea.lib.auditmodules.sqlaudit"
    PI_AUDIT_KEY_PRIVATE = "tests/testdata/private.pem"
    PI_AUDIT_KEY_PUBLIC = "tests/testdata/public.pem"
    PI_AUDIT_SERVERNAME = "your choice"

    Optional:
    PI_AUDIT_SQL_URI = "sqlite://"
    PI_AUDIT_SQL_TRUNCATE = True | False

If the PI_AUDIT_SQL_URI is omitted the Audit data is written to the
token database.
"""

import logging
from privacyidea.lib.auditmodules.base import (Audit as AuditBase, Paginate)
from privacyidea.lib.crypto import Sign
from privacyidea.lib.pooling import get_engine
from privacyidea.lib.utils import censor_connect_string
from privacyidea.lib.lifecycle import register_finalizer
from privacyidea.lib.utils import truncate_comma_list
from privacyidea.lib.framework import get_app_config_value
from sqlalchemy import MetaData, cast, String
from sqlalchemy import asc, desc, and_, or_
import datetime
import traceback
from six import string_types
from privacyidea.models import audit_column_length as column_length
from privacyidea.models import Audit as LogEntry
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

log = logging.getLogger(__name__)

metadata = MetaData()


class Audit(AuditBase):
    """
    This is the SQLAudit module, which writes the audit entries
    to an SQL database table.
    It requires the configuration parameters in pi.cfg:
    * PI_AUDIT_KEY_PUBLIC
    * PI_AUDIT_KEY_PRIVATE

    If you want to host the SQL Audit database in another DB than the
    token DB, you can use:
    * PI_AUDIT_SQL_URI

    It also takes the optional parameters:
    * PI_AUDIT_POOL_SIZE
    * PI_AUDIT_POOL_RECYCLE
    * PI_AUDIT_SQL_TRUNCATE
    * PI_AUDIT_NO_SIGN

    You can use PI_AUDIT_NO_SIGN = True to avoid signing of the audit log.

    If PI_CHECK_OLD_SIGNATURES = True old style signatures (text-book RSA) will
    be checked as well, otherwise they will be marked as 'FAIL'.
    """
    
    def __init__(self, config=None):
        self.name = "sqlaudit"
        self.config = config or {}
        self.audit_data = {}
        self.sign_data = not self.config.get("PI_AUDIT_NO_SIGN")
        self.sign_object = None
        self.verify_old_sig = get_app_config_value('PI_CHECK_OLD_SIGNATURES')
        if self.sign_data:
            self.read_keys(self.config.get("PI_AUDIT_KEY_PUBLIC"),
                           self.config.get("PI_AUDIT_KEY_PRIVATE"))
            self.sign_object = Sign(self.private, self.public)

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
        register_finalizer(self.session.close)
        self.session._model_changes = {}

    def _create_engine(self):
        """
        :return: a new SQLAlchemy engine connecting to the database specified in PI_AUDIT_SQL_URI.
        """
        # an Engine, which the Session will use for connection
        # resources
        connect_string = self.config.get("PI_AUDIT_SQL_URI", self.config.get(
            "SQLALCHEMY_DATABASE_URI"))
        log.debug("using the connect string {0!s}".format(censor_connect_string(connect_string)))
        try:
            pool_size = self.config.get("PI_AUDIT_POOL_SIZE", 20)
            engine = create_engine(
                connect_string,
                pool_size=pool_size,
                pool_recycle=self.config.get("PI_AUDIT_POOL_RECYCLE", 600))
            log.debug("Using SQL pool size of {}".format(pool_size))
        except TypeError:
            # SQLite does not support pool_size
            engine = create_engine(connect_string)
            log.debug("Using no SQL pool_size.")
        return engine

    def _truncate_data(self):
        """
        Truncate self.audit_data according to the column_length.
        :return: None
        """
        for column, l in column_length.items():
            if column in self.audit_data:
                data = self.audit_data[column]
                if isinstance(data, string_types):
                    if column == "policies":
                        # The policies column is shortend per comma entry
                        data = truncate_comma_list(data, l)
                    else:
                        data = data[:l]
                self.audit_data[column] = data

    @staticmethod
    def _create_filter(param, timelimit=None):
        """
        create a filter condition for the logentry
        """
        conditions = []
        param = param or {}
        for search_key in param.keys():
            search_value = param.get(search_key)
            if search_key == "allowed_audit_realm":
                # Add each realm in the allowed_audit_realm list to the
                # search condition
                realm_conditions = []
                for realm in search_value:
                    realm_conditions.append(LogEntry.realm == realm)
                filter_realm = or_(*realm_conditions)
                conditions.append(filter_realm)
            # We do not search if the search value only consists of '*'
            elif search_value.strip() != '' and search_value.strip('*') != '':
                try:
                    if search_key == "success":
                        # "success" is the only integer.
                        search_value = search_value.strip("*")
                        conditions.append(getattr(LogEntry, search_key) ==
                                          int(search_value))
                    else:
                        # All other keys are compared as strings
                        column = getattr(LogEntry, search_key)
                        if search_key == "date":
                            # but we cast "date" to a string first (required on postgresql)
                            column = cast(column, String)
                        search_value = search_value.replace('*', '%')
                        if '%' in search_value:
                            conditions.append(column.like(search_value))
                        else:
                            conditions.append(column == search_value)
                except Exception as exx:
                    # The search_key was no search key but some
                    # bullshit stuff in the param
                    log.debug("Not a valid searchkey: {0!s}".format(exx))

        if timelimit:
            conditions.append(LogEntry.date >= datetime.datetime.now() -
                              timelimit)
        # Combine them with or to a BooleanClauseList
        filter_condition = and_(*conditions)
        return filter_condition

    def get_total(self, param, AND=True, display_error=True, timelimit=None):
        """
        This method returns the total number of audit entries
        in the audit store
        """
        count = 0
        # if param contains search filters, we build the search filter
        # to only return the number of those entries
        filter_condition = self._create_filter(param, timelimit=timelimit)
        
        try:
            count = self.session.query(LogEntry.id)\
                .filter(filter_condition)\
                .count()
        finally:
            self.session.close()
        return count

    def finalize_log(self):
        """
        This method is used to log the data.
        It should hash the data and do a hash chain and sign the data
        """
        try:
            self.audit_data["policies"] = ",".join(self.audit_data.get("policies",[]))
            if self.config.get("PI_AUDIT_SQL_TRUNCATE"):
                self._truncate_data()
            le = LogEntry(action=self.audit_data.get("action"),
                          success=int(self.audit_data.get("success", 0)),
                          serial=self.audit_data.get("serial"),
                          token_type=self.audit_data.get("token_type"),
                          user=self.audit_data.get("user"),
                          realm=self.audit_data.get("realm"),
                          resolver=self.audit_data.get("resolver"),
                          administrator=self.audit_data.get("administrator"),
                          action_detail=self.audit_data.get("action_detail"),
                          info=self.audit_data.get("info"),
                          privacyidea_server=self.audit_data.get("privacyidea_server"),
                          client=self.audit_data.get("client", ""),
                          loglevel=self.audit_data.get("log_level"),
                          clearance_level=self.audit_data.get("clearance_level"),
                          policies=self.audit_data.get("policies")
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
            log.error("exception {0!r}".format(exx))
            log.error("DATA: {0!s}".format(self.audit_data))
            log.debug("{0!s}".format(traceback.format_exc()))
            self.session.rollback()

        finally:
            self.session.close()
            # clear the audit data
            self.audit_data = {}

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
            id_bef = self.session.query(LogEntry.id
                                        ).filter(LogEntry.id ==
                                                 int(audit_id) - 1).count()
            id_aft = self.session.query(LogEntry.id
                                        ).filter(LogEntry.id ==
                                                 int(audit_id) + 1).count()
            # We may not do a commit!
            # self.session.commit()
            if id_bef and id_aft:
                res = True
        except Exception as exx:  # pragma: no cover
            log.error("exception {0!r}".format(exx))
            log.debug("{0!s}".format(traceback.format_exc()))
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
        s = u"id=%s,date=%s,action=%s,succ=%s,serial=%s,t=%s,u=%s,r=%s,adm=%s," \
            u"ad=%s,i=%s,ps=%s,c=%s,l=%s,cl=%s" % (le.id,
                                                   le.date,
                                                   le.action,
                                                   le.success,
                                                   le.serial,
                                                   le.token_type,
                                                   le.user,
                                                   le.realm,
                                                   le.administrator,
                                                   le.action_detail,
                                                   le.info,
                                                   le.privacyidea_server,
                                                   le.client,
                                                   le.loglevel,
                                                   le.clearance_level)
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
                    'token_type': LogEntry.token_type,
                    'user': LogEntry.user,
                    'realm': LogEntry.realm,
                    'administrator': LogEntry.administrator,
                    'action_detail': LogEntry.action_detail,
                    'info': LogEntry.info,
                    'privacyidea_server': LogEntry.privacyidea_server,
                    'client': LogEntry.client,
                    'loglevel': LogEntry.loglevel,
                    'policies': LogEntry.policies,
                    'clearance_level': LogEntry.clearance_level}
        return sortname.get(key)

    def csv_generator(self, param=None, user=None, timelimit=None):
        """
        Returns the audit log as csv file.
        :param timelimit: Limit the number of dumped entries by time
        :type timelimit: datetime.timedelta
        :param param: The request parameters
        :type param: dict
        :param user: The user, who issued the request
        :return: None. It yields results as a generator
        """
        filter_condition = self._create_filter(param,
                                               timelimit=timelimit)
        logentries = self.session.query(LogEntry).filter(filter_condition).all()

        for le in logentries:
            audit_dict = self.audit_entry_to_dict(le)
            audit_list = list(audit_dict.values())
            string_list = [u"'{0!s}'".format(x) for x in audit_list]
            yield ",".join(string_list)+"\n"

    def get_count(self, search_dict, timedelta=None, success=None):
        # create filter condition
        filter_condition = self._create_filter(search_dict)
        conditions = [filter_condition]
        if success is not None:
            conditions.append(LogEntry.success == success)

        if timedelta is not None:
            conditions.append(LogEntry.date >= datetime.datetime.now() -
                              timedelta)

        filter_condition = and_(*conditions)
        log_count = self.session.query(LogEntry).filter(filter_condition).count()

        return log_count

    def search(self, search_dict, page_size=15, page=1, sortorder="asc",
               timelimit=None):
        """
        This function returns the audit log as a Pagination object.

        :param timelimit: Only audit entries newer than this timedelta will
            be searched
        :type timelimit: timedelta
        """
        page = int(page)
        page_size = int(page_size)
        paging_object = Paginate()
        paging_object.page = page
        paging_object.total = self.get_total(search_dict, timelimit=timelimit)
        if page > 1:
            paging_object.prev = page - 1
        if paging_object.total > (page_size * page):
            paging_object.next = page + 1

        auditIter = self.search_query(search_dict, page_size=page_size,
                                      page=page, sortorder=sortorder,
                                      timelimit=timelimit)
        while True:
            try:
                le = next(auditIter)
                # Fill the list
                paging_object.auditdata.append(self.audit_entry_to_dict(le))
            except StopIteration as _e:
                log.debug("Interation stopped.")
                break
            except UnicodeDecodeError as _e:
                # Unfortunately if one of the audit entries fails, the whole
                # iteration stops and we return an empty paging_object.
                # TODO: Check if we can return the other entries in the auditIter
                #  or some meaningful error for the user.
                log.warning('Could not read audit log entry! '
                            'Possible database encoding mismatch.')
                log.debug("{0!s}".format(traceback.format_exc()))

        return paging_object
        
    def search_query(self, search_dict, page_size=15, page=1, sortorder="asc",
                     sortname="number", timelimit=None):
        """
        This function returns the audit log as an iterator on the result

        :param timelimit: Only audit entries newer than this timedelta will
            be searched
        :type timelimit: timedelta
        """
        logentries = None
        try:
            limit = int(page_size)
            offset = (int(page) - 1) * limit
            
            # create filter condition
            filter_condition = self._create_filter(search_dict,
                                                   timelimit=timelimit)

            if sortorder == "desc":
                logentries = self.session.query(LogEntry).filter(
                    filter_condition).order_by(
                    desc(self._get_logentry_attribute("number"))).limit(
                    limit).offset(offset)
            else:
                logentries = self.session.query(LogEntry).filter(
                    filter_condition).order_by(
                    asc(self._get_logentry_attribute("number"))).limit(
                    limit).offset(offset)
                                         
        except Exception as exx:  # pragma: no cover
            log.error("exception {0!r}".format(exx))
            log.debug("{0!s}".format(traceback.format_exc()))
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
        self.session.query(LogEntry).delete()
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
                log.debug('{0!s}'.format(traceback.format_exc()))

        is_not_missing = self._check_missing(int(audit_entry.id))
        # is_not_missing = True
        audit_dict = {'number': audit_entry.id,
                      'date': audit_entry.date.isoformat(),
                      'sig_check': "OK" if sig else "FAIL",
                      'missing_line': "OK" if is_not_missing else "FAIL",
                      'action': audit_entry.action,
                      'success': audit_entry.success,
                      'serial': audit_entry.serial,
                      'token_type': audit_entry.token_type,
                      'user': audit_entry.user,
                      'realm': audit_entry.realm,
                      'resolver': audit_entry.resolver,
                      'administrator': audit_entry.administrator,
                      'action_detail': audit_entry.action_detail,
                      'info': audit_entry.info,
                      'privacyidea_server': audit_entry.privacyidea_server,
                      'policies': audit_entry.policies,
                      'client': audit_entry.client,
                      'log_level': audit_entry.loglevel,
                      'clearance_level': audit_entry.clearance_level
                      }
        return audit_dict
