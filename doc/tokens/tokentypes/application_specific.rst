.. _application_specific_token:

Application Specific Password Token
-----------------------------------

This token type allows the user to have an application specific static password.

This can be used in certain scenarios, when e.g. an OTP token or WebAuthn token is not suitable.
This can be the case e.g. with email clients that cache the password, even if in other cases the mail server
allows for more secure two factor authentication, when e.g. accessing via a web interface.

The user can set the static password and in addition a `service_id` needs to be set.
This `service_id` ensures, that the token is only used for this service (like "mailserver", "owncloud", "SAP").

The `service_id` is a parameter that is passed in the `/validate/check` request. The corresponding plugin can
send the parameter itself. The privacyIDEA administrator can also define an event handler
(:ref:`requestmanglerhandler`), to set the `service_id` e.g. based on the IP address or based on a realm.

If the passed service_id matches the one of the token, the token can be used for authentication.

.. note:: Please note, that all other tokens of the user are of course also used and checked for authentication.
