# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2026 Nils Behlen <nils.behlen@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from sqlalchemy.orm.session import close_all_sessions

from privacyidea.app import create_app
from privacyidea.cli.pitokenjanitor.main import cli
from privacyidea.lib.auth import create_db_admin
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.user import User
from privacyidea.lib.usersetting import SUBJECT_LOCAL_ADMIN, SUBJECT_USER
from privacyidea.models import UserSetting, db


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
def settings(app, realm):
    """Live principals (a resolvable user + a present local admin) plus two
    orphan rows: a user uid the resolver never saw and a deleted local admin."""
    live_user = User(login="cornelius", realm="realm1")
    create_db_admin("admin1", "admin1@localhost", "pw")
    db.session.add_all([
        UserSetting(subject_type=SUBJECT_USER, username="cornelius", user_id=live_user.uid,
                    resolver="testresolver", realm_id=live_user.realm_id, settings={"theme": "dark"}),
        UserSetting(subject_type=SUBJECT_LOCAL_ADMIN, username="admin1", settings={"theme": "dark"}),
        UserSetting(subject_type=SUBJECT_USER, user_id="ghost-9999", resolver="testresolver",
                    realm_id=live_user.realm_id, settings={"a": 1}),
        UserSetting(subject_type=SUBJECT_LOCAL_ADMIN, username="ghost-admin", settings={"a": 1}),
    ])
    db.session.commit()
    yield


class TestUserSettingsJanitor:
    def test_list_reports_orphans(self, app, settings):
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["user-settings", "list"])
        assert result.exit_code == 0, result.output
        assert "ghost-9999" in result.output
        assert "ghost-admin" in result.output
        # Live principals must not appear as orphans.
        assert "cornelius" not in result.output
        assert "admin1" not in result.output

    def test_default_subcommand_is_list(self, app, settings):
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["user-settings"])
        assert result.exit_code == 0, result.output
        assert "ghost-9999" in result.output

    def test_delete_with_yes_removes_orphans(self, app, settings):
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["user-settings", "delete", "--yes"])
        assert result.exit_code == 0, result.output
        assert "Deleted 2" in result.output

        # Live principals' rows survive.
        with app.app_context():
            assert db.session.query(UserSetting).filter_by(username="cornelius").count() == 1
            assert db.session.query(UserSetting).filter_by(username="admin1").count() == 1

        result = runner.invoke(cli, ["user-settings", "list"])
        assert result.exit_code == 0, result.output
        assert "No orphaned user settings" in result.output

    def test_delete_aborts_without_yes(self, app, settings):
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["user-settings", "delete"], input="n\n")
        assert result.exit_code != 0  # click.confirm(abort=True) raises Abort
        with app.app_context():
            assert db.session.query(UserSetting).filter_by(username="ghost-admin").count() == 1

    def test_list_when_no_orphans(self, app, realm):
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["user-settings", "list"])
        assert result.exit_code == 0, result.output
        assert "No orphaned user settings" in result.output

    def test_delete_when_no_orphans(self, app, realm):
        # With nothing to clean up, delete reports it and exits 0 (no prompt).
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["user-settings", "delete", "--yes"])
        assert result.exit_code == 0, result.output
        assert "No orphaned user settings" in result.output

    def test_orphan_when_resolver_was_deleted(self, app, realm):
        with app.app_context():
            db.session.add(UserSetting(subject_type=SUBJECT_USER, user_id="some-uid",
                                       resolver="ghost-resolver", realm_id=None, settings={"a": 1}))
            db.session.commit()
        runner = app.test_cli_runner()
        result = runner.invoke(cli, ["user-settings", "list"])
        assert result.exit_code == 0, result.output
        assert "some-uid" in result.output
        assert "ghost-resolver" in result.output
