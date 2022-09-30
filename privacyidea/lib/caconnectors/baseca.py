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

# This takes a set of all CA Connector modules.
AvailableCAConnectors = []


class BaseCAConnector(object):
    def revoke_cert(self, certificate, request_id=None, reason=None):
        """
        Revoke the specified certificate. At this point only the database
        index.txt is updated.

        :param certificate: The certificate to revoke
        :type certificate: Either takes X509 object or a PEM encoded
            certificate (string)
        :param request_id: The Id of the certificate in the certificate authority
        :type request_id: int
        :param reason: One of the available reasons the certificate gets revoked
        :type reason: basestring
        :return: Returns the serial number of the revoked certificate. Otherwise
            an error is raised.
        """
        pass

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
        :return: Returns a return value and the certificate
        :rtype: (int, x509)
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

    def request_cert(self):
        """
        create key server side
        create key on client side
        via PKCS10
        :return:
        """
        pass

    def get_cr_status(self, request_id):
        """
        If a certificate needs a CA manager approval the request is in a pending state.
        This method fetches the state of a requested certificate.
        This way we can know, if the certificate was issued in the meantime.

        :return:
        """
        pass

    def get_issued_certificate(self, request_id):
        """
        If get_csr_status returned the information that the certificate has been enrolled,
        we can fetch the issued certificate.

        :param request_id: The id of the original certificate request
        :return: The certificate as PEM string
        """
        pass

    @classmethod
    def get_caconnector_description(cls):
        """
        Return the description of this CA connectors.
        This contains the name as a key and the possible parameters.

        :return: resolver description dict
        :rtype:  dict
        """
        return {}

    def set_config(self, config=None):
        """
        Set the configuration of the
        :param config: A dict with specific config values
        :return:
        """
        pass

    def get_templates(self):
        """
        Return a dictionary of available certificate templates.
        The names of the certificate templates are the keys of the dict.

        Depending on the user we could return different templates.

        :return:
        """
        return {}

    def get_config(self, config):
        """
        This method helps to format the config values of the CA Connector.
        :param config: The configuration as it is stored in the database
        :type config: dict
        :return:
        """
        return config

    def get_specific_options(self):
        """
        Returns a dict of additional options for a specific connector instance.
        :return:
        """
        return {}
