# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
The local CA connector names the CSR and certificate files itself and passes them to openssl as separate
arguments, so the subject of a request can neither choose a path outside the CSR/certificate directory, nor
overwrite the files of the CA itself, nor add options to the openssl command line.
"""
import os
import shutil
import tempfile
from unittest import mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from privacyidea.lib.caconnectors import localca
from privacyidea.lib.caconnectors.localca import LocalCAConnector
from privacyidea.lib.caconnector import save_caconnector, delete_caconnector
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
from .base import MyApiTestCase, MyTestCase
from .conftest import prepare_ca_directory

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_csr(common_name: str) -> str:
    builder = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
    return builder.sign(_KEY, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode()


def files_below(directory: str) -> set[str]:
    found = set()
    for base, _dirs, names in os.walk(directory):
        for name in names:
            found.add(os.path.join(base, name))
    return found


class LocalCASubjectTestCase(MyTestCase):
    """The directory layout `pi-manage ca create` configures: CSRs and certificates go to the CA directory."""

    def setUp(self) -> None:
        self.root = tempfile.mkdtemp()
        self.ca_dir = prepare_ca_directory(os.path.join(self.root, "ca"))
        self.connector = LocalCAConnector("localCA", {"cakey": "cakey.pem", "cacert": "cacert.pem",
                                                      "openssl.cnf": "openssl.cnf", "WorkingDir": self.ca_dir,
                                                      "CSRDir": "", "CertificateDir": ""})

    def tearDown(self) -> None:
        shutil.rmtree(self.root)
        super().tearDown()

    def sign(self, request: str, options: dict | None = None) -> list[list[str]]:
        """Sign the request, check that a certificate came back and return the argv lists given to Popen."""
        argv_lists = []
        real_popen = localca.Popen

        def recording_popen(args, **kwargs):
            argv_lists.append(list(args))
            return real_popen(args, **kwargs)

        with mock.patch.object(localca, "Popen", side_effect=recording_popen):
            return_value, certificate = self.connector.sign_request(request, options)
        self.assertEqual(0, return_value)
        self.assertIsInstance(x509.load_pem_x509_certificate(certificate.encode()), x509.Certificate)
        return argv_lists

    def test_01_subject_stays_inside_the_ca_directory(self):
        self.sign(make_csr("../outside"))
        self.assertEqual(set(), files_below(self.root) - files_below(self.ca_dir))

    def test_02_subject_does_not_overwrite_the_ca_key(self):
        with open(os.path.join(self.ca_dir, "cakey.pem")) as key_file:
            ca_key_before = key_file.read()
        self.sign(make_csr("cakey"))
        with open(os.path.join(self.ca_dir, "cakey.pem")) as key_file:
            ca_key_after = key_file.read()
        self.assertEqual(ca_key_before, ca_key_after)

    def test_03_spkac_subject_does_not_overwrite_the_ca_database(self):
        try:
            from .test_lib_caconnector import SPKAC
        except ImportError:
            self.skipTest("this branch has no SPKAC support")
        with open(os.path.join(self.ca_dir, "index.txt"), "w") as index_file:
            index_file.write("V\t300101000000Z\t\t0FFF\tunknown\t/CN=existing\n")
        self.sign(SPKAC.replace("CN=Steve Test", "CN=index"), {"spkac": 1})
        with open(os.path.join(self.ca_dir, "index.txt")) as index_file:
            index_after = index_file.read()
        self.assertTrue(index_after.startswith("V\t300101000000Z"), index_after[:80])

    def test_04_subject_adds_no_openssl_option(self):
        argv_lists = self.sign(make_csr("a\t-config\tb"))
        for argv in argv_lists:
            self.assertEqual(1, argv.count("-config"), argv)

    def test_05_apostrophe_in_subject(self):
        self.sign(make_csr("O'Brien"))


class LocalCAUserEnrollmentTestCase(MyApiTestCase):
    """A user who may enroll a certificate token reaches sign_request with a subject of their choice."""

    def setUp(self) -> None:
        self.root = tempfile.mkdtemp()
        self.ca_dir = prepare_ca_directory(os.path.join(self.root, "ca"))
        save_caconnector({"caconnector": "localCA", "type": "local", "cakey": "cakey.pem", "cacert": "cacert.pem",
                          "openssl.cnf": "openssl.cnf", "WorkingDir": self.ca_dir, "CSRDir": "",
                          "CertificateDir": ""})
        self.setUp_user_realms()
        set_policy("user_enroll_cert", scope=SCOPE.USER, action="enrollCERTIFICATE")
        self.authenticate_selfservice_user()

    def tearDown(self) -> None:
        delete_policy("user_enroll_cert")
        delete_caconnector("localCA")
        shutil.rmtree(self.root)
        super().tearDown()

    def test_01_user_request_keeps_the_ca_key(self):
        with open(os.path.join(self.ca_dir, "cakey.pem")) as key_file:
            ca_key_before = key_file.read()
        with self.app.test_request_context("/token/init", method="POST",
                                           data={"type": "certificate", "ca": "localCA",
                                                 "request": make_csr("cakey")},
                                           headers={"Authorization": self.at_user}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        with open(os.path.join(self.ca_dir, "cakey.pem")) as key_file:
            ca_key_after = key_file.read()
        self.assertEqual(ca_key_before, ca_key_after)
