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
import logging
import sys, os
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with
from importlib import import_module as dyn_import
# except:
# importlib is not available in python 2.6
# But we will not run on python 2.6 anyway
#    def dyn_import(name):
#        mod = __import__(name)
#        components = name.split('.')
#        for comp in components[1:]:
#            mod = getattr(mod, comp)
#        return mod


class MachineApplication(object):

    application_name = "base"
    '''If bulk_call is false, the administrator may
    only retrieve authentication items for the
    very host he is starting the request.
    '''
    allow_bulk_call = False

    @classmethod
    def get_name(cls):
        """
        returns the identifying name of this application class
        """
        return cls.application_name

    @classmethod
    def get_authentication_item(cls,
                                token_type,
                                serial,
                                challenge=None):
        """
        returns a dictionary of authentication items
        like public keys, challenges, responses...
        """
        return "nothing"

    @classmethod
    def get_options(cls):
        """
        returns a dictionary with a list of required and optional options
        """
        return {'required': [],
                'optional': []}


@log_with(log)
def get_auth_item(application,
                  application_module,
                  token_type,
                  serial,
                  challenge=None):

    mod = dyn_import(application_module)
    # should be able to run as class or as object
    auth_class = mod.MachineApplication
    auth_item = auth_class.get_authentication_item(token_type,
                                                   serial,
                                                   challenge=challenge)
    return auth_item


@log_with(log)
def is_application_allow_bulk_call(application_module):
    mod = dyn_import(application_module)
    auth_class = mod.MachineApplication
    return auth_class.allow_bulk_call


@log_with(log)
def get_application_types():
    """
    This function returns a dictionary of application types with the
    corresponding available attributes.

    {"luks": {"options": {"required": [],
                          "optional": ["slot", "partition"]}}
     "ssh": {"options": {"required": [],
                         "optional": ["user"]}}
    }

    :return: dictionary describing the applications
    """
    ret = {}
    current_module = sys.modules[__name__]
    module_dir = os.path.dirname(current_module.__file__)

    # load all modules and get their application names
    files = [os.path.basename(f)[:-3] for f in os.listdir(module_dir) if
             f.endswith(".py")]
    for f in files:
        if f not in ["base", "__init__"]:
            try:
                mod = dyn_import("privacyidea.lib.applications.%s" % f)
                name = mod.MachineApplication.application_name
                options = mod.MachineApplication.get_options()
                ret[name] = {"options": options}
            except Exception:
                pass


    return ret
