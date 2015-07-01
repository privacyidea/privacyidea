# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
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
__author__ = "Cornelius Kölbel, <cornelius@privacyidea.org>"

from flask import (Blueprint, render_template, request)

login_blueprint = Blueprint('login_blueprint', __name__)


@login_blueprint.route('/', methods=['GET'])
def single_page_application():
    instance = request.script_root
    if instance == "/":
        instance = ""
    # The backend URL should come from the configuration of the system.
    backend_url = ""

    browser_lang = request.accept_languages.best_match(["en", "de"])
    return render_template("index.html", instance=instance,
                           backendUrl=backend_url,
                           browser_lang=browser_lang)

