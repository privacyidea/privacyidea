# -*- coding: utf-8 -*-
#
#    privacyIDEA is a fork of LinOTP
#    May 28, 2014 Cornelius Kölbel
#    E-mail: info@privacyidea.org
#    Contact: www.privacyidea.org
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

"""
This is the SMSClass to send SMS via HTTP Gateways
It can handle HTTP/HTTPS PUT and GET requests also with Proxy support
"""

#from SMSProvider import getSMSProviderClass
from privacyidea.smsprovider.SMSProvider import ISMSProvider

import base64

import urllib
import httplib2
import urllib2
from urlparse import urlparse

import logging
log = logging.getLogger(__name__)

## on debian squeeze the httplib is too old and does not contain
## a socks module. So we take an elder one, which does satiisfy
## the import BUT it does not work as well as the former urllib
## proxy does not work :-(

try:
    import httplib2.socks as socks
    log.info('Using httplib2.socks')
except ImportError:
    import socks as socks
    log.info('Using socksipy socks')


class HttpSMSProvider(ISMSProvider):
    def __init__(self):
        self.config = {}

    def submitMessage(self, phone, message):
        '''
        send out a message to a phone via an http sms connector
        :param phone: the phone number
        :param message: the message to submit to the phone
        '''
        url = self.config.get('URL', None)
        if url is None:
            return

        log.debug("[submitMessage] submitting message "
                  "%s to %s" % (message, phone))

        method = self.config.get('HTTP_Method', 'GET')
        username = self.config.get('USERNAME', None)
        password = self.config.get('PASSWORD', None)

        log.debug("[submitMessage] by method %s" % method)
        parameter = self.getParameters(message, phone)

        log.debug("[submitMessage] Now doing the Request")

        ## urlib2 has problems with authentication AND https
        ## below a test of urllib and httplib which shows, that
        ## we should use in case of Basic Auth and https the httplib:

        #NO_PROX  --  HTTPS Basic Auth  -- urllib  -- : Fail
        #NO_PROX  --  HTTPS  --            urllib  -- : Ok
        #NO_PROX  --  HTTP Basic Auth  --  urllib  -- : Ok
        #NO_PROX  --  HTTP  --             urllib  -- : Ok

        #PROX  --     HTTPS Basic Auth  -- urllib  -- : Fail
        #PROX  --     HTTPS  --            urllib  -- : Ok
        #PROX  --     HTTP Basic Auth  --  urllib  -- : Ok
        #PROX  --     HTTP  --             urllib  -- : Ok


        #NO_PROX  -- HTTPS Basic Auth  --  httplib  -- : OK
        #NO_PROX  -- HTTPS  --             httplib  -- : OK
        #NO_PROX  -- HTTP Basic Auth  --   httplib  -- : OK
        #NO_PROX  -- HTTP  --              httplib  -- : OK

        #PROX  --    HTTPS Basic Auth  -- httplib  -- : OK
        #PROX  --    HTTPS  --            httplib  -- : OK
        #PROX  --    HTTP Basic Auth  --  httplib  -- : Fail
        #PROX  --    HTTP  --             httplib  -- : Fail


        basic_auth = False
        https = False

        ## there might be the basic authentication in the request url
        ## like http://user:passw@hostname:port/path
        if password is None and username is None:
            parsed_url = urlparse(url)
            if "@" in parsed_url[1]:
                puser, server = parsed_url[1].split('@')
                username, password = puser.split(':')

        if username and password is not None:
            basic_auth = True

        if url.startswith('https:'):
            https = True

        lib = 'urllib'
        try:
            if basic_auth == True and https == True:
                lib = 'httplib'
                ret = self.httplib_request(url, parameter, username=username,
                                           password=password, method=method)
            else:
                ret = self.urllib_request(url, parameter, username=username,
                                           password=password, method=method)
        except Exception as exx:

            log.warning("Failed to access the HTTP SMS Service with %s: %r"
                        % (lib, exx))
            try:
                if lib == 'httplib':
                    ret = self.urllib_request(url, parameter, username=username,
                                               password=password, method=method)
                else:
                    ret = self.httplib_request(url, parameter, username=username,
                                               password=password, method=method)
            except Exception as new_exx:
                ## if we as well get an error, we raise the first exception
                ## to be more authentic ;-)
                log.warning("Failed again to access the HTTP SMS Service: %r"
                        % new_exx)
                raise exx


        return ret

    def getParameters(self, message, phone):

        urldata = {}

        ## transfer the phone key
        phoneKey = self.config.get('SMS_PHONENUMBER_KEY', "phone")
        urldata[phoneKey] = phone
        log.debug("[getParameters] urldata: %s" % urldata)

        ## transfer the sms key
        messageKey = self.config.get('SMS_TEXT_KEY', "sms")
        urldata[messageKey] = message
        log.debug("[getParameters] urldata: %s" % urldata)

        params = self.config.get('PARAMETER', {})
        urldata.update(params)

        log.debug("[getParameters] urldata: %s" % urldata)

        return urldata


    def _check_success(self, reply):
        '''
        Check the success according to the reply
        1. if RETURN_SUCCESS is defined
        2. if RETURN_FAIL is defined
        '''
        ret = False
        log.debug("[_check_success] entering with config %s" % self.config)
        if "RETURN_SUCCESS" in self.config:
            success = self.config.get("RETURN_SUCCESS")
            log.debug("[_check_success] success: %s" % success)
            if reply[:len(success)] == success:
                log.debug("[_check_success] sending sms success")
                ret = True
            else:
                log.warning("[_check_success] failed to send sms. Reply does not match the RETURN_SUCCESS definition")
                raise Exception("We received a none success reply from the SMS Gateway.")

        elif "RETURN_FAIL" in self.config:
            fail = self.config.get("RETURN_FAIL")
            log.debug("[_check_success] fail: %s" % fail)
            if reply[:len(fail)] == fail:
                log.warning("[_check_success] sending sms fail")
                raise Exception("We received a predefined error from the SMS Gateway.")
            else:
                log.warning("[_check_success] sending sms success full. The reply does not match the RETURN_FAIL definition")
                ret = True
        else:
            ret = True
        return ret

    def get_proxy_info(self, proxy):
        """
        helper to parse the proxyurl and to create the proxy_info object

        :param proxy: proxy url string
        :return: ProxyInfo object
        """
        proxy_params = {}
        proxy_host = None
        proxy_port = 8888

        parts = urlparse(proxy)
        net_loc = parts[1]

        if "@" in net_loc:
            puser, server = net_loc.split('@')
            if ':' in puser:
                proxy_user, proxy_pass = puser.split(':')
                proxy_params["proxy_user"] = proxy_user
                proxy_params["proxy_pass"] = proxy_pass
        else:
            server = net_loc

        if ':' in server:
            proxy_host, port = server.split(':')
            proxy_port = int(port)
        else:
            proxy_host = server

        # using httplib2:
        # the proxy spec and url + enc. parameters must be of
        # type string str() - otherwise the following error will occur:
        # : GeneralProxyError: (5, 'bad input') :

        proxy_info = httplib2.ProxyInfo(proxy_type=socks.PROXY_TYPE_HTTP,
                                        proxy_host=proxy_host,
                                        proxy_port=proxy_port,
                                        **proxy_params)
        return proxy_info

    def httplib_request(self, url, parameter,
                       username=None, password=None, method='GET'):
        """
        build the urllib request and check the response for success or fail



        :param url: target url
        :param parameter: additonal parameter to append to the url request
        :param username: basic authentication with username (optional)
        :param password: basic authentication with password (optional)
        :param method: run an GET or POST request

        :return: False or True
        """

        #httplib2.debuglevel = 4

        ret = False
        http_params = {}

        log.debug("Do the request to %s with %s" % (url, parameter))

        if 'PROXY' in self.config:
            ## prepare proxy from urls like
            ##   "http://username:password@your-proxy:8080"
            proxy = str(self.config['PROXY'])
            proxy_info = self.get_proxy_info(proxy)
            http_params["proxy_info"] = proxy_info

        http_params["disable_ssl_certificate_validation"] = True

        try:
            ## test if httplib is compiled with ssl - will raise a TypeError
            ## TypeError: __init__() got an unexpected keyword argument
            ## 'disable_ssl_certificate_validation'
            http = httplib2.Http(**http_params)
        except TypeError as exx:
            log.warning("httplib2 'disable_ssl_certificate_validation' "
                        "attribute error: %r" % exx)
            ## so we remove the ssl param from the arguments
            del http_params["disable_ssl_certificate_validation"]
            ## and retry
            http = httplib2.Http(**http_params)

        ## for backward compatibility we have to support url with the format
        ##  http://user:pass@server:port/path
        ## so we extract the url_user and the url_pass and use them if
        ## not overruled by the explicit parameters username and password
        url_user = None
        url_pass = None
        parsed_url = urlparse(url)

        if "@" in parsed_url[1]:
            puser, server = parsed_url[1].split('@')
            url_user, url_pass = puser.split(':')

            ## now rewrite the url to not contain the user anymore
            url = url.replace(parsed_url[1], server)

        if username and password is not None:
            http.add_credentials(name=username, password=password)
        elif url_user and url_pass is not None:
            http.add_credentials(name=url_user, password=url_pass)

        ##! the parameters to the httplib / proxy must be of type str()
        encoded_params = str(urllib.urlencode(parameter))
        call_url = str(url)

        try:
            ## do a GET request - which has no body but all params
            ## added to the url
            if method == 'GET':
                call_data = None
                if len(encoded_params) > 0:
                    ## extend the url with our parameters
                    call_url = str("%s?%s" % (call_url, encoded_params))

            ## or do a POST request - the more secure default and fallback
            else:
                method = 'POST'
                call_data = encoded_params

            # using httplib2:
            # the proxy spec and url + enc. parameters must be of
            # type string str() - otherwise the following error will occur:
            # : GeneralProxyError: (5, 'bad input') :

            (_resp, reply) = http.request(call_url, method=method,
                                         body=call_data)

            # some providers like clickatell have no response.status!
            log.debug("HttpSMSProvider >>%s...%s<<", reply[:20], reply[-20:])
            ret = self._check_success(reply)

        except Exception as exc:
            log.error("HttpSMSProvider %r" % exc)
            raise Exception("Failed to send SMS. %s" % str(exc))

        return ret


    def urllib_request(self, url, parameter,
                       username=None, password=None, method='GET'):
        """
        build the urllib request and check the response for success or fail

        :param url: target url
        :param parameter: additonal parameter to append to the url request
        :param username: basic authentication with username (optional)
        :param password: basic authentication with password (optional)
        :param method: run an GET or POST request

        :return: False or True
        """
        try:

            handlers = []
            if 'PROXY' in self.config and self.config['PROXY']:
                # for simplicity we set both protocols
                proxy_handler = urllib2.ProxyHandler({"http": self.config['PROXY'],
                                                      "https":self.config['PROXY']})
                handlers.append(proxy_handler)
                print "using Proxy: %r" % self.config['PROXY']

            if username and password is not None:
                password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                password_mgr.add_password(None, url, username, password)
                auth_handler = urllib2.HTTPBasicAuthHandler(password_mgr)
                handlers.append(auth_handler)

            opener = urllib2.build_opener(*handlers)
            urllib2.install_opener(opener)

            full_url = str(url)
            encoded_params = None
            if parameter is not None and len(parameter) > 0 :
                encoded_params = str(urllib.urlencode(parameter))

            if method == 'GET':
                c_data = None
                if encoded_params:
                    full_url = str("%s?%s" % (url, encoded_params))
            else:
                c_data = encoded_params

            requ = urllib2.Request(full_url, data=c_data, headers={})
            if username and password is not None:
                base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
                requ.add_header("Authorization", "Basic %s" % base64string)

            response = urllib2.urlopen(requ)
            reply = response.read()

            # some providers like clickatell have no response.status!
            log.debug("HttpSMSProvider >>%s...%s<<", reply[:20], reply[-20:])
            ret = self._check_success(reply)

        except Exception as exc:
            log.error("HttpSMSProvider %r" % exc)
            raise Exception("Failed to send SMS. %s" % str(exc))

        return ret


    def loadConfig(self, configDict):
        self.config = configDict

##eof##########################################################################
