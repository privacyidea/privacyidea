# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2015-01-29 Adapt for migration to flask
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
__doc__ = """This module defines the RadiusTokenClass. The RADIUS token
forwards the authentication request to another RADIUS server.

The code is tested in tests/test_lib_tokens_radius
"""

import logging

import traceback
import binascii
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.remotetoken import RemoteTokenClass
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.log import log_with
from privacyidea.lib.config import get_from_config
from privacyidea.lib.decorators import check_token_locked

import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary


optional = True
required = False

log = logging.getLogger(__name__)


###############################################
class RadiusTokenClass(RemoteTokenClass):

    def __init__(self, db_token):
        RemoteTokenClass.__init__(self, db_token)
        self.set_type(u"radius")
        self.mode = ['authenticate', 'challenge']

    @classmethod
    def get_class_type(cls):
        return "radius"

    @classmethod
    def get_class_prefix(cls):
        return "PIRA"

    @classmethod
    @log_with(log)
    def get_class_info(cls, key=None, ret='all'):
        """
        returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict or string
        """
        res = {'type': 'radius',
               'title': 'RADIUS Token',
               'description': 'RADIUS: Forward authentication request to a '
                              'RADIUS server.',
               'init': {'page': {'html': 'radiustoken.mako',
                                 'scope': 'enroll'},
                        'title': {'html': 'radiustoken.mako',
                                  'scope': 'enroll.title', }},
               'config': {'page': {'html': 'radiustoken.mako',
                                   'scope': 'config'},
                          'title': {'html': 'radiustoken.mako',
                                    'scope': 'config.title'}},
               'user':  ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {},
               }

        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret

    def update(self, param):

        radiusServer = getParam(param, "radius.server", required)
        self.add_tokeninfo("radius.server", radiusServer)
        # if another OTP length would be specified in /admin/init this would
        # be overwritten by the parent class, which is ok.
        self.set_otplen(6)
        TokenClass.update(self, param)
        val = getParam(param, "radius.local_checkpin", optional)
        self.add_tokeninfo("radius.local_checkpin", val)

        val = getParam(param, "radius.user", required)
        self.add_tokeninfo("radius.user", val)

        val = getParam(param, "radius.secret", required)
        self.token.set_otpkey(binascii.hexlify(val))

    @property
    def check_pin_local(self):
        """
        lookup if pin should be checked locally or on radius host

        :return: bool
        """
        local_check = False

        if 1 == int(self.get_tokeninfo("radius.local_checkpin")):
            local_check = True
        log.debug("local checking pin? %r" % local_check)

        return local_check

    @log_with(log)
    def split_pin_pass(self, passw, user=None, options=None):
        """
        Split the PIN and the OTP value.
        Only if it is locally checked and not remotely.
        """
        res = 0
        pin = ""
        otpval = passw
        if self.check_pin_local:
            (res, pin, otpval) = TokenClass.split_pin_pass(self, passw)

        return res, pin, otpval

    @log_with(log)
    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        run the RADIUS request against the RADIUS server

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
        options = options or {}
        radiusServer = self.get_tokeninfo("radius.server")
        radiusUser = self.get_tokeninfo("radius.user")

        # Read the secret
        secret = self.token.get_otpkey()
        radiusSecret = binascii.unhexlify(secret.getKey())

        # here we also need to check for radius.user
        log.debug("checking OTP len:%s on radius server: %s, user: %s" 
                  % (len(otpval), radiusServer, radiusUser))

        try:
            # pyrad does not allow to set timeout and retries.
            # it defaults to retries=3, timeout=5

            # TODO: At the moment we support only one radius server.
            # No round robin.
            server = radiusServer.split(':')
            r_server = server[0]
            r_authport = 1812
            nas_identifier = get_from_config("radius.nas_identifier",
                                             "privacyIDEA")
            r_dict = get_from_config("radius.dictfile",
                                     "/etc/privacyidea/dictionary")

            if len(server) >= 2:
                r_authport = int(server[1])
            log.debug("NAS Identifier: %r, "
                      "Dictionary: %r" % (nas_identifier, r_dict))
            log.debug("constructing client object "
                      "with server: %r, port: %r, secret: %r" %
                      (r_server, r_authport, radiusSecret))

            srv = Client(server=r_server,
                         authport=r_authport,
                         secret=radiusSecret,
                         dict=Dictionary(r_dict))

            req = srv.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                                       User_Name=radiusUser.encode('ascii'),
                                       NAS_Identifier=nas_identifier.encode('ascii'))

            req["User-Password"] = req.PwCrypt(otpval)
            if "transactionid" in options:
                req["State"] = str(options.get("transactionid"))

            response = srv.SendPacket(req)
            c = response.code
            # TODO: handle the RADIUS challenge
            """
            if response.code == pyrad.packet.AccessChallenge:
                opt = {}
                for attr in response.keys():
                    opt[attr] = response[attr]
                res = False
                log.debug("challenge returned %r " % opt)
                # now we map this to a privacyidea challenge
                if "State" in opt:
                    reply["transactionid"] = opt["State"][0]
                if "Reply-Message" in opt:
                    reply["message"] = opt["Reply-Message"][0]
            """
            if response.code == pyrad.packet.AccessAccept:
                log.info("Radiusserver %s granted "
                         "access to user %s." % (r_server, radiusUser))
                otp_count = 0
            else:
                log.warning("Radiusserver %s"
                            "rejected access to user %s." %
                            (r_server, radiusUser))

        except Exception as ex:  # pragma: no cover
            log.error("Error contacting radius Server: %r" % (ex))
            log.error(traceback.format_exc())

        return otp_count

