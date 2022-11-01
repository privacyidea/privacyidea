.. _migration_strategies:

What are possible migration strategies?
---------------------------------------

.. index:: migration strategy, migration, radius server, radius migration

You are already running an OTP system like RSA SecurID, SafeNet or Vasco
(alphabetical order) but you would like to migrate to privacyIDEA.

There are different migration strategies using the
:ref:`radius_token` token or the RADIUS :ref:`passthru_policy` policy.

RADIUS token migration strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure your application like your VPN to authenticate against the
privacyIDEA RADIUS server and not against the old deprecated RADIUS server.

Now, you can enroll a :ref:`radius_token` token for each user, who is supposed to
login to this application. Configure the RADIUS token for each user so that
the RADIUS request is forwarded to the old RADIUS server.

Now you can start to enroll tokens for the users within privacyIDEA. After
enrolling a new token in privacyIDEA you can delete the RADIUS token for this
user.

When all RADIUS tokens are deleted, you can switch off the old RADIUS server.

For strategies on enrolling token see :ref:`rollout_strategies`.

RADIUS PASSTHRU policy migration strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Configure your application like your VPN to authenticate against the
privacyIDEA RADIUS server and not against the old deprecated RADIUS server.

Starting with privacyIDEA 2.11 the :ref:`passthru_policy` policy was enhanced. You
can define a system wide RADIUS server. Then you can create a
*authentication* policy with the passthru action pointing to this RADIUS
server. This means that - as long as a user trying to authenticate - has not
token assigned, all authentication request with this very username and the
password are forwarded to this RADIUS server.

As soon as you enroll a new token for this user in privacyIDEA the user will
authenticate with this very token within privacyIDEA an his authentication
request will not be forwarded anymore.

As soon as all users have a new token within privacyIDEA, you can switch of
the old RADIUS server.

For strategies on enrolling token see :ref:`rollout_strategies`.

Some dull changes
