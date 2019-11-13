.. _audit:

Audit
=====

.. index:: Audit

The systems provides a sophisticated audit log, that can be viewed in the 
WebUI.

.. figure:: auditlog.png
   :width: 500

   *Audit Log*

privacyIDEA comes with a default SQL audit module (see :ref:`code_audit`).

Starting with version 3.2 privacyIDEA also provides a :ref:`logger_audit` and
a :ref:`container_audit` which can be used to send privacyIDEA audit log messages
to service like splunk or logstash.

.. _sql_audit:

SQL Audit
---------

.. _audit_rotate:

Cleaning up entries
~~~~~~~~~~~~~~~~~~~

.. index:: Audit Log Rotate

The ``sqlaudit`` module writes audit entries to an SQL database.
For performance reasons the audit module does no log rotation during
the logging process.

But you can set up a cron job to clean up old audit entries. Since version
2.19 audit entries can be either cleaned up based on the number of entries or
based on on the age.

Cleaning based on the age takes precedence:

You can specify a *highwatermark* and a *lowwatermark*. To clean
up the audit log table, you can call ``pi-manage`` at command line::
   
   pi-manage rotate_audit --highwatermark 20000 --lowwatermark 18000

This will, if there are more than 20.000 log entries, clean all old
log entries, so that only 18000 log entries remain.

Cleaning based on the age:

You can specify the number of days, how old an audit entry may be at a max.

   pi-manage rotate_audit --age 365

will delete all audit entries that are older than one year.

Cleaning based on the config file:

.. index:: retention time

Using a config file you can define different retention times for the audit data.
E.g. this way you can define, that audit entries about token listings can be deleted after
one month,
while the audit information about token creation will only deleted after ten years.

The config file is a YAML format and looks like this::

    # DELETE auth requests of nils after 10 days
    - rotate: 10
      user: nils
      action: .*/validate/check.*

    # DELETE auth requests of friedrich after 7 days
    - rotate: 7
      user: friedrich
      action: .*/validate/check.*

    # Delete nagios user test auth directly
    - rotate: 0
      user: nagiosuser
      action: POST /validate/check.*

    # Delete token listing after one month
    - rotate: 30
      action: ^GET /token

    # Delete audit logs for token creating after 10 years
    - rotate: 3650
      action: POST /token/init

    # Delete everything else after 6 months
    - rotate: 180
      action: .*

This is a list of rules.
privacyIDEA iterates over *all* audit entries. The first matching rule for an entry wins.
If the rule matches, the audit entry is deleted if the entry is older than the days
specified in "rotate".

If is a good idea to have a *catch-all* rule at the end.

.. note:: The keys "user", "action"... correspond to the column names of the audit table.
   You can use any column name here like "date", "action", "action_detail", "success", "serial", "administrator",
   "user", "realm"... for a complete list see the model definition.
   You may use Python regular expressions for matching.

You can the add a call like

   pi-manage rotate_audit --config /etc/privacyidea/audit.yaml

in your crontab.


Access rights
~~~~~~~~~~~~~

You may also want to run the cron job with reduced rights. I.e. a user who
has no read access to the original pi.cfg file, since this job does not need
read access to the SECRET or PEPPER in the pi.cfg file.

So you can simply specify a config file with only the content::

   PI_AUDIT_SQL_URI = <your database uri>

Then you can call ``pi-manage`` like this::

   PRIVACYIDEA_CONFIGFILE=/home/cornelius/src/privacyidea/audit.cfg \
   pi-manage rotate_audit

This will read the configuration (only the database uri) from the config file
``audit.cfg``.

Table size
~~~~~~~~~~

Sometimes the entires to be written to the database may be longer than the
column in the database. You can either enlarge the columns in the database or
you can set

   PI_AUDIT_SQL_TRUNCATE = True

in ``pi.cfg``. This will truncate each entry to the defined column length.

.. _logger_audit:

Logger Audit
------------

The *Logger Audit* module can be used to write audit log information to
the Python logging facility and thus write log messages to a plain file.

To activate the *Logger Audit* module you need to configure the following
settings in your ``pi.cfg`` file::

   PI_AUDIT_MODULE = "privacyidea.lib.auditmodules.loggeraudit"
   PI_AUDIT_SERVERNAME = "your choice"
   PI_LOGCONFIG = "/etc/privacyidea/logging.cfg"

In contrast to the :ref:`sql_audit` you *need* a ``PI_LOGCONFIG`` otherwise
the *Logger Audit* will not work correctly.

In the ``logging.cfg`` you then need to define the audit logger::

   [logger_audit]
   handlers=audit
   qualname=privacyidea.lib.auditmodules.loggeraudit
   level=INFO

   [handler_audit]
   class=logging.handlers.RotatingFileHandler
   backupCount=14
   maxBytes=10000000
   formatter=detail
   level=INFO
   args=('/var/log/privacyidea/audit.log',)

Note, that the ``level`` always needs to be *INFO*. In this example the
audit log will be written to the file ``/var/log/privacyidea/audit.log``.

Finally you need to extend the following settings with the defined audit logger
and audit handler::

   [handlers]
   keys=file,audit

   [loggers]
   keys=root,privacyidea,audit

.. note:: The *Logger Audit* only allows to **write** audit information. It
   can not be used to **read** data. So if you are only using the
   *Audit Logger*, you will not be able to *view* audit information in the
   privacyIDEA Web UI!
   To still be able to *read* audit information, take a look at the
   :ref:`container_audit`.

.. _container_audit:

Container Audit
---------------

The *Container Audit* module is a meta audit module, that can be used to
write audit information to more than one audit module.

It is configured in the ``pi.cfg`` like this::

    PI_AUDIT_MODULE = 'privacyidea.lib.auditmodules.containeraudit'
    PI_AUDIT_CONTAINER_WRITE = ['privacyidea.lib.auditmodules.sqlaudit','privacyidea.lib.auditmodules.loggeraudit']
    PI_AUDIT_CONTAINER_READ = 'privacyidea.lib.auditmodules.sqlaudit'

The key ``PI_AUDIT_CONTAINER_WRITE`` contains a list of audit modules,
to which the audit information should be written. The listed
audit modules need to be configured as mentioned in the corresponding audit
module description.

The key ``PI_AUDIT_CONTAINER_READ`` contains one single audit module, that
is capable of reading information. In this case the :ref:`sql_audit` module can be
used. The :ref:`logger_audit` module can **note** be used for reading!

Using the *Container Audit* module you can on the one hand send audit information
to external services using the :ref:`logger_audit` but also keep the
audit information visible within privacyIDEA using the :ref:`sql_audit` module.