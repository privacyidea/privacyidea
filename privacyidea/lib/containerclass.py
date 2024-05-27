import logging
from datetime import datetime, timezone

from typing import List

from privacyidea.lib.config import get_token_types
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.token import create_tokenclass_object
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import TokenContainerOwner, Realm, Token, db, TokenContainerState

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
        (user_id, resolver_type, resolver_name) = user.get_user_identifiers()
        if not TokenContainerOwner.query.filter_by(container_id=self._db_container.id,
                                                   user_id=user_id,
                                                   resolver=resolver_name).first():
            TokenContainerOwner(container_id=self._db_container.id,
                                user_id=user_id,
                                resolver=resolver_name,
                                realm_id=user.realm_id).save()
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
        TokenContainerState.query.filter_by(container_id=self._db_container.id).delete()

        # Set new states
        state_types = self.get_state_types().keys()
        for state in value:
            if state not in state_types:
                raise ParameterError(f"State {state} not supported. Supported states are {state_types}.")
            else:
                TokenContainerState(container_id=self._db_container.id, state=state).save()
        self.update_last_updated()

    @staticmethod
    def get_state_types():
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
        self._db_container.del_info()
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
