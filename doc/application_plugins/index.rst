.. _application_plugins:

Application Plugins
===================

.. index:: Application Plugins, OTRS, FreeRADIUS, SAML

privacyIDEA comes with application plugins. These are plugins for
applications like OTRS, FreeRADIUS or simpleSAMLphp which enable these
application to authenticate users against privacyIDEA.

.. _freeradius_plugin:

FreeRADIUS Plugin
-----------------

If you want to install the FreeRADIUS Plugin on Ubuntu 14.04 LTS this can be
easily done, since there is a ready made package (see
:ref:`install_ubuntu_freeradius`).

If you want to run your FreeRADIUS server on another distribution, you
may download the module at [#rlmPerl]_.

Then you need to configure your FreeRADIUS site and the perl module. The
latest FreeRADIUS plugin uses the ``/validate/check`` REST API of privacyIDEA.

You need to configure the perl module in FreeRADIUS ``modules/perl`` to look
something like this::

   perl {
       module = /usr/share/privacyidea/freeradius/privacyidea_radius.pm
   }

Your freeradius enabled site config should contain something like this::

   authenticate {
        Auth-Type Perl {
           perl
        }
        digest
        unix
   }

While you define the default authenticate type to be ``Perl`` in the
``users`` file::

   DEFAULT Auth-Type := Perl


.. note:: The perl module is not thread safe, so you need to start FreeRADIUS
   with the -t switch.

.. _simplesaml_plugin:

simpleSAMLphp Plugin
--------------------
You can install the plugin for simpleSAMLphp on Ubuntu 14.04 LTS (see
:ref:`install_ubuntu_simplesaml`) or on any other distribution using the
source files from [#simpleSAML]_.

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



.. [#rlmPerl] https://github.com/privacyidea/privacyidea/tree/master/authmodules/FreeRADIUS
.. [#simpleSAML]  https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
