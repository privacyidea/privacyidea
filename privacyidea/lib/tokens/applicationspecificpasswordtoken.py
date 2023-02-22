# -*- coding: utf-8 -*-
#
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
from privacyidea.lib.policy import SCOPE, ACTION, GROUP
from privacyidea.api.lib.utils import getParam


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
                   SCOPE.ENROLL: {
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of application specific "
                                     "password tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
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
        PasswordTokenClass.update(self, param)
        # In addition to the initialization from the parent class, we also need to set the service_id
        service_id = getParam(param, TOKENINFO_KEY, optional=False)
        self.add_tokeninfo(TOKENINFO_KEY, service_id)

    @property
    def service_id(self):
        r = self.get_tokeninfo()
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
            log.debug("The request has no {0!s}.".format(TOKENINFO_KEY))
            return False
        if not self.service_id:
            # A token could be missing the service_id
            log.debug("The token has no {0!s}.".format(TOKENINFO_KEY))
            return False
        return self.service_id.lower() == service_id.lower()
