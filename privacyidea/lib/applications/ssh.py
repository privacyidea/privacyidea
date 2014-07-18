from privacyidea.lib.applications import MachineApplicationBase
import logging
log = logging.getLogger(__name__)
# from privacyidea.lib.log import log_with
from privacyidea.lib.token import getTokens4UserOrSerial


class MachineApplication(MachineApplicationBase):
    '''
    This is the application for SSH.
    
    Required options:
        option_user
    '''
    application_name = "ssh"
    
    def get_authentication_item(self,
                                token_type,
                                serial,
                                challenge=None):
        '''
        :param token_type: the type of the token. At the moment
                           we support the tokenype "sshkey"
        :param serial:     the serial number of the token.
        :return auth_item: For Yubikey token type it
                           returns a dictionary with a "challenge" and
                           a "response".
        '''
        ret = {}
        if (token_type.lower() == "sshkey"):
                toks = getTokens4UserOrSerial(serial=serial)
                if len(toks) == 1:
                    # tokenclass is a SSHkeyTokenClass
                    tokclass = toks[0]
                    # We just return the ssh public key, so that
                    # it can be included into authorized keys.
                    ret["sshkey"] = tokclass.get_sshkey()
        else:
                log.info("Token %r, type %r is not supported by"
                         "SSH application module" % (serial, token_type))
            
        return ret
    
    def get_options(self):
        '''
        returns a dictionary with a list of required and optional options
        '''
        return {'required': [],
                'optional': ['option_user']}