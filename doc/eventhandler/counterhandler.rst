.. _counterhandler:

Counter Handler Module
----------------------

.. index:: Counter Handler, Handler Modules

The counter event handler module is used to count certain events.
You can define arbitrary counter names and each occurrence of an event will
increase the counter in the counter table.

These counters can be used to graph time series of failed authentication, assigned tokens,
user numbers or any other data with any condition over time.

Possible Actions
~~~~~~~~~~~~~~~~

increase_counter
................

This action increases the counter in the database table ``eventcounter``.

Possible Options
~~~~~~~~~~~~~~~~

counter_name
............

This is the name of the counter in the database.
You can have as many counters in as many event handlers as you like.