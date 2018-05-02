.. _rlm_perl:

RADIUS plugin
=============

Installation
------------

If you want to install the FreeRADIUS Plugin on Ubuntu 14.04 LTS or 16.04 LTS, this can be
easily done, since there is a ready made package (see
:ref:`install_ubuntu_freeradius`).

However, it can also be installed on other distributions.
The FreeRADIUS plugin is a perl module, that e.g. requires on a Debian system
the following packages to be installed:

* libconfig-inifiles-perl
* libdata-dump-perl
* libtry-tiny-perl
* libjson-perl

The module itself may be downloaded at [#rlmPerl]_ and placed at, e.g.,
``/usr/share/privacyidea/freeradius/privacyidea_radius.pm``.

Setup
-----

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

Configuration
-------------

The RADIUS plugin configuration is read from the file
``/opt/privacyIDEA/rlm_perl.ini``.

Starting with version 2.7 the plugin first tries to read from the following
locations:

* ``/etc/privacyidea/rlm_perl.ini``
* ``/etc/freeradius/rlm_perl.ini``
* ``/opt/privacyIDEA/rlm_perl.ini``.

If no file exists, the default values are::

   [Default]
   URL = https://localhost/validate/check
   REALM =

But it can also look like this::

   [Default]
   URL = https://your.server/validate/check
   REALM = someRealm
   RESCONF = someResolver
   SSL_CHECK = true
   DEBUG = true
   TIMEOUT = 10

   [Mapping]
   serial = privacyIDEA-Serial

   [Mapping user]
   group = Class


.. note:: The default behaviour is to not check the SSL certificate.
   So in a productive environment where the privacyIDEA system is located on
   another server than the RADIUS server, you should set "SSL_CHECK = true".

.. _radius_and_realms:

Radius and Realms
~~~~~~~~~~~~~~~~~

.. index:: RADIUS, FreeRADIUS, RADIUS Realms, Realms

FreeRADIUS also has a notion of realms. In general the RADIUS realms are not
necessarily the same as the privacyIDEA realms, but they can be mapped.

A user can authenticate to the FreeRADIUS either with a simple username
"fred", or a username combined with a RADIUS realm in the format like
"fred@realm1" or "realm1\\fred".

.. note:: The format of the realms is defined in
   ``/etc/freeradius/modules/realm`` as "suffix" and "ntdomain". I.e. you could
   also change the delimiter.
   The "suffix" and "ntdomain" is referenced in the ``authorize`` section in
   ``/etc/freeradius/sites-enabled/privacyidea``.

The RADIUS server tries to split the realms according to the definition of
"suffix" or "ntdomain". I.e. a ``User-Name`` "fred@realmRadius" would be
split
into ``Stripped-User-Name`` "fred" and ``Realm`` (RADIUS realm) "realmRadius".
**But only if** FreeRADIUS can identify "realmRadius" as a RADIUS realm. For
FreeRADIUS to identify this as a REALM you need to add this to the file
``/etc/freeradius/proxy.conf``::

   realm realmRadius {
   }

Realm processing in FreeRADIUS
..............................

A ``User-Name`` "fred@realmRadius" or "realmRadius\\fred" is sent to the
FreeRADIUS server.

If "realmRadius" can not be identified as RADIUS realm (missing entry in
proxy.conf), then no realm can be split and the complete ``User-Name`` will be
sent to privacyIDEA for validation.
This can work out with "fred@realmRadius", since privacyIDEA
might split the @-sign. But this probably will not work out for
"realmRadius\\fred".

If the "realmRadius" can be identified as RADIUS realm (entry in proxy.conf),
then FreeRADIUS will split the ``User-Name`` into the RADIUS attributes
``Stripped-User-Name`` and ``Realm`` and the "fred" will be sent as user and
"realmRadius" as the realm to privacyIDEA.

This way you can directly map RADIUS realms in the RADIUS user name to realm
in privacyIDEA.

.. note:: If the ``User-Name`` could be split into the RADIUS attributes
   ``Stripped-User-Name`` and ``Realm``, then these values are sent to the
   privacyIDEA server. If the ``User-Name`` could not be split (and
   ``Stripped-User-Name`` is empty) then ``User-Name`` is sent to the
   privacyIDEA server.

   For a deeper insight take a look at the code
   https://github.com/privacyidea/FreeRADIUS/blob/master/privacyidea_radius.pm#L276

.. note:: The ``NAS-IP-Address`` is sent as the *client* parameter to the
   privacyIDEA server. Using :ref:`override_client` you can pass the RADIUS
   client IP to the privacyIDEA server to perform policies based on the
   RADIUS client's IP address.


.. note:: You can define a realm in ``/opt/privacyIDEA/rlm_perl.ini``. Such a
   realm definition will override a RADIUS realm in the ``User-Name``.

Mapping privacyIDEA return values to RADIUS Attribute-Value pairs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The plugin can use information from the ``detail`` section
(see :ref:`rest_validate`) of the
privacyIDEA response to map these values to arbitrary RADIUS Attribute-Value
pairs.

To do this use the ``[Mapping]`` section in the ``rlm_perl.ini`` file.

Using the Token serial number
.............................

In case of a successful authentication privacyIDEA returns the serial number
of the token used.

If available (see :ref:`policy_no_detail_on_success` and
:ref:`policy_no_detail_on_fail`) the FreeRADIUS server can receive this
serial number.

In ``rlm_perl_ini`` use::

    [Mapping]
    serial = privacyIDEA-Serial

This will map the ``detail->serial`` in the privacyIDEA response and add an
attribute ``privacyIDEA-Serial`` in your RADIUS response.

To use the ``privacyIDEA-Serial`` in the RADIUS response, you need to include
the ``dictionary.netknights`` in your FreeRADIUS dictionary.
You can get it here [#netknights_dict]_.

Return user attributes
......................

If the authorization policy :ref:`policy_add_user_in_response` is configured
the privacyIDEA response contains an additional tree ``detail->user`` with
user information.

The FreeRADIUS plugin can also map these user information to RADIUS
Attribute-Value pairs. Certain VPN systems use RADIUS return values to put
users into certain groups to allow access to special sub networks.

If you want to map such user values you need to add a section in
``rlm_perl.ini``::

   [Mapping user]
   a_user_attribute = any_RADIUS_Attribute_even_vendor_specific

This way you can map any user attribute like name, email, realm, group to any
arbitrary RADIUS attribute.

You can also address different sections in the privacyIDEA detail response by
changing the keyword in ``rlm_perl.ini`` to ``[Mapping other_section]``.


Debugging RADIUS
~~~~~~~~~~~~~~~~

If you need to DEBUG the FreeRADIUS go like this.

Add "DEBUG = true" to ``/opt/privacyIDEA/rlm_perl.ini``.
Then stop the FreeRADIUS and run it in debug mode as user root::

   /etc/init.d/freeradius stop; freeradius -X

Now you can send requests to the RADIUS server like this::

   echo 'User-Name=realm3\\cornelius, Password=test' | radclient -s \
      127.0.0.1 auth test

Of course you need to replace the IP of your RADIUS server and the RADIUS
secret "test" with your clients secret.

.. rubric:: Footnotes

.. [#netknights_dict] https://github.com/privacyidea/privacyidea/blob/master/authmodules/FreeRADIUS/dictionary.netknights
.. [#rlmPerl] https://github.com/privacyidea/freeradius
