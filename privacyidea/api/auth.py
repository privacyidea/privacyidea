# -*- coding: utf-8 -*-
#
# 2014-12-15 Cornelius Kölbel, info@privacyidea.org
#            Initial creation
#
# (c) Cornelius Kölbel
# Info: http://www.privacyidea.org
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
from flask import (Blueprint,
                   request,
                   url_for,
                   current_app,
                   jsonify,
                   abort,
                   g)
from lib.utils import (send_result, remove_session_from_param)
from ..lib.crypto import geturandom
from ..lib.error import AuthError
from ..lib.auth import verify_db_admin
import jwt
import json
from functools import wraps
from datetime import (datetime,
                      timedelta)
from privacyidea.lib.audit import getAudit



# TODO: provide the user object
#
#class LoginUser(object):
#    def __init__(self, uid, username, role=None):
#        self.id = uid
#        self.username = username
#        self.role = role


jwtauth = Blueprint('jwtauth', __name__)


@jwtauth.before_request
def before_request():
    """
    This is executed before the request
    """

    g.audit_object = getAudit(current_app.config)
    g.audit_object.log({"success": False,
                        "info": ""})
    request.all_data = remove_session_from_param(request.values, request.data)


@jwtauth.route('', methods=['POST'])
def get_auth_token():
    """
    This call verifies the credentials of the user and issues an
    authentication token, that is used for the later API calls. The
    authentication token has a validitiy, that is usually 1 hour.

    :jsonparam username: The username of the user who wants to authenticate to
        the API.
    :type username: basestring
    :jsonparam password: The password/credentials of the user who wants to
        authenticate to the API.

    :return: A json response with an authentication token, that needs to be
        used in any further request.

    :status 200: in case of success
    :status 401: if authentication fails

    **Example Authentication Request**:

    .. sourcecode:: http

       POST /auth HTTP/1.1
       Host: example.com
       Accept: application/json

       username=admin
       password=topsecret

    **Example Authentication Response**:

    .. sourcecode:: http

       HTTP/1.0 200 OK
       Content-Length: 354
       Content-Type: application/json

       {
            "id": 1,
            "jsonrpc": "2.0",
            "result": {
                "status": true,
                "value": {
                    "token": "eyJhbGciOiJIUz....jdpn9kIjuGRnGejmbFbM"
                }
            },
            "version": "privacyIDEA unknown"
       }

    **Response for failed authentication**:

    .. sourcecode:: http

       HTTP/1.1 401 UNAUTHORIZED
       Content-Type: application/json
       Content-Length: 203

       {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "error": {
              "code": -401,
              "message": "missing Authorization header"
            },
            "status": false
          },
          "version": "privacyIDEA unknown"
       }

    """
    validity = timedelta(hours=1)
    username = request.all_data.get("username")
    password = request.all_data.get("password")
    secret = current_app.secret_key
    if username is None:
        raise AuthError("Authentication failure",
                        "missing Username",
                        status=401)
    # TODO: Verify the password
    if current_app.config.get("TESTING"):
        # we do no password checking in TESTING mode
        pass
    else:
        if not verify_db_admin(username, password):
            raise AuthError("Authentication failure",
                            "Wrong credentials", status=401)

    token = jwt.encode({"username": username,
                        "nonce": geturandom(hex=True),
                        "exp": datetime.utcnow() + validity},
                       secret)
    return send_result({"token": token})


def auth_required(f):
    """
    This is a decorator for routes, that require to be authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        check_auth_token()
        return f(*args, **kwargs)
    return decorated_function


def check_auth_token():
    """
    This checks the authentication token
    
    You need to pass an authentication header:
    
        Authorization: <token>
        
    You can do this using httpie like this:
    
        http -j POST http://localhost:5000/system/getConfig Authorization:ewrt
    """
    auth_token = request.headers.get('Authorization', None)
    if auth_token is None:
        raise AuthError("Authentication failure",
                        "missing Authorization header",
                        status=401)
    try:
        r = jwt.decode(auth_token, current_app.secret_key)
    except jwt.DecodeError as err:
        raise AuthError("Authentication failure",
                        "error during decoding your token: %s" % err,
                        status=401)
    except jwt.ExpiredSignature as err:
        raise AuthError("Authentication failure",
                        "Your token has expired: %s" % err,
                        status=401)
    # TODO: more tests from the json web token
    g.logged_in_user = r.get("username")

