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

You can define as many polcies as you wish to.
The logic of the polcies in the scopes is additive.

.. figure:: policies.png
   :width: 500

   *policy definition*

Each policiy can contain the following attributes:

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

**realm**

  This is the realm, for which this policy is valid.

**client**

  This is the requesting client, for which this action is valid.
  I.e. you can define different policies if the user access the
  selfservice from different IP addresses.

**time**

  Not used, yet.


.. note:: Policies can be active or inactive. So be sure to activate a policy to 
   get the desired effect. 
