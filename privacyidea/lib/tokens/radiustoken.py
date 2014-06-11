# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
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
'''
  Description:  This file contains the definition of the RADIUS token class
  
  Dependencies: -

'''

import logging

import traceback
import binascii

from privacyidea.lib.util    import getParam
from privacyidea.lib.log import log_with

optional = True
required = False

## for update, we require the TokenClass
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.remotetoken import RemoteTokenClass


log = logging.getLogger(__name__)

# we need this for the radius token
import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary
from pylons.configuration import config as env


VOID_RADIUS_SECRET = "voidRadiusSecret"

###############################################
class RadiusTokenClass(RemoteTokenClass):

    def __init__(self, aToken):
        RemoteTokenClass.__init__(self, aToken)
        self.setType(u"radius")

        self.radiusServer = ""
        self.radiusUser = ""
        self.radiusLocal_checkpin = "0"
        self.radiusSecret = VOID_RADIUS_SECRET

    @classmethod
    def getClassType(cls):
        return "radius"

    @classmethod
    def getClassPrefix(cls):
        return "LSRA"

    @classmethod
    @log_with(log)
    def getClassInfo(cls, key=None, ret='all'):
        '''
        getClassInfo - returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string

        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype: s.o.

        '''
        res = {
               'type'           : 'radius',
               'title'          : 'RADIUS Token',
               'description'    : ('RADIUS token to forward the authentication request to another RADIUS server'),

               'init'         : {'page' : {'html'      : 'radiustoken.mako',
                                            'scope'      : 'enroll', },
                                   'title'  : {'html'      : 'radiustoken.mako',
                                             'scope'     : 'enroll.title', },
                                   },

               'config'        : { 'page' : {'html'      : 'radiustoken.mako',
                                            'scope'      : 'config', },
                                   'title'  : {'html'      : 'radiustoken.mako',
                                             'scope'     : 'config.title', },
                                 },

               'selfservice'   :  {},
               'policy' : {},
               }

        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret


    def update(self, param):

        self.radiusServer = getParam(param, "radius.server", required)
        # if another OTP length would be specified in /admin/init this would
        # be overwritten by the parent class, which is ok.
        self.setOtpLen(6)

        val = getParam(param, "radius.local_checkpin", optional)
        if val is not None:
            self.radiusLocal_checkpin = val

        val = getParam(param, "radius.user", required)
        if val is not None:
            self.radiusUser = val

        val = getParam(param, "radius.secret", required)
        if val is not None:
            self.radiusSecret = val

        if self.radiusSecret == VOID_RADIUS_SECRET:
            log.warning("Usage of default radius secret is not recomended!!")


        TokenClass.update(self, param)
        # We need to write the secret!
        self.token.setHKey(binascii.hexlify(self.radiusSecret))

        self.addToTokenInfo("radius.server", self.radiusServer)
        self.addToTokenInfo("radius.local_checkpin", self.radiusLocal_checkpin)
        self.addToTokenInfo("radius.user", self.radiusUser)

    @log_with(log)
    def check_pin_local(self):
        """
        lookup if pin should be checked locally or on radius host

        :return: bool
        """
        local_check = False

        if 1 == int(self.getFromTokenInfo("radius.local_checkpin")):
            local_check = True
        log.debug(" local checking pin? %r" % local_check)

        return local_check

    @log_with(log)
    def checkPin(self, pin, options=None):
        '''
        check the pin - either remote or localy
        - in case of remote, we return true, as the
          the splitPinPass will put the passw then in the otpVal

        :param pin: the pin which should be checked
        :param options: the additional request parameters
        '''
        res = True

        if self.check_pin_local():
            log.debug("checking PIN locally")
            res = RemoteTokenClass.checkPin(self, pin)

        return res

    @log_with(log)
    def splitPinPass(self, passw):
        '''
        Split the PIN and the OTP value.
        Only if it is locally checked and not remotely.
        '''
        res = 0
        pin = ""
        otpval = ""

        local_check = self.check_pin_local()
        log.debug("local checking pin? %r"
                  % local_check)

        if self.check_pin_local():
            log.debug("locally checked")
            (res, pin, otpval) = TokenClass.splitPinPass(self, passw)
        else:
            log.debug("remotely checked")
            pin = ""
            otpval = passw
        return (res, pin, otpval)

    @log_with(log)
    def do_request(self, anOtpVal, transactionid=None, user=None):
        '''
        Here we contact the Radius Server to verify the pass
        '''
        log.debug("do_request")

        reply = {}
        res = False
        otp_count = -1

        radiusServer = self.getFromTokenInfo("radius.server")
        radiusUser = self.getFromTokenInfo("radius.user")

        ## Read the secret!!!
        secret = self.token.getHOtpKey()
        radiusSecret = binascii.unhexlify(secret.getKey())

        if radiusSecret == VOID_RADIUS_SECRET:
            log.warning("Usage of default radius secret is not recomended!!")

        ## here we also need to check for radius.user
        log.debug("checking OTP len:%s on radius server: %s, user: %s" 
                  % (len(anOtpVal), radiusServer, radiusUser))

        try:
            # pyrad does not allow to set timeout and retries.
            # it defaults to retries=3, timeout=5

            # TODO: At the moment we support only one radius server.
            # No round robin.
            server = radiusServer.split(':')
            r_server = server[0]
            r_authport = 1812
            nas_identifier = env.get("radius.nas_identifier", "privacyIDEA")
            r_dict = env.get("radius.dictfile", "/etc/privacyidea/dictionary")

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

            req["User-Password"] = req.PwCrypt(anOtpVal)
            if transactionid is not None:
                req["State"] = str(transactionid)

            response = srv.SendPacket(req)

            if response.code == pyrad.packet.AccessChallenge:
                opt = {}
                for attr in response.keys():
                    opt[attr] = response[attr]
                res = False
                log.debug("challenge returned %r " % opt)
                ## now we map this to a privacyidea challenge
                if "State" in opt:
                    reply["transactionid"] = opt["State"][0]
                if "Reply-Message" in opt:
                    reply["message"] = opt["Reply-Message"][0]

            elif response.code == pyrad.packet.AccessAccept:
                log.info("Radiusserver %s granted "
                         "access to user %s." % (r_server, radiusUser))
                otp_count = 0
                res = True
            else:
                log.warning("Radiusserver %s"
                            "rejected access to user %s." %
                            (r_server, radiusUser))
                res = False

        except Exception as ex:
            log.error("Error contacting radius Server: %r" % (ex))
            log.error(traceback.format_exc())

        return (res, otp_count, reply)

