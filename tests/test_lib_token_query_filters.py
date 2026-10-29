# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
The filters of the token queries: each filter of ``get_tokens`` selects exactly the tokens it names, and the
paginated generator the token janitors use applies the same filters.
"""
from typing import Any

import mock

from privacyidea.lib.error import PrivacyIDEAError
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.resolvers.PasswdIdResolver import IdResolver as PasswdResolver
from privacyidea.lib.token import (check_serial, convert_token_objects_to_dicts, get_one_token, get_tokens,
                                   get_tokens_paginate, get_tokens_paginated_generator, init_token)
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models import db, TokenOwner
from .base import MyTestCase, PWFILE, PWFILE2


class TokenQueryFilterTestCase(MyTestCase):
    """
    All tests of this class work on the tokens enrolled in setUpClass, and scope their queries to those serials, so
    that tokens another test left behind can not change the results.
    """

    serial_wildcard = "QF*"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        save_resolver({"resolver": cls.resolvername1, "type": "passwdresolver", "fileName": PWFILE})
        save_resolver({"resolver": cls.resolvername3, "type": "passwdresolver", "fileName": PWFILE2})
        # cornelius of the first and franzi of the second resolver have the same user id
        set_realm(cls.realm1, [{"name": cls.resolvername1}, {"name": cls.resolvername3}])
        set_realm(cls.realm2, [{"name": cls.resolvername1}])

        def enroll(serial: str, token_type: str = "hotp", user: User | None = None, **columns: Any) -> TokenClass:
            token = init_token({"type": token_type, "genkey": 1, "serial": serial}, user=user)
            for column, value in columns.items():
                setattr(token.token, column, value)
            db.session.commit()
            return token

        enroll("QFPLAIN")
        enroll("QFTOTP", token_type="totp")
        # Only the one flag, so that the filters of the flags can not stand in for each other
        enroll("QFREVOKED", revoked=True)
        enroll("QFLOCKED", locked=True)
        enroll("QFBELOWMAX", failcount=2, maxfail=3)
        enroll("QFATMAX", failcount=3, maxfail=3)
        enroll("QFOVERMAX", failcount=4, maxfail=3)
        # In mixed case, so that the filters have to ignore the case on both sides
        enroll("QFROLLOUT", rollout_state="ClientWait")
        enroll("QFDESC", description="Mixed Case Description")
        enroll("QFINFO").add_tokeninfo("queryfilter", "a_b%c")
        enroll("QFINFOKEY").add_tokeninfo("otherkey", "a_b%c")
        # Matched by the value above if "_" and "%" acted as wildcards
        enroll("QFINFOLIKE").add_tokeninfo("queryfilter", "aXbYYc")
        enroll("QFCORNELIUS", user=User("cornelius", cls.realm1, cls.resolvername1))
        enroll("QFFRANZI", user=User("franzi", cls.realm1, cls.resolvername3))
        # Owned by a user the resolver does not know (any more)
        unknown_owner_token = enroll("QFUNKNOWN")
        TokenOwner(token_id=unknown_owner_token.token.id, user_id="999999", resolver=cls.resolvername1,
                   realmname=cls.realm1).save()

    def serials(self, **filters: Any) -> set[str]:
        return {token.token.serial for token in get_tokens(serial_wildcard=self.serial_wildcard, **filters)}

    def test_01_revoked_and_locked(self):
        self.assertSetEqual({"QFREVOKED"}, self.serials(revoked=True))
        not_revoked = self.serials(revoked=False)
        self.assertNotIn("QFREVOKED", not_revoked)
        self.assertTrue({"QFPLAIN", "QFLOCKED"} <= not_revoked, not_revoked)

        self.assertSetEqual({"QFLOCKED"}, self.serials(locked=True))
        not_locked = self.serials(locked=False)
        self.assertNotIn("QFLOCKED", not_locked)
        self.assertTrue({"QFPLAIN", "QFREVOKED"} <= not_locked, not_locked)

    def test_02_maxfail_counts_a_token_at_its_limit(self):
        self.assertSetEqual({"QFATMAX", "QFOVERMAX"}, self.serials(maxfail=True))
        below_the_limit = self.serials(maxfail=False)
        self.assertTrue({"QFPLAIN", "QFBELOWMAX"} <= below_the_limit, below_the_limit)
        self.assertFalse({"QFATMAX", "QFOVERMAX"} & below_the_limit, below_the_limit)

    def test_03_tokeninfo_matches_key_and_exact_value(self):
        # Neither a token with the value under another key nor one that matches only if "_" and "%" were
        # wildcards is returned
        self.assertSetEqual({"QFINFO"}, self.serials(tokeninfo={"queryfilter": "a_b%c"}))
        self.assertSetEqual({"QFINFOLIKE"}, self.serials(tokeninfo={"queryfilter": "aXbYYc"}))
        self.assertSetEqual(set(), self.serials(tokeninfo={"queryfilter": "a_b"}))

        # Exactly one key and value can be filtered by
        with self.assertRaises(PrivacyIDEAError):
            get_tokens(tokeninfo={})
        with self.assertRaises(PrivacyIDEAError):
            get_tokens(tokeninfo={"queryfilter": "a_b%c", "otherkey": "a_b%c"})

    def test_04_filters_ignore_the_case(self):
        self.assertSetEqual({"QFTOTP"}, self.serials(tokentype="TOTP"))
        self.assertSetEqual({"QFTOTP"}, self.serials(tokentype="T*P"))
        self.assertSetEqual({"QFTOTP"}, self.serials(token_type_list=["TOTP"]))
        self.assertSetEqual({"QFROLLOUT"}, self.serials(rollout_state="CLIENTWAIT"))
        self.assertSetEqual({"QFROLLOUT"}, self.serials(rollout_state="CLIENT*"))
        self.assertSetEqual({"QFFRANZI"}, self.serials(resolver=self.resolvername3.upper()))
        self.assertSetEqual({"QFFRANZI"}, self.serials(resolver="RES*3"))
        for description in ("mixed case description", "MIXED*"):
            result = get_tokens_paginate(serial=self.serial_wildcard, description=description)
            self.assertListEqual(["QFDESC"], [token["serial"] for token in result["tokens"]], description)

    def test_05_the_user_filter_applies_the_resolver_of_the_user(self):
        # The owners of both tokens have the same user id in different resolvers of the realm
        self.assertSetEqual({"QFCORNELIUS"}, self.serials(user=User("cornelius", self.realm1, self.resolvername1)))
        self.assertSetEqual({"QFFRANZI"}, self.serials(user=User("franzi", self.realm1, self.resolvername3)))
        self.assertSetEqual({"QFCORNELIUS", "QFFRANZI"}, self.serials(userid="1000"))

    def test_06_the_generator_applies_the_same_filters(self):
        for filters in ({"revoked": True}, {"locked": False}, {"maxfail": True}, {"maxfail": False},
                        {"tokeninfo": {"queryfilter": "a_b%c"}}, {"rollout_state": "clientwait"},
                        {"tokentype": "totp"}, {"assigned": True}, {"resolver": self.resolvername3},
                        {"realm": self.realm1}, {"user": User("cornelius", self.realm1, self.resolvername1)}):
            expected = self.serials(**filters)
            self.assertTrue(expected, filters)
            generated = {token.token.serial
                         for chunk in get_tokens_paginated_generator(serial_wildcard=self.serial_wildcard, psize=2,
                                                                     **filters)
                         for token in chunk}
            self.assertSetEqual(expected, generated, filters)

    def test_07_user_editable_follows_the_resolver(self):
        def user_editable() -> bool:
            return get_tokens_paginate(serial="QFCORNELIUS")["tokens"][0]["user_editable"]

        self.assertFalse(user_editable())
        with mock.patch.object(PasswdResolver, "editable", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(user_editable())

    def test_08_an_owner_the_resolver_does_not_know_has_an_empty_login(self):
        token = get_tokens_paginate(serial="QFUNKNOWN")["tokens"][0]
        self.assertEqual("", token["username"], token)
        self.assertEqual("999999", token["user_id"], token)

    def test_09_a_user_sees_the_details_of_own_tokens_only(self):
        tokens = get_tokens(serial_wildcard=self.serial_wildcard, assigned=True)
        cornelius = User("cornelius", self.realm1, self.resolvername1)

        token_dicts = {token["serial"]: token for token in convert_token_objects_to_dicts(tokens, user=cornelius)}
        self.assertEqual("cornelius", token_dicts["QFCORNELIUS"]["username"], token_dicts)
        # The token of franzi, who has the same user id in another resolver, shows only its serial
        self.assertDictEqual({"serial": "QFFRANZI"}, token_dicts["QFFRANZI"])

        # The same login name in another realm is another user
        cornelius_of_realm2 = User("cornelius", self.realm2)
        token_dicts = {token["serial"]: token
                       for token in convert_token_objects_to_dicts(tokens, user=cornelius_of_realm2)}
        self.assertDictEqual({"serial": "QFCORNELIUS"}, token_dicts["QFCORNELIUS"])

        # Without a user, every token shows only its serial
        token_dicts = convert_token_objects_to_dicts(tokens, user=None)
        self.assertTrue(all(token == {"serial": token["serial"]} for token in token_dicts), token_dicts)

    def test_10_one_token(self):
        self.assertEqual("QFPLAIN", get_one_token(serial="QFPLAIN").token.serial)
        # Several matching tokens are no single token
        self.assertIsNone(get_one_token(serial_wildcard=self.serial_wildcard, silent_fail=True))
        self.assertIsNone(get_one_token(serial="QFNOTHERE", silent_fail=True))

    def test_11_check_serial_suggests_a_numbered_serial(self):
        self.assertTupleEqual((False, "QFPLAIN_01"), check_serial("QFPLAIN"))
        self.assertTupleEqual((True, "QFNOTHERE"), check_serial("QFNOTHERE"))
