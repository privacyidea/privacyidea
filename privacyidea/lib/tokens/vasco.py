# -*- coding: utf-8 -*-
#
# 2018-01-15 friedrich.weber@netknights.it
#            Remove unused routines, redesign serialization step,
#            adapt to privacyIDEA, refactoring
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
""" VASCO library binding """

import logging

# from ctypes import *
from ctypes import CDLL, create_string_buffer
from ctypes import Structure

from ctypes import byref
from ctypes import c_ulong
from ctypes import c_char
from ctypes import c_byte

from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.error import ParameterError

__all__ = ["vasco_otp_check"]


log = logging.getLogger(__name__)

vasco_dll = None

try:
    vasco_library_path = get_app_config_value("PI_VASCO_LIBRARY")
    if vasco_library_path is not None: # pragma: no cover
        log.info("Loading VASCO library from {!s} ...".format(vasco_library_path))
        vasco_dll = CDLL(vasco_library_path)
    else:
        log.debug("PI_VASCO_LIBRARY option is not set, functionality disabled")
except Exception as exx:
    log.warning("Could not load VASCO library: {!r}".format(exx))


def check_vasco(fn):
    """
    This is a decorator:
    checks if vasco dll is defined,
    it then runs the function otherwise raises RuntimeError

    :param fn: function - the to be called function
    :return: return the function call result
    """
    def new(*args, **kw):
        if not vasco_dll:
            raise RuntimeError("No VASCO library available")
        else:
            return fn(*args, **kw)
    return new


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


def vasco_verify(data, params, password, challenge=b"\0" * 16):
    # Construct actual buffers in case the library writes to ``password`` or ``challenge``
    password_buffer = create_string_buffer(password)
    challenge_buffer = create_string_buffer(challenge)
    res = vasco_dll.AAL2VerifyPassword(byref(data),
                                       byref(params),
                                       password_buffer,
                                       challenge_buffer)

    return res, data


def vasco_serialize(datablob):
    """
    Convert the given ``TDigipassBlob`` object to a bytestring and return it

    :param datablob: Digipass blob
    :return: bytestring
    """
    tokendata = memoryview(datablob).tobytes()
    if len(tokendata) != 248:  # pragma: no cover
        raise ParameterError("Datablob has incorrect size")
    return tokendata


def vasco_deserialize(tokendata):
    """
    Convert the given bytestring to a ``TDigipassBlob`` object and return it

    :param tokendata: A string of 248 bytes
    :return: The Vasco data blob
    """
    if len(tokendata) != 248:
        raise ParameterError("Data blob has incorrect size")
    return TDigipassBlob.from_buffer_copy(tokendata)


@check_vasco
def vasco_otp_check(otpkey, otp):
    """
    check the otp value

    :param data: the vasco_token_data, stored in LinOTP database as otpkey
    :param otp: the otp value
    :type otp: bytes
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

    data = vasco_deserialize(otpkey)
    (res, data) = vasco_verify(data, kp, otp)
    otpkey = vasco_serialize(data)

    return res, otpkey
