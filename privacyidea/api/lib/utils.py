#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
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
import functools
import json
import logging
import re
import secrets
import string
import threading
import time
from copy import copy
from urllib.parse import unquote

import jwt
from flask import jsonify, current_app, Response, Request, request, g, has_request_context
from flask_babel import _

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import (log_authentication_event, AuthLogUserRole,
                                                                   get_attempt_id_for_transaction)
from privacyidea.lib.user import User
# Re-exported from privacyidea.lib.params for backwards-compatibility with
# callers that import these names from privacyidea.api.lib.utils.
from privacyidea.lib.params import (  # noqa: F401
    _get_param,
    get_required,
    get_required_one_of,
    get_optional,
    get_optional_one_of,
    attestation_certificate_allowed,
)
# check_policy_name lives in lib/policy; re-exported here for backward compatibility
from privacyidea.lib.policy import check_policy_name  # noqa: F401
from privacyidea.lib.utils import prepare_result, get_version, to_unicode, get_plugin_info_from_useragent
from ...lib.error import (PolicyError, ResourceNotFoundError,
                          PrivacyIDEAError, AuthError, Error)
from ...lib.log import log_with

log = logging.getLogger(__name__)
ENCODING = "utf-8"
TRUSTED_JWT_ALGOS = ["ES256", "ES384", "ES512",
                     "RS256", "RS384", "RS512",
                     "PS256", "PS384", "PS512"]

INTERNAL_OPTION_KEYS = frozenset({
    "session",                   # stamps a challenge as enrollment -> enroll_via_validate
    "data",                      # email/SMS concurrent_challenges OTP cache
    "initTime",                  # overrides server time -> strips the TOTP time window
    "radius_result",             # short-circuits the real RADIUS Access-Request
    "radius_state",              # RADIUS intra-request state
    # NOTE: "challenge" is intentionally NOT stripped — it is a legitimate OCRA/DisplayTAN
    # client input (the transaction to sign, read by ocratoken.create_challenge); on the
    # transaction_id path check_challenge_response overwrites it from the stored challenge,
    # so it cannot be used to bypass authentication.
    "push_triggered",            # set by create_challenges_from_tokens
    "valid_token_num",           # server-set count of already-valid tokens (check_token_list -> pushtoken)
})

# The following user-agents (with versions) do not need extra unquoting
# TODO: we should probably switch this when we do not do the extra unquote anymore
NO_UNQUOTE_USER_AGENTS = {
    'privacyidea-cp': None,
    'privacyidea-ldap-proxy': None,
    'simplesamlphp': None
}

SESSION_KEY_LENGTH = 32


def generate_attempt_id() -> str:
    """
    Mint a fresh attempt id: 128-bit cryptographically random hex string (32 hex chars).

    Each logical authentication attempt (which may span multiple HTTP requests in challenge / multichallenge flows)
    shares the same attempt id. The high entropy avoids silent collision across the retained authentication log.
    """
    return secrets.token_hex(16)


def resolve_attempt_id(request: Request | None, transaction_id: str | None = None) -> str:
    """
    Determine the per-attempt correlation id for the authentication-log row of the current request.

    All rows of one logical authentication attempt share an ``attempt_id`` so a policy can count *attempts* rather
    than individual log rows (a challenge / multichallenge attempt spans several requests, hence several rows). The id
    is derived entirely from the durable authentication log, so nothing has to be stored on the (ephemeral) challenge:

    * A request that carries no ``transaction_id`` / ``state`` starts a new attempt and gets a freshly minted id.
    * A request answering a previously triggered challenge carries that challenge's ``transaction_id``. The trigger
      request already wrote a row with both that ``transaction_id`` and the ``attempt_id``, so the attempt is
      recovered from it (:func:`~privacyidea.lib.conditional_access.authentication_log.get_attempt_id_for_transaction`)
      and every row of the attempt shares one id. ``state`` is the RADIUS alias of ``transaction_id``.

    The **client-sent** transaction id takes precedence: for a multichallenge continuation the row's own
    *transaction_id* is the freshly minted next challenge (no attempt row yet), while the request still carries the
    *answered* one, which is the correct grouping key. When the request carries none, the row's own *transaction_id*
    is used as a fallback — this is what groups a challenge resolved inside its own triggering request (push_wait
    logs both the trigger and the terminal row on one request that has no transaction_id of its own).

    A missing or legacy trigger row (no stored ``attempt_id``) falls back to a fresh id, so every new row is grouped
    as at least its own attempt rather than left ungrouped.

    :param request: the current request, or ``None`` when logging outside a request
    :param transaction_id: the transaction_id being written on this row, used as the lookup key when the request
        itself carries none
    :return: the attempt id to store on this request's authentication-log row
    """
    request_transaction_id = None
    if request is not None:
        request_data = getattr(request, "all_data", {})
        request_transaction_id = (get_optional(request_data, "transaction_id")
                                  or get_optional(request_data, "state"))
    lookup_transaction_id = request_transaction_id or transaction_id
    if lookup_transaction_id:
        existing = get_attempt_id_for_transaction(lookup_transaction_id)
        if existing:
            return existing
    return generate_attempt_id()


def send_result(obj, rid=1, details=None, **kwargs) -> Response:
    """
    sendResult - return a json result document

    :param obj: simple result object like dict, sting or list
    :type obj: dict or list or string/unicode
    :param rid: id value, for future versions
    :type rid: int
    :param details: optional parameter, which allows to provide more detail
    :type  details: None or simple type like dict, list or string/unicode

    :return: json rendered string result
    :rtype: string
    """
    return jsonify(prepare_result(obj, rid, details, **kwargs))


def send_error(errstring, rid=1, context=None, error_code=-311, details=None):
    """
    sendError - return a json error result document

    remark:
     the 'context' is especially required to catch errors from the _before_
     methods. The return of a _before_ must be of type response and
     must have the attribute response._exception set, to stop further
     processing, which otherwise will have ugly results!!

    :param errstring: An error message
    :type errstring: basestring
    :param rid: id value, for future versions
    :type rid: int
    :param context: default is None or 'before'
    :type context: string
    :param error_code: The error code in the JSON object along with the error
    message.
    :type error_code: int
    :param details: dict with additional details about the error (like
        challenges)
    :type details: dict

    :return: json rendered sting result
    :rtype: string

    """
    if details:
        details["threadid"] = threading.current_thread().ident
    res = {"jsonrpc": "2.0",
           "detail": details,
           "result": {"status": False,
                      "error": {"code": error_code,
                                "message": errstring}
                      },
           "version": get_version(),
           "id": rid,
           "time": time.time()
           }

    ret = jsonify(res)
    return ret


def send_html(output):
    """
    Send the output as HTML to the client with the correct mimetype.

    :param output: The HTML to send to the client
    :type output: str
    :return: The generated response
    :rtype: flask.Response
    """
    return current_app.response_class(output, mimetype='text/html')


def send_file(output, filename, content_type='text/csv'):
    """
    Send the output to the client with the "Content-disposition" header to
    declare it as a downloadable file.

    :param output: The data that should be sent as a file
    :type output: str
    :param filename: The proposed filename
    :type filename: str
    :param content_type: The proposed content type of the data
    :type content_type: str (should be something from this list:
                             https://www.iana.org/assignments/media-types/media-types.xhtml)
    :return: The generated response
    :rtype: flask.Response
    """
    headers = {'Content-disposition': f'attachment; filename={filename!s}'}
    return current_app.response_class(output, headers=headers, mimetype=content_type)


def send_csv_result(obj, data_key="tokens",
                    filename="privacyidea-tokendata.csv"):
    """
    returns a CSV document of the input data (like in /token/list)

    It takes an obj as a dict like:
    { "tokens": [ { ...token1... }, { ...token2....}, ... ],
      "count": 100,
      "....": .... }

    :param obj: The data, that gets serialized as CSV
    :type obj: dict
    :param data_key: The key, from which the list should be returned as CSV.
    Usually this is "tokens".
    :type data_key: basestring
    :param filename: The filename to save the CSV to.
    :type filename: basestring
    :return: The result serialized as a CSV
    :rtype: Response object
    """
    delim = "'"
    output = ""
    # check if there is any data
    if data_key in obj and len(obj[data_key]) > 0:
        # Do the header
        for k, _v in obj.get(data_key)[0].items():
            output += f"{delim!s}{k!s}{delim!s}, "
        output += "\n"

        # Do the data
        for row in obj.get(data_key):
            for val in row.values():
                if isinstance(val, str):
                    value = val.replace("\n", " ")
                else:
                    value = val
                output += f"{delim!s}{value!s}{delim!s}, "
            output += "\n"

    return send_file(output, filename)


@log_with(log)
def getLowerParams(param):
    ret = {}
    for key in param:
        lkey = key.lower()
        # strip the session parameter!
        if "session" != lkey:
            lval = param[key]
            ret[lkey] = lval
    return ret


def _determine_user_role(user: User | None, internal_admin: bool) -> AuthLogUserRole:
    """
    Classify the authenticating principal for the authentication log. A local database admin is only knowable at the
    caller (``/auth`` via ``verify_db_admin``/``db_admin_exists``) and is signalled by *internal_admin*. Otherwise a
    user whose realm is a configured ``SUPERUSER_REALM`` is an external (admin-realm) admin; everyone else is a
    regular user. The superuser realms are only readable inside an app context, so outside one the principal is
    treated as a regular user (the only events logged outside a request are user token flows, e.g. push_wait).
    """
    if internal_admin:
        return AuthLogUserRole.ADMIN_INTERNAL
    if user and user.realm and has_request_context():
        superuser_realms = [realm.lower() for realm in current_app.config.get("SUPERUSER_REALM", [])]
        if user.realm.lower() in superuser_realms:
            return AuthLogUserRole.ADMIN_EXTERNAL
    return AuthLogUserRole.USER


def log_authentication(event_type: AuthEventType | None, request: Request | None = None, user: User | None = None,
                       serial: str | None = None, transaction_id: str | None = None,
                       username: str | None = None,
                       internal_admin: bool = False, attempt_id: str | None = None) -> int | None:
    """
    Write one authentication_log entry for the current request.

    This is the single API-layer persistence point: the lib layer classifies
    the outcome and the views call this to record it. ``source_ip`` uses the
    same client-IP resolution as the audit log; ``client_label`` is the
    ``client_id`` parameter if supplied, otherwise the User-Agent header.

    The ``(resolver, uid, realm)`` identity tuple is only written for a resolved
    user; an unresolvable user (e.g. USER_UNKNOWN) is logged with resolver and uid
    None while realm and username are still captured from the User object.

    ``username`` overrides the login name derived from the User object. It is needed for
    local administrators, who have no User object (the login name is not stored there) but
    whose login name should still be recorded.

    Some requests identify a token but not its user (e.g. the smartphone ``/ttype/push`` confirm carries only the
    serial). In that case the token owner is resolved from the serial, so a row that names a single token always also
    records that token's user, keeping the log symmetric.

    ``source_ip`` (from ``g``) and ``client_label`` (from ``request``) are only read inside a request context, so the
    lib layer can record an event from outside a view (e.g. push_wait). Worst case those two columns are empty; the
    event itself is never lost.

    ``user_role`` records whether the principal is a regular user or an admin (see :class:`AuthLogUserRole`). Pass
    ``internal_admin=True`` for a local database admin (``/auth`` only); an admin-realm admin is detected from the
    user's realm, so the caller need not flag it.

    ``attempt_id`` groups all rows of one logical authentication attempt (see :func:`resolve_attempt_id`). When not
    given it is resolved automatically from the request: minted fresh for an initial request, or recovered from the
    answered challenge's trigger row for a follow-up. Pass it explicitly only when the answered ``transaction_id`` is
    not carried on the request (e.g. the out-of-band push answer at ``/ttype/push``).
    """
    if not event_type:
        log.debug("Not logging authentication event, because no event type is given.")
        return
    if attempt_id is None:
        attempt_id = resolve_attempt_id(request, transaction_id)
    client_label = None
    source_ip = None
    if has_request_context():
        source_ip = g.client_ip
        if request is not None:
            client_label = get_optional(request.all_data, "client_id") or (request.user_agent.string or None)
    # TODO: replace by user function (after related PR is merged)
    resolved = bool(user and user.resolver)
    if not resolved and serial and "," not in serial:
        # The request carried a single serial but no (resolved) user. Resolve the token owner so the user is logged
        # alongside the serial. A failure here must not break the logging, so it is swallowed.
        try:
            from privacyidea.lib.token import get_one_token
            token = get_one_token(serial=serial, silent_fail=True)
            if token is not None and token.user and token.user.resolver:
                user = token.user
                resolved = True
        except Exception as ex:
            log.debug(f"Could not resolve the token owner for the authentication log: {ex!r}")
    return log_authentication_event(
        event_type=event_type,
        transaction_id=transaction_id,
        resolver=user.resolver if resolved else None,
        uid=user.uid if resolved else None,
        realm=(user.realm or None) if user else None,
        username=username or ((user.login or None) if user else None),
        user_role=_determine_user_role(user, internal_admin),
        source_ip=source_ip,
        client_label=client_label,
        serial=serial,
        attempt_id=attempt_id,
    )


def conditional_access_precheck(user) -> "Response | None":
    """
    Reject a request pre-auth (before any token logic and before the failcounter /
    max_auth checks) when conditional-access policies forbid it. Returns a generic
    failure :class:`~flask.Response` to be returned to the client, or ``None`` to
    continue with the normal flow.

    The rejection is deliberately generic and leaks no reason: the machine-facing
    API response never reveals that the user is locked, the source IP is blocked,
    or a policy denied access — the real reason is recorded only in the audit log.

    A currently-locked user is rejected first, then a source IP blocked by a
    ``BLOCK_IP`` action. The pre-auth conditional-access DENY decision is evaluated
    last, after the lock/block pre-checks (so an ALLOW cannot override them); a
    DENY rejects this single request without persisting state, while
    ALLOW / CONTINUE fall through. ``g.client_ip`` is the source IP checked.
    """
    # Imported lazily: this module is loaded early, while the engine pulls in the
    # ORM models, so a module-level import would risk an import-order cycle.
    from privacyidea.lib.conditional_access.engine import (is_user_locked, is_ip_blocked,
                                                           evaluate_access_decision, AccessDecision)
    if is_user_locked(user):
        log.info(f"Rejecting authentication for locked user {user!r}.")
        g.audit_object.log({"success": False,
                            "info": "Rejected: account is temporarily locked"})
        return send_result(False, rid=2, details={})
    if is_ip_blocked(g.client_ip):
        log.info(f"Rejecting authentication from blocked IP {g.client_ip!r}.")
        g.audit_object.log({"success": False,
                            "info": "Rejected: source IP is blocked"})
        return send_result(False, rid=2, details={})
    if evaluate_access_decision(user, g.client_ip) == AccessDecision.DENY:
        log.info(f"Denying authentication for {user!r} by conditional-access policy.")
        g.audit_object.log({"success": False,
                            "info": "Rejected: denied by conditional-access policy"})
        return send_result(False, rid=2, details={})
    return None


def conditional_access_gate(identity_resolver=None):
    """
    View decorator that runs :func:`conditional_access_precheck` before the
    decorated endpoint body (and, when placed above them, before the endpoint's
    pre-policies). If the pre-check rejects the request, its generic-failure
    response is returned immediately and the endpoint never runs.

    :param identity_resolver: an optional zero-argument callable returning the
        :class:`~privacyidea.lib.user.User` the pre-check should gate on. When
        omitted, ``request.User`` is used. Endpoints that must resolve the
        identity differently (a serial/credential-id request, or a transaction
        owner) pass their own resolver.
    """
    def decorator(wrapped_function):
        @functools.wraps(wrapped_function)
        def wrapper(*args, **kwargs):
            user = identity_resolver() if identity_resolver is not None else request.User
            rejection = conditional_access_precheck(user)
            if rejection is not None:
                return rejection
            return wrapped_function(*args, **kwargs)
        return wrapper
    return decorator


def conditional_access_posteval(user, event_type) -> None:
    """
    Run the conditional-access policy engine for this request's classified
    *event_type*, after the authentication-log row for it has been written (so a
    failure count over the log includes the just-written event). ``g.client_ip``
    is passed as the source IP for ``BLOCK_IP`` actions.

    This only produces side effects that the NEXT inbound request consults (it
    writes lockout state); it must never alter or break the response that already
    completed, so every error is swallowed.
    """
    from privacyidea.lib.conditional_access.engine import evaluate_lockout_policies
    from privacyidea.models import db
    try:
        # The engine commits its own writes (and rolls them back on failure), so
        # this caller must NOT wrap them in a transaction. Wrapping in
        # db.session.begin_nested() and then committing breaks under SQLAlchemy 2.x:
        # the engine's inner commit closes the transaction, so leaving the savepoint
        # context raises InvalidRequestError ("Can't operate on closed transaction
        # inside context manager") — which this caller would silently swallow.
        evaluate_lockout_policies(user, event_type, source_ip=g.client_ip)
    except Exception as ex:
        log.warning(f"Conditional-access policy evaluation failed: {ex!r}")
        # A failure may leave the session in an aborted state; clear it so request
        # teardown can proceed cleanly. Guard the rollback so this helper never
        # raises (it must never break the already-completed response).
        try:
            db.session.rollback()
        except Exception:
            pass


def check_unquote(request, data):
    """
    Check if we need to unquote the given data.
    Based on the user-agent header of the request we unquote the given values
    in `data`. The user-agent string parsing is based on
    https://httpwg.org/specs/rfc9110.html#field.user-agent

    :param request: The Flask request context
    :type request: Flask.Request
    :param data: The dictionary containing the requested data
    :type data: dict
    :return: New dictionary with the possibly unquoted values
    :rtype: dict
    """
    ua_name, ua_version, _ua_comment = get_plugin_info_from_useragent(request.user_agent.string)
    # if no user agent is available, we assume that we must unquote the data
    if not ua_name:
        return {key: unquote(value) for (key, value) in data.items()}

    if ua_name.lower() not in NO_UNQUOTE_USER_AGENTS:
        return {key: unquote(value) for (key, value) in data.items()}
    else:
        return copy(data)


def get_all_params(request):
    """
    Retrieve all parameters from a request, no matter if these are GET or POST requests
    or parameters are contained as viewargs like the serial in DELETE /token/<serial>

    :param request: The flask request object
    """
    param = request.values
    body = request.data
    return_param = {}
    if param:
        log.debug(f"Update params in request {request.method!s} {request.base_url!s} with values.")
        # Add the unquoted HTML and form parameters
        return_param = check_unquote(request, request.values)

    if request.is_json:
        log.debug(f"Update params in request {request.method!s} {request.base_url!s} with JSON data.")
        # Add the original JSON data
        return_param.update(request.json)
    elif body:
        # In case of serialized JSON data in the body, add these to the values.
        try:
            json_data = json.loads(to_unicode(body))
            for k, v in json_data.items():
                return_param[k] = v
        except Exception as exx:
            log.debug(f"Can not get param: {exx!s}")

    if request.view_args:
        log.debug(f"Update params in request {request.method!s} {request.base_url!s} with view_args.")
        # We add the unquoted view_args
        return_param.update(check_unquote(request, request.view_args))

    return return_param


def get_priority_from_param(param):
    """
    Return a dictionary of priorities as int from params like
    priority.key1=value1

    :param param: The params dictionary
    :type param: dict
    :return: dict
    """
    priority = {}
    for k, v in param.items():
        if k.startswith("priority.") and isinstance(v, int):
            priority[k[len("priority."):]] = int(v)
    return priority


def verify_auth_token(auth_token, required_role=None):
    """
    Check if a given auth token is valid.

    Return a dictionary describing the authenticated user.

    :param auth_token: The Auth Token
    :param required_role: list of "user" and "admin"
    :return: dict with authtype, realm, rights, role, username, exp, nonce
    :rtype: dict
    """
    r = None
    if required_role is None:
        required_role = ["admin", "user"]
    if auth_token is None:
        raise AuthError(_("Authentication failure. Missing Authorization header."), id=Error.AUTHENTICATE_AUTH_HEADER)

    try:
        headers = jwt.get_unverified_header(auth_token)
    except jwt.DecodeError as err:
        raise AuthError(_("Authentication failure. Error decoding the Authorization token:") + f" {err!s}",
                        id=Error.AUTHENTICATE_DECODING_ERROR)
    algorithm = headers.get("alg")
    wrong_username = None
    if algorithm in TRUSTED_JWT_ALGOS:
        # The trusted JWTs are RSA, PSS or elliptic curve signed
        trusted_jwts = current_app.config.get("PI_TRUSTED_JWT", [])
        for trusted_jwt in trusted_jwts:
            try:
                if trusted_jwt.get("algorithm") in TRUSTED_JWT_ALGOS:
                    j = jwt.decode(auth_token, trusted_jwt.get("public_key"), algorithms=[trusted_jwt.get("algorithm")])
                    if (dict((k, j.get(k)) for k in ("role", "resolver", "realm")) ==
                            dict((k, trusted_jwt.get(k)) for k in ("role", "resolver", "realm"))):
                        if re.match(trusted_jwt.get("username") + "$", j.get("username")):
                            r = j
                            break
                        else:
                            r = wrong_username = j.get("username")
                else:
                    log.warning("Unsupported JWT algorithm in PI_TRUSTED_JWT.")
            except jwt.ExpiredSignatureError as err:
                # We have the correct token. It expired, so we raise an error
                raise AuthError(_("Authentication failure. Your token has expired:") + f" {err!s}",
                                id=Error.AUTHENTICATE_TOKEN_EXPIRED)
            except jwt.InvalidTokenError:
                # Wrong signature, wrong/disallowed algorithm, malformed, ... -> this
                # definition simply does not match; try the next one.
                log.info("A given JWT definition does not match.")

    if not r:
        try:
            r = jwt.decode(auth_token, current_app.secret_key, algorithms=['HS256'])
        except jwt.ExpiredSignatureError as err:
            raise AuthError(_("Authentication failure. Your token has expired:") + f" {err!s}",
                            id=Error.AUTHENTICATE_TOKEN_EXPIRED)
        except jwt.InvalidTokenError as err:
            # Covers DecodeError as well as InvalidAlgorithmError (a token whose alg is a
            # trusted-JWT algorithm but matches no PI_TRUSTED_JWT entry decodes here against
            # HS256 and would otherwise raise InvalidAlgorithmError). Normalising every
            # invalid token to an AuthError keeps callers from leaking an HTTP 500.
            raise AuthError(_("Authentication failure. Error decoding the Authorization token:") + f" {err!s}",
                            id=Error.AUTHENTICATE_DECODING_ERROR)
    if wrong_username:
        raise AuthError(_("Authentication failure. The username {wrong_username} "
                          "is not allowed to impersonate via JWT.").format(wrong_username=wrong_username))
    if required_role and r.get("role") not in required_role:
        # If we require a certain role like "admin", but the users role does
        # not match
        raise AuthError(_("Authentication failure. You do not have the necessary "
                          "role ({required_role}) to access this resource!").format(required_role=required_role),
                        id=Error.AUTHENTICATE_MISSING_RIGHT)
    return r


def get_auth_token_from_request():
    """
    Return the auth token presented on the current request, looking at the
    ``PI-Authorization`` header first and falling back to ``Authorization``.

    :return: the token string, or None if neither header is set
    """
    return request.headers.get("PI-Authorization") or request.headers.get("Authorization")


def logged_in_user_from_token(token_payload):
    """
    Build the standard ``g.logged_in_user`` dict from a verified/decoded auth
    token payload.

    :param token_payload: the dict returned by ``verify_auth_token`` (or a
        decoded JWT) carrying ``username``, ``realm`` and ``role``
    :return: dict with ``username``, ``realm`` and ``role``
    """
    return {"username": token_payload.get("username"),
            "realm": token_payload.get("realm"),
            "role": token_payload.get("role")}


def is_fqdn(x):
    """
    Check whether a given string could plausibly be a FQDN.

    This checks, whether a string could be a FQDN. Please note, that this
    function will currently return true for plenty of strings, that are not
    actually valid FQDNs. This is expected. This function performs a simple
    plausibility check to ward against obvious mistakes, like a user
    accidentally putting in a full url with protocol. The caller should not
    rely on this function, if it is absolutely crucial, that the checked
    string is a valid FQDN. It is solely intended to be used to implement user
    convenience, by alerting the user early on, if they have misunderstood
    a particular fields purpose.

    :param x: String to check.
    :type x: basestring
    :return: Whether the given string may plausibly be a FQDN.
    :rtype: bool
    """
    return set(string.punctuation).intersection(x).issubset({'-', '.'})


def map_error_to_code(error: Exception, default: int = 500) -> int:
    error_mapping: dict[type[Exception], int] = {
        PrivacyIDEAError: 400,
        AuthError: 401,
        PolicyError: 403,
        ResourceNotFoundError: 404,
        NotImplementedError: 501,
    }
    # return the code for the closest ancestor that is in the map
    for cls in type(error).mro():
        if cls in error_mapping:
            return error_mapping[cls]
    return default
