from .base import MyTestCase

from privacyidea.lib.error import PolicyError
from privacyidea.lib.clients import create_client
from privacyidea.lib.policies.conditions import PolicyConditionClass, ConditionSection


class ClientConditionTestCase(MyTestCase):
    """
    Tests for the 'client' policy condition section, which matches on the
    attributes of the API client identified by the X-API-Key header.
    """

    def _client_id(self, client_type="windows_cp"):
        client, _key = create_client("cond client", client_type)
        return client.id

    def test_01_match_by_client_type(self):
        client_id = self._client_id("windows_cp")
        cond = PolicyConditionClass(ConditionSection.CLIENT, "client_type", "equals", "windows_cp", True)
        self.assertTrue(cond.match("p", None, None, None, client_id=client_id))

        cond = PolicyConditionClass(ConditionSection.CLIENT, "client_type", "equals", "keycloak", True)
        self.assertFalse(cond.match("p", None, None, None, client_id=client_id))

    def test_02_match_by_id(self):
        client_id = self._client_id()
        cond = PolicyConditionClass(ConditionSection.CLIENT, "id", "equals", client_id, True)
        self.assertTrue(cond.match("p", None, None, None, client_id=client_id))

    def test_03_unknown_key_raises_by_default(self):
        client_id = self._client_id()
        cond = PolicyConditionClass(ConditionSection.CLIENT, "nonexistent", "equals", "x", True)
        self.assertRaises(PolicyError, cond.match, "p", None, None, None, client_id=client_id)

    def test_04_missing_client_default_raises(self):
        # No client on the request (client_id=None) with the default
        # handle_missing_data (raise_error) -> PolicyError.
        cond = PolicyConditionClass(ConditionSection.CLIENT, "client_type", "equals", "windows_cp", True)
        self.assertRaises(PolicyError, cond.match, "p", None, None, None, client_id=None)

    def test_05_missing_client_condition_is_false(self):
        # The recommended setting for a client condition: requests without an
        # API client simply do not match, instead of raising.
        cond = PolicyConditionClass(ConditionSection.CLIENT, "client_type", "equals", "windows_cp", True,
                                    handle_missing_data="condition_is_false")
        self.assertFalse(cond.match("p", None, None, None, client_id=None))

    def test_06_client_is_a_known_section(self):
        self.assertIn("client", ConditionSection.get_all_sections())
