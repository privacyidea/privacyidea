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

import re
from datetime import datetime
from sqlalchemy import Sequence

from privacyidea.models import db
from privacyidea.models.config import TimestampMethodsMixin
from privacyidea.models.utils import MethodsMixin
from privacyidea.lib.utils import is_true


class Policy(TimestampMethodsMixin, db.Model):
    """
    The policy table contains the policy definitions.

    The Policies control the behaviour in the scopes
     * enrollment
     * authentication
     * authorization
     * administration
     * user actions
     * webui
    """
    __tablename__ = "policy"
    id = db.Column(db.Integer, Sequence("policy_seq"), primary_key=True)
    active = db.Column(db.Boolean, default=True)
    check_all_resolvers = db.Column(db.Boolean, default=False)
    name = db.Column(db.Unicode(64), unique=True, nullable=False)
    user_case_insensitive = db.Column(db.Boolean, default=False)
    scope = db.Column(db.Unicode(32), nullable=False)
    action = db.Column(db.Text, default="")
    realm = db.Column(db.Unicode(256), default="")
    adminrealm = db.Column(db.Unicode(256), default="")
    adminuser = db.Column(db.Unicode(256), default="")
    resolver = db.Column(db.Unicode(256), default="")
    pinode = db.Column(db.Unicode(256), default="")
    user = db.Column(db.Unicode(256), default="")
    client = db.Column(db.Unicode(256), default="")
    time = db.Column(db.Unicode(64), default="")
    user_agents = db.Column(db.Unicode(256), default="")
    # If there are multiple matching policies, choose the one
    # with the lowest priority number. We choose 1 to be the default priority.
    priority = db.Column(db.Integer, default=1, nullable=False)
    conditions = db.relationship("PolicyCondition",
                                 lazy="joined",
                                 backref="policy",
                                 order_by="PolicyCondition.id",
                                 # With these cascade options, we ensure that whenever a Policy object is added
                                 # to a session, its conditions are also added to the session (save-update, merge).
                                 # Likewise, whenever a Policy object is deleted, its conditions are also
                                 # deleted (delete). Conditions without a policy are deleted (delete-orphan).
                                 cascade="save-update, merge, delete, delete-orphan")
    description = db.relationship('PolicyDescription', backref='policy',
                                  cascade="save-update, merge, delete, delete-orphan")

    def __init__(self, name,
                 active=True, scope="", action="", realm="", adminrealm="", adminuser="",
                 resolver="", user="", client="", time="", pinode="", priority=1,
                 check_all_resolvers=False, conditions=None, user_case_insensitive=False, user_agents=None):
        if isinstance(active, str):
            active = is_true(active.lower())
        self.name = name

        self.user_case_insensitive = user_case_insensitive
        self.action = action
        self.scope = scope
        self.active = active
        self.realm = realm
        self.adminrealm = adminrealm
        self.adminuser = adminuser
        self.resolver = resolver
        self.pinode = pinode
        self.user = user
        self.client = client
        self.time = time
        self.priority = priority
        self.check_all_resolvers = check_all_resolvers
        self.user_agents = user_agents
        self.conditions = []

    def get_conditions_tuples(self):
        """
        :return: a list of 5-tuples (section, key, comparator, value, active).
        """
        return [condition.as_tuple() for condition in self.conditions]

    def get_policy_description(self):
        """

        """
        if self.description:
            ret = self.description[0].description
        else:
            ret = None
        return ret

    @staticmethod
    def _split_string(value):
        """
        Split the value at the "," and returns an array.
        If value is empty, it returns an empty array.
        The normal split would return an array with an empty string.

        :param value: The string to be split
        :type value: basestring
        :return: list
        """
        ret = [r.strip() for r in (value or "").split(",")]
        if ret == ['']:
            ret = []
        return ret

    def get(self, key=None):
        """
        Either returns the complete policy entry or a single value
        :param key: return the value for this key
        :type key: string
        :return: complete dict or single value
        :rytpe: dict or value
        """
        d = {"name": self.name,
             "user_case_insensitive": self.user_case_insensitive,
             "active": self.active,
             "scope": self.scope,
             "realm": self._split_string(self.realm),
             "adminrealm": self._split_string(self.adminrealm),
             "adminuser": self._split_string(self.adminuser),
             "resolver": self._split_string(self.resolver),
             "pinode": self._split_string(self.pinode),
             "check_all_resolvers": self.check_all_resolvers,
             "user": self._split_string(self.user),
             "client": self._split_string(self.client),
             "time": self.time,
             "conditions": self.get_conditions_tuples(),
             "priority": self.priority,
             "description": self.get_policy_description(),
             "user_agents": self._split_string(self.user_agents)}
        action_list = [x.strip().split("=", 1) for x in re.split(r'(?<!\\),', self.action or "")]
        action_dict = {}
        for a in action_list:
            if len(a) > 1:
                action_dict[a[0]] = a[1]
            else:
                action_dict[a[0]] = True
        d["action"] = action_dict
        if key:
            ret = d.get(key)
        else:
            ret = d
        return ret


class PolicyCondition(MethodsMixin, db.Model):
    __tablename__ = "policycondition"

    id = db.Column(db.Integer, Sequence("policycondition_seq"), primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policy.id'), nullable=False)
    section = db.Column(db.Unicode(255), nullable=False)
    # We use upper-case "Key" and "Value" to prevent conflicts with databases
    # that do not support "key" or "value" as column names
    Key = db.Column(db.Unicode(255), nullable=False)
    comparator = db.Column(db.Unicode(255), nullable=False, default='equals')
    Value = db.Column(db.Unicode(2000), nullable=False, default='')
    active = db.Column(db.Boolean, nullable=False, default=True)
    handle_missing_data = db.Column(db.Unicode(255), nullable=True)

    def __init__(self, section, Key, comparator, Value, active=True, handle_missing_data=None):
        self.section = section
        self.Key = Key
        self.comparator = comparator
        self.Value = Value
        self.active = active
        self.handle_missing_data = handle_missing_data

    def as_tuple(self):
        """
        :return: the condition as a tuple (section, key, comparator, value, active, handle_missing_data)
        """
        return self.section, self.Key, self.comparator, self.Value, self.active, self.handle_missing_data


class PolicyDescription(TimestampMethodsMixin, db.Model):
    """
    The description table is used to store the description of policy
    """
    __tablename__ = 'description'
    id = db.Column(db.Integer, Sequence("description_seq"), primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey('policy.id'), nullable=False)
    object_type = db.Column(db.Unicode(64), unique=False, nullable=False)
    last_update = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.UnicodeText())

    def __init__(self, object_id, name="", object_type="", description=""):
        self.name = name
        self.object_type = object_type
        self.object_id = object_id
        self.last_update = datetime.now()
        self.description = description
