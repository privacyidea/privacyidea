#  2023-02-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             initial write
#  (c) 2023 Cornelius Kölbel - cornelius.koelbel@netknights.it
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
This file contains the definition of the application specific password token class
"""

import logging
from privacyidea.lib.tokens.passwordtoken import PasswordTokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib import _
from privacyidea.lib.policy import SCOPE, GROUP
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.params import get_required
from privacyidea.lib.error import ParameterError
from privacyidea.lib.serviceid import get_serviceids


TOKENINFO_KEY = "service_id"

log = logging.getLogger(__name__)


class ApplicationSpecificPasswordTokenClass(PasswordTokenClass):
    """
    This Token does use a fixed Password as the OTP value.
    In addition, the OTP PIN can be used with this token.

    This static password is tied to a certain application or service,
    making it an application specific password.
    """
    # We use an easier length of 23 for password tokens
    default_length = 23
    default_contents = 'cn'

    owned_tokeninfo_keys = frozenset({TOKENINFO_KEY})

    def __init__(self, aToken):
        PasswordTokenClass.__init__(self, aToken)
        self.set_type("applspec")

    @staticmethod
    def get_class_type():
        return "applspec"

    @staticmethod
    def get_class_prefix():
        return "ASPW"

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
        :rtype: dict or scalar
        """
        res = {'type': 'applspec',
               'title': 'Application Specific Password Token',
               'description': _('Application Specific Password: A token with a fixed password. Can be used '
                                'for certain applications or services.'),
               'init': {},
               'config': {},
               'user':  ["enroll"],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.ADMIN: {
                       PolicyAction.FORCE_SERVER_GENERATE: {'type': 'bool',
                                                      'desc': ApplicationSpecificPasswordTokenClass.desc_key_gen}
                   },
                   SCOPE.USER: {
                       PolicyAction.FORCE_SERVER_GENERATE: {'type': 'bool',
                                                      'desc': ApplicationSpecificPasswordTokenClass.desc_key_gen}
                   },
                   SCOPE.ENROLL: {
                       PolicyAction.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of application specific "
                                     "password tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       PolicyAction.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of active application specific"
                                     " password tokens assigned."),
                           'group': GROUP.TOKEN
                       }
                   }
               },
               }
        # I don't think we need to define the lost token policies here...

        if key:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log, log_entry=False)
    def update(self, param):
        """
        This method is called during the initialization process.
        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        # The service ID is checked before the parent class generates the password: the parent commits the new
        # password, and a token that already exists is not removed when the initialization fails, so a rollover
        # with an unusable service ID would leave the token with a password that was never handed out.
        service_id = self._check_service_id(get_required(param, TOKENINFO_KEY))
        PasswordTokenClass.update(self, param)
        # In addition to the initialization from the parent class, we also need to set the service_id
        self.write_tokeninfo(TOKENINFO_KEY, service_id)

    @staticmethod
    def _check_service_id(service_id) -> str:
        """
        Return the given service ID in the spelling it is defined with.

        A token only authenticates if its service ID matches the one the service sends, which is compared
        case-insensitively. The defined service IDs are therefore looked up the same way, and the name is stored as
        it is defined, so that the token carries the service ID the administrator defined and not a variation of it.

        A definition whose name matches exactly wins, because two definitions can differ in case alone on a database
        that compares case-sensitively.

        :param service_id: The service ID from the request, which is not necessarily a string: a JSON request body
            keeps the type it was sent with
        :return: The name of the matching service ID definition
        """
        service_id = str(service_id)
        defined_names = [entry.name for entry in get_serviceids()]
        if service_id in defined_names:
            return service_id
        for defined_name in defined_names:
            if defined_name.lower() == service_id.lower():
                return defined_name
        raise ParameterError(f"The service ID {service_id!r} is not defined.")

    @property
    def service_id(self):
        service_id = self.get_tokeninfo(TOKENINFO_KEY)
        return service_id

    @log_with(log)
    def use_for_authentication(self, options):
        """
        This method checks, if this token should be used for authentication.

        In this case the service_id of the token needs to match the service_id from
        the request.

        :param options: This is the option list, that basically contains the Request parameters.
        :return:
        """
        service_id = options.get(TOKENINFO_KEY)
        if not service_id:
            log.debug(f"The request has no {TOKENINFO_KEY!s}.")
            return False
        if not self.service_id:
            # A token could be missing the service_id
            log.debug(f"The token has no {TOKENINFO_KEY!s}.")
            return False
        return self.service_id.lower() == service_id.lower()
