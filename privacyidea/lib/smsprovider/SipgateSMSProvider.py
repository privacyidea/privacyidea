# -*- coding: utf-8 -*-
#
#    privacyIDEA
#    (c) 2014 Cornelius Kölbel
#    E-mail: info@privacyidea.org
#    Contact: www.privacyidea.org
#
#    This program is free software: you can redistribute it and/or
#    modify it under the terms of the GNU Affero General Public
#    License, version 3, as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the
#               GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
__doc__="""This module provides sending SMS via sipgate

The code is tested in tests/test_lib_smsprovider
"""
from privacyidea.lib.smsprovider.SMSProvider import ISMSProvider, SMSError
import logging
import requests
log = logging.getLogger(__name__)


REQUEST_XML='''<?xml version="1.0" encoding="UTF-8"?>
<methodCall>
<methodName>samurai.SessionInitiate</methodName>
<params>
<param>
<value>
<struct>
<member>
<name>RemoteUri</name>
<value><string>sip:%s@sipgate.de</string></value>
</member>
<member>
<name>TOS</name>
<value><string>text</string></value>
</member>
<member>
<name>Content</name>
<value><string>%s</string></value>
</member>
</struct>
</value>
</param>
</params>
</methodCall>'''

URL = "https://samurai.sipgate.net/RPC2"

class SipgateSMSProvider(ISMSProvider):

    # We do not need to overwrite the __init__ and
    # the loadConfig functions!
    # They provide the self.config dictionary.

    def submit_message(self, phone, message):
        username = self.config.get("USERNAME")
        password = self.config.get("PASSWORD")
        proxy = self.config.get('PROXY')
        proxies = None
        if proxy:
            protocol = proxy.split(":")[0]
            proxies = {protocol: proxy}

        r = requests.post(URL,
                          data=REQUEST_XML % (phone.strip().strip("+"),
                                              message),
                          headers={'content-type': 'text/xml'},
                          auth=(username, password),
                          proxies=proxies)

        log.debug("SMS submitted: {0!s}".format(r.status_code))
        log.debug("response content: {0!s}".format(r.text))

        if r.status_code != 200:
            raise SMSError(r.status_code, "SMS could not be "
                                          "sent: %s" % r.status_code)
        return True

