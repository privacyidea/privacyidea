# -*- coding: utf-8 -*-
#
#    privacyIDEA is a fork of LinOTP
#    May 28, 2014 Cornelius Kölbel
#    E-mail: info@privacyidea.org
#    Contact: www.privacyidea.org
#
#    2015-01-30 Rewrite for migration to flask
#               Cornelius Kölbel <cornelius@privacyidea.org>
#
#
#    Copyright (C) LinOTP: 2010 - 2014 LSE Leading Security Experts GmbH
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

__doc__="""This is the SMSClass to send SMS via HTTP Gateways
It can handle HTTP/HTTPS PUT and GET requests also with Proxy support

The code is tested in tests/test_lib_smsprovider
"""

from privacyidea.lib.smsprovider.SMSProvider import (ISMSProvider, SMSError)
import requests
from urlparse import urlparse

import logging
log = logging.getLogger(__name__)


class HttpSMSProvider(ISMSProvider):

    def submit_message(self, phone, message):
        """
        send a message to a phone via an http sms gateway
        :param phone: the phone number
        :param message: the message to submit to the phone
        :return:
        """
        success = False
        url = self.config.get('URL', None)
        if url is None:
            log.warning("can not submit message. URL is missing.")
            raise SMSError(-1, "No URL specified in the provider config.")

        log.debug("submitting message %s to %s" % (message, phone))

        method = self.config.get('HTTP_Method', 'GET')
        username = self.config.get('USERNAME', None)
        password = self.config.get('PASSWORD', None)
        ssl_verify = self.config.get('CHECK_SSL', True)
        parameter = self._get_parameters(message, phone)
        basic_auth = None

        # there might be the basic authentication in the request url
        # like http://user:passw@hostname:port/path
        if password is None and username is None:
            parsed_url = urlparse(url)
            if "@" in parsed_url[1]:
                puser, server = parsed_url[1].split('@')
                username, password = puser.split(':')

        if username and password is not None:
            basic_auth = (username, password)

        proxy = self.config.get('PROXY', None)
        proxies = None
        if proxy:
            protocol = proxy.split(":")[0]
            proxies = {protocol: proxy}

        # url, parameter, username, password, method
        requestor = requests.get
        if method == "POST":
            requestor = requests.post

        log.debug("issuing request with parameters %s and method %s and "
                  "authentication %s to url %s." % (parameter, method,
                                                    basic_auth, url))
        r = requestor(url, params=parameter,
                      data=parameter,
                      verify=ssl_verify,
                      auth=basic_auth,
                      proxies=proxies)
        log.debug("queued SMS on the HTTP gateway. status code returned: %s" %
                  r.status_code)

        # We assume, that all gateway return with HTTP Status Code 200
        if r.status_code != 200:
            raise SMSError(r.status_code, "SMS could not be "
                                          "sent: %s" % r.status_code)
        success = self._check_success(r)
        return success

    def _get_parameters(self, message, phone):

        urldata = {}
        # transfer the phone key
        phoneKey = self.config.get('SMS_PHONENUMBER_KEY', "phone")
        urldata[phoneKey] = phone
        # transfer the sms key
        messageKey = self.config.get('SMS_TEXT_KEY', "sms")
        urldata[messageKey] = message
        params = self.config.get('PARAMETER', {})
        urldata.update(params)
        log.debug("[getParameters] urldata: %s" % urldata)
        return urldata

    def _check_success(self, response):
        """
        Check the success according to the reply
        1. if RETURN_SUCCESS is defined
        2. if RETURN_FAIL is defined
        :response reply: A response object.
        """
        reply = response.text
        ret = False
        if "RETURN_SUCCESS" in self.config:
            success = self.config.get("RETURN_SUCCESS")
            if reply[:len(success)] == success:
                log.debug("sending sms success")
                ret = True
            else:
                log.warning("failed to send sms. Reply %s does not match "
                            "the RETURN_SUCCESS definition" % reply)
                raise SMSError(response.status_code,
                               "We received a none success reply from the "
                               "SMS Gateway: %s" % reply)

        elif "RETURN_FAIL" in self.config:
            fail = self.config.get("RETURN_FAIL")
            if fail in reply:
                log.warning("sending sms failed. %s was not found "
                            "in %s" % (fail, reply))
                raise SMSError(response.status_code,
                               "We received the predefined error from the "
                               "SMS Gateway.")
            else:
                log.debug("sending sms success")
                ret = True
        else:
            ret = True
        return ret
