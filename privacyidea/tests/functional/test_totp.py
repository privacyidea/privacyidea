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
  Description:  functional tests
                
  Dependencies: -

'''
import datetime
import binascii
import hmac
import struct
import time
import random

import json

import traceback

from hashlib import sha1, sha256, sha512

from privacyidea.lib.crypto   import geturandom
from privacyidea.tests import TestController, url


import logging
log = logging.getLogger(__name__)


'''
  +-------------+--------------+------------------+----------+--------+
  |  Time (sec) |   UTC Time   | Value of T (hex) |   TOTP   |  Mode  |
  +-------------+--------------+------------------+----------+--------+
  |      59     |  1970-01-01  | 0000000000000001 | 94287082 |  SHA1  |
  |             |   00:00:59   |                  |          |        |
  |  1111111109 |  2005-03-18  | 00000000023523EC | 07081804 |  SHA1  |
  |             |   01:58:29   |                  |          |        |
  |  1111111111 |  2005-03-18  | 00000000023523ED | 14050471 |  SHA1  |
  |             |   01:58:31   |                  |          |        |
  |  1234567890 |  2009-02-13  | 000000000273EF07 | 89005924 |  SHA1  |
  |             |   23:31:30   |                  |          |        |
  |  2000000000 |  2033-05-18  | 0000000003F940AA | 69279037 |  SHA1  |
  |             |   03:33:20   |                  |          |        |
  | 20000000000 |  2603-10-11  | 0000000027BC86AA | 65353130 |  SHA1  |
  |             |   11:33:20   |                  |          |        |

  |      59     |  1970-01-01  | 0000000000000001 | 46119246 | SHA256 |
  |             |   00:00:59   |                  |          |        |
  |  1111111109 |  2005-03-18  | 00000000023523EC | 68084774 | SHA256 |
  |             |   01:58:29   |                  |          |        |
  |  1111111111 |  2005-03-18  | 00000000023523ED | 67062674 | SHA256 |
  |             |   01:58:31   |                  |          |        |
  |  1234567890 |  2009-02-13  | 000000000273EF07 | 91819424 | SHA256 |
  |             |   23:31:30   |                  |          |        |
  |  2000000000 |  2033-05-18  | 0000000003F940AA | 90698825 | SHA256 |
  |             |   03:33:20   |                  |          |        |
  | 20000000000 |  2603-10-11  | 0000000027BC86AA | 77737706 | SHA256 |
  |             |   11:33:20   |                  |          |        |

  |      59     |  1970-01-01  | 0000000000000001 | 90693936 | SHA512 |
  |             |   00:00:59   |                  |          |        |
  |  1111111109 |  2005-03-18  | 00000000023523EC | 25091201 | SHA512 |
  |             |   01:58:29   |                  |          |        |
  |  1111111111 |  2005-03-18  | 00000000023523ED | 99943326 | SHA512 |
  |             |   01:58:31   |                  |          |        |
  |  1234567890 |  2009-02-13  | 000000000273EF07 | 93441116 | SHA512 |
  |             |   23:31:30   |                  |          |        |
  |  2000000000 |  2033-05-18  | 0000000003F940AA | 38618901 | SHA512 |
  |             |   03:33:20   |                  |          |        |
  | 20000000000 |  2603-10-11  | 0000000027BC86AA | 47863826 | SHA512 |
  |             |   11:33:20   |                  |          |        |
  +-------------+--------------+------------------+----------+--------+



'''
seed = "3132333435363738393031323334353637383930"
seed32 = "3132333435363738393031323334353637383930313233343536373839303132"
seed64 = "31323334353637383930313233343536373839303132333435363738393031323334353637383930313233343536373839303132333435363738393031323334"

testvector = [
     { 'key'   : seed, 'timeStep' : 30,
       'hash'  : sha1, 'shash': 'sha1',
       'otps'  : [ (59, '94287082', '1970-01-01 00:00:59'), (1111111109, '07081804', '2005-03-18 01:58:29'),
                   (1111111111, '14050471', '2005-03-18 01:58:31'), (1234567890, '89005924', '2009-02-13 23:31:30'),
                   (2000000000, '69279037', '2033-05-18 03:33:20'), (20000000000, '65353130', '2603-10-11 11:33:20'), ] },

     { 'key'   : seed32, 'timeStep' : 30,
       'hash'  : sha256, 'shash': 'sha256',
       'otps'  : [ (59, '46119246', '1970-01-01 00:00:59'), (1111111109, '68084774' , '2005-03-18 01:58:29'),
                   (1111111111, '67062674', '2005-03-18 01:58:31'), (1234567890, '91819424' , '2009-02-13 23:31:30'),
                   (2000000000, '90698825', '2033-05-18 03:33:20'), (20000000000, '77737706', '2603-10-11 11:33:20'), ] },

     { 'key'   : seed64, 'timeStep' : 30,
       'hash'  : sha512, 'shash': 'sha512',
       'otps'  : [(59, '90693936', '1970-01-01 00:00:59'), (1111111109, '25091201', '2005-03-18 01:58:29'),
                  (1111111111, '99943326', '2005-03-18 01:58:31'), (1234567890, '93441116', '2009-02-13 23:31:30'),
                  (2000000000, '38618901', '2033-05-18 03:33:20'), (20000000000, '47863826', '2603-10-11 11:33:20'), ] }
]


class HmacOtp:

    def __init__(self, key, counter=0, digits=6, hashfunc=sha1):
        self.key = key
        self.counter = counter
        self.digits = digits
        self.hashfunc = hashfunc

    def hmac(self, key=None, counter=None):
        key = key or self.key
        counter = counter or self.counter
        digest = hmac.new(key, struct.pack(">Q", counter), self.hashfunc)
        return digest.digest()

    def truncate(self, digest):
        offset = ord(digest[-1:]) & 0x0f

        binary = (ord(digest[offset + 0]) & 0x7f) << 24
        binary |= (ord(digest[offset + 1]) & 0xff) << 16
        binary |= (ord(digest[offset + 2]) & 0xff) << 8
        binary |= (ord(digest[offset + 3]) & 0xff)

        return binary % (10 ** self.digits)

    def generate(self, key=None, counter=None):
        key = key or self.key
        counter = counter or self.counter
        otp = unicode(self.truncate(self.hmac(key, counter)))
        sotp = (self.digits - len(otp)) * "0" + otp
        return sotp

class TotpToken(object):

    def __init__(self, key=None, keylen=20, algo=None, digits=6, offset=0, jitter=0, timestep=60):


        ''' no key given - create one '''
        if key is None:
            self.key = binascii.hexlify(geturandom(keylen))
        else:
            self.key = key.decode('hex')
            keylen = len(self.key)

        if algo is None:
            if keylen == 20:
                algo = sha1
            elif keylen == 32:
                algo = sha256
            elif keylen == 64:
                algo = sha512
        else:
            algo = algo

        self.offset = offset
        self.jitter = jitter
        self.timestep = timestep
        self.digits = digits


        self.hmacOtp = HmacOtp(self.key, digits=self.digits, hashfunc=algo)

        return

    def getOtp(self, counter= -1, offset=0, jitter=0):
        '''
            @note: we require the ability to set the counter directly
                to validate the hmac token against the defined test vectors
        '''
        if counter == -1:

            if self.jitter != 0 or jitter != 0:
                jitter = random.randrange(-self.jitter , self.jitter)
            else:
                jitter = 0

            offset = self.offset + offset
            T0 = time.time() + offset + jitter
            counter = int((T0 / self.timestep) + 0.5)
        else:
            counter = int((counter / self.timestep) + 0.5)

        otp = self.hmacOtp.generate(counter=counter)

        return (otp, counter)

    def getKey(self):
        return self.key

    def getTimeStep(self):
        return self.timestep


    def getTimeFromCounter(self, counter):
        try:
            idate = int(counter - 0.5) * self.timestep
            ddate = datetime.datetime.utcfromtimestamp(idate / 1.0)
        except Exception as e:
            print "%r" % e
        return ddate



class TestTotpController(TestController):
    '''
    '''
    def setUp(self):
        TestController.setUp(self)
        self.serials = []



    def removeTokens(self):
        for serial in self.serials:
            self.delToken(serial)
        return

    def delToken(self, serial):
        p = {"serial" : serial }
        response = self.app.get(url(controller='admin', action='remove'), params=p)
        return response

    def time2float(self, curTime):
        '''
            time2float - convert a datetime object or an datetime sting into a float

            http://bugs.python.org/issue12750
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
            except Exception as e:
                log.error('[time2float] Error during conversion of datetime: %r' % e)
                log.error("[time2float] %s" % traceback.format_exc())
                raise Exception(e)
        else:
            log.error("[time2float] invalid curTime: %s. You need to specify a datetime.datetime" % type(curTime))
            raise Exception("[time2float] invalid curTime: %s. You need to specify a datetime.datetime" % type(curTime))

        td = (dt - datetime.datetime(1970, 1, 1))
        tCounter = (td.microseconds * 1.0 + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10.0 ** 6

        return tCounter

    def addToken(self, user, pin=None, serial=None, typ=None, key=None, timeStep=60, timeShift=0, hashlib='sha1', otplen=8):

        if serial is None:
            serial = 's' + user

        if pin is None:
            pin = user

        if typ is None:
            typ = 'totp'

        param = { 'user': user, 'pin':pin, 'serial': serial, 'type':typ, 'timeStep':timeStep, 'otplen' : otplen, 'hashlib':hashlib}

        if key is not None:
            param['otpkey'] = key

        response = self.app.get(url(controller='admin', action='init'), params=param)
        assert '"status": true,' in response

        return serial

    def createTOTPToken(self, serial, seed):
        '''
            creates the test tokens
        '''
        parameters = {
                          "serial"  : serial,
                          "type"    : "TOTP",
                          # 64 byte key
                          "otpkey"  : seed,
                          "otppin"  : "1234",
                          "pin"     : "pin",
                          "otplen"  : 8,
                          "description" : "TOTP testtoken",
                          }

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        assert '"value": true' in response
        return


    def getTokenInfo(self, serial):
        param = { 'serial': serial}
        response = self.app.get(url(controller='admin', action='show'), params=param)
        assert '"status": true,' in response
        return json.loads(response.body)


    def checkOtp(self, user, otp, pin=None):
        if pin is None:
            pin = user

        param = { 'user': user, 'pass':pin + otp }
        response = self.app.get(url(controller='validate', action='check'), params=param)
        assert '"status": true,' in response

        return response


    def test_algo(self):
        '''
            totp test: verify that the local totp algorith is correct - selftest against testvector spec
        '''
        for tokData in testvector:
            key = tokData.get('key')
            algo = tokData.get('hash')
            step = tokData.get('timeStep')

            t1 = TotpToken(key, digits=8, algo=algo, timestep=step)
            otps = tokData.get('otps')
            for o in otps:
                counter = o[0]
                otp = o[1]
                if 20000000000 != counter:
                    tt = t1.getTimeFromCounter(counter)
                    log.debug("tokentime: %r" % tt)

                (rotp, _count) = t1.getOtp(counter=counter)
                if otp != rotp:
                    (rotp, _count) = t1.getOtp(counter=counter)
                    assert otp == rotp

        return

    def test_increment_timeshift(self):
        '''
            totp test: increments the time offset and verify the timeshift increases
        '''
        tokData = testvector[0]
        user = 'root'


        key = tokData.get('key')
        algo = tokData.get('hash')
        salgo = tokData.get('shash')
        step = tokData.get('timeStep')

        t1 = TotpToken(key, digits=8, algo=algo, timestep=step)
        step = t1.getTimeStep()

        tserial = self.addToken(user=user, typ='totp', key=key, timeStep=step, hashlib=salgo)
        self.serials.append(tserial)

        otpSet = set()

        for i in range(1, 5):
            offset = i * step
            (otp, counter) = t1.getOtp(offset=offset)
            tt = t1.getTimeFromCounter(counter)
            log.debug("tokentime: %r" % tt)

            res = self.checkOtp(user, otp)

            if otp not in otpSet:
                assert '"value": true' in res.body
                resInfo = self.getTokenInfo(tserial)
                tInfo = json.loads(resInfo.get('result').get('value').get('data')[0].get('privacyIDEA.TokenInfo'))
                tShift = tInfo.get('timeShift')
                assert tShift <= offset and tShift >= offset - step
            else:
                assert '"value": false' in res.body

            otpSet.add(otp)
            time.sleep(step / 2)
            log.debug('res')

        self.delToken('s'+user)
        return

    def test_decrement_timeshift(self):
        '''
            totp test: decrements the time offset and verify the timeshift decreases
        '''
        tokData = testvector[0]
        user = 'root'


        key = tokData.get('key')
        algo = tokData.get('hash')
        salgo = tokData.get('shash')
        step = tokData.get('timeStep')

        t1 = TotpToken(key, digits=8, algo=algo, timestep=step)
        step = t1.getTimeStep()

        self.delToken('s'+user)
        tserial = self.addToken(user=user, typ='totp', key=key, timeStep=step, hashlib=salgo)
        self.serials.append(tserial)

        otpSet = set()

        for i in range(1):
            offset = i * step * -1
            (otp, counter) = t1.getOtp(offset=offset)
            tt = t1.getTimeFromCounter(counter)
            log.debug("tokentime: %r" % tt)

            res = self.checkOtp(user, otp)

            if otp not in otpSet:
                if '"value": true' not in res.body:
                    assert '"value": true' in res.body
                resInfo = self.getTokenInfo(tserial)
                tInfo = json.loads(resInfo.get('result').get('value').get('data')[0].get('privacyIDEA.TokenInfo'))
                tShift = tInfo.get('timeShift')
                assert tShift <= offset and tShift >= offset - step
            else:
                assert '"value": false' in res.body

            otpSet.add(otp)
            time.sleep(step)
            log.debug('res')

        self.delToken('s'+user)
        return

    def test_use_token_twice(self):
        '''
            totp test: test if an otp could be used twice
        '''
        user = 'root'
        step = 30

        t1 = TotpToken(timestep=step)
        key = t1.getKey().encode('hex')
        step = t1.getTimeStep()

        tserial = self.addToken(user=user, otplen=t1.digits, typ='totp', key=key, timeStep=step)

        self.serials.append(tserial)

        (otp, counter) = t1.getOtp()
        tt = t1.getTimeFromCounter(counter)
        log.debug("tokentime: %r" % tt)

        res = self.checkOtp(user, otp)
        assert '"value": true' in res.body

        ''' reusing the otp again will fail'''
        res = self.checkOtp(user, otp)
        assert '"value": false' in res.body

        time.sleep(step)


        ''' after a while, we could do a check again'''
        (otp, counter) = t1.getOtp()
        tt = t1.getTimeFromCounter(counter)
        log.debug("tokentime: %r" % tt)

        res = self.checkOtp(user, otp)
        assert '"value": true' in res.body

        return


    def test_getotp(self):
        '''
            totp test: test the getotp - verify that in the list of getotp is the correct start otp of our test vector
        '''


        parameters = { 'name' : 'getmultitoken',
                       'scope' : 'gettoken',
                       'realm' : 'mydefrealm',
                       'action' : 'max_count_dpw=10, max_count_hotp=10, max_count_totp=10',
                       'user' : 'admin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)


        tFormat = "%Y-%m-%d %H:%M:%S"

        for tokData in testvector:
            tkey = tokData.get('key')
            algo = tokData.get('hash')
            salgo = tokData.get('shash')
            step = tokData.get('timeStep')

            t1 = TotpToken(key=tkey, digits=8, algo=algo, timestep=step)
            tserial = self.addToken(user='root', typ='totp', key=tkey, timeStep=step, hashlib=salgo)

            self.serials.append(tserial)

            otps = tokData.get('otps')
            for o in otps:
                tCounter = o[0]
                counter = int(((tCounter) / step))
                otp = o[1]
                curTime = o[2]

                (cotp, ccounter) = t1.getOtp(counter=tCounter)
                tt = t1.getTimeFromCounter(ccounter)
                log.debug("tokentime: %r" % tt)

                parameters = {'serial' : tserial,
                              'curTime' : curTime,
                              'count' : "20",
                              'selftest_admin' : 'admin' }
                response = self.app.get(url(controller='gettoken', action='getmultiotp'), params=parameters)

                print response
                resp = json.loads(response.body)

                otpres = resp.get('result').get('value').get('otp')

                otp1 = otpres.get(str(counter))

                ''' calculate the utc offset'''
                uTime = otp1.get('time')
                fTime = self.time2float(uTime)
                ut = datetime.datetime.utcfromtimestamp(fTime)
                ot = datetime.datetime.fromtimestamp(fTime)
                td = (ut - ot)
                delta = (td.microseconds * 1.0 + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10.0 ** 6

                ''' compare the time absolute values'''
                dt = datetime.datetime.strptime(uTime, tFormat) + datetime.timedelta(seconds=delta)
                ct = datetime.datetime.strptime(curTime, tFormat)
                cl = ct - datetime.timedelta(seconds=step)

                assert dt <= ct and cl <= dt
                assert otp1.get('otpval') == otp


            self.removeTokens()

        return



    def tearDown(self):
        self.removeTokens()

        TestController.tearDown(self)
