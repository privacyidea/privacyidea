# -*- coding: utf-8 -*-
#
#  http://www.privacyidea.org
#  2015-09-28 Initial writeup.
#             Cornelius Kölbel <cornelius@privacyidea.org>
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
from OpenSSL import crypto
import binascii
from hashlib import sha256
import base64
import logging
import time
import ecdsa
import struct
import six
import codecs
from cryptography.hazmat.primitives.asymmetric.utils import (encode_dss_signature,
                                                             decode_dss_signature)

from privacyidea.lib.utils import (to_bytes, to_unicode, hexlify_and_unicode,
                                   urlsafe_b64encode_and_unicode)

__doc__ = """Helper functions for U2F protocol according to
https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment-20150514/fido-u2f-raw-message-formats.html

This file is tested in tests/test_lib_tokens_utf.py
"""

log = logging.getLogger(__name__)


def url_decode(url):
    """
    Decodes a base64 encoded, not padded string as used in FIDO U2F
    :param url: base64 urlsafe encoded string
    :type url: str
    :return: the decoded string
    :rtype: bytes
    """
    pad_len = len(url) % 4
    padding = pad_len * "="
    res = base64.urlsafe_b64decode(to_bytes(url + padding))
    return res


def url_encode(data):
    """
    Encodes a string base64 websafe and omits trailing padding "=".
    :param data: Some string
    :return: websafe b64 encoded string
    """
    url = urlsafe_b64encode_and_unicode(data)
    return url.strip("=")


def parse_response_data(resp_data):
    """
    According to https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment-20150514/fido-u2f-raw-message-formats.html#authentication-response-message-success
    the response is made up of
    0:      user presence byte
    1-4:    counter
    5-:     signature

    :param resp_data: response data from the FIDO U2F client
    :type resp_data: hex string
    :return: tuple of user_presence_byte(byte), counter(int),
        signature(hexstring)
    """
    resp_data_bin = binascii.unhexlify(resp_data)
    user_presence = six.int2byte(six.indexbytes(resp_data_bin, 0))
    signature = resp_data_bin[5:]
    counter = struct.unpack(">L", resp_data_bin[1:5])[0]
    return user_presence, counter, signature


def parse_registration_data(reg_data, verify_cert=True):
    """
    returns the parsed registration data in a tuple
    attestation_cert, user_pub_key, key_handle, signature, description

     * attestation_cert is a x509 object
     * user_pub_key is a hex string
     * key_handle is a hex string
     * signature is a hex string
     * description is a basestring

    see
    https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment
    -20150514/fido-u2f-raw-message-formats.html#registration-messages

    :param reg_data: base64 encoded registration data
    :param verify_cert: whether the attestation certificate should be verified
    :return: tuple
    """
    reg_data_bin = url_decode(reg_data)
    reserved_byte = six.int2byte(six.indexbytes(reg_data_bin, 0))  # must be '\x05'
    if reserved_byte != b'\x05':
        raise Exception("The registration data is in a wrong format. It must"
                        "start with 0x05")
    user_pub_key = reg_data_bin[1:66]
    key_handle_len = six.indexbytes(reg_data_bin, 66)
    # We need to save the key handle
    key_handle = reg_data_bin[67:67+key_handle_len]

    certificate = reg_data_bin[67+key_handle_len:]
    attestation_cert = crypto.load_certificate(crypto.FILETYPE_ASN1,
                                               certificate)
    cert_len = len(crypto.dump_certificate(crypto.FILETYPE_ASN1,
                                           attestation_cert))
    # TODO: Check the issuer of the certificate
    issuer = attestation_cert.get_issuer()
    log.debug("The attestation certificate is signed by {0!r}".format(issuer))
    not_after = to_unicode(attestation_cert.get_notAfter())
    not_before = to_unicode(attestation_cert.get_notBefore())
    log.debug("The attestation certificate "
              "is valid from %s to %s" % (not_before, not_after))
    start_time = time.strptime(not_before, "%Y%m%d%H%M%SZ")
    end_time = time.strptime(not_after, "%Y%m%d%H%M%SZ")
    # check the validity period of the certificate
    if verify_cert:
        if start_time > time.localtime() or \
                        end_time < time.localtime():  #pragma no cover
            log.error("The certificate is not valid. {0!s} -> {1!s}".format(not_before,
                                                                  not_after))
            raise Exception("The time of the attestation certificate is not "
                            "valid.")

    # Get the subject as description
    subj_x509name = attestation_cert.get_subject()
    subj_list = subj_x509name.get_components()
    description = ""
    cdump = to_unicode(crypto.dump_certificate(crypto.FILETYPE_PEM, attestation_cert))
    log.debug("This attestation certificate registered: {0!s}".format(cdump))

    for component in subj_list:
        # each component is a tuple. We are looking for CN
        if component[0].upper() == b"CN":
            description = to_unicode(component[1])
            break

    signature = reg_data_bin[67+key_handle_len+cert_len:]
    return (attestation_cert, hexlify_and_unicode(user_pub_key),
            hexlify_and_unicode(key_handle), hexlify_and_unicode(signature),
            description)


def check_registration_data(attestation_cert, app_id,
                            client_data, user_pub_key,
                            key_handle, signature):
    """
    See example in fido spec
    https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment-20150514/fido-u2f-raw-message-formats.html#registration-example

    In case of signature error an exception is raised

    :param attestation_cert: The Attestation cert of the FIDO device
    :type attestation_cert: x509 Object
    :param app_id: The appId
    :type app_id: str
    :param client_data: The ClientData
    :type client_data: str
    :param user_pub_key: The public key for this AppID
    :type user_pub_key: hex string
    :param key_handle: The keyHandle on the FIDO device
    :type key_handle: hex string
    :param signature: The signature of the registration request
    :type signature: hex string
    :return: Bool
    """
    app_id_hash = sha256(to_bytes(app_id)).digest()
    client_data_hash = sha256(to_bytes(client_data)).digest()
    reg_data = b'\x00' + app_id_hash + client_data_hash \
               + binascii.unhexlify(key_handle) + binascii.unhexlify(user_pub_key)
    try:
        crypto.verify(attestation_cert,
                      binascii.unhexlify(signature),
                      reg_data,
                      "sha256")
    except Exception as exx:
        raise Exception("Error checking the signature of the registration "
                        "data. %s" % exx)
    return True


def sign_challenge(user_priv_key, app_id, client_data, counter,
                   user_presence_byte=b'\x01'):
    """
    This creates a signature for the U2F data.
    Only used in test scenario

    The calculation of the signature is described here:
    https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment-20150514/fido-u2f-raw-message-formats.html#authentication-response-message-success

    The input_data is a concatenation of:
        * AppParameter: sha256(app_id)
        * The user presence [1byte]
        * counter [4byte]
        * ChallengeParameter: sha256(client_data)

    :param user_priv_key: The private key
    :type user_priv_key: hex string
    :param app_id: The application id
    :type app_id: str
    :param client_data: the stringified JSON
    :type client_data: str
    :param counter: the authentication counter
    :type counter: int
    :param user_presence_byte: one byte 0x01
    :type user_presence_byte: char
    :return: The DER encoded signature
    :rtype: hex string
    """
    app_id_hash = sha256(to_bytes(app_id)).digest()
    client_data_hash = sha256(to_bytes(client_data)).digest()
    counter_bin = struct.pack(">L", counter)
    input_data = app_id_hash + user_presence_byte + counter_bin + \
                 client_data_hash
    priv_key_bin = binascii.unhexlify(user_priv_key)
    sk = ecdsa.SigningKey.from_string(priv_key_bin, curve=ecdsa.NIST256p,
                                      hashfunc=sha256)
    signature = sk.sign(input_data)
    der_sig = der_encode(signature)
    return hexlify_and_unicode(der_sig)


def check_response(user_pub_key, app_id, client_data, signature,
                   counter, user_presence_byte=b'\x01'):
    """
    Check the ECDSA Signature with the given pubkey.
    The signed data is constructed from
     * app_id
     * user_presence_byte
     * counter and
     * client_data

    :param user_pub_key: The Application specific public key
    :type user_pub_key: hex string
    :param app_id: The AppID for this challenge response
    :type app_id: str
    :param client_data: The ClientData
    :type client_data: str
    :param counter: A counter
    :type counter: int
    :param user_presence_byte: User presence byte
    :type user_presence_byte: byte
    :param signature: The signature of the authentication request
    :type signature: hex string
    :return:
    """
    res = True
    app_id_hash = sha256(to_bytes(app_id)).digest()
    client_data_hash = sha256(to_bytes(client_data)).digest()
    user_pub_key_bin = binascii.unhexlify(user_pub_key)
    counter_bin = struct.pack(">L", counter)
    signature_bin = binascii.unhexlify(signature)

    input_data = app_id_hash + user_presence_byte + counter_bin \
                 + client_data_hash

    # The first byte 0x04 only indicates, that the public key is in the
    # uncompressed format x: 32 byte, y: 32byte
    user_pub_key_bin = user_pub_key_bin[1:]
    signature_bin_asn = der_decode(signature_bin)
    vkey = ecdsa.VerifyingKey.from_string(user_pub_key_bin,
                                          curve=ecdsa.NIST256p,
                                          hashfunc=sha256)
    try:
        vkey.verify(signature_bin_asn, input_data)
    except ecdsa.BadSignatureError:
        log.error("Bad signature for app_id {0!s}".format(app_id))
        res = False
    return res


def der_encode(signature_bin_asn):
    """
    This encodes a raw signature to DER.
    It uses the encode_dss_signature() function from cryptography.

    :param signature_bin_asn: RAW signature
    :type signature_bin_asn: bytes
    :return: DER encoded signature
    :rtype: bytes
    """
    if len(signature_bin_asn) != 64:
        raise Exception("The signature needs to be 64 bytes.")
    vr = int(binascii.hexlify(signature_bin_asn[:32]), 16)
    vs = int(binascii.hexlify(signature_bin_asn[32:]), 16)
    signature_bin = encode_dss_signature(vr, vs)
    return signature_bin


def der_decode(signature_bin):
    """
    This decodes a DER encoded signature so that it can be used with ecdsa.
    It uses the decode_dss_signature() function from cryptography.

    :param signature_bin: DER encoded signature
    :type signature_bin: bytes
    :return: raw signature
    :rtype: bytes
    """
    try:
        r, s = decode_dss_signature(signature_bin)
        sig_bin_asn = binascii.unhexlify('{0:064x}{1:064x}'.format(r, s))
    except ValueError as _e:
        raise Exception("The signature is not in supported DER format.")

    # we can only check for too long signatures since we prepend the hex-values
    # with '0' to reach 64 digits. This will prevent an error in case the one of
    # the values (r, s) is smaller than 32 bytes (first byte is '0'
    # in original value).
    if len(sig_bin_asn) != 64:
        raise Exception("The signature needs to be 64 bytes.")
    return sig_bin_asn


def x509name_to_string(x509name):
    """
    converts a X509Name to a string as in a DN

    :param x509name: THe X509Name object
    :return:
    """
    components = x509name.get_components()
    return ",".join(["{0}={1}".format(to_unicode(c[0]), to_unicode(c[1])) for c in components])
