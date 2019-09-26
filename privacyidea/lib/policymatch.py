# -*- coding: utf-8 -*-
#
#  2019-07-19 Friedrich Weber <friedrich.weber@netknights.it>
#             Add a high-level API for policy matching
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
High-level API for matching policies. This module provides a class ``Match``,
which encapsulates a policy matching operation. ``Match`` objects are created
using several classmethods which represent different flavors of matching
operations: For example, there are classmethods for matching policies based
on a user realm, or based on a user object.

In addition, the ``Match`` object performs postprocessing of matching results,
e.g. by extracing action values from the matching policies. Finally, it writes
the matched policies to the audit log (though this can be disabled).

This module is tested in ``test_lib_policymatch.py``.
"""

from privacyidea.lib.user import User
from privacyidea.lib.error import ServerError
from privacyidea.lib.policy import SCOPE


class MatchingError(ServerError):
    pass


class Match(object):
    """
    This class provides a high-level API for policy matching. It should not be instantiated directly. Instead,
    code should use one of the provided classmethods to construct a ``Match`` object. See the respective
    classmethods for details.

    A ``Match`` object encapsulates a policy matching operation, i.e. a call to ``PolicyClass.match_policies``.
    In order to retrieve the matching policies, one should use one of ``policies()``, ``action_values()`` and ``any()``.
    By default, these functions write the matched policies to the audit log. This behavior can be explicitly disabled.

    Every classmethod expects a so-called "context object" as its first argument.
    The context object implements the following attributes:
     * ``audit_object``: an ``Audit`` object which is used to write the used policies to the audit log.
                         In case False is passed for ``write_to_audit_log``, the audit object may be None.
     * ``policy_object``: a ``PolicyClass`` object that is used to retrieve the matching policies.
     * ``client_ip``: the IP of the current client, as a string
     * ``logged_in_user``: a dictionary with keys "username", "realm", "role" that describes the
                           currently logged-in (managing) user
    In our case, this context object is usually the ``flask.g`` object.
    """
    def __init__(self, g, **kwargs):
        self._g = g
        self._match_kwargs = kwargs

    def policies(self, write_to_audit_log=True):
        """
        Return a list of policies. The list is sorted by priority, which means that prioritized policies appear first.
        :param write_to_audit_log: If True, write the list of matching policies to the audit log
        :return: a list of policy dictionaries
        :rtype: list
        """
        if write_to_audit_log:
            audit_data = self._g.audit_object.audit_data
        else:
            audit_data = None
        return self._g.policy_object.match_policies(audit_data=audit_data,
                                                    **self._match_kwargs)

    def any(self, write_to_audit_log=True):
        """
        Return True if at least one policy matches.
        :param write_to_audit_log: If True, write the list of matching policies to the audit log
        :return: True or False
        """
        return bool(self.policies(write_to_audit_log=write_to_audit_log))

    def action_values(self, unique, allow_white_space_in_action=False, write_to_audit_log=True):
        """
        Return a dictionary of action values extracted from the matching policies.
        The dictionary maps each action value to a list of policies which define this action value.
        :param unique: If True, return only the prioritized action value.
                       See ``PolicyClass.get_action_values`` for details.
        :param allow_white_space_in_action: If True, allow whitespace in action values.
                       See ``PolicyClass.get_action_values`` for details.
        :param write_to_audit_log: If True, augment the audit log with the names of all
                       policies whose action values are returned
        :rtype: dict
        """
        policies = self.policies(write_to_audit_log=False)
        action_values = self._g.policy_object.extract_action_values(policies,
                                                                    self._match_kwargs['action'],
                                                                    unique=unique,
                                                                    allow_white_space_in_action=
                                                                    allow_white_space_in_action)
        if write_to_audit_log:
            for action_value, policy_names in action_values.items():
                for p_name in policy_names:
                    self._g.audit_object.audit_data.setdefault("policies", []).append(p_name)
        return action_values

    @classmethod
    def action_only(cls, g, scope, action):
        """
        Match active policies solely based on a scope and an action, which may also be None.
        The client IP is matched implicitly.
        :param g: context object
        :param scope: the policy scope. SCOPE.ADMIN cannot be passed, ``admin`` must be used instead.
        :param action: the policy action, or None
        :rtype: ``Match``
        """
        if scope == SCOPE.ADMIN:
            raise MatchingError("Match.action_only cannot be used for policies with scope ADMIN")
        return cls(g, name=None, scope=scope, realm=None, active=True,
                   resolver=None, user=None, user_object=None,
                   client=g.client_ip, action=action, adminrealm=None, time=None,
                   sort_by_priority=True)

    @classmethod
    def realm(cls, g, scope, action, realm):
        """
        Match active policies with a scope, an action and a user realm.
        The client IP is matched implicitly.
        :param g: context object
        :param scope: the policy scope. SCOPE.ADMIN cannot be passed, ``admin`` must be used instead.
        :param action: the policy action
        :param realm: the realm to match
        :rtype: ``Match``
        """
        if scope == SCOPE.ADMIN:
            raise MatchingError("Match.realm cannot be used for policies with scope ADMIN")
        return cls(g, name=None, scope=scope, realm=realm, active=True,
                   resolver=None, user=None, user_object=None,
                   client=g.client_ip, action=action, adminrealm=None, time=None,
                   sort_by_priority=True)

    @classmethod
    def user(cls, g, scope, action, user_object):
        """
        Match active policies with a scope, an action and a user object (which may be None).
        The client IP is matched implicitly.
        :param g: context object
        :param scope: the policy scope. SCOPE.ADMIN cannot be passed, ``admin`` must be used instead.
        :param action: the policy action
        :param user_object: the user object to match. Might also be None, which means that the policy
                     attributes ``user``, ``realm`` and ``resolver`` are ignored.
        :type user_object: User or None
        :rtype: ``Match``
        """
        if scope == SCOPE.ADMIN:
            raise MatchingError("Match.user cannot be used for policies with scope ADMIN")
        if not (user_object is None or isinstance(user_object, User)):
            raise MatchingError("Invalid user")
        # Username, realm and resolver will be extracted from the user_object parameter
        return cls(g, name=None, scope=scope, realm=None, active=True,
                   resolver=None, user=None, user_object=user_object,
                   client=g.client_ip, action=action, adminrealm=None, time=None,
                   sort_by_priority=True)

    @classmethod
    def admin(cls, g, action, realm):
        """
        Match admin policies with an action and, optionally, a realm.
        Assumes that the currently logged-in user is an admin, and throws an error otherwise.
        Policies will be matched against the admin's username and adminrealm,
        and optionally also the provided user realm.
        The client IP is matched implicitly.
        :param g: context object
        :param action: the policy action
        :param realm: the user realm against which policies should be matched. Can be None.
        :type realm: str or None
        :rtype: ``Match``
        """
        username = g.logged_in_user["username"]
        adminrealm = g.logged_in_user["realm"]
        from privacyidea.lib.auth import ROLE
        if g.logged_in_user["role"] != ROLE.ADMIN:
            raise MatchingError("Policies with scope ADMIN can only be retrieved by admins")
        return cls(g, name=None, scope=SCOPE.ADMIN, realm=realm, active=True,
                   resolver=None, user=username, user_object=None,
                   client=g.client_ip, action=action, adminrealm=adminrealm, time=None,
                   sort_by_priority=True)

    @classmethod
    def admin_or_user(cls, g, action, realm):
        """
        Depending on the role of the currently logged-in user, match either scope=ADMIN or scope=USER policies.
        If the currently logged-in user is an admin, match policies against the username, adminrealm
        and the given user realm.
        If the currently logged-in user is a user, match policies against the username and the given realm.
        The client IP is matched implicitly.
        :param g: context object
        :param action: the policy action
        :param realm: the given realm
        :rtype: ``Match``
        """
        from privacyidea.lib.auth import ROLE
        if g.logged_in_user["role"] == ROLE.ADMIN:
            scope = SCOPE.ADMIN
            username = g.logged_in_user["username"]
            adminrealm = g.logged_in_user["realm"]
        elif g.logged_in_user["role"] == ROLE.USER:
            scope = SCOPE.USER
            username = g.logged_in_user["username"]
            adminrealm = None
        else:
            raise MatchingError("Unknown role")
        return cls(g, name=None, scope=scope, realm=realm, active=True,
                   resolver=None, user=username, user_object=None,
                   client=g.client_ip, action=action, adminrealm=adminrealm, time=None,
                   sort_by_priority=True)