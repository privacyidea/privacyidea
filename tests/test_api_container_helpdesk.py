# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import json
import mock
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from typing import Optional

import passlib
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey

from privacyidea.lib.applications.offline import MachineApplication, REFILLTOKEN_LENGTH
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.container import (create_container_template, get_template_obj, delete_container_by_serial,
                                       get_container_realms, set_container_states, unregister)
from privacyidea.lib.container import (init_container, find_container_by_serial, add_token_to_container, assign_user,
                                       add_container_realms, remove_token_from_container)
from privacyidea.lib.containers.container_info import PI_INTERNAL, TokenContainerInfoData, RegistrationState
from privacyidea.lib.containers.container_states import ContainerStates
from privacyidea.lib.containers.smartphone import SmartphoneOptions
from privacyidea.lib.crypto import generate_keypair_ecc, decrypt_aes
from privacyidea.lib.error import Error
from privacyidea.lib.machine import attach_token
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.conditions import ConditionSection, ConditionHandleMissingData
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.privacyideaserver import add_privacyideaserver
from privacyidea.lib.realm import set_realm, set_default_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.serviceid import set_serviceid
from privacyidea.lib.smsprovider.FirebaseProvider import FirebaseConfig
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.token import (get_one_token, get_tokens_from_serial_or_user,
                                   get_tokeninfo, get_tokens)
from privacyidea.lib.token import init_token, get_tokens_paginate, unassign_token
from privacyidea.lib.tokens.papertoken import PAPERACTION
from privacyidea.lib.tokens.pushtoken import PushAction
from privacyidea.lib.tokens.tantoken import TANAction
from privacyidea.lib.user import User
from privacyidea.lib.utils.compare import PrimaryComparators
from privacyidea.models import Realm
from tests.base import MyApiTestCase
from tests.test_lib_tokencontainer import MockSmartphone

from .api_container_common import (
    APIContainerTest,
    APIContainerAuthorization,
    SmartphoneRequests,
    UNSPECIFIC_ERROR_MESSAGES,
)


class APIContainerAuthorizationHelpdesk(APIContainerAuthorization):
    """
    Test the authorization of the API endpoints for helpdesk admins.
        * allowed: helpdesk admin has the required rights on the realm / resolver / user of the container
        * denied: helpdesk admin does not have the required rights on the container
    """

    def test_01_helpdesk_create_allowed(self):
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE, realm=self.realm1)
        result = self.request_assert_success('/container/init', {"type": "generic", "realm": self.realm1}, self.at)
        self.assertGreater(len(result["result"]["value"]["container_serial"]), 0)
        delete_policy("policy")

    def test_02_helpdesk_create_denied(self):
        self.setUp_user_realm2()
        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE, realm=self.realm1)
        self.request_denied_assert_403('/container/init', {"type": "Smartphone", "realm": self.realm2},
                                       self.at)
        # create container for no realm is denied
        self.request_denied_assert_403('/container/init',
                                       {"type": "Smartphone"},
                                       self.at)
        delete_policy("policy")

        # policy for a resolver
        self.setUp_user_realm3()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE, resolver=self.resolvername1)
        self.request_denied_assert_403('/container/init',
                                       {"type": "Smartphone", "user": "corny", "realm": self.realm3},
                                       self.at)
        # create container for no user is denied
        self.request_denied_assert_403('/container/init',
                                       {"type": "Smartphone"},
                                       self.at)
        delete_policy("policy")

    def test_03_helpdesk_delete_allowed(self):
        self.setUp_user_realm2()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE, realm=[self.realm2, self.realm1])
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_04_helpdesk_delete_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE, realm=self.realm3)
        # container of a user
        self.request_denied_assert_403(f"/container/{c_serial_user}", {}, self.at, method='DELETE')
        # container without user
        self.request_denied_assert_403(f"/container/{c_serial_no_user}", {}, self.at, method='DELETE')
        delete_policy("policy")

        # policy for a resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE, resolver=self.resolvername3)
        # container of a user
        self.request_denied_assert_403(f"/container/{c_serial_user}", {}, self.at, method='DELETE')
        # container without user
        self.request_denied_assert_403(f"/container/{c_serial_no_user}", {}, self.at, method='DELETE')
        delete_policy("policy")

    def test_05_helpdesk_description_allowed(self):
        self.setUp_user_realm2()
        # policy for realms
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION,
                   realm=[self.realm1, self.realm2])
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                    method='POST')
        delete_policy("policy")
        # policy for resolver
        container_serial = self.create_container_for_user()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                    method='POST')
        delete_policy("policy")
        # policy for user
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, user="selfservice",
                   realm=self.realm1, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/description", {"description": "test"}, self.at,
                                    method='POST')
        delete_policy("policy")

    def test_06_helpdesk_description_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, realm=self.realm3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/description", {"description": "test"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

        # policy for a resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, resolver=self.resolvername3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/description", {"description": "test"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

        # policy for a user
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, user="hans",
                   realm=self.realm1,
                   resolver=self.resolvername1)
        self.request_denied_assert_403(f"/container/{c_serial_user}/description", {"description": "test"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/description", {"description": "test"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_07_helpdesk_state_allowed(self):
        container_serial = self.create_container_for_user()
        # policy for realm
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_STATE, realm=self.realm1)
        self.request_assert_success(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                    self.at, method='POST')
        delete_policy("policy")

        # policy for resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_STATE, realm=self.realm1,
                   resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/states", {"states": "active, damaged, lost"},
                                    self.at, method='POST')
        delete_policy("policy")

    def test_08_helpdesk_state_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # policy for realm
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_STATE, realm=self.realm3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        delete_policy("policy")

        # policy for resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_STATE, resolver=self.resolvername3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/states", {"states": "active, damaged, lost"},
                                       self.at, method='POST')
        delete_policy("policy")

    def test_09_helpdesk_add_token_allowed(self):
        self.setUp_user_realm3()
        set_policy("policy_realm", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.CONTAINER_ADD_TOKEN}=true, {PolicyAction.CONTAINER_REMOVE_TOKEN}=true",
                   realm=self.realm1)
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN,
                   resolver=self.resolvername3)
        container_serial = self.create_container_for_user()

        # Add single token
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                    method='POST')

        # Add token that is in another container
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        old_container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        add_token_to_container(old_container_serial, token_serial)
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": token_serial}, self.at,
                                    method='POST')

        # add multiple tokens: one authorized with the realm, the other with the resolver
        token2 = init_token({"genkey": "1", "realm": self.realm1})
        token3 = init_token({"genkey": "1"}, user=User("corny", self.realm3))
        token_serials = ','.join([token2.get_serial(), token3.get_serial()])
        result = self.request_assert_success(f"/container/{container_serial}/addall", {"serial": token_serials},
                                             self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        self.assertTrue(result["result"]["value"][token3.get_serial()])
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

        # Add token to container during enrollment allowed
        set_policy("policy", scope=SCOPE.ADMIN, action=[PolicyAction.CONTAINER_ADD_TOKEN, "enrollHOTP"],
                   realm=self.realm1)
        result = self.request_assert_success("/token/init", {"type": "hotp", "realm": self.realm1, "genkey": 1,
                                                             "container_serial": container_serial}, self.at,
                                             method='POST')
        token_serial = result["detail"]["serial"]
        tokens = get_tokens_paginate(serial=token_serial)
        self.assertEqual(container_serial, tokens["tokens"][0]["container_serial"])
        delete_policy("policy")

    def test_10_helpdesk_add_token_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # helpdesk of user realm realm3: container and token are both in realm1
        set_policy("policy_realm", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN, realm=self.realm3)
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN,
                   resolver=self.resolvername3)
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # helpdesk of user realm realm3: only container is in realm1
        token = init_token({"genkey": "1", "realm": self.realm3})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

        # helpdesk of user realm realm1: only token is in realm3
        set_policy("policy_realm", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN, realm=self.realm1)
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN,
                   resolver=self.resolvername3)
        token = init_token({"genkey": "1", "realm": self.realm3})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # Helpdesk is not allowed to remove token from old container
        token.set_realms([self.realm1])
        add_token_to_container(c_serial_no_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # Adding multiple tokens
        token2 = init_token({"genkey": "1"}, user=User("hans", self.realm1))
        token3 = init_token({"genkey": "1", "realm": self.realm1})
        token_no_user = init_token({"genkey": "1"})
        token_serials = ','.join(
            [token.get_serial(), token2.get_serial(), token_no_user.get_serial(), token3.get_serial()])
        # to authorized container
        result = self.request_assert_success(f"/container/{c_serial_user}/addall", {"serial": token_serials}, self.at,
                                             method='POST')
        self.assertFalse(result["result"]["value"][token.get_serial()])
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        self.assertTrue(result["result"]["value"][token3.get_serial()])
        self.assertFalse(result["result"]["value"][token_no_user.get_serial()])
        # to not authorized container
        container = find_container_by_serial(c_serial_user)
        container.remove_user(User("selfservice", self.realm1))
        container.set_realms([self.realm3], add=False)
        self.request_denied_assert_403(f"/container/{c_serial_user}/addall", {"serial": token_serials}, self.at,
                                       method='POST')

        # helpdesk of user realm realm1: container has no owner, token in realm 1
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # helpdesk of userealm realm1: container has no owner, token is in realm3
        token = init_token({"genkey": "1", "realm": self.realm3})
        token_serial = token.get_serial()
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/add", {"serial": token_serial}, self.at,
                                       method='POST')

        # adding multiple tokens denied, since access on container is not allowed
        token2 = init_token({"genkey": "1", "realm": self.realm3})
        token3 = init_token({"genkey": "1", "realm": self.realm1})
        token_serials = ','.join([token2.get_serial(), token3.get_serial()])
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/addall", {"serial": token_serials}, self.at,
                                       method='POST')
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

        # Add token to container during enrollment fails
        set_policy("policy", scope=SCOPE.ADMIN, action=[PolicyAction.CONTAINER_ADD_TOKEN, "enrollHOTP"],
                   realm=self.realm1)
        container_serial = init_container({"type": "generic", "realm": self.realm2})["container_serial"]
        result = self.request_assert_success("/token/init", {"type": "hotp", "realm": self.realm1, "genkey": 1,
                                                             "container_serial": container_serial}, self.at,
                                             method='POST')
        token_serial = result["detail"]["serial"]
        tokens = get_tokens_paginate(serial=token_serial)
        self.assertEqual("", tokens["tokens"][0]["container_serial"])

    def test_11_helpdesk_remove_token_allowed(self):
        self.setUp_user_realm3()
        set_policy("policy_realm", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REMOVE_TOKEN, realm=self.realm1)
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REMOVE_TOKEN,
                   resolver=self.resolvername3)
        container_serial = self.create_container_for_user()
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()

        # single token
        add_token_to_container(container_serial, token_serial)
        result = self.request_assert_success(f"/container/{container_serial}/remove", {"serial": token_serial}, self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"])

        # multiple tokens
        add_token_to_container(container_serial, token_serial)
        token2 = init_token({"genkey": "1"}, user=User("corny", self.realm3))
        add_token_to_container(container_serial, token2.get_serial())
        token_serials = ','.join([token_serial, token2.get_serial()])
        result = self.request_assert_success(f"/container/{container_serial}/removeall", {"serial": token_serials},
                                             self.at,
                                             method='POST')
        self.assertTrue(result["result"]["value"][token_serial])
        self.assertTrue(result["result"]["value"][token2.get_serial()])
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

    def test_12_helpdesk_remove_token_denied(self):
        self.setUp_user_realm2()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # helpdesk of user realm realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REMOVE_TOKEN, realm=self.realm2)
        # container and token are both in realm1
        token = init_token({"genkey": "1", "realm": self.realm1})
        token_serial = token.get_serial()
        add_token_to_container(c_serial_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        # container has no owner, token is in realm1
        remove_token_from_container(c_serial_user, token_serial)
        add_token_to_container(c_serial_no_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        # container in realm1 and token in realm 2
        token = init_token({"genkey": "1", "realm": self.realm2})
        token_serial = token.get_serial()
        add_token_to_container(c_serial_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        # container has no owner, token is in realm2
        remove_token_from_container(c_serial_user, token_serial)
        add_token_to_container(c_serial_no_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')
        delete_policy("policy")

        # helpdesk of userealm realm1: container in realm1 and token in realm 2
        set_policy("policy_realm", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REMOVE_TOKEN, realm=self.realm1)
        remove_token_from_container(c_serial_no_user, token_serial)
        add_token_to_container(c_serial_user, token_serial)
        self.request_denied_assert_403(f"/container/{c_serial_user}/remove", {"serial": token_serial}, self.at,
                                       method='POST')

        # multiple tokens
        self.setUp_user_realm3()
        set_policy("policy_resolver", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REMOVE_TOKEN,
                   resolver=self.resolvername3)
        token_no_user = init_token({"genkey": "1"})
        add_token_to_container(c_serial_user, token_no_user.get_serial())
        token_user = init_token({"genkey": "1"}, user=User("hans", self.realm2))
        add_token_to_container(c_serial_user, token_user.get_serial())
        token_serials = ','.join([token_no_user.get_serial(), token_user.get_serial()])

        self.request_denied_assert_403(f"/container/{c_serial_user}/removeall", {"serial": token_serials},
                                       self.at,
                                       method='POST',
                                       error_message=("Admin actions are defined, but the action "
                                                      "container_remove_token is not allowed for any of "
                                                      "the serials provided!"))
        delete_policy("policy_realm")
        delete_policy("policy_resolver")

    def test_13_helpdesk_assign_user_allowed(self):
        # Allow to assign a user to a container in the helpdesk realm
        self.setUp_user_realms()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER, realm=self.realm1)
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/assign",
                                    {"realm": self.realm1, "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

        # Allow to assign a user to a container without user and realm
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER, realm=self.realm4,
                   resolver=self.resolvername1)
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/assign",
                                    {"realm": self.realm4, "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_14_helpdesk_assign_user_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()

        # helpdesk of user realm realm3
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER, realm=self.realm3)

        # container in realm3, but new user from realm1
        container_serial = init_container({"type": "generic", "realm": self.realm3})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": self.realm1, "user": "hans", "resolver": self.resolvername1}, self.at)

        # container in realm1, new user from realm3
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": self.realm3, "user": "corny"}, self.at)
        delete_policy("policy")

        # helpdesk for resolver1
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER, realm=self.realm4,
                   resolver=self.resolvername1)
        # container without user, new user from resolver3
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": self.realm4, "user": "corny"}, self.at)
        # container in realm1, new user from resolver1
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/assign",
                                       {"realm": self.realm4, "user": "hans"}, self.at)
        delete_policy("policy")

    def test_15_helpdesk_remove_user_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_UNASSIGN_USER, realm=self.realm1)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/unassign",
                                    {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

        # Policy for realm and resolver
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_UNASSIGN_USER, realm=self.realm4,
                   resolver=self.resolvername3)
        container_serial = init_container({"type": "generic",
                                           "user": "corny",
                                           "realm": self.realm4,
                                           "resolver": self.resolvername3})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/unassign",
                                    {"realm": self.realm4, "user": "corny", "resolver": self.resolvername3}, self.at)
        delete_policy("policy")

        # Helpdesk for resolver3
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_UNASSIGN_USER,
                   resolver=self.resolvername1)
        # container is in realm1, user is from resolver1
        container_serial = init_container({"type": "generic",
                                           "user": "hans",
                                           "realm": self.realm1,
                                           "resolver": self.resolvername1})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}/unassign",
                                    {"realm": self.realm1, "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

    def test_16_helpdesk_remove_user_denied(self):
        self.setUp_user_realm2()

        # Helpdesk for realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_UNASSIGN_USER, realm=self.realm2)
        # container in realm1, user from realm1
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        # container is additionally in realm2, but user is still from realm1
        add_container_realms(container_serial, ["realm2"], allowed_realms=None)
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": "realm1", "user": "hans", "resolver": self.resolvername1}, self.at)
        delete_policy("policy")

        # Helpdesk for resolver3 in realm4
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_UNASSIGN_USER, realm=self.realm4,
                   resolver=self.resolvername3)
        # container and user in realm4, but user is from resolver1
        container_serial = init_container({"type": "generic",
                                           "user": "hans",
                                           "realm": self.realm4,
                                           "resolver": self.resolvername1})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": self.realm4, "user": "hans", "resolver": self.resolvername1}, self.at)
        # container is in realm3, user is from resolver3 (correct resolver, but wrong realm)
        container_serial = init_container({"type": "generic",
                                           "user": "corny",
                                           "realm": self.realm3,
                                           "resolver": self.resolvername3})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/unassign",
                                       {"realm": self.realm3, "user": "corny", "resolver": self.resolvername3}, self.at)
        delete_policy("policy")

    def test_17_helpdesk_container_realms_allowed(self):
        self.setUp_user_realm2()
        # Helpdesk for realm1 and realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REALMS, realm=[self.realm1, self.realm2])
        # container in realm1, add realm2
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        delete_policy("policy")

        # Helpdesk for resolver1 in realm1 and realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REALMS, realm=[self.realm1, self.realm2],
                   resolver=self.resolvername1)
        # container in realm1 and resolver1, add realm2
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        delete_policy("policy")

        # Helpdesk for resolver1 (is allowed to set all realms)
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REALMS, resolver=self.resolvername1)
        # container in realm1 and resolver1, add realm2
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": [self.realm1, self.realm2]},
                                    self.at)
        delete_policy("policy")

        # Helpdesk for realm1
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REALMS, realm=[self.realm1])
        # container in realm1, add realm2
        container_serial = self.create_container_for_user()
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": [self.realm1, self.realm2]},
                                    self.at)
        self.assertSetEqual({self.realm1}, set(get_container_realms(container_serial)))
        delete_policy("policy")

    def test_18_helpdesk_container_realms_denied(self):
        self.setUp_user_realm2()
        self.setUp_user_realm3()

        # helpdesk of user realm realm2
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REALMS, realm=self.realm2)

        # container in realm1
        container_serial = self.create_container_for_user()
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)

        # container in realm1, set realm3
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm3"}, self.at)
        delete_policy("policy")

        # Helpdesk for realm1
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REALMS, realm=self.realm1)

        # container in realm1, set realm2 (not allowed)
        result = self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2"}, self.at)
        self.assertFalse(result["result"]["value"]["realm2"])
        container = find_container_by_serial(container_serial)
        realms = [realm.name for realm in container.realms]
        self.assertSetEqual({self.realm1}, set(realms))

        # helpdesk of user realm realm1: container in realm1, set realm2 and realm1 (only realm1 allowed)
        result = self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm2,realm1"},
                                             self.at)
        self.assertFalse(result["result"]["value"]["realm2"])
        self.assertTrue(result["result"]["value"]["realm1"])

        # container in realm1 and realm2, set realm1 (removes realm2 not allowed)
        add_container_realms(container_serial, ["realm1", "realm2"], allowed_realms=None)
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        container = find_container_by_serial(container_serial)
        realms = [realm.name for realm in container.realms]
        self.assertEqual(2, len(realms))
        self.assertIn("realm1", realms)
        self.assertIn("realm2", realms)

        # container in no realm, set realm1
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        delete_policy("policy")

        # Helpdesk for realm1 and realm4 and resolver3
        self.setUp_user_realm4_with_2_resolvers()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REALMS, realm=[self.realm4, self.realm1],
                   resolver=self.resolvername3)
        # container of realm4  with user from resolver1
        container_serial = init_container({"type": "generic",
                                           "realm": self.realm4,
                                           "resolver": self.resolvername1,
                                           "user": "hans"})["container_serial"]
        self.request_denied_assert_403(f"/container/{container_serial}/realms", {"realms": "realm1"}, self.at)
        delete_policy("policy")

    def test_19_helpdesk_container_list_allowed(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_LIST, realm=self.realm1)
        self.request_assert_success('/container/', {}, self.at, 'GET')

        # container with token from another realm: reduce token info
        set_policy("policy2", scope=SCOPE.ADMIN, action=PolicyAction.TOKENLIST, realm=self.realm1)
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        token_1 = init_token({"genkey": 1, "realm": self.realm1})
        token_2 = init_token({"genkey": 1, "realm": self.realm2})
        add_token_to_container(container_serial, token_1.get_serial())
        add_token_to_container(container_serial, token_2.get_serial())
        result = self.request_assert_success('/container/', {"container_serial": container_serial}, self.at, 'GET')
        tokens = result["result"]["value"]["containers"][0]["tokens"]
        tokens_dict = {token["serial"]: token for token in tokens}
        # first token: all information
        self.assertEqual(token_1.get_serial(), tokens_dict[token_1.get_serial()]["serial"])
        self.assertEqual("hotp", tokens_dict[token_1.get_serial()]["tokentype"])
        # second token: only serial
        self.assertEqual(token_2.get_serial(), tokens_dict[token_2.get_serial()]["serial"])
        self.assertEqual(1, len(tokens_dict[token_2.get_serial()].keys()))
        self.assertNotIn("tokentype", tokens_dict[token_2.get_serial()].keys())

        delete_policy("policy")
        delete_policy("policy2")

    def helpdesk_container_register_allowed(self):
        container_serial = self.create_container_for_user("smartphone")
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REGISTER,
                   realm=[self.realm2, self.realm1])
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial}
        self.request_assert_success('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")
        return container_serial

    def test_20_helpdesk_container_register_allowed_2(self):
        self.helpdesk_container_register_allowed()

    def test_21_helpdesk_container_register_denied(self):
        container_serial = self.create_container_for_user("smartphone")
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})

        # Helpdesk does not have CONTAINER_REGISTER rights for the realm of the container
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REGISTER, realm=self.realm2)
        data = {"container_serial": container_serial}
        self.request_denied_assert_403('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_22_helpdesk_container_unregister_allowed(self):
        container_serial = self.helpdesk_container_register_allowed()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_UNREGISTER, realm=self.realm1)
        self.request_assert_success(f'/container/register/{container_serial}/terminate', {}, self.at, 'POST')
        delete_policy("policy")

    def test_23_helpdesk_container_unregister_denied(self):
        container_serial = self.helpdesk_container_register_allowed()
        # Admin does not have CONTAINER_UNREGISTER rights for the realm of the container (realm 1)
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_UNREGISTER, realm=self.realm2)
        self.request_denied_assert_403(f'/container/register/{container_serial}/terminate', {}, self.at, 'POST')
        delete_policy("policy")

    def test_24_helpdesk_container_rollover_allowed(self):
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                value=RegistrationState.REGISTERED.value,
                                                                info_type=PI_INTERNAL)])
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ROLLOVER, realm=self.realm1)
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        data = {"container_serial": container_serial, "rollover": True}
        self.request_assert_success('/container/register/initialize', data, self.at, 'POST')

        delete_policy("policy")
        delete_policy("container_policy")

    def test_25_helpdesk_container_rollover_denied(self):
        # Helpdesk has no CONTAINER_ROLLOVER rights for the realm of the container
        container_serial = self.create_container_for_user("smartphone")
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                value=RegistrationState.REGISTERED.value,
                                                                info_type=PI_INTERNAL)])
        set_policy("container_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test"})
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REGISTER, realm=self.realm2)
        data = {"container_serial": container_serial, "rollover": True}
        self.request_denied_assert_403('/container/register/initialize', data, self.at, 'POST')
        delete_policy("policy")
        delete_policy("container_policy")

    def test_26_helpdesk_compare_template_container(self):
        template_name = "test"
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={PolicyAction.CONTAINER_TEMPLATE_LIST: True, PolicyAction.CONTAINER_LIST: True},
                   realm=self.realm1)
        set_policy("admin", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)

        # Test with containers the user might not be allowed to see
        # Create containers with template
        request_params = json.dumps({"type": "smartphone", "template": template_params})

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        container_serial_no_user = result["result"]["value"]["container_serial"]

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        container_serial_user = result["result"]["value"]["container_serial"]
        container_user = find_container_by_serial(container_serial_user)
        container_user.add_user(User("selfservice", self.realm1))

        result = self.request_assert_success(f'/container/template/{template_name}/compare', {}, self.at, 'GET')
        containers = result["result"]["value"].keys()
        self.assertIn(container_serial_user, containers)
        self.assertNotIn(container_serial_no_user, containers)

        # Compare specific container
        # container of the user
        result = self.request_assert_success(f'/container/template/{template_name}/compare',
                                             {"container_serial": container_serial_user}, self.at_user, 'GET')
        containers = result["result"]["value"].keys()
        self.assertIn(container_serial_user, containers)
        self.assertNotIn(container_serial_no_user, containers)
        # container without user
        result = self.request_assert_success(f'/container/template/{template_name}/compare',
                                             {"container_serial": container_serial_no_user}, self.at_user, 'GET')
        containers = result["result"]["value"].keys()
        self.assertNotIn(container_serial_user, containers)
        self.assertNotIn(container_serial_no_user, containers)

        delete_policy("policy")
        delete_policy("admin")

        # Helpdesk has no container_list rights for the realm of the container
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={PolicyAction.CONTAINER_TEMPLATE_LIST: True, PolicyAction.CONTAINER_LIST: True},
                   realm=self.realm2)
        result = self.request_assert_success(f'/container/template/{template_name}/compare', {}, self.at, 'GET')
        containers = result["result"]["value"].keys()
        self.assertNotIn(container_serial_user, containers)
        self.assertNotIn(container_serial_no_user, containers)
        delete_policy("policy")

        get_template_obj("test").delete()

    def test_28_helpdesk_create_container_with_template_with_user(self):
        # admin is allowed to create container and enroll HOTP and TOTP tokens for realm 1
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={PolicyAction.CONTAINER_CREATE: True, "enrollHOTP": True, "enrollTOTP": True},
                   realm=self.realm1)

        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {
                               "tokens": [{"type": "totp", "genkey": True, "user": True},
                                          {"type": "hotp", "genkey": True},
                                          {"type": "spass"}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        request_params = json.dumps(
            {"type": "generic", "template": template_params, "user": "hans", "realm": self.realm1})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertSetEqual({"totp", "hotp"}, {token.get_type() for token in tokens})
        self.assertEqual(2, len(tokens))
        # check user of tokens
        for token in tokens:
            if token.get_tokentype() == "totp":
                self.assertEqual("hans", token.user.login)
                self.assertEqual(self.realm1, token.user.realm)
            elif token.get_tokentype() == "hotp":
                self.assertIsNone(token.user)
        container_template = container.template
        self.assertEqual(template_params["name"], container_template.name)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("policy")

    def test_29_helpdesk_create_container_with_template_with_realm(self):
        # admin is allowed to create container and enroll HOTP and TOTP tokens for realm 1
        set_policy("policy", scope=SCOPE.ADMIN,
                   action={PolicyAction.CONTAINER_CREATE: True, "enrollHOTP": True, "enrollTOTP": True},
                   realm=self.realm1)

        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {
                               "tokens": [{"type": "totp", "genkey": True, "user": True},
                                          {"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        request_params = json.dumps(
            {"type": "generic", "template": template_params, "realm": self.realm1})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertSetEqual({"totp", "hotp"}, {token.get_type() for token in tokens})
        self.assertEqual(2, len(tokens))
        # check realm of tokens
        for token in tokens:
            self.assertIsNone(token.user)
            realms = token.get_realms()
            if token.get_tokentype() == "totp":
                self.assertEqual(1, len(realms))
                self.assertEqual(self.realm1, realms[0])
            elif token.get_tokentype() == "hotp":
                self.assertEqual(0, len(realms))

        container_template = container.template
        self.assertEqual(template_params["name"], container_template.name)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("policy")

    def test_30_helpdesk_set_container_info_allowed(self):
        self.setUp_user_realm2()
        # policy for realms
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, realm=[self.realm1, self.realm2])
        self.request_assert_success(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                    method='POST')
        delete_policy("policy")

        # policy for resolver
        container_serial = self.create_container_for_user()
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                    method='POST')
        delete_policy("policy")

        # policy for user
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, user="selfservice",
                   realm=self.realm1, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/info/test", {"value": "1234"}, self.at,
                                    method='POST')
        delete_policy("policy")

    def test_31_helpdesk_set_container_info_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]

        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, realm=self.realm3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        delete_policy("policy")

        # policy for a resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, resolver=self.resolvername3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        delete_policy("policy")

        # policy for a user
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, user="hans", realm=self.realm1,
                   resolver=self.resolvername1)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/test", {"value": "1234"}, self.at,
                                       method='POST')
        delete_policy("policy")

    def test_32_helpdesk_delete_container_info_allowed(self):
        self.setUp_user_realm2()
        # policy for realms
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, realm=[self.realm1, self.realm2])
        self.request_assert_success(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                    method="DELETE")
        delete_policy("policy")

        # policy for resolver
        container_serial = self.create_container_for_user()
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                    method="DELETE")
        delete_policy("policy")

        # policy for user
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, user="selfservice",
                   realm=self.realm1, resolver=self.resolvername1)
        self.request_assert_success(f"/container/{container_serial}/info/delete/test", {}, self.at,
                                    method="DELETE")
        delete_policy("policy")

    def test_33_helpdesk_delete_container_info_denied(self):
        self.setUp_user_realm3()
        c_serial_user = self.create_container_for_user()
        container_user = find_container_by_serial(c_serial_user)
        container_user.update_container_info([TokenContainerInfoData(key="test", value="1234")])
        c_serial_no_user = init_container({"type": "generic"})["container_serial"]
        container_no_user = find_container_by_serial(c_serial_no_user)
        container_no_user.update_container_info([TokenContainerInfoData(key="test", value="1234")])

        # policy for a realm
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, realm=self.realm3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        delete_policy("policy")

        # policy for a resolver
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, resolver=self.resolvername3)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        delete_policy("policy")

        # policy for a user
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_INFO, user="hans", realm=self.realm1,
                   resolver=self.resolvername1)
        self.request_denied_assert_403(f"/container/{c_serial_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        self.request_denied_assert_403(f"/container/{c_serial_no_user}/info/delete/test", {}, self.at,
                                       method="DELETE")
        delete_policy("policy")
