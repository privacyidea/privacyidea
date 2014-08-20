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
import json
import binascii

log = logging.getLogger(__name__)


class TestMachineController(TestController):

    def _create_yubikeys(self,
                         serials=["UBOM123456_1",
                                  "UBOM234567_1"],
                         machine="machine1",
                         ip="10.0.0.1",
                         otpkey="a60f076ca60e6d966f3bdcdc96f5e94c3c8efc32"):
        client = ip
        machine1 = machine
        self._create_machine(machine1,
                             ip=client)
        # create two tokens for the one machine
        for serial in serials:
            param = {'type': 'yubikey',
                     'serial': serial,
                     'otpkey': otpkey,
                     'otplen': 8,
                     'type': "TOTP"}
            response = self.app.get(url(controller='admin', action='init'),
                                    params=param)
            print response
            assert '"value": true' in response
            
    def _delete_yubikeys(self,
                         serials=["UBOM123456_1",
                                  "UBOM234567_1"],
                         machine="machine1"):
        self._delete_machine(machine)
        for serial in serials:
            self._delete_token(serial)
        
    def _create_token(self, serial=None):
        # create a token and add this new token to the machine
        response = self.app.get(url(controller='admin', action='init'),
                                {'type': "spass",
                                 "serial": serial,
                                 "pin": "123454"})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

    def _delete_token(self, serial=None):
        # create a token and add this new token to the machine
        response = self.app.get(url(controller='admin', action='remove'),
                                {"serial": serial})
        print response
        assert ('"status": true' in response)
        assert ('"value": 1' in response)

    def _create_machine(self, name, ip=None, desc=None, decommission=None,
                        admin=None):
        response = self.app.get(url(controller='machine', action='create'),
                                {'name': name,
                                 "ip": ip,
                                 "desc": desc,
                                 "decommission": decommission,
                                 "selftest_admin": admin})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

    def _delete_machine(self, name, ip=None, desc=None, decommission=None):
        response = self.app.get(url(controller='machine', action='delete'),
                                {'name': name})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

    def _add_token(self, name, serial, app):
        response = self.app.get(url(controller='machine', action='addtoken'),
                                {'name': name,
                                 'serial': serial,
                                 'application': app})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

    def _rm_token(self, name, serial, app):
        response = self.app.get(url(controller='machine', action='deltoken'),
                                {'name': name,
                                 'serial': serial,
                                 'application': app})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)

    def test_filter_show(self):
        '''
        Testing the filtering of the machine listing
        '''
        machines = {"machine1": "1.2.3.4",
                    "machine2": "1.2.3.5",
                    "machine3": "1.2.3.6"}
        for m in machines.keys():
            self._create_machine(name=m, ip=machines[m])

        # list all machines
        response = self.app.get(url(controller='machine', action='show'))
        print response
        assert ("machine1" in response)
        assert ("machine2" in response)
        assert ("machine3" in response)

        response = self.app.get(url(controller='machine', action='show'),
                                {'name': "machine1"})
        print response
        assert ("machine1" in response)
        assert ("machine2" not in response)
        assert ("machine3" not in response)

        for m in machines.keys():
            self._delete_machine(name=m)

    def test_create_with_description(self):
        '''
        Create a machine with IP and description
        '''
        self._create_machine(name="newmachine",
                             ip="1.2.3.4",
                             desc="Some strange machine äää")

        response = self.app.get(url(controller='machine', action='show'),
                                {'name': "newmachine"})
        print response
        # We do not care about the database encoding here
        assert ('Some strange machine' in response)

        self._delete_machine(name="newmachine")

    def test_machine(self):
        '''Testing creating and deleting client machines'''
        name1 = "machine1"
        name2 = "machine2"
        ip1 = "2.3.4.5"

        self._create_machine(name1, ip1)

        # Creating the machine a second time should not work!
        response = self.app.get(url(controller='machine', action='create'),
                                {'name': name1,
                                 'ip': ip1})
        print response
        assert ('"status": false' in response)
        assert ('UNIQUE' in response or "IntegrityError" in response)

        response = self.app.get(url(controller='machine', action='show'))
        print response
        assert ('"name": "%s"' % name1 in response)

        # Try to delete a machine, that does not exist
        response = self.app.get(url(controller='machine', action='delete'),
                                {'name': name2})
        print response
        assert ('"status": false' in response)
        assert ('There is no machine with name=' in response)

        # delete a machine, that does exist.
        self._delete_machine(name1)

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

        self._create_machine(name=name1)
        # adding a token that does not exist will not work
        response = self.app.get(url(controller='machine', action='addtoken'),
                                {'name': name1,
                                 'serial': token1,
                                 'application': "ssh"})
        print response
        assert ('"status": false' in response)
        assert ('There is no token with the serial number' in response)

        self._create_token(serial=token1)

        self._add_token(name1, token1, "ssh")
        # try to add the same again
        response = self.app.get(url(controller='machine', action='addtoken'),
                                {'name': name1,
                                 'serial': token1,
                                 'application': "ssh"})
        print response
        assert ('"status": false' in response)
        assert ('UNIQUE' in response or "IntegrityError" in response)

        # add another application
        self._add_token(name1, token1, "luks")

        # show machinetoken
        response = self.app.get(url(controller='machine', action='showtoken'),
                                {})
        print "SHOWTOKEN: "
        print response
        assert ('"status": true' in response)
        assert ('"application": "ssh"' in response)
        assert ('"application": "luks"' in response)

        # delete the machines
        for app in ["ssh", "luks"]:
            self._rm_token(name1, token1, app)
        self._delete_token(token1)
        self._delete_machine(name1)

    def test_delete_token(self):
        '''
        Delete a token, that is assigned to a machine
        '''
        name1 = "machineA"
        token1 = "tokABCD"

        # create the machine
        self._create_machine(name1)
        # create the token
        self._create_token(token1)

        # add the token to the machine
        self._add_token(name1, token1, "ssh")

        # show machinetoken
        response = self.app.get(url(controller='machine', action='showtoken'),
                                {})
        print response
        assert ('"status": true' in response)
        assert ('"application": "ssh"' in response)

        # delete the token --- the machine-token binding will also be deleted!
        self._delete_token(token1)
        self._delete_machine(name1)

    def test_output(self):
        """
        Test the json output of the machine-token-config.
        """
        import json
        response = self.app.get(url(controller='machine', action='showtoken'),
                                {})
        data = json.loads(response.body)
        result = data.get("result")
        print result
        assert result.get("status") is True
        start_token_num = int(result.get("value", {}).get("total", 0))
        
        self._create_token("t1")
        self._create_token("t2")
        self._create_token("t3")
        self._create_token("t4")

        self._create_machine(name="m1", ip="1.2.3.4")
        self._create_machine(name="m2", ip="1.2.3.5")
        self._create_machine(name="m3", ip="1.2.3.6")
        self._create_machine(name="m4", ip="1.2.3.7")

        self._add_token("m1", "t1", "SSH")
        self._add_token("m1", "t2", "SSH")
        self._add_token("m1", "t3", "SSH")
        self._add_token("m2", "t1", "SSH")
        self._add_token("m3", "t2", "SSH")
        self._add_token("m4", "t3", "SSH")

        # show machinetoken
        response = self.app.get(url(controller='machine', action='showtoken'),
                                {})
        print response
        assert ('"status": true' in response)
        assert ('"application": "SSH"' in response)
        
        data = json.loads(response.body)
        result = data.get("result")
        print result
        assert result.get("status") is True
        end_token_num = int(result.get("value", {}).get("total", 0))
        assert (end_token_num - start_token_num == 6)

        self._rm_token("m1", "t1", "SSH")
        self._rm_token("m1", "t2", "SSH")
        self._rm_token("m1", "t3", "SSH")
        self._rm_token("m2", "t1", "SSH")
        self._rm_token("m3", "t2", "SSH")
        self._rm_token("m4", "t3", "SSH")

        self._delete_machine(name="m1")
        self._delete_machine(name="m2")
        self._delete_machine(name="m3")
        self._delete_machine(name="m4")

        self._delete_token("t1")
        self._delete_token("t2")
        self._delete_token("t3")
        self._delete_token("t4")

    def test_decommission(self):
        """
        Testing machine decommission date
        """
        self._create_machine("tokDec", decommission="2014-12-31")
        self._delete_machine("tokDec")

    def test_wrong_token_and_wrong_machine(self):
        """
        Testing adding non existing token to non existing machine must fail
        """
        response = self.app.get(url(controller='machine', action='addtoken'),
                                {'name': "no_machine",
                                 'serial': "no_token",
                                 'application': "luks"})
        print response
        assert ('"status": false' in response)
        assert ('There is no machine with name' in response)

    def test_with_policies(self):
        """
        Testing machine management with policies
        """
        serial = "tok1_machine"
        machine1 = "mach1"
        machine2 = "mach2"
        self._create_token(serial)
        self._create_machine(machine1, ip="10.0.0.1")

        parameters = {'name': 'ManageAll',
                      'scope': 'machine',
                      'action': 'create, delete, addtoken, gettokenapps',
                      'realm': "*",
                      'user': 'superadmin',
                      'selftest_admin': 'superadmin'}
        response = self.app.get(url(controller='system', action='setPolicy'),
                                params=parameters)
        log.error(response)
        assert '"status": true' in response

        response = self.app.get(url(controller='machine', action='create'),
                                {'name': "newmachine",
                                 'ip': '2.3.4.5',
                                 'selftest_admin': 'looser'})
        print response
        assert "You do not have the right to manage machines" in response

        self._create_machine(machine2, ip='10.0.0.2', admin="superadmin")

        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                params={})
        print response
        assert '"status": true' in response

        # delete the policy
        parameters = {'name': 'ManageAll',
                      'selftest_admin': 'superadmin'}
        response = self.app.get(url(controller='system', action='delPolicy'),
                                params=parameters)
        log.error(response)
        assert '"status": true' in response

        self._delete_machine(machine1)
        self._delete_machine(machine2)
        self._delete_token(serial)

    def test_get_tokenapps(self):
        '''
        testing retrieving apps for a machine
        '''
        machine1 = "mach101"
        machine2 = "mach102"
        serial = "tok102"
        self._create_token(serial)
        self._create_machine(machine1, ip="10.0.0.1")
        self._create_machine(machine2, ip="10.0.0.2")
        self._add_token(machine1, serial, "ssh")
        self._add_token(machine1, serial, "luks")
        self._add_token(machine2, serial, "ssh")
        
        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                params={"name": machine1,
                                        "client": "10.0.0.1"})
        print "=============="
        print "Get token apps"
        print "=============="
        print response
        print "=============="
        assert '"total": 2' in response
        assert '"application": "ssh",' in response
        assert '"application": "luks",' in response
        
        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                params={"name": machine1,
                                        "client": "10.0.0.1",
                                        "application": "luks"})
        print response
        assert '"total": 1' in response
        assert '"application": "luks",' in response
        
        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                params={"name": machine1,
                                        "client": "10.0.0.2",
                                        "application": "luks"})
        print response
        assert '"status": false' in response
        assert 'There is no machine with name' in response
        
        self._rm_token(machine2, serial, "ssh")
        self._rm_token(machine1, serial, "luks")
        self._rm_token(machine1, serial, "ssh")
        self._delete_token(serial)
        self._delete_machine(machine1)
        self._delete_machine(machine2)
        
    def test_fail_wrong_app(self):
        '''
        testing a wrong app will not assign
        '''
        machine1 = "mach1"
        serial = "tok2_machine"
        app = "does not exist"
        self._create_token(serial)
        self._create_machine(machine1)
        response = self.app.get(url(controller="machine",
                                    action="addtoken"),
                                params={"name": machine1,
                                        "application": app,
                                        "serial": serial})
        print response
        assert "Unkown application" in response
        
        self._delete_machine(machine1)
        self._delete_token(serial)
        
    def test_nist_pub_198_a_2(self):
        """
        Yubikey test vector
        http://opensource.yubico.com/yubikey-personalization/ykchalresp.1.html
        """
        machine = "toms_key"
        serial = "UBOM_toms_token"
        app = "luks"
        ip = "10.0.0.1"
        otpkey = "303132333435363738393a3b3c3d3e3f40414243"
        challenge = "Sample #2"
        result_hex = "0922d3405faa3d194f82a45830737d5cc6c75d24"
        self._create_yubikeys(serials=[serial],
                              machine=machine,
                              ip=ip,
                              otpkey=otpkey)
        self._add_token(machine, serial, app)
        print "==================== gettokenapps for yubikey ============"
        # get all auth_items for LUKS on machine without serial number
        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                {"name": machine,
                                 "application": app,
                                 "serial": serial,
                                 "client": ip,
                                 "challenge": binascii.hexlify(challenge)})
        print response
        assert result_hex in response
        self._delete_token(serial)
        self._delete_machine(machine)
        
    def test_get_authentication_items(self):
        '''
        get authentication items
        '''
        serials = ["UBOM123456_1", "UBOM234567_1"]
        machine = "machine1"
        ip = "10.0.0.1"
        chal_hex = "d1835d598bc20c4ce8312ba94f046a015f7a70c48631b88f29922f1183e77873"
        resp_hex = "c7f7a081d06a738f913dce36b538091adc6d2e93"
        app = "luks"
        self._create_yubikeys(serials=serials,
                              machine=machine,
                              ip=ip)
        for serial in serials:
            self._add_token(machine, serial, app)
        
        # get all auth_items for LUKS on machine without serial number
        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                params={"name": machine,
                                        "application": app,
                                        "client": ip,
                                        "challenge": chal_hex})
        print "============"
        print "gettokenapps"
        print "============"
        print response
        
        assert '"auth_item":' in response
        assert '"challenge": "%s"' % chal_hex in response
        assert '"response": "%s"' % resp_hex in response
        assert '"serial": "UBOM123456_1",' in response
        assert '"serial": "UBOM234567_1",' in response
        assert '"application": "luks",' in response
        
        self._delete_yubikeys(serials=serials)
        
    def test_add_machine_options(self):
        '''
        Adding MachineTokenOptions, slot for LUKS app...
        '''
        serials = ["UBOM123456_1", "UBOM234567_1"]
        machine = "machine1"
        ip = "10.0.0.1"
        app = "luks"
        self._create_yubikeys(serials=serials,
                              machine=machine,
                              ip=ip)

        response = self.app.get(url(controller='machine', action='addtoken'),
                                {'name': machine,
                                 'serial': serials[0],
                                 'application': app,
                                 'option_slot': 2})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                params={"name": machine,
                                        "application": app,
                                        "client": ip})
        print "============"
        print "slot options"
        print "============"
        print response
        
        assert '"option_slot": "2"' in response
        
        self._delete_yubikeys(serials=serials)

    def test_add_and_remove_options(self):
        """
        Add and remove options from a machinetoken definition
        """
        serials = ["UBOM123456_1", "UBOM234567_1"]
        machine = "machine1"
        ip = "10.0.0.1"
        app = "luks"
        self._create_yubikeys(serials=serials,
                              machine=machine,
                              ip=ip)
        # add a token
        response = self.app.get(url(controller='machine', action='addtoken'),
                                {'name': machine,
                                 'serial': serials[1],
                                 'application': app})
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        # determine the machinetoken_id
        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                params={"name": machine,
                                        "application": app,
                                        "client": ip})
        data = json.loads(response.body)
        print response
        assert "UBOM234567_1" in response
        
        print "=========== Add option ==============="
        mtid = data.get("result").get("value").get("machines").keys()[0]
        # add the option
        response = self.app.get(url(controller="machine", action="addoption"),
                                params={"mtid": mtid,
                                        "option_slot": 5})
        print response
        assert ('"status": true' in response)
        assert ('"value": 1' in response)
        
        print "=========== Check options ==============="
        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                params={"name": machine,
                                        "application": app,
                                        "client": ip})
        print response
        assert '"option_slot": "5"' in response
        
        print "====== delete option ====================="
        response = self.app.get(url(controller="machine", action="deloption"),
                                params={"mtid": mtid,
                                        "key": "option_slot"})
        print response
        assert ('"status": true' in response)
        assert ('"value": true' in response)
        
        print "=========== Check options ==============="
        response = self.app.get(url(controller='machine',
                                    action='gettokenapps'),
                                params={"name": machine,
                                        "application": app,
                                        "client": ip})
        print response
        assert '"option_slot": "5"' not in response
        # cleanup
        self._delete_yubikeys(serials=serials)
        
    def test_delete_token_withoptions(self):
        name1 = "mach1"
        ip1 = "1.2.3.4"
        serial = "123456"
        self._create_machine(name1, ip1)
        self._create_token(serial)
        
        self._add_token(name1, serial, "ssh")
        response = self.app.get(url(controller="machine", action="addoption"),
                                params={"name": name1,
                                        "serial": serial,
                                        "application": "ssh",
                                        "option_user": "root"})
        print response
        assert('"status": true' in response)
        assert('"value": 1' in response)
        
        # Now, we can successfully delete the token!
        response = self.app.get(url(controller="machine", action="deltoken"),
                                params={"name": name1,
                                        "serial": serial,
                                        "application": "ssh"})
        print response
        assert('"status": true' in response)
        assert('"value": true' in response)
        
        self._delete_token(serial)
        self._delete_machine(name1)