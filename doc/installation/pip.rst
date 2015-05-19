.. _pip_install:

Python Package Index
--------------------

.. index:: pip install, virtual environment

You can install privacyidea on usually any Linux distribution in a python
virtual environment
like this::

  virtualenv /opt/privacyidea

  cd /opt/privacyidea
  source bin/activate

Now you are within the python virtual environment.
Within the environment you can now run::

  pip install privacyidea

.. _configuration:

Please see the section :ref:`cfgfile` for a quick setup of your configuration.


Then create the encryption key and the signing keys::

   pi-manage.py create_enckey
   pi-manage.py create_signkey

Create the database and the first administrator::

   pi-manage.py createdb
   pi-manage.py admin add admin admin@localhost

Now you can run the server for your first test::

   pi-manage.py runserver


Depending on the database you want to use, you may have to install additional packages.

.. rubric:: Footnotes

.. [#ppa] https://launchpad.net/~privacyidea
.. [#simpleSAML]  https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
