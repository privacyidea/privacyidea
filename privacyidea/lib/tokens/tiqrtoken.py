# -*- coding: utf-8 -*-
#
#  http://www.privacyidea.org
#  2015-09-01 Initial writeup.
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
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
__doc__ = """
This is the implementation for the TiQR token. See:
    https://tiqr.org
    https://www.usenix.org/legacy/events/lisa11/tech/full_papers/Rijswijk.pdf

The TiQR token is a special App based token, which allows easy login and
which is based on OCRA.

This code is tested in tests/test_lib_tokens_tiqr
"""

import time
from .HMAC import HmacOtp
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.config import get_from_config
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.apps import create_google_authenticator_url as cr_google
from privacyidea.lib.apps import create_oathtoken_url as cr_oath
from privacyidea.lib.utils import create_img
from privacyidea.lib.utils import generate_otpkey
from privacyidea.lib.utils import create_img
import traceback
import logging
from privacyidea.lib.token import get_tokens
from privacyidea.lib.error import ParameterError

log = logging.getLogger(__name__)
optional = True
required = False
import gettext
_ = gettext.gettext

keylen = {'sha1': 20,
          'sha256': 32,
          'sha512': 64
          }


class TiqrTokenClass(TokenClass):
    """
    The TiQR Token implementation.

    It generated an enrollment QR code, which contains a link with the more
    detailed enrollment information.
    """

    @classmethod
    def get_class_type(cls):
        """
        Returns the internal token type identifier
        :return: tiqr
        :rtype: basestring
        """
        return "tiqr"

    @classmethod
    def get_class_prefix(cls):
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: TiQR
        :rtype: basestring
        """
        return "TiQR"

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
        :rtype: dict or scalar
        """
        res = {'type': 'tiqr',
               'title': 'TiQR Token',
               'description': ('TiQR: Enroll a TiQR token.'),
               'init': {},
               'config': {},
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

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new TiQR Token object from a database object

        :param db_token: instance of the orm db object
        :type db_token: DB object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"tiqr")
        self.hKeyRequired = False

    def update(self, param):
        """
        This method is called during the initialization process.

        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        ocrasuite_default = "OCRA-1:HOTP-SHA1-6:QH10-S"
        ocrasuite = get_from_config("tiqr.ocrasuite") or ocrasuite_default
        self.add_tokeninfo("ocrasuite", ocrasuite)
        TokenClass.update(self, param)

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we return the URL for the TiQR App.
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        params = params or {}
        #secretHOtp = self.token.get_otpkey()
        #registrationcode = secretHOtp.getKey()
        #response_detail["registrationcode"] = registrationcode
        enroll_url = get_from_config("tiqr.regServer")
        log.info("using tiqr.regServer for enrollment: %s" % enroll_url)
        serial = self.token.serial
        session = generate_otpkey()
        # save the session in the token
        self.add_tokeninfo("session", session)
        tiqrenroll = "tiqrenroll://%s?action=metadata&session=%s&serial=%s" % (
            enroll_url, session, serial)

        response_detail["tiqrenroll"] = {"description":
                                                    _("URL for TiQR "
                                                      "enrollment"),
                                         "value": tiqrenroll,
                                         "img": create_img(tiqrenroll,
                                                           width=250)}

        return response_detail

    @classmethod
    def api_endpoint(cls, params):
        """
        This provides a function to be plugged into the API endpoint
        /ttype/<tokentype> which is defined in api/ttype.py

        :param params: The Request Parameters which can be handled with getParam
        :return: Flask Response
        """
        action = getParam(params, "action", required)
        allowed_actions = ["metadata", "enrollment"]
        if action not in allowed_actions:
            raise ParameterError("Allowed actions are %s" % allowed_actions)

        if action == "metadata":
            session = getParam(params, "session", required)
            serial = getParam(params, "serial", required)
            # The user identifier is displayed in the App
            # TODO: We need to set the user ID
            user_idenitfier = "1289734"
            user_displayname = "hans"

            ocrasuite_default = "OCRA-1:HOTP-SHA1-6:QH10-S"
            ocrasuite = get_from_config("tiqr.ocrasuite") or ocrasuite_default
            service_displayname = get_from_config("tiqr.serviceDisplayname") or \
                                  "privacyIDEA"
            reg_server = get_from_config("tiqr.regServer")
            auth_server = get_from_config("tiqr.authServer") or reg_server

            service = {"displayName": service_displayname,
                       "identifier": "org.privacyidea",
                       "logoUrl": "https://www.privacyidea.org/wp-content/uploads"
                                  "/2014/05/privacyIDEA1.png",
                       "infoUrl": "https://www.privacyidea.org",
                       "authenticationUrl":
                           "%s/validate/check" % auth_server,
                       "ocraSuite": ocrasuite,
                       "enrollmentUrl":
                           "%s?action=enrollment&session=%s&serial=%s" % (reg_server,
                                                            session, serial)
                       }
            identity = {"identifier": user_idenitfier,
                        "displayName": user_displayname
                        }

            res = {"service": service,
                   "identity": identity
                   }

            return "json", res

        elif action == "enrollment":
            """
            operation: register
            secret: HEX
            notificationType: GCM
            notificationAddress: ...
            language: de
            session:
            serial:
            """
            res = "Fail"
            serial = getParam(params, "serial", required)
            session = getParam(params, "session", required)
            secret = getParam(params, "secret", required)
            # The secret needs to be stored in the token object.
            # We take the token "serial" and check, if it contains the "session"
            # in the tokeninfo.
            enroll_tokens = get_tokens(serial=serial)
            if len(enroll_tokens) == 1:
                if enroll_tokens[0].get_tokeninfo("session") == session:
                    # save the secret
                    enroll_tokens[0].set_otpkey(secret)
                    # delete the session
                    enroll_tokens[0].del_tokeninfo("session")
                    res = "OK"
                else:
                    raise ParameterError("Invalid Session")

            return "text", res
