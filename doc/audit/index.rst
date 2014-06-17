.. _audit:

Audit
=====

The systems provides a sophisticated audit log, that can be viewed in the 
WebUI.

privacyIDEA comes with an SQL audit module. (see :ref:`code_audit`)


Cleaning up entries
-------------------

The ``sqlaudit`` module writes audit entries to an SQL database.
For performance reasons the audit module does no log rotation during
the logging process.

But you can set up a cron job to clean up old audit entries.

You can specify a *highwatermark* and a *lowwatermark*. To clean
up the audit log table, you can call the sqlaudit module at the
command line::
   
   python privacyidea/lib/auditmodules/sqlaudit.py \
       -f config/privacyidea.ini.example \
       --low=5000
       --high=10000

This will, if there are more than 10.000 log entries, clean all old
log entries, so that only 5000 log entries remain.
