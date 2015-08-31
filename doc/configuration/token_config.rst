.. _tokens:

Tokens
------

.. toctree::
   tokens/supported.rst

.. _tokentypes:

Supported Tokentypes
.....................

.. index:: token types, Yubico, Yubikey, SMS, SSH Key, registration

At the moment the following tokentypes are supported:

* :ref:`hotp_token` - event base One Time Password tokens based on
  `RFC4225 <https://tools.ietf.org/html/rfc4226>`_.
* :ref:`totp_token` - time based One Time Password tokens based on
  `RFC6238 <https://tools.ietf.org/html/rfc6238>`_.
* mOTP - time based One Time Password tokens for mobile phones based on an
  a `public Algorithm <http://motp.sourceforge.net>`_.
* :ref:`four_eyes` - Meta token that can be used to create a
  `Two Man Rule <https://en.wikipedia.org/wiki/Two-man_rule>`_.
* password - A password token used for :ref:`lost_token` scenario.
* :ref:`registration` - A special token type used for enrollment scenarios (see
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
* :ref:`sms` - A token that sends the OTP value to the mobile phone of the
  user.
* :ref:`email_token` - A token that sends the OTP value to the EMail address of
  the user.
* :ref:`yubico` - A Yubikey hardware that authenticates against the Yubico
  Cloud service.
* :ref:`yubikey` - A Yubikey hardware initialized in the AES mode, that
  authenticates against privacyIDEA.
* Daplug - A hardware OTP token similar to the Yubikey.

The Tokentypes:

.. toctree::
   tokens/4eyes
   tokens/certificate
   tokens/email
   tokens/hotp
   tokens/totp
   tokens/radius
   tokens/registration
   tokens/remote
   tokens/sms
   tokens/sshkey
   tokens/yubico
   tokens/yubikey

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

