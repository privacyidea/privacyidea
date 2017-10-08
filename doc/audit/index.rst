.. _audit:

Audit
=====

.. index:: Audit

The systems provides a sophisticated audit log, that can be viewed in the 
WebUI.

.. figure:: auditlog.png
   :width: 500

   *Audit Log*

privacyIDEA comes with an SQL audit module. (see :ref:`code_audit`)

.. _audit_rotate:

Cleaning up entries
-------------------

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
E.g. this way you can define, that audit entries about token listings can be deleted after one month,
while the audit information about token creation will only deleted after ten years.

The config file is a YAML format and looks like this:

   - ["POST /token/init.*", "3650"] # Save creation and deletion of tokens for 10 years
   - ["DELETE /token/.*", "3650"]
   - ["POST /validate.*", 1825] # Save authentication REQUESTS for 5 years
   - ["GET /validate.*", 1825] # Save authentication REQUESTS for 5 years
   - ["POST .*", 750] # Save all POST Reqeusts for 25 months
   - ["DELETE .*", 1825] # Save all DELETE Requests for 5 years
   - ["GET .*", "30"]  # Only keep GET requests for 30 days!
   - [".*", 180] # Everything else for half a year

This is a list of rules.
Each rule has a regular expression for the audit action and an integer, for how many days the specified
audit log entry should be saved.

Note that the order of the list matters. If the action matches an entry, this rule is applied and
the list is exited.
In the example the rule in the list is a kind of a catch all entry. If there was no other rule,
that matched, the entry will be deleted after 5 months.

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
