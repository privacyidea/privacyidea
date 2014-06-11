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
Interface for the Challenge Response Token (OCRA)
'''

import traceback
import logging
from urllib import urlencode


from pylons import request, response, config, tmpl_context as c
from privacyidea.model.meta import Session

from privacyidea.lib.base import BaseController
from privacyidea.weblib.util import get_client
from privacyidea.lib.error   import ParameterError

from privacyidea.lib.util    import getParam, getLowerParams
from privacyidea.lib.reply   import sendResult, sendError
from privacyidea.lib.reply   import sendQRImageResult


from privacyidea.lib.realm   import getDefaultRealm
from privacyidea.lib.user    import getUserFromRequest
from privacyidea.lib.user    import getUserInfo
from privacyidea.lib.user    import User

from privacyidea.lib.policy  import PolicyClass
from privacyidea.lib.policy  import PolicyException

from privacyidea.lib.token import getTokens4UserOrSerial
from privacyidea.lib.tokenclass import OcraTokenClass
from privacyidea.lib.token import get_token_type_list
from privacyidea.lib.token import checkSerialPass
from privacyidea.lib.user import  getUserFromParam
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.log import log_with
import webob


log = logging.getLogger(__name__)

optional = True
required = False


class OcraController(BaseController):
    '''
    The OcraController implements challenges/response tokens according to RFC 6287
    '''

    @log_with(log)
    def __before__(self, action, **params):
        '''
        Here we see, what action is to be called and check the authorization
        '''

        try:
            c.audit['success'] = False
            c.audit['client'] = get_client()
            self.Policy = PolicyClass(request, config, c,
                                      get_privacyIDEA_config(),
                                      token_type_list = get_token_type_list())
            if action != "check_t":
                self.before_identity_check(action)

            return response

        except webob.exc.HTTPUnauthorized as acc:
            ## the exception, when an abort() is called if forwarded
            log.error("%r webob.exception %r" % (action, acc))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            raise acc

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
        self.audit.log(c.audit)

        return response


########################################################
    @log_with(log)
    def request(self, action, **params):
        """
        method:
            orcra/request

        description:
            request a challenge for a user or for a serial number (token).

        arguments:
            * serial: (required - string)
                    Serial number of the token, for which a challenge should
                    be generated (either serial or user is required)

            * user:   (required  - string)
                    The user for whose token a challenge should be generated
                    If the user has more than one token, an error is returend.
                    (either serial or user is required)

            * data:   (required - String: URLendoced)
                    These are the display data, that can be used to generate the challenge

        remark:
            the app will report a wrong qrcode, if the policy
             {'authentication' : qrtanurl=https://localhost }
            is not defined !!

        returns:

            A JSON respone::

                        {
                            "version": "privacyIDEA 2.4",
                            "jsonrpc": "2.0",
                            "result": {
                                "status": true,
                                "value": false,
                            },
                            "detail": {
                                    "transactionid" : TRANSAKTIONSID,
                                    "data" : DATAOBJECT,
                            }
                        }

            * transactionid:
                    This is the transaction ID, that is used later for
                    verifying the Return code /TAN.

            * data:
                    This is an object (URL) which can be used to generate a
                    QR-Coide to be displayed to the QRTAN App


        exception:

        """
        res = {}
        description = 'ocra/request: request a challenge for a given user or token (serial). You must either provide a parameter "user" or a parameter "serial".'
        dataobj = ""

        try:
            param = getLowerParams(request.params)

            self.Policy.checkPolicyPre('ocra', "request")

            serial = getParam(param, 'serial', optional)
            user = getUserFromParam(param, optional)

            if user.isEmpty() and serial is None:
                ## raise exception
                log.error("user or serial is required")
                raise ParameterError("Usage: %s" % description, id=77)

            message = getParam(param, 'data'  , optional)
            if message is None:
                message = ''

            ## ocra token
            tokens = getTokens4UserOrSerial(user, serial)

            if len(tokens) > 1 :
                error = ('More than one token found: unable to create challenge '
                        'for (u:%r,s:%r)!' % (user, serial))
                log.error(error)
                raise Exception(error)

            if len(tokens) == 0:
                error = ('No token found: unable to create challenge for'
                          ' (u:%r,s:%r)!' % (user, serial))
                log.error(error)
                raise Exception(error)

            ocra = tokens[0]
            (transId, challenge, res, url) = ocra.challenge(message)

            u = urlencode({'u':str(url.encode("utf-8"))})

            uInfo = {'tr': transId, 'ch' : challenge,
                      'me': str(message.encode("utf-8")), 'u': u[2:]}
            detail = {"transactionid"   : transId,
                      'challenge'       : challenge,
                      'message'         : str(message.encode("utf-8")),
                      'url'             : str(url.encode("utf-8")),
                     }

            ## create the app_url from the data'''
            dataobj = 'lseqr://req?%s' % (str(urlencode(uInfo)))

            ## append the signature to the url '''
            signature = {'si' : ocra.signData(dataobj)}
            uInfo['si'] = signature
            dataobj = '%s&%s' % (dataobj, str(urlencode(signature)))

            detail["data"] = dataobj

            c.audit['success'] = res
            #c.audit['info'] += "%s=%s, " % (k, value)

            Session.commit()
            qr = getParam(param, 'qr', optional)
            if qr is not None:
                param['alt'] = detail
                return sendQRImageResult(response, dataobj, param)
            else:
                return sendResult(response, res, 1, opt=detail)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe))

        except Exception as exx:
            log.error("failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(exx))

        finally:
            Session.close()



    ## https://privacyideaserver/ocra/check_t?transactionid=TRANSACTIONID&pass=TAN
    @log_with(log)
    def check_t(self, action, **params):
        """
        method:
            orcra/check_t

        description:
            verify the response of the ocra token

        arguments:
            * transactionid:  (required - string)
                    Dies ist eine Transaktions-ID, die bei der Challenge ausgegeben wurde.

            * pass:   (required - string)
                    die response, die der OCRA Token auf Grund der Challenge berechnet hat

        returns:

            A JSON response::

                {
                 "version": "privacyIDEA 2.4",
                 "jsonrpc": "2.0",
                 "result": {
                     "status": true,
                     "value": {
                         "failcount" : 3,
                         "result": false
                        }
                    },
                 "id": 0
                }

        exception:

        """
        res = {}
        description = 'ocra/check_t: validate a token request.'

        try:
            param = getLowerParams(request.params)

            #checkPolicyPre('ocra', "check_t" )

            passw = getParam(param, 'pass'  , optional)
            if passw is None:
                ## raise exception'''
                log.error("missing pass ")
                raise ParameterError("Usage: %s Missing parameter 'pass'." % description, id=77)

            transid = getParam(param, 'transactionid', optional)
            if transid is None:
                ## raise exception'''
                log.error("missing transactionid, user or serial number of token")
                raise ParameterError("Usage: %s Missing parameter 'transactionid'." % description, id=77)

            ## if we have a transaction, get serial from this challenge
            value = {}
            ocraChallenge = OcraTokenClass.getTransaction(transid)
            if ocraChallenge is not None:
                serial = ocraChallenge.tokenserial

                tokens = getTokens4UserOrSerial(serial=serial)
                if len(tokens) == 0 or len(tokens) > 1:
                    raise Exception('tokenmismatch for token serial: %s'
                                    % (unicode(serial)))

                theToken = tokens[0]
                tok = theToken.token
                desc = tok.get()
                realms = desc.get('privacyIDEA.RealmNames')
                if realms is None or len(realms) == 0:
                    realm = getDefaultRealm()
                elif len(realms) > 0:
                    realm = realms[0]

                userInfo = getUserInfo(tok.privacyIDEAUserid, tok.privacyIDEAIdResolver, tok.privacyIDEAIdResClass)
                user = User(login=userInfo.get('username'), realm=realm)

                (ok, opt) = checkSerialPass(serial, passw, user=user,
                                     options={'transactionid':transid})

                failcount = theToken.getFailCount()
                value['result'] = ok
                value['failcount'] = int(failcount)

            else:
                ## no challenge found for this transid
                value['result'] = False
                value['failure'] = 'No challenge for transaction %r found'\
                                    % transid

            c.audit['success'] = res
            #c.audit['info'] += "%s=%s, " % (k, value)

            Session.commit()
            return sendResult(response, value, 1)

        except Exception as e :
            log.error("failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendResult(response, unicode(e), 0)

        finally:
            Session.close()


    '''
        https://privacyideaserver/ocra/checkstatus?transactionid=TRANSACTIONID
        https://privacyideaserver/ocra/checkstatus?serial=SERIENNUMMER
        https://privacyideaserver/ocra/checkstatus?user=BENUTZER
    '''
    @log_with(log)
    def checkstatus(self, action, **params):
        """
        method:
            orcra/checkstatus

        description:
            Methode zur assynchronen Ueberpruefungen eines Challenge Response Valiadation requests

        arguments:

            * transactionid:  (required one of  - string - (hex))
                    Dies ist eine Transaktions-ID, die bei der Challenge ausgegeben wurde.

            * serial: (required one of  - string)
                    die Serien Nummer des OCRA Token

            * user: (required one of  - string)
                    die Benutzer eines Tokens

            required is one of (user,serial,transactionid)

        returns:

            A JSON response::

                {
                 "version": "privacyIDEA 2.4",
                 "jsonrpc": "2.0",
                 "result": {
                     "status": true,
                     "value": [
                             {
                             "serial": SERIENNUMMER1,
                             "transactionid": TRANSACTIONID1,
                             "received_tan": true,
                             "valid_tan": true,
                             "failcount": 0
                             },
                             {
                             "serial": SERIENNUMMER1,
                             "transactionid": TRANSACTIONID2,
                             "received_tan": false,
                             "valid_tan": false,
                             "failcount": 0
                             },
                             {
                             "serial": SERIENNUMMER2,
                             "transactionid": TRANSACTIONID3,
                             "received_tan": true,
                             "valid_tan": false,
                             "failcount": 2
                             },
                         ]
                     },
                 "id": 0
                 }

        exception:

        """
        res = {}
        description = 'ocra/checkstatus: check the token status - for assynchronous verification. Missing parameter: You need to provide one of the parameters "transactionid", "user" or "serial"'

        try:
            param = getLowerParams(request.params)

            self.Policy.checkPolicyPre('ocra', "status")

            transid = getParam(param, 'transactionid'   , optional)
            user = getUserFromParam(param, optional)
            #user   = getParam(param, 'user'          ,optional)
            serial = getParam(param, 'serial'          , optional)

            if transid is None and user.isEmpty() and serial is None:
                ## raise exception
                log.error("missing transactionid, user or serial number for token")
                raise ParameterError("Usage: %s" % description, id=77)

            tokens = []
            serials = set()
            status = []

            if serial is not None:
                serials.add(serial)

            ## if we have a transaction, get serial from this challenge
            if transid is not None :
                ocraChallenge = None
                try:
                    ocraChallenge = OcraTokenClass.getTransaction(transid)
                except:
                    pass
                if ocraChallenge is not None:
                    serials.add(ocraChallenge.tokenserial)

            ## if we have a serial number of  token
            if len(serials) > 0:
                for serial in serials:
                    tokens.extend(getTokens4UserOrSerial(serial=serial))

            ## if we have a user
            if user.isEmpty() == False:
                try:
                    tokens.extend(getTokens4UserOrSerial(user=user))
                except:
                    log.warning("no token or user %r found!" % user)

            for token in tokens:
                if token.getType() == 'ocra':
                    challenges = []
                    if transid is None:
                        serial = token.getSerial()
                        challenges = OcraTokenClass.getTransactions4serial(serial)
                    else:
                        challenges.append(OcraTokenClass.getTransaction(transid))

                    for challenge in challenges:
                        stat = token.getStatus(challenge.transid)
                        if stat is not None and len(stat) > 0:
                            status.append(stat)

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



    @log_with(log)
    def getActivationCode(self, action, **params):
        '''
        method:
            orcra/getActivationCode

        description:
            returns an valid example activcation code

        arguments:
            ./.

        returns:
            JSON with     "activationcode": "JZXW4ZI=2A"
        '''

        from privacyidea.lib.crypto import createActivationCode

        res = {}
        #description = 'ocra/getActivationCode'

        try:
            params = getLowerParams(request.params)

            self.Policy.checkPolicyPre('ocra', "activationcode")

            ac = str(params.get('activationcode'))
            activationCode = createActivationCode(acode=ac)
            res = {'activationcode':activationCode}

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
            return sendError(response, unicode(exx), 0)

        finally:
            Session.close()


    @log_with(log)
    def calculateOtp(self, action, **params):
        '''

        '''
        from privacyidea.lib.crypto import kdf2
        from privacyidea.lib.ocra import OcraSuite
        from datetime import datetime

        from urlparse import urlparse
        from urlparse import parse_qs

        res = {}
        #description = 'ocra/calculateOtp: calculate the first otp from the given init2 response '

        try:
            params = getLowerParams(request.params)

            self.Policy.checkPolicyPre('ocra', "calcOTP")

            sharedsecret = params.get('sharedsecret')
            activationcode = params.get('activationcode')
            nonce = params.get('nonce')
            ocrasuite = params.get('ocrasuite')
            challenge = params.get('challenge')
            counter = params.get('counter')
            ocrapin = params.get('ocrapin')

            nonce3 = params.get('no')
            ocrasuite3 = params.get('os')
            #serial3         = params.get('se')

            challenge = params.get('challenge')
            counter = params.get('counter')
            ocrapin = params.get('ocrapin')
            init1 = params.get('init1')
            init2 = params.get('init2')

            ## parse init1 '''
            if init1 is not None:
                ## now parse the appurl for the ocrasuite '''
                uri = urlparse(init1.replace('lseqr://', 'http://'))
                qs = uri.query
                qdict = parse_qs(qs)

                ocrasuite2 = qdict.get('os', None)
                if ocrasuite2 is not None and len(ocrasuite2) > 0:
                    ocrasuite2 = ocrasuite2[0]

                if ocrasuite is None:
                    ocrasuite = ocrasuite2

                sharedsecret2 = qdict.get('sh', None)
                if sharedsecret2 is not None and len(sharedsecret2) > 0:
                    sharedsecret2 = sharedsecret2[0]

                if sharedsecret is None:
                    sharedsecret = sharedsecret2

            ## parse init1
            if init2 is not None:
                ## now parse the appurl for the ocrasuite
                uri = urlparse(init2.replace('lseqr://', 'http://'))
                qs = uri.query
                qdict = parse_qs(qs)

                challenge2 = qdict.get('ch', None)
                if challenge2 is not None and len(challenge2) > 0:
                    challenge2 = challenge2[0]
                if challenge is None:
                    challenge = challenge2

                nonce2 = qdict.get('no', None)
                if nonce2 is not None and len(nonce2) > 0:
                    nonce2 = nonce2[0]
                if nonce is None:
                    nonce = nonce2

            if ocrapin is None:
                ocrapin = ''
            if counter is None:
                counter = 0

            if nonce3 is not None:
                nonce = unicode(nonce3)

            if ocrasuite3 is not None:
                ocrasuite = unicode(ocrasuite3)

            ##  now we have all in place for the key derivation to create the new key
            ##     sharedsecret, activationcode and nonce
            key_len = 20
            if ocrasuite.find('-SHA256'):
                key_len = 32
            elif ocrasuite.find('-SHA512'):
                key_len = 64

            if sharedsecret is not None:
                sharedsecret = unicode(sharedsecret)
            if nonce is not None:
                nonce = unicode(nonce)
            if activationcode is not None:
                activationcode = unicode(activationcode)

            newkey = kdf2(sharedsecret, nonce, activationcode, len=key_len)
            ## hnewkey = binascii.hexlify(newkey)
            ocra = OcraSuite(ocrasuite)

            param = {}
            param['C'] = int(counter)
            param['Q'] = unicode(challenge)
            param['P'] = unicode(ocrapin)
            param['S'] = ''
            if ocra.T is not None:
                ## Default value for G is 1M, i.e., time-step size is one minute and the
                ##  T represents the number of minutes since epoch time [UT].
                now = datetime.now()
                stime = now.strftime("%s")
                itime = int(stime)
                param['T'] = itime

            data = ocra.combineData(**param)
            otp = ocra.compute(data, newkey)

            res = {'otp':otp}

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, pe)

        except Exception as e:
            log.error("failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(e), 0)

        finally:
            Session.close()


#eof###########################################################################

