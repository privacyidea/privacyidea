.. _upgrade:

Upgrading
---------

In any case before upgrading a major version read the document
`READ_BEFORE_UPDATE`_
which is continuously updated in the Github repository.
Note, that when you are upgrading over several major versions, read all the comments
for all versions.

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
you can follow this basic upgrade process.

First you might want to backup your program directory:

.. code-block:: bash

   tar -zcf privacyidea-old.tgz /opt/privacyidea

and your database:

.. code-block:: bash

   source /opt/privacyidea/bin/activate
   pi-manage backup create

Running upgrade
^^^^^^^^^^^^^^^

The script ``privacyidea-pip-update`` performs the
update of the python virtualenv and the DB schema.

Just enter your python virtualenv (you already did so, when running the
backup) and run the command::

   privacyidea-pip-update

The script refuses to run outside of an activated virtual environment. It
upgrades the ``privacyidea`` package and its pinned dependencies and then runs
``privacyidea-schema-upgrade``.

The following parameters are allowed:

``-f`` or ``--force`` skips the confirmation question. The schema update still
runs, unless you also pass ``-n``.

``-s`` or ``--skipstamp`` skips the version stamping during schema update.

``-n`` or ``--noschema`` completely skips the schema update and only updates the code.


Manual upgrade
^^^^^^^^^^^^^^

Now you can upgrade the installation:

.. code-block:: bash

   source /opt/privacyidea/bin/activate
   pip install --upgrade privacyidea

Usually you will need to upgrade/migrate the database:

.. code-block:: bash

   privacyidea-schema-upgrade

.. note::
    .. versionchanged:: 3.12 The migration directory is detected automatically.

    If the migration directory is not found, e.g. in an editable installation,
    pass it with ``-d``::

        privacyidea-schema-upgrade -d /opt/privacyidea/lib/python3.X/site-packages/privacyidea/migrations

    ``privacyidea-schema-upgrade`` does not accept the directory without ``-d``.
    ``-s`` skips stamping a database that has no version stamp yet.

Now you need to restart your webserver for the new code to take effect.

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
default tools (e.g. apt and dnf). In any case, read the
`READ_BEFORE_UPDATE`_
file. It is also a good idea to backup your system before upgrading.

Ubuntu upgrade
^^^^^^^^^^^^^^

If you use the Ubuntu packages in a default setup, the upgrade should be done
using::

   apt update
   apt dist-upgrade


RHEL upgrade
^^^^^^^^^^^^

For a Red Hat Enterprise Linux (RHEL) installation run::

 dnf upgrade

to upgrade.

.. _READ_BEFORE_UPDATE: https://github.com/privacyidea/privacyidea/blob/master/READ_BEFORE_UPDATE.md
