.. _email_token:

EMail
-----

.. index:: EMail token

The token type *email* sends the OTP value in an EMail to the user. You can
configure the EMail server in :ref:`email_otp_token`.


.. figure:: images/enroll_email.png
   :width: 500

   *Enroll an EMail token*

When enrolling an EMail token, you only need to specify the email address of
the user.

The EMail token is a challenge response token. I.e. when using the OTP PIN in
the first authentication request, the sending of the EMail will be triggered
and in a second authentication request the OTP value from the EMail needs to be
presented. It implements the :ref:`challenge authentication mode <authentication_mode_challenge>`.


For a more detailed insight see the code documentation :ref:`code_email_token`.
