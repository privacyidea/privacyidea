.. _daypassword_token:

Day Password Token
-------------------

The day password token is a modification of the :ref:`totp_token`. The difference between the
:ref:`totp_token` and day password token is, that the PIN of the day password token can be used more
then ones. For example you can use the day password token as a day password, in this way you get every
day a new password for the day.
Because the day password token basing on :ref:`totp_token` it works with the same Algorithms. You
can find the Algorithm hir `RFC6238 <https://tools.ietf.org/html/rfc6238>`_.

The day password token algorithm has some parameter, like if the generated OTP value will
be 6 digits or 8 digits or if the SHA1 or the SHA256 hashing algorithm is
used. You can freely set the timestep. For example you can set the timestep 3600, this way you get
a pin for one hour.

The day password token implements the :ref:`authenticate mode <authentication_mode_authenticate>`.
With a suitable :ref:`policy_challenge_response` policy, it may also be used
in the :ref:`challenge mode <authentication_mode_challenge>`.


Software tokens
~~~~~~~~~~~~~~~

Experiences
...........

The Google Authenticator and the FreeOTP token can be enrolled easily in
day password mode using the QR-Code enrollment Feature.

The Google Authenticator is available for iOS, Android and Blackberry devices.

Enrollment
~~~~~~~~~~

Default settings for day password tokens can be configured at :ref:`daypassword_token_config`.

The enrollment is the same as described in :ref:`hotp_token`.
However, when enrolling TBP token, you can specify some additional parameters.
