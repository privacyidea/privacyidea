.. _database_connect:

Database connect string
-----------------------

Due to its use of a database abstraction layer, privacyIDEA can work with several
databases with the help of corresponding database drivers.

The database and corresponding driver are specified in the connect string
``SQLALCHEMY_DATABASE_URI`` in :ref:`cfgfile`

.. _tested_databases:

Tested database versions
~~~~~~~~~~~~~~~~~~~~~~~~~~

The continuous integration runs the full test suite against **MariaDB 10.11**
(the LTS most installations run) and **PostgreSQL 17**. On every change to the
database models or migrations it additionally runs the migration test suite
against **MariaDB 10.11 and 11**, **MySQL 8.4** and **PostgreSQL 17**. This
suite upgrades databases of version 3.9 and of recent releases, with their data,
to the current schema. Then it downgrades them back. It also runs every
migration a second time, as after a failed update, and restores backups made
with ``pi-manage backup``. A single-node MariaDB Galera cluster is
covered as well, to catch cluster-specific DDL constraints.

**SQLite** is the default for development and small, single-node installations.

.. _mysqldb:

MySQL / MariaDB
~~~~~~~~~~~~~~~

While there are several database driver packages for MySQL, we recommend *PyMySQL*
which is a pure Python package and does not require external libraries or a build
environment on the server.

*PyMySQL* is already installed in the virtual environment as a requirement for
privacyIDEA.

**connect string**: ``mysql+pymysql://<user>:<password>@<host>/<database>``


.. _postgresdb:

PostgreSQL
~~~~~~~~~~

PostgreSQL is tested using the ``psycopg2`` driver which can be installed into
the privacyIDEA virtual environment with::

   (privacyidea) $ pip install psycopg2_binary

The corresponding connect string looks like this:

**connect string**: ``postgresql+psycopg2://<user>:<password>@<host>/<database>``

.. _oracledb:

Oracle
~~~~~~

Oracle stores an empty string as NULL. privacyIDEA handles this difference, but two effects
remain visible.

Some columns must hold an empty string, because it is part of a key or because the column
does not accept NULL. On Oracle, these columns store the character ``chr(0)`` instead of an
empty string, and privacyIDEA reads it back as an empty string. These are the columns:

* ``resolver`` and ``realm`` of ``user_lock_state``, for example in the lock of a local
  database administrator
* ``labels_key`` and ``node`` of ``metric_aggregate``, for example in a metric without labels

Scripts or reporting tools that read these tables directly see ``chr(0)`` in these columns.

In API responses, some text fields that are empty on other databases are ``null`` on Oracle.
Examples are the description of a policy or a container, and empty audit fields.


Other databases
~~~~~~~~~~~~~~~

The continuous integration regularly tests MariaDB, MySQL and PostgreSQL, see
:ref:`tested_databases`.

Other databases like Oracle or MSSQL are working as well but not all
functionality can be assured, so be aware that "Your mileage may vary".
For example, ``pi-manage backup`` does not support them, see
:ref:`pimanage_backup`.
