import logging
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with

try:
    from importlib import import_module as dyn_import
except:
    # importlib is not available in python 2.6
    def dyn_import(name):
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod


class MachineApplicationBase(object):

    application_name = "base"
        
    @classmethod
    def get_name(self):
        '''
        returns the identifying name of this application class
        '''
        return self.application_name
    
    def get_authentication_item(self,
                                token_type,
                                serial,
                                challenge=None):
        return "nothing"


@log_with(log)
def get_auth_item(application,
                  application_module,
                  token_type,
                  serial,
                  challenge=None):
    
    mod = dyn_import(application_module)
    auth_class = mod.MachineApplication()
    auth_item = auth_class.get_authentication_item(token_type,
                                                   serial,
                                                   challenge=challenge)
    return auth_item
