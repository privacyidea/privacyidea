.. _realms:

Realms
------

.. index:: realms, default realm

Users need to be in realms to have tokens assigned. A user, who is not
member of a realm can not have a token assigned and can not authenticate.

You can combine several different UserIdResolvers (see :ref:`useridresolvers`)
into a realm.
The system knows one default realm. Users within this default realm can 
authenticate with their username.

Users in realms, that are not the default realm, need to be additionally identified.
Therefor the users need to authenticate with their username and the realm like this::
   
   user@realm

.. _list_of_realms:

List of realms
..............

The realms dialog gives you a list of the already defined realms.

It shows the name of the realms, whether it is the default realm and
the names of the resolvers, that are combined to this realm.

You can delete or edit an existing realm or create a new realm.

.. _edit_realm:

Edit realm
..........

Each realm has to have a unique name. The name of the realm is 
case insensitive. If you create a new realm with the same name
like an existing realm, the existing realm gets overwritten.

The *Edit Realm* dialog gives you list of the available resolvers.
You can click on the resolvers to mark it to be added to this realm.
Holding the Ctrl-key while clicking lets you select multiple
resolvers.


