.. _upgrade:

Upgrading
---------

Before every update, read :read-before-update:`READ_BEFORE_UPDATE.md` of the version
you update to. It lists what changes and what you have to do before and after the
update. When you skip versions, read the sections of all versions in between.

If you installed privacyIDEA via DEB or RPM repository you can use the normal
system ways of *apt* and *dnf* to upgrade privacyIDEA to the
current version.

Different upgrade processes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Depending on the way privacyIDEA was installed, there are different recommended update procedures.
The following section describes the process for pip installations.
Instructions for packaged versions on RHEL and Ubuntu are found in :ref:`upgrade_packaged`.

Upgrading a pip installation
............................

If you install privacyIDEA into a python virtualenv like */opt/privacyidea*,
the upgrade consists of these steps, described below:

#. Read :read-before-update:`READ_BEFORE_UPDATE.md`.
#. Stop the web server that runs privacyIDEA, and pause the cron jobs or timers
   that run privacyIDEA commands. The schema upgrade changes and moves data; a
   process that still runs the old code would keep reading and writing it the old
   way.
#. Back up the program directory, the database and the configuration.
#. Upgrade the code.
#. Run the schema upgrade once.
#. Check that ``pi-manage db current`` shows the newest revision, marked
   ``(head)``.
#. Start the web server and the cron jobs again.

Back up your program directory:

.. code-block:: bash

   tar -zcf privacyidea-old.tgz /opt/privacyidea

and your database and configuration:

.. code-block:: bash

   source /opt/privacyidea/bin/activate
   pi-manage backup create

Run the backup as ``root``. Another user has to pass a backup directory it can
write to with ``-d``, the default is ``/var/lib/privacyidea/backup/``. The
archive contains a dump of the database and the configuration directory
``/etc/privacyidea/``, but not the encryption key: add ``-e`` to include it
(only a key file inside that directory is added), or keep a copy of the key
elsewhere. A MySQL/MariaDB or PostgreSQL dump needs ``mysqldump`` or
``pg_dump``. See :ref:`pimanage_backup`.

Running upgrade
^^^^^^^^^^^^^^^

The script ``privacyidea-pip-update`` performs the
update of the python virtualenv and the DB schema.

Just enter your python virtualenv (you already did so, when running the
backup) and run the command::

   privacyidea-pip-update

The script refuses to run outside of an activated virtual environment. It
upgrades the ``privacyidea`` package and its pinned dependencies and then runs
``privacyidea-schema-upgrade``. If one of these steps fails, the script stops
there and ends with the exit code of that step.

The following parameters are allowed:

``-f`` or ``--force`` skips the confirmation question. The schema update still
runs, unless you also pass ``-n``.

``-s`` or ``--skipstamp`` is accepted for compatibility and has no effect.

``-n`` or ``--noschema`` completely skips the schema update and only updates the code.


Manual upgrade
^^^^^^^^^^^^^^

Now you can upgrade the installation. Upgrade the package and then install the
pinned dependencies of the new version (see
:ref:`pip_deterministic_installation`):

.. code-block:: bash

   source /opt/privacyidea/bin/activate
   pip install --upgrade privacyidea
   pip install -r /opt/privacyidea/lib/privacyidea/requirements.txt

Without the second command pip keeps the dependency versions of the previous
release wherever they still fit, and installs dependencies that are new in this
release in their newest version, a combination that was never tested. The
second command can also downgrade a package.

Usually you will need to upgrade/migrate the database:

.. code-block:: bash

   privacyidea-schema-upgrade

The script prints the schema revision of the database before and after the
upgrade. If the upgrade fails, the second revision shows how far it got.

The script does not change a database that has no revision stamp, because it
cannot tell which migrations such a database needs. It stops with an error
instead. Stamp the database with the newest revision of the version that created
its tables, then run the script again:

* Tables created with ``pi-manage setup create_tables --no-stamp`` by the
  installed version: ``pi-manage db stamp head``.
* Tables created by a version before 3.10: the revision of that version in the
  table below, for example ``pi-manage db stamp 5cb310101a1f`` for 3.9. These
  versions created the tables without a stamp by default.

Use the version that created the tables, not the version that you installed
last. If the code was updated without a schema update, the two are different. A
wrong revision makes the upgrade skip or repeat migrations.

.. list-table:: Newest schema revision of the versions before 3.10
   :header-rows: 1

   * - Version
     - Revision
   * - 2.0 to 2.2
     - ``2181294eed0b``
   * - 2.3
     - ``e5cbeb7c177``
   * - 2.4 and 2.5
     - ``4d9178fa8336``
   * - 2.6 to 2.9
     - ``20969b4cbf06``
   * - 2.10
     - ``4023571658f8``
   * - 2.11
     - ``239995464c48``
   * - 2.12
     - ``50adc980d625``
   * - 2.13
     - ``5402fd96fbca``
   * - 2.14
     - ``3ae3c668f444``
   * - 2.15
     - ``3c6e9dd7fbac``
   * - 2.16
     - ``37e6b49fc686``
   * - 2.17 to 2.18.1
     - ``58e4f7ebb705``
   * - 2.19 and 2.19.1
     - ``3429d523e51f``
   * - 2.20 and 2.20.1
     - ``36428afb2457``
   * - 2.21 to 2.21.4
     - ``14a1bcb10018``
   * - 2.22 to 2.22.4
     - ``145ce80decd``
   * - 2.23 to 2.23.5
     - ``1a0710df148b``
   * - 3.0 to 3.0.2
     - ``849170064430``
   * - 3.1 to 3.1.2
     - ``3d7f8b29cbb1``
   * - 3.2 to 3.2.2
     - ``0c7123345224``
   * - 3.3 to 3.3.3
     - ``a7e91b18a460``
   * - 3.4 and 3.4.1
     - ``140ba0ca4f07``
   * - 3.5 to 3.5.2
     - ``d5870fd2f2a4``
   * - 3.6 to 3.6.3
     - ``fa07bd604a75``
   * - 3.7 to 3.7.4
     - ``ef29ba43e290``
   * - 3.8 and 3.8.1
     - ``006d4747f858``
   * - 3.9 to 3.9.3
     - ``5cb310101a1f``

.. note::
    .. versionchanged:: 3.12 The migration directory is detected automatically.

    ``-d`` takes the migrations from another directory than the one of the
    installed version::

        privacyidea-schema-upgrade -d /path/to/privacyidea/migrations

    ``privacyidea-schema-upgrade`` does not accept the directory without ``-d``.
    ``-s`` is accepted for compatibility and has no effect.

Check that ``pi-manage db current`` shows the newest revision, marked ``(head)``.
Then start the web server and the cron jobs again.

.. note::

   If you have enabled the optional :ref:`redis_cache`, authentications that
   were already in flight at the moment of the restart may need to be
   started over by the user. The Redis cache is opt-in and does not affect
   the schema upgrade itself; see :ref:`redis_cache_upgrades` for the
   payload-compatibility policy and what to expect when a release changes
   the on-the-wire format.

.. _upgrade_packaged:

Upgrading a packaged installation
.................................

In general, the upgrade of a packaged version of privacyIDEA should be done using the
default tools (e.g. apt and dnf). In any case, read
:read-before-update:`READ_BEFORE_UPDATE.md` first. It is also a good idea to backup your
system before upgrading.

Ubuntu upgrade
^^^^^^^^^^^^^^

If you use the Ubuntu packages in a default setup, the upgrade should be done
using::

   apt update
   apt upgrade

The ``privacyidea`` package is only upgraded together with the server package
(``privacyidea-apache2`` or ``privacyidea-nginx``), which runs the schema upgrade.

The server package runs the schema upgrade while the web server keeps serving
requests, and restarts the web server afterwards. Plan the upgrade for a time with
little traffic.

If the upgrade stops with an error, the new program files are installed but the
database is not migrated completely, and the web server keeps running the old code
until it is restarted or reloaded next. Fix the cause the output names, then finish
the upgrade with::

   dpkg --configure -a

The output of the upgrade, including that of the schema upgrade, is kept in
``/var/log/apt/term.log``.

When apt asks whether to install the package maintainer's version of
``/etc/privacyidea/pi.cfg``, keep your version (answer ``N``). The file of the
package contains no database connection, pepper and secret key, and installing it
replaces them with new ones: the administrators can no longer log in, and the upgrade
either fails or points the server at a new, empty database.

If you changed ``/etc/cron.d/privacyidea``, apt asks about it as well. Keeping your
version keeps your jobs, but not the jobs that a new version adds. Compare it with
``/etc/cron.d/privacyidea.dpkg-dist`` and add them.


RHEL upgrade
^^^^^^^^^^^^

If you installed privacyIDEA from the :ref:`RPM repository <rpm_installation>`, run::

 dnf upgrade

to upgrade.
