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
from sqlalchemy import Sequence, and_

from privacyidea.models import db
from privacyidea.models.token import Token, get_token_id
from privacyidea.models.config import save_config_timestamp
from privacyidea.models.utils import MethodsMixin
from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.lib.log import log_with

log = logging.getLogger(__name__)


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
    id = db.Column(db.Integer(), Sequence("machinetoken_seq"),
                   primary_key=True, nullable=False)
    token_id = db.Column(db.Integer(),
                         db.ForeignKey('token.id'))
    machineresolver_id = db.Column(db.Integer())
    machine_id = db.Column(db.Unicode(255))
    application = db.Column(db.Unicode(64))
    # This connects the machine with the token and makes the machines visible
    # in the token as "machine_list".
    token = db.relationship('Token',
                            lazy='joined',
                            backref='machine_list')

    @log_with(log)
    def __init__(self, machineresolver_id=None,
                 machineresolver=None, machine_id=None, token_id=None,
                 serial=None, application=None):

        if machineresolver_id:
            self.machineresolver_id = machineresolver_id
        elif machineresolver:
            # determine the machineresolver_id:
            self.machineresolver_id = MachineResolver.query.filter(
                MachineResolver.name == machineresolver).first().id
        if token_id:
            self.token_id = token_id
        elif serial:
            # determine token_id
            self.token_id = Token.query.filter_by(serial=serial).first().id
        self.machine_id = machine_id
        self.application = application

    def delete(self):
        ret = self.id
        db.session.query(MachineTokenOptions) \
            .filter(MachineTokenOptions.machinetoken_id == self.id) \
            .delete()
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
    id = db.Column(db.Integer(), Sequence("machtokenopt_seq"),
                   primary_key=True, nullable=False)
    machinetoken_id = db.Column(db.Integer(),
                                db.ForeignKey('machinetoken.id'))
    mt_key = db.Column(db.Unicode(64), nullable=False)
    mt_value = db.Column(db.Unicode(64), nullable=False)
    # This connects the MachineTokenOption with the MachineToken and makes the
    # options visible in the MachineToken as "option_list".
    machinetoken = db.relationship('MachineToken',
                                   lazy='joined',
                                   backref='option_list')

    def __init__(self, machinetoken_id, key, value):
        log.debug("setting {0!r} to {1!r} for MachineToken {2!s}".format(key,
                                                                         value,
                                                                         machinetoken_id))
        self.machinetoken_id = machinetoken_id
        self.mt_key = convert_column_to_unicode(key)
        self.mt_value = convert_column_to_unicode(value)

        # if the combination machinetoken_id / mt_key already exist,
        # we need to update
        c = MachineTokenOptions.query.filter_by(
            machinetoken_id=self.machinetoken_id,
            mt_key=self.mt_key).first()
        if c is None:
            # create a new one
            db.session.add(self)
        else:
            # update
            MachineTokenOptions.query.filter_by(
                machinetoken_id=self.machinetoken_id,
                mt_key=self.mt_key).update({'mt_value': self.mt_value})
        db.session.commit()


class MachineResolver(MethodsMixin, db.Model):
    """
    This model holds the definition to the machinestore.
    Machines could be located in flat files, LDAP directory or in puppet
    services or other...

    The usual MachineResolver just holds a name and a type and a reference to
    its config
    """
    __tablename__ = 'machineresolver'
    id = db.Column(db.Integer, Sequence("machineresolver_seq"),
                   primary_key=True, nullable=False)
    name = db.Column(db.Unicode(255), default="",
                     unique=True, nullable=False)
    rtype = db.Column(db.Unicode(255), default="",
                      nullable=False)
    rconfig = db.relationship('MachineResolverConfig',
                              lazy='dynamic',
                              backref='machineresolver')

    def __init__(self, name, rtype):
        self.name = name
        self.rtype = rtype

    def delete(self):
        ret = self.id
        # delete all MachineResolverConfig
        db.session.query(MachineResolverConfig) \
            .filter(MachineResolverConfig.resolver_id == ret) \
            .delete()
        # delete the MachineResolver itself
        db.session.delete(self)
        db.session.commit()
        return ret


class MachineResolverConfig(db.Model):
    """
    Each Machine Resolver can have multiple configuration entries.
    The config entries are referenced by the id of the machine resolver
    """
    __tablename__ = 'machineresolverconfig'
    id = db.Column(db.Integer, Sequence("machineresolverconf_seq"),
                   primary_key=True)
    resolver_id = db.Column(db.Integer,
                            db.ForeignKey('machineresolver.id'))
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.Unicode(2000), default='')
    Type = db.Column(db.Unicode(2000), default='')
    Description = db.Column(db.Unicode(2000), default='')
    __table_args__ = (db.UniqueConstraint('resolver_id',
                                          'Key',
                                          name='mrcix_2'),)

    def __init__(self, resolver_id=None, Key=None, Value=None, resolver=None,
                 Type="", Description=""):
        if resolver_id:
            self.resolver_id = resolver_id
        elif resolver:
            self.resolver_id = MachineResolver.query \
                .filter_by(name=resolver) \
                .first() \
                .id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type
        self.Description = Description

    def save(self):
        c = MachineResolverConfig.query.filter_by(
            resolver_id=self.resolver_id, Key=self.Key).first()
        if c is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            MachineResolverConfig.query.filter_by(
                resolver_id=self.resolver_id, Key=self.Key) \
                .update({'Value': self.Value,
                         'Type': self.Type,
                         'Description': self.Description})
            ret = c.id
        db.session.commit()
        return ret


def get_machineresolver_id(resolvername):
    """
    Return the database ID of the machine resolver
    :param resolvername:
    :return:
    """
    mr = MachineResolver.query.filter(MachineResolver.name ==
                                      resolvername).first()
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
    token_id = get_token_id(serial)
    if resolver_name:
        resolver = MachineResolver.query.filter(MachineResolver.name == resolver_name).first()
        resolver_id = resolver.id
    else:
        resolver_id = None

    mtokens = MachineToken.query.filter(and_(MachineToken.token_id == token_id,
                                             MachineToken.machineresolver_id == resolver_id,
                                             MachineToken.machine_id == machine_id,
                                             MachineToken.application == application)).all()
    if mtokens:
        for mt in mtokens:
            ret.append(mt.id)
    return ret
