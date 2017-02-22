# -*- coding: utf-8 -*-
#
#  2015-04-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#
# License:  AGPLv3
# (c) 2015. Cornelius Kölbel
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
#
__doc__ = """This module contains the connectors to Certificate Authorities.
In this first implementation it is only a local certificate authority.

This module is tested in tests/test_lib_caconnector.py
"""
from privacyidea.lib.error import CAError
from privacyidea.lib.utils import int_to_hex
from privacyidea.lib.caconnectors.baseca import BaseCAConnector
from OpenSSL import crypto
from subprocess import Popen, PIPE
import shlex
import re

CA_SIGN = "openssl ca -keyfile {cakey} -cert {cacert} -config {config} " \
          "-extensions {extension} -days {days} -in {csrfile} -out {" \
          "certificate} -batch"
CA_SIGN_SPKAC = "openssl ca -keyfile {cakey} -cert {cacert} -config {config} "\
                "-extensions {extension} -days {days} -spkac {spkacfile} -out " \
                "{certificate} -batch"

CA_REVOKE = "openssl ca -keyfile {cakey} -cert {cacert} -config {config} "\
            "-revoke {certificate} -crl_reason {reason}"

CA_GENERATE_CRL = "openssl ca -keyfile {cakey} -cert {cacert} -config " \
                  "{config} -gencrl -out {CRL}"


CRL_REASONS = ["unspecified", "keyCompromise", "CACompromise",
               "affiliationChanged", "superseded", "cessationOfOperation"]


class ATTR(object):
    __doc__ = """This is the list Attributes of the Local CA."""
    CAKEY = "cakey"
    CACERT = "cacert"
    OPENSSL_CNF = "openssl.cnf"
    WORKING_DIR = "WorkingDir"
    CSR_DIR = "CSRDir"
    CERT_DIR = "CertificateDir"
    CRL = "CRL"
    CRL_VALIDITY_PERIOD = "CRL_Validity_Period"
    CRL_OVERLAP_PERIOD = "CRL_Overlap_Period"


class LocalCAConnector(BaseCAConnector):
    """
    This connector connects to a local CA represented by a CA certificate and
    key in the local file system.
    OpenSSL is used.
    """

    connector_type = "local"

    def __init__(self, name, config=None):
        """
        Required attributes are:
         * cakey - the private key of the CA
         * cacert - the certificate of the CA
        Optional Attributes are:
         * List of CDPs
         * List of templates
         * Key directory
         * Default key size
         * ...
        :param config: A dictionary with all necessary attributes.
        :return:
        """
        self.name = name
        if config:
            self.set_config(config)

    @classmethod
    def get_caconnector_description(cls):
        """
        Return the description of this CA connectors.
        This contains the name as a key and the possible parameters.

        :return: resolver description dict
        :rtype:  dict
        """
        typ = cls.connector_type
        config = {ATTR.CAKEY: 'string',
                  ATTR.CACERT: 'string',
                  ATTR.OPENSSL_CNF: 'string',
                  ATTR.WORKING_DIR: 'string',
                  ATTR.CSR_DIR: 'string',
                  ATTR.CERT_DIR: 'string',
                  ATTR.CRL: 'string',
                  ATTR.CRL_OVERLAP_PERIOD: 'int',
                  ATTR.CRL_VALIDITY_PERIOD: 'int'}
        return {typ: config}

    def _check_attributes(self):
        for req_key in [ATTR.CAKEY, ATTR.CACERT]:
            if req_key not in self.config:
                raise CAError("required argument '{0!s}' is missing.".format(
                    req_key))

    def set_config(self, config=None):
        self.config = config or {}
        self._check_attributes()
        # The CAKEY and the CACERT are passed as filenames
        self.cakey = self.config.get(ATTR.CAKEY)
        self.cacert = self.config.get(ATTR.CACERT)

    @staticmethod
    def _filename_from_x509(x509_name, file_extension="pem"):
        """
        return a filename from the subject from an x509 object
        :param x509_name: The X509Name object
        :type x509_name: X509Name object
        :return: filename
        :rtype: basestring
        """
        name_components = x509_name.get_components()
        filename = ""
        for (key, value) in name_components:
            filename += value+"_"
        filename = filename[:-1] + "." + file_extension
        return filename

    def sign_request(self, csr, options=None):
        """
        Signs a certificate request with the key of the CA.

        options can be
        WorkingDir: The directory where the configuration like openssl.cnf
        can be found.
        CSRDir: The directory, where to save the certificate signing
        requests. This is relative to the WorkingDir.
        CertificateDir: The directory where to save the certificates. This is
        relative to the WorkingDir.

        :param csr: Certificate signing request
        :type csr: PEM string or SPKAC
        :param options: Additional options like the validity time or the
            template or spkac=1
        :type options: dict
        :return: Returns the certificate
        :rtype: basestring
        """
        # Sign the certificate for one year
        options = options or {}
        days = options.get("days", 365)
        spkac = options.get("spkac")
        config = options.get(ATTR.OPENSSL_CNF,
                             self.config.get(
                                 ATTR.OPENSSL_CNF, "/etc/ssl/openssl.cnf"))
        extension = options.get("extension", "server")
        workingdir = options.get(ATTR.WORKING_DIR,
                                 self.config.get(ATTR.WORKING_DIR))
        csrdir = options.get(ATTR.CSR_DIR,
                             self.config.get(ATTR.CSR_DIR, ""))
        certificatedir = options.get(ATTR.CERT_DIR,
                                     self.config.get(ATTR.CERT_DIR, ""))
        if workingdir:
            if not csrdir.startswith("/"):
                # No absolut path
                csrdir = workingdir + "/" + csrdir
            if not certificatedir.startswith("/"):
                certificatedir = workingdir + "/" + certificatedir

        # Determine filename from the CN of the request
        if spkac:
            common_name = re.search("CN=(.*)", csr).group(0).split('=')[1]
            csr_filename = common_name + ".txt"
            certificate_filename = common_name + ".der"
        else:
            csr_obj = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr)
            csr_filename = self._filename_from_x509(csr_obj.get_subject(),
                                                    file_extension="req")
            certificate_filename = self._filename_from_x509(
                csr_obj.get_subject(), file_extension="pem")
            #csr_extensions = csr_obj.get_extensions()
        csr_filename = csr_filename.replace(" ", "_")
        certificate_filename = certificate_filename.replace(" ", "_")
        # dump the file
        with open(csrdir + "/" + csr_filename, "w") as f:
            f.write(csr)

        if spkac:
            cmd = CA_SIGN_SPKAC.format(cakey=self.cakey, cacert=self.cacert,
                                       days=days, config=config,
                                       extension=extension,
                                       spkacfile=csrdir + "/" + csr_filename,
                                       certificate=certificatedir + "/" +
                                                   certificate_filename)
        else:
            cmd = CA_SIGN.format(cakey=self.cakey, cacert=self.cacert,
                                 days=days, config=config, extension=extension,
                                 csrfile=csrdir + "/" + csr_filename,
                                 certificate=certificatedir + "/" +
                                             certificate_filename)
        # run the command
        args = shlex.split(cmd)
        p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=workingdir)
        result, error = p.communicate()
        if p.returncode != 0:  # pragma: no cover
            # Some error occurred
            raise CAError(error)

        with open(certificatedir + "/" + certificate_filename, "r") as f:
            certificate = f.read()

        # We return the cert_obj.
        if spkac:
            filetype = crypto.FILETYPE_ASN1
        else:
            filetype = crypto.FILETYPE_PEM
        cert_obj = crypto.load_certificate(filetype, certificate)
        return cert_obj

    def view_pending_certs(self):
        """
        CA Manager approval
        the token/init of would not create a certificate but a
        pending certificate request, that needs to be approved by a
        CA manager. So we need some kind of approve method.
        :return:
        """
        pass

    def request_cert(self):
        """
        create key server side
        create key on client side
        via PKCS10
        :return:
        """
        pass

    def get_templates(self):
        """
        Return a list of available certificate templates
        :return:
        """
        pass

    def publish_cert(self):
        """
        The certificate might get published somewhere
        """
        pass

    def revoke_cert(self, certificate, reason=CRL_REASONS[0]):
        """
        Revoke the specified certificate. At this point only the database
        index.txt is updated.

        :param certificate: The certificate to revoke
        :type certificate: Either takes X509 object or a PEM encoded
            certificate (string)
        :param reason: One of the available reasons the certificate gets revoked
        :type reason: basestring
        :return: Returns the serial number of the revoked certificate. Otherwise
            an error is raised.
        """
        if type(certificate) in [basestring, unicode, str]:
            cert_obj = crypto.load_certificate(crypto.FILETYPE_PEM, certificate)
        elif type(certificate) == crypto.X509:
            cert_obj = certificate
        else:
            raise CAError("Certificate in unsupported format")
        serial = cert_obj.get_serial_number()
        serial_hex = int_to_hex(serial)
        filename = serial_hex + ".pem"

        cmd = CA_REVOKE.format(cakey=self.cakey, cacert=self.cacert,
                               config=self.config.get(ATTR.OPENSSL_CNF),
                               certificate=filename,
                               reason=reason)
        workingdir = self.config.get(ATTR.WORKING_DIR)
        args = shlex.split(cmd)
        p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=workingdir)
        result, error = p.communicate()
        if p.returncode != 0:  # pragma: no cover
            # Some error occurred
            raise CAError(error)

        return serial_hex

    def create_crl(self, publish=True):
        """
        Create and Publish the CRL.

        :param publish: Whether the CRL should be published at its CDPs
        :return: the CRL location
        """
        crl = self.config.get(ATTR.CRL, "crl.pem")
        cmd = CA_GENERATE_CRL.format(cakey=self.cakey, cacert=self.cacert,
                                     config=self.config.get(ATTR.OPENSSL_CNF),
                                     CRL=crl)
        workingdir = self.config.get(ATTR.WORKING_DIR)
        args = shlex.split(cmd)
        p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=workingdir)
        result, error = p.communicate()
        if p.returncode != 0:  # pragma: no cover
            # Some error occurred
            raise CAError(error)

        return crl
