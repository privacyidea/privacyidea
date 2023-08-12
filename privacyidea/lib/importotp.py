# -*- coding: utf-8 -*-
#
#  2021-02-04 Timo Sturm <timo.sturm@netknights.it>
#             Fix import of yubikeys from yubico
#  2020-11-11 Timo Sturm <timo.sturm@netknights.it>
#             Select how to validate PSKC imports
#  2018-05-10 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add fileversion to OATH CSV
#  2017-11-24 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Generate the encryption key for PSKC export
#             in the HSM
#  2017-10-17 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Allow export to pskc file
#  2017-01-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Avoid XML bombs
#  2016-07-17 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add GPG encrpyted import
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
import hmac, hashlib
import defusedxml.ElementTree as etree
import re
import binascii
import base64
import html
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from privacyidea.lib.error import TokenImportException
from privacyidea.lib.utils import (modhex_decode, modhex_encode,
                                   hexlify_and_unicode, to_unicode, to_utf8,
                                   b64encode_and_unicode)
from privacyidea.lib.config import get_token_class
from privacyidea.lib.log import log_with
from privacyidea.lib.crypto import (aes_decrypt_b64, aes_encrypt_b64, geturandom)
from bs4 import BeautifulSoup
import traceback
from passlib.crypto.digest import pbkdf2_hmac
import gnupg
from os import path

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
    cipher = Cipher(algorithms.AES(binascii.unhexlify(key_hex)),
                    modes.ECB(), default_backend())  # nosec B305 # part of Yubikey specification
    encryptor = cipher.encryptor()
    password_bin = encryptor.update(msg_bin) + encryptor.finalize()
    password = modhex_encode(password_bin)

    return password


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

    for HOTP
        serial, key, hotp, [6|8], [counter]

    for TOTP
        serial, key, totp, [6|8], [30|60]

    for OCRA
        serial, key, ocra, [ocra-suite]

    for TAN
        serial, key, tan, tan1 tan2 tan3 tan4

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
    version = 0

    csv_array = csv.split('\n')

    m = re.match(r"^#\s*version:\s*(\d+)", csv_array[0])
    if m:
        version = m.group(1)
        log.debug("the file is version {0}.".format(version))

    log.debug("the file contains {0:d} lines.".format(len(csv_array)))
    for line in csv_array:
        # Do not parse comment lines
        if line.startswith("#"):
            continue

        l = line.split(',')
        # Do not parse emtpy lines, it could be [] or ['']
        if len(l) <= 1:
            continue

        # Import the user
        user = {}
        if version == "2":
            # extract the user from the first three columns
            user["username"] = l.pop(0).strip()
            user["resolver"] = l.pop(0).strip()
            user["realm"] = l.pop(0).strip()

        # check for empty serial
        serial = l[0].strip()
        if len(serial) > 0:
            if len(l) < 2:
                log.error("the line {0!s} did not contain a hotp key".format(line))
                continue

            # ttype
            if len(l) == 2:
                # No tokentype, take the default "hotp"
                l.append("hotp")

            ttype = l[2].strip().lower()

            tok_class = get_token_class(ttype)
            params = tok_class.get_import_csv(l)
            log.debug("read the line {0!s}".format(params))

            params["user"] = user
            TOKENS[serial] = params

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
    try:
        elem_tokencontainer = etree.fromstring(xml)
    except etree.ParseError as e:
        log.debug(traceback.format_exc())
        raise TokenImportException('Could not parse XML data: {0!s}'.format(e))

    if getTagName(elem_tokencontainer) != "Tokens":
        raise TokenImportException("No toplevel element Tokens")

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
        raise TokenImportException("The XML KeyContainer specifies a derived "
                              "encryption key, but no password given!")

    keymeth = xml.keycontainer.encryptionkey.derivedkey.keyderivationmethod
    derivation_algo = keymeth["algorithm"].split("#")[-1]
    if derivation_algo.lower() != "pbkdf2":
        raise TokenImportException("We only support PBKDF2 as Key derivation "
                              "function!")
    salt = keymeth.find("salt").text.strip()
    keylength = keymeth.find("keylength").text.strip()
    rounds = keymeth.find("iterationcount").text.strip()
    r = pbkdf2_hmac('sha1', to_utf8(password), base64.b64decode(salt),
                    rounds=int(rounds), keylen=int(keylength))
    return binascii.hexlify(r)


@log_with(log)
def parsePSKCdata(xml_data,
                  preshared_key_hex=None,
                  password=None,
                  validate_mac='check_fail_hard',
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
    :param validate_mac: Operation mode of hmac validation. Possible values:
        - 'check_fail_hard' : If an invalid hmac is encountered no token gets parsed.
        - 'check_fail_soft' : Skip tokens with invalid MAC.
        - 'no_check' : Hmac of tokens are not checked, every token is parsed.

    :return: tuple of a dictionary of token dictionaries and a list of serial of not imported tokens
        { serial : { otpkey , counter, .... }}, [serial, serial, ...]
    """

    abort = False

    not_imported_serials = []
    tokens = {}
    xml = strip_prefix_from_soup(BeautifulSoup(xml_data, "lxml"))

    if not xml.keycontainer:
        raise TokenImportException("No KeyContainer found in PSKC data. Could not "
                              "import any tokens.")
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

        algo = key["algorithm"]
        serial = key["id"]

        # Special treatment for pskc files exported from Yubico
        yubi_mapping = {"http://www.yubico.com/#yubikey-aes": ("yubikey", "UBAM"),
                        "urn:ietf:params:xml:ns:keyprov:pskc:hotp": ("hotp", "UBOM")}
        if algo in yubi_mapping.keys() and re.match(r"\d+:\d+",
                                                    serial):  # check if the serial fits the pattern "<SerialNo>:<Slot>
            t_type = yubi_mapping[algo][0]
            serial_split = serial.split(":")
            serial_no = serial_split[0]
            slot = serial_split[1]
            serial = "{!s}{!s}_{!s}".format(yubi_mapping[algo][1], serial_no, slot)
        else:
            try:
                serial = key_package.deviceinfo.serialno.string.strip()
            except Exception as exx:
                log.debug("Can not get serial string from device info {0!s}".format(exx))
            t_type = algo.split(":")[-1].lower()

        token["type"] = t_type

        parameters = key.algorithmparameters
        token["otplen"] = parameters.responseformat["length"] or 6
        # token["hashlib"] = parameters.suite or "sha1"

        hash_lib = "sha1"

        # Check if hashlib is explicitly set in file
        if parameters.suite and parameters.suite.string:
            hash_lib = parameters.suite.string.lower()
        else:
            log.warning("No hashlib defined, falling back to default {}.".format(hash_lib))

        token["hashlib"] = hash_lib

        try:
            if key.data.secret.plainvalue:
                secret = key.data.secret.plainvalue.string
                token["otpkey"] = hexlify_and_unicode(base64.b64decode(secret))
            elif key.data.secret.encryptedvalue:
                encryptionmethod = key.data.secret.encryptedvalue.encryptionmethod
                enc_algorithm = encryptionmethod["algorithm"].split("#")[-1]
                if enc_algorithm.lower() != "aes128-cbc":
                    raise TokenImportException("We only import PSKC files with "
                                          "AES128-CBC.")
                enc_data = key.data.secret.encryptedvalue.ciphervalue.text
                enc_data = enc_data.strip()

                preshared_key = binascii.unhexlify(preshared_key_hex)

                secret = aes_decrypt_b64(preshared_key, enc_data)

                if token["type"].lower() in ["hotp", "totp"]:
                    token["otpkey"] = hexlify_and_unicode(secret)
                elif token["type"].lower() in ["pw"]:
                    token["otpkey"] = to_unicode(secret)
                else:
                    token["otpkey"] = to_unicode(secret)

                if validate_mac != 'no_check':
                    # Validate MAC:
                    encrypted_mac_key = xml.keycontainer.find("mackey").text
                    mac_key = aes_decrypt_b64(preshared_key, encrypted_mac_key)

                    enc_data_bin = base64.b64decode(enc_data)
                    hm = hmac.new(key=mac_key, msg=enc_data_bin, digestmod=hashlib.sha1)
                    mac_value_calculated = b64encode_and_unicode(hm.digest())

                    mac_value_xml = key.data.find('valuemac').text.strip()

                    is_invalid = not hmac.compare_digest(mac_value_xml, mac_value_calculated)

                    if is_invalid and validate_mac == 'check_fail_hard':
                        abort = True
                    elif is_invalid and validate_mac == 'check_fail_soft':
                        not_imported_serials.append(serial)
                        continue

        except Exception as exx:
            log.error("Failed to import tokendata: {0!s}".format(exx))
            log.debug(traceback.format_exc())
            raise TokenImportException("Failed to import tokendata. Wrong "
                                  "encryption key? %s" % exx)

        if token["type"] in ["hotp", "totp"] and key.data.counter:
            token["counter"] = key.data.counter.text.strip()
        if token["type"] == "totp":
            if key.data.timeinterval:
                token["timeStep"] = key.data.timeinterval.text.strip()
            if key.data.timedrift:
                token["timeShift"] = key.data.timedrift.text.strip()

        tokens[serial] = token

    if abort:
        not_imported_serials = tokens.keys()
        tokens = {}  # reset tokens

    return tokens, not_imported_serials


class GPGImport(object):
    """
    This class is used to decrypt GPG encrypted import files.

    The decrypt method returns the unencrpyted files.

    Create the keypair like this:

    GNUPGHOME=/etc/privacyidea/gpg gpg --gen-key
    """
    def __init__(self, config=None):
        self.config = config or {}
        self.gnupg_home = self.config.get("PI_GNUPG_HOME",
                                          "/etc/privacyidea/gpg")
        if path.isdir(self.gnupg_home):
            self.gpg = gnupg.GPG(gnupghome=self.gnupg_home)
            self.private_keys = self.gpg.list_keys(True)
        else:
            log.warning("Directory {} does not exists!".format(self.gnupg_home))



    def get_publickeys(self):
        """
        This returns the public GPG key to be displayed in the Import Dialog.
        The administrator can send this public key to his token vendor and
        the token vendor can use this public key to encrypt the token import
        file.
        :return: a dictionary of public keys with fingerprint
        """
        public_keys = {}
        if path.isdir(self.gnupg_home):
            keys = self.gpg.list_keys(secret=True)
        else:
            keys = []
            log.warning("Directory {} does not exists!".format(self.gnupg_home))

        for key in keys:
            ascii_armored_public_key = self.gpg.export_keys(key.get("keyid"))
            public_keys[key.get("keyid")] = {"armor": ascii_armored_public_key,
                                             "fingerprint": key.get(
                                                 "fingerprint")}
        return public_keys

    def decrypt(self, input_data):
        """
        Decrypts the input data with one of the private keys.

        Since this functionality is only used for decrypting import lists, the
        decrypted data is assumed to be of type text und thus converted to unicode.

        :param input_data: The data to decrypt
        :type input_data: str or bytes
        :return: The decrypted input_data
        :rtype: str
        """
        decrypted = self.gpg.decrypt(message=input_data)

        if not decrypted.ok:
            log.error("Decrpytion failed: {0!s}. {1!s}".format(
                decrypted.status, decrypted.stderr))
            raise Exception(decrypted.stderr)

        return to_unicode(decrypted.data)


def export_pskc(tokenobj_list, psk=None):
    """
    Take a list of token objects and create a beautifulsoup xml object.

    If no preshared key is given, we create one and return it.

    :param tokenobj_list: list of token objects
    :param psk: pre-shared-key for AES-128-CBC in hex format
    :return: tuple of (psk, number of tokens, beautifulsoup)
    """
    if psk:
        psk = binascii.unhexlify(psk)
    else:
        psk = geturandom(16)

    mackey = geturandom(20)
    encrypted_mackey = aes_encrypt_b64(psk, mackey)
    number_of_exported_tokens = 0

    # define the header
    soup = BeautifulSoup("""<KeyContainer Version="1.0"
     xmlns="urn:ietf:params:xml:ns:keyprov:pskc"
     xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
     xmlns:xenc="http://www.w3.org/2001/04/xmlenc#">
     <EncryptionKey>
         <ds:KeyName>Pre-shared-key</ds:KeyName>
     </EncryptionKey>
     <MACMethod Algorithm="http://www.w3.org/2000/09/xmldsig#hmac-sha1">
         <MACKey>
             <xenc:EncryptionMethod
             Algorithm="http://www.w3.org/2001/04/xmlenc#aes128-cbc"/>
             <xenc:CipherData>
                 <xenc:CipherValue>{encrypted_mackey}</xenc:CipherValue>
             </xenc:CipherData>
         </MACKey>
     </MACMethod>
""".format(encrypted_mackey=encrypted_mackey), "html.parser")

    for tokenobj in tokenobj_list:
        if tokenobj.type.lower() not in ["totp", "hotp", "pw"]:
            continue
        type = tokenobj.type.lower()
        issuer = "privacyIDEA"
        try:
            manufacturer = tokenobj.token.description.encode("ascii", "replace")
            manufacturer = to_unicode(manufacturer)
        except UnicodeEncodeError:
            manufacturer = "deleted during export"
        serial = tokenobj.token.serial
        otplen = tokenobj.token.otplen
        counter = tokenobj.token.count
        suite = tokenobj.get_tokeninfo("hashlib", default="sha1")
        if type == "totp":
            timestep = tokenobj.get_tokeninfo("timeStep")
            timedrift = tokenobj.get_tokeninfo("timeShift")
        else:
            timestep = 0
            timedrift = 0
        otpkey = tokenobj.token.get_otpkey().getKey()
        try:
            if tokenobj.type.lower() in ["totp", "hotp"]:
                encrypted_otpkey = aes_encrypt_b64(psk, binascii.unhexlify(otpkey))
            elif tokenobj.type.lower() in ["pw"]:
                encrypted_otpkey = aes_encrypt_b64(psk, otpkey)
            else:
                encrypted_otpkey = aes_encrypt_b64(psk, otpkey)

            hm = hmac.new(key=mackey, msg=base64.b64decode(encrypted_otpkey), digestmod=hashlib.sha1)
            mac_value = b64encode_and_unicode(hm.digest())
        except TypeError:
            # Some keys might be odd string length
            continue
        try:
            kp2 = BeautifulSoup("""<KeyPackage>
        <DeviceInfo>
          <Manufacturer>{manufacturer}</Manufacturer>
          <SerialNo>{serial}</SerialNo>
        </DeviceInfo>
        <Key Id="{serial}"
             Algorithm="urn:ietf:params:xml:ns:keyprov:pskc:{type}">
                 <Issuer>{issuer}</Issuer>
                 <AlgorithmParameters>
                     <ResponseFormat Length="{otplen}" Encoding="DECIMAL"/>
                     <Suite hashalgo="{suite}" />
                 </AlgorithmParameters>
                 <Data>
                    <Secret>
                         <EncryptedValue>
                             <xenc:EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#aes128-cbc"/>
                             <xenc:CipherData>
                                 <xenc:CipherValue>{encrypted_otpkey}</xenc:CipherValue>
                             </xenc:CipherData>
                         </EncryptedValue>
                         <ValueMAC>{value_mac}</ValueMAC>
                     </Secret>
                    <Time>
                        <PlainValue>0</PlainValue>
                    </Time>
                    <TimeInterval>
                        <PlainValue>{timestep}</PlainValue>
                    </TimeInterval>
                    <Counter>
                        <PlainValue>{counter}</PlainValue>
                    </Counter>
                    <TimeDrift>
                        <PlainValue>{timedrift}</PlainValue>
                    </TimeDrift>
                </Data>
        </Key>
        </KeyPackage>""".format(serial=html.escape(serial), type=html.escape(type), otplen=otplen,
                                issuer=html.escape(issuer), manufacturer=html.escape(manufacturer),
                                counter=counter, timestep=timestep, encrypted_otpkey=encrypted_otpkey,
                                timedrift=timedrift, value_mac=mac_value,
                                suite=html.escape(suite)), "html.parser")

            soup.macmethod.insert_after(kp2)
            number_of_exported_tokens += 1
        except Exception as e:
            log.warning("Failed to export the token {0!s}: {1!s}".format(serial, e))
            tb = traceback.format_exc()
            log.debug(tb)

    return hexlify_and_unicode(psk), number_of_exported_tokens, soup
