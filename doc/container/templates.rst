.. _container_templates:

Container Templates
...................

Typically, the same set of tokens is enrolled for multiple users. To simplify the token rollout, privacyIDEA supports
container templates from version 3.11. A container template is a predefined set of tokens. Creating a container from a
template enrolls the tokens from the template in the new container. Each token is enrolled with the enrollment policies
of the user or administrator who creates the container. A token they are not allowed to enroll (e.g. the token type is
not allowed, the maximum number of tokens is reached, or a required description is missing) or that can not be created
is skipped without an error: the container is created with the remaining tokens, and the response lists only the
tokens that were created. The same applies to a token for which an enrollment policy that is checked after the creation
fails (e.g. ``verify_enrollment`` or ``change_pin_on_first_use``): the token is deleted again. Each skipped token is
reported in ``tokens_not_created`` of the response with its type, the error and its serial if it is known. This entry
contains no enrollment data of the token. If all tokens were created, ``tokens_not_created`` is not contained in the
response.

Using container templates in combination with the synchronization feature allows for a simplified token rollout. The
user only needs to scan the QR code for the container and gets all tokens on his smartphone without the need to scan
each token individually.

A container template is related to a container type. The container type defines which token types are supported by the
container. However, there are some token types not supported by any container template. These tokens require individual
information during the rollout, e.g. the Questionnaire token.

Additionally, one can set a default template for each container type. This template is preselected when creating a new
container of this type.

For each token in the template, you can choose whether it is assigned to the container owner (*Assign to user*). This
setting is only applied to admin users. For normal users, all tokens of the template are always assigned to them. If
*Assign to user* is selected but the container has no owner, the token gets no user, only the first realm of the
container, if it has one. A token without *Assign to user* gets neither a user nor a realm.

For each token in the template, you can also choose whether its PIN must be changed on first use (*Change PIN on first
use*). The option applies to tokens that administrators create and to tokens that users create, also when a user enrolls
a container via multichallenge. With this option, a user who gets a token without a PIN from a template must set a PIN.
The option is in addition to the policy :ref:`policy_change_pin_first_use`, which still applies when an administrator
creates a token from a template. If the option is not set, the policy decides as for a single token. The user is asked
for the new PIN only if the application honors the PIN change or the policy :ref:`policy_change_pin_via_validate` is
set.

.. note:: privacyIDEA enforces the option only if it reads the template from the database. This is the case if a
   container is created with the template name, as the :ref:`container_wizard` does, and for the enrollment via
   multichallenge (:ref:`policy_enroll_via_multichallenge`). In the other cases, the client sends the template with the
   request. Hence, a user who can create containers can also send the template without the option.

.. versionadded:: 3.14.1 The option *Change PIN on first use*.

The enrollment policies are checked for each token as for a single token enrollment: against the user and the realm the
token gets, not against the user of the container. Hence, an administrator whose policies are restricted to certain
realms can not create a token without *Assign to user*.

During the creation of a container, the user can edit the template in place. However, these changes are only applied to
the container and do not change the template itself. If the template is not changed, the container will be
associated with this template. This allows comparing the container with the template to see if the container
contains the same tokens as the template or whether a new token needs to be enrolled or an old one might be removed.

The following token types are supported by the container templates:

Generic
~~~~~~~

* :ref:`four_eyes_token` - Meta token that can be used to create a
  Two Man Rule.
* :ref:`daypassword_token` - The DayPassword Token is a time based password
  loosely based on the TOTP algorithm which can be used multiple times.
* :ref:`email_token` - A token that sends the OTP value to the email address of
  the user.
  Using the option to read the email dynamically from the user store, makes it applicable for templates.
* :ref:`hotp_token` - event based One Time Password token
* :ref:`indexedsecret_token` - a challenge response token that asks the user for random positions
  from a secret string.
  Requires setting ``indexedsecret_force_attribute`` in the admin or user policy to be applicable for templates.
* :ref:`paper_token` - event based One Time Password tokens that give
  you a list of one-time passwords on a sheet of paper.
* :ref:`push_token` - A challenge response token, that sends a
  challenge to the user's smartphone and the user simply accepts the
  request to log in.
* :ref:`application_specific_token` - This is an application specific password token.
  It can be used to provide a static password for specific services or applications, where e.g. one time passwords
  are not suitable.
  The password can be generated randomly by the server, which allows using this token in a template.
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
* :ref:`tiqr_token` - A smartphone token that can be used to log in by only scanning a QR code.
  The token must be assigned to a user, so it is only created if the template assigns it to the container owner and
  the container has an owner, or if a user creates the container.
* :ref:`totp_token` - time based One Time Password tokens.


Smartphone
~~~~~~~~~~

* :ref:`daypassword_token` - The DayPassword Token is a time based password
  loosely based on the TOTP algorithm which can be used multiple times.
* :ref:`hotp_token` - event based One Time Password token
* :ref:`push_token` - A challenge response token, that sends a
  challenge to the user's smartphone and the user simply accepts the
  request to log in.
* :ref:`sms_token` - A token that sends the OTP value to the mobile phone of the
  user.
  Using the option to read the phone number dynamically from the user store, makes it applicable for templates.
* :ref:`totp_token` - time based One Time Password tokens.


YubiKey
~~~~~~~

* :ref:`hotp_token` - event based One Time Password token
