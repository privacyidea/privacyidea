# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2026 Nils Behlen <nils.behlen@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.cli.pitokenjanitor.main import cli
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.user import User
from privacyidea.models import InternalUserAttribute, db


@pytest.fixture(scope="function")
def app():
    app = create_app(config_name="testing", config_file="", silent=True)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        call_finalizers()
        close_all_sessions()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture(scope="function")
def realm(app):
    with app.app_context():
        save_resolver({"resolver": "testresolver",
                       "type": "passwdresolver",
                       "fileName": "tests/testdata/passwords"})
        set_realm(realm="realm1", resolvers=[{"name": "testresolver"}])
        db.session.commit()
        yield


@pytest.fixture(scope="function")
def attributes(app, realm):
    """A live user with an internal attribute + an orphan row whose uid the resolver has never seen."""
    live = User(login="cornelius", realm="realm1")
    live.set_internal_attribute("fido2_user_id", "live-value")

    ghost = InternalUserAttribute(user_id="ghost-9999",
                                  resolver="testresolver",
                                  realm_id=live.realm_id,
                                  Key="fido2_user_id",
                                  Value="ghost-value")
    db.session.add(ghost)
    db.session.commit()
    yield {"live": live, "ghost_uid": "ghost-9999"}


class TestInternalAttributes:
    def test_list_reports_orphans(self, app, attributes):
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["internal-attributes", "list"])
        assert result.exit_code == 0, result.output
        assert "ghost-9999" in result.output
        # Live user must not appear as orphan.
        assert "cornelius" not in result.output

    def test_default_subcommand_is_list(self, app, attributes):
        """Invoking the group without a subcommand should run `list`."""
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["internal-attributes"])
        assert result.exit_code == 0, result.output
        assert "ghost-9999" in result.output

    def test_delete_with_yes_removes_orphans(self, app, attributes):
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["internal-attributes", "delete", "--yes"])
        assert result.exit_code == 0, result.output
        assert "Deleted 1" in result.output

        # The live user's row survives.
        with app.app_context():
            self_check = User(login="cornelius", realm="realm1")
            assert self_check.internal_attributes == {"fido2_user_id": "live-value"}

        # A subsequent run finds nothing.
        result = runner.invoke(cli, ["internal-attributes", "list"])
        assert result.exit_code == 0, result.output
        assert "No orphaned internal user attributes" in result.output

    def test_delete_aborts_without_yes(self, app, attributes):
        """Without --yes the user is asked to confirm; sending 'n' aborts."""
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["internal-attributes", "delete"], input="n\n")
        assert result.exit_code != 0  # click.confirm(abort=True) raises Abort

        # Orphan row is still present.
        with app.app_context():
            ghost_rows = db.session.query(InternalUserAttribute).filter_by(
                user_id="ghost-9999").count()
            assert ghost_rows == 1

    def test_list_when_no_orphans(self, app, realm):
        """Empty state: no orphan rows, list reports the clean message."""
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["internal-attributes", "list"])
        assert result.exit_code == 0, result.output
        assert "No orphaned internal user attributes" in result.output

    def test_delete_when_no_orphans(self, app, realm):
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["internal-attributes", "delete", "--yes"])
        assert result.exit_code == 0, result.output
        assert "No orphaned internal user attributes" in result.output

    def test_orphan_when_resolver_was_deleted(self, app, realm):
        """A row whose resolver no longer exists is also reported as orphaned."""
        # Reference a resolver that has never existed — easier than tearing
        # down the live one (which is bound to a realm).
        row = InternalUserAttribute(user_id="some-uid",
                                    resolver="ghost-resolver",
                                    realm_id=None,
                                    Key="fido2_user_id",
                                    Value="v")
        db.session.add(row)
        db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["internal-attributes", "list"])
        assert result.exit_code == 0, result.output
        assert "some-uid" in result.output
        assert "ghost-resolver" in result.output
