connectmfa: Open-Source Multi-Factor Authentication
===================================================

connectmfa is an open-source MFA platform for orchestrating all your multi-factor authentication needs. Secure your entire stack with a flexible, self-hosted solution that puts you in control.

Key Features
------------

* **Universal MFA:** Add a second factor to virtually any application—from SSH and VPNs to IdPs like Keycloak and web portals.
* **Extensive Factor Support:** Go beyond simple OTP with Passkeys, push authentication, and various OTP types.
* **Vendor-Agnostic:** Connect to your existing user stores (AD, LDAP, SQL, EntraID) without being locked into a specific ecosystem.
* **Truly Open:** Licensed under AGPLv3.

Supported Authentication Factors
--------------------------------

* **Passkeys & Hardware:** FIDO2/WebAuthn devices (YubiKey, etc.)
* **Smartcards (PIV/x509):** Certificate enrollment support
* **Software & Mobile:** TOTP, HOTP, PUSH notifications
* **Classic & Remote:** SMS, Email, SSH Keys, Registration Codes

Setup
=====

Development environment::

    git clone <repository-url>
    cd connectmfa
    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

Running it
==========

Create the database and encryption key::

    ./pi-manage create_tables
    ./pi-manage create_enckey

Create audit keys::

    ./pi-manage create_audit_keys

Create the first administrator::

    ./pi-manage admin add <username>

Run the server::

    ./pi-manage run

Connect to http://localhost:5000 with your browser and login as administrator.

Run tests
=========

::

    pip install -r tests/requirements.txt
    python -m pytest -v --cov=privacyidea --cov-report=html tests/

License
=======

AGPLv3
