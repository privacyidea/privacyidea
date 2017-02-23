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


class BaseCAConnector(object):
    def revoke_cert(self, certificate, reason=None):
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
        pass

    def create_crl(self, publish=True):
        """
        Create and Publish the CRL.

        :param publish: Whether the CRL should be published at its CDPs
        :return: the CRL location
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
