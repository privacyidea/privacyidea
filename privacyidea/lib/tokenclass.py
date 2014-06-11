# -*- coding: utf-8 -*-
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

  Description:  This file containes the standard token definitions:
              - OCRATokenClass

              It also contains the base class "TokenClass", that you may use to
              define your own tokenclasses.

              You can add your own Tokens by adding the modules comma seperated to the directive
                  privacyideaTokenModules
              in the privacyidea.ini file.

  Dependencies: depends on several modules from privacyidea.lib but also in case of VascoTokenClass on
              privacyideaee.lib.ImportOTP.vasco


'''
import re
import binascii

import logging
import time
import hashlib
import datetime

import traceback


from privacyidea.lib.error import TokenAdminError
from privacyidea.lib.error import ParameterError

from privacyidea.lib.util import getParam
from privacyidea.lib.util import generate_otpkey
from privacyidea.lib.log import log_with

from privacyidea.lib.config  import getFromConfig

from privacyidea.lib.user import getUserResolverId
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.crypto import decryptPin
from privacyidea.lib.crypto import encryptPin
from privacyidea.lib.crypto import kdf2
from privacyidea.lib.crypto import urandom
from privacyidea.lib.crypto import createNonce

### TODO: move this as ocra specific methods
from privacyidea.lib.token import getRolloutToken4User
from privacyidea.lib.util import normalize_activation_code

from privacyidea.lib.ocra    import OcraSuite
from privacyidea.model       import OcraChallenge

from privacyidea.model.meta  import Session
from privacyidea.lib.reply   import create_img
from privacyidea.lib.apps    import create_google_authenticator_url
from privacyidea.lib.apps    import create_oathtoken_url

from privacyidea.lib.validate import check_pin
from privacyidea.lib.validate import check_otp
from privacyidea.lib.validate import split_pin_otp

from sqlalchemy         import asc, desc
#from sqlalchemy.sql.expression import in_

from pylons.i18n.translation import _



# needed for ocra token
import urllib

import json


optional = True
required = False

log = logging.getLogger(__name__)

class TokenClass(object):

    @log_with(log)
    def __init__(self, token):
        self.type = ''
        self.token = token
        ## the info is a generic container, to store token specific processing info
        ## which could be retrieved in the controllers
        self.info = {}
        self.hKeyRequired = False
        self.mode = ['authenticate', 'challenge']

    def setType(self, typ):
        typ = u'' + typ
        self.type = typ
        self.token.setType(typ)

    @classmethod
    def getClassType(cls):
        return None

    @classmethod
    def getClassPrefix(cls):
        return "UNK"

    def getType(self):
        return self.token.getType()

    def addToInfo(self, key, value):
        self.info[key] = value
        return self.info

    def setInfo(self, info):
        if type(info) not in (dict):
            raise Exception("Info setting: wron data type - msut be dict")
        self.info = info
        return self.info

    @log_with(log)
    def getInfo(self):
        '''
        getInfo - return the status of the token rollout

        :return: return the status dict.
        :rtype: dict
        '''
        return self.info

    def checkOtp(self, anOtpVal1, counter, window, options=None):
        '''
        This checks the OTP value, AFTER the upper level did
        the checkPIN

        return:
            counter of the matching OTP value.
        '''
        return -1

    def getOtp(self, curtTime=""):
        '''
        The default token does not support getting the otp value
        will return something like:
            1, pin, otpval, combined

        a negative value is a failure.
        '''
        return (-2, 0, 0, 0)

    def get_multi_otp(self, count=0, epoch_start=0, epoch_end=0, curTime=None, timestamp=None):
        '''
        This returns a dictionary of multiple future OTP values of a token.

        parameter
        :param count: how many otp values should be returned
        :param epoch_start: time based tokens: start when
        :param epoch_end: time based tokens: stop when
        :param curTime: current time for TOTP token (for selftest)
        :type curTime: datetime object
        :param timestamp: unix time, current time for TOTP token (for selftest)
        :type timestamp: int

        :return: True/False, error text, OTP dictionary
        :rtype: Tuple
        '''
        return (False, "get_multi_otp not implemented for this tokentype", {})

### new highlevel interface which covers the checkPin and checkOTP
    def authenticate(self, passw, user, options=None):
        '''
        This is the method that verifies single shot authentication like
        they are done with push button tokens.

        It is a high level interface to support as well other tokens, which
        do not have a pin and otp seperation - they could overwrite
        this method

        **remarks:** we have to call the global methods (check_pin,++) as they
        take the pin policies into account

        :param passw: the passw which could be pin+otp
        :type passw: string
        :param user: The authenticating user
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: (dict)

        :return: returns tuple true or false for the pin match, the otpcounter (int)
        and the reply (dict) that will be added as additional information in
        the JSON response of ``/validate/check``.
        '''

        pin_match = False
        otp_counter = -1
        reply = None

        (res, pin, otpval) = split_pin_otp(self, passw, user, options=options)
        if res != -1:
            pin_match = check_pin(self, pin, user=user, options=options)
            if pin_match is True:
                otp_counter = check_otp(self, otpval, options=options)

        return (pin_match, otp_counter, reply)


### challenge interfaces starts here
    def is_challenge_request(self, passw, user, options=None):
        '''
        This method checks, if this is a request, that triggers a challenge.

        The default behaviour to trigger a challenge is,
        if the ``passw`` parameter only contains the correct token pin *and*
        the request contains a ``data`` or a ``challenge`` key i.e. if the
        ``options`` parameter contains a key ``data`` or ``challenge``.

        Each token type can decide on its own under which condition a challenge
        is triggered by overwriting this method.

        **please note**: in case of pin policy == 2 (no pin is required)
        the ``check_pin`` would always return true! Thus each request
        containing a ``data`` or ``challenge`` would trigger a challenge!

        :param passw: password, which might be pin or pin+otp
        :type passw: string
        :param user: The user from the authentication request
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict

        :return: true or false
        '''

        request_is_valid = False

        pin_match = check_pin(self, passw, user=user, options=options)
        if pin_match is True:
            if "data" in options or "challenge" in options:
                request_is_valid = True

        return request_is_valid

    def is_challenge_response(self, passw, user, options=None, challenges=None):
        '''
        This method checks, if this is a request, that is the response to
        a previously sent challenge.

        The default behaviour to check if this is the response to a
        previous challenge is simply by checking if the request contains
        a parameter ``state`` or ``transactionid`` i.e. checking if the
        ``options`` parameter contains a key ``state`` or ``transactionid``.

        This method does not try to verify the response itself!
        It only determines, if this is a response for a challenge or not.

        :param passw: password, which might be pin or pin+otp
        :type passw: string
        :param user: the requesting user
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: (dict)
        :param challenges: A list of challenges for this token. These challenges may be used, to identify
        if this request is a response for a challenge.

        :return: true or false
        '''

        challenge_response = False
        if "state" in options or "transactionid" in options:
            challenge_response = True

        ## we leave out the checkOtp, which is done later
        ## either in checkResponse4Challenge
        ## or in the check pin+otp

        return challenge_response


    def is_challenge_valid(self, challenge=None):
        '''
        This method verifies if the given challenge is still valid.

        The default implementation checks, if the challenge start is in the
        default validity time window.

        **Please note**: This method does not check the response for the
        challenge itself. This is done by the method
        :py:meth:`~privacyidea.lib.tokenclass.TokenClass.checkResponse4Challenge`.
        E.g. this very method ``is_challenge_valid`` is used by the method
        :py:meth:`~privacyidea.lib.tokenclass.TokenClass.challenge_janitor`
        to clean up old challenges.

        :param challenge: The challenge to be checked
        :type challenge: challenge object
        :return: true or false
        '''

        validity = 120
        ret = False

        try:
            validity = int(getFromConfig('DefaultChallengeValidityTime', 120))

            ## handle the token specific validity
            typ = self.getType()
            if typ == 'sms':
                lookup_for = 'SMSProviderTimeout'
            else:
                lookup_for = typ.capitalize() + 'ChallengeValidityTime'
            validity = int(getFromConfig(lookup_for, validity))

            ## instance specific timeout
            validity = int(self.getFromTokenInfo('challenge_validity_time',
                                                 validity))

        except ValueError:
            validity = 120

        if challenge is not None:
            c_start_time = challenge.get('timestamp')
            c_now = datetime.datetime.now()
            if (c_now < c_start_time + datetime.timedelta(seconds=validity)
                and c_now > c_start_time):
                ret = True

        return ret

    def initChallenge(self, transactionid, challenges=None, options=None):
        """
        This method initializes the challenge.

        This is a hook that is called before the method
        :py:meth:`~privacyidea.lib.tokenclass.TokenClass.createChallenge`, which
        will only be called if this method returns success==true.

        Thus this method can be used, to verify if there is an outstanding challenge
        or if a new challenge needs to be created.
        E.g. this hook can be used, to implement a blocking mechanism to
        allow the creation of a new challenge only after a certain timeout.
        If there is an already outstanding challenge the return value can refer to this.
        (s. ticket #2986)

        :param transactionid: the id of the new challenge
        :type transactionid: string
        :param options: the request parameters
        :type options: dict
        :param challenges: a list of all valid challenges for this token.
        :type challenges: list

        :return: tuple of ( success, transid, message, additional attributes )

        The ``transid`` (the best transaction id for this request context),
        ``message``, and additional ``attributes`` (dictionar) are displayed as results
        in the JSON response of the ``/validate/check`` request.

        Only in case of ``success`` == true the next method ``createChallenge`` will be called.
        """
        return (True, transactionid, 'challenge init ok', {})


    def checkResponse4Challenge(self, user, passw, options=None, challenges=None):
        '''
        This method verifies if the given ``passw`` matches any existing ``challenge``
        of the token.

        It then returns the new otp_counter of the token and the
        list of the matching challenges.

        In case of success the otp_counter needs to be > 0.
        The matching_challenges is passed to the method
        :py:meth:`~privacyidea.lib.tokenclass.TokenClass.challenge_janitor`
        to clean up challenges.

        :param user: the requesting user
        :type user: User object
        :param passw: the password (pin+otp)
        :type passw: string
        :param options:  additional arguments from the request, which could be token specific
        :type options: dict
        :param challenges: A sorted list of valid challenges for this token.
        :type challenges: list
        :return: tuple of (otpcounter and the list of matching challenges)

        '''
        otp_counter = -1
        transid = None
        matching = None
        matching_challenges = []

        if 'transactionid' in options or 'state' in options:
            ## fetch the transactionid
            transid = options.get('transactionid', None)
            if transid == None:
                transid = options.get('state', None)

        ## check if the transactionid is in the list of challenges
        if transid is not None:
            for challenge in challenges:
                if challenge.getTransactionId() == transid:
                    matching = challenge
                    break
            if matching is not None:
                otp_counter = check_otp(self, passw, options=options)
                if otp_counter >= 0:
                    matching_challenges.append(matching)

        return (otp_counter, matching_challenges)



    def challenge_janitor(self, matching_challenges, challenges):
        '''
        This is the default janitor for the challenges of a token.

        The idea is to delete all challenges, which have an id lower than
        the matching one. Other janitors could be implemented on a token base
        and overwrite this behaviour.

        **Remarks**: In later versions this will be the place to hook a dynamically
        loaded default token specific janitor.

        :param matching_challenges: the last matching challenge
        :type matching_challenges: list
        :param challenges: all current challenges
        :type challenges: list

        :return: list of all challenges, which should be deleted
        '''
        to_be_deleted = []
        if matching_challenges is not None and len(matching_challenges) > 0:
            match_id = 0
            for match in matching_challenges:
                match_id = max([match_id, int(match.get('id'))])

            for ch in challenges:
                if int(ch.get('id')) <= match_id:
                    to_be_deleted.append(ch)

        ## as well append all out dated challenges
        for ch in challenges:
            if self.is_challenge_valid(ch) is False:
                to_be_deleted.append(ch)

        return to_be_deleted


    def createChallenge(self, transactionid, options=None):
        '''
        This method creates a challenge, which is submitted to the user.
        The submitted challenge will be preserved in the challenge
        database.

        This method is called *after* the method
        :py:meth:`~privacyidea.lib.tokenclass.TokenClass.initChallenge`.

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
        :type options: dict
        :return: tuple of (bool, message, data, attributes)

        The return tuple builds up like this:

        ``bool`` if submit was successfull;
        ``message`` which is displayed in the JSON response;
        ``data`` is preserved in the challenge;
        additional ``attributes``, which are displayed in the JSON response.

        '''
        message = 'Otp: '
        data = {'serial' : self.token.getSerial()}
        attributes = None
        return (True, message, data, attributes)

    def flush(self):
        self.token.storeToken()
        Session.flush()
        Session.commit()
        return



    def update(self, param, reset_failcount=True):

        tdesc = getParam(param, "description", optional)
        if tdesc is not None:
            self.token.setDescription(tdesc)

        ## key_size as parameter overrules a prevoiusly set
        ## value e.g. in hashlib in the upper classes
        key_size = getParam(param, "keysize", optional)
        if key_size is None:
            key_size = 20

        ##
        ## process the otpkey:
        ##   if otpkey given - take this
        ##   if not given
        ##       if genkey == 1 : create one
        ##   if required and otpkey == None:
        ##      raise param Exception, that we require an otpkey
        ##
        otpKey = getParam(param, "otpkey", optional)
        genkey = int(getParam(param, "genkey", optional) or 0)

        assert (genkey in [0, 1]), "TokenClass supports only genkey in range [0,1] : %r" % genkey

        if genkey == 1 and otpKey is not None:
            raise ParameterError('[ParameterError] You may either specify genkey or otpkey, but not both!', id=344)

        if otpKey is not None:
            self.token.setHKey(otpKey, reset_failcount=reset_failcount)
        else:
            if genkey == 1:
                otpKey = self._genOtpKey_()

        ## otpKey still None?? - raise the exception
        if otpKey is None:
            if self.hKeyRequired == True:
                otpKey = getParam(param, "otpkey", required)

        if otpKey is not None:
            self.addToInfo('otpkey', otpKey)
            self.setOtpKey(otpKey)

        pin = getParam(param, "pin", optional)
        if pin is not None:
            storeHashed = True
            enc = getParam(param, "encryptpin", optional)
            if enc is not None and "true" == enc.lower():
                storeHashed = False
            self.token.setPin(pin, storeHashed)

        otplen = getParam(param, 'otplen', optional)
        if otplen is not None:
            self.setOtpLen(otplen)

        return

    def _genOtpKey_(self, otpkeylen=None):
        '''
        private method, to create an otpkey
        '''
        if otpkeylen is None:
            if hasattr(self, 'otpkeylen'):
                otpkeylen = getattr(self, 'otpkeylen')
            else:
                otpkeylen = 20
        return generate_otpkey(otpkeylen)

    def setDescription(self, description):
        self.token.setDescription(u'' + description)
        return

    def setDefaults(self):
        ## set the defaults

        self.token.privacyIDEAOtpLen = int(getFromConfig("DefaultOtpLen") or 6)
        self.token.privacyIDEACountWindow = int(getFromConfig("DefaultCountWindow") or 10)
        self.token.privacyIDEAMaxFail = int(getFromConfig("DefaultMaxFailCount") or 10)
        self.token.privacyIDEASyncWindow = int(getFromConfig("DefaultSyncWindow")or 1000)

        self.token.privacyIDEATokenType = u'' + self.type
        return

    def setUser(self, user, report):
        '''
        :param user: a User() object, consisting of loginname and realm
        :param report: tbdf.
        '''
        (uuserid, uidResolver, uidResolverClass) = getUserResolverId(user, report)
        self.token.privacyIDEAIdResolver = uidResolver
        self.token.privacyIDEAIdResClass = uidResolverClass
        self.token.privacyIDEAUserid = uuserid

    def getUser(self):
        uidResolver = self.token.privacyIDEAIdResolver
        uidResolverClass = self.token.privacyIDEAIdResClass
        uuserid = self.token.privacyIDEAUserid
        return (uuserid, uidResolver, uidResolverClass)

    def setUid(self, uid, uidResolver, uidResClass):
        '''
        sets the UID values in the database
        '''
        self.token.privacyIDEAIdResolver = uidResolver
        self.token.privacyIDEAIdResClass = uidResClass
        self.token.privacyIDEAUserid = uid
        return

    def reset(self):
        self.token.privacyIDEAFailCount = 0

    def addToSession(self, Session):
        Session.add(self.token)

    def deleteToken(self):
        self.token.deleteToken()

    def storeToken(self):
        self.token.storeToken()

    def resync(self, otp1, otp2, options=None):
        pass

    def getOtpCountWindow(self):
        return self.token.privacyIDEACountWindow

    def getOtpCount(self):
        return self.token.privacyIDEACount

    def isActive(self):
        return self.token.privacyIDEAIsactive

    def getFailCount(self):
        return self.token.privacyIDEAFailCount

    def setFailCount(self, failCount):
        self.token.privacyIDEAFailCount = failCount

    def getMaxFailCount(self):
        return self.token.privacyIDEAMaxFail

    def getUserId(self):
        return self.token.privacyIDEAUserid

    def setRealms(self, realms):
        self.token.setRealms(realms)

    def getSerial(self):
        return self.token.getSerial()

    def setSoPin(self, soPin):
        self.token.setSoPin(soPin)

    def setUserPin(self, userPin):
        self.token.setUserPin(userPin)

    def setOtpKey(self, otpKey):
        self.token.setHKey(otpKey)

    def setOtpLen(self, otplen):
        self.token.privacyIDEAOtpLen = int(otplen)

    def getOtpLen(self):
        return self.token.privacyIDEAOtpLen


    def setOtpCount(self, otpCount):
        self.token.privacyIDEACount = int(otpCount)

    def setPin(self, pin, param=None):
        '''
        set the PIN. The optional parameter "param" can hold the information,
        if the PIN is encrypted or hashed.
        '''
        if param == None:
            param = {}
        storeHashed = True
        enc = getParam(param, "encryptpin", optional)
        if enc is not None and "true" == enc.lower():
            storeHashed = False

        self.token.setPin(pin, storeHashed)

    def getPinHashSeed(self):
        return self.token.privacyIDEAPinHash, self.token.privacyIDEASeed

    def setPinHashSeed(self, pinhash, seed):
        self.token.privacyIDEAPinHash = pinhash
        self.token.privacyIDEASeed = seed

    def enable(self, enable):
        self.token.privacyIDEAIsactive = enable

    def setMaxFail(self, maxFail):
        self.token.privacyIDEAMaxFail = maxFail

    def setHashLib(self, hashlib):
        self.addToTokenInfo("hashlib", hashlib)

    def incOtpFailCounter(self):
        log.debug('incOtpFailCounter')

        if self.token.privacyIDEAFailCount < self.token.privacyIDEAMaxFail:
            self.token.privacyIDEAFailCount = self.token.privacyIDEAFailCount + 1

        try:
            self.token.storeToken()
        except:
            log.error('update failed')
            raise TokenAdminError("Token Fail Counter update failed", id=1106)

        return self.token.privacyIDEAFailCount



    ### TODO: - this is only HMAC??
    def setCounterWindow(self, countWindow):
        self.token.privacyIDEACountWindow = int(countWindow)

    def getCounterWindow(self):
        return self.token.privacyIDEACountWindow


    def setSyncWindow(self, syncWindow):
        self.token.privacyIDEASyncWindow = int(syncWindow)

    def getSyncWindow(self):
        return self.token.privacyIDEASyncWindow

    ## hashlib algorithms:
    ## http://www.doughellmann.com/PyMOTW/hashlib/index.html#module-hashlib

    def getHashlib(self, hLibStr):

        if hLibStr is None:
            return hashlib.sha1

        hashlibStr = hLibStr.lower()

        if hashlibStr == "md5":
            return hashlib.md5
        elif hashlibStr == "sha1":
            return hashlib.sha1
        elif hashlibStr == "sha224":
            return hashlib.sha224
        elif hashlibStr == "sha256":
            return hashlib.sha256
        elif hashlibStr == "sha384":
            return hashlib.sha384
        elif hashlibStr == "sha512":
            return hashlib.sha512
        else:
            return hashlib.sha1


    def getTokenInfo(self):
        info = {}

        tokeninfo = self.token.getInfo()
        try:
            info = json.loads(tokeninfo)
        except Exception as e:
            log.error('getTokenInfo %r' % (e))

        return info

    def setTokenInfo(self, info):

        if info is not None:
            tokeninfo = u'' + json.dumps(info, indent=0)
            self.token.setInfo(tokeninfo)


    def addToTokenInfo(self, key, value):
        info = {}
        tokeninfo = self.token.getInfo()

        if tokeninfo is not None:
            if len(tokeninfo) > 0 :
                info = json.loads(tokeninfo)

        #if info.has_key(key) == True:
        info[key] = value

        self.setTokenInfo(info)

    def getFromTokenInfo(self, key, default=None):
        ret = default

        info = self.getTokenInfo()

        if key in info:
            ret = info.get(key)
        return ret

    # FIXME: we could store the
    #   count_auth_success_max
    #   count_auth_success
    # and
    #   count_auth_max
    #   count_auth
    # in dedicated columns!
    def set_count_auth_success_max(self, count):
        '''
        Sets the counter for the maximum allowed successful logins
        '''
        self.addToTokenInfo("count_auth_success_max", int(count))

    def set_count_auth_success(self, count):
        '''
        Sets the counter for the occurred successful logins
        '''
        self.addToTokenInfo("count_auth_success", int(count))

    def set_count_auth_max(self, count):
        '''
        Sets the counter for the maximum allowed login attemps
        '''
        self.addToTokenInfo("count_auth_max", int(count))

    def set_count_auth(self, count):
        '''
        Sets the counter for the occurred login attepms
        '''
        self.addToTokenInfo("count_auth", int(count))

    def get_count_auth_success_max(self):
        ret = 0
        try:
            ret = int(self.getFromTokenInfo("count_auth_success_max"))
        except:
            pass
        return ret

    def get_count_auth_success(self):
        ret = 0
        try:
            ret = int(self.getFromTokenInfo("count_auth_success"))
        except:
            pass
        return ret

    def get_count_auth_max(self):
        ret = 0
        try:
            ret = int(self.getFromTokenInfo("count_auth_max"))
        except:
            pass
        return ret

    def get_count_auth(self):
        ret = 0
        try:
            ret = int(self.getFromTokenInfo("count_auth"))
        except:
            pass
        return ret

    def get_validity_period_end(self):
        '''
        returns the end of validity period (if set)
        '''
        ret = ""
        try:
            ret = self.getFromTokenInfo("validity_period_end")
        except:
            pass
        return ret

    def set_validity_period_end(self, end_date):
        '''
        sets the end date of the validity period for a token
        '''
        ## upper layer will catch. we just try to verify the date format
        datetime.datetime.strptime(end_date, "%d/%m/%y %H:%M")

        self.addToTokenInfo("validity_period_end", end_date)

    def get_validity_period_start(self):
        '''
        returns the start of validity period (if set)
        '''
        ret = ""
        try:
            ret = self.getFromTokenInfo("validity_period_start")
        except:
            pass
        return ret

    def set_validity_period_start(self, start_date):
        '''
        sets the start date of the validity period for a token
        '''
        ##  upper layer will catch. we just try to verify the date format
        datetime.datetime.strptime(start_date, "%d/%m/%y %H:%M")
        self.addToTokenInfo("validity_period_start", start_date)


    def inc_count_auth_success(self):
        count = self.get_count_auth_success()
        count += 1
        self.set_count_auth_success(count)
        return count

    def inc_count_auth(self):
        count = self.get_count_auth()
        count += 1
        self.set_count_auth(count)
        return count

    def check_auth_counter(self):
        '''
        This function checks the count_auth and the count_auth_success
        '''
        if 0 != self.get_count_auth_max():
            if self.get_count_auth() >= self.get_count_auth_max():
                return False

        if 0 != self.get_count_auth_success_max():
            if self.get_count_auth_success() >= self.get_count_auth_success_max():
                return False

        return True

    def check_validity_period(self):
        '''
        This checks if the datetime.datetime.now() is within the validity period of the token.

        Returns either True/False
        '''
        start = self.get_validity_period_start()
        end = self.get_validity_period_end()

        check_start = False
        check_end = False
        try:
            dt_start = datetime.datetime.strptime(start, "%d/%m/%y %H:%M")
            check_start = True
        except:
            pass

        try:
            dt_end = datetime.datetime.strptime(end, "%d/%m/%y %H:%M")
            check_end = True
        except:
            pass

        if check_end:
            if dt_end < datetime.datetime.now():
                return False

        if check_start:
            if dt_start > datetime.datetime.now():
                return False

        return True

    @log_with(log)
    def incOtpCounter(self, counter, reset=True):
        '''
        method
            incOtpCounter(aToken, counter)

        parameters:
            token - a token object
            counter - the new counter
            reset - optional -

        exception:
            in case of an transaction fail an exception is thrown

        side effects:
            default of reset will reset the failCounter

        '''
        log.debug('incOtpCounter')

        resetCounter = False
        self.token.privacyIDEACount = counter + 1

        if reset == True:
            if getFromConfig("DefaultResetFailCount") == "True" :
                resetCounter = True

        #log.error("Serial %s: privacyIDEAFailCount %d < privacyIDEAMaxFail %d",token.privacyIDEATokenSerialnumber, token.privacyIDEAFailCount,token.privacyIDEAMaxFail)

        if resetCounter == True:
            if self.token.privacyIDEAFailCount < self.token.privacyIDEAMaxFail and self.token.privacyIDEAIsactive == True:
                self.token.privacyIDEAFailCount = 0;

        try:
            self.token.storeToken()

        except Exception as ex :
            log.error("Token Counter update failed: %r" % (ex))
            raise TokenAdminError("Token Counter update failed: %r" % (ex), id=1106)

        return self.token.privacyIDEACount


    def check_otp_exist(self, otp, window=None):
        '''
        checks if the given OTP value is/are values of this very token.
        This is used to autoassign and to determine the serial number of
        a token.
        '''
        return -1


    def splitPinPass(self, passw):

        res = 0
        try:
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError:
            otplen = 6

        if getFromConfig("PrependPin") == "True" :
            pin = passw[0:-otplen]
            otpval = passw[-otplen:]
        else:
            pin = passw[otplen:]
            otpval = passw[0:otplen]

        #log.error("Pin: %s, otpval:%s",pin,otpval)

        return (res, pin, otpval)


    def checkPin(self, pin, options=None):
        '''
        checkPin - test is the pin is matching

        :param pin:      the pin
        :param options:  additional optional parameters, which could
                         be token specific
        :return: boolean

        '''
        res = False
        log.debug("entering checkPin function")

        if self.token.comparePin(pin) == True:
            res = True

        log.debug("result %r" % res)
        return res

    def statusValidationFail(self):
        ##  callback to enable a status change, if auth failed
        return


    def statusValidationSuccess(self):
        ##  callback to enable a status change, if auth failed
        return

    def __repr__(self):
        '''
        return the token state as text

        :return: token state as string representation
        :rtype:  string
        '''
        ldict = {}
        for attr in self.__dict__:
            key = "%r" % attr
            val = "%r" % getattr(self, attr)
            ldict[key] = val
        res = "<%r %r>" % (self.__class__, ldict)
        return res

    def get_vars(self, save=False):
        '''
        return the token state as dicts
        :return: token as dict
        '''
        ldict = {}
        for attr in self.__dict__:
            key = attr
            val = getattr(self, attr)
            if type(val) in [list, dict, str, unicode, int, float, bool]:
                ldict[key] = val
            elif type(val).__name__.startswith('Token'):
                ldict[key] = val.get_vars(save=save)
            else:
                ldict[key] = "%r" % val
        return ldict

    def getInitDetail(self, params , user=None):
        '''
        to complete the token normalisation, the response of the initialiastion
        should be build by the token specific method, the getInitDetails
        '''
        response_detail = {}

        info = self.getInfo()
        response_detail.update(info)
        response_detail['serial'] = self.getSerial()

        tok_type = self.type.lower()

        otpkey = None
        if 'otpkey' in info:
            otpkey = info.get('otpkey')

        if otpkey != None:
            response_detail["otpkey"] = {
                  "description": _("OTP seed"),
                  "value"      :  "seed://%s" % otpkey,
                  "img"        :  create_img(otpkey, width=200),
                     }
            if user is not None:
                try:

                    goo_url = create_google_authenticator_url(user.login,
                                                  user.realm, otpkey,
                                                  tok_type.lower(),
                                                  serial=self.getSerial())
                    response_detail["googleurl"] = {
                          "description": _("URL for google Authenticator"),
                          "value" :     goo_url,
                          "img"   :     create_img(goo_url, width=250)
                          }

                    oath_url = create_oathtoken_url(user.login, user.realm,
                                                    otpkey, tok_type,
                                                    serial=self.getSerial())
                    response_detail["oathurl"] = {
                          "description" : _("URL for OATH token"),
                           "value" : oath_url,
                           "img"   : create_img(oath_url, width=250)
                           }
                except Exception as ex:
                    log.info('failed to set oath or google url: %r' % ex)

        return response_detail


    def getQRImageData(self, response_detail):
        '''
        '''
        url = None
        hparam = {}

        if response_detail is not None:
            if 'googleurl' in response_detail:
                url = response_detail.get('googleurl')
                hparam['alt'] = url

        return url, hparam


#### OcraTokenClass #####################################


class OcraTokenClass(TokenClass):
    '''
    OcraTokenClass  implement an ocra compliant token

    used from Config
        OcraMaxChallenges         - number of open challenges per token if None: 3
        OcraChallengeTimeout      - timeout definition like 1D, 2H or 3M if None: 1M
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
    def classInit(cls, param, user=None):

        helper_param = {}

        tok_type = "ocra"

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
    @log_with(log)
    def getClassType(cls):
        '''
        getClassType - return the token type shortname

        :return: 'ocra'
        :rtype: string
        '''
        return "ocra"

    @classmethod
    @log_with(log)
    def getClassPrefix(cls):
        return "ocra"

    def __init__(self, aToken):
        '''
        getInfo - return the status of the token rollout

        :return: info of the ocra token state
        :rtype: dict
        '''
        TokenClass.__init__(self, aToken)
        self.setType(u"ocra")
        self.transId = 0
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
        update: add further defintion for token from param in case of init
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
                log.warning('missing parameter genkey\ to complete the rollout 2!')
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
            (transid, challenge, _ret, url) = self.challenge(message)

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
    def challenge(self, data, session='', typ='raw', challenge=None):
        '''
        the challenge method is for creating an transaction / challenge object

        remark: the transaction has a maximum lifetime and a reference to the OcraSuite token (serial)

        :param data:     data, which is the base for the challenge or None
        :type data:     string or None
        :param session:  session support for ocratokens
        :type session:  string
        :type typ:      define, which kind of challenge base should be used
                         could be raw - take the data input as is (extract chars accordind challenge definition Q)
                         or random    - will generate a random input
                         or hased     - will take the hash of the input data

        :return:    challenge response containing the transcation id and the challenge for the ocrasuite
        :rtype :    tuple of (transId(string), challenge(string))


        '''
        s_data = 'None'
        s_session = 'None'
        s_challenge = 'None'
        if data is not None: s_data = data
        if session is not None: s_session = session
        if challenge is None: s_challenge = challenge
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

        serial = self.getSerial()
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
            log.error("%r" % (traceback.format_exc()))
            raise Exception('[OcraTokenClass] Failed to create ocrasuite challenge: %r' % (ex))

        ##  save the object
        digits = '0123456789'
        transid = ''
        transactionIdLen = 12

        try:
            transactionIdLen = int(getFromConfig("OcraDefaultSuite", '12'))
        except:
            transactionIdLen = 12
            log.debug("Failed to set transactionId length from config - using fallback %d" % (transactionIdLen))

        ##  create a non exisiting challenge
        try:
            while True:
                for _c in range(0, transactionIdLen):
                    transid += urandom.choice(digits)

                chall = OcraTokenClass.getTransaction(transid)
                if chall is None:
                    break

            ddata = ''
            if data is not None:
                ddata = data

            chall = OcraChallenge(transid, typ + ':' + challenge, serial, typ + ':' + ddata)
            chall.save()

        except Exception as ex:
            ##  this might happen if we have a db problem or the uniqnes constrain does not fit
            log.error("%r" % (traceback.format_exc()))
            raise Exception('[OcraTokenClass] Failed to create challenge object: %s' % (ex))

        realm = None
        realms = self.token.getRealms()
        if len(realms) > 0:
            realm = realms[0]

        url = ''
        if realm is not None:
            from privacyidea.lib.policy import PolicyClass
            from pylons import request, config, tmpl_context as c
            Policy = PolicyClass(request, config, c,
                                 get_privacyIDEA_config()) 
            url = Policy.get_qrtan_url(realm.name)

        return (transid, challenge, True, url)


    @log_with(log)
    def checkOtp(self, passw , counter , window , options=None):
        '''
        checkOtp - standard callback of privacyidea to verify the token

        :param passw:      the passw / otp, which has to be checked
        :type passw:       string
        :param counter:    the start counter
        :type counter:     int
        :param  window:    the window, in which the token is valid
        :type  window:     int
        :param options:    options contains the transaction id, eg. if check_t checks one transaction
                           this will support assynchreonous otp checks (when check_t is used)
        :type options:     dict

        :return:           verification counter or -1
        :rtype:            int (-1)

        '''
        ret = -1

        secretHOtp = self.token.getHOtpKey()
        ocraSuite = OcraSuite(self.getOcraSuiteSuite(), secretHOtp)

        ## if we have no transactionid given through the options,
        ## we have to retrieve the eldest challenge for this ocra token
        serial = self.getSerial()
        challenges = []

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

        if options is None:
            challenges = OcraTokenClass.getTransactions4serial(serial, currentOnly=True)

        elif options is not None:
            if type(options).__name__ != 'dict':
                err = '[chekOtp] "options" not of type dict! %r' % (type(options))
                log.error(err)
                raise Exception(err)

            if options.has_key('transactionid'):
                transid = options.get('transactionid')
                challenges.append(OcraTokenClass.getTransaction(transid))

            elif options.has_key('challenge'):
                challenges.append(options)

            ## due to the added options in checkUserPass, we have to extend
            ## the logic here:
            ## if no challenges found in between but we have a serial, we catch
            ## the open challenges by serial (s.o.)
            if len(challenges) == 0:
                challenges = OcraTokenClass.getTransactions4serial(serial, currentOnly=True)

        if len(challenges) == 0:
            ##  verify that there has already been a challenge
            challenges = OcraTokenClass.getTransactions4serial(serial)
            if len(challenges) > 0:
                err = 'No current transaction found!'
                ret = -1
                return ret
            else:
                err = 'No open transaction found!'
                log.error(err)
                if type(options) == dict and options.has_key('transactionid'):
                    raise Exception(err)
                ret = -1
                return ret

        for ch in challenges:
            challenge = {}

            if type(ch) == dict:
                ##  transaction less checkOtp
                self.transId = 0
                challenge.update(ch)

            elif type(ch) == OcraChallenge:
                ##  preserve transaction context, so we could use this in the status callback
                self.transId = ch.transid
                challenge['challenge'] = ch.challenge
                challenge['transid'] = ch.transid
                challenge['session'] = ch.session



            ret = ocraSuite.checkOtp(passw, counter, window, challenge, pin=ocraPin , options=options, timeshift=timeShift)

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
                log.warn('sync failed! Not a valid pass in scope (%r)' % (otp1))
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

            log.debug('sync done!')

        return res

    def is_challenge_response(self, passw, user, options=None, challenges=None):
        '''
        check, if the request contains the result of a challenge

        :param passw: password, which might be pin or pin+otp
        :param user: the requesting user
        :param options: dictionary of additional request parameters

        :return: returns true or false
        '''

        challenge_response = False

        return challenge_response

    @log_with(log)
    def statusValidationFail(self):
        '''
        statusValidationFail - callback to enable a status change,

        will be called if the token verification has failed

        :return - nothing

        '''
        ocraChallenge = None

        if self.transId == 0 :
            return

        try:
            ocraChallenge = OcraTokenClass.getTransaction(self.transId)
            ocraChallenge.setTanStatus(received=True, valid=False)

            ##  still in rollout state??
            rolloutState = self.getFromTokenInfo('rollout', '0')

            if rolloutState == '1':
                log.info('rollout state 1 for token %r not completed' % (self.getSerial()))

            elif rolloutState == '2':
                try:
                    maxchall = int(getFromConfig("OcraMaxChallengeRequests", '3'))
                except:
                    maxchall = 3

                if int(ocraChallenge.received_count) >= maxchall:
                    ##  after 3 fails in rollout state 2 - reset to rescan
                    self.addToTokenInfo('rollout', '1')
                    log.info('rollout for token %r reset to phase 1:' % (self.getSerial()))

                log.info('rollout for token %r not completed' % (self.getSerial()))

        except Exception as ex:
            log.error('Error during validation finalisation for token %r :%r' % (self.getSerial(), ex))
            log.error("%r" % (traceback.format_exc()))
            raise Exception(ex)

        finally:
            if ocraChallenge != None:
                ocraChallenge.save()

        return

    
    @log_with(log)
    def statusValidationSuccess(self):
        '''
        statusValidationSuccess - callback to enable a status change,

        remark: will be called if the token shas been succesfull verified

        :return: - nothing

        '''
        if self.transId == 0 :
            return

        ocraChallenge = OcraTokenClass.getTransaction(self.transId)
        ocraChallenge.setTanStatus(received=True, valid=True)
        ocraChallenge.save()

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

        o_challenges = OcraTokenClass.getTransactions4serial(self.getSerial())
        for challenge in o_challenges:
            challenges.append(challenge)

        ##  check if there are enough challenges around
        if len(challenges) < 2:
            return False

        challenge1 = {}
        challenge2 = {}

        if options is None:
            ch1 = challenges[0]
            challenge1['challenge'] = ch1.challenge
            challenge1['transid'] = ch1.transid
            challenge1['session'] = ch1.session

            ch2 = challenges[1]
            challenge2['challenge'] = ch2.challenge
            challenge2['transid'] = ch2.transid
            challenge2['session'] = ch2.session

        else:
            if options.has_key('challenge1'):
                challenge1['challenge'] = options.get('challenge1')
            if options.has_key('challenge2'):
                challenge2['challenge'] = options.get('challenge2')


        if len(challenge1) == 0 or len(challenge2) == 0:
            error = "No challeges found!"
            log.error('%s' % (error))
            raise Exception('[OcraTokenClass:resync] %s' % (error))



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
            raise Exception('[OcraTokenClass:resync] unknown error: %s' % (ex))

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
        ocraChallenge = OcraTokenClass.getTransaction(transactionId)
        if ocraChallenge is not None:
            statusDict['serial'] = ocraChallenge.tokenserial
            statusDict['transactionid'] = ocraChallenge.transid
            statusDict['received_tan'] = ocraChallenge.received_tan
            statusDict['valid_tan'] = ocraChallenge.valid_tan
            statusDict['failcount'] = self.getFailCount()
            statusDict['id'] = ocraChallenge.id
            statusDict['timestamp'] = unicode(ocraChallenge.timestamp)
            statusDict['active'] = unicode(self.isActive())

        return statusDict


    @classmethod
    @log_with(log)
    def timeoutJanitor(cls):
        '''
        timeoutJanitor - remove all outdated transactions / challenges

        :return: - nothing

        '''
        delta = datetime.timedelta(days=0)
        scopeDef = getFromConfig("OcraChallengeTimeout", '1D')

        ##  timedelta supports : days[, seconds[, microseconds[, milliseconds[, minutes[, hours[, weeks]]]]]]])
        if re.match('^(\d+[DHMS])+$', scopeDef):
            delta = datetime.timedelta(days=0)
            parts = re.findall('\d+[DHMS]', scopeDef)
            for part in parts:
                period = part[-1]
                quantity = int(part[:-1])
                if period == 'D':
                    delta = delta + datetime.timedelta(days=quantity)
                elif period == 'H':
                    delta = delta + datetime.timedelta(hours=quantity)
                elif period == 'M':
                    delta = delta + datetime.timedelta(minutes=quantity)
                elif period == 'S':
                    delta = delta + datetime.timedelta(seconds=quantity)
        else:
            log.info('OcraChallengeTimeout value %r does not match timedelta definition (^(\d+[DHMS])+$)' % (scopeDef))
            try:
                scope_def = int(scopeDef)
                delta = datetime.timedelta(seconds=scope_def)
            except ValueError:
                log.info('Failed to convert OcraChallengeTimeout value from config: %r' % (scopeDef))
                delta = datetime.timedelta(days=1)


        ocraChallenges = Session.query(OcraChallenge).filter(
                            OcraChallenge.timestamp < datetime.datetime.now() - delta)


        for ocraChallenge in ocraChallenges:
            log.warning("dropping outdated ocraChallenge): %r for token %r" %
                        (ocraChallenge.transid, ocraChallenge.tokenserial))
            Session.delete(ocraChallenge)

        return

    @classmethod
    @log_with(log)
    def maxChallengeRequestJanitor(cls):
        '''
        maxChallengeRequestJanitor - remove all transactions / challenges which have been made more than maxChallengeRequests

        :return: - nothing

        '''
        maxRequests = int(getFromConfig("OcraMaxChallengeRequests", '3'))

        ocraChallenges = Session.query(OcraChallenge).filter(
                            OcraChallenge.received_count >= maxRequests)


        for ocraChallenge in ocraChallenges:
            log.warning("dropping outdated ocraChallenge): %r for token %r" % (ocraChallenge.transid, ocraChallenge.tokenserial))
            Session.delete(ocraChallenge)
        return

    @classmethod
    @log_with(log)
    def maxChallengeJanitor(cls, transId=None, serial=None):
        '''
        maxChallengeJanitor - remove for one token (serial) all challengens but the last ones

        :param transId:     the current transaction, which provides a the lookup for the serial number
        :type transId:     string

        :param serial:     the serial number of the token
        :type serial:     string

        :return: - nothing

        '''
        maxChallDef = getFromConfig("OcraMaxChallenges", '3')
        try:
            ones = int(maxChallDef)
        except ValueError as ex:
            log.error('Faild to convert OcraMaxChallenges value from config: %r :%r' % (maxChallDef, ex))
            ones = 3

        if ones <= 0:
            ones = 3

        if transId is not None:
            challenges = Session.query(OcraChallenge).filter(OcraChallenge.transid == u'' + transId)
            if challenges is None:
                log.info('no ocraChallenge found for tranid %r' % (transId))
                return

            for challenge in challenges:
                serial = challenge.tokenserial

        if serial is None:
            log.error('failed to lookup for transid %r or serial %r' % (transId, serial))
            return

        challenges = Session.query(OcraChallenge).\
                        filter(OcraChallenge.tokenserial == u'' + serial)\
                        .order_by(desc(OcraChallenge.id))

        lastIds = set()
        for challenge in challenges:
            if len(lastIds) < ones:
                lastIds.add(challenge.id)
            else:
                log.warning("dropping max ocraChallenges: %r :: %r for token %r" % \
                            (challenge.id, challenge.transid, challenge.tokenserial))
                Session.delete(challenge)
        return

    @classmethod
    @log_with(log)
    def getTransaction(cls, transId):
        '''
        getTransaction - lookup for the challenge object of the given id

        :param transId:   challenge identifier
        :type transId:   string

        :return: the challenge data object
        :rtype: OcraChallenge

        '''
        ##  first do housekeeping - remove outdated transactions
        cls.timeoutJanitor()
        cls.maxChallengeRequestJanitor()
        cls.maxChallengeJanitor(transId=transId)

        ocraChallenge = None
        count = 0


        if transId is not None:
            challenges = Session.query(OcraChallenge).filter(OcraChallenge.transid == u'' + transId)


        if challenges is None:
            log.info('no ocraChallenge found for tranid %r' % (transId))
            return None


        for ocraChallenge in challenges:
            log.debug("%r for token: %r" % (ocraChallenge.transid, ocraChallenge.tokenserial))
            count += 1

        if count == 0 or count > 1:
            log.error('%r ocraChallenge token found for this transaction %r ' % (count, transId))
            #raise Exception('%r ocraChallenge token found for this transaction %r '%(count,transId))

        log.debug('%r' % (ocraChallenge))
        return ocraChallenge


    @classmethod
    @log_with(log)
    def getTransactions4serial(cls, serial, currentOnly=False):
        '''
        getTransactions4serial - give all challenges for a given token serial number

        :param serial:     token serial identifier
        :type serial:     string
        :param currentOnly: boolean Flag to return all Challenges (like for status request)
                             or to return the eldest open transaction / challenge
        :type currentOnly: boolean flag

        :return:         return a list of Challenges
        :rtype:         OcraChallenge obejct list

        '''
        log.debug('%r: %r' % (serial, currentOnly))

        ##  first do housekeeping - remove outdated transactions
        cls.timeoutJanitor()
        cls.maxChallengeRequestJanitor()
        cls.maxChallengeJanitor(serial=serial)


        ocraChallenges = []
        ocraChallenge = None
        challenges = []


        if serial is not None:
            if currentOnly == False:
                challenges = Session.query(OcraChallenge)\
                    .filter(OcraChallenge.tokenserial == u'' + serial)\
                    .order_by(desc(OcraChallenge.id))
            else:
                ##  return the oldest transaction onyl -  orderby(id).limit(1)
                challenges = Session.query(OcraChallenge)\
                    .filter(OcraChallenge.tokenserial == u'' + serial)\
                    .filter(OcraChallenge.received_tan == False)\
                    .order_by(asc(OcraChallenge.id))

        if challenges is None:
            log.info('no ocraChallenge found for serial %r' % (serial))
            return None

        for ocraChallenge in challenges:
            log.debug("%r for token: %r" % (ocraChallenge.transid, ocraChallenge.tokenserial))
            ocraChallenges.append(ocraChallenge)

        return ocraChallenges

    def getInitDetail(self, params , user=None):
        '''
        to complete the token normalisation, the response of the initialiastion
        should be build by the token specific method, the getInitDetails
        '''
        response_detail = {}

        info = self.getInfo()
        response_detail.update(info)

        otpkey = None
        if 'otpkey' in info:
            otpkey = info.get('otpkey')
        response_detail["otpkey"] = otpkey

        ocra_url = info.get('app_import')
        response_detail["ocraurl"] = {
               "description": _("URL for OCRA token"),
               "value": ocra_url,
                "img": create_img(ocra_url, width=250),
               }

        return response_detail

    def getQRImageData(self, response_detail):
        '''
        '''
        url = None
        hparam = {}

        if response_detail is not None:
            if 'ocraurl' in response_detail:
                url = response_detail.get('ocraurl', {}).get('value', '')
                hparam['alt'] = response_detail.get('app_import', '')
        return url, hparam


##eof##########################################################################
