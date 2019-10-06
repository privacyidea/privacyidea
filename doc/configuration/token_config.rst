.. _tokens:

Tokens
------

.. toctree::
   supported_tokens.rst
   authentication_modes.rst

.. _tokentypes:

Supported Tokentypes
.....................

.. index:: token types, Yubico, Yubikey, SMS, SSH Key, registration, TiQR

At the moment the following tokentypes are supported:

* :ref:`hotp_token` - event based One Time Password tokens based on
  `RFC4225 <https://tools.ietf.org/html/rfc4226>`_.
* :ref:`totp_token` - time based One Time Password tokens based on
  `RFC6238 <https://tools.ietf.org/html/rfc6238>`_.
* :ref:`push_token` - A challenge response token, that sends a
  challenge to the user's smartphone and the user simply accepts the
  request to login.
* mOTP - time based One Time Password tokens for mobile phones based on an
  a `public Algorithm <http://motp.sourceforge.net>`_.
* :ref:`paper_token` - event based One Time Password tokens that get
  you list of one time passwords on a sheet of paper.
* :ref:`questionnaire_token` - A token that contains a list of answered
  questions. During authentication a random question is presented as
  challenge from the list of answered questions is presented. The user must
  give the right answer.
* :ref:`email_token` - A token that sends the OTP value to the EMail address of
  the user.
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
* :ref:`spass` - The simple pass token. A token that has no OTP component and
  just consists of the OTP pin or (if otppin=userstore is set) of the userstore
  password.
* :ref:`tiqr` - A Smartphone token that can be used to login by only scanning
  a QR code.
* :ref:`ocra` - A basic OATH Challenge Response token.
* :ref:`u2f` - A U2F device as specified by the FIDO Alliance. This is a USB
  device to be used for challenge response authentication.
* :ref:`vasco` - The proprietary VASCO token.
* :ref:`yubico` - A Yubikey hardware that authenticates against the Yubico
  Cloud service.
* :ref:`yubikey` - A Yubikey hardware initialized in the AES mode, that
  authenticates against privacyIDEA.
* Daplug - A hardware OTP token similar to the Yubikey.


The Tokentypes:

.. toctree::
   :glob:
   :maxdepth: 1

   tokens/*

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
   :glob:
   :maxdepth: 1

   tokenconfig/*
