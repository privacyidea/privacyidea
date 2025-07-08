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

from sqlalchemy import Sequence

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin
from privacyidea.lib.utils import convert_column_to_unicode


class CustomUserAttribute(MethodsMixin, db.Model):
    """
    The table "customuserattribute" is used to store additional, custom attributes
    for users.

    A user is identified by the user_id,  the resolver_id and the realm_id.

    The additional attributes are stored in Key and Value.
    The Type can hold extra information like e.g. an encrypted value / password.

    Note: Since the users are external, i.e. no objects in this database,
          there is no logic reference on a database level.
          Since users could be deleted from user stores
          without privacyIDEA realizing that, this table could pile up
          with remnants of attributes.
    """
    __tablename__ = 'customuserattribute'
    id = db.Column(db.Integer(), Sequence("customuserattribute_seq"), primary_key=True)
    user_id = db.Column(db.Unicode(320), default='', index=True)
    resolver = db.Column(db.Unicode(120), default='', index=True)
    realm_id = db.Column(db.Integer(), db.ForeignKey('realm.id'))
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.UnicodeText(), default='')
    Type = db.Column(db.Unicode(100), default='')

    def __init__(self, user_id, resolver, realm_id, Key, Value, Type=None):
        """
        Create a new customuserattribute for a user tuple
        """
        self.user_id = user_id
        self.resolver = resolver
        self.realm_id = realm_id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type

    def save(self, persistent=True):
        ua = CustomUserAttribute.query.filter_by(user_id=self.user_id,
                                                 resolver=self.resolver,
                                                 realm_id=self.realm_id,
                                                 Key=self.Key).first()
        if ua is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            CustomUserAttribute.query.filter_by(user_id=self.user_id,
                                                resolver=self.resolver,
                                                realm_id=self.realm_id,
                                                Key=self.Key
                                                ).update({'Value': self.Value, 'Type': self.Type})
            ret = ua.id
        if persistent:
            db.session.commit()
        return ret
