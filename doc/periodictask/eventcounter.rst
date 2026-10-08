.. _eventcounter:

EventCounter
------------

The Event Counter task module can be used with the :ref:`periodic_tasks` to create time series of certain events.
An event could be a failed authentication request. Using the Event Counter, privacyIDEA records how the number of
failed authentication requests develops over time. privacyIDEA does not display these values itself: an external
monitoring tool can read the time series with ``GET /monitoring/<stats_key>`` (see :ref:`rest_monitoring`), which needs
the admin right :ref:`policy_statistics_read`, and draw the graphs.

To do this, the Event Counter task module reads a counter value from the database table ``EventCounter`` and adds this
current value in a time series in the database table ``MonitoringStats``.
As the administrator can use the event handler :ref:`counterhandler` to record any arbitrary event under any condition,
this task module can be used to record any metric in privacyIDEA as a time series, be it failed authentication requests
per time unit, the number of token delete requests or the number of PIN resets per month.

Options
~~~~~~~

The Event Counter task module provides the following options:

**event_counter**

    This is the name of the event counter key that was defined in a :ref:`counterhandler` definition and that is
    read from the database table ``EventCounter``. The counter is created when the counter handler counts its first
    event. Until then the task writes no value but still counts as a successful run; it only logs a warning. A
    misspelled counter name therefore shows up as an empty time series and a warning in the privacyIDEA log.

**stats_key**

    This is the name of the statistics key that is written to the ``MonitoringStats`` database table.
    The event counter key stores the current number of counted events, the ``stats_key`` takes the current number
    and stores it with the timestamp as a time series.

**reset_event_counter**

    This is a boolean value. If it is set to true (the checkbox is checked), then the event counter will be reset to zero
    after the task module has read the key.

    Resetting the event counter results in a time series of "events per time interval". The time interval is
    specified by the time interval in which the Event Counter task module is called.
    If ``reset_event_counter`` is not checked, then the event handler will continue to increase the counter value.
    Use this if you want to create a time series that displays the absolute number of events.

