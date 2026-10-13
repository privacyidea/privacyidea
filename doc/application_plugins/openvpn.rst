:orphan:

.. _openvpn:

OTP with OpenVPN
~~~~~~~~~~~~~~~~

.. index:: PAM, OpenVPN

This section describes how you can set up OpenVPN to authenticate against
privacyIDEA. There are basically three ways to integrate OpenVPN with
privacyIDEA:

1. use the privacyIDEA PAM module
2. integrate OpenVPN directly with RADIUS
3. use the PAM module for RADIUS in OpenVPN

Each of the methods has its advantages as well as drawbacks.

On the client side, you need to add::

   auth-user-pass

to the client configuration.

Now the user is asked for a password when establishing the VPN connection.
The entered password is sent to privacyIDEA. Thus you can require the user to
enter a password consisting of a static part he knows and the OTP part which
the user needs to generate with the OTP token he possesses.

Another addition you most probably want to make is adding the following option
to both the client and the server configuration::

   reneg-sec 0

By default, the channel key gets renegotiated after 3600 seconds, either
partner can request a renegotiation. If only one partner disables this
option, the other one will request it. This works fine for static password
or dual-factor authentication where both factors are static (e.g. password
and certificate/smartcard).

When using OTP authentication, note that this default value may cause the
end user to be challenged to reauthorize once per hour. The OpenVPN client
with the option ``--auth-user-pass`` prompts for username and password for
every renegotiation.

Network-Manager does not rechallenge the user and the VPN connection hangs,
so you'll need to disable the renegotiation.

If you are also requiring client certificates, the user needs

   1. a machine certificate
   2. a password
   3. and an OTP token

to establish a VPN connection.

privacyIDEA PAM module for OpenVPN
==================================

For this the PAM stack is used. To get the basic information
about integrating privacyIDEA with PAM, read :ref:`pam_plugin`.
Since we do not use RADIUS this is the least complex configuration and for
most installations probably the preferred one. The biggest drawback is that
you need to install the privacyIDEA PAM module ``pam_privacyidea.so`` on your
OpenVPN server. As long as the module is not part of your distribution you need
to handle updates/security fixes manually, e.g. with the releases of the
`privacyidea-pam <https://github.com/privacyidea/privacyidea-pam/releases>`_
project.

You can create a file */etc/pam.d/openvpn* on your OpenVPN server that
basically looks like this::

   auth    [success=1 default=ignore]      pam_privacyidea.so url=https://your.privacyidea.server
   auth    requisite           pam_deny.so
   auth    required            pam_permit.so
   session sufficient          pam_permit.so
   account sufficient          pam_permit.so

The options of ``pam_privacyidea.so``, e.g. ``realm=``, are described in the
`README <https://github.com/privacyidea/privacyidea-pam/blob/main/README.md>`_
of the PAM module.

Then you need to configure the OpenVPN server like this::

   port 1194
   [...]
   plugin /usr/lib/openvpn/openvpn-plugin-auth-pam.so openvpn

The important line is the last line, which tells OpenVPN to use the PAM stack
to authenticate the user and within the PAM stack the configuration for
"openvpn". On certain distributions the library might be located elsewhere, e.g. at
*/usr/lib64/openvpn/plugins/openvpn-plugin-auth-pam.so*.

Integration of OpenVPN directly with RADIUS
===========================================

This configuration does not use PAM, so might be preferred in some installations.
You will need the package *openvpn-auth-radius* which should be part of your
distribution. Before you can configure your OpenVPN you need a FreeRADIUS
server with the privacyIDEA plugin, configured according to :ref:`freeradius`.
FreeRADIUS can run on the privacyIDEA server or on another machine.
Be sure that RADIUS works before you start.

Copy the file */usr/share/doc/openvpn-auth-radius/examples/radiusplugin.cnf* into */etc/openvpn*
and adapt it to your configuration. The most important parts of the file should contain::

  # The NAS identifier which is sent to the RADIUS server
  NAS-Identifier=OpenVPN
  OpenVPNConfig=/etc/openvpn/server.conf
  [...]
  server
  {
        # The UDP port for radius accounting.
        acctport=1813
        # The UDP port for radius authentication.
        authport=1812
        # The name or ip address of the radius server.
        name=<your-radius-server>
        # How many times should the plugin send the request if there is no response?
        retry=1
        # How long should the plugin wait for a response?
        wait=1
        # The shared secret.
        sharedsecret=<shared-secret>
  }

Then load the plugin in the OpenVPN server configuration, with the path of
``radiusplugin.cnf`` as argument::

   plugin /usr/lib/openvpn/radiusplugin.so /etc/openvpn/radiusplugin.cnf

On certain distributions the library might be located elsewhere.

After the changes restart your OpenVPN service and keep an eye on the
logs of OpenVPN on your access server as well as the freeradius logs on
your RADIUS server.

.. note:: The OpenVPN RADIUS plugin also sends accounting requests to the
   ``acctport``. If they are not answered, it refuses the connection even
   though the authentication succeeded. The site ``privacyidea`` installed by
   the ``privacyidea-radius`` package only answers authentication requests.
   Either add accounting inside the ``server`` section of this site
   (``/etc/freeradius/3.0/sites-enabled/privacyidea``)::

      listen {
          type = acct
          ipaddr = *
          port = 0
      }
      accounting {
          detail
      }

   or set ``nonfatalaccounting=true`` in ``radiusplugin.cnf``, so that the
   connection does not depend on the accounting. Add the accounting to the
   site ``privacyidea`` itself: the package removes all other sites from
   ``sites-enabled`` when it is installed or upgraded.

Using the PAM module for RADIUS in OpenVPN
==========================================

The other method to integrate OpenVPN with RADIUS (and privacyIDEA) is to
use the PAM module *libpam-radius-auth*. If you have other services running
on your OpenVPN server that should integrate into privacyIDEA as well, this
might be your preferred method.

You can create a file */etc/pam.d/openvpn* on your OpenVPN server that
basically looks like this::

   auth    [success=1 default=ignore]      pam_radius_auth.so
   auth    requisite           pam_deny.so
   auth    required            pam_permit.so
   session sufficient          pam_permit.so
   account sufficient          pam_permit.so

Then you need to configure the OpenVPN server like this::

   port 1194
   [...]
   plugin /usr/lib/openvpn/openvpn-plugin-auth-pam.so openvpn

Now we need to tell the PAM plugin which RADIUS server to use. Modify the
file */etc/pam_radius_auth.conf* to point to your RADIUS server and add
the shared secret::

  # server[:port] shared_secret      timeout (s)
  #127.0.0.1      secret             1
  #other-server    other-secret       3
  <your-radius-server>:1812 <shared-secret> 3

Now you can restart your OpenVPN service and should be able to connect
with your PIN and OTP. Again, have a look at the logs of both OpenVPN
and RADIUS.
