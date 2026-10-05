.. _application_plugins:

Application Plugins
===================

.. index:: Application Plugins, FreeRADIUS, SAML, PAM, ownCloud, Nextcloud

privacyIDEA comes with application plugins. These are plugins for
applications like PAM, Apache2, FreeRADIUS, ownCloud, Nextcloud, SimpleSAMLphp,
Keycloak, Shibboleth or AD FS, which enable these
applications to authenticate users against privacyIDEA.

You may also write your own application plugin or connect your own application
to privacyIDEA. To do so, please check the :ref:`plugin_guide`.

.. _pam_plugin:

Pluggable Authentication Module
-------------------------------

.. index:: offline, PAM

The `PAM module of privacyIDEA <https://github.com/privacyidea/privacyidea-pam>`_ directly
communicates with the privacyIDEA server via the API. The PAM module also supports offline
authentication. In this case you need to configure an offline token (See
:ref:`application_offline`).

For more information about building and configuring the PAM module see the
`README <https://github.com/privacyidea/privacyidea-pam/blob/main/README.md>`_.

For FIDO2/passkey authentication in the PAM stack there is the separate module
`pam-passkey <https://github.com/privacyidea/pam-passkey>`_.

Sending the password from the PAM stack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With the option ``sendPassword``, the PAM module sends the username and the
password that is already present in the PAM stack to privacyIDEA before it asks
for an OTP value. If no password is present, the user is prompted for one.
If this password is successfully validated, then the user is
logged in without additional requests.
If the password is not validated by privacyIDEA, the user is asked for an
OTP value or to answer the challenges that the request triggered.

The option ``sendEmptyPass`` sends an empty password instead, which can be used
to trigger challenges.

.. note:: ``sendPassword`` can be used in conjunction with the :ref:`passthru_policy`
   policy. In this case users with no tokens will be able to log in with only
   the password in the PAM stack.


.. _pam_ssh:

Use cases SSH and VPN
~~~~~~~~~~~~~~~~~~~~~~

privacyIDEA can easily be used to set up a secure SSH login combining SSH keys
with a second factor. The configuration is given in
`SSH Keys and OTP: Really strong two factor authentication
<https://www.privacyidea.org/ssh-keys-and-otp-really-strong-two-factor-authentication/>`_
on the privacyIDEA website.

Read more about how to use PAM to do :ref:`openvpn`.


.. _pam_yubico:

Using pam_yubico
----------------

.. index:: pam_yubico, PAM

If you are using Yubikey tokens you might also use ``pam_yubico``.
You can use Yubikey tokens for two more or less distinct applications.
The first is using privacyIDEA's PAM module as described above.
In this case privacyIDEA handles the policies
for user access and password validation. This works fine, when you only use
privacyIDEA for token validation.

The second mode is using the standard PAM module for Yubikeys from Yubico
``pam_yubico`` to handle the token validation. The upside is that you can
use the PAM module included with your distribution, but there are downsides as
well.

* You can't set a token PIN in privacyIDEA, because ``pam_yubico`` tries to
  use the token PIN entered by the user as a system password (which is likely
  to fail), i.e. the PIN will be stripped by ``pam_yubico`` and will not reach
  the privacyIDEA system.

* Setting the policy which tokens are valid for which users is done either in
  ``~/.yubico/authorized_keys`` or in the file given by the ``authfile`` option
  in the PAM configuration. The API server will only validate the token, but
  not check any kind of policy.

You can work around the restrictions by using a clever combination
of tokentype *Yubikey* and *Yubico* as follows:

* enroll a Yubikey token with ``privacyidea token yubikey_mass_enroll --yubimode YUBICO``
  (see :ref:`privacyideaadm_enrollment`).

* do not set a token password.

* do not assign the token to a user.

* please make a note of yubikey.prefix (12 characters starting with vv).

Now the token can be used with ``pam_yubico``, but will not allow any
user access in privacyIDEA. If you want to use the token with
``pam_yubico`` see the manual page for details. You'll want something like the
following in your PAM config::

   auth required pam_yubico.so id=<apiid> key=<API key> \
        urllist=https://<privacyidea-server>/ttype/yubikey authfile=/etc/yubikeys/authorized_yubikeys

The file ``/etc/yubikeys/authorized_yubikeys`` contains a line
for each user with the username and the allowed tokens delimited
by ":", for example::

   <username>:<serial number1>:<prefix1>:<prefix2>

How to configure the client ID (API ID) and the API key in privacyIDEA is
described in :ref:`yubikey_token_config`.


Now create a second token representing the Yubikey, but this time
use the *Yubico Cloud Mode*. Go to *Token* -> *Enroll Token* and select
*Yubikey Cloud mode*. Enter the 12-character prefix you noted above
and assign this token to a user and possibly set a token PIN. It would
be nice to have the serial number of the UBCM token correspond
to the UBAM token, but this is right now not possible with the WebUI.

In the WebUI, test the UBAM token without a Token PIN, test the UBCM token
with the stored Token PIN, and check the token info afterwards.
Check the Yubikey token via ``/ttype/yubikey``. The endpoint requires the
parameters ``id`` (the API ID), ``otp`` and ``nonce`` (16 to 40 random
characters), for example::

   curl "https://<privacyidea>/ttype/yubikey?id=<apiid>&otp=<otp>&nonce=<random characters>"

A successful request returns ``status=OK``.
There should be successful authentications (count_auth_success),
but no failures.


.. _freeradius:

FreeRADIUS
----------

There are two ways to integrate FreeRADIUS:

* Using a Perl-based privacyIDEA plugin, which is available for FreeRADIUS 3.x.
  It supports advanced use cases (such as challenge-response authentication or attribute mapping).
  Read more about it at :ref:`rlm_perl`.
* Using the rlm_rest module provided by FreeRADIUS. However, this setup does not support
  challenge-response or attribute mapping. Read more about it at :ref:`rlm_rest`.

With either setup, you can test the RADIUS setup using a command like this::

   echo "User-Name=user, User-Password=password" | radclient -sx yourRadiusServer \
      auth topsecret

.. note:: Do not forget to configure the ``clients.conf`` accordingly.

Microsoft NPS server
--------------------
You can also use the Microsoft Network Policy Server (NPS) with privacyIDEA.
A full featured integration guide can be found at the
`NetKnights webpage <https://netknights.it/en/nps-2012-for-two-factor-authentication-with-privacyidea/>`_.


.. _simplesaml_plugin:

SimpleSAMLphp Plugin
--------------------
You can install the
`SimpleSAMLphp module <https://github.com/privacyidea/simplesamlphp-module-privacyidea>`_
with composer in the root directory of your SimpleSAMLphp installation::

    composer require privacyidea/simplesamlphp-module-privacyidea

The module can perform the complete authentication as an authentication source
or only the second factor as an authentication processing filter.
As an authentication source, it is configured in ``config/authsources.php``.
A basic configuration looks like this::

    'example-privacyidea' => array(
        'privacyidea:PrivacyideaAuthSource',

        /*
         * The URL of the privacyIDEA server.
         * Required.
         */
        'privacyideaServerURL' => 'https://your.server.com',

        /*
         * Check the TLS certificate of the privacyIDEA server.
         * Optional. The default is 'true'.
         */
        'sslVerifyHost' => 'true',
        'sslVerifyPeer' => 'true',

        /*
         * The realm where the user is located in.
         * Optional.
         */
        'realm' => '',

        /*
         * The authentication flow: 'sendPassword', 'triggerChallenge'
         * or 'separateOTP'.
         * Required.
         */
        'authenticationFlow' => 'sendPassword',

        /*
         * This is the translation from privacyIDEA attribute names to
         * SAML attribute names.
         * Required.
         */
        'attributemap' => array(
            'username' => 'samlLoginName',
            'surname' => 'surName',
            'givenname' => 'givenName',
            'email' => 'emailAddress',
            'phone' => 'telePhone',
            'mobile' => 'mobilePhone',
        ),
    ),

privacyIDEA only returns the user attributes if the policy
:ref:`policy_add_user_in_response` is set.
All options and the configuration as an authentication processing filter are
described in the
`module documentation <https://github.com/privacyidea/simplesamlphp-module-privacyidea/blob/master/docs/privacyidea.md>`_.


.. _keycloak_plugin:

Keycloak
--------

With the privacyIDEA Keycloak-provider, there is a plugin available for the Keycloak identity manager.
It is available from the GitHub repository `keycloak-provider <https://github.com/privacyidea/keycloak-provider>`_.

Like SimpleSAMLphp, it can be used to realize single sign-on use cases with a strong second factor authentication.


.. _shibboleth_plugin:

Shibboleth
----------

The `privacyIDEA Shibboleth plugin <https://github.com/privacyidea/shibboleth-plugin>`_ adds
multi-factor authentication with privacyIDEA to the Shibboleth Identity Provider (version 5 and later).


.. _apache_plugin:

Apache2
-------

The Apache plugin uses ``mod_wsgi`` and ``redis`` to provide basic
authentication on the Apache2 side and validate the credentials against
privacyIDEA.

You need the authentication script ``privacyidea_apache.py`` and a valid
configuration in ``/etc/privacyidea/apache.conf``. Both can be found on
`GitHub <https://github.com/privacyidea/privacyidea/tree/master/authmodules/apache2>`__.

To activate the OTP authentication on a "Location" or "Directory" you need to
configure Apache2 like this, using the path where you placed the script::

   <Directory /var/www/html/secretdir>
        AuthType Basic
        AuthName "Protected Area"
        AuthBasicProvider wsgi
        WSGIAuthUserScript /path/to/privacyidea_apache.py
        Require valid-user
   </Directory>

.. note:: Basic Authentication sends the base64 encoded password on each
   request. So the browser will send the same one time password with each
   request. Thus the authentication module needs to cache the password when the
   authentication is successful. Redis is used for caching the password.

.. warning:: As redis per default is accessible by every user on the machine,
   you need to use this plugin with caution! Every user on the machine can
   access the redis database to read the passwords of the users. The cached
   credentials are stored as pbkdf2+sha512 hash.

.. _nginx_plugin:

NGINX
-----

The third-party NGINX plugin uses the internal scripting language ``lua`` of the NGINX
webserver and ``redis`` as caching backend to provide basic authentication
against privacyIDEA. It is not maintained by the privacyIDEA project and was
last updated in 2022.

You can retrieve the nginx plugin from `GitHub <https://github.com/dhoffend/lua-nginx-privacyidea>`__.

To activate the OTP authentication on a "Location" you need to include the
``lua`` script that basically verifies the given credentials against the
caching backend. New authentications will be sent to a different (internal)
location via subrequest which points to the privacyIDEA authentication backend
(via proxy_pass).

For the basic configuration you need to include the following lines to your
``location`` block::

    location / {
        # additional plugin configuration goes here #
        access_by_lua_file 'privacyidea.lua';
    }
    location /privacyidea-validate-check {
        internal;
        proxy_pass https://privacyidea/validate/check;
    }

You can customize the authentication plugin by setting some of the following
variables in the secured ``location`` block::

    # redis host:port
    # set $privacyidea_redis_host "127.0.0.1";
    set $privacyidea_redis_port 6379;

    # how long are accepted authentication allowed to be cached
    # if expired, the user has to reauthenticate
    set $privacyidea_ttl 900;

    # privacyIDEA realm. leave empty == default
    set $privacyidea_realm 'somerealm'; # (optional)

    # pointer to the internal validation proxy pass
    set $privacyidea_uri "/privacyidea-validate-check";

    # the http realm presented to the user
    set $privacyidea_http_realm "Secure zone (use PIN + OTP)";

.. note:: Basic Authentication sends the base64 encoded password on each
   request. So the browser will send the same one time password with each
   request. Thus the authentication module needs to cache the password after a
   successful authentication. Redis is used for caching the password similar
   to the Apache2 plugin.

.. warning:: As redis per default is accessible by every user on the machine,
   you need to use this plugin with caution! Every user on the machine can
   access the redis database to read the passwords of the users. The cached
   credentials are stored as SHA1_HMAC hash. If you prefer a stronger hashing
   method feel free to extend the given ``password_hash/verify`` functions
   using additional lua libraries (for example by using ``lua-resty-string``).

ownCloud
--------

.. index:: ownCloud

The privacyIDEA ownCloud App uses the two-factor framework of ownCloud to add
a second factor that is centrally managed by privacyIDEA to the ownCloud
installation.

The ownCloud privacyIDEA App is available from the `ownCloud App Store
<https://marketplace.owncloud.com/apps/twofactor_privacyidea>`_ and on
`GitHub <https://github.com/privacyidea/privacyidea-owncloud-app>`__.

The App requires a subscription file to work for more than ten users. You can
get the subscription file from `NetKnights
<https://netknights.it/en/products/privacyidea-owncloud-app/>`_.

Nextcloud
---------

.. index:: Nextcloud

The `privacyIDEA Nextcloud App <https://github.com/privacyidea/privacyidea-nextcloud-app>`_
adds multi-factor authentication with privacyIDEA to Nextcloud. It is
available from the Nextcloud App Store.


OpenVPN
-------

.. index:: OpenVPN

Read more about how to use OpenVPN with privacyIDEA at :ref:`openvpn`.

LDAP Proxy
----------

.. index:: LDAP Proxy

The `privacyIDEA LDAP Proxy <https://github.com/privacyidea/privacyidea-ldap-proxy>`_
intercepts LDAP bind requests and authenticates them against privacyIDEA.
This way, applications that authenticate their users with an LDAP bind can use
multi-factor authentication.

Windows
-------

.. index:: Windows

Credential Provider
~~~~~~~~~~~~~~~~~~~
The privacyIDEA Credential Provider adds multi-factor authentication to
the Windows desktop or Remote Desktop Services (RDS) hosts.
See https://privacyidea-credential-provider.readthedocs.io

AD FS
~~~~~

The `privacyIDEA AD FS provider <https://github.com/privacyidea/adfs-provider>`_ adds
multi-factor authentication with privacyIDEA to Microsoft Active Directory
Federation Services (AD FS).

C# client
~~~~~~~~~

There is a `C# client <https://github.com/privacyidea/csharp-client>`__, which you can
use to integrate privacyIDEA authentication into other .NET products and workflows.
