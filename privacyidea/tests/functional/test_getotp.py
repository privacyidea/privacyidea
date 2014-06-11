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
from json import loads

from privacyidea.tests import TestController, url

import logging
log = logging.getLogger(__name__)


class TestGetOtpController(TestController):
    '''
    This test at the moment only tests the implementation for the Tagespasswort Token
    
        getotp
        get_multi_otp
    '''
    seed = "3132333435363738393031323334353637383930"
    seed32 = "3132333435363738393031323334353637383930313233343536373839303132"
    seed64 = "31323334353637383930313233343536373839303132333435363738393031323334353637383930313233343536373839303132333435363738393031323334"


    def setUp(self):
        '''
        This sets up all the resolvers and realms
        '''
        TestController.setUp(self)
        self.curTime = datetime.datetime(2012, 5, 16, 9, 0, 52, 227413)
        #self.TOTPcurTime = datetime.datetime.fromtimestamp(1337292860.585256)
        self.TOTPTimestamp = 1337292860
        self.initToken()


    ###############################################################################

    def createDPWToken(self, serial, seed):
        '''        
        creates the test tokens
        '''
        parameters = {
                          "serial"  : serial,
                          "type"    : "DPW",
                          # 64 byte key
                          "otpkey"  : seed,
                          "otppin"  : "1234",
                          "pin"     : "pin",
                          "otplen"  : 6,
                          "description" : "DPW testtoken",
                          }


        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        assert '"value": true' in response


    def createHOTPToken(self, serial, seed):
        '''        
        creates the test tokens
        '''
        parameters = {
                          "serial"  : serial,
                          "type"    : "HMAC",
                          # 64 byte key
                          "otpkey"  : seed,
                          "otppin"  : "1234",
                          "pin"     : "pin",
                          "otplen"  : 6,
                          "description" : "HOTP testtoken",
                          }

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        assert '"value": true' in response


    def createTOTPToken(self, serial, seed, timeStep=30):
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
                          "timeStep"    : timeStep,
                          }

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        assert '"value": true' in response


    def removeTokenBySerial(self, serial):

        parameters = {
                      "serial": serial,
                      }

        response = self.app.get(url(controller='admin', action='remove'), params=parameters)
        return response


    def setTokenRealm(self, serial, realms):
        parameters = { "serial" : serial,
                       "realms" : realms}

        response = self.app.get(url(controller="admin", action="tokenrealm"), params=parameters)
        return response



    def initToken(self):
        '''
        init one DPW token
        '''

        self.createDPWToken("dpw1", "12341234123412341234123412341234")
        '''
        curTime = datetime.datetime(2012, 5, 16, 9, 0, 52, 227413)
            "12-05-22": "202690",
            "12-05-23": "252315",
            "12-05-20": "6",
            "12-05-21": "325819",
            "12-05-24": "263973",
            "12-05-25": "321965",
            "12-05-17": "028193",
            "12-05-16": "427701",
            "12-05-19": "167074",
            "12-05-18": "857788"
        '''
        self.createHOTPToken("hotp1", "12341234123412341234123412341234")
        '''
            "0": "819132",
            "1": "301156",
            "2": "586172",
            "3": "720026",
            "4": "062511",
            "5": "598723",
            "6": "770725",
            "7": "596337",
            "8": "647211",
            "9": "294016",
            "10": "161051",
            "11": "886458"
        '''
        self.createTOTPToken("totp1", self.seed, timeStep=30)
        '''
        T0=44576428.686175205 (*30)
            "44576428": "33726427",
            "44576429": "84341529",
            "44576430": "35692495",
            "44576431": "70995873",
            "44576432": "12048114",
            "44576433": "06245460",
            "44576434": "10441015",
            "44576435": "50389782",
            "44576436": "78905052",
            "44576437": "52978758",
            "44576438": "90386435",
            "44576439": "76892112"
        
        '''

        resp = self.setTokenRealm("dpw1", "mydefrealm")
        print resp
        assert '"status": true' in resp

        resp = self.setTokenRealm("hotp1", "mydefrealm")
        print resp
        assert '"status": true' in resp

        resp = self.setTokenRealm("totp1", "mydefrealm")
        print resp
        assert '"status": true' in resp

        resp = self.app.get(url(controller='admin', action='assign'), { 'user':'localuser', 'serial':'totp1' })
        assert '"status": true' in resp

        #parameters = {'user' : 'root',
        #              'serial' : 'totp1' }
        parameters = {}
        resp = self.app.get(url(controller='system', action='getRealms'), params=parameters)
        print "getRealms: ", resp
        assert '"status": true' in resp

        parameters = { 'name' : 'getmultitoken',
                       'scope' : 'gettoken',
                       'realm' : 'mydefrealm',
                       'action' : 'max_count_dpw=10, max_count_hotp=10, max_count_totp=10',
                       'user' : 'admin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        print "setPolicy:" , response
        assert '"status": true' in response
        
        response = self.app.get(url(controller='system', action='getPolicy'), params=parameters)
        print "getPolicy:" , response
        assert '"getmultitoken": {' in response

        response = self.app.get(url(controller='system', action='getConfig'), params={})
        print "config", response
        assert '"status": true' in response


    def test_01_getotp_dpw(self):
        '''
        test for the correct otp value of the DPW token
        '''
        parameters = {'serial' : 'dpw1',
                      'curTime' : self.curTime,
                      'selftest_admin' : 'admin' }
        response = self.app.get(url(controller='gettoken', action='getotp'), params=parameters)
        print "current time %s" % self.curTime
        print response
        assert '"otpval": "427701"' in response


    def test_03_getmultiotp(self):
        '''
        test for the correct otp value of the DPW token
        '''
        parameters = {'serial' : 'dpw1',
                      'curTime' : self.curTime,
                      'count' : "10",
                      'selftest_admin' : 'admin' }
        response = self.app.get(url(controller='gettoken', action='getmultiotp'), params=parameters)
        print response
        assert '"12-05-17": "028193"' in response
        assert '"12-05-18": "857788"' in response

    def test_05_getotp_hotp(self):
        '''
        test for the correct otp value of the HOTP token
        '''
        parameters = {'serial' : 'hotp1' }
        response = self.app.get(url(controller='gettoken', action='getotp'), params=parameters)
        print response
        assert '"otpval": "819132"' in response

    def test_06_getmultiotp(self):
        '''
        test for the correct otp value of the HOTP token
        '''
        parameters = {'serial' : 'hotp1',
                      'curTime' : self.curTime,
                      'count' : "20",
                      'selftest_admin' : 'admin' }
        response = self.app.get(url(controller='gettoken', action='getmultiotp'), params=parameters)
        print response
        assert '"0": "819132"' in response
        assert '"1": "301156"' in response


    def test_07_getotp_totp(self):
        '''
        test for the correct otp value of the TOTP token
        
        
          +-------------+--------------+------------------+----------+--------+
          |  Time (sec) |   UTC Time   | Value of T (hex) |   TOTP   |  Mode  |
          +-------------+--------------+------------------+----------+--------+
          |      59     |  1970-01-01  | 0000000000000001 | 94287082 |  SHA1  |
          |             |   00:00:59   |                  |          |        |
          |  1111111109 |  2005-03-18  | 00000000023523EC | 07081804 |  SHA1  |1111107509
          |             |   01:58:29   |                  |          |        |
          |  1111111111 |  2005-03-18  | 00000000023523ED | 14050471 |  SHA1  |
          |             |   01:58:31   |                  |          |        |
          |  1234567890 |  2009-02-13  | 000000000273EF07 | 89005924 |  SHA1  |
          |             |   23:31:30   |                  |          |        |
          |  2000000000 |  2033-05-18  | 0000000003F940AA | 69279037 |  SHA1  |
          |             |   03:33:20   |                  |          |        |
          | 20000000000 |  2603-10-11  | 0000000027BC86AA | 65353130 |  SHA1  |
          |             |   11:33:20   |                  |          |        |        
        
        '''
        cTimes = [('1970-01-01 00:00:59', '94287082'), ('2005-03-18 01:58:29', '07081804'),
                  ('2005-03-18 01:58:31', '14050471'), ('2009-02-13 23:31:30', '89005924'),
                  ('2033-05-18 03:33:20', '69279037'),
                 ]
        for cTime in cTimes:
            TOTPcurTime = cTime[0]
            otp = cTime[1]

            parameters = {'serial' : 'totp1',
                          'curTime' : TOTPcurTime }
            response = self.app.get(url(controller='gettoken', action='getotp'), params=parameters)
            print response
            assert otp in response

        return

    def test_08_getmultiotp(self):
        '''
        test for the correct otp value of the TOTP token
        '''
        parameters = {'serial' : 'totp1',
                      'timestamp' : self.TOTPTimestamp,
                      'count' : "20",
                      'selftest_admin' : 'admin' }
        response = self.app.get(url(controller='gettoken', action='getmultiotp'), params=parameters)
        print response
        resp = loads(response.body)
        otps = resp.get('result').get('value').get('otp')

        otp1 = otps.get('44576429')
        assert otp1.get('otpval') == '36163821'

        otp2 = otps.get('44576430')
        assert otp2.get('otpval') == '58711820'

        return

    def test_09_usergetmultiotp_no_policy(self):
        '''
        test for the correct OTP value for a users own token with missing policy
        '''
        parameters = {'serial' : 'totp1',
                      'timestamp' : self.TOTPTimestamp,
                      'count' : "20",
                      'selftest_user' : 'localuser@mydefrealm' }
        response = self.app.get(url(controller='selfservice', action='usergetmultiotp'), params=parameters)
        print "test_09: ", response
        assert '"message": "ERR410:' in response


    def test_10_usergetmultiotp(self):
        '''
        test for the correct OTP value for a users own token
        '''
        parameters = { 'name' : 'usertoken',
                       'scope' : 'selfservice',
                       'realm' : 'mydefrealm',
                       'action' : 'max_count_dpw=10, max_count_hotp=10, max_count_totp=10'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        print "setPolicy:" , response
        assert '"status": true' in response

        parameters = {'serial' : 'totp1',
                      'timestamp' : self.TOTPTimestamp,
                      'count' : "20",
                      'selftest_user' : 'localuser@mydefrealm' }
        response = self.app.get(url(controller='selfservice', action='usergetmultiotp'), params=parameters)
        print response

        resp = loads(response.body)
        otps = resp.get('result').get('value').get('otp')

        otp1 = otps.get('44576428')
        assert otp1.get('otpval') == '85291609'

        otp2 = otps.get('44576437')
        assert otp2.get('otpval') == '74602968'

        return

    def test_11_usergetmultiotp_fail(self):
        '''
        test for the correct OTP value for a  token that does not belong to the user
        '''
        parameters = {'serial' : 'hotp1',
                      'timestamp' : self.TOTPTimestamp,
                      'count' : "20",
                      'selftest_user' : 'localuser@mydefrealm' }
        response = self.app.get(url(controller='selfservice', action='usergetmultiotp'), params=parameters)
        print response
        assert '"message": "The serial hotp1 does not belong to user localuser@mydefrealm"' in response

