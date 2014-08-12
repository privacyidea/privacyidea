# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  (c) 2014 Cornelius Kölbel, cornelius@privacyidea.org
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
'''
This file is part of the privacyidea service
'''
import logging

from pylons import request, response, config, tmpl_context as c

from privacyidea.lib.base import BaseController
from privacyidea.lib.token import get_token_type_list, getTokenType

from privacyidea.lib.util import getParam
from privacyidea.weblib.util import get_client
from privacyidea.lib.user import getUserFromRequest
from privacyidea.lib.reply import sendResult, sendError

from privacyidea.model.meta import Session
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.policy import PolicyException
from privacyidea.lib.error import ParameterError
from privacyidea.lib.config import get_privacyIDEA_config

from privacyidea.lib.machine import delete as delete_machine
from privacyidea.lib.machine import create as create_machine
from privacyidea.lib.machine import show as show_machine
from privacyidea.lib.machine import addtoken
from privacyidea.lib.machine import deltoken
from privacyidea.lib.machine import showtoken
from privacyidea.lib.machine import get_token_apps
from privacyidea.lib.machine import addoption
from privacyidea.lib.machine import deloption


import traceback
import webob
import json

from privacyidea.lib.log import log_with

log = logging.getLogger(__name__)

optional = True
required = False


class MachineController(BaseController):

    @log_with(log)
    def __before__(self, action, **params):
        '''
        '''
        try:
            c.audit['success'] = False
            c.audit['client'] = get_client()
            self.Policy = PolicyClass(request, config, c,
                                      get_privacyIDEA_config(),
                                      tokenrealms=request.params.get('serial'),
                                      token_type_list=get_token_type_list())
            self.set_language()

            self.before_identity_check(action)

            Session.commit()
            return request

        except webob.exc.HTTPUnauthorized as acc:
            # the exception, when an abort() is called if forwarded
            log.info("%r: webob.exception %r" % (action, acc))
            log.info(traceback.format_exc())
            Session.rollback()
            Session.close()
            raise acc

        except Exception as exx:
            log.error("exception %r" % (action, exx))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            return sendError(response, exx, context='before')

        finally:
            pass

    @log_with(log)
    def __after__(self, action, **params):
        '''
        '''
        params = {}

        try:
            params.update(request.params)
            c.audit['administrator'] = getUserFromRequest(request).get("login")
            if 'serial' in params:
                    c.audit['serial'] = request.params['serial']
                    c.audit['token_type'] = getTokenType(params.get('serial'))

            self.audit.log(c.audit)

            Session.commit()
            return request

        except Exception as e:
            log.error("unable to create a session cookie: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, context='after')

        finally:
            Session.close()

    @log_with(log)
    def create(self, action, **params):
        '''
        Create a new client machine entry

        :param name: the unique name of the machine (required).
                     Can be the FQDN.
        :param desc: description of the machine
        :param ip: The IP address of the machine (required)
        :param decommission: A date when the machine will not be valid anymore

        :return: True or False if the creation was successful.
        '''
        try:
            res = False
            param = {}
            # check machine authorization
            self.Policy.checkPolicyPre('machine', 'create')

            param.update(request.params)
            machine_name = getParam(param, "name", required)
            ip = getParam(param, "ip", required)
            desc = getParam(param, "desc", optional)
            decommission = getParam(param, "decommission", optional)
            machine = create_machine(machine_name,
                                     ip=ip,
                                     desc=desc,
                                     decommission=decommission)
            if machine:
                res = True
            Session.commit()
            c.audit["success"] = True
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()
            
    @log_with(log)
    def delete(self, action, **params):
        '''
        Delete an existing client machine entry
        
        :param name: the unique name of the machine
        
        :return: value is either true (success) or false (fail)
        '''
        try:
            res = {}
            param = {}
            # check machine authorization
            self.Policy.checkPolicyPre('machine', 'delete')
            param.update(request.params)
            machine_name = getParam(param, "name", required)
            res = delete_machine(machine_name)
            Session.commit()
            c.audit["success"] = True
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()

    @log_with(log)
    def show(self, action, **params):
        '''
        Returns a list of the client machines.
        
        :param name: Optional parameter to only show this single machine
        
        :return: JSON details
        '''
        try:
            res = {}
            param = {}
            # check machine authorization
            self.Policy.checkPolicyPre('machine', 'show')
            param.update(request.params)
            machine_name = getParam(param, "name", optional)
            
            res = show_machine(machine_name)
            Session.commit()
            c.audit["success"] = True
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()

    @log_with(log)
    def addtoken(self, action, **params):
        '''
        Add a token and a application to a machine
        
        :param name: Name of the machine
        :param serial: serial number of the token
        :param application: name of the application
        :param option_*: parameter is passed as additional option to
                         the machinetoken to be stored in 
                         machine_t_options table.
                         In case of LUKS application this can be
                         "option_slot"
        '''
        try:
            res = False
            param = {}
            options = {}
            # check machine authorization
            self.Policy.checkPolicyPre('machine', 'addtoken')
            param.update(request.params)
            machine_name = getParam(param, "name", required)
            serial = getParam(param, "serial", required)
            application = getParam(param, "application", required)
            
            if application.lower() not in config.get("applications").keys():
                log.error("Unknown application %r. Available applications: "
                          "%r" % (application, config.get("applications").keys()))
                raise Exception("Unkown application!")
            
            for p in param.keys():
                if p.startswith("option_"):
                    options[p] = param.get(p)
            
            mt = addtoken(machine_name,
                          serial,
                          application,
                          options=options)
            if mt:
                res = True
            Session.commit()
            c.audit["success"] = True
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()

    @log_with(log)
    def addoption(self, action, **params):
        '''
        Add an option to a machinetoken definition
        
        :param mtid: id of the machine token definition
        :param name: machine_name
        :param serial: serial number of the token
        :param application: application
        :param option_*: name of the option.
                         In case of LUKS application this can be
                         "option_slot"
                         
        You either need to provide the machine-token-id (mtid) directly or
        you need to provide the tuple (name, serial, application)
        '''
        try:
            num = -1
            param = {}
            options = {}
            # check machine authorization
            self.Policy.checkPolicyPre('machine', 'addtoken')
            param.update(request.params)
            mtid = getParam(param, "mtid", optional)
            machine_name = getParam(param, "name", optional)
            serial = getParam(param, "serial", optional)
            application = getParam(param, "application", optional)
            if not (mtid or (machine_name and serial and application)):
                raise ParameterError("You need to specify either mtid or"
                                     "the tuple name, serial, application",
                                     id=201)
               
            for p in param.keys():
                if p.startswith("option_"):
                    options[p] = param.get(p)
            
            num = addoption(mtid,
                            name=machine_name,
                            serial=serial,
                            application=application,
                            options=options)
            Session.commit()
            c.audit["success"] = True
            return sendResult(response, num, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()

    @log_with(log)
    def deloption(self, action, **params):
        '''
        Delete an option from a machinetoken definition
        
        :param mtid: id of the machine token definition
        :param name: machine_name
        :param serial: serial number of the token
        :param application: application
        :param key: key of the option to delete
                         
        You either need to provide the machine-token-id (mtid) directly or
        you need to provide the tuple (name, serial, application)
        '''
        try:
            num = -1
            param = {}
            options = {}
            # check machine authorization
            self.Policy.checkPolicyPre('machine', 'deltoken')
            param.update(request.params)
            mtid = getParam(param, "mtid", optional)
            machine_name = getParam(param, "name", optional)
            serial = getParam(param, "serial", optional)
            option_key = getParam(param, "key", required)
            application = getParam(param, "application", optional)
            if not (mtid or (machine_name and serial and application)):
                raise ParameterError("You need to specify either mtid or"
                                     "the tuple name, serial, application",
                                     id=201)
            num = deloption(mtid,
                            name=machine_name,
                            serial=serial,
                            application=application,
                            key=option_key)
            Session.commit()
            c.audit["success"] = True
            return sendResult(response, num, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()

    @log_with(log)
    def deltoken(self, action, **params):
        '''
        delete a token and a application from a machine
        
        :param name: Name of the machine
        :param serial: serial number of the token
        :param application: name of the application
        '''
        try:
            res = False
            param = {}
            # check machine authorization
            self.Policy.checkPolicyPre('machine', 'deltoken')
            param.update(request.params)
            machine_name = getParam(param, "name", required)
            serial = getParam(param, "serial", required)
            application = getParam(param, "application", required)
            
            res = deltoken(machine_name, serial, application)
            Session.commit()
            c.audit["success"] = True
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)
        finally:
            Session.close()

    @log_with(log)
    def showtoken(self, action, **params):
        '''
        show a token and a application from a machine
        This function is used in the flexigrid management
        
        :param name: Name of the machine
        :param serial: serial number of the token
        :param application: name of the application
        :param flexi: if set to 1, we do return flexigrid input
        '''
        try:
            res = False
            param = {}
            # check machine authorization
            self.Policy.checkPolicyPre('machine', 'showtoken')
            param.update(request.params)
            machine_name = getParam(param, "name", optional)
            serial = getParam(param, "serial", optional)
            application = getParam(param, "application", optional)
            # if set, this should be returned for flexigrid
            flexi = getParam(param, "flexi", optional)

            res = showtoken(machine_name,
                            serial,
                            application,
                            flexi=flexi,
                            params=param)
            Session.commit()
            c.audit["success"] = True
            if flexi:
                response.content_type = 'application/json'
                return json.dumps(res, indent=3)
            else:
                return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()

    @log_with(log)
    def gettokenapps(self, action, **params):
        '''
        returns the apps and the authentication information
        for the given machine.

        If an application is given only the authentication item for
        this application is returned. otherwise the application items
        for all applications are returned.

        TODO: Authenticate the client machine

        :param name: the machine name -
                    otherwise the machine is identified by the IP
        :type name: string, optional
        :param application: the name of the application. If the application is
                            given the response will also conatin the auth_item
        :type application: string, optional
        :param serial: The serial number of the token
        
        :return: dictionary with machine and authentication information
        
        
        {"total": 2,
         "machines":  { 1 : {"application": "luks",
                             "auth_item": {"challenge": "hex...",
                                           "response":: "hex..."},
                             "id": 1,
                             "ip": 10.0.0.1,
                             "machine_id": 1,
                             "machinename": "computerABC",
                             "serial": "<serialnumber of token>",
                             "token_id": 1
                            },
                        2 : ...
                      }
        }
        '''
        try:
            res = False
            param = {}
            self.Policy.checkPolicyPre('machine', 'gettokenapps')
            param.update(request.params)
            machine_name = getParam(param, "name", optional)
            application = getParam(param, "application", optional)
            serial = getParam(param, "serial", optional)
            # In case of LUKS and Yubikey we need the client to
            # pass the challenge as the challenge is the Password
            challenge = getParam(param, "challenge", optional)
            client_ip = get_client()
            
            if application:
                if application not in config.get("applications").keys():
                    log.error("Unknown application %r. Available applications:"
                              "%r" % (application,
                                      config.get("applications").keys()))
            application_module = config.get("applications").get(application)
            
            res = get_token_apps(machine=machine_name,
                                 application=application,
                                 application_module=application_module,
                                 serial=serial,
                                 client_ip=client_ip,
                                 challenge=challenge)
            Session.commit()
            c.audit["success"] = True
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()
     
    
       
    @log_with(log)
    def getapplications(self, action, **params):
        '''
        Returns a list of available applications
        '''
        try:
            return sendResult(response, config.get("applications").keys())
        
        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()
            