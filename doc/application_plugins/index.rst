.. _application_plugins:

Application Plugins
===================

.. index:: Application Plugins, OTRS, FreeRADIUS, SAML, PAM

privacyIDEA comes with application plugins. These are plugins for
applications like PAM, OTRS, FreeRADIUS or simpleSAMLphp which enable these
application to authenticate users against privacyIDEA.

.. _pam_plugin:

Pluggable Authentication Module
-------------------------------

.. index:: offline, PAM

The PAM module of privacyIDEA directly communicates with the privacyIDEA
server via the API. The PAM module also supports offline authentication. In
this case you need to configure an offline machine application. (See
:ref:`application_offline`)

You can install the PAM module with a ready made debian package for Ubuntu or
just use the source code file. It is a python module, that requires pam-python.

The configuration could look like this::

 ... pam_python.so /path/to/privacyidea_pam.py
 url=https://localhost prompt=privacyIDEA_Authentication

The URL parameter defaults to ``https://localhost``. You can also add the
parameters ``realm=`` and ``debug``.

The default behaviour is to trigger an online authentication request.
If the request was successful, the user is logged in.
If the request was done with a token defined for offline authentication, than
in addition all offline information is passed to the client and cached on the
client so that the token can be used to authenticate without the privacyIDEA
server available.


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

You can test the RADIUS setup using a command like this::

   echo "User-Name=user, Password=password" | radclient -sx yourRadiusServer \
      auth topsecret

.. note:: Do not forget to configure the ``clients.conf`` accordingly.

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

TYPO3
-----
You can install the privacyIDEA extension from the TYPO3 Extension Repository.
The privacyIDEA extension is easily configured.

**privacyIDEA Server URL**

This is the URL of your privacyIDEA installation. You do not need to add the
path *validate/check*. Thus the URL for a common installation would be
*https://yourServer/*.

**Check certificate**

Whether the validity of the SSL certificate should be checked or not.

.. warning:: If the SSL certificate is not checked,  the authentication
request could be modified and the answer to the request can be modified,
easily granting access to an attacker.

**Enable privacyIDEA for backend users**

If checked, a user trying to authenticate at the backend, will need to
authenticate against privacyIDEA.


**Enable privacyIDEA for frontend users**

If checked, a user trying to authenticate at the frontend, will need to
authenticate against privacyIDEA.

**Pass to other authentication module**

If the authentication at privacyIDEA fails, the credential the user entered
will be verified against the next authentication module.

This can come in handy, if you are setting up the system and if you want to
avoid locking yourself out.

Anyway, in a productive environment you probably want to uncheck this feature.

OTRS
----




Further plugins
---------------
You can find further plugins for
Dokuwiki, Wordpress, Contao and Django at [#cornelinuxGithub]_.


.. [#rlmPerl] https://github.com/privacyidea/privacyidea/tree/master/authmodules/FreeRADIUS
.. [#simpleSAML] https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
.. [#privacyideaGithub] https://github.com/privacyidea/privacyidea/tree/master/authmodules
.. [#cornelinuxGithub] https://github.com/cornelinux?tab=repositories
