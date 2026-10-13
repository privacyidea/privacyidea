.. _cfgfile:

The Config File
===============

.. index:: config file, external hook, hook, debug, loglevel

privacyIDEA reads its configuration in three steps. Each step overwrites the
values of the previous ones:

   1. the default configuration from the module ``privacyidea/config.py``,
   2. environment variables with the prefix ``PRIVACYIDEA_`` (see below),
   3. one config file: ``/etc/privacyidea/pi.cfg``, or, if the environment
      variable ``PRIVACYIDEA_CONFIGFILE`` is set, the file it names instead::

         export PRIVACYIDEA_CONFIGFILE=/your/config/file

Only one config file is read: if ``PRIVACYIDEA_CONFIGFILE`` is set,
``/etc/privacyidea/pi.cfg`` is not read at all, so the file it names has to
contain the complete configuration. If the config file cannot be read, a
warning is printed and privacyIDEA starts with the values of the first two
steps. Values defined in ``privacyidea/config.py`` that are not set in the
environment or in the config file stay the same. The web server of the Docker
image ignores ``PRIVACYIDEA_CONFIGFILE``: it reads ``/etc/privacyidea/pi.cfg``
and then the environment (see the note on the order below). ``pi-manage`` in the
container reads them in the order above.

You can create a new config file (either ``/etc/privacyidea/pi.cfg`` or any other
file at any location and set the environment variable).
The file should contain the following contents::

   # The realm, where users are allowed to login as administrators
   SUPERUSER_REALM = ['super', 'administrators']
   # Your database
   SQLALCHEMY_DATABASE_URI = 'sqlite:////etc/privacyidea/data.sqlite'
   # Signs the JWT that /auth issues. Use the same value on all processes and nodes.
   # Generate a random value, see below
   # SECRET_KEY = ...
   # Added to local admin passwords, password reset codes and API key secrets
   # before they are hashed. Changing it invalidates all of them.
   # Generate a random value, see below
   # PI_PEPPER = ...
   # This is used to encrypt the token data and token passwords
   PI_ENCFILE = '/etc/privacyidea/enckey'
   # This is used to sign the audit log
   PI_AUDIT_KEY_PRIVATE = '/etc/privacyidea/private.pem'
   PI_AUDIT_KEY_PUBLIC = '/etc/privacyidea/public.pem'
   # PI_AUDIT_MODULE = <python audit module>
   # PI_AUDIT_SQL_URI = <special audit log DB uri>
   # Options passed to the Audit DB engine (supersedes SQLALCHEMY_ENGINE_OPTIONS)
   # PI_AUDIT_SQL_OPTIONS = {}
   # PI_LOGFILE = '....'
   # PI_LOGLEVEL = 20
   # PI_INIT_CHECK_HOOK = 'your.module.function'
   # PI_CSS = '/location/of/theme.css'
   # PI_UI_DEACTIVATED = True
   # PI_ENABLE_CSP = True
   # PI_FORCE_HTTPS = True

.. note:: The config file is parsed as python code, so you can use variables to
   set the path and you need to take care of the indentation.

Generate your own random values for ``SECRET_KEY`` and ``PI_PEPPER`` and add them
to the file, for example::

    PEPPER="$(tr -dc A-Za-z0-9_ </dev/urandom | head -c24)"
    echo "PI_PEPPER = '$PEPPER'" >> /etc/privacyidea/pi.cfg
    SECRET="$(tr -dc A-Za-z0-9_ </dev/urandom | head -c24)"
    echo "SECRET_KEY = '$SECRET'" >> /etc/privacyidea/pi.cfg

Never use values from an example or from another installation.

If ``SECRET_KEY`` is not set, privacyIDEA generates a random key at start. Each
worker process can then have a key of its own, so a JWT issued by one process is
refused by another, and every restart ends all WebUI sessions. Set it, with the
same value on all nodes.

``SQLALCHEMY_DATABASE_URI`` defines the location of your database.
For more information about the database connect string, supported databases and
drivers please read :ref:`database_connect`.

``SQLALCHEMY_ENGINE_OPTIONS`` is a dictionary of keyword args to send
to `create_engine() <https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy
.create_engine>`_. Oracle does not need ``max_identifier_length``: SQLAlchemy
determines the maximum identifier length of the database on the first
connection (128 characters since Oracle Database 12.2). A value set here is used
as is, without that check.

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
takes the ``request`` and ``action`` (either "init" or "assign") as
arguments and can modify the request or raise an exception to avoid the
request being handled.

``PI_HASH_ALGO_LIST`` is a user-defined list of hash algorithms which are used
to verify passwords and pins. The first entry in ``PI_HASH_ALGO_LIST`` is used
for hashing a new password/pin.
If ``PI_HASH_ALGO_LIST`` is not defined, ``['argon2', 'pbkdf2_sha512']`` is the default.
Further information can be found in the FAQ (:ref:`faq_crypto_pin_hashing`).

.. note:: If you change the hash algorithm, take care that the previously used one is still
   included in the ``PI_HASH_ALGO_LIST`` so already generated hashes can still be verified.


``PI_HASH_ALGO_PARAMS`` is a user-defined dictionary where various parameters for the hash algorithm
can be set, for example::

   PI_HASH_ALGO_PARAMS = {'argon2__rounds': 5, 'argon2__memory_cost': 768}

Further information on possible parameters can be found in the
`PassLib documentation <https://passlib.readthedocs.io/en/stable/lib/passlib.hash.html>`_.

.. note:: privacyIDEA checks ``PI_HASH_ALGO_LIST`` and ``PI_HASH_ALGO_PARAMS`` when it starts and
   refuses to start if they can not be used: an unknown algorithm or parameter, an algorithm that
   can not hash on this system (for instance ``argon2`` without the ``argon2-cffi`` package), a
   parameter value that PassLib would reject or silently adjust, or a parameter for an algorithm
   that is not in ``PI_HASH_ALGO_LIST``. This applies to the server and to the command line tools
   such as ``pi-manage`` alike, so a mistake in either entry stops all of them with an error like::

      RuntimeError: 'PI_HASH_ALGO_PARAMS' is not usable: argon2id__rounds names a hash algorithm that is not in 'PI_HASH_ALGO_LIST'

Both entries apply wherever privacyIDEA hashes a password or a PIN: token PINs,
administrator passwords, password reset codes and the entries of the authentication
cache (see :ref:`policy_auth_cache`). Changing ``PI_HASH_ALGO_PARAMS`` keeps the
existing hashes verifiable, because every hash carries the parameters it was created
with - but only as long as the algorithm that created it is still listed in
``PI_HASH_ALGO_LIST``, as the note above says.

.. note:: In the **database-backed** authentication cache an entry is stored in a column
   of 255 characters, which the hashes of the shipped algorithms fit into comfortably
   (Argon2 needs 97 and PBKDF2-SHA512 130). A configuration that produces a longer hash,
   for instance through an unusually large salt or digest, does not fit. PostgreSQL and
   MySQL or MariaDB in strict mode reject it, so caching an authentication fails visibly;
   a MySQL or MariaDB without strict mode truncates the value instead, and the entry it
   stores can then never be verified - it is discarded and the authentication reaches the
   user store again. The Redis cache of :ref:`redis_auth_cache` keeps the entry as an
   encrypted JSON record rather than in that column, so it has no such limit.

Security
--------

``PI_ENABLE_CSP = True`` makes the server return a strict Content Security
Policy for the browser, together with further security headers such as
``Strict-Transport-Security`` (on HTTPS requests) and
``X-Frame-Options: SAMEORIGIN``. It also answers every plain HTTP request with a
redirect to HTTPS, because ``PI_FORCE_HTTPS`` defaults to ``True``. A request
that a reverse proxy marks with the header ``X-Forwarded-Proto: https`` is not
redirected. If a proxy terminates TLS and does not send this header, set
``PI_FORCE_HTTPS = False``; otherwise the requests end in a redirect loop.
``PI_FORCE_HTTPS`` only takes effect if ``PI_ENABLE_CSP`` is set.

``PI_SESSION_COOKIE_SECURE`` (default ``True``) sets the ``Secure`` flag of the
Flask session cookie. Like ``PI_FORCE_HTTPS``, it only takes effect if
``PI_ENABLE_CSP`` is set. privacyIDEA does not use the Flask session, so the
setting currently has no effect. The remember-device cookie that privacyIDEA
sets is always marked ``Secure``, ``HttpOnly`` and ``SameSite=Strict``.

``PI_BASE_URL`` is the trusted public URL of this privacyIDEA server, e.g.::

    PI_BASE_URL = "https://pi.example.com"

It is used to build user-facing links that are sent out of band, such as the
password-recovery link (``POST /recover``) and the ``{url}`` tag in
notifications. These links are never derived from the inbound HTTP ``Host``
header. If ``PI_BASE_URL`` is not configured, the password-recovery endpoint refuses to
operate and the ``{url}`` notification tag is left blank. Always configure
``PI_BASE_URL`` for a secure deployment.

``WEBUI_PASSKEY_LOGIN_ENABLED`` (default ``True``) allows logging in to the WebUI
with a passkey without entering a username. Set it to ``False`` to refuse such
logins. A passkey or WebAuthn token that answers a challenge triggered with the
PIN or password is not affected. To hide the passkey login button on the login
page, use the :ref:`policy_passkey_login` policy.

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
is using. It only affects the previous WebUI (see :ref:`legacy_webui`); the
WebUI privacyIDEA serves is translated when it is built.

Logging
-------

There are three config entries, that can be used to define the logging:
``PI_LOGLEVEL``, ``PI_LOGFILE`` and ``PI_LOGCONFIG``. ``PI_LOGCONFIG`` names a
logging configuration file (default ``/etc/privacyidea/logging.cfg``). If this
file exists and can be read, it defines the whole logging, and ``PI_LOGLEVEL``
and ``PI_LOGFILE`` are ignored; set the level and the file in the logging
configuration file instead. These entries are described in :ref:`debug_log`.

You can use ``PI_CSS`` to define the location of another cascading style
sheet to customize the look and feel of the previous WebUI (see
:ref:`legacy_webui`); the WebUI privacyIDEA serves does not read it. Read more
at :ref:`themes`.

.. note:: Since version 3.14 privacyIDEA hides passwords, PINs, OTP values and
   other secrets in its debug messages at every log level, so a level below
   ``logging.DEBUG`` such as ``PI_LOGLEVEL = 9`` no longer writes them to the
   log file.

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
not been tampered with, you can set the parameter
``PI_RESPONSE_NO_PRIVATE_KEY_CHECK`` to ``True`` in order to skip the validation
of the key. The loaded key is kept as long as the key file does not change, so
the check only runs the first time each worker process signs a response and
again after the key file was replaced.

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

With ``PI_AUDIT_SQL_OPTIONS`` you can pass a dictionary of options to the
database engine. If ``PI_AUDIT_SQL_OPTIONS`` is not set,
``SQLALCHEMY_ENGINE_OPTIONS`` will be used.

Audit entries are always shortened to the length of the database fields, so that
an entry with long request data is written instead of being rejected. The former
setting ``PI_AUDIT_SQL_TRUNCATE`` is ignored (See
:ref:`Audit table size <audit_table_size>`).

In certain cases when you are experiencing problems you may use the parameters
``PI_AUDIT_POOL_SIZE`` and ``PI_AUDIT_POOL_RECYCLE``. However, they are only
effective if you also set ``PI_ENGINE_REGISTRY_CLASS`` to ``"shared"``.

For signing and verifying each Audit entry, the RSA keys in ``PI_AUDIT_KEY_PRIVATE``
and ``PI_AUDIT_KEY_PUBLIC`` are used. If you can be sure that the private key has
not been tampered with, you can set the parameter ``PI_AUDIT_NO_PRIVATE_KEY_CHECK``
to ``True`` in order to skip the validation of the key. The loaded key is kept as
long as the key file does not change, so the check only runs the first time each
worker process uses the key and again after the key file was replaced.

A key file that is replaced while the server is running is picked up without a
restart, because the contents of the key files are read and compared whenever they
are used. Kubernetes updates a mounted secret by pointing a symlink at a new
version of the file, which is picked up in the same way.

.. warning:: Rotating the audit keypair means that every entry written with the
   previous key is verified against the new public key from then on, so the whole
   audit log up to the rotation is displayed with the signature *FAIL* - which can
   not be told apart from a tampered entry. privacyIDEA verifies with a single
   public key, so entries from before the rotation can not be verified any more
   once the new key is in place. Worker processes also pick up a new key
   independently of each other, so entries written during the changeover are split
   across both keys.

.. note:: The audit keys are always configured as *file names* and never hold the
   key material itself, so it can not be passed in an environment variable. A
   container deployment mounts the keypair instead; the Docker configuration picks
   up ``/run/secrets/audit_key_private`` and ``/run/secrets/audit_key_public`` on
   its own. Docker secrets are immutable, so rotating one there means a new secret
   and a new container rather than a replaced file.

If for any reason you want to avoid signing audit entries entirely, you can
set ``PI_AUDIT_NO_SIGN = True``. If ``PI_AUDIT_NO_SIGN`` is set to ``True``
audit entries will not be signed and also the signature of audit entries will not be
verified. Audit entries will appear with the *signature* *fail*.
Please see also :ref:`faq_crypto_audit` and :ref:`faq_perf_crypto_audit`

Audit entries written by older privacyIDEA versions can carry an old style
signature (text-book RSA). These entries appear with the signature *fail*, unless
you set ``PI_CHECK_OLD_SIGNATURES = True`` to verify old style signatures as
well. Verifying them is slow.

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

.. _picfg_metrics_health:

Metrics and certificate health
------------------------------

These parameters control the internal metrics and the certificate-health
information shown on the :ref:`dashboard`.

``PI_NO_INTERNAL_METRICS`` (default ``False``). privacyIDEA records
pre-aggregated timing and delivery metrics into the ``metric_aggregate`` table,
which back the *Resolver Timing* and *Notification Delivery* dashboard panels.
Set this to ``True`` to disable recording entirely; the panels then show no
data and the table stays empty. Reads remain available and
``pi-manage config metrics cleanup`` (see :ref:`pimanage_metrics`) keeps working.

``PI_CERT_CHECK_CACHE_SECONDS`` (default ``3600``) sets how long the results of
the certificate-health checks are cached. Saving or deleting a resolver drops
the cache: without :ref:`redis_health_cache` only in the worker process that
handled the request (the other processes keep their results until they expire),
with it for all workers and nodes.

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

Health check endpoints
----------------------

``PI_HEALTHZ_RESOLVER_CACHE_SECONDS`` (default ``10``) sets how long the result
of ``GET /healthz/resolversz`` is cached. This endpoint opens a connection to
every configured LDAP and SQL resolver, so the cache keeps frequent calls from
connecting to every backend each time. Each worker process caches its own
result. Set it to ``0`` to probe the resolvers on every call. See
:ref:`rest_healthcheck`.


privacyIDEA Nodes
-----------------

privacyIDEA can run in a redundant setup. For several purposes you
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


This entry means that the private key that corresponds to the given
public key can sign a JWT that impersonates *userA* in resolver
*resolverX* in *realm1*.

.. note:: The ``username`` can be a regular expression like ".*".
   This way you could allow a private signing key to impersonate every
   user in a realm.

A JWT can be created like this::

   auth_token = jwt.encode(payload={"role": "user",
                                    "username": "userA",
                                    "realm": "realm1",
                                    "resolver": "resolverX"},
                           key=private_key,
                           algorithm="RS256")

.. note:: For an entry with ``"role": "admin"``, neither the user nor the realm
   has to exist. For ``"role": "user"``, the user has to exist in the realm named
   in the JWT; otherwise the requests that work with the user, such as listing or
   enrolling the user's tokens, fail with the error that the user can not be
   found. Define the policies this user or administrator needs as usual.
   If you are using an administrative user, the realm of this administrative user
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

.. _picfg_module_allowlist:

Classes privacyIDEA may import
..............................

.. versionadded:: 3.14

Two pieces of configuration name a python class for privacyIDEA to import: the ``module`` of an
SMS gateway definition and the value of the :ref:`policy_pinhandling` policy action. Since both
are written through the API rather than through this file, the class is checked against the
classes that ship with privacyIDEA before it is imported.

Writing an own class is supported, so the check is extensible. Name your own classes here::

    PI_SMS_PROVIDER_MODULES = ["mycompany.smsprovider.MyProvider"]
    PI_PIN_HANDLER_MODULES = ["mycompany.pinhandler.LetterPinHandler"]

What happens to a class that is on neither list is decided by::

    PI_MODULE_ALLOWLIST_MODE = "warn"

``warn`` is the default. The class is used, and a warning is written to the log naming the class
and the setting to declare it in, so nothing stops working on an upgrade and you can see what
your installation actually uses. Setting it to ``enforce`` refuses such a class instead.

.. note::
    Declare the classes you use before switching to ``enforce``, otherwise an SMS gateway or a
    pin handler that relies on an own class stops working. The classes that ship with
    privacyIDEA never need declaring.

.. _picfg_3rd_party_tokens:

3rd party token types
.....................

You can add 3rd party token types to privacyIDEA. Read more about this
at :ref:`customize_3rd_party_tokens`.

To make the new token type available in privacyIDEA,
you need to specify a list of your 3rd party token class modules
in ``pi.cfg`` using the parameter ``PI_TOKEN_MODULES``::

    PI_TOKEN_MODULES = [ "myproject.cooltoken", "myproject.lametoken" ]

.. _picfg_vasco_library:

VASCO library
.............

The :ref:`vasco_token` relies on a shared library of the vendor, which is not
part of privacyIDEA. Set the path to this library with ``PI_VASCO_LIBRARY``::

    PI_VASCO_LIBRARY = "/path/to/the/vendor/library.so"

Each worker process loads the library once. If the option is not set or the
library cannot be loaded, VASCO tokens cannot be used to authenticate.

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

   As of 3.14 no token types are in this state. Types that are *fully*
   removed (e.g. ``u2f`` in 3.14) are migrated by the schema update to
   ``tokentype='deprecated'`` and handled via ``pi-tokenjanitor deprecated``
   - see the developer note ``dev/token-deprecation-strategy.md``.

.. _picfg_allowed_ssh_key_types:

Allowed SSH key types
.....................

.. versionadded:: 3.14

The SSH key token only accepts a set of well known SSH key types (``ssh-rsa``,
``ssh-ed25519``, ``ecdsa-sha2-nistp256``,
``sk-ecdsa-sha2-nistp256@openssh.com`` and
``sk-ssh-ed25519@openssh.com``). If you need to enroll SSH keys of other
types, you can add them as a list in ``pi.cfg``::

    PI_ALLOWED_SSH_KEY_TYPES = ['ssh-dss', 'ecdsa-sha2-nistp521']


The configured key types are added to the default key types. privacyIDEA does
not evaluate the key type itself, the SSH server decides which key types it
accepts (see ``PubkeyAcceptedAlgorithms``).

.. _picfg_email_validators:

3rd party email validators
--------------------------

privacyIDEA can use email validators while enrolling email tokens via validate/check.
You can configure your own email validators in the ``pi.cfg``::

    PI_EMAIL_VALIDATOR_MODULES = [ "myproject.emailvalidator", "otherproject.nogmail" ]

This module needs to provide a function ``validate_email(email: str) -> bool`` which returns True if the
email is valid.

The email validator module that comes with privacyIDEA is ``privacyidea.lib.utils.emailvalidation``.
You do not need to add this in the ``pi.cfg`` file, this is available by default.

Listing a module in ``PI_EMAIL_VALIDATOR_MODULES`` only makes it available. To use it,
select it in the enrollment policy :ref:`email_validation <policy_email_validate>`; without
such a policy the module that comes with privacyIDEA is used. A module that can not be
imported is written to the log as a warning and is not offered in the policy.


.. _custom_web_ui:

Custom Web UI
-------------

You can configure privacyIDEA to use your own WebUI, which is completely different and stored at another location.

You can do this using the following config values::

    PI_INDEX_HTML = "myindex.html"
    PI_STATIC_FOLDER = "mystatic"
    PI_TEMPLATE_FOLDER = "mystatic/templates"

In this example the file ``mystatic/templates/myindex.html`` would be loaded
as the initial single page application, and its assets would be served from
``mystatic`` under the unchanged URL ``/static/``.

Both paths are relative to the ``privacyidea`` package directory. They are also how the
WebUI privacyIDEA ships is selected, see :ref:`new_webui`: the folder that is served is
``static/`` and the one privacyIDEA renders its own pages from is ``static_old/templates/``.


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

Each workload has its own feature flag and stays off by default.

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

With ``PI_REDIS_CACHE_CHALLENGES``, the list of all challenges - the challenge
list of the WebUI and ``GET /token/challenges/`` without an exact serial or
transaction ID - is read from the database, so it shows only the challenges
that were written there while Redis could not be reached. The challenges of one
token, one transaction ID or one user are read from Redis as usual.

If ``PI_REDIS_URL`` is not set, every cache call degrades to a no-op and
privacyIDEA behaves exactly as a database-only deployment.

In a Docker deployment, the URL can be loaded from a secret file via
``PI_REDIS_URL_FILE`` (e.g. ``/run/secrets/redis_url``) instead of being passed
in the environment.

In a setup with several nodes, all of them must use the same Redis (the same
``PI_REDIS_URL``) and the same ``PI_REDIS_CACHE_*`` settings. With
``PI_REDIS_CACHE_CHALLENGES`` challenges are kept only in Redis, so a node with
another Redis or without the setting does not find a challenge that another node
created, and the second request of a challenge-response or push login fails when
it reaches that node. See :ref:`ha_setups`.

.. _redis_user_cache:

User cache
..........

.. index:: user cache, Redis

``PI_REDIS_CACHE_USERS`` caches the answers privacyIDEA gets from its user
stores: the user ID behind a login name, the login name behind a user ID, and a
user's attributes. Every one of those is a round trip to an external system - an
LDAP search, an SQL query, an HTTP call - and the answers change rarely, so
serving them from Redis removes most of the user store traffic from
authentication and from listing tokens.

Unlike the two other user caches, this one is shared: the
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
* an admin deletes the user cache (``DELETE /system/user-cache``, or *Delete
  User Cache* in the system configuration of the WebUI) - everything goes.

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
....................

.. index:: AuthCache, Authentication Cache, Redis

``PI_REDIS_CACHE_AUTH`` moves the entries of the :ref:`policy_auth_cache` policy
from the ``authcache`` table into Redis.

That table is written to on the authentication path in three directions: an
``UPDATE`` on every cache *hit* to count the use, an ``INSERT`` per successful
authentication, and ``DELETE`` statements for entries that turn out to be stale.
With Redis enabled none of that reaches the database.

An entry is accepted only within the policy's first interval (the ``4h`` in
``4h/5m``), counted from the *first* authentication, so using an entry does not
extend its life. All entries of a user are kept under one Redis key, whose
lifetime is extended to that of the user's longest-lived entry. An entry that is
past its interval is no longer accepted, but it stays in Redis until a later
authentication of the user removes it or the key expires.
``PI_REDIS_AUTH_CACHE_TTL`` (default 3600 seconds) is only a fallback for a
caller that cannot name a window.

Two consequences worth knowing:

* The ``pi-manage config authcache cleanup`` command only has the entries left
  to remove that were written to the database while Redis could not be reached:
  once Redis answers again, nothing reads or deletes them. Keep its cron job
  (see :ref:`cleanup_jobs`) for those.
* The database-backed cache never bounded how many entries a user accumulated,
  and every lookup verifies the presented password against each of them with
  the configured key derivation function - so the cache got slower the more it
  was used. Per-entry expiry bounds
  that set.

Like the other workloads it degrades safely: if Redis cannot be reached the
database takes over, and a lost entry costs one real authentication against the
token or the user store, nothing else.

.. _redis_health_cache:

Certificate health results
..........................

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

With Redis, each worker reads the shared results first and keeps a local copy
only as a fallback for when Redis cannot be reached (or while another worker is
probing). The TTL is the same for both, and saving or deleting a resolver drops
the shared copy, so one admin's change reaches every worker instead of only the
one that served the request.

Nothing here is on the authentication path and the results only feed a display,
so if Redis cannot be reached the worker simply probes for itself, exactly as it
did before.

.. _redis_cache_security:

Security
........

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

A ``rediss://`` URL verifies the server certificate and the host name by
default (``ssl_cert_reqs=required``), against the system CA store and the CA
file given in ``ssl_ca_certs``. Do not set ``ssl_cert_reqs=none`` in production.

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
* Authentication cache entries are **encrypted** the same way. An entry holds a
  hash of the user's password, made with the algorithm and the parameters that
  ``PI_HASH_ALGO_LIST`` and ``PI_HASH_ALGO_PARAMS`` configure, which could be
  attacked offline if it leaked in the clear. Note that, exactly as with the database-backed cache, a
  password changed in the user store stays usable until its entry expires, so
  keep the :ref:`policy_auth_cache` window short enough to live with that.
* Certificate health results are stored as plaintext. They hold no credentials,
  but they do name your internal LDAP and Keycloak hosts and their certificate
  subjects, which is one more reason not to expose the Redis instance.

Because the encryption uses the privacyIDEA encryption key, cached entries
written before an encryption key rotation can no longer be read afterwards.
Such entries are treated as a cache miss: an open challenge has to be started
again, a user cache entry is replaced by a new lookup in the user store, and a
cached authentication by one real authentication. Unreadable challenges expire
with their validity, unreadable user cache entries are deleted when they are
read, and unreadable authentication cache entries stay until the user's cache
key expires (see :ref:`redis_auth_cache`).

.. _redis_cache_upgrades:

Upgrades and payload compatibility
..................................

privacyIDEA does not support rolling upgrades on the SQL side (the schema
migration step expects a single writer), so the Redis cache does not need to
clear a higher bar. The policy below applies whenever the cache is enabled.

**Within a single key prefix** (e.g. ``pi:challenge:v1:``), the payload may
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
hand-edited key), the read is treated as a cache miss and a warning is written
to the log. For Redis-only storage like challenges, the
user-visible outcome is "challenge not found, please try again." The cache
itself never crashes the worker.

Cache-aside workloads such as the :ref:`redis_user_cache` are backed by an
authoritative source: an entry that cannot be read is answered by that source
and cached again, so a change of their payload costs nothing but a few extra
lookups.

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
strict, fail-secure behavior (no grace: any stale counter is treated as theft).
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

.. _ini_conditional_access_never_block:

Conditional access never-block list
-----------------------------------

.. index:: conditional access, lock, never-block

The conditional access policies can block a source IP (the ``BLOCK_IP``
action). ``PI_CONDITIONAL_ACCESS_NEVER_BLOCK`` lists the addresses and networks
that must never be blocked by that machinery::

    PI_CONDITIONAL_ACCESS_NEVER_BLOCK = ["10.0.0.0/8", "192.0.2.15"]

The value is either a list of entries or a single string of entries separated by
commas or whitespace. Each entry is a CIDR network or a bare IP address; an entry
that cannot be parsed is written to the log and ignored. Loopback (``127.0.0.0/8``
and ``::1/128``) is always on the list and cannot be removed. Blocking it would
lock out a reverse proxy running on the same host, and when ``OverrideAuthorizationClient``
(see :ref:`override_client`) is unset every client is seen as that proxy.

An IPv4 entry also covers the IPv4-mapped form of the same address
(``::ffff:10.0.0.1`` for ``10.0.0.1``), which is what a dual-stack listener
reports for an IPv4 client, so an IPv4 network does not have to be listed twice.
Tunnel encodings that merely carry an IPv4 address (6to4, Teredo) are not
covered: unlike the mapped form, those are chosen by the client rather than by
the operating system.

Put the addresses of your reverse proxies, load balancers, NAT gateways and
management networks here. Blocking shared infrastructure locks out everyone
behind it.

The list wins over an existing block: if an IP is already blocked and is added to
this list afterwards, the block is no longer enforced, and the block entry itself
is removed the next time that IP authenticates. Removing the IP from the list
again does not bring the old block back.

This setting can **only** be configured on the server, either in ``pi.cfg`` or
through the ``PRIVACYIDEA_PI_CONDITIONAL_ACCESS_NEVER_BLOCK`` environment
variable, which is the usual path in a container::

    PRIVACYIDEA_PI_CONDITIONAL_ACCESS_NEVER_BLOCK='["10.0.0.0/8", "192.0.2.15"]'

The environment variable is read as JSON where possible and otherwise taken as a
plain string, so both a JSON list and ``10.0.0.0/8,192.0.2.15`` work.

Set the list in one place only. The two sources do not merge, and which one wins
depends on the entry point: the standard server reads ``pi.cfg`` after the
environment, so the file wins, while the container entry point reads the
environment last, so there the variable wins.

It is deliberately not a system setting, and there is no WebUI or API for it, so
that neither a change through the API nor a mistaken conditional access policy
can remove an address from it. It keeps the listed addresses from being blocked
by IP (``BLOCK_IP`` and the ``DENY`` of a policy that targets the source IP); it
does not lift a user lock or the ``DENY`` of a policy that targets the user.
Changes take effect after a restart of the web server.

.. versionadded:: 3.14

.. _picfg_further_keys:

Further keys
------------

These keys are described on the pages where they are used:

* ``PI_CHECK_RELOAD_CONFIG``: :ref:`performance`
* ``PI_LDAP_POOLING_LOOP_TIMEOUT``: :ref:`ldap_resolver`
* ``PI_HSM_MODULE`` and its ``PI_HSM_MODULE_*`` parameters: :ref:`securitymodule`
* ``PI_GNUPG_HOME``: :ref:`import`
* ``PI_AUDIT_SQL_COLUMN_LENGTH``: :ref:`audit_table_size`;
  ``PI_AUDIT_CONTAINER_READ`` and ``PI_AUDIT_CONTAINER_WRITE``:
  :ref:`container_audit`; ``PI_AUDIT_LOGGER_QUALNAME``: :ref:`logger_audit`
* ``PI_SCRIPT_HANDLER_DIRECTORY``: :ref:`scripthandler`
* ``PI_NOTIFICATION_HANDLER_SPOOLDIRECTORY``: :ref:`usernotification`
* ``PI_SCRIPT_SMSPROVIDER_DIRECTORY``: :ref:`sms_gateway_config`
* ``PI_LOGO`` and ``PI_PAGE_TITLE``: :ref:`customize`; ``PI_CUSTOMIZATION``:
  :ref:`pi_customization`

Keys of the previous WebUI (see :ref:`legacy_webui`), which the WebUI
privacyIDEA serves does not read:

* ``PI_EXTERNAL_LINKS`` (default ``True``): set it to ``False`` to hide the
  links to the support page and the community forum.
* ``PI_CUSTOM_CSS`` (default ``False``): set it to ``True`` to load
  ``css/custom.css`` from the ``PI_CUSTOMIZATION`` folder.

``PI_INITIALIZE_HSM`` (default ``False``) is read by the Docker image only. With
``True`` the security module is initialized when the container starts instead of
at the first request that needs it, like the ``initialize_hsm`` parameter of the
WSGI script of a normal installation (see :ref:`securitymodule`). It can be set
in ``pi.cfg`` or as ``PRIVACYIDEA_PI_INITIALIZE_HSM=true``.

The Docker image also reads environment variables without the ``PRIVACYIDEA_``
prefix: the database settings ``PI_DB_DRIVER``, ``PI_DB_USER``,
``PI_DB_PASSWORD``, ``PI_DB_HOST``, ``PI_DB_PORT``, ``PI_DB_NAME`` and
``PI_DB_EXTRA_PARAMS``, ``PI_SECRET_KEY`` as another name for ``SECRET_KEY``,
and for ``SQLALCHEMY_DATABASE_URI``, ``PI_DB_PASSWORD``, ``PI_PEPPER``,
``SECRET_KEY`` and ``PI_REDIS_URL`` a ``*_FILE`` variant that names a file
holding the value. They are described in ``deploy/docker/README.Docker.md`` in
the source tree. The image refuses to start if ``PI_ENCFILE`` does not name a
readable file or ``PI_PEPPER`` is not set. Without ``SECRET_KEY`` it generates a
random key, and without ``PI_AUDIT_KEY_PRIVATE`` and ``PI_AUDIT_KEY_PUBLIC`` it
switches off the signing of the audit log and of the responses.

In a normal installation, ``ProductionConfig`` in ``privacyidea/config.py``
takes ``SECRET_KEY``, ``DATABASE_URL`` (the database URI) and ``PI_REDIS_URL``
from environment variables of the same name, without the ``PRIVACYIDEA_``
prefix; a value in ``pi.cfg`` overrides them.
The environment variable ``PI_CONFIG_NAME`` overrides the set of defaults the
WSGI script selects (``config_name="production"``); it is meant for development
and tests.
