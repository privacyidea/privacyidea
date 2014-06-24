.. _system_policies:

System policies
---------------

.. index:: system policies

System policies are used to regulate the configuration of the system.
This is defining useridresolvers and realms, setting token defaults
and defining system configuration.

If no system policy is defined, each administrator is allowed
to do everything in the scope system.

Technically system policies controll if the administrator is able
to write to the database table *Config* or if the administrator
can use of the :ref:`system_controller`.
System policies are checked using the method ``getAuthorization``
of the :ref:`code_policy_class`.

The ``user`` in the system policies refers to the administrator.

.. note:: System policies do not make use of realms!

.. warning:: Creating policies is an act of writing the 
   system configuration. So if you define admin policies
   and do not define system policies, every administrator
   can still change the policies! The recommended way is
   to create your admin policies and then create the
   system policies.

 
The following actions are available in the scope 
*system*:

read
~~~~

type: bool

The administrator is allowed to read the system configuration.
A token administrator might not be allowed to read system
configuration to avoid letting him know which realms and
userresolvers exist.

write
~~~~~

type: bool

The administrator is allowed to write system configuration.

