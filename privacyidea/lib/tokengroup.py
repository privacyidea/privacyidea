# -*- coding: utf-8 -*-
#  2022-09-28 Cornelius Kölbel <cornelius.koelbel@netknights.it>
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
This module contains the functions to manage tokengroups.
It depends on the models
"""

import traceback
import string
import datetime
import os
import logging

from privacyidea.lib.error import privacyIDEAError
from privacyidea.models import TokenTokengroup, Tokengroup, db

log = logging.getLogger(__name__)

ENCODING = "utf-8"


def set_tokengroup(name, description=None):
    return Tokengroup(name, description).save()


def delete_tokengroup(name=None, id=None):
    if not name and not id:
        raise privacyIDEAError("You need to specify either a tokengroup ID or a name.")

    delete_id = id
    if (name):
        tokengroup_id = Tokengroup.query.filter(Tokengroup.name == name).all()
        delete_id =tokengroup_id[0].id

    tokengroup_count = db.session.query(TokenTokengroup)\
        .filter(TokenTokengroup.tokengroup_id == delete_id).count();
    if ( tokengroup_count > 0 ):
        raise privacyIDEAError("This tokengroup is " + str(tokengroup_count) + " times assigned.")

    Tokengroup.query.filter_by(id=delete_id).delete()
    db.session.commit()


def get_tokengroups(name=None, id=None):
    query = Tokengroup.query
    if name:
        query = query.filter(Tokengroup.name == name)
    if id:
        query = query.filter(Tokengroup.id == id)
    return query.all()
