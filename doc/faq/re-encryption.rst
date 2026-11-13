.. _faq_reencryption:

Re-Encrypting data
------------------

You might need to re-encrypt your token data, i.e. the secret OTP keys and the other encrypted data of your tokens.
This may be because you are changing your security module or you think your encryption key is compromised.

privacyIDEA provides tools to reencrypt your token data.

Note that currently we do not reencrypt configuration data like LDAP resolver passwords.

Reencryption is currently done offline. You will have to export your existing tokens and reimport the tokens to
the system with the new security module or encryption key.

This process will only update existing tokens in the new system. It will not create these tokens and it will not change
user assignments.


Export tokens
~~~~~~~~~~~~~

Export the tokens to a YAML file with the :ref:`export <pi-tokenjanitor_export>`
of :ref:`pi-tokenjanitor`:

.. code-block:: bash

    pi-tokenjanitor find export --format yaml --file my-tokens.yaml

The file contains the secret OTP keys of the tokens **unencrypted**, and also
their token info and owner. Keep the file safe.

Error messages are written to stderr, so check them. Do not add ``--b32``. The
update command needs the OTP keys in hex.

Updating tokens
~~~~~~~~~~~~~~~

Now go to the system with the new security module or the new encryption key.
The tokens must already exist on this system. The update does not create
tokens.

Run the :ref:`update command <pi-tokenjanitor_update>` with the exported file::

    pi-tokenjanitor update my-tokens.yaml

This stores the OTP keys and the encrypted token info again, encrypted with the
new key. Error messages are written to stderr, so check them.

The update keeps the fail counter, the token kind, the active state and the
rollout state. It also keeps the OTP counter, or takes the one from the file if
it is higher. So an OTP value that was already used stays invalid. Other token
info, e.g. a TAN list, is not written back.

.. warning:: The PIN of mOTP tokens and PINs that are stored encrypted
   (enrollment policy ``encrypt_pin``) are not re-encrypted. Set these PINs
   again after the key change. Hashed PINs, the default, do not depend on the
   encryption key.

What can possibly go wrong
~~~~~~~~~~~~~~~~~~~~~~~~~~

Tokens with a broken OTP key may fail to export or import. This could e.g. happen if tokens are not fully enrolled.

If a token does not exist in the new system, it will not be updated!

Configuration data is not reencrypted during this process.

Thoughts about the configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We described how you can re-encrypt the token data. Configuration data is not re-encrypted
by the token janitor. To re-encrypt it, export the configuration with
:ref:`pi-manage <pimanage>` on the system with the old encryption key and import it on the
system with the new one::

    pi-manage config export -f yaml -o my-config.yaml
    pi-manage config import -i my-config.yaml

Without ``-t``, all configuration types are exported. Resolvers are only one of the types
that hold secrets: the export also contains the passwords and secrets of SMTP servers,
RADIUS servers, SMS gateways, CA connectors and machine resolvers, and the system settings
of the type password, all of them decrypted. Handle the file with care, and do not add
``--censor``, which replaces the secrets with a placeholder. The import overwrites the
configuration objects with the same name and encrypts their secrets with the new key.
Instead of importing, you can also enter each password again in the configuration of the
new system; this way it is also encrypted with the new key.
