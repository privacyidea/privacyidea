import hashlib
import binascii
from Crypto.Cipher import DES

class MSCHAPV2:
    def __init__(self):
        # please not that the standards use sha1 and shs for the same cipher
        self.SHSpad1 = "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

        self.SHSpad2 = "\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2" \
            "\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2" \
            "\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2" \
            "\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2\xF2"

    # Private Methods ##############################################################

    def _Padding7to8(self, s):
        s7bit = [ ord(s[i]) for i in range(len(s)) ]
        s7bit.extend([0] * (8 - len(s7bit)))
        s8bit = [ ((s7bit[0] >> 1) & 0xff) << 1 ]
        s8bit.append(((((s7bit[0] & 0x01) << 6) | (((s7bit[1] & 0xff) >> 2) & 0xff)) & 0xff) << 1)
        s8bit.append(((((s7bit[1] & 0x03) << 5) | (((s7bit[2] & 0xff) >> 3) & 0xff)) & 0xff) << 1)
        s8bit.append(((((s7bit[2] & 0x07) << 4) | (((s7bit[3] & 0xff) >> 4) & 0xff)) & 0xff) << 1)
        s8bit.append(((((s7bit[3] & 0x0F) << 3) | (((s7bit[4] & 0xff) >> 5) & 0xff)) & 0xff) << 1)
        s8bit.append(((((s7bit[4] & 0x1F) << 2) | (((s7bit[5] & 0xff) >> 6) & 0xff)) & 0xff) << 1)
        s8bit.append(((((s7bit[5] & 0x3F) << 1) | (((s7bit[6] & 0xff) >> 7) & 0xff)) & 0xff) << 1)
        s8bit.append((s7bit[6] & 0x7F) << 1)
        ret = ''.join(map(chr, s8bit))
        return ret

    def _DesEncryptECB(self, Clear, key):
        key2 = self._Padding7to8(key)
        des = DES.new(key2, DES.MODE_ECB)
        return des.encrypt(Clear)

    def _DesEncryptCBC(self, StdText, Clear):
        des = DES.new(self._Padding7to8(Clear), DES.MODE_CBC)
        return des.encrypt(StdText)

    def _DesHash(self, Clear):
        StdText = r'KGS!@#$%'
        return self._DesEncryptCBC(StdText, Clear)

    # see rfc2759
    def _GenerateNTResponse(self, AuthenticatorChallenge, PeerChallenge, UserName, Password):
        Challenge = self._ChallengeHash(PeerChallenge, AuthenticatorChallenge, UserName)
        PasswordHash = self.NtPasswordHash(Password)
        Response = self._ChallengeResponse(Challenge, PasswordHash)
        return Response

    # see rfc2759
    def _ChallengeHash(self, PeerChallenge, AuthenticatorChallenge, UserName):
        m = hashlib.sha1()
        m.update(PeerChallenge[:16])
        m.update(AuthenticatorChallenge[:16])

        # Only the user name (as presented by the peer and
        # excluding any prepended domain name)
        # is used as input to SHAUpdate().
        m.update(UserName)

        Challenge = m.digest()[:8]
        return Challenge

    # see rfc2759
    def _ChallengeResponse(self, Challenge, PasswordHash):
        # cheap zero-pad the ZPasswordHash
        ZPasswordHash = PasswordHash + "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
        Response1 = self._DesEncryptECB(Challenge[:8], ZPasswordHash[:7])
        Response2 = self._DesEncryptECB(Challenge[:8], ZPasswordHash[7:14])
        Response3 = self._DesEncryptECB(Challenge[:8], ZPasswordHash[14:21])
        return Response1 + Response2 + Response3






    # Exported Methods  ##############################################################
    def CheckPassword(self, AuthenticatorChallenge, PeerChallenge, User, Password, NTResponse):
        # check if a password is matching with the challenges and responses
        NTResponse2 = self._GenerateNTResponse(AuthenticatorChallenge, PeerChallenge, User, Password)
        if (NTResponse2 == NTResponse):
            return 1
        else:
            return 0


    def NtPasswordHash(self, Password):
        PasswordHash = hashlib.new('md4', Password).digest()
        return PasswordHash


    def HashNtPasswordHash(self, PasswordHash):
        PasswordHashHash = hashlib.new('md4', PasswordHash).digest()
        return PasswordHashHash


    def LmPasswordHash(self, password):
        # requires ansi pass
        UcasePassword = password.upper()[0:14]
        return ''.join([self._DesHash(UcasePassword[0:7]), self._DesHash(UcasePassword[7:14])])

    # see rfc2759
    def GenerateAuthenticatorResponse(self, Password, NTResponse, PeerChallenge, AuthenticatorChallenge, UserName):
        # "Magic" constants used in response generation
        Magic1 = "\x4D\x61\x67\x69\x63\x20\x73\x65\x72\x76" \
            "\x65\x72\x20\x74\x6F\x20\x63\x6C\x69\x65" \
            "\x6E\x74\x20\x73\x69\x67\x6E\x69\x6E\x67" \
            "\x20\x63\x6F\x6E\x73\x74\x61\x6E\x74"

        Magic2 = "\x50\x61\x64\x20\x74\x6F\x20\x6D\x61\x6B"  \
            "\x65\x20\x69\x74\x20\x64\x6F\x20\x6D\x6F" \
            "\x72\x65\x20\x74\x68\x61\x6E\x20\x6F\x6E" \
            "\x65\x20\x69\x74\x65\x72\x61\x74\x69\x6F" \
            "\x6E"

        PasswordHash = self.NtPasswordHash(Password)
        PasswordHashHash = self.HashNtPasswordHash(PasswordHash)

        m = hashlib.sha1()
        m.update(PasswordHashHash[:16])
        m.update(NTResponse[:24])
        m.update(Magic1[:39])
        Digest = m.digest()

        Challenge = self._ChallengeHash(PeerChallenge, AuthenticatorChallenge, UserName)

        n = hashlib.sha1()
        n.update(Digest[:20])
        n.update(Challenge[:8])
        n.update(Magic2[:41])
        AuthenticatorResponse = n.digest()

        return AuthenticatorResponse

    # see draft-ietf-pppext-mschapv2-keys-02
    def GetMasterKey(self, PasswordHashHash, NTResponse):
        Magic1 = "\x54\x68\x69\x73\x20\x69\x73\x20\x74" \
            "\x68\x65\x20\x4D\x50\x50\x45\x20\x4D" \
            "\x61\x73\x74\x65\x72\x20\x4B\x65\x79"

        m = hashlib.sha1()
        m.update(PasswordHashHash[:16])
        m.update(NTResponse[:24])
        m.update(Magic1[:27])
        Digest = m.digest()
        MasterKey = Digest[:16]
        return MasterKey

    # see draft-ietf-pppext-mschapv2-keys-02
    def GetAsymetricStartKey(self, MasterKey, SessionKeyLength, IsSend, IsServer):
        Magic2 = "\x4F\x6E\x20\x74\x68\x65\x20\x63\x6C\x69" \
            "\x65\x6E\x74\x20\x73\x69\x64\x65\x2C\x20" \
            "\x74\x68\x69\x73\x20\x69\x73\x20\x74\x68" \
            "\x65\x20\x73\x65\x6E\x64\x20\x6B\x65\x79" \
            "\x3B\x20\x6F\x6E\x20\x74\x68\x65\x20\x73" \
            "\x65\x72\x76\x65\x72\x20\x73\x69\x64\x65" \
            "\x2C\x20\x69\x74\x20\x69\x73\x20\x74\x68" \
            "\x65\x20\x72\x65\x63\x65\x69\x76\x65\x20" \
            "\x6B\x65\x79\x2E"

        Magic3 = "\x4F\x6E\x20\x74\x68\x65\x20\x63\x6C\x69" \
            "\x65\x6E\x74\x20\x73\x69\x64\x65\x2C\x20" \
            "\x74\x68\x69\x73\x20\x69\x73\x20\x74\x68" \
            "\x65\x20\x72\x65\x63\x65\x69\x76\x65\x20" \
            "\x6B\x65\x79\x3B\x20\x6F\x6E\x20\x74\x68" \
            "\x65\x20\x73\x65\x72\x76\x65\x72\x20\x73" \
            "\x69\x64\x65\x2C\x20\x69\x74\x20\x69\x73" \
            "\x20\x74\x68\x65\x20\x73\x65\x6E\x64\x20" \
            "\x6B\x65\x79\x2E"

        if (IsSend == 1):
            if (IsServer == 1):
                s = Magic3
            else:
                s = Magic2
        else:
            if (IsServer == 1):
                s = Magic2
            else:
                s = Magic3

        m = hashlib.sha1()
        m.update(MasterKey[:16])
        m.update(self.SHSpad1[:40])
        m.update(s[:84])
        m.update(self.SHSpad2[:40])
        SessionKey = m.digest()[:SessionKeyLength]
        return SessionKey

#    def GetNewKeyFromSHA(self, StartKey, SessionKey, SessionKeyLength):
#        m = hashlib.sha1()
#        m.update(StartKey[:SessionKeyLength])
#        m.update(self.SHSpad1[:40])
#        m.update(SessionKey[:SessionKeyLength])
#        m.update(self.SHSpad2[:40])
#        InterimKey = m.digest()
#        return InterimKey[:SessionKeyLength]





##############################################################
#
# How to use this...
#
##############################################################
if __name__ == '__main__':

    a = MSCHAPV2()

    # Folgendes kommt ueber die SOAP Schnittstelle rein:
    User = "kay"
    AuthenticatorChallenge = "\xad\x26\x7f\xd1\x91\x4b\xf2\x59\xa8\x3c\xd5\x75\xd2\x52\x29\x34"
    PeerChallenge = "\x84\x93\xc2\x67\xfd\x58\x41\x22\xe6\x4a\xe6\x36\xca\x39\xb1\xf9"
    NTResponse = "\x39\x37\x18\x89\xcb\xd4\x75\x30\xa7\x8b\xe4\xe6\xa2\x3b\x36\x48\xf3\x46\x52\x03\x22\xf0\xef\x0e"

    # wir kennen das Passwort des Users aus unserer Datenbank (notwendig!)
    realPass = "test"
    # und die n naechsten validen OTP Werte
    nextPins = ("000000", "123123", "321321", "533269", "999999", "111222", "")

    # wir testen welchen der User eingegeben hat
    for pin in nextPins:
        Pass = realPass + pin
        Password = Pass.encode('utf-16-le')
        if (a.CheckPassword(AuthenticatorChallenge, PeerChallenge, User, Password, NTResponse) == 1):
            break

    #testen ob wir am ende des Arrays angelangt sind
    if (Pass == realPass):
        exit(-1)

    # wir haben das aktuell eingegebene Passwort mit Pin ermittelt
    # das brauchen wir zum einen fuer die naechsten Schritte, zum anderen
    # um den Counter zu aktualisieren
    print "Valid Password: " + Pass


    # jetzt muessen wir noch die Keys/Werte generieren die wir ueber die Soap Schnittstelle zurueckliefern
    #
    AuthResponse = a.GenerateAuthenticatorResponse(Password, NTResponse, PeerChallenge, AuthenticatorChallenge, User)
    print "Authenticator Response : " + binascii.hexlify(AuthResponse)

    PasswordHash = a.NtPasswordHash(Password)
    PasswordHashHash = a.HashNtPasswordHash(PasswordHash)
    MasterKey = a.GetMasterKey(PasswordHashHash, NTResponse)
    #print "MasterKey : " + binascii.hexlify(MasterKey)

    MasterReceiveKey = a.GetAsymetricStartKey(MasterKey, 16, 0, 1)
    print "MppeRecvKey : " + binascii.hexlify(MasterReceiveKey)

    MasterSendKey = a.GetAsymetricStartKey(MasterKey, 16, 1, 1)
    print "MppeSendKey : " + binascii.hexlify(MasterSendKey)

    # brauchen wir nicht, koennen wir aber ;-)
    #
    #SendSessionKey = a.GetNewKeyFromSHA(MasterSendKey, MasterSendKey, 16)
    #"D1269EC49FA62E3E"
    #print "MasterSendKey : " + binascii.hexlify(SendSessionKey)
    #
    #RecvSessionKey = a.GetNewKeyFromSHA(MasterReceiveKey, MasterReceiveKey, 16)
    #print "MasterReceiveKey : " + binascii.hexlify(RecvSessionKey)

    # MS Chap Mppe Key
    print "MsChapMppeKeys :" + binascii.hexlify(a.LmPasswordHash(Pass))[:16] + binascii.hexlify(a.NtPasswordHash(Password)) + "0000000000000000"

    #
    # Wenn alles geklappt hat haben wir folgendes generiert:
    #
    #    Authenticator Response
    #    0000  23 c0 1f 56 8e 57 98 f1:ef 6f 6d 97 ed ea 38 65  #..V.W...om...8e
    #    0010  f7 e4 86 f4                                      ....
    #    MppeRecvKey
    #    0000  75 e7 50 09 14 b9 75 83:e7 dc e0 bb 29 ad 46 d5  u.P...u.....).F.
    #    MppeSendKey
    #    0000  3e 91 a4 6d 47 2b 02 3e:49 92 59 aa af 12 e8 56  >..mG+.>I.Y....V
    #    MsChapMppeKeys
    #    0000  70 73 69 bc 8c 44 c7 c9:12 01 10 70 2e 9e ec 5c  psi..D.....p...\
    #    0010  77 59 22 2c d5 f4 db 5b:00 00 00 00 00 00 00 00  wY",...[........
    #







'''
POST /OTPAuthentication/Service.asmx HTTP/1.1
Accept: */*
SOAPAction: "http://tempuri.org/Authenticate"
Content-Type: text/xml; charset=utf-8
User-Agent: lse-peap-otp/1.0
Host: 192.168.0.1
Content-Length: 944
Connection: Keep-Alive

<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/"><soap:Body><Authenticate xmlns="http://tempuri.org/"><request>&lt;?xml version="1.0"?&gt;&#x000D;&#x000A;&lt;otp_authentication_request&gt;&lt;user_name&gt;kay&lt;/user_name&gt;&lt;protocol_information&gt;&lt;type&gt;MSCHAPv2&lt;/type&gt;&lt;protocol_specific&gt;&lt;Mschapv2Info&gt;&lt;UserName&gt;a2F5&lt;/UserName&gt;&lt;AuthenticatorChallenge&gt;d5IdJ2Vz0lPQnbWCtkANEg==&lt;/AuthenticatorChallenge&gt;&lt;PeerChallenge&gt;9BLF7lf4rXn0d2/lKlD4sQ==&lt;/PeerChallenge&gt;&lt;Response&gt;ZkFXjp+Pbpun7yw+kPwwscjMCrlMifEg&lt;/Response&gt;&lt;/Mschapv2Info&gt;&lt;/protocol_specific&gt;&lt;/protocol_information&gt;&lt;/otp_authentication_request&gt;&#x000D;&#x000A;</request></Authenticate></soap:Body></soap:Envelope>


HTTP/1.1 200 OK
Date: Tue, 07 Dec 2010 12:30:33 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private, max-age=0
Content-Type: text/xml; charset=utf-8
Content-Length: 1023

<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><AuthenticateResponse xmlns="http://tempuri.org/"><AuthenticateResult>&lt;?xml version="1.0" encoding="UTF-8"?&gt;&lt;otp_authentication_response&gt;&lt;error_code&gt;0&lt;/error_code&gt;&lt;error_description&gt;&lt;/error_description&gt;&lt;protocol_information&gt;&lt;protocol_specific&gt;&lt;Mschapv2Response&gt;&lt;MppeRecvKey&gt;Fqp+6ZYTBXcF+/WxhrPl2w==&lt;/MppeRecvKey&gt;&lt;MppeSendKey&gt;NLbqfzJ46qWkj7o2piJwIg==&lt;/MppeSendKey&gt;&lt;AuthenticatorResponse&gt;9d/tDuQYp+UqCqtkiBHyCVusw2g=&lt;/AuthenticatorResponse&gt;&lt;MschapMppeKeys&gt;FNcjWi+hZhVZElihVL3bjeisBR8oMExBAAAAAAAAAAA=&lt;/MschapMppeKeys&gt;&lt;/Mschapv2Response&gt;&lt;/protocol_specific&gt;&lt;/protocol_information&gt;&lt;/otp_authentication_response&gt;</AuthenticateResult></AuthenticateResponse></soap:Body></soap:Envelope>




POST /OTPAuthentication/Service.asmx HTTP/1.1
Accept: */*
SOAPAction: "http://tempuri.org/Authenticate"
Content-Type: text/xml; charset=utf-8
User-Agent: lse-peap-otp/1.0
Host: 192.168.0.1
Content-Length: 944
Connection: Keep-Alive

<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/"><soap:Body><Authenticate xmlns="http://tempuri.org/"><request>&lt;?xml version="1.0"?&gt;&#x000D;&#x000A;&lt;otp_authentication_request&gt;&lt;user_name&gt;kay&lt;/user_name&gt;&lt;protocol_information&gt;&lt;type&gt;MSCHAPv2&lt;/type&gt;&lt;protocol_specific&gt;&lt;Mschapv2Info&gt;&lt;UserName&gt;a2F5&lt;/UserName&gt;&lt;AuthenticatorChallenge&gt;z9PgKRK5SW2gk24+E1IgVA==&lt;/AuthenticatorChallenge&gt;&lt;PeerChallenge&gt;RVdooRLVqxqDTbbuZsPw4w==&lt;/PeerChallenge&gt;&lt;Response&gt;PRaWDoetxEy9RAA8WrLSuXavIBnmLO/w&lt;/Response&gt;&lt;/Mschapv2Info&gt;&lt;/protocol_specific&gt;&lt;/protocol_information&gt;&lt;/otp_authentication_request&gt;&#x000D;&#x000A;</request></Authenticate></soap:Body></soap:Envelope>


HTTP/1.1 200 OK
Date: Tue, 07 Dec 2010 12:30:59 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private, max-age=0
Content-Type: text/xml; charset=utf-8
Content-Length: 675

<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><AuthenticateResponse xmlns="http://tempuri.org/"><AuthenticateResult>&lt;?xml version="1.0" encoding="UTF-8"?&gt;&lt;otp_authentication_response&gt;&lt;error_code&gt;1&lt;/error_code&gt;&lt;error_description&gt;OTP authentication failed. &lt;/error_description&gt;&lt;protocol_information&gt;&lt;protocol_specific /&gt;&lt;/protocol_information&gt;&lt;/otp_authentication_response&gt;</AuthenticateResult></AuthenticateResponse></soap:Body></soap:Envelope>




'''
