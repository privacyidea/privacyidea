# -*- coding: utf-8 -*-
#  2022-09-28 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Init
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
##
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
This module contains the functions to manage tokengroups.
It depends on the models
"""

import traceback
import string
import datetime
import os
import logging
from six import string_types

from sqlalchemy import (and_, func)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import expression

from privacyidea.lib.error import (TokenAdminError,
                                   ParameterError,
                                   privacyIDEAError, ResourceNotFoundError)
from privacyidea.lib.decorators import (check_user_or_serial,
                                        check_copy_serials)
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.utils import is_true, BASE58, hexlify_and_unicode, check_serial_valid
from privacyidea.lib.crypto import generate_password
from privacyidea.lib.log import log_with
from privacyidea.models import Tokengroup
from privacyidea.lib.config import (get_token_class, get_token_prefix,
                                    get_token_types, get_from_config,
                                    get_inc_fail_count_on_false_pin, SYSCONF)
from privacyidea.lib.user import User
from privacyidea.lib import _
from privacyidea.lib.realm import realm_is_defined
from privacyidea.lib.resolver import get_resolver_object
from privacyidea.lib.policydecorators import (libpolicy,
                                              auth_user_does_not_exist,
                                              auth_user_has_no_token,
                                              auth_user_passthru,
                                              auth_user_timelimit,
                                              auth_lastauth,
                                              auth_cache,
                                              config_lost_token,
                                              reset_all_user_tokens)
from privacyidea.lib.challengeresponsedecorators import (generic_challenge_response_reset_pin,
                                                         generic_challenge_response_resync)
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.tokenclass import TOKENKIND
from dateutil.tz import tzlocal

log = logging.getLogger(__name__)

ENCODING = "utf-8"


def set_tokengroup(name, description=None):
    return Tokengroup(name, description).save()


def delete_tokengroup(name=None, id=None):
    if not name and not id:
        raise privacyIDEAError("You need to specify either a tokengroup ID or a name.")
    if id:
        Tokengroup.query.filter_by(id=id).delete()
    elif name:
        Tokengroup.query.filter_by(name=name).delete()


def get_tokengroups(name=None, id=None):
    query = Tokengroup.query
    if name:
        query = query.filter(Tokengroup.name == name)
    if id:
        query = query.filter(Tokengroup.id == id)
    return query.all()