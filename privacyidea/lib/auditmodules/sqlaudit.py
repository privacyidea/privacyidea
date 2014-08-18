# -*- coding: utf-8 -*-
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
import logging
log = logging.getLogger(__name__)
from privacyidea.lib.audit import AuditBase


from sqlalchemy import Table, MetaData, Column
from sqlalchemy import Integer, String, DateTime, asc, desc, and_
from sqlalchemy.orm import mapper
import datetime
# from privacyidea.lib.config  import get_privacyIDEA_config
from pylons import config as ini_config
import traceback
from Crypto.Hash import SHA256 as HashFunc
from Crypto.PublicKey import RSA
from sqlalchemy.exc import OperationalError
from privacyidea.lib.log import log_with

metadata = MetaData()

logentry = Table('pidea_audit',
                 metadata,
                 Column('id', Integer, primary_key=True),
                 Column('date', DateTime),
                 Column('signature', String(620)),
                 Column('action', String(50)),
                 Column('success', Integer),
                 Column('serial', String(20)),
                 Column('token_type', String(12)),
                 Column('user', String(20)),
                 Column('realm', String(20)),
                 Column('administrator', String(20)),
                 Column('action_detail', String(50)),
                 Column('info', String(50)),
                 Column('privacyidea_server', String(20)),
                 Column('client', String(20)),
                 Column('loglevel', String(12)),
                 Column('clearance_level', String(12))
                 )


class LogEntry(object):
    def __init__(self,
                 action="",
                 success=0,
                 serial="",
                 token_type="",
                 user="",
                 realm="",
                 administrator="",
                 action_detail="",
                 info="",
                 privacyidea_server="",
                 client="",
                 loglevel="default",
                 clearance_level="default"
                 ):
        self.signature = ""
        self.date = datetime.datetime.now()
        self.action = action
        self.success = success
        self.serial = serial
        self.token_type = token_type
        self.user = user
        self.realm = realm
        self.administrator = administrator
        self.action_detail = action_detail
        self.info = info
        self.privacyidea_server = privacyidea_server
        self.client = client
        self.loglevel = loglevel
        self.clearance_level = clearance_level

mapper(LogEntry, logentry)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class Audit(AuditBase):
    '''
    This is the SQLAudit module, which writes the audit entries
    to an SQL database table.
    It requires the configuration parameters:
    
    privacyideaAudit.sql.url (default: sqlalchemy.url)
    
    '''
    
    def __init__(self):
        self.name = "sqlaudit"
        self.readKeys()
        
        # conf = get_privacyIDEA_config()
        # an Engine, which the Session will use for connection
        # resources
        connect_string = ini_config.get("privacyideaAudit.sql.url",
                                        ini_config.get("sqlalchemy.url"))
        log.info("using the connect string %s" % connect_string)
        self.engine = create_engine(connect_string)

        # create a configured "Session" class
        Session = sessionmaker(bind=self.engine)

        # create a Session
        self.session = Session()
        try:
            metadata.create_all(self.engine)
        except OperationalError as exx:
            log.info("%r" % exx)
            pass
            
    def getAuditId(self):
        return self.name

    def _create_filter(self, param):
        '''
        create a filter condition for the logentry
        '''
        conditions = []
        for search_key in param.keys():
            search_value = param.get(search_key)
            if search_value.strip() != '':
                try:
                    conditions.append(getattr(LogEntry,
                                              search_key).like("%" +
                                                               search_value +
                                                               "%"))
                except:
                    # The search_key was no search key but some
                    # bullshit stuff in the param
                    pass
        # Combine them with or to a BooleanClauseList
        filter_condition = and_(*conditions)
        return filter_condition

    def getTotal(self, param, AND=True, display_error=True):
        '''
        This method returns the total number of audit entries
        in the audit store
        '''
        count = 0

        # if param contains search filters, we build the search filter
        # to only return the number of those entries
        filter_condition = self._create_filter(param)
        
        try:
            count = self.session.query(LogEntry.id)\
                .filter(filter_condition)\
                .count()
        finally:
            self.session.close()
        return count

    @log_with(log)
    def log(self, param):
        '''
        This method is used to log the data.
        It should hash the data and do a hash chain and sign the data
        '''
        try:
            le = LogEntry(action=param.get("action"),
                          success=param.get("success"),
                          serial=param.get("serial"),
                          token_type=param.get("token_type"),
                          user=param.get("user"),
                          realm=param.get("realm"),
                          administrator=param.get("administrator"),
                          action_detail=param.get("action_detail"),
                          info=param.get("info"),
                          privacyidea_server=param.get("privacyidea_server"),
                          client=param.get("client", ""),
                          loglevel=param.get("log_level"),
                          clearance_level=param.get("clearance_level")
                          )
            self.session.add(le)
            self.session.commit()
            # Add the signature
            s = self._log_to_string(le)
            sign = self._sign(s)
            le.signature = sign
            self.session.merge(le)
            self.session.commit()
        except Exception as exx:
            log.error("exception %r" % exx)
            log.error("%s" % traceback.format_exc())
            self.session.rollback()

        finally:
            self.session.close()
    
    def _sign(self, s):
        '''
        Create a signature of the string s
        
        :return: The signature of the string
        :rtype: long
        '''
        RSAkey = RSA.importKey(self.private)
        hashvalue = HashFunc.new(s).digest()
        signature = RSAkey.sign(hashvalue, 1)
        s_signature = str(signature[0])
        return s_signature
    
    def _verify_sig(self, audit_entry):
        '''
        Check the signature of the audit log in the database
        '''
        r = False
        try:
            RSAkey = RSA.importKey(self.public)
            hashvalue = HashFunc.new(self._log_to_string(audit_entry)).digest()
            signature = long(audit_entry.signature)
            r = RSAkey.verify(hashvalue, (signature,))
        except Exception:
            log.error("Failed to verify audit entry: %r" % audit_entry.id)
            log.error(traceback.format_exc())
        return r

    def _check_missing(self, audit_id):
        '''
        Check if the audit log contains the entries before and after
        the given id.
        
        TODO: We can not check at the moment if the first or the last entries
        were deleted. If we want to do this, we need to store some signed
        meta information
        1. Which one was the first entry. (use initialize_log)
        2. Which one was the last entry.
        '''
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
        except Exception as exx:
            log.error("exception %r" % exx)
            log.error("%s" % traceback.format_exc())
            # self.session.rollback()
        finally:
            # self.session.close()
            pass
            
        return res
    
    def _log_to_string(self, le):
        '''
        This function creates a string from the logentry so
        that this string can be signed.
        
        Note: Not all elements of the LogEntry are used to generate the
        string (the Signature is not!), otherwise we could have used pickle
        '''
        s = "id=%s,date=%s,action=%s,succ=%s,serial=%s,t=%s,u=%s,r=%s,adm=%s,ad=%s,i=%s,ps=%s,c=%s,l=%s,cl=%s" % ( 
            le.id,
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
        
    def _get_logentry_attribute(self, key):
        '''
        This function returns the LogEntry attribute for the given key value
        '''
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
                    'clearance_level': LogEntry.clearance_level}
        return sortname.get(key)
        
    def search(self, search_dict, rp_dict):
        '''
        This function returns the audit log as a list of dictionaries.
        '''
        res = []
        auditIter = self.searchQuery(search_dict, rp_dict=rp_dict)
        try:
            le = auditIter.next()
            while le:
                # Fill the list
                res.append(self.audit_entry_to_dict(le))
                le = auditIter.next()
        except StopIteration:
            pass
        return res
        
    def searchQuery(self, search_dict, rp_dict):
        '''
        This function returns the audit log as an iterator on the result
        '''
        logentries = None
        try:
            limit = int(rp_dict.get('rp', 15))
            offset = (int(rp_dict.get('page', 1)) - 1) * limit
            
            # create filter condition
            filter_condition = self._create_filter(search_dict)
            
            if rp_dict.get("sortorder") == "desc":
                logentries = self.session.query(LogEntry)\
                                         .filter(filter_condition)\
                                         .order_by(desc(self._get_logentry_attribute(rp_dict.get("sortname"))))\
                                         .limit(limit)\
                                         .offset(offset)
            else:
                logentries = self.session.query(LogEntry)\
                                         .filter(filter_condition)\
                                         .order_by(asc(self._get_logentry_attribute(rp_dict.get("sortname"))))\
                                         .limit(limit)\
                                         .offset(offset)

        except Exception as exx:
            log.error("exception %r" % exx)
            log.error("%s" % traceback.format_exc())
            self.session.rollback()
        finally:
            self.session.close()

        if logentries is None:
            return iter([])
        else:
            return iter(logentries)
    
    def audit_entry_to_dict(self, audit_entry):
        sig = self._verify_sig(audit_entry)
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
                      'administrator': audit_entry.administrator,
                      'action_detail': audit_entry.action_detail,
                      'info': audit_entry.info,
                      'privacyidea_server': audit_entry.privacyidea_server,
                      'client': audit_entry.client,
                      'log_level': audit_entry.loglevel,
                      'clearance_level': audit_entry.clearance_level
                      }
        return audit_dict
    
#########################################################################
#
# To be run at the command line to clean the logs
#

import os
import sys
from getopt import getopt, GetoptError
import ConfigParser


def usage():
    print('''cleanup audit database according to:
        privacyideaAudit.sql.highwatermark and
        privacyideaAudit.sql.lowwatermark
        
    Parameter:
    -f, --file <privacyidea.ini file>
    --high <high watermark>
    --low  <low wartermark>
    ''')


def cleanup_db(filename, highwatermark=None, lowwatermark=None):

    config_path = os.path.abspath(os.path.dirname(filename))
    config = ConfigParser.ConfigParser()
    config.read(filename)
    # Set the current path, which we might need, if we are using sqlite
    config.set("DEFAULT", "here", config_path)
    config.set("app:main", "here", config_path)
    # get the type - we only work for sqlaudit
    audit_type = config.get("DEFAULT", "privacyideaAudit.type")
    if audit_type != "privacyidea.lib.auditmodules.sqlaudit":
        raise Exception("We only work with audit type sql. %s given."
                        % audit_type)
    
    if not highwatermark:
        try:
            highwatermark = config.get("DEFAULT",
                                       "privacyideaAudit.sql.highwatermark")
        except ConfigParser.NoOptionError:
            highwatermark = 10000
        
    if not lowwatermark:
        try:
            lowwatermark = config.get("DEFAULT",
                                      "privacyideaAudit.sql.lowwatermark")
        except ConfigParser.NoOptionError:
            lowwatermark = 5000
    
    try:
        sql_url = config.get("DEFAULT", "privacyideaAudit.sql.url")
    except ConfigParser.NoOptionError:
        sql_url = config.get("app:main", "sqlalchemy.url")
        
    print "Cleaning up with high: %s, low: %s. %s" % (highwatermark,
                                                      lowwatermark,
                                                      sql_url)
    
    engine = create_engine(sql_url)
    # create a configured "Session" class
    session = sessionmaker(bind=engine)()
    # create a Session
    metadata.create_all(engine)
    count = session.query(LogEntry.id).count()
    for l in session.query(LogEntry.id).order_by(desc(LogEntry.id)).limit(1):
        last_id = l[0]
    print "The log audit log has %i entries, the last one is %i" % (count,
                                                                    last_id)
    # deleting old entries
    if count > highwatermark:
        print "More than %i entries, deleting..." % highwatermark
        cut_id = last_id - lowwatermark
        # delete all entries less than cut_id
        print "Deleting entries smaller than %i" % cut_id
        session.query(LogEntry.id).filter(LogEntry.id < cut_id).delete()
        session.commit()
    

def main():

    filename = None
    highwatermark = None
    lowwatermark = None
    try:
        opts, _args = getopt(sys.argv[1:], "hf:", ["help",
                                                   "file=",
                                                   "high=",
                                                   "low="])

    except GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ('-f', '--file'):
            filename = arg
        elif opt in ('-h', '--help'):
            usage()
            sys.exit(1)
        elif opt in ('--high'):
            highwatermark = int(arg)
        elif opt in ('--low'):
            lowwatermark = int(arg)

    if filename:
        cleanup_db(filename,
                   highwatermark=highwatermark,
                   lowwatermark=lowwatermark)
    else:
        usage()
        sys.exit(2)

if __name__ == '__main__':
    main()
    
