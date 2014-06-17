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
'''
The provider can be tested by running
python SipgateSMSProvider <username> <password> <phonenumber>
'''
try:
    from privacyidea.smsprovider.SMSProvider import ISMSProvider
except:
    from SMSProvider import ISMSProvider
import logging
log = logging.getLogger(__name__)
import httplib2


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

class SipgateSMSProvider(ISMSProvider):

    # We not need to overwrite the __init__ and 
    # the loadConfig functions!
    # They provide the self.config dictionary.
    
    def submitMessage(self, phone, message):
        ret = False
        username = self.config.get("USERNAME")
        password = self.config.get("PASSWORD")
        http = httplib2.Http()
        http.add_credentials(username, password)
        response, content = http.request("https://samurai.sipgate.net/RPC2", "POST",
                                headers={'content-type':'text/xml'},
                                body=REQUEST_XML % (phone.strip().strip("+"), message))
        log.debug("SMS submitted: %s" % response)
        log.debug("response content: %s" % content)
        if response.get("status") == "200":
            ret = True
        else:
            log.error("Error during sending SMS: %s\n%s" % (response, content))
            ret = response.get("status")

        return ret
        

import sys
        
if __name__ == "__main__":
    username = sys.argv[1]
    password = sys.argv[2] 
    phone = sys.argv[3]
    text = "Your OTP"
    config = {'USERNAME' : username,
              'PASSWORD' : password}
    sms = SipgateSMSProvider()
    sms.loadConfig(config)
    r = sms.submitMessage(phone, text)
    print r
    

        
    
    