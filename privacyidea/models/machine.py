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
from typing import Optional

from sqlalchemy import (
    Sequence,
    and_,
    select,
    update,
    Unicode,
    Integer,
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.lib.log import log_with
from privacyidea.lib.utils import convert_column_to_unicode
# Assuming these imports and classes exist in your project
from privacyidea.models import db
from privacyidea.models.config import save_config_timestamp
from privacyidea.models.token import Token, get_token_id
from privacyidea.models.utils import MethodsMixin

log = logging.getLogger(__name__)


class MachineResolver(MethodsMixin, db.Model):
    """
    This model holds the definition to the machinestore.
    Machines could be located in flat files, LDAP directory or in puppet
    services or other...

    The usual MachineResolver just holds a name and a type and a reference to
    its config
    """
    __tablename__ = 'machineresolver'
    id: Mapped[int] = mapped_column(Integer, Sequence("machineresolver_seq"),
                                    primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(255), default="",
                                      unique=True, nullable=False)
    rtype: Mapped[str] = mapped_column(Unicode(255), default="",
                                       nullable=False)
    # The cascade option handles automatic deletion of related
    # MachineResolverConfig when a MachineResolver is deleted.
    rconfig = relationship('MachineResolverConfig',
                           lazy='dynamic',
                           backref='machineresolver',
                           cascade="all, delete-orphan")

    def __init__(self, name, rtype):
        self.name = name
        self.rtype = rtype

    def delete(self):
        ret = self.id
        # The cascade option handles the deletion of child records automatically.
        db.session.delete(self)
        db.session.commit()
        return ret


class MachineResolverConfig(db.Model):
    """
    Each Machine Resolver can have multiple configuration entries.
    The config entries are referenced by the id of the machine resolver
    """
    __tablename__ = 'machineresolverconfig'
    id: Mapped[int] = mapped_column(Integer, Sequence("machineresolverconf_seq"), primary_key=True)
    resolver_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('machineresolver.id'))
    Key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Value: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    Type: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    Description: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    __table_args__ = (UniqueConstraint('resolver_id',
                                       'Key',
                                       name='mrcix_2'),)

    def __init__(self, resolver_id=None, Key=None, Value=None, resolver=None,
                 Type="", Description=""):
        if resolver_id:
            self.resolver_id = resolver_id
        elif resolver:
            # Replaced .query with a modern select statement
            stmt = select(MachineResolver.id).filter_by(name=resolver)
            self.resolver_id = db.session.execute(stmt).scalar_one_or_none()
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type
        self.Description = Description

    def save(self):
        # Replaced .query.filter_by().first() with a modern select statement
        stmt = select(MachineResolverConfig).filter_by(
            resolver_id=self.resolver_id, Key=self.Key
        )
        c = db.session.execute(stmt).scalar_one_or_none()
        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # Replaced .query.update() with a modern update statement
            update_stmt = (
                update(MachineResolverConfig)
                .where(
                    MachineResolverConfig.resolver_id == self.resolver_id,
                    MachineResolverConfig.Key == self.Key
                )
                .values(
                    Value=self.Value,
                    Type=self.Type,
                    Description=self.Description
                )
            )
            db.session.execute(update_stmt)
            ret = c.id
        db.session.commit()
        return ret


class MachineToken(MethodsMixin, db.Model):
    """
    The MachineToken assigns a Token and an application type to a
    machine.
    The Machine is represented as the tuple of machineresolver.id and the
    machine_id.
    The machine_id is defined by the machineresolver.

    This can be an n:m mapping.
    """
    __tablename__ = 'machinetoken'
    id: Mapped[int] = mapped_column(Integer, Sequence("machinetoken_seq"),
                                    primary_key=True, nullable=False)
    token_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('token.id'))
    machineresolver_id: Mapped[Optional[int]] = mapped_column(Integer)
    machine_id: Mapped[Optional[str]] = mapped_column(Unicode(255))
    application: Mapped[Optional[str]] = mapped_column(Unicode(64))

    # This connects the machine with the token and makes the machines visible
    # in the token as "machine_list". The cascade option handles automatic
    # deletion of related MachineTokenOptions when a MachineToken is deleted.
    token = relationship('Token', lazy='joined', backref='machine_list')
    option_list = relationship('MachineTokenOptions', lazy='joined',
                               backref='machinetoken', cascade="all, delete-orphan")

    @log_with(log)
    def __init__(self, machineresolver_id=None,
                 machineresolver=None, machine_id=None, token_id=None,
                 serial=None, application=None):

        if machineresolver_id:
            self.machineresolver_id = machineresolver_id
        elif machineresolver:
            # Replaced .query with a modern select statement
            stmt = select(MachineResolver.id).filter(
                MachineResolver.name == machineresolver
            )
            self.machineresolver_id = db.session.execute(stmt).scalar_one_or_none()

        if token_id:
            self.token_id = token_id
        elif serial:
            # Replaced .query with a modern select statement
            stmt = select(Token.id).filter_by(serial=serial)
            self.token_id = db.session.execute(stmt).scalar_one_or_none()

        self.machine_id = machine_id
        self.application = application

    def delete(self):
        ret = self.id
        # The cascade="all, delete-orphan" on the relationship handles the
        # deletion of child records automatically.
        db.session.delete(self)
        save_config_timestamp()
        db.session.commit()
        return ret


class MachineTokenOptions(db.Model):
    """
    This class holds an Option for the token assigned to
    a certain client machine.
    Each Token-Clientmachine-Combination can have several
    options.
    """
    __tablename__ = 'machinetokenoptions'
    id: Mapped[int] = mapped_column(Integer, Sequence("machtokenopt_seq"),
                                    primary_key=True, nullable=False)
    machinetoken_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('machinetoken.id'))
    mt_key: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    mt_value: Mapped[str] = mapped_column(Unicode(64), nullable=False)

    def __init__(self, machinetoken_id, key, value):
        log.debug("setting {0!r} to {1!r} for MachineToken {2!s}".format(key,
                                                                         value,
                                                                         machinetoken_id))
        self.machinetoken_id = machinetoken_id
        self.mt_key = convert_column_to_unicode(key)
        self.mt_value = convert_column_to_unicode(value)

        # Replaced .query.first() and .query.update() with modern
        # select and update statements
        stmt = select(MachineTokenOptions).filter_by(
            machinetoken_id=self.machinetoken_id,
            mt_key=self.mt_key
        )
        c = db.session.execute(stmt).scalar_one_or_none()

        if c is None:
            # create a new one
            db.session.add(self)
        else:
            # update
            update_stmt = (
                update(MachineTokenOptions)
                .where(
                    and_(
                        MachineTokenOptions.machinetoken_id == self.machinetoken_id,
                        MachineTokenOptions.mt_key == self.mt_key
                    )
                )
                .values(mt_value=self.mt_value)
            )
            db.session.execute(update_stmt)
        db.session.commit()


def get_machineresolver_id(resolvername):
    """
    Return the database ID of the machine resolver
    :param resolvername:
    :return:
    """
    # Replaced .query.first() with a modern select statement
    stmt = select(MachineResolver).filter(MachineResolver.name == resolvername)
    mr = db.session.execute(stmt).scalar_one_or_none()
    return mr.id


def get_machinetoken_ids(machine_id, resolver_name, serial, application):
    """
    Returns a list of the ID in the machinetoken table

    :param machine_id: The resolverdependent machine_id
    :type machine_id: basestring
    :param resolver_name: The name of the resolver
    :type resolver_name: basestring
    :param serial: the serial number of the token
    :type serial: basestring
    :param application: The application type
    :type application: basestring
    :return: A list of IDs of the machinetoken entry
    :rtype: list of int
    """
    ret = []
    # Replaced .query with modern select statements
    token_id = get_token_id(serial)

    resolver_id = None
    if resolver_name:
        stmt = select(MachineResolver.id).filter(MachineResolver.name == resolver_name)
        resolver_id = db.session.execute(stmt).scalar_one_or_none()

    stmt = select(MachineToken).filter(
        and_(
            MachineToken.token_id == token_id,
            MachineToken.machineresolver_id == resolver_id,
            MachineToken.machine_id == machine_id,
            MachineToken.application == application
        )
    )
    mtokens = db.session.scalars(stmt).unique().all()

    if mtokens:
        for mt in mtokens:
            ret.append(mt.id)
    return ret
