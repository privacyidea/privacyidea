# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Policy definitions and enrollment-URL helpers."""

import logging
from typing import Any

from flask import Request

from privacyidea.api.lib.utils import send_result
from privacyidea.lib import _
from privacyidea.lib.config import (get_token_types, get_enrollable_token_types)
from privacyidea.lib.error import (PolicyError)
from privacyidea.lib.user import User

from privacyidea.lib.token.lifecycle import init_token
from privacyidea.lib.token.query import get_one_token, get_tokenclass_info


log = logging.getLogger(__name__)



def get_dynamic_policy_definitions(scope: str | None = None) -> dict:
    """
    This returns the dynamic policy definitions that come with the new loaded
    token classes.

    :param scope: an optional scope parameter. Only return the policies of
        this scope. If the scope is not defined, an empty dictionary is returned.
    :return: The policy definition for the token or only for the scope.
    """
    from privacyidea.lib.policy import SCOPE, MAIN_MENU, GROUP

    pol = {SCOPE.ADMIN: {},
           SCOPE.USER: {},
           SCOPE.AUTH: {},
           SCOPE.ENROLL: {},
           SCOPE.WEBUI: {},
           SCOPE.AUTHZ: {}}

    enrollable_token_types = get_enrollable_token_types()
    for ttype in get_token_types():
        if ttype in enrollable_token_types:
            pol[SCOPE.ADMIN][f"enroll{ttype.upper()}"] = {
                'type': 'bool',
                'desc': _("Admin is allowed to initialize {0!s} tokens.").format(ttype.upper()),
                'mainmenu': [MAIN_MENU.TOKENS],
                'group': GROUP.ENROLLMENT
            }

            conf = get_tokenclass_info(ttype, section='user')
            if 'enroll' in conf:
                pol[SCOPE.USER][f"enroll{ttype.upper()}"] = {
                    'type': 'bool',
                    'desc': _("The user is allowed to enroll a {0!s} token.").format(ttype.upper()),
                    'mainmenu': [MAIN_MENU.TOKENS],
                    'group': GROUP.ENROLLMENT
                }

        # now merge the dynamic Token policy definition
        # into the global definitions
        policy = get_tokenclass_info(ttype, section='policy')

        # get all policy sections like: admin, user, enroll, auth, authz
        pol_keys = list(pol)

        for pol_section in policy.keys():
            # if we have a dyn token definition of this section type
            # add this to this section - and make sure, that it is
            # then token type prefixed
            if pol_section in pol_keys:
                pol_entry = policy.get(pol_section)
                for pol_def in pol_entry:
                    set_def = pol_def
                    if pol_def.startswith(ttype) is not True:
                        set_def = f'{ttype!s}_{pol_def!s}'

                    pol[pol_section][set_def] = pol_entry.get(pol_def)

        # If the token class should provide specific PIN policies, now merge
        # PIN policies
        pin_scopes = get_tokenclass_info(ttype, section='pin_scopes') or []
        for pin_scope in pin_scopes:
            pol[pin_scope][f'{ttype.lower()}_otp_pin_maxlength'] = {
                'type': 'int',
                'value': list(range(0, 32)),
                "desc": _("Set the maximum allowed PIN length of the {0!s} token.").format(ttype.upper()),
                'group': GROUP.PIN
            }
            pol[pin_scope][f'{ttype.lower()}_otp_pin_minlength'] = {
                'type': 'int',
                'value': list(range(0, 32)),
                "desc": _("Set the minimum required PIN length of the {0!s} token.").format(ttype.upper()),
                'group': GROUP.PIN
            }
            pol[pin_scope][f'{ttype.lower()}_otp_pin_contents'] = {
                'type': 'str',
                "desc": _("Specify the required PIN contents of the {0!s} token. (c)haracters, (n)umeric, (s)pecial, "
                          "(o)thers. [+/-]!").format(ttype.upper()),
                'group': GROUP.PIN
            }

    # return subsection, if scope is defined
    # return empty dict for invalid scopes
    if scope:
        if scope not in pol:
            log.debug(f"Scope '{scope}' is not defined in the dynamic policy definitions.")
        pol = pol.get(scope, {})

    return pol


def regenerate_enroll_url(serial: str, request: Request, g: Any) -> str | None:
    """
    Returns the enroll URL for a token with the given serial number that is already enrolled.
    Loads the configurations from the policies.
    If the rollout state of a token is 'enrolled' None is returned.
    """
    token = get_one_token(serial=serial)
    token_owner = token.user or User()
    request.User = token_owner
    if token_owner:
        request.all_data["user"] = token_owner.login
        request.all_data["realm"] = token_owner.realm
        request.all_data["resolver"] = token_owner.resolver
    request.all_data["serial"] = serial
    request.all_data["type"] = token.get_type()
    g.serial = serial

    # Get policies for the token
    # TODO: Refactor including original uses of these functions (decorators on token init endpoint)
    from privacyidea.api.lib.prepolicy import (pushtoken_add_config, tantoken_count, papertoken_count,
                                               init_tokenlabel)
    from privacyidea.api.lib.postpolicy import check_verify_enrollment

    try:
        pushtoken_add_config(request, None)
        tantoken_count(request, None)
        papertoken_count(request, None)
        init_tokenlabel(request, None)
    except PolicyError as ex:
        log.warning(f"{ex}")

    params = request.all_data
    params.update({"genkey": True, "rollover": True})
    params["policies"] = g.policies
    token = init_token(params)
    enroll_url = token.get_enroll_url(token_owner, params)

    # Check post policies
    init_result = {token.get_serial(): {"type": token.get_type()}}
    init_result[token.get_serial()].update(token.get_init_detail(params, token_owner))
    try:
        response = send_result(True, details=init_result[token.get_serial()])
        check_verify_enrollment(request, response)
    except PolicyError as ex:
        log.warning(f"{ex}")

    return enroll_url
