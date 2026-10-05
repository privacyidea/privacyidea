Policies
--------

How to disable policies?
~~~~~~~~~~~~~~~~~~~~~~~~

I created an evil admin policy and locked myself out. How can I disable a
policy?

You can use :ref:`the pi-manage command line tool <pimanage_policy>` to list,
enable, disable and delete policies, e.g.::

   pi-manage config policy list
   pi-manage config policy disable <name>

A :ref:`conditional access <conditional_access>` policy is disabled with
``pi-manage conditionalaccess disable-policy <name>``, see
:ref:`pimanage_conditional_access`.


How do policies work anyway?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:ref:`policies` are just a set of definitions. These definitions are meant to
modify the way privacyIDEA reacts to requests. Different policies have
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

The :ref:`authorization_policies` decide, if a user, who would authenticate
successfully is *allowed* to issue this request. I.e. a user may present the
right credentials, but he is not allowed to log in from a specific IP address
or with a not secure token type (see :ref:`tokentype_policy`).

How is this technically achieved?
.................................

At the beginning of a request privacyIDEA creates a policy object of the class
``PolicyClass`` (see :ref:`code_policy`). The policy object does not store the
policies itself, but reads them from the request-local configuration object,
which caches the policy set from the database.

The logical part is performed by policy decorators. The decorators modify the
behavior of the above-mentioned endpoints.

Each policy has its own decorator. The decorator can be used on different
functions, methods, endpoints. The decorators are implemented in
``privacyidea/api/lib/prepolicy.py`` and ``privacyidea/api/lib/postpolicy.py``.

PrePolicy decorators are executed at the beginning of a request, PostPolicy
decorators at the end of the request.

To find the policies that apply to the request, a decorator uses the ``Match``
class in ``privacyidea/lib/policy.py``. Its class methods, e.g.
``Match.action_only``, ``Match.realm``, ``Match.user``, ``Match.token``,
``Match.admin`` or ``Match.admin_or_user``, match the active policies of a
scope and an action against the given realm, user, token or administrator.
The resulting ``Match`` object provides the result the decorator needs:

* ``any()`` tells whether a boolean action like :ref:`passonnotoken` is set,
* ``action_values()`` returns the defined value of a non-boolean action like
  :ref:`otppin_policy`,
* ``allowed()`` tells whether an action in the scope ``admin`` or ``user`` is
  allowed.

By default, the matched policies are written to the audit log.

All policies can depend on IP address, user and time. The ``Match`` class
takes the client IP address into account implicitly, and only policies that
are valid at the current time match.

.. note:: Each decorator represents one policy and defines its own logic,
   while the filtering by IP address, user and time is done by the ``Match``
   class.
