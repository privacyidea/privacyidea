# -*- coding: utf-8 -*-
#
#  http://www.privacyidea.org
#  2015-09-21 Initial writeup.
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
U2F Token
"""

from privacyidea.api.lib.utils import getParam
from privacyidea.lib.config import get_from_config
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import generate_otpkey
from privacyidea.lib.utils import create_img
import logging
from privacyidea.lib.token import get_tokens
from privacyidea.lib.error import ParameterError
from privacyidea.models import Challenge
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.tokens.ocra import OCRASuite, OCRA
from privacyidea.lib.challenge import get_challenges
from privacyidea.models import cleanup_challenges
import gettext
from privacyidea.lib.policydecorators import challenge_response_allowed
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.crypto import geturandom
import base64


U2F_Version = "U2F_V2"

log = logging.getLogger(__name__)
optional = True
required = False
_ = gettext.gettext


class U2fTokenClass(TokenClass):
    """
    The U2F Token implementation.
    """

    @classmethod
    def get_class_type(cls):
        """
        Returns the internal token type identifier
        :return: tiqr
        :rtype: basestring
        """
        return "u2f"

    @classmethod
    def get_class_prefix(cls):
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: U2F
        :rtype: basestring
        """
        return "U2F"

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
        res = {'type': 'u2f',
               'title': 'U2F Token',
               'description': 'U2F: Enroll a U2F token.',
               'init': {},
               'config': {},
               'user':  ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {},
               }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new U2F Token object from a database object

        :param db_token: instance of the orm db object
        :type db_token: DB object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"u2f")
        self.hKeyRequired = False
        self.init_step = 1

    def update(self, param):
        """
        This method is called during the initialization process.

        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        #user_object = get_user_from_param(param)
        #self.set_user(user_object)
        TokenClass.update(self, param)
        # We have to set the realms here, since the token DB object does not
        # have an ID before TokenClass.update.
        #self.set_realms([user_object.realm])

        description = ""
        reg_data = getParam(param, "regdata")
        if reg_data:
            self.init_step = 2
            pad_len = len(reg_data) % 4
            padding = pad_len * "="
            reg_data_bin = base64.urlsafe_b64decode(str(reg_data) + padding)
            # see
            # https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment
            # -20150514/fido-u2f-raw-message-formats.html#registration-messages
            reserved_byte = reg_data_bin[0]  # must be '\x05'
            user_pub_key = reg_data_bin[1:66]
            key_handle_len = ord(reg_data_bin[66])
            key_handle = reg_data_bin[67:67+key_handle_len]
            certificate = reg_data_bin[67+key_handle_len:]
            from OpenSSL import crypto
            x509 = crypto.load_certificate(crypto.FILETYPE_ASN1, certificate)
            # TODO: We might want to check the certificate.
            pkey = x509.get_pubkey()
            subj_x509name = x509.get_subject()
            issuer = x509.get_issuer()
            not_after = x509.get_notAfter()
            subj_list = subj_x509name.get_components()
            for component in subj_list:
                # each component is a tuple. We are looking for CN
                if component[0].upper() == "CN":
                    description = component[1]
                    break
        self.set_description(description)

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we ask the user the press the button
        """
        response_detail = {}
        if self.init_step == 1:
            # This is the first step of the init request
            app_id = "http://localhost:5000"
            nonce = base64.urlsafe_b64encode(geturandom(32))
            response_detail = TokenClass.get_init_detail(self, params, user)
            register_request = {"version": U2F_Version,
                                "challenge": nonce,
                                "appId": app_id,
                                "origin": app_id}
            response_detail["u2fRegisterRequest"] = register_request

        elif self.init_step == 2:
            # This is the second step of the init request
            response_detail["u2fResponse"] = {"subject": self.token.description}

        return response_detail


