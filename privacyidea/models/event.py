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
from privacyidea.models.config import save_config_timestamp
from privacyidea.lib.utils import convert_column_to_unicode


class EventHandler(MethodsMixin, db.Model):
    """
    This model holds the list of defined events and actions to this events.
    A handler module can be bound to an event with the corresponding
    condition and action.
    """
    __tablename__ = 'eventhandler'
    id = db.Column(db.Integer, Sequence("eventhandler_seq"), primary_key=True,
                   nullable=False)
    # in fact the name is a description
    name = db.Column(db.Unicode(64), unique=False, nullable=True)
    active = db.Column(db.Boolean, default=True)
    ordering = db.Column(db.Integer, nullable=False, default=0)
    position = db.Column(db.Unicode(10), default="post")
    # This is the name of the event in the code
    event = db.Column(db.Unicode(255), nullable=False)
    # This is the identifier of an event handler module
    handlermodule = db.Column(db.Unicode(255), nullable=False)
    condition = db.Column(db.Unicode(1024), default="")
    action = db.Column(db.Unicode(1024), default="")
    # This creates an attribute "eventhandler" in the EventHandlerOption object
    options = db.relationship('EventHandlerOption',
                              lazy='dynamic',
                              backref='eventhandler')
    # This creates an attribute "eventhandler" in the EventHandlerCondition object
    conditions = db.relationship('EventHandlerCondition',
                                 lazy='dynamic',
                                 backref='eventhandler')

    def __init__(self, name, event, handlermodule, action, condition="",
                 ordering=0, options=None, id=None, conditions=None,
                 active=True, position="post"):
        self.name = name
        self.ordering = ordering
        self.event = event
        self.handlermodule = handlermodule
        self.condition = condition
        self.action = action
        self.active = active
        self.position = position
        if id == "":
            id = None
        self.id = id
        self.save()
        # add the options to the event handler
        options = options or {}
        for k, v in options.items():
            EventHandlerOption(eventhandler_id=self.id, Key=k, Value=v).save()
        conditions = conditions or {}
        for k, v in conditions.items():
            EventHandlerCondition(eventhandler_id=self.id, Key=k, Value=v).save()
        # Delete event handler conditions, that ar not used anymore.
        ev_conditions = EventHandlerCondition.query.filter_by(
            eventhandler_id=self.id).all()
        for cond in ev_conditions:
            if cond.Key not in conditions:
                EventHandlerCondition.query.filter_by(
                    eventhandler_id=self.id, Key=cond.Key).delete()
                db.session.commit()

    def save(self):
        if self.id is None:
            # create a new one
            db.session.add(self)
        else:
            # update
            EventHandler.query.filter_by(id=self.id).update({
                "ordering": self.ordering or 0,
                "position": self.position or "post",
                "event": self.event,
                "active": self.active,
                "name": self.name,
                "handlermodule": self.handlermodule,
                "condition": self.condition,
                "action": self.action
            })
        save_config_timestamp()
        db.session.commit()
        return self.id

    def delete(self):
        ret = self.id
        # delete all EventHandlerOptions
        db.session.query(EventHandlerOption) \
            .filter(EventHandlerOption.eventhandler_id == ret) \
            .delete()
        # delete all Conditions
        db.session.query(EventHandlerCondition) \
            .filter(EventHandlerCondition.eventhandler_id == ret) \
            .delete()
        # delete the event handler itself
        db.session.delete(self)
        save_config_timestamp()
        db.session.commit()
        return ret

    def get(self):
        """
        Return the serialized eventhandler object including the options

        :return: complete dict
        :rytpe: dict
        """
        d = {"active": self.active,
             "name": self.name,
             "handlermodule": self.handlermodule,
             "id": self.id,
             "ordering": self.ordering,
             "position": self.position or "post",
             "action": self.action,
             "condition": self.condition}
        event_list = [x.strip() for x in self.event.split(",")]
        d["event"] = event_list
        option_dict = {}
        for option in self.options:
            option_dict[option.Key] = option.Value
        d["options"] = option_dict
        condition_dict = {}
        for cond in self.conditions:
            condition_dict[cond.Key] = cond.Value
        d["conditions"] = condition_dict
        return d


class EventHandlerCondition(db.Model):
    """
    Each EventHandler entry can have additional conditions according to the
    handler module
    """
    __tablename__ = "eventhandlercondition"
    id = db.Column(db.Integer, Sequence("eventhandlercond_seq"),
                   primary_key=True)
    eventhandler_id = db.Column(db.Integer,
                                db.ForeignKey('eventhandler.id'))
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.Unicode(2000), default='')
    comparator = db.Column(db.Unicode(255), default='equal')
    __table_args__ = (db.UniqueConstraint('eventhandler_id',
                                          'Key',
                                          name='ehcix_1'),)

    def __init__(self, eventhandler_id, Key, Value, comparator="equal"):
        self.eventhandler_id = eventhandler_id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.comparator = comparator
        self.save()

    def save(self):
        ehc = EventHandlerCondition.query.filter_by(
            eventhandler_id=self.eventhandler_id, Key=self.Key).first()
        if ehc is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            EventHandlerCondition.query.filter_by(
                eventhandler_id=self.eventhandler_id, Key=self.Key) \
                .update({'Value': self.Value,
                         'comparator': self.comparator})
            ret = ehc.id
        db.session.commit()
        return ret


class EventHandlerOption(db.Model):
    """
    Each EventHandler entry can have additional options according to the
    handler module.
    """
    __tablename__ = 'eventhandleroption'
    id = db.Column(db.Integer, Sequence("eventhandleropt_seq"),
                   primary_key=True)
    eventhandler_id = db.Column(db.Integer,
                                db.ForeignKey('eventhandler.id'))
    Key = db.Column(db.Unicode(255), nullable=False)
    Value = db.Column(db.Unicode(2000), default='')
    Type = db.Column(db.Unicode(2000), default='')
    Description = db.Column(db.Unicode(2000), default='')
    __table_args__ = (db.UniqueConstraint('eventhandler_id',
                                          'Key',
                                          name='ehoix_1'),)

    def __init__(self, eventhandler_id, Key, Value, Type="", Description=""):
        self.eventhandler_id = eventhandler_id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type
        self.Description = Description
        self.save()

    def save(self):
        eho = EventHandlerOption.query.filter_by(
            eventhandler_id=self.eventhandler_id, Key=self.Key).first()
        if eho is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update
            EventHandlerOption.query.filter_by(
                eventhandler_id=self.eventhandler_id, Key=self.Key) \
                .update({'Value': self.Value,
                         'Type': self.Type,
                         'Description': self.Description})
            ret = eho.id
        db.session.commit()
        return ret
