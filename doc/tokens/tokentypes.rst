.. _token_overview:
.. _tokentypes:

Token types in privacyIDEA
--------------------------

.. index:: token types, Yubico, YubiKey, SMS, SSH Key, registration, TiQR

The following list is an overview of the supported token types.
For more details, consult the respective description listed in :ref:`tokens`.
Some tokens require prior configuration as described in :ref:`tokentypes_details`.

* :ref:`passkey` - A FIDO2 credential that is tied to an application or domain. Allows easy use via fingerprint, face scan, or PIN.
* :ref:`four_eyes_token` - Meta token that can be used to create a
  `Two Man Rule <https://en.wikipedia.org/wiki/Two-man_rule>`_.
* :ref:`certificate_token` - A token that represents a client
  certificate.
* :ref:`daypassword_token` - The DayPassword Token is a time based password
  loosely based on the TOTP algorithm which can be used multiple times.
* :ref:`email_token` - A token that sends the OTP value to the email address of
  the user.
* :ref:`hotp_token` - event based One Time Password tokens based on
  `RFC4226 <https://www.rfc-editor.org/rfc/rfc4226>`_.
* :ref:`indexedsecret_token` - a challenge response token that asks the user for random positions
  from a secret string.
* Daplug - Legacy hardware OTP token similar to the YubiKey.
* :ref:`motp_token` - time based One Time Password tokens for mobile phones based on a
  `public algorithm <https://motp.sourceforge.net/>`_.
* :ref:`ocra_token` - A basic OATH Challenge Response token.
* :ref:`paper_token` - event based One Time Password tokens that give
  you a list of one-time passwords on a sheet of paper.
* :ref:`push_token` - A challenge response token, that sends a
  challenge to the user's smartphone and the user simply accepts the
  request to log in.
* :ref:`pw_token` - A password token used for :ref:`lost_token` scenario.
* :ref:`application_specific_token` - This is an application specific password token based on the :ref:`pw_token`.
  It can be used to provide a static password for specific services or applications, where e.g. one time passwords
  are not suitable.
* :ref:`questionnaire_token` - A token that contains a list of answered
  questions. During authentication a random question from the list of answered
  questions is presented as challenge. The user must give the right answer.
* :ref:`registration_token` - A special token type used for enrollment scenarios (see
  :ref:`faq_registration_code`).
* :ref:`radius_token` - A virtual token that forwards the authentication request to
  a RADIUS server.
* :ref:`remote_token` - A virtual token that forwards the authentication request to
  another privacyIDEA server.
* :ref:`sms_token` - A token that sends the OTP value to the mobile phone of the
  user.
* :ref:`spass_token` - The simple pass token. A token that has no OTP component and
  just consists of the OTP pin or (if otppin=userstore is set) of the userstore
  password.
* :ref:`sshkey_token` - An SSH public key that can be managed and used in conjunction
  with the :ref:`machines` concept.
* :ref:`tan_token` - A list of TANs that can be used in any order.
* :ref:`tiqr_token` - A smartphone token that can be used to log in by only scanning
  a QR code.
* :ref:`totp_token` - time based One Time Password tokens based on
  `RFC6238 <https://www.rfc-editor.org/rfc/rfc6238>`_.
* :ref:`vasco_token` - The proprietary OneSpan (formerly VASCO) token.
* :ref:`webauthn` - The WebAuthn or FIDO2 token which can use several different mechanisms like
  USB tokens or TPMs to authenticate via public key cryptography.
* :ref:`yubikey_token` - A YubiKey hardware token initialized in AES mode, that
  authenticates against privacyIDEA.
* :ref:`yubico_token` - A YubiKey hardware token that authenticates against the Yubico
  Cloud service.

.. _tokentypes_details:

Token type details
.....................

Detailed information on the different token types used in privacyIDEA can
be found in the following sections.

.. toctree::
   :glob:
   :maxdepth: 1

   tokentypes/*
