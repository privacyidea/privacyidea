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
from sqlalchemy import (
    Sequence,
    Unicode,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    select,
    update,
    delete,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.lib.utils import convert_column_to_unicode
from privacyidea.models import db
from privacyidea.models.config import save_config_timestamp
from privacyidea.models.utils import MethodsMixin


class EventHandler(MethodsMixin, db.Model):
    """
    This model holds the list of defined events and actions of this eventhandler.
    A handler module can be bound to an event with the corresponding condition and action.
    """
    __tablename__ = 'eventhandler'
    id: Mapped[int] = mapped_column(Integer, Sequence("eventhandler_seq"), primary_key=True,
                                    nullable=False)
    # in fact the name is a description
    name: Mapped[str] = mapped_column(Unicode(64), unique=False, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    ordering: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[str] = mapped_column(Unicode(10), default="post")
    # This is the name of the event in the code
    event: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    # This is the identifier of an event handler module
    handlermodule: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    condition: Mapped[str] = mapped_column(Unicode(1024), default="")
    action: Mapped[str] = mapped_column(Unicode(1024), default="")

    # Relationships with cascade to automatically delete child records
    options = relationship('EventHandlerOption', lazy='dynamic', backref='eventhandler', cascade="all, delete-orphan")
    conditions = relationship('EventHandlerCondition', lazy='dynamic', backref='eventhandler',
                              cascade="all, delete-orphan")

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

        # Save the main event handler object first to get an ID
        self.save()

        # Add the options to the event handler
        options = options or {}
        for k, v in options.items():
            db.session.add(EventHandlerOption(eventhandler_id=self.id, Key=k, Value=v))

        conditions = conditions or {}
        for k, v in conditions.items():
            db.session.add(EventHandlerCondition(eventhandler_id=self.id, Key=k, Value=v))

        # Delete event handler conditions, that are not used anymore.
        # This replaces the legacy .query.delete() and ensures a bulk operation.
        delete_stmt = delete(EventHandlerCondition).where(
            EventHandlerCondition.eventhandler_id == self.id,
            EventHandlerCondition.Key.not_in(conditions.keys())
        )
        db.session.execute(delete_stmt)

        # We perform one commit at the end of the __init__ method for efficiency
        db.session.commit()

    def save(self):
        if self.id is None:
            # create a new one
            db.session.add(self)
        else:
            # update with a modern update statement
            update_stmt = (
                update(EventHandler)
                .where(EventHandler.id == self.id)
                .values(
                    ordering=self.ordering or 0,
                    position=self.position or "post",
                    event=self.event,
                    active=self.active,
                    name=self.name,
                    handlermodule=self.handlermodule,
                    condition=self.condition,
                    action=self.action
                )
            )
            db.session.execute(update_stmt)
        save_config_timestamp()
        db.session.commit()
        return self.id

    def delete(self):
        ret = self.id
        # The cascade="all, delete-orphan" on the relationships handles the deletion
        # of child records automatically. We only need to delete the parent.
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
        # Fetching all options from the relationship
        for option in self.options:
            option_dict[option.Key] = option.Value
        d["options"] = option_dict
        condition_dict = {}
        # Fetching all conditions from the relationship
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
    id: Mapped[int] = mapped_column(Integer, Sequence("eventhandlercond_seq"), primary_key=True)
    eventhandler_id: Mapped[int] = mapped_column(Integer, ForeignKey('eventhandler.id'))
    Key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Value: Mapped[str] = mapped_column(Unicode(2000), default='')
    comparator: Mapped[str] = mapped_column(Unicode(255), default='equal')
    __table_args__ = (UniqueConstraint('eventhandler_id', 'Key', name='ehcix_1'),)

    def __init__(self, eventhandler_id, Key, Value, comparator="equal"):
        self.eventhandler_id = eventhandler_id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.comparator = comparator
        # This is commented out to allow for a single commit in EventHandler.__init__
        # self.save()

    def save(self):
        # Find existing object using a modern select statement
        stmt = select(EventHandlerCondition).filter_by(eventhandler_id=self.eventhandler_id, Key=self.Key)
        ehc = db.session.execute(stmt).scalar_one_or_none()

        if ehc is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update using a modern update statement
            update_stmt = (
                update(EventHandlerCondition)
                .where(EventHandlerCondition.eventhandler_id == self.eventhandler_id,
                       EventHandlerCondition.Key == self.Key)
                .values(Value=self.Value, comparator=self.comparator)
            )
            db.session.execute(update_stmt)
            ret = ehc.id
        db.session.commit()
        return ret


class EventHandlerOption(db.Model):
    """
    Each EventHandler entry can have additional options according to the
    handler module.
    """
    __tablename__ = 'eventhandleroption'
    id: Mapped[int] = mapped_column(Integer, Sequence("eventhandleropt_seq"), primary_key=True)
    eventhandler_id: Mapped[int] = mapped_column(Integer, ForeignKey('eventhandler.id'))
    Key: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    Value: Mapped[str] = mapped_column(Unicode(2000), default='')
    Type: Mapped[str] = mapped_column(Unicode(2000), default='')
    Description: Mapped[str] = mapped_column(Unicode(2000), default='')
    __table_args__ = (UniqueConstraint('eventhandler_id', 'Key', name='ehoix_1'),)

    def __init__(self, eventhandler_id, Key, Value, Type="", Description=""):
        self.eventhandler_id = eventhandler_id
        self.Key = Key
        self.Value = convert_column_to_unicode(Value)
        self.Type = Type
        self.Description = Description
        # This is commented out to allow for a single commit in EventHandler.__init__
        # self.save()

    def save(self):
        # Find existing object using a modern select statement
        stmt = select(EventHandlerOption).filter_by(eventhandler_id=self.eventhandler_id, Key=self.Key)
        eho = db.session.execute(stmt).scalar_one_or_none()

        if eho is None:
            # create a new one
            db.session.add(self)
            db.session.commit()
            ret = self.id
        else:
            # update using a modern update statement
            update_stmt = (
                update(EventHandlerOption)
                .where(EventHandlerOption.eventhandler_id == self.eventhandler_id, EventHandlerOption.Key == self.Key)
                .values(Value=self.Value, Type=self.Type, Description=self.Description)
            )
            db.session.execute(update_stmt)
            ret = eho.id
        db.session.commit()
        return ret
