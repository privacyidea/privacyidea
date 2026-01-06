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

from sqlalchemy import select

from privacyidea.lib.error import privacyIDEAError, ResourceNotFoundError
from privacyidea.models import Tokengroup, db

log = logging.getLogger(__name__)

ENCODING = "utf-8"


def set_tokengroup(name: str, description: str = None) -> int:
    """
    Create a new token group or updates the description for an existing one.

    :param name: Name of the token group
    :param description: Description of the token group
    :return: ID of the created or updated token group
    """
    statement = select(Tokengroup).where(Tokengroup.name == name)
    token_group = db.session.execute(statement).scalar_one_or_none()
    if token_group:
        # Update existing group
        token_group.Description = description
        return token_group.save()
    else:
        return Tokengroup(name, description).save()


def delete_tokengroup(name: str = None, tokengroup_id: int = None):
    """
    Delete the tokengroup given by either name or id.
    If there are still tokens assigned to the tokengroup, the function fails
    with an error.

    :param name: Name of the tokengroup to be deleted
    :param tokengroup_id: ID of the tokengroup to be deleted
    """
    if not name and not tokengroup_id:
        raise ResourceNotFoundError("You need to specify either a tokengroup ID or a name.")

    statement = select(Tokengroup)
    if name:
        statement = statement.where(Tokengroup.name == name)
    if tokengroup_id:
        statement = statement.where(Tokengroup.id == tokengroup_id)

    token_group = db.session.execute(statement).scalar()
    if not token_group:
        error_msg = "Token group "
        if name:
            error_msg += f"with name '{name}' "
        if tokengroup_id:
            error_msg += f"with ID '{tokengroup_id}' "
        error_msg += "does not exist."
        raise ResourceNotFoundError(error_msg)

    if len(token_group.token_list) > 0:
        raise privacyIDEAError(
            "The token group with name '{0!s}' still has {1:d} tokens assigned.".format(token_group.name,
                                                                                        len(token_group.token_list)))

    db.session.delete(token_group)
    db.session.commit()


def get_tokengroups(name: str = None, id: int = None) -> list[Tokengroup]:
    """
    Returns a list of token groups. You can filter by name or id. If no filter is given, all token groups are returned.
    """
    statement = select(Tokengroup)
    if name:
        statement = statement.where(Tokengroup.name == name)
    if id:
        statement = statement.where(Tokengroup.id == id)
    return db.session.execute(statement).scalars().all()
