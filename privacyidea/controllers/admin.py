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
'''
import logging

from pylons import request, response, config, tmpl_context as c


from privacyidea.lib.base import BaseController

from privacyidea.lib.token import enableToken, assignToken , unassignToken, removeToken
from privacyidea.lib.token import setPin, setMaxFailCount, setOtpLen, setSyncWindow, setCounterWindow
from privacyidea.lib.token import setDescription
from privacyidea.lib.token import resyncToken, resetToken, setPinUser, setPinSo, setHashLib, addTokenInfo
from privacyidea.lib.token import TokenIterator, initToken, setRealms, getTokenType, get_serial_by_otp
from privacyidea.lib.token import getTokens4UserOrSerial, copyTokenPin, copyTokenUser, losttoken, check_serial
from privacyidea.lib.token import getTokenRealms
from privacyidea.lib.token import genSerial
from privacyidea.lib.token import newToken
from privacyidea.lib.token import get_token_type_list

from privacyidea.lib.error import ParameterError
from privacyidea.lib.util import getParam, getLowerParams
from privacyidea.weblib.util import get_client
from privacyidea.lib.util import remove_session_from_param
from privacyidea.lib.user import getSearchFields, getUserList, User, getUserFromParam, getUserFromRequest

from privacyidea.lib.realm import getDefaultRealm

from privacyidea.lib.reply import sendResult, sendError, sendXMLResult, sendXMLError, sendCSVResult
from privacyidea.lib.reply import sendQRImageResult

from privacyidea.lib.validate import get_challenges

from privacyidea.model.meta import Session
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.policy import PolicyException
from privacyidea.lib.audit import logTokenNum
from privacyidea.lib.config import get_privacyIDEA_config
# for loading XML file
from privacyidea.lib.ImportOTP import parseSafeNetXML, parseOATHcsv, ImportException, parseYubicoCSV


from tempfile import mkstemp
import os
import traceback
import webob

from privacyidea.lib.log import log_with

# For logout
from webob.exc import HTTPUnauthorized


log = logging.getLogger(__name__)

optional = True
required = False


class AdminController(BaseController):

    '''
    The privacyidea.controllers are the implementation of the web-API to talk to the privacyIDEA server.
    The AdminController is used for administrative tasks like adding tokens to privacyIDEA,
    assigning tokens or revoking tokens.
    The functions of the AdminController are invoked like this

        https://server/admin/<functionname>

    The functions are described below in more detail.
    '''

    @log_with(log)
    def __before__(self, action, **params):
        '''
        '''
        try:
            c.audit['success'] = False
            c.audit['client'] = get_client()
            self.Policy = PolicyClass(request, config, c,
                                      get_privacyIDEA_config(),
                                      tokenrealms = request.params.get('serial'),
                                      token_type_list = get_token_type_list())
            self.set_language()

            self.before_identity_check(action)

            Session.commit()
            return request

        except webob.exc.HTTPUnauthorized as acc:
            ## the exception, when an abort() is called if forwarded
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
    def show(self, action, **params):
        """
        method:
            admin/show

        description:
            displays the list of the available tokens

        arguments:
            * serial  - optional: only this serial will be displayed
            * user    - optional: only the tokens of this user will be displayed. If the user does not exist,
              privacyidea will search tokens of users, who contain this substring.
              **TODO:** This can be very time consuming an will be changed in the next release to use wildcards.
            * filter  - optional: takes a substring to search in table token columns
            * viewrealm - optional: takes a realm, only the tokens in this realm will be displayed
            * sortby  - optional: sort the output by column
            * sortdir - optional: asc/desc
            * page    - optional: reqeuest a certain page
            * pagesize- optional: limit the number of returned tokens
            * user_fields - optional: additional user fields from the userid resolver of the owner (user)
            * outform - optional: if set to "csv", than the token list will be given in CSV

        returns:
            a json result with:
            { "head": [],
            "data": [ [row1], [row2] .. ]
            }

        exception:
            if an error occurs an exception is serialized and returned
        """

        param = request.params
        try:
            serial = getParam(param, "serial", optional)
            page = getParam(param, "page", optional)
            filter = getParam(param, "filter", optional)
            sort = getParam(param, "sortby", optional)
            dir = getParam(param, "sortdir", optional)
            psize = getParam(param, "pagesize", optional)
            realm = getParam(param, "viewrealm", optional)
            ufields = getParam(param, "user_fields", optional)
            output_format = getParam(param, "outform", optional)

            user_fields = []
            if ufields:
                user_fields = [u.strip() for u in ufields.split(",")]

            user = getUserFromParam(param, optional)

            filterRealm = []
            # check admin authorization
            res = self.Policy.checkPolicyPre('admin', 'show', param , user=user)

            filterRealm = res['realms']
            # check if policies are active at all
            # If they are not active, we are allowed to SHOW any tokens.
            pol = self.Policy.getAdminPolicies("show")
            # If there are no admin policies, we are allowed to see all realms
            if not pol['active']:
                filterRealm = ["*"]

            # If the admin wants to see only one realm, then do it:
            log.debug("[checking to only see tokens in realm <%s>" % realm)
            if realm:
                if realm in filterRealm or '*' in filterRealm:
                    filterRealm = [realm]

            log.info("admin >%s< may display the following realms: %s" % (res['admin'], filterRealm))
            log.debug("displaying tokens: serial: %s, page: %s, filter: %s, user: %s", serial, page, filter, user.login)

            toks = TokenIterator(user, serial, page, psize, filter, sort, dir, filterRealm, user_fields)

            c.audit['success'] = True
            c.audit['info'] = "realm: %s, filter: %r" % (filterRealm, filter)

            # put in the result
            result = {}

            # now row by row
            lines = []
            for tok in toks:
                # CKO:
                log.debug("tokenline: %s" % tok)
                lines.append(tok)

            result["data"] = lines
            result["resultset"] = toks.getResultSetInfo()

            Session.commit()

            if output_format == "csv":
                return sendCSVResult(response, result)
            else:
                return sendResult(response, result)

        except PolicyException as pe:
            log.error('policy failed: %r' % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error('failed: %r' % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()



########################################################
    @log_with(log)
    def remove(self, action, **params):
        """
        method:
            admin/remove

        description:
            deletes either a certain token given by serial or all tokens of a user

        arguments:
            * serial  - optional
            * user    - optional

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        param = request.params

        try:
            serial = getParam(param, "serial", optional)
            user = getUserFromParam(param, optional)

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'remove', param)

            log.info("removing token with serial %s for user %s", serial, user.login)
            ret = removeToken(user, serial)

            c.audit['user'] = user.login
            c.audit['realm'] = user.realm
            logTokenNum()
            c.audit['success'] = ret

            Session.commit()
            return sendResult(response, ret)

        except PolicyException as pe:
            log.error("policy failed %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed! %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def enable (self, action, **params):
        """
        method:
            admin/enable

        description:
            enables a token or all tokens of a user

        arguments:
            * serial  - optional
            * user    - optional

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        param = request.params
        try:
            serial = getParam(param, "serial", optional)
            user = getUserFromParam(param, optional)

            # check admin authorization
            # Determine the token realm, the token is in.
            tokenrealms = []
            if serial:
                tokenrealms = getTokenRealms(serial)
            self.Policy.checkPolicyPre('admin', 'enable', param , user=user,
                                        tokenrealms = tokenrealms)
            log.info("enable token with serial %s for user %s@%s.", serial, user.login, user.realm)
            ret = enableToken(True, user, serial)

            c.audit['success'] = ret
            c.audit['user'] = user.login
            c.audit['realm'] = user.realm
            logTokenNum()
            Session.commit()
            return sendResult(response, ret, 1)

        except PolicyException as pe:
            log.error("policy failed %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            
            return sendError(response, e, 1)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def getSerialByOtp (self, action, **params):
        """
        method:
            admin/getSerialByOtp

        description:
            searches for the token, that generates the given OTP value.
            The search can be restricted by several critterions

        arguments:
            * otp      - required. Will search for the token, that produces this OTP value
            * type     - optional, will only search in tokens of type
            * realm    - optional, only search in this realm
            * assigned - optional. 1: only search assigned tokens, 0: only search unassigned tokens

        returns:
            a json result with the serial


        exception:
            if an error occurs an exception is serialized and returned

        """
        ret = {}
        param = request.params

        try:
            otp = getParam(param, "otp", required)
            typ = getParam(param, "type", optional)
            realm = getParam(param, "realm", optional)
            assigned = getParam(param, "assigned", optional)

            serial = ""
            username = ""

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'getserial', param)

            serial, username, resolverClass = get_serial_by_otp(None, otp, 10, typ=typ, realm=realm, assigned=assigned)
            log.debug("found %s with user %s" % (serial, username))

            if "" != serial:
                self.Policy.checkPolicyPost('admin', 'getserial', {'serial' : serial})

            c.audit['success'] = 1
            c.audit['serial'] = serial

            ret['success'] = True
            ret['serial'] = serial
            ret['user_login'] = username
            ret['user_resolver'] = resolverClass

            Session.commit()
            return sendResult(response, ret, 1)

        except PolicyException as pe:
            log.error("policy failed %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            c.audit['success'] = 0
            Session.rollback()
            log.error('error: %r' % e)
            log.error(traceback.format_exc())
            return sendError(response, e, 1)

        finally:
            Session.close()



########################################################
    @log_with(log)
    def disable (self, action, **params):
        """
        method:
            admin/disable

        description:
            disables a token given by serial or all tokens of a user

        arguments:
            * serial  - optional
            * user    - optional

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        param = request.params
        try:
            serial = getParam(param, "serial", optional)
            user = getUserFromParam(param, optional)

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'disable', param, user=user)

            log.info("disable token with serial %s for user %s@%s.", serial, user.login, user.realm)
            ret = enableToken(False, user, serial)

            c.audit['success'] = ret
            c.audit['user'] = user.login
            c.audit['realm'] = user.realm
            Session.commit()
            return sendResult(response, ret, 1)

        except PolicyException as pe:
            log.error("policy failed %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed! %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


#######################################################
    @log_with(log)
    def check_serial(self, action, **params):
        '''
        method
            admin/check_serial

        description:
            This function checks, if a given serial will be unique.
            It returns True if the serial does not yet exist and
            new_serial as a new value for a serial, that does not exist, yet

        arguments:
            serial    - required- the serial to be checked

        returns:
            a json result with a new suggestion for the serial

        exception:
            if an error occurs an exception is serialized and returned

        '''
        param = request.params
        try:
            serial = getParam(param, "serial", required)

            # check admin authorization
            #try:
            #    self.Policy.checkPolicyPre('admin', 'disable', param )
            #except PolicyException as pe:
            #    return sendError(response, str(pe), 1)

            log.info("checking serial %s" % serial)
            (unique, new_serial) = check_serial(serial)

            c.audit['success'] = True
            c.audit['serial'] = serial
            c.audit['action_detail'] = "%r - %r" % (unique, new_serial)

            Session.commit()
            return sendResult(response, {"unique":unique, "new_serial":new_serial}, 1)

        except PolicyException as pe:
            log.error("policy failed %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed! %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()


########################################################
    @log_with(log, log_entry=False)
    def init(self, action, **params):
        """
        method:
            admin/init

        description:
            creates a new token.

        arguments:
            * otpkey    - required - the hmac Key of the token
            * genkey    - required - =1, if key should be generated. We either need otpkey or genkey
            * keysize   - optional - either 20 or 32. Default is 20
            * serial    - required - the serial number / identifier of the token
            * description - optional
            * pin        - optional - the pin of the user pass
            * user       - optional - login user name
            * realm      - optional - realm of the user
            * type       - optional - the type of the token
            * tokenrealm - optional - the realm a token should be put into
            * otplen     - optional  - length of the OTP value
            * hashlib    - optional  - used hashlib sha1 oder sha256

        ocra arguments:
            for generating OCRA Tokens type=ocra you can specify the following parameters:

            * ocrasuite    - optional - if you do not want to use the default ocra suite OCRA-1:HOTP-SHA256-8:QA64
            * sharedsecret - optional - if you are in Step0 of enrolling an OCRA/QR token the
              sharedsecret=1 specifies,
              that you want to generate a shared secret
            * activationcode - optional - if you are in Step1 of enrolling an OCRA token you need to pass the
              activation code, that was generated in the QRTAN-App

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        ret = False
        response_detail = {}
        helper_param = {}

        try:
            tokenrealm = None
            param = request.params
            helper_param.update(param)

            user = getUserFromParam(param, optional)

            # check admin authorization
            res = self.Policy.checkPolicyPre('admin', 'init', param, user=user,
                                             options={'token_num' : len(getTokens4UserOrSerial(user))})

            if user is not None:
                helper_param['user.login'] = user.login
                helper_param['user.realm'] = user.realm

            ## for genkey, we have to transfer this to the lowest level
            key_size = getParam(param, "keysize", optional) or 20
            helper_param['key_size'] = key_size

            tok_type = getParam(param, "type", optional) or 'hmac'

            # if no user is given, we put the token in all realms of the admin
            if user.login == "":
                log.debug("setting tokenrealm %s" % res['realms'])
                tokenrealm = res['realms']


            ## look for the tokenclass to support a class init
            ## the classInit could do a rewrite of the request parameters
            ## which are then used in the tokenInit as parameters
            ## this is for example
            ##   to find all open init challenges of a token type and set the
            ##   serial number in the parameter list

            g = config['pylons.app_globals']
            tokenclasses = g.tokenclasses

            tokenTypes = tokenclasses.keys()
            if tok_type in tokenTypes:
                tclass = tokenclasses.get(tok_type)
                tclass_object = newToken(tclass)
                if hasattr(tclass_object, 'classInit'):
                    h_params = tclass_object.classInit(param, user=user)
                    helper_param.update(h_params)


            serial = helper_param.get('serial', None)
            prefix = helper_param.get('prefix', None)
            if serial is None or len(serial) == 0:
                serial = genSerial(tok_type, prefix)
                helper_param['serial'] = serial


            log.info("initialize token. user: %s, serial: %s" % (user.login, serial))
            (ret, tokenObj) = initToken(helper_param, user, tokenrealm=tokenrealm)

            ## result enrichment - if the token is sucessfully created,
            ## some processing info is added to the result document,
            ##  e.g. the otpkey :-) as qr code
            initDetail = tokenObj.getInitDetail(helper_param, user)
            response_detail.update(initDetail)

            c.audit['success'] = ret
            c.audit['user'] = user.login
            c.audit['realm'] = user.realm

            logTokenNum()

            # setting the random PIN
            randomPINLength = self.Policy.getRandomOTPPINLength(user)
            if randomPINLength > 0:
                newpin = self.Policy.getRandomPin(randomPINLength)
                log.debug("setting random pin for token with serial "
                              "%s and user: %s" % (serial, user))
                setPin(newpin, None, serial)
                
            c.audit['success'] = ret

            Session.commit()

            ## finally we render the info as qr immage, if the qr parameter
            ## is provided and if the token supports this
            if 'qr' in param and tokenObj is not None:
                (rdata, hparam) = tokenObj.getQRImageData(response_detail)
                hparam.update(response_detail)
                hparam['qr'] = param.get('qr') or 'html'
                return sendQRImageResult(response, rdata, hparam)
            else:
                return sendResult(response, ret, opt=response_detail)

        except PolicyException as pe:
            log.error("policy failed %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("token initialization failed! %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def unassign(self, action, **params):
        """
        method:
            admin/unassign - remove the assigned user from the token

        description:
            unassigns a token from a user. i.e. the binding between the token
            and the user is removed

        arguments:
            * serial    - required - the serial number / identifier of the token
            * user      - optional

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        param = request.params

        try:

            serial = getParam(param, "serial", required)
            user = getUserFromParam(param, optional)
            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'unassign', param)
            log.info("unassigning token with serial %r from "
                     "user %r@%r" % (serial, user.login, user.realm))
            res = unassignToken(serial, user, None)

            c.audit['success'] = res
            c.audit['user'] = user.login
            c.audit['realm'] = user.realm
            if "" == c.audit['realm']:
                c.audit['realm'] = getDefaultRealm()

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error('policy failed %r' % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed! %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def assign(self, action, **params):
        """
        method:
            admin/assign

        description:
            assigns a token to a user, i.e. a binding between the token and
            the user is created.

        arguments:
            * serial     - required - the serial number / identifier of the token
            * user       - required - login user name
            * pin        - optional - the pin of the user pass

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        param = request.params

        try:

            upin = getParam(param, "pin", optional)
            serial = getParam(param, "serial", optional)
            user = getUserFromParam(param, optional)

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'assign', param)

            log.info("assigning token with serial %s to user %s@%s" % (serial, user.login, user.realm))
            res = assignToken(serial, user, upin, param)

            c.audit['success'] = res
            c.audit['user'] = user.login
            c.audit['realm'] = user.realm

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error('policy failed %r' % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e :
            log.error('token assignment failed! %r' % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 0)

        finally:
            Session.close()



########################################################
    @log_with(log)
    def setPin(self, action, **params):
        """
        method:
            admin/set

        description:
            This function sets the smartcard PINs of a eTokenNG OTP.
            The userpin is used to store the mOTP PIN of mOTP tokens!
            !!! For setting the OTP PIN, use the function /admin/set!

        arguments:
            * serial     - required
            * userpin    - optional: store the userpin
            * sopin      - optional: store the sopin

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}
        count = 0

        description = "setPin: parameters are\
        serial\
        userpin\
        sopin\
        "
        try:
            param = getLowerParams(request.params)

            ## if there is a pin
            if param.has_key("userpin"):
                msg = "setting userPin failed"
                userPin = getParam(param, "userpin", required)
                serial = getParam(param, "serial", required)

                # check admin authorization
                self.Policy.checkPolicyPre('admin', 'setPin', param)

                log.info("setting userPin for token with serial %s" % serial)
                ret = setPinUser(userPin, serial)
                res["set userpin"] = ret
                count = count + 1
                c.audit['action_detail'] += "userpin, "

            if param.has_key("sopin"):
                msg = "setting soPin failed"
                soPin = getParam(param, "sopin", required)
                serial = getParam(param, "serial", required)

                # check admin authorization
                self.Policy.checkPolicyPre('admin', 'setPin', param)

                log.info("setting soPin for token with serial %s" % serial)
                ret = setPinSo(soPin, serial)
                res["set sopin"] = ret
                count = count + 1
                c.audit['action_detail'] += "sopin, "

            if count == 0 :
                Session.rollback()
                return sendError(response, ParameterError("Usage: %s" % description, id=77))

            c.audit['success'] = count

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error('policy failed %r, %r' % (msg, pe))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)


        except Exception as e :
            log.error('%s :%r' % (msg, e))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(e), 0)

        finally:
            Session.close()



########################################################
    @log_with(log)
    def set(self, action, **params):
        """
        method:
            admin/set

        description:
            this function is used to set many different values of a token.

        arguments:
            * serial     - optional
            * user       - optional
            * pin        - optional - set the OTP PIN
            * MaxFailCount  - optional - set the maximum fail counter of a token
            * SyncWindow    - optional - set the synchronization window of the token
            * OtpLen        - optional - set the OTP Lenght of the token
            * CounterWindow - optional - set the counter window (blank presses)
            * hashlib       - optioanl - set the hashing algo for HMAC tokens. This can be sha1, sha256, sha512
            * timeWindow    - optional - set the synchronize window for timebased tokens (in seconds)
            * timeStep      - optional - set the timestep for timebased tokens (usually 30 or 60 seconds)
            * timeShift     - optional - set the shift or timedrift of this token
            * countAuthSuccessMax    - optional    - set the maximum allowed successful authentications
            * countAuthSuccess\      - optional    - set the counter of the successful authentications
            * countAuth        - optional - set the counter of authentications
            * countAuthMax     - optional - set the maximum allowed authentication tries
            * validityPeriodStart    - optional - set the start date of the validity period. The token can not be used before this date
            * validityPeriodEnd      - optional - set the end date of the validaity period. The token can not be used after this date
            * phone - set the phone number for an SMS token

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}
        count = 0

        description = "set: parameters are\
        pin\
        MaxFailCount\
        SyncWindow\
        OtpLen\
        CounterWindow\
        hashlib\
        timeWindow\
        timeStep\
        timeShift\
        countAuthSuccessMax\
        countAuthSuccess\
        countAuth\
        countAuthMax\
        validityPeriodStart\
        validityPeriodEnd\
        description\
        phone\
        "
        msg = ""

        try:
            param = getLowerParams(request.params)

            serial = getParam(param, "serial", optional)
            user = getUserFromParam(param, optional)

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'set', param, user=user)

            ## if there is a pin
            if param.has_key("pin"):
                msg = "setting pin failed"
                upin = getParam(param, "pin", required)
                log.info("setting pin for token with serial %r" % serial)
                if serial is not None:
                    tokenrealms=getTokenRealms(serial)
                else:
                    tokenrealms=[]
                if 1 == self.Policy.getOTPPINEncrypt(serial=serial, user=user, 
                                                     tokenrealms=tokenrealms):
                    param['encryptpin'] = "True"
                ret = setPin(upin, user, serial, param)
                res["set pin"] = ret
                count = count + 1
                c.audit['action_detail'] += "pin, "

            if param.has_key("MaxFailCount".lower()):
                msg = "setting MaxFailCount failed"
                maxFail = int(getParam(param, "MaxFailCount".lower(), required))
                log.info("setting maxFailCount (%r) for token with serial %r" % (maxFail, serial))
                ret = setMaxFailCount(maxFail, user, serial)
                res["set MaxFailCount"] = ret
                count = count + 1
                c.audit['action_detail'] += "maxFailCount=%d, " % maxFail

            if param.has_key("SyncWindow".lower()):
                msg = "setting SyncWindow failed"
                syncWindow = int(getParam(param, "SyncWindow".lower(), required))
                log.info("setting syncWindow (%r) for token with serial %r" % (syncWindow, serial))
                ret = setSyncWindow(syncWindow, user, serial)
                res["set SyncWindow"] = ret
                count = count + 1
                c.audit['action_detail'] += "syncWindow=%d, " % syncWindow

            if param.has_key("description".lower()):
                msg = "setting description failed"
                description = getParam(param, "description".lower(), required)
                log.info("setting description (%r) for token with serial %r" % (description, serial))
                ret = setDescription(description, user, serial)
                res["set description"] = ret
                count = count + 1
                c.audit['action_detail'] += "description=%r, " % description

            if param.has_key("CounterWindow".lower()):
                msg = "setting CounterWindow failed"
                counterWindow = int(getParam(param, "CounterWindow".lower(), required))
                log.info("setting counterWindow (%r) for token with serial %r" % (counterWindow, serial))
                ret = setCounterWindow(counterWindow, user, serial)
                res["set CounterWindow"] = ret
                count = count + 1
                c.audit['action_detail'] += "counterWindow=%d, " % counterWindow

            if param.has_key("OtpLen".lower()):
                msg = "setting OtpLen failed"
                otpLen = int(getParam(param, "OtpLen".lower(), required))
                log.info("setting OtpLen (%r) for token with serial %r" % (otpLen, serial))
                ret = setOtpLen(otpLen, user, serial)
                res["set OtpLen"] = ret
                count = count + 1
                c.audit['action_detail'] += "otpLen=%d, " % otpLen

            if param.has_key("hashlib".lower()):
                msg = "setting hashlib failed"
                hashlib = getParam(param, "hashlib".lower(), required)
                log.info("setting hashlib (%r) for token with serial %r" % (hashlib, serial))
                ret = setHashLib(hashlib, user, serial)
                res["set hashlib"] = ret
                count = count + 1
                c.audit['action_detail'] += "hashlib=%s, " % unicode(hashlib)

            if param.has_key("timeWindow".lower()):
                msg = "setting timeWindow failed"
                timeWindow = int(getParam(param, "timeWindow".lower(), required))
                log.info("setting timeWindow (%r) for token with serial %r" % (timeWindow, serial))
                ret = addTokenInfo("timeWindow", timeWindow , user, serial)
                res["set timeWindow"] = ret
                count = count + 1
                c.audit['action_detail'] += "timeWindow=%d, " % timeWindow

            if param.has_key("timeStep".lower()):
                msg = "setting timeStep failed"
                timeStep = int(getParam(param, "timeStep".lower(), required))
                log.info("setting timeStep (%r) for token with serial %r" % (timeStep, serial))
                ret = addTokenInfo("timeStep", timeStep , user, serial)
                res["set timeStep"] = ret
                count = count + 1
                c.audit['action_detail'] += "timeStep=%d, " % timeStep

            if param.has_key("timeShift".lower()):
                msg = "setting timeShift failed"
                timeShift = int(getParam(param, "timeShift".lower(), required))
                log.info("setting timeShift (%r) for token with serial %r" % (timeShift, serial))
                ret = addTokenInfo("timeShift", timeShift , user, serial)
                res["set timeShift"] = ret
                count = count + 1
                c.audit['action_detail'] += "timeShift=%d, " % timeShift

            if param.has_key("countAuth".lower()):
                msg = "setting countAuth failed"
                ca = int(getParam(param, "countAuth".lower(), required))
                log.info("setting count_auth (%r) for token with serial %r" % (ca, serial))
                tokens = getTokens4UserOrSerial(user, serial)
                ret = 0
                for tok in tokens:
                    tok.set_count_auth(int(ca))
                    count = count + 1
                    ret += 1
                res["set countAuth"] = ret
                c.audit['action_detail'] += "countAuth=%d, " % ca

            if param.has_key("countAuthMax".lower()):
                msg = "setting countAuthMax failed"
                ca = int(getParam(param, "countAuthMax".lower(), required))
                log.info("setting count_auth_max (%r) for token with serial %r" % (ca, serial))
                tokens = getTokens4UserOrSerial(user, serial)
                ret = 0
                for tok in tokens:
                    tok.set_count_auth_max(int(ca))
                    count = count + 1
                    ret += 1
                res["set countAuthMax"] = ret
                c.audit['action_detail'] += "countAuthMax=%d, " % ca

            if param.has_key("countAuthSuccess".lower()):
                msg = "setting countAuthSuccess failed"
                ca = int(getParam(param, "countAuthSuccess".lower(), required))
                log.info("setting count_auth_success (%r) for token with serial %r" % (ca, serial))
                tokens = getTokens4UserOrSerial(user, serial)
                ret = 0
                for tok in tokens:
                    tok.set_count_auth_success(int(ca))
                    count = count + 1
                    ret += 1
                res["set countAuthSuccess"] = ret
                c.audit['action_detail'] += "countAuthSuccess=%d, " % ca

            if param.has_key("countAuthSuccessMax".lower()):
                msg = "setting countAuthSuccessMax failed"
                ca = int(getParam(param, "countAuthSuccessMax".lower(), required))
                log.info("setting count_auth_success_max (%r) for token with serial %r" % (ca, serial))
                tokens = getTokens4UserOrSerial(user, serial)
                ret = 0
                for tok in tokens:
                    tok.set_count_auth_success_max(int(ca))
                    count = count + 1
                    ret += 1
                res["set countAuthSuccessMax"] = ret
                c.audit['action_detail'] += "countAuthSuccessMax=%d, " % ca

            if param.has_key("validityPeriodStart".lower()):
                msg = "setting validityPeriodStart failed"
                ca = getParam(param, "validityPeriodStart".lower(), required)
                log.info("setting validity_period_start (%r) for token with serial %r" % (ca, serial))
                tokens = getTokens4UserOrSerial(user, serial)
                ret = 0
                for tok in tokens:
                    tok.set_validity_period_start(ca)
                    count = count + 1
                    ret += 1
                res["set validityPeriodStart"] = ret
                c.audit['action_detail'] += u"validityPeriodStart=%s, " % unicode(ca)

            if param.has_key("validityPeriodEnd".lower()):
                msg = "setting validityPeriodEnd failed"
                ca = getParam(param, "validityPeriodEnd".lower(), required)
                log.info("setting validity_period_end (%r) for token with serial %r" % (ca, serial))
                tokens = getTokens4UserOrSerial(user, serial)
                ret = 0
                for tok in tokens:
                    tok.set_validity_period_end(ca)
                    count = count + 1
                    ret += 1
                res["set validityPeriodEnd"] = ret
                c.audit['action_detail'] += "validityPeriodEnd=%s, " % unicode(ca)

            if "phone" in param:
                msg = "setting phone failed"
                ca = getParam(param, "phone".lower(), required)
                log.info("setting phone (%r) for token with serial %r" % (ca, serial))
                tokens = getTokens4UserOrSerial(user, serial)
                ret = 0
                for tok in tokens:
                    tok.addToTokenInfo("phone", ca)
                    count = count + 1
                    ret += 1
                res["set phone"] = ret
                c.audit['action_detail'] += "phone=%s, " % unicode(ca)

            if count == 0 :
                Session.rollback()
                return sendError(response, ParameterError("Usage: %s" % description, id=77))

            c.audit['success'] = count
            c.audit['user'] = user.login
            c.audit['realm'] = user.realm

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error('policy failed: %s, %r' % (msg, pe))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e :
            log.error('%s :%r' % (msg, e))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()



########################################################
    @log_with(log)
    def resync(self, action, **params):
        """
        method:
            admin/resync - resync a token to a new counter

        description:
            this function resync the token, if the counter on server side is out of sync
            with the physica token.

        arguments:
            * serial     - serial or user required
            * user       - s.o.
            * otp1       - the next otp to be found
            * otp2       - the next otp after the otp1

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        param = request.params
        try:
            serial = getParam(param, "serial", optional)
            user = getUserFromParam(param, optional)

            otp1 = getParam(param, "otp1", required)
            otp2 = getParam(param, "otp2", required)

            ''' to support the challenge based resync, we have to pass the challenges
                down to the token implementation
            '''
            chall1 = getParam(param, "challenge1", optional)
            chall2 = getParam(param, "challenge2", optional)

            options = None
            if chall1 is not None and chall2 is not None:
                options = {'challenge1' : chall1, 'challenge2':chall2 }

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'resync', param)

            log.info("resyncing token with serial %r, user %r@%r"
                     % (serial, user.login, user.realm))
            res = resyncToken(otp1, otp2, user, serial, options)

            c.audit['success'] = res
            c.audit['user'] = user.login
            c.audit['realm'] = user.realm
            if "" == c.audit['realm'] and "" != c.audit['user']:
                c.audit['realm'] = getDefaultRealm()

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error('policy failed %r' % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error('resyncing token failed %r' % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def userlist(self, action, **params):
        """
        method:
            admin/userlist - list all users

        description:
            lists the user in a realm

        arguments:
            * <searchexpr> - will be retrieved from the UserIdResolverClass
            * realm	 - a realm, which is a collection of resolver configurations
            * resConf	 - a destinct resolver configuration

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        users = []
        param = request.params

        # check admin authorization
        # check if we got a realm or resolver, that is ok!
        try:
            realm = getParam(param, "realm", optional)
            #_resolver = getParam(param, "resConf", optional)

            self.Policy.checkPolicyPre('admin', 'userlist',
                           { 'user': "dummy", 'realm':realm})

            up = 0
            user = getUserFromParam(param, optional)

            log.info("displaying users with param: %s, ", param)

            if (len(user.realm) > 0):
                up = up + 1
            if (len(user.conf) > 0):
                up = up + 1
            # Here we need to list the users, that are only visible in the realm!!
            #  we could also only list the users in the realm, if the admin got
            #  the right "userlist".

            ### list searchfields if no other param
            if len(param) == up:
                usage = {"usage":"list available users matching the given search patterns:"}
                usage["searchfields"] = getSearchFields(user)
                res = usage
            else:
                users = getUserList(remove_session_from_param(param), user)
                res = users

                c.audit['success'] = True
                c.audit['info'] = "realm: %s" % realm

            Session.commit()
            return sendResult(response, res)

        except PolicyException as pe:
            log.error('policy failed %r' % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def tokenrealm(self, action, **params):
        '''
        method:
            admin/tokenrealm - set the realms a token belongs to

        description:
            sets the realms of a token

        arguments:
            * serial    - required -  serialnumber of the token
            * realms    - required -  comma seperated list of realms
        '''
        param = request.params
        try:
            serial = getParam(param, "serial", required)
            realms = getParam(param, "realms", required)

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'tokenrealm', param)

            log.info("setting realms for token %s to %s" % (serial, realms))
            realmList = realms.split(',')
            ret = setRealms(serial, realmList)

            c.audit['success'] = ret
            c.audit['info'] = realms

            Session.commit()
            return sendResult(response, ret, 1)

        except PolicyException as pe:
            log.error('policy failed %r' % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error('error setting realms for token %r' % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def reset(self, action, **params):
        """
        method:
            admin/reset

        description:
            reset the FailCounter of a Token

        arguments:
            user or serial - to identify the tokens

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        param = request.params

        serial = getParam(param, "serial", optional)
        user = getUserFromParam(param, optional)

        try:

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'reset', param , user=user)

            log.info("resetting the FailCounter for token with serial %s" % serial)
            ret = resetToken(user, serial)

            c.audit['success'] = ret
            c.audit['user'] = user.login
            c.audit['realm'] = user.realm

            # DeleteMe: This code will never run, since getUserFromParam
            # always returns a realm!
            #if "" == c.audit['realm'] and "" != c.audit['user']:
            #    c.audit['realm'] = getDefaultRealm()

            Session.commit()
            return sendResult(response, ret)

        except PolicyException as pe:
            log.error('policy failed %r' % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as exx:
            log.error("Error resetting failcounter %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()



########################################################
    @log_with(log)
    def copyTokenPin(self, action, **params):
        """
        method:
            admin/copyTokenPin

        description:
            copies the token pin from one token to another

        arguments:
            * from - required - serial of token from
            * to   - required - serial of token to

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        ret = 0
        err_string = ""
        param = request.params

        try:
            serial_from = getParam(param, "from", required)
            serial_to = getParam(param, "to", required)

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'copytokenpin', param)

            log.info("copying Pin from token %s to token %s" % (serial_from, serial_to))
            ret = copyTokenPin(serial_from, serial_to)

            c.audit['success'] = ret
            c.audit['serial'] = serial_to
            c.audit['action_detail'] = "from %s" % serial_from

            err_string = unicode(ret)
            if -1 == ret:
                err_string = "can not get PIN from source token"
            if -2 == ret:
                err_string = "can not set PIN to destination token"
            if 1 != ret:
                c.audit['action_detail'] += ", " + err_string
                c.audit['success'] = 0

            Session.commit()
            # Success
            if 1 == ret:
                return sendResult(response, True)
            else:
                return sendError(response, "copying token pin failed: %s" % err_string)

        except PolicyException as pe:
            log.error("Error doing losttoken %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("Error copying token pin")
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def copyTokenUser(self, action, **params):
        """
        method:
            admin/copyTokenUser

        description:
            copies the token user from one token to another

        arguments:
            * from - required - serial of token from
            * to   - required - serial of token to

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        ret = 0
        err_string = ""
        param = request.params

        try:

            serial_from = getParam(param, "from", required)
            serial_to = getParam(param, "to", required)

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'copytokenuser', param)

            log.info("copying User from token %s to token %s" % (serial_from, serial_to))
            ret = copyTokenUser(serial_from, serial_to)

            c.audit['success'] = ret
            c.audit['serial'] = serial_to
            c.audit['action_detail'] = "from %s" % serial_from

            err_string = unicode(ret)
            if -1 == ret:
                err_string = "can not get user from source token"
            if -2 == ret:
                err_string = "can not set user to destination token"
            if 1 != ret:
                c.audit['action_detail'] += ", " + err_string
                c.audit['success'] = 0

            Session.commit()
            # Success
            if 1 == ret:
                return sendResult(response, True)
            else:
                return sendError(response, "copying token user failed: %s" % err_string)

        except PolicyException as pe:
            log.error("Error doing losttoken %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("Error copying token user")
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()


########################################################
    @log_with(log)
    def losttoken(self, action, **params):
        """
        method:
            admin/losttoken

        description:
            creates a new password token and copies the PIN and the
            user of the old token to the new token.
            The old token is disabled.

        arguments:
            * serial - serial of the old token

        returns:
            a json result with the new serial an the password

        exception:
            if an error occurs an exception is serialized and returned

        """
        ret = 0
        res = {}
        param = request.params

        try:

            serial = getParam(param, "serial", required)

            # check admin authorization
            self.Policy.checkPolicyPre('admin', 'losttoken', param)

            res = losttoken(serial)

            c.audit['success'] = ret
            c.audit['serial'] = res.get('serial')
            c.audit['action_detail'] = "from %s" % serial

            Session.commit()
            return sendResult(response, res)

        except PolicyException as pe:
            log.error("Error doing losttoken %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("Error doing losttoken %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(e))

        finally:
            Session.close()


########################################################
    @log_with(log)
    def loadtokens(self, action, **params):
        """
        method:
            admin/loadtokens

        description:
            loads a whole token file to the server

        arguments:
            * file -  the file in a post request
            * type -  the file type.

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = "Loading token file failed!"
        known_types = ['aladdin-xml', 'oathcsv', 'yubikeycsv']
        TOKENS = {}
        res = None

        sendResultMethod = sendResult
        sendErrorMethod = sendError

        try:
            from privacyideaee.lib.ImportOTP import getKnownTypes
            known_types.extend(getKnownTypes())
            log.info("importing privacyideaee.lib. Running Enterprise Edition. Known import types: %s" % known_types)

            from privacyideaee.lib.ImportOTP.PSKC import parsePSKCdata
            log.info("loaded parsePSKCdata")

            from privacyideaee.lib.ImportOTP.DPWplain import parseDPWdata
            log.info("loaded parseDPWdata")

            from privacyideaee.lib.ImportOTP.eTokenDat import parse_dat_data
            log.info("loaded parseDATdata")

            from privacyideaee.lib.ImportOTP.vasco import parseVASCOdata
            log.info("loaded parseVASCOdata")

        except Exception as e:
            log.warning("Unable to load privacyideaee.lib. Running Community Edition: %r" % e)

        try:
            log.debug("getting POST request")
            log.debug(request.POST)
            tokenFile = request.POST['file']
            fileType = request.POST['type']

            pskc_type = None
            pskc_password = None
            pskc_preshared = None
            pskc_checkserial = False

            hashlib = None

            if "pskc" == fileType:
                pskc_type = request.POST['pskc_type']
                pskc_password = request.POST['pskc_password']
                pskc_preshared = request.POST['pskc_preshared']
                if 'pskc_checkserial' in request.POST:
                    pskc_checkserial = True

            fileString = ""
            typeString = ""

            log.debug("loading token file to server using POST request. Filetype: %s. File: %s"
                        % (fileType, tokenFile))

            # In case of form post requests, it is a "instance" of FieldStorage
            # i.e. the Filename is selected in the browser and the data is transferred
            # in an iframe. see: http://jquery.malsup.com/form/#sample4
            #
            if type(tokenFile).__name__ == 'instance':
                log.debug("Field storage file: %s", tokenFile)
                fileString = tokenFile.value
                sendResultMethod = sendXMLResult
                sendErrorMethod = sendXMLError
            else:
                fileString = tokenFile
            log.debug("fileString: %s", fileString)

            if type(fileType).__name__ == 'instance':
                log.debug("Field storage type: %s", fileType)
                typeString = fileType.value
            else:
                typeString = fileType
            log.debug("typeString: <<%s>>", typeString)
            if "pskc" == typeString:
                log.debug("passing password: %s, key: %s, checkserial: %s" % (pskc_password, pskc_preshared, pskc_checkserial))

            if fileString == "" or typeString == "":
                log.error("file: %s", fileString)
                log.error("type: %s", typeString)
                log.error("Error loading/importing token file. file or type empty!")
                return sendErrorMethod(response, "Error loading tokens. File or Type empty!")

            if typeString not in known_types:
                log.error("Unknown file type: >>%s<<. We only know the types: %s" % (typeString, ', '.join(known_types)))
                return sendErrorMethod(response, "Unknown file type: >>%s<<. We only know the types: %s" % (typeString, ', '.join(known_types)))

            # Parse the tokens from file and get dictionary
            if typeString == "aladdin-xml":
                TOKENS = parseSafeNetXML(fileString)
                # we only do hashlib for aladdin at the moment.
                if 'aladdin_hashlib' in request.POST:
                    hashlib = request.POST['aladdin_hashlib']
            elif typeString == "oathcsv":
                TOKENS = parseOATHcsv(fileString)
            elif typeString == "yubikeycsv":
                TOKENS = parseYubicoCSV(fileString)
            elif typeString == "dpw":
                TOKENS = parseDPWdata(fileString)

            elif typeString == "dat":
                startdate = request.POST.get('startdate', None)
                TOKENS = parse_dat_data(fileString, startdate)

            elif typeString == "feitian":
                TOKENS = parsePSKCdata(fileString, do_feitian=True)
            elif typeString == "pskc":
                if "key" == pskc_type:
                    TOKENS = parsePSKCdata(fileString, preshared_key_hex=pskc_preshared, do_checkserial=pskc_checkserial)
                elif "password" == pskc_type:
                    TOKENS = parsePSKCdata(fileString, password=pskc_password, do_checkserial=pskc_checkserial)
                    #log.debug(TOKENS)
                elif "plain" == pskc_type:
                    TOKENS = parsePSKCdata(fileString, do_checkserial=pskc_checkserial)
            elif typeString == "vasco":
                vasco_otplen = request.POST['vasco_otplen']
                (fh, filename) = mkstemp()
                f = open(filename, "w")
                f.write(fileString)
                f.close()
                TOKENS = parseVASCOdata(filename, int(vasco_otplen))
                os.remove(filename)
                if TOKENS is None:
                    raise ImportException("Vasco DLL was not properly loaded. Importing of VASCO token not possible. Please check the log file for more details.")


            log.debug("read %i tokens. starting import now" % len(TOKENS))

            # Now import the Tokens from the dictionary
            ret = ""
            for serial in TOKENS:
                log.debug("importing token %s" % TOKENS[serial])

                # this needs to return the valid realms of the admin.
                # it also checks the license token number
                res = self.Policy.checkPolicyPre('admin', 'import', {})
                # we put the token in the FIRST realm of the admin.
                # so tokenrealm will either be ONE realm or NONE
                log.info("setting tokenrealm %s" % res['realms'])
                tokenrealm = None
                if res['realms']:
                    tokenrealm = res.get('realms')[0]


                log.info("initialize token. serial: %s, realm: %s" % (serial, tokenrealm))

                ## for the eToken dat we assume, that it brings all its
                ## init parameters in correct format
                if typeString == "dat":
                    init_param = TOKENS[serial]

                else:
                    init_param = {'serial':serial,
                                    'type':TOKENS[serial]['type'],
                                    'description': TOKENS[serial].get("description", "imported"),
                                    'otpkey' : TOKENS[serial]['hmac_key'],
                                    'otplen' : TOKENS[serial].get('otplen'),
                                    'timeStep' : TOKENS[serial].get('timeStep'),
                                    'hashlib' : TOKENS[serial].get('hashlib')}



                # add additional parameter for vasco tokens
                if TOKENS[serial]['type'] == "vasco":
                    init_param['vasco_appl'] = TOKENS[serial]['tokeninfo'].get('application')
                    init_param['vasco_type'] = TOKENS[serial]['tokeninfo'].get('type')
                    init_param['vasco_auth'] = TOKENS[serial]['tokeninfo'].get('auth')

                # add ocrasuite for ocra tokens, only if ocrasuite is not empty
                if TOKENS[serial]['type'] == 'ocra':
                    if TOKENS[serial].get('ocrasuite', "") != "":
                        init_param['ocrasuite'] = TOKENS[serial].get('ocrasuite')

                if hashlib and hashlib != "auto":
                    init_param['hashlib'] = hashlib

                if tokenrealm:
                    self.Policy.checkPolicyPre('admin', 'loadtokens',
                                   {'tokenrealm': tokenrealm })

                (ret, tokenObj) = initToken(init_param, User('', '', ''),
                                            tokenrealm=tokenrealm)

            log.info ("%i tokens imported." % len(TOKENS))
            res = { 'value' : True, 'imported' : len(TOKENS) }

            c.audit['info'] = "%s, %s (imported: %i)" % (fileType, tokenFile, len(TOKENS))
            c.audit['serial'] = ', '.join(TOKENS.keys())
            logTokenNum()
            c.audit['success'] = ret

            Session.commit()
            return sendResultMethod(response, res)

        except PolicyException as pe:
            log.error("Failed checking policy: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed! %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendErrorMethod(response, unicode(e))

        finally:
            Session.close()


    @log_with(log)
    def testresolver(self, action, **params):
        """
        method:
            admin/testresolver

        description:
            This method tests a useridresolvers configuration

        arguments:
            * type     - "LDAP": depending on the type there are other parameters:
                       - "SQL"

            * LDAP:
                * BINDDN
                * BINDPW
                * LDAPURI
                * TIMEOUT
                * LDAPBASE
                * LOGINNAMEATTRIBUTE
                * LDAPSEARCHFILTER
                * LDAPFILTER
                * USERINFO
                * LDAPSEARCHFILTER
                * SIZELIMIT
                * NOREFERRALS
                * CACERTIFICATE

            * SQL:
                * Driver
                * Server
                * Port
                * Database
                * User
                * Password
                * Table
                
            * SCIM:
                * Authserver
                * Resourceserver
                * Client
                * Secret
                * Map

        returns:
            a json result with a boolean
              "result": true

        exception:
            if an error occurs an exception is serialized and returned

        """
        res = {}

        try:
            param = getLowerParams(request.params)
            typ = getParam(param, "type", required)

            if typ == "ldap":
                import privacyidea.lib.resolvers.LDAPIdResolver

                param['BINDDN'] = getParam(param, "ldap_binddn", required)
                param['BINDPW'] = getParam(param, "ldap_password", required)
                param['LDAPURI'] = getParam(param, "ldap_uri", required)
                param['TIMEOUT'] = getParam(param, "ldap_timeout", required)
                param['LDAPBASE'] = getParam(param, "ldap_basedn", required)
                param['LOGINNAMEATTRIBUTE'] = getParam(param, "ldap_loginattr", required)
                param['LDAPSEARCHFILTER'] = getParam(param, "ldap_searchfilter", required)
                param['LDAPFILTER'] = getParam(param, "ldap_userfilter", required)
                param['USERINFO'] = getParam(param, "ldap_mapping", required)
                param['SIZELIMIT'] = getParam(param, "ldap_sizelimit", required)
                param['NOREFERRALS'] = getParam(param, "noreferrals", optional)
                param['CACERTIFICATE'] = getParam(param, "ldap_certificate", optional)

                (success, desc) = privacyidea.lib.resolvers.LDAPIdResolver.IdResolver.testconnection(param)
                res['result'] = success
                res['desc'] = desc

            elif typ == "sql":
                import privacyidea.lib.resolvers.SQLIdResolver

                param["Driver"] = getParam(param, "sql_driver", required)
                param["Server"] = getParam(param, "sql_server", required)
                param["Port"] = getParam(param, "sql_port", required)
                param["Database"] = getParam(param, "sql_database", required)
                param["User"] = getParam(param, "sql_user", required)
                param["Password"] = getParam(param, "sql_password", required)
                param["Table"] = getParam(param, "sql_table", required)
                param["Where"] = getParam(param, "sql_where", optional)

                (num, err_str) = privacyidea.lib.resolvers.SQLIdResolver.IdResolver.testconnection(param)
                res['result'] = (num >= 0)
                res['rows'] = num
                res['err_string'] = err_str

            elif typ == "scim":
                import privacyidea.lib.resolvers.SCIMIdResolver
                param["Authserver"] = getParam(param, "authserver", required)
                param["Resourceserver"] = getParam(param, "resourceserver", required)
                param["Client"] = getParam(param, "client", required)
                param["Secret"] = getParam(param, "secret", required)
                param["Map"] = getParam(param, "map", required)

                (num, err_str) = privacyidea.lib.resolvers.SCIMIdResolver.IdResolver.testconnection(param)
                res['result'] = (num >= 0)
                res['rows'] = num
                res['err_string'] = err_str

                 

            Session.commit()
            return sendResult(response, res)

        except Exception as e:
            log.error("failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(e), 1)

        finally:
            Session.close()


    @log_with(log)
    def checkstatus(self, action, **params):
        """
        show the status either

        * of one dedicated challenge
        * of all challenges of a token
        * of all challenges belonging to all tokens of a user

        :param transactionid/state:  the transaction id of the challenge
        :param serial: serial number of the token - will show all challenges
        :param user:

        :return: json result of token and challenges

        """
        res = {}
        param = {}


        description = """
            admin/checkstatus: check the token status -
            for assynchronous verification. Missing parameter:
            You need to provide one of the parameters "transactionid", "user" or "serial"'
            """

        try:

            param.update(request.params)
            self.Policy.checkPolicyPre('admin', "checkstatus")

            transid = param.get('transactionid', None) or param.get('state', None)
            user = getUserFromParam(param, optional)
            serial = getParam(param, 'serial'          , optional)

            if transid is None and user.isEmpty() and serial is None:
                ## raise exception
                log.error("missing parameter: "
                             "transactionid, user or serial number for token")
                raise ParameterError("Usage: %s" % description, id=77)

            ## gather all challenges from serial, transactionid and user
            challenges = set()
            if serial is not None:
                challenges.update(get_challenges(serial=serial))

            if transid is not None :
                challenges.update(get_challenges(transid=transid))

            ## if we have a user
            if user.isEmpty() == False:
                tokens = getTokens4UserOrSerial(user=user)
                for token in tokens:
                    serial = token.getSerial()
                    challenges.update(get_challenges(serial=serial))

            serials = set()
            for challenge in challenges:
                serials.add(challenge.getTokenSerial())

            status = {}
            ## sort all information by token serial number
            for serial in serials:
                stat = {}
                chall_dict = {}

                ## add the challenges info to the challenge dict
                for challenge in challenges:
                    if challenge.getTokenSerial() == serial:
                        chall_dict[challenge.getTransactionId()] = challenge.get_vars(save=True)
                stat['challenges'] = chall_dict

                ## add the token info to the stat dict
                tokens = getTokens4UserOrSerial(serial=serial)
                token = tokens[0]
                stat['tokeninfo'] = token.get_vars(save=True)

                ## add the local stat to the summary status dict
                status[serial] = stat

            res['values'] = status
            c.audit['success'] = res

            Session.commit()
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
            return sendResult(response, unicode(exx), 0)

        finally:
            Session.close()


#eof###########################################################################

