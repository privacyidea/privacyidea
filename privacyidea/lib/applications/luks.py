from privacyidea.lib.applications import MachineApplicationBase
import logging
log = logging.getLogger(__name__)
# from privacyidea.lib.log import log_with
from privacyidea.lib.crypto import geturandom
import binascii
from privacyidea.lib.token import getTokens4UserOrSerial


class MachineApplication(MachineApplicationBase):
    '''
    This is the application for LUKS.
    '''
    application_name = "luks"
    
    def get_authentication_item(self,
                                token_type,
                                serial,
                                challenge=None):
        ret = {}
        if (token_type.lower() == "totp" and serial.startswith("UBOM")):
                # create a challenge of 32 byte
                if challenge is None:
                    challenge = geturandom(32)
                    challenge_hex = binascii.hexlify(challenge)
                else:
                    challenge_hex = challenge
                ret["challenge"] = challenge_hex
                # create the response. We need to get
                # the HMAC key and calculate a HMAC response for
                # the challenge
                toks = getTokens4UserOrSerial(serial=serial)
                if len(toks) == 1:
                    # tokenclass is a TimeHmacTokenClass
                    tokclass = toks[0]
                    (_r, _p, otp, _c) = tokclass.getOtp(challenge=challenge_hex,
                                                        do_truncation=False)
                    ret["response"] = otp
        else:
                log.info("Token %r, type %r is not supported by"
                         "LUKS application module" % (serial, token_type))
            
        return ret
