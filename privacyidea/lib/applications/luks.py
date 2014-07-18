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
        '''
        :param token_type: the type of the token. At the moment
                           we only support yubikeys, tokentype "TOTP".
        :param serial:     the serial number of the token.
                           The challenge response token needs to start with
                           "UBOM".
        :param challenge:  A challenge, for which a response get calculated.
                           If none is presented, we create one.
        :type challenge:   hex string
        :return auth_item: For Yubikey token type it
                           returns a dictionary with a "challenge" and
                           a "response".
        '''
        ret = {}
        if (token_type.lower() == "totp" and serial.startswith("UBOM")):
                # create a challenge of 32 byte
                # Although the yubikey is capable of doing 64byte challenges
                # the hmac module calculates different responses for 64 bytes.
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
