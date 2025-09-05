.. .. image:: https://circleci.com/gh/privacyidea/privacyidea/tree/master.svg?style=shield&circle-token=:circle-token
..     :alt: CircleCI
..     :target: https://circleci.com/gh/privacyidea/privacyidea

.. image:: https://codecov.io/gh/privacyidea/privacyidea/coverage.svg?branch=master
    :target: https://codecov.io/gh/privacyidea/privacyidea?branch=master

.. .. image:: https://img.shields.io/pypi/dm/privacyidea.svg
..    :alt: Downloads
..    :target: https://pypi.python.org/pypi/privacyIDEA/

.. image:: https://img.shields.io/pypi/v/privacyidea.svg
    :alt: Latest Version
    :target: https://pypi.python.org/pypi/privacyIDEA/#history

.. image:: https://img.shields.io/pypi/pyversions/privacyidea.svg
    :alt: PyPI - Python Version
    :target: https://pypi.python.org/pypi/privacyIDEA/

.. image:: https://img.shields.io/github/license/privacyidea/privacyidea.svg
    :alt: License
    :target: https://pypi.python.org/pypi/privacyIDEA/

.. image:: https://readthedocs.org/projects/privacyidea/badge/?version=master
    :alt: Documentation
    :target: http://privacyidea.readthedocs.org/en/master/

.. .. image:: https://codeclimate.com/github/privacyidea/privacyidea/badges/gpa.svg
..    :alt: Code Climate
..    :target: https://codeclimate.com/github/privacyidea/privacyidea

.. .. image:: https://api.codacy.com/project/badge/grade/d58934978e1a4bcca325f2912ea386ff
    :alt: Codacy Badge
    :target: https://www.codacy.com/app/cornelius-koelbel/privacyidea

privacyIDEA: Open-Source Multi-Factor Authentication
====================================================

privacyIDEA is an open-source MFA platform for orchestrating all your multi-factor authentication needs. Secure your entire stack with a flexible, self-hosted solution that puts you in control. As an on-premise platform, your sensitive user data always remains within your infrastructure.

Key Features
------------

* **Universal MFA:** Add a second factor to virtually any application—from SSH and VPNs to IdPs like Keycloak and web portals.
* **Extensive Factor Support:** Go beyond simple OTP. We support everything from cutting-edge Passkeys and push authentication to various OTP types.
* **Vendor-Agnostic:** Connect to your existing user stores (AD, LDAP, SQL, EntraID) without being locked into a specific ecosystem.
* **Truly Open:** Licensed under AGPLv3 to guarantee your software freedom, always.

Supported Authentication Factors
--------------------------------

* 🔑 **Passkeys & Hardware:** FIDO2/WebAuthn devices (like YubiKey, Plug-Up).
* 💳 **Smartcards (PIV/x509):** Connect to a Microsoft CA using the `ms-ca-service <https://github.com/privacyidea/ms-ca-service>`_ and enroll certificates directly to PIV-compatible devices with our `enrollment client for Windows <https://github.com/privacyidea/smartcard-client-windows>`_.
* 📱 **Software & Mobile:** Use the `privacyIDEA Authenticator <https://github.com/privacyidea/pi-authenticator>`_ for PUSH notifications, TOTP, and HOTP; for standard TOTP/HOTP, other apps like Google Authenticator are also compatible. TiQR is also supported.
* 📜 **Classic & Remote:** SMS, Email, SSH Keys, Security Questionnaires, and simple Registration Codes for easy rollout.

Seamless Integration
--------------------

Enhance the security of your existing infrastructure:

* **Operating Systems:** `Linux (PAM) <https://github.com/privacyidea/privacyidea-pam>`_, `Windows (Credential Provider) <https://github.com/privacyidea/privacyidea-credential-provider>`_
* **Identity Providers:** `Keycloak <https://github.com/privacyidea/keycloak-provider>`_, `ADFS <https://github.com/privacyidea/adfs-provider>`_, `Shibboleth <https://github.com/privacyidea/shibboleth-plugin>`_, `SimpleSAMLphp <https://github.com/privacyidea/simplesamlphp-module-privacyidea>`_
* **Remote Access:** VPNs with RADIUS (OpenVPN, Fortinet, Palo Alto), SSH
* **Web Applications:** Apache, Nginx, any web portal via our REST API.
* `nextCloud <https://github.com/privacyidea/privacyidea-nextcloud-app>`_, `ownCloud <https://github.com/privacyidea/privacyidea-owncloud-app>`_
* **and more...**

----

Join the Community
------------------

Have feedback, questions, or ideas? Join the discussion on our community forum:
https://community.privacyidea.org

Setup
=====

For setting up the system to *run* it, please read install instructions
at `privacyidea.readthedocs.io <http://privacyidea.readthedocs.io/en/latest/installation/index
.html>`_.

If you want to setup a development environment start like this::

    git clone https://github.com/privacyidea/privacyidea.git
    cd privacyidea
    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

.. _testing_env:

You may additionally want to set up your environment for testing, by adding the
additional dependencies::

    pip install -r tests/requirements.txt

You may also want to read the blog post about development and debugging at
https://www.privacyidea.org/privacyidea-development-howto/

Running it
==========

First You need to create a `config-file <https://privacyidea.readthedocs
.io/en/latest/installation/system/inifile.html>`_.

Then create the database tables and the encryption key::

    ./pi-manage create_tables
    ./pi-manage create_enckey

If You want to keep the development database upgradable, You should `stamp
<https://privacyidea.readthedocs.io/en/latest/installation/upgrade.html>`_ it
to simplify updates::

    ./pi-manage db stamp head -d migrations/

Create the key for the audit log::

    ./pi-manage create_audit_keys

Create the first administrator::

    ./pi-manage admin add <username>

Run it::

    ./pi-manage run

Now you can connect to http://localhost:5000 with your browser and login
as administrator.

Run tests
=========

If you have followed the steps above to set up your
`environment for testing <#testing-env>`__, running the test suite should be as
easy as running `pytest <http://pytest.org/>`_ with the following options::

    python -m pytest -v --cov=privacyidea --cov-report=html tests/

Contributing
============

There are a lot of different ways to contribute to privacyIDEA, even
if you are not a developer.

If you found a security vulnerability please report it to
security@privacyidea.org.

You can find detailed information about contributing here:
https://github.com/privacyidea/privacyidea/blob/master/CONTRIBUTING.md

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

Subscriptions and limitations of community edition
==================================================

Using privacyIDEA Server and the privacyIDEA FreeRADIUS plugin there is technically no
limitation of the community edition or the code in this repository.
Admins will receive a welcome message about possible support, if more than 50 users
are enrolled.

Plugins
-------

The privacyIDEA project also provides several plugins for 3rd party applications like SSO Identity Providers
or Windows Login.

Plugins can be limited in the number of users. I.e. the plugin will complain, if the total number of users
in privacyIDEA with an active token exceeds a certain limit. There is a certain base number of users, with which
the plugin will work. To enhance this number, you will need a subscription. In some cases an additional
demo subscription can be found in the release list of the corresponding github plugin repository,
you can get a subscription from the company NetKnights
or if you have a very good understanding of this Open Source code, you could create a subscription on your own.

====================  ==============  ========================
Plugin                Number of users
--------------------  ----------------------------------------
Name                  contained       in demo subscription
====================  ==============  ========================
Keycloak              10000           N/A
SimpleSAMLphp         10000           N/A
Shibboleth            10000           N/A
ADFS                  50              50
privacyIDEA PAM       10000           N/A
Credential Provider   50              50
nextCloud              50              N/A
ownCloud              50              N/A
LDAP proxy            50              N/A
====================  ==============  ========================

Versioning
==========
privacyIDEA adheres to `Semantic Versioning <http://semver.org/>`_.
