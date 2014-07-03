# -*- coding: utf-8 -*-
#
#    privacyIDEA Account test suite
# 
#    Copyright (C)  2014 Cornelius Kölbel, cornelius@privacyidea.org
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from privacyidea.tests import TestController, url


log = logging.getLogger(__name__)

class TestAccountController(TestController):

    def _create_token(self, serial=None):
        # create a token and add this new token to the machine
        response = self.app.get(url(controller='admin', action='init'), {'type' : "spass",
                                                                           "serial" : serial,
                                                                           "pin" :  "123454"})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

    def _create_machine(self, name, ip=None, desc=None, decommission=None):
        response = self.app.get(url(controller='machine', action='create'), {'name' : name,
                                                                                  "ip" : ip,
                                                                                  "desc" : desc,
                                                                                  "decommission" : decommission})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
    def _add_token(self, name, serial, app):
        response = self.app.get(url(controller='machine', action='addtoken'), {'name' : name,
                                                                               'serial' : serial,
                                                                               'application' : app})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

    def test_filter_show(self):
        '''
        Testing the filtering of the machine listing
        '''
        machines = [ "machine1", 
                    "machine2", 
                    "machine3"]
        for m in machines:
            self.app.get(url(controller='machine', action='create'), {'name' : m})
            
        # list all machines
        response = self.app.get(url(controller='machine', action='show'))
        print response
        assert ("machine1" in response)
        assert ("machine2" in response)
        assert ("machine3" in response)
        
        response = self.app.get(url(controller='machine', action='show'), {'name' : "machine1" })
        print response
        assert ("machine1" in response)
        assert ("machine2" not in response)
        assert ("machine3" not in response)
        
        for m in machines:
            self.app.get(url(controller='machine', action='delete'), {'name' : m })
        
    def test_create_with_description(self):
        '''
        Create a machine with IP and description
        '''
        # cleanup
        self.app.get(url(controller='machine', action='delete'), {'name' : "newmachine"})
                                            
        self._create_machine(name = "newmachine",
                             ip = "1.2.3.4",
                             desc = "Some strange machine äää")                           
        
        
        response = self.app.get(url(controller='machine', action='show'), {'name' : "newmachine" })
        print response
        # We do not care about the database encoding here
        assert ('Some strange machine' in response)
        
        
        response = self.app.get(url(controller='machine', action='delete'), {'name' : "newmachine"} )
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
    
    def test_machine(self):
        '''Testing creating and deleting client machines'''
        name1 = "machine1"
        name2 = "machine2"
        # cleanup
        self.app.get(url(controller='machine', action='delete'), {'name' : name1})
        
        response = self.app.get(url(controller='machine', action='create'), {'name' : name1})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
        # Creating the machine a second time should not work!
        response = self.app.get(url(controller='machine', action='create'), {'name' : name1})
        print response
        assert ('"status": false' in response)
        assert ('column cm_name is not unique' in response)

        response = self.app.get(url(controller='machine', action='show'))
        print response
        assert ('"name": "%s"' % name1 in response)

        # Try to delete a machine, that does not exist
        response = self.app.get(url(controller='machine', action='delete'), {'name' : name2})
        print response
        assert ('"status": true' in response)
        assert ('"value": false' in response)

        # delete a machine, that does exist.
        response = self.app.get(url(controller='machine', action='delete'), {'name' : name1})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

        # list the machines.
        response = self.app.get(url(controller='machine', action='show'))
        print response
        assert ('"name": "%s"' % name1 not in response)

    def test_add_token(self):
        '''
        Adding token to a machine
        '''
        name1 = "tokenmachine"
        token1 = "tok123456"
        # cleanup
        self.app.get(url(controller='machine', action='delete'), {'name' : name1})
        
        response = self.app.get(url(controller='machine', action='create'), {'name' : name1})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
        # Creating the machine a second time should not work!
        response = self.app.get(url(controller='machine', action='addtoken'), {'name' : name1,
                                                                               'serial' : token1,
                                                                               'application' : "app"})
        print response
        assert ('"status": false' in response)
        assert ('There is no token with the serial number' in response)
        
        self._create_token(serial=token1)
        
        response = self.app.get(url(controller='machine', action='addtoken'), {'name' : name1,
                                                                               'serial' : token1,
                                                                               'application' : "app"})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
        # try to add the same again
        response = self.app.get(url(controller='machine', action='addtoken'), {'name' : name1,
                                                                               'serial' : token1,
                                                                               'application' : "app"})
        print response
        assert ('"status": false' in response)
        assert ('columns token_id, machine_id, application are not unique' in response)
        
        # add another application
        response = self.app.get(url(controller='machine', action='addtoken'), {'name' : name1,
                                                                               'serial' : token1,
                                                                               'application' : "app2"})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
        # show machinetoken
        response = self.app.get(url(controller='machine', action='showtoken'), {})
        print response
        assert ('"status": true' in response)
        assert ('"application": "app"' in response)
        assert ('"application": "app2"' in response)
        
        # delete the machines
        for app in ["app", "app2"]:
            response = self.app.get(url(controller='machine', action='deltoken'), {'name' : name1,
                                                                                   'serial' : token1,
                                                                                   'application' : app})
            print response
            assert ('"status": true' in response)
            assert ('"value": true' in response)
            
            
    def test_delete_token(self):
        '''
        Delete a token, that is assigned to a machine
        '''    
        name1 = "machineA"
        token1 = "tokABCD"
        
        # create the machine
        response = self.app.get(url(controller='machine', action='create'), {'name' : name1})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

        # create the token
        self._create_token(token1)
        
        # add the token to the machine
        response = self.app.get(url(controller='machine', action='addtoken'), {'name' : name1,
                                                                               'serial' : token1,
                                                                               'application' : "app3"})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
        # show machinetoken
        response = self.app.get(url(controller='machine', action='showtoken'), {})
        print response
        assert ('"status": true' in response)
        assert ('"application": "app3"' in response)
        
        # delete the token
        response = self.app.get(url(controller='admin', action='remove'), {"serial" : token1})
        print response
        assert ('"status": true' in response)
        assert ('"value": 1' in response)
        
        # show machinetoken
        response = self.app.get(url(controller='machine', action='showtoken'), {})
        print response
        assert ('"status": true' in response)
        assert ('"application": "app3"' not in response)
        
    def test_output(self):
        """
        Test the json output of the machine-token-config.
        """
        self._create_token("t1")
        self._create_token("t2")
        self._create_token("t3")
        self._create_token("t4")
        
        self._create_machine(name="m1")
        self._create_machine(name="m2")
        self._create_machine(name="m3")
        
        self._add_token("m1", "t1", "App")
        self._add_token("m1", "t2", "App")
        self._add_token("m1", "t3", "App")
        self._add_token("m2", "t1", "App")
        self._add_token("m3", "t2", "App")
        self._add_token("m4", "t3", "App")
        
        # show machinetoken
        response = self.app.get(url(controller='machine', action='showtoken'), {})
        print response
        assert ('"status": true' in response)
        assert ('"application": "App"' in response)
        assert ('"6": {' in response)
        assert ('"total": 6' in response)
        
    def test_decommission(self):
        """
        Testing machine decommission date
        """
        self._create_machine("tokDec", decommission="2014-12-31")