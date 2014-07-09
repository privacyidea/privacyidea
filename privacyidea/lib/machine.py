# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  June 30, 2014 Cornelius Kölbel, info@privacyidea.org
#  http://www.privacyidea.org
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
from privacyidea.model import Machine
from privacyidea.model import Token
from privacyidea.model import MachineToken
from privacyidea.model import MachineOptions
from privacyidea.model.meta import Session
from privacyidea.lib.token import getTokens4UserOrSerial
from sqlalchemy import and_
from netaddr import IPAddress

import logging
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with


@log_with(log)
def create(name, ip=None, desc=None, decommission=None):
    machine = Machine(name, ip=ip, desc=desc, decommission=decommission)
    machine.store()
    log.info("Machine %r created." % machine)
    return machine


@log_with(log)
def delete(name):
    '''
    Delete the machine with the name and return the number of deleted machines
    
    Should always be 1
    Should be 0 if such a machine did not exist.
    '''
    mid = _get_machine_id(name)
    _assigns = Session.query(MachineToken)\
        .filter(MachineToken.machine_id == mid).delete()
    num = Session.query(Machine).filter(Machine.cm_name == name).delete()
    Session.commit()
    # 1 -> success
    return num == 1
    

@log_with(log)
def show(name=None, client_ip=None):
    res = {}
    cond_list = []
    if name:
        cond_list.append(Machine.cm_name == name)
    if client_ip:
        cond_list.append(Machine.cm_ip == client_ip)
                  
    condition = and_(*cond_list)
    sqlquery = Session.query(Machine).filter(condition)
    for machine in sqlquery:
        res[machine.cm_name] = machine.to_json()
    return res


def _get_machine_id(machine_name, client_ip=None):
    # determine the machine_id for the machine name
    machine = show(machine_name, client_ip)
    machine_id = machine.get(machine_name, {}).get("id")
    if machine_id is None:
        raise Exception("There is no machine with name=%r and IP=%r" %
                        (machine_name, client_ip))
    return machine_id


def _get_token_id(serial):
    # determine the token_id for the serial
    tokenlist = getTokens4UserOrSerial(serial=serial)
    if len(tokenlist) == 0:
        raise Exception("There is no token with the serial number %r" % serial)
    
    token_id = tokenlist[0].token.privacyIDEATokenId
    return token_id


@log_with(log)
def addtoken(machine_name, serial, application):
    machine_id = _get_machine_id(machine_name)
    if not machine_id:
        raise Exception("No machine with name %r found!" % machine_name)
    token_id = _get_token_id(serial)
    if not token_id:
        raise Exception("No token with serial %r found!" % serial)
    machinetoken = MachineToken(machine_id, token_id, application)
    machinetoken.store()
    return machinetoken


@log_with(log)
def deltoken(machine_name, serial, application):
    machine_id = _get_machine_id(machine_name)
    token_id = _get_token_id(serial)
    
    num = Session.query(MachineToken).\
        filter(and_(MachineToken.token_id == token_id,
                    MachineToken.machine_id == machine_id,
                    MachineToken.application == application)).delete()
    Session.commit()
    # 1 -> success
    return num == 1
    
    
@log_with(log)
def showtoken(machine_name=None,
              serial=None,
              application=None,
              client_ip=None,
              flexi=None,
              params=None):
    '''
    :param flexi: If set, the output will be in flexigrid format and
            we will output all machines, even if they have no token assigned
    :return: JSON of all tokens connected to machines with the corresponding
             application.
    '''
    res = {}
    machine_id = None
    token_id = None
    cond_list = []
    # default
    order = Machine.cm_name
    page = 1
    page_size = 15

    if machine_name:
        machine_id = _get_machine_id(machine_name, client_ip)
    if serial:
        token_id = _get_token_id(serial)
    
    if machine_id:
        cond_list.append(MachineToken.machine_id == machine_id)
    if token_id:
        cond_list.append(MachineToken.token_id == token_id)
    if application:
        cond_list.append(MachineToken.application == application)
    
    machines = {}
     
    # For flexigrid we use addtional parameter
    if flexi:
        if params:
            # Filtering
            qtype = params.get("qtype")
            query = params.get("query")
            if qtype == "machine":
                cond_list.append(Machine.cm_name.like("%" + query + "%"))
            elif qtype == "IP":
                cond_list.append(Machine.cm_ip.like("%" + query + "%"))
            elif qtype == "description":
                cond_list.append(Machine.cm_desc.like("%" + query + "%"))
            elif qtype == "serial":
                cond_list.append(Token.privacyIDEATokenSerialnumber.\
                                 like("%" + query + "%"))
            elif qtype == "application":
                cond_list.append(MachineToken.application.like("%" 
                                                               + query + "%"))

            condition = and_(*cond_list)

            # Flexigrid sorting
            sort = params.get("sortname")
            sort_order = params.get("sortorder")
            if sort == "machine_id":
                order = MachineToken.machine_id
            elif sort == "machine":
                order = Machine.cm_name
            elif sort == "IP":
                order = Machine.cm_ip
            elif sort == "description":
                order = Machine.cm_desc
            elif sort == "serial":
                order = Token.privacyIDEATokenSerialnumber
            elif sort == "application":
                order = MachineToken.application
            
            if sort_order is not None and sort_order == "desc":
                order = order.desc()
            else:
                order = order.asc()
                
            # pagination
            page = int(params.get("page", 1))
            page_size = int(params.get("rp", 15))

        sqlquery = Session.query(Machine,
                                 MachineToken.application,
                                 Token.privacyIDEATokenSerialnumber)\
                                        .outerjoin(MachineToken)\
                                        .outerjoin(Token)\
                                        .filter(condition)\
                                        .order_by(order)\
                                        .limit(page_size)\
                                        .offset(page_size*(page-1))
        # Fixme: This is not best way to determine the total count.
        sql_total = Session.query(Machine,
                              MachineToken.application,
                              Token.privacyIDEATokenSerialnumber)\
                                        .outerjoin(MachineToken)\
                                        .outerjoin(Token)\
                                        .filter(condition)
        total = 0
        for _i in sql_total:
            total += 1
        rows = []
        m_id = 0
        for row in sqlquery:
            machine, application, serial = row
            m_id += 1
            rows.append({'id': m_id,
                         'cell': [(m_id),
                                  (machine.id),
                                  (machine.cm_name),
                                  (machine.cm_ip),
                                  (machine.cm_desc),
                                  (serial),
                                  (application)]})
        
        res = {"page": page,
               "total": total}
        res["rows"] = rows
    else:
        condition = and_(*cond_list)
        sqlquery = Session.query(MachineToken).filter(condition)
        for row in sqlquery:
            machines[row.id] = row.to_json()
        res["total"] = len(machines)
        res["machines"] = machines

    Session.commit()
    return res


@log_with(log)
def get_token_apps(machine=None, application=None, client_ip=None):
    '''
    This method returns the authentication data for the
    requested application
    
    :param machine: the machine name (optional)
    :param application: the name of the application (optional)
    :param client: the IP of the client (required)
    '''
    if not client_ip:
        log.warning("No client IP.")
        return {}
    if not IPAddress(client_ip):
        log.warning("No valid client IP: %r" % client_ip)
        return {}

    res = showtoken(machine_name=machine,
                    client_ip=client_ip,
                    application=application)
    
    # add the authentication item to the result
    # for config in res.keys:
    #    res[config]
    
    return res
