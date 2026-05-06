# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2015-12-28 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add sending of email via smtp config
# 2015-12-23 Cornelius Kölbel <cornelius@privacyidea.org>
#            Add this register endpoint for new users to create a new user
#            account.
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
__doc__ = """
The register REST API lets an unauthenticated user create a new user
account in an editable user resolver. Successful registration creates
the user, issues a registration token, and emails the registration key
to the user. The user can then complete enrollment by authenticating
with their chosen password and that registration key.

Both endpoints are anonymous (no auth header). Registration is gated
by a set of policies in scope ``register`` — a destination
``resolver`` is required, plus ``smtpconfig`` for sending the email,
optionally ``realm``, ``registration_body`` and ``requiredemail``. See
:ref:`register_policy` for the full list.
"""
from flask_babel import _
from flask import (Blueprint, request, g)
from .lib.utils import getParam, map_error_to_code, send_error, send_result
from .lib.utils import required
import logging
from privacyidea.lib.policy import SCOPE
from ..lib.policies.actions import PolicyAction
from privacyidea.lib.user import create_user
from privacyidea.lib.user import User
from privacyidea.lib.token import init_token
from privacyidea.lib.policy import Match
from privacyidea.lib.realm import get_default_realm
from privacyidea.lib.error import RegistrationError, Error
from privacyidea.api.lib.prepolicy import required_email, prepolicy
from privacyidea.lib.smtpserver import send_email_identifier

DEFAULT_BODY="""
Your registration token is {regkey}.
"""

log = logging.getLogger(__name__)

register_blueprint = Blueprint('register_blueprint', __name__)


# The before and after methods are the same as in the validate endpoint

@register_blueprint.route('', methods=['GET'])
def register_status():
    """
    Return whether self-registration is enabled on this server. The result
    is ``True`` when at least one policy in scope ``register`` configures a
    ``resolver`` action; otherwise ``False``. The WebUI uses this to decide
    whether to show the registration button.

    This endpoint is anonymous — no authentication header is required.

    :status 200: ``result.value`` is ``True`` if registration is configured,
        ``False`` otherwise.
    """
    resolvername = Match.action_only(g, scope=SCOPE.REGISTER, action=PolicyAction.RESOLVER)\
        .action_values(unique=True)
    result = bool(resolvername)
    g.audit_object.log({"info": result,
                        "success": True})
    return send_result(result)


@register_blueprint.route('', methods=['POST'])
@prepolicy(required_email, request=request)
def register_post():
    """
    Register a new user in a configured user resolver. The destination
    resolver must be editable (e.g. an SQL resolver). On success the call
    creates the user account, issues a registration token, and emails the
    registration key to ``email``.

    If the email cannot be sent, the just-created user and token are
    removed before the request fails — failed registrations leave no
    state behind.

    This endpoint is anonymous. Registration depends on policies in scope
    ``register``:

    * ``resolver`` (required) — the editable resolver to create the user in.
    * ``smtpconfig`` (required) — identifier of the SMTP server used to
      send the registration email.
    * ``realm`` (optional) — the realm to register in. Defaults to the
      default realm.
    * ``registration_body`` (optional) — text template for the email body;
      ``{regkey}`` is substituted with the registration key.
    * ``requiredemail`` (optional) — restricts which email addresses may
      register (enforced by the ``required_email`` prepolicy).
    * ``hide_specific_error_message`` (optional) — masks specific error
      messages with a generic registration error.

    :jsonparam username: login name of the new user (required).
    :jsonparam givenname: given name (required).
    :jsonparam surname: surname (required).
    :jsonparam email: email address (required); registration key is sent
        here.
    :jsonparam password: password the user will authenticate with
        (required).
    :jsonparam mobile: mobile phone number.
    :jsonparam phone: land line phone number.
    :status 200: ``result.value`` is ``True`` if the user was created and
        the registration email was sent.
    :status 400: registration prerequisites not met (no resolver
        configured, SMTP not configured, username already registered,
        email rejected by ``requiredemail``, send failure).
    """
    username = getParam(request.all_data, "username", required)
    surname = getParam(request.all_data, "surname", required)
    givenname = getParam(request.all_data, "givenname", required)
    email = getParam(request.all_data, "email", required)
    password = getParam(request.all_data, "password", required)
    mobile = getParam(request.all_data, "mobile")
    phone = getParam(request.all_data, "phone")
    options = {"g": g,
               "clientip": g.client_ip}
    g.audit_object.log({"info": username})
    # Add all params to the options
    for key, value in request.all_data.items():
            if value and key not in ["g", "clientip"]:
                options[key] = value

    # 0. check, if we can do the registration at all!
    smtpconfig = Match.action_only(g, scope=SCOPE.REGISTER, action=PolicyAction.EMAILCONFIG)\
        .action_values(unique=True)
    if not smtpconfig:
        raise RegistrationError(_("No SMTP server configuration specified!"))

    # 1. determine, in which resolver/realm the user should be created
    realm = Match.action_only(g, scope=SCOPE.REGISTER, action=PolicyAction.REALM)\
        .action_values(unique=True)
    if not realm:
        # No policy for realm, so we use the default realm
        realm = get_default_realm
    else:
        # we use the first realm in the list
        realm = list(realm)[0]
    resolvername = Match.action_only(g, scope=SCOPE.REGISTER, action=PolicyAction.RESOLVER)\
        .action_values(unique=True)
    if not resolvername:
        raise RegistrationError(_("No resolver specified to register in!"))
    resolvername = list(resolvername)[0]

    try:
        # Check if the user exists
        user = User(username, realm=realm, resolver=resolvername)
        if user.exist():
            raise RegistrationError(_("The username is already registered!"))
        # Create user
        uid = create_user(resolvername, {"username": username,
                                         "email": email,
                                         "phone": phone,
                                         "mobile": mobile,
                                         "surname": surname,
                                         "givenname": givenname,
                                         "password": password})

        # 3. create a registration token for this user
        user = User(realm=realm, resolver=resolvername, uid=uid)
        token = init_token({"type": "registration"}, user=user)
        # 4. send the registration token to the users email
        registration_key = token.init_details.get("otpkey")

        smtpconfig = list(smtpconfig)[0]
        # Send the registration key via email
        body = Match.action_only(g, scope=SCOPE.REGISTER, action=PolicyAction.REGISTERBODY)\
            .action_values(unique=True)
        body = body or DEFAULT_BODY
        email_sent = send_email_identifier(
            smtpconfig, email,
            "Your privacyIDEA registration",
            body.format(regkey=registration_key))
        if not email_sent:
            log.warning("Failed to send registration email to {0!r}".format(email))
            # delete registration token
            token.delete_token()
            # delete user
            user.delete()
            raise RegistrationError(_("Failed to send email!"))

        log.debug("Registration email sent to {0!r}".format(email))

        g.audit_object.log({"success": email_sent})
        return send_result(email_sent)

    except Exception as e:
        if Match.realm(
            g,
            scope=SCOPE.REGISTER,
            action=PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE,
            realm=realm,
        ).any():
            return send_error("Failed registering new user", error_code=Error.REGISTRATION), map_error_to_code(e)
        raise
