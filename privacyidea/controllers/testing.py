# -*- coding: utf-8 -*-
#
#
#  privacyIDEA is a fork of LinOTP
#  May 28, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
#    This program is free software: you can redistribute it and/or
#    modify it under the terms of the GNU Affero General Public
#    License, version 3, as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the
#               GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
"""
testing controller - for testing purposes only
This controller is only used in the test scripts.
"""



import logging

from pylons import request, response
from privacyidea.lib.base import BaseController

from privacyidea.lib.util import  getParam
from privacyidea.lib.user import  getUserFromParam

from privacyidea.lib.reply import sendResult, sendError

from privacyidea.model.meta import Session
from privacyidea.lib.selftest import isSelfTest
from privacyidea.lib.policy import PolicyClass

import traceback

optional = True
required = False

log = logging.getLogger(__name__)

#from paste.debug.profile import profile_decorator

class TestingController(BaseController):

    def __before__(self):
        return response


    def __after__(self):
        return response


    def autosms(self):
        '''
        This function is used to test the autosms policy

        method:
            testing/autosms

        arguments:
            user    - username / loginname
            realm   - additional realm to match the user to a useridresolver


        returns:
            JSON response
        '''
        log.debug('[autosms]')

        param = request.params
        try:

            if isSelfTest() == False:
                Session.rollback()
                return sendError(response, "The testing controller can only be used in SelfTest mode!", 0)

            user = getUserFromParam(param, required)
            Policy = PolicyClass()
            ok = Policy.get_auth_AutoSMSPolicy()

            Session.commit()
            return sendResult(response, ok, 0)

        except Exception as e:
            log.error("[autosms] validate/check failed: %r", e)
            log.error("[autosms] %s" % traceback.format_exc())
            Session.rollback()
            return sendError(response, "validate/check failed:" + unicode(e), 0)

        finally:
            Session.close()
            log.debug('[autosms] done')


    def http2sms(self):
        '''
        This function simulates an HTTP SMS Gateway.

        method:
            test/http2sms

        arguments:

           * sender, absender
           * from, von
           * destination, ziel
           * password, passwort
           * from, von
           * text
           * account
           * api_id


        returns:
           As this is a test controller, the response depends on the input values.

            account = 5vor12, sender = legit
                -> Response Success: "200" (Text)

            account = 5vor12, sender = <!legit>
                -> Response Failed: "Failed" (Text)

            account = clickatel, username = legit
                -> Response Success: "ID <Random Number>" (Text)

            account = clickatel, username = <!legit>
                -> Response Success: "FAILED" (Text)
        '''
        log.debug('[http2sms]')
        param = request.params

        try:
            account = getParam(param, "account", optional=False)
            sender = getParam(param, "sender", optional=True)
            username = getParam(param, "username", optional=True)

            destination = getParam(param, "destination")
            if not destination:
                destination = getParam(param, "ziel")

            text = getParam(param, "text")
            if not text:
                text = getParam(param, "text")

            if not destination:
                raise Exception("Missing <destination>")

            if not text:
                raise Exception("Missing <text>")

            if account == "5vor12":
                if sender == "legit":
                    return "200"
                else:
                    return "Failed"

            if account == "clickatel":
                if username == "legit":
                    return "ID 1000"
                else:
                    return "FAILED"

            Session.commit()
            return "Missing account info."

        except Exception as e:
            log.error('[http2sms] %r' % e)
            log.error("[http2sms] %s" % traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(e), 0)

        finally:
            Session.close()
            log.debug('[http2sms] done')


#eof###########################################################################

