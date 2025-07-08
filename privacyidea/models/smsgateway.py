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


class SMSGateway(MethodsMixin, db.Model):
    """
    This table stores the SMS Gateway definitions.
    See
    https://github.com/privacyidea/privacyidea/wiki/concept:-Delivery-Gateway

    It saves the
    * unique name
    * a description
    * the SMS provider module

    All options and parameters are saved in other tables.
    """
    __tablename__ = 'smsgateway'
    id = db.Column(db.Integer, Sequence("smsgateway_seq"), primary_key=True)
    identifier = db.Column(db.Unicode(255), nullable=False, unique=True)
    description = db.Column(db.Unicode(1024), default="")
    providermodule = db.Column(db.Unicode(1024), nullable=False)
    options = db.relationship('SMSGatewayOption',
                              lazy='dynamic',
                              backref='smsgw')

    def __init__(self, identifier, providermodule, description=None,
                 options=None, headers=None):

        options = options or {}
        headers = headers or {}
        sql = SMSGateway.query.filter_by(identifier=identifier).first()
        if sql:
            self.id = sql.id
        self.identifier = identifier
        self.providermodule = providermodule
        self.description = description
        self.save()
        # delete non-existing options in case of update
        opts = {"option": options, "header": headers}
        if sql:
            sql_opts = {"option": sql.option_dict, "header": sql.header_dict}
            for typ, vals in opts.items():
                for key in sql_opts[typ].keys():
                    # iterate through all existing options/headers
                    if key not in vals:
                        # if the option is not contained anymore
                        SMSGatewayOption.query.filter_by(gateway_id=self.id,
                                                         Key=key, Type=typ).delete()
        # add the options and headers to the SMS Gateway
        for typ, vals in opts.items():
            for k, v in vals.items():
                SMSGatewayOption(gateway_id=self.id, Key=k, Value=v, Type=typ).save()

    def save(self):
        if self.id is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
        else:
            # update
            SMSGateway.query.filter_by(id=self.id).update({
                "identifier": self.identifier,
                "providermodule": self.providermodule,
                "description": self.description
            })
            db.session.commit()
        return self.id

    def delete(self):
        """
        When deleting an SMS Gateway we also delete all the options.
        :return:
        """
        ret = self.id
        # delete all SMSGatewayOptions
        db.session.query(SMSGatewayOption) \
            .filter(SMSGatewayOption.gateway_id == ret) \
            .delete()
        # delete the SMSGateway itself
        db.session.delete(self)
        db.session.commit()
        return ret

    @property
    def option_dict(self):
        """
        Return all connected options as a dictionary

        :return: dict
        """
        res = {}
        for option in self.options:
            if option.Type == "option" or not option.Type:
                res[option.Key] = option.Value
        return res

    @property
    def header_dict(self):
        """
        Return all connected headers as a dictionary

        :return: dict
        """
        res = {}
        for option in self.options:
            if option.Type == "header":
                res[option.Key] = option.Value
        return res

    def as_dict(self):
        """
        Return the object as a dictionary

        :return: complete dict
        :rytpe: dict
        """
        d = {"id": self.id,
             "name": self.identifier,
             "providermodule": self.providermodule,
             "description": self.description,
             "options": self.option_dict,
             "headers": self.header_dict}

        return d


class SMSGatewayOption(MethodsMixin, db.Model):
    """
    This table stores the options, parameters and headers for an SMS Gateway definition.
    """
    __tablename__ = 'smsgatewayoption'
    id = db.Column(db.Integer, Sequence("smsgwoption_seq"), primary_key=True)
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.UnicodeText(), default='')
    Type = db.Column(db.Unicode(100), default='option')
    gateway_id = db.Column(db.Integer(),
                           db.ForeignKey('smsgateway.id'), index=True)
    __table_args__ = (db.UniqueConstraint('gateway_id',
                                          'Key', 'Type',
                                          name='sgix_1'),)

    def __init__(self, gateway_id, Key, Value, Type=None):

        """
        Create a new gateway_option for the gateway_id
        """
        self.gateway_id = gateway_id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type
        self.save()

    def save(self):
        # See, if there is this option or header for this gateway
        # The first match takes precedence
        go = SMSGatewayOption.query.filter_by(gateway_id=self.gateway_id,
                                              Key=self.Key, Type=self.Type).first()
        if go is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            SMSGatewayOption.query.filter_by(gateway_id=self.gateway_id,
                                             Key=self.Key, Type=self.Type
                                             ).update({'Value': self.Value,
                                                       'Type': self.Type})
            ret = go.id
        db.session.commit()
        return ret
