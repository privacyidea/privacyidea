# (c) NetKnights GmbH 2026,  https://netknights.it
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
from privacyidea.lib.resolvers.PasswdIdResolver import IdResolver
from tests.base import MyTestCase, PWFILE


class PasswdResolverTest(MyTestCase):

    def setUp(self):
        super().setUp()
        self.resolver = IdResolver()
        # File contains an empty line
        config = {"fileName": PWFILE,
                  "type.fileName": "string",
                  "desc.fileName": "The name of the file"}
        self.resolver.loadConfig(config)

    def test_01_load_config_with_empty_file_name(self):
        # Create a resolver with an empty filename will use the filename /etc/passwd
        resolver = IdResolver()
        config = {"fileName": "",
                  "type.fileName": "string",
                  "desc.fileName": "The name of the file"}
        resolver.loadConfig(config)

        rid = resolver.getResolverId()
        self.assertEqual("/etc/passwd", rid)
        rtype = resolver.getResolverType()
        self.assertTrue(rtype == "passwdresolver", rtype)
        rdesc = resolver.getResolverDescriptor()
        self.assertIn("config", rdesc.get("passwdresolver"), rdesc)
        self.assertIn("clazz", rdesc.get("passwdresolver"), rdesc)

    def test_02_get_user_list(self):
        ulist = self.resolver.getUserList({"username": "*"})
        self.assertEqual(15, len(ulist), ulist)
        ulist = self.resolver.getUserList({"username": "hans"})
        self.assertEqual(1, len(ulist), ulist)

        # unknown search fields. We get an empty userlist
        users = self.resolver.getUserList({"blabla": "something"})
        self.assertListEqual([], users)
        # list exactly one user
        users = self.resolver.getUserList({"userid": "=1000"})
        self.assertEqual(1, len(users), users)
        users = self.resolver.getUserList({"userid": "<1001"})
        self.assertEqual(1, len(users), users)
        users = self.resolver.getUserList({"userid": ">1000"})
        self.assertGreater(len(users), 1, users)
        users = self.resolver.getUserList({"userid": "between 1000, 1001"})
        self.assertEqual(2, len(users), users)
        users = self.resolver.getUserList({"userid": "between 1001, 1000"})
        self.assertEqual(2, len(users), users)
        users = self.resolver.getUserList({"userid": "<=1000"})
        self.assertEqual(1, len(users), "{0!s}".format(users))
        users = self.resolver.getUserList({"userid": ">=1000"})
        self.assertGreater(len(users), 1, users)

        users = self.resolver.getUserList({"description": "field1"})
        self.assertEqual(0, len(users), users)
        users = self.resolver.getUserList({"description": "*field1*"})
        self.assertEqual(2, len(users), users)
        users = self.resolver.getUserList({"email": "field1"})
        self.assertEqual(0, len(users), users)
        users = self.resolver.getUserList({"email": "*field1*"})
        self.assertEqual(2, len(users), users)

    def test_03_check_password(self):
        self.assertTrue(self.resolver.checkPass("1000", "test"))
        self.assertFalse(self.resolver.checkPass("1000", "wrong password"))
        self.assertRaises(NotImplementedError, self.resolver.checkPass, "1001", "secret")
        self.assertFalse(self.resolver.checkPass("1002", "no pw at all"))

    def test_04_get_username(self):
        self.assertEqual("cornelius", self.resolver.getUsername("1000"))
        self.assertEqual("", self.resolver.getUsername("non-existing-uid"))

    def test_05_get_userid(self):
        self.assertEqual("1000", self.resolver.getUserId("cornelius"))
        self.assertEqual("", self.resolver.getUserId("non-existing-user"))

    def test_06_non_ascii_user(self):
        self.assertEqual("nönäscii", self.resolver.getUsername("1116"))
        self.assertEqual("1116", self.resolver.getUserId("nönäscii"))
        self.assertEqual("Nön", self.resolver.getUserInfo("1116").get('givenname'))
        self.assertFalse(self.resolver.checkPass("1116", "wrong"))
        self.assertTrue(self.resolver.checkPass("1116", "pässwörd"))
        r = self.resolver.getUserList({"username": "*ö*"})
        self.assertEqual(1, len(r))

    def test_07_get_search_fields(self):
        search_fields = self.resolver.get_search_fields({"username": "*"})
        self.assertEqual("text", search_fields.get("username"), search_fields)

    def test_08_string_match(self):
        self.assertTrue(self.resolver._string_match("Hallo", "*lo"))
        self.assertTrue(self.resolver._string_match("Hallo", "Hal*"))
        self.assertFalse(self.resolver._string_match("Duda", "Hal*"))
        self.assertTrue(self.resolver._string_match("HalloDuda", "*Du*"))
        self.assertTrue(self.resolver._string_match("Duda", "Duda"))

    def test_09_check_attribute(self):
        line = ["username", "crypt_pass", "id", "group", "description/email", "", ""]

        self.assertTrue(self.resolver.check_attribute(line, "username", "username"))
        self.assertFalse(self.resolver.check_attribute(line, "othername", "username"))
        self.assertFalse(self.resolver.check_attribute([], "username", "username"))

        self.assertTrue(self.resolver.check_attribute(line, "description*", "description"))
        self.assertFalse(self.resolver.check_attribute(line, "otherdescription", "otherdescription"))
        self.assertFalse(self.resolver.check_attribute(line[:3], "description*", "description"))

        self.assertTrue(self.resolver.check_attribute(line, "*email", "email"))
        self.assertFalse(self.resolver.check_attribute(line, "otheremail", "email"))
        self.assertFalse(self.resolver.check_attribute(line[:3], "*email", "email"))

        # unknown attribute name
        self.assertFalse(self.resolver.check_attribute(line, "somevalue", "unknownattribute"))
        self.assertFalse(self.resolver.check_attribute(line, "", "unknownattribute"))

    def test_10_get_user_info(self):
        user_info = self.resolver.getUserInfo("1001")
        self.assertEqual("shadow", user_info.get("username"))
        self.assertEqual("1001", user_info.get("userid"))
        self.assertEqual("x", user_info.get("cryptpass"))
        self.assertEqual("field1,field2,field3", user_info.get("description"))
        self.assertEqual("", user_info.get("email"))
        self.assertEqual("field1", user_info.get("givenname"))
        self.assertEqual("", user_info.get("surname"))
        self.assertEqual("", user_info.get("phone"))
        self.assertEqual("", user_info.get("mobile"))

        # Get unknown user
        user_info = self.resolver.getUserInfo("9999")
        self.assertDictEqual({}, user_info)