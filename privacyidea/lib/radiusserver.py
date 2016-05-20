# -*- coding: utf-8 -*-
#
#  2016-02-19 Cornelius Kölbel <cornelius@privacyidea.org>
#             RADIUS Server implementation
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
from privacyidea.models import RADIUSServer as RADIUSServerDB
from privacyidea.lib.crypto import decryptPassword, encryptPassword
from privacyidea.lib.config import get_from_config
import logging
from privacyidea.lib.log import log_with
from privacyidea.lib.error import ConfigAdminError, privacyIDEAError
import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary
from gettext import gettext as _

__doc__ = """
This is the library for creating, listing and deleting RADIUS server objects in
the Database.

It depends on the RADIUSserver in the database model models.py. This module can
be tested standalone without any webservices.
This module is tested in tests/test_lib_radiusserver.py
"""

log = logging.getLogger(__name__)


class RADIUSServer(object):
    """
    RADIUS Server object with configuration. The RADIUS Server object
    contains a test functionality so that the configuration can be tested.
    """

    def __init__(self, db_radius_object):
        """
        Create a new RADIUSServer instance fomr a DB RADIUS object

        :param db_radius_object: The database object
        :return: A RADIUS Server object
        """
        self.config = db_radius_object

    def get_secret(self):
        return decryptPassword(self.config.secret)

    @staticmethod
    def request(config, user, password):
        """
        Perform a RADIUS request to a RADIUS server.
        The RADIUS configuration contains the IP address, the port and the
        secret of the RADIUS server.

        * config.server
        * config.port
        * config.secret

        :param config: The RADIUS configuration
        :type config: RADIUSServer Database Model
        :param user: the radius username
        :param password: the radius password
        :return: True or False. If any error occurs, an exception is raised.
        """
        success = False

        nas_identifier = get_from_config("radius.nas_identifier",
                                         "privacyIDEA")
        r_dict = config.dictionary or get_from_config("radius.dictfile",
                                                      "/etc/privacyidea/"
                                                      "dictionary")
        log.debug("NAS Identifier: %r, "
                  "Dictionary: %r" % (nas_identifier, r_dict))
        log.debug("constructing client object "
                  "with server: %r, port: %r, secret: %r" %
                  (config.server, config.port, config.secret))

        srv = Client(server=config.server,
                     authport=config.port,
                     secret=decryptPassword(config.secret),
                     dict=Dictionary(r_dict))

        req = srv.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                                   User_Name=user.encode('ascii'),
                                   NAS_Identifier=nas_identifier.encode('ascii'))

        req["User-Password"] = req.PwCrypt(password)
        response = srv.SendPacket(req)
        if response.code == pyrad.packet.AccessAccept:
            log.info("Radiusserver %s granted "
                     "access to user %s." % (config.server, user))
            success = True
        else:
            log.warning("Radiusserver %s"
                        "rejected access to user %s." %
                        (config.server, user))

        return success


@log_with(log)
def get_radius(identifier):
    """
    This returns the RADIUSServer object of the RADIUSServer definition
    "identifier".
    In case the identifier does not exist, an exception is raised.

    :param identifier: The name of the RADIUSserver definition
    :return: A RADIUSServer Object
    """
    server_list = get_radiusservers(identifier=identifier)
    if not server_list:
        raise ConfigAdminError("The specified RADIUSServer configuration does "
                               "not exist.")
    return server_list[0]


@log_with(log)
def get_radiusservers(identifier=None, server=None):
    """
    This returns a list of all RADIUSServers matching the criterion.
    If no identifier or server is provided, it will return a list of all RADIUS
    server definitions.

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
    sql_query = RADIUSServerDB.query
    if identifier:
        sql_query = sql_query.filter(RADIUSServerDB.identifier == identifier)
    if server:
        sql_query = sql_query.filter(RADIUSServerDB.server == server)

    for row in sql_query.all():
        res.append(RADIUSServer(row))

    return res


@log_with(log)
def add_radius(identifier, server, secret, port=1812, description="",
               dictionary='/etc/privacyidea/dictionary'):
    """
    This adds a RADIUS server to the RADIUSServer database table.

    If the "identifier" already exists, the database entry is updated.

    :param identifier: The identifier or the name of the RADIUSServer
        definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no radius server
    :type identifier: basestring
    :param server: The FQDN or IP address of the RADIUS server
    :type server: basestring
    :param secret: The RADIUS secret
    :param port: the radius port
    :type port: int
    :param description: Human readable description of the RADIUS server
        definition
    :param dictionary: The RADIUS dictionary
    :return: The Id of the database object
    """
    cryptedSecret = encryptPassword(secret)
    if len(cryptedSecret) > 255:
        raise privacyIDEAError(description=_("The RADIUS secret is too long"),
                               id=2234)
    r = RADIUSServerDB(identifier=identifier, server=server, port=port,
                       secret=cryptedSecret, description=description,
                       dictionary=dictionary).save()
    return r


@log_with(log)
def delete_radius(identifier):
    """
    Delete the given server from the database
    :param identifier: The identifier/name of the server
    :return: The ID of the database entry, that was deleted
    """
    ret = -1
    radius = RADIUSServerDB.query.filter(RADIUSServerDB.identifier ==
                                         identifier).first()
    if radius:
        radius.delete()
        ret = radius.id
    return ret

