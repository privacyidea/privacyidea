# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  Jul 18, 2014 Cornelius Kölbel
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
This file is tested in tests/test_lib_machinetokens.py
"""
from privacyidea.lib.applications import MachineApplicationBase
import logging
from privacyidea.lib.token import get_tokens
from privacyidea.lib.policy import TYPE
from privacyidea.lib.serviceid import get_serviceids
from privacyidea.lib import _
log = logging.getLogger(__name__)


class MachineApplication(MachineApplicationBase):
    """
    This is the application for SSH.

    Possible options:
        user

    """
    application_name = "ssh"
    '''as the authentication item is no sensitive information,
    we can set bulk_call to True. Thus the admin can call
    all public keys to distribute them via salt.
    FIXME: This is only true for SSH pub keys.
    If we would support OTP with SSH, this might be sensitive information!
    '''
    allow_bulk_call = True

    @staticmethod
    def get_authentication_item(token_type,
                                serial,
                                challenge=None, options=None,
                                filter_param=None):
        """
        :param token_type: the type of the token. At the moment
                           we support the tokenype "sshkey"
        :param serial:     the serial number of the token.
        :return auth_item: Return the SSH pub keys.
        """
        options = options or {}
        ret = {}
        filter_param = filter_param or {}
        user_filter = filter_param.get("user")
        if token_type.lower() == "sshkey":
            toks = get_tokens(serial=serial, active=True)
            if len(toks) == 1:
                # We return this entry, either if no user_filter is requested
                #  or if the user_filter matches the user
                if (user_filter and user_filter == options.get("user")) or \
                        not user_filter:
                    # tokenclass is a SSHkeyTokenClass
                    tokclass = toks[0]
                    # We just return the ssh public key, so that
                    # it can be included into authorized keys.
                    log.info("Using SSH key {0!s} for SSH user {1!s}".format(tokclass.token.serial,
                                                                              options.get("user")))
                    ret["sshkey"] = tokclass.get_sshkey()
                    # We return the username if the token is assigned to a
                    # user, so that this username could be used to save
                    # the ssh key accordingly
                    user_object = toks[0].user
                    if user_object:
                        uInfo = user_object.info
                        if "username" in uInfo:
                            ret["username"] = uInfo.get("username")
                else:
                    log.debug("The requested user {0!s} does not match the user "
                              "option ({0!s}) of the SSH application.".format(
                        user_filter, options.get("user")))
        else:
            log.info("Token {0!r}, type {0!r} is not supported by "
                     "SSH application module".format(serial, token_type))

        return ret

    @staticmethod
    def get_options():
        """
        returns a dictionary with a list of options
        """
        sids = [s.name for s in get_serviceids()]
        return {'user': {'type': TYPE.STRING,
                         'description': _('The username on the SSH server.')},
                'service_id': {'type': TYPE.STRING,
                               'description': _('The service ID of the SSH server. '
                                                'Several servers can have the same service ID.'),
                               'value': sids}}
