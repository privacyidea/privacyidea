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
from privacyidea.tests import TestController, url
from privacyidea.lib.config import get_privacyIDEA_config
import re
from json import loads

log = logging.getLogger(__name__)

class TestPolicies(TestController):


    def setUp(self):
        '''
        Overwrite the deleting of the realms!

        If the realms are deleted also the table TokenRealm gets deleted and we loose the information
        how many tokens are within a realm!
        '''
        ## here we do the system test init per test method
        #self.__deleteAllRealms__()
        #self.__deleteAllResolvers__()
        #self.__createResolvers__()
        #self.__createRealms__()
        return

    def tearDown(self):
        ''' Overwrite parent tear down, which removes all realms '''
        return

    ### define Admins

    def test_00_init(self):
        '''
        Policy 00: Init the tests....
        '''
        self.__createResolvers__()
        self.__createRealms__()

    def test_01createPolicy_Super(self):
        '''
        Policy 01: create a policy for the superadmin
        '''
        parameters = { 'name' : 'ManageAll',
                       'scope' : 'admin',
                       'realm' : '*',
                       'action' : '*',
                       'user' : 'superadmin, Administrator',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

    def test_02getPolicy_Realm(self):
        '''
        Policy 02: create a policy for the realm admin
        '''
        parameters = { 'name' : 'ManageRealm1',
                       'scope' : 'admin',
                       'realm' : 'myDefRealm',
                       'action' : '*',
                       'user' : 'adminR1, adminR2',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

    def test_03getPolicy(self):
        '''
        Policy 03: Realm admin reads policies
        '''
        parameters = { 'selftest_admin' : 'adminR1'}
        response = self.app.get(url(controller='system', action='getPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

    ##### Define System access

    def test_04setPolicy_System(self):
        '''
        Policy 04: The superadmin is allowed to write to system and thus to set policies
        '''
        parameters = { 'name' : 'sysSuper',
                       'scope' : 'system',
                       'realm' : '*',
                       'action' : '*',
                       'user' : 'superadmin',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

    def test_05setPolicy_System(self):
        '''
        Policy 05: The realmAdmin is allowed to read the system config
        '''
        parameters = { 'name' : 'sysRealms1Admin',
                       'scope' : 'system',
                       'realm' : '*',
                       'action' : 'read',
                       'user' : 'adminR1',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

    def test_06setPolicy_System(self):
        """
        Policy 06: The adminEnroller is not allowed to read system
            obsolete, as this should happen implicit, as in test_05
            a system policy is already set and anybody else should now
            have no access to the system
        """

        parameters = { 'name': 'sysAdminEnroller',
                       'scope': 'system',
                       'realm': '*',
                       'action': '',
                       'user': 'adminEnroller',
                       'selftest_admin': 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'),
                                params=parameters)
        log.error(response)
        assert '"status": false' in response
        assert 'setPolicy failed: name and action required!' in response

        return

    def test_07a_setPolicy_w_empty_action(self):
        """
        Policy 07a: The setting of a policy with an empty action is not allowed
        """

        parameters = { 'name' : 'sysAdminEnroller',
                       'scope' : 'system',
                       'realm' : '*',
                       'action' : '',
                       'user' : 'adminEnroller',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": false' in response
        assert 'setPolicy failed: name and action required!' in response

        return

    #### now check the system rights
    def test_07checkPolicy_System(self):
        '''
        Policy 07: The realm Admin returns true, if he reads the system
        '''
        parameters = {
                       'selftest_admin' : 'adminR1'
                      }
        response = self.app.get(url(controller='system', action='getPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

    def test_08checkPolicy_System(self):
        '''
        Policy 08: The realm Admin returns false, if he tries to write to system
        '''
        parameters = { 'name' : 'sysXXX',
                       'scope' : 'system',
                       'realm' : '*',
                       'action' : '',
                       'user' : 'neuerAdmin',
                       'selftest_admin' : 'adminR1'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": false' in response

    def test_09checkPolicy_System(self):
        '''
        Policy 09: The enroller Admin returns false, if he tries to write to system
        '''
        parameters = { 'name' : 'sysXXX',
                       'scope' : 'system',
                       'realm' : '*',
                       'action' : '',
                       'user' : 'adminEnroller',
                       'selftest_admin' : 'adminEnroller'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": false' in response

    def test_10checkPolicy_System(self):
        '''
        Policy 10: The enroller Admin returns false, if he tries to read to system
        '''
        parameters = {
                       'selftest_admin' : 'adminEnroller'
                      }
        response = self.app.get(url(controller='system', action='getPolicy'), params=parameters)
        log.error(response)
        assert '"status": false' in response


    ##### define admin access
    '''
    Here we need to define admin rights and test the admin rights
    '''
    def test_201_setPolicy(self):
        '''
        Policy 201: creating all the administrators (scope admin) with all necessary policies.
        '''
        # one administrator for initialize
        parameters = { 'name' : 'adm201',
                       'scope' : 'admin',
                       'realm' : '*',
                       'action' : 'initSPASS, initHMAC, initETNG, initSMS, initMOTP',
                       'user' : 'admin_init',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response
        # one administrator for enabling and disabling
        parameters = { 'name' : 'adm201a',
                       'scope' : 'admin',
                       'realm' : '*',
                       'action' : 'enable, disable',
                       'user' : 'admin_enable_disable',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        # one administrator for setting
        parameters = { 'name' : 'adm201b',
                       'scope' : 'admin',
                       'realm' : '*',
                       'action' : 'set',
                       'user' : 'admin_set',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        # one administrator for setting
        parameters = { 'name' : 'adm201c',
                       'scope' : 'admin',
                       'realm' : '*',
                       'action' : 'setOTPPIN, setMOTPPIN, setSCPIN',
                       'user' : 'admin_setpin',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        # one administrator for resyncing
        parameters = { 'name' : 'adm201d',
                       'scope' : 'admin',
                       'realm' : '*',
                       'action' : 'resync',
                       'user' : 'admin_resync',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        # one administrator for resetting
        parameters = { 'name' : 'adm201e',
                       'scope' : 'admin',
                       'realm' : '*',
                       'action' : 'reset',
                       'user' : 'admin_reset',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        # one administrator for removing
        parameters = { 'name' : 'adm201f',
                       'scope' : 'admin',
                       'realm' : '*',
                       'action' : 'remove',
                       'user' : 'admin_remove',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        # one administrator for removing
        parameters = { 'name' : 'adm201g',
                       'scope' : 'admin',
                       'realm' : '*',
                       'action' : 'assign, unassign',
                       'user' : 'admin_assign_unassign',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response


    def test_202_initToken(self):
        '''
        Policy 202: Init tokens in different with different admins. "admin_init" is allowed to do so, "admin_reset" not.
        '''
        parameters = { 'serial' : 'cko_test_001',
                       'type' : 'spass',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        parameters = { 'serial' : 'cko_test_003',
                       'type' : 'spass',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        parameters = { 'serial' : 'cko_test_002',
                       'type' : 'spass',
                       'selftest_admin' : 'admin_reset'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert '"status": false' in response


    def test_203_enable_disbale(self):
        '''
        Policy 203: enabling and disabling tokens. "admin_enable_disable" is allowed, "admin_init" not.
        '''
        parameters = { 'serial' : 'cko_test_001',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='disable'), params=parameters)
        log.error(response)
        assert '"status": false' in response

        parameters = { 'serial' : 'cko_test_001',
                       'selftest_admin' : 'admin_enable_disable'
                      }
        response = self.app.get(url(controller='admin', action='disable'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        parameters = { 'serial' : 'cko_test_001',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='enable'), params=parameters)
        log.error(response)
        assert '"status": false' in response

        parameters = { 'serial' : 'cko_test_001',
                       'selftest_admin' : 'admin_enable_disable'
                      }
        response = self.app.get(url(controller='admin', action='enable'), params=parameters)
        log.error(response)
        assert '"status": true' in response


    def test_204_set(self):
        '''
        Policy 204: setting token properties. "admin_set" is allowed, "admin_init" not.
        '''
        parameters = { 'serial' : 'cko_test_001',
                       'maxFailCount' : '20',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='set'), params=parameters)
        log.error(response)
        assert '"status": false' in response

        parameters = { 'serial' : 'cko_test_001',
                       'maxFailCount' : '20',
                       'selftest_admin' : 'admin_set'
                      }
        response = self.app.get(url(controller='admin', action='set'), params=parameters)
        log.error(response)
        assert '"status": true' in response


    def test_205_setPIN(self):
        '''
        Policy 205: setting PIN. "admin_setpin" is allowed, "admin_set" not!
        '''
        parameters = { 'serial' : 'cko_test_001',
                       'userpin' : 'test',
                       'selftest_admin' : 'admin_set'
                      }
        response = self.app.get(url(controller='admin', action='setPin'), params=parameters)
        log.error(response)
        assert '"status": false' in response

        parameters = { 'serial' : 'cko_test_001',
                       'userpin' : 'test',
                       'selftest_admin' : 'admin_setpin'
                      }
        response = self.app.get(url(controller='admin', action='setPin'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        parameters = { 'serial' : 'cko_test_001',
                       'pin' : 'test',
                       'selftest_admin' : 'admin_set'
                      }
        response = self.app.get(url(controller='admin', action='set'), params=parameters)
        log.error(response)
        assert '"status": false' in response

        parameters = { 'serial' : 'cko_test_001',
                       'pin' : 'test',
                       'selftest_admin' : 'admin_setpin'
                      }
        response = self.app.get(url(controller='admin', action='set'), params=parameters)
        log.error(response)
        assert '"status": true' in response


    def test_206_resync(self):
        '''
        Policy 206: resynching token. "admin_resync" is allowed. "admin_set" not.
        '''
        parameters = { 'serial' : 'cko_test_001',
                       'otp1' : '123456',
                       'otp2' : '123456',
                       'selftest_admin' : 'admin_set'
                      }
        response = self.app.get(url(controller='admin', action='resync'), params=parameters)
        log.error(response)
        assert '"status": false' in response

        parameters = { 'serial' : 'cko_test_001',
                       'otp1' : '123456',
                       'otp2' : '123456',
                       'selftest_admin' : 'admin_resync'
                      }

        response = self.app.get(url(controller='admin', action='resync'), params=parameters)
        log.error(response)
        assert '"status": true' in response

    def test_207_reset(self):
        '''
        Policy 207: admin is allowed to reset a token
        '''
        parameters = { 'serial' : 'cko_test_001',
                       'selftest_admin' : 'admin_set'
                      }
        response = self.app.get(url(controller='admin', action='reset'), params=parameters)
        log.error(response)
        assert '"status": false' in response

        parameters = { 'serial' : 'cko_test_001',
                       'selftest_admin' : 'admin_reset'
                      }
        response = self.app.get(url(controller='admin', action='reset'), params=parameters)
        log.error(response)
        assert '"status": true' in response

    def test_208_assign_unassign(self):
        '''
        Policy 208: admin_assign_unassign is allowed to assign and unassign a token. admin_set is not allowed to assign
        '''
        parameters = { 'serial' : 'cko_test_001',
                       'user' : 'root',
                       'selftest_admin' : 'admin_set'
                      }
        response = self.app.get(url(controller='admin', action='assign'), params=parameters)
        log.error(response)
        assert '"status": false' in response

        parameters = { 'serial' : 'cko_test_001',
                       'user' : 'root',
                       'selftest_admin' : 'admin_assign_unassign'
                      }
        response = self.app.get(url(controller='admin', action='assign'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        parameters = { 'serial' : 'cko_test_001',
                       'selftest_admin' : 'admin_assign_unassign'
                      }
        response = self.app.get(url(controller='admin', action='unassign'), params=parameters)
        log.error(response)
        assert '"status": true' in response

    def test_209_remove_fail(self):
        '''
        Policy 209: test remove fail
        '''
        parameters = { 'serial' : 'cko_test_003',
                       'selftest_admin' : 'admin_set'
                      }
        response = self.app.get(url(controller='admin', action='remove'), params=parameters)
        log.error(response)
        assert '"status": false' in response

    def test_210_remove_success(self):
        '''
        Policy 210: test remove success
        '''
        parameters = { 'serial' : 'cko_test_001',
                       'selftest_admin' : 'admin_remove'
                      }
        response = self.app.get(url(controller='admin', action='remove'), params=parameters)
        log.error(response)
        assert '"status": true' in response


    def test_211_remove_in_wrong_realm(self):
        '''
        Policy 211: An administrator is not allowed to remove a token, if the token is in the wrong realm
        '''
        policy = "pol211"
        admin = "admin211"
        realm = "realm211"
        realm_wrong = "realmwrong211"
        serial = "spass211"
        response = self.app.get(url(controller="system", action="setPolicy"), params={'name' : policy,
                                                                                  'scope' : 'admin',
                                                                                  'action' : 'initHMAC, remove',
                                                                                  'user' : admin,
                                                                                  'realm' : realm,
                                                                                  'selftest_admin' : 'superadmin'})

        log.error(response)
        assert '"setPolicy pol211":' in response
        assert '"status": true,' in response

        # add token to realm_wrong
        response = self.app.get(url(controller="admin", action="init"), params={'serial' : serial,
                                                                               'type' : 'spass',
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true,' in response
        assert '"value": true' in response

        response = self.app.get(url(controller="admin", action="tokenrealm"), params={'serial' : serial,
                                                                               'realms' : realm_wrong,
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true,' in response
        assert '"value": 1' in response

        # admin will fail to remove token in wrong realm
        response = self.app.get(url(controller="admin", action="remove"), params={'serial' : serial,
                                                                               'selftest_admin' : admin})
        log.error(response)
        assert '"status": false,' in response
        assert 'You do not have the administrative right to remove token' in response

        # remove token
        response = self.app.get(url(controller="admin", action="remove"), params={'serial' : serial,
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true,' in response
        assert '"value": 1' in response

        # remove policy
        response = self.app.get(url(controller="system", action="delPolicy"), params={'name' : policy,
                                                                                  'selftest_admin' : 'superadmin'})

        log.error(response)
        assert '"status": true,' in response
        assert '"privacyidea.Policy.%s.scope": true' % policy in response

    def test_212_remove_no_action(self):
        '''
        Policy 212: admin is not allowed to remove token, if he does not have the action in the right realm
        '''
        policy = "pol212"
        admin = "admin212"
        realm = "realm212"
        serial = "spass212"

        # add token to realm_wrong
        #response = self.app.get(url(controller="admin", action="init"),
        #                        params={'serial' : serial,
        #                                   'type' : 'spass',
        #                                   'selftest_admin' : 'superadmin'})
        #log.error(response)
        #assert '"status": true,' in response
        #assert '"value": true' in response


        response = self.app.get(url(controller="system", action="setPolicy"),
                                params={'name' : policy,
                                          'scope' : 'admin',
                                          'action' : 'initHMAC, initSPASS',
                                          'user' : admin,
                                          'realm' : realm,
                                          'selftest_admin' : 'superadmin'
                                        }
                                )

        log.error(response)
        assert '"setPolicy pol212":' in response
        assert '"status": true,' in response

        # add token to realm_wrong
        response = self.app.get(url(controller="admin", action="init"),
                                params={'serial' : serial,
                                           'type' : 'spass',
                                           'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true,' in response
        assert '"value": true' in response

        response = self.app.get(url(controller="admin", action="tokenrealm"),
                                params={'serial' : serial,
                                           'realms' : realm,
                                           'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true,' in response
        assert '"value": 1' in response

        # admin will fail to remove token in his right realm
        response = self.app.get(url(controller="admin", action="remove"),
                                params={'serial' : serial,
                                           'selftest_admin' : admin})
        log.error(response)
        assert '"status": false,' in response
        assert 'ERR410: You do not have the administrative right to remove token' in response

        # remove token
        response = self.app.get(url(controller="admin", action="remove"), params={'serial' : serial,
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true,' in response
        assert '"value": 1' in response

        # remove policy
        response = self.app.get(url(controller="system", action="delPolicy"),
                                params={'name' : policy,
                                        'selftest_admin' : 'superadmin'})

        log.error(response)
        assert '"status": true,' in response
        assert '"privacyidea.Policy.%s.scope": true' % policy in response


        return


    def test_213_remove_no_realm(self):
        '''
        Policy 213: An administrator is not allowed to remove a token, if the token is in NO realm
        '''
        policy = "pol213"
        admin = "admin213"
        realm = "realm213"
        serial = "spass213"
        response = self.app.get(url(controller="system", action="setPolicy"), params={'name' : policy,
                                                                                  'scope' : 'admin',
                                                                                  'action' : 'initHMAC, remove',
                                                                                  'user' : admin,
                                                                                  'realm' : realm,
                                                                                  'selftest_admin' : 'superadmin'})

        log.error(response)
        assert '"setPolicy pol213":' in response
        assert '"status": true,' in response

        # token has no realm
        response = self.app.get(url(controller="admin", action="init"), params={'serial' : serial,
                                                                               'type' : 'spass',
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true,' in response
        assert '"value": true' in response

        # admin will fail to remove the token as it is in no realm of his
        response = self.app.get(url(controller="admin", action="remove"), params={'serial' : serial,
                                                                               'selftest_admin' : admin})
        log.error(response)
        assert '"status": false,' in response
        assert 'You do not have the administrative right to remove token' in response

        # remove token
        response = self.app.get(url(controller="admin", action="remove"), params={'serial' : serial,
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true,' in response
        assert '"value": 1' in response

        # remove policy
        response = self.app.get(url(controller="system", action="delPolicy"), params={'name' : policy,
                                                                                  'selftest_admin' : 'superadmin'})

        log.error(response)
        assert '"status": true,' in response
        assert '"privacyidea.Policy.%s.scope": true' % policy in response


    '''
    TODO: check different REALMS, manageRealms usw.
    '''

    '''
    Check the self services
    '''
    def test_41_setSelfservice_Policies(self):
        '''
        Policy 41: Test several self service policies
        '''
        parameters = { 'name' : 'self_01',
                       'scope' : 'selfservice',
                       'realm' : 'myDefRealm',
                       'action' : 'enrollSMS, enrollMOTP, assign',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        parameters = { 'name' : 'self_02',
                       'scope' : 'selfservice',
                       'realm' : 'myOtherRealm',
                       'action' : 'enrollMOTP, disable, resync, setOTPPIN, setMOTPPIN',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        parameters = { 'name' : 'self_03',
                       'scope' : 'selfservice',
                       'realm' : 'myMixRealm',
                       'action' : 'webprovisionOATH, webprovisionGOOGLE',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

    def test_420_selfService_init(self):
        '''
        Policy 420: test enrolling of tokens in the selfservice portal
        '''
        parameters = { 'type': 'motp',
                       'serial': 'self001',
                       'otpkey' : '1234123412341234',
                       'otppin' : '1234',
                       'selftest_user' : 'horst@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userinit'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        parameters = { 'type': 'motp',
                       'serial': 'self002',
                       'otpkey' : '1234123412341234',
                       'otppin' : '1234',
                       'selftest_user' : 'postgres@myOtherRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userinit'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        '''
        Users in myMixRealm are not allowed to init a token
        '''
        parameters = { 'type': 'motp',
                       'serial': 'self003',
                       'otpkey' : '1234123412341234',
                       'otppin' : '1234',
                       'selftest_user' : 'horst@myMixRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userinit'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

    def test_421_selfService_disable(self):
        '''
        Policy 421: Test disabling tokens in the selfservice portal
        '''
        # myDefRealm is not allowed to disable
        parameters = { 'serial': 'self001',
                       'selftest_user' : 'horst@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userdisable'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

        # myOtherRealm is allowed to disable
        parameters = { 'serial': 'self002',
                       'selftest_user' : 'postgres@myOtherRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userdisable'), params=parameters)
        log.error(response)
        assert  '"disable token": 1' in response

        # myOtherRealm: a user, not the owner of the token can not disable the token
        parameters = { 'serial': 'self002',
                       'selftest_user' : 'not_the_owner@myOtherRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userdisable'), params=parameters)
        log.error(response)
        assert  '"status": false' in response


    def test_422_sefService_setOTPPIN(self):
        '''
        Policy 422: Test setting PIN in the selfserivce portal
        '''
        # myDefRealm is not allowed to disable
        parameters = { 'serial': 'self001',
                       'userpin' : 'test',
                       'selftest_user' : 'horst@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usersetpin'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

        # myOtherRealm is allowed to set PIN
        parameters = { 'serial': 'self002',
                       'userpin' : 'test',
                       'selftest_user' : 'postgres@myOtherRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usersetpin'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        parameters = { 'serial': 'self001',
                       'selftest_admin': 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='remove'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        parameters = { 'serial': 'self002',
                       'selftest_admin': 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='remove'), params=parameters)
        log.error(response)
        assert  '"status": true' in response


    def test_423_selfservice_webprovision(self):
        '''
        Policy 423: Testing webprovisioning. myMixRealm users are allowed to provision, users in myDefRealm not.
        '''
        parameters = {
                       'type' : 'oathtoken',
                       'selftest_user' : 'horst@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userwebprovision'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

        parameters = { 'type' : 'oathtoken',
                       'selftest_user' : 'horst@myMixRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userwebprovision'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        parameters = { 'type' : 'googleauthenticator',
                       'selftest_user' : 'horst@myMixRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userwebprovision'), params=parameters)
        log.error(response)
        assert  '"status": true' in response


    def test_423a_selfservice_assign(self):
        '''
        Policy 423a: users in myDefRealm are allowed to assign. use the token  cko_test_003
        '''
        parameters = { 'serial' : 'cko_test_003',
                       'realms' : 'myDefRealm',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='tokenrealm'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        response = self.app.get(url(controller='admin', action='show'), params={ 'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"privacyIDEA.TokenSerialnumber": "cko_test_003"' in response
        assert '"privacyIDEA.CountWindow": 10' in response
        assert '"privacyIDEA.MaxFail": 10' in response
        assert '"User.description": ""' in response
        assert '"privacyIDEA.IdResClass": ""' in response
        assert '"mydefrealm"' in response


        parameters = { 'serial' : 'cko_test_003',
                       'selftest_user' : 'horst@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userassign'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        # unassign the token
        parameters = { 'serial' : 'cko_test_003',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='unassign'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

    def test_424_selfservice_assign(self):
        '''
        Policy 424: user in myOtherRealm may not assign token
        '''
        parameters = { 'serial' : 'cko_test_003',
                       'realms': 'myOtherRealm',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='tokenrealm'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        # user tries to assign
        parameters = { 'serial' : 'cko_test_003',
                       'selftest_user' : 'root@myOtherRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userassign'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

    def test_425_selfservice_user(self):
        '''
        Policy 425: check a user dependent policy
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'self_user_pol1',
                                                                                       'scope' : 'selfservice',
                                                                                       'realm' : 'myDefRealm',
                                                                                       'user' : 'user1',
                                                                                       'action' : 'webprovisionOATH',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # user in realm, who has no policy
        parameters = { 'type' : 'oathtoken',
                       'selftest_user' : 'user2@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userwebprovision'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

        # user who has a policy
        parameters = { 'type' : 'oathtoken',
                       'selftest_user' : 'user1@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userwebprovision'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'self_user_pol1',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # delete both tokens
        response = self.app.get(url(controller='admin', action='remove'), params={'user' : 'user1',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='remove'), params={'user' : 'user2',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

    def test_426_selfservice_resolver(self):
        '''
        Policy 426: check a resolver dependent policy
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'self_res_pol1',
                                                                                       'scope' : 'selfservice',
                                                                                       'realm' : 'myMixRealm',
                                                                                       'user' : 'myDefRes:',
                                                                                       'action' : 'webprovisionOATH',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # delete the old self_03 policy, so that we can use the mixrealm to test
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'self_03',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # we list all the policy to find errors
        response = self.app.get(url(controller='system', action='getPolicy'), params={'scope':'selfservice' ,
                                                                                      'realm':'mymixrealm',
                                                                                     'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # user in resolver myOtherRes, who is not allowed to enroll token
        parameters = { 'type' : 'oathtoken',
                       'selftest_user' : 'other_user@myMixRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userwebprovision'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

        # user in resolver myDefRes, who is allowed to enroll token
        parameters = { 'type' : 'oathtoken',
                       'selftest_user' : 'user1@myMixRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userwebprovision'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'self_res_pol1',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # delete both tokens
        response = self.app.get(url(controller='admin', action='remove'), params={'user' : 'user1',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='remove'), params={'user' : 'user2',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

    def test_427_selfservice_assign(self):
        '''
        Policy 427: user in realm myDefRealm assignes a token, that is not contained in any realm
        '''
        serial = 'temp_spass_427'
        parameters = { 'serial' : serial,
                       'type' : 'spass',
                       'pin' : 'something',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        # check this token is in no realm
        response = self.app.get(url(controller='admin', action='show'), params={})
        log.error(response)
        assert '"privacyIDEA.TokenSerialnumber": "%s"' % serial in response
        assert '"privacyIDEA.CountWindow": 10' in response
        assert '"privacyIDEA.MaxFail": 10' in response
        assert '"User.description": ""' in response
        assert '"privacyIDEA.IdResClass": ""' in response
        assert '"privacyIDEA.RealmNames": []' in response

        # user tries to assign
        parameters = { 'serial' : serial,
                       'selftest_user' : 'horst@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userassign'), params=parameters)
        log.error(response)
        assert  '"assign token": true' in response

        response = self.app.get(url(controller='admin', action='remove'), params={'serial':serial})
        log.error(response)
        assert '"value": 1' in response


    def test_428_selfservice_assign(self):
        '''
        Policy 428: user in realm myDefRealm can not assign a token that is contained in another realm
        '''
        serial = 'temp_spass_428'
        parameters = { 'serial' : serial,
                       'type' : 'spass',
                       'pin' : 'something',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        # set the realm of the token
        response = self.app.get(url(controller='admin', action='tokenrealm'), params={'serial' : serial,
                                                                                     'realms':'myOtherRealm',
                                                                                     'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"value": 1'  in response


        # check this token is in no realm
        response = self.app.get(url(controller='admin', action='show'), params={"serial" : serial})
        log.error(response)
        assert '"privacyIDEA.TokenSerialnumber": "temp_spass_428"'  in response
        assert '"privacyIDEA.CountWindow": 10'  in response
        assert '"privacyIDEA.MaxFail": 10'  in response
        assert '"User.description": ""'  in response
        assert '"privacyIDEA.IdResClass": ""'  in response
        assert '"myotherrealm"'  in response

        # user tries to assign
        parameters = { 'serial' : serial,
                       'selftest_user' : 'horst@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='userassign'), params=parameters)
        log.error(response)
        assert  '"status": false' in response
        assert 'The token you want to assign is not contained in your realm!' in response

        response = self.app.get(url(controller='admin', action='remove'), params={'serial':serial})
        log.error(response)
        assert '"value": 1' in response

    def test_429_get_serial_by_OTP(self):
        '''
        Policy 429: get serial by OTP value
        '''
        # TODO
        seed = "154bf508c52f3048fcf9cf721bbb892637f5e348"
        otps = ["295354", "297395", "027303", "618651"]

        serial = 'oath429'
        parameters = { 'serial' : serial,
                       'type' : 'hmac',
                       'otpkey' : seed,
                       'pin' : 'something',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

        # set the realm of the token
        response = self.app.get(url(controller='admin', action='tokenrealm'), params={'serial' : serial,
                                                                                     'realms':'myDefRealm',
                                                                                     'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"value": 1'  in response

        # check this token is in no realm
        response = self.app.get(url(controller='admin', action='show'), params={"serial" : serial})
        log.error(response)
        assert '"privacyIDEA.TokenSerialnumber": "oath429"'  in response

        # user to get the serial of the OTP of the unassigned token.
        parameters = { 'otp' : otps[3],
                       'selftest_user' : 'passthru_user1@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usergetSerialByOtp'), params=parameters)
        log.error(response)
        assert  '"status": false' in response
        assert 'The policy settings do not allow you to request a serial by OTP!' in response

        # set policy
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'getSerial',
                                                                                     'scope' : 'selfservice',
                                                                                     'realm' : 'myDefRealm',
                                                                                     'action' : 'getserial',
                                                                                     'selftest_admin' : 'superadmin' })
        log.error(response)
        assert '"value" : true'

        # try again to get the serial
        parameters = { 'otp' : otps[0],
                       'realm' : "myDefRealm",
                       'selftest_user' : 'passthru_user1@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usergetSerialByOtp'), params=parameters)
        log.error(response)
        assert  '"status": true' in response
        assert '"serial": "oath429"' in response

        parameters = { 'otp' : otps[3],
                       'selftest_user' : 'passthru_user1@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usergetSerialByOtp'), params=parameters)
        log.error(response)
        assert  '"status": true' in response
        assert '"serial": "oath429"' in response

        # remove the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'getSerial',
                                                                                     'selftest_admin' : 'superadmin' })
        log.error(response)
        assert '"value" : true'

        # remove the token
        response = self.app.get(url(controller='admin', action='remove'), params={'serial':serial})
        log.error(response)
        assert '"value": 1' in response

    def test_430_passthru_policy(self):
        '''
        Policy 430: check the passthru policy. passthru_user1/geheim1 is allowed, passthru_user2/geheim2 is not.
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'passthru',
                                                                                       'scope' : 'authentication',
                                                                                       'realm' : 'myDefRealm',
                                                                                       'user' : 'passthru_user1',
                                                                                       'action' : 'passthru',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # user1 is allowed to passthru as he has no token.
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'pass':'geheim1'})
        log.error(response)
        assert '"value": true' in response

        # user2 is allowed to passthru as he is not in the policy
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'pass':'geheim2'})
        log.error(response)
        assert '"value": false' in response

        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'NoToken',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

    def test_430_passOnNoToken_policy(self):
        '''
        Policy 430: check the passOnNoToken policy. passthru_user1 is allowed with any password, passthru_user2/geheim2 is not.
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'NoToken',
                                                                                       'scope' : 'authentication',
                                                                                       'realm' : 'myDefRealm',
                                                                                       'user' : 'passthru_user1',
                                                                                       'action' : 'passOnNoToken',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # user1 is allowed to passthru as he has no token.
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'pass':'argsargs'})
        log.error(response)
        assert '"value": true' in response

        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'pass':'OtherPW'})
        log.error(response)
        assert '"value": true' in response

        # user2 is allowed to passthru as he is not in the policy
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'pass':'geheim2'})
        log.error(response)
        assert '"value": false' in response

        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'NoToken',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

    def test_431_otppin_policy(self):
        '''
        Policy 431: check that passthru_user1 can authenticate with the password but passthru_user2 authenticates with OTP PIN.
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'otppin',
                                                                                       'scope' : 'authentication',
                                                                                       'realm' : 'myDefRealm',
                                                                                       'user' : 'passthru_user1',
                                                                                       'action' : 'otppin=1',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll a token for each user
        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user1',
                                                                               'type' : 'spass',
                                                                                   'serial' : 'spass_pin_1',
                                                                                   'pin' : 'otppin',
                                                                                   'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user2',
                                                                               'type' : 'spass',
                                                                                   'serial' : 'spass_pin_2',
                                                                                   'pin' : 'otppin',
                                                                                   'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response


        # user1 has otppin=1
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'pass':'geheim1'})
        log.error(response)
        assert '"value": true' in response

        # user2 has default otppin=0
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'pass':'geheim2'})
        log.error(response)
        assert '"value": false' in response

        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": true' in response

        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'otppin',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # remove the tokens
        response = self.app.get(url(controller='admin', action='remove'), params={ 'serial' : 'spass_pin_2',
                                                                                   'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='remove'), params={ 'serial' : 'spass_pin_1',
                                                                                   'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response


    def test_440_check_authorize(self):
        '''
        Policy 440: check if a user is authorized (scope=authorization) to login from  a certain client
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'authorize_user1',
                                                                                       'scope' : 'authorization',
                                                                                       'realm' : 'myDefRealm',
                                                                                       'user' : 'passthru_user1',
                                                                                       'action' : 'authorize',
                                                                                       'client' : '192.168.17.15',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll a token for each user
        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user1',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_1',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user2',
                                                                               'type' : 'spass',
                                                                               'serial' : 'spass_pin_2',
                                                                               'pin' : 'otppin',
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response


        # auth user 1
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'pass':'otppin',
                                                                                   'client' : '192.168.17.15'})
        log.error(response)
        assert '"value": true' in response

        # auth user 1 fails. Wrong client
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'pass':'otppin',
                                                                                   'client' : '192.168.17.16'})
        log.error(response)
        assert '"value": false' in response

        # user2 is not allowed to auth
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'pass':'otppin',
                                                                                   'client' : '192.168.17.15'})
        log.error(response)
        assert '"value": false' in response

        # user2 may login at other clients
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'pass':'otppin',
                                                                                   'client' : '192.168.17.16'})
        log.error(response)
        assert '"value": false' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'authorize_user1',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # remove the tokens
        response = self.app.get(url(controller='admin', action='remove'), params={ 'serial' : 'spass_pin_2',
                                                                                   'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='remove'), params={ 'serial' : 'spass_pin_1',
                                                                                   'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response


    def test_440a_check_authorize_client_exclude(self):
        '''
        Policy 440a: check if authorize policy honor the excluded clients
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'authorize_root',
                                                                                       'scope' : 'authorization',
                                                                                       'realm' : 'myDefRealm',
                                                                                       'user' : 'passthru_user1',
                                                                                       'action' : 'authorize',
                                                                                       'client' : '192.168.17.15, 192.168.17.16',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'authorize_all',
                                                                                       'scope' : 'authorization',
                                                                                       'realm' : 'myDefRealm',
                                                                                       'user' : '*',
                                                                                       'action' : 'authorize',
                                                                                       'client' : '192.168.0.0/16, -192.168.17.15, !192.168.17.16',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll a token for each user
        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user1',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_1',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user2',
                                                                               'type' : 'spass',
                                                                               'serial' : 'spass_pin_2',
                                                                               'pin' : 'otppin',
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response


        # auth user 1
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'pass':'otppin',
                                                                                   'client' : '192.168.17.15'})
        log.error(response)
        assert '"value": true' in response

        # auth user 1 can also auth on othe clients
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'pass':'otppin',
                                                                                   'client' : '192.168.20.1'})
        log.error(response)
        assert '"value": true' in response

        # user2 is not allowed to auth on certain clients
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'pass':'otppin',
                                                                                   'client' : '192.168.17.15'})
        log.error(response)
        assert '"value": false' in response

        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'pass':'otppin',
                                                                                   'client' : '192.168.17.16'})
        log.error(response)
        assert '"value": false' in response

        # user2 may login at other clients
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'pass':'otppin',
                                                                                   'client' : '192.168.20.1'})
        log.error(response)
        assert '"value": true' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'authorize_root',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'authorize_all',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # remove the tokens
        response = self.app.get(url(controller='admin', action='remove'), params={ 'serial' : 'spass_pin_2',
                                                                                   'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='remove'), params={ 'serial' : 'spass_pin_1',
                                                                                   'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response


    def test_441_check_tokentype(self):
        '''
        Policy 441: check the authorization token type.
            User with tokentype PW may login, tokentype SPASS may not
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'authorize_user1',
                                                                                       'scope' : 'authorization',
                                                                                       'realm' : 'myDefRealm',
                                                                                       'user' : 'passthru_user1',
                                                                                       'action' : 'tokentype=PW',
                                                                                       'client' : '192.168.20.21',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll a token for each user
        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user1',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_1',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # Token type SPASS is not allowed to login
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'client' : '192.168.20.21',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": false' in response

        # Token type SPASS is allowed to login from another client
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'client' : '192.168.20.22',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": true' in response


        # delete old token SPASS and enroll PW token
        response = self.app.get(url(controller='admin', action='remove'), params={'serial' : 'spass_pin_1',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user1',
                                                                               'type' : 'pw',
                                                                                'serial' : 'pw_1',
                                                                                'pin' : 'otppin',
                                                                                'otpkey' : 'secret',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # Token type PW is allowed to login
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'client' : '192.168.20.21',
                                                                                   'pass':'otppinsecret'})
        log.error(response)
        assert '"value": true' in response

        # delete PW token
        response = self.app.get(url(controller='admin', action='remove'), params={'serial' : 'pw_1',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        #
        # enroll PW token for passthru_user2
        #

        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user2',
                                                                               'type' : 'spass',
                                                                               'serial' : 'spass_2',
                                                                               'pin' : 'otppin',
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # user 2 can authenticate with other token, since he is not in policy
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'client' : '192.168.20.21',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": true' in response

        # delete pw_2
        response = self.app.get(url(controller='admin', action='remove'), params={'serial' : 'spass_2',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'authorize_user1',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

    def test_441b_check_auth_serial(self):
        '''
        Policy 441b: check the authorization serial.
            User with serial  may login, tokentype SPASS may not
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'authorize_user1',
                                                                                       'scope' : 'authorization',
                                                                                       'realm' : 'myDefRealm',
                                                                                       'user' : 'passthru_user1',
                                                                                       'action' : 'serial=^pw.*',
                                                                                       'client' : '192.168.20.21',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll a token for each user
        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user1',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_1',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # Token type SPASS is not allowed to login
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'client' : '192.168.20.21',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": false' in response

        # Token type SPASS is allowed to login from another client
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'client' : '192.168.20.22',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": true' in response


        # delete old token SPASS and enroll PW token
        response = self.app.get(url(controller='admin', action='remove'), params={'serial' : 'spass_pin_1',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user1',
                                                                               'type' : 'pw',
                                                                                'serial' : 'pw_1',
                                                                                'pin' : 'otppin',
                                                                                'otpkey' : 'secret',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # Token type PW is allowed to login
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1',
                                                                                   'client' : '192.168.20.21',
                                                                                   'pass':'otppinsecret'})
        log.error(response)
        assert '"value": true' in response

        # delete PW token
        response = self.app.get(url(controller='admin', action='remove'), params={'serial' : 'pw_1',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        #
        # enroll PW token for passthru_user2
        #

        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user2',
                                                                               'type' : 'spass',
                                                                               'serial' : 'spass_2',
                                                                               'pin' : 'otppin',
                                                                               'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # user 2 can authenticate with other token, since he is not in policy
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2',
                                                                                   'client' : '192.168.20.21',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": true' in response

        # delete pw_2
        response = self.app.get(url(controller='admin', action='remove'), params={'serial' : 'spass_2',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'authorize_user1',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response



    def test_442_set_realm(self):
        '''
        Policy 442: set the realm during authentication for a given user
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'set_realm',
                                                                                       'scope' : 'authorization',
                                                                                       'realm' : 'WrongRealm',
                                                                                       'user' : 'passthru_user1',
                                                                                       'action' : 'setrealm=myDefRealm',
                                                                                       'client' : '192.168.20.21',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll a token for each user
        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user1',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_1',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='init'), params={'user':'passthru_user2',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_2',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        # Realm for user1 gets rewritten
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user1@WrongRealm',
                                                                                   'client' : '192.168.20.21',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": true' in response

        # Realm for user2 gets not rewritten
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2@WrongRealm',
                                                                                   'client' : '192.168.20.21',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": false' in response

        # User 2 can login with right realm
        response = self.app.get(url(controller='validate', action='check'), params={'user':'passthru_user2@myDefRealm',
                                                                                   'client' : '192.168.20.21',
                                                                                   'pass':'otppin'})
        log.error(response)
        assert '"value": true' in response


        # delete the tokens
        response = self.app.get(url(controller='admin', action='remove'), params={'serial' : 'spass_pin_1',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='admin', action='remove'), params={'serial' : 'spass_pin_2',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response


        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'set_realm',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response



    def test_501_check_userlist(self):
        '''
        Policy 501: check the userlisting for admins. Set up the policies
        '''
        parameters = { 'name' : '501_user1',
                      'scope' : 'admin',
                      'realm' : 'MyDefRealm',
                      'user' : '501_admin_def',
                      'action' : 'userlist',
                      'selftest_admin' : 'superadmin' }

        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        print response
        assert ('"realm": true' in response)

        parameters = { 'name' : '501_user2',
                      'scope' : 'admin',
                      'realm' : 'MyOtherRealm',
                      'user' : '501_admin_other',
                      'action' : 'userlist',
                      'selftest_admin' : 'superadmin' }

        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        print response
        assert ('"realm": true' in response)

    def test_502_check_userlist(self):
        '''
        Policy 502: check the userlisting rights. Userlisting allowed
        '''
        parameters = { 'realm' : 'MyDefRealm',
                      'selftest_admin' : '501_admin_def'}
        response = self.app.get(url(controller='admin', action='userlist'), params=parameters)
        print response
        assert('"status": true' in response)

        response = self.app.get(url(controller='manage', action='userview_flexi'), params=parameters)
        print response

        assert('"rows":' in response)

    def test_503_check_userlist(self):
        '''
        Policy 503: check the userlisting rights. Userlisting forbidden
        '''
        parameters = { 'realm' : 'MyDefRealm',
                      'selftest_admin' : '501_admin_other'}
        response = self.app.get(url(controller='admin', action='userlist'), params=parameters)
        print response
        assert('You do not have the administrative right to list users' in response)

        response = self.app.get(url(controller='manage', action='userview_flexi'), params=parameters)
        print response

        assert('You do not have the administrative right to list users' in response)

    def test_550_check_policy(self):
        '''
        Policy 550: Test the policy checker.
        '''
        policies = [ {'name':'cp1',
                    'selftest_admin':'superadmin',
                    'scope' : 'admin',
                    'user' : 'cp1_admin',
                    'realm' : 'realm1',
                    'action' : '*',
                    },
                    {'name':'cp2',
                     'selftest_admin':'superadmin',
                     'scope':'admin',
                     'user':'cp2_admin',
                     'realm' : 'realm1',
                     'action' : 'remove'
                     },
                     {'name' : 'cp_enroll_1',
                      'selftest_admin':'superadmin',
                      'scope' : 'enrollment',
                      'user' : 'user1',
                      'action' : 'maxtoken=3',
                      'realm' : 'myDefRealm'
                      },
                      {'name' : 'cp_enroll_2',
                      'selftest_admin':'superadmin',
                      'scope' : 'enrollment',
                      'user' : '',
                      'action' : 'maxtoken=1',
                      'realm' : 'myDefRealm'
                      },
                      {'name' : 'cp_auth_1',
                      'selftest_admin':'superadmin',
                      'scope' : 'authentication',
                      'user' : 'user1',
                      'action' : 'otppin=0',
                      'realm' : 'myDefRealm'
                      },
                      {'name' : 'cp_auth_2',
                      'selftest_admin':'superadmin',
                      'scope' : 'authentication',
                      'user' : '',
                      'action' : 'otppin=1',
                      'realm' : 'myDefRealm'
                      },
                      {'name' : 'cp_self_1',
                      'selftest_admin':'superadmin',
                      'scope' : 'selfservice',
                      'user' : 'user1',
                      'action' : 'initHMAC, setOTPPIN',
                      'realm' : 'myDefRealm'
                      },
                      {'name' : 'cp_self_2',
                      'selftest_admin':'superadmin',
                      'scope' : 'selfservice',
                      'user' : 'user1',
                      'action' : 'initHMAC, setOTPPIN, webprovisionGOOGLE',
                      'realm' : 'myDefRealm',
                      'client' : '172.16.200.10'
                      },
                      {'name' : 'cp_self_3',
                      'selftest_admin':'superadmin',
                      'scope' : 'selfservice',
                      'user' : '',
                      'action' : 'initHMAC',
                      'realm' : 'myDefRealm'
                      }
                  ]

        # set the policies
        for pol in policies:
            response = self.app.get(url(controller='system', action='setPolicy'), pol)
            log.error(response)
            assert  '"status": true' in response

        # check the policies
        # cp1_admin is allowed to do all actions in realm1
        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'cp1_admin',
                                                                                'realm' : 'realm1',
                                                                                'action' : 'initHMAC',
                                                                                'scope' : 'admin',
                                                                                'client' : ''})
        log.error(response)
        assert '"cp1": {' in response
        assert '"allowed": true' in response

        # cp1_admin has no rights in realm2
        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'cp1_admin',
                                                                                'realm' : 'realm2',
                                                                                'action' : 'initHMAC',
                                                                                'scope' : 'admin',
                                                                                'client' : ''})
        log.error(response)
        assert '"allowed": false' in response

        # cp2_admin is allowed to remove in realm2
        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'cp2_admin',
                                                                                'realm' : 'realm1',
                                                                                'action' : 'remove',
                                                                                'scope' : 'admin',
                                                                                'client' : ''})
        log.error(response)
        assert '"cp2": {' in response
        assert '"allowed": true' in response

        # cp2_admin is not allowed to enroll in realm2
        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'cp2_admin',
                                                                                'realm' : 'realm1',
                                                                                'action' : 'initHMAC',
                                                                                'scope' : 'admin',
                                                                                'client' : ''})
        log.error(response)
        assert '"allowed": false' in response

        
        # check scope enrollment, user1 may enroll 3 tokens, user2 only 1 token
        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'user1',
                                                                                'realm' : 'myDefRealm',
                                                                                'action' : 'maxtoken',
                                                                                'scope' : 'enrollment',
                                                                                'client' : ''})
        log.error(response)
        assert '"cp_enroll_1": {' in response
        assert '"action": "maxtoken=3",' in response

        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'user2',
                                                                                'realm' : 'myDefRealm',
                                                                                'action' : 'maxtoken',
                                                                                'scope' : 'enrollment',
                                                                                'client' : ''})
        log.error(response)
        assert '"cp_enroll_2": {' in response
        assert '"action": "maxtoken=1",' in response

        # check scope authentication
        # user1 has otppin=0, all other suers otppin=1
        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'user1',
                                                                                'realm' : 'myDefRealm',
                                                                                'action' : 'otppin',
                                                                                'scope' : 'authentication',
                                                                                'client' : ''})
        log.error(response)
        assert '"cp_auth_1": {' in response
        assert '"action": "otppin=0",' in response

        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'user2',
                                                                                'realm' : 'myDefRealm',
                                                                                'action' : 'otppin',
                                                                                'scope' : 'authentication',
                                                                                'client' : ''})
        log.error(response)
        assert '"cp_auth_2": {' in response
        assert '"action": "otppin=1",' in response

        # check scope selfservice
        # Webprovisioning from 192.168.20.1 is not allowed
        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'user1',
                                                                                'realm' : 'myDefRealm',
                                                                                'action' : 'webprovisionGOOGLE',
                                                                                'scope' : 'selfservice',
                                                                                'client' : '192.168.20.1'})
        log.error(response)
        assert '"allowed": false' in response

        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'user1',
                                                                                'realm' : 'myDefRealm',
                                                                                'action' : 'initHMAC',
                                                                                'scope' : 'selfservice',
                                                                                'client' : '192.168.20.1'})
        log.error(response)
        assert '"allowed": true' in response
        assert '"action": "initHMAC, setOTPPIN",' in response

        # webprovisioning from 172.16.200.X is allowrd
        response = self.app.get(url(controller='system', action='checkPolicy'), { 'user' : 'user1',
                                                                                'realm' : 'myDefRealm',
                                                                                'action' : 'webprovisionGOOGLE',
                                                                                'scope' : 'selfservice',
                                                                                'client' : '172.16.200.10'})
        log.error(response)

        #response = self.app.get(url(controller='system', action='getPolicy'),{ 'selftest_admin':'superadmin' })
        #log.error(response)
        assert '"cp_self_2": {' in response
        assert '"action": "initHMAC, setOTPPIN, webprovisionGOOGLE",' in response



        # delete the policies
        for policy in policies:
            response = self.app.get(url(controller='system', action='delPolicy'), params={'name':policy['name']})
            log.error(response)
            assert  '"status": true' in response

    def test_601_otppin_length01(self):
        '''
        Policy 601: set policy to allow setting OTP PIN
        '''
        parameters = { 'name' : 'self_01',
                       'scope' : 'selfservice',
                       'realm' : 'myDefRealm',
                       'action' : 'setOTPPIN',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

    def test_602_otppin_length02(self):
        '''
        Policy 602: Set policy to define the length of the OTP PIN
        '''
        parameters = { 'name' : 'self_pin01',
                       'scope' : 'selfservice',
                       'realm' : 'myDefRealm',
                       'action' : 'otp_pin_maxlength=8, otp_pin_minlength=4 ',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

    def test_603_otppin_length02(self):
        '''
        Policy 603: prepare testing length of PIN: Assign token to user
        '''
        parameters = { 'serial' : 'cko_test_004',
                       'user': 'root@myDefRealm',
                       'otpkey' : '1234123412341234',
                       'otppin' : '1234',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

    def test_604_otp_length_do(self):
        '''
        Policy 604: test the otp length
        '''
        # PIN to short
        parameters = { 'serial' : 'cko_test_004',
                       'userpin': 'bla',
                       'selftest_user' : 'root@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usersetpin'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

        # PIN to long
        parameters = { 'serial' : 'cko_test_004',
                       'userpin': '12345678test',
                       'selftest_user' : 'root@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usersetpin'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

        # PIN perfect
        parameters = { 'serial' : 'cko_test_004',
                       'userpin': '1234567',
                       'selftest_user' : 'root@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usersetpin'), params=parameters)
        log.error(response)
        assert  '"status": true' in response


    def test_605_otppin_contents(self):
        '''
        Policy 605: testing contents of pin: set policy contents=c
        '''
        parameters = { 'name' : 'self_pin02',
                       'scope' : 'selfservice',
                       'realm' : 'myDefRealm',
                       'action' : 'otp_pin_contents=c',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

    def test_606_otppin_contents(self):
        '''
        Policy 606: testing contents of pin: wrong pin
        '''
        # PIN wrong
        parameters = { 'serial' : 'cko_test_004',
                       'userpin': '123456',
                       'selftest_user' : 'root@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usersetpin'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

    def test_607_otppin_contents(self):
        '''
        Policy 607: testing contents of pin: PIN ok
        '''
        # PIN OK
        parameters = { 'serial' : 'cko_test_004',
                       'userpin': 'ab3456',
                       'selftest_user' : 'root@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usersetpin'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

    def test_608_otppin_contents(self):
        '''
        Policy 608: testing contents of pin: contents=cns
        '''
        parameters = { 'name' : 'self_pin02',
                       'scope' : 'selfservice',
                       'realm' : 'myDefRealm',
                       'action' : 'otp_pin_contents=cns',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert  '"status": true' in response

    def test_609_otppin_contents(self):
        '''
        Policy 609: testing contents of pin: wrong pin
        '''
        # PIN wrong
        parameters = { 'serial' : 'cko_test_004',
                       'userpin': 'ab3456',
                       'selftest_user' : 'root@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usersetpin'), params=parameters)
        log.error(response)
        assert  '"status": false' in response

    def test_610_otppin_contents(self):
        '''
        Policy 610: testing contents of pin: PIN ok
        '''
        parameters = { 'serial' : 'cko_test_004',
                       'userpin': 'ab3456!!',
                       'selftest_user' : 'root@myDefRealm'
                      }
        response = self.app.get(url(controller='selfservice', action='usersetpin'), params=parameters)
        log.error(response)
        assert  '"status": true' in response


    '''
        We would also need to define enrollment policies.
        This will be done in the selfservice test script
    '''
    def test_701_enrollment(self):
        '''
        Policy 701: testing enrollment settings: Token limit per user: 2, tokens per realm 5. Setting policy
        '''

        parameters = { 'name' : 'enrollment_01',
                       'scope' : 'enrollment',
                       'realm' : 'myDefRealm',
                       'action' : 'maxtoken=2, tokencount=3, otp_pin_random =4',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert  '"status": true' in response


    def test_702_cleanup(self):
        '''
        Policy 702: Unassigning user root@myDefRealm and deleting all tokens from myDefRealm.
        '''
        for t in ['cko_test_001', 'cko_test_002', 'cko_test_003', 'cko_test_004', 'self001', 'self002']:
            parameters = { 'serial' : t,
                           'selftest_admin' : 'superadmin'
                          }
            response = self.app.get(url(controller='admin', action='remove'), params=parameters)
            log.error(response)
            assert  '"status": true' in response


    def test_703_enrollment01(self):
        '''
        Policy 703: testing enrollment: the first two tokens will enroll, the 3rd will complain
        as the user may not own a 3rd token!
        '''
        # now assign tokens
        parameters = { 'serial' : 'enroll_001',
                       'type' : 'spass',
                       'user' : 'root@myDefRealm',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        parameters = { 'serial' : 'enroll_002',
                       'type' : 'spass',
                       'user' : 'root@myDefRealm',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        # The user may not own a third token!
        parameters = { 'serial' : 'enroll_003',
                       'type' : 'spass',
                       'user' : 'root@myDefRealm',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert '"status": false' in response

    def test_704_enrollment02(self):
        '''
        Policy 704: enroll the 3rd token in myDefRealm. The 4th token will complain, as tokencount = 3

        This was defined in test_701_enrollment
        '''

        parameters = { 'serial' : 'enroll_003',
                       'type' : 'spass',
                       'user' : 'remoteuser@myDefRealm',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        # this would be the 4th token, but only 3 allowed.
        parameters = { 'serial' : 'enroll_004',
                       'type' : 'spass',
                       'user' : 'remoteuser@myDefRealm',
                       'selftest_admin' : 'admin_init'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert '"status": false' in response
        assert 'You can not init any more tokens' in response

    def test_705_tokencount(self):
        '''
        Policy 705: create a new token enroll_tc_01 and try to assign this token to auser in the realm. Assigning will fail, since realm is full
        '''
        parameters = {  "serial": "enroll_tc_01",
                        "otpkey" : "e56eb2bcbafb2eea9bce9463f550f86d587d6c71",
                        "description" : "my EToken",
                        'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='init'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        parameters = { 'serial' : 'enroll_tc_01',
                       'user' : 'remoteuser@myDefRealm',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='assign'), params=parameters)
        log.error(response)
        assert '"status": false' in response
        #assert 'You can not assign any more tokens' in response


    def test_706_tokencount(self):
        '''
        Policy 706: Try to set the tokenrealm of the token enroll_tc_01 to the realm "myDefRealm". Will fail, since realm is full
        '''
        parameters = { 'serial' : 'enroll_tc_01',
                       'realms' : 'mydefrealm',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='tokenrealm'), params=parameters)
        log.error(response)
        assert '"status": false' in response
        assert 'You may not put any more tokens in realm' in response


    def test_707_tokencount(self):
        '''
        Policy 707: Try to enable a token in a full realm. Will fail, since realm is full
        '''

        parameters = { 'serial' : 'enroll_003',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='disable'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        parameters = { 'serial' : 'enroll_tc_01',
                       'realms' : 'mydefrealm',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='tokenrealm'), params=parameters)
        log.error(response)
        assert '"status": true' in response

        parameters = { 'serial' : 'enroll_003',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='enable'), params=parameters)
        log.error(response)
        assert '"status": false' in response
        assert 'You may not enable any more tokens in realm' in response


    def test_708_tokencount(self):
        '''
        Policy 708: Import token into a realm, that is already full. This is done by and admin, who only has rights in this realm. Will fail!
        '''
        parameters = { 'name' : 'realmadmin',
                       'scope' : 'admin',
                       'realm' : 'mydefrealm',
                       'user' : 'realmadmin',
                       'action' : 'import, importcsv',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)
        assert  '"status": true' in response


        parameters = { 'type' : 'oathcsv',
                       'file' : 'import0001, 1234123412345',
                       'selftest_admin': 'realmadmin' }
        response = self.app.put(url(controller="admin", action='loadtokens'), params=parameters)
        log.error(response)
        assert "The maximum number of allowed tokens in realm" in response

    def test_709_maxtoken_with_user(self):
        '''
        Policy 709: Testing maxtoken per user. Policy will be applied for defined user, not for not defined user
        We take myOtherRealm, since for myDefRealm already a maxtoken-policy exist
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'maxtoken_per_user',
                                                                                       'scope' : 'enrollment',
                                                                                       'realm' : 'myOtherRealm',
                                                                                       'user' : 'max1',
                                                                                       'action' : 'maxtoken=1',
                                                                                       'client' : '',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll a token max1
        response = self.app.get(url(controller='admin', action='init'), params={'user':'max1',
                                                                               'realm':'myOtherRealm',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_1',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"value": true' in response

        # enroll 2nd token for max1 will fail
        response = self.app.get(url(controller='admin', action='init'), params={'user':'max1',
                                                                               'realm':'myOtherRealm',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_2',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert 'the maximum number of allowed tokens per user is exceeded' in response

        # enroll 2 tokens for max2
        response = self.app.get(url(controller='admin', action='init'), params={'user':'max2',
                                                                               'realm':'myOtherRealm',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_3',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"value": true' in response

        response = self.app.get(url(controller='admin', action='init'), params={'user':'max2',
                                                                               'realm':'myOtherRealm',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_4',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"value": true' in response

        # delete the tokens of the user
        for serial in ["spass_pin_1", "spass_pin_3", "spass_pin_4"]:
            response = self.app.get(url(controller='admin', action='remove'), params={'serial' : serial,
                                                                                 'selftest_admin' : 'superadmin'
                                                                                  })
            log.error(response)
            assert '"status": true' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'maxtoken_per_user',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

    def test_710_otp_pin_random_for_users(self):
        '''
        Policy 710: Testing scope=enrollment, otp_pin_random for different users
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'otppinrandom_per_user',
                                                                                       'scope' : 'enrollment',
                                                                                       'realm' : 'myOtherRealm',
                                                                                       'user' : 'max1',
                                                                                       'action' : 'otp_pin_random=4',
                                                                                       'client' : '',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll a token max1
        response = self.app.get(url(controller='admin', action='init'), params={'user':'max1',
                                                                               'realm':'myOtherRealm',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_1',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"value": true' in response

        # enroll token for max2
        response = self.app.get(url(controller='admin', action='init'), params={'user':'max2',
                                                                               'realm':'myOtherRealm',
                                                                               'type' : 'spass',
                                                                                'serial' : 'spass_pin_2',
                                                                                'pin' : 'otppin',
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"value": true' in response

        # validate token of max1: unknown otp pin
        response = self.app.get(url(controller='validate', action='check'), params={'user':'max1',
                                                                               'realm':'myOtherRealm',
                                                                               'pass' : 'otppin'
                                                                                })
        log.error(response)
        assert '"value": false' in response

        # validate token of max2: known otp pin
        response = self.app.get(url(controller='validate', action='check'), params={'user':'max2',
                                                                               'realm':'myOtherRealm',
                                                                               'pass' : 'otppin'
                                                                                })
        log.error(response)
        assert '"value": true' in response

        # delete the tokens of the user
        for serial in ["spass_pin_1", "spass_pin_2"]:
            response = self.app.get(url(controller='admin', action='remove'), params={'serial' : serial,
                                                                                 'selftest_admin' : 'superadmin'
                                                                                  })
            log.error(response)
            assert '"status": true' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'otppinrandom_per_user',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

    def test_711_get_tokenlabel_for_users(self):
        '''
        Policy 711: Testing scope=enrollment, tokenlabel for different users
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'tokenlabel_per_user',
                                                                                       'scope' : 'enrollment',
                                                                                       'realm' : 'myOtherRealm',
                                                                                       'user' : 'max1',
                                                                                       'action' : 'tokenlabel=<u>',
                                                                                       'client' : '',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll a token max1
        response = self.app.get(url(controller='admin', action='init'), params={'user':'max1',
                                                                               'realm':'myOtherRealm',
                                                                               'serial' : 'hmac1',
                                                                               'type' : 'hmac',
                                                                                'genkey' : 1,
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"value": "otpauth://hotp/max1?' in response

        # enroll token for max2
        response = self.app.get(url(controller='admin', action='init'), params={'user':'max2',
                                                                               'realm':'myOtherRealm',
                                                                                'serial' : 'hmac2',
                                                                               'type' : 'hmac',
                                                                                'genkey' : 1,
                                                                                'selftest_admin' : 'superadmin'})
        log.error(response)
        assert 'value": "otpauth://hotp/hmac2?' in response


        # delete the tokens of the user
        for serial in ["hmac1", "hmac2"]:
            response = self.app.get(url(controller='admin', action='remove'), params={'serial' : serial,
                                                                                 'selftest_admin' : 'superadmin'
                                                                                  })
            log.error(response)
            assert '"status": true' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'tokenlabel_per_user',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

    def test_712_autoassignment_for_users(self):
        '''
        Policy 712: Testing scope=enrollment, autoassignment for different users

        max1/password1
        max2/password2
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'autoassignment_user',
                                                                                       'scope' : 'enrollment',
                                                                                       'realm' : 'myOtherRealm',
                                                                                       'user' : 'max1',
                                                                                       'action' : 'autoassignment=6',
                                                                                       'client' : '',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll tokens in realm myOtherRealm
        response = self.app.get(url(controller='admin', action='init'), params={'type' : 'hmac',
                                                                                'serial' : 'token1',
                                                                                'otpkey' : 'd9848218d9977592fa70522579ec00e30adc490a',
                                                                                'selftest_admin' : 'superadmin'})  # OTP: 585489
        log.error(response)
        assert '"value": true' in response

        response = self.app.get(url(controller='admin', action='init'), params={'type' : 'hmac',
                                                                                'serial' : 'token2',
                                                                                'otpkey' : '6b9c172fd7a521e57891f758141ce66741694c59',
                                                                                'selftest_admin' : 'superadmin'})  # OTP: 843851
        log.error(response)
        assert '"value": true' in response

        # set realm of tokens
        response = self.app.get(url(controller='admin', action='tokenrealm'), params={'serial' : 'token1',
                                                                                     'realms' : 'myOtherRealm',
                                                                                     'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response
        assert '"value": 1' in response

        response = self.app.get(url(controller='admin', action='tokenrealm'), params={'serial' : 'token2',
                                                                                     'realms' : 'myOtherRealm',
                                                                                     'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"status": true' in response
        assert '"value": 1' in response

        # check tokens in realm
        response = self.app.get(url(controller='admin', action='show'), params={ 'selftest_admin' : 'superadmin'})
        log.error(response)
        assert '"privacyIDEA.TokenSerialnumber": "token2"' in response
        assert '"privacyIDEA.CountWindow": 10' in response
        assert '"privacyIDEA.MaxFail": 10' in response
        assert '"User.description": ""' in response
        assert '"privacyIDEA.IdResClass": ""' in response

        assert '"myotherrealm"' in response

        assert '"privacyIDEA.TokenSerialnumber": "token1"' in response
        assert '"privacyIDEA.CountWindow": 10' in response
        assert '"privacyIDEA.MaxFail": 10' in response
        assert '"User.description": ""' in response
        assert '"privacyIDEA.IdResClass": ""' in response
        assert '"myotherrealm"' in response

        # authenticate max1, gets the token assigned.
        response = self.app.get(url(controller='validate', action='check'), params={'user' : 'max1',
                                                                                  'realm' : 'myotherrealm',
                                                                                  'pass' : 'password1585489'
                                                                                  })
        log.error(response)
        assert '"value": true' in response

        # max 2 can not autoassign a token pw2
        response = self.app.get(url(controller='validate', action='check'), params={'user' : 'max2',
                                                                                  'realm' : 'myotherrealm',
                                                                                  'pass' : 'password2843851'
                                                                                  })
        log.error(response)
        assert '"value": false' in response


        # delete the tokens of the user
        for serial in ["token1", "token2"]:
            response = self.app.get(url(controller='admin', action='remove'), params={'serial' : serial,
                                                                                 'selftest_admin' : 'superadmin'
                                                                                  })
            log.error(response)
            assert '"status": true' in response

        # delete the policy
        response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : 'autoassignment_user',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response


    def test_713_losttoken_for_users(self):
        '''
        Policy 713: Testing scope=enrollment, losttoken for different users.

        max1 gets pwlen=10
        max2 gets pwlen=20
        '''
        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'losttoken_user_1',
                                                                                       'scope' : 'enrollment',
                                                                                       'realm' : 'myOtherRealm',
                                                                                       'user' : 'max1',
                                                                                       'action' : 'lostTokenPWLen=8',
                                                                                       'client' : '',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='system', action='setPolicy'), params={'name' : 'losttoken_user_2',
                                                                                       'scope' : 'enrollment',
                                                                                       'realm' : 'myOtherRealm',
                                                                                       'user' : 'max2',
                                                                                       'action' : 'lostTokenPWLen=20',
                                                                                       'client' : '',
                                                                                       'selftest_admin' : 'superadmin'
                                                                                       })
        log.error(response)
        assert '"status": true' in response

        # enroll tokens in realm myOtherRealm
        response = self.app.get(url(controller='admin', action='init'), params={'type' : 'hmac',
                                                                               'user' : "max1",
                                                                               "realm" : "myOtherRealm",
                                                                                'serial' : 'token1',
                                                                                'otpkey' : 'd9848218d9977592fa70522579ec00e30adc490a',
                                                                                'selftest_admin' : 'superadmin'})  # OTP: 585489
        log.error(response)
        assert '"value": true' in response

        response = self.app.get(url(controller='admin', action='init'), params={'type' : 'hmac',
                                                                                'serial' : 'token2',
                                                                                'user' : "max2",
                                                                               "realm" : "myOtherRealm",
                                                                                'otpkey' : '6b9c172fd7a521e57891f758141ce66741694c59',
                                                                                'selftest_admin' : 'superadmin'})  # OTP: 843851
        log.error(response)
        assert '"value": true' in response

        # generate lost tokens
        response = self.app.get(url(controller='admin', action="losttoken"), params={"serial" : "token1",
                                                                                    "selftest_admin": "superadmin"})
        log.error(response)
        # check for password length 10
        assert re.search('"password": "\S{8}"', unicode(response)) is not None

        response = self.app.get(url(controller='admin', action="losttoken"), params={"serial" : "token2",
                                                                                    "selftest_admin": "superadmin"})
        log.error(response)
                # check for password length 10
        assert re.search('"password": "\S{20}"', unicode(response)) is not None


        # delete the tokens of the user
        for serial in ["token1", "token2", "losttoken1", "losttoken2"]:
            response = self.app.get(url(controller='admin', action='remove'), params={'serial' : serial,
                                                                                 'selftest_admin' : 'superadmin'
                                                                                  })
            log.error(response)
            assert '"status": true' in response

        # delete the policy
        for p in ["losttoken_user_1", "losttoken_user_2"]:
            response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : p,
                                                                                         'selftest_admin' : 'superadmin'
                                                                                       })
            log.error(response)
            assert '"status": true' in response



    def test_801_getqrtanurl(self):
        '''
        Policy 801: Testing Authentication Scope: the QR-TAN Url with * realms
        '''
        URL = "https://testserver/ocra/check_t"
        parameters = { 'name' : 'authQRTAN',
                       'scope' : 'authentication',
                       'realm' : '*',
                       'action' : 'qrtanurl=%s' % URL,
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)

        from privacyidea.lib.policy import PolicyClass
        from pylons import request, config, tmpl_context as c
        Policy = PolicyClass(request, config, c,
                             get_privacyIDEA_config()) 
        u = Policy.get_qrtan_url("testrealm")
        assert(u == URL)

    def test_802_getqrtanurl(self):
        '''
        Policy 802: Testing Authentication Scope: the QR-TAN Url with a single realm
        '''
        URL = "https://testserver/ocra/check_t"
        parameters = { 'name' : 'authQRTAN',
                       'scope' : 'authentication',
                       'realm' : 'testrealm',
                       'action' : 'qrtanurl=%s' % URL,
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)

        from privacyidea.lib.policy import PolicyClass
        from pylons import request, config, tmpl_context as c
        Policy = PolicyClass(request, config, c,
                             get_privacyIDEA_config()) 
        u = Policy.get_qrtan_url("testrealm")
        assert(u == URL)

    def test_803_getqrtanurl(self):
        '''
        Policy 803: Testing Authentication Scope: the QR-TAN Url with 3 realms
        '''
        URL = "https://testserver/ocra/check_t"
        parameters = { 'name' : 'authQRTAN',
                       'scope' : 'authentication',
                       'realm' : 'testrealm, realm2, realm3',
                       'action' : 'qrtanurl=%s' % URL,
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)

        from privacyidea.lib.policy import PolicyClass
        from pylons import request, config, tmpl_context as c
        Policy = PolicyClass(request, config, c,
                             get_privacyIDEA_config()) 
        u = Policy.get_qrtan_url("testrealm")
        assert(u == URL)

    def test_804_ocra_policy(self):
        '''
        Policy 804: Testing the ocra policies
        '''
        policies = [ {'name':'ocra_1',
                     'scope' : 'ocra',
                     'realm' : '*',
                     'action' : 'request, status',
                     'user' : 'ocra_admin_1',
                     'selftest_admin' : 'superadmin',
                     'client' : ''},
                     {'name':'ocra_2',
                     'scope' : 'ocra',
                     'realm' : '*',
                     'action' : 'activationcode, calcOTP',
                     'user' : 'ocra_admin_2',
                     'selftest_admin' : 'superadmin',
                     'client' : ''}
                    ]
        # create policies
        for policy in policies:
            response = self.app.get(url(controller='system', action='setPolicy'), params=policy)
            log.error(response)
            assert '"status": true' in response
            assert '"setPolicy %s"' % policy.get('name') in response

        # check policies
        for policy in policies:
            response = self.app.get(url(controller='system', action='getPolicy'), params={'name':policy.get('name')})
            log.error(response)
            assert '"status": true' in response


        response = self.app.get(url(controller='ocra', action='request'), params={'selftest_admin':'ocra_admin_1',
                                                                                 'user' : 'user1',
                                                                                 'data' : 'Testdaten'})
        log.error(response)
        assert '"status": false' in response
        assert '"No token found: unable to create challenge for ' in response

        response = self.app.get(url(controller='ocra', action='checkstatus'), params={'selftest_admin':'ocra_admin_1',
                                                                                     'user': 'user1'})
        log.error(response)
        assert '"status": true' in response
        assert '"values": []' in response

        response = self.app.get(url(controller='ocra', action='checkstatus'), params={'selftest_admin':'ocra_admin_2',
                                                                                     'user': 'user1'})
        log.error(response)
        assert '"status": false' in response
        assert 'You do not have the administrative right to do an ocra/checkstatus' in response

        response = self.app.get(url(controller='ocra', action='getActivationCode'), params={'selftest_admin':'ocra_admin_2'})
        log.error(response)
        assert '"status": true' in response
        assert '"activationcode": "' in response

        response = self.app.get(url(controller='ocra', action='calculateOtp'), params={'selftest_admin':'ocra_admin_2'})
        log.error(response)
        assert '"status": false' in response
        assert '\'NoneType\' object has no attribute \'find\'' in response

        response = self.app.get(url(controller='ocra', action='calculateOtp'), params={'selftest_admin':'ocra_admin_1'})
        log.error(response)
        assert '"status": false' in response
        assert '"code": 410' in response

        response = self.app.get(url(controller='ocra', action='getActivationCode'), params={'selftest_admin':'ocra_admin_1'})
        log.error(response)
        assert '"status": false' in response
        assert 'You do not have the administrative right to do an ocra/getActivationCode' in response


        # delete policies
        for policy in policies:
            response = self.app.get(url(controller='system', action='delPolicy'), params={'name':policy.get('name')})
            log.error(response)
            assert '"status": true,' in response
            assert '"privacyidea.Policy.%s.scope": true' % policy.get('name') in response


    def test_810_admin_is_not_allowed_to_show(self):
        '''
        Policy 810: admin only wants to show tokens of a selected realm

        Although the admin is allowed to view tokens in two realms,
        he only wants to see the tokens of one realm.
        '''
        policies = [ {'name':'admin_show_1',
                     'scope' : 'admin',
                     'realm' : 'testrealm, myDefRealm',
                     'action' : 'show',
                     'user' : 'show_admin_1',
                     'selftest_admin' : 'superadmin',
                     'client' : ''},
                    ]
        # create policies
        for policy in policies:
            response = self.app.get(url(controller='system', action='setPolicy'), params=policy)
            log.error(response)
            assert '"status": true' in response
            assert '"setPolicy %s"' % policy.get('name') in response

        # test, if admin show_admin_1 is not allowed to show
        response = self.app.get(url(controller='admin', action='show'),
                                params={'viewrealm' : 'testrealm',
                                        'selftest_admin' : 'show_admin_1'
                                        })
        print response
        assert '"status": true,' in response


    def test_812_empty_policy_name(self):
        '''
        Policy 819: Saving policies with empty policy name is not possible
        '''
        policy = {'name':'',
                     'scope' : 'admin',
                     'realm' : '*',
                     'action' : 'initETNG',
                     'selftest_admin' : 'superadmin'}
        response = self.app.get(url(controller='system', action='setPolicy'), params=policy)
        print response
        assert '"status": false' in response
        assert '"message": "The name of the policy must not be empty"' in response

    def test_820_detail_on_success(self):
        '''
        Policy 820: check the authorization/detail_on_success and detail_on_fail policy
        '''
        # enroll token
        response = self.app.get(url(controller='admin', action='init'), params={'serial' : 'detail01',
                                                                                'type' : 'spass',
                                                                                'selftest_admin' : 'superadmin',
                                                                                'pin' : 'secret',
                                                                                'user' : 'detail_user',
                                                                                'realm' : 'myMixRealm'
                                                                                })
        print response
        assert '"value": true' in response

        policies = [ {'name':'detail_1',
                     'scope' : 'authorization',
                     'realm' : 'myMixRealm',
                     'action' : 'detail_on_success',
                     'user' : '*',
                     'selftest_admin' : 'superadmin',
                     'client' : ''},
                    {'name':'detail_2',
                     'scope' : 'authorization',
                     'realm' : 'myMixRealm',
                     'action' : 'detail_on_fail',
                     'user' : '*',
                     'selftest_admin' : 'superadmin',
                     'client' : ''}
                    ]

        # set policy for authorization
        for pol in policies:
            response = self.app.get(url(controller='system', action='setPolicy'), params=pol)
            print response
            assert '"status": true' in response
            assert '"setPolicy detail_' in response

        # check the successful validation
        response = self.app.get(url(controller='validate', action='check'), params={'user' : 'detail_user@myMixRealm',
                                                                                    'pass' : 'secret'})
        print response
        assert '"value": true' in response
        assert '"serial": "detail01",' in response
        assert '"realm": "myMixRealm",' in response
        assert '"user": "detail_user",' in response
        assert '"tokentype": "spass"' in response

        # check failed validation
        response = self.app.get(url(controller='validate', action='check'), params={'user' : 'detail_user@myMixRealm',
                                                                                    'pass' : 'wrong'})
        print response
        assert '"value": false' in response
        assert '"error": "wrong otp pin -1"' in response

        #delete policies
        for pol in ["detail_1", "detail_2"]:
            response = self.app.get(url(controller='system', action='delPolicy'), params={'name' : pol,
                                                                                          'selftest_admin' : 'superadmin'
                                                                                          })
            print response
            assert '"status": true' in response
            assert '"delPolicy"' in response

        # delete token
        response = self.app.get(url(controller='admin', action='remove'), params={'serial' : 'detail01',
                                                                                'selftest_admin' : 'superadmin'
                                                                                })
        print response
        assert '"value": 1' in response



    def test_998_cleanup_policies(self):
        '''
        Policy 998: remove (hopefully all policies)
        '''
        # generic delete of all policies
        parameters = {'selftest_admin' : 'superadmin'}
        response = self.app.get(url(controller='system', action='getPolicy'), params=parameters)
        log.error(response)

        result = loads(response.body)
        names = result.get("result").get('value').keys()

        ## delete all standard policies
        for name in names:
            if name in ["ManageAll", "sysSuper"]:
                continue
            parameters = { 'name' : name,
                          'selftest_admin' : 'superadmin' }
            response = self.app.get(url(controller='system', action='delPolicy'), params=parameters)
            log.error(response)
            assert '"status": true' in response

        ## delete all super policies as the end
        for name in ["ManageAll", "sysSuper"]:
            parameters = { 'name' : name,
                          'selftest_admin' : 'superadmin' }
            response = self.app.get(url(controller='system', action='delPolicy'), params=parameters)
            log.error(response)
            assert '"status": true' in response





    def test_999_check_NO_policies(self):
        '''
        Policy 999: Check if all policies are deleted from the system
        '''
        # check if we deleted all policies
        parameters = {'selftest_admin' : 'superadmin'}
        response = self.app.get(url(controller='system', action='getPolicy'), params=parameters)
        log.error(response)
        assert '"status": true' in response
        assert '"value": {}' in response
