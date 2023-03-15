# -*- coding: utf-8 -*-
#  2023-03-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Init
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
##
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
"""
This module contains the functions to manage service ids.
It depends on the models.py
"""

import logging

from privacyidea.lib.utils import fetch_one_resource
from privacyidea.lib.error import privacyIDEAError, ResourceNotFoundError
from privacyidea.models import Serviceid, db

log = logging.getLogger(__name__)

ENCODING = "utf-8"


def set_serviceid(name, description=None):
    return Serviceid(name, description).save()


def delete_serviceid(name=None, sid=None):
    """
    Delete the serviceid given by either name or id.
    If there are still applications with this serviceid, the function fails
    with an error.

    :param name: Name of the serviceid to be deleted
    :type name: str
    :param sid: ID of the serviceid to delete
    :type sid: int
    """
    si = None
    if name:
        si = fetch_one_resource(Serviceid, name=name)
    if sid:
        if si:
            if si.id != sid:
                raise privacyIDEAError('ID of the serviceid with name {0!s} does not '
                                       'match given ID ({1:d}).'.format(name, sid))
        else:
            si = fetch_one_resource(Serviceid, id=sid)
    if si:
        # TODO: Implement check for used serviceids
        si.delete()
        db.session.commit()
    else:
        raise ResourceNotFoundError("You need to specify either a ID or name of a serviceid.")


def get_serviceids(name=None, id=None):
    query = Serviceid.query
    if name:
        query = query.filter(Serviceid.name == name)
    if id:
        query = query.filter(Serviceid.id == id)
    return query.all()
