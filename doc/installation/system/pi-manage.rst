.. _pimanage:

The pi-manage Script
====================

.. index:: pi-manage

*pi-manage* is the script that is used during the installation process to
setup the database and do many other tasks.

.. note:: The interesting thing about pi-manage is, that it does not need
   the server to run as it acts directly on the database.
   Therefor you need read access to /etc/privacyidea/pi.cfg and the encryption
   key.

If you want to use a config file other than /etc/privacyidea/pi.cfg, you can
set an environment variable::

   PRIVACYIDEA_CONFIGFILE=/home/user/pi.cfg pi-manage

pi-manage always takes a command and sometimes a sub command::

   pi-manage <command> [<subcommand>] [<parameters>]

For a complete list of commands and sub commands use the *-h* parameter.

You can do the following tasks.

Encryption Key
--------------

You can create an encryption key and encrypt the encryption key.

Create encryption key::

   pi-manage setup create_enckey [--enckey_b64=BASE64_ENCODED_ENCKEY]

.. note:: The filename of the encryption
   key is read from the configuration. The key will not be created, if it
   already exists.
   Optionally, enckey can be passed via `--enckey_b64` argument, but it is not recommended.
   `--enckey_b64` must be a string with 96 bytes, encoded in base 64 in order to avoid ambiguous chars.

The encryption key is a plain file on your hard drive. You need to take care,
to set the correct access rights.

You can also encrypt the encryption key with a passphrase. To do this do::

   pi-manage setup encrypt_enckey /etc/privacyidea/enckey

and pipe the encrypted *enckey* to a new file.

Read more about the database encryption and the *enckey* in :ref:`securitymodule`.

Backup and Restore
------------------

.. index:: Backup, Restore

You can create a backup which will be save to */var/lib/privacyidea/backup/*.

The backup will contain the database dump and the complete directory
*/etc/privacyidea*. You may choose if you want to add the encryption key to
the backup or not.

.. warning:: If the backup includes the database dump and the encryption key
   all seeds of the OTP tokens can be read from the backup.

As the backup contains the etc directory and the database you only need this
tar archive backup to perform a complete restore.


Rotate Audit Log
----------------

Audit logs are written to the database. You can use pi-manage to perform a
log rotation::

   pi-manage audit rotate

You can specify a highwatermark and a lowwatermark, age or a config file. Read more
about it at :ref:`cleaning up audit entries <audit_rotate>`.

.. _pimanage_challenge:

Clean up challenges
-------------------

The challenges of challenge-response tokens are stored in a database table.
Each challenge has a validity time. Challenges which haven't been answered,
persist in the database and must be cleaned up manually. To clean up all
expired challenges use::

   pi-manage config challenge cleanup

To clean up challenges older than a certain age (in minutes), use the parameter
``--age``::

   pi-manage config challenge cleanup --age 10

This will clean up challenges that were created more than 10 minutes ago.

Use ``--chunksize`` to avoid deadlocks when cleaning up a large challenge table.
To get only the number of challenges which would be deleted, use ``--dryrun``.

API Keys
--------

You can use ``pi-manage`` to create API keys. API keys can be used to

1. secure the access to the ``/validate/check`` API or
2. to access administrative tasks via the REST API.

You can create API keys for ``/validate/check`` using the command::

   pi-manage api createtoken -r validate

If you want to secure the access to ``/validate/check`` you also need to
define a policy in scope ``authorizaion``. See :ref:`policy_api_key`.

If you wan to use the API key to automate administrative REST API calls, you
can use the command::

   pi-manage api createtoken -r admin

This command also generates an admin account name. But it does not create
this admin account. You need to do so using ``pi-manage admin``.
You can now use this API key to enroll tokens as administrator.

.. note:: These API keys are not persistent. They are not stored in the
   privacyIDEA server. The API key is connected to the username, that is also
   generated. This means you have to create an administrative account with
   this very username to use this API key for this admin user.
   You also should set policies for this admin user, so that this API key has
   only restricted rights!

.. note:: The API key is valid for 365 days.

Policies
--------

You can use ``pi-manage config policy`` to enable, disable, create and delete policies.


Exporting and Importing the Configuration
-----------------------------------------

.. index:: Configuration export, Configuration import

Using ``pi-manage config export`` and ``pi-manage config import`` you can export
and import parts of the server configuration like policies, resolvers, realms,
events, periodic tasks, CA connectors, SMS, SMTP and RADIUS server definitions
and the global configuration. Run ``pi-manage config export -h`` to see the list
of available configuration types on your installation.

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
   resolver, a RADIUS secret or an SMTP password - in clear text, so that it can
   be imported into an instance with a different encryption key. Store the
   exported files in a secure location or use the ``--censor`` option described
   below.

Censoring secrets on export
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you do not want the secrets to leave the server in clear text, use the
``--censor`` option. Every secret - resolver and CA connector passwords, the
RADIUS secret, the SMTP password and private key password and secret-looking
SMS gateway options and headers - is then replaced with the placeholder
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
  secret to keep, so the affected object is created *without* the secret. You
  then have to set the passwords manually afterwards.

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

This can also be used to transfer the policies from one privacyIDEA
instance to another.
