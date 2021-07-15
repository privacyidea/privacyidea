# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2014-05-21 Cornelius Kölbel, <cornelius@privacyidea.org>
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
__doc__ = """This is the Web Form for creating the certificate request with
the web form in the browser.

This code is tested in test_ui_certificate.py
"""
__author__ = "Cornelius Kölbel, <cornelius@privacyidea.org>"

from flask import (Blueprint, render_template, request)
from privacyidea.api.lib.utils import (get_all_params,
                                       verify_auth_token, send_html)


cert_blueprint = Blueprint('cert_blueprint', __name__)


@cert_blueprint.before_request
def before_request():
    """
    This is executed before the request
    """
    # remove session from param and gather all parameters, either
    # from the Form data or from JSON in the request body.
    request.all_data = get_all_params(request)
    # Verify the authtoken!
    authtoken = request.all_data.get("authtoken")
    r = verify_auth_token(authtoken, ["user", "admin"])
    request.PI_username = r.get("username")
    request.PI_realm = r.get("realm")
    request.PI_role = r.get("role")


@cert_blueprint.route('', methods=['POST'])
def cert_form():
    instance = request.script_root
    if instance == "/":
        instance = ""
    # The backend URL should come from the configuration of the system.
    backend_url = ""
    authtoken = request.all_data.get("authtoken")
    ca = request.all_data.get("ca")
    return send_html(render_template("cert_request_form.html",
                                     instance=instance,
                                     backendUrl=backend_url, ca=ca,
                                     authtoken=authtoken))


@cert_blueprint.route('/enroll', methods=['POST'])
def cert_enroll():
    instance = request.script_root
    if instance == "/":
        instance = ""
    # The backend URL should come from the configuration of the system.
    backend_url = ""

    r = request
    request_key = request.form.get("requestkey")
    # Firefox creates line breaks, Google Chrome does not
    request_key = request_key.replace('\n', "")
    request_key = request_key.replace('\r', "")
    ca = request.form.get("ca")
    # TODO: Read the email address from the user source
    email = "meine"
    csr = """SPKAC={0!s}
CN={1!s},CN={2!s},O={3!s}
emailAddress={4!s}
""".format(request_key,
           request.PI_username,
           request.PI_role,
           request.PI_realm,
           email)
    # Take the CSR and run a token init
    from privacyidea.lib.token import init_token
    tokenobject = init_token({"request": csr,
                              "spkac": 1,
                              "type": "certificate",
                              "ca": ca})
    certificate = tokenobject.get_tokeninfo("certificate")
    serial = tokenobject.get_serial()
    cert_pem = certificate.replace('\r', "").replace('\n', "")
    cert_pem = cert_pem.replace("-----BEGIN CERTIFICATE-----", "")
    cert_pem = cert_pem.replace("-----END CERTIFICATE-----", "")
    render_context = {'instance': instance,
                      'backendUrl': backend_url,
                      'username': "{0!s}@{1!s}".format(request.PI_username,
                                                       request.PI_realm),
                      'role': request.PI_role,
                      'serial': serial,
                      'certificate': certificate,
                      'cert_pem': cert_pem }
    return send_html(render_template("token_enrolled.html", **render_context))
