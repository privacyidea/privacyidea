.. _container_types:

Container Types
...............

The following list is an overview of the supported container types.

* **Generic** - A generic container can contain arbitrary token types. It is the base class which all other container
  types inherit from.
* **Smartphone** - A smartphone can contain :ref:`hotp_token`, :ref:`totp_token`, :ref:`push_token`,
  :ref:`daypassword_token`, and :ref:`sms_token` tokens.
* **Yubikey** - A Yubikey can contain :ref:`hotp_token`, :ref:`certificate_token`, :ref:`yubikey_token`,
  :ref:`yubico_token`, :ref:`webauthn`, and :ref:`passkey` tokens.
