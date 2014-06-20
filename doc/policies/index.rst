.. _policies:

Policies
========

.. index:: policies, scope


Policies can be used to define the reaction and behaviour of the system.

Each policy defines the behaviour in a certain area, called scope. 
privacyIDEA knows the scopes:

  * admin
  * system 
  * selfservice
  * enrollment
  * authentication
  * authorization
  * audit
  * ocra
  * gettoken

You can define as many policies as you wish to.
The logic of the policies in the scopes is additive.

.. figure:: policies.png
   :width: 500

   *policy definition*

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
  A policy can contain several actions, seperated
  with a comma. Some scopes allow to use the wildcard `*` which
  indicates that all actions are allowed.
  Actions can be of type `boolean`, `string` or `integer`.
  Boolean actions are enabled by just adding this action.
  `string` and `integer` actions need to be configured like this::
      
      action=<value>

**user**

  This is the user, for whom this policy is valid. Depending on the scope
  the user is either an administrator or a normal authenticating user.

.. note:: In certain scopes the authentication ``user`` 
   contain a list of users and
   also resolvers, which are identified by a ":". The notation
   is *user:resolver*. A policy containing *user=:resolver1* will only
   be valid for the users in *resolver1*.


**realm**

  This is the realm, for which this policy is valid.

.. _client_policies:

**client**

  This is the requesting client, for which this action is valid.
  I.e. you can define different policies if the user access the
  selfservice from different IP addresses like the internal
  network or remotely via the firewall.

  You can enter an IP address or a subnet (like 10.2.0.0/16).

**time**

  Not used, yet.


.. note:: Policies can be active or inactive. So be sure to activate a policy to 
   get the desired effect. 

Read more about the specific policies in the scopes:

.. toctree::

  admin
  system
  selfservice
  enrollment
  authentication
  authorization
  audit
  ocra
  gettoken

