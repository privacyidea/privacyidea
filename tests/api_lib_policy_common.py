# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared mixin and constants for split test_api_lib_policy_*.py files."""

from flask import Request, g
from werkzeug.test import EnvironBuilder

from privacyidea.lib.container import (init_container, find_container_by_serial)
from privacyidea.lib.policy import (PolicyClass)
from privacyidea.lib.token import (init_token)
from privacyidea.lib.user import User

HOSTSFILE = "tests/testdata/hosts"
SSHKEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDO1rx366cmSSs/89j" \
         "/0u5aEiXa7bYArHn7zFNCBaVnDUiK9JDNkpWBj2ucbmOpDKWzH0Vl3in21E" \
         "8BaRlq9AobASG0qlEqlnwrYwlH+vcYp6td4QBoh3sOelzhyrJFug9dnfe8o7" \
         "0r3IL4HIbdQOdh1b8Ogi7aL01V/eVE9RgGfTNHUzuYRMUL3si4dtqbCsSjFZ" \
         "6dN1nnVhos9cSphPr7pQEbq8xW0uxzOGrFDY9g1NSOleA8bOjsCT9k+3X4R7" \
         "00iVGvpzWkKopcWrzXJDIa3yxylAMOM0c3uO9U3NLfRsucvcQ5Cs8S6ctM30" \
         "8cua3t5WaBOsr3RyoXs+cHIPIkXnJHg03HsnWONaGxl8VPymC9s3P0zVwm2jMFx" \
         "JD9WbBqep7Dwc5unxLOSKidKrnNflQiMyiIv+5dY5lhc0YTJdktC2Scse64ac2E" \
         "7ldjG3bJuKSIWAz8Sd1km4ZJWWIx8NlpC9AfbHcgMyFUDniV1EtFIaSQLPspIk" \
         "thzIMqPTpKblzdRZP37mPu/FpwfYG4S+F34dCmJ4BipslsVcqgCFJQHoAYAJc4N" \
         "Dq5IRDQqXH2KybHpSLATnbSY7zjVD+evJeU994yTaXTFi5hBmd0aWTC+ph79mmE" \
         "tu3dokA2YbLa7uWkAIXvX/HHauGLMTyCOpYi1BxN47c/kccxyNg" \
         "jPw== corny@schnuck"

YUBIKEY_CSR = """-----BEGIN CERTIFICATE REQUEST-----
MIICbTCCAVUCAQAwFzEVMBMGA1UEAwwMY249Y29ybmVsaXVzMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzqQ5MCVz5J3mNzuFWYPvo275g7n3SLAL1egF
QGHNxVq8ES9bTtBPuNDofwWrrSQLkNQ/YOwVtk6+jtkmq/IvfzXCpqG8UjrZiPuz
+nEguVEO+K8NFr69XbmrMNWsazy87ihKT2/UCRX3mK932zYVLh7uD9DZYK3bucQ/
xiUy+ePpULjshKDE0pz9ziWAhX46rUynQBsKWBifwl424dFE6Ua23LQoouztAvcl
eeGGjmlnUu6CIbeELcznqDlXfaMe6VBjdymr5KX/3O5MS14IK2IILXW4JmyT6/VF
6s2DWFMVRuZrQ8Ev2YhLPdX9DP9RUu1U+yctWe9MUM5xzetamQIDAQABoBEwDwYJ
KoZIhvcNAQkOMQIwADANBgkqhkiG9w0BAQsFAAOCAQEArLWY74prQRtKojwMEOsw
4efmzCwOvLoO/WXDwzrr7kgSOawQanhFzD+Z4kCwapf1ZMmobBnyWREpL4EC9PzC
YH+mgSDCI0jDj/4OSfklb31IzRhuWcCVOpV9xuiDW875WM792t09ILCpx4rayw2a
8t92zv49IcWHtJNqpo2Q8064p2fzYf1J1r4OEBKUUxEIcw2/nifIiHHTb7DqDF4+
XjcD3ygUfTVbCzPYBmLPwvt+80AxgT2Nd6E612L/fbI9clv5DsvMwnVeSvlP1wXo
5BampVY4p5CQRFLlCQa9fGWZrT+ArC9Djo0mHf32x6pEsSz0zMOlmjHrh+ChVkAs
tA==
-----END CERTIFICATE REQUEST-----"""


class PrePolicyHelperMixin:
    """Mock-request helper methods shared across PrePolicy* split test cases."""

    def mock_token_request(self, role):
        """
        Mocks a request for a user or an admin.
        An HOTP token is created for user 'root' in realm 'realm3' and resolver 'reso3' and an additional
        token realm 'realm1'. The serial is included in the request.

        :param role: User role for whom to create the request 'admin' or 'user'
        :return: Request object and token object
        """
        # create request and token
        req, token = self.mock_token_request_no_user(role)

        # add user to the token
        user = User(login="root", realm=self.realm3, resolver=self.resolvername3)
        token.add_user(user)
        token.set_realms([self.realm1], add=True)
        req.User = user

        return req, token

    def mock_token_request_no_user(self, role):
        """
        Mocks a request for a user or an admin.
        An HOTP token is created without any user or realm. The serial is included in the request.

        :param role: User role for whom to create the request 'admin' or 'user'
        :return: Request object and token object
        """
        if role == "admin":
            g.logged_in_user = {"username": "admin",
                                "role": "admin"}
        elif role == "user":
            g.logged_in_user = {"username": "root",
                                "realm": self.realm3,
                                "resolver": self.resolvername3,
                                "role": "user"}
        token = init_token({"type": "hotp", "genkey": True})
        token_serial = token.get_serial()
        builder = EnvironBuilder(method='POST', data={'serial': token_serial}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"serial": token_serial}
        req.User = User()
        g.policy_object = PolicyClass()
        return req, token

    def mock_container_request(self, role, container_type="generic"):
        """
        Mocks a request for a user or an admin.
        A container is created for user 'root' in realm 'realm3' and resolver 'reso3' and an additional
        container realm 'realm1'. The container serial is included in the request.

        :param role: User role for whom to create the request 'admin' or 'user'
        :param container_type: Type of the container to create
        :return: Request object and container object
        """
        # Create request object and container
        req, container = self.mock_container_request_no_user(role, container_type)

        # add user root (realm3) and realm 1 to the container
        root = User(login="root", realm=self.realm3, resolver=self.resolvername3)
        container.add_user(root)
        container.set_realms([self.realm1], add=True)
        req.User = root

        return req, container

    def mock_container_request_no_user(self, role, container_type="generic"):
        """
        Mocks a request for a user or an admin.
        A container is created. The container serial is included in the request.

        :param role: User role for whom to create the request 'admin' or 'user'
        :param container_type: Type of the container to create
        :return: Request object and container object
        """
        # create container for user hans (realm3) and realm 1
        container_serial = init_container({"type": container_type})["container_serial"]
        container = find_container_by_serial(container_serial)
        builder = EnvironBuilder(method='POST', data={'container_serial': container_serial}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"container_serial": container_serial}
        req.User = User()
        if role == "admin":
            g.logged_in_user = {"username": "admin",
                                "role": "admin",
                                "realm": ""}
        elif role == "user":
            g.logged_in_user = {"username": "root",
                                "realm": self.realm3,
                                "resolver": self.resolvername3,
                                "role": "user"}
            req.User = User(login="root", realm=self.realm3, resolver=self.resolvername3)
        g.policy_object = PolicyClass()

        return req, container

    def mock_request_user_params(self, role):
        """
        Mocks a request for a user or an admin with a user passed in the parameters.

        :param role: User role for whom to create the request 'admin' or 'user'
        :return: Request object
        """
        if role == "admin":
            g.logged_in_user = {"username": "admin",
                                "role": "admin"}
        elif role == "user":
            g.logged_in_user = {"username": "cornelius",
                                "realm": self.realm4,
                                "resolver": self.resolvername1,
                                "role": "user"}

        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {'user': 'cornelius', 'realm': self.realm4}
        req.User = User("cornelius", self.realm4)
        g.policy_object = PolicyClass()

        return req

    def mock_client_container_request(self):
        """
        Mocks a request for a client.
        A smartphone container is created for user 'root' in realm 'realm3' and resolver 'reso3' and an additional
        container realm 'realm1'. The container serial is included in the request.

        :return: Request object and container object
        """
        # Create request object and container
        req, container = self.mock_client_container_request_no_user()

        # add user hans (realm3) and realm 1 to the container
        hans = User(login="root", realm=self.realm3, resolver=self.resolvername3)
        container.add_user(hans)
        container.set_realms([self.realm1], add=True)
        req.User = hans

        return req, container

    @classmethod
    def mock_client_container_request_no_user(cls):
        """
        Mocks a request for a client.
        A smartphone container is created. The container serial is included in the request.

        :return: Request object and container object
        """
        # create container for user hans (realm3) and realm 1
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        container = find_container_by_serial(container_serial)
        builder = EnvironBuilder(method='POST', data={'container_serial': container_serial}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"container_serial": container_serial}
        req.User = User()
        g.policy_object = PolicyClass()

        return req, container
