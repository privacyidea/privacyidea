#   2016-06-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#              Add allowed parameters to the SMS Provider
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
from privacyidea.lib import _
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
        phone = self._mangle_phone(phone, self.config)
        if self.smsgateway:
            username = self.smsgateway.option_dict.get("USERNAME")
            password = self.smsgateway.option_dict.get("PASSWORD")
            proxy = self.smsgateway.option_dict.get("PROXY")
        else:
            username = self.config.get("USERNAME")
            password = self.config.get("PASSWORD")
            proxy = self.config.get('PROXY')
        proxies = None
        if proxy:
            protocol = proxy.split(":")[0]
            proxies = {protocol: proxy}

        log.debug("submitting message {0!r} to {1!s}".format(message, phone))
        r = requests.post(URL,
                          data=REQUEST_XML % (phone.strip().strip("+"),
                                              message),
                          headers={'content-type': 'text/xml'},
                          auth=(username, password),
                          proxies=proxies,
                          timeout=60)

        log.debug("SMS submitted: {0!s}".format(r.status_code))
        log.debug("response content: {0!s}".format(r.text))

        if r.status_code != 200:
            raise SMSError(r.status_code, "SMS could not be "
                                          "sent: %s" % r.status_code)
        return True

    @classmethod
    def parameters(cls):
        """
        Return a dictionary, that describes the parameters and options for the
        SMS provider.
        Parameters are required keys to values.

        :return: dict
        """
        from privacyidea.lib.smtpserver import get_smtpservers
        params = {"options_allowed": False,
                  "headers_allowed": False,
                  "parameters": {
                      "USERNAME": {
                          "required": True,
                          "description": "The sipgate username."},
                      "PASSWORD": {
                          "required": True,
                          "description": "The sipgate password."},
                      "PROXY": {
                          "description": "An optional proxy URI."
                      },
                      "REGEXP": {
                          "description": cls.regexp_description
                      }
                  }
                  }
        return params
