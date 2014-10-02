.. _ini_file:

The ini file
============

.. index:: init file

privacyIDEA is a pylons application that uses an ini-file. 
The default location of the ini-file is ``/etc/privacyidea/privacyidea.ini``, but
depending on your installation it can reside anywhere else.

Common config
-------------

The ini file looks like this::

   [DEFAULT]
   debug = false
   profile = false
   email_to = you@yourdomain.com
   smtp_server = localhost
   error_email_from = paste@localhost

You can use the ``debug`` parameter to output debug messages, if you are running
privacyIDEA with the paster. If you are running privacyIDEA in Apache WSGI,
you need to set this to *false*.

The ``profile`` parameter writes profiling output, so that you can measure the 
performance of the code.

The parameters ``email_to``, ``smtp_server`` and ``error_email_from`` can be used
to send email in cases of severe error.

.. index:: audit

Audit
-----

There are audit specific parameter::

   privacyideaAudit.type = privacyidea.lib.auditmodules.sqlaudit
   privacyideaAudit.key.private = %(here)s/private.pem
   privacyideaAudit.key.public = %(here)s/public.pem

   privacyideaAudit.sql.url = mysql://privacyidea:privacyidea@localhost/privacyidea
   privacyideaAudit.sql.highwatermark = 10000
   privacyideaAudit.sql.lowwatermark = 5000

privacyIDEA can write an Audit log. With the paramter ``privacyideaAudit.type`` 
you can specify which python module should be used to write the log.

The audit trail is digitally signed. So you need to specify a private and public RSA 
key ``privacyideaAudit.key.private`` and ``privacyideaAudit.key.public``.

You can decide, which audit module should be used for the audit log to
be written. privacyIDEA comes with an SQLAudit module 
*privacyidea.lib.auditmodules.sqlaudit* that writes the audit log to
an SQL database table. You could also create your own audit module.
Take a look at :ref:`code_audit`.

Audit log rotation
..................

The SQL audit module can do audit log rotation.
To optimize performace log rotation is not performed within the 
server context but you can call the module to do it::

   python /usr/lib/python2.7/dist-packages/privacyidea/lib/auditmodules/sqlaudit.py

You can need to add the parameter ``--file`` and you can add
the parameters ``--high`` and ``-low``. If these parameters are
not specified, the values ``hightwatermark`` and the ``lowwatermark``
are read from the ini-file. (also see :ref:`audit`)

If the audit table reaches the number of entries specified in ``highwatermark``
old entries will be deleted, so that only ``lowwatermark`` entries remain.

You should set up a cron job to rotate the audit log.

Other paramters
---------------

Finally there are several other parameters::

   # If true, OTP values can be retrieved via the getotp controller
   privacyideaGetotp.active = True

   privacyideaSecretFile = %(here)s/dummy-encKey

   # This file contains the token administrators. 
   # It can be created like this:
   # % tools/privacyidea-create-pwidresolver-user -u admin -p test -i 1000 >> config/admin-users
   privacyideaSuperuserFile = %(here)s/admin-users
   # list of realms, that are admins
   privacyideaSuperuserRealms = superuser, 2ndsuperusers
   privacyIDEASessionTimeout = 1200
   # This is the server, where this system is running.
   # This is need to issue a request during login to the 
   # management with an OTP token.
   privacyideaURL = http://localhost:5001
   #
   # This determines if the SSL certificate is checked during the login to 
   # privacyIDEA. Set to True, if you have a self signed certificate.
   privacyideaURL.disable_ssl = False

   privacyidea.useridresolver = privacyidea.lib.resolvers.PasswdIdResolver.IdResolver

   # These are the settings for the RADIUS Token
   # The location of the RADIUS dictionary file
   radius.dictfile= %(here)s/dictionary
   # The NAS Identifier of your privacyIDEA server, 
   # that is sent to the RADIUS server
   radius.nas_identifier = privacyIDEA

.. index:: OTP list, printed OTP list

``privacyideaGetotp.active`` can turn on the possibility to retrieve OTP values
from the server. Usually it is not possible to ask the server for future OTP
values of a token. Using this parameter you can allow this, thus creating 
printed OTP lists.

Finally there are some settings for the use of RADIUS tokens ``radius.dictfile`` and
``radius.nas_identifier`` which you usually do not need to change.

.. _inifile_superusers:

Administrators
..............

privacyIDEA authenticates the administrators. The simple default way is to 
search the admin in a file defined by ``privacyideaSuperuserFile``. 
All users in this file can login with *<username>@admin*. 
In addition you can use the paramter ``privacyideaSuperuserRealms`` to 
specify a list of internal realms, which users will be able to act as
administrators. The authentication then will be done against privacyIDEA
meaning that the administrators would be able to authenticate with OTP tokens
or other tokens like the simple PASS token or authenticate against LDAP using
a *passthru* policy (see :ref:`policies`).
To do so you need to set the parameters ``privacyideaURL`` and 
``privacyideaURL.disable_SSL`` to define how to address your privacyIDEA server
and if the SSL certificate should be validated or not.

Database connection
-------------------

You need to specify what database you want to use::

   [app:main]
   #sqlalchemy.url = mysql://privacyidea:privacyidea@localhost/privacyidea
   sqlalchemy.url = sqlite:///%(here)s/token.sqlite

Take a look at 
`SQLAlchemy <http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html>`_, 
how the connect string needs to look like.

Logfiles
--------

privacyIDEA uses *repoze.who* to do the authentication to the WebUI.
You can specify, where the logfile should be located::
   
   who.log_level = debug
   who.log_file = %(here)s/privacyidea.log

If you are running in Apache WSGI you should not use the ``%(here)s`` statement
but you should specify a logfile like */var/log/privacyidea/who.log*.

.. index:: Logging

privacyIDEA uses the python logging framework. 
You can specify which module should log which level and where all 
information should be logged - being it a file, smtp or syslog::

   #
   #  Note: You should change the Logging Level from DEGUB to WARN
   #
   # Logging configuration
   [loggers]
   keys = root, privacyidea, sqlalchemy, controllers
   
   [logger_root]
   level = WARNING
   handlers = file
   
   [logger_privacyidea]
   level = INFO
   handlers = file
   qualname = privacyidea
   
   [logger_controllers]
   level = DEBUG
   handlers = file
   qualname = privacyidea.controllers.account
   
   [logger_sqlalchemy]
   level = ERROR
   handlers = file
   qualname = sqlalchemy.engine
   # "level = INFO" logs SQL queries.
   # "level = DEBUG" logs SQL queries and results.
   # "level = WARN" logs neither.  (Recommended for production systems.)
   
   [handlers]
   keys = file
   
   [handler_file]
   class = handlers.RotatingFileHandler
   args = ('/var/log/privacyidea/privacyidea.log','a', 10000000, 4)
   level = INFO
   formatter = generic
   
   [formatters]
   keys = generic
   
   [formatter_generic]
   class = privacyidea.lib.log.SecureFormatter
   format = %(asctime)s %(levelname)-5.5s {%(thread)d} [%(name)s][%(funcName)s #%(lineno)d] %(message)s
   datefmt = %Y/%m/%d - %H:%M:%S
 
Please see 
`python logging <https://docs.python.org/2/library/logging.config.html#configuration-file-format>`_
for more details.

.. note:: privacyIDEA provides its own ``SecureFormatter`` which removes 
   nonprintable characters, that cause problems.


