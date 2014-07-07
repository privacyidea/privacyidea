.. _machine_policies:

Machine policies
----------------

.. index:: machine policies

For the understanding of the idea of machines read :ref:`machines`.

Machine polcies are used to rule the actions of creating machines 
and adding tokens and applications to machines.
Technically admin policies controll the use of the :ref:`machine_controller`
and are checked using the method ``get_machine_manage_policies``
of the :ref:`code_policy_class`.

The ``user`` in the machine policies refers to the administrator.

.. note:: As long as no machine policy is defined all administrators
   are allowed to manage machines.


The following actions are available in the scope 
*machine*:

create
~~~~~~

type: bool

The administrator is allowed to create machine
definitions.


delete
~~~~~~

type: bool

The administrator can delete machine definitions.

show
~~~~

type: bool

The administrator can list the machine definitions.

addtoken
~~~~~~~~

type: bool

The administrator can add a token to a machine definition.

deltoken
~~~~~~~~

type: bool

The administrator can delete a token from a machine
definition.

showtoken
~~~~~~~~~

type: bool

The administrator can show the token assignments to
the machines.
