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

Use the :ref:`token_janitor` to export the tokens to a YAML file. This file contains the **unencrypted** secret keys
of the tokens and also the tokeninfos of the tokens.

You need to handle this file with care!

.. code-block:: bash

    privacyidea-token-janitor find --action export --yaml > my-tokens.yaml

The tokens are written to stdout, error messages to stderr. Check for error messages!
Do not add ``--b32``, the update command expects the OTP keys in hex.

Updating tokens
~~~~~~~~~~~~~~~

You can then turn to the system with the new security module or encryption key.
Note that the new privacyIDEA system actually has to contain the tokens!

Use the :ref:`update command <token_janitor_update>` to store the secret OTP keys and the encrypted token info with
the new encryption mechanism::

    privacyidea-token-janitor update my-tokens.yaml

Check for error messages written to stderr!

The update keeps the OTP counter, the fail counter, the token kind, the active state and the rollout state of each
token, and it does not write back TAN lists or other token info, so OTP values that were already used do not become
valid again.

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
