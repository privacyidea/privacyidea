# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2014-10-17 Fix the empty result problem
#             Cornelius Kölbel, <cornelius@privacyidea.org>
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
__doc__="""This is the BaseClass for audit trails

The audit is supposed to work like this. First we need to create an audit
object. E.g. this can be done in the before_request:

    g["audit_obj"] = getAudit(file_config)

During the request, the g.audit_obj can be used to add audit information:

    g["audit_obj"].log({"client": "123.2.3.4", "action": "validate/check"})

Thus at many different places in the code, audit information can be added to
the audit object.
Finally the audit_object needs to be stored to the audit storage. So we call:

    g["audit_obj"].finalize_log()

which creates a signature of the audit data and writes the data to the audit
storage.
"""

import logging
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with
import socket
import json


@log_with(log)
def getAuditClass(packageName, className):
    """
    helper method to load the Audit class from a given
    package in literal:

    example:

        getAuditClass("privacyidea.lib.auditmodules.sqlaudit", "Audit")

    check:
        checks, if the log method exists
        if not an error is thrown

    """
    if packageName is None:
        log.error("No suiteable Audit Class found. Working with dummy "
                  "AuditBase class.")
        packageName = "privacyidea.lib.auditmodules"
        className = "AuditBase"

    mod = __import__(packageName, globals(), locals(), [className])
    klass = getattr(mod, className)
    log.debug("klass: %s" % klass)
    if not hasattr(klass, "log"):
        raise NameError("Audit AttributeError: " + packageName + "." +
                        className + " instance has no attribute 'log'")
    return klass


@log_with(log)
def getAudit(config):
    """
    This wrapper function creates a new audit object based on the config
    from the config file. The config file entry could look like this:

        privacyideaAudit.module = privacyidea.lib.auditmodules.sqlaudit

    Each audit module (at the moment only SQL) has its own additional config
    entries.

    :param config: The config entries from the file config
    :return: Audit Object
    """
    audit_module = config.get("privacyideaAudit.module")
    audit = getAuditClass(audit_module, "Audit")(config)
    return audit



@log_with(log)
def search(param, user=None, columns=None):

    audit = getAudit()

    search_dict = {}

    if "query" in param:
        if "extsearch" == param['qtype']:
            # search patterns are delimitered with ;
            search_list = param['query'].split(";")
            for s in search_list:
                log.debug(s)
                key, _e, value = s.partition("=")
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
            if "number" in a:
                cell = []
                for c in columns:
                    cell.append(a.get(c))
                lines.append({'id': a['number'],
                              'cell': cell
                              })
    else:
        # Here we use all columns, that exist
        for a in result:
            if "number" in a:
                lines.append({'id': a['number'],
                              'cell': [a.get('number', ''),
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



class AuditBase(object):

    def __init__(self, config=None):
        """
        Create a new audit object.

        :param config: The web config is passed to the audit module, so that
        the special module implementation can get its configuration.
        :type config: dict
        :return:
        """
        self.name = "AuditBase"
        self.audit_data = {}
        self.private = ""
        self.public = ""

    @log_with(log)
    def initialize(self):
        # defaults
        self.audit_data = {'action_detail': '',
                   'info': '',
                   'log_level': 'INFO',
                   'administrator': '',
                   'value': '',
                   'key': '',
                   'serial': '',
                   'token_type': '',
                   'clearance_level': 0,
                   'privacyidea_server': socket.gethostname(),
                   'realm': '',
                   'user': '',
                   'client': ''
                   }
        #controller = request.environ['pylons.routes_dict']['controller']
        #action = request.environ['pylons.routes_dict']['action']
        #c.audit['action'] = "%s/%s" % (controller, action)

    def log_token_num(self, count):
        """
        Log the number of the tokens.
        Can be passed like
        log_token_num(get_tokens(count=True))

        :param count: Number of tokens
        :type count: int
        :return:
        """
        self.audit_data['action_detail'] = "tokennum = %s" % str(count)


    @log_with(log)
    def read_keys(self, pub, priv):
        """
        Set the private and public key for the audit class. This is achieved by
        passing the entries.

        #priv = config.get("privacyideaAudit.key.private")
        #pub = config.get("privacyideaAudit.key.public")

        :param pub: Public key, used for verifying the signature
        :type pub: string with filename
        :param priv: Private key, used to sign the audit entry
        :type priv: string with filename
        :return: None
        """

        try:
            f = open(priv, "r")
            self.private = f.read()
            f.close()
        except Exception as e:
            log.error("Error reading private key %s: (%r)" % (priv, e))
            raise e

        try:
            f = open(pub, "r")
            self.public = f.read()
            f.close()
        except Exception as e:
            log.error("Error reading public key %s: (%r)" % (pub, e))
            raise e

    def get_audit_id(self):
        return self.name

    def get_total(self, param, AND=True, display_error=True):
        """
        This method returns the total number of audit entries
        in the audit store
        """
        return None

    @log_with(log)
    def log(self, param):
        """
        This method is used to log the data.
        During a request this method can be called several times to fill the
        internal audit_data dictionary.
        """
        pass

    def finalize_log(self):
        """
        This method is called to finalize the audit_data. I.e. sign the data
        and write it to the database.
        It should hash the data and do a hash chain and sign the data
        """
        pass

    def initialize_log(self, param):
        """
        This method initialized the log state.
        The fact, that the log state was initialized, also needs to be logged.
        Therefor the same params are passed as i the log method.
        """
        pass

    def set(self):
        """
        This function could be used to set certain things like the signing key.
        But maybe it should only be read from privacyidea.ini?
        """
        pass

    def search(self, param, AND=True, display_error=True, rp_dict=None):
        """
        This function is used to search audit events.

        param:
            Search parameters can be passed.

        return:
            A list of dictionaries is returned.
            Each list element denotes an audit event.
            
        This function is deprecated.
        """
        if rp_dict is None:
            rp_dict = {}
        result = [{}]
        return result
    
    def search_query(self, search_dict, rp_dict):
        """
        This function returns the audit log as an iterator on the result
        """
        return None
    
    def audit_entry_to_dict(self, audit_entry):
        """
        If the searchQuery returns an iteretor with elements that are not a
        dictionary, the audit module needs
        to provide this function, to convert the audit entry to a dictionary.
        """
        return {}


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
                    key, _e, value = s.partition("=")
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
            # convert table data to dict!
            a = self.audit.audit_entry_to_dict(a)

        columns = self.columns
        if columns:
            # In this case we have only a limited list of columns, like in
            # the selfservice portal
            if 'number' in a:
                cell = []
                for c in columns:
                    cell.append(a.get(c))

                # Fixme: why is this not used?
                _lentry = {'id': a['number'],
                           'cell': cell}
        else:
            # Here we use all columns, that exist
            if 'number' in a:
                entry = {'id': a['number'],
                         'cell': [a.get('number', ''),
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
                    entry['data'] = ['number',
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
        beginning = ""
        closing = ""
        cell = ""
        if self.last is not None:
            raise self.last

        if self.count == 0:
            beginning = ('{ "page": %d, "rows": [') % int(self.page)
            self.count = self.count + 1

        try:
            entry = self.parent.next()
        except Exception as exx:
            self.last = exx
            # get the complete number of audit logs
            total = self.audit.getTotal(self.search_dict)
            closing = '{} ], "total": %d }' % int(total)
            if self.count == 1:
                # There was no other entry and we just return an empty list
                return beginning + closing
            else:
                return closing

        entry_s = json.dumps(entry, indent=3)

        if self.count > 0:
            self.count = self.count + 1
            cell = entry_s + ", "
        return beginning + cell


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

        # we must escape some dump entries, which destroy the
        # import of the csv data - like SMSProviderConfig 8-(
        for row_entry in raw_row:
            if type(row_entry) in (str, unicode):
                row_entry = row_entry.replace('\"', "'")
            row.append(row_entry)

        r_str = json.dumps(row)[1:-1]
        result += r_str
        result += "\n"

        self.count += 1

        return result
