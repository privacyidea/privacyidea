# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
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
__doc__ = """This REST API is used to list machines from Machine Resolvers.

The code is tested in tests/test_api_machines
"""
from flask import (Blueprint,
                   request)
from lib.utils import (getParam,
                       send_result)
from ..api.lib.prepolicy import prepolicy, check_base_action
from ..lib.policy import ACTION

from flask import (g)
from ..lib.machine import (get_machines, attach_token, detach_token,
                           add_option, delete_option,
                           list_token_machines, list_machine_tokens,
                           get_auth_items)
import logging
import netaddr


log = logging.getLogger(__name__)


machine_blueprint = Blueprint('machine_blueprint', __name__)


@machine_blueprint.route('/', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.MACHINELIST)
def list_machines_api():
    """
    List all machines that can be found in the machine resolvers.

    :param hostname: only show machines, that match this hostname as substring
    :param ip: only show machines, that exactly match this IP address
    :param id: filter for substring matching ids
    :param resolver: filter for substring matching resolvers
    :param any: filter for a substring either matching in "hostname", "ip"
        or "id"
    
    :return: json result with "result": true and the machine list in "value".

    **Example request**:

    .. sourcecode:: http

       GET /hostname?hostname=on HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": [
              {
                "id": "908asljdas90ad0",
                "hostname": [ "flavon.example.com", "test.example.com" ],
                "ip": "1.2.3.4",
                "resolver_name": "machineresolver1"
              },
              {
                "id": "1908209x48x2183",
                "hostname": [ "london.example.com" ],
                "ip": "2.4.5.6",
                "resolver_name": "machineresolver1"
              }
            ]
          },
          "version": "privacyIDEA unknown"
        }
    """
    hostname = getParam(request.all_data, "hostname")
    ip = getParam(request.all_data, "ip")
    if ip:
        ip = netaddr.IPAddress(ip)
    id = getParam(request.all_data, "id")
    resolver = getParam(request.all_data, "resolver")

    any = getParam(request.all_data, "any")

    machines = get_machines(hostname=hostname, ip=ip, id=id, resolver=resolver,
                            any=any)
    # this returns a list of Machine Object. This is not JSON serialiable,
    # so we need to convert the Machine Object to dict
    machines = [mobject.get_dict() for mobject in machines]
    g.audit_object.log({'success': True,
                        'info': "hostname: %s, ip: %s" % (hostname, ip)})
    
    return send_result(machines)


@machine_blueprint.route('/token', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.MACHINETOKENS)
def attach_token_api():
    """
    Attach an existing token to a machine with a certain application.

    :param hostname: identify the machine by the hostname
    :param machineid: identify the machine by the machine ID and the resolver
        name
    :param resolver: identify the machine by the machine ID and the resolver name
    :param serial: identify the token by the serial number
    :param application: the name of the application like "luks" or "ssh".

    Parameters not listed will be treated as additional options.

    :return: json result with "result": true and the machine list in "value".

    **Example request**:

    .. sourcecode:: http

       POST /token HTTP/1.1
       Host: example.com
       Accept: application/json

       { "hostname": "puckel.example.com",
         "machienid": "12313098",
         "resolver": "machineresolver1",
         "serial": "tok123",
         "application": "luks" }

    """
    hostname = getParam(request.all_data, "hostname")
    machineid = getParam(request.all_data, "machineid")
    resolver = getParam(request.all_data, "resolver")
    serial = getParam(request.all_data, "serial", optional=False)
    application = getParam(request.all_data, "application", optional=False)

    # get additional options:
    options = {}
    for key in request.all_data.keys():
        if key not in ["hostname", "machineid", "resolver", "serial",
                       "application"]:
            # We use the key as additional option
            options[key] = request.all_data.get(key)

    mt_object = attach_token(serial, application, hostname=hostname,
                             machine_id=machineid, resolver_name=resolver,
                             options=options)

    g.audit_object.log({'success': True,
                        'info': "serial: %s, application: %s" % (serial,
                                                                 application)})

    return send_result(mt_object.id)


@machine_blueprint.route('/token/<serial>/<machineid>/<resolver>/<application>',
                         methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.MACHINETOKENS)
def detach_token_api(serial, machineid, resolver, application):
    """
    Detach a token from a machine with a certain application.

    :param machineid: identify the machine by the machine ID and the resolver
        name
    :param resolver: identify the machine by the machine ID and the resolver name
    :param serial: identify the token by the serial number
    :param application: the name of the application like "luks" or "ssh".

    :return: json result with "result": true and the machine list in "value".

    **Example request**:

    .. sourcecode:: http

       DELETE /token HTTP/1.1
       Host: example.com
       Accept: application/json

       { "hostname": "puckel.example.com",
         "resolver": "machineresolver1",
         "application": "luks" }

    """
    r = detach_token(serial, application,
                     machine_id=machineid, resolver_name=resolver)

    g.audit_object.log({'success': True,
                        'info': "serial: %s, application: %s" % (serial,
                                                                 application)})

    return send_result(r)



@machine_blueprint.route('/token', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.MACHINETOKENS)
def list_machinetokens_api():
    """
    Return a list of MachineTokens either for a given machine or for a given
    token.

    :param serial: Return the MachineTokens for a the given Token
    :param hostname: Identify the machine by the hostname
    :param machineid: Identify the machine by the machine ID and the resolver
        name
    :param resolver: Identify the machine by the machine ID and the resolver
        name
    :return:
    """
    hostname = getParam(request.all_data, "hostname")
    machineid = getParam(request.all_data, "machineid")
    resolver = getParam(request.all_data, "resolver")
    serial = getParam(request.all_data, "serial")
    application = getParam(request.all_data, "application")

    res = []

    if not hostname and not machineid and not resolver:
        # We return the list of the machines for the given serial
        res = list_token_machines(serial)
    else:
        res = list_machine_tokens(hostname=hostname, machine_id=machineid,
                                  resolver_name=resolver)

    g.audit_object.log({'success': True,
                        'info': "serial: %s, hostname: %s" % (serial,
                                                              hostname)})
    return send_result(res)


@machine_blueprint.route('/tokenoption', methods=['POST'])
@prepolicy(check_base_action, request, ACTION.MACHINETOKENS)
def set_option_api():
    """
    This sets a Machine Token option or deletes it, if the value is empty.

    :param hostname: identify the machine by the hostname
    :param machineid: identify the machine by the machine ID and the resolver
        name
    :param resolver: identify the machine by the machine ID and the resolver name
    :param serial: identify the token by the serial number
    :param application: the name of the application like "luks" or "ssh".

    Parameters not listed will be treated as additional options.

    :return:
    """
    hostname = getParam(request.all_data, "hostname")
    machineid = getParam(request.all_data, "machineid")
    resolver = getParam(request.all_data, "resolver")
    serial = getParam(request.all_data, "serial", optional=False)
    application = getParam(request.all_data, "application", optional=False)

    # get additional options:
    options_add = {}
    options_del = []
    for key in request.all_data.keys():
        if key not in ["hostname", "machineid", "resolver", "serial",
                       "application"]:
            # We use the key as additional option
            value = request.all_data.get(key)
            if value:
                options_add[key] = request.all_data.get(key)
            else:
                options_del.append(key)

    o_add = add_option(serial=serial, application=application,
                       hostname=hostname,
                       machine_id=machineid, resolver_name=resolver,
                       options=options_add)
    o_del = len(options_del)
    for k in options_del:
        delete_option(serial=serial, application=application,
                      hostname=hostname,
                      machine_id=machineid, resolver_name=resolver,
                      key=k)

    g.audit_object.log({'success': True,
                        'info': "serial: %s, application: %s" % (serial,
                                                                 application)})

    return send_result({"added": o_add, "deleted": o_del})


@machine_blueprint.route('/authitem', methods=['GET'])
@machine_blueprint.route('/authitem/<application>', methods=['GET'])
@prepolicy(check_base_action, request, ACTION.AUTHITEMS)
def get_auth_items_api(application=None):
    """
    This fetches the authentication items for a given application and the
    given client machine.

    :param challenge: A challenge for which the authentication item is
        calculated. In case of the Yubikey this can be a challenge that produces
        a response. The authentication item is the combination of the challenge
        and the response.
    :type challenge: basestring
    :param hostname: The hostname of the machine
    :type hostname: basestring

    :return: dictionary with lists of authentication items

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "value": { "ssh": [ { "username": "....",
                                  "sshkey": "...."
                                }
                              ],
                       "luks": [ { "slot": ".....",
                                   "challenge": "...",
                                   "response": "...",
                                   "partition": "..."
                               ]
                     }
          },
          "version": "privacyIDEA unknown"
        }
    """
    challenge = getParam(request.all_data, "challenge")
    hostname = getParam(request.all_data, "hostname", optional=False)
    # Get optional additional filter parameters
    filter_param = request.all_data
    for key in ["challenge", "hostname"]:
        if key in filter_param:
            del(filter_param[key])

    ret = get_auth_items(hostname, ip=request.remote_addr,
                         application=application, challenge=challenge,
                         filter_param=filter_param)
    g.audit_object.log({'success': True,
                        'info': "host: %s, application: %s" % (hostname,
                                                               application)})
    return send_result(ret)

