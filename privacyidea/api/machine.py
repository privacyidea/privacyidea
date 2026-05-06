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
__doc__ = """
The machine REST API lists machines resolved by configured machine
resolvers, attaches and detaches tokens to those machines via
application plugins, and fetches the authentication items the plugins
need at runtime. See :ref:`machines` for the conceptual chapter and
:ref:`application_plugins` for the available applications.

All endpoints require admin authentication. Listing is gated by the
admin policy action :ref:`policy_machinelist`; attaching, detaching
and managing token-machine options by
:ref:`policy_manage_machine_tokens`; the runtime
``/machine/authitem`` endpoint by
:ref:`policy_fetch_authentication_items`.
"""

from flask import (Blueprint,
                   request, g)
from .lib.utils import (getParam, send_result)
from ..api.lib.prepolicy import prepolicy, check_base_action, mangle
from ..lib.policies.actions import PolicyAction

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
@prepolicy(check_base_action, request, PolicyAction.MACHINELIST)
def list_machines_api():
    """
    List machines from every configured machine resolver. Filters can
    be combined; ``any`` performs a substring match across hostname,
    IP and id at once.

    Requires admin authentication and the policy action
    :ref:`policy_machinelist`.

    :query hostname: substring match against the machine's hostnames.
    :query ip: exact match against the machine's IP address.
    :query id: substring match against the machine id.
    :query resolver: substring match against the resolver name.
    :query any: substring match against ``hostname``, ``ip`` or ``id``.
    :status 200: list of machine dictionaries in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       GET /machine/?hostname=on HTTP/1.1
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
               "hostname": ["flavon.example.com", "test.example.com"],
               "ip": "1.2.3.4",
               "resolver_name": "machineresolver1"
             },
             {
               "id": "1908209x48x2183",
               "hostname": ["london.example.com"],
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
@prepolicy(check_base_action, request, PolicyAction.MACHINETOKENS)
def attach_token_api():
    """
    Attach an existing token to a machine for use with a given
    application plugin (``ssh``, ``luks``, ``offline``, ...). The
    machine can be identified either by ``hostname`` or by the pair
    (``machineid``, ``resolver``). Any body fields not listed below
    are forwarded to the application plugin as options.

    Requires admin authentication and the policy action
    :ref:`policy_manage_machine_tokens`.

    :jsonparam hostname: identify the target machine by hostname.
    :jsonparam machineid: identify the target machine by machine id
        (combine with ``resolver``).
    :jsonparam resolver: machine resolver name.
    :jsonparam serial: token serial number (required).
    :jsonparam application: application plugin name (required).
    :jsonparam: any other field is treated as a plugin option.
    :status 200: id of the new machine-token row in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       POST /machine/token HTTP/1.1
       Host: example.com
       Content-Type: application/json

       {
         "hostname": "puckel.example.com",
         "machineid": "12313098",
         "resolver": "machineresolver1",
         "serial": "tok123",
         "application": "luks"
       }
    """
    hostname = getParam(request.all_data, "hostname")
    machine_id = getParam(request.all_data, "machineid")
    resolver = getParam(request.all_data, "resolver")
    serial = getParam(request.all_data, "serial", optional=False)
    application = getParam(request.all_data, "application", optional=False)
    if resolver == "":
        resolver = None
        machine_id = None

    # get additional options:
    options = {}
    for key in request.all_data.keys():
        if key not in ["hostname", "machineid", "resolver", "serial", "application"]:
            # We use the key as additional option
            options[key] = request.all_data.get(key)

    machine_token = attach_token(serial, application, hostname=hostname, machine_id=machine_id, resolver_name=resolver,
                             options=options)

    g.audit_object.log({"success": True, "info": f"serial: {serial}, application: {application}"})

    return send_result(machine_token.id)


@machine_blueprint.route('/token/<serial>/<machineid>/<resolver>/<application>',
                         methods=['DELETE'])
@machine_blueprint.route('/token/<serial>/<application>/<mtid>', methods=['DELETE'])
@prepolicy(check_base_action, request, PolicyAction.MACHINETOKENS)
def detach_token_api(serial, machineid=None, resolver=None, application=None, mtid=None):
    """
    Detach a token from a machine. Two URL shapes are accepted:
    ``/machine/token/<serial>/<machineid>/<resolver>/<application>``
    identifies the binding by machine-id + resolver,
    ``/machine/token/<serial>/<application>/<mtid>`` by the
    machine-token row id directly.

    Requires admin authentication and the policy action
    :ref:`policy_manage_machine_tokens`.

    :param serial: path component, the token serial.
    :param machineid: path component, the machine id.
    :param resolver: path component, the machine resolver name.
    :param application: path component, the application plugin name.
    :param mtid: path component, the machine-token row id (alternative
        to machineid + resolver).
    :status 200: number of removed bindings in ``result.value``.
    """
    r = detach_token(serial, application,
                     machine_id=machineid, resolver_name=resolver, machine_token_id=mtid)

    g.audit_object.log({'success': True,
                        'info': "serial: {0!s}, application: {1!s}".format(serial,
                                                                           application)})

    return send_result(r)


@machine_blueprint.route('/token', methods=['GET'])
@prepolicy(check_base_action, request, PolicyAction.MACHINETOKENS)
def list_machinetokens_api():
    """
    List machine-token bindings, either for a given machine or for a
    given token. Without machine identification but with ``serial``
    and no extra filters, returns the machines that the given token
    is attached to.

    Requires admin authentication and the policy action
    :ref:`policy_manage_machine_tokens`.

    :query serial: token serial (supports the ``*`` wildcard for
        substring matching).
    :query hostname: identify the machine by hostname.
    :query machineid: identify the machine by machine id.
    :query resolver: machine resolver name.
    :query application: filter by application plugin name (``ssh``,
        ``offline``, ...).
    :query sortby: column to sort by — ``serial`` or any option key
        (e.g. ``service_id``). Default ``serial``.
    :query sortdir: ``asc`` (default) or ``desc``.
    :query: any other key is treated as an option filter (e.g.
        ``service_id``, ``user`` for SSH; ``count``, ``rounds`` for
        offline). Filter values support the ``*`` wildcard.
    :status 200: list of machine-token bindings in ``result.value``.

    Example response value::

        [
          {
            "application": "ssh",
            "id": 1,
            "options": {"service_id": "webserver", "user": "root"},
            "resolver": null,
            "serial": "SSHKEY1",
            "type": "sshkey"
          }
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
@prepolicy(check_base_action, request, PolicyAction.MACHINETOKENS)
def set_option_api():
    """
    Set or remove options on a machine-token binding. Body fields not
    listed below are treated as options: a non-empty value adds or
    updates the option, an empty value removes it. The binding may be
    addressed either by ``mtid`` or by the (machine, token, application)
    tuple.

    Requires admin authentication and the policy action
    :ref:`policy_manage_machine_tokens`.

    :jsonparam hostname: identify the machine by hostname.
    :jsonparam machineid: identify the machine by machine id.
    :jsonparam resolver: machine resolver name.
    :jsonparam serial: token serial.
    :jsonparam application: application plugin name.
    :jsonparam mtid: machine-token row id (alternative to the tuple).
    :jsonparam: any other field — non-empty values add/update an
        option, empty values remove it.
    :status 200: ``{"added": <n>, "deleted": <m>}`` in ``result.value``.
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
        o_add = add_option(machine_token_id=mtid, options=options_add)
    else:
        o_add = add_option(serial=serial, application=application,
                           hostname=hostname,
                           machine_id=machineid, resolver_name=resolver,
                           options=options_add)
    o_del = len(options_del)
    for k in options_del:
        if mtid:
            delete_option(machine_token_id=mtid, key=k)
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
@prepolicy(check_base_action, request, PolicyAction.AUTHITEMS)
def get_auth_items_api(application=None):
    """
    Fetch the authentication items the application plugin needs at
    runtime for the given client machine. Each plugin defines its own
    item shape — for example SSH returns a list of ``{username,
    sshkey}`` records, LUKS returns a list of
    ``{slot, challenge, response, partition}`` records.

    Without ``application`` in the path, items for every plugin
    attached to the machine are returned, keyed by application name.

    Requires admin authentication and the policy action
    :ref:`policy_fetch_authentication_items`.

    :param application: optional path component, the application
        plugin name to limit the response to.
    :query hostname: hostname of the calling client machine (required).
    :query challenge: challenge value for plugins that compute a
        challenge/response item (e.g. Yubikey). The returned item is
        the combination of challenge and response.
    :query: any other key is forwarded as an additional plugin filter.
    :status 200: dict of authentication items keyed by application in
        ``result.value``.

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": {
             "ssh": [
               {"username": "...", "sshkey": "..."}
             ],
             "luks": [
               {"slot": "...", "challenge": "...", "response": "...",
                "partition": "..."}
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
            del (filter_param[key])

    ret = get_auth_items(hostname, application=application, challenge=challenge,
                         filter_param=filter_param)
    g.audit_object.log({'success': True,
                        'info': "host: {0!s}, application: {1!s}".format(hostname,
                                                                         application)})
    return send_result(ret)
