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
# SPDX-License-Identifier: AGPL-3.0-or-later
#
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, SCOPE
from tests.base import MyApiTestCase


class LoginTestCase(MyApiTestCase):

    def test_01_get_ui_config_defaults(self):
        """Test fetching the UI configuration"""
        with self.app.test_request_context("/config",
                                           method="GET"):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            config = result.get("value")
            expected_entries = {"instance", "backendUrl", "browser_lang", "remote_user", "force_remote_user", "theme",
                                "translation_warning", "password_reset", "hsm_ready", "has_job_queue", "customization",
                                "custom_css", "customization_menu_file", "customization_baseline_file", "realms",
                                "show_node", "external_links", "login_text", "gdpr_link", "logo", "page_title",
                                "otp_pin_set_random_user"}
            self.assertSetEqual(expected_entries, set(config.keys()))

            self.assertEqual("static/customize", config["customization"])
            self.assertEqual("", config["custom_css"])
            self.assertEqual("privacyIDEA1.png", config["logo"])
            self.assertEqual("privacyIDEA Authentication System", config["page_title"])
            self.assertEqual("", config["realms"])
            self.assertEqual("", config["show_node"])
            self.assertEqual("templates/menu.html", config["customization_menu_file"])
            self.assertEqual("templates/baseline.html", config["customization_baseline_file"])
            self.assertEqual("", config["login_text"])

    def test_02_get_ui_config_custom_values(self):
        self.app.config['PI_CUSTOMIZATION'] = '/my/custom/path'
        self.app.config["PI_LOGO"] = 'mylogo.png'
        self.app.config["PI_PAGE_TITLE"] = 'My Custom Title'

        set_policy("ui", scope=SCOPE.WEBUI,
                   action=f"{PolicyAction.REALMDROPDOWN}=realm1 realm2,{PolicyAction.SHOW_NODE},"
                          f"{PolicyAction.CUSTOM_MENU}=myMenu.html,{PolicyAction.LOGIN_TEXT}=Please log in")

        with self.app.test_request_context("/config",
                                           method="GET"):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            config = result.get("value")

            self.assertEqual("my/custom/path", config["customization"])
            self.assertEqual("", config["custom_css"])
            self.assertEqual("mylogo.png", config["logo"])
            self.assertEqual("My Custom Title", config["page_title"])
            self.assertEqual("realm1,realm2", config["realms"])
            self.assertEqual("Node1", config["show_node"])
            self.assertEqual("myMenu.html", config["customization_menu_file"])
            self.assertEqual("templates/baseline.html", config["customization_baseline_file"])
            self.assertEqual("Please log in", config["login_text"])
