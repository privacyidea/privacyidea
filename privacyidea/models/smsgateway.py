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
from sqlalchemy import Sequence, Unicode, Integer, ForeignKey, UniqueConstraint, and_, select, update, delete
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin
from privacyidea.lib.utils import convert_column_to_unicode

log = logging.getLogger(__name__)


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
    id: Mapped[int] = mapped_column(Integer, Sequence("smsgateway_seq"), primary_key=True)
    identifier: Mapped[str] = mapped_column(Unicode(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Unicode(1024), default="")
    providermodule: Mapped[str] = mapped_column(Unicode(1024), nullable=False)
    options: Mapped[list["SMSGatewayOption"]] = relationship(
        'SMSGatewayOption',
        lazy='dynamic',
        back_populates='smsgw'
    )

    def __init__(self, identifier, providermodule, description=None,
                 options=None, headers=None):

        options = options or {}
        headers = headers or {}

        stmt = select(SMSGateway).filter_by(identifier=identifier)
        sql = db.session.execute(stmt).scalar_one_or_none()

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
                        delete_stmt = delete(SMSGatewayOption).where(
                            and_(
                                SMSGatewayOption.gateway_id == self.id,
                                SMSGatewayOption.Key == key,
                                SMSGatewayOption.Type == typ
                            )
                        )
                        db.session.execute(delete_stmt)
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
            update_stmt = (
                update(SMSGateway)
                .where(SMSGateway.id == self.id)
                .values(
                    identifier=self.identifier,
                    providermodule=self.providermodule,
                    description=self.description
                )
            )
            db.session.execute(update_stmt)
            db.session.commit()
        return self.id

    def delete(self):
        """
        When deleting an SMS Gateway we also delete all the options.
        """
        ret = self.id
        delete_stmt = delete(SMSGatewayOption).where(SMSGatewayOption.gateway_id == ret)
        db.session.execute(delete_stmt)
        # delete the SMSGateway itself
        db.session.delete(self)
        db.session.commit()
        return ret

    @property
    def option_dict(self):
        res = {}
        for option in self.options:
            if option.Type == "option" or not option.Type:
                res[option.Key] = option.Value
        return res

    @property
    def header_dict(self):
        res = {}
        for option in self.options:
            if option.Type == "header":
                res[option.Key] = option.Value
        return res

    def as_dict(self):
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
    id: Mapped[int] = mapped_column(Integer, Sequence("smsgwoption_seq"), primary_key=True)
    Key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Value: Mapped[str] = mapped_column(Unicode(2000), default='')
    Type: Mapped[str] = mapped_column(Unicode(100), default='option')
    gateway_id: Mapped[int] = mapped_column(Integer, ForeignKey('smsgateway.id'), index=True)

    smsgw = relationship("SMSGateway", back_populates="options")

    __table_args__ = (UniqueConstraint('gateway_id',
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
        stmt = select(SMSGatewayOption).filter(
            and_(
                SMSGatewayOption.gateway_id == self.gateway_id,
                SMSGatewayOption.Key == self.Key,
                SMSGatewayOption.Type == self.Type
            )
        )
        go = db.session.execute(stmt).scalar_one_or_none()

        if go is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            update_stmt = (
                update(SMSGatewayOption)
                .where(
                    and_(
                        SMSGatewayOption.gateway_id == self.gateway_id,
                        SMSGatewayOption.Key == self.Key,
                        SMSGatewayOption.Type == self.Type
                    )
                )
                .values(Value=self.Value, Type=self.Type)
            )
            db.session.execute(update_stmt)
            ret = go.id
        db.session.commit()
        return ret
