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

.. index:: realm edit

Each realm has to have a unique name. The name of the realm is 
case insensitive. If you create a new realm with the same name
like an existing realm, the existing realm gets overwritten.

If you click *Edit Realm* you can select which userresolver should be
contained in this realm. A realm can contain several resolvers.

.. figure:: images/edit-realm.png
   :width: 500

   *Edit a realm*

.. _autocreate_realm:

Autocreate Realm
................

.. index:: realm autocreation

.. figure:: images/ask-create-realm.png
   :scale: 40 %

If you have a fresh installation, no resolver and no realm is
defined. To get you up and running faster, the system
will ask you, if it should create the first realm for you.

If you answer "yes", it will create a resolver named "deflocal"
that contains all users from /etc/passwd and a realm named
"defrealm" with this very resolver.

Thus you can immediately start assigning and enrolling tokens.

If you check "Do not ask again" this will be stored in 
a cookie in your browser.

.. note:: The realm "defrealm" will be the default realm. 
   So if you create a new realm manually and want this new
   realm to be the default realm, you need to set this new
   realm to be default manually.
