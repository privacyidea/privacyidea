# -*- coding: utf-8 -*-
#
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

from flask import (Blueprint, render_template, request,
                   current_app, g)
from privacyidea.api.lib.utils import send_html
from privacyidea.api.lib.prepolicy import is_remote_user_allowed
from privacyidea.lib.passwordreset import is_password_reset
from privacyidea.lib.error import HSMException
from privacyidea.lib.realm import get_realms
from privacyidea.lib.policy import PolicyClass, ACTION, SCOPE, Match
from privacyidea.lib.subscriptions import subscription_status
from privacyidea.lib.utils import get_client_ip
from privacyidea.lib.config import get_from_config, SYSCONF
from privacyidea.lib.queue import has_job_queue

DEFAULT_THEME = "/static/contrib/css/bootstrap-theme.css"

login_blueprint = Blueprint('login_blueprint', __name__)


@login_blueprint.before_request
def before_request():
    """
    This is executed before the request
    """
    g.policy_object = PolicyClass()
    g.audit_object = None
    # access_route contains the ip addresses of all clients, hops and proxies.
    g.client_ip = get_client_ip(request, get_from_config(SYSCONF.OVERRIDECLIENT))


@login_blueprint.route('/', methods=['GET'])
def single_page_application():
    instance = request.script_root
    if instance == "/":
        instance = ""
    # The backend URL should come from the configuration of the system.
    backend_url = ""

    if current_app.config.get("PI_UI_DEACTIVATED"):
        # Do not provide the UI
        return send_html(render_template("deactivated.html"))

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
    # Get the logo file
    logo = current_app.config.get("PI_LOGO", "privacyIDEA1.png")
    browser_lang = request.accept_languages.best_match(["en", "de", "de-DE"], default="en").split("-")[0]
    # The page title can be configured in pi.cfg
    page_title = current_app.config.get("PI_PAGE_TITLE", "privacyIDEA Authentication System")
    # check if login with REMOTE_USER is allowed.
    remote_user = ""
    password_reset = False
    if not hasattr(request, "all_data"):
        request.all_data = {}
    # Depending on displaying the realm dropdown, we fill realms or not.
    realms = ""
    realm_dropdown = Match.action_only(g, scope=SCOPE.WEBUI, action=ACTION.REALMDROPDOWN)\
        .policies(write_to_audit_log=False)
    if realm_dropdown:
        try:
            realm_dropdown_values = Match.action_only(g, scope=SCOPE.WEBUI, action=ACTION.REALMDROPDOWN) \
                .action_values(unique=False, write_to_audit_log=False)
            # Use the realms from the policy.
            realms = ",".join(realm_dropdown_values)
        except AttributeError as _e:
            # The policy is still a boolean realm_dropdown action
            # Thus we display ALL realms
            realms = ",".join(get_realms())

    try:
        if is_remote_user_allowed(request):
            remote_user = request.remote_user
        password_reset = is_password_reset(g)
        hsm_ready = True
    except HSMException:
        hsm_ready = False

    # Use policies to determine the customization of menu
    # and baseline. get_action_values returns an array!
    sub_state = subscription_status()
    customization_menu_file = Match.action_only(g, action=ACTION.CUSTOM_MENU,
                                                scope=SCOPE.WEBUI)\
        .action_values(unique=True, allow_white_space_in_action=True, write_to_audit_log=False)
    if len(customization_menu_file) and list(customization_menu_file)[0] \
            and sub_state not in [1, 2]:
        customization_menu_file = list(customization_menu_file)[0]
    else:
        customization_menu_file = "templates/menu.html"
    customization_baseline_file = Match.action_only(g, action=ACTION.CUSTOM_BASELINE,
                                                    scope=SCOPE.WEBUI) \
        .action_values(unique=True, allow_white_space_in_action=True, write_to_audit_log=False)
    if len(customization_baseline_file) and list(customization_baseline_file)[0] \
            and sub_state not in [1, 2]:
        customization_baseline_file = list(customization_baseline_file)[0]
    else:
        customization_baseline_file = "templates/baseline.html"

    login_text = Match.action_only(g, action=ACTION.LOGIN_TEXT, scope=SCOPE.WEBUI) \
        .action_values(unique=True, allow_white_space_in_action=True, write_to_audit_log=False)
    if len(login_text) and list(login_text)[0] and sub_state not in [1, 2]:
        login_text = list(login_text)[0]
    else:
        login_text = ""

    render_context = {
        'instance': instance,
        'backendUrl': backend_url,
        'browser_lang': browser_lang,
        'remote_user': remote_user,
        'theme': theme,
        'password_reset': password_reset,
        'hsm_ready': hsm_ready,
        'has_job_queue': str(has_job_queue()),
        'customization': customization,
        'custom_css': custom_css,
        'customization_menu_file': customization_menu_file,
        'customization_baseline_file': customization_baseline_file,
        'realms': realms,
        'external_links': external_links,
        'login_text': login_text,
        'logo': logo,
        'page_title': page_title
    }

    return send_html(render_template("index.html", **render_context))
