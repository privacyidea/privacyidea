
.. _yubico_token_config:

Yubico Cloud mode
.................

.. index:: Yubico Cloud mode

The Yubico Cloud mode sends the One Time Password emitted by the yubikey to
the Yubico Cloud service or another (possibly self hosted) validation server.

.. figure:: images/yubico.png
   :width: 500

   *Configure the Yubico Cloud mode*

To contact the Yubico Cloud service you need to get an API key and a Client
ID from Yubico and enter these here in the config dialog. In that case you
can leave the Yubico URL blank and privacyidea will use the Yubico servers.

You can use another validation host, e.g. a self hosted validation server.
If you use privacyidea token type yubikey, you can use the URL
https://<privacyideaserver>/ttype/yubikey, other validation servers might
use https://<validationserver>/wsapi/2.0/verify. You'll get the Client ID
and API key from the configuration of your validation server.

You can get your own API key at [#yubico]_.

.. [#yubico] https://upgrade.yubico.com/getapikey/.

