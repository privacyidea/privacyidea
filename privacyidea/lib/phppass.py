#!/usr/bin/env python
#
# phpass version: 0.3 / genuine.
#
# Placed in public domain
#
# source: https://github.com/exavolt/python-phpass
#

#CHECK: use pyDES instead of the native crypt module?

import os
import time
import hashlib
import crypt


try:
    import bcrypt
    _bcrypt_hashpw = bcrypt.hashpw
except ImportError:
    _bcrypt_hashpw = None

# On App Engine, this function is not available.
if hasattr(os, 'getpid'):
    _pid = os.getpid()
else:
    # Fake PID
    from privacyidea.lib.crypto import urandom
    _pid = urandom.randint(0, 100000)


class PasswordHash:

    def __init__(self, iteration_count_log2=8, portable_hashes=True,
         algorithm=''):
        alg = algorithm.lower()
        if (alg == 'blowfish' or alg == 'bcrypt') and _bcrypt_hashpw is None:
            raise NotImplementedError('The bcrypt module is required')
        self.itoa64 = \
            './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        if iteration_count_log2 < 4 or iteration_count_log2 > 31:
            iteration_count_log2 = 8
        self.iteration_count_log2 = iteration_count_log2
        self.portable_hashes = portable_hashes
        self.algorithm = algorithm
        self.random_state = '%r%r' % (time.time(), _pid)

    def get_random_bytes(self, count):
        outp = ''
        try:
            outp = os.urandom(count)
        except:
            pass
        if len(outp) < count:
            outp = ''
            rem = count
            while rem > 0:
                self.random_state = hashlib.md5(str(time.time())
                    + self.random_state).hexdigest()
                outp += hashlib.md5(self.random_state).digest()
                rem -= 1
            outp = outp[:count]
        return outp

    def encode64(self, inp, count):
        outp = ''
        cur = 0
        while cur < count:
            value = ord(inp[cur])
            cur += 1
            outp += self.itoa64[value & 0x3f]
            if cur < count:
                value |= (ord(inp[cur]) << 8)
            outp += self.itoa64[(value >> 6) & 0x3f]
            if cur >= count:
                break
            cur += 1
            if cur < count:
                value |= (ord(inp[cur]) << 16)
            outp += self.itoa64[(value >> 12) & 0x3f]
            if cur >= count:
                break
            cur += 1
            outp += self.itoa64[(value >> 18) & 0x3f]
        return outp

    def gensalt_private(self, inp):
        outp = '$P$'
        outp += self.itoa64[min([self.iteration_count_log2 + 5, 30])]
        outp += self.encode64(inp, 6)
        return outp

    def crypt_private(self, pw, setting):
        outp = '*0'
        if setting.startswith(outp):
            outp = '*1'
        if not setting.startswith('$P$') and not setting.startswith('$H$'):
            return outp
        count_log2 = self.itoa64.find(setting[3])
        if count_log2 < 7 or count_log2 > 30:
            return outp
        count = 1 << count_log2
        salt = setting[4:12]
        if len(salt) != 8:
            return outp
        if not isinstance(pw, str):
            pw = pw.encode('utf-8')
        hx = hashlib.md5(salt + pw).digest()
        while count:
            hx = hashlib.md5(hx + pw).digest()
            count -= 1
        return setting[:12] + self.encode64(hx, 16)

    def gensalt_extended(self, inp):
        count_log2 = min([self.iteration_count_log2 + 8, 24])
        count = (1 << count_log2) - 1
        outp = '_'
        outp += self.itoa64[count & 0x3f]
        outp += self.itoa64[(count >> 6) & 0x3f]
        outp += self.itoa64[(count >> 12) & 0x3f]
        outp += self.itoa64[(count >> 18) & 0x3f]
        outp += self.encode64(inp, 3)
        return outp

    def gensalt_blowfish(self, inp):
        itoa64 = \
            './ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        outp = '$2a$'
        outp += chr(ord('0') + self.iteration_count_log2 / 10)
        outp += chr(ord('0') + self.iteration_count_log2 % 10)
        outp += '$'
        cur = 0
        while True:
            c1 = ord(inp[cur])
            cur += 1
            outp += itoa64[c1 >> 2]
            c1 = (c1 & 0x03) << 4
            if cur >= 16:
                outp += itoa64[c1]
                break
            c2 = ord(inp[cur])
            cur += 1
            c1 |= c2 >> 4
            outp += itoa64[c1]
            c1 = (c2 & 0x0f) << 2
            c2 = ord(inp[cur])
            cur += 1
            c1 |= c2 >> 6
            outp += itoa64[c1]
            outp += itoa64[c2 & 0x3f]
        return outp

    def hash_password(self, pw):
        rnd = ''
        alg = self.algorithm.lower()
        if (not alg or alg == 'blowfish' or alg == 'bcrypt') \
             and not self.portable_hashes:
            if _bcrypt_hashpw is None:
                if (alg == 'blowfish' or alg == 'bcrypt'):
                    raise NotImplementedError('The bcrypt module is required')
            else:
                rnd = self.get_random_bytes(16)
                salt = self.gensalt_blowfish(rnd)
                hx = _bcrypt_hashpw(pw, salt)
                if len(hx) == 60:
                    return hx
        if (not alg or alg == 'ext-des') and not self.portable_hashes:
            if len(rnd) < 3:
                rnd = self.get_random_bytes(3)
            hx = crypt.crypt(pw, self.gensalt_extended(rnd))
            if len(hx) == 20:
                return hx
        if len(rnd) < 6:
            rnd = self.get_random_bytes(6)
        hx = self.crypt_private(pw, self.gensalt_private(rnd))
        if len(hx) == 34:
            return hx
        return '*'

    def check_password(self, pw, stored_hash):
        # This part is different with the original PHP
        if stored_hash.startswith('$2a$'):
            # bcrypt
            if _bcrypt_hashpw is None:
                raise NotImplementedError('The bcrypt module is required')
            hx = _bcrypt_hashpw(pw, stored_hash)
        elif stored_hash.startswith('_'):
            # ext-des
            hx = crypt.crypt(pw, stored_hash)
        else:
            # portable hash
            hx = self.crypt_private(pw, stored_hash)
        return hx == stored_hash



if __name__ == "__main__":
    import getpass
    while True:
        pw = getpass.getpass()
        pw2 = getpass.getpass('Retype password: ')
        if pw == pw2:
            break
        print "Both passwords must be the same"
    t_hasher = PasswordHash(8, True)
    print "Password hash: " + t_hasher.hash_password(pw)

