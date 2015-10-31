from .log import log_with
import logging
log = logging.getLogger(__name__)
import binascii
from .crypto import geturandom
import qrcode
import StringIO
import urllib
from privacyidea.lib.crypto import urandom
import string
import re
from datetime import timedelta

def generate_otpkey(key_size=20):
    """
    generates the HMAC key of keysize. Should be 20 or 32
    The key is returned as a hexlified string
    :param key_size: The size of the key to generate
    :type key_size: int
    :return: hexlified key
    :rtype: string
    """
    log.debug("generating key of size %s" % key_size)
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
        width_str = " width=%d " % (int(width))

    if alt is not None:
        val = urllib.urlencode({'alt': alt})
        alt_str = " alt=%r " % (val[len('alt='):])

    ret_img = 'data:image/png;base64,%s' % data_uri

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
        raise Exception("type or description without necessary data! %s" %
                        unicode(params))

    return data, types, desc


def parse_timedelta(delta):
    """
    This parses a string that contains a time delta for the last_auth policy
    in the format like
    1h, 1d, 1y.

    :param delta: The time delta
    :type delta: basestring
    :return: timedelta
    """
    delta = delta.strip().replace(" ", "")
    time_specifier = delta[-1].lower()
    if time_specifier not in ["h", "d", "y"]:
        raise Exception("Invalid time specifier")
    time = int(delta[:-1])
    td = timedelta(hours=time)
    if time_specifier == "d":
        td = timedelta(days=time)
    if time_specifier == "y":
        td = timedelta(days=time*365)

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
