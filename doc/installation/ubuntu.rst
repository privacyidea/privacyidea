
.. _install_ubuntu:

Ubuntu Packages
---------------

.. index:: ubuntu

There are ready made debian packages for Ubuntu 14.04 LTS.
These are available in a public ppa repository [#ppa]_,
so that the installation
will automatically resolve all dependencies.
Install it like this::

   add-apt-repository ppa:privacyidea/privacyidea
   apt-get update
   apt-get install python-privacyidea privacyideaadm

Optionally you can also install necessary configuration files to run
privacyIDEA within the Nginx Webserver::

   apt-get install privacyidea-nginx

Alternatively you can install privacyIDEA running in an Apache webserver::

   apt-get install privacyidea-apache2

After installing in Nginx or Apache2 you only need to create your first
administrator and you are done::

   pi-manage.py admin add admin admin@localhost


Now you may proceed to :ref:`first_steps`.

.. _install_ubuntu_freeradius:

FreeRADIUS
..........

privacyIDEA has a perl module to "translate" RADIUS requests to the API of the
privacyIDEA server. This module plugs into FreeRADIUS. The FreeRADIUS does not
have to run on the same machine like privacyIDEA.
To install this module run::

   apt-get install privacyidea-radius

For further details see :ref:`freeradius_plugin`.

.. _install_ubuntu_simplesaml:

SimpleSAMLphp
.............

Starting with 1.4 privacyIDEA also supports SAML via a plugin
for simpleSAMLphp [#simpleSAML]_.
The simpleSAMLphp service does not need to run on the same machine
like the privacyIDEA server.

To install it on a Ubuntu 14.04 system please run::

   apt-get install privacyidea-simplesamlphp

For further details see :ref:`simplesaml_plugin`.


.. rubric:: Footnotes

.. [#ppa] https://launchpad.net/~privacyidea
.. [#simpleSAML]  https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
