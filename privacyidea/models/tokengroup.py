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
from sqlalchemy import Sequence

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
    id = db.Column(db.Integer, Sequence("tokengroup_seq"), primary_key=True,
                   nullable=False)
    name = db.Column(db.Unicode(255), default='',
                     unique=True, nullable=False)
    Description = db.Column(db.Unicode(2000), default='')

    @log_with(log)
    def __init__(self, groupname, description=None):
        self.name = groupname
        self.Description = description

    def delete(self):
        ret = self.id
        # delete all TokenTokenGroup
        db.session.query(TokenTokengroup) \
            .filter(TokenTokengroup.tokengroup_id == ret) \
            .delete()
        # delete the tokengroup
        db.session.delete(self)
        save_config_timestamp()
        db.session.commit()
        return ret

    def save(self):
        ti_func = Tokengroup.query.filter_by(name=self.name).first
        ti = ti_func()
        if ti is None:
            return TimestampMethodsMixin.save(self)
        else:
            # update
            Tokengroup.query.filter_by(id=ti.id).update({'Description': self.Description})
            ret = ti.id
            db.session.commit()
        return ret


class TokenTokengroup(TimestampMethodsMixin, db.Model):
    """
    This table stores the assignment of tokens to tokengroups.
    A token can be assigned to several different token groups.
    """
    __tablename__ = 'tokentokengroup'
    __table_args__ = (db.UniqueConstraint('token_id',
                                          'tokengroup_id',
                                          name='ttgix_2'),)
    id = db.Column(db.Integer(), Sequence("tokentokengroup_seq"), primary_key=True)
    token_id = db.Column(db.Integer(),
                         db.ForeignKey('token.id'))
    tokengroup_id = db.Column(db.Integer(),
                              db.ForeignKey('tokengroup.id'))
    # This creates an attribute "tokengroup_list" in the Token object
    token = db.relationship('Token',
                            lazy='joined',
                            backref='tokengroup_list')
    # This creates an attribute "token_list" in the Tokengroup object
    tokengroup = db.relationship('Tokengroup',
                                 lazy='joined',
                                 backref='token_list')

    def __init__(self, tokengroup_id=0, token_id=0, tokengroupname=None):
        """
        Create a new TokenTokengroup assignment
        :param tokengroup_id: The id of the token group
        :param tokengroupname: the name of the tokengroup
        :param token_id: The id of the token
        """
        if tokengroupname:
            r = Tokengroup.query.filter_by(name=tokengroupname).first()
            if not r:
                raise Exception("tokengroup does not exist")
            self.tokengroup_id = r.id
        if tokengroup_id:
            self.tokengroup_id = tokengroup_id
        self.token_id = token_id

    def save(self):
        """
        We only save this, if it does not exist, yet.
        """
        tr_func = TokenTokengroup.query.filter_by(tokengroup_id=self.tokengroup_id,
                                                  token_id=self.token_id).first
        tr = tr_func()
        if tr is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            if get_app_config_value(SAFE_STORE, False):
                tr = tr_func()
                ret = tr.id
            else:
                ret = self.id
        else:
            ret = self.id
        return ret
