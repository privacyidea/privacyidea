# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2014 Sep 29 Cornelius Kölbel, cornelius@privacyidea.org
#              added tests for getRealmsOfTokenOrUser and getAllTokenUsers
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
import pylons
from paste.deploy import loadapp
from webtest import TestApp

from privacyidea.tests import TestController, url

log = logging.getLogger(__name__)


class TestManageController(TestController):

    ###############################################################################
    def test_01_index(self):
        '''
        Manage: testing index access
        '''
        response = self.app.get(url(controller='manage', action='index'),
                                params={})
        print "index response: %r" % response.testbody
        assert '<title>privacyIDEA Management</title>' in response.testbody


    def test_02_policies(self):
        '''
        Manage: testing policies tab
        '''
        response = self.app.get(url(controller='manage', action='policies'),
                                params={})
        print "policies response: %r" % response.testbody
        assert '<a id=policy_export>' in response.testbody
        assert '<button id=policy_import>' in response.testbody
        assert '<button  id=button_policy_delete>' in response.testbody

    def test_03_audit(self):
        '''
        Manage: testing audit trail
        '''
        response = self.app.get(url(controller='manage', action='audittrail'),
                                params={})
        print "audit response: %r" % response.testbody
        assert 'table id="audit_table"' in response.testbody
        assert 'view_audit();' in response.testbody

    def test_04_tokenview(self):
        '''
        Manage: testing tokenview
        '''
        response = self.app.get(url(controller='manage', action='tokenview'),
                                params={})
        print "token response: %r" % response.testbody
        assert 'button_losttoken' in response.testbody
        assert 'button_tokeninfo' in response.testbody
        assert 'button_resync' in response.testbody
        assert 'button_tokenrealm' in response.testbody
        assert 'table id="token_table"' in response.testbody
        assert 'view_token();' in response.testbody
        assert 'tokenbuttons();' in response.testbody

    def test_05_userview(self):
        '''
        Manage: testing userview
        '''
        response = self.app.get(url(controller='manage', action='userview'),
                                params={})
        print "user response: %r" % response.testbody
        assert 'table id="user_table"' in response.testbody
        assert 'view_user();' in response.testbody

    def test_06_tokenflexi(self):
        '''
        Manage: testing the tokenview_flexi method
        '''
        response = self.app.get(url(controller='manage', action='tokenview_flexi'),
                                params={})

        testbody = response.body.replace('\n', ' ').replace('\r', '').replace("  ", " ")
        print "token flexi response 1: %r" % response.testbody
        #assert '"total": 3' in testbody
        assert '"token1",       true,       "heinz"' in testbody
        assert '"token2",       true,       "nick"' in testbody
        assert '"token3",       true,       "renate"' in testbody

        # only renates token
        response = self.app.get(url(controller='manage', action='tokenview_flexi'),
                                params={'qtype' : 'loginname',
                                        'query' : 'renate'})
        testbody = response.body.replace('\n', ' ').replace('\r', '').replace("  ", " ")
        print "token flexi response 2: %r" % response.testbody
        assert '"total": 1' in testbody
        assert '"token3",       true,       "renate"' in testbody

        # only tokens in realm1
        response = self.app.get(url(controller='manage', action='tokenview_flexi'),
                                params={'qtype' : 'realm',
                                        'query' : 'realm1'})
        print "token flexi response 3: %r" % response.testbody
        assert '"total": 2' in response.testbody
        testbody = response.body.replace('\n', ' ').replace('\r', '').replace("  ", " ")
        assert '"token1",       true,       "heinz"' in testbody
        assert '"token2",       true,       "nick"' in testbody

        # search in all columns
        response = self.app.get(url(controller='manage', action='tokenview_flexi'),
                                params={'qtype' : 'all',
                                        'query' : 'token2'})
        print "token flexi response 4: %r" % response.testbody
        assert '"total": 1' in response.testbody
        testbody = response.body.replace('\n', ' ').replace('\r', '').replace("  ", " ")
        assert '"token2",       true,       "nick"' in testbody

        # with wildcard
        response = self.app.get(url(controller='manage', action='tokenview_flexi'),
                                params={"qtype": "loginname",
                                        "query": "r*"})
        testbody = response.body.replace('\n', ' ').replace('\r', '').replace("  ", " ")
        print "=== Testing with wildcard ==="
        print testbody
        assert '"total": 1' in testbody
        assert 'token3' in testbody

    def test_07_userflexi(self):
        '''
        Manage: testing the userview_flexi method
        '''
        # No realm, no user
        response = self.app.get(url(controller='manage', action='userview_flexi'),
                                params={})
        print "user flexi response 1: %r" % response.testbody
        assert '"total": 0' in response.testbody

        # No realm, no user

        response = self.app.get(url(controller='manage', action='userview_flexi'),
                                params={"page" :1,
                                        "rp": 15,
                                        "sortname": "username",
                                        "sortorder": "asc",
                                        "query": "",
                                        "qtype": "username",
                                        "realm": "realm1"})
        print "user flexi response 2: %r" % response.testbody
        assert '"id": "heinz"' in response.testbody


        response = self.app.get(url(controller='manage', action='userview_flexi'),
                                params={"page" :1,
                                        "rp": 15,
                                        "sortname": "username",
                                        "sortorder": "desc",
                                        "query": "",
                                        "qtype": "username",
                                        "realm": "realm2"})
        print "user flexi response 3: %r" % response.testbody
        assert '"id": "renate"' in response.testbody


    def test_08_tokeninfo(self):
        '''
        Manage: Testing tokeninfo dialog
        '''
        response = self.app.get(url(controller='manage', action='tokeninfo'),
                                params={"serial" : "token1"})
        print "tokeninfo response: %r" % response.testbody
        assert 'class=tokeninfoOuterTable' in response.testbody
        assert 'Heinz Hirtz' in response.testbody
        assert 'Heinz Hirtz' in response.testbody
        assert '<td class=tokeninfoOuterTable>privacyIDEA.TokenSerialnumber</td>\n    \t<!-- middle column -->\n    <td class=tokeninfoOuterTable>\n    \ttoken1\n    </td>\n        \t<!-- right column -->' in response.testbody


    def test_09_logout(self):
        '''
        Manage: testing logout
        '''
        response = self.app.get(url(controller='account', action='logout'),
                                params={})
        print "logout response: %r" % response.testbody
        assert u'302 Found' in response.testbody
        
    def test_10_custom_style(self):
        '''
        Manage: testing custom style
        '''
        response = self.app.get(url(controller='manage', action='custom_style'),
                                params={})
        print "custom style: %s" % response.headers
        assert response.headers.get("Content-Type") == "text/css"
