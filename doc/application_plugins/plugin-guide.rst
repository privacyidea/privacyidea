:orphan:

.. _plugin_guide:

Plugin Guide
============

In this chapter, we will discuss some considerations when developing a plugin to work with the privacyIDEA authentication server.
Because of the many configuration possibilities in privacyIDEA, it can be a good idea to have these considerations in
mind when developing a plugin, so that it is capable of serving future changes in the configuration of your privacyIDEA
server without having to change the plugin again.

First, we will present the general concepts of token types and how they can be used for authentication.
Then we will discuss the possible structure of the plugins and their parent software.

If you find any workflows that are not considered here or other mistakes, feel free to reach out to open a
`GitHub issue <https://github.com/privacyidea/privacyidea/issues>`_
so we can extend and improve this document.

Token Types and Authentication Modes
------------------------------------

(You may also read :ref:`tokens` and :ref:`authentication_modes`.)

There are the standard tokens, like HOTP, SMS or Email, which you just enter into the OTP field.
Optionally this can be preceded by a PIN.
On the other hand, there are challenge-response tokens, like PUSH or WebAuthn. They present a challenge to the user or a
device of the user, such as accepting the authentication on the smartphone or using a YubiKey for WebAuthn.
The smartphone or YubiKey will then produce a (cryptographic) response to the challenge to complete the authentication.
Challenge-response tokens have to be triggered to generate the challenge. This can be done in 3 different ways (depending on configuration):

1. Send the username and an empty pass to ``/validate/check`` (see REST API :ref:`rest_validate`):
   This will trigger all tokens of the user that have no PIN.
2. Send the username and the password to ``/validate/check`` (see REST API :ref:`rest_validate`):
   This will trigger all tokens of the user that have the
   password as PIN (interesting with ``otppin=userstore`` policy! - see :ref:`otppin_policy`)
3. Get an auth token for a service account via ``/auth`` (see REST API :ref:`rest_auth`). The service account has
   to be an administrator that is allowed the admin policy action :ref:`policy_triggerchallenge` (as soon as any
   admin policy is defined, this action has to be granted explicitly). Then use the auth token in the
   authorization header and use ``/validate/triggerchallenge`` with the username: This will trigger all tokens of
   the user, regardless of their PIN. The downside is that a service account has to be configured in each plugin.

It is also important to note that 1. and 2. can return authentication success instantly,
if ``passOnNoToken`` or ``passOnNoUser`` is configured in privacyIDEA. The plugin should be able to identify that and skip
the check for the second factor.

Passkeys are not triggered by these requests (unless the policy :ref:`policy_passkey_trigger_by_pin` is set).
To offer a login with a passkey, the plugin requests a challenge with ``POST /validate/initialize`` and the
parameter ``type=passkey``; no username is needed. The response contains the options for the browser's WebAuthn
API (``navigator.credentials.get``) in ``detail.passkey`` and the ``transaction_id``. The plugin passes the
challenge to the browser as the UTF-8 bytes of the string in ``detail.passkey.challenge``, without base64url-decoding
it as it would for a WebAuthn challenge (see :ref:`webauthn_passkey_interop`). The plugin sends the result
to ``/validate/check`` with the parameters ``transaction_id``, ``credential_id`` (the ID of the credential the
browser returned), ``authenticatorData``, ``clientDataJSON``, ``signature`` and ``userHandle``, and with the
origin of the login page in the HTTP header ``Origin``. If the request contains no ``user``, privacyIDEA
authenticates the owner of the passkey and returns the login name in ``detail.username``.
See :ref:`rest_validate` for both endpoints.

When challenges are triggered, the response of privacyIDEA will also include a message for each challenge which can
give the user directions on what to do to authenticate. These messages are configurable and it is a good idea to show them in your UI.
This enables you to configure instructions for your users centrally in the privacyIDEA server.
To summarize, it is useful to have a pre-authentication or "setup" step in your plugin so that challenge-response tokens
can be triggered before any UI is shown. This way, if any challenges were triggered, their messages can be presented right away.
Also your plugin will know which client modes it has to offer to serve the triggered tokens.

Now let's briefly outline how PUSH and WebAuthn tokens work. A PUSH token is a challenge-response token which has to be confirmed on a smartphone.
When a PUSH token is triggered, privacyIDEA generates a challenge for the authentication and waits for the response from the smartphone.
The plugin is not notified when the challenge has been answered but has to request the status of the challenge itself,
repeatedly (polling ``GET /validate/polltransaction`` with the ``transaction_id``).
When the plugin polled success for a challenge, it has to *try* to finalize the authentication by calling
``/validate/check`` with the username, the ``transaction_id`` of the challenge and an empty pass parameter
(see :ref:`authentication_mode_outofband`). Without the ``transaction_id``, privacyIDEA does not treat the request
as the answer to the challenge; for a push token without PIN it triggers a new push challenge instead.
This call will take policies set in the server into account and will
give the final result of authentication.

WebAuthn is the successor of U2F and intended to authenticate users on web-based applications.
The good thing is that the browser will do the heavy lifting for us and do the communication with the OS and
thus with the device. We have a `WebAuthn client <https://github.com/privacyidea/webauthn-client>`_
that will ensure the right formatting of the challenge and the
resulting response. This means you can just take the challenge, pass it to the browser's WebAuthn API and then pass the response
back to privacyIDEA.

The client mode of a challenge (``client_mode`` in each entry of ``multi_challenge``, see :ref:`client_modes`)
defines what the UI should show and how the plugin should process the inputs. Currently there are 3 client modes:
``interactive`` (OTP mode below), ``poll`` (PUSH mode) and ``webauthn`` (WebAuthn, also used for passkeys).
``detail.preferred_client_mode`` names the mode to show first.
We usually present a button for each mode that is available and the page will then switch to that mode.

*OTP mode* offers an input field for the user to enter their OTP and optionally their PIN. The OTP can be the usual
HOTP or TOTP, but also Email or SMS, which are challenge-response type tokens.

*PUSH mode* just refreshes the page to trigger the server side code (plugin) to run, so it can poll for the status
of the challenge. If the challenge has been successfully answered, try to finalize the authentication as described above.
This is why this mode is separated from the other modes. The refresh would interrupt any other input.
It would also be feasible to do the polling on the client (the user's browser)
and just the finalization in the plugin code itself, but that would require the user's browser to be able
to access privacyIDEA, which is not always the case.

*WebAuthn* is not really a separate mode UI-wise. Pressing the button (in our plugins) will open the OS dialog
with the WebAuthn device. This can be done in OTP mode. If the plugin is in PUSH mode, it is suggested to switch to
OTP UI/stop the refreshing before opening the OS dialog.

When the form is submitted, the mode is used to identify which parameters to send to privacyIDEA.

* In OTP mode, take the input from the OTP field.
* In PUSH mode, try to finalize the authentication.
* In WebAuthn mode, take the WebAuthnSignResponse from our WebAuthn client.

Additional Considerations
-------------------------

You will also have to figure out how to:

* Get the configuration values
* Pass information to the UI
* Retrieve information from the UI
* Persist data in a session or similar mechanism provided

Possible Structure
------------------

From our experience, plugin interfaces can often be categorized in one of two categories:

1. The plugin is responsible for the *whole* authentication, which means it has to verify username, password and second factor.
   In these cases, the plugin is often expected to return user information to the parent software, so it knows which user is logged in.
   privacyIDEA can handle these cases by relaying the username and password to a connected user store and having them verified there.

2. The plugin adds another "step" to the login. In these cases, the parent software often does the "first step" by
   verifying username + password and then executes a single/list of registered interface implementations (plugins).
   In these cases it is assumed that username+password are already present and can be obtained from the data passed
   into the interface. Only the second factor has to be requested from the user.

We like to think about the authentication in steps:

* Step 1 is getting the username+password and their verification
* Step 2 is the second factor

However, it is important to note that the second step can be repeated many times, depending on how privacyIDEA is configured.
The second step can be used to change the PIN of a token or to enroll a new token.
Therefore, the authentication should only end when the second step returns success and no more challenges have been triggered.
Depending on the plugin interface, there might be different functions for each "step" or there is just one function and
the plugin has to keep track of the "step" internally.

Some easy to understand code examples can be found in the
`Keycloak provider <https://github.com/privacyidea/keycloak-provider/blob/df005a7e076cf0c860ec7e06853e29a534988194/src/main/java/org/privacyidea/authenticator/PrivacyIDEAAuthenticator.java#L120>`_
or the `AD FS provider <https://github.com/privacyidea/adfs-provider/blob/07ea721a17a336dcafff0bbcda51aabbb2016bb7/privacyIDEAADFSProvider/Adapter.cs#L47>`_.

We also have client libraries for some languages which might save you some time:

* PHP: https://github.com/privacyidea/php-client
* C#: https://github.com/privacyidea/csharp-client
* Java: https://github.com/privacyidea/java-client
