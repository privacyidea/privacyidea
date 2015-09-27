# -*- coding: utf-8 -*-
#
# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2015-05-19 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add setting validity period
#
# 2015-03-14 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Add get_serial_by_otp
# 2014-12-08 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Complete rewrite during flask migration
#            Try to provide REST API
#
# privacyIDEA is a fork of LinOTP. Some code is adapted from
# the system-controller from LinOTP, which is
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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

from flask import Blueprint
from ..lib.log import log_with
from lib.utils import (optional,
                       send_result,
                       send_csv_result, required, get_all_params)
from ..lib.user import get_user_from_param
from ..lib.token import (init_token, get_tokens_paginate, assign_token,
                         unassign_token, remove_token, enable_token,
                         revoke_token,
                         reset_token, resync_token, set_pin_so, set_pin_user,
                         set_pin, set_description, set_count_window,
                         set_sync_window, set_count_auth,
                         set_hashlib, set_max_failcount, set_realms,
                         copy_token_user, copy_token_pin, lost_token,
                         get_serial_by_otp, get_tokens,
                         set_validity_period_end, set_validity_period_start)
from werkzeug.datastructures import FileStorage
from cgi import FieldStorage
from privacyidea.lib.error import (ParameterError, TokenAdminError)
from privacyidea.lib.importotp import (parseOATHcsv, parseSafeNetXML,
                                       parseYubicoCSV, parsePSKCdata)
import logging
from lib.utils import getParam
from flask import request, g
from privacyidea.lib.audit import getAudit
from flask import current_app
from privacyidea.lib.policy import PolicyClass, ACTION
from privacyidea.api.lib.prepolicy import (prepolicy, check_base_action,
                                           check_token_init, check_token_upload,
                                           check_max_token_user,
                                           check_max_token_realm,
                                           init_tokenlabel, init_random_pin,
                                           encrypt_pin, check_otp_pin,
                                           check_external)
from privacyidea.api.auth import (user_required, admin_required)
from privacyidea.api.audit import audit_blueprint
from privacyidea.api.user import user_blueprint
from .caconnector import caconnector_blueprint


token_blueprint = Blueprint('token_blueprint', __name__)
log = logging.getLogger(__name__)

__doc__ = """
The token API can be accessed via /token.

You need to authenticate to gain access to these token
functions.
If you are authenticated as administrator, you can manage all tokens.
If you are authenticated as normal user, you can only manage your own tokens.
Some API calls are only allowed to be accessed by adminitrators.

To see how to authenticate read :ref:`rest_auth`.
"""

@token_blueprint.before_request
@audit_blueprint.before_request
@user_blueprint.before_request
@caconnector_blueprint.before_request
@user_required
def before_request():
    """
    This is executed before the request.

    user_required checks if there is a logged in admin or user

    The checks for ONLY admin are preformed in api/system.py
    """
    # remove session from param and gather all parameters, either
    # from the Form data or from JSON in the request body.
    request.all_data = get_all_params(request.values, request.data)

    g.policy_object = PolicyClass()
    g.audit_object = getAudit(current_app.config)
    # Already get some typical parameters to log
    serial = getParam(request.all_data, "serial")
    realm = getParam(request.all_data, "realm")
    # log it
    g.audit_object.log({"success": False,
                        "serial": serial,
                        "realm": realm,
                        "client": request.remote_addr,
                        "client_user_agent": request.user_agent.browser,
                        "privacyidea_server": request.host,
                        "action": "%s %s" % (request.method, request.url_rule),
                        "action_detail": "",
                        "info": ""})

    if g.logged_in_user.get("role") == "user":
        # A user is calling this API
        # In case the token API is called by the user and not by the admin we
        #  need to restrict the token view.
        CurrentUser = get_user_from_param({"user":
                                               g.logged_in_user.get(
                                                   "username"),
                                           "realm": g.logged_in_user.get(
                                               "realm")})
        request.all_data["user"] = CurrentUser.login
        request.all_data["resolver"] = CurrentUser.resolver
        request.all_data["realm"] = CurrentUser.realm
        g.audit_object.log({"user": CurrentUser.login,
                            "realm": CurrentUser.realm})
    else:
        # An administrator is calling this API
        g.audit_object.log({"administrator": g.logged_in_user.get("username")})
        # TODO: Check is there are realm specific admin policies, so that the
        # admin is only allowed to act on certain realms
        # If now realm is specified, we need to add "filterrealms".
        # If the admin tries to view realms, he is not allowed to, we need to
        #  raise an exception.


@token_blueprint.route('/init', methods=['POST'])
@prepolicy(check_max_token_realm, request)
@prepolicy(check_max_token_user, request)
@prepolicy(check_token_init, request)
@prepolicy(init_tokenlabel, request)
@prepolicy(init_random_pin, request)
@prepolicy(encrypt_pin, request)
@prepolicy(check_otp_pin, request)
@prepolicy(check_external, request, action="init")
@log_with(log, log_entry=False)
def init():
    """
    create a new token.

    :jsonparam otpkey: required: the secret key of the token
    :jsonparam genkey: set to =1, if key should be generated. We either
                   need otpkey or genkey
    :jsonparam keysize: the size (byte) of the key. Either 20 or 32. Default is 20
    :jsonparam serial: required: the serial number/identifier of the token
    :jsonparam description: A description for the token
    :jsonparam pin: the pin of the user pass
    :jsonparam user: the login user name. This user gets the token assigned
    :jsonparam realm: the realm of the user.
    :jsonparam type: the type of the token
    :jsonparam tokenrealm: additional realms, the token should be put into
    :jsonparam otplen: length of the OTP value
    :jsonparam hashlib: used hashlib sha1 oder sha256

    :return: a json result with a boolean "result": true

    **Example response**:

       .. sourcecode:: http

           HTTP/1.1 200 OK
           Content-Type: application/json

           {
              "detail": {
                "googleurl": {
                  "description": "URL for google Authenticator",
                  "img": "<img    width=250   src=\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAcIAAAHCAQAAAABUY/ToAAADsUlEQVR4nO2czY3bMBCF34QCfKSALcClyB2kpCAlpQOxlBQQgDwaoPBy4I+p9W4OSRaWF28OgizxgylgMJw/0oi/k/DlL0FApEiRIkWKFCnyeKRVmdrjNAFh3srTMuSS2qjLg2cr8pDkQpKMgF3SBITz1QA4YolVfQA4kiT35CNmK/JQZLM8aQaWH+3pEkEgTZlhBojksgGAAS7/83+K/ORkOF/NLtismiCfYXbOd+AxZivygCTXdCLCDJRLfTbhTo4wW5FHIJtyeAJIAJb4AobLBIP/ZQRAwMcyakxIPtd3ivw4EqObXJzody9t1EKS63N9p8iPI4sO3QTwGSSbA1Q0x+cWunWRDolsUjSnxvau6VB0xMIMrp4EPAnAkWsjpEMiu+ysD1mUZomuKk1/i6WtedIhkXupS1MEsMRmaVafh7dVfXwGV0D+kMj3yXDOsIsngXQiV59R0tZIE7jC0b4VA3WE2Yo8CtkTPy7b8sPA8HWbWML6dCKAqxG4GgADw+weOVuRRyTHuGztbk+PwdqQPIzTWibyDbJWVdOJQDLj9xkod4yOCK2gbzZvVpyip/xOkR9B4maCbnF8c53vHGuuLVaTHRLZpBgYgweAVP0hLPElA+mFtVrvf3W/aTM+brYij0j23o8JthAweNc1J5cCmSFNYDCAS5wfOVuRRyT7QpVL9F6XLN/zjhG4ZSAHj1trmcgmLcfoWoq6/B4LZLeqBxmVpxb5WobYfl8vaxfU7DSA4mdLh0S+TW5W2xXTiaWZ0WbALqiXmi5KU/n5tN8p8r+TzaqUH936MKNW6/2uIkvZIZF/IEleDfAZZnYi1zSB/DmVpa2YJZtVLxP5JmnfWCutty5qwNcFrWSsV2xGxs3+03+K/Cxk74WtTWflDr652L0XtoZuylOLvJNb9H7XPzQ0DOX9RTokcpAhAzRYpN4LO5TsI1rQLx0SOci4z7VcSuvQZgxWX1gfbfBX1ctEvhLupbZSe5bNQK0Jv/dTe9U6RL6WtoIBqDs33NA7Xdey3SYzrWUi99L8IfJW4cC4pYNjg+Ow/+O5vlPkx5OpnSsUzler2cbS29g8pmBmWH6elGMU+UqaFwS0NBBa9O45Rmhr26Mof0jkTt440MNlC9aOGQqzA8McaQs34xJfsv3rf4r8XOTduR+lezHN5fyh0sdY76qz/cDZijwwGcxqs0c9gNFx5w9t7e18hNmKPBRZ7NDtXKF6V1qp2e9qtZ7DkOf6TpEiRYoUKVKkyPfkNyq7YXtdjZCIAAAAAElFTkSuQmCC\"/>",
                  "value": "otpauth://hotp/mylabel?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&counter=0"
                },
                "oathurl": {
                  "description": "URL for OATH token",
                  "img": "<img    width=250   src=\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAcIAAAHCAQAAAABUY/ToAAADfElEQVR4nO2cTYrjMBCFX40EvZRvkKPIN5gz9c3so/QBBqxlwObNQpIlp2cYaBI6zrxamDjyhywo6leyEV+T+ccXQUCkSJEiRYoUKfL5SCviy7+zmZWBAbARmwGpPjXeZU6RL0ZGkuQCAMkMCCTmqlJ8HwAb4UiSPJJfn1Pki5Fpty8AED/MEBeAU/JoA52pOuk6Rd6f9H/60xBWbwCMyG7Mg0j3mlPky5OOiB9v5AQACCQnONr4yDlFnpisdigQQAIM4WpE2oyAWy0umyfCku1QX5A81zpFPo5EHybDEXH566U+FUlyOtc6RT6OzHao2RfOgwMQVqBYJADz5WrFVN1jTpGvRRY7FLmCExwR8y3JKbAm84HkFFawieyQyCpFJRagaMniikqRK4C9KpSVa3GULxN5lGZp8n3kinrr2H5xCmsZlQ6JPEiLqbPzKh5sRefL4uJILq4MyJeJPEjzZb2jQnFopQmSH3FZw2SHRB6lC3bQeatDiI2wghOAaoykQyKb7L2OzQPpjZjNEUgDDNiMSAMAOFpchjvNKfK1yGqHlkNetofYxclVs5RzNfkykZ/J4rc+So+++S2zy1ofDVezMXmURtoZ1ynyEeRuh1xXSiwJPtCFRyUygupDIm+l5fa9Q+Na0rT8yCG3lw6JPEqtMZaCUNfmyPWhBajtMx46Iedap8jHkV2/DK0cDWBXqapczY0ptxd5kFZjLEqzlJi6C4WyHYJjHZAOieyk2aGsSNyjoF2l0Jsg9TpE/oVMHpgvK8wupRZkIwDMQy0S5QMfbVfsOdcp8v5kF1M3N9ZaGrX/sbf2g+yQyFtpPdW2/75pTtGX5tWCcnuRt9L1OtguLcFve9DazmrpkMheOn3Ju4aA4tX6gVopiurbi7yV3Lc3IJ+vh0VuHoBbAWyeSH41hF+fzzKea50iH012QdE8OPJ92MzG9HY4NJRDpqt9+9uKfEayffeDU/J7z3UzG8PVSlqfPMrlm99W5FOSsUY8Noarmdkb+T7UTSF7Wv8kbyvyqcguL+u23k/7cDvdmm9Vpxb5LzLbobErObbc/lFzijw3eZtvcR4WAtjKx2Lmn1djztBAWN5ZPX3X24p8RrI719HcWNnsEVoz1vWPyJeJ7KXYoTln7A4Wcz6/eQL7xxxyRr95IlwNskMiezF941ykSJEiRYoU+Z+TvwF49nApsKFZZAAAAABJRU5ErkJggg==\"/>",
                  "value": "oathtoken:///addToken?name=mylabel&lockdown=true&key=3132333435363738393031323334353637383930"
                },
                "otpkey": {
                  "description": "OTP seed",
                  "img": "<img    width=200   src=\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAUoAAAFKAQAAAABTUiuoAAAB70lEQVR4nO2aTY6jQAyFPw9IWYI0B+ijwNHhKH0DWLZU6PXCVYSOZkF6xM/CXkQkfIsnWRU/22ViZ4x/9pIQaKCBBhpooEeilqPGrAWzdjGYy8/94QICfQftJEkTAIsBlYBKkqSf6DECAn0HnfMRkj4fnjfrATOrzxEQ6I6oX74bYGJuzxIQ6H9kqySqSjCfISDQX6CNpKE8mX18lT9GpXMEBLofHc3M7WA/19B9PgQsbgnPEBDonrCXyZMB/HMaFZOnu6DWz2aMZqaBZ79Vw9gu0W/dBsU7qm4CL16aKq9geonhcq2BlqR4jirRSYImoaF8eO8c2boeXR38YnRavIwJkNFUsg1xudZAy5ywreSFyqcabgxr8lE7XECgu8JPjpj/Ao2AJtXAYoIEYzsVi3i51kBz3Rq8O658RFhKVn4Rdesu6MYTemZoEm468kh+TejlWgNdjXoeMGVjOJXXnVJk6zboa1uFb7Wm1csTZ+tu6HN3TKcEYwvZIlLJ+sMFBPoO+twdjz7GXQy8Mf6Kqe7t0HV37FaDSp630R7Rb90WtR6ytxiaFPute6Gvu2OY6wRzC92EtguUy7UGWvqtzWgX8DtPZZ8cnvAuKNs7aH4v7ZnBPH6PWcZd0DInLPHjqSTvSAGBBhpooIEG+gb6DeDWV0l+Ofz2AAAAAElFTkSuQmCC\"/>",
                  "value": "seed://3132333435363738393031323334353637383930"
                },
                "serial": "OATH00096020"
              },
              "id": 1,
              "jsonrpc": "2.0",
              "result": {
                "status": true,
                "value": true
              },
              "version": "privacyIDEA unknown"
            }
    """
    response_details = {}
    tokenrealms = None
    param = request.all_data

    # check admin authorization
    # user_tnum = len(getTokens4UserOrSerial(user))
    # res = self.Policy.checkPolicyPre('admin', 'init', param, user=user,
    #                                 options={'token_num': user_tnum})

    # if no user is given, we put the token in all realms of the admin
    # if user.login == "":
    #    log.debug("setting tokenrealm %s" % res['realms'])
    #    tokenrealm = res['realms']

    user = get_user_from_param(param)
    tokenobject = init_token(param,
                             user,
                             tokenrealms=tokenrealms)

    if tokenobject:
        g.audit_object.log({"success": True})
        # The token was created successfully, so we add token specific
        # init details like the google URL to the response
        init_details = tokenobject.get_init_detail(param, user)
        response_details.update(init_details)

    g.audit_object.log({'user': user.login,
                        'realm': user.realm,
                        'serial': tokenobject.token.serial,
                        'token_type': tokenobject.token.tokentype})

    # logTokenNum()

    # setting the random PIN
    # randomPINLength = self.Policy.getRandomOTPPINLength(user)
    # if randomPINLength > 0:
    #    newpin = self.Policy.getRandomPin(randomPINLength)
    #    log.debug("setting random pin for token with serial "
    #              "%s and user: %s" % (serial, user))
    #    setPin(newpin, None, serial)
        
    # finally we render the info as qr immage, if the qr parameter
    # is provided and if the token supports this
    # if 'qr' in param and tokenobject is not None:
    #    (rdata, hparam) = tokenobject.getQRImageData(response_detail)
    #    hparam.update(response_detail)
    #    hparam['qr'] = param.get('qr') or 'html'
    #    return sendQRImageResult(response, rdata, hparam)
    # else:
    #    return sendResult(response, ret, opt=response_detail)

    return send_result(True, details=response_details)


@token_blueprint.route('/', methods=['GET'])
@log_with(log)
def list_api():
    """
    Display the list of tokens. Using different parameters you can choose,
    which tokens you want to get and also in which format you want to get the
    information (*outform*).

    :query serial: Display the token data of this single token. You can do a
        not strict matching by specifying a serial like "*OATH*".
    :query type: Display only token of type. You ca do a non strict matching by
        specifying a tokentype like "*otp*", to file hotp and totp tokens.
    :query user: display tokens of this user
    :query viewrealm: takes a realm, only the tokens in this realm will be
        displayed
    :query basestring description: Display token with this kind of description
    :query sortby: sort the output by column
    :query sortdir: asc/desc
    :query page: request a certain page
    :query assigned: Only return assigned (True) or not assigned (False) tokens
    :query pagesize: limit the number of returned tokens
    :query user_fields: additional user fields from the userid resolver of
        the owner (user)
    :query outform: if set to "csv", than the token list will be given in CSV

    :return: a json result with the data being a list of token dictionaries::

        { "data": [ { <token1> }, { <token2> } ]}

    :rtype: json
    """
    param = request.all_data
    user = get_user_from_param(param, optional)
    serial = getParam(param, "serial", optional)
    page = int(getParam(param, "page", optional, default=1))
    tokentype = getParam(param, "type", optional)
    description = getParam(param, "description", optional)
    sort = getParam(param, "sortby", optional, default="serial")
    sdir = getParam(param, "sortdir", optional, default="asc")
    psize = int(getParam(param, "pagesize", optional, default=15))
    realm = getParam(param, "tokenrealm", optional)
    ufields = getParam(param, "user_fields", optional)
    output_format = getParam(param, "outform", optional)
    assigned = getParam(param, "assigned", optional)
    if assigned:
        assigned = assigned.lower() == "true"
    
    user_fields = []
    if ufields:
        user_fields = [u.strip() for u in ufields.split(",")]

    # filterRealm determines, which realms the admin would be allowed to see
    filterRealm = ["*"]
    # TODO: Userfields

    # If the admin wants to see only one realm, then do it:
    if realm:
        if realm in filterRealm or '*' in filterRealm:
            filterRealm = [realm]
    g.audit_object.log({'info': "realm: %s" % (filterRealm)})

    # get list of tokens as a dictionary
    tokens = get_tokens_paginate(serial=serial, realm=realm, page=page,
                                 user=user, assigned=assigned, psize=psize,
                                 sortby=sort, sortdir=sdir,
                                 tokentype=tokentype,
                                 description=description)
    g.audit_object.log({"success": True})
    if output_format == "csv":
        return send_csv_result(tokens)
    else:
        return send_result(tokens)


@token_blueprint.route('/assign', methods=['POST'])
@prepolicy(check_max_token_realm, request)
@prepolicy(check_max_token_user, request)
@prepolicy(check_base_action, request, action=ACTION.ASSIGN)
@prepolicy(encrypt_pin, request)
@prepolicy(check_external, request, action="assign")
@log_with(log)
def assign_api():
    """
    Assign a token to a user.

    :jsonparam serial: The token, which should be assigned to a user
    :jsonparam user: The username of the user
    :jsonparam realm: The realm of the user
    :return: In case of success it returns "value": True.
    :rtype: json object
    """
    user = get_user_from_param(request.all_data, required)
    serial = getParam(request.all_data, "serial", required)
    pin = getParam(request.all_data, "pin")
    encrypt_pin = getParam(request.all_data, "encryptpin")
    res = assign_token(serial, user, pin=pin, encrypt_pin=encrypt_pin)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/unassign', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.UNASSIGN)
@log_with(log)
def unassign_api():
    """
    Unssign a token from a user.
    You can either provide "serial" as an argument to unassign this very
    token or you can provide user and realm, to unassign all tokens of a user.

    :return: In case of success it returns "value": True.
    :rtype: json object
    """
    user = get_user_from_param(request.all_data, optional)
    serial = getParam(request.all_data, "serial", optional)
    res = unassign_token(serial, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/revoke', methods=['POST'])
@token_blueprint.route('/revoke/<serial>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.REVOKE)
@log_with(log)
def revoke_api(serial=None):
    """
    Revoke a single token or all the tokens of a user.
    A revoked token will usually be locked. A locked token can not be used
    anymore.
    For certain token types additional actions might occur when revoking a
    token.

    :jsonparam basestring serial: the serial number of the single token to
        revoke
    :jsonparam basestring user: The login name of the user
    :jsonparam basestring realm: the realm name of the user
    :return: In case of success it returns the number of revoked
        tokens in "value".
    :rtype: JSON object
    """
    user = get_user_from_param(request.all_data, optional)
    if not serial:
        serial = getParam(request.all_data, "serial", optional)

    res = revoke_token(serial, user=user)
    g.audit_object.log({"success": res > 0})
    return send_result(res)



@token_blueprint.route('/enable', methods=['POST'])
@token_blueprint.route('/enable/<serial>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.ENABLE)
@log_with(log)
def enable_api(serial=None):
    """
    Enable a single token or all the tokens of a user.

    :jsonparam basestring serial: the serial number of the single token to
        enable
    :jsonparam basestring user: The login name of the user
    :jsonparam basestring realm: the realm name of the user
    :return: In case of success it returns the number of enabled
        tokens in "value".
    :rtype: json object
    """
    user = get_user_from_param(request.all_data, optional)
    if not serial:
        serial = getParam(request.all_data, "serial", optional)

    res = enable_token(serial, enable=True, user=user)
    g.audit_object.log({"success": res > 0})
    return send_result(res)


@token_blueprint.route('/disable', methods=['POST'])
@token_blueprint.route('/disable/<serial>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.DISABLE)
@log_with(log)
def disable_api(serial=None):
    """
    Disable a single token or all the tokens of a user either by providing
    the serial number of the single token or a username and realm.

    Disabled tokens can not be used to authenticate but can be enabled again.

    :jsonparam basestring serial: the serial number of the single token to
        disable
    :jsonparam basestring user: The login name of the user
    :jsonparam basestring realm: the realm name of the user
    :return: In case of success it returns the number of disabled
        tokens in "value".
    :rtype: json object
    """
    user = get_user_from_param(request.all_data, optional)
    if not serial:
        serial = getParam(request.all_data, "serial", optional)

    res = enable_token(serial, enable=False, user=user)
    g.audit_object.log({"success": res > 0})
    return send_result(res)



@token_blueprint.route('/<serial>', methods=['DELETE'])
@prepolicy(check_base_action, request, action=ACTION.DELETE)
@log_with(log)
def delete_api(serial=None):
    """
    Delete a token by its serial number or delete all tokens of a user.

    :jsonparam serial: The serial number of a single token.
    :jsonparam user: The username of the user, whose tokens should be deleted.
    :jsonparam realm: The realm of the user.

    :return: In case of success it return the number of deleted tokens in
        "value"
    :rtype: json object
    """
    # If the API is called by a user, we pass the User Object to the function
    user = get_user_from_param(request.all_data)
    res = remove_token(serial, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/reset', methods=['POST'])
@token_blueprint.route('/reset/<serial>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.RESET)
@log_with(log)
def reset_api(serial=None):
    """
    Reset the failcounter of a single token or of all tokens of a user.

    :jsonparam basestring serial: the serial number of the single token to reset
    :jsonparam basestring user: The login name of the user
    :jsonparam basestring realm: the realm name of the user
    :return: In case of success it returns "value"=True
    :rtype: json object
    """
    user = get_user_from_param(request.all_data, optional)
    if not serial:
        serial = getParam(request.all_data, "serial", optional)

    res = reset_token(serial, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/resync', methods=['POST'])
@token_blueprint.route('/resync/<serial>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.RESYNC)
@log_with(log)
def resync_api(serial=None):
    """
    Resync the OTP token by providing two consecutive OTP values.

    :jsonparam basestring serial: the serial number of the single token to reset
    :jsonparam basestring otp1: First OTP value
    :jsonparam basestring otp2: Second OTP value
    :return: In case of success it returns "value"=True
    :rtype: json object
    """
    user = get_user_from_param(request.all_data, optional)
    if not serial:
        serial = getParam(request.all_data, "serial", required)
    otp1 = getParam(request.all_data, "otp1", required)
    otp2 = getParam(request.all_data, "otp2", required)

    res = resync_token(serial, otp1, otp2, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/setpin', methods=['POST'])
@token_blueprint.route('/setpin/<serial>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.SETPIN)
@prepolicy(encrypt_pin, request)
@prepolicy(check_otp_pin, request)
@log_with(log)
def setpin_api(serial=None):
    """
    Set the the user pin or the SO PIN of the specific token.
    Usually these are smartcard or token specific PINs.
    E.g. the userpin is used with mOTP tokens to store the mOTP PIN.

    The token is identified by the unique serial number.

    :jsonparam basestring serial: the serial number of the single
        token to reset
    :jsonparam basestring userpin: The user PIN of a smartcard
    :jsonparam basestring sopin: The SO PIN of a smartcard
    :jsonparam basestring otppin: The OTP PIN of a token
    :return: In "value" returns the number of PINs set.
    :rtype: json object
    """
    if not serial:
        serial = getParam(request.all_data, "serial", required)
    userpin = getParam(request.all_data, "userpin")
    sopin = getParam(request.all_data, "sopin")
    otppin = getParam(request.all_data, "otppin")
    user = get_user_from_param(request.all_data)
    encrypt_pin = getParam(request.all_data, "encryptpin")

    res = 0
    if userpin:
        g.audit_object.add_to_log({'action_detail': "userpin, "})
        res += set_pin_user(serial, userpin, user=user)

    if sopin:
        g.audit_object.add_to_log({'action_detail': "sopin, "})
        res += set_pin_so(serial, sopin, user=user)

    if otppin:
        g.audit_object.add_to_log({'action_detail': "otppin, "})
        res += set_pin(serial, otppin, user=user, encrypt_pin=encrypt_pin)

    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/set', methods=['POST'])
@token_blueprint.route('/set/<serial>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.SET)
@log_with(log)
@admin_required
def set_api(serial=None):
    """
    This API is only to be used by the admin!
    This can be used to set token specific attributes like

        * description
        * count_window
        * sync_window
        * count_auth_max
        * count_auth_success_max
        * hashlib,
        * max_failcount

    The token is identified by the unique serial number or by the token owner.
    In the later case all tokens of the owner will be modified.

    :jsonparam basestring serial: the serial number of the single token to reset
    :jsonparam basestring user: The username of the token owner
    :jsonparam basestring realm: The realm name of the token owner
    :return: returns the number of attributes set in "value"
    :rtype: json object
    """
    if not serial:
        serial = getParam(request.all_data, "serial", required)
    user = get_user_from_param(request.all_data)

    description = getParam(request.all_data, "description")
    count_window = getParam(request.all_data, "count_window")
    sync_window = getParam(request.all_data, "sync_window")
    hashlib = getParam(request.all_data, "hashlib")
    max_failcount = getParam(request.all_data, "max_failcount")
    count_auth_max = getParam(request.all_data, "count_auth_max")
    count_auth_success_max = getParam(request.all_data, "count_auth_success_max")
    validity_period_start = getParam(request.all_data, "validity_period_start")
    validity_period_end = getParam(request.all_data, "validity_period_end")

    res = 0

    if description:
        g.audit_object.add_to_log({'action_detail': "description=%r, "
                                                    "" % description})
        res += set_description(serial, description, user=user)

    if count_window:
        g.audit_object.add_to_log({'action_detail': "count_window=%r, "
                                                    "" % count_window})
        res += set_count_window(serial, count_window, user=user)

    if sync_window:
        g.audit_object.add_to_log({'action_detail': "sync_window=%r, "
                                                    "" % sync_window})
        res += set_sync_window(serial, sync_window, user=user)

    if hashlib:
        g.audit_object.add_to_log({'action_detail': "hashlib=%r, "
                                                    "" % hashlib})
        res += set_hashlib(serial, hashlib, user=user)

    if max_failcount:
        g.audit_object.add_to_log({'action_detail': "max_failcount=%r, "
                                                    "" % max_failcount})
        res += set_max_failcount(serial, max_failcount, user=user)

    if count_auth_max:
        g.audit_object.add_to_log({'action_detail': "count_auth_max=%r, "
                                                    "" % count_auth_max})
        res += set_count_auth(serial, count_auth_max, user=user, max=True)

    if count_auth_success_max:
        g.audit_object.add_to_log({'action_detail':
                                       "count_auth_success_max=%r, " %
                                       count_auth_success_max})
        res += set_count_auth(serial, count_auth_success_max, user=user,
                              max=True, success=True)

    if validity_period_end:
        g.audit_object.add_to_log({'action_detail':
                                       "validity_period_end=%r, " %
                                       validity_period_end})
        res += set_validity_period_end(serial, user, validity_period_end)

    if validity_period_start:
        g.audit_object.add_to_log({'action_detail':
                                       "validity_period_start=%r, " %
                                       validity_period_start})
        res += set_validity_period_start(serial, user, validity_period_start)



    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/realm/<serial>', methods=['POST'])
@log_with(log)
@prepolicy(check_max_token_realm, request)
@prepolicy(check_base_action, request, action=ACTION.TOKENREALMS)
@admin_required
def tokenrealm_api(serial=None):
    """
    Set the realms of a token.
    The token is identified by the unique serial number

    You can call the function like this:
        POST /token/realm?serial=<serial>&realms=<something>
        POST /token/realm/<serial>?realms=<hash>


    :jsonparam basestring serial: the serial number of the single token to reset
    :jsonparam basestring realms: The realms the token should be assigned to.
        Comma separated
    :return: returns value=True in case of success
    :rtype: bool
    """
    realms = getParam(request.all_data, "realms", required)
    if type(realms) == list:
        realm_list = realms
    else:
        realm_list = [r.strip() for r in realms.split(",")]

    res = set_realms(serial, realms=realm_list)
    g.audit_object.log({"success": True})
    return send_result(res == 1)


@token_blueprint.route('/load/<filename>', methods=['POST'])
@log_with(log)
@prepolicy(check_token_upload, request)
@admin_required
def loadtokens_api(filename=None):
    """
    The call imports the given file containing token definitions.
    The file can be an OATH CSV file, an aladdin XML file or a Yubikey CSV file
    exported from the yubikey initialization tool.

    The function is called as a POST request with the file upload.

    :jsonparam basestring filename: The name of the token file, that is imported
    :jsonparam basestring type: The file type. Can be "aladdin-xml",
        "oathcsv" or "yubikeycsv".
    :jsonparam basestring tokenrealms: comma separated list of tokens.
    :return: The number of the imported tokens
    :rtype: int
    """
    if not filename:
        filename = getParam(request.all_data, "filename", required)
    known_types = ['aladdin-xml', 'oathcsv', "OATH CSV", 'yubikeycsv',
                   'Yubikey CSV', 'pskc']
    file_type = getParam(request.all_data, "type", required)
    hashlib = getParam(request.all_data, "aladdin_hashlib")
    trealms = getParam(request.all_data, "tokenrealms") or ""
    tokenrealms = trealms.split(",")

    TOKENS = {}
    token_file = request.files['file']
    file_contents = ""
    # In case of form post requests, it is a "instance" of FieldStorage
    # i.e. the Filename is selected in the browser and the data is
    # transferred
    # in an iframe. see: http://jquery.malsup.com/form/#sample4
    #
    if type(token_file) == FieldStorage:  # pragma: no cover
        log.debug("Field storage file: %s", token_file)
        file_contents = token_file.value
    elif type(token_file) == FileStorage:
        log.debug("Werkzeug File storage file: %s", token_file)
        file_contents = token_file.read()
    else:  # pragma: no cover
        file_contents = token_file

    if file_contents == "":
        log.error("Error loading/importing token file. file %s empty!" %
                  filename)
        raise ParameterError("Error loading token file. File empty!")

    if file_type not in known_types:
        log.error("Unknown file type: >>%s<<. We only know the types: %s" %
                  (file_type, ', '.join(known_types)))
        raise TokenAdminError("Unknown file type: >>%s<<. We only know the "
                              "types: %s" % (file_type,
                                             ', '.join(known_types)))

    # Parse the tokens from file and get dictionary
    if file_type == "aladdin-xml":
        TOKENS = parseSafeNetXML(file_contents)
    elif file_type in ["oathcsv", "OATH CSV"]:
        TOKENS = parseOATHcsv(file_contents)
    elif file_type in ["yubikeycsv", "Yubikey CSV"]:
        TOKENS = parseYubicoCSV(file_contents)
    elif file_type in ["pskc"]:
        # At the moment we only process unencrypted data
        # TODO: We need to also parse encryption!
        TOKENS = parsePSKCdata(file_contents)

    # Now import the Tokens from the dictionary
    ret = ""
    for serial in TOKENS:
        log.debug("importing token %s" % TOKENS[serial])

        log.info("initialize token. serial: %s, realm: %s" % (serial,
                                                              tokenrealms))

        init_param = {'serial': serial,
                      'type': TOKENS[serial]['type'],
                      'description': TOKENS[serial].get("description",
                                                        "imported"),
                      'otpkey': TOKENS[serial]['otpkey'],
                      'otplen': TOKENS[serial].get('otplen'),
                      'timeStep': TOKENS[serial].get('timeStep'),
                      'hashlib': TOKENS[serial].get('hashlib')}

        if hashlib and hashlib != "auto":
            init_param['hashlib'] = hashlib

        #if tokenrealm:
        #    self.Policy.checkPolicyPre('admin', 'loadtokens',
        #                   {'tokenrealm': tokenrealm })

        init_token(init_param, tokenrealms=tokenrealms)

    g.audit_object.log({'info': "%s, %s (imported: %i)" % (file_type,
                                                           token_file,
                                                           len(TOKENS)),
                        'serial': ', '.join(TOKENS.keys())})
    # logTokenNum()

    return send_result(len(TOKENS))


@token_blueprint.route('/copypin', methods=['POST'])
@log_with(log)
@prepolicy(check_base_action, request, action=ACTION.COPYTOKENPIN)
@admin_required
def copypin_api():
    """
    Copy the token PIN from one token to the other.

    :jsonparam basestring from: the serial number of the token, from where you
        want to copy the pin.
    :jsonparam basestring to: the serial number of the token, from where you
        want to copy the pin.
    :return: returns value=True in case of success
    :rtype: bool
    """
    serial_from = getParam(request.all_data, "from", required)
    serial_to = getParam(request.all_data, "to", required)
    res = copy_token_pin(serial_from, serial_to)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/copyuser', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.COPYTOKENUSER)
@log_with(log)
@admin_required
def copyuser_api():
    """
    Copy the token user from one token to the other.

    :jsonparam basestring from: the serial number of the token, from where you
        want to copy the pin.
    :jsonparam basestring to: the serial number of the token, from where you
        want to copy the pin.
    :return: returns value=True in case of success
    :rtype: bool
    """
    serial_from = getParam(request.all_data, "from", required)
    serial_to = getParam(request.all_data, "to", required)
    res = copy_token_user(serial_from, serial_to)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/lost/<serial>', methods=['POST'])
@prepolicy(check_base_action, request, action=ACTION.LOSTTOKEN)
@log_with(log)
def lost_api(serial=None):
    """
    Mark the specified token as lost and create a new temporary token.
    This new token gets the new serial number "lost<old-serial>" and
    a certain validity period and the PIN of the lost token.

    This method can be called by either the admin or the user on his own tokens.

    You can call the function like this:
        POST /token/lost/serial

    :jsonparam basestring serial: the serial number of the lost token.
    :return: returns value=dictionary in case of success
    :rtype: bool
    """
    # check if a user is given, that the user matches the token owner.
    userobj = get_user_from_param(request.all_data)
    if userobj:
        toks = get_tokens(serial=serial, user=userobj)
        if len(toks) == 0:
            raise TokenAdminError("The user %s does not own the token %s" % (
                userobj, serial))

    options = {"g": g,
               "clientip": request.remote_addr}
    res = lost_token(serial, options=options)

    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/getserial/<otp>', methods=['GET'])
@prepolicy(check_base_action, request, action=ACTION.GETSERIAL)
@log_with(log)
@admin_required
def get_serial_by_otp_api(otp=None):
    """
    Get the serial number for a given OTP value.
    If the administrator has a token, he does not know to whom it belongs,
    he can type in the OTP value and gets the serial number of the token, that
    generates this very OTP value.

    :query otp: The given OTP value
    :query type: Limit the search to this token type
    :query unassigned: If set=1, only search in unassigned tokens
    :query assigned: If set=1, only search in assigned tokens
    :query serial: This can be a substring of serial numbers to search in.
    :query window: The number of OTP look ahead (default=10)
    :return: The serial number of the token found
    """
    ttype = getParam(request.all_data, "type")
    unassigned_param = getParam(request.all_data, "unassigned")
    assigned_param = getParam(request.all_data, "assigned")
    serial_substr = getParam(request.all_data, "serial")
    window = int(getParam(request.all_data, "window", default=10))

    serial_substr = serial_substr or ""

    assigned = None
    if unassigned_param:
        assigned = False
    if assigned_param:
        assigned = True

    tokenobj_list = get_tokens(tokentype=ttype,
                               serial="*%s*" % serial_substr,
                               assigned=assigned)
    serial = get_serial_by_otp(tokenobj_list, otp=otp, window=window)

    g.audit_object.log({"success": True,
                        "info": "get %s by OTP" % serial})

    return send_result({"serial": serial})
