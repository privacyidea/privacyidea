# -*- coding: utf-8 -*-
#
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
import qrcode
import StringIO
import urllib
from privacyidea.lib.crypto import urandom, geturandom
import string
import re
from datetime import timedelta, datetime, time
from netaddr import IPAddress, IPNetwork, AddrFormatError
import traceback
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
    check_hour = time(check_time.hour, check_time.minute)
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
                time_start = time(ts[0], ts[1])
            else:
                time_start = time(ts[0])
            if len(te) == 2:
                time_end = time(te[0], te[1])
            else:
                time_end = time(te[0])

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


def sanity_name_check(name, name_exp="^[A-Za-z0-9_\-]+$"):
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

    :param params: The inpurt parameters like passed from the REST API
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

    :param date_string: a string containing a date or an offset
    :return: datetime object
    """
    date_string = date_string.strip()
    if date_string == "":
        return datetime.now()
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
        return datetime.now() + td

    # check 2016/12/23, 23.12.2016 and including hour and minutes.
    d = None
    for date_format in ["%Y/%m/%d", "%d.%m.%Y",
                        "%Y/%m/%d %I:%M%p",
                        "%d.%m.%Y %H:%M"]:
        try:
            d = datetime.strptime(date_string, date_format)
            break
        except ValueError:
            log.debug("Dateformat {1!s} did not match date {0!s}".format(
                date_string, date_format))

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
                    request.blueprint in ["validate_blueprint",
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
