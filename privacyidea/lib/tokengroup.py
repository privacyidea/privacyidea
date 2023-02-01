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

import logging

from privacyidea.lib.utils import fetch_one_resource
from privacyidea.lib.error import privacyIDEAError, ResourceNotFoundError
from privacyidea.models import Tokengroup, TokenTokengroup, db

log = logging.getLogger(__name__)

ENCODING = "utf-8"


def set_tokengroup(name, description=None):
    return Tokengroup(name, description).save()


def delete_tokengroup(name=None, tokengroup_id=None):
    """
    Delete the tokengroup given by either name or id.
    If there are still tokens assigned to the tokengroup, the function fails
    with an error.

    :param name: Name of the tokengroup to be deleted
    :type name: str
    :param tokengroup_id: ID of the tokengroup to be deleted
    :type tokengroup_id: int
    """
    tg = None
    if name:
        tg = fetch_one_resource(Tokengroup, name=name)
    if tokengroup_id:
        if tg:
            if tg.id != tokengroup_id:
                raise privacyIDEAError('ID of tokengroup with name {0!s} does not '
                                       'match given ID ({1:d}).'.format(name, tokengroup_id))
        else:
            tg = fetch_one_resource(Tokengroup, id=tokengroup_id)
    if tg:
        tok_count = TokenTokengroup.query.filter_by(tokengroup_id=tg.id).count()
        if tok_count > 0:
            raise privacyIDEAError('The tokengroup with name {0!s} still has '
                                   '{1:d} tokens assigned.'.format(tg.name, tok_count))
        tg.delete()
        db.session.commit()
    else:
        raise ResourceNotFoundError("You need to specify either a tokengroup ID or a name.")


def get_tokengroups(name=None, id=None):
    query = Tokengroup.query
    if name:
        query = query.filter(Tokengroup.name == name)
    if id:
        query = query.filter(Tokengroup.id == id)
    return query.all()
