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

import logging

from flask import (Blueprint, request, g, current_app)
from flask_babel import _
from werkzeug.datastructures import FileStorage

from privacyidea.api.auth import admin_required
from privacyidea.api.lib.postpolicy import (save_pin_change, check_verify_enrollment,
                                            postpolicy)
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
                                           twostep_enrollment_activation,
                                           twostep_enrollment_parameters,
                                           sms_identifiers, pushtoken_add_config,
                                           verify_enrollment,
                                           indexedsecret_force_attribute,
                                           check_admin_tokenlist, fido2_enroll, webauthntoken_allowed,
                                           webauthntoken_request, required_piv_attestation,
                                           hide_tokeninfo, init_ca_connector, init_ca_template,
                                           init_subject_components, require_description_on_edit, require_description,
                                           check_container_action, check_user_params,
                                           force_server_generate_key)
from privacyidea.lib.challenge import (cancel_challenge, get_challenges, get_challenges_for_user,
                                        get_challenges_paginate, cleanup_expired_challenges)
from privacyidea.lib.error import (ParameterError, TokenAdminError,
                                   ResourceNotFoundError, PolicyError, Error)
from privacyidea.lib.event import event
from privacyidea.lib.importotp import (parseOATHcsv, parseSafeNetXML,
                                       parseYubicoCSV, parsePSKCdata, GPGImport)
from privacyidea.lib.subscriptions import CheckSubscription
from privacyidea.lib.tokenrolloutstate import RolloutState
from .lib.utils import send_result, send_csv_result, get_optional, get_required
from ..lib.container import find_container_by_serial, add_token_to_container
from ..lib.fido2.util import get_credential_ids_for_user
from ..lib.log import log_with
from ..lib.policies.actions import PolicyAction
from ..lib.policy import Match
from ..models.audit import audit_column_length
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
from ..lib.tokens.passkeytoken import PasskeyTokenClass
from ..lib.tokens.webauthntoken import WebAuthnTokenClass
from ..lib.policydecorators import check_admin_allowed_for_token_owner
from ..lib.user import get_user_from_param, User

token_blueprint = Blueprint('token_blueprint', __name__)
log = logging.getLogger(__name__)

__doc__ = """
The token REST API manages the lifecycle of authentication tokens -
enrollment, listing, assignment to users, PIN management, realm
membership, tokengroup membership, token info, lost-token handling,
bulk import, and admin-only attribute editing.

All endpoints require authentication. Admins may operate on any token
that their realm-scoped admin policies permit; regular users may only
operate on their own tokens (the request hooks force the
``user`` / ``realm`` / ``resolver`` parameters to the calling user's
identity for non-admin callers). Per-action authorization is enforced
by the token-scope policies (``enroll<TOKENTYPE>``, ``assign``,
``unassign``, ``revoke``, ``enable``, ``disable``, ``delete``,
``reset``, ``resync``, ``setpin``, ``setrandompin``,
``setdescription``, ``set``, ``tokenrealms``, ``losttoken``,
``getserial``, ``getchallenges``, ``settokeninfo``, ``tokengroups``,
``copytokenpin``, ``copytokenuser``, ``import``).

Many endpoints operate on either a single token (via ``serial``) or
on a user's full set of tokens (when ``user`` and ``realm`` are
supplied without a serial); the
:func:`~privacyidea.api.lib.prepolicy.check_token_action` decorator
expands the user-only call to every token the user owns.

See :ref:`rest_auth` for authentication and :ref:`policies` for the
overall policy concept.
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
    Create or roll over a token. The token type drives both the
    request shape (each token class accepts its own parameters; see
    the corresponding ``TokenClass.update`` method) and the response
    shape (each token class returns its own enrollment payload -
    typically QR codes, ``otpauth://`` URLs, seeds, etc.).

    Requires authentication. Authorization is gated by the
    ``enroll<TOKENTYPE>`` policy in the calling principal's scope
    (admin or user); a request without an explicit ``type`` defaults
    to ``HOTP`` and is therefore checked against ``enrollHOTP``.

    For user callers, the ``user`` / ``realm`` / ``resolver`` fields
    are bound to the calling user before the view runs; a regular
    user can only enroll tokens for themselves.

    :jsonparam type: token type (e.g. ``hotp``, ``totp``, ``push``,
        ``webauthn``, ``passkey``, ...). Defaults to ``hotp`` when
        omitted.
    :jsonparam serial: optional serial; auto-generated when omitted.
    :jsonparam description: free-form description.
    :jsonparam pin: the OTP PIN.
    :jsonparam user: login name of the user to assign the token to.
    :jsonparam realm: realm of the user; if no ``user`` is given,
        the token is assigned to the realm directly.
    :jsonparam tokenrealm: additional realms to add the token to.
    :jsonparam otpkey: the token secret. Either ``otpkey`` or
        ``genkey`` is required for OTP token types.
    :jsonparam genkey: ``1`` to have the server generate the secret.
    :jsonparam keysize: byte length of the generated key. The
        accepted values depend on the token class.
    :jsonparam otplen: length of the OTP value (typically ``6`` or
        ``8``).
    :jsonparam hashlib: HMAC hash algorithm - ``sha1``, ``sha256`` or
        ``sha512``.
    :jsonparam validity_period_start: start of the validity period.
    :jsonparam validity_period_end: end of the validity period.
    :jsonparam 2stepinit: ``1`` together with ``genkey=1`` to start
        a two-step enrollment (see :ref:`2step_enrollment`).
    :jsonparam otpkeyformat: alternate encoding for the supplied
        ``otpkey`` (``hex`` or ``base32check``).
    :jsonparam rollover: ``1`` or ``true`` to roll over a token that
        is already in the ``clientwait`` state.
    :jsonparam container_serial: optional, attach the new token to
        this container. Requires the
        :ref:`policy_container_add_token` policy on the caller; if
        the policy is missing, the enrollment still succeeds but the
        token is not added to the container.
    :status 200: ``True`` in ``result.value`` plus a token-type-specific
        enrollment payload in ``detail`` (QR codes, URLs, seeds,
        challenge/verify hand-shake info, ...).

    Depending on the token type there can be additional parameters;
    see each class' ``update`` method for the full list.

    **Example response** (HOTP token):

       .. sourcecode:: http

           HTTP/1.1 200 OK
           Content-Type: application/json

           {
             "detail": {
               "googleurl": {
                 "description": "URL for google Authenticator",
                 "img": "<img width=250 src=\\"data:image/png;base64,...\\"/>",
                 "value": "otpauth://hotp/mylabel?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&counter=0"
               },
               "oathurl": {
                 "description": "URL for OATH token",
                 "img": "<img width=250 src=\\"data:image/png;base64,...\\"/>",
                 "value": "oathtoken:///addToken?name=mylabel&lockdown=true&key=3132...3930"
               },
               "otpkey": {
                 "description": "OTP seed",
                 "img": "<img width=200 src=\\"data:image/png;base64,...\\"/>",
                 "value": "seed://3132...3930"
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

    The ``img`` fields carry inline base64-encoded PNGs (the QR codes
    shown in the WebUI); they have been abbreviated above for
    readability.

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
                and token.rollout_state == RolloutState.CLIENTWAIT):
            param["registered_credential_ids"] = get_credential_ids_for_user(user)

        # The token was created successfully, so we add token specific init details like the Google URL to the response
        try:
            init_details = token.get_init_detail(param, user)
            response_details.update(init_details)
        except ParameterError as e:
            if e.id == Error.PARAMETER_USER_MISSING:
                remove_token(serial=token.get_serial())
            raise e

        # Check if a container_serial is set and assign the token to the container
        container_serial = param.get("container_serial", {})
        if container_serial:
            # Check if user is allowed to add tokens to containers
            try:
                container_add_token_right = check_container_action(request, action=PolicyAction.CONTAINER_ADD_TOKEN)
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
@prepolicy(check_base_action, request, action=PolicyAction.GETCHALLENGES)
@event("token_getchallenges", request, g)
@log_with(log)
def get_challenges_api(serial=None):
    """
    Return the open challenges.

    Three filter modes (mutually exclusive):

    * ``<serial>`` path component -> challenges for that token (paginated).
    * ``?user=<name>[&realm=<realm>]`` query -> every challenge across all
      tokens owned by that user. Used by the user-detail view.
    * neither -> all open challenges across the server, paginated.

    Requires admin authentication and the policy action
    :ref:`policy_getchallenges`. Realm-scoping is enforced against the
    target's owning user when a serial or user filter is given.

    :param serial: optional path component, the token serial.
    :query user: optional username - switches to user-aggregation mode.
    :query realm: optional realm for the user lookup.
    :query sortby: sort column, default ``timestamp`` (paginated mode only).
    :query sortdir: ``asc`` (default) or ``desc``.
    :query page: 1-indexed page number.
    :query pagesize: page size (default ``15``).
    :query transaction_id: restrict to challenges with this transaction id.
    :status 200: challenge list in ``result.value``.
    """
    param = request.all_data
    # user-aggregation mode kicks in only when the caller explicitly passes
    # the ``user`` query param. An empty string is rejected so the absence
    # of an actual username can never be mistaken for "every user".
    if "user" in param:
        if serial is not None:
            # The three filter modes (path serial / ?user= / list-all) are
            # mutually exclusive. Reject the ambiguous combination loudly.
            raise ParameterError("Specify either a path serial or the 'user' query parameter, not both.")
        user = get_user_from_param(param, optional_or_required=False)
        if user.is_empty():
            raise ParameterError("user is required")
        g.audit_object.log({"user": user.login, "realm": user.realm})
        # @prepolicy(check_base_action, ...) confirms the admin has the
        # action *somewhere*. Re-match against the target user so that an
        # admin whose getchallenges policy is scoped to realm A cannot
        # read challenges of users in realm B. .allowed() honors the
        # default-allow-when-no-policies semantic.
        if not Match.admin(g, action=PolicyAction.GETCHALLENGES, user_obj=user).allowed():
            raise PolicyError(f"You are not allowed to view challenges for user "
                              f"{user.login!s}@{user.realm!s}.")
        from privacyidea.lib.cache import redis_feature_enabled
        challenges = get_challenges_for_user(user)
        payload = {
            "challenges": [c.get() for c in challenges],
            "count": len(challenges),
            "redis_cache_enabled": redis_feature_enabled("challenges"),
        }
        g.audit_object.log({"success": True})
        return send_result(payload)

    page = int(get_optional(param, "page", default=1))
    sort = get_optional(param, "sortby", default="timestamp")
    sdir = get_optional(param, "sortdir", default="asc")
    psize = int(get_optional(param, "pagesize", default=15))
    transaction_id = get_optional(param, "transaction_id")
    g.audit_object.log({"serial": serial})
    # Realm-scope check when a specific serial is targeted, so a realm-
    # restricted admin can't read challenges of tokens outside their realm.
    # The list-all variants - serial is None, or a wildcard pattern like
    # ``*`` or ``**`` that the WebUI uses to populate the global challenges
    # table - preserve existing behavior. They predate this PR and should
    # be revisited separately. A wildcard pattern can't be reduced to a
    # single owning realm without resolving every match first.
    if serial and "*" not in serial:
        # Missing serial here is a real 404: the resource the admin
        # addressed (the token) doesn't exist.
        token = get_one_token(serial=serial)
        check_admin_allowed_for_token_owner(g, token, PolicyAction.GETCHALLENGES,
                                            "view challenges for")
    challenges = get_challenges_paginate(serial=serial, sortby=sort,
                                         transaction_id=transaction_id,
                                         sortdir=sdir, page=page, psize=psize)
    g.audit_object.log({"success": True})
    return send_result(challenges)


def _pack_serials(serials: list, limit: int) -> tuple:
    """
    Comma-join whole serials up to ``limit`` characters.

    Returns ``(packed, dropped)`` where ``dropped`` is the number of serials
    that did not fit. Packing whole serials avoids a mid-serial chop that
    would corrupt forensic detail when written into a fixed-width audit
    column (which is hard-cut by the audit module).
    """
    packed = ""
    for index, serial in enumerate(serials):
        candidate = f"{packed},{serial}" if packed else serial
        if len(candidate) > limit:
            return packed, len(serials) - index
        packed = candidate
    return packed, 0


@token_blueprint.route('/challenges/transaction/<transaction_id>', methods=['DELETE'])
@admin_required
@prepolicy(check_base_action, request, action=PolicyAction.CANCELCHALLENGE)
@event("token_cancelchallenge", request, g)
@log_with(log)
def cancel_challenge_api(transaction_id):
    """
    Cancel (delete) a single active challenge by its transaction ID. Removes
    it from both the Redis cache (when active) and the database.

    :param transaction_id: The transaction ID of the challenge to cancel.
    :return: json with ``deleted`` count.
    """
    # Look up the serial before deletion so the audit row carries it.
    # The lookup goes through the same cache+DB path as the deletion,
    # so worst case it's the same I/O the cancel itself would make.
    existing = get_challenges(transaction_id=transaction_id)
    serials = sorted({c.serial for c in existing if getattr(c, 'serial', None)})
    # Realm-scope each affected token. If the admin lacks cancelchallenge
    # for any of the target realms, deny the whole call rather than
    # partially cancelling - atomicity matters for an action with audit
    # impact. We deliberately do NOT log the target serials before the
    # realm check passes - otherwise a realm-A admin could probe arbitrary
    # transaction_ids and observe realm-B token serials in the audit log.
    #
    # ``serials`` can legitimately be empty in two cases - both allowed by
    # design under the base CANCELCHALLENGE policy:
    #   1. Usernameless passkey challenges, which are written with
    #      serial="" (cache_challenge skips the serial set for these) and
    #      filtered out by the truthy-comprehension above. There is no
    #      realm to scope against - the base-action policy is the only gate.
    #   2. The challenge already evaporated (TTL expired or concurrent
    #      cancel). cancel_challenge below is a safe no-op in this case.
    # Both fall under "no realm context exists to enforce against."
    #
    # Per-serial token resolution is wrapped in try/except: an orphan
    # transaction (token already deleted, cache entry surviving) is
    # exactly what an admin would call this endpoint to clean up, so a
    # missing token here is not a reason to refuse the cancel.
    for s in serials:
        try:
            token = get_one_token(serial=s)
        except ResourceNotFoundError:
            continue
        check_admin_allowed_for_token_owner(g, token, PolicyAction.CANCELCHALLENGE,
                                            "cancel challenges for")
    result = cancel_challenge(transaction_id)
    # Build a single audit entry now that the realm check passed and the
    # cancel result is known. The `serial` column is 40 chars by default -
    # plenty for the common case (one transaction -> one token, with
    # default 8-char serials, 4-5 still fit comma-joined). Pack whole
    # serials in arrival order up to the column budget; if some had to be
    # dropped, also record the list in `info` (500 chars) so the forensic
    # detail isn't lost. `info` is hard-cut by the audit module, so pack it
    # to whole serials here too rather than risk a mid-serial chop, and
    # summarise any that still overflow with a trailing "+N more".
    serial_limit = audit_column_length.get("serial")
    info_limit = audit_column_length.get("info")
    packed_serials, serial_dropped = _pack_serials(serials, serial_limit)
    info = f"Cancelled {result.removed} challenge(s) for transaction {transaction_id}"
    if serial_dropped:
        prefix, suffix = f"{info} (serials: ", ")"
        # Reserve room for a worst-case "+<count> more" marker so the closing
        # state always fits regardless of how many serials are dropped.
        marker_reserve = len(f",+{len(serials)} more")
        packed_info, info_dropped = _pack_serials(
            serials, info_limit - len(prefix) - len(suffix) - marker_reserve)
        if info_dropped:
            packed_info += f"{',' if packed_info else ''}+{info_dropped} more"
        info = f"{prefix}{packed_info}{suffix}"
    g.audit_object.log({
        "success": True,
        "serial": packed_serials or None,
        "info": info,
    })
    payload = {"status": True, "deleted": result.removed}
    if not result.cache_available:
        # The worker handling this request is in its Redis retry cooldown,
        # so the cache eviction did not run. Other workers still have a
        # live Redis client and may continue serving this challenge from
        # cache until its TTL expires (typically minutes). Surfacing the
        # warning lets the operator know the cancel may not have propagated
        # cluster-wide yet.
        payload["warning"] = ("Redis cache unreachable on this worker; the "
                              "challenge may still be served from cache by "
                              "other nodes until its TTL expires.")
    return send_result(payload)


@token_blueprint.route("/challenges/expired", methods=['DELETE'])
@admin_required
@log_with(log)
def delete_expired_challenges_api():
    """
    Remove all expired entries from the challenge table. Useful as a
    periodic-task target on busy installations.

    Requires admin authentication.

    :reqheader PI-Authorization: authentication token.
    :status 200: ``{"status": True, "deleted": <n>}`` in
        ``result.value``, where ``n`` is the number of removed rows.

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": {"status": true, "deleted": 42}
         },
         "version": "privacyIDEA unknown"
       }
    """
    row_count = cleanup_expired_challenges(chunk_size=None, age=None)
    g.audit_object.log({"success": True, "info": f"Deleted {row_count} entries from challenges"})
    return send_result({"status": True, "deleted": row_count})


@token_blueprint.route('/', methods=['GET'])
@prepolicy(check_admin_tokenlist, request, PolicyAction.TOKENLIST)
@prepolicy(hide_tokeninfo, request)
@event("token_list", request, g)
@log_with(log)
def list_api():
    """
    Return tokens, paginated and filtered by the supplied query
    parameters. Realm-admins are restricted by their policies; user
    callers always see only their own tokens regardless of the
    ``user`` / ``realm`` parameters (the request hooks bind those
    fields to the calling user).

    Requires authentication and the policy action ``tokenlist``. The
    ``hide_tokeninfo`` policy may strip configured token-info keys
    from the response.

    :query serial: filter by serial. Substring match via ``*``
        (e.g. ``*OATH*``); comma-separated list of serials also
        supported.
    :query type: filter by token type. Substring match via ``*``
        (e.g. ``*otp*`` matches hotp and totp).
    :query type_list: comma-separated list of token types.
    :query user: **admin only** - filter by this user. Accepts
        ``user@realm`` syntax. If both ``user`` and ``realm`` are
        given, ``realm`` wins. Ignored for user-role callers.
    :query realm: **admin only** - filter by realm of the assigned
        user. Without a ``user`` parameter, returns every token
        assigned to any user in this realm. Ignored for user-role
        callers.
    :query tokenrealm: filter to tokens that belong to this realm
        (independent of the user's realm). Substring match via ``*``;
        comma-separated list of realm names also supported, where each
        entry may contain wildcards
        (e.g. ``realm1,realm2,realm3`` or ``staff*,students*``).
    :query description: filter by description.
    :query assigned: ``True`` or ``False`` to limit to assigned or
        unassigned tokens.
    :query active: ``True`` or ``False`` to limit to active or
        inactive tokens.
    :query rollout_state: filter by rollout state (e.g.
        ``clientwait``).
    :query infokey: filter by token-info key (combine with
        ``infovalue``).
    :query infovalue: filter by token-info value (combine with
        ``infokey``).
    :query container_serial: filter to tokens attached to the given
        container; pass an empty string to limit to tokens without
        any container.
    :query hidden_tokeninfo: list of token-info keys to strip from
        the response. Overridden by the ``hide_tokeninfo`` policy if
        active.
    :query sortby: sort column, default ``serial``.
    :query sortdir: ``asc`` (default) or ``desc``.
    :query page: 1-indexed page number, default ``1``.
    :query pagesize: page size, default ``15``.
    :query outform: ``csv`` to return ``text/csv`` instead of JSON.
        Pagination still applies.
    :status 200: paginated token list in ``result.value`` (or as a
        CSV body when ``outform=csv``).
    """
    param = request.all_data
    serial = get_optional(param, "serial")
    page = int(get_optional(param, "page", default=1))
    tokentype = get_optional(param, "type")
    token_type_list = get_optional(param, "type_list")
    if token_type_list:
        token_type_list = token_type_list.replace(" ", "").split(",")
    description = get_optional(param, "description")
    sort = get_optional(param, "sortby", default="serial")
    sdir = get_optional(param, "sortdir", default="asc")
    psize = int(get_optional(param, "pagesize", default=15))
    realm = get_optional(param, "tokenrealm")
    userid = get_optional(param, "userid")
    resolver = get_optional(param, "resolver")

    # Only admins may use the "user" and "realm" query parameters to query
    # tokens of arbitrary users or realms. For callers with role "user" we
    # always use request.User (which resolve_logged_in_user already forced to
    # their own identity) so that a regular user can never see other users'
    # tokens via these params.
    is_admin = g.logged_in_user.get("role") == "admin"
    user_param = get_optional(param, "user")
    realm_param = get_optional(param, "realm")
    if is_admin and user_param:
        user = get_user_from_param(param)
    elif is_admin and realm_param:
        user = User(login="", realm=realm_param)
    else:
        user = request.User
    output_format = get_optional(param, "outform")
    assigned = get_optional(param, "assigned")
    active = get_optional(param, "active")
    tokeninfokey = get_optional(param, "infokey")
    tokeninfovalue = get_optional(param, "infovalue")
    rollout_state = get_optional(param, "rollout_state")
    container_serial = get_optional(param, "container_serial")
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
    g.audit_object.log({'info': f"realm: {allowed_realms!s}"})

    # get hide_tokeninfo setting from all_data
    hidden_tokeninfo = get_optional(param, 'hidden_tokeninfo', default=None)

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
@prepolicy(check_token_action, request, action=PolicyAction.ASSIGN)
@prepolicy(check_user_params, request, action=PolicyAction.ASSIGN)
@prepolicy(encrypt_pin, request)
@prepolicy(check_otp_pin, request)
@prepolicy(check_external, request, action="assign")
@CheckSubscription(request)
@event("token_assign", request, g)
@log_with(log)
def assign_api():
    """
    Assign a token to a user. The user's realm is added to the
    token's realm list; existing realms are preserved. An optional
    PIN may be set on the same call.

    Requires authentication and the policy action ``assign``.
    User-role callers can only assign tokens to themselves.

    :jsonparam serial: token serial (required, must be non-empty).
    :jsonparam user: login name of the user (required).
    :jsonparam realm: realm of the user (required if not the default
        realm).
    :jsonparam pin: optional OTP PIN to set in the same call.
    :jsonparam encryptpin: ``True`` to store the PIN encrypted (the
        default behavior is governed by the ``encrypt_pin`` policy).
    :status 200: ``True`` on success in ``result.value``.
    """
    user = get_user_from_param(request.all_data, False)
    serial = get_required(request.all_data, "serial", allow_empty=False)
    pin = get_optional(request.all_data, "pin")
    encrypt_pin_param = get_optional(request.all_data, "encryptpin")
    if g.logged_in_user.get("role") == "user":
        err_message = "Token already assigned to another user."
    else:
        err_message = None
    res = assign_token(serial, user, pin=pin, encrypt_pin=encrypt_pin_param,
                       error_message=err_message)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/unassign', methods=['POST'])
@prepolicy(check_token_action, request, action=PolicyAction.UNASSIGN)
@event("token_unassign", request, g)
@log_with(log)
def unassign_api():
    """
    Remove the user assignment from a token. Three call shapes are
    supported:

    * ``serial=...`` (single, or comma-separated list) - operate on
      these tokens.
    * ``serials=[...]`` - operate on this list of tokens.
    * ``user=...&realm=...`` (no serial) - operate on every token
      currently assigned to that user.

    Requires authentication and the policy action ``unassign``.
    Tokens the caller is not authorized to manage are silently
    skipped and reported back; missing serials are reported in
    ``failed``.

    :jsonparam serial: single serial or comma-separated list.
    :jsonparam serials: list of serials.
    :jsonparam user: user name (only when ``serial`` / ``serials``
        is omitted; requires ``realm``).
    :jsonparam realm: realm name (only when ``serial`` / ``serials``
        is omitted; requires ``user``).
    :status 200: for a single-serial call the response is ``True``
        in ``result.value``; for any multi-serial call (or any case
        with skipped tokens), the response value is
        ``{"count_success": <n>, "failed": [...], "unauthorized": [...]}``.
    """
    user = request.User
    serial_list = get_optional(request.all_data, "serials")

    # check_token_action will raise an error if no processable token are given. So at this point we can assume that
    # serial_list at least contains one serial.
    # check_token_action will also put the serials of all token of the users in the serial_list
    # if just the user was given as parameter, so we do not need to check that here - just use the serial_list

    g.audit_object.log({"serial": serial_list if len(serial_list) != 1 else serial_list[0]})

    not_authorized_serials = get_optional(request.all_data, "not_authorized_serials", [])
    not_found_serials = get_optional(request.all_data, "not_found_serials", [])
    # If only one serial is given, the value in the send result is expected to be a boolean (old API behavior).
    if len(serial_list) == 1 and not not_authorized_serials and not not_found_serials:
        res = unassign_token(serial_list[0], user=user)
        g.audit_object.log({"success": True})
        return send_result(res)

    count_success = 0
    failed = get_optional(request.all_data, "not_found_serials", [])
    for serial in serial_list:
        try:
            tmp = unassign_token(serial, user=user)
            count_success += tmp
        except Exception as ex:
            log.error(f"Error unassigning token {serial}: {ex}")
            failed.append(serial)
    res = {
        "count_success": count_success,
        "failed": failed,
        "unauthorized": not_authorized_serials
    }
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/revoke', methods=['POST'])
@token_blueprint.route('/revoke/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=PolicyAction.REVOKE)
@event("token_revoke", request, g)
@log_with(log)
def revoke_api(serial=None):
    """
    Revoke a token. A revoked token is locked and can no longer
    authenticate; some token types perform additional teardown
    (e.g. push tokens unsubscribe, certificate tokens revoke their
    cert).

    Without ``serial`` and with ``user`` set, every token of that
    user is revoked.

    Requires authentication and the policy action ``revoke``.

    :param serial: optional path component, the token serial.
    :jsonparam serial: token serial (alternative to the path
        component).
    :jsonparam user: login name (only when no serial is given -
        revokes every token of the user).
    :jsonparam realm: realm of the user.
    :status 200: number of revoked tokens in ``result.value``.
    """
    user = request.User
    if not serial:
        serial = get_optional(request.all_data, "serial")
    g.audit_object.log({"serial": serial})

    res = revoke_token(serial, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/enable', methods=['POST'])
@token_blueprint.route('/enable/<serial>', methods=['POST'])
@prepolicy(check_max_token_user, request)
@prepolicy(check_token_action, request, action=PolicyAction.ENABLE)
@event("token_enable", request, g)
@log_with(log)
def enable_api(serial=None):
    """
    Enable a token. Without ``serial`` and with ``user`` set, every
    token of that user is enabled.

    Requires authentication and the policy action ``enable``. Subject
    to the per-user token-count limit (``check_max_token_user``).

    :param serial: optional path component, the token serial.
    :jsonparam serial: token serial (alternative to the path
        component).
    :jsonparam user: login name (only when no serial is given -
        enables every token of the user).
    :jsonparam realm: realm of the user.
    :status 200: number of enabled tokens in ``result.value``.
    """
    user = request.User
    if not serial:
        serial = get_optional(request.all_data, "serial")
    g.audit_object.log({"serial": serial})

    res = enable_token(serial, enable=True, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/disable', methods=['POST'])
@token_blueprint.route('/disable/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=PolicyAction.DISABLE)
@event("token_disable", request, g)
@log_with(log)
def disable_api(serial=None):
    """
    Disable a token. Disabled tokens cannot authenticate but can be
    re-enabled later. Without ``serial`` and with ``user`` set,
    every token of that user is disabled.

    Requires authentication and the policy action ``disable``.

    :param serial: optional path component, the token serial.
    :jsonparam serial: token serial (alternative to the path
        component).
    :jsonparam user: login name (only when no serial is given -
        disables every token of the user).
    :jsonparam realm: realm of the user.
    :status 200: number of disabled tokens in ``result.value``.
    """
    user = request.User
    if not serial:
        serial = get_optional(request.all_data, "serial")
    g.audit_object.log({"serial": serial})

    res = enable_token(serial, enable=False, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/', methods=['DELETE'])
@token_blueprint.route('/<serial>', methods=['DELETE'])
@prepolicy(check_token_action, request, action=PolicyAction.DELETE)
@event("token_delete", request, g)
@log_with(log)
def delete_api(serial=None):
    """
    Delete tokens. Three call shapes are supported, mirroring
    :http:post:`/token/unassign`:

    * single serial via the ``<serial>`` path component, or
      ``serial=...`` (or comma-separated list);
    * ``serials=[...]`` list;
    * ``user=...&realm=...`` (no serial) - delete every token of
      that user.

    Requires authentication and the policy action ``delete``.
    Tokens the caller is not authorized to manage are silently
    skipped and reported back; missing serials are reported in
    ``failed``.

    :param serial: optional path component, the token serial.
    :jsonparam serial: single serial or comma-separated list.
    :jsonparam serials: list of serials.
    :jsonparam user: login name.
    :jsonparam realm: realm of the user.
    :status 200: for a single-serial call the response is the
        number of deleted tokens in ``result.value``; for any
        multi-serial call (or any case with skipped tokens), the
        response value is
        ``{"count_success": <n>, "failed": [...], "unauthorized": [...]}``.
    """
    user = request.User
    serial_list = get_optional(request.all_data, "serials")
    not_authorized_serials = get_optional(request.all_data, "not_authorized_serials") or []

    g.audit_object.log({"serial": serial_list[0] if len(serial_list) == 1 else serial_list})

    # If only one serial is given, the value in the send result is expected to be a boolean (old API behavior).
    if len(serial_list) == 1 and not not_authorized_serials:
        res = remove_token(serial_list[0], user=user)
        g.audit_object.log({"success": True})
        return send_result(res)

    count_success = 0
    failed = get_optional(request.all_data, "not_found_serials", [])
    for serial in serial_list:
        try:
            tmp = remove_token(serial, user=user)
            count_success += tmp
        except Exception as ex:
            log.exception(f"Error deleting token {serial}: {ex}")
            failed.append(serial)

    res = {
        "count_success": count_success,
        "failed": failed,
        "unauthorized": not_authorized_serials
    }
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/reset', methods=['POST'])
@token_blueprint.route('/reset/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=PolicyAction.RESET)
@event("token_reset", request, g)
@log_with(log)
def reset_api(serial=None):
    """
    Reset the fail counter of a token. Without ``serial`` and with
    ``user`` set, every token of that user is reset.

    Requires authentication and the policy action ``reset``.

    :param serial: optional path component, the token serial.
    :jsonparam serial: token serial (alternative to the path
        component).
    :jsonparam user: login name (only when no serial is given -
        resets every token of the user).
    :jsonparam realm: realm of the user.
    :status 200: ``True`` on success in ``result.value``.
    """
    user = request.User
    if not serial:
        serial = get_optional(request.all_data, "serial")
    g.audit_object.log({"serial": serial})

    res = reset_token(serial, user=user)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/resync', methods=['POST'])
@token_blueprint.route('/resync/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=PolicyAction.RESYNC)
@event("token_resync", request, g)
@log_with(log)
def resync_api(serial=None):
    """
    Resynchronize an OTP token by submitting two consecutive OTP
    values it produced. Used when an event-based token (HOTP) has
    drifted out of sync with the server's counter, or when a
    time-based token (TOTP) is on a clock the server cannot reach.

    Requires authentication and the policy action ``resync``.

    :param serial: optional path component, the token serial.
    :jsonparam serial: token serial (required if not in the path).
    :jsonparam otp1: first OTP value (required).
    :jsonparam otp2: second OTP value, immediately following ``otp1``
        (required).
    :status 200: ``True`` if the token resynchronized, ``False``
        otherwise.
    """
    user = request.User
    if not serial:
        serial = get_required(request.all_data, "serial")
    g.audit_object.log({"serial": serial})
    otp1 = get_required(request.all_data, "otp1")
    otp2 = get_required(request.all_data, "otp2")

    res = resync_token(serial, otp1, otp2, user=user)
    g.audit_object.log({"success": bool(res)})
    return send_result(res)


@token_blueprint.route('/setpin', methods=['POST'])
@token_blueprint.route('/setpin/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=PolicyAction.SETPIN)
@prepolicy(encrypt_pin, request)
@prepolicy(check_otp_pin, request, action=PolicyAction.SETPIN)
@postpolicy(save_pin_change, request)
@event("token_setpin", request, g)
@log_with(log)
def setpin_api(serial=None):
    """
    Set one or more PINs on a token. Three PIN slots are supported:

    * ``userpin`` - the user PIN of a smartcard, also used by mOTP
      tokens to store the mOTP PIN.
    * ``sopin`` - the security-officer PIN of a smartcard.
    * ``otppin`` - the regular OTP PIN that gates token use.

    Each supplied field is set independently; omitted fields are
    untouched.

    Requires authentication and the policy action ``setpin``.

    :param serial: optional path component, the token serial.
    :jsonparam serial: token serial (required if not in the path).
    :jsonparam userpin: smartcard user PIN.
    :jsonparam sopin: smartcard SO PIN.
    :jsonparam otppin: OTP PIN.
    :jsonparam encryptpin: ``True`` to store the OTP PIN encrypted
        (default behavior is governed by the ``encrypt_pin`` policy).
    :status 200: number of PINs set in ``result.value``.
    """
    if not serial:
        serial = get_required(request.all_data, "serial")
    g.audit_object.log({"serial": serial})
    userpin = get_optional(request.all_data, "userpin")
    sopin = get_optional(request.all_data, "sopin")
    otppin = get_optional(request.all_data, "otppin")
    user = request.User
    encrypt_pin_param = get_optional(request.all_data, "encryptpin")

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
@prepolicy(check_token_action, request, action=PolicyAction.SETRANDOMPIN)
@prepolicy(set_random_pin, request)
@prepolicy(encrypt_pin, request)
@postpolicy(save_pin_change, request)
@event("token_setrandompin", request, g)
@log_with(log)
def setrandompin_api(serial=None):
    """
    Generate a random OTP PIN and set it on the token. The PIN
    length and content rules come from the ``otp_pin_set_random``
    policy; if that policy is not configured the call fails.

    The freshly generated PIN is included in the response under
    ``detail.pin`` so that the calling principal can show or relay
    it once. Treat the response body accordingly - do not log or
    persist it past handing it to the user.

    Requires authentication and the policy action ``setrandompin``.

    :param serial: optional path component, the token serial.
    :jsonparam serial: token serial (required if not in the path).
    :jsonparam encryptpin: ``True`` to store the PIN encrypted
        (default behavior is governed by the ``encrypt_pin`` policy).
    :status 200: number of PINs set in ``result.value``; the
        generated PIN is in ``detail.pin``.
    """
    if not serial:
        serial = get_required(request.all_data, "serial")
    g.audit_object.log({"serial": serial})
    user = request.User
    encrypt_pin_param = get_optional(request.all_data, "encryptpin")
    pin = get_optional(request.all_data, "pin")
    if not pin:
        raise TokenAdminError(
            "We have an empty PIN. Please check your policy 'otp_pin_set_random'.")

    g.audit_object.add_to_log({'action_detail': "otppin (random), "})
    res = set_pin(serial, pin, user=user, encrypt_pin=encrypt_pin_param)
    g.audit_object.log({"success": True})
    return send_result(res, details={"pin": pin})


@token_blueprint.route('/description', methods=['POST'])
@token_blueprint.route('/description/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=PolicyAction.SETDESCRIPTION)
@event("token_set", request, g)
@log_with(log)
def set_description_api(serial=None):
    """
    Set the description of a token. May be required by the
    ``require_description_on_edit`` policy.

    Requires authentication and the policy action ``setdescription``.

    :param serial: optional path component, the token serial.
    :jsonparam serial: token serial (required if not in the path).
    :jsonparam description: new description (required).
    :status 200: ``True`` on success in ``result.value``.
    """
    user = request.User
    if not serial:
        serial = get_required(request.all_data, "serial")
    g.audit_object.log({"serial": serial})
    description = get_required(request.all_data, "description", allow_empty=True)
    g.audit_object.add_to_log({'action_detail': f"description={description!r}"})
    token = get_one_token(serial=serial, user=user)
    request.all_data["type"] = token.type
    require_description_on_edit(request)
    res = set_description(serial, description, user=user, token=token)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/set', methods=['POST'])
@token_blueprint.route('/set/<serial>', methods=['POST'])
@admin_required
@prepolicy(check_token_action, request, action=PolicyAction.SET)
@event("token_set", request, g)
@log_with(log)
def set_api(serial=None):
    """
    Admin-only. Set one or more low-level token attributes on a
    token (or on every token of a user). Each supplied field is
    applied independently; omitted fields are untouched.

    Requires admin authentication and the policy action ``set``.

    :param serial: optional path component, the token serial.
    :jsonparam serial: token serial (alternative to the path
        component). Either ``serial`` or ``user`` is required; with
        ``user`` and no serial, every token of that user is
        modified.
    :jsonparam user: login name.
    :jsonparam realm: realm of the user.
    :jsonparam description: free-form description.
    :jsonparam count_window: counter look-ahead window (HOTP).
    :jsonparam sync_window: synchronization window.
    :jsonparam count_auth_max: maximum authentication count before
        the token is locked.
    :jsonparam count_auth_success_max: maximum number of successful
        authentications before the token is locked.
    :jsonparam hashlib: HMAC hash algorithm (``sha1``, ``sha256``,
        ``sha512``).
    :jsonparam max_failcount: maximum allowed failed authentications.
    :jsonparam validity_period_start: ISO 8601 start of validity
        (``YYYY-MM-DDThh:mm+oooo``).
    :jsonparam validity_period_end: ISO 8601 end of validity.
    :status 200: number of attribute updates applied in
        ``result.value``.
    """
    if not serial:
        serial = get_required(request.all_data, "serial")
    g.audit_object.log({"serial": serial})
    user = request.User

    description = get_optional(request.all_data, "description")
    count_window = get_optional(request.all_data, "count_window")
    sync_window = get_optional(request.all_data, "sync_window")
    hashlib = get_optional(request.all_data, "hashlib")
    max_failcount = get_optional(request.all_data, "max_failcount")
    count_auth_max = get_optional(request.all_data, "count_auth_max")
    count_auth_success_max = get_optional(request.all_data, "count_auth_success_max")
    validity_period_start = get_optional(request.all_data, "validity_period_start")
    validity_period_end = get_optional(request.all_data, "validity_period_end")

    res = 0

    if description is not None:
        g.audit_object.add_to_log({'action_detail': f"description={description!r}, "})
        res += set_description(serial, description, user=user)

    if count_window is not None:
        g.audit_object.add_to_log({'action_detail': f"count_window={count_window!r}, "})
        res += set_count_window(serial, count_window, user=user)

    if sync_window is not None:
        g.audit_object.add_to_log({'action_detail': f"sync_window={sync_window!r}, "})
        res += set_sync_window(serial, sync_window, user=user)

    if hashlib is not None:
        g.audit_object.add_to_log({'action_detail': f"hashlib={hashlib!r}, "})
        res += set_hashlib(serial, hashlib, user=user)

    if max_failcount is not None:
        g.audit_object.add_to_log({'action_detail': f"max_failcount={max_failcount!r}, "})
        res += set_max_failcount(serial, max_failcount, user=user)

    if count_auth_max is not None:
        g.audit_object.add_to_log({'action_detail': f"count_auth_max={count_auth_max!r}, "})
        res += set_count_auth(serial, count_auth_max, user=user, max=True)

    if count_auth_success_max is not None:
        g.audit_object.add_to_log({'action_detail':
                                       f"count_auth_success_max={count_auth_success_max!r}, "})
        res += set_count_auth(serial, count_auth_success_max, user=user,
                              max=True, success=True)

    if validity_period_end is not None:
        g.audit_object.add_to_log({'action_detail':
                                       f"validity_period_end={validity_period_end!r}, "})
        res += set_validity_period_end(serial, user, validity_period_end)

    if validity_period_start is not None:
        g.audit_object.add_to_log({'action_detail':
                                       f"validity_period_start={validity_period_start!r}, "})
        res += set_validity_period_start(serial, user, validity_period_start)

    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/realm/<serial>', methods=['POST'])
@admin_required
@log_with(log)
@prepolicy(check_max_token_realm, request)
@prepolicy(check_admin_tokenlist, request, action=PolicyAction.TOKENREALMS)
@prepolicy(check_token_action, request, action=PolicyAction.TOKENREALMS)
@event("token_realm", request, g)
def tokenrealm_api(serial=None):
    """
    Replace the realms a token belongs to. The full set of realms is
    replaced - realms not listed in the request are removed. For
    realm-admin callers, the call is restricted to realms the
    caller's policies cover.

    Requires admin authentication and the policy action
    :ref:`policy_tokenrealms`. Subject to the per-realm token-count
    limit (``check_max_token_realm``).

    :param serial: path component, the token serial.
    :jsonparam realms: comma-separated string or JSON list of realm
        names (required; empty list removes all realms).
    :status 200: ``True`` on success in ``result.value``.

    **Example request**:

    .. sourcecode:: http

       POST /token/realm/<serial> HTTP/1.1
       Host: example.com
       Content-Type: application/json

       {"realms": "realm1,realm2"}
    """
    realms = get_required(request.all_data, "realms")
    if isinstance(realms, list):
        realm_list = realms
    else:
        realm_list = [r.strip() for r in realms.split(",")]
    g.audit_object.log({"serial": serial})

    allowed_realms = getattr(request, "pi_allowed_realms", None)

    set_realms(serial, realms=realm_list, allowed_realms=allowed_realms)
    g.audit_object.add_to_log({'action_detail': f"realms={realm_list}, "})
    g.audit_object.log({"success": True})
    return send_result(True)


@token_blueprint.route('/load/<filename>', methods=['POST'])
@admin_required
@log_with(log)
@prepolicy(check_token_upload, request)
@event("token_load", request, g)
def loadtokens_api(filename=None):
    """
    Bulk-import tokens from a file. Accepts OATH CSV, Aladdin XML,
    Yubikey CSV (as exported by the Yubikey initialization tool) and
    PSKC. PGP-encrypted files (``-----BEGIN PGP MESSAGE-----``
    header) are decrypted in-place using the configured GPG keyring
    before parsing.

    The request body must be ``multipart/form-data`` with the file in
    the ``file`` field; the path component ``filename`` is used only
    for logging.

    Requires admin authentication and the import policy in scope
    ADMIN. The check honors the supplied ``tokenrealms``: the admin
    must be allowed to import into every named realm.

    :param filename: path component, used as a log/audit label for
        the imported file.
    :reqheader Content-Type: ``multipart/form-data`` (required).
    :formparam file: the file contents (required).
    :jsonparam type: file format - ``aladdin-xml``, ``oathcsv``
        (alias ``OATH CSV``), ``yubikeycsv`` (alias ``Yubikey CSV``),
        or ``pskc`` (required).
    :jsonparam tokenrealms: comma-separated list of realms to assign
        the imported tokens to.
    :jsonparam psk: Pre-Shared Key for PSKC import (32 hex
        characters / 128 bits).
    :jsonparam password: passphrase for PSKC import when keys are
        password-derived.
    :jsonparam pskcValidateMAC: PSKC MAC handling - ``no_check``
        skips MAC verification, ``check_fail_soft`` warns,
        ``check_fail_hard`` (default) rejects on bad MAC.
    :status 200: ``{"n_imported": <int>, "n_not_imported": <int>}``
        in ``result.value``.
    :status 400: empty file, undecodable file, unknown ``type``, or
        bad pre-shared-key length.
    """
    if not filename:
        filename = get_required(request.all_data, "filename")
    known_types = ['aladdin-xml', 'oathcsv', "OATH CSV", 'yubikeycsv',
                   'Yubikey CSV', 'pskc']
    file_type = get_required(request.all_data, "type")
    aes_validate_mac = get_optional(request.all_data, "pskcValidateMAC", default='check_fail_hard')
    aes_psk = get_optional(request.all_data, "psk")
    aes_password = get_optional(request.all_data, "password")
    if aes_psk and len(aes_psk) != 32:
        raise TokenAdminError(_("The Pre Shared Key must be 128 Bit hex "
                                "encoded. It must be 32 characters long!"))
    trealms = get_optional(request.all_data, "tokenrealms") or ""
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
        raise ParameterError(_("Unable to convert file contents. Binary data is not supported"))

    if file_contents == "":
        log.error(f"Error loading/importing token file. File {filename} is empty!")
        raise ParameterError(_("Error loading token file. File empty!"))

    if file_type not in known_types:
        log.error(f"Unknown file type: '{file_type}'. Supported types are: "
                  f"{', '.join(known_types)}")
        raise TokenAdminError(
            _("Unknown file type: '{file_type}'. Supported file types are: {known_types}")
            .format(file_type=file_type, known_types=', '.join(known_types))
        )

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

    return send_result(
        {'n_imported': len(import_tokens), 'n_not_imported': len(not_imported_serials)})


@token_blueprint.route('/copypin', methods=['POST'])
@admin_required
@log_with(log)
@prepolicy(check_base_action, request, action=PolicyAction.COPYTOKENPIN)
@event("token_copypin", request, g)
def copypin_api():
    """
    Copy the OTP PIN of one token onto another. Used by helpdesk
    flows where a replacement token is issued without forcing the
    user to set a new PIN.

    Requires admin authentication and the policy action
    :ref:`policy_copytokenpin`. The check is global rather than
    realm-scoped, so an admin holding ``copytokenpin`` can copy a
    PIN between tokens regardless of which realms those tokens
    belong to.

    :jsonparam from: serial of the source token (required).
    :jsonparam to: serial of the destination token (required).
    :status 200: ``True`` on success in ``result.value``.
    """
    serial_from = get_required(request.all_data, "from")
    serial_to = get_required(request.all_data, "to")
    res = copy_token_pin(serial_from, serial_to)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/copyuser', methods=['POST'])
@admin_required
@prepolicy(check_base_action, request, action=PolicyAction.COPYTOKENUSER)
@event("token_copyuser", request, g)
@log_with(log)
def copyuser_api():
    """
    Copy the user assignment of one token onto another. Used by
    helpdesk flows where a replacement token must inherit the
    original token's owner without re-running the assign workflow.

    Requires admin authentication and the policy action
    :ref:`policy_copytokenuser`. The check is global rather than
    realm-scoped; see ``copypin`` above for the same caveat.

    :jsonparam from: serial of the source token (required).
    :jsonparam to: serial of the destination token (required).
    :status 200: ``True`` on success in ``result.value``.
    """
    serial_from = get_required(request.all_data, "from")
    serial_to = get_required(request.all_data, "to")
    res = copy_token_user(serial_from, serial_to)
    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/lost/<serial>', methods=['POST'])
@prepolicy(check_token_action, request, action=PolicyAction.LOSTTOKEN)
@event("token_lost", request, g)
@log_with(log)
def lost_api(serial=None):
    """
    Mark a token as lost and issue a temporary replacement. The
    replacement carries a derived serial (``lost<original-serial>``),
    a generated password, the original token's PIN, and a limited
    validity period. The original token is disabled.

    Callable by both admins and users; user-role callers may only
    operate on their own tokens (the view enforces ownership).

    Requires authentication and the policy action ``losttoken``.

    :param serial: path component, the serial of the lost token.
    :status 200: dict carrying the new serial, the temporary
        password, and the validity window in ``result.value``.
    """
    # check if a user is given, that the user matches the token owner.
    g.audit_object.log({"serial": serial})
    userobj = request.User
    if userobj:
        toks = get_tokens(serial=serial, user=userobj)
        if not toks:
            raise TokenAdminError(_("The user {0!r} does not own the token {1!s}").format(
                userobj, serial))

    options = {"g": g,
               "clientip": g.client_ip}
    res = lost_token(serial, options=options)

    g.audit_object.log({"success": True})
    return send_result(res)


@token_blueprint.route('/getserial/<otp>', methods=['GET'])
@admin_required
@prepolicy(check_base_action, request, action=PolicyAction.GETSERIAL)
@event("token_getserial", request, g)
@log_with(log)
def get_serial_by_otp_api(otp=None):
    """
    Identify a token by an OTP value. Useful when an admin holds an
    unlabeled token and wants to know which token (and therefore
    which user) it belongs to.

    Requires admin authentication and the policy action
    :ref:`policy_getserial`.

    :param otp: path component, the observed OTP value.
    :query type: limit the search to this token type.
    :query serial: substring filter against token serials (e.g.
        ``OATH``).
    :query unassigned: ``1`` to search only unassigned tokens.
    :query assigned: ``1`` to search only assigned tokens.
    :query count: ``1`` to return only the number of tokens that
        would be searched, without performing the OTP check.
    :query window: OTP look-ahead window, default ``10``.
    :status 200: ``{"serial": <serial-or-null>, "count": <int>}`` in
        ``result.value``.
    """
    ttype = get_optional(request.all_data, "type")
    unassigned_param = get_optional(request.all_data, "unassigned")
    assigned_param = get_optional(request.all_data, "assigned")
    serial_substr = get_optional(request.all_data, "serial")
    count_only = get_optional(request.all_data, "count")
    window = int(get_optional(request.all_data, "window", default=10))

    serial_substr = serial_substr or ""

    serial = None
    assigned = None
    if unassigned_param:
        assigned = False
    if assigned_param:
        assigned = True

    count = get_tokens(tokentype=ttype, serial_wildcard=f"*{serial_substr!s}*", assigned=assigned, count=True)
    if not count_only:
        tokenobj_list = get_tokens(tokentype=ttype,
                                   serial_wildcard=f"*{serial_substr!s}*",
                                   assigned=assigned)
        serial = get_serial_by_otp(tokenobj_list, otp=otp, window=window)

    g.audit_object.log({"success": True,
                        "info": f"get {serial!s} by OTP. {count!s} tokens"})

    return send_result({"serial": serial,
                        "count": count})


@token_blueprint.route('/info/<serial>/<key>', methods=['POST'])
@admin_required
@prepolicy(check_token_action, request, action=PolicyAction.SETTOKENINFO)
@event("token_info", request, g)
@log_with(log)
def set_tokeninfo_api(serial, key):
    """
    Set a single tokeninfo entry on a token. If an entry with this
    key already exists, the value is overwritten.

    Requires admin authentication and the policy action
    ``settokeninfo``.

    :param serial: path component, the token serial.
    :param key: path component, the tokeninfo key.
    :jsonparam value: tokeninfo value to set (required).
    :status 200: ``True`` on success in ``result.value``.
    """
    value = get_required(request.all_data, "value")
    g.audit_object.log({"serial": serial})
    count = add_tokeninfo(serial, key, value)
    success = count > 0
    g.audit_object.log({"success": success})
    return send_result(success)


@token_blueprint.route('/info/<serial>/<key>', methods=['DELETE'])
@admin_required
@prepolicy(check_token_action, request, action=PolicyAction.SETTOKENINFO)
@event("token_info", request, g)
@log_with(log)
def delete_tokeninfo_api(serial, key):
    """
    Delete a tokeninfo entry from a token.

    Requires admin authentication and the policy action
    ``settokeninfo``.

    :param serial: path component, the token serial.
    :param key: path component, the tokeninfo key.
    :status 200: ``True`` if a matching token existed (which does
        not necessarily mean the key was set on it), ``False``
        otherwise.
    """
    g.audit_object.log({"serial": serial})
    count = delete_tokeninfo(serial, key)
    success = count > 0
    g.audit_object.log({"success": success})
    return send_result(success)


@token_blueprint.route('/group/<serial>/<groupname>', methods=['POST'])
@token_blueprint.route('/group/<serial>', methods=['POST'])
@admin_required
@prepolicy(check_token_action, request, PolicyAction.TOKENGROUPS)
@event("token_assign_group", request, g)
@log_with(log)
def assign_tokengroup_api(serial, groupname=None):
    """
    Modify the tokengroup membership of a token. The endpoint has
    two shapes:

    * with the ``<groupname>`` path component, the named tokengroup
      is added to the token (additive, single membership).
    * without the path component, the body must carry ``groups`` -
      the token's membership is **replaced** with that list, so any
      tokengroup not in ``groups`` is removed.

    Requires admin authentication and the policy action
    ``tokengroups``.

    :param serial: path component, the token serial.
    :param groupname: optional path component - if present, add this
        tokengroup; if absent, replace membership from ``groups``.
    :jsonparam groups: list (or comma-separated string) of
        tokengroup names. Required when ``groupname`` is omitted;
        ignored otherwise.
    :status 200: ``1`` in ``result.value``.
    """
    g.audit_object.log({"serial": serial})
    if groupname:
        g.audit_object.add_to_log({'action_detail': groupname})
        assign_tokengroup(serial, tokengroup=groupname)
    else:
        groups = get_required(request.all_data, "groups")
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
@prepolicy(check_token_action, request, PolicyAction.TOKENGROUPS)
@event("token_unassign_group", request, g)
@log_with(log)
def unassign_tokengroup_api(serial, groupname):
    """
    Remove a single tokengroup from a token.

    Requires admin authentication and the policy action
    ``tokengroups``.

    :param serial: path component, the token serial.
    :param groupname: path component, the tokengroup name.
    :status 200: ``1`` in ``result.value``.
    """
    g.audit_object.add_to_log({'action_detail': groupname})
    unassign_tokengroup(serial, tokengroup=groupname)
    g.audit_object.log({'success': True})
    return send_result(1)
