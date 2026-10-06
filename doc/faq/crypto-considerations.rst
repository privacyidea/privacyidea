.. _crypto_considerations:

Cryptographic considerations of privacyIDEA
-------------------------------------------

.. index:: Crypto considerations

Encryption keys
~~~~~~~~~~~~~~~

The encryption key is a set of 3 256bit AES keys. Usually this key is located
in a 96 byte long file "enckey" specified by *PI_ENCFILE* in :ref:`cfgfile`.
The encryption key can be encrypted with a password.

The first key encrypts the OTP seeds and secret keys stored in the *Token*
table, and token PINs if they are stored encrypted (see
:ref:`faq_crypto_pin_hashing`). The second key encrypts all other stored
secrets, such as the passwords of resolvers to connect to LDAP/AD or SQL
(stored in the *ResolverConfig* table), of SMTP servers, RADIUS servers and SMS
gateways, and token information of the type password. The third key is
currently not used.

OTP seeds and passwords are needed in clear text to calculate OTP values or
to connect to user stores. So these values need to be stored in a decryptable
way.

Token Hash Algorithms
~~~~~~~~~~~~~~~~~~~~~

OTP values according to HOTP and TOTP can be calculated using SHA1, SHA2-256
and SHA2-512.

.. _faq_crypto_pin_hashing:

PIN Hashing
~~~~~~~~~~~

Token PINs are managed by privacyIDEA as the first of the two factors. Each
token has its own token PIN. The token PIN is hashed and stored in the *Token*
database table. By default the hash is Argon2 with 9 rounds; the hash
algorithms and their parameters are set with ``PI_HASH_ALGO_LIST`` and
``PI_HASH_ALGO_PARAMS`` in :ref:`cfgfile`. If the enrollment policy
``encrypt_pin`` is set (see :ref:`enrollment_policies`), the PIN is stored
encrypted with the first encryption key instead, so it can be decrypted.

This PIN hashing is performed in *lib.crypto:pass_hash*.

Administrator Passwords
~~~~~~~~~~~~~~~~~~~~~~~

privacyIDEA can manage internal administrators using :ref:`pimanage`.
Internal administrators are stored in the database table *Admin*.

The password is stored as a hash (by default Argon2 with 9 rounds, like the
token PIN) with an additional pepper.
While Argon2 uses a salt which is stored in the *Admin* table
created randomly for each admin password the pepper is unique for one
privacyIDEA installation and stored in the pi.cfg file.

This way a database administrator is not able to inject rogue password hashes.

The admin password hashing is performed in *lib.crypto:hash_with_pepper*.

.. _faq_crypto_audit:

Audit Signing
~~~~~~~~~~~~~

The audit log is digitally signed. (see :ref:`audit` and :ref:`audit_parameters`).

The audit log can be handled by different modules. privacyIDEA comes with an
SQL Audit Module which is enabled by default.

For signing the audit log the SQL Audit Module uses the RSA keys specified
with the values ``PI_AUDIT_KEY_PUBLIC`` and ``PI_AUDIT_KEY_PRIVATE`` in
:ref:`cfgfile`.

By default the installer generates 2048bit RSA keys.

If you can assure that the private key has not been tampered with, the config
entry ``PI_AUDIT_NO_PRIVATE_KEY_CHECK = True`` avoids a time-consuming check during
loading of the private key. The loaded key is kept by the worker process as long
as the key file does not change, so this check is not part of the cost of an
individual audit entry (See also :ref:`faq_perf_crypto_audit`).

The audit signing is performed in *lib.crypto:Sign.sign* using SHA2-256 as
hash function.
