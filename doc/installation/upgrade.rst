.. _upgrade:

Upgrading
---------

In any case before upgrading a major version read the document
`READ_BEFORE_UPDATE <https://github.com/privacyidea/privacyidea/blob/master/READ_BEFORE_UPDATE.md>`_
which is continuously updated in the Github repository.
Note, that when you are upgrading over several major versions, read all the comments
for all versions.

If you installed privacyIDEA via DEB or RPM repository you can use the normal
system ways of *apt-get*, *aptitude* and *rpm* to upgrade privacyIDEA to the
current version.

If you want to upgrade your Ubuntu installation from privacyIDEA 2.23 to
privacyIDEA 3.0, please read :ref:`upgrade_ubuntu`.

Basic pip upgrade process
~~~~~~~~~~~~~~~~~~~~~~~~~

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
...............

Starting with version 2.17 the script ``privacyidea-pip-update`` performs the
update of the python virtualenv and the DB schema.

Just enter your python virtualenv (you already did so, when running the
backup) and run the command:

   privacyidea-pip-update

The following parameters are allowed:

``-f`` or ``--force`` skips the safety question, if you really want to update.

``-s`` or ``--skipstamp`` skips the version stamping during schema update.

``-n`` or ``--noshema`` completely skips the schema update and only updates the code.


Manual upgrade
..............

Now you can upgrade the installation:

.. code-block:: bash

   source /opt/privacyidea/bin/activate
   pip install --upgrade privacyidea

Usually you will need to upgrade/migrate the database:

.. code-block:: bash

   privacyidea-schema-upgrade /opt/privacyidea/lib/privacyidea/migrations

Now you need to restart your webserver for the new code to take effect.


Upgrade to privacyIDEA 2.12
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In privacyIDEA 2.12 the Event Handler framework was added.
Two new tables "eventhandler" and "eventhandleroption" were added.

You need to update the database models:

.. code-block:: bash

   pi-manage db stamp 4f32a4e1bf33 -d path/to/migrations
   pi-manage db upgrade -d path/to/migrations


Upgrade to privacyIDEA 2.11
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In privacyIDEA 2.11 the RADIUS server definition was added.
RADIUS servers can be used in RADIUS tokens and in the
RADIUS passthru policy. 

A new database table "radiusserver" was added.

You need to update the database models:

.. code-block:: bash

   pi-manage db stamp 4f32a4e1bf33 -d path/to/migrations
   pi-manage db upgrade -d path/to/migrations


Upgrade to privacyIDEA 2.10
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In privacyIDEA 2.10 SMTP servers were added. SMTP servers can be used for
notifications, registration and also for Email token and SMS token.

SMTP servers need a new database table "smtpserver".

You need to update the database models:

.. code-block:: bash

   pi-manage db stamp 4f32a4e1bf33 -d path/to/migrations
   pi-manage db upgrade -d path/to/migrations

privacyIDEA 2.10 can import all kind of PSKC token files. These XML files
need to be parsed. Therefore *BeautifulSoup4* and *lxml* is used. On pip
installations you need to install a package like *libxslt1-dev*.


Upgrade From privacyIDEA 2.x to 2.3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In 2.3 the priority of resolvers in realms was added.

You need to update the database models:

.. code-block:: bash

   pi-manage db stamp 4f32a4e1bf33 -d path/to/migrations
   pi-manage db upgrade -d path/to/migrations

.. note:: You need to specify the path to the migrations scripts.
   This could be /usr/lib/privacyidea/migrations.

.. note:: When upgrading with the Ubuntu LTS packages, the database
   update is performed automatically.

Upgrade From privacyIDEA 1.5
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning:: privacyIDEA 2.0 introduces many changes in
   database schema, so at least perform a database backup!

Stopping Your Server
....................

Be sure to stop your privacyIDEA server.

Upgrade Software
................

To upgrade the code enter your python virtualenv and run:

.. code-block:: bash

   pip install --upgrade privacyidea

Configuration
.............

Read about the configuration in the :ref:`cfgfile`.

You can use the old `enckey`, the old `signing keys` and the
old `database uri`. The values can be found in your old ini-file 
as ``privacyideaSecretFile``, ``privacyideaAudit.key.private``, 
``privacyideaAudit.key.public`` and ``sqlalchemy.url``. Your new 
config file might look like this:

.. code-block:: python

   config_path = "/home/cornelius/tmp/pi20/etc/privacyidea/"
   # This is your old database URI
   # Note the three slashes!
   SQLALCHEMY_DATABASE_URI = "sqlite:///" + config_path + "token.sqlite"
   # This is new!
   SECRET_KEY = 't0p s3cr3t'
   # This is new 
   #This is used to encrypt the admin passwords
   PI_PEPPER = "Never know..."
   # This is used to encrypt the token data and token passwords
   # This is your old encryption key!
   PI_ENCFILE = config_path + 'enckey'
   # THese are your old signing keys
   # This is used to sign the audit log
   PI_AUDIT_KEY_PRIVATE = config_path + 'private.pem'
   PI_AUDIT_KEY_PUBLIC = config_path + 'public.pem'

To verify the new configuration run:

.. code-block:: bash

   pi-manage create_enckey

It should say, that the enckey already exists!

Migrate The Database
....................

You need to upgrade the database to the new database schema:

.. code-block:: bash

   pi-manage db upgrade -d lib/privacyidea/migrations

.. note:: In the Ubuntu package the migrations folder is located at
   ``/usr/lib/privacyidea/migrations/``.

Create An Administrator
.......................

With privacyIDEA 2.0 the administrators are stored in the database.
The password of the administrator is salted and also peppered, to avoid
having a database administrator slip in a rogue password.

You need to create new administrator accounts:

.. code-block:: bash

   pi-manage addadmin <email-address> <admin-name>

Start The Server
................

Run the server:

.. code-block:: bash

   pi-manage runserver

or add it to your Apache or Nginx configuration.
