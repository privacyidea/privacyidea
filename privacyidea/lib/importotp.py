# -*- coding: utf-8 -*-
#
#  2016-01-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add PSKC import with pre shared key
#  2015-05-28 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add PSKC import
#  2014-12-11 Cornelius Kölbel <cornelius@privacyidea.org>
#             code cleanup during flask migration
#  2014-10-27 Cornelius Kölbel <cornelius@privacyidea.org>
#             add parsePSKCdata
#  2014-05-08 Cornelius Kölbel
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
'''This file is part of the privacyidea service
It is used for importing SafeNet (former Aladdin)
XML files, that hold the OTP secrets for eToken PASS.
'''

import xml.etree.ElementTree as etree
import re
import binascii
import base64
from privacyidea.lib.utils import modhex_decode
from privacyidea.lib.utils import modhex_encode
from privacyidea.lib.log import log_with
from privacyidea.lib.crypto import aes_decrypt
from Crypto.Cipher import AES
from bs4 import BeautifulSoup
import traceback
from passlib.utils.pbkdf2 import pbkdf2
from privacyidea.lib.utils import to_utf8

import logging
log = logging.getLogger(__name__)


def _create_static_password(key_hex):
    '''
    According to yubikey manual 5.5.5 the static-ticket is the same
    algorithm with no moving factors.
    The msg_hex that is encoded with the AES key is
    '000000000000ffffffffffffffff0f2e'
    '''
    msg_hex = "000000000000ffffffffffffffff0f2e"
    msg_bin = binascii.unhexlify(msg_hex)
    aes = AES.new(binascii.unhexlify(key_hex), AES.MODE_ECB)
    password_bin = aes.encrypt(msg_bin)
    password = modhex_encode(password_bin)

    return password


class ImportException(Exception):
    def __init__(self, description):
        self.description = description

    def __str__(self):
        return ('{0!s}'.format(self.description))


def getTagName(elem):
    match = re.match("^({.*?})(.*)$", elem.tag)
    if match:
        return match.group(2)
    else:
        return elem.tag


@log_with(log)
def parseOATHcsv(csv):
    '''
    (#653)
    This function parses CSV data for oath token.
    The file format is

        serial, key, [hotp,totp], [6,8], [30|60],
        serial, key, ocra, [ocra-suite]

    It imports sha1 hotp or totp token.
    I can also import ocra token.
    The default is hotp
    if totp is set, the default seconds are 30
    if ocra is set, an ocra-suite is required, otherwise the default
    ocra-suite is used.

    It returns a dictionary:
        {
            serial: {   'type' : xxxx,
                        'otpkey' : xxxx,
                        'timeStep' : xxxx,
                        'otplen' : xxx,
                        'ocrasuite' : xxx  }
        }
    '''
    TOKENS = {}

    csv_array = csv.split('\n')

    log.debug("the file contains {0:d} tokens.".format(len(csv_array)))
    for line in csv_array:
        l = line.split(',')
        serial = ""
        key = ""
        ttype = "hotp"
        seconds = 30
        otplen = 6
        hashlib = "sha1"
        ocrasuite = ""
        serial = l[0].strip()

        # check for empty line
        if len(serial) > 0 and not serial.startswith('#'):
            if len(l) >= 2:
                key = l[1].strip()

                if len(key) == 32:
                    hashlib = "sha256"
            else:
                log.error("the line {0!s} did not contain a hotp key".format(line))
                continue

            # ttype
            if len(l) >= 3:
                ttype = l[2].strip().lower()

            # otplen or ocrasuite
            if len(l) >= 4:
                if ttype != "ocra":
                    otplen = int(l[3].strip())
                elif ttype == "ocra":
                    ocrasuite = l[3].strip()

            # timeStep
            if len(l) >= 5:
                seconds = int(l[4].strip())

            log.debug("read the line |{0!s}|{1!s}|{2!s}|{3:d} {4!s}|{5:d}|".format(serial, key, ttype, otplen, ocrasuite, seconds))

            TOKENS[serial] = {'type': ttype,
                              'otpkey': key,
                              'timeStep': seconds,
                              'otplen': otplen,
                              'hashlib': hashlib,
                              'ocrasuite': ocrasuite
                              }
    return TOKENS


@log_with(log)
def parseYubicoCSV(csv):
    '''
    This function reads the CSV data as created by the Yubico personalization
    GUI.

    Traditional Format:
    Yubico OTP,12/11/2013 11:10,1,vvgutbiedkvi,
            ab86c04de6a3,d26a7c0f85fdda28bd816e406342b214,,,0,0,0,0,0,0,0,0,0,0
    OATH-HOTP,11.12.13 18:55,1,cccccccccccc,,
            916821d3a138bf855e70069605559a206ba854cd,,,0,0,0,6,0,0,0,0,0,0
    Static Password,11.12.13 19:08,1,,d5a3d50327dc,
            0e8e37b0e38b314a56748c030f58d21d,,,0,0,0,0,0,0,0,0,0,0

    Yubico Format:
    # OATH mode
    508326,,0,69cfb9202438ca68964ec3244bfa4843d073a43b,,2013-12-12T08:41:07,
    1382042,,0,bf7efc1c8b6f23604930a9ce693bdd6c3265be00,,2013-12-12T08:41:17,
    # Yubico mode
    508326,cccccccccccc,83cebdfb7b93,a47c5bf9c152202f577be6721c0113af,,
            2013-12-12T08:43:17,
    # static mode
    508326,,,9e2fd386224a7f77e9b5aee775464033,,2013-12-12T08:44:34,

    column 0: serial
    column 1: public ID in yubico mode
    column 2: private ID in yubico mode, 0 in OATH mode, blank in static mode
    column 3: AES key

    BUMMER: The Yubico Format does not contain the information,
    which slot of the token was written.

    If now public ID or serial is given, we can not import the token, as the
    returned dictionary needs the token serial as a key.

    It returns a dictionary with the new tokens to be created:

        {
            serial: {   'type' : yubico,
                        'otpkey' : xxxx,
                        'otplen' : xxx,
                        'description' : xxx
                         }
        }
    '''
    TOKENS = {}
    csv_array = csv.split('\n')

    log.debug("the file contains {0:d} tokens.".format(len(csv_array)))
    for line in csv_array:
        l = line.split(',')
        serial = ""
        key = ""
        otplen = 32
        public_id = ""
        slot = ""
        if len(l) >= 6:
            first_column = l[0].strip()
            if first_column.lower() in ["yubico otp",
                                        "oath-hotp",
                                        "static password"]:
                # traditional format
                typ = l[0].strip()
                slot = l[2].strip()
                public_id = l[3].strip()
                key = l[5].strip()

                if public_id == "":
                    # Usually a "static password" does not have a public ID!
                    # So we would bail out here for static passwords.
                    log.warning("No public ID in line {0!r}".format(line))
                    continue

                serial_int = int(binascii.hexlify(modhex_decode(public_id)),
                                 16)

                if typ.lower() == "yubico otp":
                    ttype = "yubikey"
                    otplen = 32 + len(public_id)
                    serial = "UBAM{0:08d}_{1!s}".format(serial_int, slot)
                    TOKENS[serial] = {'type': ttype,
                                      'otpkey': key,
                                      'otplen': otplen,
                                      'description': public_id
                                      }
                elif typ.lower() == "oath-hotp":
                    '''
                    WARNING: this does not work out at the moment, since the
                    Yubico GUI either
                    1. creates a serial in the CSV, but then the serial is
                       always prefixed! We can not authenticate with this!
                    2. if it does not prefix the serial there is no serial in
                       the CSV! We can not import and assign the token!
                    '''
                    ttype = "hotp"
                    otplen = 6
                    serial = "UBOM{0:08d}_{1!s}".format(serial_int, slot)
                    TOKENS[serial] = {'type': ttype,
                                      'otpkey': key,
                                      'otplen': otplen,
                                      'description': public_id
                                      }
                else:
                    log.warning("at the moment we do only support Yubico OTP"
                                " and HOTP: %r" % line)
                    continue
            elif first_column.isdigit():
                # first column is a number, (serial number), so we are
                # in the yubico format
                serial = first_column
                # the yubico format does not specify a slot
                slot = "X"
                key = l[3].strip()
                if l[2].strip() == "0":
                    # HOTP
                    typ = "hotp"
                    serial = "UBOM{0!s}_{1!s}".format(serial, slot)
                    otplen = 6
                elif l[2].strip() == "":
                    # Static
                    typ = "pw"
                    serial = "UBSM{0!s}_{1!s}".format(serial, slot)
                    key = _create_static_password(key)
                    otplen = len(key)
                    log.warning("We can not enroll a static mode, since we do"
                                " not know the private identify and so we do"
                                " not know the static password.")
                    continue
                else:
                    # Yubico
                    typ = "yubikey"
                    serial = "UBAM{0!s}_{1!s}".format(serial, slot)
                    public_id = l[1].strip()
                    otplen = 32 + len(public_id)
                TOKENS[serial] = {'type': typ,
                                  'otpkey': key,
                                  'otplen': otplen,
                                  'description': public_id
                                  }
        else:
            log.warning("the line {0!r} did not contain a enough values".format(line))
            continue

    return TOKENS


@log_with(log)
def parseSafeNetXML(xml):
    """
    This function parses XML data of a Aladdin/SafeNet XML
    file for eToken PASS

    It returns a dictionary of
        serial : { otpkey , counter, type }
    """

    TOKENS = {}
    elem_tokencontainer = etree.fromstring(xml)

    if getTagName(elem_tokencontainer) != "Tokens":
        raise ImportException("No toplevel element Tokens")

    for elem_token in list(elem_tokencontainer):
        SERIAL = None
        COUNTER = None
        HMAC = None
        DESCRIPTION = None
        if getTagName(elem_token) == "Token":
            SERIAL = elem_token.get("serial")
            log.debug("Found token with serial {0!s}".format(SERIAL))
            for elem_tdata in list(elem_token):
                tag = getTagName(elem_tdata)
                if "ProductName" == tag:
                    DESCRIPTION = elem_tdata.text
                    log.debug("The Token with the serial %s has the "
                              "productname %s" % (SERIAL, DESCRIPTION))
                if "Applications" == tag:
                    for elem_apps in elem_tdata:
                        if getTagName(elem_apps) == "Application":
                            for elem_app in elem_apps:
                                tag = getTagName(elem_app)
                                if "Seed" == tag:
                                    HMAC = elem_app.text
                                if "MovingFactor" == tag:
                                    COUNTER = elem_app.text
            if not SERIAL:
                log.error("Found token without a serial")
            else:
                if HMAC:
                    hashlib = "sha1"
                    if len(HMAC) == 64:
                        hashlib = "sha256"

                    TOKENS[SERIAL] = {'otpkey': HMAC,
                                      'counter': COUNTER,
                                      'type': 'hotp',
                                      'hashlib': hashlib
                                      }
                else:
                    log.error("Found token {0!s} without a element 'Seed'".format(
                              SERIAL))

    return TOKENS


def strip_prefix_from_soup(xml_soup):
    """
    We strip prefixes from the XML tags.
        <pskc:encryption>
        </pskc:encryption>
    results in:
        <encryption>
        </encryption>

    :param xml_soup: Beautiful Soup XML with tags with prefixes
    :type xml_soup: Beautiful Soup object
    :return: Beautiful Soup without prefixes in the tags
    """
    # strip the prefixes from the tags!
    for tag in xml_soup.findAll():
        if tag.name.find(":") >= 1:
            prefix, name = tag.name.split(":")
            tag.name = name

    return xml_soup


def derive_key(xml, password):
    """
    Derive the encryption key from the password with the parameters given
    in the XML soup.

    :param xml: The XML
    :param password: the password
    :return: The derived key, hexlified
    """
    if not password:
        raise ImportException("The XML KeyContainer specifies a derived "
                              "encryption key, but no password given!")

    keymeth= xml.keycontainer.encryptionkey.derivedkey.keyderivationmethod
    derivation_algo = keymeth["algorithm"].split("#")[-1]
    if derivation_algo.lower() != "pbkdf2":
        raise ImportException("We only support PBKDF2 as Key derivation "
                              "function!")
    salt = keymeth.find("salt").text.strip()
    keylength = keymeth.find("keylength").text.strip()
    rounds = keymeth.find("iterationcount").text.strip()
    r = pbkdf2(to_utf8(password), base64.b64decode(salt), int(rounds),
               int(keylength))
    return binascii.hexlify(r)


@log_with(log)
def parsePSKCdata(xml_data,
                  preshared_key_hex=None,
                  password=None,
                  do_checkserial=False):
    """
    This function parses XML data of a PSKC file, (RFC6030)
    It can read
    * AES-128-CBC encrypted (preshared_key_bin) data
    * password based encrypted data
    * plain text data

    :param xml_data: The XML data
    :type xml_data: basestring
    :param preshared_key_hex: The preshared key, hexlified
    :param password: The password that encrypted the keys
    :param do_checkserial: Check if the serial numbers conform to the OATH
        specification (not yet implemented)

    :return: a dictionary of token dictionaries
        { serial : { otpkey , counter, .... }}
    """

    tokens = {}
    #xml = BeautifulSoup(xml_data, "lxml")
    xml = strip_prefix_from_soup(BeautifulSoup(xml_data, "lxml"))

    if xml.keycontainer.encryptionkey and \
            xml.keycontainer.encryptionkey.derivedkey:
        # If we have a password we also need a tag EncryptionKey in the
        # KeyContainer
        preshared_key_hex = derive_key(xml, password)

    key_packages = xml.keycontainer.findAll("keypackage")
    for key_package in key_packages:
        token = {}
        key = key_package.key
        try:
            token["description"] = key_package.deviceinfo.manufacturer.string
        except Exception as exx:
            log.debug("Can not get manufacturer string {0!s}".format(exx))
        serial = key["id"]
        try:
            serial = key_package.deviceinfo.serialno.string
        except Exception as exx:
            log.debug("Can not get serial string from device info {0!s}".format(exx))
        algo = key["algorithm"]
        token["type"] = algo[-4:].lower()
        parameters = key.algorithmparameters
        token["otplen"] = parameters.responseformat["length"] or 6
        try:
            if key.data.secret.plainvalue:
                secret = key.data.secret.plainvalue.string
                token["otpkey"] = binascii.hexlify(base64.b64decode(secret))
            elif key.data.secret.encryptedvalue:
                encryptionmethod = key.data.secret.encryptedvalue.encryptionmethod
                enc_algorithm = encryptionmethod["algorithm"].split("#")[-1]
                if enc_algorithm.lower() != "aes128-cbc":
                    raise ImportException("We only import PSKC files with "
                                          "AES128-CBC.")
                enc_data = key.data.secret.encryptedvalue.ciphervalue.text
                enc_data = base64.b64decode(enc_data.strip())
                enc_iv = enc_data[:16]
                enc_cipher = enc_data[16:]
                secret = aes_decrypt(binascii.unhexlify(preshared_key_hex),
                                     enc_iv, enc_cipher)
                token["otpkey"] = binascii.hexlify(secret)
        except Exception as exx:
            log.error("Failed to import tokendata: {0!s}".format(exx))
            log.debug(traceback.format_exc())
            raise ImportException("Failed to import tokendata. Wrong "
                                  "encryption key? %s" % exx)
        if token["type"] == "hotp" and key.data.counter:
                token["counter"] = key.data.counter.text.strip()
        elif token["type"] == "totp" and key.data.timeinterval:
                token["timeStep"] = key.data.timeinterval.text.strip()

        tokens[serial] = token
    return tokens
