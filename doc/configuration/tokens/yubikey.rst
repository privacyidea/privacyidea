.. _yubikey:

Yubikey
-------

.. index:: Yubikey, Yubico AES mode

The Yubikey is initialized with privacyIDEA and works in Yubicos own AES mode.
It outputs a 44 digit OTP value. But in contrast to the :ref:`yubico` Cloud
mode, in this mode the secret key is contained within the token and your own
privacyIDEA installation.

If you have the time and care about privacy, you should prefer the
Yubikey AES mode over the :ref:`yubico` Cloud mode.

.. figure:: images/enroll_yubikey.png
   :width: 500

   *Enroll a Yubikey AES mode token*

You can use this dialog to enroll a Yubikey AES mode token, if you have
initialized the yubikey with the external *ykpersonalize* tool.

.. note:: However, we recommend that you use the ``privacyidea`` command line
   client, to initialize the Yubikeys. You can use the mass enrollment, which
   eases the process of initializing a whole bunch of tokens.

Run the command like this::

   privacyidea -U https://your.privacyidea.server -a admin token \
   yubikey_mass_enroll --yubimode YUBICO


