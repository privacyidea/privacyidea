"""
This test file tests the lib.importotp

"""


from .base import MyTestCase
from privacyidea.lib.importotp import (parseOATHcsv, parseYubicoCSV,
                                       parseSafeNetXML, ImportException,
                                       parsePSKCdata)

XML_PSKC = '''<?xml version="1.0" encoding="UTF-8"?>
<KeyContainer Version="1.0" xmlns ="urn:ietf:params:xml:ns:keyprov:pskc">
  <KeyPackage>
    <DeviceInfo>
      <Manufacturer>Feitian Technology Co.,Ltd</Manufacturer>
      <SerialNo>1000133508267</SerialNo>
    </DeviceInfo>
    <Key Id="1000133508267" Algorithm="urn:ietf:params:xml:ns:keyprov:pskc:hotp">
      <AlgorithmParameters>
        <ResponseFormat Length="6" Encoding="DECIMAL"/>
      </AlgorithmParameters>
      <Data>
        <Secret>
          <PlainValue>PuMnCivln/14Ii3DNhR4/1zGN5A=</PlainValue>
        </Secret>
        <Counter>
          <PlainValue>0</PlainValue>
        </Counter>
      </Data>
      <Policy>
        <StartDate>2012-08-01T00:00:00Z</StartDate>
        <ExpiryDate>2037-12-31T00:00:00Z</ExpiryDate>
      </Policy>
    </Key>
  </KeyPackage>
  <KeyPackage>
    <DeviceInfo>
      <Manufacturer>Feitian Technology Co.,Ltd</Manufacturer>
      <SerialNo>1000133508255</SerialNo>
    </DeviceInfo>
    <Key Id="1000133508255" Algorithm="urn:ietf:params:xml:ns:keyprov:pskc:hotp">
      <AlgorithmParameters>
        <ResponseFormat Length="6" Encoding="DECIMAL"/>
      </AlgorithmParameters>
      <Data>
        <Secret>
          <PlainValue>wRjcslncyKj//L1oaDVQbAvCNnI=</PlainValue>
        </Secret>
        <Counter>
          <PlainValue>0</PlainValue>
        </Counter>
      </Data>
      <Policy>
        <StartDate>2012-08-01T00:00:00Z</StartDate>
        <ExpiryDate>2037-12-31T00:00:00Z</ExpiryDate>
      </Policy>
    </Key>
  </KeyPackage>
  <KeyPackage>
    <DeviceInfo>
      <Manufacturer>Feitian Technology Co.,Ltd</Manufacturer>
      <SerialNo>2600124809778</SerialNo>
    </DeviceInfo>
    <Key Id="2600124809778" Algorithm="urn:ietf:params:xml:ns:keyprov:pskc:totp">
      <AlgorithmParameters>
        <ResponseFormat Length="6" Encoding="DECIMAL"/>
      </AlgorithmParameters>
      <Data>
        <Secret>
          <PlainValue>MRffGnGNJKmo8uSW313HCvGNIYM=</PlainValue>
        </Secret>
        <Time>
          <PlainValue>0</PlainValue>
        </Time>
        <TimeInterval>
          <PlainValue>60</PlainValue>
        </TimeInterval>
      </Data>
      <Policy>
        <StartDate>2012-08-01T00:00:00Z</StartDate>
        <ExpiryDate>2037-12-31T00:00:00Z</ExpiryDate>
      </Policy>
    </Key>
  </KeyPackage>
  <KeyPackage>
    <DeviceInfo>
      <Manufacturer>Feitian Technology Co.,Ltd</Manufacturer>
      <SerialNo>2600124809787</SerialNo>
    </DeviceInfo>
    <Key Id="2600124809787" Algorithm="urn:ietf:params:xml:ns:keyprov:pskc:totp">
      <AlgorithmParameters>
        <ResponseFormat Length="6" Encoding="DECIMAL"/>
      </AlgorithmParameters>
      <Data>
        <Secret>
          <PlainValue>9O9PX9g20x74kIcaLLrGiwMUReM=</PlainValue>
        </Secret>
        <Time>
          <PlainValue>0</PlainValue>
        </Time>
        <TimeInterval>
          <PlainValue>60</PlainValue>
        </TimeInterval>
      </Data>
      <Policy>
        <StartDate>2012-08-01T00:00:00Z</StartDate>
        <ExpiryDate>2037-12-31T00:00:00Z</ExpiryDate>
      </Policy>
    </Key>
  </KeyPackage>
  <KeyPackage>
    <DeviceInfo>
      <Manufacturer>Feitian Technology Co.,Ltd</Manufacturer>
      <SerialNo>2600135004012</SerialNo>
    </DeviceInfo>
    <Key Id="2600135004012" Algorithm="urn:ietf:params:xml:ns:keyprov:pskc:totp">
      <AlgorithmParameters>
        <ResponseFormat Length="6" Encoding="DECIMAL"/>
      </AlgorithmParameters>
      <Data>
        <Secret>
          <PlainValue>A0DxFX1zRVTsxJlMKFsDXuNQYcI=</PlainValue>
        </Secret>
        <Time>
          <PlainValue>0</PlainValue>
        </Time>
        <TimeInterval>
          <PlainValue>60</PlainValue>
        </TimeInterval>
      </Data>
      <Policy>
        <StartDate>2012-08-01T00:00:00Z</StartDate>
        <ExpiryDate>2037-12-31T00:00:00Z</ExpiryDate>
      </Policy>
    </Key>
  </KeyPackage>
  <KeyPackage>
    <DeviceInfo>
      <Manufacturer>Feitian Technology Co.,Ltd</Manufacturer>
      <SerialNo>2600135004013</SerialNo>
    </DeviceInfo>
    <Key Id="2600135004013" Algorithm="urn:ietf:params:xml:ns:keyprov:pskc:totp">
      <AlgorithmParameters>
        <ResponseFormat Length="6" Encoding="DECIMAL"/>
      </AlgorithmParameters>
      <Data>
        <Secret>
          <PlainValue>NSLuCF/qeQPsqY7Sod4anJMjIBg=</PlainValue>
        </Secret>
        <Time>
          <PlainValue>0</PlainValue>
        </Time>
        <TimeInterval>
          <PlainValue>60</PlainValue>
        </TimeInterval>
      </Data>
      <Policy>
        <StartDate>2012-08-01T00:00:00Z</StartDate>
        <ExpiryDate>2037-12-31T00:00:00Z</ExpiryDate>
      </Policy>
    </Key>
  </KeyPackage>
</KeyContainer>
'''

DATDATA = '''
# ===== SafeWord Authenticator Records $Version: 100$ =====
dn: sccAuthenticatorId=RAINER01
objectclass: sccCompatibleToken
sccAuthenticatorId: RAINER01
sccTokenType: eToken-PASS-ES
sccTokenData: sccKey=E26BF3661C254BBAB7370296A6DE60D7AC8E0141;sccMode=E;sccPwLen=6;sccVer=6.20;
sccSignature:MC0CFGxPAjrb0zg7MwFzrPibnC70klMnAhUAwZzVdGBaKGjA0djXrGuv6ejTtII=

dn: sccAuthenticatorId=RAINER02
objectclass: sccCompatibleToken
sccAuthenticatorId: RAINER02
sccTokenType: eToken-PASS-TS
sccTokenData: sccKey=535CC2CB9DEA0B55B0A2D585EAB648EBCE73AC8B;sccMode=T;sccPwLen=6;sccVer=6.20;sccTick=30;sccPrTime=2013/03/12 00:00:00
sccSignature: MC4CFQDju23MCRqmkWC7Z9sVDB0y0TeEOwIVAOIibmqMFxhPiY7mLlkt5qmRT/xn        '''


YUBIKEYCSV= '''
        Static Password: Scan Code,17.04.12 12:25,1,051212172c092728,,,,,0,0,0,0,0,0,0,0,0,0
        Static Password: Scan Code,17.04.12 12:27,1,282828051212172c092728,,,,,0,0,0,0,0,0,0,0,0,0
        LOGGING START,17.04.12 12:29
        Static Password: Scan Code,17.04.12 12:29,1,2828282828051212172c092728,,,,,0,0,0,0,0,0,0,0,0,0
        LOGGING START,11.12.13 16:43
        Yubico OTP,11.12.13 16:43,1,cccccccirblh,b321173a2fb8,6faa3ce885fcd5eda7efa5195e5a5d44,,,0,0,0,0,0,0,0,0,0,1
        Yubico OTP,11.12.13 16:43,1,ccccccbgbhkl,9b19889fc5c1,11261596dbbeae6538b26ce0cfd4f9c9,,,0,0,0,0,0,0,0,0,0,1
        LOGGING START,11.12.13 18:55
        OATH-HOTP,11.12.13 18:55,1,cccccccccccc,,916821d3a138bf855e70069605559a206ba854cd,,,0,0,0,6,0,0,0,0,0,0
        LOGGING START,11.12.13 18:58
        Yubico OTP,11.12.13 18:58,1,,,a54c68c7c3d5a1fec8a0c85b8d60765b,,,0,0,0,0,0,0,0,0,0,0
        LOGGING START,11.12.13 19:00
        OATH-HOTP,11.12.13 19:00,1,cccccccccccc,,1390612c06ec6dd0fa077ce99bf9c86d2c058f42,,,0,0,0,6,0,0,0,0,0,0
        LOGGING START,11.12.13 19:01
        OATH-HOTP,11.12.13 19:01,1,,,d41845578effd750887edc70f04df754603e2b63,,,0,0,0,6,0,0,0,0,0,0
        LOGGING START,11.12.13 19:05
        Static Password: Scan Code,11.12.13 19:05,1,040716040416070416041607041607,,,,,0,0,0,0,0,0,0,0,0,0
        LOGGING START,11.12.13 19:06
        Static Password: Scan Code,11.12.13 19:06,1,1e1f201a1407048796,,,,,0,0,0,0,0,0,0,0,0,0
        Static Password: Scan Code,11.12.13 19:06,1,1e1f201a1407048796,,,,,0,0,0,0,0,0,0,0,0,0
        LOGGING START,11.12.13 19:07
        Static Password,11.12.13 19:07,1,,ba23877e747c,fe8abdf8c0c9b6ad6a1daabefa4d50b3,,,0,0,0,0,0,0,0,0,0,0
        Static Password,11.12.13 19:08,1,,d5a3d50327dc,0e8e37b0e38b314a56748c030f58d21d,,,0,0,0,0,0,0,0,0,0,0
        Static Password,11.12.13 19:08,1,cccc,d5a3d50327dc,
        0e8e37b0e38b314a56748c030f58d21d,,,0,0,0,0,0,0,0,0,0,0
# Traditional Format:
Yubico OTP,12/11/2013 11:10,1,vvgutbiedkvi,ab86c04de6a3,d26a7c0f85fdda28bd816e406342b214,,,0,0,0,0,0,0,0,0,0,0
OATH-HOTP,11.12.13 18:55,1,cccccccccccc,,916821d3a138bf855e70069605559a206ba854cd,,,0,0,0,6,0,0,0,0,0,0
Static Password,11.12.13 19:08,1,,d5a3d50327dc,0e8e37b0e38b314a56748c030f58d21d,,,0,0,0,0,0,0,0,0,0,0
# Yubico Format:
# OATH mode
508327,,0,69cfb9202438ca68964ec3244bfa4843d073a43b,,2013-12-12T08:41:07,
1382042,,0,bf7efc1c8b6f23604930a9ce693bdd6c3265be00,,2013-12-12T08:41:17,
# Yubico mode
508328,cccccccccccc,83cebdfb7b93,a47c5bf9c152202f577be6721c0113af,,2013-12-12T08:43:17,
# static mode
508329,,,9e2fd386224a7f77e9b5aee775464033,,2013-12-12T08:44:34,
        '''

ALADDINXML = '''
        <Tokens>
        <Token serial="00040008CFA5">
        <CaseModel>5</CaseModel>
        <Model>101</Model>
        <ProductionDate>02/19/2009</ProductionDate>
        <ProductName>Safeword Alpine</ProductName>
        <Applications>
        <Application ConnectorID="{ab1397d2-ddb6-4705-b66e-9f83f322deb9}">
        <Seed>123412354</Seed>
        <MovingFactor>1</MovingFactor>
        </Application>
        </Applications>
        </Token>

        <Token serial="00040008CFA52">
        <CaseModel>5</CaseModel>
        <Model>101</Model>
        <ProductionDate>02/19/2009</ProductionDate>
        <ProductName>Safeword Alpine</ProductName>
        <Applications>
        <Application ConnectorID="{ab1397d2-ddb6-4705-b66e-9f83f322deb9}">
        <Seed>123456</Seed>
        <MovingFactor>1</MovingFactor>
        </Application>
        </Applications>
        </Token>

        <Token info="token without serial">
        <CaseModel>5</CaseModel>
        <Model>101</Model>
        <ProductionDate>02/19/2009</ProductionDate>
        <ProductName>Safeword Alpine</ProductName>
        <Applications>
        <Application ConnectorID="{ab1397d2-ddb6-4705-b66e-9f83f322deb9}">
        <Seed>123456</Seed>
        <MovingFactor>1</MovingFactor>
        </Application>
        </Applications>
        </Token>

        <Token serial="token_without_seed">
        <CaseModel>5</CaseModel>
        <Model>101</Model>
        <ProductionDate>02/19/2009</ProductionDate>
        <ProductName>Safeword Alpine</ProductName>
        <Applications>
        <Application ConnectorID="{ab1397d2-ddb6-4705-b66e-9f83f322deb9}">
        <MovingFactor>1</MovingFactor>
        </Application>
        </Applications>
        </Token>

        <Token serial="sha256">
        <CaseModel>5</CaseModel>
        <Model>101</Model>
        <ProductionDate>02/19/2009</ProductionDate>
        <ProductName>Safeword Alpine</ProductName>
        <Applications>
        <Application ConnectorID="{ab1397d2-ddb6-4705-b66e-9f83f322deb9}">
        <seed>1234567890123456789012345678901234567890123456789012345678901234
        </seed>
        <MovingFactor>1</MovingFactor>
        </Application>
        </Applications>
        </Token>

        </Tokens>
        '''

ALADDINXML_WITHOUT_TOKENS = '''
        <Token serial="00040008CFA5">
        <CaseModel>5</CaseModel>
        <Model>101</Model>
        <ProductionDate>02/19/2009</ProductionDate>
        <ProductName>Safeword Alpine</ProductName>
        <Applications>
        <Application ConnectorID="{ab1397d2-ddb6-4705-b66e-9f83f322deb9}">
        <Seed>123412354</Seed>
        <MovingFactor>1</MovingFactor>
        </Application>
        </Applications>
        </Token>
        '''

OATHCSV = '''
        tok1, 1212
        tok2, 1212, totp, 6
        tok3, 1212, hotp, 8
        tok4, 1212, totp, 8, 60

        tok5, 12345678901234567890123456789023
        # this is a comment
        # a serial without an OTP key will not create a token
        serialX
        '''

class ImportOTPTestCase(MyTestCase):

    def test_00_import_oath(self):
        tokens = parseOATHcsv(OATHCSV)
        self.assertTrue(len(tokens) == 5, len(tokens))
        self.assertTrue("tok1" in tokens, tokens)
        self.assertTrue("tok2" in tokens, tokens)
        self.assertTrue("tok3" in tokens, tokens)
        self.assertTrue("tok4" in tokens, tokens)

    def test_01_import_aladdin_xml(self):
        tokens = parseSafeNetXML(ALADDINXML)
        self.assertTrue(len(tokens) == 2)
        self.assertTrue("00040008CFA52" in tokens, tokens)

        # fail to import without toplevel TOKENS tag
        self.assertRaises(ImportException, parseSafeNetXML,
                          ALADDINXML_WITHOUT_TOKENS)

    def test_02_import_yubikey(self):
        tokens = parseYubicoCSV(YUBIKEYCSV)
        self.assertTrue(len(tokens) == 7, len(tokens))
        self.assertTrue("UBAM00508326_1" in tokens, tokens)

    def test_03_import_pskc(self):
        tokens = parsePSKCdata(XML_PSKC)
        self.assertEqual(len(tokens), 6)
        self.assertEqual(tokens["1000133508267"].get("type"), "hotp")
        self.assertEqual(tokens["2600135004013"].get("type"), "totp")
        self.assertEqual(tokens["2600135004013"].get("timeStep"), "60")
