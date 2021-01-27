.. _yubikey_token:

Yubikey
-------

.. index:: Yubikey, Yubico AES mode

As Yubikey token type, privacyIDEA refers to Yubico's own AES mode.
A Yubikey, configured in this mode
outputs a 44 character OTP value, consisting of a 12 character prefix and
a 32 character OTP. But in contrast to the :ref:`yubico_token` Cloud
mode, in this mode the secret key is contained within the token and your own
privacyIDEA installation.
If you have the time and care about privacy, you should prefer the
Yubikey AES mode over the :ref:`yubico_token` Cloud mode.

There are several possible ways to enroll a Yubikey token in privacyIDEA.
We describe the methods in :ref:`yubikey_enrollment_tools`.

Redirect API URLs to /ttype/yubikey
...................................

To have a service query not the Yubico Cloud URL, but the privacyIDEA
endpoint ``/ttype/yubikey``, you sometimes need to redirect the default
API URL via the local webserver.
Yubico servers use ``/wsapi/2.0/verify`` as the path in the
validation URL. Some tools (e.g. Kolab 2FA) let the
user/admin change the API host, but not the rest of
the URL. To redirect the API URL to privacyIDEA's endpoint
``/ttype/yubikey``, you'll need to enable the following two
lines in ``/etc/apache2/site-enabled/privacyidea.conf``::

    RewriteEngine  on
    RewriteRule    "^/wsapi/2.0/verify"  "/ttype/yubikey" [PT]

If you use nginx there is a similar line provided as a comment
to the nginx configuration as well.

.. rubric:: Footnotes

.. [#ykotp] https://developers.yubico.com/OTP/OTPs_Explained.html
