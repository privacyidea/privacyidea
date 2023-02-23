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
__doc__="""The SSHKeyTokenClass provides a TokenClass that stores the public
SSH key. This can be used to manage SSH keys and retrieve the public ssh key
to import it to authorized keys files.

The code is tested in tests/test_lib_tokens_ssh
"""

import logging
from privacyidea.lib import _
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.error import TokenAdminError
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass, ROLLOUTSTATE, AUTHENTICATIONMODE
from privacyidea.lib.policy import SCOPE, ACTION, GROUP

log = logging.getLogger(__name__)


optional = True
required = False


##TODO: We should save a fingerprint of the SSH Key in the encrypted OTP
# field, so that we can be sure, that the public ssh key was not changed in
# the database!


class SSHkeyTokenClass(TokenClass):
    """
    The SSHKeyTokenClass provides a TokenClass that stores the public
    SSH key. This can be used to manage SSH keys and retrieve the public ssh key
    to import it to authorized keys files.
    """
    mode = [AUTHENTICATIONMODE.AUTHENTICATE]
    using_pin = False

    def __init__(self, db_token):
        TokenClass.__init__(self, db_token)
        self.set_type("sshkey")

    @staticmethod
    def get_class_type():
        return "sshkey"

    @staticmethod
    def get_class_prefix():
        return "SSHK"

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
        """
        returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dictionary
        """
        res = {'type': 'sshkey',
               'title': 'SSHkey Token',
               'description': _('SSH Public Key: The public SSH key.'),
               'config': {},
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of SSH keys assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _(
                               "The user may only have this maximum number of active SSH keys assigned."),
                           'group': GROUP.TOKEN
                       }
                   }
               },
               }
        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res

        return ret

    def update(self, param):
        """
        The key holds the public ssh key and this is required
        
        The key probably is of the form "ssh-rsa BASE64 comment"
        """
        # We need to save the token, so that we can later add the tokeninfo
        # Otherwise we might not have created the DB entry, yet and we would
        # be missing the token.id
        self.token.save()

        getParam(param, "sshkey", required)

        key_elem = param.get("sshkey").split(" ", 2)
        if key_elem[0] not in ["ssh-rsa", "ssh-ed25519", "ecdsa-sha2-nistp256",
                               "sk-ecdsa-sha2-nistp256@openssh.com", "sk-ssh-ed25519@openssh.com"]:
            self.token.rollout_state = ROLLOUTSTATE.BROKEN
            self.token.save()
            raise TokenAdminError("The keytype you specified is not supported.")

        if len(key_elem) < 2:
            self.token.rollout_state = ROLLOUTSTATE.BROKEN
            self.token.save()
            raise TokenAdminError("Missing key.")

        key_type = key_elem[0]
        key = key_elem[1]
        if len(key_elem) > 2:
            key_comment = key_elem[2]
        else:
            key_comment = ""
        
        # convert key to hex
        self.add_tokeninfo("ssh_key", key, value_type="password")
        self.add_tokeninfo("ssh_type", key_type)
        self.add_tokeninfo("ssh_comment", key_comment)

        # call the parents function
        TokenClass.update(self, param)
        
    @log_with(log)
    def get_sshkey(self):
        """
        returns the public SSH key
        
        :return: SSH pub key
        :rtype: string
        """
        ti = self.get_tokeninfo()
        key_type = ti.get("ssh_type")
        key_comment = ti.get("ssh_comment")
        # get the ssh key directly, otherwise it will not be decrypted
        sshkey = self.get_tokeninfo("ssh_key")
        r = "{0!s} {1!s}".format(key_type, sshkey)
        if key_comment:
            r += " " + key_comment
        return r
