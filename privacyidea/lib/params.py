# privacyIDEA is a fork of LinOTP
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
Parameter helpers for extracting values from request-parameter dictionaries.

These functions operate on plain ``dict`` objects and have no dependency on
Flask or any other framework layer.  They are the canonical location for
parameter extraction in ``lib/`` code.

The old ``getParam`` / ``optional`` / ``required`` API that lived in
``api/lib/utils.py`` is kept there as a thin compatibility shim so that
existing API-layer call sites continue to work without changes.
"""

import re

from privacyidea.lib.error import ParameterError


def _get_param(dictionary, key, default=None):
    """
    Get the parameter from the dictionary.
    If the parameter is not present, return the default value or None.
    """
    if dictionary and key in dictionary:
        return dictionary[key]
    if default is not None:
        return default
    return None


def get_required(dictionary, key, allow_empty=False):
    """
    Get the required parameter from the dictionary.

    :param dictionary: the parameter dictionary
    :param key: the key to look up
    :param allow_empty: if False (default), raise a ParameterError when the
        value is present but is an empty string
    :raises ParameterError: if the key is missing or (when allow_empty=False)
        if the value is an empty string
    :return: the value
    """
    ret = _get_param(dictionary, key, None)
    if ret is None or (not allow_empty and ret == ""):
        raise ParameterError(f"Missing parameter: {key}", id=905)
    return ret


def get_required_one_of(param, keys, allow_empty=False):
    """
    Return the first value from *param* whose key is in *keys* and is
    non-empty.

    :param param: the parameter dictionary
    :param keys: iterable of candidate keys
    :param allow_empty: if False (default), skip keys whose value is an empty
        string
    :raises ParameterError: if none of the keys are present with a valid value
    :return: the first matching value
    """
    for key in keys:
        ret = _get_param(param, key, None)
        if ret is not None:
            if not allow_empty and ret == "":
                continue
            return ret
    raise ParameterError(f"Missing one of the following parameters: {keys}", id=905)


def get_optional(param, key, default=None, allowed_values=None):
    """
    Get the optional parameter from the dictionary.

    :param param: the parameter dictionary
    :param key: the key to look up
    :param default: value to return when the key is absent (default: None)
    :param allowed_values: if given, return *default* when the value is not in
        this list (same behaviour as the old ``getParam`` ``allowed_values``
        argument)
    :return: the value, or *default* if the key is absent or not in allowed_values
    """
    value = _get_param(param, key, default)
    if allowed_values is not None and value not in allowed_values:
        return default
    return value


def get_optional_one_of(param, keys, default=None):
    """
    Return the first value from *param* whose key is in *keys*.

    :param param: the parameter dictionary
    :param keys: iterable of candidate keys
    :param default: value to return when none of the keys are present
        (default: None)
    :return: the first matching value, or *default*
    """
    for key in keys:
        ret = _get_param(param, key, None)
        if ret is not None:
            return ret
    return default


def attestation_certificate_allowed(cert_info, allowed_certs_pols):
    """
    Check a certificate against a set of policies.

    This will check an attestation certificate of a U2F- or WebAuthn-Token
    against a list of policies to verify whether a token with the given
    attestation may be enrolled or authorized.

    The certificate info may be None, in which case True will be returned if
    the policies are also empty.

    :param cert_info: The ``attestation_issuer``, ``attestation_serial``, and
        ``attestation_subject`` of the cert.
    :type cert_info: dict or None
    :param allowed_certs_pols: The policies restricting enrollment or
        authorization.
    :type allowed_certs_pols: dict or None
    :return: Whether the token should be allowed to complete enrollment or
        authorization based on its attestation.
    :rtype: bool
    """
    if not cert_info:
        return not allowed_certs_pols

    if allowed_certs_pols:
        for allowed_cert in allowed_certs_pols:
            tag, matching, _rest = allowed_cert.split("/", 3)
            tag_value = cert_info.get(f"attestation_{tag!s}")
            m = re.search(matching, tag_value) if matching and tag_value else None
            if matching and not m:
                return False

    return True


