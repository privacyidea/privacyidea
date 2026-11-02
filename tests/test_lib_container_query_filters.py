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
