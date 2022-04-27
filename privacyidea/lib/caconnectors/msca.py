# -*- coding: utf-8 -*-
#
# License:  AGPLv3
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
This implementation is for the Microsoft CA via our middleware.

This module is tested in tests/test_lib_caconnector.py

TODO: write tests
"""

from privacyidea.lib.error import CAError
from privacyidea.lib.utils import int_to_hex, to_unicode
from privacyidea.lib.caconnectors.baseca import BaseCAConnector
from OpenSSL import crypto
from subprocess import Popen, PIPE
import yaml
import datetime
import shlex
import re
import logging
import os
from six import string_types
from six.moves import input
import traceback
import grpc
import privacyidea.lib.caconnectors.caservice_pb2_grpc
from privacyidea.lib.caconnectors.caservice_pb2 import *

log = logging.getLogger(__name__)

CRL_REASONS = ["unspecified", "keyCompromise", "CACompromise",
               "affiliationChanged", "superseded", "cessationOfOperation"]

def _get_crl_next_update(filename):
    """
    Read the CRL file and return the next update as datetime
    :param filename:
    :return:
    """
    pass


class CONFIG(object):

    def __init__(self, name):
        self.hostname = "foo.bar"
        self.port = 5000
        self.http_proxy = 0

    def __str__(self):
        s = """
        Worker HostName  : {ca.hostname}
        Worker Port      : {ca.port}
        Connect via HTTP Proxy      : {ca.http_proxy}
        """.format(ca=self)
        return s


class ATTR(object):
    __doc__ = """This is the list Attributes of the Microsoft CA connector."""
    HOSTNAME = "hostname"
    PORT = "port"
    HTTP_PROXY = "http_proxy"

class MSCAConnector(BaseCAConnector):
    """
    This connector connects to our middleware for the Microsoft CA. 
    """

    connector_type = "microsoft"

    def __init__(self, name, config=None):
        """
        Required attributes are:
         * hostname - the hostname of the middleware
         * port - the port the middleware listenes on
         * http_proxy - if http proxy should be used
        :param config: A dictionary with all necessary attributes.
        :return:
        """
        self.name = name
        self.hostname = None
        self.port = None
        self.http_proxy = None
        if config:
            self.set_config(config)
            
    def connect_to_worker(self):
        """
        creates a connection to the middleware and returns it.
        """
        channel = grpc.insecure_channel(f'{self.hostname}:{self.port}', options=(('grpc.enable_http_proxy', int(self.http_proxy)),))
        try:
            grpc.channel_ready_future(channel).result(timeout=3)
        except grpc.FutureTimeoutError:
            log.info("Worker seems to be offline. No connection could be established!")
        else:
            return privacyidea.lib.caconnectors.caservice_pb2_grpc.CAServiceStub(channel)


    @classmethod
    def get_caconnector_description(cls):
        """
        Return the description of this CA connectors.
        This contains the name as a key and the possible parameters.

        :return: resolver description dict
        :rtype:  dict
        """
        typ = cls.connector_type
        config = {ATTR.HOSTNAME: 'string',
                  ATTR.PORT: 'string',
                  ATTR.HTTP_PROXY: 'string'}
        return {typ: config}

    def _check_attributes(self):
        for req_key in [ATTR.HOSTNAME, ATTR.PORT]:
            if req_key not in self.config:
                raise CAError("required argument '{0!s}' is missing.".format(
                    req_key))

    def set_config(self, config=None):
        self.config = config or {}
        self._check_attributes()
        self.hostname = self.config.get(ATTR.HOSTNAME)
        self.port = self.config.get(ATTR.PORT)
        self.http_proxy = self.config.get(ATTR.HTTP_PROXY)
        self.templates = self.get_templates()

    @staticmethod
    def _filename_from_x509(x509_name, file_extension="pem"):
        """
        return a filename from the subject from an x509 object
        :param x509_name: The X509Name object
        :type x509_name: X509Name object
        :param file_extension:
        :type file_extension: str
        :return: filename
        :rtype: str
        """
        name_components = x509_name.get_components()
        filename = "_".join([to_unicode(value) for (key, value) in name_components])
        return '.'.join([filename, file_extension])

    def sign_request(self, csr, options=None):
        """
        Send a signing request to the Microsoft CA

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
        :return: Returns the certificate object if cert was provided instantly
        :rtype: X509 or None
        """
        conn = self.connect_to_worker()
        if conn:
            reply = conn.SubmitCR(SubmitCRRequest(cr=csr, templateName=options.get("template"), caName=conn.GetCAs(GetCAsRequest()).caName[0])) # options.get("ca")))
            if reply.disposition == 3:
                log.info("cert rolled out")
                certificate = conn.GetCertificate(GetCertificateRequest(id=reply.requestId, caName=conn.GetCAs(GetCAsRequest()).caName[0])).cert
                return  crypto.load_certificate(crypto.FILETYPE_PEM, certificate)
            if reply.disposition == 5:
                log.info("cert still under submission")
            else:
                log.error("certification request could not be fullfilled!")


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
        Return the dict of available templates

        :return: String
        """
        conn = self.connect_to_worker()
        if conn:
            templ = {}
            for template in conn.GetTemplates(GetTemplatesRequest()).ListFields()[0][1]:
                templ[template] = ""
            return templ

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
        pass

    def create_crl(self, publish=True, check_validity=False):
        """
        Create and Publish the CRL.

        :param publish: Whether the CRL should be published at its CDPs
        :param check_validity: Onle create a new CRL, if the old one is about to
            expire. Therfore the overlap period and the remaining runtime of
            the CRL is checked. If the remaining runtime is smaller than the
            overlap period, we recreate the CRL.
        :return: the CRL location or None, if no CRL was created
        """
        pass

    @staticmethod
    def create_ca(name):
        """
        Create parameters for a new CA connector.
        The configuration is requested at the command line in questions and
        answers.
        If the configuration is valid, the CA will be created on the file system
        and the configuration for the new LocalCAConnector is returned.

        We are asking for the following:
        * hostname of the middleware
        * port of the middleware
        * if a http_proxy is used

        :param name: The name of the CA connector.
        :type name: str
        :return: The LocalCAConnector configuration
        :rtype: dict
        """
        config = CONFIG(name)

        while True:
            hostname = input("Whats the hostname of the Microsoft CA middleware ".format(config.hostname))
            port = input("Whats the port of the Microsoft CA middleware ".format(config.port))
            http_proxy = input("Is a http proxy being used ".format(config.http_proxy))
            print("="*60)
            print("{0!s}".format(config))
            answer = input("Is this configuration correct? [y/n] ")
            if answer.lower() == "y":
                break

        _init_ca(config)

        # return the configuration to the upper level, so that the CA
        # connector can be created in the database
        caparms = {u"caconnector": name,
                   u"type": u"msca",
                   ATTR.HOSTNMAE: config.hostname,
                   ATTR.PORT: config.port,
                   ATTR.HTTP_PROXY: config.http_proxy
                   }
        return caparms

def _init_ca(config):
    """
    Generate the CA certificate
    :param config:
    :return:
    """
    pass
