.. _counterhandler:

Counter Handler Module
----------------------

.. index:: Counter Handler, Handler Modules

The counter event handler module is used to count certain events.
You can define arbitrary counter names and each occurrence of an event will
modify the counter in the counter table according to the selected action.

These counters can be used to graph time series of failed authentication, assigned tokens,
user numbers or any other data with any condition over time.

Possible Actions
~~~~~~~~~~~~~~~~

increase_counter
................

This action increases the counter in the database table ``eventcounter``.
If the counter does not exists, it will be created and increased.

decrease_counter
................

This action decreases the counter in the database table ``eventcounter``.
If the counter does not exists, it will be created and decreased.

  .. note::  This action will not decrease the counter beyond zero unless the option
    :ref:`pi_doc_eventhandler_counter` is enabled.

reset_counter
.............

This action resets the counter in the database table ``eventcounter`` to ``zero``.


Possible Options
~~~~~~~~~~~~~~~~

counter_name
............

This is the name of the counter in the database.
You can have as many counters in as many event handlers as you like.

.. _pi_doc_eventhandler_counter:

allow_negative_values
.....................

Only available for the ``decrease_counter`` action. Allows the counter to become negative. If set
 to ``False`` (default) decreasing stops at ``zero``.
 .. note:: Since the option ``allow_negative_values`` is an attribute of the counter event
 handler action (and not the counter itself in the database) it is possible to define multiple
 event handler accessing the same counter. Thus if a negative counter is accessed by an event
 handler with the option ``allow_negative_values`` set to true, the counter will be reset to
 ``zero``
