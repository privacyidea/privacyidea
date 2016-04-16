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

PKCS11 Security Module
-----------------------

The PKCS11 Security Module can be used to encrypt data with an hardware
security module, that is connected via the PKCS11 interface. To encrypt and
decrypt data you can use an RSA key pair that is stored on the HSM.

To activate this module add the following to the configuration file
(:ref:`cfgfile`)

   PI_HSM_MODULE = "privacyidea.lib.security.pkcs11.PKCS11SecurityModule"

Additional attributes are

``PI_HSM_MODULE_MODULE`` which takes the pkcs11 library. This is the full
specified path to the shared object file in the file system.

``PI_HSM_MODULE_KEY_ID`` is the key id (integer) on the HSM.
