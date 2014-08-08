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
  Description:  This file contains the definition of the TOTP token class
  
  Dependencies: -

'''

import logging
import time
import math
import datetime

import traceback


from privacyidea.lib.HMAC    import HmacOtp
from privacyidea.lib.util    import getParam
from privacyidea.lib.util    import generate_otpkey
from privacyidea.lib.config  import getFromConfig
from privacyidea.lib.log import log_with

optional = True
required = False

from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.hmactoken import HmacTokenClass

keylen = {'sha1' : 20,
          'sha256' : 32,
          'sha512' : 64
          }

log = logging.getLogger(__name__)



###############################################
###############################################
"""
TOTP Algorithm

   This variant of the HOTP algorithm specifies the calculation of a
   one-time password value, based on a representation of the counter as
   a time factor.

4.1.  Notations

   - X represents the time step in seconds (default value X = 30
   seconds) and is a system parameter;

   - T0 is the Unix time to start counting time steps (default value is
   0, Unix epoch) and is also a system parameter.

4.2.  Description

   Basically, we define TOTP as TOTP = HOTP(K, T) where T is an integer
   and represents the number of time steps between the initial counter
   time T0 and the current Unix time (i.e. the number of seconds elapsed
   since midnight UTC of January 1, 1970).

   More specifically T = (Current Unix time - T0) / X where:

   - X represents the time step in seconds (default value X = 30
   seconds) and is a system parameter;

   - T0 is the Unix time to start counting time steps (default value is
   0, Unix epoch) and is also a system parameter;

   - The default floor function is used in the computation.  For
   example, with T0 = 0 and time step X = 30, T = 1 if the current Unix
   time is 59 seconds and T = 2 if the current Unix time is 60 seconds.

M'Raihi, et al.          Expires March 12, 2011                 [Page 5]

Internet-Draft                HOTPTimeBased               September 2010


"""

###############################################
class TimeHmacTokenClass(HmacTokenClass):

    resyncDiffLimit = 3

    @log_with(log)
    def __init__(self, aToken):
        '''
        constructor - create a token object

        :param aToken: instance of the orm db object
        :type aToken:  orm object

        '''
        TokenClass.__init__(self, aToken)
        self.setType(u"TOTP")
        self.hKeyRequired = True

        ''' timeStep defines the granularity: '''
        self.timeStep = getFromConfig("totp.timeStep", 30)

        ''' window size in seconds:
            30 seconds with as step width of 30 seconds results
            in a window of 1  which is one attempt
        '''
        self.timeWindow = getFromConfig("totp.timeWindow", 180)


        '''the time shift is specified in seconds  - and could be
        positive and negative
        '''
        self.timeShift = getFromConfig("totp.timeShift", 0)

        '''we support various hashlib methods, but only on create
        which is effectively set in the update
        '''
        self.hashlibStr = getFromConfig("totp.hashlib", u'sha1')
        return
    
    @classmethod
    def getClassType(cls):
        '''
        getClassType - return the token type shortname

        :return: 'totp'
        :rtype: string

        '''
        return "totp"

    @classmethod
    def getClassPrefix(cls):
        return "TOTP"


    @classmethod
    @log_with(log)
    def getClassInfo(cls, key=None, ret='all'):
        '''
        getClassInfo - returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string

        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype: s.o.

        '''
        res = {
               'type'           : 'totp',
               'title'          : 'HMAC Time Token',
               'description'    : ('time based otp token using the hmac algorithm'),

               'init'         : {'page' : {'html'      : 'totptoken.mako',
                                            'scope'      : 'enroll', },
                                   'title'  : {'html'      : 'totptoken.mako',
                                             'scope'     : 'enroll.title', },
                                   },

               'config'        : { 'page' : {'html'      : 'totptoken.mako',
                                            'scope'      : 'config', },
                                   'title'  : {'html'      : 'totptoken.mako',
                                             'scope'     : 'config.title', },
                                 },

               'selfservice'   :  { 'enroll' : {'page' : {'html'       : 'totptoken.mako',
                                                          'scope'      : 'selfservice.enroll', },
                                               'title'  : { 'html'      : 'totptoken.mako',
                                                         'scope'      : 'selfservice.title.enroll', },
                                                  },
                                  },
               'policy' : {
                    'selfservice' : {
                        'totp_timestep': {
                            'type':'int',
                            'value' : [30, 60],
                            'desc' : 'Specify the time step of the timebased OTP token.'
                                  },
                       'totp_hashlib' : {'type':'int',
                          'value' : [1, 2],
                          'desc' : 'Specify the hashlib to be used. Can be sha1 (1) or sha2-256 (2).'
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
    def update(self, param):
        '''
        update - process the initialization parameters

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing
        '''
        ## check for the required parameters
        val = getParam(param, "hashlib", optional)
        if val is not None:
            self.hashlibStr = val
        else:
            self.hashlibStr = 'sha1'

        otpKey = ''

        if (self.hKeyRequired == True):
            genkey = int(getParam(param, "genkey", optional) or 0)
            if 1 == genkey:
                # if hashlibStr not in keylen dict, this will raise an Exception
                otpKey = generate_otpkey(keylen.get(self.hashlibStr))
                del param['genkey']
            else:
                # genkey not set: check otpkey is given
                # this will raise an exception if otpkey is not present
                otpKey = getParam(param, "otpkey", required)

        # finally set the values for the update
        param['otpkey'] = otpKey
        param['hashlib'] = self.hashlibStr

        val = getParam(param, "otplen", optional)
        if val is not None:
            self.setOtpLen(int(val))
        else:
            self.setOtpLen(getFromConfig("DefaultOtpLen"))

        val = getParam(param, "timeStep", optional)
        if val is not None:
            self.timeStep = val

        val = getParam(param, "timeWindow", optional)
        if val is not None:
            self.timeWindow = val

        val = getParam(param, "timeShift", optional)
        if val is not None:
            self.timeShift = val


        HmacTokenClass.update(self, param)

        self.addToTokenInfo("timeWindow", self.timeWindow)
        self.addToTokenInfo("timeShift", self.timeShift)
        self.addToTokenInfo("timeStep", self.timeStep)
        self.addToTokenInfo("hashlib", self.hashlibStr)

        return

    @log_with(log)
    def check_otp_exist(self, otp, window=10):
        '''
        checks if the given OTP value is/are values of this very token.
        This is used to autoassign and to determine the serial number of
        a token.

        :param otp: the to be verified otp value
        :type otp: string

        :param window: the lookahead window for the counter
        :type window: int

        :return: counter or -1 if otp does not exist
        :rtype:  int

        '''
        res = -1

        try:
            counter = int(self.token.privacyIDEACount)
        except ValueError as ex:
            log.warning("a value error occurred while converting: counter %r : ValueError: %r ret: %r "
                      % (self.token.privacyIDEACount, ex, res))
            return res

        res = self.checkOtp(otp, counter, range)

        return res

    def _time2counter_(self, T0, timeStepping=60):
        rnd = 0.5
        counter = int((T0 / timeStepping) + rnd)
        return counter

    def _counter2time_(self, counter, timeStepping=60):
        rnd = 0.5
        T0 = (float(counter) - rnd) * timeStepping
        return T0

    def _getTimeFromCounter(self, counter, timeStepping=30, rnd=1):
        idate = int(counter - rnd) * timeStepping
        ddate = datetime.datetime.fromtimestamp(idate / 1.0)
        return ddate

    @log_with(log)
    def time2float(self, curTime):
        '''
        time2float - convert a datetime object or an datetime sting into a float
        s. http://bugs.python.org/issue12750

        :param curTime: time in datetime format
        :type curTime: datetime object

        :return: time as float
        :rtype: float
        '''
        dt = datetime.datetime.now()
        if type(curTime) == datetime.datetime:
            dt = curTime
        elif type(curTime) == unicode:
            if '.' in curTime:
                tFormat = "%Y-%m-%d %H:%M:%S.%f"
            else:
                tFormat = "%Y-%m-%d %H:%M:%S"
            try:
                dt = datetime.datetime.strptime(curTime, tFormat)
            except Exception as ex:
                log.error('Error during conversion of datetime: %r' % (ex))
                log.error("%r" % traceback.format_exc())
                raise Exception(ex)
        else:
            log.error("invalid curTime: %s. You need to specify a datetime.datetime" % type(curTime))
            raise Exception("[time2float] invalid curTime: %s. You need to specify a datetime.datetime" % type(curTime))

        td = (dt - datetime.datetime(1970, 1, 1))
        ## for python 2.6 compatibility, we have to implement 2.7 .total_seconds()::
        ## TODO: fix to float!!!!
        tCounter = ((td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) * 1.0) / 10 ** 6
        return tCounter


    @log_with(log)
    def checkOtp(self, anOtpVal, counter, window, options=None):
        '''
        checkOtp - validate the token otp against a given otpvalue

        :param anOtpVal: the to be verified otpvalue
        @type anOtpVal:  string

        :param counter: the counter state, that should be verified
        :type counter: int

        :param window: the counter +window, which should be checked
        :type window: int

        :param options: the dict, which could contain token specific info
        :type options: dict

        :return: the counter state or -1
        :rtype: int

        '''

        try:
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError as e:
            raise e

        secretHOtp = self.token.getHOtpKey()
        self.hashlibStr = self.getFromTokenInfo("hashlib", self.hashlibStr)

        timeStepping = int(self.getFromTokenInfo("timeStep", self.timeStep))
        window = int(self.getFromTokenInfo("timeWindow", self.timeWindow))
        shift = int(self.getFromTokenInfo("timeShift", self.timeShift))

        ## oldCounter we have to remove one, as the normal otp handling will increment
        oCount = self.getOtpCount() - 1

        initTime = -1
        if options != None and type(options) == dict:
            initTime = int(options.get('initTime', -1))

        if oCount < 0: oCount = 0
        log.debug("timestep: %i, timeWindow: %i, timeShift: %i" %
                  (timeStepping, window, shift))
        inow = int(time.time())

        T0 = time.time() + shift
        if initTime != -1: T0 = int(initTime)


        log.debug("T0 : %i" % T0)
        counter = self._time2counter_(T0, timeStepping=timeStepping)


        otime = self._getTimeFromCounter(oCount, timeStepping=timeStepping)
        ttime = self._getTimeFromCounter(counter, timeStepping=timeStepping)

        log.debug("last log: %r :: %r" % (oCount, otime))
        log.debug("counter : %r :: %r <==> %r" %
                  (counter, ttime, datetime.datetime.now()))


        log.debug("shift   : %r " % (shift))

        hmac2Otp = HmacOtp(secretHOtp, counter, otplen, self.getHashlib(self.hashlibStr))
        res = hmac2Otp.checkOtp(anOtpVal, int (window / timeStepping), symetric=True)

        log.debug("comparing the result %i to the old counter %i." % (res, oCount))
        if res != -1 and oCount != 0 and res <= oCount:
            if initTime == -1:
                log.warning("a previous OTP value was used again!\n former tokencounter: %i, presented counter %i" %
                        (oCount, res))
                res = -1
                return res

        if -1 == res :
            ## autosync: test if two consecutive otps have been provided
            res = self.autosync(hmac2Otp, anOtpVal)


        if res != -1:
            ## on success, we have to save the last attempt
            self.setOtpCount(counter)

            #
            # here we calculate the new drift/shift between the server time and the tokentime
            #
            tokentime = self._counter2time_(res, timeStepping)
            tokenDt = datetime.datetime.fromtimestamp(tokentime / 1.0)

            nowDt = datetime.datetime.fromtimestamp(inow / 1.0)

            lastauth = self._counter2time_(oCount, timeStepping)
            lastauthDt = datetime.datetime.fromtimestamp(lastauth / 1.0)

            log.debug("last auth : %r" % (lastauthDt))
            log.debug("tokentime : %r" % (tokenDt))
            log.debug("now       : %r" % (nowDt))
            log.debug("delta     : %r" % (tokentime - inow))

            new_shift = (tokentime - inow)
            log.debug("the counter %r matched. New shift: %r" %
                      (res, new_shift))
            self.addToTokenInfo('timeShift', new_shift)
        return res

    @log_with(log)
    def autosync(self, hmac2Otp, anOtpVal):
        '''
        auto - sync the token based on two otp values
        - internal method to realize the autosync within the
        checkOtp method

        :param hmac2Otp: the hmac object (with reference to the token secret)
        :type hmac2Otp: hmac object

        :param anOtpVal: the actual otp value
        :type anOtpVal: string

        :return: counter or -1 if otp does not exist
        :rtype:  int

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
        except Exception as e:
            log.error('autosync check failed %r' % e)
            return res

        ' if autosync is not enabled: do nothing '
        if False == autosync:
            return res

        info = self.getTokenInfo();
        syncWindow = self.getSyncWindow()

        #check if the otpval is valid in the sync scope
        res = hmac2Otp.checkOtp(anOtpVal, syncWindow, symetric=True)
        log.debug("found otpval %r in syncwindow (%r): %r" %
                  (anOtpVal, syncWindow, res))

        #if yes:
        if res != -1:
            # if former is defined
            if (info.has_key("otp1c")):
                #check if this is consecutive
                otp1c = info.get("otp1c");
                otp2c = res
                log.debug("otp1c: %r, otp2c: %r" % (otp1c, otp2c))
                diff = math.fabs(otp2c - otp1c)
                if (diff > self.resyncDiffLimit):
                    res = -1
                else:
                    T0 = time.time()
                    timeStepping = int(self.getFromTokenInfo("timeStep"))
                    counter = int((T0 / timeStepping) + 0.5)

                    shift = otp2c - counter
                    info["timeShift"] = shift
                    self.setTokenInfo(info)


                ## now clean the resync data
                del info["otp1c"]
                self.setTokenInfo(info)

            else:
                log.debug("etting otp1c: %s" % res)
                info["otp1c"] = res
                self.setTokenInfo(info)
                res = -1

        if res == -1:
            msg = "call was not successful"
        else:
            msg = "call was successful"
        log.debug("end. %r: res %r" % (msg, res))

        return res

    @log_with(log)
    def resync(self, otp1, otp2, options=None):
        '''
        resync the token based on two otp values
        - external method to do the resync of the token

        :param otp1: the first otp value
        :type otp1: string

        :param otp2: the second otp value
        :type otp2: string

        :param options: optional token specific parameters
        :type options:  dict or None

        :return: counter or -1 if otp does not exist
        :rtype:  int

        '''
        ret = False

        try:
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError:
            return ret


        secretHOtp = self.token.getHOtpKey()

        self.hashlibStr = self.getFromTokenInfo("hashlib", 'sha1')
        timeStepping = int(self.getFromTokenInfo("timeStep", 30))
        shift = int(self.getFromTokenInfo("timeShift", 0))

        try:
            window = int(self.token.privacyIDEASyncWindow) * timeStepping
        except:
            window = 10 * timeStepping

        log.debug("timestep: %r, syncWindow: %r, timeShift: %r"
                  % (timeStepping, window, shift))


        T0 = time.time() + shift

        log.debug("T0 : %i" % T0)
        counter = int((T0 / timeStepping) + 0.5)  # T = (Current Unix time - T0) / timeStepping
        log.debug("counter (current time): %i" % counter)

        oCount = self.getOtpCount()

        log.debug("tokenCounter: %r" % oCount)
        log.debug("now checking window %s, timeStepping %s" % (window, timeStepping))
        # check 2nd value
        hmac2Otp = HmacOtp(secretHOtp, counter, otplen, self.getHashlib(self.hashlibStr))
        log.debug("%s in otpkey: %s " % (otp2, secretHOtp))
        res2 = hmac2Otp.checkOtp(otp2, int (window / timeStepping), symetric=True)  #TEST -remove the 10
        log.debug("res 2: %r" % res2)
        # check 1st value
        hmac2Otp = HmacOtp(secretHOtp, counter - 1, otplen, self.getHashlib(self.hashlibStr))
        log.debug("%s in otpkey: %s " % (otp1, secretHOtp))
        res1 = hmac2Otp.checkOtp(otp1, int (window / timeStepping), symetric=True)  #TEST -remove the 10
        log.debug("res 1: %r" % res1)

        if res1 < oCount:
            # A previous OTP value was used again!
            log.warning("a previous OTP value was used again! tokencounter: %i, presented counter %i" %
                        (oCount, res1))
            res1 = -1

        if res1 != -1 and res1 + 1 == res2:
            # here we calculate the new drift/shift between the server time and the tokentime
            tokentime = (res2 + 0.5) * timeStepping
            currenttime = T0 - shift
            new_shift = (tokentime - currenttime)
            log.debug("the counters %r and %r matched. New shift: %r"
                       % (res1, res2, new_shift))
            self.addToTokenInfo('timeShift', new_shift)

            # The OTP value that was used for resync must not be used again!
            self.setOtpCount(res2+1)

            ret = True

        if ret == True:
            msg = "resync was successful"
        else:
            msg = "resync was not successful"

        log.debug("end. %s: ret: %r" % (msg, ret))
        return ret

    def getSyncTimeOut(self):
        '''
        get the token sync timeout value

        :return: timeout value in seconds
        :rtype:  int
        '''

        timeOut = int(getFromConfig("AutoResyncTimeout", 5 * 60))
        return timeOut

    @log_with(log)
    def getOtp(self,
               curTime=None,
               do_truncation=True,
               tCounter=None,
               challenge=None):
        '''
        get the next OTP value

        :return: next otp value
        :rtype: string
        '''
        otplen = int(self.token.privacyIDEAOtpLen)
        secretHOtp = self.token.getHOtpKey()
        self.hashlibStr = self.getFromTokenInfo("hashlib", "sha1")
        timeStepping = int(self.getFromTokenInfo("timeStep", 30))
        shift = int(self.getFromTokenInfo("timeShift", 0))

        hmac2Otp = HmacOtp(secretHOtp,
                           self.getOtpCount(),
                           otplen,
                           self.getHashlib(self.hashlibStr))

        if tCounter is None:
            tCounter = self.time2float(datetime.datetime.now())
        if curTime:
            tCounter = self.time2float(curTime)

        # we don't need to round here as we have alread float
        counter = int(((tCounter - shift) / timeStepping))
        otpval = hmac2Otp.generate(counter=counter,
                                   inc_counter=False,
                                   do_truncation=do_truncation,
                                   challenge=challenge)

        pin = self.token.getPin()
        combined = "%s%s" % (otpval, pin)
        if getFromConfig("PrependPin") == "True":
            combined = "%s%s" % (pin, otpval)
            
        return (1, pin, otpval, combined)

    @log_with(log)
    def get_multi_otp(self, count=0, epoch_start=0, epoch_end=0,
                      curTime=None, timestamp=None):
        '''
        return a dictionary of multiple future OTP values
        of the HOTP/HMAC token

        :param count: how many otp values should be returned
        :type count: int

        :return: tuple of status: boolean, error: text and the OTP dictionary

        '''
        otp_dict = {"type": "TOTP", "otp": {}}
        ret = False
        error = "No count specified"
        try:
            otplen = int(self.token.privacyIDEAOtpLen)
        except ValueError:
            return ret

        secretHOtp = self.token.getHOtpKey()

        self.hashlibStr = self.getFromTokenInfo("hashlib", "sha1")
        timeStepping = int(self.getFromTokenInfo("timeStep", 30))
        shift = int(self.getFromTokenInfo("timeShift", 0))

        hmac2Otp = HmacOtp(secretHOtp, self.getOtpCount(),
                           otplen, self.getHashlib(self.hashlibStr))

        tCounter = self.time2float(datetime.datetime.now())
        if curTime:
            tCounter = self.time2float(curTime)
        if timestamp:
            tCounter = int(timestamp)

        ## we don't need to round here as we have alread float
        counter = int(((tCounter - shift) / timeStepping))


        otp_dict["shift"] = shift
        otp_dict["timeStepping"] = timeStepping

        if count > 0:
            for i in range(0, count):
                otpval = hmac2Otp.generate(counter=counter + i, inc_counter=False)
                timeCounter = ((counter + i) * timeStepping) + shift
                otp_dict["otp"][ counter + i] = {
                     'otpval' : otpval,
                     'time'  : datetime.datetime.fromtimestamp(timeCounter).strftime("%Y-%m-%d %H:%M:%S"),
                    }
            ret = True
            
        return (ret, error, otp_dict)


