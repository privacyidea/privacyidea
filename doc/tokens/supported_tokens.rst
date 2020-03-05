.. _supported_tokens:

Hardware and Software Tokens
................

privacyIDEA supports a wide variety of tokens by different hardware vendors.
It also supports token apps on the smartphone.

Tokens not listed, will be probably supported, too, since most tokens use
standard algorithms.

If in doubt drop your question on the mailing list.

Hardware Tokens
~~~~~~~~~~~~~~~

.. index:: Hardware Tokens

The following hardware tokens are known to work well.

**Yubikey**. The Yubikey is supported in all modes:
AES (:ref:`yubikey_token`),
:ref:`hotp_token`
and :ref:`yubico_token` Cloud.
You can initialize the Yubikey yourself, so that the secret key is not known
to the vendor.

**eToken Pass**. The eToken Pass is a push button token by SafeNet. It can be
initialized with a special hardware device. Or you get a seed file, that you
need to import to privacyIDEA.
The eToken Pass can run as :ref:`hotp_token` or :ref:`totp_token` token.

**eToken NG OTP**. The eToken NG OTP is a push button token by SafeNet. As it
has a USB connector, you can initialize the token via the USB connector. Thus
the hardware vendor does not know the secret key.

**DaPlug**. The DaPlug token is similar to the Yubikey and can be initialized
via the USB connector. The secret key is not known to the hardware vendor.

**Smartdisplayer OTP Card**. This is a push button card. It features an eInk
display, that can be read very good in all light condition at all angles.
The Smartdisplayer OTP card is initialized at the factory and you get a seed
file, that you need to import to privacyIDEA.

**Feitian**. The C100 and C200 tokens are classical, reasonably priced push
button tokens. The C100 is an :ref:`hotp_token` token and the C200 a
:ref:`totp_token` token. These
tokens are initialized at the factory and you get a seed file, that you need
to import to privacyIDEA.

**U2F**. The Yubikey and the Daplug token are known U2F devices to work well
with privacyIDEA. See :ref:`u2f_token`.

Smartphone Apps
~~~~~~~~~~~~~~~

.. index:: Software Tokens

.. _privacyidea_authenticator:

**privacyIDEA Authenticator**. Our own privacyIDEA Authenticator is based
on the concept of the Google Authenticator and works with the usual QR Code key URI
enrollment. But on top it also allows for a more secure
enrollment process (See :ref:`2step_enrollment`).
It can be used for :ref:`hotp_token`, :ref:`totp_token` and :ref:`push_token`.

**Google Authenticator**. The Google Authenticator is working well in
:ref:`hotp_token`
and :ref:`totp_token` mode. If you choose "Generate OTP Key on the Server"
during
enrollment, you can scan a QR Code with the Google Authenticator.
See :ref:`first_steps_token` to learn how to do this.

**FreeOTP**. privacyIDEA is known to work well with the FreeOTP App. The
FreeOTP App is a :ref:`totp_token` token. So if you scan the QR Code of an
HOTP token, the OTP will not validate.

**mOTP**. Several mOTP Apps like "Potato", "Token2" or "DroidOTP" are supported.
