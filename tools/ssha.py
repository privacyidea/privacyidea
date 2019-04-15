#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import base64
import getpass
import hashlib
import os


def get_hash(passwd, salt):
    """
    Calculate a sha1 hash of a password with salt.

    :param passwd: The password
    :type passwd: string
    :param salt: The salt
    :type salt: bytestring
    :return: string

    lets see if doctest works:

    >>> print(get_hash('test', b'test'))
    {SSHA}Uau5Y2B43vv4iNhFenx2+FyPEUx0ZXN0

    """
    h = hashlib.sha1(passwd.encode('utf8') + salt).digest()
    return '{SSHA}' + base64.b64encode(h + salt).decode('utf8')


if __name__ == '__main__':
    salt = os.urandom(8)  # edit the length as you see fit
    print(get_hash(getpass.getpass(), salt))
