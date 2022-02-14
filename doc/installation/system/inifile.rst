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
   # Truncate Audit entries to fit into DB columns
   PI_AUDIT_SQL_TRUNCATE = True
   # PI_LOGFILE = '....'
   # PI_LOGLEVEL = 20
   # PI_INIT_CHECK_HOOK = 'your.module.function'
   # PI_CSS = '/location/of/theme.css'
   # PI_UI_DEACTIVATED = True


.. note:: The config file is parsed as python code, so you can use variables to
   set the path and you need to take care for indentations.

``SQLALCHEMY_DATABASE_URI`` defines the location of your database.
You may want to use the MySQL database or Maria DB. There are two possible
drivers, to connect to this database. Please read :ref:`mysqldb`.

``SQLALCHEMY_ENGINE_OPTIONS`` is a dictionary of keyword args to send
to `create_engine() <https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy
.create_engine>`_. The ``max_identifier_length`` is the database’s
configured maximum number of characters that may be used in a SQL identifier
such as a table name, column name, or label name. For Oracle version 19 and above
the `max_identifier_length <https://docs.sqlalchemy.org/en/14/core/engines
.html#sqlalchemy.create_engine.params.max_identifier_length>`_ should be set to 128.


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

privacyIDEA digitally signs the responses. You can disable this using the
parameter ``PI_NO_RESPONSE_SIGN``. Set this to *True* to suppress the
response signature.

You can set ``PI_UI_DEACTIVATED = True`` to deactivate the privacyIDEA UI.
This can be interesting if you are only using the command line client or your
own UI and you do not want to present the UI to the user or the outside world.

.. note:: The API calls are all still accessible, i.e. privacyIDEA is
   technically fully functional.

The parameter ``PI_TRANSLATION_WARNING`` can be used to provide a prefix, that is
set in front of every string in the UI, that is not translated to the language your browser
is using.

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

Audit parameters
----------------

``PI_AUDIT_MODULE`` lets you specify an alternative auditing module. The
default which is shipped with privacyIDEA is
``privacyidea.lib.auditmodules.sqlaudit``. There is no need to change this,
unless you know exactly what you are doing.

You can change the servername of the privacyIDEA node, which will be logged
to the audit log using the variable ``PI_AUDIT_SERVERNAME``.

You can run the database for the audit module on another database or even
server. For this you can specify the database URI via ``PI_AUDIT_SQL_URI``.

``PI_AUDIT_SQL_TRUNCATE = True`` lets you truncate audit entries to the length
of the database fields.

In certain cases when you experiencing problems you may use the parameters
``PI_AUDIT_POOL_SIZE`` and ``PI_AUDIT_POOL_RECYCLE``. However, they are only
effective if you also set ``PI_ENGINE_REGISTRY_CLASS`` to ``"shared"``.

If you by any reason want to avoid signing audit entries you can
set ``PI_AUDIT_NO_SIGN = True``. If ``PI_AUDIT_NO_SIGN`` is set to ``True``
audit entries will not be signed and also the signature of audit entries will not be
verified. Audit entries will appears with *signature* *fail*.

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


privacyIDEA Nodes
-----------------

privacyIDEA can run in a redundant setup. For statistics and monitoring purposes you
can give these different nodes, dedicated names.

``PI_NODE`` is a string with the name of this very node. ``PI_NODES`` is a list of
all available nodes in the cluster.

If ``PI_NODE`` is not set, then ``PI_AUDIT_SERVERNAME`` is used as node name.
If this is also not set, the node name is returned as "localnode".

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

.. _picfg_3rd_party_tokens:

3rd party token types
---------------------

You can add 3rd party token types to privacyIDEA. Read more about this
at :ref:`customize_3rd_party_tokens`.

To make the new token type available in privacyIDEA,
you need to specify a list of your 3rd party token class modules
in ``pi.cfg`` using the parameter ``PI_TOKEN_MODULES``::

    PI_TOKEN_MODULES = [ "myproject.cooltoken", "myproject.lametoken" ]

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

