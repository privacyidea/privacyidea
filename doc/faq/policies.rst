Policies
--------

How to disable policies?
~~~~~~~~~~~~~~~~~~~~~~~~

I create an evil admin policy and locked myself out. How can I disable a
policy?

You can use the *pi-manage* command line tool to list, enable and disable
policies. See

   pi-manage policy -h


How do policies work anyway?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:ref:`policies` are just a set of definitions. These definitions are ment to
modify the way privacyIDEA reacts on requests. Different policies have
different **scopes** where they act.

*admin* policies define, what an administrator is
allowed to do. These policies influence endpoints like ``/token``, ``/realm``
and all other endpoints, which are used to configure the system.
(see :ref:`admin_policies`)

*user* policies define, how the system reacts if a user is managing his own
tokens.
(see :ref:`user_policies`)

*authentication* and *authorization* policies influence the */validate/*
endpoint (:ref:`rest_validate`).

The :ref:`authentication_policies` define if an authentication request would
be successful at all. So it defines how to really check the authentication
request. E.g. this is done by defining if the user has to add a specific OTP
PIN or his LDAP password (see :ref:`otppin_policy`).

The :ref:`authorization_policies` decide, if a user, who would authentication
successfully is *allowed* to issue this request. I.e. a user may present the
right credentials, but he is not allowed to login from a specific IP address
or with a not secure token type (see :ref:`tokentype_policy`).

How is this technically achieved?
.................................

At the beginning of a request the complete policy set is read from the
database into a policy object, which is a singleton of PolicyClass (see
:ref:`code_policy`).

The logical part is performed by policy decorators. The decorators modify the
behaviour of the above mentioned endpoints.

Each policy has its own decorator. The decorator can be used on different
functions, methods, endpoints. The decorators are implemented in
api/lib/prepolicy.py and api/lib/postpolicy.py.

PrePolicy decorators are executed at the beginning of a request, PostPolicy
decoratros at the end of the request.

A policy decorator uses one of the methods get_action_value or get_policies.

get_policies is used to determine boolean actions like
:ref:`passonnotoken_policy`.

get_action_value is used to get the defined value of non-boolean policies
like :ref:`otppin_policy`.

All policies can depend on IP address, user and time. So these values are
taken into account by the decorator when determining the defined policy.

.. note:: Each decorator represents one policy and defines its own logic
   i.e. checking filtering for IP address and fetching the necessary policy
   sets from the policy object.



