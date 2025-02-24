.. _templates:

Container Templates
...................

Typically, the same set of tokens is enrolled for multiple users. To simplify the token rollout, privacyIDEA supports
container templates from version 3.11. A container template is a predefined set of tokens. Creating a container from a
template enrolls all tokens from the template in the new container.

Using container templates in combination with the synchronization feature allows for a simplified token rollout. The
user only needs to scan the QR code for the container and gets all tokens on his smartphone without the need to scan
each token individually.

A container template is related to a container type. The container type defines which token types are supported by the
container. However, there are some token types not supported by any container template. These tokens require individual
information during the rollout, e.g. the Questionnaire token.

Additionally, one can set a default template for each container type. This template is preselected when creating a new
container of this type.

By default, the tokens are assigned to the container owner. This can be deselected for each token in the template, but
is only applied to admin users. Normal users will always be assigned to all tokens of the template.

During the creation of a container, the user can edit the template in place. However, these changes are only applied to
the container and do not change the template itself. If the template is not changed, the container will be
associated with this template. This allows to compare the container with the template to see if the container
contains the same tokens as the template or whether a new token needs to be enrolled or an old one might be removed.

The following token types are supported by the container templates:

Generic
~~~~~~~

* :ref:`four_eyes_token` - Meta token that can be used to create a
  Two Man Rule.
* :ref:`daypassword_token` - The DayPassword Token is a time based password
  loosely based on the TOTP algorithm which can be used multiple times.
* :ref:`email_token` - A token that sends the OTP value to the EMail address of
  the user.
  Using the option to read the email dynamically from the user store, makes it applicable for templates.
* :ref:`hotp_token` - event based One Time Password token
* :ref:`indexedsecret_token` - a challenge response token that asks the user for random positions
  from a secret string.
  Requires to set ``indexedsecret_force_attribute`` in the admin or user policy to be applicable for templates.
* :ref:`paper_token` - event based One Time Password tokens that get
  you list of one time passwords on a sheet of paper.
* :ref:`push_token` - A challenge response token, that sends a
  challenge to the user's smartphone and the user simply accepts the
  request to login.
* :ref:`application_specific_token` - This is an application specific password token.
  It can be used to provide static password for specific services or applications, where e.g. one time passwords
  are not suitable.
  The password can be generated randomly by the server, which allows to use this token in a template.
* :ref:`registration_token` - A special token type used for enrollment scenarios (see
  :ref:`faq_registration_code`).
* :ref:`remote_token` - A virtual token that forwards the authentication request to
  another privacyIDEA server.
* :ref:`sms_token` - A token that sends the OTP value to the mobile phone of the
  user.
  Using the option to read the phone number dynamically from the user store, makes it applicable for templates.
* :ref:`spass_token` - The simple pass token. A token that has no OTP component and
  just consists of the OTP pin or (if otppin=userstore is set) of the userstore
  password.
* :ref:`tan_token` - TANs printed on a sheet of paper.
* :ref:`totp_token` - time based One Time Password tokens.


Smartphone
~~~~~~~~~~

* :ref:`daypassword_token` - The DayPassword Token is a time based password
  loosely based on the TOTP algorithm which can be used multiple times.
* :ref:`hotp_token` - event based One Time Password token
* :ref:`push_token` - A challenge response token, that sends a
  challenge to the user's smartphone and the user simply accepts the
  request to login.
* :ref:`sms_token` - A token that sends the OTP value to the mobile phone of the
  user.
  Using the option to read the phone number dynamically from the user store, makes it applicable for templates.
* :ref:`totp_token` - time based One Time Password tokens.


Yubikey
~~~~~~~

* :ref:`hotp_token` - event based One Time Password token
