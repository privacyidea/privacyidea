.. _performance:

Performance considerations
--------------------------

You can test performance using the apache bench from the apache utils.
Creating a simple pass token for a user, eases the performance testing.

Then you can run::

   ab -l -n 200 -c 8 -s 30 'https://localhost/validate/check?user=yourUser&pass=yourPassword'

The performance depends on several aspects like the connection speed to your
database and the connection speed to your user stores.

Processes
~~~~~~~~~

You should run several processes and threads. You might start with the
number of processes equal to the number of your CPU cores. But you
should evaluate, which is the best number of processes to get the
highest performance.

Config caching
~~~~~~~~~~~~~~

Starting with privacyIDEA 2.15 privacyIDEA uses a Cache per instance and process to
cache system configuration, resolver, realm and policies.

As the configuration might have been changed in the database by another process
or another instance, privacyIDEA compares a cache timestamp with the timestamp in the
database. Thus at the beginning of the request privacyIDEA reads the timestamp from
the database.

You can configure how often the timestamp should be read using the pi.cfg
variable ``PI_CHECK_RELOAD_CONFIG``. You can set this to seconds. If you use this
config value to set values higher than 0, you will improve your performance.
But: other processes or instances will learn later about configuration changes
which might lead to unexpected behavior.

.. _faq_perf_crypto:

Cryptography
~~~~~~~~~~~~

Cryptography, especially Public-key cryptography is typically based on solving
difficult and/or time-consuming problems. privacyIDEA uses a lot of cryptographic
techniques to ensure the security of its operation.

Some cryptographic operations are not strictly necessary for the secure operation
but provide additional safety for the user. If performance is an issue, some of
these can be disabled to improve the throughput.

Please also read :ref:`crypto_considerations` to understand the implications.

.. _faq_perf_crypto_audit:

The Audit-log
^^^^^^^^^^^^^

Each entry in the :ref:`audit` log is digitally signed to detect tampering.
If you can be sure that the private key in ``PI_AUDIT_KEY_PRIVATE`` has not been
tampered with, you can set the config entry ``PI_AUDIT_NO_PRIVATE_KEY_CHECK = True``
in :ref:`cfgfile` to improve the performance when loading the key.

With the config entry ``PI_AUDIT_NO_SIGN = True`` the signing of the Audit-log
can be deactivated completely.

The privacyIDEA Response
^^^^^^^^^^^^^^^^^^^^^^^^

By default, privacyIDEA signs every JSON-Response with the private key in
``PI_AUDIT_KEY_PRIVATE``. To improve the performance when loading the private
key the config entry ``PI_RESPONSE_NO_PRIVATE_KEY_CHECK`` can be set to ``True``.

The signing of the response can be disabled completely by setting
``PI_NO_RESPONSE_SIGN`` to ``True``.

Logging
~~~~~~~

Choose a logging level like ``WARNING`` or ``ERROR``. Setting the logging level
to ``INFO`` or ``DEBUG`` will produce much log output and lead to a decrease in
performance.

Response
~~~~~~~~

You can strip the authentication response to get a slight increase in performance
by using the policy ``no_details_on_success``.


Clean configuration
~~~~~~~~~~~~~~~~~~~

Remove unused resolvers and policies. Have a realm with several resolvers is
a bit slower than one realm with one resolver. Finding the user in the first
resolver is faster than in the last resolver.
Although e.g. the LDAP resolver utilizes caching.

Also see :ref:`performance_tokenview`.
