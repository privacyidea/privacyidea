# -*- coding: utf-8 -*-
#
#    E-mail: info@privacyidea.org
#    Contact: www.privacyidea.org
#
#    2018-06-15 Pascal Fuks <pascal@foxit.pro>
#               Added REGEXP parameter on phone number
#    2018-01-10 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               Fix type cast for timeout
#    2016-06-14 Cornelius Kölbel <cornelius@privacyidea.org>
#               Add properties for new SMS provider model
#    2016-04-08 Cornelius Kölbel <cornelius@privacyidea.org>
#               Remote "None" as redundant 2nd argument to get
#    2016-01-13 Cornelius Kölbel <cornelius@privacyidea.org>
#               omit data object in GET request
#               omit params in POST request
#
#    privacyIDEA is a fork of LinOTP
#    May 28, 2014 Cornelius Kölbel
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

__doc__ = """This is the SMSClass to send SMS via HTTP Gateways
It can handle HTTP/HTTPS POST and GET requests also with Proxy support

The code is tested in tests/test_lib_smsprovider
"""

from privacyidea.lib.smsprovider.SMSProvider import (ISMSProvider, SMSError)
from privacyidea.lib import _
import requests
from urllib.parse import urlparse
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
        parameter = {}
        headers = {}
        if self.smsgateway:
            phone = self._mangle_phone(phone, self.smsgateway.option_dict)
            url = self.smsgateway.option_dict.get("URL")
            method = self.smsgateway.option_dict.get("HTTP_METHOD", "GET")
            username = self.smsgateway.option_dict.get("USERNAME")
            password = self.smsgateway.option_dict.get("PASSWORD")
            ssl_verify = self.smsgateway.option_dict.get("CHECK_SSL",
                                                         "yes") == "yes"
            json_data = self.smsgateway.option_dict.get("SEND_DATA_AS_JSON",
                                                        "no") == "yes"
            # FIXME: The Proxy option is deprecated and will be removed a version > 2.21
            proxy = self.smsgateway.option_dict.get("PROXY")
            http_proxy = self.smsgateway.option_dict.get('HTTP_PROXY')
            https_proxy = self.smsgateway.option_dict.get('HTTPS_PROXY')
            timeout = self.smsgateway.option_dict.get("TIMEOUT") or 3
            for k, v in self.smsgateway.option_dict.items():
                if k not in self.parameters().get("parameters"):
                    # This is an additional option
                    parameter[k] = v.format(otp=message, phone=phone)
            headers = self.smsgateway.header_dict
        else:
            phone = self._mangle_phone(phone, self.config)
            url = self.config.get('URL')
            method = self.config.get('HTTP_Method', 'GET')
            username = self.config.get('USERNAME')
            password = self.config.get('PASSWORD')
            ssl_verify = self.config.get('CHECK_SSL', True)
            json_data = False
            # FIXME: The Proxy option is deprecated and will be removed a version > 2.21
            proxy = self.config.get('PROXY')
            http_proxy = self.config.get('HTTP_PROXY')
            https_proxy = self.config.get('HTTPS_PROXY')
            parameter = self._get_parameters(message, phone)
            timeout = self.config.get("TIMEOUT") or 3

        log.debug("submitting message {0!r} to {1!s}".format(message, phone))

        if url is None:
            log.warning("can not submit message. URL is missing.")
            raise SMSError(-1, "No URL specified in the provider config.")
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

        proxies = {}
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
        if not proxies and proxy:
            # No new proxy config but only the old one.
            protocol = proxy.split(":")[0]
            proxies = {protocol: proxy}

        # url, parameter, username, password, method
        requestor = requests.get
        params = parameter
        data = None
        json_param = None
        if method == "POST":
            requestor = requests.post
            params = None
            if json_data:
                json_param = parameter
                log.debug("passing JSON data: {0!s}".format(json_param))
            else:
                data = parameter

        log_dict = {'params': params,
                    'headers': headers,
                    'method': method,
                    'basic_auth': basic_auth,
                    'url': url,
                    'data': data,
                    'json_param': json_param}
        log.debug("issuing request with parameters {params} (data: {data}, "
                  "json: {json_param}), headers {headers}, method {method} and"
                  "authentication {basic_auth} "
                  "to url {url}.".format(**log_dict))
        # Todo: drop basic auth if Authorization-Header is given?
        r = requestor(url, params=params, headers=headers,
                      data=data, json=json_param,
                      verify=ssl_verify,
                      auth=basic_auth,
                      timeout=float(timeout),
                      proxies=proxies)
        log.debug("queued SMS on the HTTP gateway. status code returned: {0!s}".format(
                  r.status_code))

        # We assume, that all gateways return with HTTP Status Code 200,
        # 201 or 202
        if r.status_code not in [200, 201, 202]:
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
        log.debug("[getParameters] urldata: {0!s}".format(urldata))
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
        if self.smsgateway:
            return_success = self.smsgateway.option_dict.get("RETURN_SUCCESS")
            return_fail = self.smsgateway.option_dict.get("RETURN_FAIL")
        else:
            return_success = self.config.get("RETURN_SUCCESS")
            return_fail = self.config.get("RETURN_FAIL")

        if return_success:
            if return_success in reply:
                log.debug("sending sms success")
                ret = True
            else:
                log.warning("failed to send sms. Reply %s does not match "
                            "the RETURN_SUCCESS definition" % reply)
                raise SMSError(response.status_code,
                               "We received a none success reply from the "
                               "SMS Gateway: {0!s} ({1!s})".format(reply,
                                                                   return_success))

        elif return_fail:
            if return_fail in reply:
                log.warning("sending sms failed. %s was not found "
                            "in %s" % (return_fail, reply))
                raise SMSError(response.status_code,
                               "We received the predefined error from the "
                               "SMS Gateway.")
            else:
                log.debug("sending sms success")
                ret = True
        else:
            ret = True
        return ret

    @classmethod
    def parameters(cls):
        """
        Return a dictionary, that describes the parameters and options for the
        SMS provider.
        Parameters are required keys to values.

        :return: dict
        """
        params = {"options_allowed": True,
                  "headers_allowed": True,
                  "parameters": {
                      "URL": {
                          "required": True,
                          "description": _("The base URL of the HTTP Gateway")},
                      "HTTP_METHOD": {
                          "required": True,
                          "description": _("Should the HTTP Gateway be "
                                           "connected via an HTTP GET or POST "
                                           "request."),
                          "values": ["GET", "POST"]},
                      "RETURN_SUCCESS": {
                          "description": _("Specify a substring, "
                                           "that indicates, that the SMS was "
                                           "delivered successfully.")},
                      "RETURN_FAIL": {
                          "description": _("Specify a substring, "
                                           "that indicates, that the SMS "
                                           "failed to be delivered.")},
                      "USERNAME": {
                          "description": _("Username in case of basic "
                                           "authentication.")
                      },
                      "PASSWORD": {
                          "description": _("Password in case of basic "
                                           "authentication.")
                      },
                      "CHECK_SSL": {
                          "required": True,
                          "description": _("Should the SSL certificate be "
                                           "verified."),
                          "values": ["yes", "no"]
                      },
                      "SEND_DATA_AS_JSON": {
                          "required": True,
                          "description": _("Should the data in a POST Request be sent "
                                           "as JSON."),
                          "values": ["yes", "no"]
                      },
                      "REGEXP": {
                          "description": cls.regexp_description
                      },
                      "PROXY": {"description": _("An optional proxy string. DEPRECATED. Do not use "
                                                 "this anymore. Rather use HTTP_PROXY for http "
                                                 "connections and HTTPS_PROXY for https "
                                                 "connection. The PROXY option will be removed in "
                                                 "future.")},
                      "HTTP_PROXY": {"description": _("Proxy setting for HTTP connections.")},
                      "HTTPS_PROXY": {"description": _("Proxy setting for HTTPS connections.")},
                      "TIMEOUT": {"description": _("The timeout in seconds.")}
                  }
                  }
        return params
