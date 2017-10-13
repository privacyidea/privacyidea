#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# (c) Cornelius Kölbel
# Info: http://www.privacyidea.org

import argparse
import re
from Crypto.Cipher import AES, DES
import binascii

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", help="LDIF export file.", required=True)

args = parser.parse_args()

all_tokens = []
current_token = {}
aes_key = "encryptionkey"
des_key = "encryoptionkey"

with open(args.file, 'r') as f:
    for line in f:
        if re.match("objectclass: SccDesAuthenticator.*", line):
            current_token = {}
        if re.match("sccAuthenticatorId", line):
            m = re.match("sccAuthenticatorId:(.*)$", line)
            serial = m.group(1).strip()
            current_token["serial"] = serial

        if re.match("sccTokenData", line):
            m = re.search("sccKey=\((.*?)\).*", line)
            if m:
                seed = m.group(1)
                algo, data = seed.split(":")
                current_token["algo"] = algo
                current_token["data"] = data

                if algo.lower() == "aes":
                    aes = AES.new(aes_key, AES.MODE_ECB)
                    d = aes.decrypt(binascii.unhexlify(data))
                    current_token["seed"] = d.strip("\x00")

                elif algo.lower() == "des":
                    des = DES.new(des_key)
                    d = des.decrypt(binascii.unhexlify(data))
                    current_token["seed"] = d.strip("\x00")
            else:
                print("Could not find key for token! {0}".format(line))

        if "serial" in current_token and "data" in current_token:
            all_tokens.append(current_token)
            current_token = {}


for token in all_tokens:
    print("{0!s}, {1!s}".format(token.get("serial"), token.get("seed")))

