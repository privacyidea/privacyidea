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

This module is tested in tests/test_lib_machinetokens.py and
tests/test_lib_machines.py.

It depends on the database model models.py and on the machineresolver
lib/machineresolver.py, so this can be tested standalone without realms,
tokens and webservice!
"""
from .error import ResourceNotFoundError, ParameterError
from .machineresolver import get_resolver_list, get_resolver_object
from privacyidea.models import Token
from privacyidea.models import (MachineToken, db, MachineTokenOptions,
                                MachineResolver, get_token_id,
                                get_machineresolver_id,
                                get_machinetoken_ids)
from privacyidea.lib.utils import fetch_one_resource
from netaddr import IPAddress
from sqlalchemy import and_
import logging
import re

from .token import token_exist

log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with
from privacyidea.lib.applications.base import get_auth_item, get_machine_application_class_dict

ANY_MACHINE = "any machine"
NO_RESOLVER = "no resolver"


@log_with(log)
def get_machines(hostname=None, ip=None, id=None, resolver=None, any=None,
                 substring=True):
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
    :param any: a substring, that matches EITHER of hostname, ip or resolver
    :type any: basestring
    :param substring: If True, machines are search with the parameters as
        substrings
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
                                                  any=any,
                                                  substring=substring)
        all_machines += resolver_machines

    return all_machines


def get_hostname(ip):
    """
    Return a hostname for a given IP address
    :param ip: IP address
    :type ip: IPAddress
    :return: hostname
    """
    machines = get_machines(ip=ip)
    if len(machines) > 1:
        raise Exception("Can not get unique ID for IP=%r. "
                        "More than one machine found." % ip)
    if len(machines) == 1:
        # There is only one machine in the list and we get its ID
        hostname = machines[0].hostname
        # return the first hostname
        if type(hostname) == list:
            hostname = hostname[0]
    else:
        raise Exception("There is no machine with IP={0!r}".format(ip))
    return hostname


def get_machine_id(hostname, ip=None):
    """
    Determine the id for a given hostname.
    The ID consists of the resolvername and the machine_id in this resolver.

    :param hostname: The hostname of the machine
    :param ip: The optional IP of the machine
    :return: tuple of machine_id and resolvername
    """
    machine_id = None
    resolver_name = None
    machines = get_machines(hostname=hostname, ip=ip, substring=False)
    if len(machines) > 1:
        raise Exception("Can not get unique ID for hostname=%r and IP=%r. "
                        "More than one machine found." % (hostname, ip))
    if len(machines) == 1:
        # There is only one machine in the list and we get its ID
        machine_id = machines[0].id
        resolver_name = machines[0].resolver_name

    if machine_id is None:
        raise Exception("There is no machine with name={0!r} and IP={1!r}".format(hostname, ip))

    return machine_id, resolver_name


#
#  Attach tokens to machines
#


@log_with(log)
def attach_token(serial, application, hostname=None, machine_id=None,
                 resolver_name=None, options=None):
    """
    Attach a token with an application to a machine. You need to provide
    either the hostname or the (machine_id, resolver_name) of the machine,
    to which you want to attach the token.

    :param serial: The serial number of the token
    :type serial: string
    :param application: The name of the application - something like ssh or luks
    :type application: basestring
    :param hostname: The hostname of the machine, to which your want to
    attach the token. If the hostname is not unique, an exception is raised.
    :type hostname: basestring
    :param machine_id: The machine ID of the machine, you want to attach the
    token to.
    :type machine_id: basestring
    :param resolver_name: The resolver_name of the machine you want attach
    the token to.
    :type resolver_name: basestring
    :param options: additional options
    :return: the new MachineToken Object
    """
    # Check for valid serial
    if not token_exist(serial):
        raise ResourceNotFoundError(f"Token with serial {serial} does not exist.")

    # Check for valid application
    valid_applications = get_machine_application_class_dict().keys()
    if application not in valid_applications:
        raise ParameterError(
            f"Application {application} is not supported. Valid applications are {valid_applications}.")

    if hostname or machine_id or resolver_name:
        machine_id, resolver_name = _get_host_identifier(hostname, machine_id,
                                                         resolver_name)
    # Now we have all data to create the MachineToken
    machinetoken = MachineToken(machineresolver=resolver_name,
                                machine_id=machine_id, serial=serial,
                                application=application)
    machinetoken.save()
    # Add options to the machine token
    if options:
        add_option(machinetoken_id=machinetoken.id,
                   options=options)

    return machinetoken


@log_with(log)
def detach_token(serial, application, hostname=None, machine_id=None,
                 resolver_name=None, mtid=None, filter_params=None):
    """
    Delete a machine token.
    Also deletes the corresponding MachineTokenOptions
    You need to provide either the hostname or the (machine_id,
    resolver_name) of the machine, from which you want to detach the
    token.

    :param serial: The serial number of the token
    :type serial: string
    :param application: The name of the application - something like ssh or luks
    :type application: basestring
    :param hostname: The hostname of the machine
    If the hostname is not unique, an exception is raised.
    :type hostname: basestring
    :param machine_id: The machine ID of the machine
    :type machine_id: basestring
    :param resolver_name: The resolver_name of the machine
    :type resolver_name: basestring
    :param mtid: The specific id of a specific machinetoken
    :param filter_params: additional machinetoken options to filter the detachment
    :type filter_params: dict
    :return: the number of deleted MachineToken objects
    """
    r = None
    if mtid:
        # We have specific mtid, which we are supposed to delete.
        MachineTokenOptions.query.filter(MachineTokenOptions.machinetoken_id == int(mtid)).delete()
        # Delete MachineToken
        r = MachineToken.query.filter(MachineToken.id == int(mtid)).delete()
    else:
        filter_params = filter_params or {}
        if machine_id == ANY_MACHINE and resolver_name == NO_RESOLVER:
            # For later handling we need to reset the machine_id and the resolver_name:
            machine_id = None
            resolver_name = None

        mts = list_token_machines(serial)
        # Delete MachineTokenOptions
        for mt in mts:
            if (mt.get("application") == application and (
                    (not machine_id or machine_id == mt.get("machine_id") and
                     (not hostname or hostname == mt.get("hostname")) and
                     (not resolver_name or resolver_name == mt.get("resolver"))))):
                delete_mt = True
                for key, value in filter_params.items():
                    # Check if the machinetoken contains the correct filter values
                    if mt.get("options").get(key) != value:
                        delete_mt = False
                if delete_mt:
                    MachineTokenOptions.query.filter(MachineTokenOptions.machinetoken_id == mt.get("id")).delete()
                    # Delete MachineToken
                    r = MachineToken.query.filter(MachineToken.id == mt.get("id")).delete()
    db.session.commit()
    return r


def add_option(machinetoken_id=None, machine_id=None, resolver_name=None,
               hostname=None, serial=None, application=None, options=None):
    """
    Add options to the machine token definition.
    You can either specify machinetoken_id or
     * machine_id, resolvername, serial, application or
     * hostname, serial, application
    :param machinetoken_id: The database id of the machinetoken
    :param machine_id: the resolver dependent machine id
    :param resolver_name: the name of the machine resolver
    :param hostname: the machine name
    :param serial: the serial number of the token
    :param application: the application
    :param options: options to add
    """
    if options is None:
        options = {}
    if machinetoken_id:
        machinetoken_ids = [machinetoken_id]
    else:
        machine_id, resolver_name = _get_host_identifier(hostname, machine_id,
                                                         resolver_name)

        machinetoken_ids = get_machinetoken_ids(machine_id,
                                                resolver_name,
                                                serial,
                                                application)

    for option_name, option_value in options.items():
        for mtid in machinetoken_ids:
            MachineTokenOptions(mtid, option_name, option_value)
    return len(options)


def delete_option(machinetoken_id=None, machine_id=None, resolver_name=None,
                  hostname=None, serial=None, application=None, key=None):
    """
    delete option from a machine token definition

    You can either specify machinetoken_id or
     * machine_id, resolvername, serial, application or
     * hostname, serial, application
    :param machinetoken_id: The database id of the machinetoken
    :param machine_id: the resolver dependent machine id
    :param resolver_name: the name of the machine resolver
    :param hostname: the machine name
    :param serial: the serial number of the token
    :param application: the application
    """
    if machinetoken_id:
        machinetoken_ids = [int(machinetoken_id)]
    else:
        machine_id, resolver_name = _get_host_identifier(hostname, machine_id,
                                                         resolver_name)
        machinetoken_ids = get_machinetoken_ids(machine_id,
                                                resolver_name,
                                                serial,
                                                application)

    for mtid in machinetoken_ids:
        r = MachineTokenOptions.query.filter(and_(
            MachineTokenOptions.machinetoken_id == mtid,
            MachineTokenOptions.mt_key == key)).delete()
    db.session.commit()
    return r


@log_with(log)
def list_machine_tokens(hostname=None,
                        machine_id=None,
                        resolver_name=None,
                        serial=None,
                        application=None,
                        filter_params=None,
                        serial_pattern=None):
    """
    Returns a list of tokens assigned to the given machine.

    :return: JSON of all tokens connected to machines with the corresponding
             application.
    """
    res = []
    filter_params = filter_params or {}
    service_id = filter_params.get("service_id")
    # The service_id overrules the hostname
    if not service_id and (hostname or machine_id or resolver_name):
        machine_id, resolver_name = _get_host_identifier(hostname, machine_id,
                                                         resolver_name)
        machineresolver_id = get_machineresolver_id(resolver_name)
        sql_query = MachineToken.query.filter(and_(MachineToken.machine_id == machine_id,
                                                   MachineToken.machineresolver_id == machineresolver_id))
    else:
        # If we have no specific machine defined, we find all applications/serials
        sql_query = MachineToken.query.filter()

    if application:
        sql_query = sql_query.filter(MachineToken.application == application)
    if serial:
        # discrete serial
        token_id = get_token_id(serial)
        sql_query = sql_query.filter(MachineToken.token_id == token_id)

    for row in sql_query.all():
        # row.token contains the database token
        option_list = row.option_list
        options = {}
        for option in option_list:
            options[option.mt_key] = option.mt_value
        include_mt = True
        # check serial_pattern
        if serial_pattern:
            if not re.match(serial_pattern, row.token.serial, re.I):
                include_mt = False
        # we still think, it should be included
        if include_mt:
            for key, value in filter_params.items():
                tokenoptionvalue = options.get(key, "")
                if "*" in value:
                    # Simple wildcard matching
                    pattern = value.replace("*", ".*")
                    # We do a case insensitive match
                    if not re.match(pattern, tokenoptionvalue, re.I):
                        include_mt = False
                elif tokenoptionvalue != value:
                    include_mt = False
        if include_mt:
            res.append({"serial": row.token.serial,
                        "machine_id": machine_id,
                        "resolver": resolver_name,
                        "type": row.token.tokentype,
                        "application": row.application,
                        "id": row.id,
                        "options": options})

    return res


@log_with(log)
def list_token_machines(serial):
    """
    This method returns the machines for a given token

    :return: returns a list of machines and apps
    """
    res = []
    db_token = fetch_one_resource(Token, serial=serial)

    for machine in db_token.machine_list:
        hostname = "unknown"
        if machine.machine_id and machine.machineresolver_id:
            MR = fetch_one_resource(MachineResolver, id=machine.machineresolver_id)
            resolver_name = MR.name
        else:
            resolver_name = NO_RESOLVER
            hostname = "any host"

        option_list = machine.option_list
        options = {}
        for option in option_list:
            options[option.mt_key] = option.mt_value

        # Try to determine the hostname
        machines = get_machines(id=machine.machine_id, resolver=resolver_name)
        if len(machines) == 1:
            # There is only one machine in the list and we get its ID
            hostname = machines[0].hostname
            # return the first hostname
            if type(hostname) == list:
                hostname = hostname[0]

        res.append({"machine_id": machine.machine_id or ANY_MACHINE,
                    "hostname": hostname,
                    "application": machine.application,
                    "resolver": resolver_name,
                    "options": options,
                    "id": machine.id,
                    "serial": serial})

    return res


def _get_host_identifier(hostname, machine_id, resolver_name):
    """
    This returns the combiniation of machine_id and resolver_name for some
    of the given values. This is used when attaching and detaching tokens to
    a machine to create a uniquely identifyable machine object.

    :param hostname:
    :param machine_id:
    :param resolver_name:
    :return:
    """
    if hostname:
        (machine_id, resolver_name) = get_machine_id(hostname)
    if not (machine_id and resolver_name):  # pragma: no cover
        raise Exception("Incomplete tuple of machine_id and resolver_name")

    return machine_id, resolver_name


def get_auth_items(hostname=None, ip=None, application=None,
                   serial=None, challenge=None, filter_param=None, user_agent=None):
    """
    Return the authentication items for a given hostname and the application.
    The hostname is used to identify the machine object. Then all attached
    tokens to this machine and its applications are searched.

    :param hostname:
    :param ip:
    :param application:
    :param serial:
    :param challenge: A challenge for the authitem
    :type challenge: basestring
    :param filter_param: Additional application specific parameter to filter
        the return value
    :type filter_param: dict
    :param user_agent: The user agent header of the request
    :type user_agent: str
    :return: dictionary of lists of the application auth items

    **Example response**:

    .. sourcecode:: json

       { "luks": [ { "slot": "....",
                     "partition": "....",
                     "challenge": "....",
                     "response": "...." }
                 ],
         "ssh": [ { "username": "....",
                    "sshkey": "...."},
                  { "username": "....",
                    "sshkey": "...." }
                 ] }
    """
    auth_items = {}
    machine_tokens = list_machine_tokens(hostname=hostname,
                                         serial=serial,
                                         application=application,
                                         filter_params=filter_param)

    for mtoken in machine_tokens:
        auth_item = get_auth_item(mtoken.get("application"),
                                  mtoken.get("type"),
                                  mtoken.get("serial"),
                                  challenge,
                                  options=mtoken.get("options"),
                                  filter_param=filter_param,
                                  user_agent=user_agent)
        if auth_item:
            if mtoken.get("application") not in auth_items:
                # we create a new empty list for the new application type
                auth_items[mtoken.get("application")] = []

            # Add the options to auth_item
            for k, v in mtoken.get("options", {}).items():
                auth_item[k] = v
            auth_item["serial"] = serial

            # append the auth_item to the list
            auth_items[mtoken.get("application")].append(auth_item)

    return auth_items
