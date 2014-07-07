# -*- coding: utf-8 -*-
#  privacyIDEA
#  (c)  2014 Cornelius Kölbel

#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
from pylons import config as ini_config
from netaddr import IPAddress
from netaddr import IPNetwork

import logging
log = logging.getLogger(__name__)


def get_basic_auth_client_list():
    '''
    returns the list of the clients, that should to basic auth.
    The list is configured in the ini-file like this:
    basic_auth_clients = 10.2.2.1, 172.15.0.0/16
    
    :return: the list of the clients and client sub nets.
    :rtype: list of strings
    '''


    clients = ini_config.get("privacyideaBasicAuth.clients", "")
    client_list = [ c.strip() for c in clients.split("," )]
    return client_list

def is_client_in_basic_auth(client):
    '''
    :param client: the client ip address
    :return: returns true, if this client should do basic auth
    :rtype: bool
    '''
    res = False
    try:
        client_list = get_basic_auth_client_list()
        for network in client_list:
            if IPAddress(client) in IPNetwork(network):
                res = True
    except Exception as exx:
        # THe client IPs could be misconfigured
        log.error("Can not be determined: %r" % exx)
        
    return res

def request_classifier(environ):
    '''
    Classify the request to be either a browser request that
    should get a form authentication or an API request, that
    should get an basic authentication
    '''
    # get client
    client = environ.get("REMOTE_ADDR")
    if is_client_in_basic_auth(client):
        return 'basic'
    return 'browser'


