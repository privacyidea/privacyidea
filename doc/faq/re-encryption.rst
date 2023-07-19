.. _faq_reencryption:

Re-Encrypting data
------------------

You might need to reencrypt your token data, i.e. the secret OTP keys of your tokens.
It could be since you are changing your security module or you think your encryption key is compromized.

privacyIDEA provides tooks to reencrypt your token data.

Note, that currently we do not reencrypt configuration data like LDAP resolver passwords.

Reencryption is currently done offline. You will have to export your existing tokens and reimport the tokens to
the system with the new security module or encryption key.

This process will only update existing tokens in the new system. It will not create these tokens.

Export tokens
~~~~~~~~~~~~~

Use the :ref:`token-janitor` to export the tokens to a YAML file. This file contains the **unencrypted** secret keys
of the tokens and also the tokeninfos of the tokens.

You need to handle this file with care!

    privacyidea-token-janitor find --action export --yaml my-tokens.yaml

Check for error messages written to stderr!

Updating tokens
~~~~~~~~~~~~~~~

You can then turn to the system with the new security module or encryption key.
Note, that the new privacyIDEA system actually has to contain the tokens!

Use the update command to to store the secret OTP keys with the new encryption mechanism.

    privacyidea-token-janitor updatetokens --yaml my-tokens.yaml

Check for error messages written to stderr!

What can possibly go wrong
~~~~~~~~~~~~~~~~~~~~~~~~~~

Tokens with a broken OTP key may fail to export or import. This could e.g. happen if tokens are not fully enrolled.

If a token does not exist in the new system, it will not be updated!

