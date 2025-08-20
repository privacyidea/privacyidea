# SPDX-FileCopyrightText: (C) 2016 Cornelius Kölbel <cornelius.koelbel@netknights.it>
# SPDX-FileCopyrightText: (C) 2016 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2019 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.

#  2017-10-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add timeout handling
#  2016-02-19 Cornelius Kölbel <cornelius@privacyidea.org>
#             RADIUS Server implementation
#
"""
This is the library for creating, listing and deleting RADIUS server objects in
the Database.

It depends on the RADIUSserver in the database model models.py. This module can
be tested standalone without any webservices.
This module is tested in tests/test_lib_radiusserver.py
"""
import logging
import pyrad.packet
from pyrad.client import Client
from pyrad.client import Timeout
from pyrad.dictionary import Dictionary

from privacyidea.models import db, RADIUSServer as RADIUSServerDB
from privacyidea.lib.crypto import (decryptPassword, encryptPassword,
                                    FAILED_TO_DECRYPT_PASSWORD)
from privacyidea.lib.config import get_from_config
from privacyidea.lib.log import log_with
from privacyidea.lib.error import (ConfigAdminError, privacyIDEAError,
                                   ResourceNotFoundError)
from privacyidea.lib import _
from privacyidea.lib.utils import fetch_one_resource, to_bytes
from privacyidea.lib.utils.export import (register_import, register_export)
from privacyidea.lib.resolver import CENSORED

log = logging.getLogger(__name__)


class RADIUSServer(object):
    """
    RADIUS Server object with configuration. The RADIUS Server object
    contains a test functionality so that the configuration can be tested.
    """

    def __init__(self, db_radius_object: RADIUSServerDB):
        """
        Create a new RADIUSServer instance from a RADIUSServer database row

        :param db_radius_object: The database object
        :return: A RADIUS Server object
        """
        self.config = db_radius_object

    def get_secret(self):
        return decryptPassword(self.config.secret)

    def request(self, user, password):
        """
        Perform a RADIUS request to a RADIUS server.
        The RADIUS configuration contains the IP address, the port and the
        secret of the RADIUS server.

        * config.server
        * config.port
        * config.secret
        * config.retries
        * config.timeout

        :param user: the radius username
        :type user: str
        :param password: the radius password
        :type password: str
        :return: True or False. If any error occurs, an exception is raised.
        """
        success = False

        nas_identifier = get_from_config("radius.nas_identifier",
                                         "privacyIDEA")
        r_dict = self.config.dictionary or get_from_config("radius.dictfile",
                                                           "/etc/privacyidea/"
                                                           "dictionary")
        message_authenticator = False
        if self.config.options:
            message_authenticator = self.config.options.get("message_authenticator", False)
        log.debug("NAS Identifier: %r, "
                  "Dictionary: %r" % (nas_identifier, r_dict))
        log.debug("constructing client object "
                  "with server: %r, port: %r, secret: %r" %
                  (self.config.server, self.config.port, self.config.secret))
        log.debug("Using Message-Authenticator: %r", message_authenticator)

        srv = Client(server=self.config.server,
                     authport=self.config.port,
                     secret=to_bytes(decryptPassword(self.config.secret)),
                     dict=Dictionary(r_dict))

        # Set retries and timeout of the client
        srv.timeout = self.config.timeout
        srv.retries = self.config.retries

        req = srv.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                                   User_Name=user.encode('utf-8'),
                                   NAS_Identifier=nas_identifier.encode('ascii'),
                                   message_authenticator=message_authenticator)

        # PwCrypt encodes unicode strings to UTF-8
        req["User-Password"] = req.PwCrypt(password)
        try:
            # The authenticator is available after the call to PwCrypt
            request_authenticator = req.authenticator
            response = srv.SendPacket(req)

            if response.code == pyrad.packet.AccessAccept:
                if response.verify_message_authenticator(original_authenticator=request_authenticator):
                    log.info("RADIUS server %s granted access to user %s.", self.config.server, user)
                    success = True
                else:
                    log.warning("Unable to verify 'Message-Authenticator' attribute of RADIUS response.")
            elif response.code == pyrad.packet.AccessChallenge:
                log.info("RADIUS server create a challenge.")
                pass
            else:
                log.warning("Radiusserver %s rejected access to user %s. "
                            "Received response package code %d", self.config.server, user, response.code)
        except Timeout:
            log.warning("Received timeout from remote radius server {0!s}".format(self.config.server))

        return success


@log_with(log)
def get_radius(identifier: str) -> RADIUSServer:
    """
    This returns the RADIUSServer object of the RADIUSServer definition
    "identifier".
    In case the identifier does not exist, an exception is raised.

    :param identifier: The name of the RADIUSserver definition
    :return: A RADIUSServer Object
    """
    server_list = get_radiusservers(identifier=identifier)
    if not server_list:
        raise ConfigAdminError(f"The specified RADIUSServer configuration "
                               f"'{identifier}' does not exist.")
    return server_list[0]


@log_with(log)
def get_radiusservers(identifier: str = None, server: str = None) -> list[RADIUSServer]:
    """
    This returns a list of all RADIUSServers matching the criterion.
    If no identifier or server is provided, it will return a list of all RADIUS
    server definitions.

    :param identifier: The identifier or the name of the RADIUSServer
        definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no RADIUSServer
    :param server: The FQDN or IP address of the RADIUSServer
    :return: list of RADIUSServer Objects.
    """
    result = []
    sql_query = db.select(RADIUSServerDB)
    if identifier:
        sql_query = sql_query.filter_by(identifier=identifier)
    if server:
        sql_query = sql_query.filter_by(server=server)

    for row in db.session.execute(sql_query).scalars():
        result.append(RADIUSServer(row))

    return result


@log_with(log)
def list_radiusservers(identifier=None, server=None):
    res = {}
    server_list = get_radiusservers(identifier=identifier, server=server)
    for server in server_list:
        decrypted_secret = decryptPassword(server.config.secret)
        # If the database contains garbage, use the empty password as fallback
        if decrypted_secret == FAILED_TO_DECRYPT_PASSWORD:
            decrypted_secret = ""  # nosec B105 # Reset password in case of error
        res[server.config.identifier] = {"server": server.config.server,
                                         "port": server.config.port,
                                         "dictionary": server.config.dictionary,
                                         "description": server.config.description,
                                         "secret": decrypted_secret,
                                         "timeout": server.config.timeout,
                                         "retries": server.config.retries,
                                         "options": server.config.options}

    return res


@log_with(log)
def add_radius(identifier: str, server: str = None, secret: str = None,
               port: int = 1812, description: str = "",
               dictionary: str = '/etc/privacyidea/dictionary',
               retries: int = 3, timeout: int = 5, options: dict = None) -> int:
    """
    This adds a RADIUS server to the RADIUSServer database table.

    If the "identifier" already exists, the database entry is updated.

    :param identifier: The identifier or the name of the RADIUSServer
        definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no radius server
    :param server: The FQDN or IP address of the RADIUS server
    :param secret: The RADIUS secret
    :param port: the radius port
    :param description: Human readable description of the RADIUS server
        definition
    :param dictionary: The RADIUS dictionary
    :param retries: Number of times to retry the request RADIUS request
    :param timeout: Timeout in seconds for the RADIUS request
    :param options: Additional options for the RADIUS server
    :return: The Id of the database object
    """
    encrypted_secret = encryptPassword(secret)
    if len(encrypted_secret) > 255:
        raise privacyIDEAError(description=_("The RADIUS secret is too long"),
                               id=2234)
    r = RADIUSServerDB(identifier=identifier, server=server, port=port,
                       secret=encrypted_secret, description=description,
                       dictionary=dictionary,
                       retries=retries, timeout=timeout, options=options).save()
    return r


@log_with(log)
def test_radius(identifier, server, secret, user, password, port=1812, description="",
                dictionary='/etc/privacyidea/dictionary', retries=3, timeout=5,
                options=None):
    """
    This tests a RADIUS server configuration by sending an access request.

    :param identifier: The identifier or the name of the RADIUSServer definition
    :type identifier: basestring
    :param server: The FQDN or IP address of the RADIUS server
    :type server: basestring
    :param secret: The RADIUS secret
    :type secret: str
    :param user: the username to send
    :param password: the password to send
    :param port: the radius port
    :type port: int
    :param description: Human readable description of the RADIUS server
        definition
    :param dictionary: The RADIUS dictionary
    :param retries: Number of times to retry the request RADIUS request
    :param timeout: Timeout in seconds for the RADIUS request
    :param options: Additional options for the RADIUS server
    :return: The result of the access request
    """
    # Check if the secret is censored. If it is, we can assume a configuration exists and use its secret
    encrypted_secret = encryptPassword(secret)
    if secret == CENSORED:
        try:
            rad_serv = fetch_one_resource(RADIUSServerDB, identifier=identifier)
            encrypted_secret = rad_serv.secret
        except ResourceNotFoundError:
            # Maybe __CENSORED__ is the secret?
            pass
    if len(encrypted_secret) > 255:
        raise privacyIDEAError(description=_("The RADIUS secret is too long"),
                               id=2234)
    s = RADIUSServerDB(identifier=identifier, server=server, port=port,
                       secret=encrypted_secret, dictionary=dictionary,
                       retries=retries, timeout=timeout,
                       description=description, options=options)
    radius_server = RADIUSServer(s)
    return radius_server.request(user, password)


@log_with(log)
def delete_radius(identifier):
    """
    Delete the given server from the database.
    If no such entry could be found, a ResourceNotFoundError is raised.
    :param identifier: The identifier/name of the server
    :return: The ID of the database entry, that was deleted
    """
    return fetch_one_resource(RADIUSServerDB, identifier=identifier).delete()


@register_export('radiusserver')
def export_radiusserver(name=None):
    """ Export given or all radiusserver configuration """
    return list_radiusservers(identifier=name)


@register_import('radiusserver')
def import_radiusserver(data, name=None):
    """Import radiusserver configuration"""
    log.debug('Import radiusserver config: {0!s}'.format(data))
    for res_name, res_data in data.items():
        if name and name != res_name:
            continue
        res_data['secret'] = res_data.pop('password')
        rid = add_radius(res_name, **res_data)
        log.info('Import of smtpserver "{0!s}" finished,'
                 ' id: {1!s}'.format(res_name, rid))
