.. _tokens:

Tokens
------

.. _tokentypes:

Supported Tokentypes
.....................

.. index:: token types, Yubico, Yubikey, SMS, SSH Key, registration

At the moment the following tokentypes are supported:

* HOTP
* TOTP
* mOTP
* password
* registration
* Simple Pass
* Certificate
* SSH Key
* Remote
* RADIUS
* SMS
* EMail
* Yubico Cloud mode
* Yubikey AES mode


.. _token_config:

Token configuration
....................

.. index:: token configuration

Each token type can provide its own configuration dialog.

.. figure:: images/token-config.png
   :width: 500

   *Token Configuration: SMS*

.. toctree::
   tokenconfig/sms
   tokenconfig/email
