.. _application_plugins:

Application Plugins
===================

.. index:: Application Plugins, OTRS, FreeRADIUS, SAML, PAM, ownCloud

privacyIDEA comes with application plugins. These are plugins for
applications like PAM, OTRS, Apache2, FreeRADIUS, ownCloud or simpleSAMLphp
which enable these
application to authenticate users against privacyIDEA.

You may also write your own application plugin or connect your own application
to privacyIDEA. This is quite simple using a REST API 
:ref:`rest_validate`.

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

If you want to disable certificate validation, which you should not do in a
productive environment, you can use the parameter ``nosslverify``.

A new parameter ``cacerts=`` lets you define a CA Cert-Bundle file, that
contains the trusted certificate authorities in PEM format.

The default behaviour is to trigger an online authentication request.
If the request was successful, the user is logged in.
If the request was done with a token defined for offline authentication, than
in addition all offline information is passed to the client and cached on the
client so that the token can be used to authenticate without the privacyIDEA
server available.

Read more about how to use PAM to do :ref:`openvpn`.

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

.. note:: The privacyIDEA module uses other perl modules that were not thread
   safe in the
   past. So in case you are using old perl dependencies and are experiencing
   thread problems, please start FreeRADIUS with the -t switch.
   (Everything works fine with Ubuntu 14.04 and Debian 7.)

You can test the RADIUS setup using a command like this::

   echo "User-Name=user, Password=password" | radclient -sx yourRadiusServer \
      auth topsecret

.. note:: Do not forget to configure the ``clients.conf`` accordingly.

Read more about :ref:`radius_and_realms` or :ref:`rlm_perl_ini`.

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

.. _otrs_plugin:

OTRS
----

There are two plugins for OTRS. For OTRS version 4.0 and higher use
*privacyIDEA-4_0.pm*.

This perl module needs to be installed to the directory ``Kernel/System/Auth``.

On Ubuntu 14.04 LTS you can also install the module using the PPA repository
and installing::

   apt-get install privacyidea-otrs

To activate the OTP authentication you need to add the following to
``Kernel/Config.pm``::

   $Self->{'AuthModule'} = 'Kernel::System::Auth::privacyIDEA';
   $Self->{'AuthModule::privacyIDEA::URL'} = \
           "https://localhost/validate/check";
   $Self->{'AuthModule::privacyIDEA::disableSSLCheck'} = "yes";

.. note:: As mentioned earlier you should only disable the checking of the
   SSL certificate if you are in a test environment. For productive use
   you should never disable the SSL certificate checking.

.. note:: This plugin requires, that you also add the path *validate/check*
   to the URL.

.. _apache_plugin:

Apache2
-------

The Apache plugin uses ``mod_wsgi`` and ``redis`` to provide a basic
authentication on Apache2 side and validating the credentials against
privacyIDEA.

On Ubuntu 14.04 LTS you can easily install the module from the PPA repository
by issuing::

   apt-get install privacyidea-apache-client

To activate the OTP authentication on a "Location" or "Directory" you need to
configure Apache2 like this::

   <Directory /var/www/html/secretdir>
        AuthType Basic
        AuthName "Protected Area"
        AuthBasicProvider wsgi
        WSGIAuthUserScript /usr/share/pyshared/privacyidea_apache.py
        Require valid-user
   </Directory>

.. note:: Basic Authentication sends the base64 encoded password on each
   request. So the browser will send the same one time password with each
   reqeust. Thus the authentication module needs to cache the password as the
   successful authentication. Redis is used for caching the password.

.. warning:: As redis per default is accessible by every user on the machine,
   you need to use this plugin with caution! Every user on the machine can
   access the redis database to read the passwords of the users. This way the
   fix password component of the user will get exposed!


ownCloud
--------

The ownCloud plugin is a ownCloud user backend. The directory
``user_privacyidea`` needs to be copied to your owncloud ``apps`` directory.

.. figure:: owncloud.png
   :width: 500

   *Activating the ownCloud plugin*

You can then activate the privacyIDEA ownCloud plugin by checking *Use
privacyIDEA to authenticate the users.*
All users now need to be known to privacyIDEA and need to authenticate using
the second factor enrolled in privacyIDEA - be it an OTP token, Google
Authenticator or SMS/Smartphone.

Checking *Also allow users to authenticate with their normal passwords.* lets
the user choose if he wants to authenticate with the OTP token or with his
original password from the original user backend.

.. note:: At the moment using a desktop client with a static password is not
   supported.


Further plugins
---------------
You can find further plugins for
Dokuwiki, Wordpress, Contao and Django at [#cornelinuxGithub]_.


.. [#rlmPerl] https://github.com/privacyidea/privacyidea/tree/master/authmodules/FreeRADIUS
.. [#simpleSAML] https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
.. [#privacyideaGithub] https://github.com/privacyidea/privacyidea/tree/master/authmodules
.. [#cornelinuxGithub] https://github.com/cornelinux?tab=repositories
