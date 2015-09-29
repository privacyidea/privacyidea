# -*- coding: utf-8 -*-
#
#  http://www.privacyidea.org
#  2015-09-28 Initial writeup.
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
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
__doc__ = """Helper functions for U2F protocol according to
https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment-20150514/fido-u2f-raw-message-formats.html

This file is tested in tests/test_lib_tokens_utf.py
"""
from OpenSSL import crypto
import binascii
from hashlib import sha256
import base64
import logging
import time
import ecdsa
import struct

log = logging.getLogger(__name__)


def url_decode(url):
    """
    Decodes a base64 encoded, not padded string as used in FIDO U2F
    :param url: base64 urlsafe encoded string
    :return: string
    """
    pad_len = len(url) % 4
    padding = pad_len * "="
    res = base64.urlsafe_b64decode(str(url) + padding)
    return res


def url_encode(data):
    """
    Encodes a string base64 websafe and omits trailing padding "=".
    :param data: Some string
    :return: websafe b64 encoded string
    """
    url = base64.urlsafe_b64encode(data)
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
    user_presence = resp_data_bin[0]
    signature = resp_data_bin[5:]
    counter = struct.unpack(">L", resp_data_bin[1:5])[0]
    return user_presence, counter, signature


def parse_registration_data(reg_data):
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
    :return: tuple
    """
    reg_data_bin = url_decode(reg_data)
    reserved_byte = reg_data_bin[0]  # must be '\x05'
    user_pub_key = reg_data_bin[1:66]
    key_handle_len = ord(reg_data_bin[66])
    # We need to save the key handle
    key_handle = reg_data_bin[67:67+key_handle_len]

    certificate = reg_data_bin[67+key_handle_len:]
    attestation_cert = crypto.load_certificate(crypto.FILETYPE_ASN1,
                                               certificate)
    cert_len = len(crypto.dump_certificate(crypto.FILETYPE_ASN1,
                                           attestation_cert))
    # TODO: Check the issuer of the certificate
    issuer = attestation_cert.get_issuer()
    log.debug("The attestation certificate is signed by %s" % issuer)
    not_after = attestation_cert.get_notAfter()
    not_before = attestation_cert.get_notBefore()
    log.debug("The attestation certificate "
              "is valid from %s to %s" % (not_before, not_after))
    start_time = time.strptime(not_before, "%Y%m%d%H%M%SZ")
    end_time = time.strptime(not_after, "%Y%m%d%H%M%SZ")
    # check the validity period of the certificate
    if start_time > time.localtime() or \
                    end_time < time.localtime():  #pragma no cover
        log.error("The certificate is not valid. %s -> %s" % (not_before,
                                                              not_after))
        raise Exception("The time of the attestation certificate is not "
                        "valid.")

    # Get the subject as description
    subj_x509name = attestation_cert.get_subject()
    subj_list = subj_x509name.get_components()
    for component in subj_list:
        # each component is a tuple. We are looking for CN
        if component[0].upper() == "CN":
            description = component[1]
            break

    signature = reg_data_bin[67+key_handle_len+cert_len:]
    return (attestation_cert, binascii.hexlify(user_pub_key),
            binascii.hexlify(key_handle), binascii.hexlify(signature),
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
    :type app_id: basestring
    :param client_data: The ClientData
    :type client_data: basestring
    :param user_pub_key: The public key for this AppID
    :type user_pub_key: hex string
    :param key_handle: The keyHandle on the FIDO device
    :type key_handle: hex string
    :param signature: The signature of the registration request
    :type signature: hex string
    :return: Bool
    """
    app_id_hash = sha256(app_id).digest()
    client_data_hash = sha256(client_data).digest()
    try:
        crypto.verify(attestation_cert,
                      binascii.unhexlify(signature),
                          chr(0x00) +
                          app_id_hash +
                          client_data_hash +
                          binascii.unhexlify(key_handle) +
                          binascii.unhexlify(user_pub_key),
                          "sha256")
    except Exception as exx:
        raise Exception("Error checking the signature of the registration "
                        "data. %s" % exx)
    return True


def check_response(user_pub_key, app_id, client_data, signature,
                   counter, user_presence_byte=chr(0x01)):
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
    :type app_id: basestring
    :param client_data: The ClientData
    :type client_data: basestring
    :param counter: A counter
    :type counter: int
    :param user_presence_byte: User presence byte
    :type user_presence_byte: char
    :param signature: The signature of the authentication request
    :type signature: hex string
    :return:
    """
    app_id_hash = sha256(app_id).digest()
    client_data_hash = sha256(client_data).digest()
    user_pub_key_bin = binascii.unhexlify(user_pub_key)
    counter_bin = struct.pack(">L", counter)
    signature_bin = binascii.unhexlify(signature)

    input_data = app_id_hash + user_presence_byte + counter_bin + \
                 client_data_hash

    # The first byte 0x04 only indicates, that the public key is in the
    # uncompressed format x: 32 byte, y: 32byte
    user_pub_key_bin = user_pub_key_bin[1:]
    # We need to decode the DER encoded signature, so that we can use it with
    # ecdsa. (see http://crypto.stackexchange.com/questions/1795/how-can-i
    # -convert-a-der-ecdsa-signature-to-asn-1)
    # DER encoded signature: 0x30 b1 0x02 b2 (vr) 0x02 b3 (vs)
    b2 = ord(signature_bin[3])
    vr = signature_bin[4:4+b2]
    if b2 == 33:
        # Note: The DER encoding requires a leading 0x00 in case the first
        # byte is >=128 (signed int)
        # To verify the signature, we can drop the Null-Byte
        vr = vr[1:]
    b3 = ord(signature_bin[5+b2])
    vs = signature_bin[6+b2:6+b2+b3]
    if b3 == 33:
        vs = vs[1:]
    signature_bin_asn = vr + vs
    assert(len(signature_bin_asn) == 64)
    vkey = ecdsa.VerifyingKey.from_string(user_pub_key_bin,
                                          curve=ecdsa.NIST256p,
                                          hashfunc=sha256)
    vkey.verify(signature_bin_asn, input_data)
    return True
