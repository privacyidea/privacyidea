# SPDX-FileCopyrightText: 2016 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

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
import traceback
from datetime import datetime
from typing import Union

from netaddr import IPAddress
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from privacyidea.lib.config import get_privacyidea_node
from .log import log_with
from ..models import ClientApplication, db

log = logging.getLogger(__name__)


@log_with(log)
def save_clientapplication(ip: Union[IPAddress, str], clienttype: str):
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
    last_seen = datetime.now()
    # TODO: resolve hostname

    stmt = select(ClientApplication).where(
        ClientApplication.ip == f"{ip}",
        ClientApplication.clienttype == clienttype,
        ClientApplication.node == node
    )
    client_app = db.session.execute(stmt).scalar_one_or_none()

    if client_app:
        client_app.last_seen = last_seen
    else:
        client_app = ClientApplication(ip=f"{ip}", clienttype=clienttype, node=node, lastseen=last_seen)
        db.session.add(client_app)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError) as e:  # pragma: no cover
        log.info(f'Unable to write ClientApplication entry to db: {e}')
        log.debug(traceback.format_exc())


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
    stmt = select(ClientApplication.ip,
                  ClientApplication.hostname,
                  ClientApplication.clienttype,
                  func.max(ClientApplication.lastseen).label("max_lastseen"))
    if ip:
        # Check for a valid IP address
        ip = IPAddress(ip)
        stmt = stmt.where(ClientApplication.ip == f"{ip}")

    if clienttype:
        stmt = stmt.where(ClientApplication.clienttype == clienttype)

    stmt = stmt.group_by(ClientApplication.ip,
                         ClientApplication.hostname,
                         ClientApplication.clienttype)

    applications = db.session.execute(stmt).all()
    for row in applications:
        if group_by.lower() == "clienttype":
            clients.setdefault(row.clienttype, []).append({"ip": row.ip,
                                                           "hostname": row.hostname,
                                                           "lastseen": row.max_lastseen})
        else:
            clients.setdefault(row.ip, []).append({"hostname": row.hostname,
                                                   "clienttype": row.clienttype,
                                                   "lastseen": row.max_lastseen})
    return clients
