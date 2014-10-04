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

from privacyidea.tests import TestController
from privacyidea.lib.resolvers.UserIdResolver import getResolverClass

log = logging.getLogger(__name__)


class TestSQLResolver(TestController):

    def test_01_standalone(self):
        '''
        Testing standalone functionality of SQL resolver
        '''
        y = getResolverClass("SQLIdResolver", "IdResolver")()
    
        y.loadConfig({'privacyidea.sqlresolver.Driver': 'sqlite',
                      'privacyidea.sqlresolver.Server': '/privacyidea/'
                      'tests/testdata/',
                      'privacyidea.sqlresolver.Database': "testuser.sqlite",
                      'privacyidea.sqlresolver.Table': 'users',
                      'privacyidea.sqlresolver.Encoding': "utf-8",
                      'privacyidea.sqlresolver.Map': '{ "username": "username", \
                          "userid" : "id", \
                          "email" : "email", \
                          "surname" : "name", \
                          "givenname" : "givenname", \
                          "password" : "password", \
                          "phone": "phone", \
                          "mobile": "mobile"}',
                      },
                     "")

        result = y.getUserList()
        print result
        assert len(result) == 5
        assert result[0].get("username") == "user1"
        assert result[1].get("username") == "fred"
        assert result[2].get("username") == "cornelius"
        
        user = "cornelius"
        UserId = y.getUserId(user)
        print UserId
        assert UserId == 3
        
        result = y.getUserInfo(0)
        print result
        assert {} == result
        
        user1 = {'username': u'user1',
                 'password': u'{SSHA512}zMpVSq1S/iJXpTYciIxssmDi+0iUpBZFNPfWh'
                 '0W9rnZFNvzQekuAhPEBEjEFqGEFsITfzo+LB0HTwcudZLcWm4meOzAn53kV',
                 'surname': u'dampf',
                 'mobile': u'+49 151 123454656',
                 'email': u'user1@testdomain.com',
                 'phone': u'030 123454566',
                 'givenname': u'hans',
                 'id': 1}
        result = y.getUserInfo(1)
        print result
        assert result == user1
        
        # {'username': u'cornelius', 'id': 3}
        result = y.getUserInfo(3)
        print result
        assert result.get("email") == "cornelius@privacyidea.org"
        
        # check for umlaut
        result = y.getUserInfo(3)
        print result
        assert result.get("surname") == u'K\xf6lbel'
        
        result = y.getUsername(3)
        print result
        assert "cornelius" in result
        
    def test_02_check_passwords(self):
        '''
        Checking SQL passwords
        '''
        '''
        SHA256 of "dunno"
        772cb52221f19104310cd2f549f5131fbfd34e0f4de7590c87b1d73175812607
        '''
        y = getResolverClass("SQLIdResolver", "IdResolver")()
    
        y.loadConfig({'privacyidea.sqlresolver.Driver': 'sqlite',
                      'privacyidea.sqlresolver.Server': '/privacyidea/'
                      'tests/testdata/',
                      'privacyidea.sqlresolver.Database': "testuser.sqlite",
                      'privacyidea.sqlresolver.Table': 'users',
                      'privacyidea.sqlresolver.Encoding': "utf-8",
                      'privacyidea.sqlresolver.Map': '{ "username": "username", \
                          "userid" : "id", \
                          "email" : "email", \
                          "surname" : "name", \
                          "givenname" : "givenname", \
                          "password" : "password", \
                          "phone": "phone", \
                          "mobile": "mobile"}',
                      },
                     "")
        
        result = y.checkPass(3, "dunno")
        print result
        assert result is True
        
        '''
        SHA1 base64 encoded of "dunno"
        Lg8DuLoXOwvPkMABDprnaTp0JOA=
        '''
        result = y.checkPass(2, "dunno")
        print result
        assert result is True
        
        result = y.checkPass(1, "dunno")
        print result
        assert result is True
        
        result = y.checkPass(4, "dunno")
        print result
        assert result is True
        
        result = y.checkPass(5, "dunno")
        print result
        assert result is True
        
    def test_03_testconnection(self):
        '''
        Testing standalone functionality of SQL resolver
        '''
        y = getResolverClass("SQLIdResolver", "IdResolver")()
    
        result = y.testconnection({'Driver': 'sqlite',
                                   'Server': '/privacyidea/tests/testdata/',
                                   'Database': "testuser.sqlite",
                                   'Table': 'users',
                                   'Encoding': "utf-8",
                                   'Map': '{ "username": "username", \
                                      "userid" : "id", \
                                      "email" : "email", \
                                      "surname" : "name", \
                                      "givenname" : "givenname", \
                                      "password" : "password", \
                                      "phone": "phone", \
                                      "mobile": "mobile"}',
                                   })
        print result
        assert result[0] == 5
        assert 'Found 5 users.' in result[1]