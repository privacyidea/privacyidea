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
                   request, g)
from .lib.utils import (getParam, send_result)
from ..api.lib.prepolicy import prepolicy, check_base_action, mangle
from ..lib.policy import ACTION

from ..lib.machine import (get_machines, attach_token, detach_token,
                           add_option, delete_option,
                           list_token_machines, list_machine_tokens,
                           get_auth_items)
from privacyidea.lib.machine import ANY_MACHINE
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
        try:
            ip = netaddr.IPAddress(ip)
        except netaddr.AddrFormatError:
            # This happens when filtering in the machine view
            ip = None
    id = getParam(request.all_data, "id")
    resolver = getParam(request.all_data, "resolver")

    any = getParam(request.all_data, "any")

    machines = get_machines(hostname=hostname, ip=ip, id=id, resolver=resolver,
                            any=any)
    # this returns a list of Machine Object. This is not JSON serialiable,
    # so we need to convert the Machine Object to dict
    machines = [mobject.get_dict() for mobject in machines]
    g.audit_object.log({'success': True,
                        'info': "hostname: {0!s}, ip: {1!s}".format(hostname, ip)})

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
    if resolver == "":
        resolver = None
        machineid = None

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
                        'info': "serial: {0!s}, application: {1!s}".format(serial,
                                                                 application)})

    return send_result(mt_object.id)


@machine_blueprint.route('/token/<serial>/<machineid>/<resolver>/<application>',
                         methods=['DELETE'])
@machine_blueprint.route('/token/<serial>/<application>/<mtid>', methods=['DELETE'])
@prepolicy(check_base_action, request, ACTION.MACHINETOKENS)
def detach_token_api(serial, machineid=None, resolver=None, application=None, mtid=None):
    """
    Detach a token from a machine with a certain application.

    :param machineid: identify the machine by the machine ID and the resolver
        name
    :param resolver: identify the machine by the machine ID and the resolver name
    :param serial: identify the token by the serial number
    :param application: the name of the application like "luks" or "ssh".
    :param mtid: the ID of the machinetoken definition

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
                     machine_id=machineid, resolver_name=resolver, mtid=mtid)

    g.audit_object.log({'success': True,
                        'info': "serial: {0!s}, application: {1!s}".format(serial,
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
    :param machineid: Identify the machine by the machine ID and the resolver name
    :param resolver: Identify the machine by the machine ID and the resolver name
    :query sortby: sort the output by column. Can be 'serial', 'service_id'...
    :query sortdir: asc/desc
    :query application: The type of application like "ssh" or "offline".
    :param <options>: You can also filter for options like the 'service_id' or 'user' for SSH applications, or
        'count' and 'rounds' for offline applications. The filter allows the use of "*" to match substrings.
    :return: JSON list of dicts

    [{'application': 'ssh',
      'id': 1,
      'options': {'service_id': 'webserver',
                  'user': 'root'},
      'resolver': None,
      'serial': 'SSHKEY1',
      'type': 'sshkey'},
       ...
       ]
    """
    hostname = getParam(request.all_data, "hostname")
    machineid = getParam(request.all_data, "machineid")
    resolver = getParam(request.all_data, "resolver")
    serial = getParam(request.all_data, "serial")
    application = getParam(request.all_data, "application")
    sortby = getParam(request.all_data, "sortby", "serial")
    sortdir = getParam(request.all_data, "sortdir", "asc")
    filter_params = {}
    # Use remaining params as filters
    for key, value in {k: v for k, v in request.all_data.items() if k not in [
        "hostname", "machineid", "resolver", "serial", "application", "client", "g",
        "sortby", "sortdir", "page", "pagesize"
    ]}.items():
        filter_params[key] = value

    serial_pattern = None
    if serial and "*" in serial:
        serial_pattern = serial.replace("*", ".*")
        serial = None

    if not hostname and not machineid and not resolver and serial and not filter_params:
        # We return the list of the machines for the given serial
        res = list_token_machines(serial)
    else:
        if machineid == ANY_MACHINE:
            hostname = None
            machineid = None
            resolver = None
        res = list_machine_tokens(hostname=hostname, machine_id=machineid, resolver_name=resolver,
                                  serial=serial, application=application, filter_params=filter_params,
                                  serial_pattern=serial_pattern)

    if sortby == "serial":
        res.sort(key=lambda x: x.get("serial"), reverse=sortdir == "desc")
    else:
        res.sort(key=lambda x: x.get("options", {}).get(sortby, ""), reverse=sortdir == "desc")

    g.audit_object.log({'success': True,
                        'info': "serial: {0!s}, hostname: {1!s}".format(serial,
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
    :param mtid: the ID of the machinetoken definition

    Parameters not listed will be treated as additional options.

    :return:
    """
    hostname = getParam(request.all_data, "hostname")
    machineid = getParam(request.all_data, "machineid")
    resolver = getParam(request.all_data, "resolver")
    serial = getParam(request.all_data, "serial")
    application = getParam(request.all_data, "application")
    mtid = getParam(request.all_data, "mtid")

    # get additional options:
    options_add = {}
    options_del = []
    for key, value in {k: v for k, v in request.all_data.items() if k not in [
        "hostname", "machineid", "resolver", "serial", "application", "client", "g", "mtid"
    ]}.items():
        if value:
            options_add[key] = value
        else:
            options_del.append(key)

    if mtid:
        o_add = add_option(machinetoken_id=mtid, options=options_add)
    else:
        o_add = add_option(serial=serial, application=application,
                           hostname=hostname,
                           machine_id=machineid, resolver_name=resolver,
                           options=options_add)
    o_del = len(options_del)
    for k in options_del:
        if mtid:
            delete_option(machinetoken_id=mtid, key=k)
        else:
            delete_option(serial=serial, application=application,
                          hostname=hostname,
                          machine_id=machineid, resolver_name=resolver,
                          key=k)

    g.audit_object.log({'success': True,
                        'info': "serial: {0!s}, application: {1!s}".format(serial,
                                                                 application)})

    return send_result({"added": o_add, "deleted": o_del})


@machine_blueprint.route('/authitem', methods=['GET'])
@machine_blueprint.route('/authitem/<application>', methods=['GET'])
@prepolicy(mangle, request=request)
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
    for key in ["challenge", "hostname", "application"]:
        if key in filter_param:
            del(filter_param[key])

    ret = get_auth_items(hostname, ip=g.client_ip,
                         application=application, challenge=challenge,
                         filter_param=filter_param)
    g.audit_object.log({'success': True,
                        'info': "host: {0!s}, application: {1!s}".format(hostname,
                                                               application)})
    return send_result(ret)

