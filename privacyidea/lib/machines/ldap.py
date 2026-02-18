# SPDX-FileCopyrightText: 2015 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
#  2016-08-12 Sebastian Plattner
#             Allow hostname and machine ID being the same
#             LDAP attribute.
#  2015-03-02 Cornelius Kölbel <cornelius@privacyidea.org>
#             Initial writup
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
__doc__ = """This contains the LdapMachineResolver which resolves
the machines in an Active Directory.

The computer objects are identified by
    class=computer or sAMAccountType=805306369 (MachineAccount)
    * hostname: attribute dNSHostName
    * id: DN or objectSid
    * ip: N/A

The machine id can be the DN or the objectSid in this case.

This file is tested in tests/test_lib_machine_resolver_ldap.py in the class
LdapMachineTestCase
"""

import netaddr
import traceback
import logging

import ldap3

from .base import Machine
from .base import BaseMachineResolver
from .base import MachineResolverError
from privacyidea.lib.error import ResolverError
from privacyidea.lib.utils import is_true
from privacyidea.lib.resolvers.LDAPIdResolver import AUTHTYPE, DEFAULT_CA_FILE, IdResolver
from privacyidea.lib import _

log = logging.getLogger(__name__)


class LdapMachineResolver(BaseMachineResolver):

    type = "ldap"

    def __init__(self, name, config=None):
        self.i_am_bound = False
        super(LdapMachineResolver, self).__init__(name, config)

    def _bind(self):
        if not self.i_am_bound:
            try:
                server_pool = IdResolver.create_serverpool(self.uri, self.timeout,
                                                           tls_context=self.tls_context)
                self.connection = IdResolver.create_connection(authtype=self.authtype,
                                                               server=server_pool,
                                                               user=self.binddn,
                                                               password=self.bindpw,
                                                               receive_timeout=self.timeout,
                                                               auto_referrals=not self.noreferrals,
                                                               start_tls=self.start_tls)
                bound = self.connection.bind()
            except Exception as ex:
                msg = f"Error performing bind operation for machine resolver {self.name}: {ex}!"
                log.error(msg)
                raise ResolverError(msg)
            if not bound:
                result = self.connection.result
                log.error(f"LDAP Bind unsuccessful for machine resolver {self.name}: "
                          f"{result.get('description')} ({result.get('result')})!")
                raise ResolverError(f"Unable to perform bind operation for machine resolver {self.name}: "
                                    f"{result.get('description')} ({result.get('result')})")
            self.i_am_bound = True

    @staticmethod
    def _get_entry(entry_attribute, entries):
        if isinstance(entries.get(entry_attribute), list):
            entry = entries.get(entry_attribute)[0]
        else:
            entry = entries.get(entry_attribute)
        return entry

    @staticmethod
    def _create_ldap_filter(search_filter,
                            id_attribute, machine_id,
                            hostname_attribute, hostname,
                            ip_attribute, ip, substring=False, any=False):
        ldap_filter = "(&" + search_filter

        if not any:
            if id_attribute.lower() != "dn" and machine_id:
                if substring:
                    ldap_filter += "({0!s}=*{1!s}*)".format(id_attribute, machine_id)
                else:
                    ldap_filter += "({0!s}={1!s})".format(id_attribute, machine_id)
            if hostname:
                if substring:
                    ldap_filter += "({0!s}=*{1!s}*)".format(hostname_attribute, hostname)
                else:
                    ldap_filter += "({0!s}={1!s})".format(hostname_attribute, hostname)
            if ip:
                if substring:
                    ldap_filter += "({0!s}=*{1!s}*)".format(ip_attribute, ip)
                else:
                    ldap_filter += "({0!s}={1!s})".format(ip_attribute, ip)
        ldap_filter += ")"
        if any:
            # Now we need to extend the search filter
            # like this  (& (&(....)) (|(ip=...)(host=...)) )
            any_filter = "(|"
            if id_attribute:
                any_filter += "({0!s}=*{1!s}*)".format(id_attribute, any)
            if hostname_attribute:
                any_filter += "({0!s}=*{1!s}*)".format(hostname_attribute, any)
            if ip_attribute:
                any_filter += "({0!s}=*{1!s}*)".format(ip_attribute, any)
            any_filter += ")"

            ldap_filter = "(&{0!s}{1!s})".format(ldap_filter, any_filter)

        return ldap_filter

    def get_machines(self, machine_id=None, hostname=None, ip=None, any=None,
                     substring=False):
        """
        Return matching machines.

        :param machine_id: can be matched as substring
        :param hostname: can be matched as substring
        :param ip: cannot be matched as substring
        :param substring: Whether the filtering should be a substring matching
        :type substring: bool
        :param any: a substring that matches EITHER hostname, machineid or ip
        :type any: basestring
        :return: list of Machine Objects
        """
        machines = []
        self._bind()
        attributes = []
        if self.id_attribute.lower() != "dn":
            attributes.append(self.id_attribute)
        if self.ip_attribute:
            attributes.append(self.ip_attribute)
        if self.hostname_attribute:
            attributes.append(self.hostname_attribute)

        # do the filter depending on the searchDict
        ldap_filter = self._create_ldap_filter(self.search_filter,
                                               self.id_attribute, machine_id,
                                               self.hostname_attribute, hostname,
                                               self.ip_attribute, ip,
                                               substring, any)

        if self.id_attribute.lower() == "dn" and machine_id:
            self.connection.search(search_base=machine_id,
                                   search_scope=ldap3.BASE,
                                   search_filter=ldap_filter,
                                   attributes=attributes,
                                   paged_size=self.sizelimit)
        else:
            self.connection.search(search_base=self.basedn,
                                   search_scope=ldap3.SUBTREE,
                                   search_filter=ldap_filter,
                                   attributes=attributes,
                                   paged_size=self.sizelimit)

        # returns a list of dictionaries
        for entry in self.connection.response:
            dn = entry.get("dn")
            attributes = entry.get("attributes")

            try:
                if entry.get("type") == "searchResEntry":
                    machine = {}

                    if self.id_attribute.lower() == "dn":
                        machine['machineid'] = dn
                    else:
                        machine['machineid'] = self._get_entry(self.id_attribute, attributes)

                    machine['hostname'] = self._get_entry(self.hostname_attribute, attributes)
                    machine['ip'] = self._get_entry(self.ip_attribute, attributes)

                    if machine['ip']:
                        machine['ip'] = netaddr.IPAddress(machine['ip'])

                    machines.append(Machine(self.name,
                                            machine['machineid'],
                                            hostname=machine['hostname'],
                                            ip=machine['ip']))
            except Exception as exx:  # pragma: no cover
                log.error("Error during fetching LDAP objects: {0!r}".format(exx))
                log.debug("{0!s}".format(traceback.format_exc()))

        return machines

    def get_machine_id(self, hostname=None, ip=None):

        """
        Returns the machine id for a given hostname or IP address.

        If hostname and ip is given, the resolver should also check that the
        hostname matches the IP. If it can check this and hostname and IP do
        not match, then an Exception must be raised.

        :param hostname: The hostname of the machine
        :type hostname: basestring
        :param ip: IP address of the machine
        :type ip: netaddr
        :return: The machine ID, which depends on the resolver
        :rtype: basestring
        """
        machine_id = None
        machines = self.get_machines(hostname=hostname, ip=ip)
        if len(machines) > 1:
            raise Exception("More than one machine found in LDAP resolver {0!s}".format(
                            self.name))

        if len(machines) == 1:
            machine_id = machines[0].id
        return machine_id

    def load_config(self, config):
        """
        This loads the configuration dictionary, which contains the necessary
        information for the machine resolver to find and connect to the
        machine store.

        class=computer or sAMAccountType=805306369 (MachineAccount)
        * hostname: attribute dNSHostName
        * id: DN or objectSid
        * ip: N/A

        :param config: The configuration dictionary to run the machine resolver
        :type config: dict
        :return: None
        """
        self.uri = config.get("LDAPURI")
        if self.uri is None:
            raise MachineResolverError("LDAPURI is missing!")
        self.basedn = config.get("LDAPBASE")
        if self.basedn is None:
            raise MachineResolverError("LDAPBASE is missing!")
        self.binddn = config.get("BINDDN")
        self.bindpw = config.get("BINDPW")
        self.timeout = float(config.get("TIMEOUT", 5))
        self.sizelimit = config.get("SIZELIMIT", 500)
        self.hostname_attribute = config.get("HOSTNAMEATTRIBUTE")
        self.id_attribute = config.get("IDATTRIBUTE", "DN")
        self.ip_attribute = config.get("IPATTRIBUTE")
        self.search_filter = config.get("SEARCHFILTER",
                                        "(objectClass=computer)")

        self.noreferrals = is_true(config.get("NOREFERRALS", False))
        self.authtype = config.get("AUTHTYPE", AUTHTYPE.SIMPLE)
        self.start_tls = is_true(config.get("START_TLS", False))
        self.tls_verify = is_true(config.get("TLS_VERIFY", False))
        self.tls_ca_file = config.get("TLS_CA_FILE") or DEFAULT_CA_FILE
        self.tls_version = config.get("TLS_VERSION")
        self.tls_context = IdResolver._get_tls_context(ldap_uri=self.uri,
                                                       start_tls=self.start_tls,
                                                       tls_version=self.tls_version,
                                                       tls_verify=self.tls_verify,
                                                       tls_ca_file=self.tls_ca_file)

    @classmethod
    def get_config_description(cls):
        description = {cls.type: {"config": {"LDAPURI": "string",
                                             "LDAPBASE": "string",
                                             "BINDDN": "string",
                                             "BINDPW": "password",
                                             "TIMEOUT": "int",
                                             "SIZELIMIT": "int",
                                             "HOSTNAMEATTRIBUTE": "string",
                                             "IDATTRIBUTE": "string",
                                             "IPATTRIBUTE": "string",
                                             "SEARCHFILTER": "string",
                                             "NOREFERRALS": "bool",
                                             "AUTHTYPE": "string",
                                             "TLS_VERSION": "int",
                                             "TLS_VERIFY": "bool",
                                             "TLS_CA_FILE": "string",
                                             "START_TLS": "bool"
                                             }}}

        return description

    @staticmethod
    def testconnection(params):
        """
        Test if the given filename exists.

        :param params:
        :return:
        """
        success = False
        ldap_uri = params.get("LDAPURI")
        timeout = int(params.get("TIMEOUT", 5))
        start_tls = is_true(params.get("START_TLS", False)) and not ldap_uri.lower().startswith("ldaps")
        tls_context = IdResolver._get_tls_context(ldap_uri=ldap_uri,
                                                  start_tls=start_tls,
                                                  tls_version=params.get("TLS_VERSION"),
                                                  tls_verify=is_true(params.get("TLS_VERIFY")),
                                                  tls_ca_file=params.get("TLS_CA_FILE"))
        try:
            server_pool = IdResolver.create_serverpool(ldap_uri,
                                                       float(timeout),
                                                       tls_context=tls_context)
            conn = IdResolver.create_connection(authtype=params.get("AUTHTYPE", AUTHTYPE.SIMPLE),
                                                server=server_pool,
                                                user=params.get("BINDDN"),
                                                password=params.get("BINDPW"),
                                                receive_timeout=timeout,
                                                auto_referrals=not params.get("NOREFERRALS"),
                                                start_tls=start_tls)
            if not conn.bind():
                log.error(f"LDAP Bind unsuccessful: "
                          f"{conn.result.get('description')} ({conn.result.get('result')})!")
                raise ResolverError(f"Unable to perform bind operation: "
                                    f"{conn.result.get('description')} ({conn.result.get('result')})!")
            # search for users...
            conn.search(search_base=params["LDAPBASE"],
                        search_scope=ldap3.SUBTREE,
                        search_filter="(&" + params["SEARCHFILTER"] + ")",
                        attributes=[params["HOSTNAMEATTRIBUTE"]],
                        size_limit=params.get("SIZELIMIT", 500))
            elapsed_time = conn.usage.elapsed_time.total_seconds()
            count = len([x for x in conn.response if x.get("type") ==
                         "searchResEntry"])
            message = _(f"Your LDAP machine resolver configuration seems OK, "
                        f"{count} machine objects found in {elapsed_time:.4f} "
                        f"seconds.").format({"count": count, "elapsed_time": elapsed_time})

            conn.unbind()
            success = True

        except Exception as e:
            message = f"{e}"
            log.warning(f"LDAP Machine Resolver Test failed: {e!r}")
            log.debug("{0!s}".format(traceback.format_exc()))

        return success, message
