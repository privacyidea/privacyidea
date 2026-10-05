How can I set up HA (High Availability) with privacyIDEA?
---------------------------------------------------------

.. index:: HA

privacyIDEA does not track any state internally. All information is kept in
the database. Thus you can configure several privacyIDEA instances against one
DBMS [#dbms]_ and have the DBMS do the high availability.

.. note:: The passwords and OTP key material in the database are encrypted
   using the *encKey*. Thus it is possible to put the database onto a DBMS
   that is controlled by another database administrator in another department.

.. _ha_setups:

HA setups
.........

When running HA you need to make sure that the *pi.cfg* file is configured on
all privacyIDEA instances. You might need to adapt the
``SQLALCHEMY_DATABASE_URI``.

Be sure to set the same ``SECRET_KEY`` and ``PI_PEPPER`` on all instances.

Then you need to provide the same encryption key (file *encKey*) and the same
audit signing keys on all instances.

Using one central DBMS
~~~~~~~~~~~~~~~~~~~~~~

.. figure:: images/ha-one-dbms.png
   :width: 500

If you already have a highly available, redundant DBMS -
like MariaDB Galera Cluster - which might even be
addressable via one cluster IP address the configuration is fairly simple.
In such a case you can configure the same ``SQLALCHEMY_DATABASE_URI`` on all
instances.

Using MySQL replication between two servers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. figure:: images/ha-master-master.png
   :width: 500

If you have no DBMS or might want to use a dedicated database server for
privacyIDEA, you can set up one MySQL server per privacyIDEA instance and
configure the two MySQL servers to replicate from each other, so that each
server is both source and replica of the other (formerly called
master-master replication).

.. note:: This setup only works with two MySQL servers.

The replication setup is described in the MySQL Reference Manual [#mysqlreplication]_.

.. rubric:: Footnotes

.. [#dbms] Database management system
.. [#mysqlreplication] https://dev.mysql.com/doc/refman/8.4/en/replication.html
