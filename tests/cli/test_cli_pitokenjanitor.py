# SPDX-FileCopyrightText: (C) 2024 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.
import datetime

import pytest
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.cli.pitokenjanitor.main import cli
from privacyidea.lib.container import find_container_by_serial, init_container
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.lib.realm import set_realm, get_realms
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.token import init_token, get_one_token
from privacyidea.lib.user import User
from privacyidea.models import db


@pytest.fixture(scope="module")
def app():
    """Create and configure app instance for testing"""
    app = create_app(config_name="testing", config_file="", silent=True)
    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        call_finalizers()
        close_all_sessions()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture(scope="module")
def resolver(app):
    """Create a user resolver"""
    with app.app_context():
        rid = save_resolver({"resolver": "testresolver",
                             "type": "passwdresolver",
                             "fileName": "tests/testdata/passwords"})
        assert rid > 0
        return rid


@pytest.fixture(scope="module")
def realms(app, resolver):
    with app.app_context():
        r1 = set_realm(realm="realm1", resolvers=[{"name": "testresolver"}])
        r2 = set_realm(realm="realm2", resolvers=[{"name": "testresolver"}])
        r1 = get_realms(realmname="realm1")
        r2 = get_realms(realmname="realm2")
        db.session.commit()
        return [r1, r2]


@pytest.fixture(scope="module")
def users(app, realms, resolver):
    with app.app_context():
        u1 = User(login="cornelius", realm="realm1")
        u2 = User(login="hans", realm="realm2")
        db.session.commit()
        return [u1, u2]


@pytest.fixture(scope="function")
def tokens(app, users):
    with app.app_context():
        t1 = init_token(param={
            "serial": "HOTP0001",
            "type": "hotp", },
            user=users[0]
        )
        t1.add_tokeninfo(key="info1", value="value1")
        t1.add_tokeninfo(key='date', value=datetime.datetime(2020, 1, 1))
        t1.token.active = True
        t1.token.failcount = 5

        t2 = init_token(param={
            "serial": "TOTP0001",
            "type": "totp", }
            ,
            user=users[1]
        )
        t2.add_tokeninfo(key="info2", value="value2")
        t2.add_tokeninfo(key='date', value=datetime.datetime(2022, 1, 1))
        t2.token.active = False
        t2.token.failcount = 10

        t3 = init_token(param={
            "serial": "HOTP0002",
            "type": "hotp", }
        )
        t3.token.active = True
        t3.token.failcount = 0
        db.session.commit()
        yield [t1, t2, t3]


@pytest.fixture(scope="function")
def token_container(app, tokens):
    container_dict = init_container({"type": "generic",
                                     "container_serial": "container1",
                                     "description": "test container"})
    db.session.commit()
    container = find_container_by_serial(serial=container_dict["container_serial"])

    # Re-fetch the token to attach it to the current session
    token_in_session = get_one_token(serial=tokens[0].token.serial)

    # tokens[0] is HOTP0001
    ret = container.add_token(token_in_session)
    assert ret is True
    db.session.commit()
    return container


class TestPiTokenJanitorFind:
    def test_find_no_args(self, app, tokens):
        """
        Tests that `find list` with no arguments returns all tokens.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" in result.output
        assert "HOTP0002" in result.output

    def test_find_filter_by_tokenattribute_tokentype(self, app, tokens):
        """
        Tests filtering tokens by tokentype using the --tokenattribute option.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokenattribute", "tokentype=hotp", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" in result.output

    def test_find_filter_by_active(self, app, tokens):
        """
        Tests filtering tokens by their active status.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--active", "True", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" in result.output

    def test_find_filter_by_assigned(self, app, tokens):
        """
        Tests filtering tokens by their assignment status.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--assigned", "True", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" in result.output
        assert "HOTP0002" not in result.output

    def test_find_filter_by_tokeninfo(self, app, tokens):
        """
        Tests filtering tokens by their tokeninfo.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokeninfo", "info1=value1", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" not in result.output

    def test_find_filter_by_owner(self, app, tokens, users):
        """
        Tests filtering tokens by their owner's login name.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokenowner", f"login={users[0].login}", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" not in result.output

    def test_find_summarize(self, app, tokens):
        """
        Tests the summarize option of the list command.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "list", "--summarize"])
        assert result.exit_code == 0
        assert "cornelius" in result.output
        assert "hans" in result.output
        assert "N/A" in result.output  # For unassigned token
        # Check that each user has one token, and there is one unassigned token
        assert result.output.count(",1") == 3

    def test_find_chunksize(self, app, tokens):
        """
        Tests that the chunksize option does not affect the output.
        """
        runner = app.test_cli_runner()
        result_no_chunk = runner.invoke(cli, ["find", "list"])
        assert result_no_chunk.exit_code == 0
        result_chunked = runner.invoke(cli, ["find", "--chunksize", "1", "list"])
        assert result_chunked.exit_code == 0
        output_no_chunk = sorted(result_no_chunk.output.strip().split('\n'))
        output_chunked = sorted(result_chunked.output.strip().split('\n'))
        assert output_no_chunk == output_chunked

    def test_find_has_tokeninfo_key(self, app, tokens):
        """
        Tests filtering tokens by the presence of a tokeninfo key.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--has-tokeninfo-key", "info1", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" not in result.output

    def test_find_has_not_tokeninfo_key(self, app, tokens):
        """
        Tests filtering tokens by the absence of a tokeninfo key.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--has-not-tokeninfo-key", "info1", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" not in result.output
        assert "TOTP0001" in result.output
        assert "HOTP0002" in result.output

    def test_find_range_of_serial(self, app, tokens):
        """
        Tests filtering tokens by a range of serial numbers.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--range-of-serial", "HOTP0001-HOTP0002", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" in result.output

    # def test_find_tokencontainer(self, app, tokens, token_container):
    #    """
    #    Tests filtering tokens by their container.
    #    """
    #    runner = app.test_cli_runner()
    #    result = runner.invoke(cli, ["find", "--tokencontainer", "serial=container1", "list"])
    #    assert result.exit_code == 0
    #    assert "HOTP0001" in result.output
    #    assert "TOTP0001" not in result.output
    #    assert "HOTP0002" not in result.output

    def test_find_filter_comparisons(self, app, tokens):
        """
        Tests filtering with different comparators like >, <, !, and regex.
        This tests _compare_greater_than, _compare_less_than, _compare_not,
        _compare_regex_or_equal, _try_convert_to_integer, and _try_convert_to_datetime.
        """
        runner = app.test_cli_runner()

        # Test _compare_greater_than with integers (_try_convert_to_integer)
        result = runner.invoke(cli, ["find", "--tokenattribute", "failcount > 3", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" in result.output
        assert "HOTP0002" not in result.output

        # Test _compare_less_than with integers (_try_convert_to_integer)
        result = runner.invoke(cli, ["find", "--tokenattribute", "failcount < 6", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" in result.output

        # Test _compare_regex_or_equal with integer
        result = runner.invoke(cli, ["find", "--tokenattribute", "failcount = 5", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" not in result.output

        # Test _compare_not with integer
        result = runner.invoke(cli, ["find", "--tokenattribute", "failcount ! 5", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" not in result.output
        assert "TOTP0001" in result.output
        assert "HOTP0002" in result.output

        # Test _compare_regex_or_equal with regex
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial = ^HOTP", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" in result.output

        # Test _compare_not with regex
        result = runner.invoke(cli, ["find", "--tokenattribute", "tokentype ! hotp", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" not in result.output
        assert "TOTP0001" in result.output
        assert "HOTP0002" not in result.output

        # Test _compare_after (_try_convert_to_datetime)
        result = runner.invoke(cli, ["find", "list"])
        result = runner.invoke(cli, ["find", "--tokeninfo", "date > 2021-01-01", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" not in result.output
        assert "TOTP0001" in result.output

        # Test _compare_before (_try_convert_to_datetime)
        result = runner.invoke(cli, ["find", "--tokeninfo", "date < 2021-01-01", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output


class TestPiTokenJanitorActions:
    def test_list_token_attributes(self, app, tokens):
        """
        Tests listing specific token attributes using the -t option.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "list", "-t", "tokentype", "-t", "active"])
        assert result.exit_code == 0
        assert "'active': 'True'" in result.output
        assert "'tokentype': 'hotp'" in result.output
        assert "'hashlib': 'sha1'" not in result.output

    def test_list_user_attributes(self, app, tokens, users):
        """
        Tests listing specific user attributes using the -u option.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "list", "-u", "username", "-u", "realm"])
        assert result.exit_code == 0
        assert f"'username': '{users[0].login}'" in result.output
        assert f"'username': '{users[1].login}'" in result.output
        assert f"'realm': '{users[0].realm}'" in result.output
        assert f"'realm': '{users[1].realm}'" in result.output
        assert "'user': {}" in result.output  # For unassigned token

    def test_list_summarize_with_attributes(self, app, tokens):
        """
        Tests summarizing the output.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "list", "-s"])
        assert result.exit_code == 0
        assert "testresolver" in result.output
        assert "realm1" in result.output
        assert "cornelius" in result.output
        assert "N/A" in result.output
        assert "tokentype" not in result.output

    def test_set_tokenrealms(self, app, tokens):
        """
        Tests setting token realms.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=HOTP0001", "set_tokenrealms", "--tokenrealm",
                                     "realm1", "--tokenrealm", "realm2"])
        assert result.exit_code == 0
        assert "Setting realms of token HOTP0001 to ['realm1', 'realm2']" in result.output

        with app.app_context():
            token = get_one_token(serial="HOTP0001")
            assert sorted(token.get_realms()) == sorted(['realm1', 'realm2'])

    def test_disable(self, app, tokens):
        """
        Tests disabling a token.
        """
        runner = app.test_cli_runner()
        # HOTP0001 is active by default in the fixtures
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=HOTP0001", "disable"])
        assert result.exit_code == 0
        assert "Disabled token HOTP0001" in result.output

        with app.app_context():
            token = get_one_token(serial="HOTP0001")
            assert token.token.active is False

    def test_enable(self, app, tokens):
        """
        Tests enabling a token.
        """
        runner = app.test_cli_runner()
        # TOTP0001 is inactive by default in the fixtures
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=TOTP0001", "enable"])
        assert result.exit_code == 0
        assert "Enabled token TOTP0001" in result.output

        with app.app_context():
            token = get_one_token(serial="TOTP0001")
            assert token.token.active is True

    def test_delete(self, app, tokens):
        """
        Tests deleting a token.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=HOTP0002", "delete"])
        assert result.exit_code == 0
        assert "Deleted token HOTP0002" in result.output

        with app.app_context():
            token = get_one_token(serial="HOTP0002", silent_fail=True)
            assert token is None

    def test_unassign(self, app, tokens):
        """
        Tests unassigning a token.
        """
        runner = app.test_cli_runner()
        with app.app_context():
            token = get_one_token(serial="HOTP0001")
            assert token.user.login == 'cornelius'

        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=HOTP0001", "unassign"])
        assert result.exit_code == 0
        assert "Unassigned token HOTP0001" in result.output

        with app.app_context():
            token = get_one_token(serial="HOTP0001")
            assert token.user is None

    def test_set_description(self, app, tokens):
        """
        Tests setting the description of a token.
        """
        runner = app.test_cli_runner()
        description = "This is a test description"
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=HOTP0001", "set_description", "--description",
                                     description])
        assert result.exit_code == 0
        assert f"Set description for token HOTP0001: {description}" in result.output

        with app.app_context():
            token = get_one_token(serial="HOTP0001")
            assert token.token.description == description

    def test_set_tokeninfo(self, app, tokens):
        """
        Tests setting tokeninfo for a token.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=HOTP0001", "set_tokeninfo", "--tokeninfo",
                                     "new_info=new_value"])
        assert result.exit_code == 0
        assert "Set tokeninfo for token HOTP0001: new_info=new_value" in result.output

        with app.app_context():
            token = get_one_token(serial="HOTP0001")
            assert token.get_tokeninfo("new_info") == "new_value"

    def test_remove_tokeninfo(self, app, tokens):
        """
        Tests removing tokeninfo from a token.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli,
                               ["find", "--tokenattribute", "serial=HOTP0001", "remove_tokeninfo", "--tokeninfo_key",
                                "info1"])
        assert result.exit_code == 0
        assert "Removed tokeninfo 'info1' for token HOTP0001" in result.output

        with app.app_context():
            token = get_one_token(serial="HOTP0001")
            assert "info1" not in token.get_tokeninfo()

    def test_export_pi_format(self, app, tokens):
        """
        Tests exporting tokens in the 'pi' format.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "export", "--format", "pi"], input='n\n')
        assert result.exit_code == 0
        assert "Successfully exported 3 tokens." in result.output
        assert "The key to import the tokens is:" in result.output
