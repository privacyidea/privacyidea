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


    def test_filter_show(self):
        '''
        Testing the filtering of the machine listing
        '''
        machines = [ "machine1", 
                    "machine2", 
                    "machine3"]
        for m in machines:
            self.app.get(url(controller='admin', action='machinecreate'), {'name' : m})
            
        # list all machines
        response = self.app.get(url(controller='admin', action='machineshow'))
        print response
        assert ("machine1" in response)
        assert ("machine2" in response)
        assert ("machine3" in response)
        
        response = self.app.get(url(controller='admin', action='machineshow'), {'name' : "machine1" })
        print response
        assert ("machine1" in response)
        assert ("machine2" not in response)
        assert ("machine3" not in response)
        
        for m in machines:
            self.app.get(url(controller='admin', action='machinedelete'), {'name' : m })
        
    def test_create_with_description(self):
        '''
        Create a machine with IP and description
        '''
        # cleanup
        self.app.get(url(controller='admin', action='machinedelete'), {'name' : "newmachine"})
                                                                       
        response = self.app.get(url(controller='admin', action='machinecreate'), {'name' : "newmachine",
                                                                                  "ip" : "1.2.3.4",
                                                                                  "desc" : "Some strange machine äää"})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
        response = self.app.get(url(controller='admin', action='machineshow'), {'name' : "newmachine" })
        print response
        # We do not care about the database encoding here
        assert ('Some strange machine' in response)
        
        
        response = self.app.get(url(controller='admin', action='machinedelete'), {'name' : "newmachine"} )
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
    
    def test_machine(self):
        '''Testing creating and deleting client machines'''
        name1 = "machine1"
        name2 = "machine2"
        # cleanup
        self.app.get(url(controller='admin', action='machinedelete'), {'name' : name1})
        
        response = self.app.get(url(controller='admin', action='machinecreate'), {'name' : name1})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
        # Creating the machine a second time should not work!
        response = self.app.get(url(controller='admin', action='machinecreate'), {'name' : name1})
        print response
        assert ('"status": false' in response)
        assert ('column cm_name is not unique' in response)

        response = self.app.get(url(controller='admin', action='machineshow'))
        print response
        assert ('"name": "%s"' % name1 in response)

        # Try to delete a machine, that does not exist
        response = self.app.get(url(controller='admin', action='machinedelete'), {'name' : name2})
        print response
        assert ('"status": true' in response)
        assert ('"value": false' in response)

        # delete a machine, that does exist.
        response = self.app.get(url(controller='admin', action='machinedelete'), {'name' : name1})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

        # list the machines.
        response = self.app.get(url(controller='admin', action='machineshow'))
        print response
        assert ('"name": "%s"' % name1 not in response)
