.. _upgrade:

Upgrading
---------

Upgrade to privacyIDEA 2.11
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In privacyIDEA 2.11 the RADIUS server definition was added.
RADIUS servers can be used in RADIUS tokens and in the
RADIUS passthru policy. 

A new database table "radiusserver" was added.

You need to update the database models::

   pi-manage db stamp 4f32a4e1bf33 -d path/to/migrations
   pi-manage db upgrade -d path/to/migrations


Upgrade to privacyIDEA 2.10
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In privacyIDEA 2.10 SMTP servers were added. SMTP servers can be used for
notifications, registration and also for Email token and SMS token.

SMTP servers need a new database table "smtpserver".

You need to update the database models::

   pi-manage db stamp 4f32a4e1bf33 -d path/to/migrations
   pi-manage db upgrade -d path/to/migrations

privacyIDEA 2.10 can import all kind of PSKC token files. These XML files
need to be parsed. Therefore *BeautifulSoup4* and *lxml* is used. On pip
installations you need to install a package like *libxslt1-dev*.


Upgrade From privacyIDEA 2.x to 2.3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In 2.3 the priority of resolvers in realms was added.

You need to update the database models::

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

To upgrade the code enter your python virtualenv and run::

   pip install --upgrade privacyidea

Configuration
.............

Read about the configuration in the :ref:`cfgfile`.

You can use the old `enckey`, the old `signing keys` and the
old `database uri`. The values can be found in your old ini-file 
as ``privacyideaSecretFile``, ``privacyideaAudit.key.private``, 
``privacyideaAudit.key.public`` and ``sqlalchemy.url``. Your new 
config file might look like this::

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

To verify the new configuration run::

   pi-manage create_enckey

It should say, that the enckey already exists!

Migrate The Database
....................

You need to upgrade the database to the new database schema::

   pi-manage db upgrade -d lib/privacyidea/migrations

.. note:: In the Ubuntu package the migrations folder is located at
   ``/usr/lib/privacyidea/migrations/``.

Create An Administrator
.......................

With privacyIDEA 2.0 the administrators are stored in the database.
The password of the administrator is salted and also peppered, to avoid
having a database administrator slip in a rogue password.

You need to create new administrator accounts::

   pi-manage addadmin <email-address> <admin-name>

Start The Server
................

Run the server::

   pi-manage runserver

or add it to your Apache or Nginx configuration.
