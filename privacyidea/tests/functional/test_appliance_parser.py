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
from privacyidea.lib.freeradiusparser import UserConfParser

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

USER_CONF_A = """
DEFAULT Auth-Type := perl
"""

USER_CONF_B = """
administrator Cleartext-Password := "secret"
"""

USER_CONF_C = """
user somekey == value
"""
USER_CONF_D = """
DEFAULT    Hint == "SLIP"
    Framed-Protocol = SLIP
"""

USER_CONF_E = """
DEFAULT    Hint == "SLIP"
    Framed-Protocol = SLIP,
    Something = Else
"""

USER_CONF_1 = """
#
#    Please read the documentation file ../doc/processing_users_file,
#    or 'man 5 users' (after installing the server) for more information.
#
#    This file contains authentication security and configuration
#    information for each user.  Accounting requests are NOT processed
#    through this file.  Instead, see 'acct_users', in this directory.
#
#    The first field is the user's name and can be up to
#    253 characters in length.  This is followed (on the same line) with
#    the list of authentication requirements for that user.  This can
#    include password, comm server name, comm server port number, protocol
#    type (perhaps set by the "hints" file), and huntgroup name (set by
#    the "huntgroups" file).
#
#    If you are not sure why a particular reply is being sent by the
#    server, then run the server in debugging mode (radiusd -X), and
#    you will see which entries in this file are matched.
#
#    When an authentication request is received from the comm server,
#    these values are tested. Only the first match is used unless the
#    "Fall-Through" variable is set to "Yes".
#
#    A special user named "DEFAULT" matches on all usernames.
#    You can have several DEFAULT entries. All entries are processed
#    in the order they appear in this file. The first entry that
#    matches the login-request will stop processing unless you use
#    the Fall-Through variable.
#
#    If you use the database support to turn this file into a .db or .dbm
#    file, the DEFAULT entries _have_ to be at the end of this file and
#    you can't have multiple entries for one username.
#
#    Indented (with the tab character) lines following the first
#    line indicate the configuration values to be passed back to
#    the comm server to allow the initiation of a user session.
#    This can include things like the PPP configuration values
#    or the host to log the user onto.
#
#    You can include another `users' file with `$INCLUDE users.other'
#

#
#    For a list of RADIUS attributes, and links to their definitions,
#    see:
#
#    http://www.freeradius.org/rfc/attributes.html
#

#
# Deny access for a specific user.  Note that this entry MUST
# be before any other 'Auth-Type' attribute which results in the user
# being authenticated.
#
# Note that there is NO 'Fall-Through' attribute, so the user will not
# be given any additional resources.
#
#lameuser    Auth-Type := Reject
#        Reply-Message = "Your account has been disabled."

#
# Deny access for a group of users.
#
# Note that there is NO 'Fall-Through' attribute, so the user will not
# be given any additional resources.
#
#DEFAULT    Group == "disabled", Auth-Type := Reject
#        Reply-Message = "Your account has been disabled."
#

#
# This is a complete entry for "steve". Note that there is no Fall-Through
# entry so that no DEFAULT entry will be used, and the user will NOT
# get any attributes in addition to the ones listed here.
#
#steve    Cleartext-Password := "testing"
#    Service-Type = Framed-User,
#    Framed-Protocol = PPP,
#    Framed-IP-Address = 172.16.3.33,
#    Framed-IP-Netmask = 255.255.255.0,
#    Framed-Routing = Broadcast-Listen,
#    Framed-Filter-Id = "std.ppp",
#    Framed-MTU = 1500,
#    Framed-Compression = Van-Jacobsen-TCP-IP

#
# This is an entry for a user with a space in their name.
# Note the double quotes surrounding the name.
#
#"John Doe"    Cleartext-Password := "hello"
#        Reply-Message = "Hello, %{User-Name}"

#
# Dial user back and telnet to the default host for that port
#
#Deg    Cleartext-Password := "ge55ged"
#    Service-Type = Callback-Login-User,
#    Login-IP-Host = 0.0.0.0,
#    Callback-Number = "9,5551212",
#    Login-Service = Telnet,
#    Login-TCP-Port = Telnet

#
# Another complete entry. After the user "dialbk" has logged in, the
# connection will be broken and the user will be dialed back after which
# he will get a connection to the host "timeshare1".
#
#dialbk    Cleartext-Password := "callme"
#    Service-Type = Callback-Login-User,
#    Login-IP-Host = timeshare1,
#    Login-Service = PortMaster,
#    Callback-Number = "9,1-800-555-1212"

#
# user "swilson" will only get a static IP number if he logs in with
# a framed protocol on a terminal server in Alphen (see the huntgroups file).
#
# Note that by setting "Fall-Through", other attributes will be added from
# the following DEFAULT entries
#
#swilson    Service-Type == Framed-User, Huntgroup-Name == "alphen"
#        Framed-IP-Address = 192.168.1.65,
#        Fall-Through = Yes

#
# If the user logs in as 'username.shell', then authenticate them
# using the default method, give them shell access, and stop processing
# the rest of the file.
#
#DEFAULT    Suffix == ".shell"
#        Service-Type = Login-User,
#        Login-Service = Telnet,
#        Login-IP-Host = your.shell.machine


#
# The rest of this file contains the several DEFAULT entries.
# DEFAULT entries match with all login names.
# Note that DEFAULT entries can also Fall-Through (see first entry).
# A name-value pair from a DEFAULT entry will _NEVER_ override
# an already existing name-value pair.
#

#
# Set up different IP address pools for the terminal servers.
# Note that the "+" behind the IP address means that this is the "base"
# IP address. The Port-Id (S0, S1 etc) will be added to it.
#
#DEFAULT    Service-Type == Framed-User, Huntgroup-Name == "alphen"
#        Framed-IP-Address = 192.168.1.32+,
#        Fall-Through = Yes

#DEFAULT    Service-Type == Framed-User, Huntgroup-Name == "delft"
#        Framed-IP-Address = 192.168.2.32+,
#        Fall-Through = Yes

#
# Sample defaults for all framed connections.
#
#DEFAULT    Service-Type == Framed-User
#    Framed-IP-Address = 255.255.255.254,
#    Framed-MTU = 576,
#    Service-Type = Framed-User,
#    Fall-Through = Yes

#
# Default for PPP: dynamic IP address, PPP mode, VJ-compression.
# NOTE: we do not use Hint = "PPP", since PPP might also be auto-detected
#    by the terminal server in which case there may not be a "P" suffix.
#    The terminal server sends "Framed-Protocol = PPP" for auto PPP.
#
DEFAULT    Framed-Protocol == PPP
    Framed-Protocol = PPP,
    Framed-Compression = Van-Jacobson-TCP-IP

#
# Default for CSLIP: dynamic IP address, SLIP mode, VJ-compression.
#
DEFAULT    Hint == "CSLIP"
    Framed-Protocol = SLIP,
    Framed-Compression = Van-Jacobson-TCP-IP

#
# Default for SLIP: dynamic IP address, SLIP mode.
#
DEFAULT    Hint == "SLIP"
    Framed-Protocol = SLIP

#
# Last default: rlogin to our main server.
#
#DEFAULT
#    Service-Type = Login-User,
#    Login-Service = Rlogin,
#    Login-IP-Host = shellbox.ispdomain.com

# #
# # Last default: shell on the local terminal server.
# #
# DEFAULT
#     Service-Type = Administrative-User

# On no match, the user is denied access.
"""

FILEOUTPUT_USER_ORIG = """# File parsed and saved by privacyidea.

DEFAULT Framed-Protocol == PPP
\tFramed-Protocol = PPP,
\tFramed-Compression = Van-Jacobson-TCP-IP

DEFAULT Hint == "CSLIP"
\tFramed-Protocol = SLIP,
\tFramed-Compression = Van-Jacobson-TCP-IP

DEFAULT Hint == "SLIP"
\tFramed-Protocol = SLIP

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
        

class TestFreeRADIUSUsers(unittest.TestCase):
    
    def setUp(self):
        pass
    
    def test_users_basic(self):
        UP = UserConfParser(content=USER_CONF_A)
        config = UP.get()
        print config
        self.assertEqual(config[0][0], "DEFAULT")
        self.assertEqual(config[0][1], "Auth-Type")
        self.assertEqual(config[0][2], ":=")
        self.assertEqual(config[0][3], "perl")
        
    def test_users_password(self):
        UP = UserConfParser(content=USER_CONF_B)
        config = UP.get()
        print config
        self.assertEqual(config[0][0], "administrator")
        self.assertEqual(config[0][1], "Cleartext-Password")
        self.assertEqual(config[0][2], ":=")
        self.assertEqual(config[0][3], '"secret"')
        
    def test_operators(self):
        UP = UserConfParser(content=USER_CONF_C)
        config = UP.get()
        print config
        self.assertEqual(config[0][0], "user")
        self.assertEqual(config[0][1], "somekey")
        self.assertEqual(config[0][2], "==")
        self.assertEqual(config[0][3], 'value')

    def test_reply_items(self):
        UP = UserConfParser(content=USER_CONF_D)
        config = UP.get()
        print config
        # [['DEFAULT', 'Hint', '==', '"SLIP"',
        #  [['Framed-Protocol', '=', 'SLIP']]]
        # ]

        self.assertEqual(config[0][0], "DEFAULT")
        self.assertEqual(config[0][1], "Hint")
        self.assertEqual(config[0][2], "==")
        self.assertEqual(config[0][3], '"SLIP"')
        self.assertEqual(config[0][4][0][0], 'Framed-Protocol')
        self.assertEqual(config[0][4][0][1], '=')
        self.assertEqual(config[0][4][0][2], 'SLIP')
        
    def test_reply_items2(self):
        UP = UserConfParser(content=USER_CONF_E)
        config = UP.get()
        print config
        # [['DEFAULT', 'Hint', '==', '"SLIP"',
        #  [['Framed-Protocol', '=', 'SLIP']]]
        # ]

        self.assertEqual(config[0][0], "DEFAULT")
        self.assertEqual(config[0][1], "Hint")
        self.assertEqual(config[0][2], "==")
        self.assertEqual(config[0][3], '"SLIP"')
        self.assertEqual(config[0][4][0][0], 'Framed-Protocol')
        self.assertEqual(config[0][4][0][1], '=')
        self.assertEqual(config[0][4][0][2], 'SLIP')
        self.assertEqual(config[0][4][1][0], 'Something')
        self.assertEqual(config[0][4][1][1], '=')
        self.assertEqual(config[0][4][1][2], 'Else')
    
    def test_get_complete(self):
        UP = UserConfParser(content=USER_CONF_1)
        config = UP.get()
        print len(config)
        self.assertEqual(len(config), 3)
        print config[0]
        print config[1]
        print config[2]
        self.assertEqual(len(config[0][4]), 2)
        self.assertEqual(len(config[1][4]), 2)
        self.assertEqual(len(config[2][4]), 1)
        
    def test_save_file(self):
        tmpfile = "./tmp-output"
        UP = UserConfParser(content=USER_CONF_1)
        config = UP.get()
        print config
        UP.save(config, tmpfile)
        f = open(tmpfile, "r")
        output = f.read()
        f.close()
        os.unlink(tmpfile)
        print output

        self.assertEqual(output, FILEOUTPUT_USER_ORIG)
    
if __name__ == '__main__':
    unittest.main()