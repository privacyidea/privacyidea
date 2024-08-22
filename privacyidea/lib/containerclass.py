# (c) NetKnights GmbH 2024,  https://netknights.it
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
#
# SPDX-FileCopyrightText: 2024 Nils Behlen <nils.behlen@netknights.it>
# SPDX-FileCopyrightText: 2024 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import logging
from datetime import datetime, timezone

from typing import List

from privacyidea.lib import _
from privacyidea.lib.config import get_token_types
from privacyidea.lib.error import ParameterError, ResourceNotFoundError, TokenAdminError
from privacyidea.lib.log import log_with
from privacyidea.lib.token import create_tokenclass_object
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import (TokenContainerOwner, Realm, Token, db, TokenContainerStates,
                                TokenContainerInfo, TokenContainerRealm)

log = logging.getLogger(__name__)


class TokenContainerClass:

    @log_with(log)
    def __init__(self, db_container):
        self._db_container = db_container
        # Create the TokenClass objects from the database objects
        token_list = []
        for t in db_container.tokens:
            token_object = create_tokenclass_object(t)
            if isinstance(token_object, TokenClass):
                token_list.append(token_object)

        self.tokens = token_list

    @property
    def serial(self):
        return self._db_container.serial

    @property
    def description(self):
        return self._db_container.description

    @description.setter
    def description(self, value: str):
        if not value:
            value = ""
        self._db_container.description = value
        self._db_container.save()
        self.update_last_updated()

    @property
    def type(self):
        return self._db_container.type

    @property
    def last_seen(self):
        return self._db_container.last_seen

    def update_last_seen(self):
        """
        Updates the timestamp of the last seen field in the database.
        """
        self._db_container.last_seen = datetime.now(timezone.utc)
        self._db_container.save()

    @property
    def last_updated(self):
        return self._db_container.last_updated

    def update_last_updated(self):
        """
        Updates the timestamp of the last updated field in the database.
        """
        self._db_container.last_updated = datetime.now(timezone.utc)
        self._db_container.save()
        self.update_last_seen()

    @property
    def realms(self):
        return self._db_container.realms

    def set_realms(self, realms, add=False):
        """
        Set the realms of the container. If `add` is True, the realms will be added to the existing realms, otherwise
        the existing realms will be removed.

        :param realms: List of realm names
        :param add: False if the existing realms shall be removed, True otherwise
        :return: Dictionary in the format {realm: success}, the entry 'deleted' indicates whether existing realms were
                 deleted.
        """
        result = {}

        if not realms:
            realms = []

        # delete all container realms
        if not add:
            TokenContainerRealm.query.filter_by(container_id=self._db_container.id).delete()
            result["deleted"] = True
            self._db_container.save()

            # Check that user realms are kept
            user_realms = self._get_user_realms()
            missing_realms = list(set(user_realms).difference(realms))
            realms.extend(missing_realms)
            for realm in missing_realms:
                log.warning(
                    f"Realm {realm} can not be removed from container {self.serial} "
                    f"because a user from this realm is assigned th the container.")
        else:
            result["deleted"] = False

        for realm in realms:
            if realm:
                realm_db = Realm.query.filter_by(name=realm).first()
                if not realm_db:
                    result[realm] = False
                    log.warning(f"Realm {realm} does not exist.")
                else:
                    realm_id = realm_db.id
                    # Check if realm is already assigned to the container
                    if not TokenContainerRealm.query.filter_by(container_id=self._db_container.id,
                                                               realm_id=realm_id).first():
                        self._db_container.realms.append(realm_db)
                        result[realm] = True
                    else:
                        log.info(f"Realm {realm} is already assigned to container {self.serial}.")
                        result[realm] = False
        self._db_container.save()
        self.update_last_updated()

        return result

    def _get_user_realms(self):
        """
        Returns a list of the realms of the users that are assigned to the container.
        """
        owners = self.get_users()
        realms = [owner.realm for owner in owners]
        return realms

    def remove_token(self, serial: str):
        """
        Remove a token from the container. Raises a ResourceNotFoundError if the token does not exist.

        :param serial: Serial of the token
        :return: True if the token was successfully removed, False if the token was not found in the container
        """
        token = Token.query.filter(Token.serial == serial).first()
        if not token:
            raise ResourceNotFoundError(f"Token with serial {serial} does not exist.")
        if token not in self._db_container.tokens:
            log.info(f"Token with serial {serial} not found in container {self.serial}.")
            return False

        self._db_container.tokens.remove(token)
        self._db_container.save()
        self.tokens = [t for t in self.tokens if t.get_serial() != serial]
        self.update_last_updated()
        return True

    def add_token(self, token: TokenClass):
        """
        Add a token to the container.
        Raises a ParameterError if the token type is not supported by the container.

        :param token: TokenClass object
        :return: True if the token was successfully added, False if the token is already in the container
        """
        if token.get_type() not in self.get_supported_token_types():
            raise ParameterError(f"Token type {token.get_type()} not supported for container type {self.type}. "
                                 f"Supported types are {self.get_supported_token_types()}.")
        if token.get_serial() not in [t.get_serial() for t in self.tokens]:
            self.tokens.append(token)
            self._db_container.tokens = [t.token for t in self.tokens]
            self._db_container.save()
            self.update_last_updated()
            return True
        return False

    def get_tokens(self):
        """
        Returns the tokens of the container as a list of TokenClass objects.
        """
        return self.tokens

    def delete(self):
        """
        Deletes the container and all associated objects from the database.
        """
        return self._db_container.delete()

    def add_user(self, user: User):
        """
        Assign a user to the container.
        Raises a UserError if the user does not exist.
        Raises a TokenAdminError if the container already has an owner.

        :param user: User object
        :return: True if the user was assigned
        """
        (user_id, resolver_type, resolver_name) = user.get_user_identifiers()
        if not self._db_container.owners.first():
            TokenContainerOwner(container_id=self._db_container.id,
                                user_id=user_id,
                                resolver=resolver_name,
                                realm_id=user.realm_id).save()
            # Add user realm to container realms
            realm_db = Realm.query.filter_by(name=user.realm).first()
            self._db_container.realms.append(realm_db)
            self.update_last_updated()
            return True
        log.info(f"Container {self.serial} already has an owner.")
        raise TokenAdminError("This container is already assigned to another user.")

    def remove_user(self, user: User):
        """
        Remove a user from the container. Raises a ResourceNotFoundError if the user does not exist.

        :param user: User object to be removed
        :return: True if the user was removed, False if the user was not found in the container
        """
        (user_id, resolver_type, resolver_name) = user.get_user_identifiers()
        count = TokenContainerOwner.query.filter_by(container_id=self._db_container.id,
                                                    user_id=user_id,
                                                    resolver=resolver_name).delete()
        db.session.commit()
        if count > 0:
            self.update_last_updated()
        return count > 0

    def get_users(self):
        """
        Returns a list of users that are assigned to the container.
        """
        db_container_owners: List[TokenContainerOwner] = TokenContainerOwner.query.filter_by(
            container_id=self._db_container.id).all()

        users: List[User] = []
        for owner in db_container_owners:
            realm = Realm.query.filter_by(id=owner.realm_id).first()
            user = User(uid=owner.user_id, realm=realm.name, resolver=owner.resolver)
            users.append(user)

        return users

    def get_states(self):
        """
        Returns the states of the container as a list of strings.
        """
        db_states = self._db_container.states
        states = [state.state for state in db_states]
        return states

    def _check_excluded_states(self, states):
        """
        Validates whether the state list contains states that excludes each other

        :param states: list of states
        :returns: True if the state list contains exclusive states, False otherwise
        """
        state_types = self.get_state_types()
        for state in states:
            if state in state_types:
                excluded_states = state_types[state]
                same_states = list(set(states).intersection(excluded_states))
                if len(same_states) > 0:
                    return True
        return False

    def set_states(self, state_list: List[str]):
        """
        Set the states of the container. Previous states will be removed.
        Raises a ParameterError if the state list contains exclusive states.

        :param state_list: List of states as strings
        :returns: Dictionary in the format {state: success}
        """
        if not state_list:
            state_list = []

        # Check for exclusive states
        exclusive_states = self._check_excluded_states(state_list)
        if exclusive_states:
            raise ParameterError(f"The state list {state_list} contains exclusive states!")

        # Remove old state entries
        TokenContainerStates.query.filter_by(container_id=self._db_container.id).delete()

        # Set new states
        state_types = self.get_state_types().keys()
        res = {}
        for state in state_list:
            if state not in state_types:
                # We do not raise an error here to allow following states to be set
                log.warning(f"State {state} not supported. Supported states are {state_types}.")
                res[state] = False
            else:
                TokenContainerStates(container_id=self._db_container.id, state=state).save()
                res[state] = True
        self.update_last_updated()
        return res

    def add_states(self, state_list: List[str]):
        """
        Add states to the container. Previous states are only removed if a new state excludes them.
        Raises a ParameterError if the state list contains exclusive states.

        :param state_list: List of states as strings
        :returns: Dictionary in the format {state: success}
        """
        if not state_list or len(state_list) == 0:
            return {}

        # Check for exclusive states
        exclusive_states = self._check_excluded_states(state_list)
        if exclusive_states:
            raise ParameterError(f"The state list {state_list} contains exclusive states!")

        # Add new states
        res = {}
        state_types = self.get_state_types()
        for state in state_list:
            if state not in state_types.keys():
                # We do not raise an error here to allow following states to be set
                res[state] = False
                log.warning(f"State {state} not supported. Supported states are {state_types}.")
            else:
                # Remove old states that are excluded from the new state
                for excluded_state in state_types[state]:
                    TokenContainerStates.query.filter_by(container_id=self._db_container.id,
                                                         state=excluded_state).delete()
                    log.debug(
                        f"Removed state {excluded_state} from container {self.serial} "
                        f"because it is excluded by the new state {state}.")
                TokenContainerStates(container_id=self._db_container.id, state=state).save()
                res[state] = True
        self.update_last_updated()
        return res

    @classmethod
    def get_state_types(cls):
        """
        Returns the state types that are supported by this container class and the states that are exclusive
        to each of these states.

        :return: Dictionary in the format: {state: [excluded_states]}
        """
        state_types_exclusions = {
            "active": ["disabled"],
            "disabled": ["active"],
            "lost": [],
            "damaged": []
        }
        return state_types_exclusions

    def set_container_info(self, info):
        """
        Set the containerinfo field in the DB. Old values will be deleted.

        :param info: dictionary in the format: {key: value}
        """
        self.delete_container_info()
        if info:
            self._db_container.set_info(info)

    def add_container_info(self, key, value):
        """
        Add a key and a value to the DB tokencontainerinfo

        :param key: key
        :param value: value
        """
        self._db_container.set_info({key: value})

    def get_container_info(self):
        """
        Return the tokencontainerinfo from the DB

        :return: list of tokencontainerinfo objects
        """
        return self._db_container.info_list

    def delete_container_info(self, key=None):
        """
        Delete the tokencontainerinfo from the DB

        :param key: key to delete, if None all keys are deleted
        """
        res = {}
        if key:
            container_infos = TokenContainerInfo.query.filter_by(container_id=self._db_container.id, key=key)
        else:
            container_infos = TokenContainerInfo.query.filter_by(container_id=self._db_container.id)
        for ci in container_infos:
            ci.delete()
            res[ci.key] = True
        if container_infos.count() == 0:
            log.debug(f"Container {self.serial} has no info with key {key} or no info at all.")
        return res

    @classmethod
    def get_class_type(cls):
        """
        Returns the type of the container class.
        """
        return "generic"

    @classmethod
    def get_supported_token_types(cls):
        """
        Returns the token types that are supported by the container class.
        """
        return get_token_types()

    @classmethod
    def get_class_prefix(cls):
        """
        Returns the container class specific prefix for the serial.
        """
        return "CONT"

    @classmethod
    def get_class_description(cls):
        """
        Returns a description of the container class.
        """
        return _("General purpose container that can hold any type and any number of token.")
