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
SSH key and can give the public SSH key via the getotp function.
This can be used to manage SSH keys and retrieve the public ssh key
to import it to authorized keys files.

The code is tested in tests/test_lib_tokens_ssh
"""

import logging
from privacyidea.lib import _
log = logging.getLogger(__name__)
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass



optional = True
required = False


##TODO: We should save a fingerprint of the SSH Key in the encrypted OTP
# field, so that we can be sure, that the public ssh key was not changed in
# the database!


class SSHkeyTokenClass(TokenClass):
    """
    The SSHKeyTokenClass provides a TokenClass that stores the public
    SSH key and can give the public SSH key via the getotp function.
    This can be used to manage SSH keys and retrieve the public ssh key
    to import it to authorized keys files.
    """
    mode = ['authenticate']
    using_pin = False

    def __init__(self, db_token):
        TokenClass.__init__(self, db_token)
        self.set_type(u"sshkey")

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
               'policy': {},
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
        if len(key_elem) != 3 or key_elem[0] != "ssh-rsa":
            raise Exception("The key must consist of 'ssh-rsa BASE64 comment'")

        key_type = key_elem[0]
        key = key_elem[1]
        key_comment = key_elem[2]
        
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
        return u"{0!s} {1!s} {2!s}".format(key_type, sshkey, key_comment)
