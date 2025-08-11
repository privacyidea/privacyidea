# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
#
#  Aug 12, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2020-10-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add attestation certificate functionality
#  2016-04-26 Cornelius Kölbel <cornelius@privacyidea.org>
#             Add the possibility to create key pair on server side
#             Provide download for pkcs12 file
#
#  2015-05-15 Adapt during migration to flask
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
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
import pathlib
from cryptography import x509
from cryptography.x509 import (load_pem_x509_certificate, load_pem_x509_csr,
                               Certificate)
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs12, BestAvailableEncryption
from cryptography.exceptions import InvalidSignature
import secrets
import traceback

from privacyidea.lib.utils import b64encode_and_unicode, to_byte_string
from privacyidea.lib.tokenclass import TokenClass, ROLLOUTSTATE
from privacyidea.lib.log import log_with
from privacyidea.api.lib.utils import getParam, get_optional
from privacyidea.lib.caconnector import get_caconnector_object, get_caconnector_list
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.utils import determine_logged_in_userparams
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib import _
from privacyidea.lib.policy import SCOPE, GROUP, Match
from privacyidea.lib.policies.actions import PolicyAction as BASE_ACTION
from privacyidea.lib.error import privacyIDEAError, CSRError, CSRPending, CAError

optional = True
required = False

log = logging.getLogger(__name__)


DEFAULT_CA_PATH = ["/etc/privacyidea/trusted_attestation_ca"]
# This is the key of the tokeninfo, where the request Id of a pending certificate is stored
REQUEST_ID = "requestId"


class ACTION(BASE_ACTION):
    __doc__ = """This is the list of special certificate actions."""
    TRUSTED_CA_PATH = "certificate_trusted_Attestation_CA_path"
    REQUIRE_ATTESTATION = "certificate_require_attestation"
    CA_CONNECTOR = "certificate_ca_connector"
    CERTIFICATE_TEMPLATE = "certificate_template"
    CERTIFICATE_REQUEST_SUBJECT_COMPONENT = "certificate_request_subject_component"


class REQUIRE_ACTIONS(object):
    IGNORE = "ignore"
    VERIFY = "verify"
    REQUIRE_AND_VERIFY = "require_and_verify"


def verify_certificate_path(certificate: Certificate, trusted_ca_paths: list):
    """
    Verify a certificate against the list of directories each containing files with
    a certificate chain.

    :param certificate: The certificate to verify
    :type certificate: cryptography.x509.Certificate
    :param trusted_ca_paths: A list of directories
    :type trusted_ca_paths: list
    :return: True if the certificate can be verified against the ca chains
    :rtype: bool
    """

    for capath in trusted_ca_paths:
        p = pathlib.Path(capath)
        if p.is_dir():
            chainfiles = [f for f in p.iterdir() if f.is_file()]
            for chainfile in chainfiles:
                chain = parse_chainfile(chainfile)
                try:
                    verify_certificate(certificate, chain)
                    return True
                except InvalidSignature:
                    log.info(f"Can not verify attestation certificate against chain in {chainfile}")
        else:
            log.warning(f"The configured attestation CA directory {p} does not exist.")
    return False


def parse_chainfile(chainfile):
    """
    Parse a text file, that contains a list of CA files.
    The topmost being the trusted Root CA followed by intermediate

    :param chainfile: The filename to parse
    :return: A list of PEM certificates
    """
    cacerts = []
    cacert = ""
    with open(chainfile) as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith("-----BEGIN CERTIFICATE-----"):
            cacert = line
        elif line.startswith("-----END CERTIFICATE-----"):
            cacert += line
            # End of certificate
            cacerts.append(cacert)
        elif line.startswith("#") or line == "":
            # Empty line or comment
            pass
        else:
            cacert += line
    return cacerts


def verify_certificate(certificate: Certificate, chain: list):
    """
    Verify a certificate against the certificate chain, which can be of any length

    The certificate chain starts with the root certificate and contains further
    intermediate certificates

    :param certificate: The certificate in PEM encoded format
    :type certificate: cryptography.x509.Certificate
    :param chain: A list of PEM encoded certificates
    :type chain: list
    :return: raises an exception
    """
    if not chain:
        raise privacyIDEAError("Can not verify certificate against an empty chain.")  # pragma: no cover
    # first reverse the list, since it can be popped better
    chain = list(reversed(chain))
    chain = [load_pem_x509_certificate(c.encode()) for c in chain]
    # verify chain
    signer = chain.pop()
    while chain:
        # There is another element in the list, so we check the intermediate:
        signee = chain.pop()
        signer.public_key().verify(
            signee.signature,
            signee.tbs_certificate_bytes,
            padding.PKCS1v15(),
            signee.signature_hash_algorithm
        )
        signer = signee

    # This was the last certificate in the chain, so we check the certificate
    signer.public_key().verify(
        certificate.signature,
        certificate.tbs_certificate_bytes,
        padding.PKCS1v15(),
        certificate.signature_hash_algorithm
    )


class CertificateTokenClass(TokenClass):
    """
    Token to implement an X509 certificate.
    The certificate can be enrolled by sending a CSR to the server or the
    keypair is created by the server. If the server creates the keypair,
    the user can download an encrypted PKCS12 container file.
    The OTP PIN is used as passphrase for the PKCS12 file. If no PIN is set for
    the token, a random password will be generated and returned in the init
    details.

    privacyIDEA is capable of working with different CA connectors.

    Valid parameters are ``request`` or ``certificate``, both PEM encoded.
    If you pass a ``request`` or ``genkey=1`` you also need to pass the ``ca``
    that should be used to sign the request. Passing a ``certificate`` just
    uploads the certificate to a new token object.

    A certificate token can be created by an administrative task with the
    :http:post:`/token/init` api like this:

      **Example Initialization Request**:

        .. sourcecode:: http

           POST /token/init HTTP/1.1
           Host: example.com
           Accept: application/json

           type=certificate
           user=cornelius
           realm=realm1
           request=<PEM encoded certificate request>
           attestation=<PEM encoded attestation certificate>
           ca=<name of the ca connector>

      **Example Initialization Request, key generation on servers side**

      In this case the certificate is created on behalf of another user.

        .. sourcecode:: http

           POST /token/init HTTP/1.1
           Host: example.com
           Accept: application/json

           type=certificate
           user=cornelius
           realm=realm1
           genkey=1
           ca=<name of the ca connector>

      **Example response**:

           .. sourcecode:: http

               HTTP/1.1 200 OK
               Content-Type: application/json

               {
                 "detail": {
                   "certificate": "...PEM...",
                   "serial": "CRT...."
                 },
                 "id": 1,
                 "jsonrpc": "2.0",
                 "result": {
                   "status": true,
                   "value": true
                 },
               }

    """
    using_pin = False
    hKeyRequired = False

    def __init__(self, aToken):
        TokenClass.__init__(self, aToken)
        self.set_type("certificate")
        self.otp_len = 0
        try:
            self._update_rollout_state()
        except Exception as e:
            log.warning("Failed to check for pending update. {0!s}".format(e))

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
               'policy': {
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of certificates assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of active certificates assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.REQUIRE_ATTESTATION: {
                           'type': 'str',
                           'desc': _("Enrolling a certificate token can require an attestation certificate. "
                                     "(Default: ignore)"),
                           'group': GROUP.TOKEN,
                           'value': [REQUIRE_ACTIONS.IGNORE,
                                     REQUIRE_ACTIONS.VERIFY,
                                     REQUIRE_ACTIONS.REQUIRE_AND_VERIFY]
                       },
                       ACTION.CA_CONNECTOR: {
                           'type': 'str',
                           'desc': _("The CA connector that should be used during certificate enrollment."),
                           'group': GROUP.TOKEN,
                           'value': [x.get("connectorname") for x in get_caconnector_list()]
                       },
                       ACTION.CERTIFICATE_TEMPLATE: {
                           'type': 'str',
                           'desc': _("The template that should be used to issue a certificate."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.CERTIFICATE_REQUEST_SUBJECT_COMPONENT: {
                           'type': 'str',
                           'desc': _("This takes a space separated list of elements to be added to the subject. "
                                     "Can be 'email' and 'realm'."),
                           'group': GROUP.TOKEN
                       }
                   },
                   SCOPE.USER: {
                       ACTION.TRUSTED_CA_PATH: {
                           'type': 'str',
                           'desc': _("The directory containing attestation certificate chains."),
                           'group': GROUP.TOKEN
                       }
                   },
                   SCOPE.ADMIN: {
                       ACTION.TRUSTED_CA_PATH: {
                           'type': 'str',
                           'desc': _("The directory containing attestation certificate chains."),
                           'group': GROUP.TOKEN
                       }
                   }
               }
               }
        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res
        return ret

    @classmethod
    def get_default_settings(cls, g, params):
        """
        This method returns a dictionary with additional settings for token
        enrollment.
        The settings that are evaluated are
        SCOPE.ADMIN|SCOPE.USER, action=trusted_Assertion_CA_path
        It sets a list of configured paths.

        The returned dictionary is added to the parameters of the API call.
        :param g: context object, see documentation of ``Match``
        :param params: The call parameters
        :type params: dict
        :return: default parameters
        """
        ret = {ACTION.TRUSTED_CA_PATH: DEFAULT_CA_PATH}
        (role, username, userrealm, adminuser, adminrealm) = determine_logged_in_userparams(g.logged_in_user,
                                                                                            params)
        # Now we fetch CA-pathes from the policies
        paths = Match.generic(g, scope=role,
                              action=ACTION.TRUSTED_CA_PATH,
                              user=username,
                              realm=userrealm,
                              adminuser=adminuser,
                              adminrealm=adminrealm).action_values(unique=False,
                                                                   allow_white_space_in_action=True)
        if paths:
            ret[ACTION.TRUSTED_CA_PATH] = list(paths)

        return ret

    def _update_rollout_state(self):
        """
        This is a certificate specific method, that communicates to the CA and checks,
        if a pending certificate has been enrolled, yet.
        If the certificate is enrolled, it fetches the certificate from the CA and
        updates the certificate token.

        A return code of -1 means that the status is unchanged.

        :return: the status of the rollout
        """
        status = -1
        if self.rollout_state == ROLLOUTSTATE.PENDING:
            request_id = self.get_tokeninfo(REQUEST_ID)
            ca = self.get_tokeninfo("CA")
            if ca and request_id:
                request_id = int(request_id)
                cacon = get_caconnector_object(ca)
                status = cacon.get_cr_status(request_id)
                # TODO: Later we need to make the status CA dependent. Different CAs could return
                #  different codes. So each CA Connector needs a mapper for its specific codes.
                if status in [3, 4]:  # issued or "issued out of band"
                    log.info("The certificate {0!s} has been issued by the CA.".format(self.token.serial))
                    certificate = cacon.get_issued_certificate(request_id)
                    # Update the rollout state
                    self.token.rollout_state = ROLLOUTSTATE.ENROLLED
                    self.add_tokeninfo("certificate", certificate)
                elif status == 2:  # denied
                    log.warning("The certificate {0!s} has been denied by the CA.".format(self.token.serial))
                    self.token.rollout_state = ROLLOUTSTATE.DENIED
                    self.token.save()
                else:
                    log.info("The certificate {0!s} is still pending.".format(self.token.serial))
            else:
                log.warning("The certificate token in rollout_state pending, but either the CA ({0!s}) "
                            "or the requestId ({1!s}) is missing.".format(ca, request_id))
        return status

    def update(self, param):
        """
        This method is called during the initialization process.

        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        # Remove genkey and otpkey from params to avoid generating an otpkey
        token_params = {k:v for k, v in param.items() if k not in ["genkey", "otpkey"]}
        TokenClass.update(self, token_params)

        request = get_optional(param, "request")
        spkac = get_optional(param, "spkac")
        certificate = get_optional(param, "certificate")
        generate = get_optional(param, "genkey")
        template_name = get_optional(param, "template")
        subject_components = get_optional(param, "subject_components", default=[])

        if "pin" in param:
            self.set_pin(param.get("pin"))

        request_id = None
        ca_connector = None
        if request or generate:
            # If we do not upload a user certificate, then we need a CA do
            # sign the uploaded request or generated certificate.
            ca = getParam(param, "ca", required)
            self.add_tokeninfo("CA", ca)
            ca_connector = get_caconnector_object(ca)
        if request:
            if not spkac:
                # We only do the whole attestation checking in case we have no SPKAC
                request = request.replace("\n", "")
                if not request.startswith("-----BEGIN CERTIFICATE REQUEST-----"):
                    request = "-----BEGIN CERTIFICATE REQUEST-----" + request
                if not request.endswith("-----END CERTIFICATE REQUEST-----"):
                    request = request + "-----END CERTIFICATE REQUEST-----"
                request_csr = load_pem_x509_csr(to_byte_string(request))
                # Restore the request string with newlines
                request = request_csr.public_bytes(encoding=serialization.Encoding.PEM).decode('utf-8')
                if not request_csr.is_signature_valid:
                    raise privacyIDEAError("request has invalid signature.")
                # If a request is sent, we can have an attestation certificate
                attestation = getParam(param, "attestation", optional)
                verify_attestation = getParam(param, "verify_attestation", optional)
                if attestation:
                    request_numbers = request_csr.public_key().public_numbers()
                    attestation_cert = load_pem_x509_certificate(to_byte_string(attestation))
                    attestation_numbers = attestation_cert.public_key().public_numbers()
                    if request_numbers != attestation_numbers:
                        log.warning("certificate request does not match attestation certificate.")
                        raise privacyIDEAError("certificate request does not match attestation certificate.")

                    try:
                        verified = verify_certificate_path(attestation_cert,
                                                           param.get(ACTION.TRUSTED_CA_PATH))
                    except Exception as e:
                        # We could have file system errors during verification.
                        log.debug(f"An error occurred while verifying the certificate path: {e}")
                        log.debug("{0!s}".format(traceback.format_exc()))
                        verified = False

                    if not verified:
                        log.warning("Failed to verify certificate chain of attestation certificate.")
                        if verify_attestation:
                            raise privacyIDEAError("Failed to verify certificate chain of attestation certificate.")

            # During the initialization process, we need to create the certificate
            # TODO: We should check for a pending CSR from the MSCA connector
            request_id, certificate = ca_connector.sign_request(request,
                                                                options={"spkac": spkac,
                                                                         "template": template_name})
        elif generate:
            """
            Create the certificate on behalf of another user. Now we need to create
            * the key pair,
            * the request
            * and the certificate
            We need the user for whom the certificate should be created
            """
            user = get_user_from_param(param, optionalOrRequired=required)
            keysize = get_optional(param, "keysize", 2048)
            # The key size should be at least 2048
            if keysize < 2048:
                log.info("Adjusting Key size to 2048 bits for improved security.")
                keysize = 2048
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=keysize)
            # Provide various details about who we are.
            subject_name = [x509.NameAttribute(x509.NameOID.COMMON_NAME, user.login)]
            if subject_components:
                # TODO: Add Country, Organization. Maybe from templates?
                """
                req.get_subject().countryName = 'xxx'
                req.get_subject().stateOrProvinceName = 'xxx'
                req.get_subject().localityName = 'xxx'
                req.get_subject().organizationName = 'xxx'
                """
                if "email" in subject_components and user.info.get("email"):
                    subject_name.append(
                        x509.NameAttribute(x509.NameOID.EMAIL_ADDRESS, user.info.get("email"))
                    )
                if "realm" in subject_components:
                    subject_name.append(
                        x509.NameAttribute(x509.NameOID.ORGANIZATIONAL_UNIT_NAME, user.realm)
                    )
            req = x509.CertificateSigningRequestBuilder().subject_name(x509.Name(subject_name))
            # Sign the CSR with our private key.
            req = req.sign(key, hashes.SHA256())

            csr = req.public_bytes(serialization.Encoding.PEM).decode()
            key_pem = key.private_bytes(serialization.Encoding.PEM,
                                        serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption()).decode()

            try:
                request_id, certificate = ca_connector.sign_request(
                    csr,
                    options={"template": template_name})

            except CSRPending as e:
                self.token.rollout_state = ROLLOUTSTATE.PENDING
                if hasattr(e, "requestId"):
                    request_id = e.requestId
            except (CSRError, CAError):
                # Mark the token as broken
                self.token.rollout_state = ROLLOUTSTATE.FAILED
                # Reraise the error
                raise

            # We create the pkcs12 container here and save it in the token info
            # and add it to the init details. If the rollout state is pending, there
            # will be no certificate in the container, just the private key.
            pkcs12_password, pkcs12_container = self._create_pkcs12_bin(certificate, key_pem)
            pkcs12_container_encoded = b64encode_and_unicode(pkcs12_container)
            self.add_tokeninfo("pkcs12", pkcs12_container_encoded)
            self.add_init_details("pkcs12", pkcs12_container_encoded)
            if pkcs12_password:
                self.add_init_details("pkcs12_password", pkcs12_password)

        if certificate:
            self.add_tokeninfo("certificate", certificate)

        if request_id:
            self.add_tokeninfo(REQUEST_ID, request_id)

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we return the certificate and the
        PKCS12 file, if the private key exists.
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        certificate = self.get_tokeninfo("certificate")
        response_detail["certificate"] = certificate
        response_detail["rollout_state"] = self.token.rollout_state
        # Remove the "otpkey" from the response, it is unused for certificate tokens
        if "otpkey" in response_detail:
            del response_detail["otpkey"]
        return response_detail

    def _create_pkcs12_bin(self, certificate: str = None, privatekey: str = None) -> tuple[str, bytes]:
        """
        Helper function to create an encrypted pkcs12 binary for download

        :return: PKCS12 binary
        """
        if not certificate:
            certificate = self.get_tokeninfo("certificate")
        if not privatekey:
            privatekey = self.get_tokeninfo("privatekey")

        cert = None
        if certificate:
            cert = load_pem_x509_certificate(certificate.encode())
        key = serialization.load_pem_private_key(privatekey.encode(), None)
        # Get the token PIN. If it exists we use it as the password for the
        # encrypted pkcs12 container. Otherwise, we create a random password.
        token_pin = self.token.get_pin()
        if token_pin == -1:
            passphrase = secrets.token_urlsafe(12)
        else:
            passphrase = token_pin
        # See https://cryptography.io/en/latest/hazmat/primitives/asymmetric/serialization/#cryptography.hazmat.primitives.serialization.pkcs12.serialize_key_and_certificates
        # for more details on PKCS12 export
        p12 = pkcs12.serialize_key_and_certificates(
            b"certificatetoken", key, cert, None,
            BestAvailableEncryption(passphrase.encode()))
        # If we used the token PIN to encrypt the pkcs12 container, we do not
        # return it to the caller
        if token_pin != -1:
            passphrase = None
        return passphrase, p12

    def get_as_dict(self) -> dict:
        """
        This returns the token data as a dictionary.
        It is used to display the token list at /token/list.

        The certificate token can add the PKCS12 file if it exists

        :return: The token data as dictionary
        :rtype: dict
        """
        # first get the database values as dict
        token_dict = self.token.get()

        if "pkcs12_password" in token_dict["info"]:
            # We need to use the get_tokeninfo function to decrypt the password
            token_dict["info"]["pkcs12_password"] = self.get_tokeninfo("pkcs12_password")

        # Remove the private key from the response
        if "privatekey" in token_dict["info"]:
            del token_dict["info"]["privatekey"]

        return token_dict

    @check_token_locked
    def set_pin(self, pin, encrypt=False):
        """
        set the PIN of a token.
        The PIN of the certificate token is stored encrypted. It is used as
        passphrase for the PKCS12 file.

        :param pin: the pin to be set for the token
        :type pin: str
        :param encrypt: ignored
        :type encrypt: bool
        """
        store_hashed = False
        self.token.set_pin(pin, store_hashed)

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
        revoked = ca_obj.revoke_cert(certificate_pem,
                                     request_id=ti.get(REQUEST_ID))
        log.info("Certificate {0!s} revoked on CA {1!s}.".format(revoked,
                                                                 ca_specifier))

        # call CAConnector.create_crl()
        crl = ca_obj.create_crl()
        log.info("CRL {0!s} created.".format(crl))

        return revoked
