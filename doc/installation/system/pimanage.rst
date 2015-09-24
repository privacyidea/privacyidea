.. _pimanage:

The pi-manage.py Script
=======================

.. index:: pi-manage.py

*pi-manage.py* is the script that is used during the installation process to
setup the database and do many other tasks.

.. note:: The interesting thing about pi-manage.py is, that it does not need
   the server to run as it acts directly on the database.
   Therefor you need read access to /etc/privacyidea/pi.cfg and the encryption
   key.

If you want to use a config file other than /etc/privacyidea/pi.cfg, you can
set an environment variable::

   PRIVACYIDEA_CONFIGFILE=/home/user/pi.cfg pi-manage.py

pi-manage.py always takes a command and sometimes a sub command::

   pi-manage.py <command> [<subcommand>] [<parameters>]

For a complete list of commands and sub commands use the *-h* parameter.

You can do the following tasks.

Encryption Key
--------------

You can create an encryption key and encrypt the encryption key.

Create encryption key::

   pi-manage.py create_enckey

.. note:: This command takes no parameters. The filename of the encryption
   key is read from the configuration. The key will not be created, if it
   already exists.

The encryption key is a plain file on your hard drive. You need to take care,
to set the correct access rights.

You can also encrypt the encryption key with a passphrase. To do this do::

   pi-manage.py encrypt_enckey /etc/privacyidea/enckey

and pipe the encrypted *enckey* to a new file.

**NotYetImplemented**

Backup and Restore
------------------

.. index:: Backup, Restore

You can create a backup which will be save to */var/lib/privacyidea/backup/*.

The backup will contain the database dump and the complete directory
*/etc/privacyidea* which also includes the encryption key.

.. warning:: As the backup includes the database dump and the encryption key
   all seeds of the OTP tokens can be read from the backup.

As the backup contains the etc directory and the database you only need this
tar archive backup to perform a complete restore.


Rotate Audit Log
----------------

Audit logs are written to the database. You can use pi-manage.py to perform a
log rotation.

   pi-manage.py rotate_audit

You can specify a highwatermark and a lowwatermark.
