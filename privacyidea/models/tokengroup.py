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

from sqlalchemy import Unicode, Integer, UniqueConstraint, select, update, delete
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
    Description: Mapped[str] = mapped_column(Unicode(2000), default='')

    # Define relationship back to TokenTokengroup for deletion cascade
    tokens: Mapped[List['TokenTokengroup']] = relationship(back_populates='tokengroup', cascade="all, delete-orphan")

    @log_with(log)
    def __init__(self, groupname: str, description: Optional[str] = None):
        self.name = groupname
        self.Description = description

    def delete(self):
        ret = self.id
        # SQLAlchemy's cascade="all, delete-orphan" handles the deletion of TokenTokengroup entries.
        db.session.delete(self)
        save_config_timestamp()
        db.session.commit()
        return ret

    def save(self):
        stmt = select(Tokengroup).filter_by(name=self.name)
        ti = db.session.execute(stmt).scalar_one_or_none()
        if ti is None:
            return TimestampMethodsMixin.save(self)
        else:
            # update
            update_stmt = (
                update(Tokengroup)
                .where(Tokengroup.id == ti.id)
                .values(Description=self.Description)
            )
            db.session.execute(update_stmt)
            ret = ti.id
            db.session.commit()
        return ret


class TokenTokengroup(TimestampMethodsMixin, db.Model):
    """
    This table stores the assignment of tokens to tokengroups.
    A token can be assigned to several different token groups.
    """
    __tablename__ = 'tokentokengroup'
    __table_args__ = (UniqueConstraint('token_id', 'tokengroup_id', name='ttgix_2'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('token.id'))
    tokengroup_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('tokengroup.id'))

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
        if tokengroupname:
            stmt = select(Tokengroup).filter_by(name=tokengroupname)
            r = db.session.execute(stmt).scalar_one_or_none()
            if not r:
                raise Exception("tokengroup does not exist")
            self.tokengroup_id = r.id
        elif tokengroup_id:
            self.tokengroup_id = tokengroup_id
        self.token_id = token_id

    def save(self):
        """
        We only save this, if it does not exist, yet.
        """
        stmt = select(TokenTokengroup).filter_by(tokengroup_id=self.tokengroup_id, token_id=self.token_id)
        tr = db.session.execute(stmt).scalar_one_or_none()
        if tr is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            if get_app_config_value(SAFE_STORE, False):
                tr = db.session.execute(stmt).scalar_one_or_none()
                ret = tr.id if tr else self.id
            else:
                ret = self.id
        else:
            ret = self.id
        return ret
