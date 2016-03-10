# -*- coding: utf-8 -*-
#
#  2016-03-08 Cornelius Kölbel <cornelius@privacyidea.org>
#             SAML IdP Configuration
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
from privacyidea.models import SAMLIdP as SAMLIdP_DB
import logging
from privacyidea.lib.log import log_with
from privacyidea.lib.error import ConfigAdminError
import requests
from saml2 import (
    BINDING_HTTP_POST,
    BINDING_HTTP_REDIRECT,
    entity,
)
from saml2.client import Saml2Client
from saml2.config import Config as Saml2Config
__doc__ = """
This is the library for creating, listing and deleting SAML IdP server
configurations in the database.

It depends on the SAMLIdP in the database model models.py. This module can
be tested standalone without any webservices.
This module is tested in tests/test_lib_samlidp.py
"""

log = logging.getLogger(__name__)


@log_with(log)
def fetch_metadata(identifier):
    """
    This fetches the metadata from the metadata url in and stores the result
    in the database field metadata_cache.
    :param identifier: The identifier of the SAML IdP
    :return: the metadata string
    """
    samlidp_object = get_samlidp(identifier)
    res = requests.get(samlidp_object.metadata_url)
    samlidp_object.metadata_cache = res.text
    samlidp_object.save()
    return samlidp_object.metadata_cache


@log_with(log)
def get_samlidp(identifier):
    """
    This returns the SAML IdP configuration by the "identifier".
    In case the identifier does not exist, an exception is raised.

    :param identifier: The name of the SAML IdP definition
    :return: A RADIUSServer Object
    """
    server_list = get_samlidp_list(identifier=identifier)
    if not server_list:
        raise ConfigAdminError("The specified SAML IdP configuration does "
                               "not exist.")
    return server_list[0]


@log_with(log)
def get_samlidp_list(identifier=None, active=None):
    """
    This returns a list of all SAML IdP configurations.

    :param identifier: The identifier or the name of the SAML IdP definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no IdP.
    :type identifier: basestring
    :return: list of SAML IdP Objects.
    """
    res = []
    sql_query = SAMLIdP_DB.query
    if identifier:
        sql_query = sql_query.filter(SAMLIdP_DB.identifier == identifier)

    if active is not None:
        sql_query = sql_query.filter(SAMLIdP_DB.active == active)

    for samlidp_object in sql_query.all():
        res.append(samlidp_object)

    return res


@log_with(log)
def add_samlidp(identifier, metadata_url,
                acs_url, https_acs_url,
                active=True, allow_unsolicited=True,
                authn_requests_signed=False,
                logout_requests_signed=True,
                want_assertions_signed=True,
                want_response_signed=False):
    """
    This adds a SAML IdP configuration to the SAMLIdP database table.
    If the "identifier" already exists, the database entry is updated.

    :param identifier: The identifier or the name of the SAML IdP configuration.
    :type identifier: basestring
    :param metadata_url: The URL where to fetch the metadata
    :param acs_url: The URL where the IdP returns to.
        Usually the privacyIDEA base URL
    :param https_acs_url: The URL where the IdP returns to.
    :param active: whether the SAML config should be active
    :param allow_unsolicited:
    :param authn_requests_signed:
    :param logout_requests_signed:
    :param want_response_signed:
    :param want_assertions_signed:
    :return: The Id of the database object
    """
    metadata = ""
    r = SAMLIdP_DB(identifier=identifier, active=active,
                   metadata_url=metadata_url,
                   acs_url=acs_url, https_acs_url=https_acs_url,
                   allow_unsolicited=allow_unsolicited,
                   authn_requests_signed=authn_requests_signed,
                   logout_requests_signed=logout_requests_signed,
                   want_assertions_signed=want_assertions_signed,
                   want_response_signed=want_response_signed).save()
    if r > 0:
        # We were able to save the data and immediately try to fill the
        # metadata cache
        metadata = fetch_metadata(identifier)
    return r, metadata


@log_with(log)
def delete_samlidp(identifier):
    """
    Delete the given SAML IdP from the database
    :param identifier: The identifier/name of the server
    :return: The ID of the database entry, that was deleted
    """
    ret = -1
    samlidp = SAMLIdP_DB.query.filter(SAMLIdP_DB.identifier ==
                                      identifier).first()
    if samlidp:
        samlidp.delete()
        ret = samlidp.id
    return ret


def get_saml_client(identifier):
    """
    Returns the SAML client configuration to a SAML IdP stored in the database.
    The configuration is a hash for use by saml2.config.Config

    :return: SAML client configuration
    :rtype: saml2.config.Config
    """
    saml_idps = get_samlidp_list()
    saml_config = None
    # Find the identifier in the list
    for saml_idp in saml_idps:
        if saml_idp.identifier == identifier:
            saml_config = saml_idp

    # Fetch the metadata if the data is not yet cached
    if not saml_config.metadata_cache:
        fetch_metadata(identifier)

    settings = {
        'metadata': {
            "inline": saml_config.metadata_cache
            },
        'service': {
            'sp': {
                'endpoints': {
                    'assertion_consumer_service': [
                        (saml_config.acs_url, BINDING_HTTP_REDIRECT),
                        (saml_config.acs_url, BINDING_HTTP_POST),
                        (saml_config.https_acs_url, BINDING_HTTP_REDIRECT),
                        (saml_config.https_acs_url, BINDING_HTTP_POST)
                    ],
                },
                'allow_unsolicited': saml_config.allow_unsolicited,
                'authn_requests_signed': saml_config.authn_requests_signed,
                'logout_requests_signed': saml_config.logout_requests_signed,
                'want_assertions_signed': saml_config.want_assertions_signed,
                'want_response_signed': saml_config.want_response_signed,
            },
        },
    }
    spConfig = Saml2Config()
    spConfig.load(settings)
    spConfig.allow_unknown_attributes = True
    saml_client = Saml2Client(config=spConfig)
    return saml_client
