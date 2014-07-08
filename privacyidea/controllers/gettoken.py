# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
It can retrieve information of the token,
exspecially the OTP value.
Use with care. This controller is usually disabled.
'''


import logging

from pylons import tmpl_context as c
from pylons import request, response
from pylons import config
from pylons.templating import render_mako as render


from privacyidea.lib.base import BaseController

from privacyidea.lib.util import getParam
from privacyidea.lib.util import get_client
from privacyidea.lib.user import getUserFromParam
from privacyidea.lib.user import getDefaultRealm
from privacyidea.lib.user import getUserFromRequest

from privacyidea.lib.token import get_token_type_list
from privacyidea.lib.token import getTokenType, getOtp, get_multi_otp, getTokens4UserOrSerial
from privacyidea.lib.token import getTokenRealms
from privacyidea.lib.policy import PolicyClass, PolicyException
from privacyidea.lib.reply import sendResult, sendError
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.model.meta import Session
from privacyidea.lib.log import log_with

import traceback

ENCODING = "utf-8"

optional = True
required = False

log = logging.getLogger(__name__)


class GettokenController(BaseController):

    '''
    The privacyidea.controllers are the implementation of the web-API to talk to the privacyIDEA server.
    The ValidateController is used to validate the username with its given OTP value.

    The Tagespasswort Token uses this controller to retrieve the current OTP value of
    the Token and be able to set it in the application
    The functions of the GettokenController are invoked like this

        https://server/gettoken/<functionname>

    The functions are described below in more detail.
    '''
    @log_with(log)
    def __before__(self, action, **params):
        try:
            c.audit['client'] = get_client()
            if request.params.get('serial'):
                tokentype = getTokenType(request.params.get('serial'))
            else:
                tokentype = None
            self.Policy = PolicyClass(request, config, c,
                                      get_privacyIDEA_config(),
                                      tokentype = tokentype,
                                      token_type_list = get_token_type_list())
            self.before_identity_check(action)


        except Exception as exx:
            log.error("%r exception %r" % (action, exx))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            return sendError(response, exx, context='before')

        finally:
            pass

    @log_with(log)
    def __after__(self, action, **params):
        c.audit['administrator'] = getUserFromRequest(request).get("login")
        if request.params.has_key('serial'):
                c.audit['serial'] = request.params['serial']
                c.audit['token_type'] = getTokenType(request.params['serial'])
        self.audit.log(c.audit)
        

    @log_with(log)
    def getmultiotp(self, action, **params):
        '''
        This function is used to retrieve multiple otp values for a given user or a given serial
        If the user has more than one token, the list of the tokens is returend.

        method:
            gettoken/getmultiotp

        
        :param serial: the serial number of the token
        :param count: number of otp values to return
        :param curTime: used ONLY for internal testing: datetime.datetime object
        :type curTime: datetime object
        :param timestamp: the unix time
        :type timestamp: int
        
        :return: JSON response
        '''

        getotp_active = config.get("privacyideaGetotp.active")
        if "True" != getotp_active:
            return sendError(response, "getotp is not activated.", 0)

        param = request.params
        ret = {}

        try:
            serial = getParam(param, "serial", required)
            tokenrealms = getTokenRealms(serial)
            count = int(getParam(param, "count", required))
            curTime = getParam(param, "curTime", optional)
            timestamp = getParam(param, "timestamp", optional)
            view = getParam(param, "view", optional)

            r1 = self.Policy.checkPolicyPre('admin', 'getotp', param,
                                            tokenrealms = tokenrealms)
            log.debug("admin-getotp returned %s" % r1)

            max_count = self.Policy.checkPolicyPre('gettoken', 'max_count', param,
                                                   tokenrealms = tokenrealms)
            log.debug("checkpolicypre returned %s" % max_count)
            if count > max_count:
                count = max_count

            log.debug("retrieving OTP value for token %s" % serial)
            ret = get_multi_otp(serial, count=int(count), curTime=curTime, timestamp=timestamp)
            ret["serial"] = serial

            c.audit['success'] = True
            Session.commit()

            if view:
                c.ret = ret
                return render('/manage/multiotp_view.mako')
            else:
                return sendResult(response, ret , 0)

        except PolicyException as pe:
            log.error("gettoken/getotp policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("gettoken/getmultiotp failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, "gettoken/getmultiotp failed: %s"
                             % unicode(e), 0)

        finally:
            Session.close()


    @log_with(log)
    def getotp(self, action, **params):
        '''
        This function is used to retrieve the current otp value for a given user or a given serial
        If the user has more than one token, the list of the tokens is returend.

        method:
            gettoken/getotp

        arguments:
            user    - username / loginname
            realm   - additional realm to match the user to a useridresolver
            serial  - the serial number of the token
            curTime - used ONY for internal testing: datetime.datetime object

        returns:
            JSON response
        '''

        getotp_active = config.get("privacyideaGetotp.active")
        if "True" != getotp_active:
            return sendError(response, "getotp is not activated.", 0)

        param = request.params
        ret = {}
        res = -1
        otpval = ""
        passw = ""
        serials = []

        try:

            serial = getParam(param, "serial", optional)
            user = getUserFromParam(param, optional)
            curTime = getParam(param, "curTime", optional)

            c.audit['user'] = user.login
            if "" != user.login:
                c.audit['realm'] = user.realm or getDefaultRealm()

            if serial:
                log.debug("retrieving OTP value for token %s" % serial)
            elif user.login:
                log.debug("retrieving OTP value for token for user %s@%s" % (user.login, user.realm))
                toks = getTokens4UserOrSerial(user, serial)
                tokennum = len(toks)
                if tokennum > 1:
                    log.debug("The user has more than one token. Returning the list of serials")
                    res = -3
                    for token in toks:
                        serials.append(token.getSerial())
                elif 1 == tokennum:
                    serial = toks[0].getSerial()
                    log.debug("retrieving OTP for token %s for user %s@%s" %
                                (serial, user.login, user.realm))
                else:
                    log.debug("no token found for user %s@%s" % (user.login, user.realm))
                    res = -4
            else:
                res = -5

            # if a serial was given or a unique serial could be received from the given user.
            if serial:
                tokenrealms = getTokenRealms(serial)
                max_count = self.Policy.checkPolicyPre('gettoken', 'max_count', param,
                                                       tokenrealms = tokenrealms)
                log.debug("checkpolicypre returned %s" % max_count)
                if max_count <= 0:
                    return sendError(response, "The policy forbids receiving OTP values for the token %s in this realm" % serial , 1)

                (res, pin, otpval, passw) = getOtp(serial, curTime=curTime)

            c.audit['success'] = True

            if int(res) < 0:
                ret['result'] = False
                if -1 == otpval:
                    ret['description'] = "No Token with this serial number"
                if -2 == otpval:
                    ret['description'] = "This Token does not support the getOtp function"
                if -3 == otpval:
                    ret['description'] = "The user has more than one token"
                    ret['serials'] = serials
                if -4 == otpval:
                    ret['description'] = "No Token found for this user"
                if -5 == otpval:
                    ret['description'] = "you need to provide a user or a serial"
            else:
                ret['result'] = True
                ret['otpval'] = otpval
                ret['pin'] = pin
                ret['pass'] = passw

            Session.commit()
            return sendResult(response, ret , 0)

        except PolicyException as pe:
            log.error("gettoken/getotp policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("gettoken/getotp failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, "gettoken/getotp failed: %s" % unicode(e), 0)

        finally:
            Session.close()


#eof###########################################################################

