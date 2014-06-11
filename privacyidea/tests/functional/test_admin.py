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
Description:  funcitonal tests
                
Dependencies: -
'''

import logging
from privacyidea.tests import TestController, url

log = logging.getLogger(__name__)

class TestAdminController(TestController):


    def createToken3(self):
        parameters = {
                      "serial": "003e808e",
                      "otpkey" : "e56eb2bcbafb2eea9bce9463f550f86d587d6c71",
                      "description" : "my EToken",
                      }

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        self.assertTrue('"value": true' in response, response)

    def createToken2(self, serial="F722362"):
        parameters = {
                      "serial"  : serial,
                      "otpkey"  : "AD8EABE235FC57C815B26CEF3709075580B44738",
                      "description" : "TestToken" + serial,
                      }

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        self.assertTrue('"value": true' in response, response)
        return serial

    def createTokenSHA256(self, serial="SHA256"):
        parameters = {
                      "serial" : serial,
                      "otpkey" : "47F6EE05C06FA1CDB8B9AADF520FCF86221DB0A107731452AE140EED0EB518B0",
                      "type" : "hmac",
                      "hashlib" : "sha256"
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        self.assertTrue('"value": true' in response, response)
        return serial

    def createToken(self):
        parameters = {
                      "serial"  : "F722362",
                      "otpkey"  : "AD8EABE235FC57C815B26CEF3709075580B44738",
                      "user"    : "root",
                      "pin"     : "pin",
                      "description" : "TestToken1",
                      }

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        self.assertTrue('"value": true' in response, response)

        parameters = {
                      "serial": "F722363",
                      "otpkey" : "AD8EABE235FC57C815B26CEF3709075580B4473880B44738",
                      "user" : "root",
                      "pin": "pin",
                      "description" : "TestToken2",
                      }

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        self.assertTrue('"value": true' in response, response)

        parameters = {
                      "serial": "F722364",
                      "otpkey" : "AD8EABE235FC57C815B26CEF37090755",
                      "user" : "root",
                      "pin": "pin",
                      "description" : "TestToken3",
                      }

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        self.assertTrue('"value": true' in response, response)

        ## test the update
        parameters = {
                      "serial": "F722364",
                      "otpkey" : "AD8EABE235FC57C815B26CEF37090755",
                      "user" : "root",
                      "pin": "Pin3",
                      "description" : "TestToken3",
                      }

        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        #log.error("response %s\n",response)
        self.assertTrue('"value": true' in response, response)

    def removeTokenBySerial(self, serial):

        parameters = {
                      "serial": serial,
                      }

        response = self.app.get(url(controller='admin', action='remove'), params=parameters)
        return response

    def removeTokenByUser(self, user):
        ### final delete all tokens of user root
        parameters = {
                      "user": user,
                      }

        response = self.app.get(url(controller='admin', action='remove'), params=parameters)
        return response


    def showToken(self):
        response = self.app.get(url(controller='admin', action='show'))
        return response

    def test_0000_000(self):
        self.deleteAllTokens()

    def test_set(self):
        self.createToken()

        parameters = {
                      "serial": "F722364",
                      "pin": "pin",
                      "MaxFailCount" : "20",
                      "SyncWindow" : "400",
                      "OtpLen" : "6",
                      "hashlib" : "sha256"
                      }

        response = self.app.get(url(controller='admin', action='set'), params=parameters)
        #log.debug("response %s",response)
        self.assertTrue('"set pin": 1' in response, response)
        self.assertTrue('"set SyncWindow": 1' in response, response)
        self.assertTrue('"set OtpLen": 1' in response, response)
        self.assertTrue('"set MaxFailCount": 1' in response, response)
        self.assertTrue('"set hashlib": 1' in response, response)

        parameters = {
                      "user": "root",
                      "pin": "pin",
                      "MaxFailCount" : "20",
                      "SyncWindow" : "400",
                      "OtpLen" : "6",
                      }

        response = self.app.get(url(controller='admin', action='set'), params=parameters)
        #log.error("response %s",response)
        self.assertTrue('"set pin": 3' in response, response)
        self.assertTrue('"set SyncWindow": 3' in response, response)
        self.assertTrue('"set OtpLen": 3' in response, response)
        self.assertTrue('"set MaxFailCount": 3' in response, response)

        response = self.removeTokenBySerial("F722362")
        self.assertTrue('"value": 1' in response, response)
        response = self.removeTokenByUser("root")
        self.assertTrue('"value": 2' in response, response)


    def test_remove(self):
        self.createToken()
        response = self.removeTokenByUser("root")
        log.debug(response)

    def test_enable(self):
        self.createToken()
        parameters = {"serial": "F722364"}
        response = self.app.get(url(controller='admin', action='disable'), params=parameters)
        self.assertTrue('"value": 1' in response, response)

        parameters = {"serial": "F722364"}
        response = self.app.get(url(controller='admin', action='show'), params=parameters)

        self.assertTrue('false' in response, response)
        self.assertTrue('F722364' in response, response)

        parameters = {"serial": "F722364"}
        response = self.app.get(url(controller='admin', action='enable'), params=parameters)
        self.assertTrue('"value": 1' in response, response)

        parameters = {"serial": "F722364"}
        response = self.app.get(url(controller='admin', action='show'), params=parameters)

        self.assertTrue('true' in response, response)
        self.assertTrue('F722364' in response, response)

        self.removeTokenByUser("root")
        
    def test_show_csv(self):
        '''
        testing token csv export 
        '''
        response = self.app.get(url(controller='admin', action='show'), params={"outform" : "csv"})
        print response.headers
        assert response.headers.get("Content-Disposition") == "attachment; filename=privacyidea-tokendata.csv"


    def test_show_with_realm(self):
        '''
        testing admin/show with filterrealm
        '''
        response = self.app.get(url(controller='system', action='getRealms'), params=None)
        self.assertTrue("mydefrealm" in response, response)
        
        response = self.app.get(url(controller='admin', action='show'), params={"viewrealm" : "mydefrealm"})
        self.assertTrue('"status": true,' in response, response)
        
    def test_token_realm(self):
        '''
        testing setting the tokenrealm
        '''
        response = self.app.get(url(controller="admin", action="init"), params={"serial" : "TR_001",
                                                                                "type" : "spass"})
        self.assertTrue('"status": true,' in response, response)
        
        # successful set token realm
        response = self.app.get(url(controller="admin", action="tokenrealm"), params={"serial" : "TR_001",
                                                                                "realms" : "mydefrealm, myotherrealm"})
        self.assertTrue('"status": true,' in response, response)
        
        # set tokenrealm of token, that does not exist.
        response = self.app.get(url(controller="admin", action="tokenrealm"), params={"serial" : "TR_001XXX",
                                                                                "realms" : "mydefrealm, myotherrealm"})
        self.assertTrue('No token with serial TR_001XXX found' in response, response)
        
    def test_reset(self):
        response = self.app.get(url(controller="admin", action="init"), params={"serial" : "RE_001",
                                                                                "type" : "hmac",
                                                                                "otpkey" : "123456123456123456"})
        self.assertTrue('"status": true,' in response, response)
        
        response = self.app.get(url(controller="admin", action="reset"), params={"serial" : "RE_001"})
        self.assertTrue('"status": true,' in response, response)
        self.assertTrue('"value": 1' in response, response)
        
        response = self.app.get(url(controller="admin", action="reset"), params={"serial" : "RE_001XXXX"})
        self.assertTrue('"status": true,' in response, response)
        self.assertTrue('"value": 0' in response, response)
        
        
    def test_losttoken(self):
        response = self.app.get(url(controller="admin", action="init"), params={"serial" : "LOST_001",
                                                                                "type" : "hmac",
                                                                                "otpkey" : "123456123456123456"})
        self.assertTrue('"status": true,' in response, response)
        
        response = self.app.get(url(controller="admin", action="losttoken"), params={"serial" : "LOST_001"})
        self.assertTrue('"status": false,' in response, response)
        self.assertTrue('You can only define a lost token for an assigned token.' in response, response)
        
        response = self.app.get(url(controller="admin", action="assign"), params={"serial" : "LOST_001",
                                                                                  "user" : "root"})
        self.assertTrue('"status": true,' in response, response)
        
        response = self.app.get(url(controller="admin", action="losttoken"), params={"serial" : "LOST_001"})
        self.assertTrue('"serial": "lostLOST_001",' in response, response)
        self.assertTrue('"password": "' in response, response)
        
        response = self.app.get(url(controller="admin", action="unassign"), params={"serial" : "LOST_001"})
        self.assertTrue('"status": true,' in response, response)
        
        response = self.app.get(url(controller="admin", action="remove"), params={"serial" : "LOST_001"})
        self.assertTrue('"status": true,' in response, response)
        
    def test_userlist(self):
        response = self.app.get(url(controller='admin', action='userlist'), params={"username" : "*"})
        self.assertTrue("passthru_user2" in response, response)
        self.assertTrue("passthru_user1" in response, response)
        self.assertTrue("remoteuser" in response, response)
        self.assertTrue("user1" in response, response)
        self.assertTrue("user2" in response, response)
        

    def test_resync(self):

        self.createToken()

        ## test resync of token 2
        parameters = {"user": "root", "otp1": "359864", "otp2": "348449" }
        response = self.app.get(url(controller='admin', action='resync'), params=parameters)
        #log.error("response %s\n",response)
        self.assertTrue('"value": false' in response, response)


        parameters = {"user": "root", "otp1": "359864", "otp2": "348448" }
        response = self.app.get(url(controller='admin', action='resync'), params=parameters)
        # Test response...
        log.error("response %s\n", response)
        self.assertTrue('"value": true' in response, response)


        self.removeTokenBySerial("F722364")
        self.removeTokenBySerial("F722363")
        self.removeTokenBySerial("F722362")

    def test_resync_sha256(self):
        self.createTokenSHA256(serial="SHA256")

        parameters = {"serial":"SHA256", "otp1":"778729" , "otp2":"094573" }
        response = self.app.get(url(controller="admin", action="resync"), params=parameters)

        self.assertTrue('"value": true' in response, response)
        self.removeTokenBySerial("SHA256")


    def test_setPin(self):
        self.createToken3()

        ## test resync of token 2
        parameters = {"serial":"003e808e", "userpin":"123456", "sopin":"123234" }
        response = self.app.get(url(controller='admin', action='setPin'), params=parameters)
        # log.error("response %s\n",response)
        # Test response...
        self.assertTrue('"set sopin": 1' in response, response)
        self.assertTrue('"set userpin": 1' in response, response)

        self.removeTokenBySerial("003e808e")


    def test_assign(self):

        serial = self.createToken2(serial="F722362")

        response = self.app.get(url(controller='admin', action='show'))


        respRealms = self.app.get(url(controller='system', action='getRealms'), params=None)
        log.debug(respRealms)

        ## test initial assign
        parameters = {"serial":serial, "user": "root" }
        response = self.app.get(url(controller='admin', action='assign'), params=parameters)
        # log.error("response %s\n",response)
        # Test response...
        self.assertTrue('"value": true' in response, response)

        ## test initial assign update
        parameters = {"serial": serial, "user": "root", "pin":"NewPin" }
        response = self.app.get(url(controller='admin', action='assign'), params=parameters)
        #log.error("response %s\n",response)
        # Test response...
        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='show'))
        #log.error("response %s\n",response)
        self.assertTrue('"User.userid": "0", ' in response, response)


        ## test initial assign update
        parameters = {"serial": serial , "user": "root"}
        response = self.app.get(url(controller='admin', action='unassign'), params=parameters)
        #log.error("response %s\n",response)
        self.assertTrue('"value": true' in response, response)

        ## test wrong assign
        parameters = {"serial": serial, "user": "NoBody" }
        response = self.app.get(url(controller='admin', action='assign'), params=parameters)
        #log.error("response %s\n",response)
        self.assertTrue('getUserId failed: no user >NoBody< found!' in response, response)

        response = self.app.get(url(controller='admin', action='show'))
        #log.error("response %s\n",response)
        self.assertTrue('"User.userid": "",' in response, response)



        self.removeTokenBySerial(serial)

    def test_assign_umlaut(self):
        self.createTokenSHA256(serial="umlauttoken")

        parameters = {"serial":"umlauttoken", "user":"kölbel" }
        response = self.app.get(url(controller="admin", action="assign"), params=parameters)

        self.assertTrue('"value": true' in response, response)

        self.removeTokenBySerial("umlauttoken")

    def test_enroll_umlaut(self):

        parameters = {
                      "serial" : "umlauttoken",
                      "otpkey" : "47F6EE05C06FA1CDB8B9AADF520FCF86221DB0A107731452AE140EED0EB518B0",
                      "type" : "hmac",
                      "hashlib" : "sha256",
                      "user" : "kölbel"
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        self.assertTrue('"value": true' in response, response)
        self.removeTokenBySerial("umlauttoken")

    def test_login(self):
        '''
        Testing login and logout
        account/dologin?login=corny%40r2&realm=r1&password=test
        '''
        
        response = self.app.get("http://localhost:5001/account/dologin",
                                params={'login': 'admin2@admin',
                                        'realm':'',
                                        'password':'secret'})
        
        self.assertTrue('302 Found' in response.body, response.body)
        self.assertTrue('you should be redirected automatically.' in response.body, response.body)
        
        response = self.app.get("http://localhost:5001/account/logout",
                                params={})

        print response.body
        self.assertTrue('302 Found' in response.body, response.body)
        self.assertTrue('you should be redirected automatically.' in response.body, response.body)


    def test_check_serial(self):
        '''
        Checking what happens if serial exists
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={"serial" : 'unique_serial_001',
                                        "type" : 'spass'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='check_serial'),
                                params={'serial' : 'unique_serial_002'})

        self.assertTrue('"unique": true' in response, response)
        self.assertTrue('"new_serial": "unique_serial_002"' in response, response)

        response = self.app.get(url(controller='admin', action='check_serial'),
                                params={'serial' : 'unique_serial_001'})

        self.assertTrue('"unique": false' in response, response)
        self.assertTrue('"new_serial": "unique_serial_001_01"' in response, response)

    def test_setPin_empty(self):
        '''
        Testing setting empty PIN and SO PIN
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial': 'setpin_01',
                                        'type': 'spass'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='setPin'),
                                params={'serial': 'setpin_01'})

        self.assertTrue('"status": false' in response, response)
        self.assertTrue('"code": 77' in response, response)

        response = self.app.get(url(controller='admin', action='setPin'),
                                params={'serial': 'setpin_01',
                                        'sopin' : 'geheim'})


        self.assertTrue('"set sopin": 1' in response, response)

    def test_set_misc(self):
        '''
        Setting CountWindow, timeWindow, timeStep, timeShift
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial': 'token_set_misc',
                                        'type': 'spass'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='set'),
                                params={'serial': 'token_set_misc',
                                        'CounterWindow': '100',
                                        'timeWindow': '180',
                                        'timeStep': '30',
                                        'timeShift': '0'})


        self.assertTrue('set CounterWindow": 1' in response, response)
        self.assertTrue('"set timeShift": 1' in response, response)
        self.assertTrue('"set timeWindow": 1' in response, response)
        self.assertTrue('"set timeStep": 1' in response, response)

    def test_set_count(self):
        '''
        Setting countAuth, countAuthMax, countAuthSucces countAuthSuccessMax
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial': 'token_set_count',
                                        'type': 'spass'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='set'),
                                params={'serial': 'token_set_count',
                                        'countAuth': '10',
                                        'countAuthMax': '180',
                                        'countAuthSuccess': '0',
                                        'countAuthSuccessMax': '10'})


        self.assertTrue('"set countAuthSuccess": 1' in response, response)
        self.assertTrue('"set countAuthSuccessMax": 1' in response, response)
        self.assertTrue('"set countAuth": 1' in response, response)
        self.assertTrue('"set countAuthMax": 1' in response, response)

        return

    def test_set_validity(self):
        '''
        Setting validity period
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial': 'token_set_validity',
                                        'type': 'spass'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='set'),
                                params={'serial': 'token_set_validity',
                                        'validityPeriodStart': '2012-10-12',
                                        'validityPeriodEnd': '2013-12-30',
                                        })


        self.assertTrue('"status": false' in response, response)
        self.assertTrue('does not match format' in response, response)

        response = self.app.get(url(controller='admin', action='set'),
                                params={'serial': 'token_set_validity',
                                        'validityPeriodStart': '12/12/12 10:00',
                                        'validityPeriodEnd': '30/12/13 13:00',
                                        })


        self.assertTrue('"status": true' in response, response)
        self.assertTrue('"set validityPeriodStart": 1' in response, response)
        self.assertTrue('"set validityPeriodEnd": 1' in response, response)

    def test_set_empty(self):
        '''
        Running set without parameter
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial': 'token_set_empty',
                                        'type': 'spass'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='set'),
                                params={'serial': 'token_set_empty',
                                        })


        self.assertTrue('"status": false' in response, response)
        self.assertTrue('"code": 77' in response, response)


    def test_copy_token_pin(self):
        '''
        testing copyTokenPin

        We create one token with a PIN and authenticate.
        Then we copy the PIN to another token and try to authenticate.
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial': 'copy_token_1',
                                        'type': 'spass',
                                        'pin': '1234'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='validate', action='check_s'),
                                params={'serial': 'copy_token_1',
                                        'pass': '1234'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial': 'copy_token_2',
                                        'type': 'spass',
                                        'pin': 'otherPassword'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='validate', action='check_s'),
                                params={'serial': 'copy_token_2',
                                        'pass': 'otherPassword'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='copyTokenPin'),
                                params={'from': 'copy_token_1',
                                        'to': 'copy_token_2'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='validate', action='check_s'),
                                params={'serial': 'copy_token_2',
                                        'pass': '1234'})

        self.assertTrue('"value": true' in response, response)

    def test_copy_token_user(self):
        '''
        testing copyTokenUser
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial': 'copy_user_1',
                                        'type': 'spass',
                                        'pin': 'copyTokenUser',
                                        'user': 'root'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='validate', action='check'),
                                params={'user': 'root',
                                        'pass': 'copyTokenUser'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial': 'copy_user_2',
                                        'type': 'spass',
                                        'pin': 'unknownSecret'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='copyTokenUser'),
                                params={'from': 'copy_user_1',
                                        'to': 'copy_user_2'})

        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='validate', action='check'),
                                params={'user': 'root',
                                        'pass': 'unknownSecret'})

        self.assertTrue('"value": true' in response, response)

    def test_enroll_token_twice(self):
        '''
        test to enroll another token with the same serial number
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial' : 'token01',
                                        'type' : 'hmac',
                                        'otpkey' : '123456'})

        self.assertTrue('"value": true' in response, response)

        # enrolling the token of the same type is possible
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial' : 'token01',
                                        'type' : 'hmac',
                                        'otpkey' : '567890'})

        self.assertTrue('"value": true' in response, response)

        # enrolling of another type is not possible
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial' : 'token01',
                                        'type' : 'spass',
                                        'otpkey' : '123456'})

        self.assertTrue("already exist with type" in response, response)
        self.assertTrue("Can not initialize token with new type" in response, response)

        # clean up
        response = self.app.get(url(controller='admin', action='remove'),
                                params={'serial' : 'token01'})

        self.assertTrue('"status": true' in response, response)

    def test_serial_by_otp(self):
        '''
        Test gettoken/multiotp and admin/getSerialByOtp
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial' : 'gsbo001',
                                        'type' : 'hmac',
                                        'otpkey' : '12345678901234567890123456789012',
                                        'user' : 'root',
                                        'selftest_admin' : 'superadmin'})
        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='system', action='setPolicy'),
                                params={'name' : 'gettoken',
                                        'scope' : 'gettoken',
                                        'realm' : 'myDefRealm',
                                        'action' : 'max_count_hotp=20'})
        self.assertTrue('"setPolicy gettoken"' in response, response)
        
        response = self.app.get(url(controller='gettoken', action='getmultiotp'),
                                params={'serial' : 'gsbo001',
                                        'count' : '10'})
        self.assertTrue('"3": "180096"' in response, response)
        
        response = self.app.get(url(controller='admin', action='getSerialByOtp'),
                                params={'otp' : '180096'})
        self.assertTrue('"serial": "gsbo001"' in response, response)
        
        response = self.app.get(url(controller='admin', action='remove'),
                                params={'serial' : 'gsbo001'})
        self.assertTrue('"value": 1' in response, response)
        

    def test_setting_description(self):
        '''
        Test setting the description and phone of a token
        '''
        response = self.app.get(url(controller='admin', action='init'),
                                params={'serial' : 'desc001',
                                        'type' : 'hmac',
                                        'otpkey' : '12345678901234567890123456789012',
                                        'selftest_admin' : 'superadmin'})
        self.assertTrue('"value": true' in response, response)
        
        response = self.app.get(url(controller='admin', action='set'),
                                params={'serial' : 'desc001',
                                        'description' : 'something',
                                        'phone' : '1234560'})
        
        self.assertTrue('"set description": 1' in response, response)
        self.assertTrue('"set phone": 1' in response, response)
        
        response = self.app.get(url(controller='admin', action='show'),
                                params={'serial' : 'desc001'})
        self.assertTrue('phone' in response, response)
        self.assertTrue('1234560' in response, response)
        self.assertTrue('TokenDesc": "something"' in response, response)

        response = self.app.get(url(controller='admin', action='remove'),
                                params={'serial' : 'desc001'})
        self.assertTrue('"value": 1' in response, response)
        
    def test_load_tokens(self):
        '''
        '''