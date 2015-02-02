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


def create_img(data, width=0, alt=None):
    """
        _create_img - create the qr image data

        :param data: input data that will be munched into the qrcode
        :type  data: string
        :param width: image width in pixel
        :type  width: int

        :return: image data to be used in an <img> tag
        :rtype:  string
    """
    width_str = ''
    alt_str = ''

    o_data = create_png(data, alt=alt)
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
