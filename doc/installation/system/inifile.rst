.. _cfgfile:

The Config File
===============

.. index:: config file, external hook, hook, debug, loglevel

privacyIDEA reads its configuration from different locations:

   1. default configuration from the module ``privacyidea/config.py``
   2. then from the config file ``/etc/privacyidea/pi.cfg`` if it exists and then
   3. from the file specified in the environment variable ``PRIVACYIDEA_CONFIGFILE``::

         export PRIVACYIDEA_CONFIGFILE=/your/config/file

The configuration is overwritten and extended in each step. I.e. values define
in ``privacyidea/config.py``
that are not redefined in one of the other config files, stay the same.

You can create a new config file (either ``/etc/privacyidea/pi.cfg``) or any other
file at any location and set the environment variable.
The file should contain the following contents::

   # The realm, where users are allowed to login as administrators
   SUPERUSER_REALM = ['super', 'administrators']
   # Your database
   SQLALCHEMY_DATABASE_URI = 'sqlite:////etc/privacyidea/data.sqlite'
   # Set maximum identifier length to 128
   # SQLALCHEMY_ENGINE_OPTIONS = {"max_identifier_length": 128}
   # This is used to encrypt the auth_token
   SECRET_KEY = 't0p s3cr3t'
   # This is used to encrypt the admin passwords
   PI_PEPPER = "Never know..."
   # This is used to encrypt the token data and token passwords
   PI_ENCFILE = '/etc/privacyidea/enckey'
   # This is used to sign the audit log
   PI_AUDIT_KEY_PRIVATE = '/home/cornelius/src/privacyidea/private.pem'
   PI_AUDIT_KEY_PUBLIC = '/home/cornelius/src/privacyidea/public.pem'
   # PI_AUDIT_MODULE = <python audit module>
   # PI_AUDIT_SQL_URI = <special audit log DB uri>
   # Options passed to the Audit DB engine (supersedes SQLALCHEMY_ENGINE_OPTIONS)
   # PI_AUDIT_SQL_OPTIONS = {}
   # Truncate Audit entries to fit into DB columns
   PI_AUDIT_SQL_TRUNCATE = True
   # PI_LOGFILE = '....'
   # PI_LOGLEVEL = 20
   # PI_INIT_CHECK_HOOK = 'your.module.function'
   # PI_CSS = '/location/of/theme.css'
   # PI_UI_DEACTIVATED = True
   # PI_ENABLE_CSP = True
   # PI_FORCE_HTTPS = True

.. note:: The config file is parsed as python code, so you can use variables to
   set the path and you need to take care of the indentation.

``SQLALCHEMY_DATABASE_URI`` defines the location of your database.
For more information about the database connect string, supported databases and
drivers please read :ref:`database_connect`.

``SQLALCHEMY_ENGINE_OPTIONS`` is a dictionary of keyword args to send
to `create_engine() <https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy
.create_engine>`_. The ``max_identifier_length`` is the database's
configured maximum number of characters that may be used in a SQL identifier
such as a table name, column name, or label name. For Oracle version 19 and above
the `max_identifier_length <https://docs.sqlalchemy.org/en/14/core/engines
.html#sqlalchemy.create_engine.params.max_identifier_length>`_ should be set to 128.

privacyIDEA adds ``pool_pre_ping = True`` to these options unless you set the key
yourself. The connection is then validated when it is taken from the pool and
transparently replaced if the database server has closed it in the meantime. Without
it, a connection that was dropped at the MariaDB/MySQL ``wait_timeout`` or during a
database restart is handed to a request and fails it with *MySQL server has gone
away*. The ping is skipped for SQLite, where connections cannot go stale, and it can
be switched off with ``SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": False}``.

The engine options can also be set through the environment, since values of
``PRIVACYIDEA_*`` variables are parsed as JSON and ``__`` addresses a key inside a
dictionary::

   PRIVACYIDEA_SQLALCHEMY_ENGINE_OPTIONS='{"pool_recycle": 3600, "pool_pre_ping": true}'
   PRIVACYIDEA_SQLALCHEMY_ENGINE_OPTIONS__pool_recycle=3600

.. note:: A normal installation reads the environment *before* the config file, so a
   value in ``pi.cfg`` wins over the environment. The docker deployment reads the
   config file first, so there the environment wins.

The ``SUPERUSER_REALM`` is a list of realms, in which the users get the role
of an administrator.

``PI_INIT_CHECK_HOOK`` is a function in an external module, that will be
called as decorator to ``token/init`` and ``token/assign``. This function
takes the ``request`` and ``action`` (either "init" or "assign") as an
arguments and can modify the request or raise an exception to avoid the
request being handled.

If you set ``PI_DB_SAFE_STORE`` to *True* the database layer will in the cases
of ``tokenowner``, ``tokeinfo`` and ``tokenrealm`` read the id of the newly created
database object in an additional SELECT statement and not return it directly. This is
slower but more robust and can be necessary in large redundant setups.

.. Note:: In certain cases (e.g. with Galera Cluster) it can happen that the database
   node has no information about the object id directly during the write-process.
   The database might respond with an error like "object has been deleted or its
   row is otherwise not present". In this case setting ``PI_DB_SAFE_STORE``  to *True*
   might help.

``PI_HASH_ALGO_LIST`` is a user-defined list of hash algorithms which are used
to verify passwords and pins. The first entry in ``PI_HASH_ALGO_LIST`` is used
for hashing a new password/pin.
If ``PI_HASH_ALGO_LIST`` is not defined, ``['argon2', 'pbkdf2_sha512']`` is the default.
Further information can be found in the FAQ (:ref:`faq_crypto_pin_hashing`).

.. note:: If you change the hash algorithm, take care that the previously used one is still
   included in the ``PI_HASH_ALGO_LIST`` so already generated hashes can still be verified.


``PI_HASH_ALGO_PARAMS`` is a user-defined dictionary where various parameters for the hash algorithm
can be set, for example::

   PI_HASH_ALGO_PARAMS = {'argon2__rounds': 5, 'argon2__memory_cost': 768'}

Further information on possible parameters can be found in the
`PassLib documentation <https://passlib.readthedocs.io/en/stable/lib/passlib.hash.html>`_.

Security
--------

``PI_ENABLE_CSP`` will make the server return a strict Content Security Policy for the browser.
``PI_FORCE_HTTPS`` will enforce the use of HTTPS.

``PI_BASE_URL`` is the trusted public URL of this privacyIDEA server, e.g.::

    PI_BASE_URL = "https://pi.example.com"

It is used to build user-facing links that are sent out of band, such as the
password-recovery link (``POST /recover``) and the ``{url}`` tag in
notifications. These links are never derived from the inbound HTTP ``Host``
header. If ``PI_BASE_URL`` is not configured, the password-recovery endpoint refuses to
operate and the ``{url}`` notification tag is left blank. Always configure
``PI_BASE_URL`` for a secure deployment.

Translation
-----------

``PI_PREFERRED_LANGUAGE`` is a list in which the preferred languages can be defined.
The browser's language settings are compared to this list and the "best match" wins.
If none of the languages set in the browser match, the first language in the list
will be used as the default language::

    PI_PREFERRED_LANGUAGE = ["en", "de", "es", "fr"]

.. note:: If ``PI_PREFERRED_LANGUAGE`` is not defined, the following list is used:

   .. autodata:: privacyidea.webui.login.DEFAULT_LANGUAGE_LIST

The parameter ``PI_TRANSLATION_WARNING`` can be used to provide a prefix, that is
set in front of every string in the UI, that is not translated to the language your browser
is using.

Logging
-------

There are three config entries, that can be used to define the logging. These
are ``PI_LOGLEVEL``, ``PI_LOGFILE``, ``PI_LOGCONFIG``. These are described in
:ref:`debug_log`.

You can use ``PI_CSS`` to define the location of another cascading style
sheet to customize the look and feel. Read more at :ref:`themes`.

.. note:: If you ever need passwords being logged in the log file, you may
   set ``PI_LOGLEVEL = 9``, which is a lower log level than ``logging.DEBUG``.
   Use this setting with caution and always delete the logfiles!

``PI_MAIL_DEBUG_LEVEL`` enables ``smtplib``'s SMTP debug output when sending
mails. Allowed values match ``smtplib.SMTP.set_debuglevel``: ``0`` (default,
off), ``1`` (protocol trace) or ``2`` (protocol trace with timestamps). The
output is written by ``smtplib`` directly to ``stderr`` and therefore ends
up wherever the WSGI server (Apache, uWSGI, gunicorn, systemd journal, ...)
captures stderr - typically the webserver's error log.

.. warning:: With ``PI_MAIL_DEBUG_LEVEL`` enabled the stderr stream will
   contain the full SMTP wire trace, including the ``AUTH`` line (SMTP
   credentials in base64) and the complete message body (which may include
   OTP values or enrollment links). Only enable this for short
   troubleshooting sessions and rotate or scrub the affected log
   afterwards.

privacyIDEA digitally signs the responses with the private key in
``PI_AUDIT_KEY_PRIVATE``. If you can be sure that the private key has
not been tampered with, you can set the parameter ``PI_AUDIT_NO_PRIVATE_KEY_CHECK``
to ``True`` in order to improve the performance when loading the key.

You can disable the signing of the responses completely using the parameter
``PI_NO_RESPONSE_SIGN``. Set this to ``True`` to suppress the response signature.

You can set ``PI_UI_DEACTIVATED = True`` to deactivate the privacyIDEA UI.
This can be interesting if you are only using the command line client or your
own UI and you do not want to present the UI to the user or the outside world.

.. note:: The API calls are all still accessible, i.e. privacyIDEA is
   technically fully functional.

.. _engine-registry:

Engine Registry Class
---------------------

The ``PI_ENGINE_REGISTRY_CLASS`` option controls the pooling of database connections
opened by SQL resolvers and the SQL audit module. If it is set to ``"null"``,
SQL connections are not pooled at all and new connections are opened for every request.
If it is set to ``"shared"``, connections are pooled on a per-process basis, i.e.
every wsgi process manages one connection pool for each SQL resolver and the SQL audit module.
Every request then checks out connections from this shared pool, which reduces
the overall number of open SQL connections. If the option is left unspecified,
its value defaults to ``"null"``.

.. _audit_parameters:

Audit parameters
----------------

``PI_AUDIT_MODULE`` lets you specify an alternative auditing module. The
default which is shipped with privacyIDEA is
``privacyidea.lib.auditmodules.sqlaudit``. There is usually no need to change this.

You can change the server name of the privacyIDEA node, which will be logged
to the audit log using the variable ``PI_AUDIT_SERVERNAME``. If this variable
is not set, the value from ``PI_NODE`` or ``localnode`` will be used.

You can run the database for the audit module on another database or even
server. For this you can specify the database URI via ``PI_AUDIT_SQL_URI``.

.. note:: If you run the Audit database on a different URI, the schema update script
   will not update the Audit schema automatically during update. Then check the
   READ_BEFORE_UPDATE.md, if the Audit data has been changed. Then you need to adapt
   the Audit table manually.

With ``PI_AUDIT_SQL_OPTIONS`` You can pass a dictionary of options to the
database engine. If ``PI_AUDIT_SQL_OPTIONS`` is not set,
``SQLALCHEMY_ENGINE_OPTIONS`` will be used.

``PI_AUDIT_SQL_TRUNCATE = True`` lets you truncate audit entries to the length
of the database fields (See :ref:`Audit table size <audit_table_size>`).

In certain cases when you experiencing problems you may use the parameters
``PI_AUDIT_POOL_SIZE`` and ``PI_AUDIT_POOL_RECYCLE``. However, they are only
effective if you also set ``PI_ENGINE_REGISTRY_CLASS`` to ``"shared"``.

For signing and verifying each Audit entry, the RSA keys in ``PI_AUDIT_KEY_PRIVATE``
and ``PI_AUDIT_KEY_PUBLIC`` are used. If you can be sure that the private key has
not been tampered with, you can set the parameter ``PI_AUDIT_NO_PRIVATE_KEY_CHECK``
to ``True`` in order to improve the performance when loading the key.

If you by any reason want to avoid signing audit entries entirely, you can
set ``PI_AUDIT_NO_SIGN = True``. If ``PI_AUDIT_NO_SIGN`` is set to ``True``
audit entries will not be signed and also the signature of audit entries will not be
verified. Audit entries will appear with the *signature* *fail*.
Please see also :ref:`faq_crypto_audit` and :ref:`faq_perf_crypto_audit`

.. _monitoring_modules:

Monitoring parameters
---------------------

``PI_MONITORING_MODULE`` lets you specify an alternative statistics monitoring module.
The monitoring module takes care of writing values with timestamps to a store.
This is used e.g. by the :ref:`eventcounter` and :ref:`taskmodule_simplestats`.

The first available monitoring module is ``privacyidea.lib.monitoringmodules.sqlstats``.
It accepts the following additional parameters:

``PI_MONITORING_SQL_URI`` can hold an alternative SQL connect string. If not specified the
normal ``SQLALCHEMY_DATABASE_URI`` is used.

``PI_MONITORING_POOL_SIZE`` (default 20) and ``PI_MONITORING_POOL_RECYCLE`` (default 600) let
you configure pooling. It uses the settings from the above mentioned
``PI_ENGINE_REGISTRY_CLASS``.

.. note:: A SQL database is probably not the best database to store time series.
   Other monitoring modules will follow.


.. _picfg_metrics_health:

Authentication path tuning
--------------------------

These parameters reduce work that every authentication request would otherwise
repeat. Both trade a little precision in data that is only ever read as an
approximation, and both can be turned off by setting them to ``0``.

``PI_CLIENTAPPLICATION_WRITE_INTERVAL`` (default ``60`` seconds) sets how long a
client may keep its recorded ``lastseen`` timestamp before it is written again.
privacyIDEA notes the address and user agent of every authenticating client in
the ``clientapplication`` table, which is what the client list in the WebUI and
the metering of plugin traffic read. Without this interval that means a
``SELECT``, an ``UPDATE`` and a ``COMMIT`` per request - a cluster-wide write in
a replicated setup - to keep a timestamp accurate to the second that nobody
reads that precisely. Each worker process skips the write for a client it wrote
within the interval, so ``lastseen`` is behind by at most that much. Set it to
``0`` to write on every request.

``PI_SUBSCRIPTION_COUNT_INTERVAL`` (default ``60`` seconds) sets how long the
number of users with active tokens may be reused between subscription checks.
The check runs on every authentication that carries a known plugin's user agent,
and counting those users means a ``DISTINCT`` across the whole ``tokenowner`` and
``token`` tables. A number is only reused while it stays within what the
subscription allows: as soon as it would say the subscription is exceeded, the
users are counted again, so an authentication is never refused on the strength of
a number that may be out of date. The other direction is the accepted trade - a
user given a token within the interval may not be counted yet, which changes
nothing for enforcement that is deliberately probabilistic. The subscription
overview and the statistics task always count exactly. Set it to ``0`` to count
on every check.

Metrics and certificate health
------------------------------

These parameters control the internal metrics and the certificate-health
information shown on the :ref:`dashboard`.

``PI_NO_INTERNAL_METRICS`` (default ``False``). privacyIDEA records
pre-aggregated timing and delivery metrics into the ``metric_aggregate`` table,
which back the *Resolver Timing* and *Notification Delivery* dashboard panels.
Set this to ``True`` to disable recording entirely; the panels then show no
data and the table stays empty. Reads remain available and the
``MetricsCleanup`` task (see :ref:`taskmodule_metricscleanup`) keeps working.

``PI_CERT_CHECK_CACHE_SECONDS`` (default ``3600``) sets how long the results of
the certificate-health checks are cached. The cache is also invalidated
automatically whenever a resolver is saved or deleted.

The certificate-health panel inspects the TLS certificates of your configured
LDAP and Keycloak resolvers automatically. To additionally report on the
privacyIDEA server certificate, set one or both of the following (both off by
default, both admin-controlled and never derived from request data):

``PI_SERVER_CERT_FILE`` - absolute path to a PEM (or DER) certificate file that
the privacyIDEA process can read::

    PI_SERVER_CERT_FILE = "/etc/letsencrypt/live/auth.example.com/fullchain.pem"

``PI_HEALTH_CERT_PROBES`` - a list of ``{"host": "...", "port": int}`` endpoints
that privacyIDEA opens a TLS connection to in order to read the served
certificate::

    PI_HEALTH_CERT_PROBES = [{"host": "127.0.0.1", "port": 443}]

See :ref:`dashboard` for the full description of the panels these parameters
feed.


privacyIDEA Nodes
-----------------

privacyIDEA can run in a redundant setup. For several purposes You
can give these different nodes dedicated names.

``PI_NODE`` is a string with the name of this very node. At the startup of
privacyIDEA, an installation specific unique ID will be used to tie the
node name to an installation. The administrator can set a unique ID for this
installation as well with the ``PI_NODE_UUID`` configuration value (it must
conform to `RFC 4122 <https://datatracker.ietf.org/doc/html/rfc4122.html>`_).

If no ``PI_NODE_UUID`` is configured, privacyIDEA tries to read the ID from a
dedicated file.
The administrator can specify the file with ``PI_UUID_FILE``. The default value
is ``/etc/privacyidea/uuid.txt``. If this file does not provide an ID, the
content of ``/etc/machine-id`` will be used.

If all fails, a unique ID will be generated and made persistent in the
``PI_UUID_FILE`` so the privacyIDEA process requires the necessary permission
to write to this file.

Before version 3.10, the available nodes of the setup were defined with the
``PI_NODES`` configuration value. Since version 3.10, this configuration value
is not used anymore. The names of all nodes
in a redundant setup will be made available through the database.

If ``PI_NODE`` is not set, then ``PI_AUDIT_SERVERNAME`` is used as node name.
If this is not set as well, the node name is returned as "localnode".

.. _trusted_jwt:

Trusted JWTs
-------------

Other applications can use the API without the need
to call the ``/auth`` endpoint. This can be achieved by
trusting private RSA keys to sign JWTs. You can define a list
of corresponding public keys that are trusted for certain
users and roles using the parameter ``PI_TRUSTED_JWT``::

   PI_TRUSTED_JWT = [{"public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEF...",
                      "algorithm": "RS256",
                      "role": "user",
                      "realm": "realm1",
                      "username": "userA",
                      "resolver": "resolverX"}]


This entry means, that the private key, that corresponds to the given
public key can sign a JWT, that can impersonate as the *userA* in resolver
*resolverX* in *realmA*.

.. note:: The ``username`` can be a regular expression like ".*".
   This way you could allow a private signing key to impersonate every
   user in a realm. (Starting with version 3.3)

A JWT can be created like this::

   auth_token = jwt.encode(payload={"role": "user",
                                    "username": "userA",
                                    "realm": "realm1",
                                    "resolver": "resolverX"},
                                    "key"=private_key,
                                    "algorithm"="RS256")

.. note:: The user and the realm do not necessarily need to exist in any
   resolver!
   But there probably must be certain policies defined for this user.
   If you are using an administrative user, the realm for this administrative
   must be defined in ``pi.cfg`` in the list ``SUPERUSER_REALM``.


Token parameters
----------------

.. _picfg_token_serial_random:

Random serial generation
........................

.. versionadded:: 3.11

A newly generated token serial contains an additional non-random part which
reduces the amount of possible serials. To generate completely random serials use::

    PI_TOKEN_SERIAL_RANDOM = True

.. note::
    See :py:func:`~privacyidea.lib.token.gen_serial` for more information on
    the generation of a token serial.

.. _picfg_3rd_party_tokens:

3rd party token types
.....................

You can add 3rd party token types to privacyIDEA. Read more about this
at :ref:`customize_3rd_party_tokens`.

To make the new token type available in privacyIDEA,
you need to specify a list of your 3rd party token class modules
in ``pi.cfg`` using the parameter ``PI_TOKEN_MODULES``::

    PI_TOKEN_MODULES = [ "myproject.cooltoken", "myproject.lametoken" ]

.. _picfg_enable_token_type_enrollment:

Enable Enrollment of Deprecated Token Types
...........................................

.. versionadded:: 3.12

privacyIDEA can mark a token type as *partially deprecated*: existing tokens of
that type keep working, but no new tokens of that type can be enrolled. If an
admin still wants to enroll new tokens of such a type, the type name can be
added to the ``PI_ENABLE_TOKEN_TYPE_ENROLLMENT`` list in ``pi.cfg``::

    PI_ENABLE_TOKEN_TYPE_ENROLLMENT = ['<tokentype>']

.. note::

   As of v3.14 no token types are in this state. Types that are *fully*
   removed (e.g. ``u2f`` in v3.14) are migrated by the schema update to
   ``tokentype='deprecated'`` and handled via ``pi-tokenjanitor deprecated``
   - see the developer note ``dev/token-deprecation-strategy.md``.

.. _picfg_email_validators:

3rd party email validators
--------------------------

privacyIDEA can use email validators while enrolling email tokens via validate/check.
You can configure your own email validators in the `pi.cfg`::

    PI_EMAIL_VALIDATOR_MODULES = [ "myproject.emailvalidator", "otherproject.nogmail" ]

This module needs to provide a function `validate_email(email: str) -> bool` which returns True if the
email is valid.

The email validator module that comes with privacyIDEA is `privacyidea.lib.utils.emailvalidation`.
You do not need to add this in the `pi.cfg` file, this is available by default.


.. _custom_web_ui:

Custom Web UI
-------------

The Web UI is a single page application, that is initiated from the file
``static/templates/index.html``. This file pulls all CSS, the javascript framework
and all the javascript business logic.

You can configure privacyIDEA to use your own WebUI, which is completely different and stored at another location.

You can do this using the following config values::

    PI_INDEX_HTML = "myindex.html"
    PI_STATIC_FOLDER = "mystatic"
    PI_TEMPLATE_FOLDER = "mystatic/templates"

In this example the file ``mystatic/templates/myindex.html`` would be loaded
as the initial single page application.


.. _redis_cache:

Redis cache
-----------

.. index:: Redis, cache, HA, high availability

privacyIDEA can offload selected state to Redis instead of the SQL database.
Four workloads use it today:

* **Challenges** - challenge data for challenge-response token flows in HA
  setups, where multiple privacyIDEA nodes would otherwise have to round-trip
  every challenge through a clustered database (e.g. Galera with ProxySQL).
  Challenges are ephemeral, so Redis becomes their store rather than a cache.
* **User store lookups** - the login names, user IDs and attributes that come
  back from a resolver. Here Redis is a genuine cache in front of a store that
  stays authoritative, which is what makes it cheap to drop and safe to be
  aggressive about invalidating.
* **Cached authentications** - the entries the :ref:`policy_auth_cache` policy
  works with. Like challenges they are ephemeral, and losing one costs nothing
  but a single real authentication.
* **Certificate health results** - the certificate expiry information behind the
  dashboard panel. Producing it means opening a TLS connection to every
  configured endpoint, which is worth doing once for the installation rather
  than once per worker process.

More workloads (metrics, ...) may opt into Redis later; each one ships behind
its own feature flag and stays off by default.

.. note::

   Redis **7 or later** is required. The challenge, user and authentication
   workloads rely on the ``EXPIRE ... NX`` and ``EXPIRE ... GT`` options to keep
   TTLs consistent across concurrent writes; these were introduced in Redis 7.
   The version is checked when the connection is established: an older server
   is refused up front, and the worker falls back to DB-only operation (and
   keeps retrying the connection) rather than failing later on the first write.

Configuration is two-stage:

1. Point privacyIDEA at a Redis instance with ``PI_REDIS_URL``.
2. Enable the per-workload flag(s) for the data you want to cache.

::

    # Connection (no caching is enabled by setting this alone)
    PI_REDIS_URL = "redis://localhost:6379/0"

    # Per-feature opt-in
    PI_REDIS_CACHE_CHALLENGES = True
    PI_REDIS_CACHE_USERS = True
    PI_REDIS_CACHE_AUTH = True
    PI_REDIS_CACHE_HEALTH = True

    # Optional: lifetime of a user cache entry in seconds. Default 300.
    # Setting it to 0 disables the user cache, like clearing the flag.
    # PI_REDIS_USER_CACHE_TTL = 300

    # Optional: fallback lifetime for a cached authentication, in seconds.
    # Default 3600. Only used when no auth_cache policy window applies, which
    # in practice does not happen - the policy's own interval is the lifetime.
    # PI_REDIS_AUTH_CACHE_TTL = 3600

    # Optional: how long (seconds) to wait before retrying Redis after a
    # failed op. Default 30. Raise it if your environment sees flaky Redis,
    # lower it for tighter recovery.
    # PI_REDIS_RETRY_COOLDOWN = 30

When ``PI_REDIS_CACHE_CHALLENGES`` is enabled, challenges are written to Redis
only and the SQL ``INSERT`` is skipped. Redis' TTL handles expiry - challenges
are ephemeral by nature. If a Redis operation fails at runtime the worker
enters a brief cooldown (``PI_REDIS_RETRY_COOLDOWN`` seconds, default 30)
during which it short-circuits to DB-only without paying a connect timeout
on every request, then automatically retries once the cooldown expires. If
the retry succeeds the cache is back online with no operator intervention;
if it fails the cooldown restarts. ``create_challenge`` always falls back
to the database when Redis isn't writable, so a challenge is never silently
lost.

If ``PI_REDIS_URL`` is not set, every cache call degrades to a no-op and
privacyIDEA behaves exactly as a database-only deployment.

In a Docker deployment, the URL can be loaded from a secret file via
``PI_REDIS_URL_FILE`` (e.g. ``/run/secrets/redis_url``) instead of being passed
in the environment.

.. _redis_user_cache:

User cache
~~~~~~~~~~

.. index:: user cache, Redis

``PI_REDIS_CACHE_USERS`` caches the answers privacyIDEA gets from its user
stores: the user ID behind a login name, the login name behind a user ID, and a
user's attributes. Every one of those is a round trip to an external system - an
LDAP search, an SQL query, an HTTP call - and the answers change rarely, so
serving them from Redis removes most of the user store traffic from
authentication and from listing tokens.

Unlike the two caches privacyIDEA already had, this one is shared: the
:ref:`usercache` table only holds the login/ID correlation, and an LDAP
resolver's ``CACHE_TIMEOUT`` cache is a dictionary inside a single worker
process. Redis is visible to every worker on every node, and can be flushed.

The user store remains the single source of truth. A cache miss is answered by
asking the resolver, nothing is stored that a resolver did not return, and
dropping the whole keyspace costs nothing but a few extra lookups.

**Lifetime.** ``PI_REDIS_USER_CACHE_TTL`` (default 300 seconds) is how long an
entry lives. The default is deliberately short: a change made *directly in the
user store*, behind privacyIDEA's back, is only noticed when the entry expires.
That is the same bound the :ref:`usercache` table has always had, and the reason
not to raise this into the hours.

**Invalidation.** The TTL is the backstop, not the mechanism. Entries are
dropped immediately when privacyIDEA knows something changed:

* a user is updated or deleted through privacyIDEA - that user's entries go,
* a resolver is saved or deleted - every entry of that resolver goes, because
  its configuration is what gives its answers meaning,
* an admin flushes the user cache (``DELETE /system/user-cache``, or *Flush
  user cache* in the WebUI) - everything goes.

Custom user attributes are never cached: they live in privacyIDEA's own database
and are merged on top of the resolver's answer on every read, so they cannot go
stale here.

.. note::

   A resolver with a non-zero ``CACHE_TIMEOUT`` keeps its own per-process copy
   of the same answers, and that cache has no invalidation hook at all - only
   its timeout. It therefore, not this cache, sets the real staleness bound. If
   you want the invalidation above to take effect promptly, lower or zero the
   resolvers' ``CACHE_TIMEOUT`` (see :ref:`useridresolvers`) and let the shared
   cache do the work.

.. _redis_auth_cache:

Authentication cache
~~~~~~~~~~~~~~~~~~~~

.. index:: AuthCache, Authentication Cache, Redis

``PI_REDIS_CACHE_AUTH`` moves the entries of the :ref:`policy_auth_cache` policy
from the ``authcache`` table into Redis.

That table is written to on the authentication path in three directions: an
``UPDATE`` on every cache *hit* to count the use, an ``INSERT`` per successful
authentication, and ``DELETE`` statements for entries that turn out to be stale.
With Redis enabled none of that reaches the database.

Entries live exactly as long as the policy allows: the policy's first interval
(the ``4h`` in ``4h/5m``) becomes the Redis TTL, so a cached password
disappears the moment the policy stops honouring it. Using an entry does not
extend its life, because the window runs from the *first* authentication.
``PI_REDIS_AUTH_CACHE_TTL`` (default 3600 seconds) is only a fallback for a
caller that cannot name a window.

Two consequences worth knowing:

* The ``pi-manage config authcache cleanup`` command has nothing to do, and says
  so instead of reporting that it deleted no rows. The cronjob that command
  usually needs is no longer necessary.
* The database-backed cache never bounded how many entries a user accumulated,
  and every lookup verifies the presented password against each of them with
  Argon2 - so the cache got slower the more it was used. Per-entry expiry bounds
  that set.

Like the other workloads it degrades safely: if Redis cannot be reached the
database takes over, and a lost entry costs one real authentication against the
user store, nothing else.

.. _redis_health_cache:

Certificate health results
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: health, certificate, Redis

``PI_REDIS_CACHE_HEALTH`` shares the certificate expiry information behind the
:ref:`dashboard` panel between all workers and nodes.

Producing that information means opening a TLS connection to every configured
LDAP and Keycloak resolver endpoint, every EntraID client-certificate
credential, and every admin-configured server certificate. Those results are
cached for ``PI_CERT_CHECK_CACHE_SECONDS`` (default 3600) either way - but
without Redis the cache is a dictionary in one worker process, so a deployment
with eight workers on three nodes probes every endpoint twenty-four times per
hour instead of once.

The per-process cache stays in front of the shared one: a worker that already
has the answer has no reason to ask Redis for it. The TTL is the same for both,
and saving or deleting a resolver drops the shared copy as well, so one admin's
change reaches every worker instead of only the one that served the request.

Nothing here is on the authentication path and the results only feed a display,
so if Redis cannot be reached the worker simply probes for itself, exactly as it
did before.

.. _redis_cache_security:

Security
~~~~~~~~

The Redis connection is configured entirely through ``PI_REDIS_URL`` - the URL
scheme, credentials and TLS parameters it carries are the whole security
surface. privacyIDEA does **not** enforce transport encryption or
authentication, so the points below are the operator's responsibility.

**Transport encryption (TLS).** Use the ``rediss://`` scheme to connect over
TLS::

    PI_REDIS_URL = "rediss://redis.internal:6379/0"

TLS options are taken from the URL query string (passed through to the
underlying client), for example a custom CA or client certificate for mutual
TLS::

    PI_REDIS_URL = "rediss://redis.internal:6379/0?ssl_cert_reqs=required&ssl_ca_certs=/etc/ssl/redis-ca.pem"

When relying on TLS, set ``ssl_cert_reqs=required`` explicitly so the server
certificate is verified.

**Authentication.** Credentials are embedded in the URL, either as a password
or as a Redis ACL user and password::

    PI_REDIS_URL = "redis://default:s3cr3t@redis.internal:6379/0"
    PI_REDIS_URL = "rediss://pi-cache-user:s3cr3t@redis.internal:6379/0"

To keep the password out of the process environment, load the whole URL from a
secret file with ``PI_REDIS_URL_FILE`` (see above). Credentials embedded in the
URL are redacted from the privacyIDEA log (only ``***@host`` is ever written),
so they do not leak into log files on connect or on error.

**Data sensitivity.** Redis needs the **same protection level as your
database**: restrict it to a private network, require authentication, prefer
``rediss://``, and use at-rest encryption (encrypted volume, or a managed Redis
with encryption) if your threat model requires it. Do not expose the Redis
instance on a public interface.

What is stored differs per workload:

* Challenge data: the ``data`` field is encrypted with the privacyIDEA
  encryption key before it is written, just as the SQL ``challenge.data``
  column is. That field is the one that can carry a secret - the OTP value
  itself for Email and SMS tokens when ``email.concurrent_challenges`` /
  ``sms.concurrent_challenges`` is enabled, or the display code for Push
  code-to-phone. The remaining fields (transaction ID, token serial, the
  challenge nonce, session and counters) are stored in the clear, again
  matching the database. The exposure window is small - entries carry the
  challenge validity TTL, typically a few minutes.
* User cache values are **encrypted** with the server's encryption key before
  they are written, so a dump of the Redis database is not a dump of your
  directory. The keys are not encrypted: a key contains a login name or a user
  ID, because Redis has to be able to look it up. Treat the key space as
  revealing who exists, and the values as unreadable without the encryption
  key.
* Authentication cache entries are **encrypted** the same way. An entry holds an
  Argon2 hash of the user's password, which could be attacked offline if it
  leaked in the clear. Note that, exactly as with the database-backed cache, a
  password changed in the user store stays usable until its entry expires, so
  keep the :ref:`policy_auth_cache` window short enough to live with that.
* Certificate health results are stored as plaintext. They hold no credentials,
  but they do name your internal LDAP and Keycloak hosts and their certificate
  subjects, which is one more reason not to expose the Redis instance.

Because the encryption uses the privacyIDEA encryption key, cached entries
written before an encryption key rotation can no longer be read afterwards.
Such entries are treated as a cache miss and the affected users simply repeat
the authentication; the condition clears within one challenge-validity TTL.

.. _redis_cache_upgrades:

Upgrades and payload compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

privacyIDEA does not support rolling upgrades on the SQL side (the schema
migration step expects a single writer), so the Redis cache does not need to
clear a higher bar. The policy below applies whenever the cache is enabled.

**Within a single key prefix** (today: ``pi:challenge:v1:``), the payload may
grow over time. Older workers ignore unknown fields; newer workers read older
entries via ``dict.get(field, default)``. No operator action is needed for
this kind of change.

**Breaking payload changes** are handled by bumping the version in the key
prefix (``pi:challenge:v2:txn:...``) rather than by mutating the payload in
place. The old keys are simply no longer read; they age out via TTL within
one challenge-validity window. The visible effect:

* Authentications that were already in flight at the moment of the upgrade
  may need to be restarted by the user (their cached challenge lives under
  the old prefix, the new code only writes/reads the new one). This is the
  same expectation we set for any privacyIDEA upgrade - see
  :ref:`upgrade`.
* No operational ``FLUSHDB`` is required. Disk usage on the Redis instance
  is bounded by the longest configured challenge validity time, after which
  all stale-prefix keys have expired.

**Self-healing safety net.** If a worker encounters a payload it cannot
deserialize for any reason (corruption, a fork's incompatible change, a
hand-edited key), the read is treated as a cache miss and the deserialisation
failure is logged at debug. For Redis-only storage like challenges, the
user-visible outcome is "challenge not found, please try again." The cache
itself never crashes the worker.

Future cache types may follow a different policy. Classic cache-aside
objects backed by a database row of record (e.g. cached user attributes)
will be free to mutate their payload at will, since any deserialisation
failure falls through to the database and re-caches. Each new cacheable
workload will document its own compatibility policy alongside its feature
flag.

.. _user_settings:

User Settings
-------------

The Web UI can store per-user settings (UI preferences) on the server via the
``/user/settings`` endpoint. The values are not interpreted by the backend; they
are only stored and served back to the Web UI of the logged-in user.

Only the setting keys known to the Web UI are accepted. Storing any other key
returns an error that names the rejected key. Further keys, for example for a
customized Web UI, can be allowed without a code change::

    PI_USER_SETTINGS_ALLOWED_KEYS = ["my_custom_key", "another_key"]

The value is a list of additional allowed keys (a comma-separated string is also
accepted when set via an environment variable). Removing a key from the list does
not delete settings already stored under it.

.. _ini_remember_device_grace:

Remember-device grace window
----------------------------

``PI_REMEMBER_DEVICE_GRACE_SECONDS`` (default ``10``) controls the grace window
of the :ref:`api_clients` "remember this device" feature. Two near-simultaneous
requests carrying the same rotating cookie would otherwise make the second look
like a replay (a stale counter) and destroy the session series. Within this many
seconds, and from the same source IP, the immediately-previous counter is
accepted without rotating, so concurrent requests converge on one token.

This is an advanced knob with a sensible default; most deployments never need to
change it. It is a system-wide protocol tolerance, not a per-user or per-realm
setting, so it is configured here rather than by policy. Set it to ``0`` for
strict, fail-secure behaviour (no grace: any stale counter is treated as theft).
Widening it trades theft-detection tightness for fewer re-registrations when a
client loses a rotation response.

The window is anchored to the rotation, not to the last request: it is not
refreshed on each grace hit. A client that never stores the rotated cookie (and
so keeps presenting the previous counter) is therefore tolerated only for this
many seconds and is then treated as theft, forcing the device to re-register.
This is intentional — refreshing the window on every stale request would keep a
never-rotating (or stolen) cookie alive indefinitely and defeat the rotation.

.. versionadded:: 3.14

.. _ini_subscription_version_check:

Subscription version check
--------------------------

.. index:: subscription, air-gapped

The subscription overview on the dashboard shows the latest released version of
each privacyIDEA component next to the version actually in use. These releases
are looked up on GitHub, cached for six hours and requested with a short timeout;
an unreachable repository simply leaves the column empty.

In an installation without internet access the lookup can never succeed, and
paying the timeout for it is pointless. Switch it off with::

    PI_SUBSCRIPTION_VERSION_CHECK = False

The overview still lists every component with its usage and subscription state,
only the latest-release column stays empty. This is the only outbound request the
subscription overview makes.

.. versionadded:: 3.14
