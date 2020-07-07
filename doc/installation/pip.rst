.. _pip_install:

Python Package Index
--------------------

.. index:: pip install, virtual environment

You can install privacyidea on usually any Linux distribution in a python
virtual environment. This way you keep all privacyIDEA code in one defined
subdirectory.

privacyIDEA currently runs with Python 2.7 and 3.5, 3.6, 3.7 and 3.8. Other
versions either do not work or are not tested.

You first need to install some necessary packages for your distribution,
a database, webserver, wsgi- and ssl-module for the webserver and the
python-virtualenv.

Now you can setup the virtual environment for privacyIDEA like this::

  virtualenv /opt/privacyidea

  cd /opt/privacyidea
  source bin/activate

Now you are within the python virtual environment and you can run::

  pip install privacyidea

in order to install the latest privacyIDEA version from
`PyPI <https://pypi.org/project/privacyIDEA`_.

To achieve a deterministic installation, you can install and pin the installed
versions like this::

  export PI_VERSION=3.3.1
  pip install -r https://raw.githubusercontent.com/privacyidea/privacyidea/v${PI_VERSION}/requirements.txt
  pip install https://raw.githubusercontent.com/privacyidea/privacyidea/v${PI_VERSION}/

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
