.. _user_policies:

User Policies
-------------

.. index:: selfservice policies, user policies

In the WebUI users can manage their own tokens.
A user can log in to the WebUI with the username of their
useridresolver. For example, if this user is found in an LDAP resolver pointing
to an Active Directory, they can log in with their domain
password.

User policies are used to define which actions users are
allowed to perform.

.. index:: client policies

The user policies also respect the ``client`` input, where you
can enter a list of IP addresses and subnets (like 10.2.0.0/16).

Using the ``client`` parameter you can allow different actions depending on
whether the user logs in from the internal network
or remotely from the internet via the firewall.

Technically user policies control the use of the REST API
:ref:`rest_token` and are checked using :ref:`code_policy` and
:ref:`policy_decorators`.

.. note:: If no user policy is defined, the user has
   all actions available to them to manage their tokens.

The following actions are available in the scope
*user*:

enroll
~~~~~~

type: ``bool``

There are enrollment actions per token type, e.g. ``enrollHOTP``.
The user is only allowed to enroll such specified token types.

.. versionadded:: 2.0

assign
~~~~~~

type: ``bool``

The user is allowed to assign an existing token that is
located in their realm and that does not belong to any other user
by entering the serial number.

Note that the condition ``realm`` for this action is also evaluated to true if the token is in no realm.

.. versionadded:: 2.0

disable
~~~~~~~

type: ``bool``

The user is allowed to disable their own tokens.
Disabled tokens can not be used to authenticate.

.. versionadded:: 2.0

enable
~~~~~~

type: ``bool``

The user is allowed to enable their own tokens.

.. versionadded:: 2.0

delete
~~~~~~

type: ``bool``

The user is allowed to delete their own tokens from the database.
Those tokens can not be recovered. The audit log concerning
these tokens remains.

.. versionadded:: 2.0

token_rollover
~~~~~~~~~~~~~~

type: ``bool``

The user is allowed to roll over one of their own tokens that is already
enrolled, which gives it a new secret.

``POST /token/init`` updates a token when it is called with the serial of a
token that already exists. While the enrollment of that token is still under
way, that is part of the enrollment and only needs the ``enroll<TOKENTYPE>``
action. Once the token is in use, the same request gives it a new secret and
additionally requires this action. Enrolling a new token is unaffected.

.. versionadded:: 3.14

unassign
~~~~~~~~

type: ``bool``

The user is allowed to drop their ownership of the token.
The token does not belong to any user anymore and can be
reassigned.

.. versionadded:: 2.0

resync
~~~~~~

type: ``bool``

The user is allowed to resynchronize the token if it has got out
of synchronization.

.. versionadded:: 2.0

reset
~~~~~

type: ``bool``

The user is allowed to reset the failcounter of the token.

.. versionadded:: 2.0

setpin
~~~~~~

type: ``bool``

The user is allowed to set the OTP PIN for their tokens.

.. versionadded:: 2.0

setrandompin
~~~~~~~~~~~~

type: ``bool``

If the ``setrandompin`` action is defined, the user
is allowed to call the endpoint that sets a random PIN on their
specified token.

The length of the PIN is set by the action ``otp_pin_set_random``; without a
matching ``otp_pin_set_random`` policy the request fails. The current WebUI only
offers the button when both actions apply.

.. versionadded:: 3.2

setdescription
~~~~~~~~~~~~~~

type: ``bool``

The user is allowed to set the description of their tokens.

.. versionadded:: 3.1

enrollpin
~~~~~~~~~

type: ``bool``

If the action ``enrollpin`` is defined, the user
can set a token PIN during enrollment. If the action is not defined and
the user tries to set a PIN during enrollment, the enrollment will fail with a PolicyError.
In versions 3.12 and earlier, the PIN was silently deleted and an enrollment was possible.

.. versionadded:: 2.16

hide_tokeninfo
~~~~~~~~~~~~~~

type: ``string``

This specifies a blank-separated list of tokeninfo keys, which should be removed
from the response and therefore will not be shown in the WebUI or JSON response.

For example a value ``tokenkind auto_renew`` will hide these two tokeninfo entries.

.. versionadded:: 3.7

otp_pin_maxlength
~~~~~~~~~~~~~~~~~

.. index:: PIN policy, Token specific PIN policy

type: ``integer``

range: 0 - 31

This is the maximum allowed PIN length the user is allowed to
use when setting the OTP PIN.

.. note:: There can be token type specific policies like
   ``spass_otp_pin_maxlength``, ``spass_otp_pin_minlength`` and
   ``spass_otp_pin_contents``. If such a token specific policy exists, it takes
   priority over the common PIN policy.

.. versionadded:: 2.2

otp_pin_minlength
~~~~~~~~~~~~~~~~~

type: ``integer``

range: 0 - 31

This is the minimum required PIN length the user must use when setting the
OTP PIN.

.. versionadded:: 2.2

otp_pin_contents
~~~~~~~~~~~~~~~~

type: ``string``

contents: cns

This defines what characters an OTP PIN should contain when the user
sets it.

This takes the same values as the admin policy :ref:`admin_policies_otp_pin_contents`.

.. versionadded:: 2.2

otp_pin_set_random
~~~~~~~~~~~~~~~~~~

type: ``integer``

The length of the PIN generated by the server.

.. versionadded:: 3.2

auditlog
~~~~~~~~

type: ``bool``

This action allows the user to view and search the audit entries recorded for
their user name, realm and resolver. These are not limited to actions on their own
tokens; entries without a resolver or with another resolver are not shown.

To learn more about the audit log, see :ref:`audit`.

.. versionadded:: 2.0

auditlog_age
~~~~~~~~~~~~

type: ``string``

This limits the maximum age of displayed audit entries. Older entries are not
removed from the audit table, but the user is simply not allowed to
view older entries.

Can be something like 10m (10 minutes), 10h (10 hours) or 10d (ten days).

.. versionadded:: 2.17

authentication_log_read
~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

The user is allowed to read their own entries from the
:ref:`authentication_log`. The columns identifying the user are hidden, since
every entry is the user's own. Their own entries are those recorded for their
account - its resolver, user id and realm - rather than those carrying their
login name, see :ref:`authentication_log`.

.. versionadded:: 3.14

hide_audit_columns
~~~~~~~~~~~~~~~~~~

type: ``string``

This specifies a blank separated list of audit columns, that should be removed
from the response (:ref:`rest_audit`) and also from the WebUI.
For example a value ``sig_check log_level`` will hide these two columns.

The list of available columns can be checked by examining the response of the
request to the :ref:`rest_audit`.

.. versionadded:: 3.5

updateuser
~~~~~~~~~~

.. index:: Edit User

type: ``bool``

If the ``updateuser`` action is defined, the user is allowed to change their
attributes in the user store. In the current WebUI users can not edit their user
data; the action applies to the REST API (``PUT /user/``) and to the previous WebUI.

.. note:: To be able to edit the attributes, the resolver must be defined as
   editable.

.. versionadded:: 2.4

userlist
~~~~~~~~

type: ``bool``

If the ``userlist`` action is defined, the user is
allowed to view their own user information.

.. versionadded:: 2.11

.. _user_policy_sshkey_read:

sshkey_read
~~~~~~~~~~~

type: ``bool``

If the ``sshkey_read`` action is defined, the user is allowed to read the
public SSH key of their own SSH key tokens via ``GET /token/sshkey/<serial>``.

The public key of an SSH key token is stored encrypted and is therefore only
contained in encrypted form in the token list, so this action is the way to
retrieve it. Only active tokens hand out their key. See :ref:`sshkey_token`.

.. versionadded:: 3.14

.. _user_policy_serviceid_list:

serviceid_list
~~~~~~~~~~~~~~

type: ``bool``

The user is allowed to list the available service ID definitions via
``GET /serviceid/``. This is required to enroll an application specific
password token, since the enrollment form needs to offer the defined
service IDs to choose from. Defining, changing and deleting a service ID
stays with the administrator. See :ref:`serviceids`.

.. versionadded:: 3.14

revoke
~~~~~~

type: ``bool``

Tokens can be revoked. Usually this means the token is disabled and locked.
A locked token can not be modified anymore. It can only be deleted.

Certain token types like *certificate* may define special actions when
revoking a token.

.. versionadded:: 2.6

.. _policy_password_reset:

password_reset
~~~~~~~~~~~~~~

.. index:: reset password, password reset

type: ``bool``

If the user is located in an editable user store, this policy can define, if
the user is allowed to perform a password reset. During the password reset an
email with a link to reset the password is sent to the user.

This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it
as described in :ref:`legacy_webui`. The current WebUI offers no password reset, and
the link in the email (``/#!/reset/...``) opens its login page. The endpoints of
:ref:`rest_recover` can be used directly.

.. versionadded:: 2.10

.. _user_policy_2step:
.. _hotp-2step:
.. _totp-2step:

hotp_2step and totp_2step
~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

This allows or forces the user to enroll a smartphone based token in two steps.
In the second step the smartphone generates a part of the OTP secret, which the user
needs to enter. (see :ref:`2step_enrollment`).
Possible values are *allow* and *force*.
This works in conjunction with the enrollment parameters :ref:`2step_parameters`.

Such a policy can also be set for the administrator. See :ref:`admin_policy_2step`.

.. note:: This does not work in combination with the enrollment
    policy :ref:`policy_verify_enrollment`, since the usage of 2step already
    ensures that the user has successfully scanned the QR code.

.. versionadded:: 2.21

sms_gateways
~~~~~~~~~~~~

type: ``string``

Usually an SMS token sends the SMS via the SMS gateway that is defined
system-wide in the token settings.
This policy takes a blank separated list of configured SMS gateways.
It allows the user to define an individual SMS gateway during token enrollment.

.. versionadded:: 3.0

.. _user_policy_hashlib:
.. _hotp-hashlib:
.. _totp-hashlib:
.. _daypassword-hashlib:

hotp_hashlib, totp_hashlib and daypassword_hashlib
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

Force the user to enroll HOTP, TOTP or DayPassword tokens with the specified hashlib.
The corresponding input selector will be disabled/hidden in the web UI.
Possible values are *sha1*, *sha256* and *sha512*. Without this policy, the current WebUI presets
*sha1* in the HOTP and TOTP forms (the token configuration value in the DayPassword form) and sends it.
A REST API request that does not send the value gets the value of the token configuration
(``hotp.hashlib``, ``totp.hashlib`` or ``daypassword.hashlib``), or *sha1* if it is not set there.
The previous WebUI presets the hash algorithm from the token configuration.

.. versionadded:: 2.0 ``hotp_hashlib`` and ``totp_hashlib``

.. versionadded:: 3.9 ``daypassword_hashlib``

.. _user_policy_otplen:
.. _hotp-otplen:
.. _totp-otplen:
.. _daypassword-otplen:

hotp_otplen, totp_otplen and daypassword_otplen
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``integer``

Force the user to enroll HOTP, TOTP or DayPassword tokens with the specified OTP length.
The corresponding input selector will be disabled/hidden in the web UI.
Possible values are *6* or *8*. Without this policy, the current WebUI presets *6* and sends it.
A REST API request that does not send the value gets the value of the system configuration
(``DefaultOtpLen``), or *6* if it is not set there. The previous WebUI presets *6*.

.. versionadded:: 2.0 ``hotp_otplen``

.. versionadded:: 2.10 ``totp_otplen``

.. versionadded:: 3.9 ``daypassword_otplen``

.. _user_policy_force-server-generate:
.. _hotp-force-server-generate:
.. _totp-force-server-generate:

hotp-, totp-, daypassword-, applspec- and motp_force_server_generate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

Enforce the key generation on the server. Even if an otp key is passed, the server will generate a new key.

In the web UI, a corresponding input field for the key is disabled/hidden.

Default value is *false*.

.. note:: If two step enrollment :ref:`user_policy_2step` is activated, this policy is not applied.

.. versionadded:: 2.10 ``hotp_force_server_generate`` and ``totp_force_server_generate``

.. versionadded:: 3.9 ``daypassword_force_server_generate``

.. versionadded:: 3.12 ``applspec_force_server_generate`` and ``motp_force_server_generate``

.. _totp-timestep:

totp_timestep
~~~~~~~~~~~~~

type: ``integer``

Enforce the timestep of the time-based OTP token.
A corresponding input selection will be disabled/hidden in the web UI.
Possible values are *30* or *60*. Without this policy, the current WebUI presets *30* and sends it.
A REST API request that does not send the value gets the value of the token configuration
(``totp.timeStep``), or *30* if it is not set there. The previous WebUI presets the time step from
the token configuration.

.. versionadded:: 2.0

.. _daypassword-timestep:

daypassword_timestep
~~~~~~~~~~~~~~~~~~~~

type: ``string``

Enforce the time step of the DayPassword token, for example ``24h``. The value is a number followed by one
of the units *y*, *d*, *h*, *m* or *s*.

.. versionadded:: 3.9

indexedsecret_force_attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

If a user enrolls an indexedsecret token then the value of the given
user attribute is set as the secret.
The user does not see the value and can not change the value.

For more details of this token type see :ref:`indexedsecret_token`.

.. versionadded:: 3.3

.. _user_trusted_attestation_CA:

certificate_trusted_Attestation_CA_path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

A user can enroll a certificate token.
If an attestation certificate is provided in addition, this policy holds the
path to a directory that contains trusted CA paths.
Each PEM encoded file in this directory needs to contain the root CA certificate
at the first position and the consecutive intermediate certificates.
Without this policy the directory ``/etc/privacyidea/trusted_attestation_ca`` is used.

If an attestation certificate is required, see the enrollment policy
:ref:`require_attestation`.

.. versionadded:: 3.5

.. _user_set_custom_user_attributes:

set_custom_user_attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

This defines how a user is allowed to set their own attributes.
It uses the same setting as the admin policy :ref:`admin_set_custom_user_attributes`.
In the current WebUI users can not edit their custom attributes; the action applies to
the REST API (``POST /user/attribute``) and to the previous WebUI.

.. note:: Using a '*' in this setting allows the user to set any attribute or any value and thus the user
   can overwrite existing attributes from the user store. If policies depending on user attributes
   are defined, then the user would be able to change the matching of the policies.
   Use with CAUTION!

.. versionadded:: 3.6

.. _user_delete_custom_user_attributes:

delete_custom_user_attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

This defines how a user is allowed to delete their own attributes.
It uses the same setting as the admin policy :ref:`admin_delete_custom_user_attributes`.
In the current WebUI users can not edit their custom attributes; the action applies to
the REST API (``DELETE /user/attribute/...``) and to the previous WebUI.

.. note:: Using a '*' in this setting allows the user to delete any attribute and thus the user
   can change overwritten attributes and revert to the user store attributes.
   If policies depending on user attributes
   are defined, then the user would be able to change the matching of the policies.
   Use with CAUTION!

.. versionadded:: 3.6

container_state
~~~~~~~~~~~~~~~

type: ``bool``

This action allows the users to edit the states of their own containers.

.. versionadded:: 3.10

container_description
~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows the users to edit the description of their own containers.

.. versionadded:: 3.10

container_create
~~~~~~~~~~~~~~~~

type: ``bool``

This action allows the users to create new containers.

.. versionadded:: 3.10

container_list
~~~~~~~~~~~~~~

type: ``bool``

This action allows the users to list their own containers and read the
properties of containers assigned to them.

.. versionadded:: 3.10

container_delete
~~~~~~~~~~~~~~~~

type: ``bool``

This action allows the users to delete their own containers.

.. versionadded:: 3.10

container_add_token
~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows the users to add their own tokens to their own containers.

.. versionadded:: 3.10

container_remove_token
~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows the users to remove their own tokens from their own containers.

.. versionadded:: 3.10

container_assign_user
~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows users to assign themselves to containers without an owner.

Note that the condition ``realm`` for this action is also evaluated to true if the container is in no realm.

.. versionadded:: 3.10

container_unassign_user
~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows users to unassign themselves from containers.

.. versionadded:: 3.10

container_register
~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows users to generate the QR code for the registration of a container.

.. versionadded:: 3.11

container_unregister
~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows users to unregister a container. This terminates the possibility to synchronize the container
with the server.

.. versionadded:: 3.11

container_rollover
~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows users to perform a rollover of a container and all contained tokens.

.. versionadded:: 3.11

container_template_create
~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows users to create and edit container templates.
Templates have no owner and are shared by all users and administrators: a user with this action can change (and set
as default) every template, including the ones the administrators use.

.. versionadded:: 3.11

container_template_delete
~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows users to delete container templates.
Templates have no owner and are shared by all users and administrators: a user with this action can delete every
template, including the ones the administrators use.

.. versionadded:: 3.11

container_template_list
~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows users to list container templates and see the template properties.
In combination with the ``container_list`` policy, the users are allowed to compare templates with containers.

.. versionadded:: 3.11

hide_container_info
~~~~~~~~~~~~~~~~~~~~

type: ``string``

This specifies a whitespace-separated list of container info keys that should be removed from the response of the
:http:get:`/container/` endpoint and therefore will not be shown in the WebUI on the container details page.

.. versionadded:: 3.12

