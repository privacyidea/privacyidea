# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
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
import logging
from typing import List, Optional

from sqlalchemy import Unicode, Integer, UniqueConstraint, select, update, delete, Sequence
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.models import db
from privacyidea.models.config import (TimestampMethodsMixin,
                                       save_config_timestamp, SAFE_STORE)
from privacyidea.lib.log import log_with
from privacyidea.lib.framework import get_app_config_value

log = logging.getLogger(__name__)


class Tokengroup(TimestampMethodsMixin, db.Model):
    """
    The tokengroup table contains the definition of available token groups.
    A token can then be assigned to several of these tokengroups.
    """
    __tablename__ = 'tokengroup'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(255), default='', unique=True, nullable=False)
    Description: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')

    # Define relationship back to TokenTokengroup for deletion cascade
    tokens: Mapped[List['TokenTokengroup']] = relationship(back_populates='tokengroup', cascade="all, delete-orphan")

    @log_with(log)
    def __init__(self, groupname: str, description: Optional[str] = None):
        self.name = groupname
        self.Description = description


class TokenTokengroup(TimestampMethodsMixin, db.Model):
    """
    This table stores the assignment of tokens to tokengroups.
    A token can be assigned to several different token groups.
    """
    __tablename__ = 'tokentokengroup'
    __table_args__ = (UniqueConstraint('token_id', 'tokengroup_id', name='ttgix_2'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[Optional[int]] = mapped_column(Integer, db.ForeignKey('token.id'))
    tokengroup_id: Mapped[Optional[int]] = mapped_column(Integer, db.ForeignKey('tokengroup.id'))

    # Define relationships with modern syntax
    token: Mapped['Token'] = relationship(lazy='joined', backref='tokengroup_list')
    tokengroup: Mapped['Tokengroup'] = relationship(back_populates='tokens', lazy='joined',
                                                  single_parent=True)

    def __init__(self, tokengroup_id: int = 0, token_id: int = 0, tokengroupname: Optional[str] = None):
        """
        Create a new TokenTokengroup assignment
        :param tokengroup_id: The id of the token group
        :param tokengroupname: the name of the tokengroup
        :param token_id: The id of the token
        """
        if tokengroup_id:
            self.tokengroup_id = tokengroup_id
        elif tokengroupname:
            stmt = select(Tokengroup).filter_by(name=tokengroupname)
            group = db.session.execute(stmt).scalar_one_or_none()
            if not group:
                raise Exception("tokengroup does not exist")
            self.tokengroup_id = group.id
        self.token_id = token_id
