.. _usersview:

User View
=========

.. index:: usersview

The administrator can see all users in **realms** he is allowed 
to manage. 

.. note:: Users are only visible, if the useridresolver is located 
   within a realm. If you only define a useridresolver but no realm,
   you will not be able to see the users!

You can select one of the realms in the left drop down box. The administrator
will only see the realms in the drop down box, that he is allowed to manage.

.. todo:: update image usersview.png

.. figure:: usersview.png
   :width: 500

   *User View. List all users in a realm.*

The list shows the users from the select realm. The username, surname,
given name, email and phone are filled according to the definition of 
the useridresolver. 

Even if a realm contains several useridresolvers all users from all
resolvers within this realm are displayed.

.. toctree::
   :maxdepth: 1

   details
   manage
