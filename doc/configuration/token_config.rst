.. _tokens:

Tokens
------

.. _tokentypes:

Supported Tokentypes
.....................

.. index:: token types, Yubico, Yubikey, SMS, SSH Key, registration

At the moment the following tokentypes are supported:

* HOTP - event base One Time Password tokens based on
  `RFC4225 <https://tools.ietf.org/html/rfc4226>`_.
* TOTP - time based One Time Password tokens based on
  `RFC6238 <https://tools.ietf.org/html/rfc6238>`_.
* mOTP - time based One Time Password tokens for mobile phones based on an
  a `public Algorithm <http://motp.sourceforge.net>`_.
* password - A password token used for :ref:`lost_token` scenario.
* registration - A special token type used for enrollment scenarios (see
  :ref:`faq_registration_code`).
* Simple Pass - A token that only consists of the Token PIN.
* :ref:`certificates` - A token that represents a client
  certificate.
* :ref:`sshkey` - An SSH public key that can be managed and used in conjunction
  with the :ref:`machines` concept.
* :ref:`remote` - A virtual token that forwards the authentication request to
  another privacyIDEA server.
* :ref:`radius` - A virtual token that forwards the authentication request to
  a RADIUS server.
* SMS - A token that sends the OTP value to the mobile phone of the user.
* EMail - A token that sends the OTP value to the EMail address of the user.
* Yubico Cloud mode - A Yubikey hardware that authenticates against the Yubico
  Cloud service.
* Yubikey AES mode - A Yubikey hardware initialized in the AES mode, that
  authenticates against privacyIDEA.

The Tokentypes:

.. toctree::
   tokens/certificate
   tokens/radius
   tokens/remote
   tokens/sshkey



.. _token_config:

Token configuration
....................

.. index:: token configuration

Each token type can provide its own configuration dialog.

In this configuration dialog you can define default values for these token
types.

.. figure:: images/token-config.png
   :width: 500

   *Token Configuration: SMS*

.. toctree::
   tokenconfig/email
   tokenconfig/sms
   tokenconfig/yubico

