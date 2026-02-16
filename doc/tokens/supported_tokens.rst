.. _supported_tokens:

Hardware and Software Tokens
............................

privacyIDEA supports a wide variety of tokens by different hardware vendors.
It also supports token apps on smartphones which handle software tokens.

Tokens not listed below are likely supported as well, provided they use
standard algorithms (like HOTP, TOTP, or FIDO2/WebAuthn).

Hardware Tokens
~~~~~~~~~~~~~~~

.. index:: Hardware Tokens

.. _fido_device_matrix:

FIDO2 & WebAuthn Devices
========================

FIDO2 (WebAuthn) is the modern standard for secure authentication. privacyIDEA works
with any standard-compliant FIDO2 device. The following devices are known to be
compatible and frequently used with the software.

.. list-table:: Known Compatible FIDO2 Devices
   :widths: 20 30 50
   :header-rows: 1

   * - Manufacturer
     - Supported Series
     - Specific Models (Searchable)
   * - **Yubico**
     - YubiKey 5 Series, Bio Series, Security Key Series, FIPS Series
     - YubiKey 5 NFC, YubiKey 5C NFC, YubiKey 5Ci, YubiKey 5 Nano/5C Nano, YubiKey Bio, Security Key C NFC
   * - **Google**
     - Titan Security Keys
     - Titan Security Key (USB-A/NFC), Titan Security Key (USB-C/NFC)
   * - **Feitian**
     - ePass, BioPass, iePass
     - ePass K9, ePass K40, BioPass K26/K27, iePass K44, AllinPass FIDO2
   * - **Nitrokey**
     - Nitrokey 3, FIDO2
     - Nitrokey 3A NFC, Nitrokey 3C NFC, Nitrokey FIDO2
   * - **Swissbit**
     - iShield Series
   * - **SoloKeys**
     - Solo V2, Solo Tap
     - Solo V2, Solo Tap USB-A/USB-C, Somu
   * - **Token2**
     - T2F2, PIN+
     - T2F2 NFC, T2F2 USB-C, Token2 PIN+
   * - **Kensington**
     - VeriMark
     - VeriMark Guard, VeriMark IT
   * - **Thetis**
     - FIDO2 Series
     - Thetis FIDO2 Security Key, Thetis Pro FIDO2

.. note::
   While privacyIDEA supports the standard CTAP2 protocol used by most FIDO2 devices,
   specific "manage" features (such as resident credential management or bio-enrollment)
   depend on the specific device firmware capabilities.

Classic Hardware Tokens
=======================

The following classic hardware tokens (OTP, HOTP, TOTP) are also known to work well.

**YubiKey**
    The YubiKey is supported in all modes: AES (:ref:`yubikey_token`),
    :ref:`hotp_token` and :ref:`yubico_token` Cloud.
    You can initialize the YubiKey yourself, so that the secret key is not known
    to the vendor. The process is described in :ref:`yubikey_enrollment_tools`.

**eToken Pass**
    The eToken Pass is a push button token by SafeNet. It can be
    initialized with a special hardware device. Or you get a seed file, that you
    need to import to privacyIDEA.
    The eToken Pass can run as :ref:`hotp_token` or :ref:`totp_token` token.

**eToken NG OTP**
    The eToken NG OTP is a push button token by SafeNet. As it
    has a USB connector, you can initialize the token via the USB connector. Thus
    the hardware vendor does not know the secret key.

**DaPlug**
    The DaPlug token is similar to the YubiKey and can be initialized
    via the USB connector. The secret key is not known to the hardware vendor.

**Smartdisplayer OTP Card**
    This is a push button card. It features an eInk
    display that can be read very well in all light conditions and angles.
    The Smartdisplayer OTP card is initialized at the factory and you get a seed
    file that you need to import to privacyIDEA.

**Feitian (Legacy)**
    The C100 and C200 tokens are classical, reasonably priced push
    button tokens. The C100 is an :ref:`hotp_token` token and the C200 a
    :ref:`totp_token` token. These tokens are initialized at the factory and
    you get a seed file that you need to import to privacyIDEA.

Smartphone Apps
~~~~~~~~~~~~~~~

.. index:: Software Tokens

.. _privacyidea_authenticator:

**privacyIDEA Authenticator**
    Our own privacyIDEA Authenticator is based on the concept of the Google
    Authenticator and works with the usual QR Code key URI enrollment. But on top
    it also allows for a more secure enrollment process (See :ref:`2step_enrollment`).
    It can be used for :ref:`hotp_token`, :ref:`totp_token` and :ref:`push_token`.

**Google Authenticator**
    The Google Authenticator is working well in :ref:`hotp_token`
    and :ref:`totp_token` mode. If you choose "Generate OTP Key on the Server"
    during enrollment, you can scan a QR Code with the Google Authenticator.
    See :ref:`first_steps_token` to learn how to do this.

**FreeOTP**
    privacyIDEA is known to work well with the FreeOTP App. The
    FreeOTP App is a :ref:`totp_token` token. So if you scan the QR Code of an
    HOTP token, the OTP will not validate.

**mOTP**
    Several mOTP Apps like "Potato", "Token2" or "DroidOTP" are supported.