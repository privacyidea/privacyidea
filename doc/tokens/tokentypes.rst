.. _token_overview:
.. _tokentypes:

Token types in privacyIDEA
--------------------

.. index:: token types, Yubico, Yubikey, SMS, SSH Key, registration, TiQR

The following list is an overview of the supported token types.
For more details, consult the respective description listed in :ref:`tokens`.
Some token require prior configuration as described in :ref:`tokentypes_details`.

* :ref:`four_eyes_token` - Meta token that can be used to create a
  `Two Man Rule <https://en.wikipedia.org/wiki/Two-man_rule>`_.
* :ref:`certificate_token` - A token that represents a client
  certificate.
* :ref:`email_token` - A token that sends the OTP value to the EMail address of
  the user.
* :ref:`hotp_token` - event based One Time Password tokens based on
  `RFC4226 <https://tools.ietf.org/html/rfc4226>`_.
* :ref:`indexedsecret_token` - a challenge response token that asks the user for random positions
  from a secret string.
* Daplug - A hardware OTP token similar to the Yubikey.
* :ref:`motp_token` - time based One Time Password tokens for mobile phones based on an
  a `public Algorithm <http://motp.sourceforge.net>`_.
* :ref:`ocra_token` - A basic OATH Challenge Response token.
* :ref:`paper_token` - event based One Time Password tokens that get
  you list of one time passwords on a sheet of paper.
* :ref:`push_token` - A challenge response token, that sends a
  challenge to the user's smartphone and the user simply accepts the
  request to login.
* :ref:`pw_token` - A password token used for :ref:`lost_token` scenario.
* :ref:`questionnaire_token` - A token that contains a list of answered
  questions. During authentication a random question is presented as
  challenge from the list of answered questions is presented. The user must
  give the right answer.
* :ref:`registration_token` - A special token type used for enrollment scenarios (see
  :ref:`faq_registration_code`).
* :ref:`radius_token` - A virtual token that forwards the authentication request to
  a RADIUS server.
* registration
* :ref:`remote_token` - A virtual token that forwards the authentication request to
  another privacyIDEA server.
* :ref:`sms_token` - A token that sends the OTP value to the mobile phone of the
  user.
* :ref:`spass_token` - The simple pass token. A token that has no OTP component and
  just consists of the OTP pin or (if otppin=userstore is set) of the userstore
  password.
* :ref:`sshkey_token` - An SSH public key that can be managed and used in conjunction
  with the :ref:`machines` concept.
* :ref:`tan_token` -
* :ref:`tiqr_token` - A Smartphone token that can be used to login by only scanning
  a QR code.
* :ref:`totp_token` - time based One Time Password tokens based on
  `RFC6238 <https://tools.ietf.org/html/rfc6238>`_.
* :ref:`u2f_token` - A U2F device as specified by the FIDO Alliance. This is a USB
  device to be used for challenge response authentication.
* :ref:`vasco_token` - The proprietary VASCO token.
* :ref:`webauthn` - The WebAuthn or FIDO2 token which can use several different mechanisms like
  USB tokens or TPMs to authenticate via public key cryptography.
* :ref:`yubikey_token` - A Yubikey hardware initialized in the AES mode, that
  authenticates against privacyIDEA.
* :ref:`yubico_token` - A Yubikey hardware that authenticates against the Yubico
  Cloud service.

.. todo:: *Simple Pass* removed from Token list. Spass duplicate.

.. _tokentypes_details:

Token type details
.....................

Detailed information on the different token types used in privacyIDEA can
be found in the following sections.

.. toctree::
   :glob:
   :maxdepth: 1

   tokentypes/*