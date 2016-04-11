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

    g.audit_object = getAudit(file_config)

During the request, the g.audit_object can be used to add audit information:

    g.audit_object.log({"client": "123.2.3.4", "action": "validate/check"})

Thus at many different places in the code, audit information can be added to
the audit object.
Finally the audit_object needs to be stored to the audit storage. So we call:

    g.audit_object.finalize_log()

which creates a signature of the audit data and writes the data to the audit
storage.
"""

import logging
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with
import socket
from datetime import datetime, timedelta


class Paginate(object):
    """
    This is a pagination object, that is used for searching audit trails.
    """
    def __init__(self):
        # The audit data
        self.auditdata = []
        # The number of the previous page
        self.prev = None
        # the number of the next page
        self.next = None
        # the number of the current page
        self.current = 1
        # the total entry numbers
        self.total = 0
    

class Audit(object):  # pragma: no cover

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
        self.audit_data['action_detail'] = "tokennum = {0!s}".format(str(count))

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
            log.error("Error reading private key {0!s}: ({1!r})".format(priv, e))
            raise e

        try:
            f = open(pub, "r")
            self.public = f.read()
            f.close()
        except Exception as e:
            log.error("Error reading public key {0!s}: ({1!r})".format(pub, e))
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
    def log(self, param):  # pragma: no cover
        """
        This method is used to log the data.
        During a request this method can be called several times to fill the
        internal audit_data dictionary.
        """
        pass

    def add_to_log(self, param):
        """
        Add to existing log entry
        :param param:
        :return:
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

#    def set(self):
#        """
#        This function could be used to set certain things like the signing key.
#        But maybe it should only be read from pi.cfg?
#        """
#        pass

    def search(self, param, display_error=True, rp_dict=None):
        """
        This function is used to search audit events.

        param: Search parameters can be passed.

        return: A pagination object


        This function is deprecated.
        """
        return Paginate()

    def get_count(self, search_dict, timedelta=None, success=None):
        """
        Returns the number of found log entries.
        E.g. used for checking the timelimit.

        :param param: List of filter parameters
        :return: number of found entries
        """
        return 0

    def csv_generator(self, param):
        """
        A generator that can be used to stream the audit log

        :param param:
        :return:
        """
        pass

    def search_query(self, search_dict, rp_dict):
        """
        This function returns the audit log as an iterator on the result
        """
        return None

    def audit_entry_to_dict(self, audit_entry):
        """
        If the search_query returns an iterator with elements that are not a
        dictionary, the audit module needs
        to provide this function, to convert the audit entry to a dictionary.
        """
        return {}

    def get_dataframe(self, start_time=datetime.now()-timedelta(days=7),
                      end_time=datetime.now()):
        """
        The Audit module can handle its data the best. This function is used
        to return a pandas.dataframe with all audit data in the given time
        frame.

        This dataframe then can be used for extracting statistics.

        :param start_time: The start time of the data
        :type start_time: datetime
        :param end_time: The end time of the data
        :type end_time: datetime
        :return: Audit data
        :rtype: dataframe
        """
        return None
