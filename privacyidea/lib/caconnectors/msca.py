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
from privacyidea.lib.caconnectors.baseca import BaseCAConnector, AvailableCAConnectors
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
log = logging.getLogger(__name__)

try:
    import grpc
    from privacyidea.lib.caconnectors.caservice_pb2_grpc import CAServiceStub
    from privacyidea.lib.caconnectors.caservice_pb2 import (GetCAsRequest,
                                                            GetTemplatesRequest,
                                                            SubmitCRRequest,
                                                            GetCertificateRequest)
    AvailableCAConnectors.append("privacyidea.lib.caconnectors.msca.MSCAConnector")
except ImportError:
    log.warning("Can not import grpc modules.")

from privacyidea.lib.utils import is_true
from privacyidea.lib.error import CSRError, CSRPending


CRL_REASONS = ["unspecified", "keyCompromise", "CACompromise",
               "affiliationChanged", "superseded", "cessationOfOperation"]


class CONFIG(object):

    def __init__(self, name):
        self.hostname = "foo.bar"
        self.port = 5000
        self.http_proxy = 0
        self.ca = "hostname\\caname"

    def __str__(self):
        s = """
        Worker HostName  : {ca.hostname}
        Worker Port      : {ca.port}
        Connect via HTTP Proxy      : {ca.http_proxy}
        CA               : {ca.ca}
        """.format(ca=self)
        return s


class ATTR(object):
    __doc__ = """This is the list Attributes of the Microsoft CA connector."""
    HOSTNAME = "hostname"
    PORT = "port"
    HTTP_PROXY = "http_proxy"
    CA = "ca"


class MSCAConnector(BaseCAConnector):
    """
    This connector connects to our middleware for the Microsoft CA.
    """

    connector_type = "microsoft"

    def __init__(self, name, config=None):
        """
        Required attributes are:
         * hostname - the hostname of the middleware
         * port - the port the middleware listens on
         * http_proxy - if http proxy should be used
        :param config: A dictionary with all necessary attributes.
        :return:
        """
        self.name = name
        self.hostname = None
        self.port = None
        self.http_proxy = None
        self.ca = None
        self._connection = None
        if config:
            self.set_config(config)
            self._connection = self._connect_to_worker()
            pass
        # Note: We can create an empty CA connector object and later configure it using self.set_config().

    @property
    def connection(self):
        if not self._connection:
            self._connection = self._connect_to_worker()
        return self._connection

    def get_config(self, config):
        """
        This method helps to format the config values of the CA Connector.
        :param config: The configuration as it is stored in the database
        :type config: dict
        :return:
        """
        config[ATTR.HTTP_PROXY] = is_true(config.get(ATTR.HTTP_PROXY))
        return config

    def _connect_to_worker(self):
        """
        creates a connection to the middleware and returns it.
        """
        channel = grpc.insecure_channel('{0!s}:{1!s}'.format(self.hostname, self.port),
                                        options=(('grpc.enable_http_proxy', int(is_true(self.http_proxy))),))
        try:
            grpc.channel_ready_future(channel).result(timeout=3)
        except grpc.FutureTimeoutError:
            log.warning("Worker seems to be offline. No connection could be established!")
        else:
            return CAServiceStub(channel)

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
                  ATTR.HTTP_PROXY: 'string',
                  ATTR.CA: 'string'}
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
        log.error(config)
        self.http_proxy = int(is_true(self.config.get(ATTR.HTTP_PROXY)))
        self.templates = self.get_templates()
        self.ca = self.config.get(ATTR.CA)
        log.error(self.http_proxy)

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
        if self.connection:
            reply = self.connection.SubmitCR(SubmitCRRequest(cr=csr, templateName=options.get("template"),
                                                             caName=self.ca))
            if reply.disposition == 3:
                log.info("cert rolled out")
                #requestId = reply.requestId
                certificate = self.connection.GetCertificate(GetCertificateRequest(id=reply.requestId,
                                                                                   caName=self.ca)).cert
                return crypto.load_certificate(crypto.FILETYPE_PEM, certificate)
            if reply.disposition == 5:
                log.info("cert still under submission")
                raise CSRPending(requestId=reply.requestId)
            else:
                log.error("certification request could not be fullfilled! {0!s}".format(reply))
                raise CSRError()

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
        if self.connection:
            templ = {}
            templateRequest = GetTemplatesRequest()
            templateReply = self.connection.GetTemplates(templateRequest)
            for template in templateReply.templateName:
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
        :param check_validity: Only create a new CRL, if the old one is about to
            expire. Therefore the overlap period and the remaining runtime of
            the CRL is checked. If the remaining runtime is smaller than the
            overlap period, we recreate the CRL.
        :return: the CRL location or None, if no CRL was created
        """
        pass

    @staticmethod
    def create_ca(name):  # pragma: no cover
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
            config.hostname = input("Hostname of the privacyIDEA MS CA worker: ")
            config.port = input("Port of the privacyIDEA MS CA worker: ")
            config.http_proxy = input("Use HTTP proxy [0/1]: ")
            dummy_ca = MSCAConnector("dummy", {ATTR.HOSTNAME: config.hostname,
                                               ATTR.PORT: config.port,
                                               ATTR.HTTP_PROXY: config.http_proxy})
            # returns a list of machine names\CAnames
            cARequest = GetCAsRequest()
            cAReply = dummy_ca.connection.GetCAs(cARequest)
            cas = [x for x in cAReply.caName]
            print("Available CAs: \n")
            for c in cas:
                print("     {0!s}".format(c))
            config.ca = input("Choose CA: ".format(config.ca))
            print("=" * 60)
            print("{0!s}".format(config))
            answer = input("Is this configuration correct? [y/n] ")
            if answer.lower() == "y":
                break

        # return the configuration to the upper level, so that the CA
        # connector can be created in the database
        caparms = {u"caconnector": name,
                   u"type": u"microsoft",
                   ATTR.HOSTNAME: config.hostname,
                   ATTR.PORT: config.port,
                   ATTR.HTTP_PROXY: config.http_proxy,
                   ATTR.CA: config.ca
                   }
        return caparms

    def get_specific_options(self):
        """

        :return: return the list of available CAs in the domain
        """
        cas = []
        if self.connection:
            # returns a list of machine names\CAnames
            cARequest = GetCAsRequest()
            cAReply = self.connection.GetCAs(cARequest)
            cas = [x for x in cAReply.caName]
        return {"available_cas": cas}
