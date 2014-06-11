# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  LSE
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
  Description:  This file is part of the privacyidea service
                HOTP token
  Dependencies: -

'''
import binascii
import logging
import time
import datetime

import traceback

from privacyidea.lib.config  import getFromConfig

from privacyidea.lib.crypto   import decryptPin, encryptPin
from privacyidea.lib.crypto   import kdf2
from privacyidea.lib.crypto   import createNonce

from privacyidea.lib.policy  import PolicyClass

### TODO: move this as ocra specific methods
from privacyidea.lib.token import getRolloutToken4User
from privacyidea.lib.util import normalize_activation_code

from privacyidea.lib.ocra    import OcraSuite

from privacyidea.lib.validate import create_challenge
from privacyidea.lib.validate import get_challenges
from privacyidea.lib.reply   import create_img

from pylons.i18n.translation import _
from pylons import request, config, tmpl_context as c
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with

# needed for ocra token
import urllib


optional = True
required = False

log = logging.getLogger(__name__)
#### Ocra2TokenClass #####################################


class Ocra2TokenClass(TokenClass):
    '''
    Ocra2TokenClass  implement an ocra compliant token

    used from Config
        OcraMaxChallenges         - number of open challenges per token
                                            if None: 3
        Ocra2ChallengeValidityTime  timeout definition in seconds
        OcraDefaultSuite          - if none :'OCRA-1:HOTP-SHA256-8:C-QN08'
        QrOcraDefaultSuite        - if none :'OCRA-1:HOTP-SHA256-8:C-QA64'


    algorithm Ocra Token Rollout: tow phases of rollout

    1. https://privacyideaserver/admin/init?
        type=ocra&
        genkey=1&
        sharedsecret=1&
        user=BENUTZERNAME&
        session=SESSIONKEY

        =>> "serial" : SERIENNUMMER, "sharedsecret" : DATAOBJECT, "app_import" : IMPORTURL
        - genSharedSecret - vom HSM oder urandom ?
        - app_import : + privacyidea://
                       + ocrasuite ->> default aus dem config: (DefaultOcraSuite)
                       + sharedsecret (Länge wie ???)
                       + seriennummer
        - seriennummer: uuid
        - token wird angelegt ist aber nicht aktiv!!! (counter == 0)


    2. https://privacyideaserver/admin/init?
        type=ocra&
        genkey=1&
        activationcode=AKTIVIERUNGSCODE&
        user=BENUTZERNAME&
        message=MESSAGE&
        session=SESSIONKEY

        =>> "serial" : SERIENNUMMER, "nonce" : DATAOBJECT, "transactionid" : "TRANSAKTIONSID, "app_import" : IMPORTURL

        - nonce - von HSM oder random ?
        - pkcs5 - kdf2
        - es darf zur einer Zeit nur eine QR Token inaktiv (== im Ausrollzustand) sein !!!!!
          der Token wird über den User gefunden
        - seed = pdkdf2(nonce + activcode + shared secret)
        - challenge generiern - von urandom oder HSM

    3. check_t
        - counter ist > nach der ersten Transaktion
        - if counter >= 1: delete sharedsecret löschen


    '''

    @classmethod
    @log_with(log)
    def getClassType(cls):
        '''
        getClassType - return the token type shortname

        :return: 'ocra2'
        :rtype: string
        '''
        return "ocra2"

    @classmethod
    def getClassPrefix(cls):
        return "LSO2"

    @classmethod
    def classInit(cls, param, user=None):

        helper_param = {}

        tok_type = "ocra2"

        ## take the keysize from the ocrasuite
        ocrasuite = param.get("ocrasuite", None)
        activationcode = param.get("activationcode", None)
        sharedsecret = param.get("sharedsecret", None)
        serial = param.get("serial", None)
        genkey = param.get("genkey", None)

        if activationcode is not None:
            ## dont create a new key
            genkey = None
            serial = getRolloutToken4User(user=user, serial=serial, tok_type=tok_type)
            if serial is None:
                raise Exception('no token found for user: %r or serial: %r' % (user, serial))
            helper_param['serial'] = serial
            helper_param['activationcode'] = normalize_activation_code(activationcode)

        if ocrasuite is None:
            if sharedsecret is not None or  activationcode is not None:
                ocrasuite = getFromConfig("QrOcraDefaultSuite", 'OCRA-1:HOTP-SHA256-6:C-QA64')
            else:
                ocrasuite = getFromConfig("OcraDefaultSuite", 'OCRA-1:HOTP-SHA256-8:C-QN08')
            helper_param['ocrasuite'] = ocrasuite

        if genkey is not None:
            if ocrasuite.find('-SHA256'):
                key_size = 32
            elif ocrasuite.find('-SHA512'):
                key_size = 64
            else:
                key_size = 20
            helper_param['key_size'] = key_size

        return helper_param





    @classmethod
    def getClassInfo(cls, key=None, ret='all'):
        '''
        getClassInfo - returns all or a subtree of the token definition

        :param key: subsection identifier
        :type key: string

        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype : s.o.

        '''

        res = {
               'type' : 'ocra2',
               'title' : _('OCRA2 Token'),
               'description' :
                    _('ocra challenge-response token - hmac event based'),
               'init'         : { 'title'  : {'html'      : 'ocra2token.mako',
                                             'scope'     : 'enroll.title', },
                                  'page' : {'html'      : 'ocra2token.mako',
                                            'scope'      : 'enroll', },
                                   },

               'config'         : {'title'  : {'html'      : 'ocra2token.mako',
                                             'scope'     : 'config.title', },
                                   'page' : {'html'      : 'ocra2token.mako',
                                            'scope'      : 'config', },
                                   },

               'selfservice'   :  { 'enroll' :
                                   {'title'  :
                                    { 'html'      : 'ocra2token.mako',
                                      'scope'     : 'selfservice.title.enroll',
                                      },
                                    'page' :
                                    {'html'       : 'ocra2token.mako',
                                     'scope'      : 'selfservice.enroll',
                                     },
                                    },
                                   'activate_OCRA2' :
                                   {'title'  :
                                    { 'html'      : 'ocra2token.mako',
                                      'scope'     : 'selfservice.title.activate',
                                      },
                                    'page' :
                                    {'html'       : 'ocra2token.mako',
                                     'scope'      : 'selfservice.activate',
                                     },
                                    },

                                  },

            'policy' : { 'selfservice' : {'activate_OCRA2' : {'type' : 'bool'} }}

        }

        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret


    @log_with(log)
    def __init__(self, aToken):
        '''
        getInfo - return the status of the token rollout

        :return: info of the ocra token state
        :rtype: dict
        '''
        TokenClass.__init__(self, aToken)
        self.setType(u"ocra2")
        self.transId = 0
        self.Policy = PolicyClass(request, config, c,
                                  get_privacyIDEA_config())

        self.mode = ['challenge']
        return

    @log_with(log)
    def getInfo(self):
        '''
        getInfo - return the status of the token rollout

        :return: info of the ocra token state
        :rtype: dict
        '''
        return self.info

    @log_with(log)
    def update(self, params, reset_failcount=True):
        '''
        update: add further definition for token from param in case of init
        '''
        if params.has_key('ocrasuite'):
            self.ocraSuite = params.get('ocrasuite')
        else:
            activationcode = params.get('activationcode', None)
            sharedSecret = params.get('sharedsecret', None)


            if activationcode is None and sharedSecret is None:
                self.ocraSuite = self.getOcraSuiteSuite()
            else:
                self.ocraSuite = self.getQROcraSuiteSuite()

        if params.get('activationcode', None):
            ## due to changes in the tokenclass parameter handling
            ## we have to add for compatibility a genkey parameter
            if params.has_key('otpkey') == False and params.has_key('genkey') == False:
                log.warning('missing parameter genkey\
                             to complete the rollout 2!')
                params['genkey'] = 1


        TokenClass.update(self, params, reset_failcount=reset_failcount)

        self.addToTokenInfo('ocrasuite', self.ocraSuite)

        ocraSuite = OcraSuite(self.ocraSuite)
        otplen = ocraSuite.truncation
        self.setOtpLen(otplen)

        ocraPin = params.get('ocrapin', None)
        if ocraPin is not None:
            self.token.setUserPin(ocraPin)

        if params.has_key('otpkey'):
            self.setOtpKey(params.get('otpkey'))

        self._rollout_1(params)
        self._rollout_2(params)

        return


    @log_with(log)
    def _rollout_1(self, params):
        '''
        do the rollout 1 step

        1. https://privacyideaserver/admin/init?
            type=ocra&
            genkey=1&
            sharedsecret=1&
            user=BENUTZERNAME&
            session=SESSIONKEY

            =>> "serial" : SERIENNUMMER, "sharedsecret" : DATAOBJECT, "app_import" : IMPORTURL
            - genSharedSecret - vom HSM oder urandom ?
            - app_import : + privacyidea://
                           + ocrasuite ->> default aus dem config: (DefaultOcraSuite)
                           + sharedsecret (Länge wie ???)
                           + seriennummer
            - seriennummer: uuid ??
            - token wird angelegt ist aber nicht aktiv!!! (counter == 0)

        '''
        sharedSecret = params.get('sharedsecret', None)
        if sharedSecret == '1':
            ##  preserve the rollout state
            self.addToTokenInfo('rollout', '1')

            ##  preseerver the current key as sharedSecret
            secObj = self.token.getHOtpKey()
            key = secObj.getKey()
            encSharedSecret = encryptPin(key)
            self.addToTokenInfo('sharedSecret', encSharedSecret)

            info = {}
            uInfo = {}

            info['sharedsecret'] = key
            uInfo['sh'] = key

            info['ocrasuite'] = self.getOcraSuiteSuite()
            uInfo['os'] = self.getOcraSuiteSuite()

            info['serial'] = self.getSerial()
            uInfo['se'] = self.getSerial()

            info['app_import'] = 'lseqr://init?%s' % (urllib.urlencode(uInfo))
            del info['ocrasuite']
            self.info = info

            self.token.privacyIDEAIsactive = False

        return

    @log_with(log)
    def _rollout_2(self, params):
        '''
        2.

        https://privacyideaserver/admin/init?
            type=ocra&
            genkey=1&
            activationcode=AKTIVIERUNGSCODE&
            user=BENUTZERNAME&
            message=MESSAGE&
            session=SESSIONKEY

        =>> "serial" : SERIENNUMMER, "nonce" : DATAOBJECT, "transactionid" : "TRANSAKTIONSID, "app_import" : IMPORTURL

        - nonce - von HSM oder random ?
        - pkcs5 - kdf2
        - es darf zur einer Zeit nur eine QR Token inaktiv (== im Ausrollzustand) sein !!!!!
          der Token wird über den User gefunden
        - seed = pdkdf2(nonce + activcode + shared secret)
        - challenge generiern - von urandom oder HSM

        '''
        activationcode = params.get('activationcode', None)
        if activationcode is not None:

            ##  genkey might have created a new key, so we have to rely on
            encSharedSecret = self.getFromTokenInfo('sharedSecret', None)
            if encSharedSecret is None:
                raise Exception ('missing shared secret of initialition for token %r' % (self.getSerial()))

            sharedSecret = decryptPin(encSharedSecret)

            ##  we generate a nonce, which in the end is a challenge
            nonce = createNonce()
            self.addToTokenInfo('nonce', nonce)

            ##  create a new key from the ocrasuite
            key_len = 20
            if self.ocraSuite.find('-SHA256'):
                key_len = 32
            elif self.ocraSuite.find('-SHA512'):
                key_len = 64


            newkey = kdf2(sharedSecret, nonce, activationcode, key_len)
            self.setOtpKey(binascii.hexlify(newkey))

            ##  generate challenge, which is part of the app_import
            message = params.get('message', None)

            #(transid, challenge, _ret, url) = self.challenge(message)

            #self.createChallenge()
            (res, opt) = create_challenge(self, options=params)

            challenge = opt.get('challenge')
            url = opt.get('url')
            transid = opt.get('transactionid')

            ##  generate response
            info = {}
            uInfo = {}
            info['serial'] = self.getSerial()
            uInfo['se'] = self.getSerial()
            info['nonce'] = nonce
            uInfo['no'] = nonce
            info['transactionid'] = transid
            uInfo['tr'] = transid
            info['challenge'] = challenge
            uInfo['ch'] = challenge
            if message is not None:
                uInfo['me'] = str(message.encode("utf-8"))

            ustr = urllib.urlencode({'u':str(url.encode("utf-8"))})
            uInfo['u'] = ustr[2:]
            info['url'] = str(url.encode("utf-8"))

            app_import = 'lseqr://nonce?%s' % (urllib.urlencode(uInfo))

            ##  add a signature of the url
            signature = {'si': self.signData(app_import) }
            info['signature'] = signature.get('si')

            info['app_import'] = "%s&%s" % (app_import, urllib.urlencode(signature))
            self.info = info

            ##  setup new state
            self.addToTokenInfo('rollout', '2')
            self.enable(True)

        return

    @log_with(log)
    def getOcraSuiteSuite(self):
        '''
        getQROcraSuiteSuite - return the QR Ocra Suite - if none, it will return the default

        :return: Ocrasuite of token
        :rtype: string
        '''

        defaultOcraSuite = getFromConfig("OcraDefaultSuite", 'OCRA-1:HOTP-SHA256-8:C-QN08')
        self.ocraSuite = self.getFromTokenInfo('ocrasuite', defaultOcraSuite)

        return self.ocraSuite

    @log_with(log)
    def getQROcraSuiteSuite(self):
        '''
        getQROcraSuiteSuite - return the QR Ocra Suite - if none, it will return the default

        :return: QROcrasuite of token
        :rtype: string
        '''
        defaultOcraSuite = getFromConfig("QrOcraDefaultSuite", 'OCRA-1:HOTP-SHA256-8:C-QA64')
        self.ocraSuite = self.getFromTokenInfo('ocrasuite', defaultOcraSuite)

        return self.ocraSuite


    @log_with(log)
    def signData(self, data):
        '''
        sign the received data with the secret key

        :param data: arbitrary string object
        :type param: string

        :return: hexlified signature of the data
        '''
        secretHOtp = self.token.getHOtpKey()
        ocraSuite = OcraSuite(self.getOcraSuiteSuite(), secretHOtp)
        signature = ocraSuite.signData(data)
        return signature

    @log_with(log)
    def verify_challenge_is_valid(self, challenge, session):
        '''
        verify, if a challenge is valid according to the ocrasuite definition
        of the token
        '''

        ret = True

        counter = self.getOtpCount()

        secretHOtp = self.token.getHOtpKey()
        ocraSuite = OcraSuite(self.getOcraSuiteSuite(), secretHOtp)

        ## set the pin onyl in the compliant hashed mode
        pin = ''
        if ocraSuite.P is not None:
            pinObj = self.token.getUserPin()
            pin = pinObj.getKey()

        try:
            param = {}
            param['C'] = counter
            param['Q'] = challenge
            param['P'] = pin
            param['S'] = session
            if ocraSuite.T is not None:
                now = datetime.datetime.now()
                stime = now.strftime("%s")
                itime = int(stime)
                param['T'] = itime

            ''' verify that the data is compliant with the OcraSuitesuite
                and the client is able to calc the otp
            '''
            c_data = ocraSuite.combineData(**param)
            ocraSuite.compute(c_data)

        except Exception as ex:
            log.error("challenge verification failed: "
                                "%s,%r: " % (challenge, ex))
            log.error(traceback.format_exc())
            ret = False

        return ret

    @log_with(log)
    def createChallenge(self, state, options=None):
        '''
        standard API to create an ocra challenge
        '''
        res = True

        ## which kind of challenge gen should be used
        typ = 'raw'

        input = None
        challenge = None
        session = None
        message = ""

        if options is not None:
            input = options.get('challenge', None)
            if input is None:
                input = options.get('message', None)
            if input is None:
                input = options.get('data', None)

            typ = options.get('challenge_type', 'raw')
            ## ocra token could contain a session attribute
            session = options.get('ocra_session', None)

        if input is None or len(input) == 0:
            typ = 'random'

        secretHOtp = self.token.getHOtpKey()
        ocraSuite = OcraSuite(self.getOcraSuiteSuite(), secretHOtp)

        if typ == 'raw':
            challenge = ocraSuite.data2rawChallenge(input)
        elif typ == 'random':
            challenge = ocraSuite.data2randomChallenge(input)
        elif typ == 'hash':
            challenge = ocraSuite.data2hashChallenge(input)

        log.debug('challenge: %r ' % (challenge))

        store_data = {
                'challenge' : "%s" % (challenge),
                'serial' : self.token.getSerial(),
                'input' : '',
                'url' : '',
                }

        if input is not None:
            store_data['input'] = input

        if session is not None:
            store_data["session"] = session

        res = self.verify_challenge_is_valid(challenge, session)

        ## add Info: so depending on the Info, the rendering could be done
        ##          as a callback into the token via
        ##          token.getQRImageData(opt=details)
        realms = self.token.getRealms()
        if len(realms) > 0:
            store_data["url"] = self.Policy.get_qrtan_url(realms[0].name)

        ## we will return a dict of all
        attributes = self.prepare_message(store_data, state)
        attributes['challenge'] = challenge

        if attributes != None and "data" in attributes:
            message = attributes.get("data")
            del attributes['data']

        return (res, message, store_data, attributes)

    def prepare_message(self, data, transId):
        '''
        prepare the challenge response message

        :param data:
        :param transId: the transaction/state refenence id
        remark:
        we need the state/transId in the inner scope to support the signing
        of the whole request including the state/transId
        '''

        url = data.get("url")
        u = (str(urllib.urlencode({'u': '%s' % url})))
        u = urllib.urlencode({'u': "%s" % (url.encode("utf-8"))})

        challenge = data.get('challenge')
        input = data.get('input')

        uInfo = {'tr': transId,
                 'ch': challenge,
                 'me': str(input.encode("utf-8")),
                 'u': str(u[2:])}
        detail = {'request'         : str(input.encode("utf-8")),
                  'url'             : str(url.encode("utf-8")),
                 }

        ## create the app_url from the data
        dataobj = 'lseqr://req?%s' % (str(urllib.urlencode(uInfo)))

        ## append the signature to the url
        signature = {'si': self.signData(dataobj)}
        uInfo['si'] = signature
        dataobj = '%s&%s' % (dataobj, str(urllib.urlencode(signature)))

        detail["data"] = dataobj

        return detail

    @log_with(log)
    def challenge(self, data, session='', typ='raw', challenge=None):
        '''
        the challenge method is for creating an transaction / challenge object

        remark: the transaction has a maximum lifetime and a reference to
                the OcraSuite token (serial)

        :param data:     data, which is the base for the challenge or None
        :type data:     string or None
        :param session:  session support for ocratokens
        :type session:  string
        :type typ:      define, which kind of challenge base should be used
                         could be raw - take the data input as is
                               (extract chars accordind challenge definition Q)
                         or random    - will generate a random input
                         or hased     - will take the hash of the input data

        :return:    challenge response containing the transcation id and the
                    challenge for the ocrasuite
        :rtype :    tuple of (transId(string), challenge(string))


        '''
        secretHOtp = self.token.getHOtpKey()
        ocraSuite = OcraSuite(self.getOcraSuiteSuite(), secretHOtp)

        if data is None or len(data) == 0:
            typ = 'random'

        if challenge is None:
            if typ == 'raw':
                challenge = ocraSuite.data2rawChallenge(data)
            elif typ == 'random':
                challenge = ocraSuite.data2randomChallenge(data)
            elif typ == 'hash':
                challenge = ocraSuite.data2hashChallenge(data)

        log.debug('challenge: %r ' % (challenge))

        counter = self.getOtpCount()

        ## set the pin onyl in the compliant hashed mode
        pin = ''
        if ocraSuite.P is not None:
            pinObj = self.token.getUserPin()
            pin = pinObj.getKey()

        try:
            param = {}
            param['C'] = counter
            param['Q'] = challenge
            param['P'] = pin
            param['S'] = session
            if ocraSuite.T is not None:
                now = datetime.datetime.now()
                stime = now.strftime("%s")
                itime = int(stime)
                param['T'] = itime

            ''' verify that the data is compliant with the OcraSuitesuite
                and the client is able to calc the otp
            '''
            c_data = ocraSuite.combineData(**param)
            ocraSuite.compute(c_data)

        except Exception as ex:
            log.error(traceback.format_exc())
            raise Exception('[Ocra2TokenClass] Failed to create ocrasuite '
                                                        'challenge: %r' % (ex))

        ##  create a non exisiting challenge
        try:

            (res, opt) = create_challenge(self, options={'messgae': data})

            transid = opt.get('transactionid')
            challenge = opt.get('challenge')

        except Exception as ex:
            ##  this might happen if we have a db problem or
            ##   the uniqnes constrain does not fit
            log.error(traceback.format_exc())
            raise Exception('[Ocra2TokenClass] Failed to create '
                                                'challenge object: %s' % (ex))

        realm = None
        realms = self.token.getRealms()
        if len(realms) > 0:
            realm = realms[0]

        url = ''
        if realm is not None:
            url = self.Policy.get_qrtan_url(realm.name)

        return (transid, challenge, True, url)

### challenge interfaces starts here
    def is_challenge_request(self, passw, user, options=None):
        '''
        check, if the request would start a challenge

        - default: if the passw contains only the pin, this request would
        trigger a challenge

        - in this place as well the policy for a token is checked

        :param passw: password, which might be pin or pin+otp
        :param options: dictionary of additional request parameters

        :retrun: returns true or false
        '''

        request_is_valid = False

        if passw is None:
            ## for compatibility:
            # in case of ocra2, we accept to trigger a challenge even with an
            # missing password, if there is a challenge or data in the request
            if 'data' in options or 'challenge' in options:
                request_is_valid = True
        else:
            tok = super(Ocra2TokenClass, self)
            request_is_valid = tok.is_challenge_request(passw, user,
                                                        options=options)

        return request_is_valid

    def is_challenge_response(self, passw, user, options=None,
                                                            challenges=None):
        '''
        for the ocra token,

        :param passw: password, which might be pin or pin+otp
        :param user: the requesting user
        :param options: dictionary of additional request parameters

        :return: returns true or false
        '''

        challenge_response = False
        if (passw is not None and  len(passw) > 0 and
           challenges is not None and len(challenges) > 0):
            challenge_response = True

        if 'challenge' in options or 'data' in options:
            challenge_response = False

        ## we leave out the checkOtp, which is done later
        ## either in checkResponse4Challenge
        ## or in the check pin+otp

        return challenge_response

    def is_challenge_valid(self, challenge=None):
        '''
        this method proves the validity of a challenge
        - the default implementation tests, if the challegenge start
        is in the default vality time window.

        :param challenge: challenge object
        :return: true or false
        '''

        return True

    def checkResponse4Challenge(self, user, passw, options=None, challenges=None):
        '''
        verify the response of a previous challenge

        :param user:      the requesting user
        :param passw:     the to be checked pass: (otp) & trans_id | (pin+otp)
        :param options:   options an additional argument, which could be token
                          specific
        :param challenges: the list of challenges, where each challenge is
                            described as dict
        :return: tuple of (boolean and the list matching challenge ids)
        '''
        res = False
        otpcount = -1
        matching_challenges = []
        mids = {}
        loptions = {}

        if options is not None:
            loptions.update(options)
        if 'session' in loptions:
            del loptions['session']

        (res, pin, otpval) = self.splitPinPass(passw)
        res = self.checkPin(pin)

        if res == True:
            window = self.getCounterWindow()
            counter = self.getOtpCount()
            transids = set()

            ## preserve the provided transaction
            if 'transactionid' in options:
                transids.add(options.get('transactionid'))

            ## add all identified challenges by transid
            for challenge in challenges:
                ### checkOtp recieve the challenge in the options
                ### as transcationid
                try:
                    transid = challenge.get('transid', None)
                except Exception:
                    pass
                if transid is not None:
                    mids[transid] = challenge

            for transid in mids.keys():
                ## intentional overwrite the transaction which has been provided
                loptions['transactionid'] = transid
                otpcount = self.checkOtp(otpval, counter, window, options=loptions)
                if otpcount >= 0:
                    matching_challenges.append(mids.get(transid))
                    break

        return (otpcount, matching_challenges)

    @log_with(log)
    def checkOtp(self, passw , counter, window, options=None):
        '''
        checkOtp - standard callback of privacyidea to verify the token

        :param passw:      the passw / otp, which has to be checked
        :type passw:       string
        :param counter:    the start counter
        :type counter:     int
        :param  window:    the window, in which the token is valid
        :type  window:     int
        :param options:    options contains the transaction id,
                            eg. if check_t checks one transaction
                            this will support assynchreonous otp checks
                            (when check_t is used)
        :type options:     dict

        :return:           verification counter or -1
        :rtype:            int (-1)

        '''
        ret = -1

        challenges = []
        serial = self.getSerial()

        if options is None:
            options = {}

        maxRequests = int(getFromConfig("Ocra2MaxChallengeRequests", '3'))

        if 'transactionid' in options:
            transid = options.get('transactionid', None)
            challs = get_challenges(serial=serial, transid=transid)
            for chall in challs:
                (rec_tan, rec_valid) = chall.getTanStatus()
                if rec_tan == False:
                    challenges.append(chall)
                elif rec_valid == False:
                    ## add all touched but failed challenges
                    if chall.getTanCount() <= maxRequests:
                        challenges.append(chall)

        if 'challenge' in options:
            ## direct challenge - there might be addtionalget info like
            ## session data in the options
            challenges.append(options)

        if len(challenges) == 0:
            challs = get_challenges(serial=serial)
            for chall in challs:
                (rec_tan, rec_valid) = chall.getTanStatus()
                if rec_tan == False:
                    ## add all untouched challenges
                    challenges.append(chall)
                elif rec_valid == False:
                    ## add all touched but failed challenges
                    if chall.getTanCount() <= maxRequests:
                        challenges.append(chall)

        if len(challenges) == 0:
            err = 'No open transaction found for token %s' % serial
            log.error(err)  ##TODO should log and fail!!
            raise Exception(err)

        ## prepare the challenge check - do the ocra setup
        secretHOtp = self.token.getHOtpKey()
        ocraSuite = OcraSuite(self.getOcraSuiteSuite(), secretHOtp)

        ## set the ocra token pin
        ocraPin = ''
        if ocraSuite.P is not None:
            ocraPinObj = self.token.getUserPin()
            ocraPin = ocraPinObj.getKey()

            if ocraPin is None or len(ocraPin) == 0:
                ocraPin = ''

        timeShift = 0
        if  ocraSuite.T is not None:
            defTimeWindow = int(getFromConfig("ocra.timeWindow", 180))
            window = int(self.getFromTokenInfo('timeWindow', defTimeWindow)) / ocraSuite.T
            defTimeShift = int(getFromConfig("ocra.timeShift", 0))
            timeShift = int(self.getFromTokenInfo("timeShift", defTimeShift))

        default_retry_window = int(getFromConfig("ocra2.max_check_challenge_retry", 0))
        retry_window = int(self.getFromTokenInfo("max_check_challenge_retry", default_retry_window))

        ## now check the otp for each challenge

        for ch in challenges:
            challenge = {}

            ##  preserve transaction context, so we could use this in the status callback
            self.transId = ch.get('transid', None)
            challenge['transid'] = self.transId
            challenge['session'] = ch.get('session', None)

            ## we saved the 'real' challenge in the data
            data = ch.get('data', None)
            if data is not None:
                challenge['challenge'] = data.get('challenge')
            elif 'challenge' in ch:
                ## handle explicit challenge requests
                challenge['challenge'] = ch.get('challenge')

            if challenge.get('challenge') is None:
                raise Exception('could not checkOtp due to missing challenge'
                                ' in request: %r' % ch)

            ret = ocraSuite.checkOtp(passw, counter, window, challenge, pin=ocraPin , options=options, timeshift=timeShift)
            log.debug('ret %r' % (ret))

            ## due to the assynchronous challenge verification of the checkOtp
            ## it might happen, that the found counter is lower than the given
            ## one. Thus we fix this here to deny assynchronous verification

            # we do not support retry checks anymore:
            # which means, that ret might be smaller than the actual counter
            if ocraSuite.T is None:
                if ret + retry_window < counter:
                    ret = -1

            if ret != -1:
                break

        if -1 == ret:
            ##  autosync: test if two consecutive challenges + it's counter match
            ret = self.autosync(ocraSuite, passw, challenge)


        return ret

    @log_with(log)
    def autosync(self, ocraSuite, passw, challenge):
        '''
        try to resync a token automaticaly, if a former and the current request failed

        :param  ocraSuite: the ocraSuite of the current Token
        :type  ocraSuite: ocra object
        :param  passw:
        '''
        res = -1

        autosync = False

        try:
            async = getFromConfig("AutoResync")
            if async is None:
                autosync = False
            elif "true" == async.lower():
                autosync = True
            elif "false" == async.lower():
                autosync = False
        except Exception as ex:
            log.error('autosync check undefined %r' % (ex))
            return res

        ' if autosync is not enabled: do nothing '
        if False == autosync:
            return res

        ##
        ## AUTOSYNC starts here
        ##

        counter = self.token.getOtpCounter()
        syncWindow = self.token.getSyncWindow()
        if  ocraSuite.T is not None:
            syncWindow = syncWindow / 10


        ## set the ocra token pin
        ocraPin = ''
        if ocraSuite.P is not None:
            ocraPinObj = self.token.getUserPin()
            ocraPin = ocraPinObj.getKey()

            if ocraPin is None or len(ocraPin) == 0:
                ocraPin = ''

        timeShift = 0
        if  ocraSuite.T is not None:
            timeShift = int(self.getFromTokenInfo("timeShift", 0))

        #timeStepping    = int(ocraSuite.T)

        tinfo = self.getTokenInfo()

        ## autosync does only work, if we have a token info, where the last challenge and the last sync-counter is stored
        ## if no tokeninfo, we start with a autosync request, thus start the lookup in the sync window

        if tinfo.has_key('lChallenge') == False:
            ## run checkOtp, with sync window for the current challenge
            log.debug('initial sync')
            count_0 = -1
            try:
                otp0 = passw
                count_0 = ocraSuite.checkOtp(otp0, counter, syncWindow, challenge, pin=ocraPin, timeshift=timeShift)
            except Exception as ex:
                log.error(' error during autosync0 %r' % (ex))

            if count_0 != -1:
                tinfo['lChallenge'] = {'otpc' : count_0}
                self.setTokenInfo(tinfo)
                log.info('initial sync - success: %r' % (count_0))

            res = -1
            log.debug('initial sync done!')

        else:
            ## run checkOtp, with sync window for the current challenge
            log.debug('sync')
            count_1 = -1
            try:
                otp1 = passw
                count_1 = ocraSuite.checkOtp(otp1, counter, syncWindow, challenge, pin=ocraPin, timeshift=timeShift)
            except Exception as ex:
                log.error(' error during autosync1 %r' % (ex))

            if count_1 == -1:
                del tinfo['lChallenge']
                self.setTokenInfo(tinfo)
                log.info('sync failed! Not a valid pass in scope (%r)' % (otp1))
                res = -1
            else:
                ## run checkOtp, with sync window for the old challenge
                lChallange = tinfo.get('lChallenge')
                count_0 = lChallange.get('otpc')

                if ocraSuite.C is not None:
                    ##  sync the counter based ocra token
                    if count_1 - count_0 < 2:
                        self.setOtpCount(count_1)
                        res = count_1

                if ocraSuite.T is not None:
                    ##  sync the timebased ocra token
                    if count_1 - count_0 < ocraSuite.T * 2 :
                        ## calc the new timeshift !
                        log.debug("the counter %r matches: %r" %
                                  (count_1, datetime.datetime.fromtimestamp(count_1)))

                        currenttime = int(time.time())
                        new_shift = (count_1 - currenttime)

                        tinfo['timeShift'] = new_shift
                        self.setOtpCount(count_1)
                        res = count_1

                ##  if we came here, the old challenge is not required anymore
                del tinfo['lChallenge']
                self.setTokenInfo(tinfo)

        return res




    @log_with(log)
    def statusValidationFail(self):
        '''
        statusValidationFail - callback to enable a status change,

        will be called if the token verification has failed

        :return - nothing

        '''
        challenge = None

        if self.transId == 0 :
            return
        try:

            challenges = get_challenges(self.getSerial(), transid=self.transId)
            if len(challenges) == 1:
                challenge = challenges[0]
                challenge.setTanStatus(received=True, valid=False)


            ##  still in rollout state??
            rolloutState = self.getFromTokenInfo('rollout', '0')

            if rolloutState == '1':
                log.info('rollout state 1 for token %r not completed' % (self.getSerial()))

            elif rolloutState == '2':
                if challenge.received_count >= int(getFromConfig("OcraMaxChallengeRequests", '3')):
                    ##  after 3 fails in rollout state 2 - reset to rescan
                    self.addToTokenInfo('rollout', '1')
                    log.info('rollout for token %r reset to phase 1:' % (self.getSerial()))

                log.info('rollout for token %r not completed' % (self.getSerial()))

        except Exception as ex:
            log.error('Error during validation finalisation for token %r :%r' % (self.getSerial(), ex))
            log.error(traceback.format_exc())
            raise Exception(ex)

        finally:
            if challenge is not None:
                challenge.save()

        return

    @log_with(log)
    def statusValidationSuccess(self):
        '''
        statusValidationSuccess - callback to enable a status change,

        remark: will be called if the token has been succesfull verified

        :return: - nothing

        '''
        if self.transId == 0 :
            return

        challenges = get_challenges(self.getSerial(), transid=self.transId)
        if len(challenges) == 1:
            challenge = challenges[0]
            challenge.setTanStatus(True, True)
            challenge.save()

        ##  still in rollout state??
        rolloutState = self.getFromTokenInfo('rollout', '0')

        if rolloutState == '2':
            t_info = self.getTokenInfo()
            if t_info.has_key('rollout'):
                del t_info['rollout']
            if t_info.has_key('sharedSecret'):
                del t_info['sharedSecret']
            if t_info.has_key('nonce'):
                del t_info['nonce']
            self.setTokenInfo(t_info)

            log.info('rollout for token %r completed' % (self.getSerial()))

        elif rolloutState == '1':
            raise Exception('unable to complete the rollout ')

        return

    @log_with(log)
    def resync(self, otp1, otp2, options=None):
        '''
        - for the resync to work, we take the last two transactions and their challenges
        - for each challenge, we search forward the sync window length

        '''
        ret = False
        challenges = []

        ## the challenges are orderd, the first one is the newest
        challenges = get_challenges(self.getSerial())

        ##  check if there are enough challenges around
        if len(challenges) < 2:
            return False

        challenge1 = {}
        challenge2 = {}

        if options is None:

            ## the newer one
            ch1 = challenges[0]
            challenge1['challenge'] = ch1.get('data').get('challenge')
            challenge1['transid'] = ch1.get('transid')
            challenge1['session'] = ch1.get('session')
            challenge1['id'] = ch1.get('id')


            ## the elder one
            ch2 = challenges[0]
            challenge2['challenge'] = ch2.get('data').get('challenge')
            challenge2['transid'] = ch2.get('transid')
            challenge2['session'] = ch2.get('session')
            challenge2['id'] = ch2.get('id')

        else:
            if options.has_key('challenge1'):
                challenge1['challenge'] = options.get('challenge1')
            if options.has_key('challenge2'):
                challenge2['challenge'] = options.get('challenge2')


        if len(challenge1) == 0 or len(challenge2) == 0:
            error = "No challeges found!"
            log.error(error)
            raise Exception('[Ocra2TokenClass:resync] %s' % (error))



        secretHOtp = self.token.getHOtpKey()
        ocraSuite = OcraSuite(self.getOcraSuiteSuite(), secretHOtp)

        syncWindow = self.token.getSyncWindow()
        if  ocraSuite.T is not None:
            syncWindow = syncWindow / 10

        counter = self.token.getOtpCounter()

        ## set the ocra token pin
        ocraPin = ''
        if ocraSuite.P is not None:
            ocraPinObj = self.token.getUserPin()
            ocraPin = ocraPinObj.getKey()

            if ocraPin is None or len(ocraPin) == 0:
                ocraPin = ''

        timeShift = 0
        if  ocraSuite.T is not None:
            timeShift = int(self.getFromTokenInfo("timeShift", 0))

        try:

            count_1 = ocraSuite.checkOtp(otp1, counter, syncWindow, challenge1, pin=ocraPin, timeshift=timeShift)
            if count_1 == -1:
                log.info('lookup for first otp value failed!')
                ret = False
            else:
                count_2 = ocraSuite.checkOtp(otp2, counter, syncWindow, challenge2, pin=ocraPin, timeshift=timeShift)
                if count_2 == -1:
                    log.info('lookup for second otp value failed!')
                    ret = False
                else:
                    if ocraSuite.C is not None:
                        if count_1 + 1 == count_2:
                            self.setOtpCount(count_2)
                            ret = True

                    if  ocraSuite.T is not None:
                        if count_1 - count_2 <= ocraSuite.T * 2:
                            ##  callculate the timeshift
                            date = datetime.datetime.fromtimestamp(count_2)
                            log.info('syncing token to new timestamp: %r' % (date))

                            now = datetime.datetime.now()
                            stime = now.strftime("%s")
                            timeShift = count_2 - int(stime)
                            self.addToTokenInfo('timeShift', timeShift)
                            ret = True

        except Exception as ex:
            log.error('unknown error: %r' % (ex))
            raise Exception('[Ocra2TokenClass:resync] unknown error: %s' % (ex))

        return ret


    @log_with(log)
    def getStatus(self, transactionId):
        '''
        getStatus - assembles the status of a transaction / challenge in a dict

        {   "serial": SERIENNUMMER1,
            "transactionid": TRANSACTIONID1,
            "received_tan": true,
            "valid_tan": true,
            "failcount": 0
        }

        :param transactionId:    the transaction / challenge id
        :type transactionId:    string

        :return:    status dict
        :rtype:       dict
        '''
        statusDict = {}
        challenge = get_challenges(self.getSerial(), transid=transactionId)
        if challenge is not None:
            statusDict['serial'] = challenge.tokenserial
            statusDict['transactionid'] = challenge.transid
            statusDict['received_tan'] = challenge.received_tan
            statusDict['valid_tan'] = challenge.valid_tan
            statusDict['failcount'] = self.getFailCount()
            statusDict['id'] = challenge.id
            statusDict['timestamp'] = unicode(challenge.timestamp)
            statusDict['active'] = unicode(self.isActive())

        return statusDict


    @log_with(log)
    def getInitDetail(self, params , user=None):
        '''
        to complete the token normalisation, the response of the initialiastion
        should be build by the token specific method, the getInitDetails
        '''
        response_detail = {}

        info = self.getInfo()
        response_detail.update(info)

        ocra_url = info.get('app_import')
        response_detail["ocraurl"] = {
               "description" : _("URL for OCRA token"),
               "value" : ocra_url,
               "img"   : create_img(ocra_url, width=250)}

        return response_detail

    @log_with(log)
    def getQRImageData(self, response_detail):
        '''
        '''
        url = None
        hparam = {}

        if response_detail is not None:
            if 'ocraurl' in response_detail:
                url = response_detail.get('ocraurl', {}).get("value", "")
                hparam['alt'] = url
            if 'data' in response_detail:
                url = response_detail.get('data')
                hparam['alt'] = url

        return url, hparam


#eof###########################################################################

