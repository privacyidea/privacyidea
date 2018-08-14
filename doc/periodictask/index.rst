.. _periodic_tasks:

Periodic Tasks
==============

.. index:: periodic task, recurring task

Starting with version 2.23, privacyIDEA comes with the ability to define periodically recurring tasks
in the Web UI. Currently, the primary purpose of such tasks is to periodically collect statistical information,
but in the future they might be useful to automatically perform cleanups on the database level.

As privacyIDEA is a web application, it does not actually execute the defined periodic tasks. For that,
privacyIDEA comes with a script ``privacyidea-cron`` which must be invoked by the system cron daemon.
This can, for example, be achieved by creating a file ``/etc/cron.d/privacyidea`` with the following
contents (this is done automatically by the Ubuntu package)::

	 */5 * * * *	privacyidea	privacyidea-cron run_scheduled -c

This would tell the system cron daemon to invoke the ``privacyidea-cron`` script every five minutes. At
each invocation, the ``privacyidea-cron`` script would determine which tasks should be executed and
execute the scheduled tasks. The ``-c`` option tells the script to be quiet and only print to stderr
in case of an error (see :ref:`periodictask_cron`).

Periodic tasks can be managed in the WebUI by navigating to *Config* and *Periodic Tasks*:

.. figure:: periodictasks.png

	Periodic task definitions

Every periodic task has the following attributes:

**description**
	A human-readable, unique identifier

**active**
	A boolean flag determining whether the periodic task should be run or not.

**order**
	A number (at least zero) that can be used to fix the order of periodic tasks. This is
	used by ``privacyidea-cron`` to determine the running order of tasks if multiple
	periodic tasks are scheduled to be run. Tasks with a lower number are run first.

**interval**
	The periodicity of the task. This uses crontab notation, e.g. ``*/30 * * * *`` runs
	the task every 30 minutes.

	Keep in mind that the entry in the system crontab determines the minimal resolution
	of periodic tasks: If you specify a periodic task that should be run every two minutes,
	but the ``privacyidea-cron`` script is invoked every five minutes only, the periodic task
	will actually be executed every five minutes!

**nodes**
	The names of the privacyIDEA nodes on which the periodic task should be executed.
	This is useful in a redundant master-master setup, because database-related task should then
	only be run on *one* of the nodes (because the replication will take care of
	propagating the database changes to the other node). The name of the local node
	as well as the names of remote nodes are configured in :ref:`inifile`.

**taskmodule**
	The taskmodule determines the actual activity of the task. privacyIDEA comes
	with several taskmodules, see :ref:`periodic_task_modules`.

**options**
	The options are a set of key-value pairs that configure the behavior of the taskmodule.

.. _periodic_task_modules:

Taskmodules
~~~~~~~~~~~

privacyIDEA comes with the following taskmodules:

.. toctree::
   :maxdepth: 1

   simplestats
   eventcounter


.. _privacyidea_cron:

The ``privacyidea-cron`` script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``privacyidea-cron`` script is used to execute periodic tasks defined in the Web UI. The
``run_scheduled`` command collects all active jobs that are scheduled to run on the current node
and executes them. The order is determined by their ``ordering`` values (tasks with low values
are executed first). The ``-c`` option causes the script to is useful if the script is executed via the system
crontab, as it causes the script to only

The ``list`` command can be used to get an overview of defined jobs, and the ``run_manually``
command can be used to manually invoke tasks even though they are not scheduled to be run.