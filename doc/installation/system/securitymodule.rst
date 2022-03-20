.. _securitymodule:

Security Modules
================

.. index:: Security Module, Hardware Security Module, HSM

.. note:: For a normal installation this section can be safely ignored.

privacyIDEA provides a security module that takes care of

 * encrypting the token seeds,
 * encrypting passwords from the configuration like the LDAP password,
 * creating random numbers,
 * and hashing values.

.. note:: The Security Module concept can also be used to add a Hardware
   Security Module to perform the above mentioned tasks.

Default Security Module
-----------------------

The ``default`` security module is implemented with the operating systems
capabilities. The encryption key is located in a file *enckey* specified via
``PI_ENCFILE`` in the configuration file (:ref:`cfgfile`).

This *enckey* contains three 32byte keys and is thus 96 bytes. This file
has to be protected. So the access rights to this file are set
accordingly.

In addition you can encrypt this encryption key with an additional password.
In this case, you need to enter the password each time the privacyIDEA server
is restarted and the password for decrypting the *enckey* is kept in memory.

:ref:`pimanage` contains the instruction how to encrypt the *enckey*

After starting the server, you can check, if the encryption key is accessible.
To do so run::

    privacyidea -U <yourserver> --admin=<youradmin> securitymodule

The output will contain ``"is_ready": True`` to signal that the encryption
key is operational.

If it is not yet operational, you need to pass the password to the
privacyIDEA server to decrypt the encryption key.
To do so run::

    privacyidea -U <yourserver> --admin=<youradmin> securitymodule  \
    --module=default

.. note:: If the security module is not operational yet, you might get an
   error message "HSM not ready.".

AES HSM Security Module
-----------------------

The AES Hardware Security Module can be used to encrypt data with an
hardware security module (HSM) connected via the PKCS11
interface. This module allows to use AES keys stored in the HSM to
encrypt and decrypt data.

This module uses three keys, similarly to the content of
``PI_ENCFILE``, identified as ``token``, ``config`` and ``value``.

To activate this module add the following to the configuration file
(:ref:`cfgfile`)

   PI_HSM_MODULE = "privacyidea.lib.security.aeshsm.AESHardwareSecurityModule"

Additional attributes are

``PI_HSM_MODULE_MODULE`` which takes the pkcs11 library. This is the full
specified path to the shared object file in the file system.

``PI_HSM_MODULE_SLOT`` is the slot on the HSM where the keys are
located (default: ``1``).

You can set the slot number to -1 if there is only one slot available and you do
not know the slot number. Then privacyIDEA will determine the one and only slot number and
use this one.


``PI_HSM_MODULE_PASSWORD`` is the password to access the slot.

``PI_HSM_MODULE_MAX_RETRIES`` is the number privacyIDEA tries to perform a cryptographic
operation like *decrypt*, *encrypt* or *random* if the first attempt with the HSM fails.
The default value is 5.

.. note:: Some PKCS11 libraries for network attached HSMs also implement a retry.
   You should take this into account, since retries would multiply and it could take
   a while till a request would finally fail.

``PI_HSM_MODULE_KEY_LABEL`` is the label prefix for the keys on the
HSM (default: ``privacyidea``). In order to locate the keys, the
module will search for key with a label equal to the concatenation of
this prefix, ``_`` and the key identifier (respectively ``token``,
``config`` and ``value``).

``PI_HSM_MODULE_KEY_LABEL_TOKEN`` is the label for ``token`` key
(defaults to value based on ``PI_HSM_MODULE_KEY_LABEL`` setting).

``PI_HSM_MODULE_KEY_LABEL_CONFIG`` is the label for ``config`` key
(defaults to value based on ``PI_HSM_MODULE_KEY_LABEL`` setting).

``PI_HSM_MODULE_KEY_LABEL_VALUE`` is the label for ``value`` key
(defaults to value based on ``PI_HSM_MODULE_KEY_LABEL`` setting).

Encrypt Key Security Module
---------------------------

The Encrypt Key Security Module uses a hardware security module (HSM)
to decrypt the encrypted encryption key. Within the HSM a private RSA key is
used to decrypt an encrypted file like `/etc/privacyidea/enckey.enc`.

With the first request to each process of the privacyIDEA server, the HSM is used
to decrypt the encryption key. After that the encryption key is kept in memory during run time.

To activate this module add the following to the configuration file
(:ref:`cfgfile`)

    PI_HSM_MODULE = "privacyidea.lib.security.encryptkey.EncryptKeyHardwareSecurityModule"

Further attributes are
``PI_HSM_MODULE_MODULE`` which takes the pkcs11 library. This is the fully
specified path to the shared object file in the file system.

``PI_HSM_MODULE_SLOT`` is the slot on the HSM where the keys are
located. This is an integer value.
Alternatively you can specify ``PI_HSM_MODULE_SLOTNAME`` which would be the descriptive name
of this slot.

To use the correct key in this slot you can either specify the key by providing
``PI_HSM_MODULE_KEYID`` with the integer id of the key or
``PI_HSM_MODULE_KEYLABEL``  with the descriptive label of the key.

The ``PI_HSM_MODULE_TIMEOUT`` can be used to define an integer value for a HSM lock timeout.

.. note:: Some HSM fail to provide a correct keyid and it is necessary to use the key label.

The last two mandatory attributes are ``PI_HSM_MODULE_PASSWORD`` which holds the password of the slot
and ``PI_HSM_MODULE_ENCFILE`` which specifies the encrypted encryption key.

You could e.g. use a Yubikey this way::

    PI_HSM_MODULE = "privacyidea.lib.security.encryptkey.EncryptKeyHardwareSecurityModule"
    PI_HSM_MODULE_MODULE = "/usr/lib/libykcs11.so"
    PI_HSM_MODULE_SLOTNAME = "Yubico YubiKey"
    PI_HSM_MODULE_KEYLABEL = 'Private key for PIV Authentication'
    PI_HSM_MODULE_PASSWORD = 'yourPin'
    PI_HSM_MODULE_ENCFILE = "/etc/privacyidea/enckey.enc"

To encrypt an existing key file you can use the module like this::

    python encryptkey.py --module /usr/lib/libykcs11.so --keyid 1 --slotname "Yubico YubiKey"  \
                         --infile enckey --outfile enckey.enc

If your key in the HSM is identified by a key label, then you can encrypt the existing key file like this::

    python encryptkey.py --module /usr/lib/libykcs11.so --keylabel "my secret key" --slotname "Yubico YubiKey" \
                         --infile enckey --outfile enckey.enc

