import logging
from datetime import datetime, timezone

from typing import List

from privacyidea.lib.config import get_token_types
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.token import create_tokenclass_object
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import TokenContainerOwner, Realm, Token, db, TokenContainerStates, TokenContainerInfo, \
    TokenContainerRealm

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
        self._db_container.last_seen = datetime.now(timezone.utc)
        self._db_container.save()

    @property
    def last_updated(self):
        return self._db_container.last_updated

    def update_last_updated(self):
        self._db_container.last_updated = datetime.now(timezone.utc)
        self._db_container.save()
        self.update_last_seen()

    @property
    def realms(self):
        return self._db_container.realms

    def set_realms(self, realms, add=False):
        result = {}

        # delete all container realms
        if not add:
            TokenContainerRealm.query.filter_by(container_id=self._db_container.id).delete()
            result["deleted"] = True
            self._db_container.save()
        else:
            result["deleted"] = False

        for realm in realms:
            if realm:
                realm_db = Realm.query.filter_by(name=realm).first()
                if not realm_db:
                    result[realm] = False
                    #raise ParameterError(f"Realm {realm} does not exist.")
                else:
                    realm_id = realm_db.id
                    if not TokenContainerRealm.query.filter_by(container_id=self._db_container.id,
                                                               realm_id=realm_id).first():
                        # Check if realm is already assigned to the container
                        self._db_container.realms.append(realm_db)
                        result[realm] = True
                    else:
                        result[realm] = False
        self._db_container.save()
        self.update_last_updated()

        return result

    def remove_token(self, serial: str):
        token = Token.query.filter(Token.serial == serial).first()
        if token:
            self._db_container.tokens.remove(token)
            self._db_container.save()
            self.tokens = [t for t in self.tokens if t.get_serial() != serial]
            self.update_last_updated()

    def add_token(self, token: TokenClass):
        if not token.get_type() in self.get_supported_token_types():
            raise ParameterError(f"Token type {token.get_type()} not supported for container type {self.type}. "
                                 f"Supported types are {self.get_supported_token_types()}.")
        self.tokens.append(token)
        self._db_container.tokens = [t.token for t in self.tokens]
        self._db_container.save()
        self.update_last_updated()

    def get_tokens(self):
        return self.tokens

    def delete(self):
        return self._db_container.delete()

    def add_user(self, user: User):
        """
        Assign a user to the container if the container does not have an owner yet.
        Otherwise, the new user will not be assigned and the original owner will remain.

        :param user: User object
        :return: True if the user was assigned, False if the container already has an owner
        """
        (user_id, resolver_type, resolver_name) = user.get_user_identifiers()
        if not TokenContainerOwner.query.filter_by(container_id=self._db_container.id).first():
            TokenContainerOwner(container_id=self._db_container.id,
                                user_id=user_id,
                                resolver=resolver_name,
                                realm_id=user.realm_id).save()
            self.realms = [user.realm_id]
            self.update_last_updated()
            return True
        return False

    def remove_user(self, user: User):
        (user_id, resolver_type, resolver_name) = user.get_user_identifiers()
        count = TokenContainerOwner.query.filter_by(container_id=self._db_container.id,
                                                    user_id=user_id,
                                                    resolver=resolver_name).delete()
        db.session.commit()
        if count > 0:
            self.update_last_updated()
        return count > 0

    def get_users(self):
        db_container_owners: List[TokenContainerOwner] = TokenContainerOwner.query.filter_by(
            container_id=self._db_container.id).all()

        users: List[User] = []
        for owner in db_container_owners:
            realm = Realm.query.filter_by(id=owner.realm_id).first()
            user = User(uid=owner.user_id, realm=realm.name, resolver=owner.resolver)
            users.append(user)

        return users

    def get_states(self):
        return self._db_container.states

    def set_states(self, value: List[str]):
        # Remove old state entries
        TokenContainerStates.query.filter_by(container_id=self._db_container.id).delete()

        # Set new states
        state_types = self.get_state_types().keys()
        for state in value:
            if state not in state_types:
                raise ParameterError(f"State {state} not supported. Supported states are {state_types}.")
            else:
                TokenContainerStates(container_id=self._db_container.id, state=state).save()
        self.update_last_updated()

    def add_states(self, value: List[str]):
        # Add new states
        state_types = self.get_state_types()
        for state in value:
            if state not in state_types.keys():
                raise ParameterError(f"State {state} not supported. Supported states are {state_types}.")
            else:
                # Remove states that are excluded from the new state
                for excluded_state in state_types[state]:
                    TokenContainerStates.query.filter_by(container_id=self._db_container.id,
                                                         state=excluded_state).delete()
                    log.debug(
                        f"Removed state {excluded_state} from container {self.serial} "
                        f"because it is excluded by the new state {state}.")
                TokenContainerStates(container_id=self._db_container.id, state=state).save()
        self.update_last_updated()

    @classmethod
    def get_state_types(cls):
        state_types_exclusions = {
            "active": ["disabled"],
            "disabled": ["active"],
            "lost": [],
            "damaged": []
        }
        return state_types_exclusions

    def set_containerinfo(self, info):
        """
        Set the containerinfo field in the DB. Old values will be deleted.

        :param info: dictionary with key and value
        :type info: dict
        """
        self.delete_container_info()
        self._db_container.set_info(info)

    def add_containerinfo(self, key, value):
        """
        Add a key and a value to the DB tokencontainerinfo

        :param key:
        :param value:
        """
        add_info = {key: value}
        self._db_container.set_info(add_info)

    def get_containerinfo(self):
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
        if key:
            container_infos = TokenContainerInfo.query.filter_by(container_id=self._db_container.id, Key=key)
        else:
            container_infos = TokenContainerInfo.query.filter_by(container_id=self._db_container.id)
        for ci in container_infos:
            ci.delete()

    @classmethod
    def get_class_type(cls):
        return "generic"

    @classmethod
    def get_supported_token_types(cls):
        return get_token_types()

    @classmethod
    def get_container_policy_info(cls):
        res = {
            "token_count": {"type": "int",
                            "value": "any",
                            "desc": "The maximum number of tokens in this container"},
            "token_types": {"type": "list",
                            "value": cls.get_supported_token_types(),
                            "desc": "The token types that can be stored in this container"},
            "user_modifiable": {"type": "bool",
                                "value": ["true", "false"],
                                "desc": "Whether the user can modify the tokens in this container"}
        }

        return res

    @classmethod
    def get_class_prefix(cls):
        return "CONT"

    @classmethod
    def get_class_description(cls):
        return "General purpose container that can hold any type and any number of token."
