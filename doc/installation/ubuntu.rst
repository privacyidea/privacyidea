
.. _install_ubuntu:

Ubuntu Packages
---------------

.. index:: ubuntu

There are ready made packages for Ubuntu.

A repository provides packages for Ubuntu 22.04 LTS, 24.04 LTS and 26.04 LTS.

.. note:: The packages ``privacyidea-apache2`` and ``privacyidea-nginx`` assume
   that you want to run a privacyIDEA system. These packages deactivate all
   other (default) websites. Instead, you may install only the package
   ``privacyidea``, which contains the privacyIDEA application without any
   webserver or database configuration. After this, you can integrate
   privacyIDEA with your existing webserver configuration.

Read about the upgrading process in :ref:`upgrade_packaged`.

Installing privacyIDEA
......................

Before installing privacyIDEA you need to add the package repository to the package manager.

.. _add_ubuntu_repository:

Add repository
~~~~~~~~~~~~~~

The packages are digitally signed. First you need to download the signing key::

   wget https://lancelot.netknights.it/NetKnights-Release.asc

Then you can verify the fingerprint::

   gpg --import --import-options show-only --with-fingerprint NetKnights-Release.asc

The fingerprint of the key is::

   pub 4096R/AE250082 2017-05-16 NetKnights GmbH <release@netknights.it>
   Key fingerprint = 0940 4ABB EDB3 586D EDE4 AD22 00F7 0D62 AE25 0082

Now you can add the signing key to your system::

   mv NetKnights-Release.asc /etc/apt/trusted.gpg.d/

Now you need to add the repository for your release (either ``jammy/22.04 LTS``,
``noble/24.04 LTS`` or ``resolute/26.04 LTS``).

You can do this by running the following command on Ubuntu 24.04::

   add-apt-repository http://lancelot.netknights.it/community/noble/stable

Change the code name to the running Ubuntu version accordingly.

As an alternative you can add the repo in a dedicated file. Create a new
file ``/etc/apt/sources.list.d/privacyidea-community.list`` with the
following contents for Ubuntu 24.04::

    deb http://lancelot.netknights.it/community/noble/stable noble main

Change the code name to the running Ubuntu version accordingly.

Installation of privacyIDEA
~~~~~~~~~~~~~~~~~~~~~~~~~~~

After having added the repositories, run::

   apt update
   apt install privacyidea-apache2

If you do not like the Apache2 webserver you could
alternatively use the meta package ``privacyidea-nginx``.

Both packages also install the cron jobs that clean up the database, see
:ref:`cleanup_jobs`.

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

The ``privacyidea-radius`` package is available for Ubuntu 22.04 LTS and 24.04 LTS.

For further details see :ref:`rlm_perl`.
