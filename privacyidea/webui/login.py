# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2017-11-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add custom baseline and menu
# 2016-01-07 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add password reset
# 2015-11-04 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add REMOTE_USER check
# 2014-12-22 Cornelius Kölbel, <cornelius@privacyidea.org>
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__doc__ = """This is the starting point for the single web application.
Other html code is dynamically loaded via angularJS and located in
/static/views/...
"""
__author__ = "Cornelius Kölbel <cornelius@privacyidea.org>"

import logging
import os
from collections.abc import Callable
from typing import TypeVar

from flask import (Blueprint, render_template, request,
                   current_app, g, redirect, abort, Response)
from markupsafe import escape

from privacyidea.api.lib.prepolicy import is_remote_user_allowed
from privacyidea.api.lib.postpolicy import hide_version
from privacyidea.api.lib.utils import (send_html, send_result, verify_auth_token, check_unquote,
                                       get_auth_token_from_request, logged_in_user_from_token, set_request_context)
from privacyidea.lib.config import get_from_config, SYSCONF, get_privacyidea_node
from privacyidea.lib.error import HSMException, PolicyError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.passwordreset import is_password_reset
from privacyidea.lib.policies.actions import PolicyAction, PasskeyLoginButtonOptions
from privacyidea.lib.policy import PolicyClass, SCOPE, Match, REMOTE_USER
from privacyidea.lib.queue import has_job_queue
from privacyidea.lib.realm import get_realms
from privacyidea.lib.subscriptions import subscription_status
from privacyidea.lib.utils import get_client_ip, get_version_number, get_plugin_info_from_useragent

log = logging.getLogger(__name__)

DEFAULT_THEME = "/static/contrib/css/bootstrap-theme.css"
# Layout of the compiled WebUI below the static folder. It mirrors "outputPath" in
# static/angular.json, and the locale directory below it mirrors the i18n "subPath".
WEBUI_DIST_PATH = ("dist", "privacyidea-webui", "browser")
# note: the empty comment in the following line allows to include it in the docs
DEFAULT_LANGUAGE_LIST = ['en', 'de', 'nl', 'zh_Hant', 'fr', 'es', 'tr', 'cs',
                         'it', 'ta', 'pt', 'ru', 'uk']  #:

# Cookie that records an explicit UI language choice (set by the WebUI language switcher).
# It is consulted before the browser's Accept-Language header when resolving the locale.
LOCALE_COOKIE_NAME = "pi_ui_locale"

# Meta tag carrying the WSGI SCRIPT_NAME prefix to the served WebUI bundle.
# Keep the name in sync with scriptRoot() in the WebUI's core/locale.ts.
SCRIPT_ROOT_META_NAME = "pi-script-root"

# Case-insensitive, separator-insensitive lookup: normalized key → canonical BCP 47 locale
_LOCALE_CANONICAL = {lang.replace("_", "-").lower(): lang.replace("_", "-") for lang in DEFAULT_LANGUAGE_LIST}


def _canonical_locale(locale: str, lang_list: list[str] | None = None) -> str | None:
    """Return the canonical BCP 47 locale for a given input, or None if unknown."""
    lookup = _LOCALE_CANONICAL
    if lang_list is not None:
        lookup = {lang.replace("_", "-").lower(): lang.replace("_", "-") for lang in lang_list}
    return lookup.get(locale.replace("_", "-").lower())


login_blueprint = Blueprint('login_blueprint', __name__)


def get_accepted_language():
    """Return the accepted language from the request"""
    # If we are not in the request context, return None to use the default locale
    if not request:
        return None
    # read pi.cfg and checks if preferred language is set. Otherwise, default list is selected.
    pi_lang_list = get_app_config_value("PI_PREFERRED_LANGUAGE", default=DEFAULT_LANGUAGE_LIST)
    # try to match the language from the users accept header the browser transmits.
    # (The best match wins)
    return request.accept_languages.best_match(pi_lang_list, default=pi_lang_list[0])


def get_preferred_language() -> str | None:
    """Resolve the preferred UI locale: an explicit choice stored in the locale cookie
    takes precedence, otherwise fall back to the browser's Accept-Language header and
    finally the configured default. Returns a canonical locale code or None outside a
    request context."""
    if not request:
        return None
    pi_lang_list = get_app_config_value("PI_PREFERRED_LANGUAGE", default=DEFAULT_LANGUAGE_LIST)
    # An explicit choice (set by the language switcher) wins over the browser preference.
    cookie_locale = request.cookies.get(LOCALE_COOKIE_NAME)
    if cookie_locale:
        canonical = _canonical_locale(cookie_locale, pi_lang_list)
        if canonical:
            return canonical
    return request.accept_languages.best_match(pi_lang_list, default=pi_lang_list[0])


@login_blueprint.before_request
def before_request():
    """
    This is executed before the request
    """
    g.policy_object = PolicyClass()
    # access_route contains the ip addresses of all clients, hops and proxies.
    g.client_ip = get_client_ip(request, get_from_config(SYSCONF.OVERRIDECLIENT))
    set_request_context()
    # The pages are only requested with GET, so a body, even a broken one, must not fail them
    g.request_data = check_unquote(request, request.args.to_dict())
    # The page names no token, but the check of the remote user matches the policies with g.serial
    g.serial = None
    # Populate the user agent so that policies restricted by user agent (e.g. a
    # user-agent-scoped hide_version policy) match consistently with the API
    # blueprints, which set g.user_agent in their before_request handlers.
    ua_name, _ua_version, _ua_comment = get_plugin_info_from_useragent(request.user_agent.string)
    g.user_agent = ua_name
    # Resolve the logged-in user from a presented JWT. This lets the
    # hide_version policy still expose the version number to authenticated
    # WebUI requests (e.g. the /config call made after login or on reload),
    # while it stays hidden for the anonymous login page.
    g.logged_in_user = {}
    auth_token = get_auth_token_from_request()
    if auth_token:
        try:
            user = verify_auth_token(auth_token, ["user", "admin"])
            g.logged_in_user = logged_in_user_from_token(user)
        except Exception as error:
            log.debug(f"No valid auth token presented to the login blueprint: {error}")


@login_blueprint.after_request
def after_request(response):
    """
    Lightweight after_request for the WebUI login blueprint.

    Unlike the shared after_request in before_after.py this does NOT sign the
    response: the login page and the /config endpoint are anonymous and were
    never signed, so there is no reason to load the audit private key on every
    page view. We only set cache-control headers and apply the optional
    version stripping.
    """
    response.headers['Cache-Control'] = 'no-cache'
    response = hide_version(request, response)
    return response


SettingValue = TypeVar("SettingValue")


def _read_policy_setting(setting: str, read_setting: Callable[[], SettingValue],
                         default: SettingValue) -> SettingValue:
    """
    Reads one setting of the start page from the policies. If a policy check fails, the setting uses *default* and
    the log file gets the error. Examples are ``Raise an error`` for missing data, which every ``userinfo``, token and
    container condition has on the start page, an invalid comparison, and two policies with the same priority and
    different values. Thus a policy error changes only the setting of its own policy, and the start page stays
    available.

    :param setting: the name of the setting in the log file, usually the policy action
    :param read_setting: reads the setting from the policies
    :param default: the value of the setting if no policy applies
    :return: the value of the setting
    """
    try:
        return read_setting()
    except PolicyError as error:
        log.error(f"The WebUI start page uses the default value of the setting '{setting}', because the check of its "
                  f"policies failed: {error}")
        return default


def _start_page_policies(scope: str, action: str) -> list[dict]:
    """
    Returns the policies of the scope with the action that apply to the start page. If the policy check fails, the
    list is empty, see :func:`_read_policy_setting`.
    """
    return _read_policy_setting(
        action,
        lambda: Match.action_only(g, scope=scope, action=action).policies(write_to_audit_log=False),
        [])


def _start_page_action_value(action: str, allow_white_space_in_action: bool = False) -> str:
    """
    Returns the value of the WebUI action from the policy with the highest priority that applies to the start page.
    Without such a policy, or if the policy check fails, the value is empty, see :func:`_read_policy_setting`.
    """
    action_values = _read_policy_setting(
        action,
        lambda: Match.action_only(g, scope=SCOPE.WEBUI, action=action).action_values(
            unique=True, allow_white_space_in_action=allow_white_space_in_action, write_to_audit_log=False),
        {})
    return next(iter(action_values), "")


def _realm_dropdown_realms() -> str:
    """
    Returns the realms of the realm dropdown as a comma-separated list. Without a realm_dropdown policy, the list is
    empty.
    """
    realm_dropdown = Match.action_only(g, scope=SCOPE.WEBUI, action=PolicyAction.REALMDROPDOWN)
    if not realm_dropdown.any(write_to_audit_log=False):
        return ""
    try:
        # Use the realms from the policy.
        return ",".join(realm_dropdown.action_values(unique=False, write_to_audit_log=False))
    except AttributeError:
        # The policy is still a boolean realm_dropdown action
        # Thus we display ALL realms
        return ",".join(get_realms())


def get_render_context():
    """
    Provides a dictionary with configurations for the web ui.

    A policy error changes only the setting of its own policy: the setting uses its default value, see
    :func:`_read_policy_setting`.
    """
    instance = request.script_root
    if instance == "/":
        instance = ""
    # The backend URL should come from the configuration of the system.
    backend_url = ""

    if current_app.config.get("PI_UI_DEACTIVATED"):
        # Do not provide the UI
        return {}

    # The default theme. We can change this later
    theme = current_app.config.get("PI_CSS", DEFAULT_THEME)
    theme = theme.strip('/')
    # Get further customizations
    customization = current_app.config.get("PI_CUSTOMIZATION",
                                           "/static/customize/")
    customization = customization.strip('/')
    custom_css = customization + "/css/custom.css" if current_app.config.get("PI_CUSTOM_CSS") else ""
    # Enrollment-Wizard:
    #    PI_CUSTOMIZATION/views/includes/token.enroll.pre.top.html
    #    PI_CUSTOMIZATION/views/includes/token.enroll.pre.bottom.html
    #    PI_CUSTOMIZATION/views/includes/token.enroll.post.top.html
    #    PI_CUSTOMIZATION/views/includes/token.enroll.post.bottom.html
    # Get the hidden external links
    external_links = current_app.config.get("PI_EXTERNAL_LINKS", True)
    # Read the UI translation warning
    translation_warning = current_app.config.get("PI_TRANSLATION_WARNING", False)
    # Get the logo file
    logo = current_app.config.get("PI_LOGO", "privacyIDEA1.png")
    browser_lang = get_accepted_language()
    # The page title can be configured in pi.cfg
    page_title = current_app.config.get("PI_PAGE_TITLE", "privacyIDEA Authentication System")
    # check if login with REMOTE_USER is allowed.
    remote_user = ""
    force_remote_user = False
    password_reset = False
    if not hasattr(request, "all_data"):
        request.all_data = {}
    # Depending on displaying the realm dropdown, we fill realms or not.
    realms = _read_policy_setting(PolicyAction.REALMDROPDOWN, _realm_dropdown_realms, "")
    show_node = get_privacyidea_node() if _start_page_policies(SCOPE.WEBUI, PolicyAction.SHOW_NODE) else ""

    try:
        remote_user_mode = _read_policy_setting(PolicyAction.REMOTE_USER,
                                                lambda: is_remote_user_allowed(request, write_to_audit_log=False),
                                                REMOTE_USER.DISABLE)
        force_remote_user = remote_user_mode == REMOTE_USER.FORCE
        if remote_user_mode != REMOTE_USER.DISABLE:
            remote_user = request.remote_user
        password_reset = _read_policy_setting(PolicyAction.PASSWORDRESET, lambda: is_password_reset(g), False)
        hsm_ready = True
    except HSMException:
        hsm_ready = False

    # Use policies to determine the customization of menu and baseline, the login text and the privacy statement link.
    # With the subscription states 1 and 2, the defaults apply.
    sub_state = subscription_status()
    customization_menu_file = _start_page_action_value(PolicyAction.CUSTOM_MENU, allow_white_space_in_action=True)
    if not customization_menu_file or sub_state in [1, 2]:
        customization_menu_file = "templates/menu.html"
    customization_baseline_file = _start_page_action_value(PolicyAction.CUSTOM_BASELINE,
                                                           allow_white_space_in_action=True)
    if not customization_baseline_file or sub_state in [1, 2]:
        customization_baseline_file = "templates/baseline.html"

    login_text = _start_page_action_value(PolicyAction.LOGIN_TEXT, allow_white_space_in_action=True)
    if sub_state in [1, 2]:
        login_text = ""

    gdpr_link = _start_page_action_value(PolicyAction.GDPR_LINK, allow_white_space_in_action=True)
    if sub_state in [1, 2]:
        gdpr_link = ""

    passkey_login = _start_page_action_value(PolicyAction.PASSKEY_LOGIN) or PasskeyLoginButtonOptions.SHOW

    # The version number is injected into the rendered login HTML, which the
    # hide_version postpolicy cannot strip (it only rewrites JSON responses).
    # Blank it here for the anonymous login page when the hide_version policy
    # is active. Authenticated requests (valid JWT) still receive it.
    hide_version_active = _start_page_policies(SCOPE.HARDENING, PolicyAction.HIDE_VERSION)
    show_version = bool(getattr(g, "logged_in_user", None)) or not hide_version_active
    version_number = get_version_number() if show_version else ""

    render_context: dict = {
        'instance': instance,
        'backendUrl': backend_url,
        'browser_lang': browser_lang,
        'remote_user': remote_user,
        'force_remote_user': force_remote_user,
        'theme': theme,
        'translation_warning': translation_warning,
        'password_reset': password_reset,
        'hsm_ready': hsm_ready,
        'has_job_queue': str(has_job_queue()),
        'customization': customization,
        'custom_css': custom_css,
        'customization_menu_file': customization_menu_file,
        'customization_baseline_file': customization_baseline_file,
        'realms': realms,
        'show_node': show_node,
        'external_links': external_links,
        'login_text': login_text,
        'gdpr_link': gdpr_link,
        'logo': logo,
        'page_title': page_title,
        'privacyideaVersionNumber': version_number,
        'passkey_login': passkey_login,
    }
    return render_context


def _serve_locale(locale: str) -> Response | None:
    pi_lang_list = get_app_config_value("PI_PREFERRED_LANGUAGE", default=DEFAULT_LANGUAGE_LIST)
    canonical = _canonical_locale(locale, pi_lang_list)
    if not canonical:
        return None
    dist = os.path.join(current_app.static_folder, *WEBUI_DIST_PATH, canonical)
    index_file = os.path.join(dist, "index.html")
    if not os.path.isfile(index_file):
        return None
    # The bundle's <base href> and asset/API URLs are baked in at build time as
    # absolute, root-relative paths. Behind a reverse-proxy sub-path mount
    # (Apache WSGIScriptAlias, uwsgi mount-point, ...) those need the WSGI
    # SCRIPT_NAME prefix prepended per request, so this is templated here
    # rather than served as a static file.
    script_root = request.script_root
    with open(index_file, encoding="utf-8") as f:
        content = f.read()
    content = content.replace('<base href="/', f'<base href="{script_root}/', 1)
    # A meta tag rather than an inline script: the app's CSP allows only
    # script-src 'self', so an inline script would be blocked and the frontend
    # would fall back to an empty prefix on exactly the mounts this supports.
    content = content.replace(
        "</head>",
        f'<meta name="{SCRIPT_ROOT_META_NAME}" content="{escape(script_root)}"></head>',
        1
    )
    return send_html(content)


def is_new_webui_served() -> bool:
    """
    Whether the configured static folder holds the compiled WebUI. Without it the previous WebUI is rendered.
    """
    return os.path.isfile(os.path.join(current_app.static_folder, *WEBUI_DIST_PATH, "en", "index.html"))


def _with_query_string(path: str) -> str:
    """
    Appends the query string of the request to *path*, so that a redirect to the WebUI keeps the parameters of the
    page. The WebUI sends them with its request to /config, where the request data conditions of the WebUI policies
    read them.
    """
    query_string = request.query_string.decode()
    # A concatenation and not an f-string, because CodeQL accepts a value on the right side of a "+" as a safe part of
    # a redirect target, but not a formatted value
    return path + "?" + query_string if query_string else path


@login_blueprint.route('/', methods=['GET'])
def single_page_application() -> Response:
    if current_app.config.get("PI_UI_DEACTIVATED"):
        # Do not provide the UI
        return send_html(render_template("deactivated.html"))
    # New UI: if a localized build is present, redirect to its locale entrypoint
    # under /app/v2/ so the Angular router runs with the correct base href.
    locale = get_preferred_language()
    if locale and locale != "en":
        url_locale = locale.replace("_", "-")
        dist = os.path.join(current_app.static_folder, *WEBUI_DIST_PATH, url_locale)
        if os.path.isfile(os.path.join(dist, "index.html")):
            return redirect(_with_query_string(f"{request.script_root}/app/v2/{url_locale}/"))
    if is_new_webui_served():
        return redirect(_with_query_string(f"{request.script_root}/app/v2/"))
    # Fallback to the classic AngularJS UI: no new-UI build exists, so render the
    # legacy index template from the server.
    render_context = get_render_context()
    index_page = current_app.config.get("PI_INDEX_HTML") or "index.html"
    return send_html(render_template(index_page, **render_context))


@login_blueprint.route('/app/v2/<locale>', methods=['GET'])
@login_blueprint.route('/app/v2/<locale>/', defaults={'subpath': ''}, methods=['GET'])
@login_blueprint.route('/app/v2/<locale>/<path:subpath>', methods=['GET'])
def single_page_application_locale(locale: str, subpath: str | None = None) -> Response:
    pi_lang_list = get_app_config_value("PI_PREFERRED_LANGUAGE", default=DEFAULT_LANGUAGE_LIST)
    canonical = _canonical_locale(locale, pi_lang_list)
    if not canonical:
        # The first segment is not a known locale (e.g. an app route like
        # /app/v2/login). Serve the SPA shell for the user's preferred locale
        # (cookie set by the language switcher, then Accept-Language, then the
        # configured default) instead of always defaulting to English.
        if request.accept_mimetypes.accept_html:
            preferred = get_preferred_language() or "en"
            return _serve_locale(preferred) or _serve_locale("en") or abort(404)
        abort(404)
    if canonical != locale or subpath is None:
        # The subpath is concatenated for CodeQL, as in _with_query_string
        return redirect(_with_query_string(f"{request.script_root}/app/v2/{canonical}/" + (subpath or "")))
    return _serve_locale(locale) or abort(404)


@login_blueprint.route('/config', methods=['GET'])
def get_ui_config():
    render_context = get_render_context()
    # For the new UI we do not define a default logo
    logo = current_app.config.get("PI_LOGO", "")
    render_context['logo'] = logo
    return send_result(render_context)

