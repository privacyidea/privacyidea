
.. _yubikey_token_config:

YubiKey AES mode
................

.. index:: YubiKey AES mode

The YubiKey AES mode uses the same kind of token as the Yubico Cloud service
but validates the OTP in your local privacyIDEA server. So the secrets
stay local to your system and are not stored in Yubico's Cloud service.

.. figure:: images/yubikey.png
   :width: 500

   *Configure the YubiKey AES mode*

You can have more than one Client with a Client ID connect to your server.
The Client ID starts with ``yubikey.apiid.`` and is followed by the API ID,
which you'll need to configure your clients.
If you check *Generate API Key* and click *Add*, a new API key is generated for that specific
Client ID. The API key is used to sign the validation request sent to the
server and the server signs the answer too. That way, tampering or
MITM attacks might be detected. It is possible to validate tokens without
the API key, but then the request and answer can't be verified against
the key. It is useful to use *HTTPS* for your validation requests, but
this is another kind of protection.

OTP validation can either use the privacyIDEA API ``/validate/check`` or
the YubiKey validation protocol ``/ttype/yubikey`` or - if enabled in
your web server configuration - ``/wsapi/2.0/verify``.

More information about the YubiKey OTPs can be found at `developers.yubico.com`_

.. _developers.yubico.com: https://developers.yubico.com/OTP/OTPs_Explained.html
