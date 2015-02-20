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
import sys
from getpass import getpass
from privacyidea.lib.security.default import DefaultSecurityModule
from privacyidea.lib.auth import (create_db_admin, list_db_admin,
                                  delete_db_admin)
from privacyidea.app import create_app
from flask.ext.script import Manager
from privacyidea.app import db
from flask.ext.migrate import MigrateCommand
# Wee need to import something, so that the models will be created.
from privacyidea.models import Admin
from Crypto.PublicKey import RSA

app = create_app(config_name='production')
manager = Manager(app)
admin_manager = Manager(usage='Create new administrators or modify existing '
                              'ones.')
manager.add_command('db', MigrateCommand)
manager.add_command('admin', admin_manager)


@admin_manager.command
def add(username, email, password=None):
    """
    Register a new administrator in the database.
    """
    db.create_all()
    if not password:
        password = getpass()
        password2 = getpass(prompt='Confirm: ')
        if password != password2:
            import sys
            sys.exit('Error: passwords do not match.')

    create_db_admin(app, username, email, password)
    print('Admin {0} was registered successfully.'.format(username))

@admin_manager.command
def list():
    """
    List all administrators.
    """
    list_db_admin()

@admin_manager.command
def delete(username):
    """
    Delete an existing administrator.
    """
    delete_db_admin(username)

@admin_manager.command
def change(username, email=None, password_prompt=False):
    """
    Change the email address or the password of an existing administrator.
    """
    if password_prompt:
        password = getpass()
        password2 = getpass(prompt='Confirm: ')
        if password != password2:
            import sys
            sys.exit('Error: passwords do not match.')
    else:
        password = None

    create_db_admin(app, username, email, password)


@manager.command
def test():
    """
    Run all nosetests.
    """
    from subprocess import call
    call(['nosetests', '-v',
          '--with-coverage', '--cover-package=privacyidea', '--cover-branches',
          '--cover-erase', '--cover-html', '--cover-html-dir=cover'])

@manager.command
def encrypt_enckey(encfile):
    """
    You will be asked for a password and the encryption key in the specified
    file will be encrypted with an AES key derived from your password.

    The encryption key in the file is a 96 bit binary key.

    The password based encrypted encryption key is a hex combination of an IV
    and the encrypted data.

    The result can be piped to a new enckey file.
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
def create_enckey():
    """
    If the key of the given configuration does not exist, it will be created
    """
    print
    filename = app.config.get("PI_ENCFILE")
    if os.path.isfile(filename):
        print("The file \n\t%s\nalready exist. We do not overwrite it!" %
              filename)
        sys.exit(1)
    f = open(filename, "w")
    f.write(DefaultSecurityModule.random(96))
    f.close()
    print "Encryption key written to %s" % filename
    print "Please ensure to set the access rights for the correct user to 400!"


@manager.command
def create_audit_keys(keysize=2048):
    """
    Create the RSA signing keys for the audit log.
    You may specify an additional keysize.
    The default keysize is 2048 bit.
    """
    filename = app.config.get("PI_AUDIT_KEY_PRIVATE")
    if os.path.isfile(filename):
        print("The file \n\t%s\nalready exist. We do not overwrite it!" %
              filename)
        sys.exit(1)
    new_key = RSA.generate(keysize, e=65537)
    public_key = new_key.publickey().exportKey("PEM")
    private_key = new_key.exportKey("PEM")
    f = open(filename, "w")
    f.write(private_key)
    f.close()

    f = open(app.config.get("PI_AUDIT_KEY_PUBLIC"), "w")
    f.write(public_key)
    f.close()
    print("Signing keys written to %s and %s" %
          (filename, app.config.get("PI_AUDIT_KEY_PUBLIC")))
    print("Please ensure to set the access rights for the correct user to 400!")


@manager.command
def createdb():
    """
    Initially create the tables in the database. The database must exist.
    (SQLite database will be created)
    """
    print db
    db.create_all()
    db.session.commit()

if __name__ == '__main__':
    manager.run()
