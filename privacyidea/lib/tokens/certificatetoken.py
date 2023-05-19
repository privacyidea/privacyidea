# -*- coding: utf-8 -*-
#
#  privacyIDEA
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

from privacyidea.lib.utils import to_unicode, b64encode_and_unicode, to_byte_string
from privacyidea.lib.tokenclass import TokenClass, ROLLOUTSTATE
from privacyidea.lib.log import log_with
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.caconnector import get_caconnector_object, get_caconnector_list
from privacyidea.lib.user import get_user_from_param
from privacyidea.lib.utils import determine_logged_in_userparams
from OpenSSL import crypto
from cryptography.x509 import load_pem_x509_certificate, load_pem_x509_csr
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib import _
from privacyidea.lib.policy import SCOPE, ACTION as BASE_ACTION, GROUP, Match
from privacyidea.lib.error import privacyIDEAError, CSRError, CSRPending
import traceback

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


def verify_certificate_path(certificate, trusted_ca_paths):
    """
    Verify a certificate against the list of directories each containing files with
    a certificate chain.

    :param certificate: The PEM certificate to verify
    :param trusted_ca_paths: A list of directories
    :return: True or False
    """
    from os import listdir
    from os.path import isfile, join, isdir

    for capath in trusted_ca_paths:
        if isdir(capath):
            chainfiles = [join(capath, f) for f in listdir(capath) if isfile(join(capath, f))]
            for chainfile in chainfiles:
                chain = parse_chainfile(chainfile)
                try:
                    verify_certificate(to_byte_string(certificate), chain)
                    return True
                except Exception as exx:
                    log.debug("Can not verify attestation certificate against chain {0!s}.".format(chain))
        else:
            log.warning("The configured attestation CA directory does not exist.")
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


def verify_certificate(certificate, chain):
    """
    Verify a certificate against the certificate chain, which can be of any length

    The certificate chain starts with the root certificate and contains further
    intermediate certificates

    :param certificate: The certificate
    :type certificate: PEM encoded string
    :param chain: A list of PEM encoded certificates
    :type chain: list
    :return: raises an exception
    """
    # first reverse the list, since it can be popped better
    chain = list(reversed(chain))
    if not chain:
        raise privacyIDEAError("Can not verify certificate against an empty chain.")
    certificate = load_pem_x509_certificate(to_byte_string(certificate), default_backend())
    chain = [load_pem_x509_certificate(to_byte_string(c), default_backend()) for c in chain]
    # verify chain
    while chain:
        signer = chain.pop()
        if chain:
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
           attestation=<PEM encoded attestation certificate>
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
                # different codes. So each CA Connector needs a mapper for its specific codes.
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
        TokenClass.update(self, param)

        request = getParam(param, "request", optional)
        spkac = getParam(param, "spkac", optional)
        certificate = getParam(param, "certificate", optional)
        generate = getParam(param, "genkey", optional)
        template_name = getParam(param, "template", optional)
        subject_components = getParam(param, "subject_components", optional=optional, default=[])
        request_id = None
        if request or generate:
            # If we do not upload a user certificate, then we need a CA do
            # sign the uploaded request or generated certificate.
            ca = getParam(param, "ca", required)
            self.add_tokeninfo("CA", ca)
            cacon = get_caconnector_object(ca)
        if request:
            if not spkac:
                # We only do the whole attestation checking in case we have no SPKAC
                request_csr = load_pem_x509_csr(to_byte_string(request), default_backend())
                if not request_csr.is_signature_valid:
                    raise privacyIDEAError("request has invalid signature.")
                # If a request is sent, we can have an attestation certificate
                attestation = getParam(param, "attestation", optional)
                verify_attestation = getParam(param, "verify_attestation", optional)
                if attestation:
                    request_numbers = request_csr.public_key().public_numbers()
                    attestation_cert = load_pem_x509_certificate(to_byte_string(attestation), default_backend())
                    attestation_numbers = attestation_cert.public_key().public_numbers()
                    if request_numbers != attestation_numbers:
                        log.warning("certificate request does not match attestation certificate.")
                        raise privacyIDEAError("certificate request does not match attestation certificate.")

                    try:
                        verified = verify_certificate_path(attestation,
                                                           param.get(ACTION.TRUSTED_CA_PATH))
                    except Exception as exx:
                        # We could have file system errors during verification.
                        log.debug("{0!s}".format(traceback.format_exc()))
                        verified = False

                    if not verified:
                        log.warning("Failed to verify certificate chain of attestation certificate.")
                        if verify_attestation:
                            raise privacyIDEAError("Failed to verify certificate chain of attestation certificate.")

            # During the initialization process, we need to create the certificate
            request_id, x509object = cacon.sign_request(request,
                                                        options={"spkac": spkac,
                                                                 "template": template_name})
            certificate = crypto.dump_certificate(crypto.FILETYPE_PEM,
                                                  x509object)
        elif generate:
            """
            Create the certificate on behalf of another user. Now we need to create 
            * the key pair,
            * the request
            * and the certificate
            We need the user for whom the certificate should be created
            """
            user = get_user_from_param(param, optionalOrRequired=required)
            keysize = getParam(param, "keysize", optional, 2048)
            key = crypto.PKey()
            key.generate_key(crypto.TYPE_RSA, keysize)
            req = crypto.X509Req()
            req.get_subject().CN = user.login
            # Add components to subject
            if subject_components:
                if "email" in subject_components and user.info.get("email"):
                    req.get_subject().emailAddress = user.info.get("email")
                if "realm" in subject_components:
                    req.get_subject().organizationalUnitName = user.realm
            # TODO: Add Country, Organization
            """
            req.get_subject().countryName = 'xxx'
            req.get_subject().stateOrProvinceName = 'xxx'
            req.get_subject().localityName = 'xxx'
            req.get_subject().organizationName = 'xxx'
            """
            req.set_pubkey(key)
            r = req.sign(key, "sha256")
            csr = to_unicode(crypto.dump_certificate_request(crypto.FILETYPE_PEM, req))
            try:
                request_id, x509object = cacon.sign_request(csr, options={"template": template_name})
                certificate = crypto.dump_certificate(crypto.FILETYPE_PEM, x509object)
            except CSRError:
                # Mark the token as broken
                self.token.rollout_state = ROLLOUTSTATE.FAILED
                # Reraise the error
                raise CSRError()
            except CSRPending as e:
                self.token.rollout_state = ROLLOUTSTATE.PENDING
                if hasattr(e, "requestId"):
                    request_id = e.requestId
            finally:
                # Save the private key to the encrypted key field of the token
                s = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
                self.add_tokeninfo("privatekey", s, value_type="password")

        if "pin" in param:
            self.set_pin(param.get("pin"), encrypt=True)

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
        params = params or {}
        certificate = self.get_tokeninfo("certificate")
        response_detail["certificate"] = certificate
        response_detail["rollout_state"] = self.token.rollout_state
        privatekey = self.get_tokeninfo("privatekey")
        # If there is a private key, we dump a PKCS12
        if privatekey:
            try:
                response_detail["pkcs12"] = b64encode_and_unicode(self._create_pkcs12_bin())
            except Exception:
                log.warning("Can not create PKCS12 for token {0!s}.".format(self.token.serial))

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
            passphrase = ""  # nosec B105 # defaults to empty passphrase
        pkcs12_bin = pkcs12.export(passphrase=passphrase.encode('utf8'))
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
            try:
                token_dict["info"]["pkcs12"] = b64encode_and_unicode(self._create_pkcs12_bin())
            except Exception:
                log.warning("Can not create PKCS12 for token {0!s}.".format(self.token.serial))

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
        revoked = ca_obj.revoke_cert(certificate_pem,
                                     request_id=ti.get(REQUEST_ID))
        log.info("Certificate {0!s} revoked on CA {1!s}.".format(revoked,
                                                                 ca_specifier))

        # call CAConnector.create_crl()
        crl = ca_obj.create_crl()
        log.info("CRL {0!s} created.".format(crl))

        return revoked
