.. _first_steps:

First Steps
===========

You installed privacyIDEA successfully according to :ref:`installation`.

These first steps will guide you through the tasks of logging in to the
management web UI, attaching your first users and enrolling the first token.

.. toctree::
   :maxdepth: 1

   add_admin
   login
   realm
   token

After these first steps you will be able to start attaching applications to
privacyIDEA in order to add two factor authentication to those applications.
You can 

 * use a PAM module to authenticate with OTP at SSH or local 
   login 
 * or the RADIUS plugin to configure your firewall or VPN to use OTP,
 * or use an Apache2 plugin to do Basic Authentication with OTP.
 * You can also setup different web applications to use OTP.

To attach applications read the chapter :ref:`application_plugins`.

You may also go on reading the next chapter which gives an overview on the :ref:`webui`
or you directly skip to :ref:`configuration` to get a deeper
insight in the configuration possibilities.
