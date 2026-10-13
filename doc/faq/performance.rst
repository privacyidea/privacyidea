.. _performance:

Performance considerations
--------------------------

You can test performance using the apache bench from the apache utils.
Creating a simple pass token for a user eases the performance testing.

Then you can run::

   ab -l -n 200 -c 8 -s 30 'https://localhost/validate/check?user=yourUser&pass=yourPassword'

The performance depends on several aspects like the connection speed to your
database and the connection speed to your user stores.

.. _faq_perf_is_it_the_database:

Is the database the bottleneck?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because almost every request reads from the database and the user store, a slow
database or a slow network link to it makes privacyIDEA feel slow - even though
privacyIDEA itself is not the cause. Before assuming the application is at
fault, check where the time is actually spent:

* The *Resolver Timing* panel on the :ref:`dashboard` shows the per-resolver
  latency of user-store operations. Consistently high values there point at the
  user store (e.g. a remote LDAP/SQL/HTTP backend) or the network to it, not at
  privacyIDEA.

* For the database itself, use the database's own diagnostics, which are far
  more precise than anything in the application:

  * **PostgreSQL:** set ``log_min_duration_statement`` (for example to ``200``
    ms) to log slow statements, and/or enable the ``pg_stat_statements``
    extension to see which statements cost the most over time.
  * **MySQL / MariaDB:** enable the slow query log (``slow_query_log = 1``
    together with a suitable ``long_query_time``).

* Also check the network round-trip latency to the database host, whether the
  connection pool is saturated, and that the database server has enough CPU,
  memory and I/O.

The ``ab`` benchmark above, run against a simple pass token, leaves out the OTP
calculation, but not the PIN check: a simple pass token authenticates with its
PIN only, and the PIN is checked against its stored hash, which is expensive on
purpose. The benchmark therefore measures the PIN hashing (see
:ref:`faq_perf_pin_hashing`) together with the database and the user store, in
which the user is still looked up.

Processes
~~~~~~~~~

You should run several processes and threads. You might start with the
number of processes equal to the number of your CPU cores. But you
should evaluate, which is the best number of processes to get the
highest performance.

Config caching
~~~~~~~~~~~~~~

privacyIDEA uses a cache per instance and process to
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

Loading the private key from ``PI_AUDIT_KEY_PRIVATE`` validates it, which takes
considerably longer than creating a signature with it. The loaded key is kept as
long as the key file does not change, so this happens once per process (and again
after the key file was replaced) and not once per audit entry. If you can be sure
that the private key has not been tampered with, the config entry
``PI_AUDIT_NO_PRIVATE_KEY_CHECK = True`` in :ref:`cfgfile` skips the validation,
but it only saves the single check each worker process does on the first request
it handles. The audit object is created for every request, so
that is where the key is loaded, whether or not an audit entry is written.

With the config entry ``PI_AUDIT_NO_SIGN = True`` the signing of the Audit-log
can be deactivated completely.

The privacyIDEA Response
^^^^^^^^^^^^^^^^^^^^^^^^

By default, privacyIDEA signs every JSON-Response with the private key in
``PI_AUDIT_KEY_PRIVATE``. As for the audit log, the key is loaded and validated
when a worker process signs its first response and is then kept as long as the key
file does not change, so the config entry ``PI_RESPONSE_NO_PRIVATE_KEY_CHECK = True``
only skips that one validation.

The signing of the response can be disabled completely by setting
``PI_NO_RESPONSE_SIGN`` to ``True``.

.. _faq_perf_pin_hashing:

PIN hashing
^^^^^^^^^^^

Token PINs are stored as hashes (see :ref:`faq_crypto_pin_hashing`). Checking a
PIN against its hash is expensive on purpose: with the default parameters
(Argon2id, 9 rounds, 64 MiB memory, parallelism 4) one check took about 125 ms
on a laptop. The passwords of internal administrators are hashed the same way.

An authentication request checks the PIN of every token of the user for which
the given password is at least as long as the OTP length of the token, and it
does not stop after one token has matched. A user with several tokens therefore
costs several PIN checks per request. If challenge-response is enabled for a
token type (policy :ref:`policy_challenge_response`), the PIN of a token of
this type can be checked twice in one request.

The hash algorithm and its parameters are set with ``PI_HASH_ALGO_LIST`` and
``PI_HASH_ALGO_PARAMS`` in :ref:`cfgfile`. Lower parameters make each check
faster, but also weaken the protection of the stored PINs and passwords; read
:ref:`crypto_considerations` before you change them. New parameters apply to
PINs and passwords that are set after the change; existing hashes keep the
parameters they were created with until the PIN or password is set again.

Logging
~~~~~~~

Choose a logging level like ``WARNING`` or ``ERROR``. Setting the logging level
to ``INFO`` or ``DEBUG`` will produce much log output and lead to a decrease in
performance.

Response
~~~~~~~~

You can strip the authentication response to get a slight increase in performance
by using the policy :ref:`policy_no_detail_on_success`.


Clean configuration
~~~~~~~~~~~~~~~~~~~

Remove unused resolvers and policies. Having a realm with several resolvers is
a bit slower than one realm with one resolver. Finding the user in the first
resolver is faster than in the last resolver, although e.g. the LDAP resolver
uses caching.

Also see :ref:`performance_tokenview`.
