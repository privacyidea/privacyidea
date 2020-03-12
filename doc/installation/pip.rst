.. _pip_install:

Python Package Index
--------------------

.. index:: pip install, virtual environment

You can install privacyidea on usually any Linux distribution in a python
virtual environment. This way you keep all privacyIDEA code in one defined
subdirectory.

privacyIDEA can run with Python 2.7 and 3.5, 3.6 or 3.7. Other versions either do not work
or are not tested.

You first need to install some development packages. E.g. on Debian-based
distributions like Ubuntu the packages are called

* libjpeg-dev
* libz-dev
* python-dev
* libffi-dev
* libssl-dev
* libxslt1-dev

Eventually you may have to install database-related packages such as

* libpq-dev

Now you can install privacyIDEA like this::

  virtualenv /opt/privacyidea

  cd /opt/privacyidea
  source bin/activate

Now you are within the python virtual environment.
Within the environment you can now run::
 
  pip install privacyidea

To achieve a deterministic installation, you can now pin the installed
versions to our tested versions like this::

  pip install -r lib/privacyidea/requirements.txt

  
.. _configuration:

Please see the section :ref:`cfgfile` for a quick setup of your configuration.


Then create the encryption key and the signing keys::

   pi-manage create_enckey
   pi-manage create_audit_keys

Create the database and the first administrator::

   pi-manage createdb
   pi-manage admin add admin -e admin@localhost

Now you can run the server for your first test::

   pi-manage runserver

Stamp the database, so that privacyIDEA has the right database schema version.
This is important for later update processes::

   pi-manage db stamp head -d /opt/privacyidea/lib/privacyidea/migrations

Depending on the database you want to use, you may have to install additional packages (see above).
