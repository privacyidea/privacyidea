.. _authentication_modes:

Authentication Modes
====================

privacyIDEA supports a variety of tokens that implement different
authentication flows. We call these flows *authentication modes*. Currently,
tokens may implement three authentication modes, namely ``authenticate``,
``challenge`` and ``outofband``.

Application plugins need to implement the three authentication modes
separately, as the modes differ in their user experience. For example:

* The HOTP token type implements the ``authenticate`` mode, which is a
  single-shot authentication flow. For each authentication request, the user
  uses their token to generate a new HOTP value and enters it along with their
  OTP PIN. The plugin sends both values to privacyIDEA, which decides whether
  the authentication is valid or not.
* The E-Mail and SMS token types implement the ``challenge`` mode. With such a
  token, the authentication flow consists of two steps: In a
  first step, the plugin triggers a challenge. privacyIDEA sends the challenge
  response --- a fresh OTP value --- to the user via E-Mail or SMS.
  In a second step, the user responds to the challenge by entering the
  respective OTP value in the plugin's login form. The plugin sends the
  challenge response to privacyIDEA, which decides whether the authentication
  is valid or not.
* The PUSH and TiQR token types implement the ``outofband`` mode.
  With a PUSH token, the authentication step also consists of two steps:
  In a first step, the user triggers a challenge. privacyIDEA pushes the
  challenge to the user's smartphone app. In a second step, the user approves
  the challenge on their phone, and the app responds to the challenge by
  communicating with the privacyIDEA server on behalf of the user.
  The plugin periodically queries privacyIDEA to check if
  the challenge has been answered correctly and the authentication is valid.

The following describes the authentication flows of the three authentication
modes in more detail.

.. _authentication_mode_authenticate:

``authenticate`` mode
---------------------

.. uml::
  :width: 500

  Service -> PrivacyIDEA: POST /validate/check
  Service <-- PrivacyIDEA

 * The user enters a OTP PIN along with an OTP value.
 * The plugin sends a request to the ``/validate/check`` endpoint:

   .. code-block:: text

     POST /validate/check

     user=<user>&pass=<PIN+OTP>

  and privacyIDEA returns whether the authentication request has succeeded
  or not.

.. _authentication_mode_challenge:

``challenge`` mode
------------------

.. uml::
  :width: 500

  alt with pin

    Service -> PrivacyIDEA: POST /validate/check
    Service <-- PrivacyIDEA: transaction_id

  else without pin

    Service -> PrivacyIDEA: POST /validate/triggerchallenge
    Service <-- PrivacyIDEA: transaction_id

  end

  PrivacyIDEA -> "SMS Gateway": OTP

  ...User enters OTP from SMS...

  Service -> PrivacyIDEA: POST /validate/check
  Service <-- PrivacyIDEA

 * The plugin triggers a challenge, for example via the
   ``/validate/triggerchallenge`` endpoint:

   .. code-block:: text

     POST /validate/triggerchallenge

     user=<user>

   Alternatively, a challenge can be triggered via the ``/validate/check``
   endpoint with the PIN of a challenge-response token:

   .. code-block:: text

     POST /validate/check

     user=<user>&pass=<PIN>

   In both variants, the plugin receives a transaction ID which we call
   ``transaction_id`` and asks the user for the challenge response.
 * The user enters the challenge response, which we call ``OTP``.
   The plugin forwards the response to privacyIDEA along with the
   transaction ID:

   .. code-block:: text

     POST /validate/check

     user=<user>&transaction_id=<transaction_id>&pass=<OTP>

  and privacyIDEA returns whether the authentication request succeeded or not.

.. _authentication_mode_outofband:

``outofband`` mode
------------------

.. uml::
  :width: 500

  alt with pin

    Service -> PrivacyIDEA: POST /validate/check
    Service <-- PrivacyIDEA: transaction_id

  else without pin

    Service -> PrivacyIDEA: POST /validate/triggerchallenge
    Service <-- PrivacyIDEA: transaction_id

  end

  PrivacyIDEA -> Firebase: PUSH Notification
  Firebase -> Phone: PUSH Notification

  loop until confirmed

    Service -> PrivacyIDEA: GET /validate/polltransaction
    Service <-- PrivacyIDEA: false

  end

  ...User confirms sign in on phone...

  Phone -> PrivacyIDEA: POST /ttype/push

  Service -> PrivacyIDEA: GET /validate/polltransaction
  Service <-- PrivacyIDEA: true

  |||

  Service -> PrivacyIDEA: POST /validate/check
  Service <-- PrivacyIDEA

 * The plugin triggers a challenge, for example via the
   ``/validate/triggerchallenge`` endpoint:

   .. code-block:: text

     POST /validate/triggerchallenge

     user=<user>

   or via the ``/validate/check`` endpoint with the PIN of a out-of-band token:

   .. code-block:: text

     POST /validate/check

     user=<user>&pass=<PIN>

   In both variants, the plugin receives a transaction ID which we call
   ``transaction_id``.
   The plugin may now periodically query the status of the challenge by
   polling the ``/validate/polltransaction`` endpoint:

   .. code-block:: text

     GET /validate/polltransaction

     transaction_id=<transaction_id>

   If this endpoint returns ``false``, the challenge has not been answered yet.
 * The user approves the challenge on a separate device, e.g. their
   smartphone app. The app communicates with a tokentype-specific endpoint of
   privacyIDEA, which marks the challenge as answered.
   The exact communication depends on the token type.
 * Once ``/validate/polltransaction`` returns ``true``, the plugin *must*
   finalize the authentication via the ``/validate/check`` endpoint:

   .. code-block:: text

     POST /validate/check

     user=<user>&transaction_id=<transaction_id>&pass=

   For the ``pass`` parameter, the plugin sends an empty string.

   This step is crucial because the ``/validate/check`` endpoint takes defined
   authentication and authorization policies into account to decide whether
   the authentication was successful or not.

   .. note:: The ``/validate/polltransaction`` endpoint does not require
       authentication and does not increase the failcounters of tokens. Hence, attackers
       may try to brute-force transaction IDs of correctly answered challenges.
       Due to the short expiration timeout and the length of the randomly-generated
       transaction IDs, it is unlikely that attackers correctly guess a
       transaction ID in time.
       Nonetheless, plugins must not allow users to inject transaction
       IDs, and plugins must not leak transaction IDs to users.
