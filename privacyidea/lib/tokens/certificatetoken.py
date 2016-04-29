# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  Aug 12, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2016-04-26 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add the possibility to create key pair on server side
#             Provide download for pkcs12 file
#
#  2015-05-15 Adapt during migration to flask
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
"""
This file contains the definition of the CertificateToken class.

The code is tested in test_lib_tokens_certificate.py.
"""

import logging
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.caconnector import get_caconnector_object
from privacyidea.lib.user import get_user_from_param
from OpenSSL import crypto
from privacyidea.lib.decorators import check_token_locked
import base64

optional = True
required = False

log = logging.getLogger(__name__)


class CertificateTokenClass(TokenClass):
    """
    Token to implement an X509 certificate.
    The certificate can be enrolled by sending a CSR to the server or the
    keypair is created by the server. If the server creates the keypair,
    the user can download a PKCS12 file.
    The OTP PIN is used as passphrase for the PKCS12 file.

    privacyIDEA is capable of working with different CA connectors.

    Valid parameters are *request* or *certificate*, both PEM encoded.
    If you pass a *request* you also need to pass the *ca* that should be
    used to sign the request. Passing a *certificate* just uploads the
    certificate to a new token object.

    A certificate token can be created by an administrative task with the
    token/init api like this:

      **Example Initialization Request**:

        .. sourcecode:: http

           POST /auth HTTP/1.1
           Host: example.com
           Accept: application/json

           type=certificate
           user=cornelius
           realm=realm1
           request=<PEM encoded request>
           ca=<name of the ca connector>

      **Example Initialization Request, key generation on servers side**

      In this case the certificate is created on behalf of another user.

        .. sourcecode:: http

           POST /auth HTTP/1.1
           Host: example.com
           Accept: application/json

           type=certificate
           user=cornelius
           realm=realm1
           generate=1
           ca=<name of the ca connector>

      **Example response**:

           .. sourcecode:: http

               HTTP/1.1 200 OK
               Content-Type: application/json

               {
                  "detail": {
                    "certificate": "...PEM..."
                  },
                  "id": 1,
                  "jsonrpc": "2.0",
                  "result": {
                    "status": true,
                    "value": true
                  },
                  "version": "privacyIDEA unknown"
                }

    """
    using_pin = False
    hKeyRequired = False

    def __init__(self, aToken):
        TokenClass.__init__(self, aToken)
        self.set_type(u"certificate")
        self.otp_len = 0

    @staticmethod
    def get_class_type():
        return "certificate"

    @staticmethod
    def get_class_prefix():
        return "CRT"

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
        :rtype: dict or scalar
        """
        res = {'type': 'certificate',
               'title': 'Certificate Token',
               'description': ('Certificate: Enroll an x509 Certificate '
                               'Token.'),
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

    def update(self, param):
        """
        This method is called during the initialization process.
        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        TokenClass.update(self, param)

        request = getParam(param, "request", optional)
        spkac = getParam(param, "spkac", optional)
        certificate = getParam(param, "certificate", optional)
        generate = getParam(param, "genkey", optional)
        if request or generate:
            # If we do not upload a user certificate, then we need a CA do
            # sign the uploaded request or generated certificate.
            ca = getParam(param, "ca", required)
            self.add_tokeninfo("CA", ca)
            cacon = get_caconnector_object(ca)
        if request:
            # During the initialization process, we need to create the
            # certificate
            x509object = cacon.sign_request(request,
                                            options={"spkac": spkac})
            certificate = crypto.dump_certificate(crypto.FILETYPE_PEM,
                                                  x509object)
        elif generate:
            # Create the certificate on behalf of another user.
            # Now we need to create the key pair,
            # the request
            # and the certificate
            # We need the user for whom the certificate should be created
            user = get_user_from_param(param, optionalOrRequired=required)

            keysize = getParam(param, "keysize", optional, 2048)
            key = crypto.PKey()
            key.generate_key(crypto.TYPE_RSA, keysize)
            req = crypto.X509Req()
            req.get_subject().CN = user.login
            # Add email to subject
            if user.info.get("email"):
                req.get_subject().emailAddress = user.info.get("email")
            req.get_subject().organizationalUnitName = user.realm
            # TODO: Add Country, Organization, Email
            # req.get_subject().countryName = 'xxx'
            # req.get_subject().stateOrProvinceName = 'xxx'
            # req.get_subject().localityName = 'xxx'
            # req.get_subject().organizationName = 'xxx'
            req.set_pubkey(key)
            req.sign(key, "sha256")
            x509object = cacon.sign_request(crypto.dump_certificate_request(
                crypto.FILETYPE_PEM, req))
            certificate = crypto.dump_certificate(crypto.FILETYPE_PEM,
                                                  x509object)
            # Save the private key to the encrypted key field of the token
            s = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
            self.add_tokeninfo("privatekey", s, value_type="password")

        if certificate:
            self.add_tokeninfo("certificate", certificate)

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we return the certificate and the
        PKCS12 file, if the private key exists.
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        params = params or {}
        certificate = self.get_tokeninfo("certificate")
        response_detail["certificate"] = certificate
        privatekey = self.get_tokeninfo("privatekey")
        # If there is a private key, we dump a PKCS12
        if privatekey:
            response_detail["pkcs12"] = base64.b64encode(
                self._create_pkcs12_bin())

        return response_detail

    def _create_pkcs12_bin(self):
        """
        Helper function to create an encrypted pkcs12 binary for download

        :return: PKCS12 binary
        """
        certificate = self.get_tokeninfo("certificate")
        privatekey = self.get_tokeninfo("privatekey")
        pkcs12 = crypto.PKCS12()
        pkcs12.set_certificate(crypto.load_certificate(
            crypto.FILETYPE_PEM, certificate))
        pkcs12.set_privatekey(crypto.load_privatekey(crypto.FILETYPE_PEM,
                                                     privatekey))
        # TODO define a random passphrase and hand it to the user
        passphrase = self.token.get_pin()
        if passphrase == -1:
            passphrase = ""
        pkcs12_bin = pkcs12.export(passphrase=passphrase)
        return pkcs12_bin

    def get_as_dict(self):
        """
        This returns the token data as a dictionary.
        It is used to display the token list at /token/list.

        The certificate token can add the PKCS12 file if it exists

        :return: The token data as dict
        :rtype: dict
        """
        # first get the database values as dict
        token_dict = self.token.get()

        if "privatekey" in token_dict.get("info"):
            token_dict["info"]["pkcs12"] = base64.b64encode(
                self._create_pkcs12_bin())
            #del(token_dict["privatekey"])

        return token_dict

    @check_token_locked
    def set_pin(self, pin, encrypt=False):
        """
        set the PIN of a token.
        The PIN of the certificate token is stored encrypted. It is used as
        passphrase for the PKCS12 file.

        :param pin: the pin to be set for the token
        :type pin: basestring
        :param encrypt: If set to True, the pin is stored encrypted and
                        can be retrieved from the database again
        :type encrypt: bool
        """
        storeHashed = False
        self.token.set_pin(pin, storeHashed)
