
.. _install_ubuntu:

Ubuntu Packages
---------------

.. index:: ubuntu

There are ready made packages for Ubuntu.

Packages of older releases of privacyIDEA up to version 2.23 are available for
Ubuntu 14.04 LTS and Ubuntu 16.04 LTS from a public ppa repository [#ppa]_.

For recent releases of privacyIDEA starting from version 3.0 a repository is
available which provides packages for Ubuntu 16.04 LTS and 18.04 LTS [#ubuntu]_.

.. note:: The packages ``privacyidea-apache2`` and ``privacyidea-nginx`` assume
   that you want to run a privacyIDEA system. These packages deactivate all
   other (default) websites. Instead, you may install the package
   ``privacyidea-mysql`` to install the privacyIDEA application and setup the
   database without any webserver configuration. After this, you can integrate
   privacyIDEA with your existing webserver configuration.

Read about the upgrading process in :ref:`upgrade_packaged`.

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

   gpg --import --import-options show-only --with-fingerprint NetKnights-Release.asc

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

.. note:: The link http://lancelot.netknights.it/community/.../stable is not
   ment to be called in the browser - you will get a 404. This is OK.
   This is not a link that is ment to be called directly. Rather it is used
   as a base for apt to fetch packages.
   If you still fail to fetch packages, you might most probably need to check
   your firewall and proxy settings.

Installation of privacyIDEA 3.x
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After having added the repositories, run::

   apt update
   apt install privacyidea-apache2

If you do not like the Apache2 webserver you could
alternatively use the meta package ``privacyidea-nginx``.

------------

Now you may proceed to :ref:`first_steps`.


.. _install_ubuntu_freeradius:

FreeRADIUS
..........

privacyIDEA has a perl module to "translate" RADIUS requests to the API of the
privacyIDEA server. This module plugs into FreeRADIUS. The FreeRADIUS does not
have to run on the same machine as privacyIDEA.
To install this module run::

   apt-get install privacyidea-radius

For further details see :ref:`rlm_perl`.

.. rubric:: Footnotes

.. [#ppa] https://launchpad.net/~privacyidea
.. [#ubuntu] Starting with privacyIDEA 2.15 Ubuntu 16.04 packages are
   provided. Starting with privacyIDEA 3.0 Ubuntu 16.04 and 18.04 packages
   are provided, Ubuntu 14.04 packages are dropped.
.. [#simpleSAML] https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
.. [#otrs] http://www.otrs.com/
