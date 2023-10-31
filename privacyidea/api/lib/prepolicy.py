# -*- coding: utf-8 -*-
#
#  2020-01-28 Jean-Pierre Höhmann <jean-pierre.hoehmann@netknights.it>
#             Add WebAuthn token
#  2019-02-10 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add push token enrollment policy
#  2018-11-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Implement remaining pin policies
#  2018-11-12 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             In case of "setrealm" allow a user no to be in the
#             original realm.
#  2017-04-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add wrapper for U2F token
#  2017-01-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add token specific PIN policies based on
#             Quynh's pull request.
#  2016-11-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add timelimit for audit entries
#  2016-08-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add decorator to save the client type to the database
#  2016-07-17 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add realmadmin decorator
#  2016-05-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add resolver to check_base_action
#  2016-04-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add init_token_defaults to set default parameters
#             during token init.
#  2016-04-08 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Avoid "None" as redundant 2nd argument
#  2015-12-28 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add ACTION.REQUIREDEMAIL
#  2015-12-12 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Change eval to importlib
#  2015-11-04 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add check for REMOTE_USER
#  2015-04-13 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add hook for external decorator for init and assign
#  2015-02-06 Cornelius Kölbel <cornelius@privacyidea.org>
#             Create this module for enabling decorators for API calls
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
"""
These are the policy decorators as PRE conditions for the API calls.
I.e. these conditions are executed before the wrapped API call.
This module uses the policy base functions from
privacyidea.lib.policy but also components from flask like g.

Wrapping the functions in a decorator class enables easy modular testing.

The functions of this module are tested in tests/test_api_lib_policy.py
"""

import logging

from OpenSSL import crypto
from privacyidea.lib import _
from privacyidea.lib.error import PolicyError, RegistrationError, TokenAdminError, ResourceNotFoundError, ParameterError
from flask import g, current_app
from privacyidea.lib.policy import SCOPE, ACTION, REMOTE_USER
from privacyidea.lib.policy import Match, check_pin
from privacyidea.lib.user import (get_user_from_param, get_default_realm,
                                  split_user, User)
from privacyidea.lib.token import (get_tokens, get_realms_of_token, get_token_type, get_token_owner)
from privacyidea.lib.utils import (parse_timedelta, is_true, generate_charlists_from_pin_policy,
                                   get_module_class,
                                   determine_logged_in_userparams, parse_string_to_dict)
from privacyidea.lib.crypto import generate_password
from privacyidea.lib.auth import ROLE
from privacyidea.api.lib.utils import getParam, attestation_certificate_allowed, is_fqdn
from privacyidea.api.lib.policyhelper import get_init_tokenlabel_parameters, get_pushtoken_add_config
from privacyidea.lib.clientapplication import save_clientapplication
from privacyidea.lib.config import (get_token_class)
from privacyidea.lib.tokenclass import ROLLOUTSTATE
from privacyidea.lib.tokens.certificatetoken import ACTION as CERTIFICATE_ACTION
from privacyidea.lib.token import get_one_token
import functools
import jwt
import re
import importlib

# Token specific imports!
from privacyidea.lib.tokens.webauthn import (WebAuthnRegistrationResponse,
                                             AUTHENTICATOR_ATTACHMENT_TYPES,
                                             USER_VERIFICATION_LEVELS, ATTESTATION_LEVELS,
                                             ATTESTATION_FORMS)
from privacyidea.lib.tokens.webauthntoken import (WEBAUTHNACTION,
                                                  DEFAULT_PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE,
                                                  PUBLIC_KEY_CREDENTIAL_ALGORITHMS,
                                                  PUBKEY_CRED_ALGORITHMS_ORDER,
                                                  DEFAULT_TIMEOUT, DEFAULT_ALLOWED_TRANSPORTS,
                                                  DEFAULT_USER_VERIFICATION_REQUIREMENT,
                                                  DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL,
                                                  DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
                                                  WebAuthnTokenClass, DEFAULT_CHALLENGE_TEXT_AUTH,
                                                  DEFAULT_CHALLENGE_TEXT_ENROLL,
                                                  is_webauthn_assertion_response)
from privacyidea.lib.tokens.u2ftoken import (U2FACTION, parse_registration_data)
from privacyidea.lib.tokens.u2f import x509name_to_string
from privacyidea.lib.tokens.pushtoken import PUSH_ACTION
from privacyidea.lib.tokens.indexedsecrettoken import PIIXACTION

log = logging.getLogger(__name__)

optional = True
required = False


class prepolicy(object):
    """
    This is the decorator wrapper to call a specific function before an API
    call.
    The prepolicy decorator is to be used in the API calls.
    A prepolicy decorator then will modify the request data or raise an
    exception
    """
    def __init__(self, function, request, action=None):
        """
        :param function: This is the policy function the is to be called
        :type function: function
        :param request: The original request object, that needs to be passed
        :type request: Request Object
        """
        self.action = action
        self.request = request
        self.function = function

    def __call__(self, wrapped_function):
        """
        This decorates the given function. The prepolicy decorator is ment
        for API functions on the API level.

        If some error occur the a PolicyException is raised.

        The decorator function can modify the request data.

        :param wrapped_function: The function, that is decorated.
        :type wrapped_function: API function
        :return: None
        """
        @functools.wraps(wrapped_function)
        def policy_wrapper(*args, **kwds):
            self.function(request=self.request,
                          action=self.action)
            return wrapped_function(*args, **kwds)

        return policy_wrapper


def _generate_pin_from_policy(policy, size=6):
    """
    This helper function creates a string of allowed characters from the value of a pincontents policy.

    :param policy: The policy that describes the allowed contents of the PIN (see check_pin_contents).
    :param size: The desired length of the generated pin
    :return: The generated PIN
    """

    charlists_dict = generate_charlists_from_pin_policy(policy)

    pin = generate_password(size=size, characters=charlists_dict['base'],
                      requirements=charlists_dict['requirements'])
    return pin


def set_random_pin(request=None, action=None):
    """
    This policy function is to be used as a decorator in the API setrandompin function
    If the policy is set accordingly it adds a random PIN to the
    request.all_data like.

    It uses the policy ACTION.OTPPINSETRANDOM in SCOPE.ADMIN or SCOPE.USER to set a random OTP PIN
    """
    params = request.all_data
    policy_object = g.policy_object
    # Determine the user and admin. We still pass the "username" and "realm" explicitly,
    # since we could have an admin request with only a realm, but not a complete user_object.
    user_object = request.User
    (role, username, realm, adminuser, adminrealm) = determine_logged_in_userparams(g.logged_in_user, params)

    # get the length of the random PIN from the policies
    pin_pols = Match.generic(g, action=ACTION.OTPPINSETRANDOM,
                             scope=role,
                             adminrealm=adminrealm,
                             adminuser=adminuser,
                             user=username,
                             realm=realm,
                             user_object=user_object).action_values(unique=True)

    if len(pin_pols) == 0:
        # We do this to avoid that an admin sets a random PIN manually!
        raise TokenAdminError("You need to specify a policy '{0!s}' in scope "
                              "{1!s}.".format(ACTION.OTPPINSETRANDOM, role))
    elif len(pin_pols) == 1:
        # check pin contents policy per token type, otherwise fall back
        tokentype = get_token_type(request.all_data.get("serial"))
        pol_contents = Match.admin_or_user(g, action="{0!s}_{1!s}".format(tokentype, ACTION.OTPPINCONTENTS),
                                           user_obj=request.User).action_values(unique=True)
        if not pol_contents:
            pol_contents = Match.admin_or_user(g, action=ACTION.OTPPINCONTENTS,
                                               user_obj=request.User).action_values(unique=True)

        if len(pol_contents) == 1:
            log.info("Creating random OTP PIN with length {0!s} "
                      "matching the contents policy {1!s}".format(list(pin_pols)[0], list(pol_contents)[0]))
            # generate a pin which matches the contents requirement
            r = _generate_pin_from_policy(list(pol_contents)[0], size=int(list(pin_pols)[0]))
            request.all_data["pin"] = r
        else:
            log.debug("Creating random OTP PIN with length {0!s}".format(list(pin_pols)[0]))
            request.all_data["pin"] = generate_password(size=int(list(pin_pols)[0]))

    return True


def init_random_pin(request=None, action=None):
    """
    This policy function is to be used as a decorator in the API init function
    If the policy is set accordingly it adds a random PIN to the
    request.all_data like.

    It uses the policy SCOPE.ENROLL, ACTION.OTPPINRANDOM and ACTION.OTPPINCONTENTS
    to set a random OTP PIN during Token enrollment
    """
    params = request.all_data
    user_object = get_user_from_param(params)
    # get the length of the random PIN from the policies
    pin_pols = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.OTPPINRANDOM,
                          user_object=user_object).action_values(unique=True)
    if len(pin_pols) == 1:
        # check pin contents policy per token type, otherwise fall back
        tokentype = request.all_data.get("type", "hotp")
        pol_contents = Match.admin_or_user(g, action="{0!s}_{1!s}".format(tokentype, ACTION.OTPPINCONTENTS),
                                           user_obj=request.User).action_values(unique=True)
        if not pol_contents:
            pol_contents = Match.admin_or_user(g, action=ACTION.OTPPINCONTENTS,
                                               user_obj=request.User).action_values(unique=True)

        if len(pol_contents) == 1:
            log.info("Creating random OTP PIN with length {0!s} "
                      "matching the contents policy {1!s}".format(list(pin_pols)[0], list(pol_contents)[0]))
            # generate a pin which matches the contents requirement
            r = _generate_pin_from_policy(list(pol_contents)[0], size=int(list(pin_pols)[0]))
            request.all_data["pin"] = r
        else:
            log.debug("Creating random OTP PIN with length {0!s}".format(list(pin_pols)[0]))
            request.all_data["pin"] = generate_password(size=int(list(pin_pols)[0]))

        # handle the PIN
        handle_pols = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.PINHANDLING,
                                 user_object=user_object).action_values(unique=False)
        # We can have more than one pin handler policy. So we can process the
        #  PIN in several ways!
        for handle_pol in handle_pols:
            log.debug("Handle the random PIN with the class {0!s}".format(handle_pol))
            package_name, class_name = handle_pol.rsplit(".", 1)
            pin_handler_class = get_module_class(package_name, class_name)
            pin_handler = pin_handler_class()
            # Send the PIN
            pin_handler.send(request.all_data["pin"],
                             request.all_data.get("serial", "N/A"),
                             user_object,
                             tokentype=request.all_data.get("type", "hotp"),
                             logged_in_user=g.logged_in_user)

    return True


def realmadmin(request=None, action=None):
    """
    This decorator adds the first REALM to the parameters if the
    administrator, calling this API is a realm admin.
    This way, if the admin calls e.g. GET /user without realm parameter,
    he will not see all users, but only users in one of his realms.

    TODO: If a realm admin is allowed to see more than one realm,
          this is not handled at the moment. We need to change the underlying
          library functions!

    :param request: The HTTP reqeust
    :param action: The action like ACTION.USERLIST
    """
    # This decorator is only valid for admins
    if g.logged_in_user.get("role") == ROLE.ADMIN:
        params = request.all_data
        if not "realm" in params:
            # add the realm to params
            po = Match.admin(g, action=action).policies()
            # TODO: fix this: there could be a list of policies with a list
            # of realms!
            if po and po[0].get("realm"):
                request.all_data["realm"] = po[0].get("realm")[0]

    return True


def check_otp_pin(request=None, action=None):
    """
    This policy function checks if the OTP PIN that is about to be set
    follows the OTP PIN policies ACTION.OTPPINMAXLEN, ACTION.OTPPINMINLEN and
    ACTION.OTPPINCONTENTS and token-type-specific PIN policy actions in the
    SCOPE.USER or SCOPE.ADMIN. It is used to decorate the API functions.

    The pin is investigated in the params as "otppin" or "pin"

    In case the given OTP PIN does not match the requirements an exception is
    raised.
    """
    params = request.all_data
    pin = params.get("otppin", "") or params.get("pin", "")
    serial = params.get("serial")
    tokentype = params.get("type")
    rollover = params.get("rollover")
    verify = params.get("verify")
    if rollover or verify:
        log.debug(f"Disable PIN checking due to rollover ({rollover}) or verify ({verify})")
        return True
    if not serial and action == ACTION.SETPIN:
        path_elems = request.path.split("/")
        serial = path_elems[-1]
        # Also set it for later use
        request.all_data["serial"] = serial
    if serial:
        # if this is a token, that does not use a pin, we ignore this check
        # And immediately return true
        tokensobject_list = get_tokens(serial=serial)
        if len(tokensobject_list) == 1:
            if tokensobject_list[0].using_pin is False:
                return True
            tokentype = tokensobject_list[0].token.tokentype
    # the default tokentype is still HOTP
    tokentype = tokentype or "hotp"
    check_pin(g, pin, tokentype, request.User)
    return True


def check_application_tokentype(request=None, action=None):
    """
    This pre policy checks if the request is allowed to specify the tokentype.
    If the policy is not set, a possibly set parameter "type" is removed
    from the request.

    Check ACTION.APPLICATION_TOKENTYPE

    This decorator should wrap
        /validate/check, /validate/samlcheck and /validate/triggerchallenge.

    :param request: The request that is intercepted during the API call
    :type request: Request Object
    :param action: An optional Action
    :type action: basestring
    :returns: Always true. Modified the parameter request
    """
    application_allowed = Match.generic(g, scope=SCOPE.AUTHZ,
                                        action=ACTION.APPLICATION_TOKENTYPE,
                                        user_object=request.User,
                                        active=True).any()

    # if the application is not allowed, we remove the tokentype
    if not application_allowed and "type" in request.all_data:
        log.info("Removing parameter 'type' from request, "
                 "since application is not allowed to authenticate by token type.")
        del request.all_data["type"]

    return True


def sms_identifiers(request=None, action=None):
    """
    This is a token specific wrapper for sms tokens
    to be used with the endpoint /token/init.
    According to the policy scope=SCOPE.ADMIN or scope=SCOPE.USER
    action=SMSACTION.GATEWAYS the sms.identifier is only allowed to be set to the listed gateways.

    :param request:
    :param action:
    :return:
    """
    sms_identifier = request.all_data.get("sms.identifier")
    if sms_identifier:
        from privacyidea.lib.tokens.smstoken import SMSACTION
        pols = Match.admin_or_user(g, action=SMSACTION.GATEWAYS, user_obj=request.User).action_values(unique=False)
        gateway_identifiers = []

        for p in pols:
            gateway_identifiers.append(p)
        if sms_identifier not in gateway_identifiers:
            log.warning("{0!s} not in {1!s}".format(sms_identifier, gateway_identifiers))
            raise PolicyError("The requested sms.identifier is not allowed to be enrolled.")

    return True


def papertoken_count(request=None, action=None):
    """
    This is a token specific wrapper for paper token for the endpoint
    /token/init.
    According to the policy scope=SCOPE.ENROLL,
    action=PAPERACTION.PAPER_COUNT it sets the parameter papertoken_count to
    enroll a paper token with such many OTP values.

    :param request:
    :param action:
    :return:
    """
    from privacyidea.lib.tokens.papertoken import PAPERACTION
    pols = Match.user(g, scope=SCOPE.ENROLL, action=PAPERACTION.PAPERTOKEN_COUNT,
                      user_object=request.User).action_values(unique=True)
    if pols:
        papertoken_count = list(pols)[0]
        request.all_data["papertoken_count"] = papertoken_count

    return True


def tantoken_count(request=None, action=None):
    """
    This is a token specific wrapper for tan token for the endpoint
    /token/init.
    According to the policy scope=SCOPE.ENROLL,
    action=TANACTION.TANTOKEN_COUNT it sets the parameter tantoken_count to
    enroll a tan token with such many OTP values.

    :param request:
    :param action:
    :return:
    """
    from privacyidea.lib.tokens.tantoken import TANACTION
    pols = Match.user(g, scope=SCOPE.ENROLL, action=TANACTION.TANTOKEN_COUNT,
                      user_object=request.User).action_values(unique=True)
    if pols:
        tantoken_count = list(pols)[0]
        request.all_data["tantoken_count"] = tantoken_count

    return True


def encrypt_pin(request=None, action=None):
    """
    This policy function is to be used as a decorator for several API functions.
    E.g. token/assign, token/setpin, token/init
    If the policy is set to define the PIN to be encrypted,
    the request.all_data is modified like this:
    encryptpin = True

    It uses the policy SCOPE.ENROLL, ACTION.ENCRYPTPIN
    """
    params = request.all_data
    user_object = get_user_from_param(params)
    # get the length of the random PIN from the policies
    pin_pols = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.ENCRYPTPIN,
                          user_object=user_object).policies()
    if pin_pols:
        request.all_data["encryptpin"] = "True"
    else:
        if "encryptpin" in request.all_data:
            del request.all_data["encryptpin"]

    return True


def enroll_pin(request=None, action=None):
    """
    This policy function is used as decorator for init token.
    It checks, if the user or the admin is allowed to set a token PIN during
    enrollment. If not, it deleted the PIN from the request.
    """
    resolver = request.User.resolver if request.User else None
    (role, username, userrealm, adminuser, adminrealm ) = determine_logged_in_userparams(g.logged_in_user,
                                                                                         request.all_data)
    allowed_action = Match.generic(g, scope=role,
                                   action=ACTION.ENROLLPIN,
                                   user_object=request.User,
                                   user=username,
                                   resolver=resolver,
                                   realm=userrealm,
                                   adminrealm=adminrealm,
                                   adminuser=adminuser,
                                   active=True).allowed()

    if not allowed_action:
        # Not allowed to set a PIN during enrollment!
        if "pin" in request.all_data:
            del request.all_data["pin"]
    return True


def init_token_defaults(request=None, action=None):
    """
    This policy function is used as a decorator for the API init function.
    Depending on policy settings it can add token specific default values
    like totp_hashlib, hotp_hashlib, totp_otplen...
    """
    params = request.all_data
    ttype = params.get("type") or "hotp"
    token_class = get_token_class(ttype)
    default_settings = token_class.get_default_settings(g, params)
    log.debug("Adding default settings {0!s} for token type {1!s}".format(
        default_settings, ttype))
    request.all_data.update(default_settings)
    return True


def init_token_length_contents(request=None, action=None):
    """
    This policy function is to be used as a decorator in the API token init function.

    It can set the parameters for automatic code or password created in regards to length and
    contents for the tokentypes 'registration' and 'pw'.

    If there is a valid policy set the action values of REGISTRATIONCODE_LENGTH / PASSWORD_LENGTH
    and REGISTRATIONCODE_CONTENTS / PASSWORD_CONTENTS are added to request.all_data as

    { 'registration.length': '10', 'registration.contents': 'cn' }
    or
    { 'pw.length': '10', 'pw.contents': 'cn' }
    """
    no_content_policy = True
    no_length_policy = True
    params = request.all_data
    tokentype = params.get("type")

    if tokentype == 'registration':
        from privacyidea.lib.tokens.registrationtoken import DEFAULT_LENGTH, DEFAULT_CONTENTS
        length_action = ACTION.REGISTRATIONCODE_LENGTH
        contents_action = ACTION.REGISTRATIONCODE_CONTENTS
    elif tokentype == 'pw':
        from privacyidea.lib.tokens.passwordtoken import DEFAULT_LENGTH, DEFAULT_CONTENTS
        length_action = ACTION.PASSWORD_LENGTH
        contents_action = ACTION.PASSWORD_CONTENTS
    else:
        return True

    user_object = get_user_from_param(params)
    length_pols = Match.user(g, scope=SCOPE.ENROLL, action=length_action,
                            user_object=user_object).action_values(unique=True)
    if len(length_pols) == 1:
        request.all_data[length_action] = list(length_pols)[0]
        no_length_policy = False
    content_pols = Match.user(g, scope=SCOPE.ENROLL, action=contents_action,
                            user_object=user_object).action_values(unique=True)
    if len(content_pols) == 1:
        request.all_data[contents_action] = list(content_pols)[0]
        no_content_policy = False
    # if there is no policy, set defaults.
    if no_length_policy:
        request.all_data[length_action] = DEFAULT_LENGTH
    if no_content_policy:
        request.all_data[contents_action] = DEFAULT_CONTENTS
    return True


def init_tokenlabel(request=None, action=None):
    """
    This policy function is to be used as a decorator in the API init function.
    It adds the tokenlabel definition to the params like this:
    params : { "tokenlabel": "<u>@<r>" }

    In addition it adds the tokenissuer to the params like this:
    params : { "tokenissuer": "privacyIDEA instance" }

    It also checks if the force_app_pin policy is set and adds the corresponding
    value to params.

    It uses the policy SCOPE.ENROLL, ACTION.TOKENLABEL and ACTION.TOKENISSUER
    to set the tokenlabel and tokenissuer
    of Smartphone tokens during enrollment and this fill the details of the
    response.
    """
    params = request.all_data
    user_object = get_user_from_param(params)
    token_type = getParam(params, "type", optional, "hotp").lower()
    request.all_data = get_init_tokenlabel_parameters(g, params=params, token_type=token_type, user_object=user_object)
    return True


def init_ca_connector(request=None, action=None):
    """
    This is a pre decorator for the endpoint '/token/init'.
    It reads the policy scope=enrollment, action=certificate_ca_connector and
    sets the API parameter "ca" accordingly.

    :param request: The request to enhance
    :return: None, but we modify the request
    """
    params = request.all_data
    user_object = get_user_from_param(params)
    token_type = getParam(request.all_data, "type", optional)
    if token_type and token_type.lower() == "certificate":
        # get the CA connectors from the policies
        ca_pols = Match.user(g, scope=SCOPE.ENROLL, action=CERTIFICATE_ACTION.CA_CONNECTOR,
                             user_object=user_object).action_values(unique=True)
        if len(ca_pols) == 1:
            # The policy was set, so we need to set the CA in the request
            request.all_data["ca"] = list(ca_pols)[0]


def init_ca_template(request=None, action=None):
    """
    This is a pre decorator for the endpoint '/token/init'.
    It reads the policy scope=enrollment, action=certificate_template and
    sets the API parameter "template" accordingly.

    :param request: The request to enhance
    :return: None, but we modify the request
    """
    params = request.all_data
    user_object = get_user_from_param(params)
    token_type = getParam(request.all_data, "type", optional)
    if token_type and token_type.lower() == "certificate":
        # get the CA template from the policies
        template_pols = Match.user(g, scope=SCOPE.ENROLL, action=CERTIFICATE_ACTION.CERTIFICATE_TEMPLATE,
                                   user_object=user_object).action_values(unique=True)
        if len(template_pols) == 1:
            # The policy was set, so we need to set the template in the request
            request.all_data["template"] = list(template_pols)[0]


def init_subject_components(request=None, action=None):
    """
    This is a pre decorator for the endpoint '/token/init'.
    It reads the policy scope=enrollment, action=certificate_request_subject_component and
    sets the API parameter "subject_component" accordingly.

    :param request: The request to enhance
    :return: None, but we modify the request
    """
    params = request.all_data
    user_object = get_user_from_param(params)
    token_type = getParam(request.all_data, "type", optional)
    if token_type and token_type.lower() == "certificate":
        # get the subject list from the policies
        subject_pols = Match.user(g, scope=SCOPE.ENROLL,
                                  action=CERTIFICATE_ACTION.CERTIFICATE_REQUEST_SUBJECT_COMPONENT,
                                  user_object=user_object).action_values(unique=False)
        if len(list(subject_pols)):
            # The policy was set, we need to add the list to the parameters
            request.all_data["subject_components"] = list(subject_pols)


def twostep_enrollment_activation(request=None, action=None):
    """
    This policy function enables the two-step enrollment process according
    to the configured policies.
    It is used to decorate the ``/token/init`` endpoint.

    If a ``<type>_2step`` policy matches, the ``2stepinit`` parameter is handled according to the policy.
    If no policy matches, the ``2stepinit`` parameter is removed from the request data.
    """
    user_object = get_user_from_param(request.all_data)
    serial = getParam(request.all_data, "serial", optional)
    token_type = getParam(request.all_data, "type", optional, "hotp")
    token_exists = False
    if serial:
        tokensobject_list = get_tokens(serial=serial)
        if len(tokensobject_list) == 1:
            token_type = tokensobject_list[0].token.tokentype
            token_exists = True
    token_type = token_type.lower()
    # Differentiate between an admin enrolling a token for the
    # user and a user self-enrolling a token.
    # In any case, the policy's user attribute is matched against the
    # currently logged-in user (which may be the admin or the
    # self-enrolling user).
    # Tokentypes have separate twostep actions
    action = "{}_2step".format(token_type)
    twostep_enabled_pols = Match.admin_or_user(g, action=action, user_obj=user_object).action_values(unique=True)
    if twostep_enabled_pols:
        enabled_setting = list(twostep_enabled_pols)[0]
        if enabled_setting == "allow":
            # The user is allowed to pass 2stepinit=1
            pass
        elif enabled_setting == "force":
            # We force 2stepinit to be 1 (if the token does not exist yet)
            if not token_exists:
                request.all_data["2stepinit"] = 1
        else:
            raise PolicyError("Unknown 2step policy setting: {}".format(enabled_setting))
    else:
        # If no policy matches, the user is not allowed
        # to pass 2stepinit
        # Force two-step initialization to be None
        if "2stepinit" in request.all_data:
            del request.all_data["2stepinit"]
    return True


def twostep_enrollment_parameters(request=None, action=None):
    """
    If the ``2stepinit`` parameter is set to true, this policy function
    reads additional configuration from policies and adds it
    to ``request.all_data``, that is:

     * ``{type}_2step_serversize`` is written to ``2step_serversize``
     * ``{type}_2step_clientsize`` is written to ``2step_clientsize``
     * ``{type}_2step_difficulty`` is written to ``2step_difficulty``

    If no policy matches, the value passed by the user is kept.

    This policy function is used to decorate the ``/token/init`` endpoint.
    """
    policy_object = g.policy_object
    user_object = get_user_from_param(request.all_data)
    serial = getParam(request.all_data, "serial", optional)
    token_type = getParam(request.all_data, "type", optional, "hotp")
    if serial:
        tokensobject_list = get_tokens(serial=serial)
        if len(tokensobject_list) == 1:
            token_type = tokensobject_list[0].token.tokentype
    token_type = token_type.lower()
    # Differentiate between an admin enrolling a token for the
    # user and a user self-enrolling a token.
    (role, username, userrealm, adminuser, adminrealm) = determine_logged_in_userparams(g.logged_in_user,
                                                                                         request.all_data)
    # Tokentypes have separate twostep actions
    if is_true(getParam(request.all_data, "2stepinit", optional)):
        parameters = ("2step_serversize", "2step_clientsize", "2step_difficulty")
        for parameter in parameters:
            action = "{}_{}".format(token_type, parameter)
            # SCOPE.ENROLL does not have an admin realm
            action_values = Match.generic(g, action=action,
                                          scope=SCOPE.ENROLL,
                                          user=username,
                                          realm=userrealm,
                                          user_object=request.User).action_values(unique=True)
            if action_values:
                request.all_data[parameter] = list(action_values)[0]


def verify_enrollment(request=None, action=None):
    """
    This is used to verify an already enrolled token.
    The parameter "verify" is used to do so. If successful,
    the current rollout_state "verify" of the token will be changed to "enrolled".

    :param request:
    :param action:
    :return:
    """
    serial = getParam(request.all_data, "serial", optional)
    verify = getParam(request.all_data, "verify", optional)
    if verify and serial:
        # Only now, we check if we need to verify
        tokenobj_list = get_tokens(serial=serial)
        if len(tokenobj_list) == 1:
            tokenobj = tokenobj_list[0]
            if tokenobj.rollout_state == ROLLOUTSTATE.VERIFYPENDING:
                log.debug("Verifying the token enrollment for token {0!s}.".format(serial))
                r = tokenobj.verify_enrollment(verify)
                log.info("Result of enrollment verification for token {0!s}: {1!s}".format(serial, r))
                if r:
                    tokenobj.token.rollout_state = ROLLOUTSTATE.ENROLLED
                else:
                    from privacyidea.lib.error import ParameterError
                    raise ParameterError("Verification of the new token failed.")


def check_max_token_user(request=None, action=None):
    """
    Pre Policy
    This checks the maximum token per user policy.
    Check ACTION.MAXTOKENUSER
    Check ACTION.MAXACTIVETOKENUSER

    This decorator can wrap:
        /token/init  (with a realm and user)
        /token/assign

    :param req:
    :param action:
    :return: True otherwise raises an Exception
    """
    ERROR = "The number of tokens for this user is limited!"
    ERROR_TYPE = "The number of tokens of type {0!s} for this user is limited!"
    ERROR_ACTIVE = "The number of active tokens for this user is limited!"
    ERROR_ACTIVE_TYPE = "The number of active tokens of type {0!s} for this user is limited!"
    params = request.all_data
    serial = getParam(params, "serial")
    tokentype = getParam(params, "type")
    user_object = get_user_from_param(params)
    if user_object.is_empty() and serial:
        try:
            user_object = get_token_owner(serial) or User()
        except ResourceNotFoundError:
            # in case of token init the token does not yet exist in the db
            pass
    if user_object.login:
        tokentype = getParam(params, "type")
        if not tokentype:
            if serial:
                # If we have a serial but no tokentype, we can get the tokentype from
                # the token, if it exists
                tokentype = get_token_type(serial) or "hotp"
            else:
                tokentype = "hotp"

        # check maximum number of type specific tokens of user
        limit_list = Match.user(g, scope=SCOPE.ENROLL,
                                action="{0!s}_{1!s}".format(tokentype.lower(), ACTION.MAXTOKENUSER),
                                user_object=user_object).action_values(unique=False, write_to_audit_log=False)
        if limit_list:
            # we need to check how many tokens of this specific type the user already has assigned!
            tokenobject_list = get_tokens(user=user_object, tokentype=tokentype)
            if serial and serial in [tok.token.serial for tok in tokenobject_list]:
                # If a serial is provided and this token already exists, the
                # token can be regenerated
                pass
            else:
                already_assigned_tokens = len(tokenobject_list)
                max_value = max([int(x) for x in limit_list])
                if already_assigned_tokens >= max_value:
                    g.audit_object.add_policy(limit_list.get(str(max_value)))
                    raise PolicyError(ERROR_TYPE.format(tokentype))

        # check maximum tokens of user
        limit_list = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.MAXTOKENUSER,
                                user_object=user_object).action_values(unique=False, write_to_audit_log=False)
        if limit_list:
            # we need to check how many tokens the user already has assigned!
            tokenobject_list = get_tokens(user=user_object)
            if serial and serial in [tok.token.serial for tok in tokenobject_list]:
                # If a serial is provided and this token already exists, the
                # token can be regenerated
                pass
            else:
                already_assigned_tokens = len(tokenobject_list)
                max_value = max([int(x) for x in limit_list])
                if already_assigned_tokens >= max_value:
                    g.audit_object.add_policy(limit_list.get(str(max_value)))
                    raise PolicyError(ERROR)

        # check maximum active tokens of user
        limit_list = Match.user(g, scope=SCOPE.ENROLL,
                                action="{0!s}_{1!s}".format(tokentype, ACTION.MAXACTIVETOKENUSER),
                                user_object=user_object).action_values(unique=False, write_to_audit_log=False)
        if limit_list:
            # we need to check how many active tokens the user already has assigned!
            tokenobject_list = get_tokens(user=user_object, active=True, tokentype=tokentype)
            if serial and serial in [tok.token.serial for tok in tokenobject_list]:
                # If a serial is provided and this token already exists, the
                # token can be regenerated
                pass
            else:
                already_assigned_tokens = len(tokenobject_list)
                max_value = max([int(x) for x in limit_list])
                if already_assigned_tokens >= max_value:
                    g.audit_object.add_policy(limit_list.get(str(max_value)))
                    raise PolicyError(ERROR_ACTIVE_TYPE.format(tokentype))

        # check maximum active tokens of user
        limit_list = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.MAXACTIVETOKENUSER,
                                user_object=user_object).action_values(unique=False, write_to_audit_log=False)
        if limit_list:
            # we need to check how many active tokens the user already has assigned!
            tokenobject_list = get_tokens(user=user_object, active=True)
            if serial and serial in [tok.token.serial for tok in tokenobject_list]:
                # If a serial is provided and this token already exists (and is active), the
                # token can be regenerated. If the token would be inactive, regenerating this
                # token would reactivate it and thus the user would have more tokens!
                pass
            else:
                already_assigned_tokens = len(tokenobject_list)
                max_value = max([int(x) for x in limit_list])
                if already_assigned_tokens >= max_value:
                    g.audit_object.add_policy(limit_list.get(str(max_value)))
                    raise PolicyError(ERROR_ACTIVE)

    return True


def check_max_token_realm(request=None, action=None):
    """
    Pre Policy
    This checks the maximum token per realm.
    Check ACTION.MAXTOKENREALM

    This decorator can wrap:
        /token/init  (with a realm and user)
        /token/assign
        /token/tokenrealms

    :param req: The request that is intercepted during the API call
    :type req: Request Object
    :param action: An optional Action
    :type action: basestring
    :return: True otherwise raises an Exception
    """
    ERROR = "The number of tokens in this realm is limited!"
    params = request.all_data
    user_object = get_user_from_param(params)
    if user_object:
        realm = user_object.realm
    else:  # pragma: no cover
        realm = params.get("realm")

    if realm:
        limit_list = Match.realm(g, scope=SCOPE.ENROLL, action=ACTION.MAXTOKENREALM,
                                 realm=realm).action_values(unique=False, write_to_audit_log=False)
        if limit_list:
            # we need to check how many tokens the realm already has assigned!
            tokenobject_list = get_tokens(realm=realm)
            already_assigned_tokens = len(tokenobject_list)
            max_value = max([int(x) for x in limit_list])
            if already_assigned_tokens >= max_value:
                g.audit_object.add_policy(limit_list.get(str(max_value)))
                raise PolicyError(ERROR)
    return True


def set_realm(request=None, action=None):
    """
    Pre Policy
    This pre condition gets the current realm and verifies if the realm
    should be rewritten due to the policy definition.
    I takes the realm from the request and - if a policy matches - replaces
    this realm with the realm defined in the policy

    Check ACTION.SETREALM

    This decorator should wrap
        /validate/check

    :param request: The request that is intercepted during the API call
    :type request: Request Object
    :param action: An optional Action
    :type action: basestring
    :returns: Always true. Modified the parameter request
    """
    # At the moment a realm parameter with no user parameter returns a user
    # object like "@realm". If this is changed one day, we need to also fetch
    #  the realm
    if request.User and request.User.login:
        user_object = request.User
        username = user_object.login
        policy_match = Match.user(g, scope=SCOPE.AUTHZ, action=ACTION.SETREALM,
                                  user_object=user_object)
        new_realm = policy_match.action_values(unique=False)
        if len(new_realm) > 1:
            raise PolicyError("I do not know, to which realm I should set the "
                              "new realm. Conflicting policies exist.")
        elif len(new_realm) == 1:
            # There is one specific realm, which we set in the request
            request.all_data["realm"] = list(new_realm)[0]
            # We also need to update the user
            request.User = User(username, request.all_data["realm"])

    return True


def required_email(request=None, action=None):
    """
    This precondition checks if the "email" parameter matches the regular
    expression in the policy scope=register, action=requiredemail.
    See :ref:`policy_requiredemail`.

    Check ACTION.REQUIREDEMAIL

    This decorator should wrap POST /register

    :param request: The Request Object
    :param action: An optional Action
    :return: Modifies the request parameters or raises an Exception
    """
    email = getParam(request.all_data, "email")
    email_found = False
    email_pols = Match.action_only(g, scope=SCOPE.REGISTER, action=ACTION.REQUIREDEMAIL).action_values(unique=False)
    if email and email_pols:
        for email_pol in email_pols:
            # The policy is only "/regularexpr/".
            search = email_pol.strip("/")
            if re.findall(search, email):
                email_found = True
        if not email_found:
            raise RegistrationError("This email address is not allowed to "
                                    "register!")

    return True


def check_custom_user_attributes(request=None, action=None):
    """
    This pre condition checks for the policies delete_custom_user_attributes and
    set_custom_user_attributes, if the user or admin is allowed to set or deleted
    the requested attribute.

    It decorates POST /user/attribute and DELETE /user/attribute/...

    :param request: The request that is intercepted during the API call
    :type request: Request Object
    :param action: An optional action, (would be set/delete)
    :return: Raises a PolicyError, if the wrong attribute is given.
    """
    ERROR = "You are not allowed to {0!s} the custom user attribute {1!s}!"
    is_allowed = False
    if action == "delete":
        attr_pol_dict = Match.admin_or_user(g, action=ACTION.DELETE_USER_ATTRIBUTES,
                                            user_obj=request.User).action_values(unique=False,
                                                                                 allow_white_space_in_action=True)
        attr_key = request.all_data.get("attrkey")
        for attr_pol_val in attr_pol_dict:
            attr_pol_list = [x.strip() for x in attr_pol_val.strip().split() if x]
            if attr_key in attr_pol_list or "*" in attr_pol_list:
                is_allowed = True
                break
        if is_allowed:
            g.audit_object.add_policy(attr_pol_dict.get(attr_pol_val))
        else:
            raise PolicyError(ERROR.format(action, attr_key))
    elif action == "set":
        attr_pol_dict = Match.admin_or_user(g, action=ACTION.SET_USER_ATTRIBUTES,
                                            user_obj=request.User).action_values(unique=False,
                                                                                 allow_white_space_in_action=True)
        attr_key = request.all_data.get("key")
        attr_value = request.all_data.get("value")
        for pol_string in attr_pol_dict:
            pol_dict = parse_string_to_dict(pol_string)
            if attr_value in pol_dict.get(attr_key, []):
                # It is allowed to set the key to this value
                is_allowed = True
                break
            if attr_value in pol_dict.get("*", []):
                # this value can be set in any key
                is_allowed = True
                break
            if "*" in pol_dict.get(attr_key, []):
                # This key can be set to any value
                is_allowed = True
                break
            if "*" in pol_dict.get("*", []):
                # Any key can be set to any value
                is_allowed = True
                break
        if is_allowed:
            g.audit_object.add_policy(attr_pol_dict.get(pol_string))
        else:
            raise PolicyError(ERROR.format(action, attr_key))


def auditlog_age(request=None, action=None):
    """
    This pre condition checks for the policy auditlog_age and set the
    "timelimit" parameter of the audit search API.

    Check ACTION.AUDIT_AGE

    The decorator can wrap GET /audit/

    :param request: The request that is intercepted during the API call
    :type request: Request Object
    :param action: An optional Action
    :type action: basestring
    :returns: Always true. Modified the parameter request
    """
    audit_age = Match.admin_or_user(g, action=ACTION.AUDIT_AGE, user_obj=request.User).action_values(unique=True)
    timelimit = None
    timelimit_s = None
    for aa in audit_age:
        if not timelimit:
            timelimit_s = aa
            timelimit = parse_timedelta(timelimit_s)
        else:
            # We will use the longest allowed timelimit
            if parse_timedelta(aa) > timelimit:
                timelimit_s = aa
                timelimit = parse_timedelta(timelimit_s)

        log.debug("auditlog_age: {0!s}".format(timelimit_s))
        request.all_data["timelimit"] = timelimit_s

    return True


def hide_audit_columns(request=None, action=None):
    """
    This pre condition checks for the policy hide_audit_columns and sets the
    "hidden_columns" parameter for the audit search. The given columns will be
    removed from the returned audit dict.

    Check ACTION.HIDE_AUDIT_COLUMNS

    The decorator should wrap GET /audit/

    :param request: The request that is intercepted during the API call
    :type request: Request Object
    :param action: An optional Action
    :type action: basestring
    :returns: Always true. Modified the parameter request
    """
    hidden_columns = Match.admin_or_user(g, action=ACTION.HIDE_AUDIT_COLUMNS,
                                         user_obj=request.User).action_values(unique=False)
    request.all_data["hidden_columns"] = list(hidden_columns)

    return True


def mangle(request=None, action=None):
    """
    This pre condition checks if either of the parameters pass, user or realm
    in a validate/check request should be rewritten based on an
    authentication policy with action "mangle".
    See :ref:`policy_mangle` for an example.

    Check ACTION.MANGLE

    This decorator should wrap
        /validate/check

    :param request: The request that is intercepted during the API call
    :type request: Request Object
    :param action: An optional Action
    :type action: basestring
    :returns: Always true. Modified the parameter request
    """
    user_object = request.User

    mangle_pols = Match.user(g, scope=SCOPE.AUTH, action=ACTION.MANGLE,
                             user_object=user_object).action_values(unique=False, write_to_audit_log=False)
    # We can have several mangle policies! One for user, one for realm and
    # one for pass. So we do no checking here.
    for mangle_pol_action in mangle_pols:
        # mangle_pol_action looks like this:
        # keyword/search/replace/. Where "keyword" can be "user", "pass" or
        # "realm".
        mangle_key, search, replace, _rest = mangle_pol_action.split("/", 3)
        mangle_value = request.all_data.get(mangle_key)
        if mangle_value:
            log.debug("mangling authentication data: {0!s}".format(mangle_key))
            request.all_data[mangle_key] = re.sub(search, replace,
                                                  mangle_value)
            # If we mangled something, we add the name of the policies
            g.audit_object.add_policy(mangle_pols.get(mangle_pol_action))
            if mangle_key in ["user", "realm"]:
                request.User = get_user_from_param(request.all_data)
    return True


def check_anonymous_user(request=None, action=None):
    """
    This decorator function takes the request and verifies the given action
    for the SCOPE USER without an authenticated user but the user from the
    parameters.

    This is used with password_reset

    :param request:
    :param action:
    :return: True otherwise raises an Exception
    """
    ERROR = "User actions are defined, but this action is not allowed!"
    params = request.all_data
    policy_object = g.policy_object
    user_obj = get_user_from_param(params)

    action_allowed = Match.user(g, scope=SCOPE.USER, action=action, user_object=user_obj).allowed()
    if not action_allowed:
        raise PolicyError(ERROR)
    return True


def check_admin_tokenlist(request=None, action=None):
    """
    Depending on the policy scope=admin, action=tokenlist, the
    allowed_realms parameter is set to define, the token of which
    realms and administrator is allowed to see.

    Sets the allowed_realms
    None: means the admin has no restrictions
    []: the admin can not see any realms
    ["realm1", "realm2"...]: the admin can see these realms

    :param request:
    :return:
    """
    allowed_realms = None
    wildcard = False
    role = g.logged_in_user.get("role")
    if role == ROLE.USER:
        return True

    policy_object = g.policy_object
    pols = Match.admin(g, action=ACTION.TOKENLIST).policies()
    pols_at_all = policy_object.list_policies(scope=SCOPE.ADMIN, active=True)

    if pols_at_all:
        allowed_realms = []
        for pol in pols:
            if not pol.get("realm"):
                # if there is no realm set in a tokenlist policy, then this is a wildcard!
                wildcard = True
            else:
                allowed_realms.extend(pol.get("realm"))

        if wildcard:
            allowed_realms = None

    request.pi_allowed_realms = allowed_realms
    return True


def check_base_action(request=None, action=None, anonymous=False):
    """
    This decorator function takes the request and verifies the given action
    for the SCOPE ADMIN or USER.

    :param request:
    :param action:
    :param anonymous: If set to True, the user data is taken from the request
                      parameters.
    :return: True otherwise raises an Exception
    """
    ERROR = {"user": "User actions are defined, but the action %s is not "
                     "allowed!" % action,
             "admin": "Admin actions are defined, but the action %s is not "
                      "allowed!" % action}
    params = request.all_data
    user_object = request.User
    resolver = user_object.resolver if user_object else None
    (role, username, realm, adminuser, adminrealm) = determine_logged_in_userparams(g.logged_in_user, params)

    # In certain cases we can not resolve the user by the serial!
    if action is ACTION.AUDIT:
        # In case of audit requests, the parameters "realm" and "user" are used for
        # filtering the audit log. So these values must not be taken from the request parameters,
        # but rather be NONE. The restriction for the allowed realms in the audit log is determined
        # in the decorator "allowed_audit_realm".
        realm = username = resolver = None
    else:
        realm = params.get("realm")
        if type(realm) == list and len(realm) == 1:
            realm = realm[0]
        resolver = resolver or params.get("resolver")
        # get the realm by the serial:
        if not realm and params.get("serial"):
            realm = get_realms_of_token(params.get("serial"),
                                        only_first_realm=True)

    # In this case we do not pass the user_object, since the realm is also determined
    # by the pure serial number given.
    action_allowed = Match.generic(g, scope=role,
                                   action=action,
                                   user=username,
                                   resolver=resolver,
                                   realm=realm,
                                   adminrealm=adminrealm,
                                   adminuser=adminuser).allowed()
    if not action_allowed:
        raise PolicyError(ERROR.get(role))
    return True


def check_token_upload(request=None, action=None):
    """
    This decorator function takes the request and verifies the given action
    for scope ADMIN
    :param req:
    :param filename:
    :return:
    """
    tokenrealms = request.all_data.get("tokenrealms")
    upload_allowed = True
    if tokenrealms:
        for trealm in tokenrealms.split(","):
            if not Match.generic(g, scope=SCOPE.ADMIN, action=ACTION.IMPORT,
                                 adminuser=g.logged_in_user.get("username"),
                                 adminrealm=g.logged_in_user.get("realm"), realm=trealm).allowed():
                upload_allowed = False
    else:
        upload_allowed = Match.generic(g, scope=SCOPE.ADMIN, action=ACTION.IMPORT,
                                       adminuser=g.logged_in_user.get("username"),
                                       adminrealm=g.logged_in_user.get("realm")).allowed()
    if not upload_allowed:
        raise PolicyError("Admin actions are defined, but you are not allowed to upload token files.")
    return True


def check_token_init(request=None, action=None):
    """
    This decorator function takes the request and verifies
    if the requested tokentype is allowed to be enrolled in the SCOPE ADMIN
    or the SCOPE USER.
    :param request:
    :param action:
    :return: True or an Exception is raised
    """
    ERROR = {"user": "User actions are defined, you are not allowed to "
                     "enroll this token type!",
             "admin": "Admin actions are defined, but you are not allowed to "
                      "enroll this token type!"}
    params = request.all_data
    resolver = request.User.resolver if request.User else None
    (role, username, userrealm, adminuser, adminrealm) = determine_logged_in_userparams(g.logged_in_user, params)
    tokentype = params.get("type", "HOTP")
    action = "enroll{0!s}".format(tokentype.upper())
    init_allowed = Match.generic(g, action=action,
                                 user=username,
                                 resolver=resolver,
                                 realm=userrealm,
                                 scope=role,
                                 adminrealm=adminrealm,
                                 adminuser=adminuser,
                                 user_object=request.User).allowed()
    if not init_allowed:
        raise PolicyError(ERROR.get(role))
    return True


def check_external(request=None, action="init"):
    """
    This decorator is a hook to an external check function, that is called
    before the token/init or token/assign API.

    :param request: The REST request
    :type request: flask Request object
    :param action: This is either "init" or "assign"
    :type action: basestring
    :return: either True or an Exception is raised
    """
    function_name = None
    module = None
    try:
        module_func = current_app.config.get("PI_INIT_CHECK_HOOK")
        if module_func:
            module_name = ".".join(module_func.split(".")[:-1])
            module = importlib.import_module(module_name)
            function_name = module_func.split(".")[-1]
    except Exception as exx:
        log.error("Error importing external check function: {0!s}".format(exx))

    # Import of function was successful
    if function_name:
        external_func = getattr(module, function_name)
        external_func(request, action)
    return True


def api_key_required(request=None, action=None):
    """
    This is a decorator for check_user_pass and check_serial_pass.
    It checks, if a policy scope=auth, action=apikeyrequired is set.
    If so, the validate request will only performed, if a JWT token is passed
    with role=validate.
    """
    user_object = request.User

    # Get the policies
    action = Match.user(g, scope=SCOPE.AUTHZ, action=ACTION.APIKEY, user_object=user_object).policies()
    # Do we have a policy?
    if action:
        # check if we were passed a correct JWT
        # Get the Authorization token from the header
        auth_token = request.headers.get('PI-Authorization')
        if not auth_token:
            auth_token = request.headers.get('Authorization')
        try:
            r = jwt.decode(auth_token, current_app.secret_key, algorithms=['HS256'])
            g.logged_in_user = {"username": r.get("username", ""),
                                "realm": r.get("realm", ""),
                                "role": r.get("role", "")}
        except (AttributeError, jwt.DecodeError):
            # PyJWT 1.3.0 raises AttributeError, PyJWT 1.6.4 raises DecodeError.
            raise PolicyError("No valid API key was passed.")

        role = g.logged_in_user.get("role")
        if role != ROLE.VALIDATE:
            raise PolicyError("A correct JWT was passed, but it was no API "
                              "key.")

    # If everything went fine, we call the original function
    return True


def mock_success(req, action):
    """
    This is a mock function as an example for check_external. This function
    returns success and the API call will go on unmodified.
    """
    return True


def mock_fail(req, action):
    """
    This is a mock function as an example for check_external. This function
    creates a problem situation and the token/init or token/assign will show
    this exception accordingly.
    """
    raise Exception("This is an Exception in an external check function")


def is_remote_user_allowed(req, write_to_audit_log=True):
    """
    Checks if the REMOTE_USER server variable is allowed to be used.

    .. note:: This is not used as a decorator!

    :param req: The flask request, containing the remote user and the client IP
    :param write_to_audit_log: whether the policy name should be added to the audit log entry
    :type write_to_audit_log: bool
    :return: Return a value or REMOTE_USER, can be "disable", "active" or "force".
    :rtype: str
    """
    if req.remote_user:
        loginname, realm = split_user(req.remote_user)
        realm = realm or get_default_realm()
        ruser_active = Match.generic(g, scope=SCOPE.WEBUI,
                                     action=ACTION.REMOTE_USER,
                                     user=loginname,
                                     realm=realm).action_values(unique=False,
                                                                write_to_audit_log=write_to_audit_log)
        # there should be only one action value here
        if ruser_active:
            return list(ruser_active)[0]

    # Return default "disable"
    return REMOTE_USER.DISABLE


def save_client_application_type(request, action):
    """
    This decorator is used to write the client IP and the HTTP user agent (
    clienttype) to the database.

    In fact this is not a **policy** decorator, as it checks no policy. In
    fact, we could however one day
    define this as a policy, too.
    :param req:
    :return:
    """
    # retrieve the IP. This will also be the mapped IP!
    client_ip = g.client_ip or "0.0.0.0"  # nosec B104 # default IP if no IP in request
    # ...and the user agent.
    ua = request.user_agent
    save_clientapplication(client_ip, "{0!s}".format(ua) or "unknown")
    return True


def pushtoken_disable_wait(request, action):
    """
    This is used for the /auth endpoint and sets the
    PUSH_ACTION.WAIT parameter to False.

    :param request:
    :param action:
    :return:
    """
    request.all_data[PUSH_ACTION.WAIT] = False


def pushtoken_wait(request, action):
    """
    This is a auth specific wrapper to decorate /validate/check
    According to the policy scope=SCOPE.AUTH, action=push_wait

    :param request:
    :param action:
    :return:
    """
    user_object = request.User
    waiting = Match.user(g, scope=SCOPE.AUTH, action=PUSH_ACTION.WAIT,
                         user_object=user_object if user_object else None)\
        .action_values(unique=True, allow_white_space_in_action=True)
    if len(waiting) >= 1:
        request.all_data[PUSH_ACTION.WAIT] = int(list(waiting)[0])
    else:
        request.all_data[PUSH_ACTION.WAIT] = False


def pushtoken_add_config(request, action):
    """
    This is a token specific wrapper for push token for the endpoint
    /token/init
    According to the policy scope=SCOPE.ENROLL,
    action=SSL_VERIFY or action=FIREBASE_CONFIG the parameters are added to the
    enrollment step.
    :param request:
    :param action:
    :return:
    """
    ttype = request.all_data.get("type")
    if ttype and ttype.lower() == "push":
        request.all_data = get_pushtoken_add_config(g, request.all_data, request.User)


def u2ftoken_verify_cert(request, action):
    """
    This is a token specific wrapper for u2f token for the endpoint
    /token/init
    According to the policy scope=SCOPE.ENROLL,
    action=U2FACTION.NO_VERIFY_CERT it can add a parameter to the
    enrollment parameters to not verify the attestation certificate.
    The default is to verify the cert.
    :param request:
    :param action:
    :return:
    """
    # Get the registration data of the 2nd step of enrolling a U2F device
    ttype = request.all_data.get("type")
    if ttype and ttype.lower() == "u2f":
        # Add the default to verify the cert.
        request.all_data["u2f.verify_cert"] = True
        user_object = request.User
        do_not_verify_the_cert = Match.user(g, scope=SCOPE.ENROLL, action=U2FACTION.NO_VERIFY_CERT,
                                            user_object=user_object if user_object else None).policies()
        if do_not_verify_the_cert:
            request.all_data["u2f.verify_cert"] = False

        log.debug("Should we not verify the attestation certificate? "
                  "Policies: {0!s}".format(do_not_verify_the_cert))
    return True


def u2ftoken_allowed(request, action):
    """
    This is a token specific wrapper for u2f token for the endpoint
     /token/init.
     According to the policy scope=SCOPE.ENROLL,
     action=U2FACTION.REQ it checks, if the assertion certificate is an
     allowed U2F token type.

     If the token, which is enrolled contains a non allowed attestation
     certificate, we bail out.

    :param request:
    :param action:
    :return:
    """

    ttype = request.all_data.get("type")

    # Get the registration data of the 2nd step of enrolling a U2F device
    reg_data = request.all_data.get("regdata")

    if ttype and ttype.lower() == "u2f" and reg_data:
        # We have a registered u2f device!
        serial = request.all_data.get("serial")

        # We just check, if the issuer is allowed, not if the certificate
        # is still valid! (verify_cert=False)
        attestation_cert, user_pub_key, key_handle, \
        signature, description = parse_registration_data(reg_data,
                                                         verify_cert=False)

        allowed_certs_pols = Match.user(g, scope=SCOPE.ENROLL, action=U2FACTION.REQ,
                                        user_object=request.User if request.User else None)\
            .action_values(unique=False)

        if len(allowed_certs_pols) and not _attestation_certificate_allowed(attestation_cert, allowed_certs_pols):
            log.warning("The U2F device {0!s} is not "
                        "allowed to be registered due to policy "
                        "restriction".format(
                serial))
            raise PolicyError("The U2F device is not allowed "
                              "to be registered due to policy "
                              "restriction.")
            # TODO: Maybe we should delete the token, as it is a not
            # usable U2F token, now.

    return True


def allowed_audit_realm(request=None, action=None):
    """
    This decorator function takes the request and adds additional parameters
    to the request according to the policy
    for the SCOPE.ADMIN or ACTION.AUDIT
    :param request:
    :param action:
    :return: True
    """
    # The endpoint is accessible to users, but we only set ``allowed_audit_realm``
    # for admins, as users are only allowed to view their own realm anyway (this
    # is ensured by the fixed "realm" parameter)
    if g.logged_in_user["role"] == ROLE.ADMIN:
        pols = Match.admin(g, action=ACTION.AUDIT).policies()
        if pols:
            # get all values in realm:
            allowed_audit_realms = []
            for pol in pols:
                if pol.get("realm"):
                    allowed_audit_realms += pol.get("realm")
            request.all_data["allowed_audit_realm"] = list(set(
                allowed_audit_realms))

    return True


def indexedsecret_force_attribute(request, action):
    """
    This is a token specific wrapper for indexedsecret token for the endpoint
    /token/init
    The otpkey is overwritten with the value from
    the user attribute specified in
    policy scope=SCOPE.USER and SCOPE.ADMIN,
    action=PIIXACTION.FORCE_ATTRIBUTE.
    :param request:
    :param action:
    :return:
    """
    ttype = request.all_data.get("type")
    if ttype and ttype.lower() == "indexedsecret" and request.User:
        # We only need to check the policies, if the token is actually enrolled
        # to a user.
        attributes = Match.admin_or_user(g, "indexedsecret_{0!s}".format(PIIXACTION.FORCE_ATTRIBUTE),
                                         user_obj=request.User).action_values(unique=True)
        if not attributes:
            # If there is no policy set, we simply do nothing
            return True

        attribute_value = request.User.info.get(list(attributes)[0])
        request.all_data["otpkey"] = attribute_value

    return True


def webauthntoken_request(request, action):
    """
    This is a WebAuthn token specific wrapper for all endpoints using WebAuthn tokens.

    This wraps the endpoints /token/init, /validate/triggerchallenge, /auth, and
    /validate/check. It will add WebAuthn configuration information to the
    requests, wherever a piece of information is needed for several different
    requests and thus cannot be provided by one of the more specific wrappers
    without adding unnecessary redundancy.

    Depending on the type of request, the request will be augmented with some
    (or all) of the authenticator timeout, user verification requirement and
    list of allowed AAGUIDs for the current scope, as specified by the
    policies with the determined scope and the actions WEBAUTHNACTION.TIMEOUT,
    WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT, and
    WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST, respectively.

    The value of the ORIGIN http header will also be added to the request for
    the ENROLL and AUTHZ scopes. This is to make the unit tests not require
    mocking.

    :param request:
    :type request:
    :param action:
    :type action:
    :return:
    :rtype:
    """

    webauthn = False
    scope = None

    # Check if this is an enrollment request for a WebAuthn token.
    ttype = request.all_data.get("type")
    if ttype and ttype.lower() == WebAuthnTokenClass.get_class_type():
        webauthn = True
        scope = SCOPE.ENROLL

    # Check if a WebAuthn token is being authorized.
    if is_webauthn_assertion_response(request.all_data):
        webauthn = True
        scope = SCOPE.AUTHZ

    # Check if this is an auth request (as opposed to an enrollment), and it
    # is not a WebAuthn authorization, and the request is either for
    # authentication with a WebAuthn token, or not for any particular token at
    # all (since authentication requests contain almost no parameters, it is
    # necessary to define them by what they are not, rather than by what they
    # are).
    #
    # This logic means that we will add WebAuthn specific information to any
    # unspecific authentication request, even if the user does not actually
    # have any WebAuthn tokens enrolled, but  since this decorator is entirely
    # passive and will just pull values from policies and add them to properly
    # prefixed fields in the request data, this is not a problem.
    if not request.all_data.get("type") \
            and not is_webauthn_assertion_response(request.all_data) \
            and ('serial' not in request.all_data
                or request.all_data['serial'].startswith(WebAuthnTokenClass.get_class_prefix())):
        webauthn = True
        scope = SCOPE.AUTH

    # If this is a WebAuthn token, or an authentication request for no particular token.
    if webauthn:
        actions = WebAuthnTokenClass.get_class_info('policy').get(scope)

        if WEBAUTHNACTION.TIMEOUT in actions:
            timeout_policies = Match \
                .user(g,
                      scope=scope,
                      action=WEBAUTHNACTION.TIMEOUT,
                      user_object=request.User if hasattr(request, 'User') else None) \
                .action_values(unique=True)
            timeout = int(list(timeout_policies)[0]) if timeout_policies else DEFAULT_TIMEOUT

            request.all_data[WEBAUTHNACTION.TIMEOUT] \
                = timeout * 1000

        if WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT in actions:
            user_verification_requirement_policies = Match \
                .user(g,
                      scope=scope,
                      action=WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT,
                      user_object=request.User if hasattr(request, 'User') else None) \
                .action_values(unique=True)
            user_verification_requirement = list(user_verification_requirement_policies)[0] \
                if user_verification_requirement_policies \
                else DEFAULT_USER_VERIFICATION_REQUIREMENT
            if user_verification_requirement not in USER_VERIFICATION_LEVELS:
                raise PolicyError(
                    "{0!s} must be one of {1!s}"
                        .format(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT,
                                ", ".join(USER_VERIFICATION_LEVELS)))

            request.all_data[WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT] \
                = user_verification_requirement

        if WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST in actions:
            allowed_aaguids_pols = Match \
                .user(g,
                      scope=scope,
                      action=WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST,
                      user_object=request.User if hasattr(request, 'User') else None) \
                .action_values(unique=False,
                               allow_white_space_in_action=True)
            allowed_aaguids = set(
                aaguid
                for allowed_aaguid_pol in allowed_aaguids_pols
                for aaguid in allowed_aaguid_pol.split()
            )

            if allowed_aaguids:
                request.all_data[WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST] \
                    = list(allowed_aaguids)

        request.all_data['HTTP_ORIGIN'] = request.environ.get('HTTP_ORIGIN')

    return True


def webauthntoken_authz(request, action):
    """
    This is a WebAuthn token specific wrapper for the /auth, and /validate/check endpoints.

    This will enrich the authorization request for WebAuthn tokens with the
    necessary configuration information from policy actions with
    scope=SCOPE.AUTHZ. This is currently the authorization pendant to
    webauthntoken_allowed(), but maybe expanded to cover other authorization
    policies in the future, should any be added. The request will as of now
    simply be augmented with the policies the attestation certificate is to be
    matched against.

    :param request:
    :type request:
    :param action:
    :type action:
    :return:
    :rtype:
    """

    # If a WebAuthn token is being authorized.
    if is_webauthn_assertion_response(request.all_data):
        allowed_certs_pols = Match\
            .user(g,
                  scope=SCOPE.AUTHZ,
                  action=WEBAUTHNACTION.REQ,
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=False)

        request.all_data[WEBAUTHNACTION.REQ] \
            = list(allowed_certs_pols)

    return True


def webauthntoken_auth(request, action):
    """
    This is a WebAuthn token specific wrapper for the endpoints /validate/triggerchallenge,
    /validate/check, and /auth.

    This will enrich the challenge creation request for WebAuthn tokens with the
    necessary configuration information from policy actions with
    scope=SCOPE.AUTH. The request will be augmented with the allowed
    transports and the text to display to the user when asking to confirm
    the challenge on the token, as specified by the actions
    WEBAUTHNACTION.ALLOWED_TRANSPORTS, and ACTION.CHALLENGETEXT, respectively.

    Both of these policies are optional, and have sensible defaults.

    :param request:
    :type request:
    :param action:
    :type action:
    :return:
    :rtype:
    """

    # Check if this is an auth request (as opposed to an enrollment), and it
    # is not a WebAuthn authorization, and the request is either for
    # authentication with a WebAuthn token, or not for any particular token at
    # all (since authentication requests contain almost no parameters, it is
    # necessary to define them by what they are not, rather than by what they
    # are).
    #
    # This logic means that we will add WebAuthn specific information to any
    # unspecific authentication request, even if the user does not actually
    # have any WebAuthn tokens enrolled, but  since this decorator is entirely
    # passive and will just pull values from policies and add them to properly
    # prefixed fields in the request data, this is not a problem.
    if not request.all_data.get("type") \
            and not is_webauthn_assertion_response(request.all_data) \
            and ('serial' not in request.all_data
                 or request.all_data['serial'].startswith(WebAuthnTokenClass.get_class_prefix())):
        allowed_transports_policies = Match\
            .user(g,
                  scope=SCOPE.AUTH,
                  action=WEBAUTHNACTION.ALLOWED_TRANSPORTS,
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=False,
                           allow_white_space_in_action=True)
        allowed_transports = set(
            transport
            for allowed_transports_policy in (
                list(allowed_transports_policies)
                if allowed_transports_policies
                else [DEFAULT_ALLOWED_TRANSPORTS]
            )
            for transport in allowed_transports_policy.split()
        )

        challengetext_policies = Match\
            .user(g,
                  scope=SCOPE.AUTH,
                  action="{0!s}_{1!s}".format(WebAuthnTokenClass.get_class_type(), ACTION.CHALLENGETEXT),
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=True,
                           allow_white_space_in_action=True,
                           write_to_audit_log=False)
        challengetext = list(challengetext_policies)[0] \
            if challengetext_policies \
            else DEFAULT_CHALLENGE_TEXT_AUTH

        request.all_data[WEBAUTHNACTION.ALLOWED_TRANSPORTS] \
            = list(allowed_transports)
        request.all_data["{0!s}_{1!s}".format(WebAuthnTokenClass.get_class_type(), ACTION.CHALLENGETEXT)] \
            = challengetext

    return True


def webauthntoken_enroll(request, action):
    """
    This is a token specific wrapper for the WebAuthn token for the endpoint /token/init.

    This will enrich the initialization request for WebAuthn tokens with the
    necessary configuration information from policy actions with
    scope=SCOPE.ENROLL. The request will be augmented with a name and id for
    the relying party, as specified by the with actions
    WEBAUTHNACTION.RELYING_PARTY_NAME and WEBAUTHNACTION.RELYING_PARTY_ID,
    respectively, authenticator attachment preference, public key credential
    algorithm preferences, authenticator attestation requirement level,
    authenticator attestation requirement form, allowed AAGUIDs, and the text
    to display to the user when asking to confirm the challenge on the token,
    as specified by the actions WEBAUTHNACTION.AUTHENTICATOR_ATTACHMENT,
    WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE,
    WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL,
    WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM,
    WEAUTHNACTION.AVOID_DOUBLE_REGISTRATION,
    WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST, and
    ACTION.CHALLENGETEXT, respectively.

    Setting WEBAUTHNACTION.RELYING_PARTY_NAME and
    WEBAUTHNACTION.RELYING_PARTY_ID is mandatory, and if either of these is not
    set, we bail out.

    :param request:
    :type request:
    :param action:
    :type action:
    :return:
    :rtype:
    """

    ttype = request.all_data.get("type")
    if ttype and ttype.lower() == WebAuthnTokenClass.get_class_type():
        rp_id_policies = Match\
            .user(g,
                  scope=SCOPE.ENROLL,
                  action=WEBAUTHNACTION.RELYING_PARTY_ID,
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=True)
        if rp_id_policies:
            rp_id = list(rp_id_policies)[0]
        else:
            raise PolicyError("Missing enrollment policy for WebauthnToken: " + WEBAUTHNACTION.RELYING_PARTY_ID)

        rp_name_policies = Match\
            .user(g,
                  scope=SCOPE.ENROLL,
                  action=WEBAUTHNACTION.RELYING_PARTY_NAME,
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=True,
                           allow_white_space_in_action=True)
        if rp_name_policies:
            rp_name = list(rp_name_policies)[0]
        else:
            raise PolicyError("Missing enrollment policy for WebauthnToken: " + WEBAUTHNACTION.RELYING_PARTY_NAME)

        # The RP ID is a domain name and thus may not contain any punctuation except '-' and '.'.
        if not is_fqdn(rp_id):
            log.warning(
                "Illegal value for {0!s} (must be a domain name): {1!s}"
                    .format(WEBAUTHNACTION.RELYING_PARTY_ID, rp_id))
            raise PolicyError(
                "Illegal value for {0!s} (must be a domain name)."
                    .format(WEBAUTHNACTION.RELYING_PARTY_ID))

        authenticator_attachment_policies = Match\
            .user(g,
                  scope=SCOPE.ENROLL,
                  action=WEBAUTHNACTION.AUTHENTICATOR_ATTACHMENT,
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=True)
        authenticator_attachment = list(authenticator_attachment_policies)[0] \
            if authenticator_attachment_policies \
               and list(authenticator_attachment_policies)[0] in AUTHENTICATOR_ATTACHMENT_TYPES \
            else None

        # we need to set `unique` to False since this policy can contain multiple values
        public_key_credential_algorithm_pref_policies = Match.user(
            g,
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS,
            user_object=request.User if hasattr(request, 'User') else None
        ).action_values(unique=False)
        public_key_credential_algorithm_pref = public_key_credential_algorithm_pref_policies.keys() \
            if public_key_credential_algorithm_pref_policies \
            else DEFAULT_PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE
        if not all([x in PUBLIC_KEY_CREDENTIAL_ALGORITHMS for x in public_key_credential_algorithm_pref]):
            raise PolicyError(
                "{0!s} must be one of {1!s}"
                    .format(WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS,
                            ', '.join(PUBLIC_KEY_CREDENTIAL_ALGORITHMS.keys())))

        authenticator_attestation_level_policies = Match\
            .user(g,
                  scope=SCOPE.ENROLL,
                  action=WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL,
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=True)
        authenticator_attestation_level = list(authenticator_attestation_level_policies)[0] \
            if authenticator_attestation_level_policies \
            else DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL
        if authenticator_attestation_level not in ATTESTATION_LEVELS:
            raise PolicyError(
                "{0!s} must be one of {1!s}".format(WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL,
                                                    ', '.join(ATTESTATION_LEVELS)))

        authenticator_attestation_form_policies = Match\
            .user(g,
                  scope=SCOPE.ENROLL,
                  action=WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM,
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=True)
        authenticator_attestation_form = list(authenticator_attestation_form_policies)[0] \
            if authenticator_attestation_form_policies \
            else DEFAULT_AUTHENTICATOR_ATTESTATION_FORM
        if authenticator_attestation_form not in ATTESTATION_FORMS:
            raise PolicyError(
                "{0!s} must be one of {1!s}".format(WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM,
                                                    ', '.join(ATTESTATION_FORMS)))

        challengetext_policies = Match\
            .user(g,
                  scope=SCOPE.ENROLL,
                  action="{0!s}_{1!s}".format(WebAuthnTokenClass.get_class_type(), ACTION.CHALLENGETEXT),
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=True,
                           allow_white_space_in_action=True,
                           write_to_audit_log=False)
        challengetext = list(challengetext_policies)[0] \
            if challengetext_policies \
            else DEFAULT_CHALLENGE_TEXT_ENROLL

        avoid_double_registration_policy = Match\
            .user(g,
                  scope=SCOPE.ENROLL,
                  action=WEBAUTHNACTION.AVOID_DOUBLE_REGISTRATION,
                  user_object=request.User if hasattr(request, 'User') else None).any()

        request.all_data[WEBAUTHNACTION.RELYING_PARTY_ID] = rp_id
        request.all_data[WEBAUTHNACTION.RELYING_PARTY_NAME] = rp_name

        request.all_data[WEBAUTHNACTION.AUTHENTICATOR_ATTACHMENT] \
            = authenticator_attachment
        request.all_data[WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS] \
            = [PUBLIC_KEY_CREDENTIAL_ALGORITHMS[x]
               for x in PUBKEY_CRED_ALGORITHMS_ORDER
               if x in public_key_credential_algorithm_pref]
        request.all_data[WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL] \
            = authenticator_attestation_level
        request.all_data[WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM] \
            = authenticator_attestation_form
        request.all_data["{0!s}_{1!s}".format(WebAuthnTokenClass.get_class_type(), ACTION.CHALLENGETEXT)] \
            = challengetext
        request.all_data[WEBAUTHNACTION.AVOID_DOUBLE_REGISTRATION] = avoid_double_registration_policy

    return True


def webauthntoken_allowed(request, action):
    """
    This is a token specific wrapper for WebAuthn token for the endpoint /token/init.

    According to the policy scope=SCOPE.ENROLL,
    action=WEBAUTHNACTION.REQ it checks, if the assertion certificate is
    for an allowed WebAuthn token type. According to the policy
    scope=SCOPE.ENROLL, action=WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST
    it checks, whether the AAGUID is whitelisted. Note: If self-attestation
    is allowed, it is – of course – possible to bypass the check for
    WEBAUTHNACTION.REQ

    If the token, which is being enrolled does not contain an allowed attestation
    certificate, or does not have an allowed AAGUID, we bail out.

    A very similar check (same policy actions, different policy scope) is
    performed during authorization,  however due to architectural limitations,
    this lives within the token implementation itself.

    :param request:
    :type request:
    :param action:
    :type action:
    :return:
    :rtype:
    """

    ttype = request.all_data.get("type")

    # Get the registration data of the 2nd step of enrolling a WebAuthn token
    reg_data = request.all_data.get("regdata")

    # If a WebAuthn token is being enrolled.
    if ttype and ttype.lower() == WebAuthnTokenClass.get_class_type() and reg_data:
        serial = request.all_data.get("serial")
        att_obj = WebAuthnRegistrationResponse.parse_attestation_object(reg_data)
        (
            attestation_type,
            trust_path,
            credential_pub_key,
            cred_id,
            aaguid
        ) = WebAuthnRegistrationResponse.verify_attestation_statement(fmt=att_obj.get('fmt'),
                                                                      att_stmt=att_obj.get('attStmt'),
                                                                      auth_data=att_obj.get('authData'))

        attestation_cert = crypto.X509.from_cryptography(trust_path[0]) if trust_path else None
        allowed_certs_pols = Match\
            .user(g,
                  scope=SCOPE.ENROLL,
                  action=WEBAUTHNACTION.REQ,
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=False)

        allowed_aaguids_pols = Match \
            .user(g,
                  scope=SCOPE.ENROLL,
                  action=WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST,
                  user_object=request.User if hasattr(request, 'User') else None) \
            .action_values(unique=False,
                           allow_white_space_in_action=True)
        allowed_aaguids = set(
            aaguid
            for allowed_aaguid_pol in allowed_aaguids_pols
            for aaguid in allowed_aaguid_pol.split()
        )

        # attestation_cert is of type X509. If you get a warning from your IDE
        # here, it is because your IDE mistakenly assumes it to be of type PKey,
        # due to a bug in pyOpenSSL 18.0.0. This bug is – however – purely
        # cosmetic (a wrongly hinted return type in X509.from_cryptography()),
        # and can be safely ignored.
        #
        # See also:
        # https://github.com/pyca/pyopenssl/commit/4121e2555d07bbba501ac237408a0eea1b41f467
        if allowed_certs_pols and not _attestation_certificate_allowed(attestation_cert, allowed_certs_pols):
            log.warning(
                "The WebAuthn token {0!s} is not allowed to be registered due to policy restriction {1!s}"
                    .format(serial, WEBAUTHNACTION.REQ))
            raise PolicyError("The WebAuthn token is not allowed to be registered due to a policy restriction.")

        if allowed_aaguids and aaguid not in [allowed_aaguid.replace("-", "") for allowed_aaguid in allowed_aaguids]:
            log.warning(
                "The WebAuthn token {0!s} is not allowed to be registered due to policy restriction {1!s}"
                    .format(serial, WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST))
            raise PolicyError("The WebAuthn token is not allowed to be registered due to a policy restriction.")

    return True


def _attestation_certificate_allowed(attestation_cert, allowed_certs_pols):
    """
    Check a certificate against a set of policies.

    This will check an attestation certificate of a U2F-, or WebAuthn-Token,
    against a list of policies. It is used to verify, whether a token with the
    given attestation may be enrolled, or authorized, respectively.

    The certificate info may be None, in which case, true will be returned if
    the policies are also empty.

    This is a wrapper for attestation_certificate_allowed(). It is needed,
    because during enrollment, we still have an actual certificate to check
    against, while attestation_certificate_required() expects the plain fields
    from the token info, containing just the issuer, serial and subject.

    :param attestation_cert: The attestation certificate.
    :type attestation_cert: OpenSSL.crypto.X509 or None
    :param allowed_certs_pols: The policies restricting enrollment, or authorization.
    :type allowed_certs_pols: dict or None
    :return: Whether the token should be allowed to complete enrollment, or authorization, based on its attestation.
    :rtype: bool
    """

    cert_info = {
        "attestation_issuer": x509name_to_string(attestation_cert.get_issuer()),
        "attestation_serial": "{!s}".format(attestation_cert.get_serial_number()),
        "attestation_subject": x509name_to_string(attestation_cert.get_subject())
    } \
        if attestation_cert \
        else None

    return attestation_certificate_allowed(cert_info, allowed_certs_pols)


def required_piv_attestation(request, action=None):
    """
    This is a token specific decorator for certificate tokens for the endpoint
    /token/init
    According to the policy scope=SCOPE.ENROLL,
    action=REQUIRE_ATTESTATION an exception is raised, if no attestation parameter is given.

    It also checks the policy if the attestation should be verified and sets the
    parameter verify_attestation accordingly.

    :param request:
    :param action:
    :return:
    """
    from privacyidea.lib.tokens.certificatetoken import ACTION, REQUIRE_ACTIONS
    ttype = request.all_data.get("type")
    if ttype and ttype.lower() == "certificate":
        # Get attestation certificate requirement
        require_att = Match.user(g, scope=SCOPE.ENROLL, action=ACTION.REQUIRE_ATTESTATION,
                                     user_object=request.User if request.User else None).action_values(unique=True)
        if REQUIRE_ACTIONS.REQUIRE_AND_VERIFY in list(require_att):
            if not request.all_data.get("attestation"):
                # There is no attestation certificate in the request, although it is required!
                log.warning("The request is missing an attestation certificate. {0!s}".format(require_att))
                raise PolicyError("A policy requires that you provide an attestation certificate.")

        # Add parameter verify_attestation
        request.all_data["verify_attestation"] = REQUIRE_ACTIONS.VERIFY in list(require_att) or \
                                                 REQUIRE_ACTIONS.REQUIRE_AND_VERIFY in list(require_att)


def hide_tokeninfo(request=None, action=None):
    """
    This decorator checks for the policy `hide_tokeninfo` and sets the
    `hidden_tokeninfo` parameter.

    The given tokeninfo keys will be removed from the response.

    The decorator wraps GET /token/

    :param request: The request that is intercepted during the API call
    :type request: Request Object
    :param action: An optional Action
    :type action: str
    :return: Always true. Modifies the parameter `request`
    :rtype: bool
    """
    hidden_fields = Match.admin_or_user(g, action=ACTION.HIDE_TOKENINFO,
                                        user_obj=request.User)\
        .action_values(unique=False)

    request.all_data['hidden_tokeninfo'] = list(hidden_fields)
    return True


def increase_failcounter_on_challenge(request=None, action=None):
    """
    This is a decorator for /validate/check, validate/triggerchallenge and auth
    which sets the parameter increase_failcounter_on_challenge
    """
    inc_fail_counter = Match.user(g, scope=SCOPE.AUTH, action=ACTION.INCREASE_FAILCOUNTER_ON_CHALLENGE,
                                  user_object=request.User if hasattr(request, 'User') else None).any()
    request.all_data["increase_failcounter_on_challenge"] = inc_fail_counter


def require_description(request=None, action=None):
    """
    Pre Policy
    This checks if a description is required to roll out a specific token.
    scope=SCOPE.ENROLL, action=REQUIRE_DESCRIPTION

    An exception is raised, if the tokentypes specified in the
    REQUIRE_DESCRIPTION policy match the token to be rolled out,
    but no description is given.

    :param request:
    :param action:
    :return:
    """
    params = request.all_data
    user_object = request.User
    (role, username, realm, adminuser, adminrealm) = determine_logged_in_userparams(g.logged_in_user, params)

    action_values = Match.generic(g, action=ACTION.REQUIRE_DESCRIPTION,
                             scope=SCOPE.ENROLL,
                             adminrealm=adminrealm,
                             adminuser=adminuser,
                             user=username,
                             realm=realm,
                             user_object=user_object).action_values(unique=False)

    token_types = list(action_values.keys())
    type_value = request.all_data.get("type") or 'hotp'
    if type_value in token_types:
        tok = None
        serial = getParam(params, "serial")
        if serial:
            tok = get_one_token(serial=serial, rollout_state=ROLLOUTSTATE.VERIFYPENDING, silent_fail=True) or \
                  get_one_token(serial=serial, rollout_state=ROLLOUTSTATE.CLIENTWAIT, silent_fail=True)
        # only if no token exists, yet, we need to check the description
        if not tok and not request.all_data.get("description"):
            log.warning(_("Missing description for {} token.".format(type_value)))
            raise PolicyError(_("Description required for {} token.".format(type_value)))
