.. _cleanup_jobs:

Cleanup Jobs
============

.. index:: cleanup, cron, crontab, retention time

Several database tables collect rows that are no longer needed: expired
challenges, expired remembered devices, stale authentication cache entries and
more. privacyIDEA does not delete them while it serves requests. A scheduled job
has to do it, otherwise these tables grow without limit, which costs disk space
and can slow down the queries that read them.

The :ref:`Ubuntu packages <install_ubuntu>` and the Docker image schedule these
jobs out of the box. An :ref:`installation from PyPI <pip_install>` schedules
nothing, so you have to set the jobs up yourself.

.. list-table::
   :header-rows: 1
   :widths: 22 38 20 20

   * - What
     - Command
     - Ubuntu packages (server's local time)
     - Docker ``pi-cron`` (UTC)
   * - :ref:`Periodic tasks <periodic_tasks>`
     - ``privacyidea-cron run_scheduled -c``
     - every 5 minutes
     - every minute
   * - Challenges
     - ``pi-manage config challenge cleanup``
     - daily, 01:00
     - hourly
   * - Remembered devices
     - ``pi-manage config remembered_device cleanup``
     - daily, 01:10
     - daily, 03:00
   * - Authentication cache
     - ``pi-manage config authcache cleanup``
     - daily, 01:20
     - daily, 03:00
   * - Metrics
     - ``pi-manage config metrics cleanup``
     - daily, 01:30
     - daily, 03:00
   * - Expired IP blocks and user locks
     - ``pi-manage conditionalaccess purge-expired-blocks`` and
       ``purge-expired-locks``
     - daily, 01:40
     - daily, 03:00
   * - User cache
     - ``privacyidea-usercache-cleanup``
     - daily, 01:50
     - daily, 04:00
   * - Audit log
     - ``pi-manage audit rotate``
     - commented-out example
     - daily, 02:00
   * - Authentication log
     - ``pi-manage authlog cleanup --age <days>``
     - commented-out example
     - only if ``PI_CRON_AUTHLOG_AGE`` is set

The times of the Ubuntu packages are the local time of the server: the crontab
follows the time zone the server is set to. The ``pi-cron`` container always
runs on UTC, whatever time zone the host uses.

What the jobs delete
--------------------

**Challenges.** Challenges past their validity time. Challenges kept in Redis
(see :ref:`redis_cache`) expire on their own and are not affected. See
:ref:`pimanage_challenge`.

**Remembered devices.** Remembered devices past their expiry date, see
:ref:`api_clients`.

**Authentication cache.** Entries that no active :ref:`policy_auth_cache` policy
accepts any more, i.e. those unused for longer than the most generous policy
allows, or all entries if there is no such policy. With the
:ref:`redis_auth_cache` enabled, only the entries written to the database while
Redis could not be reached are left for it.

**Metrics.** Rows of the ``metric_aggregate`` table older than 24 hours
(``--older-than-hours``, default ``24``). The :ref:`dashboard` shows at most the
last 24 hours. See :ref:`pimanage_metrics`.

**Expired IP blocks and user locks.** Blocks and locks of
:ref:`conditional access <conditional_access>` whose duration has run out. They
restrict nobody any more. Permanent blocks and locks, and those still in force,
are kept.

**User cache.** Entries of the :ref:`usercache` older than its expiration
timeout. The job does nothing while the user cache is disabled.

**Audit log.** How long to keep audit entries is your decision, so the Ubuntu
packages only ship an example. The Docker image rotates by the number of entries
(it keeps 25000 once there are more than 50000). See :ref:`audit_rotate`.

**Authentication log.** Also a retention period of your choice, so it is not
scheduled by default. Keep it comfortably longer than the longest time window of
a conditional access policy, see :ref:`authentication_log_cleanup`.

Ubuntu packages
---------------

The packages ``privacyidea-apache2`` and ``privacyidea-nginx`` install the file
``/etc/cron.d/privacyidea``, which runs the jobs of the table above at the local
time of the server, as the user ``privacyidea``. The jobs discard their normal
output, but not their errors, so cron mails the errors of a failing job, if the
system can send mail.

The audit log and authentication log jobs are commented out. Choose a retention
period and remove the ``#`` to enable them.

``/etc/cron.d/privacyidea`` is a configuration file of the package. If you have
changed it, an upgrade asks whether to keep your version or to install the new
one. If you keep yours, the new version is saved as
``/etc/cron.d/privacyidea.dpkg-dist``: compare the two and add the jobs that are
new.

The file is installed on every node. The cleanup jobs work on the shared
database, so in a setup with several nodes they only need to run on one of them.
Comment them out on the other nodes, so that the nodes do not delete the same
rows at the same time. Keep the ``privacyidea-cron`` line on every node, it only
runs the periodic tasks assigned to that node.

Installation from PyPI
----------------------

Nothing is scheduled. Create ``/etc/cron.d/privacyidea`` yourself, with the
paths of your virtual environment and the user privacyIDEA runs as, for
example::

   */5 * * * *  privacyidea  /opt/privacyidea/bin/privacyidea-cron run_scheduled -c
   0 1 * * *    privacyidea  /opt/privacyidea/bin/pi-manage config challenge cleanup > /dev/null
   10 1 * * *   privacyidea  /opt/privacyidea/bin/pi-manage config remembered_device cleanup > /dev/null
   20 1 * * *   privacyidea  /opt/privacyidea/bin/pi-manage config authcache cleanup > /dev/null
   30 1 * * *   privacyidea  /opt/privacyidea/bin/pi-manage config metrics cleanup > /dev/null
   40 1 * * *   privacyidea  /opt/privacyidea/bin/pi-manage conditionalaccess purge-expired-blocks > /dev/null
   40 1 * * *   privacyidea  /opt/privacyidea/bin/pi-manage conditionalaccess purge-expired-locks > /dev/null
   50 1 * * *   privacyidea  /opt/privacyidea/bin/privacyidea-usercache-cleanup > /dev/null

If your configuration file is not ``/etc/privacyidea/pi.cfg``, set
``PRIVACYIDEA_CONFIGFILE`` at the top of the file, see :ref:`pimanage`. Add the
audit log and authentication log jobs with the retention period of your choice.

Docker
------

The ``pi-cron`` container runs the jobs. Each can be switched off with a
``PI_CRON_*`` environment variable, and the authentication log cleanup only runs
once ``PI_CRON_AUTHLOG_AGE`` sets a retention period in days. The variables are
listed in ``deploy/docker/README.Docker.md`` in the source tree. The times are
in UTC, as the image contains no time zone data: setting ``TZ`` does not change
them.

Manual cleanups
---------------

.. index:: orphaned tokens, orphaned user data

When a user is deleted in the user store, behind privacyIDEA's back, some of
their data stays in the database: their settings, their custom and internal
attributes, and the tokens and containers still assigned to them.
:ref:`pi-tokenjanitor <pi-tokenjanitor>` finds these orphans::

   pi-tokenjanitor user-settings
   pi-tokenjanitor custom-attributes
   pi-tokenjanitor internal-attributes
   pi-tokenjanitor find --orphaned True
   pi-tokenjanitor container --orphaned True

Each command lists what it found. Append ``delete`` to remove it, e.g.
``pi-tokenjanitor user-settings delete``. The ``user-settings``,
``custom-attributes`` and ``internal-attributes`` deletes ask for confirmation
unless you pass ``--yes``. ``find ... delete`` and ``container ... delete``
delete right away, without asking. The ``container`` delete keeps the tokens of
the containers unless you add ``--tokens``.

These commands are deliberately not scheduled. They consider a user gone when
the user store does not return them, and a misconfigured resolver - a wrong base
DN, a broken search filter - returns no user without reporting an error, so an
unattended ``delete`` would remove the data of every user. A user whose user
store cannot be reached is skipped. To count such users as gone anyway, pass
``--orphaned-on-error`` before the subcommand, e.g.
``pi-tokenjanitor user-settings --orphaned-on-error list``; ``container`` has no
such option.
The commands also ask the user store about every single entry, which takes a
while with many users. The leftovers only appear when users are deleted and
cost little, so run the commands by hand from time to time and check the list
before you delete anything.
