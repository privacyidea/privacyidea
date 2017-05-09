.. _faq_admins:

So what's the thing with all the admins?
----------------------------------------

.. index:: admin accounts, pi-manage

privacyIDEA comes with its own admins, who are stored in a database table
``Admin`` in its own database (:ref:`code_db`). You can use the tool
``pi-manage`` to
manage those admins from the command line as the system's root user. (see
:ref:`installation`)

These admin users can logon to the WebUI using the admin's user name and the
specified password.
These admins are used to get a simple quick start.

Then you can define realms (see :ref:`realms`), that should be administrative
realms. I.e. each user in this realm will have administrative rights in the
WebUI.

.. note:: You need to configure these realms within privacyIDEA. Only
   after these realms exist, you can raise their rights to an administrative
   role.

.. note:: Use this carefully. Imagine you defined a resolver to a specific
   group in your Active Directory to be the pricacyIDEA admins. Then the Active
   Directory domain admins can
   simply add users to be administrator in privacyIDEA.

You define the administrative realms in the config file ``pi.cfg``, which is
usually located at ``/etc/privacyidea/pi.cfg``::

   SUPERUSER_REALM = ["adminrealm1", "super", "boss"]

In this case all the users in the realms "adminrealm1", "super" and "boss"
will have administrative rights in the WebUI, when they login with this realm.

As for all other users, you can use the :ref:`policy_login_mode` to define,
if these administrators should login to the WebUI with their userstore password
or with an OTP token.
