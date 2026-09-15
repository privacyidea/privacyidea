.. _containerhandler:

Container Handler Module
------------------------

.. index:: Container Handler, Handler Modules

The container event handler module is used to perform actions on containers and their tokens in
certain events. The container is either identified by the container serial from the request, response or from an
identified token.

This way you can define workflows to automatically modify containers, delete or
even create new containers. Additionally, the tokens in the container can be modified.

Possible Actions
~~~~~~~~~~~~~~~~
create
......
A new container will be created. This new container can be assigned to a user, which was identified in the request.
Additionally, a token identified in the request can be added to the container.

The administrator has to specify the **containertype** and can optionally specify a **description**.

delete
......

The container which was identified in the request will be deleted if all
conditions are matched. The tokens in the container will not be deleted.

unassign
........

The container which was identified in the request will be unassign from all users
if all conditions are matched. The tokens in the container will not be changed.

assign
......

The container which was identified in the request will be assigned to a user which was identified in the request.
If the logged in user performing this action has the role 'user' it is always himself. The user is not assigned to the
tokens in the container.

set states
..........

The administrator can specify states that will be set on the container identified in the request. All other states
will be removed.

The administrator can select the new **states**. If no state is selected, all states will be removed.

add states
..........

The administrator can specify states that will be added to the container identified in the request.
Previous states that are excluded by the new states will be removed. All other states that are not exclusive are kept.

The administrator can select the new **states**. If no state is selected, nothing happens.

set description
...............

For the container identified in the request a new **description** will be set.

The **description** may contain tags that are replaced when the event is handled.
The tag ``{now}`` is replaced by the current timestamp and supports offsets like
``{now}+5d`` or ``{now}-30m`` (``s``, ``m``, ``h``, ``d``); ``{current_time}`` is a
deprecated alias for it. The tags of the notification handlers are available as
well, for example ``{client_ip}``, ``{ua_browser}``, ``{ua_string}``,
``{container_serial}``, ``{username}`` and ``{userrealm}``. ``{username}`` and
``{userrealm}`` describe the owner of the container, ``{admin}`` and ``{realm}`` the
acting administrator. A tag that can not be replaced does not fail the event
handling, the text is then written as it was entered.

remove all tokens
.................

All tokens will be removed from the container identified in the request.

set container info
..................

For the container identified in the request the container info will be set. All previous entries will be removed.

It requires the specification of a **key** and optionally a **value**. If no value is defined, it is set to an empty
string "".

The **value** may contain tags that are replaced when the event is handled.
The tag ``{now}`` is replaced by the current timestamp and supports offsets like
``{now}+5d`` or ``{now}-30m`` (``s``, ``m``, ``h``, ``d``); ``{current_time}`` is a
deprecated alias for it. The tags of the notification handlers are available as
well, for example ``{client_ip}``, ``{ua_browser}``, ``{ua_string}``,
``{container_serial}``, ``{username}`` and ``{userrealm}``. ``{username}`` and
``{userrealm}`` describe the owner of the container, ``{admin}`` and ``{realm}`` the
acting administrator. A tag that can not be replaced does not fail the event
handling, the value is then written as it was entered.

add container info
..................

For the container identified in the request the container info will be added. Previous entries will be kept. Only if
the given key already exists, an old entry will be overwritten.

It requires the specification of a **key** and a optionally **value**. If no value is defined, it is set to an empty
string "".

The **value** may contain tags that are replaced when the event is handled.
The tag ``{now}`` is replaced by the current timestamp and supports offsets like
``{now}+5d`` or ``{now}-30m`` (``s``, ``m``, ``h``, ``d``); ``{current_time}`` is a
deprecated alias for it. The tags of the notification handlers are available as
well, for example ``{client_ip}``, ``{ua_browser}``, ``{ua_string}``,
``{container_serial}``, ``{username}`` and ``{userrealm}``. ``{username}`` and
``{userrealm}`` describe the owner of the container, ``{admin}`` and ``{realm}`` the
acting administrator. A tag that can not be replaced does not fail the event
handling, the value is then written as it was entered.

delete container info
.....................

For the container identified in the request the container info will be deleted. If a **key** is specified, only the
entry of this key will be deleted. If no key is passed, all entries will be removed.

enable all tokens
.................

For the container identified in the request all contained tokens will be enabled.

disable all tokens
..................

For the container identified in the request all contained tokens will be disabled.

unregister
..........

The container identified in the request will be unregistered. Synchronization with the smartphone is not possible
anymore.

Code
~~~~

.. automodule:: privacyidea.lib.eventhandler.containerhandler
   :members:
   :undoc-members:
