# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
'''This is the BaseClass for audit trails
'''


import logging
log = logging.getLogger(__name__)
from pylons import config
from pylons import tmpl_context as c
from pylons import request
from privacyidea.lib.log import log_with
import socket

import json


from privacyidea.lib.token import getTokenNumResolver

@log_with(log)
def getAuditClass(packageName, className):
    """
        helper method to load the Audit class from a given
        package in literal:

        example:

            getAuditClass("SQLAudit", "Audit")

        check:
            checks, if the log method exists
            if not an error is thrown

"""
    if packageName is None:
        log.error("No suiteable Audit Class found. Working with dummy AuditBase class.")
        packageName = "privacyidea.lib.auditmodules"
        className = "AuditBase"

    mod = __import__(packageName, globals(), locals(), [className])
    klass = getattr(mod, className)
    log.debug("klass: %s" % klass)
    if not hasattr(klass, "log"):
        raise NameError("Audit AttributeError: " + packageName + "." + \
              className + " instance has no attribute 'log'")
        return ""
    else:
        return klass

@log_with(log)
def getAudit():
    audit_type = config.get("privacyideaAudit.type")
    audit = getAuditClass(audit_type, "Audit")()
    return audit


def logTokenNum():
    # log the number of the tokens
    c.audit['action_detail'] = "tokennum = %s" % str(getTokenNumResolver())

class AuditBase(object):
    ## TODO: Fix: remove the fixed private key
    private = '''-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEArSQlRpXLI+GzARnqOe+XKEv5dy59pefcx/nXt5GGwzAthyiS
lH1oC4VwFgEyh1nvM9pOtQ2sDg5EnpCOTxkGoX+wS9mqpF5S9QhJP5IkrGn4wmIC
NPpCC3ZAzPu8TH2uFzmp8jKzbevtj6s+WodlwFUGVxD55mht2oCcD97elUmNecgQ
TmKU1r9BFt6ZEsDxXUvC1fOWStUwZnj3Heu8Hgte/5BvyBnAaK4QEfga6bKXHi33
80EMTgOYlko1Zl8xJW+QXcAiaF1yqyFqM7FjYVZOZtt0iMy9OsSXw3uT0Te05zaG
qofj9yrtTCuMrf0KxukpgGbwobirh3T+Qnr+pwIDAQABAoIBAHCJTuUrFadT2sp7
cp+HmAMsJpCNmkOMihc80DZTk3koxl7UQznarRbX+3uB+bq5/N0CJyhNI6jbI0TB
Bo5o4MN1wDv81YoSeO8lHJ8COW4LTxHhLDgM9YKHsSTK9p/tDIuyAkEXLULkFzvL
fTLQUJWLbhyHPzbAZ66e61DxdlEnNMEBsQKDKQ51U4TxtHIsYxzThC2sxSSg7keo
lIAp7j913Z7YMSmAJ+eV3A1yfEuxzoxYfNBtFxxeszVIuTjznwcKxs2TWpYxikv8
kmdx654I5UZWsupLRxpJL8L+R1c9J2k9Zeu68WU+1rrjBdnqp3IyxpkPtvWNVXZW
Z84B9zkCgYEA2f56F3H6AZNERIEHGDfGKijvEvhTryuLTdxa8Kt0EbCe1QPgZnBa
bNghEfhuXEIhiBv9V01Au+ljbh1DK7iuThprEIOKzESaPcBTmNYWTUQaaxxlwlDG
ipxjmLZYc+BNFcdAEHxvGfHwfz4GJfhqyUxcnkg2YllItvJn5+DA2yMCgYEAy1PL
G7wUqCTbrb2vfmFMx8MdiSxjuL36Lu7Gx59BiGph4InI57IXSiSP1NWkWIEzCibW
a1X+P9t4iKJ1pTbiSBsntLHNraIeOneUIJY/EFItY+xpj5KDRw+HqDn55sXLCT5n
UabSoTyYYacUTIHAbU8lEW5+Efr7KR2w5uz/+K0CgYEAgEmqQDHrFxI7krT8H9xy
2kzMpTVOyj+t81xCiG/eFqsCTgnB/YcRMAzhKVoyWEjyws72AHKOLgfjY+IEra45
pe0WJNnEzQFyY/TTPZZ/+Wiiw3YqzHgM33W5hx2IYGkX9EEWCp2wJGylQ7yUkbPn
5B70QpHsr2Qrzr5JN8SkulECgYBIeuxSTK+IaOsuegnPIVw/cZxbw8kgmAhRJqkR
jAHOYS3W3wcRIPkQYwwqsKXPLu9E1SdmR9dEaDYFbvRFGtV7IsL6tM8+8CWabfoN
y8FbThAEKMhQd8f4Ut7m5xPgYe3Is8gc4T0AYRto5ChmRXKVBLuQBTVHr5JMy9q9
1wpAWQKBgF0O/coMgJdp983OW7TEK1AgpW19cRVVR564dyZ8F81UwWCzOJqYfSsq
4R7DlPp68IXz7Lg+pCL3T5CweL2ibRTSB2SjukwjGzdeSHbkwI8YEzbH7yIT+Icm
ROxsxyEsfAZEJ5PwTNcARl15QOl4gF2kdFAzlZLz14kioZunMQyL
-----END RSA PRIVATE KEY-----'''
    public = '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArSQlRpXLI+GzARnqOe+X
KEv5dy59pefcx/nXt5GGwzAthyiSlH1oC4VwFgEyh1nvM9pOtQ2sDg5EnpCOTxkG
oX+wS9mqpF5S9QhJP5IkrGn4wmICNPpCC3ZAzPu8TH2uFzmp8jKzbevtj6s+Wodl
wFUGVxD55mht2oCcD97elUmNecgQTmKU1r9BFt6ZEsDxXUvC1fOWStUwZnj3Heu8
Hgte/5BvyBnAaK4QEfga6bKXHi3380EMTgOYlko1Zl8xJW+QXcAiaF1yqyFqM7Fj
YVZOZtt0iMy9OsSXw3uT0Te05zaGqofj9yrtTCuMrf0KxukpgGbwobirh3T+Qnr+
pwIDAQAB
-----END PUBLIC KEY-----'''

    def __init__(self):
        self.name = "AuditBase"

    @log_with(log)
    def initialize(self):
        # defaults
        c.audit = {'action_detail' : '',
                   'info' : '',
                   'log_level' : 'INFO',
                   'administrator' : '',
                   'value' : '',
                   'key' : '',
                   'serial' : '',
                   'token_type' : '',
                   'clearance_level' : 0,
                   'privacyidea_server' : socket.gethostname(),
                   'realm' : '',
                   'user' : '',
                   'client' : ''
                   }
        c.audit['action'] = "%s/%s" % (
                        request.environ['pylons.routes_dict']['controller'],
                        request.environ['pylons.routes_dict']['action'])

    @log_with(log)
    def readKeys(self):
        priv = config.get("privacyideaAudit.key.private")
        pub = config.get("privacyideaAudit.key.public")
        try:
            f = open(priv, "r")
            self.private = f.read()
            f.close()
        except Exception as e:
            log.error("Error reading private key %s: (%r)" % (priv, e))

        try:
            f = open(pub, "r")
            self.public = f.read()
            f.close()
        except Exception as e:
            log.error("Error reading public key %s: (%r)" % (pub, e))


    def getAuditId(self):
        return self.name

    def getTotal(self, param, AND=True, display_error=True):
        '''
        This method returns the total number of audit entries in the audit store
        '''
        return None

    @log_with(log)
    def log(self, param):
        '''
        This method is used to log the data.
        It should hash the data and do a hash chain and sign the data
        '''
        pass

    def initialize_log(self, param):
        '''
        This method initialized the log state.
        The fact, that the log state was initialized, also needs to be logged.
        Therefor the same params are passed as i the log method.
        '''
        pass

    def set(self):
        '''
        This function could be used to set certain things like the signing key.
        But maybe it should only be read from privacyidea.ini?
        '''
        pass

    def search(self, param, AND=True, display_error=True, rp_dict=None):
        '''
        This function is used to search audit events.

        param:
            Search parameters can be passed.

        return:
            A list of dictionaries is return.
            Each list element denotes an audit event.
            
        This function is deprecated.
        '''
        if rp_dict == None:
            rp_dict = {}
        result = [ {} ]
        return result
    
    def searchQuery(self, search_dict, rp_dict):
        '''
        This function returns the audit log as an iterator on the result
        '''
        return None
    
    def audit_entry_to_dict(self, audit_entry):
        '''
        If the searchQuery returns an iteretor with elements that are not a dictionary, the audit module needs
        to provide this function, to convert the audit entry to a dictionary.
        '''
        return {}

@log_with(log)
def search(param, user=None, columns=None):

    audit = getAudit()
    
    search_dict = {}

    if param.has_key("query"):
        if "extsearch" == param['qtype']:
            # search patterns are delimitered with ;
            search_list = param['query'].split(";")
            for s in search_list:
                log.debug(s)
                key, e, value = s.partition("=")
                key = key.strip()
                value = value.strip()
                search_dict[key] = value
            log.debug(search_dict)

        else:
            search_dict[param['qtype']] = param["query"]
    else:
        for k, v in param.items():
            search_dict[k] = v

    log.debug("search_dict: %s" % search_dict)

    rp_dict = {}
    rp_dict['page'] = param.get('page')
    page = 1
    if param.get('page'):
        page = param.get('page')

    rp_dict['rp'] = param.get('rp')
    rp_dict['sortname'] = param.get('sortname')
    rp_dict['sortorder'] = param.get('sortorder')
    log.debug("[rp_dict: %s" % rp_dict)
    if user:
        search_dict['user'] = user.login
        search_dict['realm'] = user.realm

    result = audit.search(search_dict, rp_dict=rp_dict)

    lines = []
    if columns:
        # In this case we have only a limited list of columns, like in
        # the selfservice portal
        for a in result:
            if a.has_key('number'):
                cell = []
                for c in columns:
                    cell.append(a.get(c))
                lines.append({'id': a['number'],
                              'cell' : cell
                              })
    else:
        # Here we use all columns, that exist
        for a in result:
            if a.has_key('number'):
                lines.append(
                    { 'id' : a['number'],
                        'cell': [
                            a.get('number', ''),
                            a.get('date', ''),
                            a.get('sig_check', ''),
                            a.get('missing_line', ''),
                            a.get('action', ''),
                            a.get('success', ''),
                            a.get('serial', ''),
                            a.get('token_type', ''),
                            a.get('user', ''),
                            a.get('realm', ''),
                            a.get('administrator', ''),
                            a.get('action_detail', ''),
                            a.get('info', ''),
                            a.get('privacyidea_server', ''),
                            a.get('client', ''),
                            a.get('log_level', ''),
                            a.get('clearance_level', ''),
                             ]
                    }
                )
    # get the complete number of audit logs
    total = audit.getTotal(search_dict)

    return lines, total, page


class AuditIterator(object):

    def __init__(self, param, user=None, columns=None):
        self.param = param
        self.user = user
        self.columns = columns
        self.count = 0
        self.last = None
        self.page = 1
        self.audit = None
        self.iter = None
        self.headers = False
        self.search_dict = {}
        self.audit = getAudit()

    def __iter__(self):
        """
        start iteration
        """
        search_dict = {}
        param = self.param

        if 'headers' in param:
            self.headers = True
            del param['headers']

        if "query" in param:
            if "extsearch" == self.param['qtype']:
                # search patterns are delimited with ;
                search_list = param['query'].split(";")
                for s in search_list:
                    log.debug(s)
                    key, e, value = s.partition("=")
                    key = key.strip()
                    value = value.strip()
                    search_dict[key] = value
                log.debug(search_dict)

            else:
                search_dict[param['qtype']] = param["query"]
        else:
            for k, v in param.items():
                search_dict[k] = v

        log.debug("search_dict: %s" % search_dict)

        rp_dict = {}
        page = param.get('page', None) or None
        if page is not None:
            rp_dict['page'] = param.get('page')
        self.page = param.get('page', 1)


        rp_dict['rp'] = param.get('rp', '15') or '15'


        rp_dict['sortname'] = param.get('sortname')
        rp_dict['sortorder'] = param.get('sortorder')
        log.debug("rp_dict: %s" % rp_dict)

        if self.user:
            search_dict['user'] = self.user.login
            search_dict['realm'] = self.user.realm

        # fetch the query iterator
        self.iter = self.audit.searchQuery(search_dict, rp_dict=rp_dict)
        self.search_dict = search_dict

        return self

    def next(self):
        """
        call the sql alchemy row/result iterator
        :return: row as a dict
        """

        entry = {}
        a = self.iter.next()

        if type(a) != dict:
            ## convert table data to dict!
            a = self.audit.audit_entry_to_dict(a)

        columns = self.columns
        if columns:
            # In this case we have only a limited list of columns, like in
            # the selfservice portal
            if 'number' in a:
                cell = []
                for c in columns:
                    cell.append(a.get(c))

                lentry = {'id': a['number'],
                              'cell' : cell
                              }
        else:
            # Here we use all columns, that exist
            if 'number' in a:
                entry = { 'id' : a['number'],
                        'cell': [
                            a.get('number', ''),
                            a.get('date', ''),
                            a.get('sig_check', ''),
                            a.get('missing_line', ''),
                            a.get('action', ''),
                            a.get('success', ''),
                            a.get('serial', ''),
                            a.get('token_type', ''),
                            a.get('user', ''),
                            a.get('realm', ''),
                            a.get('administrator', ''),
                            a.get('action_detail', ''),
                            a.get('info', ''),
                            a.get('privacyidea_server', ''),
                            a.get('client', ''),
                            a.get('log_level', ''),
                            a.get('clearance_level', ''),
                             ],
                    }
                if self.headers is True:
                    entry['data'] = [
                            'number',
                            'date',
                            'sig_check',
                            'missing_line',
                            'action',
                            'success',
                            'serial',
                            'token_type',
                            'user',
                            'realm',
                            'administrator',
                            'action_detail',
                            'info',
                            'privacyidea_server',
                            'client',
                            'log_level',
                            'clearance_level',
                                     ]

            return entry

class JSONAuditIterator(AuditIterator):
    """
    default audit output generator in json format
    """
    def __init__(self, param, user=None, columns=None):
        self.parent = super(JSONAuditIterator, self)
        self.parent.__init__(param, user=user, columns=columns)
        self.count = 0
        self.last = None

    def next(self):
        """
        iterator callback for the next chunk of data

        :return: returns a string representing the data row
        """
        if self.last is not None:
            raise self.last

        try:
            entry = self.parent.next()
        except Exception as exx:
            self.last = exx
            # get the complete number of audit logs
            total = self.audit.getTotal(self.search_dict)
            #closing = '], "total": %d, }' % self.total
            closing = '], "total": %d }' % int(total)
            return closing

        entry_s = json.dumps(entry, indent=3)

        if self.count == 0:
            result = ('{ "page": %d, "rows": [ %s' %
                         (int(self.page), entry_s))
            self.count = self.count + 1
        else:
            result = ", " + entry_s
        return result

class CSVAuditIterator(AuditIterator):
    """
    create cvs output by iterating over result
    """

    def __init__(self, param, user=None, columns=None):
        self.parent = super(CSVAuditIterator, self)
        self.parent.__init__(param, user=user, columns=columns)
        self.count = 0
        self.last = None
        self.delimiter = param.get('delimiter', ',') or ','

    def next(self):
        """
        iterator callback for the next chunk of data

        :return: returns a string representing the data row
        """
        result = ""

        if self.last is not None:
            raise self.last

        try:
            entry = self.parent.next()
        except Exception as exx:
            self.last = exx
            return "\n"

        if self.headers is True and self.count == 0:
            # Do the header
            row = entry.get('data', [])
            r_str = json.dumps(row)[1:-1]

            result += r_str
            result += "\n"


        row = []
        raw_row = entry.get('cell', [])

        ## we must escape some dump entries, which destroy the
        ## import of the csv data - like SMSProviderConfig 8-(
        for row_entry in raw_row:
            if type(row_entry) in (str, unicode):
                row_entry = row_entry.replace('\"', "'")
            row.append(row_entry)

        r_str = json.dumps(row)[1:-1]
        result += r_str
        result += "\n"

        self.count = self.count + 1

        return result

###eof#########################################################################
