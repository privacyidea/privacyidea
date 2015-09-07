# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2015-01-28 Rewrite for migration to flask
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  LSE
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__doc__ = """This is the implementation of the remote token. The remote token
forwards an authentication request to another privacyidea server.

To do this it uses the parameters remote.server, remote.realm,
remote.resolver, remote.user or remote.serial.
The parameter remote.local_checkpin determines, whether the PIN should be
checked locally or remotely.

The code is tested in tests/test_lib_tokens_remote
"""

import logging
import traceback
import requests
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.config import get_from_config
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.log import log_with
from privacyidea.lib.policydecorators import challenge_response_allowed
from privacyidea.lib.tokenclass import TokenClass

optional = True
required = False

log = logging.getLogger(__name__)

###############################################


class RemoteTokenClass(TokenClass):
    """
    The Remote token forwards an authentication request to another privacyIDEA
    server. The request can be forwarded to a user on the other server or to
    a serial number on the other server. The PIN can be checked on the local
    privacyIDEA server or on the remote server.

    Using the Remote token you can assign one physical token to many
    different users.
    """

    def __init__(self, db_token):
        """
        constructor - create a token class object with it's db token binding

        :param aToken: the db bound token
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"remote")
        self.mode = ['authenticate', 'challenge']

    @classmethod
    def get_class_type(cls):
        """
        return the class type identifier
        """
        return "remote"

    @classmethod
    def get_class_prefix(cls):
        """
        return the token type prefix
        """
        return "PIRE"

    @classmethod
    @log_with(log)
    def get_class_info(cls, key=None, ret='all'):
        """
        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict or string
        """
        res = {'type': 'remote',
               'title': 'Remote Token',
               'description': ('Remote Token: Forward authentication request '
                               'to another server.'),

               'init': {'page': {'html': 'remotetoken.mako',
                                 'scope': 'enroll', },
                        'title': {'html': 'remotetoken.mako',
                                  'scope': 'enroll.title', },
                        },

               'config': {'page': {'html': 'remotetoken.mako',
                                   'scope': 'config', },
                          'title': {'html': 'remotetoken.mako',
                                    'scope': 'config.title', },
                          },

               'user': [],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin"],
               'policy': {},
               }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    def update(self, param):
        """
        second phase of the init process - updates parameters

        :param param: the request parameters
        :return: - nothing -
        """
        # if another OTP length would be specified in /admin/init this would
        # be overwritten by the parent class, which is ok.
        self.set_otplen(6)
        TokenClass.update(self, param)

        remoteServer = getParam(param, "remote.server", required)
        self.add_tokeninfo("remote.server", remoteServer)

        for key in ["remote.local_checkpin", "remote.serial", "remote.user",
                    "remote.realm", "remote.resolver"]:
            val = getParam(param, key, optional)
            if val is not None:
                self.add_tokeninfo(key, val)

    @property
    def check_pin_local(self):
        """
        lookup if pin should be checked locally or on remote host

        :return: bool
        """
        local_check = False
        if 1 == int(self.get_tokeninfo("remote.local_checkpin")):
            local_check = True
        log.debug(" local checking pin? %r" % local_check)

        return local_check

    @log_with(log)
    @check_token_locked
    def authenticate(self, passw, user=None, options=None):
        """
        do the authentication on base of password / otp and user and
        options, the request parameters.

        Here we contact the other privacyIDEA server to validate the OtpVal.

        :param passw: the password / otp
        :param user: the requesting user
        :param options: the additional request parameters

        :return: tuple of (success, otp_count - 0 or -1, reply)

        """
        res = False
        otp_counter = -1
        reply = None
        otpval = passw

        # should we check the pin localy?
        if self.check_pin_local:
            (_res, pin, otpval) = self.split_pin_pass(passw, user,
                                                      options=options)

            if not TokenClass.check_pin(self, pin):
                return False, otp_counter, {'message': "Wrong PIN"}

        otp_count = self.check_otp(otpval, options=options)
        if otp_count >= 0:
            res = True
            reply = {'message': 'matching 1 tokens',
                     'serial': self.get_serial(),
                     'type': self.get_tokentype()}
        else:
            reply = {'message': 'remote side denied access'}

        return res, otp_count, reply

    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        run the http request against the remote host

        :param otpval: the OTP value
        :param counter: The counter for counter based otp values
        :type counter: int
        :param window: a counter window
        :type counter: int
        :param options: additional token specific options
        :type options: dict
        :return: counter of the matching OTP value.
        :rtype: int
        """
        otp_count = -1
        otpval = otpval.encode("utf-8")

        remoteServer = self.get_tokeninfo("remote.server") or ""
        remoteServer = remoteServer.encode("utf-8")

        # in preparation of the ability to relocate privacyidea urls,
        # we introduce the remote url path
        remotePath = self.get_tokeninfo("remote.path") or ""
        remotePath = remotePath.strip().encode('utf-8')

        remoteSerial = self.get_tokeninfo("remote.serial") or ""
        remoteSerial = remoteSerial.encode('utf-8')

        remoteUser = self.get_tokeninfo("remote.user") or ""
        remoteUser = remoteUser.encode('utf-8')

        remoteRealm = self.get_tokeninfo("remote.realm") or ""
        remoteRealm = remoteRealm.encode('utf-8')

        remoteResolver = self.get_tokeninfo("remote.resolver") or ""
        remoteResolver = remoteResolver.encode('utf-8')

        ssl_verify = get_from_config("remote.verify_ssl_certificate",
                                        False) or False

        if type(ssl_verify) in [str, unicode]:
            if ssl_verify.lower() in ["true", "1"]:
                ssl_verify = True
            else:
                ssl_verify = False

        # here we also need to check for remote.user and so on....
        log.debug("checking OTP len:%r remotely on server: %r,"
                  " serial: %r, user: %r" %
                  (len(otpval), remoteServer, remoteSerial, remoteUser))
        params = {}

        if len(remotePath) == 0:
            remotePath = "/validate/check"
        if len(remoteSerial) > 0:
            params['serial'] = remoteSerial
        elif len(remoteUser) > 0:
            params['user'] = remoteUser
            params['realm'] = remoteRealm
            params['resolver'] = remoteResolver

        else:
            log.warning("The remote token does neither contain a "
                        "remote.serial nor a remote.user.")
            return otp_count

        params['pass'] = otpval
        request_url = "%s%s" % (remoteServer, remotePath)

        try:
            r = requests.post(request_url, data=params, verify=ssl_verify)

            if r.status_code == requests.codes.ok:
                response = r.json()
                result = response.get("result")
                if result.get("value"):
                    otp_count = 1

        except Exception as exx:  # pragma: no cover
            log.error("Error getting response from "
                      "remote Server (%r): %r" % (request_url, exx))
            log.error(traceback.format_exc())

        return otp_count

    @log_with(log)
    @challenge_response_allowed
    def is_challenge_request(self, passw, user=None, options=None):
        """
        This method checks, if this is a request, that triggers a challenge.
        It depends on the way, the pin is checked - either locally or remote

        :param passw: password, which might be pin or pin+otp
        :type passw: string
        :param user: The user from the authentication request
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict

        :return: true or false
        """

        request_is_valid = False

        if self.check_pin_local:
            pin_match = self.check_pin(passw, user=user,
                                         options=options)
            if pin_match is True:
                request_is_valid = True

        return request_is_valid
