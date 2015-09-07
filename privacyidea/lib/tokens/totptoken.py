# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2014-12-03 Cornelius Kölbel <cornelius@privacyidea.org>
#             rewrite for migration to flask.
#             assure 100% code coverage
#  2014-10-03 Cornelius Kölbel <cornelius@privacyidea.org>
#             Code cleanup
#  2014-05-08 Cornelius Kölbel
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
"""
This file contains the definition of the TOTP token class
It depends on the DB model, and the lib.tokenclass.
TOTP is defined in https://tools.ietf.org/html/rfc6238
"""

import logging
import time
import math
import datetime
from privacyidea.lib.tokens.HMAC import HmacOtp
from privacyidea.lib.config import get_from_config
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.hotptoken import HotpTokenClass
from privacyidea.lib.decorators import check_token_locked

optional = True
required = False

keylen = {'sha1': 20,
          'sha256': 32,
          'sha512': 64
          }

log = logging.getLogger(__name__)

class TotpTokenClass(HotpTokenClass):

    # When resyncing we need to do two directly consecutive values.
    resyncDiffLimit = 1

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new TOTP token object from a DB Token object

        :param db_token: instance of the orm db object
        :type db_token:  orm object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"totp")
        self.hKeyRequired = True

    
    @classmethod
    def get_class_type(cls):
        """
        return the token type shortname

        :return: 'totp'
        :rtype: string
        """
        return "totp"

    @classmethod
    def get_class_prefix(cls):
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: TOTP
        """
        return "TOTP"

    @classmethod
    @log_with(log)
    def get_class_info(cls, key=None, ret='all'):
        """
        returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict or scalar
        """
        res = {'type': 'totp',
               'title': 'HMAC Time Token',
               'description': ('TOTP: Time based One Time Passwords.'),
               'init': {'page': {'html': 'totptoken.mako',
                                 'scope': 'enroll', },
                        'title': {'html': 'totptoken.mako',
                                  'scope': 'enroll.title', },
                        },
               'config': {'page': {'html': 'totptoken.mako',
                                   'scope': 'config', },
                          'title': {'html': 'totptoken.mako',
                                    'scope': 'config.title'},
                          },
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {'user': {'totp_timestep': {'type': 'int',
                                                            'value': [30, 60],
                                                            'desc': 'Specify '
                                                            'the time step of '
                                                            'the timebased OTP'
                                                            ' token.'
                                                            },
                                          'totp_hashlib': {'type': 'int',
                                                           'value': ["sha1",
                                                                     "sha256",
                                                                     "sha512"],
                                                           'desc': 'Specify '
                                                           'the hashlib to be '
                                                           'used. Can be sha1'
                                                           ' (1) or sha2-256 '
                                                           '(2).'
                                                           },
                                          },
                          },
               }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret

    @log_with(log)
    def update(self, param, reset_failcount=True):
        """
        This is called during initialzaton of the token
        to add additional attributes to the token object.

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing
        """
        HotpTokenClass.update(self, param, reset_failcount=reset_failcount)

        timeStep = param.get("timeStep",
                             get_from_config("totp.timeStep") or 30)

        timeWindow = param.get("timeWindow",
                               get_from_config("totp.timeWindow") or 180)

        timeShift = param.get("timeShift",
                              get_from_config("totp.timeShift") or 0)
        # we support various hashlib methods, but only on create
        # which is effectively set in the update
        hashlibStr = param.get("totp.hashlib",
                               get_from_config("totp.hashlib",
                                               u'sha1'))

        self.add_tokeninfo("timeWindow", timeWindow)
        self.add_tokeninfo("timeShift", timeShift)
        self.add_tokeninfo("timeStep", timeStep)
        self.add_tokeninfo("hashlib", hashlibStr)

    @property
    def timestep(self):
        timeStepping = int(self.get_tokeninfo("timeStep") or
                           get_from_config("totp.timeStep") or 30)
        return timeStepping

    @property
    def hashlib(self):
        hashlibStr = self.get_tokeninfo("hashlib") or \
                     get_from_config("totp.hashlib", u'sha1')
        return hashlibStr

    @property
    def timewindow(self):
        window = int(self.get_tokeninfo("timeWindow") or
                     get_from_config("totp.timeWindow") or 180)
        return window

    @property
    def timeshift(self):
        shift = float(self.get_tokeninfo("timeShift") or 0)
        return shift

    @log_with(log)
    def check_otp_exist(self, otp, window=None, options=None):
        """
        checks if the given OTP value is/are values of this very token at all.
        This is used to autoassign and to determine the serial number of
        a token.
        In fact it is a check_otp with an enhanced window.

        :param otp: the to be verified otp value
        :type otp: string
        :param window: the lookahead window for the counter in seconds!!!
        :type window: int
        :return: counter or -1 if otp does not exist
        :rtype:  int
        """
        options = options or {}
        timeStepping = int(self.get_tokeninfo("timeStep") or
                           get_from_config("totp.timeStep") or 30)
        window = window or (self.get_sync_window() * timeStepping)
        res = self.check_otp(otp, window=window, options=options)
        return res

    def _time2counter(self, T0, timeStepping=60):
        rnd = 0.5
        counter = int((T0 / timeStepping) + rnd)
        return counter

    def _counter2time(self, counter, timeStepping=60):
        rnd = 0.5
        T0 = (float(counter) - rnd) * int(timeStepping)
        return T0

    def _getTimeFromCounter(self, counter, timeStepping=30, rnd=1):
        idate = int(counter - rnd) * timeStepping
        ddate = datetime.datetime.fromtimestamp(idate / 1.0)
        return ddate

    @log_with(log)
    def _time2float(self, curTime):
        """
        convert a datetime object or an datetime sting into a
        float
        s. http://bugs.python.org/issue12750

        :param curTime: time in datetime format
        :type curTime: datetime object

        :return: time as float
        :rtype: float
        """
        dt = datetime.datetime.now()
        if type(curTime) == datetime.datetime:
            dt = curTime

        td = (dt - datetime.datetime(1970, 1, 1))
        # for python 2.6 compatibility, we have to implement
        # 2.7 .total_seconds()::
        # TODO: fix to float!!!!
        tCounter = ((td.microseconds +
                     (td.seconds + td.days * 24 * 3600)
                     * 10 ** 6) * 1.0) / 10 ** 6
        return tCounter

    @check_token_locked
    def check_otp(self, anOtpVal, counter=None, window=None, options=None):
        """
        validate the token otp against a given otpvalue

        :param anOtpVal: the to be verified otpvalue
        :type anOtpVal:  string
        :param counter: the counter state, that should be verified. For TOTP
        this is the unix system time (seconds) devided by 30/60
        :type counter: int
        :param window: the counter +window (sec), which should be checked
        :type window: int
        :param options: the dict, which could contain token specific info
        :type options: dict
        :return: the counter or -1
        :rtype: int
        """
        otplen = int(self.token.otplen)
        options = options or {}
        secretHOtp = self.token.get_otpkey()
        # oldCounter we have to remove one, as the normal otp handling will
        # increment
        # TODO: Migration: Really?
        # oCount = self.get_otp_count() - 1
        oCount = self.get_otp_count()
        inow = int(time.time())
        window = window or self.timewindow

        initTime = int(options.get('initTime', -1))
        if initTime != -1:
            server_time = int(initTime)
        else:
            server_time = time.time() + self.timeshift

        # If we have a counter from the parameter list
        if not counter:
            # No counter, so we take the current token_time
            counter = self._time2counter(server_time,
                                         timeStepping=self.timestep)
        otime = self._getTimeFromCounter(oCount, timeStepping=self.timestep)
        ttime = self._getTimeFromCounter(counter, timeStepping=self.timestep)

        hmac2Otp = HmacOtp(secretHOtp,
                           counter,
                           otplen,
                           self.get_hashlib(self.hashlib))
        res = hmac2Otp.checkOtp(anOtpVal,
                                int(window / self.timestep),
                                symetric=True)

        if res != -1 and oCount != 0 and res <= oCount:
            log.warning("a previous OTP value was used again! former "
                        "tokencounter: %i, presented counter %i" %
                        (oCount, res))
            res = -1
            return res

        if -1 == res:
            # _autosync: test if two consecutive otps have been provided
            res = self._autosync(hmac2Otp, anOtpVal)

        if res != -1:
            # on success, we have to save the last attempt
            self.set_otp_count(res)
            # and we reset the fail counter
            self.reset()
            # We could also store it temporarily
            # self.auth_details["matched_otp_counter"] = res

            # here we calculate the new drift/shift between the server time
            # and the tokentime
            tokentime = self._counter2time(res, self.timestep)
            tokenDt = datetime.datetime.fromtimestamp(tokentime / 1.0)

            nowDt = datetime.datetime.fromtimestamp(inow / 1.0)

            lastauth = self._counter2time(oCount, self.timestep)
            lastauthDt = datetime.datetime.fromtimestamp(lastauth / 1.0)

            log.debug("last auth : %r" % lastauthDt)
            log.debug("tokentime : %r" % tokenDt)
            log.debug("now       : %r" % nowDt)
            log.debug("delta     : %r" % (tokentime - inow))

            new_shift = (tokentime - inow)
            log.debug("the counter %r matched. New shift: %r" %
                      (res, new_shift))
            self.add_tokeninfo('timeShift', new_shift)
        return res

    @log_with(log)
    def _autosync(self, hmac2Otp, anOtpVal):
        """
        synchronize the token based on two otp values automatically.
        If the OTP is invalid, that OTP counter is stored.
        If an old OTP counter is stored, it is checked, if the new
        OTP value is the next value after this counter.

        internal method to realize the _autosync within the
        checkOtp method

        :param hmac2Otp: the hmac object (with reference to the token secret)
        :type hmac2Otp: hmac object
        :param anOtpVal: the actual otp value
        :type anOtpVal: string
        :return: counter or -1 if otp does not exist
        :rtype:  int
        """
        res = -1
        autosync = False

        async = get_from_config("AutoResync")
        if async is None:
            autosync = False
        elif "true" == async.lower():
            autosync = True

        # if _autosync is not enabled: do nothing
        if autosync is False:
            return res

        info = self.get_tokeninfo()
        syncWindow = self.get_sync_window()

        # check if the otpval is valid in the sync scope
        res = hmac2Otp.checkOtp(anOtpVal, syncWindow, symetric=True)
        log.debug("found otpval %r in syncwindow (%r): %r" %
                  (anOtpVal, syncWindow, res))

        if res != -1:
            # if former is defined
            if "otp1c" in info:
                # check if this is consecutive
                otp1c = int(info.get("otp1c"))
                otp2c = res
                log.debug("otp1c: %r, otp2c: %r" % (otp1c, otp2c))
                diff = math.fabs(otp2c - otp1c)
                if diff > self.resyncDiffLimit:
                    res = -1
                else:
                    server_time = time.time()
                    counter = int((server_time / self.timestep) + 0.5)

                    shift = otp2c - counter
                    info["timeShift"] = shift
                    self.set_tokeninfo(info)

                # now clean the resync data
                del info["otp1c"]
                self.set_tokeninfo(info)

            else:
                log.debug("setting otp1c: %s" % res)
                info["otp1c"] = res
                self.set_tokeninfo(info)
                res = -1

        return res

    @log_with(log)
    def resync(self, otp1, otp2, options=None):
        """
        resync the token based on two otp values
        external method to do the resync of the token

        :param otp1: the first otp value
        :type otp1: string
        :param otp2: the second otp value
        :type otp2: string
        :param options: optional token specific parameters
        :type options:  dict or None
        :return: counter or -1 if otp does not exist
        :rtype:  int
        """
        ret = False
        options = options or {}
        otplen = int(self.token.otplen)
        secretHOtp = self.token.get_otpkey()

        log.debug("timestep: %r, syncWindow: %r, timeShift: %r"
                  % (self.timestep, self.timewindow, self.timeshift))

        initTime = int(options.get('initTime', -1))
        if initTime != -1:
            server_time = int(initTime)
        else:
            server_time = time.time() + self.timeshift

        counter = int((server_time / self.timestep) + 0.5)
        log.debug("counter (current time): %i" % counter)

        oCount = self.get_otp_count()

        log.debug("tokenCounter: %r" % oCount)
        log.debug("now checking window %s, timeStepping %s" %
                  (self.timewindow, self.timestep))
        # check 2nd value
        hmac2Otp = HmacOtp(secretHOtp,
                           counter,
                           otplen,
                           self.get_hashlib(self.hashlib))
        log.debug("%s in otpkey: %s " % (otp2, secretHOtp))
        res2 = hmac2Otp.checkOtp(otp2,
                                 int(self.timewindow / self.timestep),
                                 symetric=True)  # TEST -remove the 10
        log.debug("res 2: %r" % res2)
        # check 1st value
        hmac2Otp = HmacOtp(secretHOtp,
                           counter - 1,
                           otplen,
                           self.get_hashlib(self.hashlib))
        log.debug("%s in otpkey: %s " % (otp1, secretHOtp))
        res1 = hmac2Otp.checkOtp(otp1,
                                 int(self.timewindow / self.timestep),
                                 symetric=True)  # TEST -remove the 10
        log.debug("res 1: %r" % res1)

        if res1 < oCount:
            # A previous OTP value was used again!
            log.warning("a previous OTP value was used again! tokencounter: "
                        "%i, presented counter %i" %
                        (oCount, res1))
            res1 = -1

        if res1 != -1 and res1 + 1 == res2:
            # here we calculate the new drift/shift between the server time
            # and the tokentime
            tokentime = (res2 + 0.5) * self.timestep
            currenttime = server_time - self.timeshift
            new_shift = (tokentime - currenttime)
            log.debug("the counters %r and %r matched. New shift: %r"
                      % (res1, res2, new_shift))
            self.add_tokeninfo('timeShift', new_shift)

            # The OTP value that was used for resync must not be used again!
            self.set_otp_count(res2 + 1)

            ret = True

        if ret is True:
            msg = "resync was successful"
        else:
            msg = "resync was not successful"

        log.debug("end. %s: ret: %r" % (msg, ret))
        return ret

    def get_otp(self, current_time=None, do_truncation=True,
                time_seconds=None, challenge=None):
        """
        get the next OTP value

        :param current_time: the current time, for which the OTP value
        should be calculated for.
        :type current_time: datetime object
        :param time_seconds: the current time, for which the OTP value
        should be calculated for (date +%s)
        :type: time_seconds: int, unix system time seconds
        :return: next otp value, and PIN, if possible
        :rtype: tuple
        """
        otplen = int(self.token.otplen)
        secretHOtp = self.token.get_otpkey()

        hmac2Otp = HmacOtp(secretHOtp,
                           self.get_otp_count(),
                           otplen,
                           self.get_hashlib(self.hashlib))

        if time_seconds is None:
            time_seconds = self._time2float(datetime.datetime.now())
        if current_time:
            time_seconds = self._time2float(current_time)

        # we don't need to round here as we have already float
        counter = int(((time_seconds - self.timeshift) / self.timestep))
        otpval = hmac2Otp.generate(counter=counter,
                                   inc_counter=False,
                                   do_truncation=do_truncation,
                                   challenge=challenge)

        pin = self.token.get_pin()
        combined = "%s%s" % (otpval, pin)
        if get_from_config("PrependPin") == "True":
            combined = "%s%s" % (pin, otpval)
            
        return 1, pin, otpval, combined

    @log_with(log)
    def get_multi_otp(self, count=0, epoch_start=0, epoch_end=0,
                      curTime=None, timestamp=None):
        """
        return a dictionary of multiple future OTP values
        of the HOTP/HMAC token

        :param count: how many otp values should be returned
        :type count: int
        :param epoch_start: not implemented
        :param epoch_end: not implemented
        :param curTime: Simulate the servertime
        :type curTime: datetime
        :param timestamp: Simulate the servertime
        :type timestamp: epoch time
        :return: tuple of status: boolean, error: text and the OTP dictionary

        """
        otp_dict = {"type": "TOTP", "otp": {}}
        ret = False
        error = "No count specified"

        otplen = int(self.token.otplen)
        secretHOtp = self.token.get_otpkey()

        hmac2Otp = HmacOtp(secretHOtp, self.get_otp_count(),
                           otplen, self.get_hashlib(self.hashlib))

        if curTime:
            # datetime object provided for simulation
            tCounter = self._time2float(curTime)
        elif timestamp:
            # epoch time provided for simulation
            tCounter = int(timestamp)
        else:
            # use the current server time
            tCounter = self._time2float(datetime.datetime.now())

        # we don't need to round here as we have alread float
        counter = int(((tCounter - self.timeshift) / self.timestep))

        otp_dict["shift"] = self.timeshift
        otp_dict["timeStepping"] = self.timeshift

        if count > 0:
            error = "OK"
            for i in range(0, count):
                otpval = hmac2Otp.generate(counter=counter + i,
                                           inc_counter=False)
                timeCounter = ((counter + i) * self.timestep) + self.timeshift
                
                val_time = datetime.datetime.\
                    fromtimestamp(timeCounter).strftime("%Y-%m-%d %H:%M:%S")
                otp_dict["otp"][counter + i] = {'otpval': otpval,
                                                'time': val_time}
            ret = True
            
        return ret, error, otp_dict
