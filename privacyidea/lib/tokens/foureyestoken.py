# -*- coding: utf-8 -*-
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2015-08-28 Initial writeup of the 4eyes token
#             according to
#             https://github.com/privacyidea/privacyidea/issues/167
#             Cornelius Kölbel <cornelius@privacyidea.org>
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
__doc__ = """This is the implementation of the 4eyes token.
The 4eyes token combines several other tokens to a virtual new token,
requiring that 2 or more users with different tokens are present to
authenticate.

A 4eyes token stores the required number of tokens of each realm
and the splitting sign.

The code is tested in tests/test_lib_tokens_4eyes.
"""
import logging
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.error import ParameterError
from privacyidea.lib.token import check_realm_pass
from privacyidea.lib.decorators import check_token_locked

log = logging.getLogger(__name__)
optional = True
required = False


class FourEyesTokenClass(TokenClass):
    """
    The FourEyes token can be used to implement the Two Man Rule.
    The FourEyes token defines how many tokens of which realms are required
    like:
    * 2 tokens of RealmA
    * 1 token of RealmB

    Then users (the owners of those tokens) need to login by everyone
    entering their OTP PIN and OTP value. It does not matter, in which order
    they enter the values. All their PINs and OTPs are concatenated into one
    password field but need to be separated by the splitting sign.

    The FourEyes token again splits the password value and tries to
    authenticate each of the these passwords in the realms using the function
    ``check_realm_pass``.

    The FourEyes token itself does not provide an OTP PIN.

    The token is initialized using additional parameters at token/init:

    **Example Authentication Request**:

        .. sourcecode:: http

           POST /auth HTTP/1.1
           Host: example.com
           Accept: application/json

           type=4eyes
           user=cornelius
           realm=realm1
           4eyes=realm1:2,realm2:1
           separator=%20
    """

    def __init__(self, db_token):
        """
        :param db_token: the token
        :type db_token: database token object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"4eyes")
        # We can not do challenge response
        self.mode = ['authenticate']

    @classmethod
    def get_class_type(cls):
        """
        return the class type identifier
        """
        return "4eyes"

    @classmethod
    def get_class_prefix(cls):
        """
        return the token type prefix
        """
        return "PI4E"

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
        res = {'type': '4eyes',
               'title': '4Eyes Token',
               'description': ('4Eyes Token: Use tokens of two or more users '
                               'to authenticate'),
               'init': {},
               'config': {},
               'user':  [],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin"],
               'policy': {},
               }

        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    @classmethod
    def realms_dict_to_string(cls, realms):
        """
        This function converts the realms - if it is a dictionary - to a string.

        {"realm1": {"selected": True,
                    "count": 1 },
         "realm2": {"selected": True,
                    "count": 2} -> realm1:1,realm2:2
        :param realms: the realms as they are passed from the WebUI
        :type realms: dict
        :return: realms
        :rtype: basestring
        """
        realms_string = ""
        if type(realms) is dict:
            for realmname, v in realms.items():
                if v.get("selected"):
                    realms_string += "%s:%s," % (realmname, v.get("count"))
            if realms_string[-1] == ',':
                realms_string = realms_string[:-1]
        else:
            realms_string = realms

        return realms_string

    @classmethod
    def convert_realms(cls, realms):
        """
        This function converts the realms as given by the API parameter to a
        dictionary.

        realm1:2,realm2:1 -> {"realm1":2,
                              "realm2":1}

        :param realms: a serialized list of realms
        :type realms: basestring
        :return: dict of realms
        """
        realms_dict = {}
        realm_list = realms.split(",")
        for rl in realm_list:
            r = rl.split(":")
            if len(r) == 2:
                realms_dict[r[0]] = int(r[1])
        return realms_dict

    def _get_realms(self):
        """
        This returns the dictionary how many tokens of each realm are necessary
        :return: dict with realms
        """
        return self.convert_realms(self.get_tokeninfo("4eyes"))

    def _get_separator(self):
        return self.get_tokeninfo("separator") or " "

    def update(self, param):
        """
        This method is called during the initialization process.
        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        TokenClass.update(self, param)

        realms = getParam(param, "4eyes", required)
        separator = getParam(param, "separator", optional, default=" ")
        if len(separator) > 1:
            raise ParameterError("The separator must only be one single "
                                 "character")
        realms = self.realms_dict_to_string(realms)
        self.convert_realms(realms)
        self.add_tokeninfo("separator", separator)
        self.add_tokeninfo("4eyes", realms)

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
        pin_match = True
        otp_counter = -1
        reply = None

        required_realms = self._get_realms()
        # This holds the found serial numbers in the realms
        found_serials = {}

        separator = self._get_separator()
        passwords = passw.split(separator)

        for realm in required_realms.keys():
            found_serials[realm] = []
            for otp in passwords:
                res, reply = check_realm_pass(realm, otp)
                if res:
                    serial = reply.get("serial")
                    found_serials[realm].append(serial)
            # uniquify the serials in the list
            found_serials[realm] = list(set(found_serials[realm]))

            if len(found_serials[realm]) < required_realms[realm]:
                reply = {"foureyes": "Only found %i tokens in realm %s" % (
                    len(found_serials[realm]), realm)}
                otp_counter = -1
                break
            else:
                otp_counter = 1

        return pin_match, otp_counter, reply
