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

from typing import List, Union

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from flask import json

from privacyidea.lib import _
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import get_token_types
from privacyidea.lib.containers.container_info import (TokenContainerInfoData, PI_INTERNAL, RegistrationState,
                                                       INITIALLY_SYNCHRONIZED)
from privacyidea.lib.containers.container_states import ContainerStates
from privacyidea.lib.crypto import verify_ecc, decryptPassword, FAILED_TO_DECRYPT_PASSWORD
from privacyidea.lib.error import ParameterError, ResourceNotFoundError, TokenAdminError
from privacyidea.lib.log import log_with
from privacyidea.lib.machine import is_offline_token
from privacyidea.lib.token import (create_tokenclass_object, get_tokens, get_serial_by_otp_list,
                                   get_tokens_from_serial_or_user)
from privacyidea.lib.tokenclass import TokenClass, CHALLENGE_SESSION
from privacyidea.lib.user import User
from privacyidea.lib.utils import is_true
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
    def get_class_options(cls, only_selectable=False) -> dict[str, list[str]]:
        """
        Returns the options for the container class.

        :param only_selectable: If True, only options with more than one value are returned.
        :return: Dictionary in the format {key: [values]}
        """
        if only_selectable:
            class_options = {key: values for key, values in cls.options.items() if len(values) > 1}
        else:
            class_options = cls.options
        return class_options

    @classmethod
    def is_multi_challenge_enrollable(cls) -> bool:
        """
        Returns True if the container type can be enrolled during the authentication process "via multi challenge"
        """
        return False

    def set_default_option(self, key) -> str:
        """
        Checks if a value is set in the container info for the requested key.
        If not, the default value is set, otherwise the already set value is kept.

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
            self.update_container_info([TokenContainerInfoData(key=key, value=value, info_type=PI_INTERNAL)])
        return value

    @property
    def serial(self) -> str:
        return self._db_container.serial

    @property
    def description(self) -> str:
        return self._db_container.description

    @description.setter
    def description(self, value: str):
        if not value:
            value = ""
        self._db_container.description = value
        self._db_container.save()

    @property
    def type(self) -> str:
        return self._db_container.type

    @property
    def db_id(self) -> int:
        return self._db_container.id

    @property
    def last_authentication(self) -> Union[datetime, None]:
        """
        Returns the timestamp of the last seen field in the database.
        It is the time when a token of the container was last used successfully for authentication.
        From this layer on it is hence called 'last_authentication'.
        If the container was never used for authentication, the value is None.
        """
        last_auth = self._db_container.last_seen
        if last_auth:
            last_auth = last_auth.replace(tzinfo=timezone.utc)
        return last_auth

    def update_last_authentication(self):
        """
        Updates the timestamp of the last seen field in the database.
        """
        # SQLite does not support timezone aware timestamps, hence all time stamps are stored in utc time.
        # The timezone information must be removed, because some databases would change the time stamp to local time
        # (e.g. postgresql)
        self._db_container.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
        self._db_container.save()

    def reset_last_authentication(self):
        """
        Resets the timestamp of the last seen field in the database.
        """
        self._db_container.last_seen = None
        self._db_container.save()

    @property
    def last_synchronization(self) -> Union[datetime, None]:
        """
        Returns the timestamp of the last updated field in the database.
        It is the time when the container was last synchronized with the privacyIDEA server.
        From this layer on it is hence called 'last_synchronization'.
        """
        last_sync = self._db_container.last_updated
        if last_sync:
            last_sync = last_sync.replace(tzinfo=timezone.utc)
        return last_sync

    def update_last_synchronization(self):
        """
        Updates the timestamp of the last updated field in the database.
        """
        # SQLite does not support timezone aware timestamps, hence all time stamps are stored in utc time.
        # The timezone information must be removed, because some databases would change the time stamp to local time
        # (e.g. postgresql)
        self._db_container.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
        self._db_container.save()

    def reset_last_synchronization(self):
        """
        Resets the timestamp of the last updated field in the database.
        """
        self._db_container.last_updated = None
        self._db_container.save()

    @property
    def realms(self) -> list[Realm]:
        return self._db_container.realms

    def set_realms(self, realms, add=False) -> dict[str, bool]:
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

    def _get_user_realms(self) -> list[str]:
        """
        Returns a list of the realm names of the users that are assigned to the container.
        """
        owners = self.get_users()
        realms = [owner.realm for owner in owners]
        return realms

    @property
    def registration_state(self) -> RegistrationState:
        """
        Returns the registration state of the container.
        The registration state is stored in the container info with key 'registration_state'.
        If the key does not exist, it returns the registration state NOT_REGISTERED with the value None.
        """
        container_info = self.get_container_info_dict()
        state = container_info.get(RegistrationState.get_key())
        return RegistrationState(state)

    def remove_token(self, serial: str) -> bool:
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

    def add_token(self, token: TokenClass) -> bool:
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

    def get_tokens(self) -> list[TokenClass]:
        """
        Returns the tokens of the container as a list of TokenClass objects.
        """
        return self.tokens

    def get_tokens_for_synchronization(self) -> list[TokenClass]:
        """
        Returns the tokens of the container that can be synchronized with a client as a list of TokenClass objects.
        """
        return self.tokens

    def delete(self) -> int:
        """
        Deletes the container and all associated objects from the database.
        Returns the id of the deleted container.
        """
        return self._db_container.delete()

    def add_user(self, user: User) -> bool:
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
            self._db_container.save()
            return True
        log.info(f"Container {self.serial} already has an owner.")
        raise TokenAdminError("This container is already assigned to another user.")

    def remove_user(self, user: User) -> bool:
        """
        Remove a user from the container. Also, non-existing users can be removed without an error.
        However, if no matching user is found to remove, we raise an error if the user does not exist.

        :param user: User object to be removed
        :return: True if the user was removed, False if the user was not found in the container
        """
        user_id = user.uid if user.uid else None
        resolver = user.resolver if user.resolver else None
        realm_id = user.realm_id if user.realm_id else None

        query = TokenContainerOwner.query.filter_by(container_id=self._db_container.id, user_id=user_id)
        if resolver:
            query = query.filter_by(resolver=resolver)
        if realm_id:
            query = query.filter_by(realm_id=realm_id)
        count = query.delete()
        db.session.commit()

        if count <= 0:
            # The user could not be unassigned, check if it might not exist
            User(user.login, user.realm).get_user_identifiers()

        return count > 0

    def get_users(self) -> list[User]:
        """
        Returns a list of users that are assigned to the container.
        """
        db_container_owners: List[TokenContainerOwner] = TokenContainerOwner.query.filter_by(
            container_id=self._db_container.id).all()

        users: list[User] = []
        for owner in db_container_owners:
            realm = Realm.query.filter_by(id=owner.realm_id).first()
            try:
                user = User(uid=owner.user_id, realm=realm.name, resolver=owner.resolver)
            except Exception as ex:
                log.error(f"Unable to get user {owner.user_id} for container {self.serial}: {ex!r}")
                # We return an empty User object here to notify that we ran into an error
                user = User(login=None, realm=realm.name, resolver=owner.resolver)
            users.append(user)

        return users

    def get_states(self) -> list[str]:
        """
        Returns the states of the container as a list of strings.
        """
        db_states = self._db_container.states
        states = [state.state for state in db_states]
        return states

    def set_states(self, state_list: list[str]) -> dict[str, bool]:
        """
        Set the states of the container. Previous states will be removed.
        Raises a ParameterError if the state list contains exclusive states.

        :param state_list: List of states as strings
        :returns: Dictionary in the format {state: success}
        """
        res = {}
        if not state_list:
            state_list = []

        # convert to ContainerState Enum and check if state exists
        supported_states = ContainerStates.get_supported_states()
        enum_states = []
        for state in state_list:
            try:
                enum_states.append(ContainerStates(state))
            except ValueError:
                # We do not raise an error here to allow following states to be set
                log.warning(f"State {state} not supported. Supported states are {supported_states}.")
                res[state] = False

        # Check for exclusive states
        exclusive_states = ContainerStates.check_excluded_states(enum_states)
        if exclusive_states:
            raise ParameterError(f"The state list {state_list} contains exclusive states!")

        # Remove old state entries
        TokenContainerStates.query.filter_by(container_id=self._db_container.id).delete()

        # Set new states
        for state in enum_states:
            TokenContainerStates(container_id=self._db_container.id, state=state.value).save()
            res[state.value] = True

        return res

    def add_states(self, state_list: list[str]) -> dict[str, bool]:
        """
        Add states to the container. Previous states are only removed if a new state excludes them.
        Raises a ParameterError if the state list contains exclusive states.

        :param state_list: List of states as strings
        :returns: Dictionary in the format {state: success}
        """
        res = {}
        if not state_list or len(state_list) == 0:
            return {}

        # convert to ContainerState Enum and check if state exists
        supported_states = ContainerStates.get_supported_states()
        enum_states = []
        for state in state_list:
            try:
                enum_states.append(ContainerStates(state))
            except ValueError:
                # We do not raise an error here to allow following states to be set
                log.warning(f"State {state} not supported. Supported states are {supported_states}.")
                res[state] = False

        # Check for exclusive states
        if ContainerStates.check_excluded_states(enum_states):
            raise ParameterError(f"The state list {state_list} contains exclusive states!")

        # Add new states
        exclusive_states = ContainerStates.get_exclusive_states()
        for state in enum_states:
            # Remove old states that are excluded from the new state
            for excluded_state in exclusive_states[state]:
                TokenContainerStates.query.filter_by(container_id=self._db_container.id,
                                                     state=excluded_state.value).delete()
                log.debug(f"Removed state {excluded_state.value} from container {self.serial} because it is excluded "
                          f"by the new state {state.value}.")
            TokenContainerStates(container_id=self._db_container.id, state=state.value).save()
            res[state.value] = True

        return res

    @classmethod
    def get_state_types(cls) -> dict[str, list[str]]:
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
        self.delete_container_info(keep_internal=True)
        if info:
            self._db_container.set_info(info)

    def update_container_info(self, info: list[TokenContainerInfoData]):
        """
        Updates the container info for the passed list of container info. Non-existing keys are added and the values
        for existing keys are updated.

        :param info: list of TokenContainerInfoData objects
        """
        for data in info:
            TokenContainerInfo(self.db_id, data.key, data.value, type=data.type, description=data.description).save(
                persistent=False)
        db.session.commit()

    def get_container_info(self) -> list[TokenContainerInfo]:
        """
        Return the tokencontainerinfo from the DB

        :return: list of tokencontainerinfo objects
        """
        return self._db_container.info_list

    def get_internal_info_keys(self) -> list[str]:
        """
        Returns the keys of the internal container info.
        """
        return [info.key for info in self.get_container_info() if info.type == PI_INTERNAL]

    def get_container_info_dict(self) -> dict[str, str]:
        """
        Return the tokencontainerinfo from the DB as dictionary

        :return: dictionary of tokencontainerinfo objects
        """
        container_info_list = self._db_container.info_list
        container_info_dict = {info.key: info.value for info in container_info_list}
        return container_info_dict

    def delete_container_info(self, key=None, keep_internal: bool = True) -> dict[str, bool]:
        """
        Delete the tokencontainerinfo from the DB

        :param key: key to delete, if None all keys are deleted
        :param keep_internal: If True, entries of type PI_INTERNAL are not deleted
        :return: dictionary of deleted keys in the format {key: deleted}
        """
        res = {}
        if key:
            container_infos = TokenContainerInfo.query.filter_by(container_id=self._db_container.id, key=key)
        else:
            container_infos = TokenContainerInfo.query.filter_by(container_id=self._db_container.id)

        if container_infos.count() == 0:
            res[key] = False
            log.debug(f"Container {self.serial} has no info with key {key} or no info at all.")

        for ci in container_infos:
            if not keep_internal or ci.type != PI_INTERNAL:
                ci.delete()
                res[ci.key] = True
            else:
                log.debug(f"Container info with key {ci.key} is of type {PI_INTERNAL} and can not be deleted.")
                res[ci.key] = False
        return res

    def add_options(self, options):
        """
        Add the given options to the container.

        :param options: The options to add as dictionary
        """
        class_options = self.get_class_options()
        for key, value in options.items():
            option_values = class_options.get(key)
            if option_values is not None:
                if value in option_values:
                    self.update_container_info([TokenContainerInfoData(key=key, value=value, info_type=PI_INTERNAL)])
                else:
                    log.debug(f"Value {value} not supported for option key {key}.")
            else:
                log.debug(f"Option key {key} not found for container type {self.get_class_type()}.")

    @property
    def template(self) -> TokenContainerTemplate:
        """
        Returns the template the container is based on.
        """
        return self._db_container.template

    @template.setter
    def template(self, template_name: str):
        """
        Set the template the container is based on.
        """
        db_template = TokenContainerTemplate.query.filter_by(name=template_name).first()
        if db_template:
            if db_template.container_type == self.type:
                self._db_container.template = db_template
                self._db_container.save()
            else:
                log.info(f"Template {template_name} is not compatible with container type {self.type}.")

    def init_registration(self, server_url: str, scope: str, registration_ttl: int, ssl_verify: bool,
                          params: dict = None):
        """
        Initializes the registration: Generates a QR code containing all relevant data.

        :param server_url: URL of the server reachable for the client.
        :param scope: The URL the client contacts to finalize the registration
                      e.g. "https://pi.net/container/register/finalize".
        :param registration_ttl: Time to live of the registration link in minutes.
        :param ssl_verify: Whether the client shall use ssl.
        :param params: Container specific parameters
        """
        raise NotImplementedError("Registration is not implemented for this container type.")

    def finalize_registration(self, params):
        """
        Finalize the registration of a container.
        """
        raise NotImplementedError("Registration is not implemented for this container type.")

    def terminate_registration(self):
        """
        Terminate the synchronisation of the container with privacyIDEA.
        """
        raise NotImplementedError("Registration is not implemented for this container type.")

    def check_challenge_response(self, params: dict):
        """
        Checks if the response to a challenge is valid.
        """
        return False

    def create_challenge(self, scope, validity_time=2):
        """
        Create a challenge for the container.
        """
        return {}

    def validate_challenge(self, signature: bytes, public_key: EllipticCurvePublicKey, scope: str,
                           transaction_id: str = None, key: str = None, container: str = None, device_brand: str = None,
                           device_model: str = None, passphrase: str = None) -> bool:
        """
        Verifies the response of a challenge:
            - Checks if challenge is valid (not expired)
            - Checks if the challenge is for the right scope
            - Verifies the signature

        Implicitly verifies the passphrase by adding it to the signature message. The passphrase needs to be defined in
        the challenge data. Otherwise, no passphrase is used.

        :param signature: Signature of the message
        :param public_key: Public key to verify the signature
        :param scope: endpoint to reach if the challenge is valid
        :param transaction_id: Transaction ID of the challenge, optional
        :param key: Key to be included in the signature, optional
        :param container: Container to be included in the signature, optional
        :param device_brand: Device brand to be included in the signature, optional
        :param device_model: Device model to be included in the signature, optional
        :param passphrase: Passphrase to be included in the signature and validated against the user store, optional
        :return: True if the challenge response is valid, False otherwise
        """
        challenge_list = get_challenges(serial=self.serial, transaction_id=transaction_id)
        container_info = self.get_container_info_dict()
        hash_algorithm = container_info.get("hash_algorithm", "SHA256")
        verify_res = {"valid": False, "hash_algorithm": hash_algorithm}

        # Checks all challenges of the container, at least one must be valid
        for challenge in challenge_list:
            if challenge.is_valid():
                # Create message
                nonce = challenge.challenge
                times_stamp = challenge.timestamp.replace(tzinfo=timezone.utc).isoformat()
                extra_data = json.loads(challenge.data)
                passphrase_user = extra_data.get("passphrase_user")
                if passphrase_user:
                    if not passphrase:
                        log.debug("The challenge requires to validate the passphrase against the user store, but no "
                                  "passphrase is provided.")
                        continue
                    owners = self.get_users()
                    if len(owners) == 0:
                        log.debug(f"No user assigned to the container {self.serial}. Passphrase can not be validated "
                                  "against the user store.")
                        continue
                    valid_passphrase = owners[0].check_password(passphrase)
                    if not valid_passphrase:
                        log.debug(f"Invalid passphrase {len(passphrase) * '*'} for user {owners[0].login} in realm "
                                  f"{owners[0].realm}.")
                        continue
                else:
                    passphrase = extra_data.get("passphrase_response")
                    if passphrase:
                        passphrase = decryptPassword(passphrase)
                        if passphrase == FAILED_TO_DECRYPT_PASSWORD:
                            challenge.delete()
                            log.warning("Failed to decrypt the passphrase from the challenge. "
                                        "Hence, deleted the challenge.")
                            continue
                challenge_scope = extra_data.get("scope")
                # explicitly check the scope that the right challenge for the right endpoint is used
                if scope != challenge_scope:
                    log.debug(f"Scope {scope} does not match challenge scope {challenge_scope}.")
                    continue

                message = f"{nonce}|{times_stamp}|{self.serial}|{challenge_scope}"
                if device_brand:
                    message += f"|{device_brand}"
                if device_model:
                    message += f"|{device_model}"
                if passphrase:
                    message += f"|{passphrase}"
                if key:
                    message += f"|{key}"
                if container:
                    message += f"|{container}"

                # Check signature
                try:
                    verify_res = verify_ecc(message.encode("utf-8"), signature, public_key, hash_algorithm)
                except InvalidSignature:
                    # It is not the right challenge: log to find reason for invalid signature
                    log.debug(f"Used hash algorithm to verify: {verify_res['hash_algorithm']}")
                    challenge_data_log = (f"Challenge data: nonce={nonce}, timestamp={times_stamp}, "
                                          f"serial={self.serial}, scope={scope}, "
                                          f"transaction_id={challenge.transaction_id}")
                    if passphrase:
                        challenge_data_log += f", passphrase={len(passphrase) * '*'}"
                    log.debug(challenge_data_log)
                    log.debug(f"Challenge data from the client: device_brand={device_brand}, "
                              f"device_model={device_model}, key={key}, container={container} ")
                    continue

                if challenge.session == CHALLENGE_SESSION.ENROLLMENT:
                    # challenge was created during the enrollment. It is still required, hence we only set the state to
                    # answered, but not delete it.
                    challenge.set_otp_status(True)
                    challenge.save()
                else:
                    # Valid challenge: delete it
                    challenge.delete()
                break
            else:
                # Delete expired challenge
                challenge.delete()

        return verify_res["valid"]

    def get_as_dict(self, include_tokens: bool = True, public_info: bool = True,
                    additional_hide_info: list = None) -> dict[str, any]:
        """
        Returns a dictionary containing all properties, contained tokens, and owners

        :param include_tokens: If True, the tokens are included in the dictionary
        :param public_info: If True, only public information is included and sensitive information is omitted
        :param additional_hide_info: List of keys that shall be omitted from the dictionary
        :return: Dictionary with the container details

        Example response:

        .. code:: python

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
                "internal_info_keys": ["hash_algorithm"],
                "realms": ["deflocal"],
                "users": [{"user_name": "testuser",
                           "user_realm": "deflocal",
                           "user_resolver": "internal",
                           "user_id": 1}],
                "tokens": ["TOTP000152D1", "HOTP00012345"]
            }
        """
        details = {"type": self.type,
                   "serial": self.serial,
                   "description": self.description,
                   "last_authentication": self.last_authentication.isoformat() if self.last_authentication else None,
                   "last_synchronization": self.last_synchronization.isoformat() if self.last_synchronization else None,
                   "states": self.get_states()}

        if public_info or additional_hide_info:
            key_blacklist = []
            if public_info:
                key_blacklist = ["public_key_client", "rollover_server_url", "rollover_challenge_ttl"]
            if additional_hide_info:
                key_blacklist.extend(additional_hide_info)
            info = self.get_container_info()
            info_dict = {i.key: i.value for i in info if i.key not in key_blacklist}
        else:
            info_dict = self.get_container_info_dict()
        details["info"] = info_dict
        details["internal_info_keys"] = self.get_internal_info_keys()

        template = self.template
        template_name = ""
        if template:
            template_name = template.name
        details["template"] = template_name

        realms = []
        for realm in self.realms:
            realms.append(realm.name)
        details["realms"] = realms

        users = []
        user_info = {}
        for user in self.get_users():
            user_info["user_realm"] = user.realm
            user_info["user_resolver"] = user.resolver
            if user.uid:
                user_info["user_name"] = user.login
                user_info["user_id"] = user.uid
            else:
                # In case we have a User object without an uid, we assume a resolver error.
                user_info["user_name"] = "**resolver error**"
                user_info["user_id"] = "**resolver error**"
            users.append(user_info)
        details["users"] = users

        if include_tokens:
            details["tokens"] = [token.get_serial() for token in self.get_tokens()]

        return details

    @classmethod
    def get_class_type(cls) -> str:
        """
        Returns the type of the container class.
        """
        return "generic"

    @classmethod
    def get_supported_token_types(cls) -> list[str]:
        """
        Returns the token types that are supported by the container class.
        """
        supported_token_types = get_token_types()
        supported_token_types.sort()
        return supported_token_types

    @classmethod
    def get_class_prefix(cls) -> str:
        """
        Returns the container class specific prefix for the serial.
        """
        return "CONT"

    @classmethod
    def get_class_description(cls) -> str:
        """
        Returns a description of the container class.
        """
        return _("General purpose container that can hold any type and any number of token.")

    def encrypt_dict(self, container_dict: dict, params: dict):
        """
        Encrypts a dictionary with the public key of the container.
        It is not supported by all container classes. Classes not supporting the encryption raise a privacyIDEA error.
        """
        raise NotImplementedError("Encryption is not implemented for this container type.")

    def synchronize_container_details(self, container_client: dict,
                                      initial_transfer_allowed: bool = False) -> dict[str, dict[str, any]]:
        """
        Compares the container from the client with the server and returns the differences.
        The container dictionary from the client contains information about the container itself and the tokens.
        For each token the type and serial shall be provided. If no serial is available, two otp values can be provided.
        The server than tries to find the serial for the otp values. If multiple serials are found, it will not be
        included in the returned dictionary, since the token can not be uniquely identified.
        The returned dictionary contains information about the container itself and the tokens that needs to be added
        or updated. For the tokens to be added the enrollUrl is provided. For the tokens to be updated at least the
        serial and the tokentype are provided.

        An example container dictionary from the client:

        .. code:: python

                {
                    "serial": "SMPH001",
                    "type": "smartphone",
                    "tokens": [{"serial": "TOTP001", "tokentype": "TOTP"},
                                {"otp": ["1234", "9876"], "tokentype": "HOTP", "counter": "2"}]
                }

        An example of a returned container dictionary:

        .. code:: python

                {
                    "container": {"type": "smartphone", "serial": "SMPH001"},
                    "tokens": {"add": ["enroll_url1", "enroll_url2"],
                               "update": [{"serial": "TOTP001", "tokentype": "totp"},
                                          {"serial": "HOTP001", "otp": ["1234", "9876"],
                                           "tokentype": "hotp", "counter": 2}]}
                }

        :param initial_transfer_allowed: If True, all tokens from the client are added to the container
        :param container_client: The container from the client as dictionary.
        :return: container dictionary
        """
        container_dict = {"container": {"type": self.type, "serial": self.serial}}
        server_token_serials = [token.get_serial() for token in self.get_tokens_for_synchronization()]

        # Get serials for client tokens without serial
        client_tokens = container_client.get("tokens", [])
        serial_otp_map = {}
        for token in client_tokens:
            dict_keys = token.keys()
            # Get serial from otp if required
            if "serial" not in dict_keys and "otp" in dict_keys:
                token_type = token.get("tokentype")
                if token_type:
                    token_type = token_type.lower()
                token_list = get_tokens(tokentype=token_type)
                client_counter = token.get("counter")
                if client_counter:
                    client_counter = int(client_counter)
                serial_list = get_serial_by_otp_list(token_list, otp_list=token["otp"], counter=client_counter)
                if len(serial_list) == 1:
                    serial = serial_list[0]
                    token["serial"] = serial
                    serial_otp_map[serial] = token["otp"]
                elif len(serial_list) > 1:
                    log.warning(f"Multiple serials found for otp {token['otp']}. Ignoring this token.")
                # shall we ignore otp values where multiple serials are found?

        # map client and server tokens
        client_serials = [token["serial"] for token in client_tokens if "serial" in token.keys()]

        registration_state = self.registration_state
        if registration_state == RegistrationState.ROLLOVER_COMPLETED:
            # rollover all tokens: generate new enroll info for all tokens
            missing_serials = server_token_serials
            same_serials = []
        else:
            missing_serials = list(set(server_token_serials).difference(set(client_serials)))
            same_serials = list(set(server_token_serials).intersection(set(client_serials)))

        # Offline tokens that do not exist on the client can not be added during synchronization since the offline
        # counter is not known by the server
        offline_serials = [serial for serial in missing_serials if is_offline_token(serial)]
        missing_serials = list(set(missing_serials).difference(set(offline_serials)))
        if registration_state == RegistrationState.ROLLOVER_COMPLETED:
            # offline tokens known by the client can be added to the update list
            # (indicating the tokens are still in the container)
            same_serials = list(set(client_serials).intersection(set(offline_serials)))
            # only offline tokens not known to the client are excluded (they can not be added to the client)
            offline_serials = list(set(offline_serials).difference(set(client_serials)))
        if len(offline_serials) > 0:
            log.info(f"The following offline tokens do not exist on the client: {offline_serials}. "
                     "They can not be added during synchronization.")

        # Initial synchronization after registration or rollover
        container_info = self.get_container_info_dict()
        if initial_transfer_allowed and not is_true(container_info.get(INITIALLY_SYNCHRONIZED)):
            self.update_container_info([TokenContainerInfoData(key=INITIALLY_SYNCHRONIZED, value="True",
                                                               info_type=PI_INTERNAL)])
            server_missing_tokens = list(set(client_serials).difference(set(server_token_serials)))
            for serial in server_missing_tokens:
                # Try to add the missing token to the container on the server
                try:
                    token = get_tokens_from_serial_or_user(serial, None)[0]
                except ResourceNotFoundError:
                    log.info(f"Token {serial} from client does not exist on the server.")
                    continue

                try:
                    self.add_token(token)
                except ParameterError as e:
                    log.info(f"Client token {serial} could not be added to the container: {e}")
                    continue
                # add token to the same_serials list to update the token details
                same_serials.append(serial)

        # Get info for same serials: token details
        update_dict = []
        for serial in same_serials:
            token = get_tokens_from_serial_or_user(serial, None)[0]
            offline = is_offline_token(serial)
            token_dict_all = token.get_as_dict()
            token_dict = {"serial": token_dict_all["serial"], "tokentype": token_dict_all["tokentype"],
                          "offline": offline}
            # rename count to counter for the client
            if "count" in token_dict_all:
                # For offline tokens the counter shall not be sent to the client
                if not offline:
                    token_dict["counter"] = token_dict_all["count"]

            # add otp values to allow the client identifying the token if he has no serial yet
            otp = serial_otp_map.get(serial)
            if otp:
                token_dict["otp"] = otp
            update_dict.append(token_dict)

        container_dict["tokens"] = {"add": missing_serials, "update": update_dict}

        if registration_state == RegistrationState.ROLLOVER_COMPLETED:
            container_dict["tokens"]["offline"] = offline_serials

        return container_dict