# -*- coding: utf-8 -*-
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2014-10-04 Cornelius Kölbel <cornelius@privacyidea.org>
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
Description:  functional tests of ldap resolver
'''
import logging

from mockldap import MockLdap
from privacyidea.tests import TestController, url
# from privacyidea.lib.resolvers import LDAPIdResolver
from privacyidea.lib.resolvers.UserIdResolver import getResolverClass

log = logging.getLogger(__name__)


class TestLDAPResolver(TestController):
    top = ('o=test', {'o': 'test'})
    example = ('ou=example,o=test', {'ou': 'example'})
    other = ('ou=other,o=test', {'ou': 'other'})
    
    alice = ('cn=alice,ou=example,o=test', {'dn': 'cn=alice,ou=example,o=test',
                                            'cn': 'alice',
                                            'userPassword': ['alicepw']})
    bob = ('cn=bob,ou=other,o=test', {'dn': 'cn=bob,ou=other,o=test',
                                      'cn': 'bob',
                                      'userPassword': ['bobpw']})
    admin = ('cn=admin,o=test', {'dn': 'cn=admin,o=test',
                                 'cn': 'admin',
                                 'userPassword': ['secret']})

    # This is the content of our mock LDAP directory. It takes the form
    # {dn: {attr: [value, ...], ...}, ...}.
    directory = dict([top, example, other,
                      alice,
                      bob,
                      admin])
    mockldap = MockLdap(directory)

    @classmethod
    def tearDownClass(cls):
        del cls.mockldap

    def setUp(self):
        # Patch ldap.initialize
        self.mockldap.start()
        self.ldapobj = self.mockldap['ldap://localhost/']

    def tearDown(self):
        # Stop patching ldap.initialize and reset state.
        self.mockldap.stop()
        del self.ldapobj

    def test_01_standalone_DN(self):
        '''
        Testing standalone functionality with UIDTYPE DN
        '''
        y = getResolverClass("LDAPIdResolver", "IdResolver")()
    
        y.loadConfig({'privacyidea.ldapresolver.LDAPURI': 'ldap://localhost',
                      'privacyidea.ldapresolver.LDAPBASE': 'o=test',
                      'privacyidea.ldapresolver.BINDDN': 'cn=admin,o=test',
                      'privacyidea.ldapresolver.BINDPW': 'secret',
                      'privacyidea.ldapresolver.LOGINNAMEATTRIBUTE': 'cn',
                      'privacyidea.ldapresolver.LDAPSEARCHFILTER': '(cn=*)',
                      'privacyidea.ldapresolver.LDAPFILTER': '(&(cn=%s))',
                      'privacyidea.ldapresolver.USERINFO': '{"username": "cn", \
                          "phone" : "telephoneNumber", \
                          "mobile" : "mobile", \
                          "email" : "mail", \
                          "surname" : "sn", \
                          "givenname" : "givenName" }',
                      'privacyidea.ldapresolver.UIDTYPE': 'dn',
                      },
                     "")

        result = y.getUserList({'username': '*'})
        print result
        assert {'username': 'bob',
                'userid': 'cn=bob,ou=other,o=test'} in result
        
        loginId = y.getUserId("bob")

        result = y.getUserInfo(loginId)
        print result
        assert result.get("username") == "bob"
    
        result = y.checkPass("cn=alice,ou=example,o=test", "alicepw")
        print result
        assert result is True
        
        result = y.checkPass("cn=alice,ou=example,o=test", "WRONG")
        print result
        assert result is False
        
        result = y.getUsername("cn=alice,ou=example,o=test")
        print result
        assert result == "alice"
        
    def test_02_standalone_CN(self):
        '''
        Testing standalone functionality with UID Type CN
        '''
        y = getResolverClass("LDAPIdResolver", "IdResolver")()
    
        y.loadConfig({'privacyidea.ldapresolver.LDAPURI': 'ldap://localhost',
                      'privacyidea.ldapresolver.LDAPBASE': 'o=test',
                      'privacyidea.ldapresolver.BINDDN': 'cn=admin,o=test',
                      'privacyidea.ldapresolver.BINDPW': 'secret',
                      'privacyidea.ldapresolver.LOGINNAMEATTRIBUTE': 'cn',
                      'privacyidea.ldapresolver.LDAPSEARCHFILTER': '(cn=*)',
                      'privacyidea.ldapresolver.LDAPFILTER': '(&(cn=%s))',
                      'privacyidea.ldapresolver.USERINFO': '{"username": "cn", \
                          "phone" : "telephoneNumber", \
                          "mobile" : "mobile", \
                          "email" : "mail", \
                          "surname" : "sn", \
                          "givenname" : "givenName" }',
                      'privacyidea.ldapresolver.UIDTYPE': 'cn',
                      },
                     "")

        result = y.getUserList({'username': '*'})
        print result
        assert {'userid': 'bob'} in result
        
        loginId = y.getUserId("bob")

        result = y.getUserInfo(loginId)
        print result
        assert result.get("username") == "bob"
    
        result = y.checkPass("alice", "alicepw")
        print result
        assert result is True
        
        result = y.checkPass("alice", "WRONG")
        print result
        assert result is False

    def test_03_testconnection(self):
        '''
        Test the connection
        '''
        y = getResolverClass("LDAPIdResolver", "IdResolver")()
    
        y.loadConfig({'privacyidea.ldapresolver.LDAPURI': 'ldap://localhost',
                      'privacyidea.ldapresolver.LDAPBASE': 'o=test',
                      'privacyidea.ldapresolver.BINDDN': 'cn=admin,o=test',
                      'privacyidea.ldapresolver.BINDPW': 'secret',
                      'privacyidea.ldapresolver.LOGINNAMEATTRIBUTE': 'cn',
                      'privacyidea.ldapresolver.LDAPSEARCHFILTER': '(cn=*)',
                      'privacyidea.ldapresolver.LDAPFILTER': '(&(cn=%s))',
                      'privacyidea.ldapresolver.USERINFO': '{"username": "cn", \
                          "phone" : "telephoneNumber", \
                          "mobile" : "mobile", \
                          "email" : "mail", \
                          "surname" : "sn", \
                          "givenname" : "givenName" }',
                      'privacyidea.ldapresolver.UIDTYPE': 'cn',
                      },
                     "")
        
        result = y.testconnection({"BINDDN": "cn=admin,o=test",
                                   "BINDPW": "secret",
                                   "LDAPURI": "ldap://localhost",
                                   "LDAPBASE": "o=test",
                                   "LOGINNAMEATTRIBUTE": "cn",
                                   "LDAPSEARCHFILTER": "(cn=*)",
                                   'USERINFO': '{"username": "cn", \
                                      "phone" : "telephoneNumber", \
                                      "mobile" : "mobile", \
                                      "email" : "mail", \
                                      "surname" : "sn", \
                                      "givenname" : "givenName" }'
                                   })
        print result
        assert result[0] is True
        assert "Your LDAP config seems to be OK" in result[1]