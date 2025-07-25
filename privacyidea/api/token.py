# http://www.privacyidea.org
# (c) cornelius kölbel, privacyidea.org
#
# 2020-11-11 Timo Sturm <timo.sturm@netknights.it>
#            Select how to validate PSKC imports
# 2020-01-28 Jean-Pierre Höhmann <jean-pierre.hoehmann@netknights.it>
#            Add WebAuthn token
# 2018-06-07 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add tantoken wrapper
# 2017-04-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add U2F policy to /token/init
# 2016-08-09 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add number of tokens, searched by get_serial_by_otp
# 2016-07-17 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add decryption of import file
# 2016-05-06 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add eventhandler
# 2016-04-28 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add init defaults for token types
# 2015-12-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Move the complete before and after logic
# 2015-11-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add the endpoint for retrieving challenges
# 2015-11-20 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add an endpoint to get the challenges of a token
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

from flask import (Blueprint, request, g, current_app)

from ..lib.container import find_container_by_serial, add_token_to_container, add_not_authorized_tokens_result
from ..lib.log import log_with
from .lib.utils import optional, send_result, send_csv_result, required, getParam
from ..lib.tokenclass import ROLLOUTSTATE
from ..lib.tokens.passkeytoken import PasskeyTokenClass
from ..lib.tokens.webauthntoken import WebAuthnTokenClass
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
                         set_validity_period_end, set_validity_period_start, add_tokeninfo,
                         delete_tokeninfo, import_token,
                         assign_tokengroup, unassign_tokengroup, set_tokengroups, get_one_token)

from ..lib.fido2.util import get_credential_ids_for_user
from werkzeug.datastructures import FileStorage
from privacyidea.lib.error import (ParameterError, TokenAdminError,
                                   ResourceNotFoundError, PolicyError, ERROR)
from privacyidea.lib.importotp import (parseOATHcsv, parseSafeNetXML,
                                       parseYubicoCSV, parsePSKCdata, GPGImport)
import logging
from privacyidea.lib.policy import ACTION
from privacyidea.lib.challenge import get_challenges_paginate, cleanup_expired_challenges
from privacyidea.api.lib.prepolicy import (prepolicy, check_base_action, check_token_action,
                                           check_token_init, check_token_upload,
                                           check_max_token_user,
                                           check_max_token_realm,
                                           init_tokenlabel, init_random_pin,
                                           init_token_length_contents,
                                           set_random_pin,
                                           encrypt_pin, check_otp_pin,
                                           check_external, init_token_defaults,
                                           enroll_pin, papertoken_count,
                                           tantoken_count,
                                           u2ftoken_allowed, u2ftoken_verify_cert,
                                           twostep_enrollment_activation,
                                           twostep_enrollment_parameters,
                                           sms_identifiers, pushtoken_add_config,
                                           verify_enrollment,
                                           indexedsecret_force_attribute,
                                           check_admin_tokenlist, fido2_enroll, webauthntoken_allowed,
                                           webauthntoken_request, required_piv_attestation,
                                           hide_tokeninfo, init_ca_connector, init_ca_template,
                                           init_subject_components, require_description_on_edit, require_description,
                                           check_container_action, check_user_params, check_token_list_action,
                                           force_server_generate_key)
from privacyidea.api.lib.postpolicy import (save_pin_change, check_verify_enrollment,
                                            postpolicy)
from privacyidea.lib.event import event
from privacyidea.api.auth import admin_required
from privacyidea.lib.subscriptions import CheckSubscription

token_blueprint = Blueprint('token_blueprint', __name__)
log = logging.getLogger(__name__)

__doc__ = """
The token API can be accessed via /token.

You need to authenticate to gain access to these token
functions.
If you are authenticated as administrator, you can manage all tokens.
If you are authenticated as normal user, you can only manage your own tokens.
Some API calls are only allowed to be accessed by administrators.

To see how to authenticate read :ref:`rest_auth`.
"""


@token_blueprint.route('/init', methods=['POST'])
@prepolicy(check_max_token_realm, request)
@prepolicy(require_description, request)
@prepolicy(check_max_token_user, request)
@prepolicy(check_token_init, request)
@prepolicy(init_tokenlabel, request)
@prepolicy(init_ca_connector, request)
@prepolicy(init_ca_template, request)
@prepolicy(init_subject_components, request)
@prepolicy(enroll_pin, request)
@prepolicy(twostep_enrollment_activation, request)
@prepolicy(twostep_enrollment_parameters, request)
@prepolicy(init_random_pin, request)
@prepolicy(encrypt_pin, request)
@prepolicy(check_otp_pin, request)
@prepolicy(check_external, request, action="init")
@prepolicy(init_token_defaults, request)
@prepolicy(init_token_length_contents, request)
@prepolicy(papertoken_count, request)
@prepolicy(sms_identifiers, request)
@prepolicy(tantoken_count, request)
@prepolicy(u2ftoken_allowed, request)
@prepolicy(u2ftoken_verify_cert, request)
@prepolicy(pushtoken_add_config, request)
@prepolicy(indexedsecret_force_attribute, request)
@prepolicy(webauthntoken_allowed, request)
@prepolicy(webauthntoken_request, request)
@prepolicy(fido2_enroll, request)
@prepolicy(required_piv_attestation, request)
@prepolicy(verify_enrollment, request)
@prepolicy(force_server_generate_key, request)
@postpolicy(save_pin_change, request)
@event("token_init", request, g)
@postpolicy(check_verify_enrollment, request)
@CheckSubscription(request)
@log_with(log, log_entry=False)
def init():
    """
    Create a new token with the specified parameters.

    :jsonparam otpkey: required: the secret key of the token
    :jsonparam genkey: set to =1, if key should be generated. We either
                   need otpkey or genkey
    :jsonparam keysize: the size (byte) of the key. Either 20 or 32. Default is 20
    :jsonparam serial: the serial number/identifier of the token
    :jsonparam description: A description for the token
    :jsonparam pin: the pin of the token. "OTP PIN"
    :jsonparam user: the login user name. This user gets the token assigned
    :jsonparam realm: the realm of the user.
    :jsonparam type: the type of the token
    :jsonparam tokenrealm: additional realms, the token should be put into
    :jsonparam otplen: length of the OTP value
    :jsonparam hashlib: used hashlib sha1, sha256 or sha512
    :jsonparam validity_period_start: The beginning of the validity period
    :jsonparam validity_period_end: The end of the validity period
    :jsonparam 2stepinit: set to =1 in conjunction with genkey=1 if you want
                    a 2 step initialization process. Additional policies have to be set
                    see :ref:`2step_enrollment`.
    :jsonparam otpkeyformat: used to supply the OTP key in alternate formats, currently
                            hex or base32check (see :ref:`2step_enrollment`)
    :jsonparam rollover: Set this to 1 or true to indicate, that you want to rollover a token.
                    This is mandatory to rollover tokens, that are in the clientwait state.

    :return: a json result with a boolean "result": true

    Depending on the token type there can be additional parameters.
    In the tokenclass you can see additional parameters in the method ``update``
    when looking for ``getParam`` functions.

    **Example response**:

       .. sourcecode:: http

           HTTP/1.1 200 OK
           Content-Type: application/json

           {
              "detail": {
                "googleurl": {
                  "description": "URL for google Authenticator",
                  "img": "<img width=250 src=\\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAcIAAAHCAQAAAABUY/ToAAADsUlEQVR4nO2czY3bMBCF34QCfKSALcClyB2kpCAlpQOxlBQQgDwaoPBy4I+p9W4OSRaWF28OgizxgylgMJw/0oi/k/DlL0FApEiRIkWKFCnyeKRVmdrjNAFh3srTMuSS2qjLg2cr8pDkQpKMgF3SBITz1QA4YolVfQA4kiT35CNmK/JQZLM8aQaWH+3pEkEgTZlhBojksgGAAS7/83+K/ORkOF/NLtismiCfYXbOd+AxZivygCTXdCLCDJRLfTbhTo4wW5FHIJtyeAJIAJb4AobLBIP/ZQRAwMcyakxIPtd3ivw4EqObXJzody9t1EKS63N9p8iPI4sO3QTwGSSbA1Q0x+cWunWRDolsUjSnxvau6VB0xMIMrp4EPAnAkWsjpEMiu+ysD1mUZomuKk1/i6WtedIhkXupS1MEsMRmaVafh7dVfXwGV0D+kMj3yXDOsIsngXQiV59R0tZIE7jC0b4VA3WE2Yo8CtkTPy7b8sPA8HWbWML6dCKAqxG4GgADw+weOVuRRyTHuGztbk+PwdqQPIzTWibyDbJWVdOJQDLj9xkod4yOCK2gbzZvVpyip/xOkR9B4maCbnF8c53vHGuuLVaTHRLZpBgYgweAVP0hLPElA+mFtVrvf3W/aTM+brYij0j23o8JthAweNc1J5cCmSFNYDCAS5wfOVuRRyT7QpVL9F6XLN/zjhG4ZSAHj1trmcgmLcfoWoq6/B4LZLeqBxmVpxb5WobYfl8vaxfU7DSA4mdLh0S+TW5W2xXTiaWZ0WbALqiXmi5KU/n5tN8p8r+TzaqUH936MKNW6/2uIkvZIZF/IEleDfAZZnYi1zSB/DmVpa2YJZtVLxP5JmnfWCutty5qwNcFrWSsV2xGxs3+03+K/Cxk74WtTWflDr652L0XtoZuylOLvJNb9H7XPzQ0DOX9RTokcpAhAzRYpN4LO5TsI1rQLx0SOci4z7VcSuvQZgxWX1gfbfBX1ctEvhLupbZSe5bNQK0Jv/dTe9U6RL6WtoIBqDs33NA7Xdey3SYzrWUi99L8IfJW4cC4pYNjg+Ow/+O5vlPkx5OpnSsUzler2cbS29g8pmBmWH6elGMU+UqaFwS0NBBa9O45Rmhr26Mof0jkTt440MNlC9aOGQqzA8McaQs34xJfsv3rf4r8XOTduR+lezHN5fyh0sdY76qz/cDZijwwGcxqs0c9gNFx5w9t7e18hNmKPBRZ7NDtXKF6V1qp2e9qtZ7DkOf6TpEiRYoUKVKkyPfkNyq7YXtdjZCIAAAAAElFTkSuQmCC\\"/>",
                  "value": "otpauth://hotp/mylabel?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&counter=0"
                },
                "oathurl": {
                  "description": "URL for OATH token",
                  "img": "<img width=250 src=\\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAcIAAAHCAQAAAABUY/ToAAADfElEQVR4nO2cTYrjMBCFX40EvZRvkKPIN5gz9c3so/QBBqxlwObNQpIlp2cYaBI6zrxamDjyhywo6leyEV+T+ccXQUCkSJEiRYoUKfL5SCviy7+zmZWBAbARmwGpPjXeZU6RL0ZGkuQCAMkMCCTmqlJ8HwAb4UiSPJJfn1Pki5Fpty8AED/MEBeAU/JoA52pOuk6Rd6f9H/60xBWbwCMyG7Mg0j3mlPky5OOiB9v5AQACCQnONr4yDlFnpisdigQQAIM4WpE2oyAWy0umyfCku1QX5A81zpFPo5EHybDEXH566U+FUlyOtc6RT6OzHao2RfOgwMQVqBYJADz5WrFVN1jTpGvRRY7FLmCExwR8y3JKbAm84HkFFawieyQyCpFJRagaMniikqRK4C9KpSVa3GULxN5lGZp8n3kinrr2H5xCmsZlQ6JPEiLqbPzKh5sRefL4uJILq4MyJeJPEjzZb2jQnFopQmSH3FZw2SHRB6lC3bQeatDiI2wghOAaoykQyKb7L2OzQPpjZjNEUgDDNiMSAMAOFpchjvNKfK1yGqHlkNetofYxclVs5RzNfkykZ/J4rc+So+++S2zy1ofDVezMXmURtoZ1ynyEeRuh1xXSiwJPtCFRyUygupDIm+l5fa9Q+Na0rT8yCG3lw6JPEqtMZaCUNfmyPWhBajtMx46Iedap8jHkV2/DK0cDWBXqapczY0ptxd5kFZjLEqzlJi6C4WyHYJjHZAOieyk2aGsSNyjoF2l0Jsg9TpE/oVMHpgvK8wupRZkIwDMQy0S5QMfbVfsOdcp8v5kF1M3N9ZaGrX/sbf2g+yQyFtpPdW2/75pTtGX5tWCcnuRt9L1OtguLcFve9DazmrpkMheOn3Ju4aA4tX6gVopiurbi7yV3Lc3IJ+vh0VuHoBbAWyeSH41hF+fzzKea50iH012QdE8OPJ92MzG9HY4NJRDpqt9+9uKfEayffeDU/J7z3UzG8PVSlqfPMrlm99W5FOSsUY8Noarmdkb+T7UTSF7Wv8kbyvyqcguL+u23k/7cDvdmm9Vpxb5LzLbobErObbc/lFzijw3eZtvcR4WAtjKx2Lmn1djztBAWN5ZPX3X24p8RrI719HcWNnsEVoz1vWPyJeJ7KXYoTln7A4Wcz6/eQL7xxxyRr95IlwNskMiezF941ykSJEiRYoU+Z+TvwF49nApsKFZZAAAAABJRU5ErkJggg==\\"/>",
                  "value": "oathtoken:///addToken?name=mylabel&lockdown=true&key=3132333435363738393031323334353637383930"
                },
                "otpkey": {
                  "description": "OTP seed",
                  "img": "<img width=200 src=\\"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAUoAAAFKAQAAAABTUiuoAAAB70lEQVR4nO2aTY6jQAyFPw9IWYI0B+ijwNHhKH0DWLZU6PXCVYSOZkF6xM/CXkQkfIsnWRU/22ViZ4x/9pIQaKCBBhpooEeilqPGrAWzdjGYy8/94QICfQftJEkTAIsBlYBKkqSf6DECAn0HnfMRkj4fnjfrATOrzxEQ6I6oX74bYGJuzxIQ6H9kqySqSjCfISDQX6CNpKE8mX18lT9GpXMEBLofHc3M7WA/19B9PgQsbgnPEBDonrCXyZMB/HMaFZOnu6DWz2aMZqaBZ79Vw9gu0W/dBsU7qm4CL16aKq9geonhcq2BlqR4jirRSYImoaF8eO8c2boeXR38YnRavIwJkNFUsg1xudZAy5ywreSFyqcabgxr8lE7XECgu8JPjpj/Ao2AJtXAYoIEYzsVi3i51kBz3Rq8O658RFhKVn4Rdesu6MYTemZoEm468kh+TejlWgNdjXoeMGVjOJXXnVJk6zboa1uFb7Wm1csTZ+tu6HN3TKcEYwvZIlLJ+sMFBPoO+twdjz7GXQy8Mf6Kqe7t0HV37FaDSp630R7Rb90WtR6ytxiaFPute6Gvu2OY6wRzC92EtguUy7UGWvqtzWgX8DtPZZ8cnvAuKNs7aH4v7ZnBPH6PWcZd0DInLPHjqSTvSAGBBhpooIEG+gb6DeDWV0l+Ofz2AAAAAElFTkSuQmCC\\"/>",
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

    **2 Step Enrollment**

    Some tokens might need a 2 step initialization process like a smartphone
    app. This way you can create a shared secret from a part generated by
    the privacyIDEA server and from a second part generated by the smartphone
    app/client.

    The first API call would be

       .. sourcecode:: http

           POST /token/init HTTP/1.1

           2stepinit=1

    The response would contain the otpkey generated by the server and the
    serial number of the token. At this point, the token is deactivated and
    marked as being in an enrollment state. The client
    would also generated a component of the key and send his component to the
    privacyIDEA server:

    The second API call would be

       .. sourcecode:: http

           POST /token/init HTTP/1.1

           serial=<serial from the previous response>
           otpkey=<key part generated by the client>

    Each tokenclass can define its own way to generate the secret key by
    overwriting the method ``generate_symmetric_key``. The
    Base Tokenclass contains an extremely simple way by concatenating the
    two parts. See
    :func:`~privacyidea.lib.tokenclass.TokenClass.generate_symmetric_key`

    **verify enrollment**

    Some tokens can be configured via enrollment policy so that the user
    needs to provide some verification that e.g. a QR code was scanned correctly or
    the token works correctly in general.
    The specific way depends on the token class.
    The necessary token class functions are

    * :func:`~privacyidea.lib.tokenclass.TokenClass.verify_enrollment`
    * :func:`~privacyidea.lib.tokenclass.TokenClass.prepare_verify_enrollment`

    The first API call to /token/init returns responses in::

        {"detail": {"verify": {"message": "Please provide a valid OTP value."},
                    "rollout_state": "verify"}}

    The second API call then needs to send the serial number and a response

       .. sourcecode:: http

           POST /token/init HTTP/1.1

           serial=<serial from the previous response>
           verify=<e.g. the OTP value>

    As long as the token is in state "verify" it can not be used for
    authentication.
    """
    response_details = {}
    param = request.all_data.copy()
    param["policies"] = g.get("policies", {})

    user = request.User
    token = init_token(param, user)

    if token:
        g.audit_object.log({"success": True})

        # If the token is a fido2 token, find all enrolled fido2 token for the user
        # to avoid registering the same authenticator multiple times
        if (token.get_type().lower() in [PasskeyTokenClass.get_class_type(), WebAuthnTokenClass.get_class_type()]
                and token.rollout_state == ROLLOUTSTATE.CLIENTWAIT):
            param["registered_credential_ids"] = get_credential_ids_for_user(user)

        # The token was created successfully, so we add token specific init details like the Google URL to the response
        try:
            init_details = token.get_init_detail(param, user)
            response_details.update(init_details)
        except ParameterError as e:
            if e.id is ERROR.PARAMETER_USER_MISSING:
                remove_token(serial=token.get_serial())
            raise e

        # Check if a container_serial is set and assign the token to the container
        container_serial = param.get("container_serial", {})
        if container_serial:
            # Check if user is allowed to add tokens to containers
            try:
                container_add_token_right = check_container_action(request, action=ACTION.CONTAINER_ADD_TOKEN)
            except PolicyError:
                container_add_token_right = False
                log.info(f"User {user.login} is not allowed to add token {token.get_serial()} to container "
                         f"{container_serial}.")
            if container_add_token_right:
                # The enrollment will not be blocked if there is problem adding the new token to a container
                # there will just be a warning in the log
                try:
                    add_token_to_container(container_serial, token.get_serial())
                    response_details.update({"container_serial": container_serial})
                    container = find_container_by_serial(container_serial)
                    g.audit_object.log({"container_serial": container_serial, "container_type": container.type})
                except ResourceNotFoundError:
                    log.warning(f"Container with serial {container_serial} not found while enrolling token "
                                f"{token.get_serial()}.")

    g.audit_object.log({"user": user.login,
                        "realm": user.realm,
                        "serial": token.token.serial,
                        "token_type": token.token.tokentype})

    return send_result(True, details=response_details)


@token_blueprint.route('/challenges/', methods=['GET'])
@token_blueprint.route('/challenges/<serial>', methods=['GET'])
@admin_required
@prepolicy(check_base_action, request, action=ACTION.GETCHALLENGES)
@event("token_getchallenges", request, g)
@log_with(log)
def get_challenges_api(serial=None):
    """
    This endpoint returns the active challenges in the database or returns
    the challenges for a single token by its serial number

    :query serial: The optional serial number of the token for which the
        challenges should be returned
    :query sortby: sort the output by column
    :query sortdir: asc/desc
    :query page: request a certain page
    :query pagesize: limit the number of returned tokens
    :query transaction_id: only returns challenges for this
        transaction_id. This is useful when working with push or tiqr tokens.
    :return: json
    """
    param = request.all_data
    page = int(getParam(param, "page", optional, default=1))
    sort = getParam(param, "sortby", optional, default="timestamp")
    sdir = getParam(param, "sortdir", optional, default="asc")
    psize = int(getParam(param, "pagesize", optional, default=15))
    transaction_id = getParam(param, "transaction_id", optional)
    g.audit_object.log({"serial": serial})
    challenges = get_challenges_paginate(serial=serial, sortby=sort,
                                         transaction_id=transaction_id,
                                         sortdir=sdir, page=page, psize=psize)
    g.audit_object.log({"success": True})
    return send_result(challenges)

@token_blueprint.route("/challenges/expired", methods=['DELETE'])
@admin_required
@log_with(log)
def delete_expired_challenges_api():
    """
    Delete all expired entries in the challenge table.

    :>json bool status: Status of the request
    :reqheader PI-Authorization: The authorization token

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "status": true,
            "deleted": 42
          },
          "version": "privacyIDEA unknown"
        }
    """
    row_count = cleanup_expired_challenges(chunksize=None, age=None)
    g.audit_object.log({"success": True, "info": f"Deleted {row_count} entries from challenges"})
    return send_result({"status": True, "deleted": row_count})


@token_blueprint.route('/', methods=['GET'])
@prepolicy(check_admin_tokenlist, request, ACTION.TOKENLIST)
@prepolicy(hide_tokeninfo, request)
@event("token_list", request, g)
@log_with(log)
def list_api():
    """
    Display the list of tokens. Using different parameters you can choose,
    which tokens you want to get and also in which format you want to get the
    information.

    The result will be paginated (even with ``outform=csv``) with a default
    page size of 15 entries.

    :query serial: Display the token data of this single token. You can do a not strict matching by specifying a serial
        like "*OATH*". Multiple serials can be passed as comma separated list.
    :query type: Display only token of type. You can do a not strict matching by
        specifying a tokentype like "*otp*", to find hotp and totp tokens.
    :query type_list: Comma separated list of token types. Display only tokens of the types in the list.
    :query user: display tokens of this user
    :query tokenrealm: takes a realm, only the tokens in this realm will be
        displayed
    :query basestring description: Display token with this kind of description
    :query sortby: sort the output by column
    :query sortdir: asc/desc
    :query page: request a certain page
    :query assigned: Only return assigned (True) or not assigned (False) tokens
    :query active: Only return active (True) or inactive (False) tokens
    :query pagesize: limit the number of returned tokens
    :query outform: if set to "csv", the token list will be given in CSV
    :query rollout_state: only list tokens with the given rollout_state
    :query infokey: only list tokens, where the infokey has the given infovalue
    :query infovalue: only list tokens, where the infokey has the given infovalue
    :query hidden_tokeninfo: A list of token-info keys which should be removed
        from the response. Will be overwritten by the "hide_tokeninfo" policy.
    :query container_serial: only list tokens, which are assigned to the container with the given serial
                            or tokens without container if the value is an empty string ""

    :return: a json result with the data being a list of token dictionaries::

        { "data": [ { <token1> }, { <token2> } ]}

    :rtype: json
    """
    param = request.all_data
    user = request.User
    serial = getParam(param, "serial", optional)
    page = int(getParam(param, "page", optional, default=1))
    tokentype = getParam(param, "type", optional)
    token_type_list = getParam(param, "type_list", optional)
    if token_type_list:
        token_type_list = token_type_list.replace(" ", "").split(",")
    description = getParam(param, "description", optional)
    sort = getParam(param, "sortby", optional, default="serial")
    sdir = getParam(param, "sortdir", optional, default="asc")
    psize = int(getParam(param, "pagesize", optional, default=15))
    realm = getParam(param, "tokenrealm", optional)
    userid = getParam(param, "userid", optional)
    resolver = getParam(param, "resolver", optional)
    output_format = getParam(param, "outform", optional)
    assigned = getParam(param, "assigned", optional)
    active = getParam(param, "active", optional)
    tokeninfokey = getParam(param, "infokey", optional)
    tokeninfovalue = getParam(param, "infovalue", optional)
    rollout_state = getParam(param, "rollout_state", optional)
    container_serial = getParam(param, "container_serial", optional)
    tokeninfo = None
    if tokeninfokey and tokeninfovalue:
        tokeninfo = {tokeninfokey: tokeninfovalue}
    if assigned:
        assigned = assigned.lower() == "true"
    if active:
        active = active.lower() == "true"

    # allowed_realms determines, which realms the admin would be allowed to see
    # In certain cases like for users, we do not have allowed_realms
    allowed_realms = getattr(request, "pi_allowed_realms", None)
    g.audit_object.log({'info': "realm: {0!s}".format(allowed_realms)})

    # get hide_tokeninfo setting from all_data
    hidden_tokeninfo = getParam(param, 'hidden_tokeninfo', default=None)

    # get list of tokens as a dictionary
    tokens = get_tokens_paginate(serial=serial, realm=realm, page=page,
                                 user=user, assigned=assigned, psize=psize,
                                 active=active, sortby=sort, sortdir=sdir,
                                 tokentype=tokentype, token_type_list=token_type_list, resolver=resolver,
                                 description=description,
                                 userid=userid, allowed_realms=allowed_realms,
                                 tokeninfo=tokeninfo, rollout_state=rollout_state,
                                 hidden_tokeninfo=hidden_tokeninfo, container_serial=container_serial)
    g.audit_object.log({"success": True})
    if output_format == "csv":
        return send_csv_result(tokens)
    else:
        return send_result(tokens)


@token_blueprint.route('/assign', methods=['POST'])
@prepolicy(check_max_token_realm, request)
@prepolicy(check_max_token_user, request)
@prepolicy(check_token_action, request, action=ACTION.ASSIGN)
@prepolicy(check_user_params, request, action=ACTION.ASSIGN)
@prepolicy(encrypt_pin, request)
@prepolicy(check_otp_pin, request)
@prepolicy(check_external, request, action="assign")
@CheckSubscription(request)
@event("token_assign", request, g)
@log_with(log)
def assign_api():
    """
    Assign a token to a user.
    It also adds the user's realm to the token realms. Existing token realms are preserved.

    :jsonparam serial: The token, which should be assigned to a user
    :jsonparam user: The username of the user
    :jsonparam realm: The realm of the user
    :return: In case of success it returns "value": True.
    :rtype: json object
    """
    user = get_user_from_param(request.all_data, required)
    serial = getParam(request.all_data, "serial", required, allow_empty=False)
    pin = getParam(request.all_data, "pin")
    encrypt_pin_param = getParam(request.all_data, "encryptpin")
    if g.logged_in_user.get("role") == "user":
        err_message = "Token already assigned to another user."
    else:
        err_message = None
    res = assign_token(serial, user, pin=pin, encrypt_pin=encrypt_pin_param,
                       error_message=err_message)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/unassign', methods=['POST'])
@prepolicy(check_token_action, request, action=ACTION.UNASSIGN)
@event("token_unassign", request, g)
@log_with(log)
def unassign_api():
    """
    Unassign a token from a user.
    You can either provide "serial" as an argument to unassign this very
    token, or you can provide user and realm, to unassign all tokens of a user.

    :return: In case of success it returns the number of unassigned tokens in "value".
    :rtype: JSON object
    """
    user = request.User
    serial = getParam(request.all_data, "serial", optional)
    g.audit_object.log({"serial": serial})

    res = unassign_token(serial, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/revoke', methods=['POST'])
@token_blueprint.route('/revoke/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=ACTION.REVOKE)
@event("token_revoke", request, g)
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
    user = request.User
    if not serial:
        serial = getParam(request.all_data, "serial", optional)
    g.audit_object.log({"serial": serial})

    res = revoke_token(serial, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/enable', methods=['POST'])
@token_blueprint.route('/enable/<serial>', methods=['POST'])
@prepolicy(check_max_token_user, request)
@prepolicy(check_token_action, request, action=ACTION.ENABLE)
@event("token_enable", request, g)
@log_with(log)
def enable_api(serial=None):
    """
    Enable a single token or all the tokens of a user.

    :jsonparam basestring serial: the serial number of the single token to enable
    :jsonparam basestring user: The login name of the user
    :jsonparam basestring realm: the realm name of the user
    :return: In case of success it returns the number of enabled tokens in "value".
    :rtype: json object
    """
    user = request.User
    if not serial:
        serial = getParam(request.all_data, "serial", optional)
    g.audit_object.log({"serial": serial})

    res = enable_token(serial, enable=True, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/disable', methods=['POST'])
@token_blueprint.route('/disable/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=ACTION.DISABLE)
@event("token_disable", request, g)
@log_with(log)
def disable_api(serial=None):
    """
    Disable a single token or all the tokens of a user either by providing
    the serial number of the single token or a username and realm.

    Disabled tokens can not be used to authenticate but can be enabled again.

    :jsonparam basestring serial: the serial number of the single token to disable
    :jsonparam basestring user: The login name of the user
    :jsonparam basestring realm: the realm name of the user
    :return: In case of success it returns the number of disabled tokens in "value".
    :rtype: json object
    """
    user = request.User
    if not serial:
        serial = getParam(request.all_data, "serial", optional)
    g.audit_object.log({"serial": serial})

    res = enable_token(serial, enable=False, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/<serial>', methods=['DELETE'])
@prepolicy(check_token_action, request, action=ACTION.DELETE)
@event("token_delete", request, g)
@log_with(log)
def delete_api(serial):
    """
    Delete a token by its serial number.

    :jsonparam serial: The serial number of a single token.

    :return: In case of success it return the number of deleted tokens in
        "value"
    :rtype: json object
    """
    # If the API is called by a user, we pass the User Object to the function
    g.audit_object.log({"serial": serial})
    user = request.User
    res = remove_token(serial, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/batchdeletion', methods=['POST'])
@prepolicy(check_token_list_action, request, action=ACTION.DELETE)
@event("token_delete", request, g)
@log_with(log)
def batch_deletion():
    """
    Delete all passed tokens, e.g. all tokens of a container
    All errors during the deletion of a token are fetched to be able to delete the remaining tokens.

    :jsonparam serial: A comma separated list of token serials to delete
    :return: Dictionary with the serials as keys and the success status of the deletion as values
    """
    serial_list = getParam(request.all_data, "serial", required)
    serial_list = serial_list.replace(" ", "").split(",")
    g.audit_object.log({"serial": serial_list})
    ret = {}
    for serial in serial_list:
        try:
            success = remove_token(serial)
        except Exception as ex:
            # We are catching the exception here to be able to delete the remaining tokens
            log.error(f"Error deleting token {serial}: {ex}")
            success = False
        ret[serial] = success

    not_authorized_serials = getParam(request.all_data, "not_authorized_serials", optional=True)
    res = add_not_authorized_tokens_result(ret, not_authorized_serials)

    return send_result(res)


@token_blueprint.route('/reset', methods=['POST'])
@token_blueprint.route('/reset/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=ACTION.RESET)
@event("token_reset", request, g)
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
    user = request.User
    if not serial:
        serial = getParam(request.all_data, "serial", optional)
    g.audit_object.log({"serial": serial})

    res = reset_token(serial, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/resync', methods=['POST'])
@token_blueprint.route('/resync/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=ACTION.RESYNC)
@event("token_resync", request, g)
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
    user = request.User
    if not serial:
        serial = getParam(request.all_data, "serial", required)
    g.audit_object.log({"serial": serial})
    otp1 = getParam(request.all_data, "otp1", required)
    otp2 = getParam(request.all_data, "otp2", required)

    res = resync_token(serial, otp1, otp2, user=user)
    g.audit_object.log({"success": bool(res)})
    return send_result(res)


@token_blueprint.route('/setpin', methods=['POST'])
@token_blueprint.route('/setpin/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=ACTION.SETPIN)
@prepolicy(encrypt_pin, request)
@prepolicy(check_otp_pin, request, action=ACTION.SETPIN)
@postpolicy(save_pin_change, request)
@event("token_setpin", request, g)
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
    g.audit_object.log({"serial": serial})
    userpin = getParam(request.all_data, "userpin")
    sopin = getParam(request.all_data, "sopin")
    otppin = getParam(request.all_data, "otppin")
    user = request.User
    encrypt_pin_param = getParam(request.all_data, "encryptpin")

    res = 0
    if userpin is not None:
        g.audit_object.add_to_log({'action_detail': "userpin, "})
        res += set_pin_user(serial, userpin, user=user)

    if sopin is not None:
        g.audit_object.add_to_log({'action_detail': "sopin, "})
        res += set_pin_so(serial, sopin, user=user)

    if otppin is not None:
        g.audit_object.add_to_log({'action_detail': "otppin, "})
        res += set_pin(serial, otppin, user=user, encrypt_pin=encrypt_pin_param)

    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/setrandompin', methods=['POST'])
@token_blueprint.route('/setrandompin/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=ACTION.SETRANDOMPIN)
@prepolicy(set_random_pin, request)
@prepolicy(encrypt_pin, request)
@postpolicy(save_pin_change, request)
@event("token_setrandompin", request, g)
@log_with(log)
def setrandompin_api(serial=None):
    """
    Set the OTP PIN for a specific token to a random value.

    The token is identified by the unique serial number.

    :jsonparam basestring serial: the serial number of the single
        token to reset
    :return: In "value" returns the number of PINs set.
        The detail-section contains the key "pin" with the set PIN.
    :rtype: json object
    """
    if not serial:
        serial = getParam(request.all_data, "serial", required)
    g.audit_object.log({"serial": serial})
    user = request.User
    encrypt_pin_param = getParam(request.all_data, "encryptpin")
    pin = getParam(request.all_data, "pin")
    if not pin:
        raise TokenAdminError("We have an empty PIN. Please check your policy 'otp_pin_set_random'.")

    g.audit_object.add_to_log({'action_detail': "otppin, "})
    res = set_pin(serial, pin, user=user, encrypt_pin=encrypt_pin_param)
    g.audit_object.log({"success": True})
    return send_result(res, details={"pin": pin})


@token_blueprint.route('/description', methods=['POST'])
@token_blueprint.route('/description/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=ACTION.SETDESCRIPTION)
@event("token_set", request, g)
@log_with(log)
def set_description_api(serial=None):
    """
    This endpoint can be used by the user or by the admin to set
    the description of a token. Setting a description may be required by a policy.

    :jsonparam basestring description: The description for the token
    :param serial:
    :return:
    """
    user = request.User
    if not serial:
        serial = getParam(request.all_data, "serial", required)
    g.audit_object.log({"serial": serial})
    description = getParam(request.all_data, "description", optional=required)
    g.audit_object.add_to_log({'action_detail': "description={0!r}".format(description)})
    token = get_one_token(serial=serial, user=user)
    request.all_data["type"] = token.type
    require_description_on_edit(request)
    res = set_description(serial, description, user=user, token=token)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/set', methods=['POST'])
@token_blueprint.route('/set/<serial>', methods=['POST'])
@admin_required
@prepolicy(check_token_action, request, action=ACTION.SET)
@event("token_set", request, g)
@log_with(log)
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
        * validity_period_start
        * validity_period_end

    The token is identified by the unique serial number or by the token owner.
    In the later case all tokens of the owner will be modified.

    The validity period needs to be provided in the format
    YYYY-MM-DDThh:mm+oooo

    :jsonparam basestring serial: the serial number of the single token to reset
    :jsonparam basestring user: The username of the token owner
    :jsonparam basestring realm: The realm name of the token owner
    :return: returns the number of attributes set in "value"
    :rtype: json object
    """
    if not serial:
        serial = getParam(request.all_data, "serial", required)
    g.audit_object.log({"serial": serial})
    user = request.User

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

    if description is not None:
        g.audit_object.add_to_log({'action_detail': "description=%r, "
                                                    "" % description})
        res += set_description(serial, description, user=user)

    if count_window is not None:
        g.audit_object.add_to_log({'action_detail': "count_window=%r, "
                                                    "" % count_window})
        res += set_count_window(serial, count_window, user=user)

    if sync_window is not None:
        g.audit_object.add_to_log({'action_detail': "sync_window=%r, "
                                                    "" % sync_window})
        res += set_sync_window(serial, sync_window, user=user)

    if hashlib is not None:
        g.audit_object.add_to_log({'action_detail': "hashlib=%r, "
                                                    "" % hashlib})
        res += set_hashlib(serial, hashlib, user=user)

    if max_failcount is not None:
        g.audit_object.add_to_log({'action_detail': "max_failcount=%r, "
                                                    "" % max_failcount})
        res += set_max_failcount(serial, max_failcount, user=user)

    if count_auth_max is not None:
        g.audit_object.add_to_log({'action_detail': "count_auth_max=%r, "
                                                    "" % count_auth_max})
        res += set_count_auth(serial, count_auth_max, user=user, max=True)

    if count_auth_success_max is not None:
        g.audit_object.add_to_log({'action_detail':
            "count_auth_success_max={0!r}, ".format(
                count_auth_success_max)})
        res += set_count_auth(serial, count_auth_success_max, user=user,
                              max=True, success=True)

    if validity_period_end is not None:
        g.audit_object.add_to_log({'action_detail':
            "validity_period_end={0!r}, ".format(
                validity_period_end)})
        res += set_validity_period_end(serial, user, validity_period_end)

    if validity_period_start is not None:
        g.audit_object.add_to_log({'action_detail':
            "validity_period_start={0!r}, ".format(
                validity_period_start)})
        res += set_validity_period_start(serial, user, validity_period_start)

    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/realm/<serial>', methods=['POST'])
@admin_required
@log_with(log)
@prepolicy(check_max_token_realm, request)
@prepolicy(check_admin_tokenlist, request, action=ACTION.TOKENREALMS)
@prepolicy(check_token_action, request, action=ACTION.TOKENREALMS)
@event("token_realm", request, g)
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
    if isinstance(realms, list):
        realm_list = realms
    else:
        realm_list = [r.strip() for r in realms.split(",")]
    g.audit_object.log({"serial": serial})

    allowed_realms = getattr(request, "pi_allowed_realms", None)

    set_realms(serial, realms=realm_list, allowed_realms=allowed_realms)
    g.audit_object.log({"success": True})
    return send_result(True)


@token_blueprint.route('/load/<filename>', methods=['POST'])
@admin_required
@log_with(log)
@prepolicy(check_token_upload, request)
@event("token_load", request, g)
def loadtokens_api(filename=None):
    """
    The call imports the given file containing token definitions.
    The file can be an OATH CSV file, an aladdin XML file or a Yubikey CSV file
    exported from the yubikey initialization tool.

    The function is called as a POST request with the file upload.

    :jsonparam filename: The name of the token file, that is imported
    :jsonparam type: The file type. Can be "aladdin-xml",
        "oathcsv" or "yubikeycsv".
    :jsonparam tokenrealms: comma separated list of realms.
    :jsonparam psk: Pre Shared Key, when importing PSKC
    :jsonparam pskcValidateMAC: Determines how invalid MACs should be handled when importing PSKC.
               Allowed values are 'no_check', 'check_fail_soft' and 'check_fail_hard'.
    :return: The number of the imported tokens
    :rtype: int
    """
    if not filename:
        filename = getParam(request.all_data, "filename", required)
    known_types = ['aladdin-xml', 'oathcsv', "OATH CSV", 'yubikeycsv',
                   'Yubikey CSV', 'pskc']
    file_type = getParam(request.all_data, "type", required)
    aes_validate_mac = getParam(request.all_data, "pskcValidateMAC", default='check_fail_hard')
    aes_psk = getParam(request.all_data, "psk")
    aes_password = getParam(request.all_data, "password")
    if aes_psk and len(aes_psk) != 32:
        raise TokenAdminError("The Pre Shared Key must be 128 Bit hex "
                              "encoded. It must be 32 characters long!")
    trealms = getParam(request.all_data, "tokenrealms") or ""
    tokenrealms = []
    if trealms:
        tokenrealms = trealms.split(",")

    not_imported_serials = []
    token_file = request.files['file']
    if isinstance(token_file, FileStorage):
        log.debug(f"Werkzeug File storage file: {token_file}")
        file_contents = token_file.read()
    else:  # pragma: no cover
        # TODO: is that even possible? We might just throw an error here
        file_contents = token_file

    try:
        if isinstance(file_contents, bytes):
            file_contents = file_contents.decode()
    except UnicodeDecodeError as e:
        log.error(f"Unable to convert contents of file '{filename}' to unicode: {e}")
        raise ParameterError("Unable to convert file contents. Binary data is not supported")

    if file_contents == "":
        log.error(f"Error loading/importing token file. File {filename} is empty!")
        raise ParameterError("Error loading token file. File empty!")

    if file_type not in known_types:
        log.error(f"Unknown file type: '{file_type}'. Supported types are: "
                  f"{', '.join(known_types)}")
        raise TokenAdminError(f"Unknown file type: '{file_type}'. Supported "
                              f"types are: {', '.join(known_types)}")

    # Decrypt file, if necessary
    if file_contents.startswith("-----BEGIN PGP MESSAGE-----"):
        gpg = GPGImport(current_app.config)
        file_contents = gpg.decrypt(file_contents)

    # Parse the tokens from file and get dictionary
    if file_type == "aladdin-xml":
        import_tokens = parseSafeNetXML(file_contents)
    elif file_type in ["oathcsv", "OATH CSV"]:
        import_tokens = parseOATHcsv(file_contents)
    elif file_type in ["yubikeycsv", "Yubikey CSV"]:
        import_tokens = parseYubicoCSV(file_contents)
    elif file_type in ["pskc"]:
        import_tokens, not_imported_serials = parsePSKCdata(
            file_contents,
            preshared_key_hex=aes_psk,
            password=aes_password,
            validate_mac=aes_validate_mac)
    else:
        import_tokens = {}

    # Now import the Tokens from the dictionary
    for serial in import_tokens:
        log.debug(f"importing token {import_tokens[serial]}")
        log.info(f"initialize token. serial: {serial}, realm: {tokenrealms}")
        import_token(serial,
                     import_tokens[serial],
                     tokenrealms=tokenrealms)

    g.audit_object.log({'info': f"{file_type}, {token_file} (imported: {len(import_tokens)})",
                        'serial': ', '.join(import_tokens),
                        'success': True})

    return send_result({'n_imported': len(import_tokens), 'n_not_imported': len(not_imported_serials)})


@token_blueprint.route('/copypin', methods=['POST'])
@admin_required
@log_with(log)
@prepolicy(check_base_action, request, action=ACTION.COPYTOKENPIN)
@event("token_copypin", request, g)
def copypin_api():
    """
    Copy the token PIN from one token to the other.

    :jsonparam basestring from: the serial number of the token, from where you
        want to copy the pin.
    :jsonparam basestring to: the serial number of the token, to where you
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
@admin_required
@prepolicy(check_base_action, request, action=ACTION.COPYTOKENUSER)
@event("token_copyuser", request, g)
@log_with(log)
def copyuser_api():
    """
    Copy the token user from one token to the other.

    :jsonparam basestring from: the serial number of the token, from where you
        want to copy the user.
    :jsonparam basestring to: the serial number of the token, to where you
        want to copy the user.
    :return: returns value=True in case of success
    :rtype: bool
    """
    serial_from = getParam(request.all_data, "from", required)
    serial_to = getParam(request.all_data, "to", required)
    res = copy_token_user(serial_from, serial_to)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/lost/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=ACTION.LOSTTOKEN)
@event("token_lost", request, g)
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
    g.audit_object.log({"serial": serial})
    userobj = request.User
    if userobj:
        toks = get_tokens(serial=serial, user=userobj)
        if not toks:
            raise TokenAdminError("The user {0!r} does not own the token {1!s}".format(
                userobj, serial))

    options = {"g": g,
               "clientip": g.client_ip}
    res = lost_token(serial, options=options)

    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/getserial/<otp>', methods=['GET'])
@admin_required
@prepolicy(check_base_action, request, action=ACTION.GETSERIAL)
@event("token_getserial", request, g)
@log_with(log)
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
    :query count: if set=1, only return the number of tokens, that will be
        searched
    :query serial: This can be a substring of serial numbers to search in.
    :query window: The number of OTP look ahead (default=10)
    :return: The serial number of the token found
    """
    ttype = getParam(request.all_data, "type")
    unassigned_param = getParam(request.all_data, "unassigned")
    assigned_param = getParam(request.all_data, "assigned")
    serial_substr = getParam(request.all_data, "serial")
    count_only = getParam(request.all_data, "count")
    window = int(getParam(request.all_data, "window", default=10))

    serial_substr = serial_substr or ""

    serial = None
    assigned = None
    if unassigned_param:
        assigned = False
    if assigned_param:
        assigned = True

    count = get_tokens(tokentype=ttype, serial_wildcard="*{0!s}*".format(
        serial_substr), assigned=assigned, count=True)
    if not count_only:
        tokenobj_list = get_tokens(tokentype=ttype,
                                   serial_wildcard="*{0!s}*".format(serial_substr),
                                   assigned=assigned)
        serial = get_serial_by_otp(tokenobj_list, otp=otp, window=window)

    g.audit_object.log({"success": True,
                        "info": "get {0!s} by OTP. {1!s} tokens".format(
                            serial, count)})

    return send_result({"serial": serial,
                        "count": count})


@token_blueprint.route('/info/<serial>/<key>', methods=['POST'])
@admin_required
@prepolicy(check_token_action, request, action=ACTION.SETTOKENINFO)
@event("token_info", request, g)
@log_with(log)
def set_tokeninfo_api(serial, key):
    """
    Add a specific tokeninfo entry to a token. Already existing entries
    with the same key are overwritten.

    :param serial: the serial number/identifier of the token
    :param key: token info key that should be set
    :query value: token info value that should be set
    :return: returns value=True in case the token info could be set
    :rtype: bool
    """
    value = getParam(request.all_data, "value", required)
    g.audit_object.log({"serial": serial})
    count = add_tokeninfo(serial, key, value)
    success = count > 0
    g.audit_object.log({"success": success})
    return send_result(success)


@token_blueprint.route('/info/<serial>/<key>', methods=['DELETE'])
@admin_required
@prepolicy(check_token_action, request, action=ACTION.SETTOKENINFO)
@event("token_info", request, g)
@log_with(log)
def delete_tokeninfo_api(serial, key):
    """
    Delete a specific tokeninfo entry of a token.

    :param serial: the serial number/identifier of the token
    :param key: token info key that should be deleted
    :return: returns value=True in case a matching token was found, which does not necessarily mean
    that the matching token had a tokeninfo value set in the first place.
    :rtype: bool
    """
    g.audit_object.log({"serial": serial})
    count = delete_tokeninfo(serial, key)
    success = count > 0
    g.audit_object.log({"success": success})
    return send_result(success)


@token_blueprint.route('/group/<serial>/<groupname>', methods=['POST'])
@token_blueprint.route('/group/<serial>', methods=['POST'])
@admin_required
@prepolicy(check_token_action, request, ACTION.TOKENGROUPS)
@event("token_assign_group", request, g)
@log_with(log)
def assign_tokengroup_api(serial, groupname=None):
    """
    Assigns a token to a given tokengroup.

    If no groupname is given, we expect a body data "groups", that
    contains a list of tokengroups. tokengroups that are
    not contained in this list, will be removed.

    :jsonparam basestring serial: the serial number of the token
    :jsonparam basestring groupname: The name of the tokengroup
    :jsonparam list groups: A list of tokengroups
    :return:
    :rtype: json object
    """
    g.audit_object.log({"serial": serial})
    if groupname:
        g.audit_object.add_to_log({'action_detail': groupname})
        assign_tokengroup(serial, tokengroup=groupname)
    else:
        groups = getParam(request.all_data, "groups", required)
        if isinstance(groups, list):
            group_list = groups
        else:
            group_list = [r.strip() for r in groups.split(",")]
        g.audit_object.add_to_log({'action_detail': ",".join(group_list)})
        set_tokengroups(serial, group_list)
    g.audit_object.log({"success": True})
    return send_result(1)


@token_blueprint.route('/group/<serial>/<groupname>', methods=['DELETE'])
@admin_required
@prepolicy(check_token_action, request, ACTION.TOKENGROUPS)
@event("token_unassign_group", request, g)
@log_with(log)
def unassign_tokengroup_api(serial, groupname):
    """
    Unassigned a token from a tokengroup.

    :jsonparam basestring serial: the serial number of the token
    :jsonparam basestring groupname: The name of the tokengroup
    :return:
    :rtype: json object
    """
    g.audit_object.add_to_log({'action_detail': groupname})
    unassign_tokengroup(serial, tokengroup=groupname)
    g.audit_object.add_to_log({'success': True})
    return send_result(1)
