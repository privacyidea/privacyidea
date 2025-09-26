# (c) NetKnights GmbH 2025,  https://netknights.it
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
# SPDX-FileCopyrightText: 2025 Paul Lettich <paul.lettich@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
"""This is the BaseClass for audit trails

The audit is supposed to work like this. First we need to create an audit
object. E.g. this can be done in the before_request::

    g.audit_object = getAudit(file_config)

During the request, the g.audit_object can be used to add audit information::

    g.audit_object.log({"client": "123.2.3.4", "action": "validate/check"})

Thus, at many different places in the code, audit information can be added to
the audit object.
Finally, the audit_object needs to be stored to the audit storage. So we call::

    g.audit_object.finalize_log()

which creates a signature of the audit data and writes the data to the audit
storage.
"""

import logging
import traceback
from typing import Union, Optional

from privacyidea.lib.log import log_with
import datetime

log = logging.getLogger(__name__)


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
        self.page = 1
        # the total entry numbers
        self.total = 0


class Audit(object):  # pragma: no cover

    is_readable = False

    def __init__(self, config=None, startdate=None):
        """
        Create a new audit object.

        :param config: The web config is passed to the audit module, so that
                       the special module implementation can get its configuration.
        :type config: dict
        :param startdate: The datetime of the beginning of the request
        :type startdate: datetime.datetime
        :return: Audit object
        """
        self.name = "AuditBase"
        self.audit_data = {'startdate': startdate or datetime.datetime.now()}
        self.config = config or {}
        self.private = b""
        self.public = b""

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
        passing the values:

        .. code-block:: python

            priv = config.get("privacyideaAudit.key.private")
            pub = config.get("privacyideaAudit.key.public")

        :param pub: Public key, used for verifying the signature
        :type pub: string with filename
        :param priv: Private key, used to sign the audit entry
        :type priv: string with filename
        :return: None
        """
        try:
            with open(priv, "rb") as privkey_file:
                self.private = privkey_file.read()
            with open(pub, 'rb') as pubkey_file:
                self.public = pubkey_file.read()
        except Exception as e:
            log.error("Error reading key file: {0!r})".format(e))
            log.debug(traceback.format_exc())
            raise e

    def get_audit_id(self):
        return self.name

    @property
    def available_audit_columns(self):
        return ['number', 'action', 'success', 'authentication', 'serial', 'date', 'startdate',
                'duration', 'token_type', 'user', 'realm', 'administrator',
                'action_detail', 'info', 'privacyidea_server', 'client',
                'user_agent', 'user_agent_version',
                'log_level', 'policies', 'clearance_level', 'sig_check',
                'missing_line', 'resolver', 'thread_id', 'container_serial', 'container_type']

    def get_total(self, param: dict, admin_params: Optional[dict] = None, AND: bool = True, display_error: bool = True,
                  timelimit: Optional[datetime.timedelta] = None) -> int:
        """
        This method returns the total number of audit entries
        in the audit store
        """
        return 0

    @property
    def has_data(self):
        # We check if there is actually audit_data with an action.
        # Since the audit_data is initialized with the startdate.
        return bool(self.audit_data and "action" in self.audit_data)

    @log_with(log)
    def log(self, param):
        """
        This method is used to log the data.
        During a request this method can be called several times to fill the
        internal audit_data dictionary.

        Add new log details in param to the internal log data self.audit_data.

        :param param: Log data that is to be added
        :type param: dict
        :return: None
        """
        for k, v in param.items():
            self.audit_data[k] = v

    def add_to_log(self, param, add_with_comma=False):
        """
        Add to existing log entry.

        :param param:
        :param add_with_comma: If set to true, new values will be appended comma separated
        :return:
        """
        for k, v in param.items():
            if k not in self.audit_data:
                # We need to create the entry
                self.audit_data[k] = v
            else:
                if add_with_comma:
                    self.audit_data[k] += ","
                self.audit_data[k] += v

    def add_policy(self, policy_names: Union[set, list, str]):
        """
        This method adds triggered policy names to the list of triggered policies.

        :param policy_names: A set, list or single policy name(s)
        :return:
        """
        audit_policies = set(self.audit_data.get('policies', []))
        if isinstance(policy_names, str):
            audit_policies.add(policy_names)
        elif isinstance(policy_names, list):
            policy_names = set(policy_names)
        if isinstance(policy_names, set):
            audit_policies.update(policy_names)
        self.audit_data["policies"] = list(audit_policies)

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
        Therefor the same parameters are passed as in the log method.
        """
        pass

#    def set(self):
#        """
#        This function could be used to set certain things like the signing key.
#        But maybe it should only be read from pi.cfg?
#        """
#        pass

    def search(self, search_dict: dict, admin_params: Optional[dict] = None, page_size: int = 15, page: int = 1,
               sortorder: str = "asc", timelimit: Optional[datetime.timedelta] = None):
        """
        This function is used to search audit events.

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
        return Paginate()

    def get_count(self, search_dict, timedelta=None, success=None):
        """
        Returns the number of found log entries.
        E.g. used for checking the timelimit.

        :param param: List of filter parameters
        :return: number of found entries
        """
        return 0

    def csv_generator(self, param: Optional[dict] = None, admin_params: Optional[dict] = None, user=None,
                      timelimit: Optional[datetime.timedelta] = None):
        """
        A generator that can be used to stream the audit log

        :param param:
        :return:
        """
        pass

    def search_query(self, search_dict: dict, admin_params: Optional[dict] = None, page_size: int = 15, page: int = 1,
                     sortorder: str = "asc", sortname: str = "number", timelimit: Optional[datetime.timedelta] = None):
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
