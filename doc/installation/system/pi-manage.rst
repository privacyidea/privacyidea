.. _pimanage:

The pi-manage Script
====================

.. index:: pi-manage

*pi-manage* is the command line tool that sets up the database during the
installation and manages the privacyIDEA server afterwards.

.. note:: pi-manage does not need the server to run, as it acts directly on
   the database. Therefore you need read access to /etc/privacyidea/pi.cfg and
   the encryption key.

If you want to use a config file other than /etc/privacyidea/pi.cfg, you can
set an environment variable::

   PRIVACYIDEA_CONFIGFILE=/home/user/pi.cfg pi-manage

pi-manage takes a command, often one or two levels of sub commands, and their
options::

   pi-manage <command> [<subcommand> ...] [<options>]

For example ``pi-manage config challenge cleanup --dryrun``. Every level lists
its commands and options with ``-h``, e.g. ``pi-manage config -h``.
``pi-manage --version`` shows the versions of privacyIDEA, Python and Flask.

In the Docker deployment pi-manage runs in the container of the ``pi``
service, see ``deploy/docker/README.Docker.md`` in the source tree.

The commands are grouped as follows. The cleanup commands among them have to
run regularly, see :ref:`cleanup_jobs`.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Command
     - Purpose
   * - ``setup``
     - Create the encryption key, the audit keys and the database tables, see
       :ref:`pimanage_setup`.
   * - ``admin``
     - Manage the local administrators, see :ref:`pimanage_admin`.
   * - ``db``
     - Run the database schema migrations, see :ref:`pimanage_db`.
   * - ``backup``
     - Back up and restore the database and the configuration, see
       :ref:`pimanage_backup`.
   * - ``audit``
     - Rotate and dump the audit log, see :ref:`pimanage_audit`.
   * - ``config challenge``, ``config remembered_device``,
       ``config authcache``, ``authlog``, ``config metrics``
     - Delete expired or old entries, see :ref:`pimanage_challenge`,
       :ref:`pimanage_remembered_device`, :ref:`pimanage_authcache`,
       :ref:`pimanage_authlog` and :ref:`pimanage_metrics`.
   * - ``config policy``
     - List, enable, disable, create and delete policies, see
       :ref:`pimanage_policy`.
   * - ``conditionalaccess``
     - Manage conditional access policies, locks and IP blocks, see
       :ref:`pimanage_conditional_access`.
   * - ``config realm``, ``config resolver``, ``config event``, ``config ca``,
       ``config hsm``
     - Manage realms, resolvers, events, CA connectors and HSM keys, see
       :ref:`pimanage_config_objects`.
   * - ``token``
     - Import tokens from a file, see :ref:`pimanage_token_import`.
   * - ``api``
     - Create API keys (deprecated), see :ref:`pimanage_api_keys`.
   * - ``config export``, ``config import``
     - Export and import the server configuration, see
       :ref:`pimanage_config_export`.
   * - ``run``, ``shell``, ``routes``
     - Development tools of the web framework, see :ref:`pimanage_development`.

.. _pimanage_setup:

Setting up a New Installation
-----------------------------

``pi-manage setup`` creates the keys and the database tables of a new
installation. The :ref:`installation guides <installation>` tell you when to
run which command.

Encryption key
~~~~~~~~~~~~~~

Create the encryption key::

   pi-manage setup create_enckey

The file name of the encryption key is read from ``PI_ENCFILE`` in the
configuration. An existing key file is never overwritten: the command refuses
and exits with an error. The new file gets the permissions ``0400``; make sure
it is owned by the user privacyIDEA runs as.

The key can also be passed with ``--enckey_b64``. This is not recommended, as
the key then ends up in the shell history. The value must be the base64
encoding of exactly 96 bytes (128 characters).

You can also encrypt the encryption key with a passphrase. The command asks
for the passphrase (or takes it from ``--password``) and writes the encrypted
key to standard output or to the file given with ``-o``::

   pi-manage setup encrypt_enckey /etc/privacyidea/enckey -o /etc/privacyidea/enckey.enc

Point ``PI_ENCFILE`` to the encrypted file. The server recognises an encrypted
key and waits for the passphrase after every start. pi-manage cannot ask for
it, so while the key is encrypted, commands that have to encrypt or decrypt
data fail. Read more about the database encryption and the *enckey* in
:ref:`securitymodule`.

Audit signing keys
~~~~~~~~~~~~~~~~~~

::

   pi-manage setup create_audit_keys

creates the RSA key pair that signs the audit entries, in the files given by
``PI_AUDIT_KEY_PRIVATE`` and ``PI_AUDIT_KEY_PUBLIC``. ``-k`` sets the key size
in bits (default ``2048``). An existing private key is not overwritten.

Database tables
~~~~~~~~~~~~~~~

::

   pi-manage setup create_tables

creates the tables in the database given by ``SQLALCHEMY_DATABASE_URI``. The
database itself has to exist; only an SQLite database file is created.
Afterwards the database is stamped with the newest schema revision, so that
later upgrades know where to start. ``-n`` skips the stamp.

.. warning:: Run ``create_tables`` only on an empty database. On the database
   of an older privacyIDEA version it only adds the missing tables, leaves the
   existing ones unchanged and then stamps the newest revision, so the schema
   migrations of the upgrade are skipped. Upgrade an existing database with
   ``pi-manage db upgrade``, see :ref:`pimanage_db`.

PGP keys
~~~~~~~~

::

   pi-manage setup create_pgp_keys

creates the GPG key pair privacyIDEA uses to decrypt GPG encrypted token seed
files, see :ref:`import`. The keys are stored in ``PI_GNUPG_HOME`` (default
``/etc/privacyidea/gpg``) without a passphrase, so restrict the access to this
directory. The command refuses if there is a private key already; ``-f``
generates an additional key and keeps the existing ones. ``-k`` sets the key
size in bits (default ``2048``).

Dropping all tables
~~~~~~~~~~~~~~~~~~~

::

   pi-manage setup drop_tables --dropit yes

.. warning:: This drops every privacyIDEA table in the database, with all
   tokens and the complete configuration. There is no confirmation question.
   Without ``--dropit yes`` the command does nothing.

.. _pimanage_admin:

Local Administrators
--------------------

.. index:: admin accounts

Local administrators are stored in the privacyIDEA database and log in to the
WebUI with their name and password, see :ref:`faq_admins`::

   pi-manage admin add <name> [-e <email>]
   pi-manage admin list
   pi-manage admin change <name> [-e <email>]
   pi-manage admin delete <name>

``add`` and ``change`` ask for the password twice, unless it is given with
``-p`` (``add``) or ``--password`` (``change``), which leaves it in the shell
history. ``change`` always sets the password, so enter the current one again
to change only the email address. ``delete`` does not ask for confirmation.

A local administrator locked by :ref:`conditional access <conditional_access>`
is unlocked with ``pi-manage conditionalaccess unlock-user <name> --admin``,
see :ref:`conditional_access_local_admins`.

.. _pimanage_db:

Database Migrations
-------------------

.. index:: database migration, schema upgrade

``pi-manage db`` runs the schema migrations of the privacyIDEA database. An
upgrade runs them for you through ``privacyidea-schema-upgrade``, see
:ref:`upgrade`. To check or run them by hand::

   pi-manage db current     # the revision the database is at
   pi-manage db heads       # the newest revision of the installed version
   pi-manage db upgrade     # migrate the database to the installed version

The migration directory is found automatically. If it is not, e.g. in an
editable installation, pass it with ``-d``::

   pi-manage db upgrade -d /opt/privacyidea/lib/python3.X/site-packages/privacyidea/migrations

``db stamp <revision>`` only records a revision in the database without
running any migration; a wrong stamp makes later upgrades skip or repeat
migrations. ``db downgrade <revision>`` reverts migrations and can drop tables
and columns with their data. A relative revision has to follow ``--``, e.g.
``pi-manage db downgrade -- -1``.

.. warning:: ``init``, ``revision``, ``migrate``, ``merge`` and ``edit`` create
   or change migration scripts. They are meant for the development of
   privacyIDEA and must not be used on an installation.

.. _pimanage_backup:

Backup and Restore
------------------

.. index:: Backup, Restore

Creating a backup
~~~~~~~~~~~~~~~~~

::

   pi-manage backup create

writes an archive with a dump of the privacyIDEA database and the complete
configuration directory */etc/privacyidea* to
*/var/lib/privacyidea/backup/privacyidea-backup-<YYYYMMDD-HHMM>.tgz*, readable
only by its owner. The options are:

* ``-e``/``--enckey`` adds the encryption key. Without it the key file is left
  out, and you have to keep a copy of it elsewhere.
* ``-d <directory>`` writes the archive to another directory.
* ``-c <directory>`` backs up another configuration directory.
* ``-r <directory>`` also adds a FreeRADIUS configuration directory.

.. warning:: If the backup includes the database dump and the encryption key
   all seeds of the OTP tokens can be read from the backup.

An archive created with ``--enckey`` is all you need to restore the
installation, with these limits:

* Only the database of ``SQLALCHEMY_DATABASE_URI`` is dumped. An audit log in
  a database of its own (``PI_AUDIT_SQL_URI``, see :ref:`audit_parameters`) is
  not part of the backup.
* The restore needs a configuration file named *pi.cfg* in the backed up
  configuration directory. A configuration file that lives elsewhere or has
  another name (see ``PRIVACYIDEA_CONFIGFILE`` above) is not backed up, and
  the archive cannot be restored.
* The encryption key is only included if its file (``PI_ENCFILE``) is in the
  backed up configuration directory.

The Docker deployment keeps its configuration in environment variables and
secret files and comes with its own backup and restore scripts, see
``deploy/docker/README.Docker.md`` in the source tree.

Supported databases
~~~~~~~~~~~~~~~~~~~

SQLite, MySQL/MariaDB and PostgreSQL are supported. Other databases, such as
Oracle or MSSQL, are not: ``backup create`` and ``backup restore`` exit with an
error, so use the backup tools of the database instead. The database is dumped
and restored with the command line tools of the respective database, which have
to be installed on the privacyIDEA machine:

.. list-table::
   :header-rows: 1

   * - Database
     - Commands used
     - Debian/Ubuntu package
   * - SQLite
     - none, the database file is copied
     - --
   * - MySQL/MariaDB
     - ``mysqldump``, ``mysql``
     - *mariadb-client* or *mysql-client*
   * - PostgreSQL
     - ``pg_dump``, ``psql``
     - *postgresql-client*

For PostgreSQL the client has to be at least as new as the server it connects
to. Dumping a PostgreSQL 17 server with the ``pg_dump`` of an older major
version fails, so install the *postgresql-client-<version>* package that
matches your server.

Restoring
~~~~~~~~~

The restore overwrites the contents of the database the restored *pi.cfg*
points to::

   pi-manage backup restore /var/lib/privacyidea/backup/privacyidea-backup-<YYYYMMDD-HHMM>.tgz

It does not create the database: the database and the database user have to
exist already, as they do on a machine that has been set up before. Only the
contents are replaced.

.. warning:: The restore extracts every file of the archive to its original
   path and overwrites the file there: the configuration directory with
   *pi.cfg*, the encryption key if the archive contains it, and a FreeRADIUS
   directory. Run it as a user that may write these files, usually root. If the
   archive contains no encryption key, the restore warns about it; put the key
   back in place yourself.

.. note:: The archive also contains the *pi.cfg* of the machine the backup was
   taken on, including its ``SQLALCHEMY_DATABASE_URI``. If you restore onto a
   machine whose database is reached under a different URI, use
   ``--keep-db-uri`` to keep the URI of the running installation instead of
   the one from the backup.

.. warning:: On MySQL/MariaDB the dump contains the name of the database it was
   taken from and creates that database if it is missing, so the restore always
   writes into a database of that name - also with ``--keep-db-uri``, which
   only changes the server, the credentials and the port that are connected to.
   Restore a MySQL/MariaDB backup only into an installation that uses the same
   database name, otherwise the data ends up in a newly created copy of the
   original database while the configured one stays untouched.

A backup can only be restored into the database engine it was taken with
(SQLite, MySQL/MariaDB or PostgreSQL): a dump written by one engine cannot be
read by another one. If the configured database uses a different engine, the
restore aborts before it changes any file or the database. It does the same if
the archive lacks *pi.cfg* or the database dump, if the *pi.cfg* in the archive
names no database, or if the client command for the restore is not installed.

.. _pimanage_audit:

Audit Log
---------

Rotating the audit log
~~~~~~~~~~~~~~~~~~~~~~

Audit logs are written to the database. You can use pi-manage to perform a
log rotation::

   pi-manage audit rotate

You can specify a highwatermark and a lowwatermark (``-hw``, ``-lw``), an age
in days (``--age``) or a config file (``--config``). ``--dryrun`` only reports
how many entries would be deleted, ``--chunksize`` deletes in batches. The
command only works with the SQL audit module. Read more about it at
:ref:`cleaning up audit entries <audit_rotate>`.

.. warning:: Without options, ``audit rotate`` deletes all but the newest 5000
   entries once there are more than 10000.

Dumping the audit log
~~~~~~~~~~~~~~~~~~~~~

``pi-manage audit dump`` writes the audit log as CSV to standard output or to
the file given with ``-f``. ``-t`` limits it to the recent entries, given as a
number with one of the units ``s``, ``m``, ``h``, ``d`` or ``y``, e.g. ``-t 5d``
for the last five days::

   pi-manage audit dump -t 30d -f audit.csv

.. _pimanage_challenge:

Clean up challenges
-------------------

The challenges of challenge-response tokens are stored in a database table.
Each challenge has a validity time. Challenges which haven't been answered,
persist in the database until they are cleaned up. The Ubuntu packages and the
Docker image do this for you, see :ref:`cleanup_jobs`. To clean up all expired
challenges use::

   pi-manage config challenge cleanup

To clean up challenges older than a certain age (in minutes), use the parameter
``--age``::

   pi-manage config challenge cleanup --age 10

This will clean up challenges that were created more than 10 minutes ago, also
those that are still valid, such as a push challenge that is still waiting for
its answer. ``--age 0`` deletes all challenges.

Use ``--chunksize`` to avoid deadlocks when cleaning up a large challenge table.
To get only the number of challenges which would be deleted, use ``--dryrun``.

Challenges kept in Redis (see :ref:`redis_cache`) expire on their own. The
command does not touch them, so in a deployment that keeps all challenges in
Redis it reports 0 deleted entries.

.. _pimanage_remembered_device:

Clean up remembered devices
---------------------------

Devices remembered through the :ref:`policy_remember_device` policy stay in
the database after they expire. To delete the expired ones use::

   pi-manage config remembered_device cleanup

``--chunksize`` deletes in batches, ``--dryrun`` only reports how many entries
would be deleted. The Ubuntu packages and the Docker image run this daily, see
:ref:`cleanup_jobs`.

.. _pimanage_authcache:

Clean up the authentication cache
---------------------------------

::

   pi-manage config authcache cleanup

deletes the entries of the authentication cache that no active
:ref:`policy_auth_cache` policy accepts any more, i.e. those that have not been
used for longer than the most generous policy allows. Without such a policy it
deletes all entries. ``-m``/``--minutes`` instead deletes all entries that have
not been used for the given number of minutes.

With the :ref:`redis_auth_cache` enabled, cached authentications expire in
Redis on their own; the command then only deletes the entries that were written
to the database while Redis could not be reached. The Ubuntu packages and the
Docker image run this daily, see :ref:`cleanup_jobs`.

.. _pimanage_authlog:

Clean up the authentication log
-------------------------------

.. index:: retention time

The :ref:`authentication_log` records every authentication request and is not
pruned automatically, so its retention period is enforced by a cron job running::

   pi-manage authlog cleanup --age 365

``--age`` is required and is given in days: the command deletes every entry
older than that, together with the classified reasons and the conditional-access
outcomes recorded on those entries. As with the challenge cleanup, ``--chunksize``
deletes in batches to avoid long locks on a large table, and ``--dryrun`` only
reports how many entries would be removed.

Keep the retention period comfortably longer than the longest time window used
by a conditional access policy - deleted entries no longer count towards its
thresholds, see :ref:`authentication_log_cleanup`. The Ubuntu packages ship this
job commented out, see :ref:`cleanup_jobs`.

.. _pimanage_metrics:

Clean up metrics
----------------

.. index:: metrics, metric_aggregate

The ``metric_aggregate`` table behind the *Resolver Timing* and *Notification
Delivery* panels of the :ref:`dashboard` gains rows every five minutes. To delete
the rows older than 24 hours use::

   pi-manage config metrics cleanup

``--older-than-hours`` sets a different age, at least ``1`` so that the window
still being written is kept. ``--dryrun`` only reports how many rows would be
removed. The Ubuntu packages and the Docker image run this daily, see
:ref:`cleanup_jobs`.

.. _pimanage_policy:

Policies
--------

``pi-manage config policy`` works without the WebUI, so it is the way back in
when an admin policy has locked you out of it::

   pi-manage config policy list
   pi-manage config policy disable <name>
   pi-manage config policy enable <name>
   pi-manage config policy delete <name>
   pi-manage config policy create <name> <scope> <action> [-f <file>]

``delete`` does not ask for confirmation. ``create`` creates an active policy
with the given scope and a comma separated list of actions, without any realm,
user, client or time condition, e.g.::

   pi-manage config policy create helpdesk admin "tokenlist, enable, disable"

With ``-f`` the policy is read from a file that contains a Python dictionary
with the attributes of the policy, e.g. ``realm``, ``adminrealm`` or
``active``. The ``name``, ``scope`` and ``action`` in the file take precedence
over the arguments, which still have to be given. If the policy cannot be
created, the command prints the error and exits with a non-zero status. To
transfer many policies use ``pi-manage config import``, see
:ref:`pimanage_config_export`.

Conditional access policies are managed with ``pi-manage conditionalaccess``,
see :ref:`pimanage_conditional_access`.

.. _pimanage_conditional_access:

Conditional Access
------------------

``pi-manage conditionalaccess`` manages the :ref:`conditional access
<conditional_access>` policies and the locks and IP blocks they produce. It is
the escape hatch when a policy has locked you out of the WebUI itself: you can
list the policies, disable one, put it into dry run or delete it, and lift the
locks and blocks that are in force::

   pi-manage conditionalaccess list-policies
   pi-manage conditionalaccess disable-policy <name>
   pi-manage conditionalaccess list-locked-users
   pi-manage conditionalaccess unlock-user <login> --realm <realm>
   pi-manage conditionalaccess clear-blocks

The commands are described in :ref:`conditional_access_policies_cli`,
:ref:`conditional_access_policies_lifting` and
:ref:`conditional_access_manual_restrictions`.
``purge-expired-blocks`` and ``purge-expired-locks`` remove the blocks and locks
that have run out; the Ubuntu packages and the Docker image run them daily, see
:ref:`cleanup_jobs`.

.. warning:: ``clear-blocks`` removes all IP blocks and ``clear-locks`` all
   user locks (with ``--realm`` only those of one realm), including the
   permanent ones and those set by hand. Both ask for confirmation, ``--yes``
   skips it. To lift a single block or lock use ``unblock-ip`` or
   ``unlock-user``.

.. _pimanage_config_objects:

Realms, Resolvers, Events, CA Connectors and HSM
------------------------------------------------

These commands cover the basic tasks. The complete configuration is edited in
the WebUI or transferred with ``pi-manage config import``, see
:ref:`pimanage_config_export`.

:ref:`Realms <realms>`::

   pi-manage config realm list
   pi-manage config realm create <name> [<resolver> ...]
   pi-manage config realm delete <name> [--delete-custom-attributes]
   pi-manage config realm set_default <name>
   pi-manage config realm clear_default

``list`` marks the default realm with ``*``. ``create`` replaces an existing
realm of the same name. ``delete`` refuses a realm that still has custom user
attributes and asks whether to delete them as well;
``--delete-custom-attributes`` deletes them without asking.

:ref:`Resolvers <useridresolvers>`::

   pi-manage config resolver list [-v]
   pi-manage config resolver create <name> <type> <file>
   pi-manage config resolver create_internal <name>

``list -v`` also prints the configuration of each resolver; only the values
named ``bindpw`` and ``password`` are masked. ``create`` reads the parameters
of the resolver from a file that contains a Python dictionary; ``<type>`` is
the resolver type, e.g. ``ldapresolver`` or ``sqlresolver``.
``create_internal`` creates an editable SQL resolver whose users are stored in
a new table ``users_<name>`` in the privacyIDEA database.

:ref:`Events <eventhandler>`::

   pi-manage config event list
   pi-manage config event enable <id>
   pi-manage config event disable <id>
   pi-manage config event delete <id>

Events are addressed by the ID that ``list`` shows. ``delete`` does not ask
for confirmation.

:ref:`CA connectors <caconnectors>`::

   pi-manage config ca list [-v]
   pi-manage config ca create <name> [-t <type>]
   pi-manage config ca create_crl <name> [-f]

``create`` with the default type ``local`` asks for the details of a new local
CA and creates its files as well, see :ref:`local_caconnector`.
``create_crl`` creates and publishes a new CRL if the current one is about to
expire; ``-f`` creates one in any case.

:ref:`Hardware security module <securitymodule>`::

   pi-manage config hsm create_keys

creates the three encryption keys on the AES hardware security module
configured with ``PI_HSM_MODULE`` and its ``PI_HSM_MODULE_*`` settings, and
prints the ``PI_HSM_MODULE_KEY_LABEL_*`` lines to add to *pi.cfg*.

.. _pimanage_token_import:

Importing Tokens
----------------

::

   pi-manage token import <file> [-t <realm>]

imports the tokens of a file in the :ref:`OATH CSV <import_oath_csv>` format.
A token whose serial exists already is updated with the data from the file.
``-t`` puts the tokens into a realm and can be given several times. The file
has to be plain text; GPG encrypted files and the other formats are imported
in the WebUI or through the API, see :ref:`import`.

.. _pimanage_api_keys:

API Keys
--------

.. deprecated:: 3.14
   The ``pi-manage api createtoken`` JWT API keys described here (and the
   :ref:`policy_api_key` policy) are deprecated and will be removed in a future
   release. The :ref:`api_clients` feature (``X-API-Key``) is intended to replace
   them — API clients are stored, individually revocable and rotatable, and
   auditable — but it does not yet cover every use of these JWTs.

You can use ``pi-manage`` to create API keys. API keys can be used to

1. secure the access to the ``/validate/check`` API or
2. access administrative tasks via the REST API.

Create an API key for ``/validate/check`` with::

   pi-manage api createtoken -r validate -u <name>

To require such a key on ``/validate/check``, define the
:ref:`policy_api_key` policy in scope ``authorization``.

To automate administrative REST API calls, create a key with the role
``admin``::

   pi-manage api createtoken -r admin -u <name>

``-u`` is required for both roles. An admin key acts as the administrator
``<name>`` in the realm ``API``; ``-R`` sets another realm. No administrator
account has to exist for it. As for every administrator, the key may do
everything as long as no admin policy is defined. Once there are admin
policies, it may only do what a policy with a matching administrative realm
and user allows, see :ref:`admin_policies`.

Send the key in the ``PI-Authorization`` header (or in ``Authorization``), see
:ref:`rest_auth`.

.. note:: The API key is valid for 365 days; ``-d`` sets another number of
   days. It is not stored on the server, but signed with the ``SECRET_KEY`` of
   *pi.cfg*. It cannot be revoked on its own: it stays valid until it expires
   or until ``SECRET_KEY`` is changed, which invalidates all API keys and logs
   out all WebUI sessions.

.. _pimanage_config_export:

Exporting and Importing the Configuration
-----------------------------------------

.. index:: Configuration export, Configuration import

Using ``pi-manage config export`` and ``pi-manage config import`` you can export
and import these parts of the server configuration: policies, resolvers, machine
resolvers, realms, events, periodic tasks, CA connectors, SMS gateways, SMTP,
RADIUS and privacyIDEA server definitions and the global configuration. Run
``pi-manage config export -h`` to see the list of available configuration types
on your installation.

Not included are tokens, local administrators, conditional access policies, API
clients, service IDs, token groups and container templates. Set these up on the
target instance separately.

This can be used to keep a versionable, human-readable copy of single
configuration objects, or to transfer a configuration from one privacyIDEA
instance to another - for example from a staging to a production system.

Export the complete configuration to a file::

   pi-manage config export -o backup.json

The export can be restricted to certain types with ``-t`` (which can be given
multiple times) and to a single object with ``-n``. The output format is chosen
with ``-f`` and can be ``json`` (default) or ``yaml``. To export only one
policy as YAML::

   pi-manage config export -t policy -n my_policy -f yaml -o my_policy.yaml

Importing works the other way round. The input format (JSON, YAML or a Python
dictionary) is detected automatically and is read from a file given with ``-i``
or from standard input::

   pi-manage config import -i backup.json

Existing configuration objects with the same name are overwritten, all other
existing configuration is kept as is. As with the export, ``-t`` and ``-n``
restrict the import to certain types or to a single object.

.. note:: In contrast to ``pi-manage backup``, the configuration export does not
   contain any tokens and is not a full disaster-recovery backup. It exports the
   *logical* configuration, which is portable between instances and - in most
   cases - between versions. Use ``pi-manage backup`` if you want a complete
   database dump to restore the very same instance.

.. warning:: By default the exported data contains decrypted secrets - for
   example the bind password of an LDAP resolver, the password of an SQL
   resolver, a RADIUS secret, an SMTP password or the password entries of the
   global configuration - in clear text, so that it can be imported into an
   instance with a different encryption key. Store the exported files in a
   secure location or use the ``--censor`` option described below.

.. versionchanged:: 3.14 The password entries of the global configuration are
   exported decrypted as well. An export written by an earlier version contains
   them encrypted with the key of its instance, and importing it stores them
   unusable, so set them again after importing such a file.

Censoring secrets on export
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you do not want the secrets to leave the server in clear text, use the
``--censor`` option. Every secret - resolver, machine resolver and CA connector
passwords, the RADIUS secret, the SMTP password and private key password,
secret-looking SMS gateway options and headers and the password entries of the
global configuration - is then replaced with the placeholder
``__CENSORED__``::

   pi-manage config export --censor -o config.json

A censored export is useful to

* share or review the configuration (for example in a version control system or
  attached to a support ticket) without disclosing any secret, and
* take a configuration snapshot of an instance that you can re-import into the
  *same* instance later, for example to roll back a change.

On import, ``__CENSORED__`` means "keep the stored secret unchanged". This only
works on the instance the data was exported from, because that is where the
original secrets still exist:

* When importing into the **same** instance, the existing secret is kept and the
  rest of the configuration is updated.
* When importing into a **different or fresh** instance, there is no stored
  secret to keep. A censored entry of the global configuration is not imported
  at all, and the other affected objects are created without a usable secret.
  You then have to set the passwords manually afterwards.

In other words: use the default (clear text) export to migrate a configuration
including its secrets to another instance, and use ``--censor`` to produce a
shareable artifact or a same-instance snapshot.

Importing a configuration that was exported from a different privacyIDEA version
may fail if it contains options that are no longer available - for example a
policy action of a token type that has been removed. In this case the affected
object is not imported while the rest of the configuration still is, and the
command exits with a non-zero status. You can use the ``--skip-invalid`` option
to drop the parts that are not valid for the running version and import the
remaining configuration::

   pi-manage config import -i backup.json --skip-invalid

Currently ``--skip-invalid`` is evaluated for policies, where it removes policy
actions that are not available in the running version. A policy that has no
valid action left after this is skipped.

.. _pimanage_development:

Development Commands
--------------------

``pi-manage run`` starts a development web server, ``pi-manage shell`` opens a
Python shell with the privacyIDEA application loaded and ``pi-manage routes``
lists the URL routes of the application. These commands come with the web
framework. The development server is not meant for production; run
privacyIDEA through a web server instead, see :ref:`wsgiscript`.

.. _pimanage_deprecated:

Deprecated Command Names
------------------------

Older guides use command names that still work, but print a deprecation
warning and are not listed by ``-h``. Use the current commands instead:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Deprecated
     - Current
   * - ``pi-manage createdb``, ``pi-manage create_tables``
     - ``pi-manage setup create_tables``
   * - ``pi-manage dropdb``, ``pi-manage drop_tables``
     - ``pi-manage setup drop_tables``
   * - ``pi-manage create_enckey``, ``encrypt_enckey``, ``create_audit_keys``,
       ``create_pgp_keys``
     - ``pi-manage setup <same name>``
   * - ``pi-manage rotate_audit``
     - ``pi-manage audit rotate``
   * - ``pi-manage realm``, ``resolver``, ``policy``, ``event``, ``ca``,
       ``authcache``, ``hsm``
     - ``pi-manage config <same name>``
   * - ``pi-manage config exporter``, ``pi-manage config importer``
     - ``pi-manage config export``, ``pi-manage config import``
   * - ``pi-manage runserver``
     - ``pi-manage run``
