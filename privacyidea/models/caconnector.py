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
from privacyidea.models.config import save_config_timestamp, TimestampMethodsMixin
from privacyidea.lib.utils import convert_column_to_unicode


class CAConnector(TimestampMethodsMixin, db.Model):
    """
    The table "caconnector" contains the names and types of the defined
    CA connectors. Each connector has a different configuration, that is
    stored in the table "caconnectorconfig".
    """
    __tablename__ = 'caconnector'
    id = db.Column(db.Integer, Sequence("caconnector_seq"), primary_key=True,
                   nullable=False)
    name = db.Column(db.Unicode(255), default="",
                     unique=True, nullable=False)
    catype = db.Column(db.Unicode(255), default="",
                       nullable=False)
    caconfig = db.relationship('CAConnectorConfig',
                               lazy='dynamic',
                               backref='caconnector')

    def __init__(self, name, catype):
        self.name = name
        self.catype = catype

    def delete(self):
        ret = self.id
        # delete all CAConnectorConfig
        db.session.query(CAConnectorConfig) \
            .filter(CAConnectorConfig.caconnector_id == ret) \
            .delete()
        # Delete the CA itself
        db.session.delete(self)
        save_config_timestamp()
        db.session.commit()
        return ret


class CAConnectorConfig(db.Model):
    """
    Each CAConnector can have multiple configuration entries.
    Each CA Connector type can have different required config values. Therefore,
    the configuration is stored in simple key/value pairs. If the type of a
    config entry is set to "password" the value of this config entry is stored
    encrypted.

    The config entries are referenced by the id of the resolver.
    """
    __tablename__ = 'caconnectorconfig'
    id = db.Column(db.Integer, Sequence("caconfig_seq"), primary_key=True)
    caconnector_id = db.Column(db.Integer,
                               db.ForeignKey('caconnector.id'))
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.Unicode(2000), default='')
    Type = db.Column(db.Unicode(2000), default='')
    Description = db.Column(db.Unicode(2000), default='')
    __table_args__ = (db.UniqueConstraint('caconnector_id',
                                          'Key',
                                          name='ccix_2'),)

    def __init__(self, caconnector_id=None,
                 Key=None, Value=None,
                 caconnector=None,
                 Type="", Description=""):
        if caconnector_id:
            self.caconnector_id = caconnector_id
        elif caconnector:
            self.caconnector_id = CAConnector.query \
                .filter_by(name=caconnector) \
                .first() \
                .id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type
        self.Description = Description

    def save(self):
        c = CAConnectorConfig.query.filter_by(caconnector_id=self.caconnector_id,
                                              Key=self.Key).first()
        save_config_timestamp()
        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            CAConnectorConfig.query.filter_by(caconnector_id=self.caconnector_id,
                                              Key=self.Key
                                              ).update({'Value': self.Value,
                                                        'Type': self.Type,
                                                        'Description': self.Description})
            ret = c.id
        db.session.commit()
        return ret
