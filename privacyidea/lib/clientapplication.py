# -*- coding: utf-8 -*-
#
#  2016-08-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Save client application information for authentication requests
#
# License:  AGPLv3
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
__doc__ = """Save and list client application information.
Client Application information was saved during authentication requests.

The code is tested in tests/test_lib_clientapplication.py.
"""

import logging
import datetime
from .log import log_with
from ..models import ClientApplication, Subscription
from netaddr import IPAddress


log = logging.getLogger(__name__)


@log_with(log)
def save_clientapplication(ip, clienttype):
    """
    Save (or update) the IP and the clienttype to the database table.

    :param ip: The IP address of the requesting client.
    :type ip: well formatted string or IPAddress
    :param clienttype: The type of the client
    :type ip: basestring
    :return: database ID
    """
    # Check for a valid IP address
    ip = IPAddress(ip)
    # TODO: resolve hostname
    id = ClientApplication(ip="{0!s}".format(ip),
                           clienttype=clienttype).save()
    return id


@log_with(log)
def get_clientapplication(ip=None, clienttype=None, group_by="clienttype"):
    """
    Return ClientApplications.

    :param ip: The IP address of the requesting client.
    :type ip: well formatted string or IPAddress
    :param clienttype: The type of the client
    :type ip: basestring
    :param group_by: can either be "ip" or "clienttype"
    :return: dictionary either grouped by clienttype or ip

    {"PAM": [{ <client1> },{ <client2> }, { <client3> }],
     "SAML": [ { <client2> } ]
    }
    """
    clients = {}
    sql_query = ClientApplication.query
    if ip:
        # Check for a valid IP address
        ip = IPAddress(ip)
        sql_query = sql_query.filter(ClientApplication.ip == "{0!s}".format(ip))

    if clienttype:
        sql_query = sql_query.filter(ClientApplication.clienttype == clienttype)

    for row in sql_query.all():
        if group_by.lower() == "clienttype":
            if not clients.get(row.clienttype):
                clients[row.clienttype] = []
            clients[row.clienttype].append({"ip": row.ip,
                                            "hostname": row.hostname,
                                            "lastseen": row.lastseen})
        else:
            if not clients.get(row.ip):
                clients[row.ip] = []
            clients[row.ip].append({"hostname": row.hostname,
                                    "clienttype": row.clienttype,
                                    "lastseen": row.lastseen})
    return clients
