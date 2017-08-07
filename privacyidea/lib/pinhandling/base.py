# -*- coding: utf-8 -*-
#
#  2015-06-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#
# License:  AGPLv3
# (c) 2015. Cornelius Kölbel
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
#
__doc__ = """This module provides the PIN Handling base class.
In case of enrolling a token, a PIN Handling class can be used to
send the PIN via Email, call an external program or print a letter.

This module is not tested explicitly.
It is tested in conjunction with the policy decorator init_random_pin in
tests/test_api_lib_policy.py
"""
import logging
log = logging.getLogger(__name__)


class PinHandler(object):
    """
    A PinHandler Class is responsible for handling the OTP PIN during
    enrollment.

    It receives the necessary data like
      * the PIN
      * the serial number of the token
      * the username
      * all other user data:

        *  given name, surname
        *  email address
        *  telephone
        *  mobile (if the module would deliver via SMS)
      * the administrator name (who enrolled the token)
    """
    def __init__(self, options=None):
        pass

    def send(self, pin, serial, user, tokentype=None, logged_in_user=None,
             userdata=None, options=None):
        """

        :param pin: The PIN in cleartext
        :param user: the owner of the token
        :type user: user object
        :param tokentype: the type of the token
        :type tokentype: basestring
        :param logged_in_user: The logged in user, who enrolled the token
        :type logged_in_user: dict
        :param userdata: Handler-specific user data like email, mobile...
        :type userdata: dict
        :param options: Handler-specific additional options
        :type options: dict
        :return: True in case of success
        :rtype: bool
        """
        # The most simple way of handling a random PIN! ;-)
        log.info("handling pin {0!r} for token {1!s} of user {2!r}".format(pin, serial,
                                                              user))
        log.info("The token was enrolled by {0!r}@{1!s}".format(logged_in_user.get("username"), logged_in_user.get("realm")))
        return True
