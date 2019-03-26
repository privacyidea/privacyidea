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
import six
import logging; log = logging.getLogger(__name__)
from importlib import import_module
import binascii
import base64
import qrcode
import sqlalchemy
from six.moves.urllib.parse import urlunparse, urlparse, urlencode
from io import BytesIO
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
import pkg_resources
import time

from privacyidea.lib.error import ParameterError, ResourceNotFoundError

ENCODING = "utf-8"

BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def check_time_in_range(time_range, check_time=None):
    """
    Check if the given time is contained in the time_range string.
    The time_range can be something like

     <DOW>-<DOW>: <hh:mm>-<hh:mm>,  <DOW>-<DOW>: <hh:mm>-<hh:mm>
     <DOW>-<DOW>: <h:mm>-<hh:mm>,  <DOW>: <h:mm>-<hh:mm>
     <DOW>: <h>-<hh>

    DOW beeing the day of the week: Mon, Tue, Wed, Thu, Fri, Sat, Sun
    hh: 00-23
    mm: 00-59

    If time is omitted the current time is used: time.localtime()

    :param time_range: The timerange
    :type time_range: basestring
    :param time: The time to check
    :type time: datetime
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
    check_hour =dt_time(check_time.hour, check_time.minute)
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
                time_start =dt_time(ts[0], ts[1])
            else:
                time_start =dt_time(ts[0])
            if len(te) == 2:
                time_end =dt_time(te[0], te[1])
            else:
                time_end =dt_time(te[0])

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
    if isinstance(s, six.text_type):
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
    elif isinstance(s, six.text_type):
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
    if not isinstance(value, (bytes, six.string_types)):
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

    res = to_unicode(binascii.hexlify(to_bytes(s)))
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
    res = to_unicode(base64.b32encode(to_bytes(s)))
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
    res = to_unicode(base64.b64encode(to_bytes(s)))
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
    res = to_unicode(base64.urlsafe_b64encode(to_bytes(s)))
    return res


def create_png(data, alt=None):
    img = qrcode.make(data)

    output = BytesIO()
    img.save(output)
    o_data = output.getvalue()
    output.close()

    return o_data


def create_img(data, width=0, alt=None, raw=False):
    """
    create the qr image data

    :param data: input data that will be munched into the qrcode
    :type data: str
    :param width: image width in pixel
    :type width: int
    :param raw: If set to false, the data will be interpreted as text and a
        QR code will be generated.

    :return: image data to be used in an <img> tag
    :rtype:  str
    """
    width_str = ''
    alt_str = ''

    if not raw:
        o_data = create_png(data, alt=alt)
    else:
        o_data = data
    data_uri = b64encode_and_unicode(o_data)

    if width != 0:
        width_str = " width={0:d} ".format((int(width)))

    if alt is not None:
        val = urlencode({'alt': alt})
        alt_str = " alt={0!r} ".format((val[len('alt='):]))

    ret_img = u'data:image/png;base64,{0!s}'.format(data_uri)
    return ret_img


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
    return u''.join([hex2ModDict[c] for c in hexlify_and_unicode(s)])


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
    for b in six.iterbytes(msg):
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
    assert len(encoded_data) % 8 == 0
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
    payload_hash = hashlib.sha1(payload).digest()
    if payload_hash[:4] != checksum:
        raise ParameterError("Malformed base32check data: Incorrect checksum")
    return hexlify_and_unicode(payload)


def sanity_name_check(name, name_exp="^[A-Za-z0-9_\-\.]+$"):
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
                    log.warn("the passed key %r is not a "
                             "parameter for the %s %r" % (k, module, type))

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
                              dayfirst=re.match(r"^\d\d[/\.]", date_string))
    except ValueError:
        log.debug("Dateformat {0!s} could not be parsed".format(date_string))

    return d


def parse_proxy(proxy_settings):
    """
    This parses the string of the system settings
    OverrideAuthorizationClient.

    This defines, which client IP may act as a proxy and rewrite the client
    IP to be used in policies and audit log.

    Valid strings are
    10.0.0.0/24 > 192.168.0.0/24
        Hosts in 10.0.0.x may specify clients as 192.168.0.x
    10.0.0.12 > 192.168.0.0/24
        Only the one host may rewrite the client IP to 192.168.0.x
    172.16.0.0/16
        Hosts in 172.16.x.x may rewrite to any client IP

    Such settings may be separated by comma.

    :param proxy_settings: The OverrideAuthorizationClient config string
    :type proxy_settings: basestring
    :return: A dictionary containing the configuration
    """
    proxy_dict = {}
    proxies_list = [s.strip() for s in proxy_settings.split(",")]
    for proxy in proxies_list:
        p_list = proxy.split(">")
        proxynet = IPNetwork(p_list[0])
        if len(p_list) > 1:
            clientnet = IPNetwork(p_list[1])
        else:
            # No mapping client, so we take the whole network
            clientnet = IPNetwork("0.0.0.0/0")
        proxy_dict[proxynet] = clientnet

    return proxy_dict


def check_proxy(proxy_ip, rewrite_ip, proxy_settings):
    """
    This function checks if the proxy_ip is allowed to rewrite the IP to
    rewrite_ip. This check is done on the specification in proxy_settings.

    :param proxy_ip: The actual client, the proxy
    :type proxy_ip: basestring
    :param rewrite_ip: The client IP, to which it should be mapped
    :type rewrite_ip: basestring
    :param proxy_settings: The proxy settings from OverrideAuthorizationClient
    :return:
    """
    try:
        proxy_dict = parse_proxy(proxy_settings)
    except AddrFormatError:
        log.error("Error parsing the OverrideAuthorizationClient setting: {"
                  "0!s}! The IP addresses need to be comma separated. Fix "
                  "this. The client IP will not be mapped!")
        log.debug("{0!s}".format(traceback.format_exc()))
        return False

    for proxynet, clientnet in proxy_dict.items():
        if IPAddress(proxy_ip) in proxynet and IPAddress(rewrite_ip) in \
                clientnet:
            return True

    return False


def get_client_ip(request, proxy_settings):
    """
    Take the request and the proxy_settings and determine the new client IP.

    :param request:
    :param proxy_settings:
    :return:
    """
    client_ip = request.remote_addr

    # Set the possible mapped IP to X-Forwarded-For
    mapped_ip = request.access_route[0] if request.access_route else None

    # We only do the client-param mapping for authentication requests!
    if not hasattr(request, "blueprint") or \
                    request.blueprint in ["validate_blueprint", "ttype_blueprint",
                                          "jwtauth"]:
        # The "client" parameter should overrule a possible X-Forwarded-For
        mapped_ip = request.all_data.get("client") or mapped_ip

    if mapped_ip:
        if proxy_settings and check_proxy(client_ip, mapped_ip,
                                          proxy_settings):
            client_ip = mapped_ip
        elif mapped_ip != client_ip:
            log.warning("Proxy {client_ip} not allowed to set IP to "
                        "{mapped_ip}.".format(client_ip=client_ip,
                                              mapped_ip=mapped_ip))

    return client_ip


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
    for ipdef in policy:
        if ipdef[0] in ['-', '!']:
            # exclude the client?
            if IPAddress(client_ip) in IPNetwork(ipdef[1:]):
                log.debug(u"the client {0!s} is excluded by {1!s}".format(client_ip, ipdef))
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
    Otherwise only realms are returned, that are contained in the policies.
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

    # compare equal
    if condition[0] in "=" + string.digits:
        if condition[0] == "=":
            compare_value = int(condition[1:])
        else:
            compare_value = int(condition)
        return value == compare_value

    # compare bigger
    if condition[0] == ">":
        compare_value = int(condition[1:])
        return value > compare_value

    # compare less
    if condition[0] == "<":
        compare_value = int(condition[1:])
        return value < compare_value


def compare_value_value(value1, comparator, value2):
    """
    This function compares value1 and value2 with the comparator.
    The comparator may be "==", ">" or "<".
    
    If the values can be converted to integers, they are compared as integers 
    otherwise as strings.
    
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

    if comparator == "==":
        return value1 == value2
    elif comparator == ">":
        return value1 > value2
    elif comparator == "<":
        return value1 < value2

    raise Exception("Unknown comparator: {0!s}".format(comparator))


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
    :param timestring: 
    :param return_date: If set to True a date is returned instead of a string
    :return: 
    """
    from privacyidea.lib.tokenclass import DATE_FORMAT
    d = parse_date_string(ts)
    if not d.tzinfo:
        # we need to reparse the string
        d = parse_date_string(ts,
                              dayfirst=re.match("^\d\d[/\.]",ts)).replace(
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
        raise Exception("Unsupported timedelta")
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
    if value is None or isinstance(value, six.text_type):
        return value
    elif isinstance(value, bytes):
        return value.decode('utf8')
    else:
        return six.text_type(value)


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
    The password is replaced with "xxxx".
    In case any error occurs, return "<error when censoring connect string>"
    """
    try:
        parsed = urlparse(connect_string)
        if parsed.password is not None:
            # We need to censor the ``netloc`` attribute: user:pass@host
            _, host = parsed.netloc.rsplit("@", 1)
            new_netloc = u'{}:{}@{}'.format(parsed.username, 'xxxx', host)
            # Convert the URL to six components. netloc is component #1.
            splitted = list(parsed)
            splitted[1] = new_netloc
            return urlunparse(splitted)
        return connect_string
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
        raise ResourceNotFoundError(u"The requested {!s} could not be found.".format(table.__name__))


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
        r = u"{0!s}+".format(r[:-1])
        return r

    while len(",".join(data)) > max_len:
        new_data = []
        longest = max(data, key=len)
        for d in data:
            if d == longest:
                # Shorten the longest and mark with "+"
                d = u"{0!s}+".format(d[:-2])
            new_data.append(d)
        data = new_data
    return ",".join(data)


def check_pin_policy(pin, policy):
    """
    The policy to check a PIN can contain of "c", "n" and "s".
    "cn" means, that the PIN should contain a character and a number.
    "+cn" means, that the PIN should contain elements from the group of characters and numbers
    "-ns" means, that the PIN must not contain numbers or special characters

    :param pin: The PIN to check
    :param policy: The policy that describes the allowed contents of the PIN.
    :return: Tuple of True or False and a description
    """
    chars = {"c": "[a-zA-Z]",
             "n": "[0-9]",
             "s": "[.:,;_<>+*!/()=?$§%&#~\^-]"}
    exclusion = False
    grouping = False
    ret = True
    comment = []

    if not policy:
        return False, "No policy given."

    if policy[0] == "+":
        # grouping
        necessary = []
        for char in policy[1:]:
            necessary.append(chars.get(char))
        necessary = "|".join(necessary)
        if not re.search(necessary, pin):
            ret = False
            comment.append("Missing character in PIN: {0!s}".format(necessary))

    elif policy[0] == "-":
        # exclusion
        not_allowed = []
        for char in policy[1:]:
            not_allowed.append(chars.get(char))
        not_allowed = "|".join(not_allowed)
        if re.search(not_allowed, pin):
            ret = False
            comment.append("Not allowed character in PIN!")

    else:
        for c in chars:
            if c in policy and not re.search(chars[c], pin):
                ret = False
                comment.append("Missing character in PIN: {0!s}".format(chars[c]))

    return ret, ",".join(comment)


def get_module_class(package_name, class_name, check_method=None):
    """
    helper method to load the Module class from a given
    package in literal.

    :param package_name: literal of the Module
    :param class_name: Name of the class in the module
    :param check_method: Name of the method to check, if this would be the right class

    example:

        get_module_class("privacyidea.lib.auditmodules.sqlaudit", "Audit", "log")

        get_module_class("privacyidea.lib.monitoringmodules.sqlstats", "Monitoring")

    check:
        checks, if the method exists
        if not an error is thrown

    """
    mod = import_module(package_name)
    if not hasattr(mod, class_name):
        raise ImportError(u"{0} has no attribute {1}".format(package_name, class_name))
    klass = getattr(mod, class_name)
    log.debug("klass: {0!s}".format(klass))
    if check_method and not hasattr(klass, check_method):
        raise NameError(u"Class AttributeError: {0}.{1} "
                        u"instance has no attribute '{2}'".format(package_name, class_name, check_method))
    return klass


def get_version_number():
    """
    returns the privacyidea version
    """
    version = "unknown"
    try:
        version = pkg_resources.get_distribution("privacyidea").version
    except:
        log.info("We are not able to determine the privacyidea version number.")
    return version


def get_version():
    """
    This returns the version, that is displayed in the WebUI and
    self service portal.
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

    return res