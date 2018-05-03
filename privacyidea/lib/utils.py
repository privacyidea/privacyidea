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
import logging
log = logging.getLogger(__name__)
import binascii
import base64
import qrcode
import StringIO
import urllib
from privacyidea.lib.crypto import urandom, geturandom
from privacyidea.lib.error import ParameterError
import string
import re
from datetime import timedelta, datetime
from datetime import time as dt_time
from dateutil.parser import parse as parse_date_string
from dateutil.tz import tzlocal
from netaddr import IPAddress, IPNetwork, AddrFormatError
import hashlib
import crypt
import traceback
import os
import time
from base64 import (b64decode, b64encode)


try:
    import bcrypt
    _bcrypt_hashpw = bcrypt.hashpw
except ImportError:  # pragma: no cover
    _bcrypt_hashpw = None

# On App Engine, this function is not available.
if hasattr(os, 'getpid'):
    _pid = os.getpid()
else:  # pragma: no cover
    # Fake PID
    _pid = urandom.randint(0, 100000)

ENCODING = "utf-8"


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
    :type password: unicode
    :return: a utf8 encoded password
    """
    if password:
        try:
            # If the password exists in unicode we encode it to utf-8
            password = password.encode(ENCODING)
        except UnicodeDecodeError as exx:
            # In case the password is already an encoded string, we fail to
            # encode it again...
            log.debug("Failed to convert password: {0!s}".format(type(password)))
    return password


def to_unicode(s, encoding="utf-8"):
    """
    converts a value to unicode if it is of type str.
    
    :param s: The utf-8 encoded str 
    :return: unicode string
    """
    if type(s) == str:
        s = s.decode(encoding)
    return s


def generate_otpkey(key_size=20):
    """
    generates the HMAC key of keysize. Should be 20 or 32
    The key is returned as a hexlified string
    :param key_size: The size of the key to generate
    :type key_size: int
    :return: hexlified key
    :rtype: string
    """
    log.debug("generating key of size {0!s}".format(key_size))
    return binascii.hexlify(geturandom(key_size))


def create_png(data, alt=None):
    img = qrcode.make(data)

    output = StringIO.StringIO()
    img.save(output)
    o_data = output.getvalue()
    output.close()

    return o_data


def create_img(data, width=0, alt=None, raw=False):
    """
    create the qr image data

    :param data: input data that will be munched into the qrcode
    :type data: string
    :param width: image width in pixel
    :type width: int
    :param raw: If set to false, the data will be interpreted as text and a
        QR code will be generated.

    :return: image data to be used in an <img> tag
    :rtype:  string
    """
    width_str = ''
    alt_str = ''

    if not raw:
        o_data = create_png(data, alt=alt)
    else:
        o_data = data
    data_uri = o_data.encode("base64").replace("\n", "")

    if width != 0:
        width_str = " width={0:d} ".format((int(width)))

    if alt is not None:
        val = urllib.urlencode({'alt': alt})
        alt_str = " alt={0!r} ".format((val[len('alt='):]))

    ret_img = 'data:image/png;base64,{0!s}'.format(data_uri)

    return ret_img


def generate_password(size=6, characters=string.ascii_lowercase +
                        string.ascii_uppercase + string.digits):
    """
    Generate a random password of the specified lenght of the given characters

    :param size: The length of the password
    :param characters: The characters the password may consist of
    :return: password
    :rtype: basestring
    """
    return ''.join(urandom.choice(characters) for _x in range(size))

#
# Modhex calculations for Yubikey
#
hexHexChars = '0123456789abcdef'
modHexChars = 'cbdefghijklnrtuv'

hex2ModDict = dict(zip(hexHexChars, modHexChars))
mod2HexDict = dict(zip(modHexChars, hexHexChars))


def modhex_encode(s):
    return ''.join(
        [hex2ModDict[c] for c in s.encode('hex')]
    )
# end def modhex_encode


def modhex_decode(m):
    return ''.join(
        [mod2HexDict[c] for c in m]
    ).decode('hex')
# end def modhex_decode


def checksum(msg):
    crc = 0xffff
    for i in range(0, len(msg) / 2):
        b = int(msg[i * 2] + msg[(i * 2) + 1], 16)
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
    :type encoded_data: basestring
    :param always_upper: If we should convert lowercase to uppercase
    :type always_upper: bool
    :return: hex-encoded payload
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
    except TypeError:
        raise ParameterError("Malformed base32check data: Invalid base32")
    # Extract checksum and payload
    if len(decoded_data) < 4:
        raise ParameterError("Malformed base32check data: Too short")
    checksum, payload = decoded_data[:4], decoded_data[4:]
    payload_hash = hashlib.sha1(payload).digest()
    if payload_hash[:4] != checksum:
        raise ParameterError("Malformed base32check data: Incorrect checksum")
    return binascii.hexlify(payload)


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
        raise Exception("type or description without necessary data! {0!s}".format(
                        unicode(params)))

    return data, types, desc


def parse_timedelta(delta):
    """
    This parses a string that contains a time delta for the last_auth policy
    in the format like
    1m (minute), 1h, 1d, 1y.

    :param delta: The time delta
    :type delta: basestring
    :return: timedelta
    """
    delta = delta.strip().replace(" ", "")
    time_specifier = delta[-1].lower()
    if time_specifier not in ["m", "h", "d", "y"]:
        raise Exception("Invalid time specifier")
    time = int(delta[:-1])
    if time_specifier == "h":
        td = timedelta(hours=time)
    elif time_specifier == "d":
        td = timedelta(days=time)
    elif time_specifier == "y":
        td = timedelta(days=time*365)
    else:
        td = timedelta(minutes=time)

    return td


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
        delta_amount = int(date_string[1:-1])
        if delta_specifier == "m":
            td = timedelta(minutes=delta_amount)
        elif delta_specifier == "h":
            td = timedelta(hours=delta_amount)
        elif delta_specifier == "d":
            td = timedelta(days=delta_amount)
        else:
            td = timedelta()
        return datetime.now(tzlocal()) + td

    # check 2016/12/23, 23.12.2016 and including hour and minutes.
    d = None
    try:
        # We only do dayfirst, if the datestring really starts with a 01/
        # If it stars with a year 2017/... we do NOT dayfirst.
        # See https://github.com/dateutil/dateutil/issues/457
        d = parse_date_string(date_string,
                              dayfirst=re.match("^\d\d[/\.]", date_string))
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
    # We only do the mapping for authentication requests!
    if not hasattr(request, "blueprint") or \
                    request.blueprint in ["validate_blueprint", "ttype_blueprint",
                                          "jwtauth"]:
        # The "client" parameter should overrule a possible X-Forwarded-For
        mapped_ip = request.all_data.get("client") or \
                    (request.access_route[0] if request.access_route else None)
        if mapped_ip:
            if proxy_settings and check_proxy(client_ip, mapped_ip,
                                              proxy_settings):
                client_ip = mapped_ip
            elif mapped_ip != client_ip:
                log.warning("Proxy {client_ip} not allowed to set IP to "
                            "{mapped_ip}.".format(client_ip=client_ip,
                                                  mapped_ip=mapped_ip))

    return client_ip


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
    rdb = False
    internal_timestamp = None
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


def parse_time_delta(s):
    """
    parses a string like +5d or -30m and returns a timedelta.
    Allowed identifiers are s, m, h, d.
    
    :param s: a string like +30m or -5d
    :return: timedelta 
    """
    seconds = 0
    minutes = 0
    hours = 0
    days = 0
    m = re.match("([+-])(\d+)([smhd])$", s)
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
    m1 = re.search("(^.*{current_time})([+-]\d+[smhd])(.*$)", s)
    m2 = re.search("(^.*{now})([+-]\d+[smhd])(.*$)", s)
    m = m1 or m2
    if m:
        s1 = m.group(1)
        s2 = m.group(2)
        s3 = m.group(3)
        s = s1 + s3
        td = parse_time_delta(s2)

    return s, td


def hash_password(password, hashtype):
    """
    Hash a password with phppass, SHA, SSHA, SSHA256, SSHA512, OTRS

    :param password: The password in plain text 
    :param hashtype: One of the hash types as string
    :return: The hashed password
    """
    hashtype = hashtype.upper()
    if hashtype == "PHPASS":
        PH = PasswordHash()
        password = PH.hash_password(password)
    elif hashtype == "SHA":
        password = hashlib.sha1(password).digest()
        password = "{SHA}" + b64encode(password)
    elif hashtype == "SSHA":
        salt = geturandom(20)
        hr = hashlib.sha1(password)
        hr.update(salt)
        pw = b64encode(hr.digest() + salt)
        return "{SSHA}" + pw
    elif hashtype == "SSHA256":
        salt = geturandom(32)
        hr = hashlib.sha256(password)
        hr.update(salt)
        pw = b64encode(hr.digest() + salt)
        return "{SSHA256}" + pw
    elif hashtype == "SSHA512":
        salt = geturandom(64)
        hr = hashlib.sha512(password)
        hr.update(salt)
        pw = b64encode(hr.digest() + salt)
        return "{SSHA512}" + pw
    elif hashtype == "OTRS":
        password = hashlib.sha256(password).hexdigest()
    else:
        raise Exception("Unsupported password hashtype. Use PHPASS, SHA, "
                        "SSHA, SSHA256, SSHA512, OTRS.")
    return password


def check_ssha(pw_hash, password, hashfunc, length):
    pw_hash_bin = b64decode(pw_hash.split("}")[1])
    digest = pw_hash_bin[:length]
    salt = pw_hash_bin[length:]
    hr = hashfunc(password)
    hr.update(salt)
    return digest == hr.digest()


def check_sha(pw_hash, password):
    b64_db_password = pw_hash[5:]
    hr = hashlib.sha1(password).digest()
    b64_password = b64encode(hr)
    return b64_password == b64_db_password


def otrs_sha256(pw_hash, password):
    hr = hashlib.sha256(password)
    digest = binascii.hexlify(hr.digest())
    return pw_hash == digest


class PasswordHash(object):
    def __init__(self, iteration_count_log2=8, portable_hashes=True,
                 algorithm=''):
        alg = algorithm.lower()
        if alg in ['blowfish', 'bcrypt'] and _bcrypt_hashpw is None:
            raise NotImplementedError('The bcrypt module is required')
        self.itoa64 = \
            './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        if not (4 <= iteration_count_log2 <= 31):
            iteration_count_log2 = 8
        self.iteration_count_log2 = iteration_count_log2
        self.portable_hashes = portable_hashes
        self.algorithm = algorithm
        self.random_state = '{0!r}{1!r}'.format(time.time(), _pid)

    def get_random_bytes(self, count):
        outp = ''
        try:
            outp = geturandom(count)
        except Exception as exx:  # pragma: no cover
            log.debug("problem getting urandom: {0!s}".format(exx))
        if len(outp) < count:  # pragma: no cover
            outp = ''
            rem = count
            while rem > 0:
                self.random_state = hashlib.md5(str(time.time())
                                                + self.random_state).hexdigest()
                outp += hashlib.md5(self.random_state).digest()
                rem -= 1
            outp = outp[:count]
        return outp

    def encode64(self, inp, count):
        outp = ''
        cur = 0
        while cur < count:
            value = ord(inp[cur])
            cur += 1
            outp += self.itoa64[value & 0x3f]
            if cur < count:
                value |= (ord(inp[cur]) << 8)
            outp += self.itoa64[(value >> 6) & 0x3f]
            if cur >= count:
                break
            cur += 1
            if cur < count:
                value |= (ord(inp[cur]) << 16)
            outp += self.itoa64[(value >> 12) & 0x3f]
            if cur >= count:
                break
            cur += 1
            outp += self.itoa64[(value >> 18) & 0x3f]
        return outp

    def gensalt_private(self, inp):  # pragma: no cover
        outp = '$P$'
        outp += self.itoa64[min([self.iteration_count_log2 + 5, 30])]
        outp += self.encode64(inp, 6)
        return outp

    def crypt_private(self, pw, setting):  # pragma: no cover
        outp = '*0'
        if setting.startswith(outp):
            outp = '*1'
        if setting[0:3] not in ['$P$', '$H$', '$S$']:
            return outp
        count_log2 = self.itoa64.find(setting[3])
        if not (7 <= count_log2 <= 30):
            return outp
        count = 1 << count_log2
        salt = setting[4:12]
        if len(salt) != 8:
            return outp
        if not isinstance(pw, str):
            pw = pw.encode('utf-8')

        hash_func = hashlib.md5
        encoding_len = 16
        if setting.startswith('$S$'):
            hash_func = hashlib.sha512
            encoding_len = 33

        hx = hash_func(salt + pw).digest()
        while count:
            hx = hash_func(hx + pw).digest()
            count -= 1
        hashed_pw = self.encode64(hx, encoding_len)

        if setting.startswith('$S$'):
            hashed_pw = hashed_pw[:-1]
        return setting[:12] + hashed_pw

    def gensalt_extended(self, inp):  # pragma: no cover
        count_log2 = min([self.iteration_count_log2 + 8, 24])
        count = (1 << count_log2) - 1
        outp = '_'
        outp += self.itoa64[count & 0x3f]
        outp += self.itoa64[(count >> 6) & 0x3f]
        outp += self.itoa64[(count >> 12) & 0x3f]
        outp += self.itoa64[(count >> 18) & 0x3f]
        outp += self.encode64(inp, 3)
        return outp

    def gensalt_blowfish(self, inp):  # pragma: no cover
        itoa64 = \
            './ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        outp = '$2a$'
        outp += chr(ord('0') + self.iteration_count_log2 / 10)
        outp += chr(ord('0') + self.iteration_count_log2 % 10)
        outp += '$'
        cur = 0
        while True:
            c1 = ord(inp[cur])
            cur += 1
            outp += itoa64[c1 >> 2]
            c1 = (c1 & 0x03) << 4
            if cur >= 16:
                outp += itoa64[c1]
                break
            c2 = ord(inp[cur])
            cur += 1
            c1 |= c2 >> 4
            outp += itoa64[c1]
            c1 = (c2 & 0x0f) << 2
            c2 = ord(inp[cur])
            cur += 1
            c1 |= c2 >> 6
            outp += itoa64[c1]
            outp += itoa64[c2 & 0x3f]
        return outp

    def hash_password(self, pw):  # pragma: no cover
        rnd = ''
        alg = self.algorithm.lower()
        if (not alg or alg in ['blowfish', 'bcrypt'] and not
        self.portable_hashes):
            if _bcrypt_hashpw is None and alg in ['blowfish', 'bcrypt']:
                raise NotImplementedError('The bcrypt module is required')
            else:
                rnd = self.get_random_bytes(16)
                salt = self.gensalt_blowfish(rnd)
                hx = _bcrypt_hashpw(pw, salt)
                if len(hx) == 60:
                    return hx
        if (not alg or alg == 'ext-des') and not self.portable_hashes:
            if len(rnd) < 3:
                rnd = self.get_random_bytes(3)
            hx = crypt.crypt(pw, self.gensalt_extended(rnd))
            if len(hx) == 20:
                return hx
        if len(rnd) < 6:
            rnd = self.get_random_bytes(6)
        hx = self.crypt_private(pw, self.gensalt_private(rnd))
        if len(hx) == 34:
            return hx
        return '*'

    def check_password(self, pw, stored_hash):
        # This part is different with the original PHP
        if stored_hash.startswith('$2a$'):
            # bcrypt
            if _bcrypt_hashpw is None:  # pragma: no cover
                raise NotImplementedError('The bcrypt module is required')
            hx = _bcrypt_hashpw(pw, stored_hash)
        elif stored_hash.startswith('_'):
            # ext-des
            stored_hash = stored_hash[1:]
            hx = crypt.crypt(pw, stored_hash)
        else:
            # portable hash
            hx = self.crypt_private(pw, stored_hash)
        return stored_hash == hx


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
    :return: a unicode object or None
    """
    if value is None or isinstance(value, unicode):
        return value
    else:
        return unicode(value)