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
#FIXME %(here)s does not work in this file!

from privacyidea.lib.resolvers.UserIdResolver import getResolverClass

from privacyidea.tests import TestController


import logging
log = logging.getLogger(__name__)
import os

class TestPasswdController(TestController):
    '''
    '''
    
    
    def setUp(self):
        TestController.setUp(self)
        self.serials = []
        self.cwd = os.getcwd()


    def test_resolver(self):
        '''
        Testing PasswdIdResolver
        '''
        y = getResolverClass("PasswdIdResolver", "IdResolver")()
        y.loadConfig({ 'privacyidea.passwdresolver.fileName' : '%s/privacyidea/tests/testdata/my-passwd' % self.cwd }, "")

        userlist = y.getUserList({'username':'*', "userid":"= 1000"})
        print userlist
        assert userlist[0].get('username') == "heinz"


        loginId = y.getUserId("heinz")
        print loginId
        assert loginId == '1000'

        ret = y.getUserInfo(loginId)
        print ret
        assert ret.get('username') == "heinz"

        username_exists = y.getUsername('1000')
        print "Username exists: %r" % username_exists
        assert username_exists

    def test_no_file(self):
        '''
        Testing PasswdIdResolver without file
        '''
        y = getResolverClass("PasswdIdResolver", "IdResolver")()
        y.loadFile()

        userlist = y.getUserList({'username':'*', "userid":"= 0"})
        print userlist
        assert userlist[0].get('username') == "root"


        loginId = y.getUserId("root")
        print loginId
        assert loginId == '0'

        ret = y.getUserInfo(loginId)
        print ret
        assert ret.get('username') == "root"

    def test_checkpass_shadow(self):
        '''
        Testing checkpass with PasswdIdResolver with a shadow passwd file
        '''
        y = getResolverClass("PasswdIdResolver", "IdResolver")()
        y.loadConfig({ 'privacyidea.passwdresolver.fileName' : '%s/privacyidea/tests/testdata/my-passwd' % self.cwd }, "")

        success = False
        try:
            y.checkPass('1000', "geheim")
        except NotImplementedError:
            success = True

        assert success

    def test_checkpass(self):
        '''
        Testing checkpass
        '''
        y = getResolverClass("PasswdIdResolver", "IdResolver")()
        y.loadConfig({"privacyidea.passwdresolver.fileName": "%s/privacyidea/tests/testdata/my-pass2" % self.cwd}, "")

        res = y.checkPass('2001', "geheim")
        print "result %r" % res
        assert res

        res = y.checkPass('2001', "wrongPW")
        print "result %r" % res
        assert res == False

    def test_searchfields(self):
        '''
        Testing getSearchfields
        '''
        y = getResolverClass("PasswdIdResolver", "IdResolver")()
        y.loadConfig({ 'privacyidea.passwdresolver.fileName' : '%s/privacyidea/tests/testdata/my-pass2' % self.cwd }, "")

        s = y.getSearchFields()
        print s
        assert s

