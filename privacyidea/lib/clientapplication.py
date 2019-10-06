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

from sqlalchemy import func
import logging
import datetime
from .log import log_with
from ..models import ClientApplication, Subscription, db
from privacyidea.lib.config import get_privacyidea_node
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
    :return: None
    """
    node = get_privacyidea_node()
    # Check for a valid IP address
    ip = IPAddress(ip)
    # TODO: resolve hostname
    app = ClientApplication(ip="{0!s}".format(ip),
                            clienttype=clienttype,
                            node=node)
    app.save()


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
    # We group the results by IP, hostname and clienttype. Then, the rows in each group
    # only differ in the respective node names and the "lastseen" timestamp. Hence, we
    # then fetch MAX(lastseen) of each group to retrieve the most recent timestamp at
    # which the client was seen on *any* node. It is written to the ``max_lastseen``
    # attribute.
    sql_query = db.session.query(ClientApplication.ip,
                                 ClientApplication.hostname,
                                 ClientApplication.clienttype,
                                 func.max(ClientApplication.lastseen).label("max_lastseen"))
    if ip:
        # Check for a valid IP address
        ip = IPAddress(ip)
        sql_query = sql_query.filter(ClientApplication.ip == "{0!s}".format(ip))

    if clienttype:
        sql_query = sql_query.filter(ClientApplication.clienttype == clienttype)

    sql_query = sql_query.group_by(ClientApplication.ip,
                                   ClientApplication.hostname,
                                   ClientApplication.clienttype)

    for row in sql_query.all():
        if group_by.lower() == "clienttype":
            clients.setdefault(row.clienttype, []).append({"ip": row.ip,
                                                           "hostname": row.hostname,
                                                           "lastseen": row.max_lastseen})
        else:
            clients.setdefault(row.ip, []).append({"hostname": row.hostname,
                                                   "clienttype": row.clienttype,
                                                   "lastseen": row.max_lastseen})
    return clients
