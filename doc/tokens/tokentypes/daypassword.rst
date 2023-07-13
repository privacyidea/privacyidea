.. _daypassword_token:

Day Password Token
-------------------

The day password token is a modification of the :ref:`totp_token`. The difference between the
:ref:`totp_token` and the day password token is, that the OTP value of the day password token can be used more
then once. For example you can use the day password token as a daily changing password.
Since the day password token is based on the :ref:`totp_token`, it works using the same algorithm described in
`RFC6238 <https://tools.ietf.org/html/rfc6238>`_.


Enrollment
~~~~~~~~~~

During enrollment of the token a QR code will be created to scan with a supported authenticator app.

The day password token can only be enrolled with an authenticator app that supports TOTP token with arbitrary time steps.


.. Note :: The link in the QR code looks like this:
``otpauth://daypassword/DayPassword0000536F?secret=NW6IT27XNRXOAZEP4GILXB3GCKCANVQR&issuer=privacyIDEA&algorithm=SHA256&digits=6&period=86400``

The day password token algorithm can be adjusted with the following parameters:
- The time step size for the generated OTP values
- The length of the OTP value (6/8)
- The hashing algorithm used in the OTP calculation (SHA1/SHA256/SHA512)

To configure the default settings for the token, you can use the corresponding user or admin
policies for ``timestep``, ``hashlib`` and ``otplen``.

The day password token implements the :ref:`authenticate mode <authentication_mode_authenticate>`.
With a suitable :ref:`policy_challenge_response` policy, it may also be used
in the :ref:`challenge mode <authentication_mode_challenge>`.

The enrollment is the same as described in :ref:`totp_token`.
However, when enrolling DayPassword token, you can specify an arbitrary time step size.

.. Note :: Implemented in privacyIDEA 3.9
