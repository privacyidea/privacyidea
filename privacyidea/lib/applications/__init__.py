import importlib
import logging
log = logging.getLogger(__name__)
from privacyidea.lib.log import log_with


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
    
    mod = importlib.import_module(application_module)
    auth_class = mod.MachineApplication()
    auth_item = auth_class.get_authentication_item(token_type,
                                                   serial,
                                                   challenge=challenge)
    return auth_item
