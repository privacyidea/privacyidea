# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  Aug 12, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
from OpenSSL import crypto

optional = True
required = False

log = logging.getLogger(__name__)


class CertificateTokenClass(TokenClass):
    """
    Token to implement an X509 certificate.
    The certificate can be enrolled by sending a CSR to the server.
    privacyIDEA is capable of working with different CA connectors.

    Valid parameters are *request* or *certificate*, both PEM encoded.
    If you pass a *request* you also need to pass the *ca* that should be
    used to sign the request. Passing a *certificate* just uploads the
    certificate to a new token object.

    A certificate token can be created by an administrative task with the
    token/init api like this:

      **Example Authentication Request**:

        .. sourcecode:: http

           POST /auth HTTP/1.1
           Host: example.com
           Accept: application/json

           type=certificate
           user=cornelius
           realm=realm1
           request=<PEM encoded request>
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

    @classmethod
    def get_class_type(cls):
        return "certificate"

    @classmethod
    def get_class_prefix(cls):
        return "CRT"

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

        if key is not None and res.has_key(key):
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
        certificate = None
        if request:
            ca = getParam(param, "ca", required)
            self.add_tokeninfo("CA", ca)
            # During the initialization process, we need to create the
            # certificate
            cacon = get_caconnector_object(ca)
            x509object = cacon.sign_request(request,
                                            options={"spkac": spkac})
            certificate = crypto.dump_certificate(crypto.FILETYPE_PEM,
                                                  x509object)
        else:
            certificate = getParam(param, "certificate", optional)

        if certificate:
            self.add_tokeninfo("certificate", certificate)

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we return the certificate
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        params = params or {}
        certificate = self.get_tokeninfo("certificate")
        response_detail["certificate"] = certificate
        return response_detail
