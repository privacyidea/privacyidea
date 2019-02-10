# -*- coding: utf-8 -*-
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2019-02-08   Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               Start the pushtoken class
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
__doc__ = """The pushtoken sends a push notification via firebase
to the registered smartphone.
The token is a challenge response token. The smartphone will sign the challenge
and send it back to the authentication endpoint. 

This code is tested in tests/test_lib_tokens_push
"""

import datetime
import json
import traceback
from six.moves.urllib.parse import quote

from privacyidea.api.lib.utils import getParam
from privacyidea.api.lib.utils import required, optional
from privacyidea.lib.utils import is_true

from privacyidea.lib.config import get_from_config
from privacyidea.lib.policy import SCOPE, ACTION, get_action_values_from_options
from privacyidea.lib.log import log_with
from json import loads
from privacyidea.lib import _

from privacyidea.lib.tokenclass import TokenClass
from privacyidea.models import Challenge
from privacyidea.lib.decorators import check_token_locked
import logging
from privacyidea.lib.apps import create_google_authenticator_url as cr_google
import binascii
from privacyidea.lib.utils import create_img, is_true, b32encode_and_unicode
from privacyidea.lib.error import ParameterError, PolicyError
from privacyidea.lib.user import User
from privacyidea.lib.apps import _construct_extra_parameters
from privacyidea.lib.crypto import geturandom

log = logging.getLogger(__name__)


class PUSH_ACTION(object):
    REGISTRATION_URL = "push_registration_url"
    TTL = "push_time_to_live"


@log_with(log)
def create_push_token_url(url=None, ttl=10, issuer="privacyIDEA", serial="mylabel",
                          tokenlabel="<s>", user_obj=None, extra_data=None, user=None, realm=None):
    """

    :param url:
    :param ttl:
    :param issuer:
    :param serial:
    :param tokenlabel:
    :param user_obj:
    :param extra_data:
    :param user:
    :param realm:
    :return:
    """
    extra_data = extra_data or {}

    # policy depends on some lib.util

    user_obj = user_obj or User()

    # We need realm und user to be a string
    realm = realm or ""
    user = user or ""

    # Deprecated
    label = tokenlabel.replace("<s>",
                               serial).replace("<u>",
                                               user).replace("<r>", realm)
    label = label.format(serial=serial, user=user, realm=realm,
                         givenname=user_obj.info.get("givenname", ""),
                         surname=user_obj.info.get("surname", ""))

    issuer = issuer.format(serial=serial, user=user, realm=realm,
                           givenname=user_obj.info.get("givenname", ""),
                           surname=user_obj.info.get("surname", ""))

    url_label = quote(label.encode("utf-8"))
    url_issuer = quote(issuer.encode("utf-8"))
    url_url = quote(url.encode("utf-8"))

    return ("otpauth://pipush/{label!s}?"
            "url={url!s}&ttl={ttl!s}&"
            "issuer={issuer!s}{extra}".format(label=url_label, issuer=url_issuer,
                                       url=url_url, ttl=ttl,
                                       extra=_construct_extra_parameters(extra_data)))


class PushTokenClass(TokenClass):
    """
    The PUSH token uses the firebase service to send challenges to the
    users smartphone. The user confirms on the smartphon, signes the
    challenge and sends it back to privacyIDEA.

    The enrollment occurs in two enrollment steps:

    # Step 1

    The device is enrolled using a QR code, that looks like this:

    otpauth://pipush/PIPU0006EF85?url=https://yourprivacyideaserver/enroll/this/token&ttl=120

    # Step 2

    In the QR code is a URL, where the smartphone sends the remaining data for the enrollment.

    POST https://yourprivacyideaserver/ttype/push
     enrollment_credential=<some credential>
     serial=<token serial>
     fbtoken=<firebase token>
     pubkey=<public key>

    For more information see:
    https://github.com/privacyidea/privacyidea/issues/1342
    https://github.com/privacyidea/privacyidea/wiki/concept%3A-PushToken

    """
    def __init__(self, db_token):
        TokenClass.__init__(self, db_token)
        self.set_type(u"push")
        self.mode = ['challenge']
        self.hKeyRequired = False


    @staticmethod
    def get_class_type():
        """
        return the generic token class identifier
        """
        return "push"

    @staticmethod
    def get_class_prefix():
        return "PIPU"

    @staticmethod
    def get_class_info(key=None, ret='all'):
        """
        returns all or a subtree of the token definition

        :param key: subsection identifier
        :type key: str
        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype : s.o.
        """
        res = {'type': 'push',
               'title': _('PUSH Token'),
               'description':
                    _('PUSH: Send a push notification to a smartphone.'),
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.ENROLL: {
                       PUSH_ACTION.TTL: {
                           'type': 'int',
                           'desc': _('How long should the second step of the enrollment be accepted (in seconds).'),
                       },
                       PUSH_ACTION.REGISTRATION_URL: {
                           'type': 'str',
                           'desc': _('The URL the Push App should contact in the second enrollment step.'
                                     ' Usually it is the endpoint /ttype/push of the privacyIDEA server.')
                       }
                   },
               },
        }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res

        return ret

    @log_with(log)
    def update(self, param, reset_failcount=True):
        """
        process the initialization parameters

        We need to distinguish the first authentication step
        and the second authentication step.

        1. step:
            parameter type contained.
            parameter genkey contained.

        2. step:
            parameter serial contained
            parameter fbtoken contained
            parameter pubkey contained

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing
        """
        upd_param = {}
        for k, v in param.items():
            upd_param[k] = v

        if "serial" in upd_param and "fbtoken" in upd_param and "pubkey" in upd_param:
            # We are in step 2:
            if not self.token.rollout_state == "clientwait":
                raise ParameterError("Invalid state! The token you want to enroll is not in the state 'clientwait'.")
            if upd_param.get("enrollment_credential") != self.get_tokeninfo("enrollment_credential"):
                raise ParameterError("Invalid enrollment credential. You are not authorized to finalize this token.")
            self.del_tokeninfo("enrollment_credential")
            self.token.rollout_state = "enrolled"
            self.add_tokeninfo("public_key_smartphone", upd_param.get("pubkey"))
            self.add_tokeninfo("firebase_token", upd_param.get("fbtoken"))
            # create a keypair for the server side.
            from privacyidea.lib.crypto import generate_keypair
            pub_key, priv_key = generate_keypair()
            self.add_tokeninfo("public_key_server", pub_key)
            self.set_otpkey(priv_key)
            # TODO: Add optional additional info, that was sent by the smartphone

        elif "genkey" in upd_param:
            # We are in step 1:
            upd_param["2stepinit"] = 1
            self.add_tokeninfo("enrollment_credential", geturandom(20, hex=True))
        else:
            raise ParameterError("Invalid Parameters. Either provide (genkey) or (serial, fbtoken, pubkey).")

        TokenClass.update(self, upd_param, reset_failcount)

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        This returns the init details during enrollment.

        In the 1st step the QR Code is returned.
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        if "otpkey" in response_detail:
            del response_detail["otpkey"]
        params = params or {}
        user = user or User()
        tokenlabel = params.get("tokenlabel", "<s>")
        tokenissuer = params.get("tokenissuer", "privacyIDEA")
        # Add rollout state the response
        response_detail['rollout_state'] = self.token.rollout_state

        extra_data = {"enrollment_credential": self.get_tokeninfo("enrollment_credential")}
        imageurl = params.get("appimageurl")
        if imageurl:
            extra_data.update({"image": imageurl})
        if self.token.rollout_state == "clientwait":
            # We display this during the first enrollment step!
            qr_url = create_push_token_url(url=params.get("registration_url"),
                                           user=user.login,
                                           realm=user.realm,
                                           serial=self.get_serial(),
                                           tokenlabel=tokenlabel,
                                           issuer=tokenissuer,
                                           user_obj=user,
                                           extra_data=extra_data,
                                           ttl=params.get("ttl"))
            response_detail["pushurl"] = {"description": _("URL for privacyIDEA Push Token"),
                                          "value": qr_url,
                                          "img": create_img(qr_url, width=250)
                                          }

            response_detail["enrollment_credential"] = self.get_tokeninfo("enrollment_credential")

        elif self.token.rollout_state == "enrolled":
            response_detail["public_key"] = self.get_tokeninfo("public_key_server")

        return response_detail

    @classmethod
    def api_endpoint(cls, request, g):
        """
        This provides a function which is called by the API endpoint
        /ttype/push which is defined in api/ttype.py

        The method returns
            return "json", {}

        :param request: The Flask request
        :param g: The Flask global object g
        :return: dictionary
        """
        from privacyidea.lib.token import get_tokens
        from privacyidea.lib.utils import prepare_result
        serial = getParam(request.all_data, "serial", optional=False)
        toks = get_tokens(serial=serial, rollout_state="clientwait")
        if len(toks) == 0:
            raise ParameterError("No token with this serial number in the rollout state 'clientwait'.")
        token_obj = toks[0]

        token_obj.update(request.all_data)
        init_detail_dict = request.all_data

        init_details = token_obj.get_init_detail(init_detail_dict)

        return "json", prepare_result(True, details=init_details)