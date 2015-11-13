.. _cfgfile:

The Config File 
===============

.. index:: config file, external hook, hook, debug, loglevel

privacyIDEA reads its configuration from different locations:

   1. default configuration from the module ``privacyidea/config.py``
   2. then from the config file ``/etc/privacyidea/pi.cfg`` if it exists and then
   3. from the file specified in the environment variable ``PRIVACYIDEA_CONFIGFILE``.

         export PRIVACYIDEA_CONFIGFILE=/your/config/file

The configuration is overwritten and extended in each step. I.e. values define
in ``privacyidea/config.py``
that are not redefined in one of the other config files, stay the same.

You can create a new config file (either ``/etc/privacyidea/pi.cfg``) or any other
file at any location and set the environment variable.
The file should contain the following contents::

   # The realm, where users are allowed to login as administrators
   SUPERUSER_REALM = ['super', 'administrators']
   # Your database
   SQLALCHEMY_DATABASE_URI = 'sqlite:////etc/privacyidea/data.sqlite'
   # This is used to encrypt the auth_token
   SECRET_KEY = 't0p s3cr3t'
   # This is used to encrypt the admin passwords
   PI_PEPPER = "Never know..."
   # This is used to encrypt the token data and token passwords
   PI_ENCFILE = '/etc/privacyidea/enckey'
   # This is used to sign the audit log
   PI_AUDIT_KEY_PRIVATE = '/home/cornelius/src/privacyidea/private.pem'
   PI_AUDIT_KEY_PUBLIC = '/home/cornelius/src/privacyidea/public.pem'
   # PI_LOGFILE = '....'
   # PI_LOGLEVEL = 20
   # PI_INIT_CHECK_HOOK = 'your.module.function'
   # PI_CSS = '/location/of/theme.css'


.. note:: The config file is parsed as python code, so you can use variables to
   set the path and you need to take care for indentations.

``SQLALCHEMY_DATABASE_URI`` defines the location of your database.
You may want to use the MySQL database or Maria DB. There are two possible
drivers, to connect to this database. Please read :ref:`mysqldb`.

The ``SUPERUSER_REALM`` is a list of realms, in which the users get the role
of an administrator.

``PI_INIT_CHECK_HOOK`` is a function in an external module, that will be
called as decorator to ``token/init`` and ``token/assign``. This function
takes the ``request`` and ``action`` (either "init" or "assing") as an
arguments and can modify the request or raise an exception to avoid the
request being handled.

There are three config entries, that can be used to define the logging. These
are ``PI_LOGLEVEL``, ``PI_LOGFILE``, ``PI_LOGCONFIG``. These are described in
:ref:`debug_log`.

.. _themes:

Themes
------

.. index:: themes, CSS

You can create your own CSS file to adapt the look and feel of the Web UI.
The default CSS is the bootstrap CSS theme. Using ``PI_CSS`` you can specify
the URL of your own CSS file.
The default CSS file url is */static/contrib/css/bootstrap-theme.css*.
The file in the file system is located at *privacyidea/static/contrib/css*.
You might add a directory *privacyidea/static/custom/css/* and add your CSS
file there.

A good stating point might be the themes at http://bootswatch.com.

.. note:: If you add your own CSS file, the file *bootstrap-theme.css* will
   not be loaded anymore. So you might start with a copy of the original file.

