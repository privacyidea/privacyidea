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
  Description:  This file contains the definition of the SMS token class
  
  Dependencies: -

'''

import time
import datetime
import traceback

from privacyidea.lib.HMAC    import HmacOtp
from privacyidea.lib.util    import getParam
from privacyidea.lib.util    import required

from privacyidea.lib.validate import check_pin
from privacyidea.lib.validate import split_pin_otp

from privacyidea.lib.config  import getFromConfig

from privacyidea.lib.policy import PolicyClass
from pylons import request, config, tmpl_context as c
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.log import log_with
from privacyidea.smsprovider.SMSProvider import getSMSProviderClass

from json import loads

from gettext import gettext as _


from privacyidea.lib.tokens.hmactoken import HmacTokenClass

import logging
log = logging.getLogger(__name__)

keylen = {'sha1'    : 20,
          'sha256'  : 32,
          'sha512'  : 64,
          }



class SmsTokenClass(HmacTokenClass):
    '''
    implementation of the sms token class
    '''
    def __init__(self, aToken):
        HmacTokenClass.__init__(self, aToken)
        self.setType(u"sms")
        self.hKeyRequired = False

        # we support various hashlib methods, but only on create
        # which is effectively set in the update
        self.hashlibStr = getFromConfig("hotp.hashlib", "sha1")
        self.mode = ['challenge']
        self.Policy = PolicyClass(request, config, c,
                                  get_privacyIDEA_config())

    @classmethod
    def getClassType(cls):
        '''
        return the generic token class identifier
        '''
        return "sms"

    @classmethod
    def getClassPrefix(cls):
        return "LSSM"

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
               'type' : 'sms',
               'title' : _('SMS Token'),
               'description' :
                    _('sms challenge-response token - hmac event based'),
               'init'         : { 'title'  : {'html'      : 'smstoken.mako',
                                             'scope'     : 'enroll.title', },
                                  'page' : {'html'      : 'smstoken.mako',
                                            'scope'      : 'enroll', },
                                   },

               'config'         : {'title'  : {'html'      : 'smstoken.mako',
                                             'scope'     : 'config.title', },
                                   'page' : {'html'      : 'smstoken.mako',
                                            'scope'      : 'config', },
                                   },

               'selfservice'   :  { 'enroll' :
                                   {'title'  :
                                    { 'html'      : 'smstoken.mako',
                                      'scope'     : 'selfservice.title.enroll',
                                      },
                                    'page' :
                                    {'html'       : 'smstoken.mako',
                                     'scope'      : 'selfservice.enroll',
                                     },
                                    },
                                  },



        }

        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret

    @log_with(log)
    def update(self, param, reset_failcount=True):
        '''
        update - process initialization parameters

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing

        '''
        # specific - phone
        phone = getParam(param, "phone", required)
        self.setPhone(phone)

        ## in case of the sms token, only the server must know the otpkey
        ## thus if none is provided, we let create one (in the TokenClass)
        if not param.has_key('genkey') and not param.has_key('otpkey'):
            param['genkey'] = 1

        HmacTokenClass.update(self, param, reset_failcount)
        return

    @log_with(log)
    def is_challenge_response(self, passw, user, options=None, challenges=None):
        '''
        check, if the request contains the result of a challenge

        :param passw: password, which might be pin or pin+otp
        :param user: the requesting user
        :param options: dictionary of additional request parameters

        :return: returns true or false
        '''

        challenge_response = False

        if "state" in options or "transactionid" in options:
            challenge_response = True

        ## it as well might be a challenge response,
        ## if the passw is longer than the pin
        if challenge_response == False:
            (res, pin, otpval) = split_pin_otp(self, passw, user=user,
                                                            options=options)
            if res >= 0 :
                res = check_pin(self, pin, user=user, options=options)
                if res == True and len(otpval) > 0:
                    challenge_response = True

        return challenge_response

### challenge interfaces starts here
    @log_with(log)
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
        ## do we need to call the
        #(res, pin, otpval) = split_pin_otp(self, passw, user, options=options)

        pin_match = check_pin(self, passw, user=user, options=options)
        if pin_match is True:
            request_is_valid = True

        return request_is_valid

    ##
    ##!!! this function is to be called in the sms controller !!!
    ##
    @log_with(log)
    def submitChallenge(self, options=None):
        '''
        submit the sms message - former method name was checkPin

        :param options: the request options context

        :return: tuple of success and message
        '''
        res = 0
        user = None
        message = "<otp>"

        ## it is configurable, if sms should be triggered by a valid pin
        send_by_PIN = getFromConfig("sms.sendByPin") or True

        if self.isActive() == True and send_by_PIN == True :
            counter = self.getOtpCount()
            log.debug("counter=%r" % counter)
            self.incOtpCounter(counter, reset=False)
            # At this point we must not bail out in case of an
            # Gateway error, since checkPIN is successful. A bail
            # out would cancel the checking of the other tokens
            try:

                if options is not None and type(options) == dict:
                    user = options.get('user', None)
                    if user:
                        _sms_ret, message = self.Policy.get_auth_smstext(
                                                realm=user.realm)
                res, message = self.sendSMS(message=message)
                self.info['info'] = "SMS sent: %r" % res

            except Exception as e:
                # The PIN was correct, but the SMS could not be sent.
                self.info['info'] = unicode(e)
                info = ("The PIN was correct, but the"
                          " SMS could not be sent: %r" % e)
                log.warning(info)
                res = False
                message = info
        if len(message) == 0:
            pass

        return res, message


    def initChallenge(self, transactionid, challenges=None, options=None):
        """
        initialize the challenge -
        in the privacyidea server a challenge object has been allocated and
        this method is called to confirm the need of a new challenge
        or if for the challenge request, there is an already outstanding
        challenge to which then could be referred (s. ticket #2986)

        :param transactionid: the id of the new challenge
        :param options: the request parameters

        :return: tuple of
                success - bool
                transid - the best transaction id for this request context
                message - which is shown to the user
                attributes - further info (dict) shown to the user
        """

        success = True
        transid = transactionid
        message = 'challenge init ok'
        attributes = {}

        now = datetime.datetime.now()
        blocking_time = int(getFromConfig('SMSBlockingTimeout', 60))

        for challenge in challenges:
            start = challenge.get('timestamp')
            expiry = start + datetime.timedelta(seconds=blocking_time)
            ## check if there is already a challenge underway
            if now >= start and now <= expiry:
                transid = challenge.getTransactionId()
                message = 'sms with otp already submitted'
                success = False
                attributes = {'info' : 'challenge already submitted',
                              'state' : transid}
                break

        return (success, transid, message, attributes)

    @log_with(log)
    def createChallenge(self, transactionid, options=None):
        """
        create a challenge, which is submitted to the user

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
        :return: tuple of (bool, message and data)
                 bool, if submit was successful
                 message is submitted to the user
                 data is preserved in the challenge
                 attributes - additional attributes, which are displayed in the
                    output
        """
        success = False
        sms = ""
        message = ""
        attributes = {'state':transactionid}

        success, sms = self.submitChallenge(options=options)

        if success is True:
            message = 'sms submitted'
            self.setValidUntil()
        else:
            attributes = {'state' : ''}
            message = 'sending sms failed'
            if len('sms') > 0:
                message = sms

        ## after submit set validity time in readable
        ## datetime format in the storeing data
        timeScope = self.loadprivacyIDEASMSValidTime()
        expiryDate = datetime.datetime.now() + \
                                    datetime.timedelta(seconds=timeScope)
        data = {'valid_until' : "%s" % expiryDate }

        return (success, message, data, attributes)

    @log_with(log)
    def checkResponse4Challenge(self, user, passw, options=None, challenges=None):
        """
        verify the response of a previous challenge

        :param user:     the requesting user
        :param passw:    the to be checked pass (pin+otp)
        :param options:  options an additional argument, which could be token
                          specific
        :param challenges: the list of challenges, where each challenge is
                            described as dict
        :return: tuple of (otpcounter and the list of matching challenges)

        do the standard check for the response of the challenge +
        change the tokeninfo data of the last challenge
        """
        otp_count = -1
        matching = []

        tok = super(SmsTokenClass, self)
        counter = self.getOtpCount()
        window = self.getOtpCountWindow()

        now = datetime.datetime.now()
        timeScope = self.loadprivacyIDEASMSValidTime()

        otp_val = passw

        ## fallback: do we have pin+otp ??
        (res, pin, otp) = split_pin_otp(self, passw, user=user,
                                                            options=options)

        if res >= 0:
            res = check_pin(self, pin, user=user, options=options)
            if res == True:
                otp_val = otp

        for challenge in challenges:
            otp_count = self.checkOtp(otp_val, counter, window,
                                                            options=options)
            if otp_count > 0 :
                matching.append(challenge)
                break

        return (otp_count, matching)

    @log_with(log)
    def checkOtp(self, anOtpVal, counter, window, options=None):
        '''
        checkOtp - check the otpval of a token against a given counter
        in the + window range

        :param passw: the to be verified passw/pin
        :type passw: string

        :return: counter if found, -1 if not found
        :rtype: int
        '''
        ret = HmacTokenClass.checkOtp(self, anOtpVal, counter, window)
        if ret != -1:
            if self.isValid() == False:
                ret = -1

        if ret >= 0:
            if self.Policy.get_auth_AutoSMSPolicy():
                user = None
                message = "<otp>"
                if options is not None and type(options) == dict:
                    user = options.get('user', None)
                    if user:
                        sms_ret, message = self.Policy.get_auth_smstext(realm=user.realm)
                self.incOtpCounter(ret, reset=False)
                success, message = self.sendSMS(message=message)

        if ret >= 0:
            msg = "otp verification was successful!"
        else:
            msg = "otp verification failed!"
        log.debug("end. %s ret: %r" % (msg, ret))
        return ret


    @log_with(log)
    def getNextOtp(self):
        '''
        access the next valid otp

        :return: otpval
        :rtype: string
        '''
        try:
            ### TODO - replace tokenLen
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError as ex:
            log.error("ValueError %r" % ex)
            raise Exception(ex)

        secret_obj = self.token.getHOtpKey()
        counter = self.token.getOtpCounter()

        #log.debug("serial: %s",serialNum)
        hmac2otp = HmacOtp(secret_obj, counter, otplen)
        nextotp = hmac2otp.generate(counter + 1)

        return nextotp

    ### in the SMS token we use the generic TokenInfo
    ### to store the phone number
    def setPhone(self, phone):
        '''
        setter for the phone number

        :param phone: phone number
        :type phone:  string

        :return: nothing
        '''
        self.setSMSInfo("phone", phone)
        return

    def setUntil(self, until):
        '''
        This is the time the sent OTP value is valid/can be used.
                                                        (internal function)

        :param until: until time in unix time sec
        :type until:  int

        :return: nothing
        '''

        self.setSMSInfo("until", until)
        return

    def getPhone(self):
        '''
        getter for the phone number

        :return:  phone number
        :rtype:  string
        '''

        (phone, _till) = self.getSMSInfo()
        return phone

    def getUntil(self):
        '''
        getter for the until time definition

        :return:  until time definition of unix time sec
        :rtype:  int
        '''

        (_phone, until) = self.getSMSInfo()

        ## suport for direct verification
        if until == 0:
            timeScope = self.loadprivacyIDEASMSValidTime()
            until = int (time.time()) + timeScope
        return until

    @log_with(log)
    def setSMSInfo(self, key, value):
        '''
        generic method to set the sms infos like phone or validity in the
        tokeninfo (json) entry

        :param key: name of the hash key
        :type key:  string
        :param value: value of the entry
        :type value: any

        :return: nothing
        '''
        self.addToTokenInfo(key, value)
        return

    @log_with(log)
    def getSMSInfo(self):
        '''
        retrieve the phone number and the validity scope

        :return: tuple of phone number and validity time in unix lifetime sec
        '''

        phone = ""
        until = 0

        info = self.getTokenInfo()

        if info.has_key("phone") == True:
            phone = info.get("phone")

        if info.has_key("until") == True:
            until = info.get("until")

        return (phone, until)


    ### we take the countWindow.column to store the time
    ##  in int format (cut off the .2 from the time() )
    ###
    @log_with(log)
    def setValidUntil(self):
        '''
        adjust the timeframe of validity

        :return: nothing
        '''
        timeScope = self.loadprivacyIDEASMSValidTime()
        dueDate = int (time.time()) + timeScope
        self.setUntil(dueDate)
        #self.token.setCountWindow(dueDate)

        return dueDate

    @log_with(log)
    def isValid(self):
        '''
        check if sms challenge is still valid

        :return: True or False
        :rtype: boolean
        '''
        ret = False
        dueDate = self.getUntil()
        now = int(time.time())
        if dueDate >= now:
            ret = True
        if ret == True:
            msg = "the sms challenge is still valid"
        else:
            msg = "the sms challenge is no more valid"
        log.debug("%s: ret: %r" % (msg, ret))
        return ret

    @log_with(log)
    def sendSMS(self, message="<otp>"):
        '''
        send sms

        :param message: the sms submit message - could contain placeholders
         like <otp> or <serial>
        :type message: string

        :return: submitted message
        :rtype: string

        '''
        ret = None

        phone = self.getPhone()
        otp = self.getNextOtp()
        serial = self.getSerial()

        message = message.replace("<otp>", otp)
        message = message.replace("<serial>", serial)

        log.debug("sending SMS to phone number %s " % phone)
        (SMSProvider, SMSProviderClass) = self.loadprivacyIDEASMSProvider()
        log.debug("smsprovider: %s, class: %s"
                                             % (SMSProvider, SMSProviderClass))

        try:
            sms = getSMSProviderClass(SMSProvider, SMSProviderClass)()
        except Exception as exc:
            log.error("Failed to load SMSProvider: %r" % exc)
            log.error(traceback.format_exc())
            raise exc

        try:
            ## now we need the config from the env
            log.debug("loading SMS configuration for class %s" % sms)
            config = self.loadprivacyIDEASMSProviderConfig()
            log.debug("config: %r" % config)
            sms.loadConfig(config)
        except Exception as exc:
            log.error("Failed to load SMSProviderConfig: %r" % exc)
            log.error(traceback.format_exc())
            raise Exception("Failed to load SMSProviderConfig: %r" % exc)

        log.debug("submitMessage: %r, to phone %r" % (message, phone))
        ret = sms.submitMessage(phone, message)
        log.debug("message submitted")

        ## after submit set validity time
        self.setValidUntil()

        # return OTP for selftest purposes
        return ret, message

    @log_with(log)
    def loadprivacyIDEASMSProvider(self):
        '''
        get the SMS Provider class definition

        :return: tuple of SMSProvider and Provider Class as string
        :rtype: tuple of (string, string)
        '''
        smsProvider = getFromConfig("SMSProvider")

        if smsProvider is not None:
            (SMSProvider, SMSProviderClass) = smsProvider.rsplit(".", 1)

        return (SMSProvider, SMSProviderClass)

    @log_with(log)
    def loadprivacyIDEASMSProviderConfig(self):
        '''
        load the defined sms provider config definition

        :return: dict of the sms provider definition
        :rtype: dict
        '''
        ## get User realm
        config = {}

        tConfig = getFromConfig("encprivacyidea.SMSProviderConfig", None)
        if tConfig is None:
            tConfig = getFromConfig("SMSProviderConfig", "{}")

        ## fix the handling of multiline config entries
        lconfig = []
        lines = tConfig.splitlines()
        for line in lines:
            line = line.strip('\\')
            if len(line) > 0:
                lconfig.append(line)

        tConfig = " ".join(lconfig)
        log.debug("providerconfig: %s" % tConfig)

        if tConfig is not None:
            config = loads(tConfig)

        return config

    @log_with(log)
    def loadprivacyIDEASMSValidTime(self):
        '''
        get the challenge time is in the specified range

        :return: the defined validation timeout in seconds
        :rtype:  int
        '''
        try:
            timeout = int(getFromConfig("SMSProviderTimeout", 5 * 60))
        except Exception as ex:
            log.warning("SMSProviderTimeout: value error %r - reset to 5*60"
                                                                        % (ex))
            timeout = 5 * 60
        return timeout

###eof#########################################################################

