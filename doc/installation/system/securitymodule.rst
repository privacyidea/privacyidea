.. _securitymodule:

Security Modules
================

.. index:: Security Module, Hardware Security Module, HSM

.. note:: For a normal installation this section can be safely ignored.

privacyIDEA provides a security module that takes care of

 * encrypting the token seeds,
 * encrypting passwords from the configuration like the LDAP password,
 * and creating random numbers.

.. note:: The Security Module concept can also be used to add a Hardware
   Security Module to perform the above mentioned tasks.

.. note:: The hardware security modules below (*AES HSM* and *Encrypt Key*)
   need the Python package ``PyKCS11`` and the PKCS#11 library of your HSM
   vendor. The Ubuntu packages and the Docker image do not contain ``PyKCS11``.
   Install it into the virtual environment of privacyIDEA
   (``pip install PyKCS11``, or ``pip install "privacyidea[hsm]"`` for an
   :ref:`installation from PyPI <pip_install>`). Without it, setting up the
   module fails with ``NameError: name 'PyKCS11' is not defined``.

Default Security Module
-----------------------

The ``default`` security module is implemented with the operating systems
capabilities. The encryption key is located in a file *enckey* specified via
``PI_ENCFILE`` in (:ref:`cfgfile`).

This *enckey* contains three 32-byte keys and is thus 96 bytes. This file
has to be protected. So the access rights to this file are set
accordingly.

In addition you can encrypt this encryption key with an additional password.
In this case, you need to enter the password each time the privacyIDEA server
is restarted. The server process then keeps the decrypted keys in memory, not
the password.

:ref:`pimanage` contains the instruction how to encrypt the *enckey*

After starting the server, you can check, if the encryption key is accessible.
To do so run::

    privacyidea -U <yourserver> --admin=<youradmin> securitymodule status

``privacyidea`` is the command line client from the privacyideaadm package
[#privacyideaadm]_. It calls the endpoint ``GET /system/hsm``.
The output will contain ``"is_ready": True`` to signal that the encryption
key is operational.

If it is not yet operational, you need to pass the password to the
privacyIDEA server to decrypt the encryption key.
To do so run the following command, which asks for the password and sends it
with ``POST /system/hsm``::

    privacyidea -U <yourserver> --admin=<youradmin> securitymodule init

.. note:: Each server process has its own security module. The password
   unlocks only the process that receives the ``POST /system/hsm`` request, and
   ``GET /system/hsm`` reports only the state of the process that answers it.
   With several worker processes - e.g. uwsgi in the nginx setup of the Ubuntu
   packages, or the gunicorn workers of the Docker image - every worker needs
   the password separately, and a worker that is restarted or recycled starts
   locked again. An encrypted *enckey* is therefore only practical with a
   single, long-lived server process, such as the Apache setup of the Ubuntu
   packages. With several workers, use an unencrypted *enckey* protected by its
   file permissions, or a hardware security module with the password in
   *pi.cfg*.

.. note:: While the security module is not operational, every request that
   needs the encryption keys fails with the error ``ERR707: hsm not ready!``.

AES HSM Security Module
-----------------------

The AES Hardware Security Module can be used to encrypt data with a
hardware security module (HSM) connected via the PKCS11
interface. This module uses AES keys stored in the HSM to
encrypt and decrypt data.

This module uses three keys, similarly to the content of
``PI_ENCFILE``, identified as ``token``, ``config`` and ``value``.

To activate this module add the following to the configuration file
(:ref:`cfgfile`)::

   PI_HSM_MODULE = "privacyidea.lib.security.aeshsm.AESHardwareSecurityModule"

Create the three keys with ``pi-manage config hsm create_keys`` (see
:ref:`pimanage`). The command uses the module, slot and password set in
*pi.cfg* (``PI_HSM_MODULE``, ``PI_HSM_MODULE_MODULE``, ``PI_HSM_MODULE_SLOT``,
``PI_HSM_MODULE_PASSWORD``), so the password has to be set there while you
create the keys. It creates the keys with new labels (``token_``, ``config_``
and ``value_`` followed by a random string) and prints the lines
``PI_HSM_MODULE_KEY_LABEL_TOKEN``, ``PI_HSM_MODULE_KEY_LABEL_CONFIG`` and
``PI_HSM_MODULE_KEY_LABEL_VALUE``. Add them to *pi.cfg*: the keys do not have
the default labels described below.

Additional attributes are

``PI_HSM_MODULE_MODULE`` which takes the pkcs11 library. This is the fully
specified path to the shared object file in the file system.

``PI_HSM_MODULE_SLOT`` is the slot on the HSM where the keys are
located (default: ``1``).

You can set the slot number to -1 if there is only one slot available and you do
not know the slot number. Then privacyIDEA will determine the one and only slot number and
use this one.


``PI_HSM_MODULE_PASSWORD`` is the password to access the slot. If it is not set,
the module starts without access to the keys and waits for the password like an
encrypted *enckey*: send it with ``POST /system/hsm`` (see *Default Security
Module* above). As there, the password unlocks only the server process that
receives it.

``PI_HSM_MODULE_MAX_RETRIES`` is the number of times privacyIDEA retries a cryptographic
operation like *decrypt*, *encrypt* or *random* after the PKCS11 library reported that the
session is no longer valid (``CKR_SESSION_HANDLE_INVALID``). Before each retry, privacyIDEA
initializes the PKCS11 library again and logs in to the slot. Other errors are not retried.
The default value is 5.

.. note:: Some PKCS11 libraries for network attached HSMs also implement a retry.
   If such a library reports a lost session, the retries multiply, and it could take
   a while till a request finally fails.

``PI_HSM_MODULE_KEY_LABEL`` is the label prefix for the keys on the
HSM (default: ``privacyidea``). In order to locate the keys, the
module will search for a key with a label equal to the concatenation of
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
used to decrypt an encrypted file like ``/etc/privacyidea/enckey.enc``.

With the first request to each process of the privacyIDEA server, the HSM is used
to decrypt the encryption key. After that the encryption key is kept in memory during run time.

To activate this module add the following to :ref:`cfgfile`::

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

The ``PI_HSM_MODULE_TIMEOUT`` can be used to define an integer value for a HSM lock timeout. The default is 15 seconds.

Using the key ``PI_HSM_MODULE_LOCK_DIR`` you can define a different locking directory.
The default is ``/dev/shm/pilock/``. Note, that the locking directory is created or removed by privacyIDEA
when acquiring or releasing the lock on the HSM and you must not create this directory manually!

.. note:: Some HSMs fail to provide a correct keyid and it is necessary to use the key label.

The last two mandatory attributes are ``PI_HSM_MODULE_PASSWORD`` which holds the password of the slot
and ``PI_HSM_MODULE_ENCFILE`` which specifies the encrypted encryption key.

You could e.g. use a YubiKey this way::

    PI_HSM_MODULE = "privacyidea.lib.security.encryptkey.EncryptKeyHardwareSecurityModule"
    PI_HSM_MODULE_MODULE = "/usr/lib/libykcs11.so"
    PI_HSM_MODULE_SLOTNAME = "Yubico YubiKey"
    PI_HSM_MODULE_KEYLABEL = 'Private key for PIV Authentication'
    PI_HSM_MODULE_PASSWORD = 'yourPin'
    PI_HSM_MODULE_ENCFILE = "/etc/privacyidea/enckey.enc"

To encrypt an existing key file you can run the module within the privacyIDEA
virtual environment like this::

    python -m privacyidea.lib.security.encryptkey --module /usr/lib/libykcs11.so --keyid 1 --slotname "Yubico YubiKey"  \
                         --infile enckey --outfile enckey.enc

If your key in the HSM is identified by a key label, then you can encrypt the existing key file like this::

    python -m privacyidea.lib.security.encryptkey --module /usr/lib/libykcs11.so --keylabel "my secret key" --slotname "Yubico YubiKey" \
                         --infile enckey --outfile enckey.enc

Preloading of encryption keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This security module allows you to preload the encryption keys. I.e. privacyIDEA can use the HSM to decrypt
the keys before the first request is sent to privacyIDEA. To do so, you need to modify :ref:`wsgiscript`
and add the parameter ``initialize_hsm``::

    application = create_app(config_name="production",
                             config_file="/etc/privacyidea/pi.cfg", initialize_hsm=True)

Moreover, you need to add the ``WSGIImportScript`` statement to your Apache2 configuration::

    WSGIApplicationGroup %{GLOBAL}
    WSGIImportScript /etc/privacyidea/privacyideaapp.wsgi process-group=privacyidea application-group=%{GLOBAL}

The Docker image has no WSGI script to change. There, set ``PI_INITIALIZE_HSM = True`` in *pi.cfg* or the
environment variable ``PRIVACYIDEA_PI_INITIALIZE_HSM=true``; each worker then sets up the security module when it
starts. The image does not contain ``PyKCS11`` (see above), so this needs an image that adds it.

.. note:: Please note, that this security module uses a lock file, to handle concurrent access to the HSM.
   In certain cases of errors the lock directory could remain and not be cleaned up.
   Ensure, that the directory ``/dev/shm/pilock/`` does *not* exist at Apache2 startup.

.. rubric:: Footnotes

.. [#privacyideaadm] https://github.com/privacyidea/privacyideaadm/
