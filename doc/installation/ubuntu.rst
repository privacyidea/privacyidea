
.. _install_ubuntu:

Ubuntu Packages
---------------

.. index:: ubuntu

There are ready made packages for Ubuntu.
Up to privacyIDEA 2.23 packages are available for 
Ubuntu 14.04 LTS and 16.04 LTS [#ubuntu1604]_. 
These are available via a public ppa repository [#ppa]_.

Starting with privacyIDEA 3.0 packages are available 
for Ubuntu 16.04LTS and 18.04LTS [#ubuntu1804]_.

Installing privacyIDEA 3.0 or higher
....................................

Before installing privacyIDEA 3.0 or upgrading to 3.0 you need to add the repository.

.. _add_ubuntu_repository:

Add repository
~~~~~~~~~~~~~~

The packages are digitally signed. First you need to download the signing key::

   wget https://lancelot.netknights.it/NetKnights-Release.asc

On Ubuntu 16.04 check the fingerprint of the key::

   gpg --with-fingerprint NetKnights-Release.asc

On 18.04 you need to run::

   gpg --dry-run --import --with-fingerprint NetKnights-Release.asc

The fingerprint of the key is::

   pub 4096R/AE250082 2017-05-16 NetKnights GmbH <release@netknights.it>
   Key fingerprint = 0940 4ABB EDB3 586D EDE4 AD22 00F7 0D62 AE25 0082

Now add the signing key to your system::

   apt-key add NetKnights-Release.asc

Now you need to add the repository for your release (either xenial/16.04LTS or bionic/18.04LTS)

You can do this by running the command::

   add-apt-repository http://lancelot.netknights.it/community/xenial/stable

or::

   add-apt-repository http://lancelot.netknights.it/community/bionic/stable

As an alternative you can add the repo in a dedicated file. Create a new 
file ``/etc/apt/sources.list.d/privacyidea-community.list`` with the
following contents::

   deb http://lancelot.netknights.it/community/xenial/stable xenial main

or::

   deb http://lancelot.netknights.it/community/bionic/stable bionic main



New installation of privacyIDEA 3.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now run::

   apt update
   apt install privacyidea-apache2


.. _upgrade_ubuntu:

Upgrading privacyIDEA to 3.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to upgrade your privacyIDEA on Ubuntu to privacyIDEA 3.0,
you need to add a new repository configuration as described in 
:ref:`add_ubuntu_repository`.

Now you can simply run::

   apt update
   apt dist-upgrade

After this it is a good idea to remove old, unused packages by running::

   apt autoremove

Installing privacyIDEA 2.23
...........................

If you want to for any reason install the old version 2.23.x, this
is still available in a public ppa repository [#ppa]_.
Install it like this::

   add-apt-repository ppa:privacyidea/privacyidea
   apt-get update

There are the base packages ``python-privacyidea`` and the administrator
tool ``privacyideaadm``.

But we recommend installing the meta package::

   apt-get install privacyidea-apache2

which will install the code, the webserver and the database and configure
everything accordingly. If you do not like the Apache2 webserver you could
alternatively use the meta package ``privacyidea-nginx``.

After installing with Apache2 or Nginx you only need to create your first
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
.. [#ubuntu1804] Starting with privacyIDEA 3.0 Ubuntu 16.04 and 18.04 packages
   are provided, Ubuntu 14.04 packages are dropped.
