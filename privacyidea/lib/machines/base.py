# -*- coding: utf-8 -*-
#
#  2015-02-25 Cornelius Kölbel <cornelius@privacyidea.org>
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
__doc__ = """This contains the Base Class for Machine Resolvers. Machines
Resolvers are used to tie a Machine Object to a token and an application. To
do so a Machine Resolver can translate between a FQDN, Hostname, IP and the
machine ID.

This file is tested in tests/test_lib_machines.py
"""
import netaddr


class Machine(object):

    """
    The Machine object is returned by the resolver for a given machine_id.
    It contains data like the hostname, the ip address and additional
    information like expiry or decommission...
    """

    def __init__(self, resolver_name, machine_id, hostname=None, ip=None):
        self.id = machine_id
        self.resolver_name = resolver_name
        self.hostname = hostname
        if type(ip) in [basestring, str, unicode]:
            self.ip = netaddr.IPAddress(ip)
        else:
            self.ip = ip

    def has_hostname(self, hostname):
        """
        Checks if the machine has the given hostname.
        A machine might have more than one hostname. The hostname is then
        provided as a list
        :param hostname: The hostname searched for
        :type hostname: basestring
        :return: True or false
        """
        if type(self.hostname) == list:
            return hostname in self.hostname
        elif type(self.hostname) in [basestring, str, unicode]:
            return hostname.lower() == self.hostname.lower()

    def has_ip(self, ip):
        """
        Checks if the machine has the given IP.
        A machine might have more than one IP Address. The ip is then
        provided as a list
        :param ip: The IP address to search for
        :type ip: Netaddr IPAddress
        :return: True or false
        """
        # convert to IPAddress
        if type(ip) in [basestring, str, unicode]:
            ip = netaddr.IPAddress(ip)

        if type(self.ip) == list:
            return ip in self.ip
        elif type(self.ip) == netaddr.IPAddress:
            return ip == self.ip

    def get_dict(self):
        """
        Convert the object attributes to a dict
        :return: dict of attributes
        """
        ip = self.ip
        if type(self.ip) == list:
            ip = ["%s" % i for i in ip]
        elif type(self.ip) == netaddr.IPAddress:
            ip = "%s" % ip

        d = {"hostname": self.hostname,
             "ip": ip,
             "resolver_name": self.resolver_name,
             "id": self.id}
        return d

class MachineResolverError(Exception):
    pass


class BaseMachineResolver(object):

    type = "base"

    def __init__(self, name, config=None):
        """

        :param name: The identifying name of the resolver
        :param config:
        :return:
        """
        self.name = name
        if config:
            self.load_config(config)

    @classmethod
    def get_type(self):
        return self.type

    def get_machines(self, machine_id=None, hostname=None, ip=None, any=None,
                     substring=False):
        """
        Return a list of all machine objects in this resolver

        :param substring: If set to true, it will also match search_hostnames,
        that only are a subnet of the machines hostname.
        :type substring: bool
        :param any: a substring that matches EITHER hostname, machineid or ip
        :type any: basestring
        :return: list of machine objects
        """
        return []

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
        return ""

    def load_config(self, config):
        """
        This loads the configuration dictionary, which contains the necessary
        information for the machine resolver to find and connect to the
        machine store.

        :param config: The configuration dictionary to run the machine resolver
        :type config: dict
        :return: None
        """
        return None

    @classmethod
    def get_config_description(self):
        """
        Returns a description what config values are expected and allowed.

        :return: dict
        """
        return {}

    @classmethod
    def testconnection(cls, params):
        """
        This method can test if the passed parameters would create a working
        machine resolver.

        :param params:
        :return: tupple of success and description
        :rtype: (bool, string)
        """
        return False, "Not Implemented"

