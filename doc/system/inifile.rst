.. _cfgfile:

The Config File 
===============

.. index:: config file

privacyidea reads its configuration from

   1. the module ``privacyidea/config.py``
   2. then from the config file ``/etc/privacyidea/pi.cfg`` if it exists and then
   3. from the file specified in the environment variable ``PRIVACYIDEA_CONFIGFILE``.

The configuration is overwritten in each step. I.e. values define in ``privacyidea/config.py``
that are not redefined in one of the other config files, stay the same.

You can create a new config file (either ``/etc/privacyidea/pi.cfg``) or any other
file at any location and set the environment variable.
The file should contain the following contents::

   # The realm, where users are allowed to login as administrators
   SUPERUSER_REALM = super
   # Your database
   SQLALCHEMY_DATABASE_URI = 'sqlite:////home/cornelius/src/privacyidea/data.sqlite'
   # This is used to encrypt the auth_token
   SECRET_KEY = 't0p s3cr3t'
   # This is used to encrypt the admin passwords
   PI_PEPPER = "Never know..."
   # This is used to encrypt the token data and token passwords
   PI_ENCFILE = '/home/cornelius/src/privacyidea/enckey'
   # This is used to sign the audit log
   PI_AUDIT_KEY_PRIVATE = '/home/cornelius/src/privacyidea/private.pem'
   PI_AUDIT_KEY_PUBLIC = '/home/cornelius/src/privacyidea/public.pem'


.. note:: The config file is parsed as a python file, so you can use variables to 
   set the path and you need to take care for indentations.

If you are using a config file other than ``/etc/privacyidea/pi.cfg`` then
you need to set the environment variable::

   export PRIVACYIDEA_CONFIGFILE=/your/config/file
