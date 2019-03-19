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

from privacyidea.lib.utils import to_unicode
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.caconnector import get_caconnector_object
#from privacyidea.lib.user import get_user_from_param
from OpenSSL import crypto
from privacyidea.lib.decorators import check_token_locked
import base64
from privacyidea.lib import _

from privacyidea.lib.user import get_user_from_param, User, get_user_info
from privacyidea.lib.token import get_tokens
from privacyidea.lib.error import NoCertificateAvailableError
import json

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
               'description': _('Certificate: Enroll an x509 Certificate '
                                'Token.'),
               'init': {},
               'config': {},
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
        template_name = getParam(param, "template", optional)
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
                                            options={"spkac": spkac,
                                                     "template": template_name})
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
            csr = to_unicode(crypto.dump_certificate_request(crypto.FILETYPE_PEM, req))
            x509object = cacon.sign_request(csr, options={"template": template_name})
            certificate = crypto.dump_certificate(crypto.FILETYPE_PEM,
                                                  x509object)
            # Save the private key to the encrypted key field of the token
            s = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
            self.add_tokeninfo("privatekey", s, value_type="password")

        if "pin" in param:
            self.set_pin(param.get("pin"), encrypt=True)

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

    def revoke(self):
        """
        This revokes the token. We need to determine the CA, which issues the
        certificate, contact the connector and revoke the certificate

        Some token types may revoke a token without locking it.
        """
        TokenClass.revoke(self)

        # determine the CA and its connector.
        ti = self.get_tokeninfo()
        ca_specifier = ti.get("CA")
        log.debug("Revoking certificate {0!s} on CA {1!s}.".format(
            self.token.serial, ca_specifier))
        certificate_pem = ti.get("certificate")

        # call CAConnector.revoke_cert()
        ca_obj = get_caconnector_object(ca_specifier)
        revoked = ca_obj.revoke_cert(certificate_pem)
        log.info("Certificate {0!s} revoked on CA {1!s}.".format(revoked,
                                                                 ca_specifier))

        # call CAConnector.create_crl()
        crl = ca_obj.create_crl()
        log.info("CRL {0!s} created.".format(crl))

        return revoked
    
    
    @staticmethod
    def api_endpoint(request, g):
        """
        Author : Tarek EL ALLAM
        This provides a function to be plugged into the API endpoint
        /ttype/<tokentype> which is defined in api/ttype.py
        See :ref:`rest_ttype`.
        Desc : 
        Add API call in order to get the last generated certificate assigned, activated, unrevoked and unlocked.
        
        Example call :
        curl -k -H "Accept: application/json" -H "Content-Type: application/json" -X GET "https://localhost/ttype/certificate?user=USERID&realm=REALMID"

        Example of response OK :
        curl -k -H "Accept: application/json" -H "Content-Type: application/json" -X GET "https://localhost/ttype/certificate?user=PC1A000400005700036&realm=domaine"
        HTTP/1.1 200 OK
        Server: nginx/1.14.0 (Ubuntu)
        Date: Mon, 18 Feb 2019 09:46:27 GMT
        Content-Type: application/json
        Content-Length: 2018
        Connection: keep-alive
        Cache-Control: no-cache

        {
            "cert": "-----BEGIN CERTIFICATE-----\nMIIDpzCCAo+gAwIBAgIBQTANBgkqhkiG9w0BAQsFADBoMQswCQYDVQQGEwJGUjEM\nMAoGA1UECAwDSURGMQwwCgYDVQQHDANJTE0xDDAKBgNVBAoMA1NGUjELMAkGA1UE\nCwwCTVcxIjAgBgNVBAMMGVNUQiBDZXJ0aWZpY2F0ZSBBdXRob3JpdHkwHhcNMTkw\nMjE0MTIzOTM1WhcNMjAwMjE0MTIzOTM1WjBJMQswCQYDVQQGEwJGUjEMMAoGA1UE\nCAwDSURGMQwwCgYDVQQKDANTRlIxCzAJBgNVBAsMAk1XMREwDwYDVQQDDAhURVNU\nXzEwNDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANtnX5TgcivzRC9x\n33y89Y6gBa13jcFy7obz+76Y0SUUklPx6x1UXg4J80FIPPorPL8FeH1yjaMlALbJ\n47vGD0sQSla96zFbMPs6OGQqnp3ETqEB741mDh7DOLZaUzl7DLw2ZN1a0iI+WksY\nvsO1tch9yywk5FUEQ/BljWCl8FrNb+t4vWs+kpA2c2+5GCbZcWk0loUsrtVlQtbS\n1XNaiGv6WQfy3Cy0qQCBtdrZdNRx+WPjXvtRZzKFB4FQ1aL4gbhBbP7UR8X31AtJ\nbRyxG2aR7DqqIQ5FTymyNIdZ0D5QpdYQG7Z2N1DNT9oWPun6USDkn/+XuX9IdeLb\nRJb3HscCAwEAAaN7MHkwCQYDVR0TBAIwADAsBglghkgBhvhCAQ0EHxYdT3BlblNT\nTCBHZW5lcmF0ZWQgQ2VydGlmaWNhdGUwHQYDVR0OBBYEFH9eXKUJuBdQ6rkXdFH+\nTJjkPqT7MB8GA1UdIwQYMBaAFCNXvrum6h4EKLdg0hlPZO2+C4zGMA0GCSqGSIb3\nDQEBCwUAA4IBAQAYK7BqMBenxkmfD+QgbekrCY2iWfkNqr+cEpblipvZ18uwJPmJ\nfZbxmueyuJ/0JYBJWsl4Rm8Q9OLHhx0ROoyvV5r8qZT4W0b8K3sNlUF04+noXeOe\npkp28YuQfjZQ/ikMUN5XlLDMPA+HZrQxcai4g4QFpJCUBbLl1ULU3EpxwLdF+Ai3\ncvul1R23A04gq69AGSqCkhsygzUi1HXdz5BNPAdL8gVfJzKRsYhc2v3KJ+Bot1//\n/ga5Z/sJwQIGz+m+LdSNXqIhMp0cRUDmMghLyOlWOVyjHBeWXyx1X9UfldxKE3Va\nY5/FPTR2zqmWFm3qS5Je/8akawZmT9H+dMAP\n-----END CERTIFICATE-----\n",
            "serial": "CRT00011E30",
            "signature": "1055021649687109905468699150589108284476743436498998736311052628038826668663181100796005981648464995262003179377231129939681564095275131015690752333812651335238597068569483954328692585380670376764836824652115323713743097231619740244159427553577016223041402114420419098182750971130349215831593670893285198783102744889920126569669344581311934112840548128283666880105473866952702040855306456277991742700909602494211970271672533550462037164487881192029662298668763737170600056539842311062573693906054927626036803833022029384629000268895265996376377754924829431670633606625702952056981956222713453527752827764551716100406"}


        Example of bad response in case of no certificate exist :
        HTTP/1.1 400 BAD REQUEST
        Server: nginx/1.14.0 (Ubuntu)
        Date: Mon, 18 Feb 2019 10:22:50 GMT
        Content-Type: application/json
        Content-Length: 838
        Connection: keep-alive
        Cache-Control: no-cache

        {
            "jsonrpc": "2.0",
            "signature": "10370642976798687514501722542046926389563344535844981738705515955010866662602201624114840847736077669093453502248219609955846409681970149835233924252528152475296743426353539640211200444136692890529722552233121662509759201996034944809731146446904302463012171496304016316125223700900452878734674355821261642108994878161782582225346929166947602896991104114384451893346327128375373734404409705905742268902008839245778679776684023427241802325766307518935368128533279224310482750043978328675448761730445421979374600578874489083523658883077151910559392352183554445977855127578457520490691082149229697038665876086185739725548",
            "detail": null,
            "version": "privacyIDEA 2.23.3",
            "result": {
                "status": false,
                "error": {
                    "message": "ERR601: No certificate available !",
                    "code": 601}
                },
                "time": 1550485370.55361,
                "id": 1
        }
        :param request: The Flask request
        :param g: The Flask global object g
        :return: Flask Response or text
        """
        params = request.all_data
        user = getParam(params, "user", required)
        domaine = getParam(params, "realm", required)
        user_object = User(login=user, realm=domaine, resolver="")

        tokens = get_tokens(tokentype="certificate", assigned=True, user=user_object, active=True, count=False, revoked=False, locked=False)
        if not tokens:
            log.info("No certificate for this user.")
            raise NoCertificateAvailableError()
        else:
            log.info("{0!s} certificate tokens found.".format(len(tokens)))

        res = {
                    "serial": tokens[len(tokens)-1].get_as_dict()["serial"],
                    "cert": tokens[len(tokens)-1].get_as_dict()["info"]["certificate"]
                }

        return "json", res
