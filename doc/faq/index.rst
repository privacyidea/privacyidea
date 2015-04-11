.. _faq:

Frequently Asked Questions
==========================

.. index:: FAQ

How can I create users in the privacyIDEA Web UI?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

So you installed privacyIDEA and want to enroll tokens to the users and are
wondering how to create users.

privacyIDEA itself does not manage users and therfor you do not need to
create users.

You very much likely already have an application (like your VPN or a Web
Application...) for which you want to increase the logon security. Then this
application already knows users. Either in an LDAP or in an SQL database.
Most web applications keep their users in a (My)SQL database.
And you also need to create users in this very user database for the user to
be able to use this application.

So there is no sense in creating the user in the application **and** in
privacyIDEA. Right?

This is why you can not create users in privacyIDEA but you only need to tell
privacyIDEA where the users are located
and you can start enrolling tokens to those users.

Please read the sections :ref:`useridresolvers` and :ref:`userview` for more
details.

So what's the thing with all the admins?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: admin accounts, pi-manage

privacyIDEA comes with its own admins, who are stored in a database table
``Admin`` in its own database (:ref:`code_db`). You can use the tool
``pi-manage.py`` to
manage those admins from the command line as the system's root user. (see
:ref:`installation`)

These admin users can logon to the WebUI using the admin's user name and the
specified password.
These admins are used to get a simple quick start.

Then you can define realms (see :ref:`realms`), that should be administrative
realms. I.e. each user in this realm will have administrative rights in the
WebUI.

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






