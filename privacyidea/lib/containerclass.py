import logging

from typing import List

from privacyidea.lib.config import get_token_types
from privacyidea.lib.error import ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.token import create_tokenclass_object
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import TokenContainerOwner, Realm, Token, TokenContainerToken, db

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

    @property
    def type(self):
        return self._db_container.type

    def remove_token(self, serial: str):
        token = Token.query.filter(Token.serial == serial).first()
        self._db_container.tokens.remove(token)
        self._db_container.save()
        self.tokens = [t for t in self.tokens if t.get_serial() != serial]

    def add_token(self, token: TokenClass):
        if not token.get_type() in self.get_supported_token_types():
            raise ParameterError(f"Token type {token.get_type()} not supported for container type {self.type}. "
                                 f"Supported types are {self.get_supported_token_types()}.")
        self.tokens.append(token)
        self._db_container.tokens = [t.token for t in self.tokens]
        self._db_container.save()

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
            return True
        return False

    def remove_user(self, user: User):
        (user_id, resolver_type, resolver_name) = user.get_user_identifiers()
        count = TokenContainerOwner.query.filter_by(container_id=self._db_container.id,
                                                    user_id=user.login,
                                                    resolver=resolver_name).delete()
        db.session.commit()
        return count > 0

    def get_users(self):
        db_container_owners: List[TokenContainerOwner] = TokenContainerOwner.query.filter_by(
            container_id=self._db_container.id).all()

        users: List[User] = []
        for owner in db_container_owners:
            realm = Realm.query.filter_by(id=owner.realm_id).first()
            user = User(login=owner.user_id, realm=realm.name, resolver=owner.resolver)
            users.append(user)

        return users

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
