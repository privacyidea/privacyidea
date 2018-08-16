.. _taskmodule_simplestats:

SimpleStats
-----------

The ``SimpleStats`` task module is a :ref:`periodic_tasks` to collect some basic statistics
from the token database and write them to the time series database table ``MonitoringStats``.

Options
~~~~~~~

The ``SimpleStats`` task module provides the following boolean options:

**total_tokens**

    If activated, the total number of tokens in the token database will be
    monitored.


**hardware_tokens**

    If activated, the total number of hardware tokens in the token database will
    be monitored.


**software_tokens**

    If activated, the total number of software tokens in the token database will
    be monitored.


**unassigned_hardware_tokens**

    If activated, the number of hardware tokens in the token database which are
    not assigned to a user will be monitored.


**assigned_tokens**

    If activated, the number of tokens in the token database which are assigned
    to users will be monitored.


**user_with_token**

    If activated, the number of users which have at least one token assigned
    will be monitored.

.. note:: The statistics key, with which the time series is identified in the
    ``MonitoringStats`` table, is the same as the option name.

    Using a statistic with the same key in a different module, which writes to the
    ``MonitoringStats`` table, will corrupt the data.

.. note:: For each of these basic statistic values the token database will be
    queried. To avoid excessive load on the database, the ``SimpleStats`` task
    should not be executed too often.
