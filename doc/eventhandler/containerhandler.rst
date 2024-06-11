.. _containerhandler:

Container Handler Module
--------------------

.. index:: Container Handler, Handler Modules

The container event handler module is used to perform actions on containers in
certain events.

This way you can define workflows to automatically modify containers, delete or
even create new containers.

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
conditions are matched.

unassign
........

The container which was identified in the request will be unassign from all users
if all conditions are matched.

assign
........

The container which was identified in the request will be assigned to a user which was identified in the request.

set states
..........

The administrator can specify states that will be set on the container identified in the request. All other states
will be removed.

The administrator can select the new **states**. If no states is selected, all states will be removed.

add states
..........

The administrator can specify states that will be added to the container identified in the request.
Previous states that are excluded by the new states will be removed. All other states that are not exclusive are kept.

The administrator can select the new **states**. If no state is selected, nothing happens.

set description
...............

For the container identified in the request a new **description** will be set.

remove tokens
..............

For the container identified in the request all tokens will be removed.

set container info
..................

For the container identified in the request the container info will be set. All previous entries will be removed.

It requires the specification of a **key** and a optionally a **value**. If no value is defined it is set to an empty
string "".

add container info
..................

For the container identified in the request the container info will be added. Previous entries will be kept. Only if
the given key already exists, an old entry will be overwritten.

It requires the specification of a **key** and a optionally a **value**. If no value is defined it is set to an empty
string "".

delete container info
.....................

For the container identified in the request the container info will be deleted. If a **key** is specified, only the
entry of this key will be deleted. If no key is passed, all entries will be removed.

Code
~~~~

.. automodule:: privacyidea.lib.eventhandler.containerhandler
   :members:
   :undoc-members: