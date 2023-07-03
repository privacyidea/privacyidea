.. _daypassword_token:

Day Password Token
-------------------

The day password token is a modification of the :ref:`totp_token`. The difference between the
:ref:`totp_token` and the day password token is, that the OTP value of the day password token can be used more
then once. For example you can use the day password token as daily changing password for a new password each day.
Since the day password token is based on the :ref:`totp_token`, it works using the same algorithm described in
`RFC6238 <https://tools.ietf.org/html/rfc6238>`_.


Enrollment
~~~~~~~~~~

During enrollment of the token a QR code will be created to scan with a supported authenticator app.

The DayPassword token can only be enrolled with an authenticator app that supports the new token.


.. Note :: The link in the QR code lucks lick this:
 otpauth://daypassword/DayPassword0000536F?secret=NW6IT27XNRXOAZEP4GILXB3GCKCANVQR&issuer=privacyIDEA&algorithm=SHA256&digits=6&period=86400

The day password token algorithm has some parameter, like if the generated OTP value will
be 6 digits or 8 digits or if the SHA1 or the SHA256 hashing algorithm is
used. You can freely set the timestep. For example you can set the timestep 3600, this way you get
a pin for one hour.

The day password token implements the :ref:`authenticate mode <authentication_mode_authenticate>`.
With a suitable :ref:`policy_challenge_response` policy, it may also be used
in the :ref:`challenge mode <authentication_mode_challenge>`.

To configure the default settings for the token, you can use the enrollment policy.

The enrollment is the same as described in :ref:`hotp_token`.
However, when enrolling DayPassword token, you can specify the timeStep.

.. Note :: Implemented in privacyIDEA 3.9
