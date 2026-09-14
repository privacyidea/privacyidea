"""
This file tests the folder layout the WebUI is served from.

Three things have to agree on it and none of them can see the others: the Angular build writes
the application to a path configured in angular.json, the server reads it from a path built in
privacyidea/webui/login.py, and the URL it is addressed under is baked into the build as its
base href. A rename that misses one of them produces a WebUI that builds and installs but is
never found, which no other test would notice, because the test environment has no build.
"""
import json
import os
import pathlib
import tempfile

from flask import Flask

from privacyidea.app import _resolve_ui_folders, _warn_if_webui_missing
from privacyidea.config import ConfigKey, DefaultConfigValues
from privacyidea.webui.login import WEBUI_DIST_PATH
from .base import MyTestCase

PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent / "privacyidea"
WEBUI_DIR = PACKAGE_DIR / DefaultConfigValues.STATIC_FOLDER
LEGACY_WEBUI_DIR = PACKAGE_DIR / DefaultConfigValues.LEGACY_STATIC_FOLDER


def write_bundle(static_folder: str, locale: str) -> None:
    """Create a minimal locale bundle where the server looks for one."""
    browser_dir = os.path.join(static_folder, *WEBUI_DIST_PATH, locale)
    os.makedirs(browser_dir, exist_ok=True)
    with open(os.path.join(browser_dir, "index.html"), "w", encoding="utf-8") as index_file:
        index_file.write("<html><head></head><body></body></html>")


class WebUIBuildContractTestCase(MyTestCase):
    """The paths the Angular build writes to and the server reads from have to match."""

    @staticmethod
    def _angular_json() -> dict:
        with open(WEBUI_DIR / "angular.json", encoding="utf-8") as config_file:
            return json.load(config_file)["projects"]["privacyidea-webui"]

    def test_the_webui_is_in_the_static_folder(self):
        """The compiled WebUI is served from the static folder, so its sources live there too."""
        self.assertTrue((WEBUI_DIR / "angular.json").is_file(), WEBUI_DIR)
        self.assertTrue((WEBUI_DIR / "public" / "policy-templates" / "index.json").is_file())

    def test_the_previous_webui_is_in_the_static_old_folder(self):
        """The previous WebUI is still shipped, and the default template folder points into it."""
        self.assertTrue((LEGACY_WEBUI_DIR / "templates" / "index.html").is_file())
        self.assertTrue((LEGACY_WEBUI_DIR / "contrib" / "css" / "bootstrap-theme.css").is_file())
        self.assertTrue(DefaultConfigValues.TEMPLATE_FOLDER.startswith(
            DefaultConfigValues.LEGACY_STATIC_FOLDER))

    def test_the_build_writes_where_the_server_reads(self):
        """angular.json's outputPath is the path the server joins onto the static folder."""
        output_path = self._angular_json()["architect"]["build"]["options"]["outputPath"]
        # The build writes <outputPath>/browser/<locale>; the last element of WEBUI_DIST_PATH is
        # that "browser" directory, which the Angular application builder always creates.
        self.assertEqual("/".join(WEBUI_DIST_PATH[:-1]), output_path)
        self.assertEqual("browser", WEBUI_DIST_PATH[-1])

    def test_the_base_href_matches_the_url_the_static_folder_is_served_under(self):
        """The production base href is baked into the build, so it cannot adapt to a renamed
        folder. It has to spell out the URL of the static folder plus the output path."""
        base_href = self._angular_json()["architect"]["build"]["configurations"]["production"]["baseHref"]
        expected = f"/{DefaultConfigValues.STATIC_FOLDER}{'/'.join(WEBUI_DIST_PATH)}/"
        self.assertEqual(expected, base_href)

    def test_the_source_locale_is_the_one_the_server_falls_back_to(self):
        """A build puts every locale in its own subdirectory, English included, and the server
        falls back to that directory when the requested locale was not built."""
        self.assertEqual("en", self._angular_json()["i18n"]["sourceLocale"]["subPath"])


class WebUIDefaultConfigTestCase(MyTestCase):
    """Without any configuration, privacyIDEA serves the WebUI from the static folder."""

    def test_the_folders_are_the_webui_and_the_legacy_templates(self):
        self.assertEqual("static", os.path.basename(self.app.static_folder))
        self.assertEqual(DefaultConfigValues.TEMPLATE_FOLDER, self.app.template_folder)

    def test_the_webui_assets_are_served(self):
        """The WebUI reads its policy templates and its logo from below /static/public/, which is
        the source directory rather than the copy the build makes."""
        response = self.app.test_client().get("/static/public/policy-templates/index.json")
        self.assertEqual(200, response.status_code)
        self.assertIn("application/json", response.headers["Content-Type"])

    def test_the_root_redirects_to_the_webui_when_it_is_built(self):
        """With a build present, / sends the browser to the application instead of rendering the
        previous WebUI. The test environment has no build, so one is created for this."""
        with tempfile.TemporaryDirectory() as static_folder:
            write_bundle(static_folder, "en")
            original = self.app.static_folder
            self.app.static_folder = static_folder
            try:
                response = self.app.test_client().get("/")
            finally:
                self.app.static_folder = original
        self.assertEqual(302, response.status_code)
        self.assertEqual("/app/v2/", response.location)


class LegacyWebUIConfigTestCase(MyTestCase):
    """The two settings that keep the previous WebUI, exactly as they are documented."""

    app_config_name = "legacyUI"

    def test_the_folders_are_the_legacy_webui(self):
        self.assertEqual("static_old", os.path.basename(self.app.static_folder))
        self.assertEqual(f"{DefaultConfigValues.LEGACY_STATIC_FOLDER}templates/", self.app.template_folder)

    def test_the_legacy_index_is_rendered(self):
        response = self.app.test_client().get("/")
        self.assertEqual(200, response.status_code)
        self.assertIn(b"/static/templates/baseline.html", response.data)

    def test_the_legacy_assets_are_served_under_the_unchanged_url(self):
        """Moving the folder must not move the URL: the legacy templates address their assets as
        /static/..., and that is resolved through whichever folder is configured."""
        client = self.app.test_client()
        for path in ["/static/favicon.png", "/static/css/menu.css", "/static/templates/baseline.html",
                     "/static/contrib/css/bootstrap-theme.css"]:
            self.assertEqual(200, client.get(path).status_code, path)

    def test_the_legacy_assets_are_cache_busted(self):
        """The previous WebUI serves its assets under stable names, so the version the versioned
        filter appends is what makes a browser pick them up after an update. It can only produce
        one by resolving the asset through the configured static folder."""
        response = self.app.test_client().get("/")
        self.assertIn(b"/static/favicon.png?v=", response.data)


class PreviewConfigRemapTestCase(MyTestCase):
    """A pi.cfg that still names the folder the WebUI was previewed from keeps working.

    The values below are spelled out rather than built from the constants they exercise. They are
    what administrators have in their pi.cfg and what the update notes tell them to remove, so a
    test that derived them would follow a wrong constant instead of catching it.
    """

    @staticmethod
    def _resolved(static_folder: str, template_folder: str | None = None) -> Flask:
        app = Flask(__name__)
        app.config[ConfigKey.STATIC_FOLDER] = static_folder
        if template_folder:
            app.config[ConfigKey.TEMPLATE_FOLDER] = template_folder
        _resolve_ui_folders(app)
        return app

    def test_the_documented_preview_configuration_is_remapped(self):
        with self.assertLogs("privacyidea.app", level="WARNING") as logs:
            app = self._resolved("static_new/", "static_new/dist/privacyidea-webui/browser/")
        self.assertEqual("static", os.path.basename(app.static_folder))
        # The preview pointed the template folder into the compiled WebUI, which holds no
        # templates, so it is reset rather than remapped.
        self.assertEqual(DefaultConfigValues.TEMPLATE_FOLDER, app.template_folder)
        self.assertIn("static_new", "".join(logs.output))

    def test_an_absolute_preview_path_is_remapped(self):
        """An appliance writes the absolute path of the installed package into pi.cfg."""
        with self.assertLogs("privacyidea.app", level="WARNING"):
            app = self._resolved("/opt/privacyidea/lib/privacyidea/static_new/")
        self.assertEqual("/opt/privacyidea/lib/privacyidea/static", app.static_folder)

    def test_the_static_folder_alone_is_remapped(self):
        """Only the first of the two documented lines is enough to break an installation."""
        with self.assertLogs("privacyidea.app", level="WARNING"):
            app = self._resolved("static_new/")
        self.assertEqual("static", os.path.basename(app.static_folder))
        self.assertEqual(DefaultConfigValues.TEMPLATE_FOLDER, app.template_folder)

    def test_a_configuration_without_the_preview_folder_is_left_alone(self):
        """A custom WebUI keeps the folders it names, and gets no deprecation warning."""
        app = self._resolved("mystatic", "mystatic/templates")
        self.assertEqual("mystatic", os.path.basename(app.static_folder))
        self.assertEqual("mystatic/templates", app.template_folder)


class MissingWebUIWarningTestCase(MyTestCase):
    """A static folder without a build is reported, rather than silently serving a broken page."""

    @staticmethod
    def _app_with_root(root_path: str) -> Flask:
        app = Flask(__name__, root_path=root_path)
        app.static_folder = os.path.join(root_path, DefaultConfigValues.STATIC_FOLDER)
        return app

    def test_a_missing_build_is_reported(self):
        with tempfile.TemporaryDirectory() as root_path:
            app = self._app_with_root(root_path)
            with self.assertLogs("privacyidea.app", level="WARNING") as logs:
                _warn_if_webui_missing(app)
        message = "".join(logs.output)
        # The warning has to name the way out, not just the problem.
        self.assertIn(DefaultConfigValues.LEGACY_STATIC_FOLDER, message)
        self.assertIn(ConfigKey.STATIC_FOLDER, message)
        self.assertIn(ConfigKey.TEMPLATE_FOLDER, message)

    def test_a_present_build_is_not_reported(self):
        with tempfile.TemporaryDirectory() as root_path:
            app = self._app_with_root(root_path)
            write_bundle(app.static_folder, "en")
            with self.assertNoLogs("privacyidea.app", level="WARNING"):
                _warn_if_webui_missing(app)

    def test_a_folder_the_administrator_chose_is_not_reported(self):
        """Pointing PI_STATIC_FOLDER somewhere else is a decision, not an accident."""
        with tempfile.TemporaryDirectory() as root_path:
            app = self._app_with_root(root_path)
            app.static_folder = os.path.join(root_path, "mystatic")
            with self.assertNoLogs("privacyidea.app", level="WARNING"):
                _warn_if_webui_missing(app)


class AlternativeUIConfigTestCase(MyTestCase):
    """A completely custom WebUI, as documented for PI_INDEX_HTML."""

    app_config_name = "altUI"

    def test_the_custom_index_is_rendered(self):
        response = self.app.test_client().get("/")
        self.assertEqual(200, response.status_code)
        self.assertIn(b"This is an alternative UI", response.data)
