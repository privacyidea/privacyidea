.. _installation:

Installation
============

The two ways described here to install privacyIDEA are

 * the installation via the python package index, which can be used on
   any Linux distribution and
 * ready made debian packages for Ubuntu 14.04LTS.

If you want to upgrade from a privacyIDEA 1.5 installation please read :ref:`upgrade`.

Python Package Index
--------------------

.. index:: pip install, virtual environment

You can install privacyidea on usually any Linux distribution in a python
virtual environment
like this::

  virtualenv /opt/privacyidea

  cd /opt/privacyidea
  source bin/activate

Now you are within the python virtual environment.
Within the environment you can now run::

  pip install privacyidea

.. _configuration:

Please see the section :ref:`cfgfile` for a quick setup of your configuration.


Then create the encryption key and the signing keys::

   pi-manage.py create_enckey
   pi-manage.py create_signkey

Create the database and the first administrator::

   pi-manage.py createdb
   pi-manage.py admin add admin admin@localhost

Now you can run the server for your first test::

   pi-manage.py runserver


Depending on the database you want to use, you may have to install additional packages.


Debian packages
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


FreeRADIUS
..........

privacyIDEA has a perl module to "translate" RADIUS requests to the API of the
privacyIDEA server. This module plugs into FreeRADIUS. The FreeRADIUS does not
have to run on the same machine like privacyIDEA.
To install this module run::

   apt-get install privacyidea-radius

If you want to run your FreeRADIUS server on another distribution, you
may download the module at [#rlmPerl]_.

Then you need to configure your FreeRADIUS site and the perl module.

.. note:: The perl module is not thread safe, so you need to start FreeRADIUS 
   with the -t switch.

SimpleSAMLphp
.............

Starting with 1.4 privacyIDEA also supports SAML via a plugin for simpleSAMLphp [#simpleSAML]_.
The simpleSAMLphp service does not need to run on the same machine like the privacyIDEA
server.

To install it on a Ubuntu 14.04 system please run::

   apt-get install privacyidea-simplesamlphp

Follow the simpleSAMLphp instructions to configure your authsources.php.
A usual configuration will look like this::

    'example-privacyidea' => array(
        'privacyidea:privacyidea',

        /*
         * The name of the privacyidea server and the protocol
         * A port can be added by a colon
         * Required.
         */
        'privacyideaserver' => 'https://your.server.com',

        /*
         * Check if the hostname matches the name in the certificate
         * Optional.
         */
        'sslverifyhost' => False,

        /*
         * Check if the certificate is valid, signed by a trusted CA
         * Optional.
         */
        'sslverifypeer' => False,
        
        /*
         * The realm where the user is located in.
         * Optional.
         */
        'realm' => '',
        
        /*
         * This is the translation from privacyIDEA attribute names to 
         * SAML attribute names.
         */
         'attributemap' => array('username' => 'samlLoginName',
                                 'surname' => 'surName',
                                 'givenname' => 'givenName',
                                 'email' => 'emailAddress',
                                 'phone' => 'telePhone',
                                 'mobile' => 'mobilePhone',
                                 ),
    ),



.. rubric:: Footnotes

.. [#ppa] https://launchpad.net/~privacyidea
.. [#rlmPerl] https://github.com/privacyidea/privacyidea/tree/master/authmodules/FreeRADIUS
.. [#simpleSAML]  https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
