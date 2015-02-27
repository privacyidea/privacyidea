# -*- coding: utf-8 -*-
#
#  2015-02-27 Cornelius Kölbel <cornelius@privacyidea.org>
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
"""
This is the library for retrieving machines and adding tokens and
applications to machines.

This module is tested in tests/test_lib_machines.py.

It depends on the database model models.py and on the machineresolver
lib/machineresolver.py, so this can be tested standalone without realms,
tokens and webservice!
"""

import logging
from log import log_with
from .machineresolver import get_resolver_list, get_resolver_object


log = logging.getLogger(__name__)



@log_with(log)
def get_machines(hostname=None, ip=None, id=None, resolver=None):
    """
    This returns a list of machines from ALL resolvers matching this criterion.

    :param hostname: The hostname of the machine, substring matching
    :type hostname: basestring
    :param ip: The IPAddress of the machine
    :type ip: netaddr.IPAddress
    :param id: The id of the machine, substring matching
    :type id: basestring
    :param resolver: The resolver of the machine, substring matching
    :type resolver: basestring
    :return: list of Machine Objects.
    """
    resolver_list = get_resolver_list()
    all_machines = []

    for reso in resolver_list.keys():
        # The resolvernames are the keys of the dictionary
        if resolver and resolver not in reso:
            # filter for other resolvers
            continue
        reso_obj = get_resolver_object(reso)
        resolver_machines = reso_obj.get_machines(hostname=hostname,
                                                  ip=ip,
                                                  machine_id=id,
                                                  substring=True)
        all_machines += resolver_machines

    return all_machines
