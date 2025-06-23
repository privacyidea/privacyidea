.. _pip_install:

Python Package Index
--------------------

.. index:: pip install, virtual environment

You can install privacyidea usually on any Linux distribution in a python
virtual environment. This way you keep all privacyIDEA code in one defined
subdirectory.

.. note::
    privacyIDEA currently runs with Python 3.9 to 3.12. Other
    versions either do not work or are not tested.

Setting up a virtual environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You first need to install a package for creating a python `virtual environment
<https://virtualenv.pypa.io/en/stable/>`_.

Now you can setup the virtual environment for privacyIDEA like this::

  $ virtualenv /opt/privacyidea

  $ cd /opt/privacyidea
  $ source bin/activate
  (privacyidea)$

.. note::
    Some distributions still ship Python 2.7 as the system python. If you want
    to use Python 3 you can create the virtual environment like this:
    `virtualenv -p /usr/bin/python3 /opt/privacyidea`

Now you are within the python virtual environment and you can proceed with the
:ref:`deterministic installation <pip_deterministic_installation>`.

.. _pip_deterministic_installation:

Deterministic Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^

The privacyIDEA package contains dependencies with a minimal required version. However, newest
versions of dependencies are not always tested and might cause problems.
To achieve a deterministic installation, you must install the pinned and tested
versions of the dependencies *before* installing privacyIDEA::

    (privacyidea)$ pip install -r https://raw.githubusercontent.com/privacyidea/privacyidea/v3.11.3/requirements.txt

Now you can install the required privacyIDEA version from
`PyPI <https://pypi.org/project/privacyIDEA>`_::

    (privacyidea)$ pip install privacyidea==3.11.3

The requirements are also available after the installation at ``/opt/privacyidea/lib/privacyidea/requirements.txt``.

.. _pip_configuration:

Configuration
^^^^^^^^^^^^^

Database
........

privacyIDEA makes use of `SQLAlchemy <https://www.sqlalchemy.org>`_ to be able
to talk to different SQL-based databases. Our best experience is with
`MySQL <https://www.mysql.com/>`_ but SQLAlchemy supports many different
databases [#sqlaDialects]_.

The database server should be installed on the host or be otherwise reachable.

In order for privacyIDEA to use the database, a database user with the
appropriate privileges is needed.
The following SQL commands will create the database as well as a user in `MySQL`::

    CREATE DATABASE pi;
    CREATE USER "pi"@"localhost" IDENTIFIED BY "<dbsecret>";
    GRANT ALL PRIVILEGES ON pi.* TO "pi"@"localhost";

You must then add the database name, user and password to your `pi.cfg`. See
:ref:`cfgfile` for more information on the configuration.

Setting up privacyIDEA
......................
Additionally to the database connection a new ``PI_PEPPER`` and ``SECRET_KEY``
must be generated in order to secure the installation::

    PEPPER="$(tr -dc A-Za-z0-9_ </dev/urandom | head -c24)"
    echo "PI_PEPPER = '$PEPPER'" >> /path/to/pi.cfg
    SECRET="$(tr -dc A-Za-z0-9_ </dev/urandom | head -c24)"
    echo "SECRET_KEY = '$SECRET'" >> /path/to/pi.cfg

An encryption key for encrypting the secrets in the database and a key for
signing the :ref:`audit` log is also needed (the following commands should be
executed inside the virtual environment)::

    (privacyidea)$ pi-manage setup create_enckey  # encryption key for the database
    (privacyidea)$ pi-manage setup create_audit_keys  # key for verification of audit log entries

To create the database tables execute::

    (privacyidea)$ pi-manage setup create_tables

After creating a local administrative user with::

    (privacyidea)$ pi-manage admin add <login>

the development server can be started with::

    (privacyidea)$ pi-manage run

.. versionchanged:: 3.10
    To start the development server with an earlier version use ``runserver``. The
    command is still available but deprecated.

.. warning::
    The development server should not be used for a productive environment.

Webserver
.........

To serve authentication requests and provide the management UI a
`WSGI <https://wsgi.readthedocs.io/en/latest/index.html>`_ capable webserver
like `Apache2 <https://httpd.apache.org/>`_ or `nginx <https://nginx.org/en>`_
is needed.

Setup and configuration of a webserver can be a complex procedure depending on
several parameter (host OS, SSL, internal network structure, ...).
Some example configuration can be found in the NetKnights GitHub
repositories [#nkgh]_. More on the WSGI setup for privacyIDEA can be found in
:ref:`wsgiscript`.


.. rubric:: Footnotes

.. [#sqlaDialects] https://docs.sqlalchemy.org/en/14/dialects/index.html
.. [#nkgh] https://github.com/NetKnights-GmbH/ubuntu/tree/master/deploy
