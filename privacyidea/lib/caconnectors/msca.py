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
from privacyidea.lib.caconnectors.baseca import BaseCAConnector, AvailableCAConnectors
from OpenSSL import crypto
import logging
from six.moves import input
from privacyidea.lib.utils import is_true
from privacyidea.lib.error import CSRError, CSRPending

log = logging.getLogger(__name__)
try:
    import grpc
    from privacyidea.lib.caconnectors.caservice_pb2_grpc import CAServiceStub
    from privacyidea.lib.caconnectors.caservice_pb2 import (GetCAsRequest,
                                                            GetTemplatesRequest,
                                                            GetCRStatusRequest,
                                                            GetCRStatusReply,
                                                            SubmitCRRequest,
                                                            GetCertificateRequest,
                                                            GetCertificateReply)
    AvailableCAConnectors.append("privacyidea.lib.caconnectors.msca.MSCAConnector")
except ImportError:
    log.warning("Can not import grpc modules.")


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
        self.http_proxy = int(is_true(self.config.get(ATTR.HTTP_PROXY)))
        self.templates = self.get_templates()
        self.ca = self.config.get(ATTR.CA)

    def sign_request(self, csr, options=None):
        """
        Send a signing request to the Microsoft CA

        options can be
        template: The name of the certificate template to issue

        :param csr: Certificate signing request
        :type csr: PEM string or SPKAC
        :param options: Additional options like the validity time or the template or spkac=1
        :type options: dict
        :return: Returns the certificate object if cert was provided instantly
        :rtype: X509 or None
        """
        if self.connection:
            reply = self.connection.SubmitCR(SubmitCRRequest(cr=csr, templateName=options.get("template"),
                                                             caName=self.ca))
            if reply.disposition == 3:
                requestId = reply.requestId
                log.info("certificate with request ID {0!s} successfully rolled out".format(requestId))
                certificate = self.connection.GetCertificate(GetCertificateRequest(id=requestId,
                                                                                   caName=self.ca)).cert
                return crypto.load_certificate(crypto.FILETYPE_PEM, certificate)
            if reply.disposition == 5:
                log.info("cert still under submission")
                raise CSRPending(requestId=reply.requestId)
            else:
                log.error("certification request could not be fulfilled! {0!s}".format(reply))
                raise CSRError()

    def get_cr_status(self, request_id):
        """
        If a certificate needs a CA manager approval the request is in a pending state.
        This method fetches the state of a requested certificate.
        This way we can know, if the certificate was issued in the meantime.

        :param request_id: Id of the request to check
        :type request_id: int
        :return: Status code of the request
        """
        if self.connection:
            csrRequest = GetCRStatusRequest()
            csrRequest.certRequestId = request_id
            csrRequest.caName = self.ca
            csrReply = self.connection.GetCRStatus(csrRequest)
            """
            Disposition 2: denied
            Disposition 3: issued
            Disposition 5: pending
            """
            return csrReply.disposition

    def get_issued_certificate(self, request_id):
        """
        If get_csr_status returned a disposition 3, we can fetch the issued certificate.

        :param request_id: The id of the original certificate request
        :return: The certificate as PEM string
        """
        if self.connection:
            certRequest = GetCertificateRequest()
            certRequest.id = request_id
            certRequest.caName = self.ca
            certReply = self.connection.GetCertificate(certRequest)
            return certReply.cert

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
