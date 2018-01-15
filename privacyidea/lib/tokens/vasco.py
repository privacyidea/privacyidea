# -*- coding: utf-8 -*-
#
#    LinOTP - the open source solution for two factor authentication
#    Copyright (C) 2010 - 2017 KeyIdentity GmbH
#
#    This program is free software: you can redistribute it and/or
#    modify it under the terms of the GNU Affero General Public
#    License, version 3, as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the
#               GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#    E-mail: linotp@keyidentity.com
#    Contact: www.linotp.org
#    Support: www.keyidentity.com
""" Import tokens from the vasco dpx files """

import pickle
import zlib
import os
import logging

# from ctypes import *
from ctypes import CDLL
from ctypes import Structure

from ctypes import pointer
from ctypes import c_void_p
from ctypes import c_char_p

from ctypes import c_int
from ctypes import c_ulong
from ctypes import c_char
from ctypes import c_byte

from tempfile import NamedTemporaryFile


from pylons import config


__all__ = ["parseVASCOdata", "vasco_otp_check"]


log = logging.getLogger(__name__)

vasco_dll = None
vasco_libs = []

# get the Vacman Controller lib
fallbacks = ["/opt/vasco/Vacman_Controller/lib/libaal2sdk.so"]

vasco_lib = config.get("linotpImport.vasco_dll")
if not vasco_lib:
    log.info("Missing linotpImport.vasco_dll in config file")
else:
    vasco_libs.append(vasco_lib)

vasco_libs.extend(fallbacks)
for vasco_lib in vasco_libs:
    try:
        log.debug("loading vasco lib %r", vasco_lib)
        vasco_dll = CDLL(vasco_lib)
        break
    except Exception as exx:
        log.info("cannot load vasco library: %r", exx)


# decorator: check_vasco
def check_vasco(fn):
    '''
    This is a decorator:
    checks if vasco dll is defined,
    it then runs the function otherwise returns NONE

    :param fn: function - the to be called function
    :return: return the function call result
    '''
    def new(*args, **kw):
        if not vasco_dll:
            log.error("[check_vasco] No vasco dll available!")
            return None
        else:
            return fn(*args, **kw)
    return new


class TDPXHandle(Structure):
    """
    Handle struct
    """
    _fields_ = [("pHandleDpxContext", c_void_p),
                ("pHandleDpxInitKey", c_void_p)]


class TKernelParams(Structure):
    """
    KernelParams struct
    """
    _fields_ = [("ParmCount", c_ulong),
                ("ITimeWindow", c_ulong),
                ("STimeWindow", c_ulong),
                ("DiagLevel", c_ulong),
                ("GMTAdjust", c_ulong),
                ("CheckChallenge", c_ulong),
                ("IThreshold", c_ulong),
                ("SThreshold", c_ulong),
                ("ChkInactDays", c_ulong),
                ("DeriveVector", c_ulong),
                ("SyncWindow", c_ulong),
                ("OnLineSG", c_ulong),
                ("EventWindow", c_ulong),
                ("HSMSlotId", c_ulong),
                ("StorageKeyId", c_ulong),
                ("TransportKeyId", c_ulong),
                ("StorageDeriveKey1", c_ulong),
                ("StorageDeriveKey2", c_ulong),
                ("StorageDeriveKey3", c_ulong),
                ("StorageDeriveKey4", c_ulong), ]


class TDigipassBlob(Structure):
    """
    Digi Pass Token Blob struct
    """
    _fields_ = [("Serial", c_char * 10),
                ("AppName", c_char * 12),
                ("DPFlags", c_byte * 2),
                ("Blob", c_char * 224)]


def vasco_dpxinit(filename="demovdp.dpx", transportkey=None):
    '''
    This function returns
     - error code
     - filehandle (TDPXHandle)
     - application count
     - application names
     - token counts
    '''
    if not transportkey:
        transportkey = "1" * 32

    c_filename = c_char_p(filename)
    c_transportkey = c_char_p(transportkey)
    # string with 97 bytes
    appl_names = "." * 97
    p_names = c_char_p(appl_names)

    filehandle = TDPXHandle()
    p_fh = pointer(filehandle)

    appl_count = c_int(0)
    p_acount = pointer(appl_count)

    token_count = c_int(0)
    p_tcount = pointer(token_count)

    res = vasco_dll.AAL2DPXInit(p_fh,
                                c_filename,
                                c_transportkey,
                                p_acount,
                                p_names,
                                p_tcount)

    return (res, filehandle, appl_count, appl_names, token_count)


def vasco_getstatic_vector(handle, params):
    """

    """
    vector = "." * 113
    p_vector = c_char_p(vector)
    vector_len = c_int(112)
    p_vector_len = pointer(vector_len)
    res = vasco_dll.AAL2DPXGetStaticVector(pointer(handle),
                                           pointer(params),
                                           p_vector,
                                           p_vector_len)

    return (res, vector, vector_len)


def vasco_gettoken(handle, params, select_appl):
    """
    access the vasco token data object
    """
    dpdata = TDigipassBlob()
    serial = "\0" * 23
    typ = "\0" * 6
    authmode = "\0" * 3
    res = vasco_dll.AAL2DPXGetToken(pointer(handle),
                                    pointer(params),
                                    c_char_p(select_appl),
                                    c_char_p(serial),
                                    c_char_p(typ),
                                    c_char_p(authmode),
                                    pointer(dpdata))

    return (res, serial, typ, authmode, dpdata)


def vasco_dpxclose(handle):
    """
    close the vasco blob
    """
    res = vasco_dll.AAL2DPXClose(pointer(handle))
    return res


def vasco_genpassword(data, params, challenge="\0" * 16):
    password = "\0" * 41
    res = vasco_dll.AAL2GenPassword(pointer(data),
                                    pointer(params),
                                    c_char_p(password),
                                    c_char_p(challenge))
    return (res, password)


def vasco_verify(data, params, password, challenge="\0" * 16):
    res = vasco_dll.AAL2VerifyPassword(pointer(data),
                                       pointer(params),
                                       c_char_p(password),
                                       c_char_p(challenge))

    return (res, data)


def vasco_settokenproperty(data, params, prop, value):
    '''
    can be used to do not use a static PIN
    pin_supported (6) : enable=1, disable=2
    '''
    res = vasco_dll.AAL2SetTokenProperty(pointer(data),
                                         pointer(params),
                                         c_ulong(prop),
                                         c_ulong(value))
    return (res, data)


def vasco_gettokenproperty(data, params, prop):
    '''
    This function returns token properties.
    PIN_LEN: property = 10
    '''
    value = 0
    res = vasco_dll.AAL2GetTokenProperty(pointer(data),
                                         pointer(params),
                                         c_ulong(prop),
                                         pointer(c_ulong(value)))
    return (res, value)


def vasco_compress(datablob):
    '''
    Compresses the data to be stored in the token database.
    The data object is pickled and compressed.

    :param datablob: Vasco Data Blob
    :return: compressed data to be stored in Token database
    '''
    return zlib.compress(pickle.dumps(datablob))


def vasco_decompress(tokendata):
    '''
    De-compresses the data when loaded from the token database.
    The data object is pickled and compressed.

    :param tokendata: The encrypted OTP Key from the database
    :return: The Vasco data blob
    '''
    return pickle.loads(zlib.decompress(tokendata))


@check_vasco
def parseVASCOdata(fileString=None, arg_otplen=6, transportkey=None):
    '''
    Parses the DPX data and returns the dictionary with the token description
    for the token_init:

       parsed_tokens[serial] = { hmac_key, type, otplen, . . }

    :param fileString: the dpx file as strings
    :param arg_otplen: the otplen of the imported tokens
    :param transportkey: the decryption key for crypted token files

    :return: the dict with tokenserial and token description
             to create the token
    '''

    parsed_tokens = {}

    kp = TKernelParams()
    kp.ParmCount = 19
    kp.ITimeWindow = 100
    kp.STimeWindow = 24
    kp.DiagLevel = 0
    kp.GMTAdjust = 0
    kp.CheckChallenge = 0
    # -- --- --
    # This is the failcounter! The failcounter needs to be reset manually
    # When we set the failcounter=0 then we can rule the failcounter in LinOTP
    # -- -- --
    kp.IThreshold = 0
    kp.SThreshold = 1
    kp.ChkInactDays = 0
    kp.DeriveVector = 0
    kp.SyncWindow = 2
    kp.OnLineSG = 1
    kp.EventWindow = 100
    kp.HSMSlotId = 0

    # the vasco dpx parser requires an physical input file :-(
    with NamedTemporaryFile("w", delete=False) as dpxfile:
        dpxfile.write(fileString)
    filename = dpxfile.name

    # we have to use a try - finally to guarante, that the tempfile is
    # removed on completion
    try:
        (res, filehandle, _appl_count,
         appl_names, tokens) = vasco_dpxinit(filename=filename,
                                             transportkey=transportkey)

        if res != 0:

            # handle some known dedicated errors
            ret = res
            if res in [-15, -14]:
                ret = "Error initkey"

            err = "Failed to initialize the import process! %r" % ret
            log.error("[parseVASCOdata] %r", err)
            raise Exception(err)

        log.debug("found %s tokens.", tokens)

        (res, _vec, _vec_len) = vasco_getstatic_vector(filehandle, kp)
        log.debug("getstaticvector: %d", res)

        # start getting tokens
        res = 100
        data = TDigipassBlob()

        while res == 100:
            (res, serial, typ, auth, data) = vasco_gettoken(filehandle,
                                                            kp, appl_names)

            if res == 107:
                log.debug("SUCCESSfully reached the end of the dpx file")

            if res == 100:
                (pres, data) = vasco_settokenproperty(data, kp, 6, 2)
                if pres != 0:
                    log.error("Failed to set token properties %r", pres)
                    log.debug("Failing token properties %r", kp)
                    continue

                # TODO: Each token could have another OTP-length.
                # At the moment we take this as parameter
                otplen = arg_otplen
                if 'APPL' in serial:
                    idx = serial.index('APPL')
                elif 'DEFAULT' in serial:
                    idx = serial.index('DEFAULT')
                else:
                    idx = len(serial)

                lin_serial = serial[:idx]

                if auth[:2] in ["RO"]:
                    # yes, we support DPGO6 and we support the
                    # response only (no signature and challenge)
                    otpkey = vasco_compress(data)

                    token_init = {'type': "vasco",
                                  'hmac_key': otpkey,
                                  "description": typ.strip("\0"),
                                  'otplen': otplen,
                                  'tokeninfo': {
                                      # "data_Serial" : data.Serial,
                                      # "data_AppName" : data.AppName,
                                      # "data_DPFlags" : data.DPFlags
                                      "application": serial.strip("\0"),
                                      "type": typ.strip("\0"),
                                      "auth": auth.strip("\0"), }, }

                    parsed_tokens["vc" + lin_serial] = token_init
                else:
                    log.warning("The tokentype %s, auth %s is not tested! "
                                "The Token %s is not imported!",
                                typ, auth, lin_serial)

        res = vasco_dpxclose(filehandle)

    finally:
        os.remove(filename)

    return parsed_tokens


@check_vasco
def vasco_otp_check(otpkey, otp):
    """
    check the otp value

    :param data: the vasco_token_data, stored in LinOTP database as otpkey
    :param otp: the otp value
    :return: tuple of (success and new_vasco_token_data)
    """
    kp = TKernelParams()
    kp.ParmCount = 19
    kp.ITimeWindow = 100
    kp.STimeWindow = 24
    kp.DiagLevel = 0
    kp.GMTAdjust = 0
    kp.CheckChallenge = 0
    #
    # This is the failcounter! The failcounter needs to be reset manually
    # When we set the failcounter=0 then we can rule the failcounter in LinOTP
    #
    kp.IThreshold = 0
    kp.SThreshold = 1
    kp.ChkInactDays = 0
    kp.DeriveVector = 0
    kp.SyncWindow = 2
    kp.OnLineSG = 1
    kp.EventWindow = 100
    kp.HSMSlotId = 0

    data = vasco_decompress(otpkey)
    (res, data) = vasco_verify(data, kp, otp)
    otpkey = vasco_compress(data)

    return (res, otpkey)


@check_vasco
def test():
    tokens = parseVASCOdata("Demo_GO6.DPX")

    for token, token_data in tokens.items():
        print token
        print token_data
        data = pickle.loads(token_data['hmac_key'])
        passw = "000000"
        while passw != "X":
            print "=========== Verify Password ============"
            passw = raw_input("Enter OTP:")
            (res, data) = vasco_otp_check(data, passw)

            print res

# eof #######################################################################
