.. _rollout_strategies:

What are possible rollout strategies?
-------------------------------------

.. index:: rollout strategy

There are different ways to enroll tokens to a big number of users.
Here are some selected high level ideas, you can do with privacyIDEA.

Autoenrollment
~~~~~~~~~~~~~~

Using the :ref:`autoassignment` policy you can distribute physical tokens to
the users. The users just start using the tokens.

.. _faq_registration_code:

Registration Code
~~~~~~~~~~~~~~~~~

If your users are physically not available and spread around the world, you can
send a registration code to the users by postal mail. The registration code
is a special token type which can be used by the user to authenticate with 2FA.
If used once, the registration token get deleted and can not be used anymore.
While logged in, the user can enroll a token on his own.

.. _faq_initial_synchronization:

Automatic initial synchronization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hardware TOTP tokens may get out of sync due to clock shift. HOTP tokens may
get out of sync due to unused keypresses. To cope with this you can activate
:ref:`autosync`.

But if you are importing hardware tokens, the clock in the TOTP token may
already be out of sync and you do not want the user to authenticate twice,
where the first authentication fails.

In this case you can use the following workflow.

In the TOTP token settings you can set the ``timeWindow`` to a very high
value. Note that this timeWindow are the seconds that privacyIDEA will search
for the valid OTP value *before* and *after* the current time. E.g. you can
set this to 86400. This way you allow the clock in the TOTP token to have
drifted for a maximum of one day.

As you do not want such a big window for all authentications, you can
automatically reset the ``timeWindow``. You can achieve this by creating an
event definition:

 * event: *validate_check*
 * handler: *token*
 * condition:
   * tokentype=TOTP
   * count_auth_success=1
 * action=set tokeninfo
   * key=*timeWindow*
   * value=*180*

This way with the first successful authentication of a TOTP token the
``timeWindow`` of the TOTP token is set to 180 seconds.


How can I translate to my language?
-----------------------------------
The web UI can be translated into different languages. The system determines
the preferred language of you browser and displays the web UI accordingly.

At the moment "en" and "de" are available.
