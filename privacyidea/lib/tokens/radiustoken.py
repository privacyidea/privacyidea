# -*- coding: utf-8 -*-
#
#  2018-01-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add tokenkind
#  2016-02-22 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add the RADIUS identifier, which points to the system wide list
#             of RADIUS servers.
#  2015-10-09 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add the RADIUS-System-Config, so that not each
#             RADIUS-token needs his own secret. -> change the
#             secret globally
#  2015-01-29 Adapt for migration to flask
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
from privacyidea.lib.utils import is_true, to_bytes, hexlify_and_unicode, to_unicode
from privacyidea.lib.tokenclass import TokenClass, TOKENKIND
from privacyidea.lib.tokens.remotetoken import RemoteTokenClass
from privacyidea.api.lib.utils import getParam, ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.config import get_from_config
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.radiusserver import get_radius

import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary
from privacyidea.lib import _


optional = True
required = False

log = logging.getLogger(__name__)


###############################################
class RadiusTokenClass(RemoteTokenClass):

    def __init__(self, db_token):
        RemoteTokenClass.__init__(self, db_token)
        self.set_type(u"radius")
        self.mode = ['authenticate', 'challenge']

    @staticmethod
    def get_class_type():
        return "radius"

    @staticmethod
    def get_class_prefix():
        return "PIRA"

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
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
               'description': _('RADIUS: Forward authentication request to a '
                                'RADIUS server.'),
               'user':  ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {},
               }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res

        return ret

    def update(self, param):
        # New value
        radius_identifier = getParam(param, "radius.identifier")
        self.add_tokeninfo("radius.identifier", radius_identifier)

        # old values
        if not radius_identifier:
            radiusServer = getParam(param, "radius.server", optional=required)
            self.add_tokeninfo("radius.server", radiusServer)
            radius_secret = getParam(param, "radius.secret", optional=required)
            self.token.set_otpkey(hexlify_and_unicode(radius_secret))
            system_settings = getParam(param, "radius.system_settings",
                                       default=False)
            self.add_tokeninfo("radius.system_settings", system_settings)

            if not (radiusServer or radius_secret) and not system_settings:
                raise ParameterError("Missing parameter: radius.identifier", id=905)

        # if another OTP length would be specified in /admin/init this would
        # be overwritten by the parent class, which is ok.
        self.set_otplen(6)
        TokenClass.update(self, param)
        val = getParam(param, "radius.local_checkpin", optional) or 0
        self.add_tokeninfo("radius.local_checkpin", val)

        val = getParam(param, "radius.user", required)
        self.add_tokeninfo("radius.user", val)
        self.add_tokeninfo("tokenkind", TOKENKIND.VIRTUAL)

    @property
    def check_pin_local(self):
        """
        lookup if pin should be checked locally or on radius host

        :return: bool
        """
        local_check = is_true(self.get_tokeninfo("radius.local_checkpin"))
        log.debug("local checking pin? {0!r}".format(local_check))

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

        radius_dictionary = None
        radius_identifier = self.get_tokeninfo("radius.identifier")
        radius_user = self.get_tokeninfo("radius.user")
        system_radius_settings = self.get_tokeninfo("radius.system_settings")
        if radius_identifier:
            # New configuration
            radius_server_object = get_radius(radius_identifier)
            radius_server = radius_server_object.config.server
            radius_port = radius_server_object.config.port
            radius_server = u"{0!s}:{1!s}".format(radius_server, radius_port)
            radius_secret = radius_server_object.get_secret()
            radius_dictionary = radius_server_object.config.dictionary

        elif system_radius_settings:
            # system configuration
            radius_server = get_from_config("radius.server")
            radius_secret = get_from_config("radius.secret")
        else:
            # individual token settings
            radius_server = self.get_tokeninfo("radius.server")
            # Read the secret
            secret = self.token.get_otpkey()
            radius_secret = binascii.unhexlify(secret.getKey())

        # here we also need to check for radius.user
        log.debug(u"checking OTP len:{0!s} on radius server: "
                  u"{1!s}, user: {2!r}".format(len(otpval), radius_server,
                                               radius_user))

        try:
            # pyrad does not allow to set timeout and retries.
            # it defaults to retries=3, timeout=5

            # TODO: At the moment we support only one radius server.
            # No round robin.
            server = radius_server.split(':')
            r_server = server[0]
            r_authport = 1812
            if len(server) >= 2:
                r_authport = int(server[1])
            nas_identifier = get_from_config("radius.nas_identifier",
                                             "privacyIDEA")
            if not radius_dictionary:
                radius_dictionary = get_from_config("radius.dictfile",
                                                    "/etc/privacyidea/dictionary")
            log.debug(u"NAS Identifier: %r, "
                      u"Dictionary: %r" % (nas_identifier, radius_dictionary))
            log.debug(u"constructing client object "
                      u"with server: %r, port: %r, secret: %r" %
                      (r_server, r_authport, to_unicode(radius_secret)))

            srv = Client(server=r_server,
                         authport=r_authport,
                         secret=to_bytes(radius_secret),
                         dict=Dictionary(radius_dictionary))

            req = srv.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                                       User_Name=radius_user.encode('utf-8'),
                                       NAS_Identifier=nas_identifier.encode('ascii'))

            req["User-Password"] = req.PwCrypt(otpval)
            if "transactionid" in options:
                req["State"] = str(options.get("transactionid"))

            response = srv.SendPacket(req)
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
                         "access to user %s." % (r_server, radius_user))
                otp_count = 0
            else:
                log.warning("Radiusserver %s rejected "
                            "access to user %s." % (r_server, radius_user))

        except Exception as ex:  # pragma: no cover
            log.error("Error contacting radius Server: {0!r}".format((ex)))
            log.debug("{0!s}".format(traceback.format_exc()))

        return otp_count
