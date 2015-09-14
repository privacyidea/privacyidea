# -*- coding: utf-8 -*-
#
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

from .base import Machine
from .base import BaseMachineResolver
from .base import MachineResolverError
import ldap3
import netaddr
import traceback
import logging
from privacyidea.lib.resolvers.LDAPIdResolver import AUTHTYPE
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver
from gettext import gettext as _

log = logging.getLogger(__name__)


class LdapMachineResolver(BaseMachineResolver):

    type = "ldap"

    def __init__(self, name, config=None):
        self.i_am_bound = False
        self.name = name
        if config:
            self.load_config(config)

    def _bind(self):
        if not self.i_am_bound:
            server = ldap3.Server(self.server, port=self.port,
                                  use_ssl=self.ssl,
                                  connect_timeout=self.timeout)
            self.l = IdResolver.create_connection(authtype=self.authtype,
                                                  server=server,
                                                  user=self.binddn,
                                                  password=self.bindpw,
                                                  auto_referrals=not
                                                 self.noreferrals)
            self.l.open()
            if not self.l.bind():
                raise Exception("Wrong credentials")
            self.i_am_bound = True

    def _get_uid(self, entry):
        if type(entry.get(self.id_attribute)) == list:
            uid = entry.get(self.id_attribute)[0]
        else:
            uid = entry.get(self.id_attribute)
        return uid

    @classmethod
    def _create_ldap_filter(cls, search_filter,
                            id_attribute, machine_id,
                            hostname_attribute, hostname,
                            ip_attribute, ip, substring=False, any=False):
        filter = "(&" + search_filter

        if not any:
            if hostname:
                if substring:
                    filter += "(%s=*%s*)" % (hostname_attribute, hostname)
                else:
                    filter += "(%s=%s)" % (hostname_attribute, hostname)
            if ip:
                if substring:
                    filter += "(%s=*%s*)" % (ip_attribute, ip)
                else:
                    filter += "(%s=%s)" % (ip_attribute, ip)
        filter += ")"
        if any:
            # Now we need to extend the search filter
            # like this  (& (&(....)) (|(ip=...)(host=...)) )
            any_filter = "(|"
            if id_attribute:
                any_filter += "(%s=*%s*)" % (id_attribute, any)
            if hostname_attribute:
                any_filter += "(%s=*%s*)" % (hostname_attribute, any)
            if ip_attribute:
                any_filter += "(%s=*%s*)" % (ip_attribute, any)
            any_filter += ")"

            filter = "(&%s%s)" % (filter, any_filter)

        return filter

    def get_machines(self, machine_id=None, hostname=None, ip=None, any=None,
                     substring=False):
        """
        Return matching machines.

        :param machine_id: can be matched as substring
        :param hostname: can be matched as substring
        :param ip: can not be matched as substring
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
        filter = self._create_ldap_filter(self.search_filter,
                                          self.id_attribute, machine_id,
                                          self.hostname_attribute, hostname,
                                          self.ip_attribute, ip,
                                          substring, any)

        self.l.search(search_base=self.basedn,
                      search_scope=ldap3.SUBTREE,
                      search_filter=filter,
                      attributes=attributes,
                      paged_size=self.sizelimit)
        # returns a list of dictionaries
        for entry in self.l.response:
            dn = entry.get("dn")
            attributes = entry.get("attributes")
            try:
                if entry.get("type") == "searchResEntry":
                    machine = {}
                    if self.id_attribute.lower() == "dn":
                        machine['machineid'] = dn
                    else:
                        machine['machineid'] = self._get_uid(attributes)
                    for k, v in attributes.items():
                        key = self.reverse_map.get(k)
                        if key:
                            if type(v) == list:
                                machine[key] = v[0]
                            else:
                                machine[key] = v
                    machine_ip = None
                    if machine.get("ip"):
                        machine_ip = netaddr.IPAddress(machine.get("ip"))
                    machines.append(Machine(self.name,
                                            machine['machineid'],
                                            hostname=machine['hostname'],
                                            ip=machine_ip))
            except Exception as exx:  # pragma: no cover
                log.error("Error during fetching LDAP objects: %r" % exx)
                log.error("%r" % traceback.format_exc())

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
            raise Exception("More than one machine found in LDAP resolver %s" %
                            self.name)

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
        (self.server, self.port, self.ssl) = IdResolver.split_uri(self.uri)
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
        self.reverse_map = {self.ip_attribute: "ip",
                            self.hostname_attribute: "hostname",
                            self.id_attribute: "id"}
        self.noreferrals = config.get("NOREFERRALS", False)
        self.certificate = config.get("CACERTIFICATE")
        self.authtype = config.get("AUTHTYPE", AUTHTYPE.SIMPLE)

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
                                             "CACERTIFICATE": "string",
                                             "AUTHTYPE": "string"}}}

        return description


    @classmethod
    def testconnection(cls, params):
        """
        Test if the given filename exists.

        :param params:
        :return:
        """
        success = False
        try:
            (host, port, ssl) = IdResolver.split_uri(params.get("LDAPURI"))
            server = ldap3.Server(host, port=port,
                                  use_ssl=ssl,
                                  connect_timeout=float(params.get("TIMEOUT",
                                                                  5)))
            l = IdResolver.create_connection(authtype=\
                                                 params.get("AUTHTYPE",
                                                            AUTHTYPE.SIMPLE),
                                             server=server,
                                             user=params.get("BINDDN"),
                                             password=params.get("BINDPW"),
                                             auto_referrals=not params.get(
                                                 "NOREFERRALS"))
            l.open()
            if not l.bind():
                raise Exception("Wrong credentials")
            # search for users...
            l.search(search_base=params["LDAPBASE"],
                     search_scope=ldap3.SUBTREE,
                     search_filter="(&" + params["SEARCHFILTER"] + ")",
                     attributes=[ params["HOSTNAMEATTRIBUTE"] ])

            count = len([x for x in l.response if x.get("type") ==
                         "searchResEntry"])
            desc = _("Your LDAP config seems to be OK, %i machine objects "
                     "found.")\
                % count

            l.unbind()
            success = True

        except Exception as e:
            desc = "%r" % e

        return success, desc
