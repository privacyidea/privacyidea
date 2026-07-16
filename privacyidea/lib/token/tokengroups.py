# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assigning tokens to token groups."""

import logging

from sqlalchemy import select

from privacyidea.lib import _
from privacyidea.lib.error import (ResourceNotFoundError)
from privacyidea.models import (db, TokenTokengroup, Tokengroup)

from privacyidea.lib.token.query import get_one_token

log = logging.getLogger(__name__)


def set_tokengroups(serial: str, tokengroups: list[str] | None = None, add: bool = False) -> None:
    """
    Set a list of tokengroups for one token

    :param serial: The serial of the token
    :param tokengroups: The list of tokengroups (names)
    :param add: Whether the list of tokengropus should be added
    :return:
    """
    tokengroups = tokengroups or []

    tokenobject = get_one_token(serial=serial)
    tokenobject.set_tokengroups(tokengroups, add=add)


def assign_tokengroup(serial: str, tokengroup: str | None = None, tokengroup_id: int | None = None) -> bool:
    """
    Assign a new tokengroup to a token

    :param serial: The serial number of the token
    :param tokengroup: The name of the tokengroup
    :param tokengroup_id: alternatively the id of the tokengroup
    :return: True
    """
    tokenobject = get_one_token(serial=serial)
    return tokenobject.add_tokengroup(tokengroup, tokengroup_id)


def unassign_tokengroup(serial: str, tokengroup: str | None = None, tokengroup_id: int | None = None) -> bool:
    """
    Removes a tokengroup from a token

    :param serial: The serial number of the token
    :param tokengroup: The name of the tokengroup
    :param tokengroup_id: alternatively the id of the tokengroup
    :return: True
    """
    tokenobject = get_one_token(serial=serial)
    return tokenobject.delete_tokengroup(tokengroup, tokengroup_id)


def list_tokengroups(tokengroup: str | None = None) -> list[TokenTokengroup]:
    """
    Return a list of tokens that are assigned to a certain tokengroup
    If no tokengroup is specified, all groups/tokens are returned.

    :param tokengroup. The name of the token group
    :return:
    """
    tg = None
    session = db.session
    if tokengroup:
        stmt = select(Tokengroup).where(Tokengroup.name == tokengroup)
        tg = session.execute(stmt).scalar_one_or_none()

    if tg:
        stmt = select(TokenTokengroup).where(TokenTokengroup.tokengroup_id == tg.id)
        tgs = session.scalars(stmt).unique().all()
    else:
        stmt = select(TokenTokengroup)
        tgs = session.scalars(stmt).unique().all()
    return tgs
