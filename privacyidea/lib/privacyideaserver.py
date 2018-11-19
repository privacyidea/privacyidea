# -*- coding: utf-8 -*-
#
#  2017-08-24 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Remote privacyIDEA server
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
from privacyidea.models import PrivacyIDEAServer as PrivacyIDEAServerDB
import logging
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import fetch_one_resource
from privacyidea.lib.error import ConfigAdminError, privacyIDEAError
import json
from privacyidea.lib import _
import requests

__doc__ = """
This is the library for creating, listing and deleting remote privacyIDEA 
server objects in the Database.

It depends on the PrivacyIDEAServver in the database model models.py. This 
module can be tested standalone without any webservices.
This module is tested in tests/test_lib_privacyideaserver.py
"""

log = logging.getLogger(__name__)


class PrivacyIDEAServer(object):
    """
    privacyIDEA Server object with configuration. The privacyIDEA Server object
    contains a test functionality so that the configuration can be tested.
    """

    def __init__(self, db_privacyideaserver_object):
        """
        Create a new PrivacyIDEA Server instance from a DB privacyIDEA object

        :param db_privacyideaserver_object: The database object
        :return: A privacyIDEA Server object
        """
        self.config = db_privacyideaserver_object

    @staticmethod
    def request(config, user, password):
        """
        Perform an HTTP test request to the privacyIDEA server.
        The privacyIDEA configuration contains the URL and the TLS verify.

        * config.url
        * config.tls

        :param config: The privacyIDEA configuration
        :type config: PrivacyIDEAServer Database Model
        :param user: the username to test
        :param password: the password/OTP to test
        :return: True or False. If any error occurs, an exception is raised.
        """
        response = requests.post(config.url + "/validate/check",
                          data={"user": user, "pass": password},
                          verify=config.tls
                          )
        log.debug("Sent request to privacyIDEA server. status code returned: "
                  "{0!s}".format(response.status_code))
        if response.status_code != 200:
            log.warning("The request to the remote privacyIDEA server {0!s} "
                        "returned a status code: {0!s}".format(config.url,
                                                               response.status_code))
            return False

        j_response = json.loads(response.content)
        result = j_response.get("result")
        return result.get("status") and result.get("value")


@log_with(log)
def get_privacyideaserver(identifier):
    """
    This returns the RADIUSServer object of the RADIUSServer definition
    "identifier".
    In case the identifier does not exist, an exception is raised.

    :param identifier: The name of the RADIUSserver definition
    :return: A RADIUSServer Object
    """
    server_list = get_privacyideaservers(identifier=identifier)
    if not server_list:
        raise ConfigAdminError("The specified privacyIDEA Server configuration "
                               "does not exist.")
    return server_list[0]


@log_with(log)
def get_privacyideaservers(identifier=None, url=None):
    """
    This returns a list of all privacyIDEA Servers matching the criterion.
    If no identifier or url is provided, it will return a list of all 
    privacyIDEA server definitions.

    :param identifier: The identifier or the name of the RADIUSServer
        definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no RADIUSServer
    :type identifier: basestring
    :param server: The FQDN or IP address of the RADIUSServer
    :type server: basestring
    :return: list of RADIUSServer Objects.
    """
    res = []
    sql_query = PrivacyIDEAServerDB.query
    if identifier:
        sql_query = sql_query.filter(PrivacyIDEAServerDB.identifier == identifier)
    if url:
        sql_query = sql_query.filter(PrivacyIDEAServerDB.server == url)

    for row in sql_query.all():
        res.append(PrivacyIDEAServer(row))

    return res


@log_with(log)
def add_privacyideaserver(identifier, url, tls=True, description=""):
    """
    This adds a privacyIDEA server to the privacyideaserver database table.

    If the "identifier" already exists, the database entry is updated.

    :param identifier: The identifier or the name of the privacyIDEA Server
        definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no radius server
    :type identifier: basestring
    :param url: The url of the privacyIDEA server
    :type url: basestring
    :param tls: whether the certificate of the server should be checked
    :type tls: bool
    :param description: Human readable description of the RADIUS server
        definition
    :return: The Id of the database object
    """
    r = PrivacyIDEAServerDB(identifier=identifier, url=url, tls=tls,
                            description=description).save()
    return r


@log_with(log)
def delete_privacyideaserver(identifier):
    """
    Delete the given server from the database.
    Raise ResourceNotFoundError if it couldn't be found.
    :param identifier: The identifier/name of the server
    :return: The ID of the database entry, that was deleted
    """
    return fetch_one_resource(PrivacyIDEAServerDB, identifier=identifier).delete()
