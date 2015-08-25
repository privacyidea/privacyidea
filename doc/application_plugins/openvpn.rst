.. _openvpn:

OTP with OpenVPN
~~~~~~~~~~~~~~~~

.. index:: PAM, OpenVPN

This section describes, how you can setup OpenVPN to authenticate against
privacyIDEA. For this the PAM stack is used. To get the basic information
about integrating privacyIDEA with PAM, read :ref:`pam_plugin`.

You can create a file */etc/pam.d/openvpn* on your OpenVPN server that
basically looks like this::

   auth    [success=1 default=ignore]      pam_python.so
       /path/to/privacyidea_pam.py url=https://your.privacyidea.server
   auth    requisite           pam_deny.so
   auth    required            pam_permit.so
   session sufficient          pam_permit.so
   account sufficient          pam_permit.so

Then you need to configure the OpenVPN server like this::

   port 1194
   [...]
   plugin /usr/lib/openvpn/openvpn-auth-pam.so openvpn

The important line is the last line, which tells OpenVPN to use the PAM stack
to authenticate the user and within the PAM stack the configuration for
"openvpn". On certain distributions the library might be located at
*/usr/lib64/openvpn/plugin/lib/openvpn-auth-pam.so*.

On the client side, you need to add::

   auth-user-pass

to the client configuration.

Now the user is asked for a password when establishing the VPN connection.
The entered password is sent to privacyIDEA. Thus you can require the user to
enter a password consisting of a static part he knows and the OTP part which
the user needs to generate with the OTP token he possesses.

If you are also requiring client certificates, the user needs

   1. a machine certificate
   2. a password
   3. and an OTP token

to establish a VPN connection.
