.. _eventhandler:

Event Handler
=============

.. index:: Event Handler, events

Added in version 2.12.

What is the difference between :ref:`policies` and event handlers?

Policies are used to define the behaviour of the system. With policies you
can *change* the way the system reacts.

With event handlers you do not change the way the system reacts. But on
certain events you can *trigger a new action* in addition to the behaviour
defined in the policies.

Events
------

Each **API call** is an **event** and you can bind arbitrary actions to each
event as you like.

Internally events are marked by a decorator "event" with an *event identifier*.
At the moment not all events might be tagged. Please drop us a note to tag
all further API calls.

.. figure:: event-list.png
   :width: 500

   *An action is bound to the event* token_init.

.. _handlermodules:

Handler Modules and Actions
---------------------------

.. index:: Handler Modules, Actions

The actions are defined in handler modules. So you bind a handler module and
the action, defined in the handler module, to the events.

The handler module can define several actions and each action in the handler
module can require additional options.

.. figure:: event-details.png
   :width: 500

   *The event* sendmail *requires the option* emailconfig.

Conditions
----------

.. index:: Event Handler, conditions

Added in version 2.14

And event handler module may also contain conditions. Only if all conditions
are fullfilled, the action is triggered. Conditions are defined in the class
property *conditions* and checked in the method *check_condition*. The
UserNotification Event Handler defines such conditions.


Available Handler Modules
~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   usernotification
   tokenhandler
