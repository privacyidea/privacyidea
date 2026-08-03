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
# SPDX-FileCopyrightText: 2025 Paul Lettich <paul.lettich@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
from logging import Formatter
import logging
import functools
import inspect
import re
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode

log = logging.getLogger(__name__)


DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "detail": {
            "()": "privacyidea.lib.log.SecureFormatter",
            "format": "[%(asctime)s][%(process)d]"
                      "[%(thread)d][%(levelname)s]"
                      "[%(name)s:%(lineno)d] "
                      "%(message)s"
        }
    },
    "handlers": {
        "file": {
            "formatter": "detail",
            "class": "logging.handlers.RotatingFileHandler",
            "backupCount": 5,
            "maxBytes": 10000000,
            "level": logging.NOTSET,
            "filename": "/var/log/privacyidea/privacyidea.log"
        }
    },
    "loggers": {"privacyidea": {"handlers": ["file"],
                                "qualname": "privacyidea",
                                "level": logging.INFO}
                }
}

DOCKER_LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "container": {
            "()": "privacyidea.lib.log.SecureFormatter",
            "format": "[%(asctime)s.%(msecs)03d][%(process)d]"
                      "[%(thread)d][%(levelname)s][%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "stream": {
            "formatter": "container",
            "class": "logging.StreamHandler",
            "level": logging.NOTSET
        }
    },
    "loggers": {
        "privacyidea": {
            "handlers": ["stream"],
            "propagate": False,
            "level": logging.INFO
        }
    },
    "root": {
        "handlers": ["stream"],
        "level": logging.INFO
    }
}


class SecureFormatter(Formatter):

    def format(self, record):
        if 's_line' in record.__dict__ and '_called' not in record.__dict__:
            # rotating file handler calls "format" to check for its length before
            # emitting the actual line
            record.msg += f" (called from {record.filename}:{record.lineno})"
            record.lineno = record.__dict__["s_line"]
            record._called = True
        # Check for printable characters in output, unicode should be fine
        if not record.msg.isprintable():
            message = ''.join(map(lambda x: x if x.isprintable() else '.', record.msg))
            message = "!!Log Entry Secured by SecureFormatter!! " + message
            record.msg = message
        return super().format(record)


HIDDEN = "HIDDEN"

# Key names whose value is never written to the log. A name only has to be listed here once: the
# denylist is applied to every argument, keyword argument and result of every decorated function,
# at any nesting depth. Matching is case insensitive and ignores separators, so a name does not
# have to be repeated for each spelling used across the API.
SENSITIVE_KEY_NAMES = frozenset({
    # "anotpval" is the parameter holding the OTP in the check_otp signature of every token class.
    # It is listed literally because "otp" is too short to be matched inside a longer name.
    "anotpval",
    "answer", "answers", "authorization", "bindpw", "cakey", "cookie", "credential", "fbtoken",
    "key_enc", "key_iv", "otp", "otp1", "otp2", "otpkey", "otpvalue", "pass", "passphrase",
    "passw", "passwd", "password", "pin", "privatekey", "questions", "recoverycode", "secret",
    "session", "sshkey", "tans",
})

# Names that are only sensitive when they are the entire key. "verify" holds the OTP typed during
# verify-enrollment, but as a part of a name it belongs to flags such as "ssl_verify" or
# "verify_tls", which an admin needs to be able to read.
EXACT_ONLY_KEY_NAMES = frozenset({
    "verify",
})

# Names that the matching below would hide although they hold no secret. Keeping them readable
# matters, because they are the fields an admin reads while debugging a policy.
#
# Most of these are policy actions and configuration knobs named after the credential they govern
# rather than holding one: a minimum PIN length, whether to change a PIN, the name of a hash
# algorithm, the right to set a PIN. The list was built by running is_sensitive_key over every
# request parameter the code reads, every policy action name and every string used as a dict key
# in lib, so it is complete for the current vocabulary and has to be revisited when names are
# added. "2stepinit" is the warning in this list: it contains "pin" across the boundary of "step"
# and "init".
#
# A more durable answer would derive this from the policy action registry instead of listing it,
# since a policy action is by definition a setting and not a credential.
INSENSITIVE_KEY_NAMES = frozenset({
    "2stepinit",
    "change_pin_every",
    "change_pin_on_first_use",
    "change_pin_via_validate",
    "copytokenpin",
    "credential_id",
    "credentialid",
    "daypassword.hashlib",
    "daypassword.timestep",
    "encryptpin",
    "encrypt_pin",
    "enrollpin",
    "force_app_pin",
    "forward_authorization_token",
    "group_attribute_mapping_key",
    "mapping",
    "otp_pin_contents",
    "otp_pin_maxlength",
    "otp_pin_minlength",
    "otp_pin_random",
    "otp_pin_set_random",
    "otp_received",
    "otp_valid",
    "otpkeyformat",
    "passkey_trigger_by_pin",
    "passonnotoken",
    "passonnouser",
    "passphrase_prompt",
    "passphrase_user",
    "password_hash_type",
    "password_reset",
    "pin_scopes",
    "pinhandling",
    "pinode",
    "pinodes",
    "radius.local_checkpin",
    "registered_credential_ids",
    "remote.local_checkpin",
    "requestmapping",
    "responsemapping",
    "send_passphrase",
    "set_hsm_password",
    "setpin",
    "setrandompin",
    "webauthn_public_key_credential_algorithms",
})

# Names that are additionally searched for anywhere inside a key, so that a glued spelling such as
# "motppin" or "LDAPBINDPW" is recognised. Short names are excluded, because "otp" would hide
# "otplen" and "pass" would hide "bypass"; "pin" is the one deliberate exception, because
# "otppin", "userpin" and "sopin" all need it. Biased towards over-hiding: a benign field logged
# as HIDDEN costs a support engineer one question, a leaked credential costs a rotation.
MIN_FRAGMENT_LENGTH = 5
SENSITIVE_KEY_FRAGMENTS = frozenset(
    re.sub(r"[^a-z0-9]", "", name) for name in SENSITIVE_KEY_NAMES | {"pin"}
    if len(name) >= MIN_FRAGMENT_LENGTH or name == "pin"
)

# A redacted copy is built for every DEBUG log line, so the recursion is bounded to keep a
# pathological structure from costing more than the log line is worth.
MAX_REDACT_DEPTH = 8


def is_sensitive_value(value) -> bool:
    """
    Decide whether a value can hold a credential at all.

    Policy actions and configuration knobs are named after the credential they govern
    ("force_app_pin", "otp_pin_minlength", "change_pin_every", "passOnNoToken"), so the key alone
    cannot tell a credential from a setting. Their values are switches and numbers, and a switch is
    never a credential, so the type decides where the name cannot.

    :param value: The value belonging to a sensitive key
    :return: True if the value has to be hidden
    """
    return not isinstance(value, (bool, type(None)))


def is_sensitive_key(key) -> bool:
    """
    Decide whether the value belonging to ``key`` has to be hidden from the log.

    :param key: A mapping key or parameter name, of any type. Non-strings are never sensitive.
    :return: True if the value must not be logged
    """
    if not isinstance(key, str):
        return False
    normalized_key = key.strip().lower()
    if normalized_key in INSENSITIVE_KEY_NAMES:
        return False
    if normalized_key in SENSITIVE_KEY_NAMES or normalized_key in EXACT_ONLY_KEY_NAMES:
        return True
    # Split on separators and on camel case humps, so that "radius.secret", "LDAP_BINDPW" and the
    # older "anOtpVal" spelling are all recognised by their parts.
    word_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key.strip()).lower()
    if any(segment in SENSITIVE_KEY_NAMES for segment in re.split(r"[._\-\s]+", word_boundaries)):
        return True
    # Finally search the key with every separator removed, so that the result does not depend on
    # whether a name was written as "bindpw", "bind_pw", "bindPw" or "LDAPBINDPW".
    squashed_key = re.sub(r"[^a-z0-9]", "", normalized_key)
    return any(fragment in squashed_key for fragment in SENSITIVE_KEY_FRAGMENTS)


def _is_headers_like(value) -> bool:
    """
    Decide whether a value is a header container that should be walked like a mapping.

    Deliberately narrow: an arbitrary object exposing ``items`` may run a query or consume an
    iterator when it is called, and a value is only being logged here.

    :param value: The value to inspect
    :return: True if the value can be walked via items() safely
    """
    return type(value).__name__ in ("Headers", "EnvironHeaders", "ImmutableTypeConversionDict",
                                    "CombinedMultiDict", "MultiDict", "ImmutableMultiDict")


def redact_url(url: str) -> str:
    """
    Replace the value of every sensitive query parameter of a URL.

    A credential sent in the query string is part of the URL, so logging the URL logs the
    credential. Use this wherever a request path is written to the log.

    :param url: A URL or path, with or without a query string
    :return: The same URL with sensitive query parameter values replaced by "HIDDEN"
    """
    path, separator, query = url.partition("?")
    if not separator or not query:
        return url
    parameters = [(key, HIDDEN if is_sensitive_key(key) else value)
                  for key, value in parse_qsl(query, keep_blank_values=True)]
    return f"{path}?{urlencode(parameters)}"


def redact(value, depth: int = 0, _path_ids: frozenset = frozenset()):
    """
    Build a copy of ``value`` in which the value of every sensitive key is replaced by "HIDDEN".

    The original is never modified, so a decorated function still receives its untouched
    arguments. Containers are rebuilt instead of deep-copied, which means an argument holding an
    object that cannot be copied does not prevent its sibling arguments from being logged.

    :param value: Any value that is about to be written to the log
    :param depth: Current recursion depth
    :param _path_ids: Ids of the containers on the current path, to survive reference cycles
    :return: A redacted copy of value
    """
    if depth > MAX_REDACT_DEPTH:
        return "<max depth>"
    # Only exact built-in containers are rebuilt. A subclass may carry behaviour in its
    # constructor: rebuilding an ORM collection, for instance, fires the events that maintain the
    # relationship and would corrupt the object that is merely being logged.
    if type(value) in (dict, list, tuple, set, frozenset):
        if id(value) in _path_ids:
            return "<recursion>"
        _path_ids = _path_ids | {id(value)}
        if type(value) is dict:
            return {key: HIDDEN if is_sensitive_key(key) and is_sensitive_value(item)
                    else redact(item, depth + 1, _path_ids)
                    for key, item in value.items()}
        return type(value)(redact(item, depth + 1, _path_ids) for item in value)
    if isinstance(value, Mapping) or _is_headers_like(value):
        # Key/value containers that are not plain dicts, most importantly the request headers,
        # which carry the session token of whoever sent the request. The result is always a plain
        # dict, so no foreign constructor runs.
        if id(value) in _path_ids:
            return "<recursion>"
        _path_ids = _path_ids | {id(value)}
        try:
            return {key: HIDDEN if is_sensitive_key(key) and is_sensitive_value(item)
                    else redact(item, depth + 1, _path_ids)
                    for key, item in value.items()}
        except Exception:
            # Returning the original here would hand an unredacted object to the log line, which
            # then renders it through its repr. A container we failed to walk is a container whose
            # contents we know nothing about, so none of it can be logged. Do not raise: redact()
            # is also called from __repr__, which has no caller able to suppress the whole line.
            return "<redaction failed>"
    return value


class log_with:
    """
    Logging decorator that allows you to log with a
    specific logger.
    """
    # Customize these messages
    ENTRY_MESSAGE = 'Entering {0} with arguments {1} and keywords {2}'
    EXIT_MESSAGE = 'Exiting {0} with result {1}'

    def __init__(self, logger=None, log_entry=True, log_exit=True, hide_args=None):
        """
        Write the parameters and the result of the function to the log.

        Sensitive values are hidden in every decorated function without any configuration, by the
        name of the key or parameter they are passed under, see ``SENSITIVE_KEY_NAMES``. Only a
        value whose name says nothing about its content needs ``hide_args``.

        :param logger: The logger object.
        :param log_entry: Whether the function parameters should be logged
        :type log_entry: bool
        :param log_exit: Whether the result of the function should be logged
        :type log_exit: bool
        :param hide_args: Indices of parameters to hide completely, for values that the name based
            hiding cannot recognise, such as the key in ``aes_cbc_decrypt(key, iv, data)``.
        :type hide_args: list of int
        """
        self.logger = logger
        self.log_exit = log_exit
        self.log_entry = log_entry
        self.hide_args = hide_args or []

    def __call__(self, func):
        """
        Returns a wrapper that wraps func.
        The wrapper will log the entry and exit points of the function
        with logging.INFO level.

        :param func: The function that is decorated
        :return: function
        """

        # Resolved once at decoration time: a secret passed as a bare string carries no key name
        # of its own, but the parameter it binds to has one. Parameter names are part of the
        # signature, so unlike a parameter index they cannot silently drift out of sync with it.
        try:
            parameter_names = list(inspect.signature(func).parameters)
        except (TypeError, ValueError) as exx:
            # Without the signature, a secret passed as a bare positional value is no longer
            # recognised, which would silently weaken the hiding for this function. Say so once,
            # at decoration time, rather than leaving it invisible.
            log.warning(f"Cannot read the signature of {getattr(func, '__name__', func)!r}, so a "
                        f"sensitive value passed positionally to it will not be hidden: {exx}")
            parameter_names = []
        sensitive_positions = {index for index, name in enumerate(parameter_names)
                               if is_sensitive_key(name)}

        @functools.wraps(func)
        def log_wrapper(*args, **kwds):
            """
            Wrap the function in log entries. The entry of the function and
            the exit of the function is logged using the DEBUG log level.
            If the logger does not log DEBUG messages, this just returns
            the result of ``func(*args, **kwds)`` to improve performance.

            :param args: The positional arguments starting with index
            :type args: tuple
            :param kwds: The keyword arguments
            :type kwds: dict
            :return: The wrapped function
            """
            # Exit early if self.logger disregards DEBUG messages.
            if not self.logger.isEnabledFor(logging.DEBUG):
                return func(*args, **kwds)

            try:
                # The denylist applies to every decorated function, so a secret is hidden no
                # matter which frame logs it and which parameter it travelled in.
                log_args = redact(list(args))
                log_kwds = redact(kwds)
                # A parameter whose own name is sensitive is hidden whichever way it was passed.
                for arg_index in sensitive_positions:
                    if arg_index < len(log_args):
                        log_args[arg_index] = HIDDEN
                # Whole parameters named by the decorator are hidden on top of the denylist.
                for arg_index in self.hide_args:
                    log_args[arg_index] = HIDDEN
            except Exception as exx:
                # Hiding failed, so nothing about this call is trustworthy enough to log. Report
                # the failure instead of dropping the arguments silently, because a decorator
                # naming a parameter that does not exist is a bug that is otherwise invisible.
                self.logger.warning(f"Could not hide sensitive arguments of {func.__name__}, "
                                    f"suppressing all of them: {exx}")
                log_args = ()
                log_kwds = {}
            try:
                import inspect
                lno = inspect.getsourcelines(func)[1] + 1
                if self.log_entry:
                    self.logger.debug(self.ENTRY_MESSAGE.format(
                        func.__name__, log_args, log_kwds),
                        stacklevel=2, extra={'s_line': lno})
                else:
                    self.logger.debug(self.ENTRY_MESSAGE.format(
                        func.__name__, "HIDDEN", "HIDDEN"),
                        stacklevel=2, extra={'s_line': lno})
            except Exception as exx:
                self.logger.error(exx)
                self.logger.error(f"Error during logging of function {func.__name__}! {exx}")

            f_result = func(*args, **kwds)

            try:
                import inspect
                lno = inspect.getsourcelines(func)[1] + 1
                if self.log_exit:
                    # Functions that pass request data along return it, so a result hides the same
                    # keys as an argument. Without this, a parameter dict that was hidden on the
                    # way in reappears in full on the way out.
                    self.logger.debug(self.EXIT_MESSAGE.format(
                        func.__name__, redact(f_result)),
                        stacklevel=2, extra={'s_line': lno})
                else:
                    self.logger.debug(self.EXIT_MESSAGE.format(
                        func.__name__, "HIDDEN"),
                        stacklevel=2, extra={'s_line': lno})
            except Exception as exx:
                self.logger.error(f"Error during logging of function {func.__name__}! {exx}")
            return f_result

        return log_wrapper
