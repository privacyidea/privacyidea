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
from log import log_with
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


def save_subscription(subscription):
    """
    Saves a subscription to the database. If the subscription already exists,
    it is updated.

    :param subscription: dictionary with all attributes of the
        subscription
    :type subscription: dict
    :return: True in case of success
    """
    # TODO verify the signature of the subscriptions
    s = Subscription(application=subscription.get("application"),
                     for_name=subscription.get("for_name"),
                     for_address=subscription.get("for_address"),
                     for_email=subscription.get("for_email"),
                     for_phone=subscription.get("for_phone"),
                     for_url=subscription.get("for_url"),
                     for_comment=subscription.get("for_comment"),
                     by_name=subscription.get("by_name"),
                     by_email=subscription.get("by_email"),
                     by_address=subscription.get("by_addresss"),
                     by_phone=subscription.get("by_phone"),
                     by_url=subscription.get("by_url"),
                     date_from=subscription.get("data_from"),
                     date_till=subscription.get("date_till"),
                     num_users=subscription.get("num_users"),
                     num_tokens=subscription.get("num_tokens"),
                     num_clients=subscription.get("num_clients"),
                     signature=subscription.get("signatue")
                     ).save()
    return s


def get_subscription(application=None):
    """
    Return a list of subscriptions for a certai application
    If application is ommitted, all applications are returned.

    :param application: Name of the application
    :return: list of subscription dictionaries
    """
    subscriptions = []
    sql_query = Subscription.query
    if application:
        sql_query = sql_query.filter(Subscription.application == application)

    for sub in sql_query.all():
        subscriptions.append(sub.get())

    return subscriptions


def delete_subscription(application):
    """
    Delete the subscription for the given application

    :param application:
    :return: True in case of success
    """
    s = Subscription.query.filter(Subscription.application ==
                                  application).delete()
    return s

