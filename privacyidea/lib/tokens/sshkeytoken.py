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
__doc__ = """The SSHKeyTokenClass provides a TokenClass that stores the public
SSH key. This can be used to manage SSH keys and retrieve the public ssh key
to import it to authorized keys files.

The code is tested in tests/test_lib_tokens_ssh
"""

import hashlib
import json
import logging

from privacyidea.config import ConfigKey
from privacyidea.lib import _
from privacyidea.lib.crypto import safe_compare, decryptPassword, FAILED_TO_DECRYPT_PASSWORD
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.error import TokenAdminError
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.log import log_with
from privacyidea.lib.params import get_required
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, GROUP
from privacyidea.lib.tokenclass import TokenClass, AuthenticationMode
from privacyidea.lib.tokenrolloutstate import RolloutState
from privacyidea.lib.utils import to_list, to_unicode

log = logging.getLogger(__name__)

#: SSH key types which are always allowed to be enrolled.
DEFAULT_ALLOWED_SSH_KEY_TYPES = ["ssh-rsa", "ssh-ed25519", "ecdsa-sha2-nistp256",
                                 "sk-ecdsa-sha2-nistp256@openssh.com", "sk-ssh-ed25519@openssh.com"]

#: Token info keys whose value is part of the SSH key integrity checksum.
#: Whenever one of these is written or deleted, the checksum must be recomputed.
SSH_KEY_INFO_KEYS = frozenset(["ssh_key", "ssh_type", "ssh_comment"])


def compute_ssh_key_checksum(serial: str, key_type: str, key: str, comment: str) -> str:
    """
    Compute the integrity checksum of an SSH key token.

    The checksum is stored in the encrypted OTP key field of the token.
    Since a database administrator can neither create the encrypted value of
    a chosen checksum nor copy the value from another token (the serial is
    part of the checksum), any manipulation of the SSH key data in the
    database can be detected.

    :param serial: The serial of the token
    :param key_type: The SSH key type, e.g. "ssh-rsa"
    :param key: The decrypted base64 encoded public key blob
    :param comment: The SSH key comment
    :return: hexlified SHA256 checksum
    """
    data = json.dumps([serial or "", key_type or "", key or "", comment or ""])
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def get_allowed_ssh_key_types() -> list[str]:
    """
    Return the list of SSH key types which may be enrolled.

    This is the list of the default key types extended by the key types
    configured in the config file with ``PI_ALLOWED_SSH_KEY_TYPES``. As the
    ``pi.cfg`` is a python file, the config value must be a list, e.g.
    ``PI_ALLOWED_SSH_KEY_TYPES = ["ssh-dss", "ecdsa-sha2-nistp521"]``.

    :return: list of allowed SSH key types
    """
    extra_key_types = get_app_config_value(ConfigKey.ALLOWED_SSH_KEY_TYPES, [])

    allowed_key_types = list(DEFAULT_ALLOWED_SSH_KEY_TYPES)
    for key_type in to_list(extra_key_types):
        key_type = str(key_type).strip()
        if key_type and key_type not in allowed_key_types:
            allowed_key_types.append(key_type)
    return allowed_key_types


class SSHkeyTokenClass(TokenClass):
    """
    The SSHKeyTokenClass provides a TokenClass that stores the public
    SSH key. This can be used to manage SSH keys and retrieve the public ssh key
    to import it to authorized keys files.
    """
    mode = [AuthenticationMode.AUTHENTICATE]
    using_pin = False

    owned_tokeninfo_keys = SSH_KEY_INFO_KEYS

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
                       PolicyAction.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of SSH keys assigned."),
                           'group': GROUP.TOKEN
                       },
                       PolicyAction.MAXACTIVETOKENUSER: {
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

        key_elem = get_required(param, "sshkey").split(" ", 2)
        allowed_key_types = get_allowed_ssh_key_types()
        if key_elem[0] not in allowed_key_types:
            self.token.rollout_state = RolloutState.BROKEN
            self.token.save()
            raise TokenAdminError(f"The keytype you specified is not supported. "
                                  f"Allowed key types are: {', '.join(allowed_key_types)}")

        if len(key_elem) < 2:
            self.token.rollout_state = RolloutState.BROKEN
            self.token.save()
            raise TokenAdminError("Missing key.")

        key_type = key_elem[0]
        key = key_elem[1]
        key_comment = key_elem[2] if len(key_elem) > 2 else ""

        self.write_tokeninfo("ssh_key", key, value_type="password")
        self.write_tokeninfo("ssh_type", key_type)
        self.write_tokeninfo("ssh_comment", key_comment)

        # call the parents function
        TokenClass.update(self, param)

        # Store an integrity checksum of the SSH key data in the encrypted
        # OTP key field, so that a manipulation of the database entries can
        # be detected in get_sshkey().
        self._update_integrity_checksum()

    def import_token(self, token_information: dict):
        """
        Import a given SSH key token and store the integrity checksum of the
        imported SSH key data in the encrypted OTP key field.
        """
        TokenClass.import_token(self, token_information)
        self._update_integrity_checksum()

    @check_token_locked
    def write_tokeninfo(self, key: str, value: str, value_type: str = None,
                        commit_db_session: bool = True) -> None:
        """
        Add a token info entry and keep the SSH key integrity checksum in sync.

        Overriding the writer makes the token class the single enforcement
        point for the checksum: every caller that changes the SSH key data
        (``update()``, token import, ...) goes through here, so the checksum
        can no longer be desynced by writing directly to the token info.

        The value type of the public key is enforced here as well, so the key
        stays encrypted no matter which caller writes it.
        """
        if key == "ssh_key":
            value_type = "password"
        super().write_tokeninfo(key, value, value_type=value_type, commit_db_session=commit_db_session)
        if key in SSH_KEY_INFO_KEYS:
            self._update_integrity_checksum()

    def remove_tokeninfo(self, key: str = None) -> None:
        """
        Delete a token info entry and keep the SSH key integrity checksum in
        sync when one of the SSH key relevant entries (or all entries) is
        removed.
        """
        super().remove_tokeninfo(key)
        if key is None or key in SSH_KEY_INFO_KEYS:
            self._update_integrity_checksum()

    def _update_integrity_checksum(self):
        """
        Recompute the SSH key integrity checksum from the current token info
        and store it in the encrypted OTP key field. This is the single point
        that keeps the checksum in sync with the ssh_key/ssh_type/ssh_comment
        token info, regardless of which caller modified them.

        A token without a public key is left untouched: a checksum over empty
        data would let such a token pass its own integrity check in
        ``get_sshkey()``, while an absent or stale checksum makes it fail
        closed.
        """
        key_type, sshkey, key_comment = self._get_ssh_key_parts()
        if not sshkey:
            log.info(f"Token {self.token.serial!s} has no SSH key, not storing an integrity checksum.")
            return
        self.token.set_otpkey(compute_ssh_key_checksum(self.token.serial, key_type, sshkey, key_comment))
        self.token.save()

    def _get_ssh_key_parts(self) -> tuple[str, str, str]:
        """
        Return the SSH key parts (type, decrypted public key, comment) of the
        token. The whole token info is fetched only once and the encrypted
        public key is decrypted directly from it.

        :return: (key_type, key, comment)
        """
        ti = self.get_tokeninfo()
        key_type = ti.get("ssh_type") or ""
        key_comment = ti.get("ssh_comment") or ""
        sshkey = ti.get("ssh_key") or ""
        if ti.get("ssh_key.type") == "password":
            sshkey = decryptPassword(sshkey)
            # decryptPassword() returns a sentinel instead of raising. If we
            # returned it as the key, a checksum could be stored over the
            # sentinel and get_sshkey() would later hand it out as the public
            # key. Treat a failed decryption as an integrity failure.
            if sshkey == FAILED_TO_DECRYPT_PASSWORD:
                log.error(f"Could not decrypt the SSH key of token {self.token.serial!s}. "
                          "The database entries might have been manipulated!")
                raise TokenAdminError(f"Could not decrypt the SSH key of token {self.token.serial!s}.")
        return key_type, sshkey, key_comment

    def _get_stored_checksum(self) -> str:
        """
        Return the integrity checksum stored in the encrypted OTP key field.

        Two failure modes are distinguished so that ``get_sshkey()`` can report
        them differently:

        * The OTP key material (``key_enc``/``key_iv``) is completely unset.
          This is the case for tokens that predate the integrity checksum and
          were never migrated. An empty string is returned so the caller can
          treat it as a missing checksum and hint at running the migration.
        * The OTP key material is present but cannot be read (malformed hex,
          wrong length, undecryptable, ...), e.g. because the columns were
          manipulated or corrupted. Rerunning the migration would not fix
          this, so a ``TokenAdminError`` about a corrupted token is raised
          directly instead of the misleading "run the migration" message.

        :return: the stored checksum, or an empty string if the token was
            never migrated (``key_enc``/``key_iv`` unset)
        :raises TokenAdminError: if the OTP key material is present but
            unreadable (the token may be corrupted)
        """
        if not self.token.key_enc or not self.token.key_iv:
            # No OTP key material at all: the token was never migrated.
            return ""
        try:
            return to_unicode(self.token.get_otpkey().getKey())
        except Exception as exx:
            log.error(f"Could not read the SSH key integrity checksum of token "
                      f"{self.token.serial!s}: {exx!r}. The token may be corrupted.")
            raise TokenAdminError(f"The SSH key integrity checksum of token "
                                  f"{self.token.serial!s} is unreadable. The token may be corrupted.")

    @log_with(log)
    def get_sshkey(self):
        """
        returns the public SSH key

        Before returning the key, the integrity checksum stored in the
        encrypted OTP key field is verified. If the SSH key data in the
        database was manipulated or the checksum is missing, a
        TokenAdminError is raised.

        :return: SSH pub key
        :rtype: string
        """
        key_type, sshkey, key_comment = self._get_ssh_key_parts()
        # Verify the integrity checksum
        stored_checksum = self._get_stored_checksum()
        if not stored_checksum:
            log.error(f"Token {self.token.serial!s} is missing the SSH key integrity checksum. "
                      "Please run the database migration to add the checksum to existing tokens.")
            raise TokenAdminError(f"Missing SSH key integrity checksum for token {self.token.serial!s}.")
        expected_checksum = compute_ssh_key_checksum(self.token.serial, key_type, sshkey, key_comment)
        if not safe_compare(stored_checksum, expected_checksum):
            log.error(f"Integrity check of the SSH key of token {self.token.serial!s} failed. "
                      "The database entries might have been manipulated!")
            raise TokenAdminError(f"The SSH key of token {self.token.serial!s} failed the integrity check.")
        r = f"{key_type!s} {sshkey!s}"
        if key_comment:
            r += " " + key_comment
        return r
