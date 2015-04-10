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

