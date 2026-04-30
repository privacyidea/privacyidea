# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the ``pi-tokenjanitor deprecated`` command group.

See privacyidea/cli/pitokenjanitor/utils/deprecated.py and
dev/token-deprecation-strategy.md.
"""
import pytest
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.cli.pitokenjanitor.main import cli
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.lib.token import get_tokens
from privacyidea.lib.tokens.deprecated import DeprecatedTokenClass
from privacyidea.models import Token, db


@pytest.fixture(scope="function")
def app():
    """Create and configure app instance for testing."""
    app = create_app(config_name="testing", config_file="", silent=True)
    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        call_finalizers()
        close_all_sessions()
        db.drop_all()
        db.engine.dispose()


def _make_deprecated(serial: str, original: str) -> None:
    """Insert a deprecated token at the DB layer mirroring what the migration produces."""
    db_token = Token(serial, tokentype="deprecated")
    db_token.active = False
    db_token.save()
    token = DeprecatedTokenClass(db_token)
    token.add_tokeninfo("original_tokentype", original)
    token.add_tokeninfo("original_active", "1")
    token.add_tokeninfo("deprecated_in", "3.14")


class TestJanitorDeprecatedList:
    def test_list_empty(self, app):
        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "list"])
            assert result.exit_code == 0, result.output
            assert "No deprecated tokens found" in result.output

    def test_list_all_groups_by_original_type(self, app):
        with app.app_context():
            _make_deprecated("U2F_A", "u2f")
            _make_deprecated("U2F_B", "u2f")
            _make_deprecated("FOO_1", "foo")
            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "list"])
            assert result.exit_code == 0, result.output
            assert "Found 3 deprecated" in result.output
            assert "u2f" in result.output
            assert "foo" in result.output
            assert "U2F_A" in result.output
            assert "U2F_B" in result.output
            assert "FOO_1" in result.output

    def test_list_filters_by_original_type(self, app):
        with app.app_context():
            _make_deprecated("U2F_A", "u2f")
            _make_deprecated("FOO_1", "foo")
            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "list", "u2f"])
            assert result.exit_code == 0, result.output
            assert "U2F_A" in result.output
            assert "FOO_1" not in result.output

    def test_list_filter_no_match(self, app):
        with app.app_context():
            _make_deprecated("U2F_A", "u2f")
            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "list", "nonexistent"])
            assert result.exit_code == 0, result.output
            assert "No deprecated tokens with original_tokentype='nonexistent'" in result.output


class TestJanitorDeprecatedDelete:
    def test_delete_requires_argument(self, app):
        """
        `deprecated delete` without an argument must fail with a usage error —
        otherwise an accidental Enter deletes everything.
        """
        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "delete"])
            assert result.exit_code != 0
            assert "Missing argument" in result.output or "Error" in result.output

    def test_delete_single_type_with_yes(self, app):
        with app.app_context():
            _make_deprecated("U2F_A", "u2f")
            _make_deprecated("U2F_B", "u2f")
            _make_deprecated("FOO_1", "foo")

            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "delete", "u2f", "--yes"])
            assert result.exit_code == 0, result.output
            assert "Deleted U2F_A" in result.output
            assert "Deleted U2F_B" in result.output
            assert "FOO_1" not in result.output  # untouched
            assert "Deleted 2 token" in result.output

            # DB state: foo still there, u2f gone
            assert len(get_tokens(serial="U2F_A")) == 0
            assert len(get_tokens(serial="U2F_B")) == 0
            assert len(get_tokens(serial="FOO_1")) == 1

    def test_delete_all_with_yes(self, app):
        with app.app_context():
            _make_deprecated("U2F_A", "u2f")
            _make_deprecated("FOO_1", "foo")

            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "delete", "all", "--yes"])
            assert result.exit_code == 0, result.output
            assert "Deleted 2 token" in result.output
            assert len(get_tokens(tokentype="deprecated")) == 0

    def test_delete_empty_noop(self, app):
        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "delete", "all", "--yes"])
            assert result.exit_code == 0, result.output
            assert "No deprecated tokens to delete" in result.output

    def test_delete_empty_specific_type(self, app):
        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "delete", "u2f", "--yes"])
            assert result.exit_code == 0, result.output
            assert "No deprecated tokens with original_tokentype='u2f' to delete" in result.output

    def test_delete_prompts_without_yes_and_abort(self, app):
        """Without --yes the command must prompt and honor an abort."""
        with app.app_context():
            _make_deprecated("U2F_A", "u2f")
            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "delete", "u2f"], input="n\n")
            assert result.exit_code != 0  # aborted
            assert len(get_tokens(serial="U2F_A")) == 1  # still there

    def test_delete_prompts_without_yes_and_confirm(self, app):
        with app.app_context():
            _make_deprecated("U2F_A", "u2f")
            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "delete", "u2f"], input="y\n")
            assert result.exit_code == 0, result.output
            assert len(get_tokens(serial="U2F_A")) == 0

    def test_delete_does_not_touch_non_deprecated_tokens(self, app):
        """A hotp token of the same serial pattern must be untouched."""
        with app.app_context():
            _make_deprecated("U2F_A", "u2f")
            # A live hotp token
            hotp = Token("HOTP0001", tokentype="hotp")
            hotp.active = True
            hotp.save()

            runner = app.test_cli_runner()
            result = runner.invoke(cli, ["deprecated", "delete", "all", "--yes"])
            assert result.exit_code == 0, result.output
            assert len(get_tokens(serial="HOTP0001")) == 1
            assert len(get_tokens(serial="U2F_A")) == 0
