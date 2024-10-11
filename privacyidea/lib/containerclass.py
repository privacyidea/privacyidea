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

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from flask import json

from privacyidea.lib import _
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import get_token_types
from privacyidea.lib.crypto import verify_ecc
from privacyidea.lib.error import ParameterError, ResourceNotFoundError, TokenAdminError, privacyIDEAError
from privacyidea.lib.log import log_with
from privacyidea.lib.token import create_tokenclass_object
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import (TokenContainerOwner, Realm, Token, db, TokenContainerStates,
                                TokenContainerInfo, TokenContainerRealm, TokenContainerTemplate)

log = logging.getLogger(__name__)


class TokenContainerClass:
    options = {}

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
        self.options = {}

    @classmethod
    def get_class_options(cls, only_selectable=False):
        """
        Returns the options for the container class.
        """
        if only_selectable:
            class_options = {key: values for key, values in cls.options.items() if len(values) > 1}
        else:
            class_options = cls.options
        return class_options

    def set_default_option(self, key):
        """
        Checks if all options (key algorithm, hash algorithm, ...) are set in the container info.
        Otherwise, the default values are set.

        :param key: The key to be checked.
        :return: The used value for the key or None if the key does not exist in the class options.
        """
        class_options = self.get_class_options()
        key_options = class_options.get(key)

        if key_options is None:
            # The key does not exist in the class options
            return None

        # Check if value is already set for this key in the container info
        container_info = self.get_container_info_dict()
        value = container_info.get(key)
        if not value:
            # key not defined: set default value
            value = class_options[key][0]
            self.add_container_info(key, value)
        return value

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

    @property
    def type(self):
        return self._db_container.type

    @property
    def last_authentication(self):
        """
        Returns the timestamp of the last seen field in the database.
        It is the time when a token of the container was last used for authentication.
        From this layer on it is hence called 'last_authentication'.
        """
        return self._db_container.last_seen

    def update_last_authentication(self):
        """
        Updates the timestamp of the last seen field in the database.
        """
        self._db_container.last_seen = datetime.now(timezone.utc)
        self._db_container.save()

    @property
    def last_synchronization(self):
        """
        Returns the timestamp of the last updated field in the database.
        It is the time when the container was last synchronized with the privacyIDEA server.
        From this layer on it is hence called 'last_synchronization'.
        """
        return self._db_container.last_updated

    def update_last_synchronization(self, timestamp=None):
        """
        Updates the timestamp of the last updated field in the database.
        """
        if timestamp:
            self._db_container.last_updated = timestamp
        else:
            self._db_container.last_updated = datetime.now(timezone.utc)
        self._db_container.save()

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

    def get_container_info_dict(self):
        """
        Return the tokencontainerinfo from the DB

        :return: dictionary of tokencontainerinfo objects
        """
        container_info_list = self._db_container.info_list
        container_info_dict = {info.key: info.value for info in container_info_list}
        return container_info_dict

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

    @property
    def template(self):
        """
        Returns the template the container is based on.
        """
        return self._db_container.template

    @template.setter
    def template(self, template_name: str):
        """
        Set the template the container is based on.
        """
        success = False
        db_template = TokenContainerTemplate.query.filter_by(name=template_name).first()
        if db_template:
            if db_template.container_type == self.type:
                self._db_container.template = db_template
                self._db_container.save()
                success = True
            else:
                log.info(f"Template {template_name} is not compatible with container type {self.type}.")
        return success

    def init_registration(self, params):
        """
        Initialize the registration of a pi container on a physical container.
        """
        return {}

    def finalize_registration(self, params):
        """
        Finalize the registration of a pi container on a physical container.
        """
        return {}

    def terminate_registration(self):
        """
        Terminate the registration of a pi container on a physical container.
        """
        return

    def init_sync(self, params):
        """
        Initialize the synchronization of a container with the pi server.
        It creates a challenge for the container to allow the registration.
        """
        return {}

    def check_synchronization_challenge(self, params):
        """
        Checks if the one who is requesting the synchronization is allowed to receive these information.
        """
        return True

    def create_challenge(self, params):
        """
        Create a challenge for the container.
        """
        return {}

    def check_challenge_response(self, params):
        """
        Check the response of a challenge.
        """
        return False

    def validate_challenge(self, signature, public_key: EllipticCurvePublicKey, transaction_id=None,
                           url=None, scope=None, key=None, container=None):
        """
        Verifies the response of a challenge:
            * Checks if challenge is valid (not expired)
            * Verifies the signature
            * Verifies the passphrase if it is part of the challenge

        :param signature: Signature of the message
        :param public_key: Public key to verify the signature
        :param transaction_id: Transaction ID of the challenge
        :param url: URL of an endpoint the client can contact
        :return: True if the challenge response is valid, False otherwise
        """
        challenge_list = get_challenges(serial=self.serial, transaction_id=transaction_id)
        valid_challenge = False

        # Checks all challenges of the container, at least one must be valid
        for challenge in challenge_list:
            if challenge.is_valid():
                # Create message
                nonce = challenge.challenge
                times_stamp = challenge.timestamp.replace(tzinfo=timezone.utc).isoformat()
                extra_data = json.loads(challenge.data)
                passphrase = extra_data.get("passphrase_response")
                message = f"{nonce}|{times_stamp}"
                if url:
                    message += f"|{url}"
                message += f"|{self.serial}"
                if passphrase:
                    message += f"|{passphrase}"
                if scope:
                    message += f"|{scope}"
                if key:
                    message += f"|{key}"
                if container:
                    message += f"|{container}"

                container_info = self.get_container_info_dict()
                hash_algorithm = container_info.get("hash_algorithm", "SHA256")

                # Check signature
                try:
                    valid_challenge, hash_algorithm = verify_ecc(message.encode("utf-8"), signature, public_key,
                                                                 hash_algorithm)
                except InvalidSignature:
                    # It is not the right challenge
                    continue

                # Check passphrase
                challenge_data = json.loads(challenge.data)
                challenge_passphrase = challenge_data.get("passphrase_response")
                if challenge_passphrase:
                    if challenge_data.get("passphrase_ad") == "AD":
                        # TODO: Validate against AD
                        pass
                    else:
                        if challenge_passphrase != passphrase:
                            raise privacyIDEAError('Could not verify signature!')

                # Valid challenge: delete it
                challenge.delete()
                break

        return valid_challenge

    def get_container_details(self, no_token=False):
        """
        Returns a dictionary containing all properties, contained tokens, and owners

        :param no_token: If True, the token details are not included
        :return: Dictionary with the container details

        Example response

        ::

            {
                "type": "smartphone",
                "serial": "SMPH00038DD3",
                "description": "My smartphone",
                "last_authentication": "2024-09-11T08:56:37.200336+00:00",
                "last_synchronization": "2024-09-11T08:56:37.200336+00:00",
                "states": ["active"],
                "info": {
                            "hash_algorithm": "SHA256",
                            "key_algorithm": "secp384r1"
                        },
                "realms": ["deflocal"],
                "users": [{"user_name": "testuser",
                           "user_realm": "deflocal",
                           "user_resolver": "internal",
                           "user_id": 1}],
                "tokens": [{"serial": "TOTP000152D1", "type": "totp", "active": True, ...}]
            }
        """
        details = {"type": self.type,
                   "serial": self.serial,
                   "description": self.description,
                   "last_authentication": self.last_authentication,
                   "last_synchronization": self.last_synchronization,
                   "states": self.get_states()}

        infos = {}
        for info in self.get_container_info():
            if info.type:
                infos[info.key + ".type"] = info.type
            infos[info.key] = info.value
        details["info"] = infos

        realms = []
        for realm in self.realms:
            realms.append(realm.name)
        details["realms"] = realms

        users = []
        user_info = {}
        for user in self.get_users():
            user_info["user_name"] = user.login
            user_info["user_realm"] = user.realm
            user_info["user_resolver"] = user.resolverModel
            user_info["user_id"] = user.uid
            users.append(user_info)
        details["users"] = users

        if not no_token:
            token_dict_list = []
            token_list = self.get_tokens()
            for token in token_list:
                token_dict_list.append(token.get_as_dict_with_user_and_containers())

            details["tokens"] = token_dict_list

        return details


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
        supported_token_types = get_token_types()
        supported_token_types.sort()
        return supported_token_types

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

    def encrypt_dict(self, container_dict: dict, params: dict):
        """
        Encrypts a dictionary with the public key of the container.
        It is not supported by all container classes. Classes not supporting the encryption return the original data.
        """
        return container_dict
