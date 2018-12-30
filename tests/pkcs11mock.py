# -*- coding: utf-8 -*-
#
#  2018-05-16 Friedrich Weber <friedrich.weber@netknights.it>
#             Implement PKCS11 mock
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNE7SS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Mock module for testing the handling of hardware security modules
"""
import sys
import mock

try:
    import PyKCS11
except ImportError:
    # PyKCS11 not installed, let's use our simple mock module
    class MockPyKCS11Error(Exception):
        def __init__(self, code):
            self.code = code


    MOCK_CONSTANTS = ['CKA_CLASS', 'CKO_SECRET_KEY', 'CKA_LABEL', 'CKR_SLOT_ID_INVALID', 'CKR_DEVICE_ERROR']


    def _setup_module_mock():
        module = mock.MagicMock()
        module.PyKCS11Error = MockPyKCS11Error
        module.CK_SLOT_INFO.side_effect = lambda: mock.MagicMock()
        for name in MOCK_CONSTANTS:
            setattr(module, name, object())
        return module


    PyKCS11 = _setup_module_mock()
    sys.modules['PyKCS11'] = PyKCS11

from PyKCS11 import PyKCS11Error
from contextlib import contextmanager

SLOT_IDS = [1, 2, 3]


def fake_encrypt(data):
    """
    simple fake encrypt function for testing: just add 1 to each byte.
    :return: a list of integers
    """
    return [(c + 1) % 256 for c in data]


def fake_decrypt(data):
    """
    simple fake decrypt function for testing: substract 1 from each byte
    :return: a list of integers
    """
    return [(c - 1) % 256 for c in data]


class PKCS11Mock(object):
    """
    Mock helper to simulate a HSM. Usage::

        with PKCS11Mock():
            hsm = AESHardwareSecurityModule(...)

            crypted = hsm.encrypt_password(...)

    Simulation of encryption and decryption is realized using
    ``fake_encrypt`` and ``fake_decrypt``. Generated random
    values are just "\x00\x01\x02...".
    """
    def __init__(self, default_mocks=True):
        self.mock = mock.MagicMock()
        self.lowlevel_mock = mock.MagicMock()
        self.session_mock = mock.MagicMock()
        if default_mocks:
            self.setup_default_mocks()

    def _mock_getSlotInfo(self, slot):
        if slot not in SLOT_IDS:
            raise PyKCS11Error(PyKCS11.CKR_SLOT_ID_INVALID)
        slot_info = PyKCS11.CK_SLOT_INFO()
        slot_info.slotDescription = "slot {!s} description".format(slot)
        return slot_info

    @contextmanager
    def simulate_failure(self, mock_function, count, error=PyKCS11.CKR_DEVICE_ERROR):
        """
        Context manager to simulate external HSM failure.
        Given a mock function, replace its side effect with a new side effect which
        fails **count** times, raising a PyKCS11Error with the given error ID *error*
        each time. Subsequent calls are forwarded to the original side effect.
        When the context is left, the old side effect is restored

        :param mock_function: Function for which failure should be simulated
        :param count: number of failures
        :param error: PyKCS11 error code
        """
        old_side_effect = mock_function.side_effect

        # we need to modify the number of remaining failures inside our new
        # side effect function. But modifying an outer variable is not easily possible
        # in Python2, so we use a class to hold the value.
        # In Python 3, we could use the ``nonlocal`` keyword

        class store:
            failures = count

        def _new_side_effect(*args, **kwargs):
            if store.failures > 0:
                store.failures -= 1
                raise PyKCS11Error(error)
            return old_side_effect(*args, **kwargs)

        try:
            mock_function.side_effect = _new_side_effect
            yield
        finally:
            mock_function.side_effect = old_side_effect

    @contextmanager
    def simulate_disconnect(self, count):
        """
        Context manager to simulate that the HSM has vanished.
        This is just a shortcut for calling ``simulate_failure`` on ``generateRandom``, ``encrypt``,
        ``decrypt`` and ``openSession``.
        """
        with self.simulate_failure(self.session_mock.generateRandom, count), \
            self.simulate_failure(self.session_mock.encrypt, count), \
            self.simulate_failure(self.session_mock.decrypt, count), \
            self.simulate_failure(self.mock.openSession, count):
            yield

    def _mock_openSession(self, slot):
        if slot not in SLOT_IDS:
            raise PyKCS11Error(PyKCS11.CKR_SLOT_ID_INVALID)
        return self.session_mock

    def _mock_encrypt(self, key, data, mechanism):
        return fake_encrypt(bytearray(data))

    def _mock_decrypt(self, key, data, mechanism):
        return fake_decrypt(bytearray(data))

    def _mock_generateRandom(self, length):
        return list(range(length))

    def setup_default_mocks(self):
        """
        Configure a number of mocks.

        This will simulate a HSM with three slots.
        All ``openSession`` calls will return ``self.session_mock``.
        On the session mock, ``encrypt``, ``decrypt`` and ``generateRandom``
        are replaced with mock functions.
        """
        self.mock.getSlotList.return_value = SLOT_IDS
        self.mock.getSlotInfo.side_effect = self._mock_getSlotInfo
        self.mock.openSession.side_effect = self._mock_openSession

        self.session_mock.encrypt.side_effect = self._mock_encrypt
        self.session_mock.decrypt.side_effect = self._mock_decrypt
        self.session_mock.generateRandom.side_effect = self._mock_generateRandom

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def start(self):
        self._patcher = mock.patch('PyKCS11.PyKCS11Lib', return_value=self.mock)
        self._patcher.start()
        self.mock.lib = self.lowlevel_mock

    def stop(self):
        self._patcher.stop()