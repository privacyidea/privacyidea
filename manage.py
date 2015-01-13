#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 2014-12-15 Cornelius Kölbel, info@privacyidea.org
#            Initial creation
#
# (c) Cornelius Kölbel
# Info: http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ./manage.py db init
# ./manage.py db migrate
# ./manage.py createdb
#
import os
import passlib.hash
from getpass import getpass
from privacyidea.lib.security.default import DefaultSecurityModule

if os.path.exists('.env'):
    print('Importing environment from .env...')
    for line in open('.env'):
        var = line.strip().split('=')
        if len(var) == 2:
            os.environ[var[0]] = var[1]

from privacyidea.app import create_app
from flask.ext.script import Manager
from privacyidea.app import db
from flask.ext.migrate import MigrateCommand
# Wee need to import something, so that the models will be created.
from privacyidea.models import Admin

app = create_app(config_name='production')
manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def test():
    from subprocess import call
    call(['nosetests', '-v',
          '--with-coverage', '--cover-package=privacyidea', '--cover-branches',
          '--cover-erase', '--cover-html', '--cover-html-dir=cover'])


@manager.command
def addadmin(email, username, password=None):
    """
    Register a new administrator in the database.
    """
    key = app.config.get("PI_PEPPER", "missing")
    config = app.config
    if not password:
        password = getpass()
        password2 = getpass(prompt='Confirm: ')
        if password != password2:
            import sys
            sys.exit('Error: passwords do not match.')

    pw_dig = passlib.hash.pbkdf2_sha512.encrypt(key + password,
                                                rounds=10023,
                                                salt_size=10)
    print pw_dig
    db.create_all()
    user = Admin(email=email, username=username, password=pw_dig)
    user.save()
    print('Admin {0} was registered successfully.'.format(username))

@manager.command
def encrypt_enckey(encfile):
    """
    You will be asked for a password and the encryption key in the specified
    file will be encrypted with an AES key derived from your password.

    The encryption key in the file is a 96 bit binary key.

    The password based encrypted encryption key is a hex combination of an IV
    and the encrypted data.

    The result can be piped to a new encKey file.
    """
    password = getpass()
    password2 = getpass(prompt='Confirm: ')
    if password != password2:
        import sys
        sys.exit('Error: passwords do not match.')
    f = open(encfile)
    enckey = f.read()
    f.close()
    res = DefaultSecurityModule.password_encrypt(enckey, password)
    print res

@manager.command
def createdb():
    print db
    db.create_all()
    db.session.commit()

if __name__ == '__main__':
    manager.run()
