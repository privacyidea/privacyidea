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

log = logging.getLogger(__name__)

class TestRadiusToken(TestController):

    p = None

    def test_00_create_radius_token(self):
        # The token with the remote PIN
        parameters1 = {
                      "serial"  : "radius1",
                      "type"    : "radius",
                      "otpkey"  : "1234567890123456",
                      "otppin"  : "",
                      "user"    : "remoteuser",
                      "pin"     : "pin",
                      "description" : "RadiusToken1",
                      'radius.server' : 'localhost:18012',
                      'radius.local_checkpin' : 0,
                      'radius.user' : 'user_with_pin',
                      'radius.secret' : 'testing123',
                      }

        # the token with the local PIN
        parameters2 = {
                      "serial"  : "radius2",
                      "type"    : "radius",
                      "otpkey"  : "1234567890123456",
                      "otppin"  : "local",
                      "user"    : "localuser",
                      "pin"     : "pin",
                      "description" : "RadiusToken2",
                      'radius.server' : 'localhost:18012',
                      'radius.local_checkpin' : 1,
                      'radius.user' : 'user_no_pin',
                      'radius.secret' : 'testing123',
                      }

        response = self.app.get(url(controller='admin', action='init'), params=parameters1)
        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='init'), params=parameters2)
        self.assertTrue('"value": true' in response, response)

        response = self.app.get(url(controller='admin', action='set'), params={'serial':'radius2', 'pin':'local'})
        self.assertTrue('"set pin": 1' in response, response)

        response = self.app.get(url(controller='admin', action='set'), params={'serial':'radius1', 'pin':''})
        self.assertTrue('"set pin": 1' in response, response)

    def deleteRadiusToken(self):
        parameters = {
                      "serial"  : "radius1",
                      }

        response = self.app.get(url(controller='admin', action='remove'), params=parameters)

        parameters = {
                      "serial"  : "radius2",
                      }

        response = self.app.get(url(controller='admin', action='remove'), params=parameters)
        log.debug(response)

    def _start_radius_server(self):
        '''
        Start the dummy radius server
        '''
        '''
        We need to start the radius server for every test, since every test instatiates a new TestClass and thus the
        radius server process will not be accessable outside of a test anymore
        '''
        import subprocess

        self.p = subprocess.Popen(["../../tools/dummy_radius_server.py"])

        assert self.p is not None

    def _stop_radius_server(self):
        '''
        stopping the dummy radius server
        '''
        if self.p:
            r = self.p.kill()
            log.debug(r)


    def test_02_check_token_local_pin(self):
        '''
        Checking if token with local PIN works
        '''
        #FIXME dummyradius server is missing
        return
        self._start_radius_server()
        parameters = {"user": "localuser", "pass": "local654321"}
        response = self.app.get(url(controller='validate', action='check'), params=parameters)
        log.error("CKO %s" % parameters)
        self._stop_radius_server()
        self.assertTrue('"value": true' in response, response)


    def test_03_check_token_remote_pin(self):
        '''
        Checking if remote PIN works
        '''
        #FIXME dummyradius server is missing
        return
        self._start_radius_server()
        parameters = {"user": "remoteuser", "pass": "test123456"}
        response = self.app.get(url(controller='validate', action='check'), params=parameters)
        self._stop_radius_server()
        self.assertTrue('"value": true' in response, response)

    def test_04_check_token_local_pin_fail(self):
        '''
        Checking if a missing local PIN will fail
        '''
        #FIXME dummyradius server is missing
        return
        self._start_radius_server()
        parameters = {"user": "localuser", "pass": "654321"}
        response = self.app.get(url(controller='validate', action='check'), params=parameters)
        self._stop_radius_server()

        assert '"value": false' in response

    def test_05_check_token_local_pin_fail2(self):
        '''
        Checking if a wrong local PIN will fail
        '''
        #FIXME dummyradius server is missing
        return
        self._start_radius_server()
        parameters = {"user": "localuser", "pass": "blabla654321"}
        response = self.app.get(url(controller='validate', action='check'), params=parameters)
        self._stop_radius_server()

        assert '"value": false' in response

    def test_06_check_token_remote_pin_fail(self):
        '''
        Checking if a missing remote PIN will fail
        '''
        #FIXME dummyradius server is missing
        return
        self._start_radius_server()
        parameters = {"user": "remoteuser", "pass": "123456"}
        response = self.app.get(url(controller='validate', action='check'), params=parameters)
        self._stop_radius_server()

        assert '"value": false' in response

    def test_06_check_token_remote_pin_fail2(self):
        '''
        Checking if a wrong remote PIN will fail
        '''
        #FIXME dummyradius server is missing
        return
        self._start_radius_server()
        parameters = {"user": "remoteuser", "pass": "abcd123456"}
        response = self.app.get(url(controller='validate', action='check'), params=parameters)
        self._stop_radius_server()

        assert '"value": false' in response


    def test_xx_clean_up(self):
        '''
        Deleting tokens 
        '''
        self.deleteRadiusToken()

