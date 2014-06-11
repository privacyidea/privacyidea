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

from privacyidea.tests import TestController
from privacyidea.tests import url

import json

import logging
log = logging.getLogger(__name__)


class TestHttpSmsController(TestController):
    '''
    Here the HTTP SMS Gateway functionality is tested.
    '''


    def setUp(self):
        '''
        This sets up all the resolvers and realms
        '''
        TestController.setUp(self)
        self.removeTokens()
        self.initToken()
        self.initProvider()



###############################################################################
    def removeTokens(self):
        for serial in ['sms01', 'sms02']:
            parameters = {'serial':serial}
            response = self.app.get(url(controller='admin', action='remove'),
                                    params=parameters)
            #log.error(response)
            self.assertTrue('"status": true' in response, response)

    def initToken(self):
        '''
        Initialize the tokens
        '''
        parameters = { 'serial' : 'sms01',
                       'otpkey' : '1234567890123456789012345678901234567890' +
                                  '123456789012345678901234',
                       'realm' : 'myDefRealm',
                       'type' : 'sms',
                       'user' : 'user1',
                       'pin' : '1234',
                       'phone' : '016012345678',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='init'),
                                params=parameters)

        self.assertTrue('"status": true' in response, response)

        parameters = { 'serial' : 'sms02',
                       'otpkey' : '1234567890123456789012345678901234567890' +
                                   '123456789012345678901234',
                       'realm' : 'myDefRealm',
                       'user' : 'user2',
                       'type' : 'sms',
                       'pin' : '1234',
                       'phone' : '016022222222',
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='admin', action='init'),
                                                             params=parameters)

        self.assertTrue('"status": true' in response, response)

    def initProvider(self):
        '''
        Initialize the HttpSMSProvider
        '''
        parameters = {
                'SMSProvider' : 'privacyidea.smsprovider.HttpSMSProvider.HttpSMSProvider',
                'selftest_admin' : 'superadmin'
                   }
        response = self.app.get(url(controller='system', action='setConfig'),
                                                             params=parameters)

        self.assertTrue('"status": true' in response, response)

    def last_audit(self, num=3, page=1):
        '''
        Checks the last audit entry
        '''
        # audit/search?sortorder=desc&rp=1
        response = self.app.get(url(controller="audit", action="search"),
                                params={ 'sortorder':'desc',
                                         'rp':num, 'page':page,
                                         'selftest_admin':'superadmin'})
        return response

    def test_0001_send_sms(self):
        '''
        send sms
        '''
        sms_conf = {
                "URL" : "http://localhost:5001/testing/http2sms",
                "PARAMETER" :
                    {"account" : "clickatel", "username" : "legit"},
                "SMS_TEXT_KEY":"text",
                "SMS_PHONENUMBER_KEY":"destination",
                "HTTP_Method" : "GET",
                "RETURN_SUCCESS" : "ID",
                }

        parameters = {
                'SMSProviderConfig' : json.dumps(sms_conf),
                'selftest_admin' : 'superadmin'
                }
        response = self.app.get(url(controller='system', action='setConfig'),
                                params=parameters)

        self.assertTrue('"status": true' in response, response)

        # check the saved configuration
        response = self.app.get(url(controller='system', action='getConfig'),
                                {'key' : 'SMSProviderConfig'})

        self.assertTrue('"status": true' in response, response)
        self.assertTrue('RETURN_SUCCESS' in response, response)
        self.assertTrue('http://localhost:5001/testing/http2sms' in response, 
                        response)

        response = self.app.get(url(controller='validate', action='smspin')
                                , params={'user' : 'user1', 'pass' : '1234'})
        self.assertTrue('"message": "sms submitted",' in response, response)


    def test_02_succesful_auth(self):
        '''
        Successful SMS sending (via smspin) and authentication
        '''
        sms_conf = { "URL" : "http://localhost:5001/testing/http2sms",
                     "PARAMETER" : { "account" : "clickatel",
                                    "username" : "legit" },
                    "SMS_TEXT_KEY":"text",
                    "SMS_PHONENUMBER_KEY":"destination",
                    "HTTP_Method" : "GET",
                    "RETURN_SUCCESS" : "ID"
                    }

        parameters = { 'SMSProviderConfig' : json.dumps(sms_conf),
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setConfig'),
                                params=parameters)

        self.assertTrue('"status": true' in response, response)

        response = self.app.get(url(controller='validate', action='smspin'),
                                params={'user' : 'user1', 'pass' : '1234'})
        self.assertTrue('"state":' in response,
                        "Expecting 'state' as challenge inidcator %r"
                        % response)


        # test authentication
        response = self.app.get(url(controller='validate', action='check'),
                                params={'user' : 'user1',
                                        'pass' : '1234973532'})
        self.assertTrue('"value": true' in response, response)

        return

    def test_03_succesful_auth(self):
        '''
        Successful SMS sending (via validate) and authentication
        '''
        #FIXME smsprovider
        return
        sms_conf = {
            "URL" : "http://localhost:5001/testing/http2sms",
            "PARAMETER" : { "account" : "clickatel", "username" : "legit" },
            "SMS_TEXT_KEY":"text",
            "SMS_PHONENUMBER_KEY":"destination",
            "HTTP_Method" : "GET",
            "RETURN_SUCCESS" : "ID"
        }
        parameters = { 'SMSProviderConfig' : json.dumps(sms_conf),
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setConfig'),
                                                             params=parameters)

        self.assertTrue('"status": true' in response, response)

        response = self.app.get(url(controller='validate', action='check'),
                                params={'user' : 'user1', 'pass' : '1234'})

        # authentication fails but sms is sent
        self.assertTrue('"value": false' in response, response)

        # check last audit entry
        response2 = self.last_audit()
        # must be success == 1
        if '"total": null' not in response2:
            self.assertTrue('''challenge created''' in response2, response2)

        # test authentication
        response = self.app.get(url(controller='validate', action='check'),
                                params={'user' : 'user1',
                                        'pass' : '1234973532'})

        self.assertTrue('"value": true' in response, response)


    def test_04_successful_SMS(self):
        '''
        Successful SMS sending with RETURN_FAILED
        '''
        #FIXME smsprovider
        return
        sms_conf = {
            "URL" : "http://localhost:5001/testing/http2sms",
            "PARAMETER" : { "account" : "clickatel", "username" : "legit" },
            "SMS_TEXT_KEY":"text",
            "SMS_PHONENUMBER_KEY":"destination",
            "HTTP_Method" : "GET",
            "RETURN_FAILED" : "FAILED"
            }
        parameters = { 'SMSProviderConfig' : json.dumps(sms_conf),
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setConfig'),
                                                            params=parameters)

        self.assertTrue('"status": true' in response, response)

        response = self.app.get(url(controller='validate', action='smspin'),
                                params={'user' : 'user1',
                                        'pass' : '1234'})

        self.assertTrue('"state"' in response, response)

        return

    def test_05_failed_SMS(self):
        '''
        Failed SMS sending with RETURN_FAIL
        '''
        #FIXME smsprovider
        return
        sms_conf = { "URL" : "http://localhost:5001/testing/http2sms",
            "PARAMETER" : {"account" : "clickatel", "username" : "anotherone"},
            "SMS_TEXT_KEY":"text",
            "SMS_PHONENUMBER_KEY":"destination",
            "HTTP_Method" : "GET",
            "RETURN_FAIL" : "FAILED"
        }

        parameters = { 'SMSProviderConfig' : json.dumps(sms_conf),
                       'selftest_admin' : 'superadmin'
                      }
        response = self.app.get(url(controller='system', action='setConfig'),
                                                            params=parameters)

        self.assertTrue('"status": true' in response, response)

        response = self.app.get(url(controller='validate', action='smspin'),
                                params={'user' : 'user1',
                                        'pass' : '1234'})

        self.assertTrue('Failed to send SMS. We received a'
                        ' predefined error from the SMS Gateway.' in response)

        return

###eof#########################################################################

