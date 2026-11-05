# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
The filters of the container queries and the container dictionaries: each filter of ``get_all_containers`` selects
exactly the containers it names.
"""
from typing import Any

from privacyidea.lib.container import (add_container_states, add_token_to_container, assign_user,
                                       create_container_dict, find_container_by_serial, get_all_containers,
                                       init_container, set_container_realms)
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.token import init_token
from privacyidea.lib.user import User
from privacyidea.models import TokenContainerOwner
from .base import MyTestCase, PWFILE, PWFILE2


class ContainerQueryFilterTestCase(MyTestCase):
    """
    All tests of this class work on the containers created in setUpClass, and scope their queries to those serials,
    so that containers another test left behind can not change the results.
    """

    serial_wildcard = "QC*"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        save_resolver({"resolver": cls.resolvername1, "type": "passwdresolver", "fileName": PWFILE})
        save_resolver({"resolver": cls.resolvername3, "type": "passwdresolver", "fileName": PWFILE2})
        # cornelius of the first and franzi of the second resolver have the same user id
        set_realm(cls.realm1, [{"name": cls.resolvername1, "priority": 1}, {"name": cls.resolvername3, "priority": 2}])
        set_realm(cls.realm2, [{"name": cls.resolvername1}])

        init_container({"type": "generic", "container_serial": "QC_CORNELIUS",
                        "description": "Mixed Case Description"})
        assign_user("QC_CORNELIUS", User("cornelius", cls.realm1, cls.resolvername1))
        init_container({"type": "generic", "container_serial": "QC_FRANZI"})
        assign_user("QC_FRANZI", User("franzi", cls.realm1, cls.resolvername3))
        add_container_states("QC_FRANZI", ["lost"])
        init_container({"type": "smartphone", "container_serial": "QC_SMARTPHONE"})
        set_container_realms("QC_SMARTPHONE", [cls.realm2], allowed_realms=None)
        token = init_token({"type": "hotp", "genkey": 1, "serial": "QCTOKEN01"})
        token.add_tokeninfo("hiddenkey", "not for everyone")
        add_token_to_container("QC_SMARTPHONE", "QCTOKEN01")

    def serials(self, **filters: Any) -> set[str]:
        return {container.serial
                for container in get_all_containers(serial=self.serial_wildcard, **filters)["containers"]}

    def test_01_the_user_filter_applies_the_resolver_of_the_user(self):
        # The owners of both containers have the same user id in different resolvers of the realm
        self.assertSetEqual({"QC_CORNELIUS"}, self.serials(user=User("cornelius", self.realm1, self.resolvername1)))
        self.assertSetEqual({"QC_FRANZI"}, self.serials(user=User("franzi", self.realm1, self.resolvername3)))

    def test_02_exact_filters_ignore_the_case(self):
        self.assertSetEqual({"QC_CORNELIUS", "QC_FRANZI"}, self.serials(ctype="GENERIC"))
        self.assertSetEqual({"QC_SMARTPHONE"}, self.serials(token_serial="qctoken01"))
        self.assertSetEqual({"QC_SMARTPHONE"}, self.serials(allowed_realms=[self.realm2.upper()]))
        self.assertSetEqual({"QC_FRANZI"}, self.serials(resolver=self.resolvername3.upper()))
        self.assertSetEqual({"QC_CORNELIUS"}, self.serials(description="mixed case description"))
        self.assertSetEqual({"QC_FRANZI"}, self.serials(state="LOST"))

    def test_03_the_last_page_has_no_next_page(self):
        result = get_all_containers(serial=self.serial_wildcard, page=1, pagesize=3)
        self.assertEqual(3, result["count"], result)
        self.assertIsNone(result["next"], result)
        result = get_all_containers(serial=self.serial_wildcard, page=1, pagesize=2)
        self.assertEqual(2, result["next"], result)
        result = get_all_containers(serial=self.serial_wildcard, page=2, pagesize=2)
        self.assertIsNone(result["next"], result)
        self.assertEqual(1, result["prev"], result)

    def test_04_the_container_dict_hides_the_token_info(self):
        container = find_container_by_serial("QC_SMARTPHONE")
        token = create_container_dict([container], logged_in_user_role="admin")[0]["tokens"][0]
        self.assertIn("hiddenkey", token["info"], token)
        token = create_container_dict([container], logged_in_user_role="admin", hide_token_info=["hiddenkey"])[0][
            "tokens"][0]
        self.assertNotIn("hiddenkey", token["info"], token)


class ContainerPaginationTestCase(MyTestCase):
    """
    A container is counted and paged once, however many of its realms or owners match the filters.
    """

    serial_wildcard = "QP*"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        save_resolver({"resolver": cls.resolvername1, "type": "passwdresolver", "fileName": PWFILE})
        set_realm(cls.realm1, [{"name": cls.resolvername1}])
        set_realm(cls.realm2, [{"name": cls.resolvername1}])
        for serial, realms in [("QP_A", [cls.realm1, cls.realm2]), ("QP_B", [cls.realm1, cls.realm2]),
                               ("QP_C", [cls.realm1])]:
            init_container({"type": "generic", "container_serial": serial})
            set_container_realms(serial, realms, allowed_realms=None)
        user = User("cornelius", cls.realm1, cls.resolvername1)
        assign_user("QP_A", user)
        assign_user("QP_B", user)
        # The database does not prevent a second owner row, only assign_user does
        TokenContainerOwner(container_serial="QP_A", resolver=user.resolver,
                            user_id=user.uid, realm_id=user.realm_id).save()

    def assert_paged_once(self, expected_pages: list[list[str]] | None = None, **filters: Any) -> None:
        if expected_pages is None:
            expected_pages = [["QP_A", "QP_B"], ["QP_C"]]
        pages = []
        for page in range(1, len(expected_pages) + 1):
            result = get_all_containers(serial=self.serial_wildcard, page=page, pagesize=2, **filters)
            self.assertEqual(sum(len(serials) for serials in expected_pages), result["count"], result)
            pages.append([container.serial for container in result["containers"]])
        self.assertListEqual(expected_pages, pages)

    def test_01_allowed_realms(self):
        self.assert_paged_once(allowed_realms=[self.realm1, self.realm2])

    def test_02_realm_wildcard(self):
        self.assert_paged_once(realm="realm*")

    def test_03_realm_wildcard_and_allowed_realms(self):
        self.assert_paged_once(realm="realm*", allowed_realms=[self.realm1, self.realm2])

    def test_04_user_with_two_owner_rows(self):
        self.assert_paged_once([["QP_A", "QP_B"]], user=User("cornelius", self.realm1, self.resolvername1))
        self.assert_paged_once([["QP_A", "QP_B"]], user=User(realm=self.realm1))

    def test_05_the_container_id_orders_equal_sort_values(self):
        # All containers have the same type, so only the id gives the pages a fixed order
        self.assert_paged_once(sortby="type")
        self.assert_paged_once([["QP_C", "QP_B"], ["QP_A"]], sortby="type", sortdir="desc")


class ContainerOwnerFilterTestCase(MyTestCase):
    """
    The database allows several owners for one container: the user filter and the resolver filter apply to the same
    owner.
    """

    serial_wildcard = "QO*"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        save_resolver({"resolver": cls.resolvername1, "type": "passwdresolver", "fileName": PWFILE})
        save_resolver({"resolver": cls.resolvername3, "type": "passwdresolver", "fileName": PWFILE2})
        set_realm(cls.realm1, [{"name": cls.resolvername1}])
        set_realm(cls.realm2, [{"name": cls.resolvername3}])
        init_container({"type": "generic", "container_serial": "QO_TWO_OWNERS"})
        assign_user("QO_TWO_OWNERS", User("cornelius", cls.realm1, cls.resolvername1))
        # assign_user refuses a second owner, so the second owner row is written directly
        franzi = User("franzi", cls.realm2, cls.resolvername3)
        TokenContainerOwner(container_serial="QO_TWO_OWNERS", resolver=franzi.resolver, user_id=franzi.uid,
                            realm_id=franzi.realm_id).save()

    def serials(self, **filters: Any) -> set[str]:
        return {container.serial
                for container in get_all_containers(serial=self.serial_wildcard, **filters)["containers"]}

    def test_01_each_owner_matches_its_own_realm_and_resolver(self):
        self.assertSetEqual({"QO_TWO_OWNERS"}, self.serials(resolver=self.resolvername3))
        self.assertSetEqual({"QO_TWO_OWNERS"}, self.serials(user=User(realm=self.realm1), resolver=self.resolvername1))
        self.assertSetEqual({"QO_TWO_OWNERS"}, self.serials(user=User(realm=self.realm2), resolver="*3"))
        self.assertSetEqual({"QO_TWO_OWNERS"},
                            self.serials(user=User("franzi", self.realm2, self.resolvername3),
                                         resolver=self.resolvername3))

    def test_02_no_owner_matches_the_realm_of_one_owner_and_the_resolver_of_the_other(self):
        self.assertSetEqual(set(), self.serials(user=User(realm=self.realm1), resolver=self.resolvername3))
        self.assertSetEqual(set(), self.serials(user=User(realm=self.realm2), resolver=self.resolvername1))
        self.assertSetEqual(set(), self.serials(user=User(realm=self.realm1), resolver="*3"))
        self.assertSetEqual(set(), self.serials(user=User("cornelius", self.realm1, self.resolvername1),
                                                resolver=self.resolvername3))
