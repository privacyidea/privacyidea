# -*- coding: utf-8 -*-
#
#  2017-11-24 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Use HSM to generate Salt for PasswordHash
#  2017-07-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add time offset parsing
#  2015-04-05 Cornelius Kölbel <cornelius@privacyidea.org>
#             Added time test function
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
#
"""
This is the library with base functions for privacyIDEA.

This module is tested in tests/test_lib_utils.py
"""
import os

import logging
from importlib import import_module
import binascii
import base64
import sqlalchemy
import string
import re
from datetime import timedelta, datetime
from datetime import time as dt_time
from dateutil.parser import parse as parse_date_string
from dateutil.tz import tzlocal, tzutc
from netaddr import IPAddress, IPNetwork, AddrFormatError
import hashlib
import traceback
import threading
import importlib_metadata
import time
import html
import segno
import mimetypes

from privacyidea.lib.error import ParameterError, ResourceNotFoundError, PolicyError

log = logging.getLogger(__name__)

BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

ALLOWED_SERIAL = r"^[0-9a-zA-Z\-_]+$"

# character lists for the identifiers in the pin content policy
CHARLIST_CONTENTPOLICY = {"c": string.ascii_letters, # characters
                          "n": string.digits,        # numbers
                          "s": string.punctuation}   # special


def check_time_in_range(time_range, check_time=None):
    """
    Check if the given time is contained in the time_range string.
    The time_range can be something like

     <DOW>-<DOW>: <hh:mm>-<hh:mm>,  <DOW>-<DOW>: <hh:mm>-<hh:mm>
     <DOW>-<DOW>: <h:mm>-<hh:mm>,  <DOW>: <h:mm>-<hh:mm>
     <DOW>: <h>-<hh>

    DOW being the day of the week: Mon, Tue, Wed, Thu, Fri, Sat, Sun
    hh: 00-23
    mm: 00-59

    If time is omitted the current time is used: time.localtime()

    :param time_range: The timerange
    :type time_range: basestring
    :param check_time: The time to check
    :type check_time: datetime
    :return: True, if time is within time_range.
    """
    time_match = False
    dow_index = {"mon": 1,
                 "tue": 2,
                 "wed": 3,
                 "thu": 4,
                 "fri": 5,
                 "sat": 6,
                 "sun": 7}

    check_time = check_time or datetime.now()
    check_day = check_time.isoweekday()
    check_hour = dt_time(check_time.hour, check_time.minute)
    # remove whitespaces
    time_range = ''.join(time_range.split())
    # split into list of time ranges
    time_ranges = time_range.split(",")
    try:
        for tr in time_ranges:
            # tr is something like: Mon-Tue:09:30-17:30
            dow, t = [x.lower() for x in tr.split(":", 1)]
            if "-" in dow:
                dow_start, dow_end = dow.split("-")
            else:
                dow_start = dow_end = dow
            t_start, t_end = t.split("-")
            # determine if we have times like 9:00-15:00 or 9-15
            ts = [int(x) for x in t_start.split(":")]
            te = [int(x) for x in t_end.split(":")]
            if len(ts) == 2:
                time_start = dt_time(ts[0], ts[1])
            else:
                time_start = dt_time(ts[0])
            if len(te) == 2:
                time_end = dt_time(te[0], te[1])
            else:
                time_end = dt_time(te[0])

            # check the day and the time
            if (dow_index.get(dow_start) <= check_day <= dow_index.get(dow_end)
                    and
                    time_start <= check_hour <= time_end):
                time_match = True
    except ValueError:
        log.error("Wrong time range format: <dow>-<dow>:<hh:mm>-<hh:mm>")
        log.debug("{0!s}".format(traceback.format_exc()))

    return time_match


def to_utf8(password):
    """
    Convert a password to utf8

    :param password: A password that should be converted to utf8
    :type password: str or bytes
    :return: a utf8 encoded password
    :rtype: bytes
    """
    if password:
        try:
            # If the password exists in unicode we encode it to utf-8
            password = password.encode('utf8')
        except (UnicodeDecodeError, AttributeError) as _exx:
            # In case the password is already an encoded string, we fail to
            # encode it again...
            log.debug("Failed to convert password: {0!s}".format(type(password)))
    return password


def to_unicode(s, encoding="utf-8"):
    """
    Converts the string s to unicode if it is of type bytes.

    :param s: the string to convert
    :type s: bytes or str
    :param encoding: the encoding to use (default utf8)
    :type encoding: str
    :return: unicode string
    :rtype: str
    """
    if isinstance(s, str):
        return s
    elif isinstance(s, bytes):
        return s.decode(encoding)
    # TODO: warning? Exception?
    return s


def to_bytes(s):
    """
    Converts the string s to a unicode encoded byte string

    :param s: string to convert
    :type s: str or bytes
    :return: the converted byte string
    :rtype: bytes
    """
    if isinstance(s, bytes):
        return s
    elif isinstance(s, str):
        return s.encode('utf8')
    # TODO: warning? Exception?
    return s


def to_byte_string(value):
    """
    Convert the given value to a byte string. If it is not a string type,
    convert it to a string first.

    :param value: the value to convert
    :type value: str or bytes or int
    :return: byte string representing the value
    :rtype: bytes
    """
    if not isinstance(value, (bytes, str)):
        value = str(value)
    value = to_bytes(value)
    return value


def hexlify_and_unicode(s):
    """

    :param s: string to hexlify
    :type s: bytes or str
    :return: hexlified string converted to unicode
    :rtype: str
    """

    res = binascii.hexlify(to_bytes(s)).decode('utf-8')
    return res


def b32encode_and_unicode(s):
    """
    Base32-encode a str (which is first encoded to UTF-8)
    or a byte string and return the result as a str.

    :param s: str or bytes to base32-encode
    :type s: str or bytes
    :return: base32-encoded string converted to unicode
    :rtype: str
    """
    res = base64.b32encode(to_bytes(s)).decode('utf-8')
    return res


def b64encode_and_unicode(s):
    """
    Base64-encode a str (which is first encoded to UTF-8)
    or a byte string and return the result as a str.

    :param s: str or bytes to base32-encode
    :type s: str or bytes
    :return: base64-encoded string converted to unicode
    :rtype: str
    """
    res = base64.b64encode(to_bytes(s)).decode('utf-8')
    return res


def urlsafe_b64encode_and_unicode(s):
    """
    Base64-urlsafe-encode a str (which is first encoded to UTF-8)
    or a byte string and return the result as a str.

    :param s: str or bytes to base32-encode
    :type s: str or bytes
    :return: base64-encoded string converted to unicode
    :rtype: str
    """
    res = base64.urlsafe_b64encode(to_bytes(s)).decode('utf-8')
    return res


def create_img(data, scale=10):
    """
    create the qr PNG image data URI

    :param data: input data that will be munched into the qrcode
    :type data: str
    :param scale: Scaling of the final PNG image
    :type scale: int
    :return: PNG data URI to be used in an <img> tag
    :rtype: str
    """
    return segno.make_qr(data).png_data_uri(scale=scale)


#
# Modhex calculations for Yubikey
#
hexHexChars = '0123456789abcdef'
modHexChars = 'cbdefghijklnrtuv'

hex2ModDict = dict(zip(hexHexChars, modHexChars))
mod2HexDict = dict(zip(modHexChars, hexHexChars))


def modhex_encode(s):
    """

    :param s: string to encode
    :type s: bytes or str
    :return: the encoded string
    :rtype: str
    """
    return ''.join([hex2ModDict[c] for c in hexlify_and_unicode(s)])


def modhex_decode(m):
    """

    :param m: string to decode
    :type m: str
    :return: decoded data
    :rtype: bytes
    """
    return binascii.unhexlify(''.join([mod2HexDict[c] for c in m]))


def checksum(msg):
    """
    Calculate CRC-16 (16-bit ISO 13239 1st complement) checksum.
    (see Yubikey-Manual - Chapter 6: Implementation details)

    :param msg: input byte string for crc calculation
    :type msg: bytes
    :return: crc16 checksum of msg
    :rtype: int
    """
    crc = 0xffff
    for b in msg:
        crc = crc ^ (b & 0xff)
        for _j in range(0, 8):
            n = crc & 1
            crc = crc >> 1
            if n != 0:
                crc = crc ^ 0x8408
    return crc


def decode_base32check(encoded_data, always_upper=True):
    """
    Decode arbitrary data which is given in the following format::

        strip_padding(base32(sha1(payload)[:4] + payload))

    Raise a ParameterError if the encoded payload is malformed.

    :param encoded_data: The base32 encoded data.
    :type encoded_data: str
    :param always_upper: If we should convert lowercase to uppercase
    :type always_upper: bool
    :return: hex-encoded payload
    :rtype: str
    """
    # First, add the padding to have a multiple of 8 bytes
    if always_upper:
        encoded_data = encoded_data.upper()
    encoded_length = len(encoded_data)
    if encoded_length % 8 != 0:
        encoded_data += "=" * (8 - (encoded_length % 8))
    # Decode as base32
    try:
        decoded_data = base64.b32decode(encoded_data)
    except (TypeError, binascii.Error, OverflowError):
        # Python 3.6.7: b32decode throws a binascii.Error when the padding is wrong
        # Python 3.6.3 (travis): b32decode throws an OverflowError when the padding is wrong
        raise ParameterError("Malformed base32check data: Invalid base32")
    # Extract checksum and payload
    if len(decoded_data) < 4:
        raise ParameterError("Malformed base32check data: Too short")
    checksum, payload = decoded_data[:4], decoded_data[4:]
    payload_hash = hashlib.sha1(payload).digest()  # nosec B324 # used as checksum for 2step enrollment
    if payload_hash[:4] != checksum:
        raise ParameterError("Malformed base32check data: Incorrect checksum")
    return hexlify_and_unicode(payload)


def sanity_name_check(name, name_exp=r"^[A-Za-z0-9_\-\.]+$"):
    """
    This function can be used to check the sanity of a name like a resolver,
    ca connector or realm.

    :param name: THe name of the resolver or ca connector
    :return: True, otherwise raises an exception
    """
    if re.match(name_exp, name) is None:
        raise Exception("non conformant characters in the name"
                        ": %r (not in %s)" % (name, name_exp))
    return True


def get_data_from_params(params, exclude_params, config_description, module,
                         type):
    """
    This is a helper function that parses the parameters when creating
    resolvers or CA connectors.
    It takes the parameters and checks, if the parameters correspond to the
    Class definition.

    :param params: The input parameters like passed from the REST API
    :type params: dict
    :param exclude_params: The parameters to be excluded like "resolver",
        "type" or "caconnector"
    :type exclude_params: list of strings
    :param config_description: The description of the allowed configuration
    :type config_description: dict
    :param module: An identifier like "resolver", "CA connector". This is
        only used for error output.
    :type module: basestring
    :param type: The type of the resolver or ca connector. Only used for
        error output.
    :type type: basestring
    :return: tuple of (data, types, description)
    """
    types = {}
    desc = {}
    data = {}
    for k in params:
        if k not in exclude_params:
            if k.startswith('type.') is True:
                key = k[len('type.'):]
                types[key] = params.get(k)
            elif k.startswith('desc.') is True:
                key = k[len('desc.'):]
                desc[key] = params.get(k)
            else:
                data[k] = params.get(k)
                if k in config_description:
                    types[k] = config_description.get(k)
                else:
                    log.warning("the passed key '{0!s}' is not a parameter for "
                                "the {1!s} type '{2!s}'".format(k, module, type))

    # Check that there is no type or desc without the data itself.
    # i.e. if there is a type.BindPW=password, then there must be a
    # BindPW=....
    _missing = False
    for t in types:
        if t not in data:
            _missing = True
    for t in desc:
        if t not in data:
            _missing = True
    if _missing:
        raise Exception("type or description without necessary data!"
                        " {0!s}".format(params))

    return data, types, desc


def parse_timelimit(limit):
    """
    This parses a string that contains a timelimit in the format
    2/5m or 1/3h, which means
    two in five minutes and
    one in three hours.

    It returns a tuple the number and the timedelta.

    :param limit: a timelimit
    :type limit: basestring
    :return: tuple of number and timedelta
    """
    # Strip and replace blanks
    limit = limit.strip().replace(" ", "")
    time_specifier = limit[-1].lower()
    if time_specifier not in ["m", "s", "h"]:
        raise Exception("Invalid time specifier")
    l = limit[:-1].split("/")
    count = int(l[0])
    time = int(l[1])
    td = timedelta(minutes=time)
    if time_specifier == "s":
        td = timedelta(seconds=time)
    if time_specifier == "h":
        td = timedelta(hours=time)

    return count, td


def parse_date(date_string):
    """
    Parses a string like

      +30d
      +12h
      +10m

    and returns a datetime object that is 30 days, 12 hours or 10 minutes
    in the future.

    It can also parse fixed date_strings like

      23.12.2016 23:30
      23.12.2016
      2016/12/23 11:30pm
      2016/12/23
      2017-04-27T20:00+0200

    :param date_string: a string containing a date or an offset
    :return: datetime object
    """
    date_string = date_string.strip()
    if date_string == "":
        return datetime.now(tzlocal())
    if date_string.startswith("+"):
        # We are using an offset
        delta_specifier = date_string[-1].lower()
        if delta_specifier not in 'mhd':
            return datetime.now(tzlocal()) + timedelta()
        delta_amount = int(date_string[1:-1])
        if delta_specifier == "m":
            td = timedelta(minutes=delta_amount)
        elif delta_specifier == "h":
            td = timedelta(hours=delta_amount)
        else:
            # delta_specifier must be "d"
            td = timedelta(days=delta_amount)
        return datetime.now(tzlocal()) + td

    # check 2016/12/23, 23.12.2016 and including hour and minutes.
    d = None
    try:
        # We only do dayfirst, if the datestring really starts with a 01/
        # If it stars with a year 2017/... we do NOT dayfirst.
        # See https://github.com/dateutil/dateutil/issues/457
        d = parse_date_string(date_string,
                              dayfirst=re.match(r"^\d\d[/.]", date_string))
    except ValueError:
        log.debug("Dateformat {0!s} could not be parsed".format(date_string))

    return d


def parse_proxy(proxy_settings):
    """
    This parses the string of the system settings OverrideAuthorizationClient into a set of "proxy paths",
    which are tuples of IPNetwork objects.

    The setting defines, which client IP may act as a proxy and rewrite the client
    IP to be used in policies and audit log.

    Valid strings are
    10.0.0.0/24 > 192.168.0.0/24
        Hosts in 10.0.0.x may specify clients as 192.168.0.x.
        This is parsed to a proxy path ``(IPNetwork("10.0.0.0/24"), IPNetwork("192.168.0.0/24"))``.
    10.0.0.1 > 192.168.0.0/24 > 192.168.1.0/24
        The proxy in 10.0.0.1 may forward requests from proxies in 192.168.0.x,
        which may in turn specify clients as 192.168.1.x.
        This is parsed to a proxy path
        ``(IPNetwork("10.0.0.0/24"), IPNetwork("192.168.0.0/24"), IPNetwork("192.168.1.0/24")``.
    10.0.0.12 > 192.168.0.0/24
        Only the one host may rewrite the client IP to 192.168.0.x.
        This is parsed to a proxy path ``(IPNetwork("10.0.0.12/32"), IPNetwork("192.168.0.0/24"))``.
    172.16.0.0/16
        Hosts in 172.16.x.x may rewrite to any client IP
        This is parsed to a proxy path ``(IPNetwork("172.16.0.0/16"), IPNetwork("0.0.0.0/0"))``.

    Multiple such settings may be separated by comma.

    :param proxy_settings: The OverrideAuthorizationClient config string
    :type proxy_settings: basestring
    :return: A set of tuples of IPNetwork objects. Each tuple has at least two elements.
    """
    proxy_set = set()
    if proxy_settings.strip():
        proxies_list = [s.strip() for s in proxy_settings.split(",")]
        for proxy in proxies_list:
            p_list = proxy.split(">")
            if len(p_list) > 1:
                proxypath = tuple(IPNetwork(proxynet) for proxynet in p_list)
            else:
                # No mapping client, so we take the whole network
                proxypath = (IPNetwork(p_list[0]), IPNetwork("0.0.0.0/0"))
            proxy_set.add(proxypath)

    return proxy_set


def check_proxy(path_to_client, proxy_settings):
    """
    This function takes a list of IPAddress objects, the so-called "path to client",
    along with the proxy settings from OverrideAuthorizationClient, and determines
    the IP from ``path_to_client`` which should be considered the effective client
    IP according to the proxy settings.

    :param path_to_client: A list of IPAddress objects containing all proxy hops, starting with the current HTTP
                           client IP and going to the client IP as given by the X-Forwarded-For header.
                           For example, a value of ``[IPAddress("192.168.1.3")]`` means that the HTTP client at
                           192.168.1.3 has not sent any X-Forwarded-For headers.
                           A value of ``[IPAddress("192.168.1.3"), IPAddress("10.1.2.3"), IPAddress("10.0.0.1")]``
                           means that the request passed two proxies: According to the X-Forwarded-For header,
                           it originated at 10.0.0.1, then passed a proxy at 10.1.2.3, then passed a proxy at
                           192.168.1.3 before finally reaching privacyIDEA.
    :param proxy_settings: The proxy settings from OverrideAuthorizationClient
    :return: an item from ``path_to_client``
    """
    try:
        proxy_dict = parse_proxy(proxy_settings)
    except AddrFormatError:
        log.error("Error parsing the OverrideAuthorizationClient setting: "
                  "{0!s}! The IP addresses need to be comma separated. Fix "
                  "this. The client IP will not be mapped!".format(proxy_settings))
        log.debug("{0!s}".format(traceback.format_exc()))
        return path_to_client[0]

    # We extract the IP from ``path_to_client`` that should be considered the "real" client IP by privacyIDEA.
    # This client IP is an item of ``path_to_client``. The problem is that parts of ``path_to_client`` may
    # be user-controlled. In order to prevent users from spoofing their IP address, ``proxy_settings``
    # specifies what proxies are trusted.
    # For each proxy path (which is a tuple of IPNetwork objects) in ``proxy_settings``, we determine the item of
    # ``path_to_client`` that would be considered the client IP according to the proxy path.
    # Example: If ``path_to_client`` is [10.1.1.1, 10.2.3.4, 192.168.1.1]:
    # * the proxy path [10.1.1.1/32, 10.2.3.0/24, 192.168.0.0/16] determines 192.168.1.1 as the client address
    # * while the proxy path [10.1.1.1/32, 192.168.0.0/16] determines 10.1.1.1 as the client address (because the
    #   proxy at 10.1.1.1 is not allowed to map to 10.2.3.4).
    # * and the proxy path [10.1.1.1/32, 10.2.3.0/24, 192.168.3.0/24] determines 10.1.1.1 as the client address,
    #   as the proxy path does not match completely because 10.2.3.4 is not allowed to map to 192.168.1.1.
    # After having processed all paths in the proxy settings, we return the "deepest" IP from ``path_to_client`` that
    # is allowed according to any proxy path of the proxy settings.
    log.debug("Determining the mapped IP from {!r} given the proxy settings {!r} ...".format(
        path_to_client, proxy_settings))
    max_idx = 0
    for proxy_path in proxy_dict:
        log.debug("Proxy path: {!r}".format(proxy_path))
        # If the proxy path contains more subnets than the path to the client, we already know that it cannot match.
        if len(proxy_path) > len(path_to_client):
            log.debug("... ignored because it is longer than the path to the client")
            continue
        # Hence, we can now be sure that len(path_to_client) >= len(proxy_path).
        current_max_idx = 0
        # If len(path_to_client) > len(proxy_path), ``zip`` cuts the lists to the same length.
        # Hence, we ignore any additional proxy hops that the client may send, which is what we want.
        for idx, (proxy_path_ip, client_path_ip) in enumerate(zip(proxy_path, path_to_client)):
            # We check if the network in the proxy path contains the IP from path_to_client.
            if client_path_ip not in proxy_path_ip:
                # If not, the current proxy path does not match and we do not have to keep checking it.
                log.debug("... ignored because {!r} is not in subnet {!r}".format(client_path_ip, proxy_path_ip))
                break
            else:
                current_max_idx = idx
        else:
            # This branch is only executed if we did *not* break out of the loop. This means that the proxy path
            # completely matches the path to client, so the mapped client IP is a viable candidate.
            if current_max_idx >= max_idx:
                log.debug("... setting new candidate for client IP: {!r}".format(path_to_client[current_max_idx]))
            max_idx = max(max_idx, current_max_idx)

    log.debug("Determined mapped client IP: {!r}".format(path_to_client[max_idx]))
    return path_to_client[max_idx]


def get_client_ip(request, proxy_settings):
    """
    Take the request and the proxy_settings and determine the new client IP.

    :param request:
    :param proxy_settings: The proxy settings from OverrideAuthorizationClient
    :return: IP address as string
    """
    # This is not so easy, because we want to support the X-Forwarded-For protocol header set by proxies,
    # but also want to prevent rogue clients from spoofing their IP address, while also supporting the
    # "client" request parameter.
    # From the X-Forwarded-For header, we determine the path to the actual client, i.e. the list of proxy servers
    # that the HTTP response will pass through, including the final client IP:
    # If a client C talks to a proxy P1, which in turn talks to a proxy P2, which talks to privacyIDEA,
    # X-Forwarded-For will be "C, P1", the HTTP client IP will be P2, and path_to_client
    # consequently will be [P2, P1, C].
    # However, if we get such a request, we cannot be sure if the X-Forwarded-For header is correct,
    # or if it was sent by a rogue client in order to spoof its IP address.
    # To prevent IP spoofing, privacyIDEA allows to configure a list of proxies that are allowed to override the
    # authentication client. See ``check_proxy`` for more details.
    # If we are handling a /validate/ or /auth/ endpoint and a "client" parameter is provided,
    # it is appended to the path to the client.
    if proxy_settings:
        if not request.access_route:
            # This is the case for tests
            return None
        elif request.access_route == [request.remote_addr]:
            # This is the case if no X-Forwarded-For header is provided
            path_to_client = [request.remote_addr]
        else:
            # This is the case if a X-Forwarded-For header is provided.
            path_to_client = [request.remote_addr] + list(reversed(request.access_route))
        # A possible ``client`` parameter is appended to the *end* of the path to client.
        if (not hasattr(request, "blueprint") or
            request.blueprint in ["validate_blueprint", "ttype_blueprint",
                                  "jwtauth"]) \
                and "client" in request.all_data:
            path_to_client.append(request.all_data["client"])
        # We now refer to ``check_proxy`` to extract the mapped IP from ``path_to_client``.
        return str(check_proxy([IPAddress(ip) for ip in path_to_client], proxy_settings))
    else:
        # If no proxy settings are defined, we do not map any IPs anyway.
        return request.remote_addr


def check_ip_in_policy(client_ip, policy):
    """
    This checks, if the given client IP is contained in a list like

       ["10.0.0.2", "192.168.2.1/24", "!192.168.2.12", "-172.16.200.1"]

    :param client_ip: The IP address in question
    :param policy: A string of single IP addresses, negated IP address and subnets.
    :return: tuple of (found, excluded)
    """
    client_found = False
    client_excluded = False
    # Remove empty strings from the list
    policy = list(filter(None, policy))
    for ipdef in policy:
        if ipdef[0] in ['-', '!']:
            # exclude the client?
            if IPAddress(client_ip) in IPNetwork(ipdef[1:]):
                log.debug("the client {0!s} is excluded by {1!s}".format(client_ip, ipdef))
                client_excluded = True
        elif IPAddress(client_ip) in IPNetwork(ipdef):
            client_found = True
    return client_found, client_excluded


def reload_db(timestamp, db_ts):
    """
    Check if the configuration database should be reloaded. This is verified
    by comparing the chache timestamp and the database timestamp

    :param timestamp: cache timestamp
    :type timestamp: timestamp
    :param db_ts: database timestamp
    :type db_ts: Config Object with timestamp str in .Value

    :return: bool
    """
    internal_timestamp = ''
    if timestamp:
        internal_timestamp = timestamp.strftime("%s")
    rdb = False
    # Reason to reload
    if db_ts and db_ts.Value.startswith("2016-"):
        # If there is an old timestamp in the database
        rdb = True
        log.debug("Old timestamp. We need to reread policies "
                  "from DB.")
    if not (timestamp and db_ts):
        # If values are not initialized
        rdb = True
        log.debug("Values are not initialized. We need to reread "
                  "policies from DB.")
    if db_ts and db_ts.Value >= internal_timestamp:
        # If the DB contents is newer
        rdb = True
        log.debug("timestamp in DB newer. We need to reread policies "
                  "from DB.")
    return rdb


def reduce_realms(all_realms, policies):
    """
    This function reduces the realm list based on the policies
    If there is a policy, that acts for all realms, all realms are returned.
    Otherwise, only realms are returned, that are contained in the policies.
    """
    realms = {}
    if not policies:
        # if there are no policies at all, this works for all realms
        realms = all_realms
    else:
        for pol in policies:
            pol_realm = pol.get("realm")
            if not pol_realm:
                # If there is ANY empty realm, this means the policy acts for
                # ALL realms
                realms = all_realms
                break
            else:
                for r in pol_realm:
                    if r not in realms:
                        # Attach each realm in the policy
                        realms[r] = all_realms.get(r)
    return realms


def is_true(value):
    """
    Returns True is the value is 1, "1", True or "true"

    :param value: string or integer
    :return: Boolean
    """
    return value in [1, "1", True, "True", "true", "TRUE"]


def compare_condition(condition, value):
    """
    This function checks, if the 'value' complies the 'condition'.
    The condition can start with '<', '=' or '>' and contain a number like:
    <100
    >1000
    =123
    123 is interpreted as =123

    :param condition: A string like <100
    :type condition: basestring
    :param value: the value to check
    :type value: int
    :return: True or False
    """
    condition = condition.replace(" ", "")
    if not condition:
        # No condition to match!
        return False

    try:
        if condition[0:2] in ["==", "!=", ">=", "=>", "<=", "=<"]:
            return compare_value_value(value, condition[0:2], int(condition[2:]))
        elif condition[0] in ["=", "<", ">"]:
            return compare_value_value(value, condition[0], int(condition[1:]))
        else:
            return value == int(condition)

    except ValueError:
        log.warning("Invalid condition {0!s}. Needs to contain an integer.".format(condition))
        return False


def compare_value_value(value1, comparator, value2):
    """
    This function compares value1 and value2 with the comparator.
    The comparator may be "==", "=", "!=", ">", "<", ">=", "=>", "<=" or "=<".

    If the values can be converted to integers or dates, they are compared as such,
    otherwise as strings.

    In case of dates make sure they can be parsed by 'parse_date()', otherwise
    they will be compared as strings.

    :param value1: First value
    :param value2: Second value
    :param comparator: The comparator
    :return: True or False
    """
    try:
        int1 = int(value1)
        int2 = int(value2)
        # We only converts BOTH values if possible
        value1 = int1
        value2 = int2
    except Exception:
        log.debug("can not compare values as integers.")

    if type(value1) != int and type(value2) != int:
        # try to convert both values to a timestamp
        try:
            date1 = parse_date(value1)
            date2 = parse_date(value2)
            if date1 and date2:
                # Only use dates, if both values can be converted to dates
                value1 = date1
                value2 = date2
        except Exception:
            log.debug("error during date conversion.")

    if comparator in ["==", "="]:
        return value1 == value2
    elif comparator == ">":
        return value1 > value2
    elif comparator == "<":
        return value1 < value2
    elif comparator in ['>=', '=>']:
        return value1 >= value2
    elif comparator in ['<=', '=<']:
        return value1 <= value2
    elif comparator == '!=':
        return value1 != value2
    else:
        raise Exception("Unknown comparator: {0!s}".format(comparator))


def compare_generic_condition(cond, key_method, warning):
    """
    Compares a condition like "tokeninfoattribute == value".
    It uses the "key_method" to determine the value of "tokeninfoattribute".

    If the value does not match, it returns False.

    :param cond: A condition containing a comparator like "==", ">", "<"
    :param key_method: A function call, that get the value from the key
    :param warning: A warning message to be written to the log file.
    :return: True of False
    """
    key = value = None
    for comparator in ["==", ">", "<"]:
        if len(cond.split(comparator)) == 2:
            key, value = [x.strip() for x in cond.split(comparator)]
            break
    if value:
        res = compare_value_value(key_method(key), comparator, value)
        log.debug("Comparing {0!s} {1!s} {2!s} with result {3!s}.".format(key, comparator, value, res))
        return res
    else:
        # There is a condition, but we do not know it!
        log.warning(warning.format(cond))
        raise Exception("Condition not parsable.")


def int_to_hex(serial):
    """
    Converts a string with an integer to a hexstring.
    This is used to convert integer serial numbers of certificates to the hex
    representation

    :param serial: an integer string
    :return: a hex formatted string
    """
    serial_hex = hex(int(serial)).upper()
    serial_hex = serial_hex.split("X")[1]
    if len(serial_hex)%2 != 0:
        serial_hex = "0" + serial_hex
    return serial_hex


def parse_legacy_time(ts, return_date=False):
    """
    The new timestrings are of the format YYYY-MM-DDThh:mm+oooo.
    They contain the timezone offset!

    Old legacy time strings are of format DD/MM/YY hh:mm without time zone 
    offset.

    This function parses string and returns the new formatted time string 
    including the timezone offset.

    :param ts:
    :param return_date: If set to True a date is returned instead of a string
    :return:
    """
    from privacyidea.lib.tokenclass import DATE_FORMAT
    d = parse_date_string(ts)
    if not d.tzinfo:
        # we need to reparse the string
        d = parse_date_string(ts,
                              dayfirst=re.match(r"^\d\d[/\.]", ts)).replace(
                                  tzinfo=tzlocal())
    if return_date:
        return d
    else:
        return d.strftime(DATE_FORMAT)


def parse_timedelta(s):
    """
    parses a string like +5d or -30m and returns a timedelta.
    Allowed identifiers are s, m, h, d, y.

    :param s: a string like +30m or -5d
    :return: timedelta
    """
    seconds = 0
    minutes = 0
    hours = 0
    days = 0
    m = re.match(r"\s*([+-]?)\s*(\d+)\s*([smhdy])\s*$", s)
    if not m:
        log.warning("Unsupported timedelta: {0!r}".format(s))
        raise TypeError(f"Unsupported timedelta {s!r}")
    count = int(m.group(2))
    if m.group(1) == "-":
        count = - count
    if m.group(3) == "s":
        seconds = count
    elif m.group(3) == "m":
        minutes = count
    elif m.group(3) == "h":
        hours = count
    elif m.group(3) == "d":
        days = count
    elif m.group(3) == "y":
        days = 365 * count

    td = timedelta(seconds=seconds, minutes=minutes, hours=hours, days=days)
    return td


def parse_time_sec_int(s):
    """
    parses a string like 5d or 24h into an int with gives the time in sec. You can use y, d, h, m and s.

    :param s: time string like 5d or 24h
    :type s: str or int
    :return: time in seconds as an integer value
    :rtype: int
    """
    try:
        td = parse_timedelta(s)
        ret = abs(td).total_seconds()
    except TypeError as _e:
        # parse_timedelta() does not accept int values
        ret = s
    return int(ret)


def parse_time_offset_from_now(s):
    """
    Parses a string as used in the token event handler
        "New date {now}+5d. Some {other} {tags}" or
        "New date {now}-30m! Some {other} {tags}".
    This returns the string "New date {now}. Some {other} {tags}" and the
    timedelta of 5 days.
    Allowed tags are {now} and {current_time}. Only one tag of {now} or {
    current_time} is allowed.
    Allowed offsets are "s": seconds, "m": minutes, "h": hours, "d": days.

    :param s: The string to be parsed.
    :return: tuple of modified string and timedelta
    """
    td = timedelta()
    m1 = re.search(r"(^.*{current_time})([+-]\d+[smhd])(.*$)", s)
    m2 = re.search(r"(^.*{now})([+-]\d+[smhd])(.*$)", s)
    m = m1 or m2
    if m:
        s1 = m.group(1)
        s2 = m.group(2)
        s3 = m.group(3)
        s = s1 + s3
        td = parse_timedelta(s2)

    return s, td


def parse_int(s, default=0):
    """
    Returns an integer either to base10 or base16.
    :param s: A possible string given.
    :param default: If the value can not be parsed or is None, return this
        default value
    :return: An integer
    """
    i = default
    try:
        i = int(s)
        return i
    except (ValueError, TypeError):
        pass

    try:
        i = int(s, 16)
        return i
    except (ValueError, TypeError):
        pass

    return i


def convert_column_to_unicode(value):
    """
    Helper function for models. If ``value`` is None or a unicode object, do nothing.
    Otherwise, convert it to a unicode object.

    :param value: the string to convert
    :type value: str
    :return: a unicode object or None
    """
    if value is None or isinstance(value, str):
        return value
    elif isinstance(value, bytes):
        return value.decode('utf8')
    else:
        return str(value)


def convert_timestamp_to_utc(timestamp):
    """
    Convert a timezone-aware datetime object to a naive UTC datetime.

    :param timestamp: datetime object that should be converted
    :type timestamp: timezone-aware datetime object
    :return: timezone-naive datetime object
    """
    return timestamp.astimezone(tzutc()).replace(tzinfo=None)


def censor_connect_string(connect_string):
    """
    Take a SQLAlchemy connect string and return a sanitized version
    that can be written to the log without disclosing the password.
    The password is replaced with "***".
    In case any error occurs, return "<error when censoring connect string>"
    """
    try:
        parsed = sqlalchemy.engine.url.make_url(connect_string)
        return parsed.__repr__()
    except Exception:
        return "<error when censoring connect string>"


def fetch_one_resource(table, **query):
    """
    Given an SQLAlchemy table and query keywords, fetch exactly one result and return it.
    If no results is found, this raises a ``ResourceNotFoundError``.
    If more than one result is found, this raises SQLAlchemy's ``MultipleResultsFound``
    """
    try:
        return table.query.filter_by(**query).one()
    except sqlalchemy.orm.exc.NoResultFound:
        raise ResourceNotFoundError("The requested {!s} could not be found.".format(table.__name__))


def truncate_comma_list(data, max_len):
    """
    This function takes a string with a comma separated list and
    shortens the longest entries this way, that the final string has a maximum
    length of max_len

    Shorted entries are marked with a "+" at the end.

    :param data: A comma separated list
    :type data: basestring
    :return: shortened string
    """
    data = data.split(",")
    # if there are more entries than the maximum length, we do an early exit
    if len(data) >= max_len:
        r = ",".join(data)[:max_len]
        # Also mark this string
        r = "{0!s}+".format(r[:-1])
        return r

    while len(",".join(data)) > max_len:
        new_data = []
        longest = max(data, key=len)
        for d in data:
            if d == longest:
                # Shorten the longest and mark with "+"
                d = "{0!s}+".format(d[:-2])
            new_data.append(d)
        data = new_data
    return ",".join(data)


def generate_charlists_from_pin_policy(policy):
    """
    This function uses the pin content policy string (e.g. "+cns", "[asdf]") to create the character lists
    for password generation.

    :param policy: The policy that describes the allowed contents of the PIN (see check_pin_contents)
    :return: Dictionary with keys "base" for the base set of allowed characters and "requirements"
     which denotes a list of characters from each of which at least one must be contained in the pin.
    """

    # regexp to check for pin content policy string validity
    VALID_POLICY_REGEXP = re.compile(r'^[+-]*[cns]+$|^\[.*\]+$')

    # default: full character list
    base_characters = "".join(CHARLIST_CONTENTPOLICY.values())
    # list of strings where a character of each string is required for the pin
    requirements = []

    if not re.match(VALID_POLICY_REGEXP, policy):
        raise PolicyError("Unknown character specifier in PIN policy.")

    if policy[0] == "+":
        # grouping
        for char in policy[1:]:
            requirements.append(CHARLIST_CONTENTPOLICY.get(char))
        requirements = ["".join(requirements)]

    elif policy[0] == "-":
        # exclusion
        base_charlist = []
        for key in CHARLIST_CONTENTPOLICY.keys():
            if key not in policy[1:]:
                base_charlist.append(CHARLIST_CONTENTPOLICY[key])
        base_characters = "".join(base_charlist)

    elif policy[0] == "[" and policy[-1] == "]":
        # only allowed characters
        base_characters = policy[1:-1]

    else:
        for c in policy:
            if c in CHARLIST_CONTENTPOLICY:
                requirements.append(CHARLIST_CONTENTPOLICY.get(c))

    return {"base": base_characters, "requirements": requirements}


def check_pin_contents(pin, policy):
    """
    The policy to check a PIN can contain of "c", "n" and "s".
    "cn" means, that the PIN should contain a character and a number.
    "+cn" means, that the PIN should contain elements from the group of characters and numbers
    "-ns" means, that the PIN must not contain numbers or special characters
    "[12345]" means, that the PIN may only consist of the characters 1,2,3,4 and 5.

    :param pin: The PIN to check
    :param policy: The policy that describes the allowed contents of the PIN.
    :return: Tuple of True or False and a description
    """

    ret = True
    comment = []

    if not policy:
        return False, "No policy given."

    charlists_dict = generate_charlists_from_pin_policy(policy)

    # check for not allowed characters
    for char in pin:
        if not char in charlists_dict["base"]:
            ret = False
    if not ret:
        comment.append("Not allowed character in PIN!")

    # check requirements
    for str in charlists_dict["requirements"]:
        if not re.search(re.compile('[' + re.escape(str) + ']'), pin):
            ret = False
            comment.append("Missing character in PIN: {0!s}".format(str))

    return ret, ",".join(comment)


def get_module_class(package_name, class_name, check_method=None):
    """
    helper method to load the Module class from a given
    package in literal.

    example::

        get_module_class("privacyidea.lib.auditmodules.sqlaudit", "Audit", "log")

        get_module_class("privacyidea.lib.monitoringmodules.sqlstats", "Monitoring")

    check:
        checks, if the method exists
        if not an error is thrown

    :param package_name: literal of the Module
    :param class_name: Name of the class in the module
    :param check_method: Name of the method to check, if this would be the right class
    """
    mod = import_module(package_name)
    if not hasattr(mod, class_name):
        raise ImportError("{0} has no attribute {1}".format(package_name, class_name))
    klass = getattr(mod, class_name)
    log.debug("klass: {0!s}".format(klass))
    if check_method and not hasattr(klass, check_method):
        raise NameError("Class AttributeError: {0}.{1} "
                        "instance has no attribute '{2}'".format(package_name, class_name, check_method))
    return klass


def get_version_number():
    """
    returns the privacyidea version
    """
    version = "unknown"
    try:
        version = importlib_metadata.version("privacyidea")
    except:
        log.info("We are not able to determine the privacyidea version number.")
    return version


def get_version():
    """
    This returns the version, that is displayed in the WebUI and
    self-service portal.
    """
    version = get_version_number()
    return "privacyIDEA {0!s}".format(version)


def prepare_result(obj, rid=1, details=None):
    """
    This is used to preformat the dictionary to be sent by the API response

    :param obj: simple result object like dict, sting or list
    :type obj: dict or list or string/unicode
    :param rid: id value, for future versions
    :type rid: int
    :param details: optional parameter, which allows to provide more detail
    :type  details: None or simple type like dict, list or string/unicode

    :return: json rendered sting result
    :rtype: string
    """
    res = {"jsonrpc": "2.0",
           "result": {"status": True,
                      "value": obj},
           "version": get_version(),
           "versionnumber": get_version_number(),
           "id": rid,
           "time": time.time()}

    if details is not None and len(details) > 0:
        details["threadid"] = threading.current_thread().ident
        res["detail"] = details

    # Fix for sending an information about challenge response
    # TODO: Make this default, when we move from the binary result->value to
    #       more states in version 4.0
    if rid > 1:
        if obj:
            r_authentication = "ACCEPT"
        elif not obj and details.get("multi_challenge"):
            # We have a challenge authentication
            r_authentication = "CHALLENGE"
        elif not obj and (details.get("challenge_status") == "declined"):
            r_authentication = "DECLINED"
        else:
            r_authentication = "REJECT"
        res["result"]["authentication"] = r_authentication

    return res


def split_pin_pass(passw, otplen, prependpin):
    """
    Split a given password based on the otp length and prepend pin

    :param passw: The password like test123456 or 123456test
    :type passw: str
    :param otplen: The length of the otp value
    :param prependpin: The password is either in front or after the otp value
    :return:
    """
    if prependpin:
        pin = passw[0:-otplen]
        otpval = passw[-otplen:]
        log.debug("PIN prepended. PIN length is {0!s}, OTP length is {0!s}.".format(len(pin),
                                                                                    len(otpval)))
    else:
        pin = passw[otplen:]
        otpval = passw[0:otplen]
        log.debug("PIN appended. PIN length is {0!s}, OTP length is {0!s}.".format(len(pin),
                                                                                   len(otpval)))
    return pin, otpval


def create_tag_dict(logged_in_user=None,
                    request=None,
                    serial=None,
                    tokenowner=None,
                    tokentype=None,
                    recipient=None,
                    registrationcode=None,
                    googleurl_value=None,
                    client_ip=None,
                    pin=None,
                    challenge=None,
                    escape_html=False):
    """
    This helper function creates a dictionary with tags to be used in sending emails
    either with email tokens or within the notification handler

    :param logged_in_user: The acting logged in user (admin)
    :param request: The HTTP request object
    :param serial: The serial number of the token
    :param tokenowner: The owner of the token
    :type tokenowner: user object
    :param tokentype: The type of the token
    :param recipient: The recipient
    :type recipient: dictionary with "givenname" and "surname"
    :param registrationcode: The registration code of a token
    :param googleurl_value: The URL for the QR code during token enrollemnt
    :param client_ip: The IP of the client
    :param pin: The PIN of a token
    :param challenge: The challenge data
    :param escape_html: Whether the values for the tags should be html escaped
    :return: The tag dictionary
    """
    time = datetime.now().strftime("%H:%M:%S")
    date = datetime.now().strftime("%Y-%m-%d")
    recipient = recipient or {}
    tags = dict(admin=logged_in_user.get("username") if logged_in_user else "",
                realm=logged_in_user.get("realm") if logged_in_user else "",
                action=request.path if request else "",
                serial=serial,
                url=request.url_root if request else "",
                user=tokenowner.info.get("givenname") if tokenowner else "",
                surname=tokenowner.info.get("surname") if tokenowner else "",
                givenname=recipient.get("givenname"),
                username=tokenowner.login if tokenowner else "",
                userrealm=tokenowner.realm if tokenowner else "",
                tokentype=tokentype,
                registrationcode=registrationcode,
                recipient_givenname=recipient.get("givenname"),
                recipient_surname=recipient.get("surname"),
                googleurl_value=googleurl_value,
                time=time,
                date=date,
                client_ip=client_ip,
                pin=pin,
                ua_browser=request.user_agent.browser if request else "",
                ua_string=request.user_agent.string if request else "",
                challenge=challenge if challenge else "")
    if escape_html:
        escaped_tags = {}
        for key, value in tags.items():
            escaped_tags[key] = html.escape(value) if value is not None else None
        tags = escaped_tags

    return tags


def check_serial_valid(serial):
    """
    This function checks the given serial number for allowed values.
    Raises an exception if the format of the serial number is not allowed

    :param serial:
    :return: True or Exception
    """
    if not re.match(ALLOWED_SERIAL, serial):
        raise ParameterError("Invalid serial number. Must comply to {0!s}.".format(ALLOWED_SERIAL))
    return True


def determine_logged_in_userparams(logged_in_user, params):
    """
    Determines the normal user and admin parameters from the logged_in user information and
    from the params.

    If an administrator is acting, the "adminuser" and "adminrealm" are set from the logged_in_user
    information and the user parameters are taken from the request parameters.
    Thus an admin can act on a user.

    If a user is acting, the adminuser and adminrealm are None, the username and userrealm are taken from
    the logged_in_user information.

    :param logged_in_user: Logged in user dictionary.
    :param params: Request parameters (all_data)
    :return: Tupe of (scope, username, realm, adminuser, adminrealm)
    """
    role = logged_in_user.get("role")
    username = logged_in_user.get("username")
    realm = logged_in_user.get("realm")
    admin_realm = None
    admin_user = None
    if role == "admin":
        admin_realm = realm
        admin_user = username
        username = params.get("user")
        realm = params.get("realm")
    elif role == "user":
        pass
    else:
        raise PolicyError("Unknown role: {}".format(role))

    return role, username, realm, admin_user, admin_realm


def to_list(input):
    """
    Returns a list if either a list, a set or a single string is given.
    If a single string is given, then it returns a list with this one element.

    :param input: Can be a list a set or a string
    :return: list of elements
    """
    if isinstance(input, list):
        return input
    if isinstance(input, set):
        return list(input)
    return [input]


def parse_string_to_dict(s, split_char=":"):
    """
    This function can parse a string that is formatted like:

       :key1: valueA valueB valueC :key2: valueD valueE

    and return a dict:

       {"key1": ["valueA", "valueB", "valueC"],
        "key2": ["valueD", "valueE"]

    Note: a whitespace is in the string is separating the values.
    Thus values can not contain a whitespace.

    :param s: The string that should be parsed
    :param split_char: The character used for splitting the string
    :return: the dict
    """
    # create a list like ["key1", "valueA valueB valueC", "key2", "valueD valueE"]
    packed_list = [x.strip() for x in s.strip().split(split_char) if x]
    keys = packed_list[::2]
    # create a list of the values: [['valueA', 'valueB', 'valueC'], ['valueD', 'valueE']]
    values = [[x for x in y.split()] for y in packed_list[1::2]]
    d = {a: b for a, b in zip(keys, values)}
    return d


def replace_function_event_handler(text, token_serial=None, tokenowner=None, logged_in_user=None):
    if logged_in_user is not None:
        login = logged_in_user.login
        realm = logged_in_user.realm
    else:
        login = ""
        realm = ""

    if tokenowner is not None:
        surname = tokenowner.info.get("surname")
        givenname = tokenowner.info.get("givenname")
        userrealm = tokenowner.realm
    else:
        surname = ""
        givenname = ""
        userrealm = ""

    if token_serial is not None:
        token_serial = token_serial
    else:
        token_serial = ""  # nosec B105 # Reset serial

    try:
        attributes = {
            "logged_in_user": login,
            "realm": realm,
            "surname": surname,
            "token_owner": givenname,
            "user_realm": userrealm,
            "token_serial": token_serial
        }
        new_text = text.format(**attributes)
        return new_text
    except(ValueError, KeyError) as err:
        log.warning("Unable to replace placeholder: ({0!s})! Please check the webhooks data option.".format(err))
        return text


def convert_imagefile_to_dataimage(imagepath):
    """
    This helper reads an image file and converts it to a dataimage string,
    that can be directly used in HTML pages.

    :param imagepath:
    :return: A dataimage as string
    """
    try:
        mime, _ = mimetypes.guess_type(imagepath)
        if not mime:
            log.warning("Unknown file type in file {0!s}.".format(imagepath))
            return ""
        with open(imagepath, "rb") as f:
            data = f.read()
            data64 = base64.b64encode(data)
        return "data:{0!s};base64,{1!s}".format(mime, to_unicode(data64))
    except FileNotFoundError:
        log.warning("The file {0!s} could not be found.".format(imagepath))
        return ""
