#!/usr/bin/env python
import base64, getpass, hashlib, os
salt = os.urandom(8) # edit the length as you see fit
print '{SSHA}' + base64.b64encode(hashlib.sha1(getpass.getpass() + salt).digest() + salt)
