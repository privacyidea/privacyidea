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

import logging

import datetime

from privacyidea.tests import TestController, url


log = logging.getLogger(__name__)

class TestAuthorizeController(TestController):
    '''
    This test tests the authorization policies

    scope: authorization
    action: authorize
    realm:
    user:
    client:

        /validate/check
        /validate/simplecheck
        get_multi_otp
    '''


    def setUp(self):
        '''
        This sets up all the resolvers and realms
        '''
        TestController.setUp(self)
        self.curTime = datetime.datetime(2012, 5, 16, 9, 0, 52, 227413)
        self.TOTPcurTime = datetime.datetime.fromtimestamp(1337292860.585256)
        self.initToken()


    ###############################################################################

    def createPWToken(self, serial, pin="", pw=""):
        '''
        creates the test tokens
        '''
        parameters = {
                          "serial"  : serial,
                          "type"    : "PW",
                          # 64 byte key
                          "otpkey"  : pw,
                          "otppin"  : pin,
                          "otplen"  : len(pw),
                          "description" : "PW testtoken",
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

    def delPolicy(self, name):

        response = self.app.get(url(controller="system", action="delPolicy"),
                               params={"name": name})
        print "delPolicy:" , response
        assert '"status": true' in response

    def setPolicy(self, parameters):
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        print "setPolicy:" , response
        assert '"status": true' in response
        # check for policy
        response = self.app.get(url(controller='system', action='getPolicy'), params=parameters)
        print "getPolicy:", response
        assert '"action": ' in response

    def initToken(self):
        '''
        init one DPW token
        '''

        self.createPWToken("pw1", pin="1234", pw="secret1")
        resp = self.app.get(url(controller='admin', action='assign'), { 'user':'localuser', 'serial':'pw1' })
        assert '"status": true' in resp
        resp = self.app.get(url(controller='admin', action='set'), { 'pin':'1234', 'serial':'pw1' })
        assert '"status": true' in resp


        self.createPWToken("pw2", pin="1234", pw="secret2")
        resp = self.app.get(url(controller='admin', action='assign'), { 'user':'horst', 'serial':'pw2' })
        assert '"status": true' in resp
        resp = self.app.get(url(controller='admin', action='set'), { 'pin':'1234', 'serial':'pw2' })
        assert '"status": true' in resp

    def create_policy(self):
        '''
        create the policy
        '''
        response = self.app.get(url(controller="system", action="setConfig"), params={"mayOverwriteClient" : None})
        print "setConfig:" , response
        assert '"status": true' in response

        parameters1 = { 'name' : 'authorization1',
                       'scope' : 'authorization',
                       'realm' : '*',
                       'action' : 'authorize',
                       'user' : 'localuser',
                       'client' : '172.16.200.0/24'
                      }
        self.setPolicy(parameters1)


    def create_policy2(self):
        '''
        create the policy
        '''
        response = self.app.get(url(controller="system", action="setConfig"),
                                params={"mayOverwriteClient" : None})
        print "setConfig:" , response
        assert '"status": true' in response

        parameters1 = { 'name' : 'authorization1',
                       'scope' : 'authorization',
                       'realm' : '*',
                       'action' : 'authorize',
                       'user' : 'horst',
                       'client' : '172.16.200.0/24'
                      }
        self.setPolicy(parameters1)


    def create_policy3(self):
        '''
        create the policy
        '''
        response = self.app.get(url(controller="system", action="setConfig"), params={"mayOverwriteClient" : None})
        print "setConfig:" , response
        assert '"status": true' in response

        parameters1 = { 'name' : 'authorization1',
                       'scope' : 'authorization',
                       'realm' : '*',
                       'action' : 'authorize',
                       'user' : '',
                       'client' : '10.0.0.0/8'
                      }
        self.setPolicy(parameters1)


    def test_00_localuser_allowed(self):
        '''
        Auth Test 00: Without policy the user is authorized to login
        '''
        parameters = {'user' : 'localuser',
                      'pass' : '1234secret1',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response

    def test_00_horst_allowed(self):
        '''
        Auth Test 00: without policy the user is allowed
        '''
        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response


    def test_01_localuser_allowed(self):
        '''
        Auth Test 01: test if localuser is allowed to authenticate
        '''
        self.create_policy()

        parameters = {'user' : 'localuser',
                      'pass' : '1234secret1',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response

    def test_02_horst_not_allowed(self):
        '''
        Auth Test 02: test if horst is not allowed to authenticate. horst is not authorized, since he is not mentioned in the policy1 as user.
        '''
        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": false' in response

    def test_03_localuser_not_allowed(self):
        '''
        Auth Test 03: localuser is not allowed to authenticate to another host than 172.16.200.X
        localuser is not authorized, since he tries to login to 10.1.1.3
        '''
        parameters = {'user' : 'localuser',
                      'pass' : '1234secret1',
                      'client' : '10.1.1.3' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": false' in response

    def test_04_horst_allowed(self):
        '''
        Auth Test 04: Now we set a new policy, and horst should be allowed
        '''
        self.create_policy2()

        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response

    def test_05_blank_user(self):
        '''
        Auth Test 05: test if blank users are working for all users
        '''
        self.create_policy3()

        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'client' : '10.0.1.2' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response


# ############################################################################
#
# PIN Policy tests
#
#There are two users in def-passwd:
#    localuser -> password test123
#    horst    -> password test123


    def test_06_pinpolicy(self):
        '''
        Auth Test 06: check a client policy with password PIN on one client
        '''

        #deleting authorization policy
        self.delPolicy("authorization1")

        # setting pin policy
        parameters = { 'name' : 'pinpolicy1',
                       'scope' : 'authentication',
                       'realm' : '*',
                       'action' : 'otppin=1',
                       'user' : '',
                       'client' : '10.0.0.0/8'
                      }

        self.setPolicy(parameters)


        parameters = {'user' : 'horst',
                      'pass' : 'test123secret2',
                      'client' : '10.0.1.2' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response

    def test_07_pinpolicy(self):
        '''
        Auth Test 07: check on a client, that is not contained in policy => authenticate with OTP PIN
        '''

        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'client' : '192.168.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response

    def test_08_pinpolicy(self):
        '''
        Auth Test 08: check user on client, but user not contained in policy for this client => authenticate with OTP PIN
        '''
        parameters = { 'name' : 'pinpolicy2',
                       'scope' : 'authentication',
                       'realm' : '*',
                       'action' : 'otppin=1',
                       'user' : 'horst',
                       'client' : '172.16.200.0/8'
                      }
        self.setPolicy(parameters)

        parameters = {'user' : 'localuser',
                      'pass' : '1234secret1',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response

##############################################################################################
#
# Toke Type tests
#
    def test_10_tokentype(self):
        '''
        Auth Test 10: client not in policy. So every tokentype should be able to authenticate
        '''
        # clear pin policy
        self.delPolicy("pinpolicy1")
        self.delPolicy("pinpolicy2")
        #
        #
        #
        parameters = { 'name' : 'tokentypepolicy1',
                       'scope' : 'authorization',
                       'realm' : '*',
                       'action' : 'tokentype=HMAC',
                       'user' : 'horst',
                       'client' : '172.16.200.0/24'
                      }
        self.setPolicy(parameters)


        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'client' : '10.0.0.2' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response


    def test_11_tokentype(self):
        '''
        Auth Test 11: Tokentype policy contains list of tokentypes. A token is allowed to authenticate
        '''
        parameters = { 'name' : 'tokentypepolicy1',
                       'scope' : 'authorization',
                       'realm' : '*',
                       'action' : 'tokentype=HMAC MOTP PW',
                       'user' : 'horst',
                       'client' : '172.16.200.0/24'
                      }
        self.setPolicy(parameters)


        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response

    def test_12_tokentype(self):
        '''
        Auth Test 12: Tokentype policy contains list of tokentypes. the tokentype is not contained and not allowed to authenticate
        '''
        parameters = { 'name' : 'tokentypepolicy1',
                       'scope' : 'authorization',
                       'realm' : '*',
                       'action' : 'tokentype=HMAC MOTP TOTP',
                       'user' : 'horst',
                       'client' : '172.16.200.0/24'
                      }
        self.setPolicy(parameters)


        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": false' in response

    def test_13_tokentype(self):
        '''
        Auth Test 13: Tokentype policy contains '*' and the token type is allowed to authenticate.
        '''
        parameters = { 'name' : 'tokentypepolicy1',
                       'scope' : 'authorization',
                       'realm' : '*',
                       'action' : 'tokentype=HMAC * TOTP MOTP',
                       'user' : 'horst',
                       'client' : '172.16.200.0/24'
                      }
        self.setPolicy(parameters)


        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='validate', action='check'), params=parameters)

        print "validate/check: ", response
        assert '"value": true' in response

        self.delPolicy("tokentypepolicy1")

##############################################################################################
#
# SMSText test
#
    def test_14_smstext(self):
        '''
        TODO: Testing policy for smstext
        '''
        pass

##############################################################################################
#
#  AutoSMS

    def test_20_autosms(self):
        '''
        Auth Test 20: autosms enabled with no client and no user. Will do for all clients in a realm
        '''
        # FIXME: When we can do sms, we need to enable this.
        return
        self.setPolicy({ 'name' : 'autosms',
                       'scope' : 'authentication',
                       'realm' : '*',
                       'action' : 'autosms',
                       'user' : None
                    })

        parameters = {'user' : 'horst',
                      'client' : '1.2.3.4' }
        response = self.app.get(url(controller='testing', action='autosms'), params=parameters)

        print "testing/autosms: ", response
        assert '"value": true' in response


    def test_21_autosms(self):
        '''
        Auth Test 21: autosms enabled for a client. Will send autosms for a client in the subnet
        '''
        return
        self.setPolicy({ 'name' : 'autosms',
                       'scope' : 'authentication',
                       'realm' : '*',
                       'action' : 'autosms',
                       'client' : '172.16.200.0/24'
                    })

        parameters = {'user' : 'horst',
                      'client' : '172.16.200.123' }
        response = self.app.get(url(controller='testing', action='autosms'), params=parameters)

        print "testing/autosms: ", response
        assert '"value": true' in response


    def test_22_autosms(self):
        '''
        Auth Test 22: autosms enabled for a client. Will not send autosms for a client outside this subnet
        '''
        return
        self.setPolicy({ 'name' : 'autosms',
                       'scope' : 'authentication',
                       'realm' : '*',
                       'action' : 'autosms',
                       'client' : '172.16.200.0/24'
                    })

        parameters = {'user' : 'horst',
                      'client' : '192.168.20.1' }
        response = self.app.get(url(controller='testing', action='autosms'), params=parameters)

        print "testing/autosms: ", response
        assert '"value": false' in response

    def test_23_autosms(self):
        '''
        Auth Test 23: autosms enabled for a client and for a user. Will send autosms for this user
        '''
        return
        self.setPolicy({ 'name' : 'autosms',
                       'scope' : 'authentication',
                       'realm' : '*',
                       'action' : 'autosms',
                       'client' : '172.16.200.0/24',
                       'user' : 'horst'
                    })

        parameters = {'user' : 'horst',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='testing', action='autosms'), params=parameters)

        print "testing/autosms: ", response
        assert '"value": true' in response

    def test_24_autosms(self):
        '''
        Auth Test 24: autosms enabled for a client and for a user. Will not send autosms for another user
        '''
        return
        self.setPolicy({ 'name' : 'autosms',
                       'scope' : 'authentication',
                       'realm' : '*',
                       'action' : 'autosms',
                       'client' : '172.16.200.0/24',
                       'user' : 'horst'
                    })

        parameters = {'user' : 'localuser',
                      'client' : '172.16.200.10' }
        response = self.app.get(url(controller='testing', action='autosms'), params=parameters)

        print "testing/autosms: ", response
        assert '"value": false' in response

###################################################################
#
#   set realm tests
#
    def test_31_setrealm(self):
        '''
        Auth Test 31: setrealm for a user in the not default realm.
        '''
        self.delPolicy("tokentypepolicy1")

        self.setPolicy({"name" : "setrealm",
                         "scope":"authorization",
                         "realm":"*",
                         "action":"setrealm=defRealm",
                         "client":"10.0.0.0/8"})
        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'realm' : 'realm_does_not_exist',
                      'client' : '10.0.0.1' }
        response = self.app.get(url(controller="validate", action="check"), params=parameters)
        print "31 setrealm : ", response
        assert '"value": true'

    def test_32_setrealm(self):
        '''
        Auth Test 32: setrealm for a user, but user provides wrong password
        '''
        parameters = {'user' : 'horst',
                      'pass' : '1234secret2xxxx',
                      'realm' : 'realm_does_not_exist',
                      'client' : '10.0.0.1' }
        response = self.app.get(url(controller="validate", action="check"), params=parameters)
        print "32 setrealm : ", response
        assert '"value": false'

    def test_33_setrealm(self):
        '''
        Auth Test 33: setrealm, but not for the right client
        '''
        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'realm' : 'realm_does_not_exist',
                      'client' : '172.0.0.1' }
        response = self.app.get(url(controller="validate", action="check"), params=parameters)
        print "33 setrealm : ", response
        assert '"value": false'

    def test_34_setrealm(self):
        '''
        Auth Test 34: setrealm, rewrite realm to a not existing realm. Auth will fail
        '''
        self.setPolicy({"name" : "setrealm",
                         "scope":"authorization",
                         "realm":"defRealm realm2 realm3",
                         "action":"setrealm=not_existing",
                         "client":"10.0.0.0/8"})

        parameters = {'user' : 'horst',
                      'pass' : '1234secret2',
                      'realm' : 'defRealm',
                      'client' : '10.0.0.1' }
        response = self.app.get(url(controller="validate", action="check"), params=parameters)
        print "34 setrealm : ", response
        assert '"value": false'

