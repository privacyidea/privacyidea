.. _pip_install:

Python Package Index
--------------------

.. index:: pip install, virtual environment

You can install privacyidea on usually any Linux distribution in a python
virtual environment. This way you keep all privacyIDEA code in one defined
subdirectory.

.. note:: privacyIDEA depends on python 2.7 to run properly.

You first need to install some development packages. E.g. on debian based
distributions the packages are called

* libjpeg-dev
* libz-dev
* python-dev
* libffi-dev
* libssl-dev
* libxslt1-dev

Now you can install privacyIDEA like this::

  virtualenv /opt/privacyidea

  cd /opt/privacyidea
  source bin/activate

Now you are within the python virtual environment.
Within the environment you can now run::

  pip install privacyidea

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


Depending on the database you want to use, you may have to install additional packages.

.. rubric:: Footnotes
.. [#ppa] https://launchpad.net/~privacyidea
.. [#simpleSAML] https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
