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
# License along with this program. If not, see <https://www.gnu.org/licenses/>.
import datetime
import json
import re
from types import SimpleNamespace

import pytest
import yaml
from cryptography.fernet import Fernet
from dateutil.tz import tzlocal
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.cli.pitokenjanitor.main import cli, findcontainer
from privacyidea.cli.pitokenjanitor.utils import findtokens
from privacyidea.lib.container import (find_container_by_serial, init_container, create_container_template,
                                       ResourceNotFoundError, get_all_containers)
from privacyidea.lib.containers.container_info import TokenContainerInfoData, PI_INTERNAL
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.lib.realm import set_realm, get_realms
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.token import init_token, get_one_token
from privacyidea.lib.tokenclass import AUTH_DATE_FORMAT
from privacyidea.lib.user import User
from privacyidea.models import db, TokenContainerOwner
from privacyidea.models.token import TokenOwner
from ..base import _reset_database


@pytest.fixture(scope="function")
def app():
    """Create and configure app instance for testing"""
    app = create_app(config_name="testing", config_file="", silent=True)
    with app.app_context():
        _reset_database()

    yield app

    with app.app_context():
        call_finalizers()
        close_all_sessions()
        db.engine.dispose()


@pytest.fixture(scope="function")
def resolver(app):
    """Create a user resolver"""
    with app.app_context():
        rid = save_resolver({"resolver": "testresolver",
                             "type": "passwdresolver",
                             "fileName": "tests/testdata/passwords"})
        assert rid > 0
        return rid


@pytest.fixture(scope="function")
def realms(app, resolver):
    with app.app_context():
        r1 = set_realm(realm="realm1", resolvers=[{"name": "testresolver"}])
        r2 = set_realm(realm="realm2", resolvers=[{"name": "testresolver"}])
        r1 = get_realms(realmname="realm1")
        r2 = get_realms(realmname="realm2")
        db.session.commit()
        return [r1, r2]


@pytest.fixture(scope="function")
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
        t1.save()

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
        t2.save()

        t3 = init_token(param={
            "serial": "HOTP0002",
            "type": "hotp", }
        )
        t3.token.active = True
        t3.token.failcount = 0
        t3.save()

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


@pytest.fixture(scope="function")
def container_template(app):
    with app.app_context():
        template_name = "test-template"
        template_id = create_container_template(
            container_type="generic",
            template_name=template_name,
            options={"tokens": [{"type": "hotp", "genkey": True, "hashlib": "sha1"},
                                {"type": "totp", "genkey": True, "hashlib": "sha256"}]}
        )
        db.session.commit()
        yield {"id": template_id, "name": template_name}


@pytest.fixture(scope="function")
def containers(app, tokens, users, realms, container_template):
    with app.app_context():
        # Container 1: generic, with token, user, realm, description, info
        c1_dict = init_container({"type": "generic", "container_serial": "C1", "description": "Container One"})
        c1 = find_container_by_serial(c1_dict['container_serial'])
        t1 = get_one_token(serial=tokens[0].get_serial())
        c1.add_token(t1)
        c1.set_realms(['realm1'])
        c1.add_user(t1.user)
        c1.update_container_info([TokenContainerInfoData(key='key1', value='value1')])

        # Container 2: smartphone, with token, user, realm, description
        c2_dict = init_container({"type": "smartphone", "container_serial": "C2", "description": "Container Two"})
        c2 = find_container_by_serial(c2_dict['container_serial'])
        t2 = get_one_token(serial=tokens[1].get_serial())
        c2.add_token(t2)
        c2.set_realms(['realm2'])
        c2.add_user(t2.user)

        # Container 3: generic, no token, no user, no realm
        c3_dict = init_container({"type": "generic", "container_serial": "C3", "description": "Container Three"})
        c3 = find_container_by_serial(c3_dict['container_serial'])

        # Container 4: generic, with token, created from template
        c4_dict = init_container(
            {"type": "generic", "container_serial": "C4", "description": "Container Four",
             "template_name": container_template["name"]})
        c4 = find_container_by_serial(c4_dict['container_serial'])
        t3 = get_one_token(serial=tokens[2].get_serial())
        c4.add_token(t3)

        db.session.commit()
        yield [c1, c2, c3, c4]


@pytest.fixture(scope="function")
def orphaned_token(app):
    """
    Creates an orphaned token: a token that has a user assigned in the database,
    but the user no longer exists in the user store.
    """
    with app.app_context():
        t_orphaned = init_token(
            param={"serial": "ORPHAN0001", "type": "hotp"}
        )
        t_orphaned.save()
        TokenOwner(token_id=t_orphaned.token.id,
                   user_id="999999", resolver="testresolver",
                   realmname="realm1").save()
        t_orphaned.set_realms(["realm1"])
        db.session.commit()
        yield t_orphaned


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

    def test_find_tokencontainer(self, app, tokens, token_container):
        """
        Tests filtering tokens by their container.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokencontainer", "serial=container1", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" not in result.output

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

    def test_find_orphaned(self, app, tokens, orphaned_token):
        """
        Tests filtering orphaned tokens. An orphaned token is one that has a user
        assigned in the database, but the user no longer exists in the user store.
        Uses the orphaned_token fixture which creates an orphaned token and the
        tokens fixture which provides valid (non-orphaned) tokens.
        """
        runner = app.test_cli_runner()

        # Find all tokens
        result = runner.invoke(cli, ["find", "list"])
        assert result.exit_code == 0
        assert "ORPHAN0001" in result.output
        assert "HOTP0001" in result.output

        # Find only orphaned tokens
        result = runner.invoke(cli, ["find", "--orphaned", "True", "list"])
        assert result.exit_code == 0
        assert "ORPHAN0001" in result.output
        assert "HOTP0001" not in result.output

        # Find only non-orphaned tokens
        result = runner.invoke(cli, ["find", "--orphaned", "False", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "ORPHAN0001" not in result.output

    def test_find_orphaned_on_error(self, app, tokens, orphaned_token):
        """
        Tests the --orphaned-on-error flag with three tokens:
        1. Tokens from the tokens fixture (non-orphaned, e.g. HOTP0001)
        2. A token from the orphaned_token fixture (orphaned, ORPHAN0001)
        3. A token assigned via an HTTP resolver that raises an error when resolving.
           With --orphaned-on-error, the error token is treated as orphaned.
           Without --orphaned-on-error, the error token is treated as not orphaned.
        """
        # Create an HTTP resolver that will raise an error when resolving users
        rid = save_resolver({
            "resolver": "httperrorresolver",
            "type": "httpresolver",
            "endpoint": "http://localhost:12345/nonexistent",
            "method": "GET",
            "requestMapping": '{"id": "{userid}"}',
            "responseMapping": '{"username": "{data.the_username}"}',
            "hasSpecialErrorHandler": False,
        })
        assert rid > 0
        (added, failed) = set_realm("httperrorrealm", [{"name": "httperrorresolver"}])
        assert len(failed) == 0
        assert len(added) == 1

        # Token assigned via the error-prone HTTP resolver
        t_error = init_token(
            param={"serial": "ERROR0001", "type": "hotp"}
        )
        t_error.save()
        TokenOwner(token_id=t_error.token.id,
                   user_id="999999", resolver="httperrorresolver",
                   realmname="httperrorrealm").save()
        t_error.set_realms(["httperrorrealm"])
        db.session.commit()

        runner = app.test_cli_runner()

        # With --orphaned-on-error: error token IS treated as orphaned
        result = runner.invoke(cli, ["find", "--orphaned", "True", "--orphaned-on-error", "list"])
        assert result.exit_code == 0
        assert "ORPHAN0001" in result.output
        assert "ERROR0001" in result.output
        assert "HOTP0001" not in result.output

        # Without --orphaned-on-error: error token is NOT treated as orphaned
        result = runner.invoke(cli, ["find", "--orphaned", "True", "list"])
        assert result.exit_code == 0
        assert "ORPHAN0001" in result.output
        assert "ERROR0001" not in result.output
        assert "HOTP0001" not in result.output

        # Non-orphaned with --orphaned-on-error: error token is excluded (it's orphaned)
        result = runner.invoke(cli, ["find", "--orphaned", "False", "--orphaned-on-error", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "ORPHAN0001" not in result.output
        assert "ERROR0001" not in result.output

        # Non-orphaned without --orphaned-on-error: error token is included (not treated as orphaned)
        result = runner.invoke(cli, ["find", "--orphaned", "False", "list"])
        assert result.exit_code == 0
        assert "HOTP0001" in result.output
        assert "ERROR0001" in result.output
        assert "ORPHAN0001" not in result.output

    def test_find_boolean_options(self, app, tokens, orphaned_token):
        """
        Tests that --orphaned, --active and --assigned accept the usual spellings of true and false, and reject
        any other value instead of taking it as false.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--orphaned", "yes", "list"])
        assert result.exit_code == 0, result.output
        assert "ORPHAN0001" in result.output
        assert "HOTP0001" not in result.output

        result = runner.invoke(cli, ["find", "--active", "no", "list"])
        assert result.exit_code == 0, result.output
        assert "TOTP0001" in result.output
        assert "HOTP0001" not in result.output

        result = runner.invoke(cli, ["find", "--assigned", "0", "list"])
        assert result.exit_code == 0, result.output
        assert "HOTP0002" in result.output
        assert "HOTP0001" not in result.output

        for option in ("--orphaned", "--active", "--assigned"):
            result = runner.invoke(cli, ["find", option, "maybe", "list"])
            assert result.exit_code == 2, result.output
            assert "Invalid value" in result.output


    def test_find_tokeninfo_relative_time(self, app, tokens):
        """
        Tests that a signed time span in a < or > comparison of the tokeninfo is a point in time relative to now,
        and that tokens without the entry match neither comparison.
        """
        now = datetime.datetime.now(tzlocal())
        get_one_token(serial="HOTP0001").write_tokeninfo(
            "last_auth", (now - datetime.timedelta(days=10)).strftime(AUTH_DATE_FORMAT))
        get_one_token(serial="TOTP0001").write_tokeninfo(
            "last_auth", (now - datetime.timedelta(days=400)).strftime(AUTH_DATE_FORMAT))
        runner = app.test_cli_runner()

        result = runner.invoke(cli, ["find", "--tokeninfo", "last_auth<-180d", "list"])
        assert result.exit_code == 0, result.output
        assert "TOTP0001" in result.output
        assert "HOTP0001" not in result.output
        assert "HOTP0002" not in result.output

        result = runner.invoke(cli, ["find", "--tokeninfo", "last_auth>-180d", "list"])
        assert result.exit_code == 0, result.output
        assert "HOTP0001" in result.output
        assert "TOTP0001" not in result.output
        assert "HOTP0002" not in result.output


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

    def test_set_tokeninfo_value_with_any_characters(self, app, tokens):
        """
        Tests that the value of set_tokeninfo is everything after the first "=", including spaces, dashes and
        further "=" characters, and that a missing value is refused.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=^HOTP0001$", "set_tokeninfo", "--tokeninfo",
                                     "marked = to-delete 2026-09-25"])
        assert result.exit_code == 0, result.output
        assert get_one_token(serial="HOTP0001").get_tokeninfo("marked") == "to-delete 2026-09-25"

        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=^HOTP0001$", "set_tokeninfo", "--tokeninfo",
                                     "note=a=b"])
        assert result.exit_code == 0, result.output
        assert get_one_token(serial="HOTP0001").get_tokeninfo("note") == "a=b"

        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=^HOTP0001$", "set_tokeninfo", "--tokeninfo",
                                     "note="])
        assert result.exit_code != 0
        assert "Can not parse tokeninfo" in result.output

    def test_list_json(self, app, tokens):
        """
        Tests that list --format json writes one JSON object per token, and with --summarize one per owner, the
        unassigned tokens under the owner null.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=^HOTP0001$", "list", "--format", "json"])
        assert result.exit_code == 0, result.output
        token = json.loads(result.stdout)
        assert token["serial"] == "HOTP0001"
        assert token["tokentype"] == "hotp"
        assert token["realms"] == ["realm1"]
        assert token["info"]["info1"] == "value1"

        result = runner.invoke(cli, ["find", "list", "--summarize", "--format", "json"])
        assert result.exit_code == 0, result.output
        owners = [json.loads(line) for line in result.stdout.splitlines()]
        assert sorted(owner["user"]["username"] for owner in owners if owner["user"]) == ["cornelius", "hans"]
        assert {"user": None, "tokens": 1} in owners
        assert all(owner["tokens"] == 1 for owner in owners)

    def test_summarize_owner_with_a_multi_valued_attribute(self, app):
        """
        Tests that the summary works with a user attribute that has several values, like the mobile numbers an LDAP
        resolver returns as a list, in the text and in the JSON output.
        """
        owner = SimpleNamespace(info={"username": "multi", "givenname": "", "surname": "", "mobile": ["1", "2"]},
                                uid="42", resolver="ldap", realm="realm1")
        token_list = [SimpleNamespace(user=owner, token=SimpleNamespace(serial=serial)) for serial in ("M1", "M2")]
        users = findtokens.export_user_data(token_list, ["mobile"])
        assert len(users) == 1
        owner_key, serials = next(iter(users.items()))
        assert serials == ["M1", "M2"]
        assert findtokens._format_owner(owner_key) == "'multi','','','42','ldap','realm1','['1', '2']'"
        assert json.loads(json.dumps(dict(owner_key)))["mobile"] == ["1", "2"]

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

    def test_set_tokeninfo_skips_an_entry_the_token_maintains(self, app, tokens):
        """
        Tests that a tokeninfo entry which the token type maintains itself is reported and skipped, and that the
        run does not stop there, since a run can cover several token types.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=HOTP0001", "set_tokeninfo", "--tokeninfo",
                                     "hashlib=sha512"])
        assert result.exit_code == 0
        assert "Skipped token HOTP0001" in result.output

        with app.app_context():
            token = get_one_token(serial="HOTP0001")
            assert token.get_tokeninfo("hashlib") != "sha512"

    def test_remove_tokeninfo_skips_an_entry_the_token_maintains(self, app, tokens):
        """
        Tests that removing a tokeninfo entry which the token needs to work is reported and skipped.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli,
                               ["find", "--tokenattribute", "serial=HOTP0001", "remove_tokeninfo",
                                "--tokeninfo_key", "hashlib"])
        assert result.exit_code == 0
        assert "Skipped token HOTP0001" in result.output

        with app.app_context():
            token = get_one_token(serial="HOTP0001")
            assert "hashlib" in token.get_tokeninfo()

    def test_export_pi_format(self, app, tokens):
        """
        Tests exporting tokens in the 'pi' format.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "export", "--format", "pi"], input='n\n')
        assert result.exit_code == 0
        assert "Successfully exported 3 tokens." in result.output
        assert "The key to import the tokens is:" in result.output

    def test_export_pi_format_to_stdout_can_be_imported(self, app, tokens, tmp_path):
        """
        Tests that an export in the 'pi' format to stdout contains nothing but the export, so that the redirected
        output can be imported. The key, the messages and the question whether to save the key go to stderr.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "export"])
        assert result.exit_code == 0, result.output
        assert "Successfully exported 3 tokens." in result.stderr
        # Without a terminal nobody could answer, so the question whether to save the key is not asked
        assert "Do you want to save the key to a file?" not in result.output
        key = re.search(r"The key to import the tokens is:\s+(\S+)", result.stderr).group(1)
        exported_tokens = json.loads(Fernet(key).decrypt(result.stdout.strip()))
        assert sorted(token["serial"] for token in exported_tokens) == ["HOTP0001", "HOTP0002", "TOTP0001"]

        export_file = tmp_path / "tokens.pi"
        export_file.write_text(result.stdout)
        result = runner.invoke(cli, ["import", "privacyidea", str(export_file), "--key", key])
        assert result.exit_code == 0, result.output
        assert "3 tokens updated." in result.output

    def test_export_pi_format_asks_to_save_the_key_on_a_terminal(self, app, tokens, tmp_path, monkeypatch):
        """
        Tests that on a terminal the export asks whether to save the key and writes it to the given file.
        """
        monkeypatch.setattr(findtokens, "_is_interactive", lambda: True)
        key_file = tmp_path / "export.key"
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "export", "--file", str(tmp_path / "tokens.pi")],
                               input=f"y\n{key_file}\n")
        assert result.exit_code == 0, result.output
        assert "Do you want to save the key to a file?" in result.stderr
        key = re.search(r"The key to import the tokens is:\s+(\S+)", result.stderr).group(1)
        assert key_file.read_text() == key

    def test_export_recognizes_stdout_by_name(self, app, tmp_path):
        """
        Tests that the export recognizes stdout by the name of the stream, also when it is a wrapper and not
        sys.stdout itself, and does not take a file for stdout.
        """
        assert findtokens._is_stdout(SimpleNamespace(name="<stdout>"))
        with open(tmp_path / "tokens.pi", "w") as export_file:
            assert not findtokens._is_stdout(export_file)

    def test_export_yaml_format(self, app, tokens):
        """
        Tests exporting tokens in the 'yaml' format with their OTP key and owner.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "export", "--format", "yaml"])
        assert result.exit_code == 0, result.output
        exported_tokens = {token["serial"]: token for token in yaml.safe_load(result.stdout)}
        assert sorted(exported_tokens) == ["HOTP0001", "HOTP0002", "TOTP0001"]
        assert exported_tokens["HOTP0001"]["owner"] == "cornelius@realm1"
        assert exported_tokens["HOTP0002"]["owner"] == "n/a"
        otp_key = get_one_token(serial="HOTP0001").token.get_otpkey().getKey().decode()
        assert exported_tokens["HOTP0001"]["otpkey"] == otp_key
        assert exported_tokens["HOTP0001"]["info_list"]["info1"] == "value1"

    def test_update_keeps_the_counters(self, app, tokens, tmp_path):
        """
        Tests that updating tokens from their own YAML export keeps the OTP key, the OTP counter, the fail
        counter and the token kind, so that OTP values which were already used do not become valid again.
        """
        token = get_one_token(serial="HOTP0001")
        otp_key = token.token.get_otpkey().getKey()
        token.token.count = 50
        token.save()
        token.write_tokeninfo("tokenkind", "hardware")
        export_file = tmp_path / "tokens.yaml"
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--tokenattribute", "serial=^HOTP0001$", "export", "--format", "yaml",
                                     "--file", str(export_file)])
        assert result.exit_code == 0, result.output

        result = runner.invoke(cli, ["update", str(export_file)])
        assert result.exit_code == 0, result.output
        assert "Updated token HOTP0001." in result.output

        token = get_one_token(serial="HOTP0001")
        assert token.token.get_otpkey().getKey() == otp_key
        assert token.token.count == 50
        assert token.token.failcount == 5
        assert token.get_tokeninfo("tokenkind") == "hardware"

    def test_update_counter_of_the_entry_and_entries_without_owner(self, app, tokens, tmp_path):
        """
        Tests that an entry without owner and counter keeps the counters of the token, that a higher counter in
        the entry raises the OTP counter, and that a lower counter does not lower it.
        """
        for serial, count in (("HOTP0001", 50), ("HOTP0002", 20), ("TOTP0001", 30)):
            token = get_one_token(serial=serial)
            token.token.count = count
            token.save()
        entries = []
        for serial, exported_count in (("HOTP0001", None), ("HOTP0002", 70), ("TOTP0001", 10)):
            entry = get_one_token(serial=serial)._to_dict()
            del entry["counter"]
            if exported_count is not None:
                entry["counter"] = exported_count
            entries.append(entry)
        entries.append({"description": "an entry without serial"})
        yaml_file = tmp_path / "tokens.yaml"
        yaml_file.write_text(yaml.safe_dump(entries))

        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["update", str(yaml_file)])
        assert result.exit_code == 0, result.output
        assert "Skipping an entry without a serial." in result.output

        assert get_one_token(serial="HOTP0001").token.count == 50
        assert get_one_token(serial="HOTP0001").token.failcount == 5
        assert get_one_token(serial="HOTP0002").token.count == 70
        assert get_one_token(serial="TOTP0001").token.count == 30
        assert get_one_token(serial="TOTP0001").token.failcount == 10

    def test_delete_more_tokens_than_chunksize(self, app, tokens):
        """
        Tests that deleting the found tokens chunk by chunk does not skip any token.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["find", "--chunksize", "1", "delete"])
        assert result.exit_code == 0, result.output
        for serial in ("HOTP0001", "HOTP0002", "TOTP0001"):
            assert f"Deleted token {serial}" in result.output
            assert get_one_token(serial=serial, silent_fail=True) is None


class TestPiTokenJanitorContainer:
    def test_findcontainer_no_args(self, app, containers):
        """
        Tests that `container list` with no arguments returns all containers.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["list"])
        assert result.exit_code == 0
        assert "C1" in result.output
        assert "C2" in result.output
        assert "C3" in result.output
        assert "C4" in result.output

    def test_findcontainer_by_type(self, app, containers):
        """
        Tests filtering containers by type.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--type", "smartphone", "list"])
        assert result.exit_code == 0
        assert "C1" not in result.output
        assert "C2" in result.output
        assert "C3" not in result.output
        assert "C4" not in result.output

    def test_findcontainer_by_token_serial(self, app, containers, tokens):
        """
        Tests filtering containers by token serial.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--token-serial", tokens[0].get_serial(), "list"])
        assert result.exit_code == 0
        assert "C1" in result.output
        assert "C2" not in result.output
        assert "C3" not in result.output
        assert "C4" not in result.output

    def test_container_delete(self, app, containers):
        """
        Tests deleting a container without deleting its tokens.
        """
        runner = app.test_cli_runner()
        with app.app_context():
            # C1 contains token HOTP0001
            assert find_container_by_serial("C1") is not None
            assert get_one_token(serial="HOTP0001") is not None

        result = runner.invoke(findcontainer, ["--serial", "C1", "delete"])
        assert result.exit_code == 0
        assert "Deleted container C1" in result.output

        with app.app_context():
            with pytest.raises(ResourceNotFoundError):
                find_container_by_serial("C1")
            # The token should still exist
            assert get_one_token(serial="HOTP0001") is not None

    def test_container_delete_with_tokens(self, app, containers):
        """
        Tests deleting a container and its tokens using the --tokens flag.
        """
        runner = app.test_cli_runner()
        with app.app_context():
            # C1 contains token HOTP0001
            assert find_container_by_serial("C1") is not None
            assert get_one_token(serial="HOTP0001") is not None

        result = runner.invoke(findcontainer, ["--serial", "C1", "delete", "--tokens"])
        assert result.exit_code == 0
        assert "Deleted container C1" in result.output

        with app.app_context():
            with pytest.raises(ResourceNotFoundError):
                find_container_by_serial("C1")
            # The token should also be deleted
            assert get_one_token(serial="HOTP0001", silent_fail=True) is None

    def test_container_update_info(self, app, containers):
        """
        Tests updating info for a container.
        """
        runner = app.test_cli_runner()
        # Add new info
        result = runner.invoke(findcontainer, ["--serial", "C2", "update_info", "new_key", "new_value"])
        assert result.exit_code == 0
        assert "Updated info new_key=new_value for container C2" in result.output

        with app.app_context():
            container = find_container_by_serial("C2")
            info = container.get_container_info_dict()
            assert info.get("new_key") == "new_value"

        # Update existing info
        result = runner.invoke(findcontainer, ["--serial", "C1", "update_info", "key1", "updated_value"])
        assert result.exit_code == 0
        assert "Updated info key1=updated_value for container C1" in result.output

        with app.app_context():
            container = find_container_by_serial("C1")
            info = container.get_container_info_dict()
            assert info.get("key1") == "updated_value"

    def test_container_delete_info(self, app, containers):
        """
        Tests deleting info from a container.
        """
        runner = app.test_cli_runner()
        with app.app_context():
            container = find_container_by_serial("C1")
            assert "key1" in container.get_container_info_dict()

        result = runner.invoke(findcontainer, ["--serial", "C1", "delete_info", "key1"])
        assert result.exit_code == 0
        assert "Deleted info key1 for container C1" in result.output

        with app.app_context():
            container = find_container_by_serial("C1")
            assert "key1" not in container.get_container_info_dict()

    def test_container_delete_info_unknown_key(self, app, containers):
        """
        Tests that deleting an info key the container does not have is reported as such.
        """
        runner = app.test_cli_runner()
        with app.app_context():
            container = find_container_by_serial("C1")
            assert "no_such_key" not in container.get_container_info_dict()

        result = runner.invoke(findcontainer, ["--serial", "C1", "delete_info", "no_such_key"])
        assert result.exit_code == 0
        assert "Container C1 has no info no_such_key" in result.output
        assert "Deleted info" not in result.output

    def test_container_set_description(self, app, containers):
        """
        Tests setting the description for a container.
        """
        runner = app.test_cli_runner()
        new_description = "A new description for C3"
        result = runner.invoke(findcontainer, ["--serial", "C3", "set_description", new_description])
        assert result.exit_code == 0
        assert f"Set description '{new_description}' for container C3" in result.output

        with app.app_context():
            container = find_container_by_serial("C3")
            assert container.description == new_description

    def test_container_set_realm(self, app, containers, realms):
        """
        Tests setting and adding realms for a container.
        """
        runner = app.test_cli_runner()
        # Set realm (overwrite)
        c3 = find_container_by_serial("C3")
        c3.set_realms(['realm1'])
        result = runner.invoke(findcontainer, ["--serial", "C3", "set_realm", "realm2"])
        assert result.exit_code == 0
        assert "Set realm '['realm2']' for container C3" in result.output

        with app.app_context():
            container = find_container_by_serial("C3")
            assert container.get_as_dict().get("realms") == ["realm2"]

        # Add realm
        result = runner.invoke(findcontainer, ["--serial", "C3", "set_realm", "realm1", "--add"])
        assert result.exit_code == 0
        assert "Set realm '['realm1']' for container C3" in result.output

        with app.app_context():
            container = find_container_by_serial("C3")
            assert sorted(container.get_as_dict().get("realms")) == sorted(["realm1", "realm2"])

    def test_container_set_realm_named_like_a_status_key(self, app, containers, realms):
        """
        Tests setting a realm that is named like a status key of the set_realms result.
        """
        runner = app.test_cli_runner()
        with app.app_context():
            set_realm(realm="deleted", resolvers=[{"name": "testresolver"}])
            db.session.commit()

        result = runner.invoke(findcontainer, ["--serial", "C3", "set_realm", "deleted"])
        assert result.exit_code == 0
        assert "Set realm '['deleted']' for container C3" in result.output

        with app.app_context():
            container = find_container_by_serial("C3")
            assert container.get_as_dict().get("realms") == ["deleted"]

    def test_findcontainer_by_realm(self, app, containers, realms):
        """
        Tests filtering containers by realm.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--realm", 'realm2', "list"])
        assert result.exit_code == 0
        assert "C1" not in result.output
        assert "C2" in result.output
        assert "C3" not in result.output
        assert "C4" not in result.output

    def test_findcontainer_by_template(self, app, containers):
        """
        Tests filtering containers by template.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--template", "test-template", "list"])
        assert result.exit_code == 0
        assert "C1" not in result.output
        assert "C2" not in result.output
        assert "C3" not in result.output
        assert "C4" in result.output

    def test_findcontainer_by_description(self, app, containers):
        """
        Tests filtering containers by description.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--description", "Container One", "list"])
        assert result.exit_code == 0
        assert "C1" in result.output
        assert "C2" not in result.output
        assert "C3" not in result.output
        assert "C4" not in result.output

    def test_findcontainer_by_assigned(self, app, containers):
        """
        Tests filtering containers by assignment status.
        """
        runner = app.test_cli_runner()
        # C1 and C2 are assigned because their tokens are assigned
        result = runner.invoke(findcontainer, ["--assigned", "True", "list"])
        assert result.exit_code == 0
        assert "C1" in result.output
        assert "C2" in result.output
        assert "C3" not in result.output
        assert "C4" not in result.output  # Token in C4 is not assigned to a user

    def test_findcontainer_by_info(self, app, containers):
        """
        Tests filtering containers by info.
        """
        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--info", "key1=value1", "list"])
        assert result.exit_code == 0
        assert "C1" in result.output
        assert "C2" not in result.output
        assert "C3" not in result.output
        assert "C4" not in result.output

    def test_findcontainer_orphaned(self, app, containers):
        """
        Tests that a container assigned to a user who no longer exists in the user store is orphaned, while the
        containers of existing users and the unassigned containers are not.
        """
        init_container({"type": "generic", "container_serial": "CORPHAN"})
        db.session.add(TokenContainerOwner(container_serial="CORPHAN", user_id="999999", resolver="testresolver",
                                           realm_name="realm1"))
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--orphaned", "True", "list"])
        assert result.exit_code == 0, result.output
        assert "Serial: CORPHAN," in result.output
        for serial in ("C1", "C2", "C3", "C4"):
            assert f"Serial: {serial}," not in result.output

        result = runner.invoke(findcontainer, ["--orphaned", "False", "list"])
        assert result.exit_code == 0, result.output
        assert "Serial: CORPHAN," not in result.output
        for serial in ("C1", "C2", "C3", "C4"):
            assert f"Serial: {serial}," in result.output

    def test_findcontainer_orphaned_owner_of_a_deleted_resolver(self, app, containers):
        """
        Tests that a container whose owner belongs to a deleted resolver is orphaned, and deleted by
        --orphaned True delete.
        """
        init_container({"type": "generic", "container_serial": "CRESOLVERGONE"})
        db.session.add(TokenContainerOwner(container_serial="CRESOLVERGONE", user_id="1000",
                                           resolver="deletedresolver", realm_name="realm1"))
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--orphaned", "True", "list"])
        assert result.exit_code == 0, result.output
        assert "Serial: CRESOLVERGONE," in result.output

        result = runner.invoke(findcontainer, ["--orphaned", "True", "delete"])
        assert result.exit_code == 0, result.output
        with pytest.raises(ResourceNotFoundError):
            find_container_by_serial("CRESOLVERGONE")

    def test_findcontainer_orphaned_skips_container_on_resolver_error(self, app, containers):
        """
        Tests that a container whose user can not be looked up because of an error of the user store is neither
        listed as orphaned nor as not orphaned, and that this is reported.
        """
        save_resolver({
            "resolver": "httperrorresolver",
            "type": "httpresolver",
            "endpoint": "http://localhost:12345/nonexistent",
            "method": "GET",
            "requestMapping": '{"id": "{userid}"}',
            "responseMapping": '{"username": "{data.the_username}"}',
            "hasSpecialErrorHandler": False,
        })
        set_realm("httperrorrealm", [{"name": "httperrorresolver"}])
        init_container({"type": "generic", "container_serial": "CERROR"})
        db.session.add(TokenContainerOwner(container_serial="CERROR", user_id="999999", resolver="httperrorresolver",
                                           realm_name="httperrorrealm"))
        db.session.commit()

        runner = app.test_cli_runner()
        for orphaned in ("True", "False"):
            result = runner.invoke(findcontainer, ["--orphaned", orphaned, "list"])
            assert result.exit_code == 0, result.output
            assert "Serial: CERROR," not in result.stdout
            assert "Can not check whether container CERROR is orphaned, the container is skipped" in result.stderr

    def test_container_delete_more_containers_than_chunksize(self, app, containers):
        """
        Tests that deleting the found containers page by page does not skip any container.
        """
        for index in range(5):
            init_container({"type": "generic", "container_serial": f"PAGE{index}", "description": "page test"})
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--description", "page test", "--chunksize", "2", "delete"])
        assert result.exit_code == 0, result.output
        for index in range(5):
            assert f"Deleted container PAGE{index}" in result.output
        assert get_all_containers(description="page test")["containers"] == []
        assert find_container_by_serial("C1") is not None

    def test_container_update_info_skips_internal_entries(self, app, containers):
        """
        Tests that update_info does not overwrite an info entry which privacyIDEA maintains itself.
        """
        container = find_container_by_serial("C1")
        container.update_container_info([TokenContainerInfoData(key="public_key_client", value="client key",
                                                                info_type=PI_INTERNAL)])

        runner = app.test_cli_runner()
        result = runner.invoke(findcontainer, ["--serial", "C1", "update_info", "public_key_client", "other key"])
        assert result.exit_code == 0, result.output
        assert "Skipped container C1" in result.output

        container = find_container_by_serial("C1")
        assert container.get_container_info_dict()["public_key_client"] == "client key"
        assert "public_key_client" in container.get_internal_info_keys()
