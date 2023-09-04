.. _push_token:

Push Token
----------

.. index:: Push Token, Firebase service

The push token uses the *privacyIDEA Authenticator* app. You can get it
from `Google Play Store`_ or `Apple App Store`_.

.. _Google Play Store: https://play.google.com/store/apps/details?id=it.netknights.piauthenticator
.. _Apple App Store: https://apps.apple.com/us/app/privacyidea-authenticator/id1445401301

The token type *push* sends a cryptographic challenge via the
Google Firebase service to the smartphone of the user. This push
notification is displayed on the smartphone of the user with a text
that tells the user that he or somebody else requests to login to a
service. The user can simply accept this request.
The smartphone sends a cryptographically signed response to the
privacyIDEA server and the login request gets marked as confirmed
in the privacyIDEA server. The application checks for this mark and
logs the user in automatically. For an example of how the components in a
typical deployment of push tokens interact reference the following diagram.

.. uml::
  :width: 500
  :caption: A typical push token deployment

  rectangle "On Prem" {
    card SAML {
      node "Service Provider" as SP
      node "Identity Provider" as IDP
    }
    card "1st Factor" {
      database LDAP
    }
    card "2nd Factor" {
      node privacyIDEA as PI
      file "User Resolver" as Users
    }
  }

  together {
    actor User
    node iPhone
    node Client
  }

  cloud Cloud {
    node Firebase
    node APN
  }

  User ~~> iPhone
  User ~~> Client

  Client -- SP
  SP -- IDP
  SP ..> Client : Require Auth

  Client --> IDP : Request Auth
  IDP -- LDAP
  IDP -- PI

  PI -- Users

  PI --> Firebase : Push Token
  Firebase --> APN
  APN --> iPhone
  iPhone --> PI : Confirm Token

To allow privacyIDEA to send push notifications, a Firebase service
needs to be configured. To do so see :ref:`firebase_provider`.

The PUSH token implements the :ref:`outofband mode <authentication_mode_outofband>`.

Configuration
~~~~~~~~~~~~~

The minimum necessary configuration is an ``enrollment`` policy
:ref:`policy_firebase_config`.

With the ``authentication`` policies :ref:`policy_push_text_on_mobile`
and :ref:`policy_push_title_on_mobile` you can define
the contents of the push notification.

If you want to use push tokens with legacy applications that are not yet set up to be compatible with out-of-band
tokens, you can set the ``authentication`` policy :ref:`policy_push_wait`. Please note, that setting this policy can
interfere with other tokentypes and will impact performance, as detailed in the documentation for ``push_wait``.

Enrollment
~~~~~~~~~~

The enrollment of the push token happens in two steps.

Step 1
......

The user scans a QR code. This QR code contains the
basic information for the push token and a enrollment URL, to which
the smartphone should respond in the enrollment process.

The smartphone stores this data and creates a new key pair.

Step 2
......

The smartphone sends its Firebase ID, the public key of the keypair,
the serial number and an enrollment credential back to the
enrollment URL of the privacyIDEA server.

The server responds with it's public key for this token.

Authentication
~~~~~~~~~~~~~~

Triggering the challenge
........................

The authentication request is triggered by an application
just the same like for any
challenge response tokens either with the PIN to the
endpoint ``/validate/check`` or via the endpoint
``/validate/triggerchallenge``.

privacyIDEA sends a cryptographic challenge with a signature to
the Firebase service.
The firebase service sends the notification to the smartphone,
which can verify the signature using the public key from enrollment step 2.

Accepting login
...............

The user can now accept the login by tapping on the push notification.
The smartphone sends the signed challenge back to the authentication URL
of the privacyIDEA server.
The privacyIDEA server verifies the response and marks this authentication
request as successfully answered.

In some cases the push notification does not reach the smartphone. Since
version 3.4 the smartphone can also poll for active challenges.

Login to application
....................

The application can check with the original transaction ID
with the privacyIDEA server, if the challenge has been successfully
answered and automatically login the user.


More information
~~~~~~~~~~~~~~~~

For a more detailed insight see the code documentation for the :ref:`code_push_token`.

For an in depth view of the protocol see
`the github issue <https://github.com/privacyidea/privacyidea/issues/1342>`_ and
`the wiki page <https://github.com/privacyidea/privacyidea/wiki/concept%3A-PushToken>`_.

Information on the polling mechanism can be found in the `corresponding wiki page <https://github
.com/privacyidea/privacyidea/wiki/concept%3A-pushtoken-poll>`_.

For recent information and a setup guide, visit the
`community blog <https://www.privacyidea.org/tag/push-token/>`_
