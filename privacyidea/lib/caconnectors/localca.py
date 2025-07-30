#  2017-02-25 Cornelius Kölbeb <cornelius.koelbel@netknights.it>
#             Add template functionality
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
from privacyidea.lib.utils import int_to_hex, to_unicode
from privacyidea.lib.caconnectors.baseca import BaseCAConnector, AvailableCAConnectors
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from subprocess import Popen, PIPE  # nosec B404
import yaml
import datetime
from pathlib import Path
import shlex
from typing import Union
import re
import logging
import os
import traceback

log = logging.getLogger(__name__)

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

OPENSSL_TEMPLATE = """
HOME			= .
RANDFILE		= $ENV::HOME/.rnd
oid_section		= new_oids

[ new_oids ]
# You may add individual OIDs here

[ ca ]
default_ca	= CA_default		# The default ca section

[ CA_default ]
dir		    =  .        		# Where everything is kept
certs		= $dir		    	# Where the issued certs are kept
crl_dir		= $dir		    	# Where the issued crl are kept
database	= $dir/index.txt	# database index file.
new_certs_dir	= $dir			# default place for new certs.

certificate	= $dir/cacert.pem	# The CA certificate
serial		= $dir/serial 		# The current serial number
crl		    = $dir/crl.pem 		# The current CRL
private_key	= $dir/cakey.pem	# The private key
RANDFILE	= $dir/.rand		# private random number file

x509_extensions	= usr_cert		# The extensions to add to the cert

default_days	= {ca_days} 	# how long to certify for
default_crl_days= {crl_days}	# how long before next CRL
default_md	= sha256		    # which md to use.
preserve	= no			    # keep passed DN ordering

policy		= policy_anything

[ policy_anything ]
countryName		= optional
stateOrProvinceName	= optional
localityName		= optional
organizationName	= optional
organizationalUnitName	= optional
commonName		= supplied
emailAddress		= optional

[ req ]
default_bits		= 2048
default_keyfile 	= privkey.pem
distinguished_name	= req_distinguished_name
attributes		= req_attributes
x509_extensions	= v3_ca	# The extensions to add to the self signed cert
string_mask = nombstr


[ req_distinguished_name ]
countryName			= Country Name (2 letter code)
countryName_min	    = 2
countryName_max		= 2

stateOrProvinceName		= State or Province Name (full name)
localityName			= Locality Name (eg, city)
0.organizationName		= Organization Name (eg, company)
organizationalUnitName	= Organizational Unit Name (eg, section)
commonName			    = Common Name (eg, your name or your server\'s hostname)
commonName_max			= 64

emailAddress			= Email Address
emailAddress_max		= 40

[ req_attributes ]
challengePassword		= A challenge password
challengePassword_min		= 4
challengePassword_max		= 20
unstructuredName		= An optional company name

[ usr_cert ]
basicConstraints=CA:FALSE
nsComment			= "OpenSSL Generated Certificate"
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer:always
crlDistributionPoints = @crl_dp_policy
#authorityInfoAccess = caIssuers;URI:http://www.example.com/yourCA.crt

[ server ]
keyUsage = digitalSignature, keyEncipherment
basicConstraints=CA:FALSE
nsCertType			= server
nsComment			= "OpenSSL Generated Server Certificate"
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer:always
extendedKeyUsage=serverAuth

[ etoken ]
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
basicConstraints=CA:FALSE
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer:always
cirlDistributionPoints = @crl_dp_policy
#authorityInfoAccess = caIssuers;URI:http://www.example.com/yourCA.crt

[ ocsp ]
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = OCSPSigning
basicConstraints=CA:FALSE
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer:always
crlDistributionPoints = @crl_dp_policy
#authorityInfoAccess = caIssuers;URI:http://www.example.com/yourCA.crt

[ user ]
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
basicConstraints = CA:FALSE
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer:always
crlDistributionPoints = @crl_dp_policy
authorityInfoAccess = caIssuers;URI:http://www.example.com/yourCA.crt

[ v3_ca ]
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always,issuer:always
basicConstraints = CA:true

[ crl_ext ]
authorityKeyIdentifier=keyid:always,issuer:always

[ crl_dp_policy ]
"""

AvailableCAConnectors.append("privacyidea.lib.caconnectors.localca.LocalCAConnector")


def _get_crl_next_update(filename: str) -> datetime.datetime:
    """
    Read the CRL file and return the next update as a timezone aware datetime

    :param filename: the name of the CRL file
    :type filename: str
    :rtype: datetime.datetime
    """
    with open(filename, 'r') as f:
        crl_buff = f.read()
        crl_obj = x509.load_pem_x509_crl(crl_buff.encode())
        return crl_obj.next_update_utc


class CONFIG(object):
    def __init__(self, name):
        self.directory = "./ca"
        self.keysize = 4096
        self.validity_ca = 1800
        self.validity_cert = 365
        self.crl_days = 30
        self.crl_overlap = 5
        self.dn = "/CN={0!s}".format(name)

    def __str__(self):
        s = """
        Directory  : {ca.directory}
        CA DN      : {ca.dn}
        CA Keysize : {ca.keysize}
        CA Validity: {ca.validity_ca}

        Validity of issued certificates: {ca.validity_cert}

        CRL validity: {ca.crl_days}
        CRL overlap : {ca.crl_overlap}
        """.format(ca=self)
        return s


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
    TEMPLATE_FILE = "templates"


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
        self.cakey = None
        self.cacert = None
        self.overlap = 1
        self.template_file = None
        self.workingdir = None
        self.templates = {}
        self.config = {}
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
                  ATTR.CRL_VALIDITY_PERIOD: 'int',
                  ATTR.TEMPLATE_FILE: 'string'}
        return {typ: config}

    def _check_attributes(self):
        for req_key in [ATTR.CAKEY, ATTR.CACERT]:
            if req_key not in self.config:
                raise CAError("required argument '{0!s}' is missing.".format(req_key))

    def set_config(self, config=None):
        self.config = config or {}
        self._check_attributes()
        # The CAKEY and the CACERT are passed as filenames
        self.cakey = self.config.get(ATTR.CAKEY)
        self.cacert = self.config.get(ATTR.CACERT)
        self.overlap = int(self.config.get(ATTR.CRL_OVERLAP_PERIOD, 2))
        self.template_file = self.config.get(ATTR.TEMPLATE_FILE)
        self.workingdir = self.config.get(ATTR.WORKING_DIR)
        if self.template_file and self.workingdir:
            if not self.template_file.startswith("/"):
                self.template_file = self.workingdir + "/" + self.template_file
        self.templates = self.get_templates()

    @staticmethod
    def _filename_from_x509(x509_name: x509.Name, file_extension="pem"):
        """
        return a filename from the subject from a x509 object

        :param x509_name: The X509Name object
        :type x509_name: X509Name object
        :param file_extension:
        :type file_extension: str
        :return: filename
        :rtype: str
        """
        filename = "_".join([to_unicode(name_attribute.value) for name_attribute in x509_name])
        return ".".join([filename, file_extension])

    def sign_request(self, csr: str, options: dict = None) -> tuple[int, Union[str, None]]:
        """
        Signs a certificate request with the key of the CA.

        *options* may contain the following entries:
          * ``openssl.cnf``: Path to the local OpenSSL CA configuration file
          * ``WorkingDir``: The directory where the configuration like openssl.cnf
                            can be found.
          * ``CSRDir``: The directory, where to save the certificate signing
                        requests. This is relative to the WorkingDir.
          * ``CertificateDir``: The directory where to save the certificates.
                                This is relative to the WorkingDir.
          * ``days``: Number of days the certificate should be valid (default 365,
                      can be overwritten by a given template setting)
          * ``spkac``: Whether the CSR is in SPKAC format
          * ``extension``: The extension section to use from the config file
          * ``template``: The template to use for signing the certificate

        :param csr: Certificate signing request (PEM string or SPKAC)
        :type csr: str
        :param options: Additional options for signing the CSR (see above)
        :type options: dict
        :return: A tuple containing a return value (0) and the certificate
                 object in PEM encoded format
        :rtype: tuple
        """
        # Sign the certificate for one year
        options = options or {}
        days = options.get("days", 365)
        spkac = options.get("spkac")
        config = options.get(ATTR.OPENSSL_CNF,
                             self.config.get(
                                 ATTR.OPENSSL_CNF, "/etc/ssl/openssl.cnf"))
        extension = options.get("extension", "server")
        template_name = options.get("template")
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

        if template_name:
            t_data = self.templates.get(template_name)
            extension = t_data.get("extensions", extension)
            days = t_data.get("days", days)

        # Determine filename from the CN of the request
        if spkac:
            common_name = re.search("CN=(.*)", csr).group(0).split("=")[1]
            csr_filename = common_name + ".txt"
            certificate_filename = common_name + ".der"
        else:
            csr_obj = x509.load_pem_x509_csr(csr.encode())
            csr_filename = self._filename_from_x509(csr_obj.subject, file_extension="req")
            certificate_filename = self._filename_from_x509(csr_obj.subject, file_extension="pem")
        csr_filename = csr_filename.replace(" ", "_")
        certificate_filename = certificate_filename.replace(" ", "_")
        # dump the file
        csr_filename = to_unicode(csr_filename.encode('ascii', 'ignore'))
        with open(os.path.join(csrdir, csr_filename), "w") as f:
            f.write(csr)

        # TODO: use the template name to set the days and the extension!
        if spkac:
            cmd = CA_SIGN_SPKAC.format(cakey=self.cakey, cacert=self.cacert,
                                       days=days, config=config,
                                       extension=extension,
                                       spkacfile=os.path.join(csrdir, csr_filename),
                                       certificate=os.path.join(certificatedir,
                                                                certificate_filename))
        else:
            cmd = CA_SIGN.format(cakey=self.cakey, cacert=self.cacert,
                                 days=days, config=config, extension=extension,
                                 csrfile=os.path.join(csrdir, csr_filename),
                                 certificate=os.path.join(certificatedir,
                                                          certificate_filename))
        # run the command
        args = shlex.split(cmd)
        # the command is configured by the administrator: CA key, CA cert, number of days, the config file
        p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=workingdir, universal_newlines=True)  # nosec B603
        result, error = p.communicate()
        if p.returncode != 0:  # pragma: no cover
            # Some error occurred
            log.warning(f"An error occurred during signing of the certificate: {error}")
            log.debug(f"Command that lead to the error: {cmd}")
            raise CAError("An error occurred during signing of the certificate")

        with open(os.path.join(certificatedir, certificate_filename), "rb") as f:
            certificate = f.read()

        # We return the cert_obj.
        if spkac:
            cert_obj = x509.load_der_x509_certificate(certificate)
            cert_result = cert_obj.public_bytes(Encoding.PEM).decode()
        else:
            # Already in PEM format
            cert_result = certificate.decode()
        return 0, cert_result

    def get_templates(self):
        """
        Return the dict of available templates, which are read from the
        template YAML file.

        :return: dict
        """
        content = {}
        if self.template_file:
            try:
                with open(self.template_file, 'r') as content_file:
                    file_content = content_file.read()
                    content = yaml.safe_load(file_content)
            except EnvironmentError:
                log.warning("Template file {0!s} for {1!s} not found or "
                            "not permitted.".format(self.template_file, self.name))
                log.debug('{0!s}'.format(traceback.format_exc()))
        return content

    def revoke_cert(self, certificate: str, request_id=None, reason=CRL_REASONS[0]) -> str:
        """
        Revoke the specified certificate. At this point only the database
        index.txt is updated.

        :param certificate: The certificate to revoke in PEM format
        :type certificate: str
        :param reason: One of the available reasons the certificate gets revoked
        :type reason: basestring
        :return: Returns the serial number of the revoked certificate. Otherwise,
                 an error is raised.
        """
        cert_obj = x509.load_pem_x509_certificate(certificate.encode())

        if reason not in CRL_REASONS:
            raise CAError("Unsupported revoke reason")

        serial = cert_obj.serial_number
        serial_hex = int_to_hex(serial)
        filename = serial_hex + ".pem"
        cmd = CA_REVOKE.format(cakey=self.cakey, cacert=self.cacert,
                               config=self.config.get(ATTR.OPENSSL_CNF),
                               certificate="/".join(p for p in [self.config.get(ATTR.CERT_DIR), filename] if p),
                               reason=reason)
        workingdir = self.config.get(ATTR.WORKING_DIR)
        args = shlex.split(cmd)
        # The command is configured by the administrator: CA key, CA cert, config file, certificate,
        # the revoking reason is fetched earlier
        p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=workingdir, universal_newlines=True)  # nosec B603
        result, error = p.communicate()
        if p.returncode != 0:  # pragma: no cover
            # Some error occurred
            raise CAError(error)

        return serial_hex

    def create_crl(self, publish=True, check_validity=False) -> str:
        """
        Create and Publish the CRL.

        :param publish: Whether the CRL should be published at its CDPs
        :param check_validity: Onle create a new CRL, if the old one is about to
            expire. Therefore, the overlap period and the remaining runtime of
            the CRL is checked. If the remaining runtime is smaller than the
            overlap period, we recreate the CRL.
        :return: the CRL location or None, if no CRL was created
        """
        crl = self.config.get(ATTR.CRL, "crl.pem")
        workingdir = self.config.get(ATTR.WORKING_DIR)
        create_new_crl = True
        ret = None
        # Check if we need to create a new CRL
        if check_validity:
            if crl.startswith("/"):
                full_path_crl = crl
            else:
                full_path_crl = workingdir + "/" + crl
            next_update = _get_crl_next_update(full_path_crl)
            if datetime.datetime.now(tz=datetime.timezone.utc) + \
                    datetime.timedelta(days=self.overlap) > next_update:
                log.info("We checked the overlap period and we need to create "
                         "the new CRL.")
            else:
                log.info("No need to create a new CRL, yet. Next Update: "
                         "{0!s}, overlap: {1!s}".format(next_update,
                                                        self.overlap))
                create_new_crl = False

        if create_new_crl:
            cmd = CA_GENERATE_CRL.format(cakey=self.cakey, cacert=self.cacert,
                                         config=self.config.get(ATTR.OPENSSL_CNF),
                                         CRL=crl)
            args = shlex.split(cmd)
            # The command is configured by the admin: CA key, CA cert, config file and CRL location
            p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=workingdir, universal_newlines=True)  # nosec B603
            result, error = p.communicate()
            if p.returncode != 0:  # pragma: no cover
                # Some error occurred
                raise CAError(error)
            ret = crl

        return ret

    @staticmethod
    def create_ca(name):
        """
        Create parameters for a new CA connector.
        The configuration is requested at the command line in questions and
        answers.
        If the configuration is valid, the CA will be created on the file system
        and the configuration for the new LocalCAConnector is returned.

        We are asking for the following:

        * Directory (should exist or the current user should be able to
          create it and write into it)
        * Keysize 2048/4096/8192
        * Validity of CA certificate
        * DN of CA Certificate
        * Validity of enrolled certificates
        * CRL:
           * default days
           * overlap period

        Fixed values:
        * Hash: SHA256
        * Name of Key, and CACert
        * Name of CRL
        * We create two templates for users and for servers.

        :param name: The name of the CA connector.
        :type name: str
        :return: The LocalCAConnector configuration
        :rtype: dict
        """
        config = CONFIG(name)

        while 1:
            directory = input("In which directory do you want to create "
                              "the CA [{0!s}]: ".format(config.directory))
            config.directory = directory or config.directory
            if not config.directory.startswith("/"):
                config.directory = os.path.abspath(config.directory)

            keysize = input("What should be the keysize of the CA (2048/4096/8192)"
                            "[{0!s}]: ".format(config.keysize))
            config.keysize = keysize or config.keysize

            validity_ca = input("How many days should the CA be valid ["
                                "{0!s}]: ".format(config.validity_ca))
            config.validity_ca = validity_ca or config.validity_ca

            dn = input("What is the DN of the CA [{0!s}]: ".format(config.dn))
            config.dn = dn or config.dn
            # At the moment we do not use this. This would be written to the
            # templates file.
            # validity_cert = raw_input(
            #    "What should be the validity period of enrolled certificates in days [{0!s}]: ".format(
            #    config.validity_cert))
            # config.validity_cert = validity_cert or config.validity_cert
            crl_days = input("How many days should the CRL be valid "
                             "[{0!s}]: ".format(config.crl_days))
            config.crl_days = crl_days or config.crl_days
            crl_overlap = input("What should be the overlap period of the CRL in days "
                                "[{0!s}]: ".format(config.crl_overlap))
            config.crl_overlap = crl_overlap or config.crl_overlap

            print("=" * 60)
            print("{0!s}".format(config))
            answer = input("Is this configuration correct? [y/n] ")
            if answer.lower() == "y":
                break

        # Create the CA on the file system
        try:
            Path(config.directory).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Unable to create local CA directory at {config.directory}: {e}")
            raise

        _generate_openssl_cnf(config)
        _init_ca(config)

        # return the configuration to the upper level, so that the CA
        # connector can be created in the database
        caparms = {"caconnector": name,
                   "type": "local",
                   ATTR.WORKING_DIR: config.directory,
                   ATTR.CACERT: "{0!s}/cacert.pem".format(config.directory),
                   ATTR.CAKEY: "{0!s}/cakey.pem".format(config.directory),
                   ATTR.CERT_DIR: config.directory,
                   ATTR.CRL: "{0!s}/crl.pem".format(config.directory),
                   ATTR.CSR_DIR: config.directory,
                   ATTR.CRL_VALIDITY_PERIOD: config.crl_days,
                   ATTR.CRL_OVERLAP_PERIOD: config.crl_overlap,
                   ATTR.OPENSSL_CNF: "{0!s}/openssl.cnf".format(config.directory)
                   }
        return caparms


def _generate_openssl_cnf(config):
    """
    Generate the openssl config file from the config object.

    :param config: Config object
    :return:
    """
    conf_file = OPENSSL_TEMPLATE.format(crl_days=config.crl_days,
                                        ca_days=config.validity_ca)
    with open("{0!s}/openssl.cnf".format(config.directory), "w") as f:
        f.write(conf_file)


def _init_ca(config):
    """
    Generate the CA certificate

    :param config:
    :return:
    """
    # Write the database
    with open("{0!s}/index.txt".format(config.directory), "w") as f:
        f.write("")

    # Write the serial file
    with open("{0!s}/serial".format(config.directory), "w") as f:
        f.write("1000")

    # create the privacy key and set accesss rights
    with open("{0!s}/cakey.pem".format(config.directory), "w") as f:
        f.write("")
    import stat
    os.chmod("{0!s}/cakey.pem".format(config.directory),
             stat.S_IRUSR | stat.S_IWUSR)
    command = "openssl genrsa -out {0!s}/cakey.pem {1!s}".format(
        config.directory, config.keysize)
    print("Running command...")
    print(command)
    args = shlex.split(command)
    # The command is created by the root user at the command line anyway
    p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=config.directory, universal_newlines=True)  # nosec B603
    result, error = p.communicate()
    if p.returncode != 0:  # pragma: no cover
        # Some error occurred
        raise CAError(error)

    # create the CA certificate
    command = """openssl req -config openssl.cnf -key cakey.pem \
      -new -x509 -days {ca_days!s} -sha256 -extensions v3_ca \
      -out cacert.pem -subj {ca_dn!s}""".format(ca_days=config.validity_ca,
                                                ca_dn=config.dn)
    print("Running command...")
    print(command)
    args = shlex.split(command)
    # The command is created by the root user at the command line anyways
    p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=config.directory, universal_newlines=True)  # nosec B603
    result, error = p.communicate()
    if p.returncode != 0:  # pragma: no cover
        # Some error occurred
        raise CAError(error)

    print("!" * 60)
    print("Please check the ownership of the private key")
    print("{0!s}/cakey.pem".format(config.directory))
    print("!" * 60)
