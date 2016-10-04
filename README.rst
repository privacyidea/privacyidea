privacyIDEA
===========

.. image:: https://travis-ci.org/privacyidea/privacyidea.svg?branch=master
    :alt: Build Status
    :target: https://travis-ci.org/privacyidea/privacyidea

.. image:: https://circleci.com/gh/privacyidea/privacyidea/tree/master.svg?style=shield&circle-token=:circle-token
    :alt: CircleCI
    :target: https://circleci.com/gh/privacyidea/privacyidea

.. image:: https://codecov.io/github/privacyidea/privacyidea/coverage.svg?branch=master
    :target: https://codecov.io/github/privacyidea/privacyidea?branch=master

.. .. image:: https://img.shields.io/pypi/dm/privacyidea.svg
..    :alt: Downloads
..    :target: https://pypi.python.org/pypi/privacyidea/
    
.. image:: https://img.shields.io/pypi/v/privacyidea.svg
    :alt: Latest Version
    :target: https://pypi.python.org/pypi/privacyidea/
    
.. image:: https://img.shields.io/github/license/privacyidea/privacyidea.svg
    :alt: License
    :target: https://pypi.python.org/pypi/privacyidea/
    
.. image:: https://readthedocs.org/projects/privacyidea/badge/?version=latest
    :alt: Documentation
    :target: http://privacyidea.readthedocs.org/en/latest/

.. .. image:: https://codeclimate.com/github/privacyidea/privacyidea/badges/gpa.svg
..    :alt: Code Climate
..    :target: https://codeclimate.com/github/privacyidea/privacyidea

.. image:: https://www.quantifiedcode.com/api/v1/project/c2e431a6764443268aa0eddb0da6b1fb/badge.svg
  :target: https://www.quantifiedcode.com/app/project/c2e431a6764443268aa0eddb0da6b1fb
  :alt: Code issues

.. image:: https://api.codacy.com/project/badge/grade/d58934978e1a4bcca325f2912ea386ff
    :alt: Codacy Badge
    :target: https://www.codacy.com/app/cornelius-koelbel/privacyidea
    
.. image:: http://issuestats.com/github/privacyidea/privacyidea/badge/pr?style=flat
    :alt: Issue stats
    :target: http://issuestats.com/github/privacyidea/privacyidea

.. image:: http://issuestats.com/github/privacyidea/privacyidea/badge/issue?style=flat
    :alt: Issue stats
    :target: http://issuestats.com/github/privacyidea/privacyidea
    
privacyIDEA is an open solution for strong two-factor authentication like 
OTP tokens, SMS, smartphones or SSH keys.
Using privacyIDEA you can enhance your existing applications like local login 
(PAM, Windows Credential Provider), 
VPN, remote access, SSH connections, access to web sites or web portals with 
a second factor during authentication. Thus boosting the security of your 
existing applications.

privacyIDEA does not bind you to any decision of the authentication
protocol or it does not dictate you where your user information should be
stored. This is achieved by its totally modular architecture.
privacyIDEA is not only open as far as its modular architecture is
concerned. But privacyIDEA is completely licensed under the AGPLv3.

It supports a wide variety of authentication devices like OTP tokens 
(HMAC, HOTP, TOTP, OCRA, mOTP), Yubikey (HOTP, TOTP, AES), FIDO U2F devices 
like Yubikey and Plug-Up, smartphone
Apps like Google Authenticator, FreeOTP, Token2  or TiQR,
SMS, Email, SSH keys, x509 certificates 
and Registration Codes for easy deployment.

privacyIDEA is based on Flask and SQLAlchemy as the python backend. The
web UI is based on angularJS and bootstrap.
A MachineToken design lets you assign tokens to machines. Thus you can use
your Yubikey to unlock LUKS, assign SSH keys to SSH servers or use Offline OTP with PAM.

You may join the Google Group to give feedback, discuss questions and ideas:
https://groups.google.com/forum/#!forum/privacyidea


Setup
=====

For setting up the system to *run* it, please read install instructions 
at http://privacyidea.readthedocs.io.

If you want to setup a development environment start like this::

    git clone https://github.com/privacyidea/privacyidea.git
    cd privacyidea
    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

You may also want to read the blog post about development and debugging at
https://www.privacyidea.org/privacyidea-development-howto/

Getting and updating submodules
===============================

Some authentication modules and the admin client are located in git submodules.
To fetch the latest release of these run::

   git pull --recurse-submodules

Running it
==========

Create the database and encryption key::

    ./pi-manage createdb
    ./pi-manage create_enckey

Create the key for the audit log::

    ./pi-manage create_audit_keys

Create the first administrator::

    ./pi-manage admin add <username>

Run it::

    ./pi-manage runserver

Now you can connect to http://localhost:5000 with your browser and login
as administrator.

Run tests
=========

    nosetests -v --with-coverage --cover-package=privacyidea --cover-html

Contributing
============

You are very welcome to contribute to privacyIDEA:

https://github.com/privacyidea/privacyidea/blob/master/CONTRIBUTING.rst

Code structure
==============

The database models are defined in ``models.py`` and tested in 
tests/test_db_model.py.

Based on the database models there are the libraries ``lib/config.py`` which is
responsible for basic configuration in the database table ``config``.
And the library ``lib/resolver.py`` which provides functions for the database
table ``resolver``. This is tested in tests/test_lib_resolver.py.

Based on the resolver there is the library ``lib/realm.py`` which provides
functions
for the database table ``realm``. Several resolvers are combined into a realm.

Based on the realm there is the library ``lib/user.py`` which provides functions 
for users. There is no database table user, since users are dynamically read 
from the user sources like SQL, LDAP, SCIM or flat files.

Versioning
==========
privacyIDEA adheres to `Semantic Versioning <http://semver.org/>`_.
