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
log = logging.getLogger(__name__)
import unittest
import os
from privacyidea.lib.freeradiusparser import ClientConfParser

CLIENT_CONF = """# This is a client.conf for freeradius
client localhost {
        ipaddr          = 127.0.0.1
        secret          = testing123
        shortname       = localhost
        nastype         = other
}

client private-network-1 {
        ipaddr          = 192.168.0.0
        netmask         = 24
        secret          = testing123-1
        shortname       = private-network-1
}
"""

CLIENT_CONF_ORIG="""#
# clients.conf - client configuration directives
#
#######################################################################

#######################################################################
#
#  Definition of a RADIUS client (usually a NAS).
#
#  The information given here over rides anything given in the
#  'clients' file, or in the 'naslist' file.  The configuration here
#  contains all of the information from those two files, and allows
#  for more configuration items.
#
#  The "shortname" is be used for logging.  The "nastype", "login" and
#  "password" fields are mainly used for checkrad and are optional.
#

#
#  Defines a RADIUS client.  The format is 'client [hostname|ip-address]'
#
#  '127.0.0.1' is another name for 'localhost'.  It is enabled by default,
#  to allow testing of the server after an initial installation.  If you
#  are not going to be permitting RADIUS queries from localhost, we suggest
#  that you delete, or comment out, this entry.
#
client 127.0.0.1 {
    #
    #  The shared secret use to "encrypt" and "sign" packets between
    #  the NAS and FreeRADIUS.  You MUST change this secret from the
    #  default, otherwise it's not a secret any more!
    #
    #  The secret can be any string, up to 31 characters in length.
    #
    secret        = testing123

    #
    #  The short name is used as an alias for the fully qualified
    #  domain name, or the IP address.
    #
    shortname    = localhost

    #
    # the following three fields are optional, but may be used by
    # checkrad.pl for simultaneous use checks
    #

    #
    # The nastype tells 'checkrad.pl' which NAS-specific method to
    #  use to query the NAS for simultaneous use.
    #
    #  Permitted NAS types are:
    #
    #    cisco
    #    computone
    #    livingston
    #    max40xx
    #    multitech
    #    netserver
    #    pathras
    #    patton
    #    portslave
    #    tc
    #    usrhiper
    #    other        # for all other types

    #
    nastype     = other    # localhost isn't usually a NAS...

    #
    #  The following two configurations are for future use.
    #  The 'naspasswd' file is currently used to store the NAS
    #  login name and password, which is used by checkrad.pl
    #  when querying the NAS for simultaneous use.
    #
#    login       = !root
#    password    = someadminpas
}

#client some.host.org {
#    secret        = testing123
#    shortname    = localhost
#}

#
#  You can now specify one secret for a network of clients.
#  When a client request comes in, the BEST match is chosen.
#  i.e. The entry from the smallest possible network.
#
#client 192.168.0.0/24 {
#    secret        = testing123-1
#    shortname    = private-network-1
#}
#
#client 192.168.0.0/16 {
#    secret        = testing123-2
#    shortname    = private-network-2
#}


#client 10.10.10.10 {
#    # secret and password are mapped through the "secrets" file.
#    secret      = testing123
#    shortname   = liv1
#       # the following three fields are optional, but may be used by
#       # checkrad.pl for simultaneous usage checks
#    nastype     = livingston
#    login       = !root
#    password    = someadminpas
#}


"""

FILEOUTPUT_ORIG = """# File parsed and saved by privacyidea.

client 127.0.0.1 {
    secret = testing123
    shortname = localhost
    nastype = other
}

"""


class TestFreeRADIUSParser(unittest.TestCase):

    def setUp(self):
        pass
    
    def test_clients_conf_simple(self):
        CP = ClientConfParser(content=CLIENT_CONF)
        config = CP.get_dict()
        print config
        self.assertTrue("localhost" in config)
        self.assertTrue("private-network-1" in config)
        self.assertEqual(config.get("private-network-1").get("secret"),
                         "testing123-1")
        self.assertEqual(config.get("private-network-1").get("shortname"),
                         "private-network-1")
        
    def test_clients_conf_original(self):
        CP = ClientConfParser(content=CLIENT_CONF_ORIG)
        config = CP.get_dict()
        print config
        # {'127.0.0.1': {'secret': 'testing123', 'shortname': 'localhost',
        # 'nastype': 'other    '}}
        self.assertTrue("localhost" not in config)
        self.assertTrue("127.0.0.1" in config)
        self.assertEqual(config.get("127.0.0.1").get("secret"),
                         "testing123")
        self.assertEqual(config.get("127.0.0.1").get("nastype"),
                         "other")
        
        output = CP.format(config)
        print output
        self.assertEqual(output, FILEOUTPUT_ORIG)
        
    def test_save_file(self):
        tmpfile = "./tmp-output"
        CP = ClientConfParser(content=CLIENT_CONF_ORIG)
        config = CP.get_dict()
        print config
        CP.save(config, tmpfile)
        f = open(tmpfile, "r")
        output = f.read()
        f.close()
        os.unlink(tmpfile)
        print output

        self.assertEqual(output, FILEOUTPUT_ORIG)
        

if __name__ == '__main__':
    unittest.main()