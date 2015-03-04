.. _policies:

Policies
========

.. index:: policies, scope


Policies can be used to define the reaction and behaviour of the system.

Each policy defines the behaviour in a certain area, called scope. 
privacyIDEA knows the scopes:

.. toctree::
   :maxdepth: 1

   admin
   user
   authentication
   authorization
   enrollment
   webui
   audit  **(TODO)**: not migrated, yet.
   machine **(TODO)**: not migrated, yet.
   ocra **(TODO)**: not migrated, yet.
   gettoken **(TODO)**: not migrated, yet.

You can define as many policies as you wish to.
The logic of the policies in the scopes is additive.

.. figure:: policies.png
   :width: 500

   *Policy Definition*

Each policy can contain the following attributes:

**policy name**

  A unique name of the policy. The name is the identifier of
  the policy. If you create a new policy with the same name,
  the policy is overwritten.

**scope**

  The scope of the policy as described above.

**action**

  This is the important part of the policy. 
  Each scope provides its own
  set of actions. 
  An action describes that something is `allowed` or
  that some behaviour is configured.
  A policy can contain several actions.
  Actions can be of type `boolean`, `string` or `integer`.
  Boolean actions are enabled by just adding this action - like
  ``scope=user:action=disable``, which allows the user to disable his own
  tokens.
  `string` and `integer` actions require an additional value - like
  ``scope=authentication:action='otppin=userstore'``.

**user**

  This is the user, for whom this policy is valid. Depending on the scope
  the user is either an administrator or a normal authenticating user.

  If this field is left blank, this policy is valid for all users.

**resolver**

  This policy will be valid for all users in this resolver.

  If this field is left blank, this policy is valid for all resolvers.

**realm**

  This is the realm, for which this policy is valid.

  If this field is left blank, this policy is valid for all realms.

.. _client_policies:

**client**

  This is the requesting client, for which this action is valid.
  I.e. you can define different policies if the user access is
  allowed to manage his tokens from different IP addresses like the internal
  network or remotely via the firewall.

  You can enter several IP addresses or subnets divided by comma
  (like ``10.2.0.0/16, 192.168.0.1``).

**time**

  Not used, yet.


.. note:: Policies can be active or inactive. So be sure to activate a policy to 
   get the desired effect. 

