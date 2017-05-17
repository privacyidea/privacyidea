
.. _install_ubuntu:

Ubuntu Packages
---------------

.. index:: ubuntu

There are ready made packages for Ubuntu 14.04 LTS and 16.04 LTS [#ubuntu1604]_.
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

   pi-manage admin add admin -e admin@localhost


Now you may proceed to :ref:`first_steps`.

.. note:: The packages *privacyidea-apache2* and *privacyidea-nginx* assume
   that you want to run a privacyIDEA system. These packages deactivate all
   other (default) websites. You can install the package
   *privacyidea-mysql* to install the privacyIDEA application and setup the
   database. After this, you need to configure the webserver on your own.

.. note:: To get the latest development snapshots, you can use the repository
   *ppa:privacyidea/privacyidea-dev*. But these packages might be broken
   sometimes!

.. _install_ubuntu_freeradius:

FreeRADIUS
..........

privacyIDEA has a perl module to "translate" RADIUS requests to the API of the
privacyIDEA server. This module plugs into FreeRADIUS. The FreeRADIUS does not
have to run on the same machine like privacyIDEA.
To install this module run::

   apt-get install privacyidea-radius

For further details see :ref:`rlm_perl`.

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

PAM
....

.. index:: PAM

privacyIDEA also comes with a PAM library to add two factor authentication to
any Linux system. You can run one central privacyIDEA server and configure
all other systems using the PAM library to authenticate against this
privacyIDEA.

To install it on a Ubuntu 14.04 system please run::

   apt-get install privacyidea-pam

For further details see :ref:`pam_plugin`.

OTRS
....

.. index:: OTRS

OTRS is an important Open Source Ticket Request System. It is written in Perl
and privacyIDEA provides an authentication plugin to authenticate at OTRS
with two factors.

To install it on Ubuntu 14.04 please run::

   apt-get install privacyidea-otrs

For further details and configuration see :ref:`otrs_plugin`.

.. rubric:: Footnotes

.. [#ppa] https://launchpad.net/~privacyidea
.. [#simpleSAML] https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
.. [#otrs] http://www.otrs.com/
.. [#ubuntu1604] Starting with privacyIDEA 2.15 Ubuntu 16.04 packages are
   provided
