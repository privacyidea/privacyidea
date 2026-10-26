How can I create users in the privacyIDEA Web UI?
-------------------------------------------------

.. index:: Creating Users

So you installed privacyIDEA and want to enroll tokens to the users and are
wondering how to create users.

privacyIDEA can read users from different existing sources like LDAP, SQL,
flat files, SCIM and HTTP-based user stores (a generic HTTP API, Microsoft
Entra ID, Keycloak).

You very likely already have an application (like your VPN or a Web
Application...) for which you want to increase the logon security. Then this
application already knows users. Either in an LDAP or in an SQL database.
Most web applications keep their users in a (My)SQL database.
And you also need to create users in this very user database for the user to
be able to use this application.

Please read the sections :ref:`useridresolvers` and :ref:`usersview` for more
details.

But you can also define an editable resolver. I.e. you can create and edit
users in the user store of an SQL, LDAP or HTTP-based resolver (HTTP, Entra
ID, Keycloak) that is marked as editable. An LDAP resolver also needs a DN
template for new users, and a generic HTTP resolver needs the requests for
creating, editing and deleting users.

If you do not have an existing SQL database with users, you can simply create
a new database with one table for the users and the corresponding columns.
