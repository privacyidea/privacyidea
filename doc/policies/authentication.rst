.. _authentication_policies:

Authentication policies
-----------------------

.. index:: authentication policies

The scope *authentication* gives you more detailed
possibilities to authenticate the user or to define 
what happens during authentication.

Technically the authentication policies apply
to the REST API :ref:`rest_validate` and are checked
using :ref:`code_policy` and
:ref:`policy_decorators`.

The following actions are available in the scope 
*authentication*:

.. _otppin_policy:

otppin
~~~~~~

type: string

This action defines how the fixed password part during
authentication should be validated.
Each token has its own OTP PIN, but you can choose 
how the authentication should be processed:

``otppin=tokenpin``

   This is the default behaviour. The user needs to
   pass the OTP PIN concatenated with the OTP value.

``otppin=userstore``

   The user needs to pass the user store password
   concatenated with the OTP value. It does not matter
   if the OTP PIN is set or not.
   If the user is located in an Active Directory the user
   needs to pass his domain password together with the
   OTP value.

.. note:: The domain password is checked with an LDAP
   bind right at the moment of authentication. 
   So if the user is locked or the password was
   changed authentication will fail.

``otppin=none``

   The user does not have to pass any fixed password.
   Authentication is only done via the OTP value.

.. _passthru_policy:

passthru
~~~~~~~~

.. index:: passthru, migration

type: str

If the user has no token assigned, he will be authenticated
against the userstore or against the given RADIUS configuration.
I.e. the user needs to provide the LDAP- or SQL-password or valid credentials
for the RADIUS server.

.. note:: This is a good way to do a smooth enrollment.
   Users having a token enrolled will have to use the 
   token, users not having a token, yet, will be able
   to authenticate with their domain password.

   It is also a way to do smooth migrations from other OTP systems.
   The authentication request of users without a token is forwarded to the
   specified RADIUS server.

.. warning:: If the user has the right to delete his
   tokens in selfservice portal, the user could 
   delete all his tokens and then authenticate with
   his static password again.

passOnNoToken
~~~~~~~~~~~~~

.. index:: passOnNoToken

type: bool

If the user has no token assigned an authentication request
for this user will always be true.

.. warning:: Only use this if you know exactly what
   you are doing.

passOnNoUser
~~~~~~~~~~~~

.. index:: passOnNoUser

type: bool

If the user does not exist, the authentication request is successful.

.. warning:: Only use this if you know exactly what you are doing.



smstext
~~~~~~~

.. index:: SMS policy, SMS text

type: string

This is the text that is sent via SMS to the user trying to
authenticate with an SMS token.
You can use the tags *<otp>* and *<serial>*.

Default: *<otp>*

smsautosend
~~~~~~~~~~~

.. index:: SMS automatic resend

type: bool

A new OTP value will be sent via SMS if the user authenticated
successfully with his SMS token. Thus the user does not
have to trigger a new SMS when he wants to login again.


emailtext
~~~~~~~~~

.. index:: EMail policy, Email text

type: string

This is the text that is sent via Email to be used with Email Token. This
text should contain the OTP value.
You can use the tags *<otp>* and *<serial>*.

Default: *<otp>*

emailsubject
~~~~~~~~~~~~

.. index:: Email policy, Email subject

type: string

This is the subject of the Email sent by the Email Token.
You can use the tags *<otp>* and *<serial>*.

Default: Your OTP

emailautosend
~~~~~~~~~~~~~

.. index:: Email policy

type: bool

If set, a new OTP Email will be sent, when successfully authenticated with an
Email Token.


.. _policy_mangle:

mangle
~~~~~~

.. index:: Mangle authentication request, Mangle policy

type: string

The ``mangle`` policy can mangle the authentication request data before they
are processed. I.e. the parameters ``user``, ``pass`` and ``realm`` can be
modified prior to authentication.

This is useful if either information needs to be stripped or added to such a
parameter.
To accomplish that, the mangle policy can do a regular expression search and
replace using the keyword *user*, *pass* (password) and *realm*.

A valid action could look like this::

   action: mangle=user/.*(.{4})/user\\1/

This would modify a username like "userwithalongname" to "username", since it
would use the last four characters of the given username ("name") and prepend
the fixed string "user".

This way you can add, remove or modify the contents of the three parameters.
For more information on the regular expressions see [#pythonre]_.

.. note:: You must escape the backslash as **\\\\** to refer to the found
   substrings.

**Example**: A policy to remove whitespace characters from the realm name would
look like this::

   action: mangle=realm/\\s//

**Example**: If you want to authenticate the user only by the OTP value, no
matter what OTP PIN he enters, a policy might look like this::

   action: mangle=pass/.*(.{6})/\\1/

**Example**: If you want to strip a string from the front of a username, for
example to have "admin_username" resolve to just "username", it would look like
this::

   action: mangle=user/admin_(.*)/\\1/

.. _policy_challenge_response:

challenge_response
~~~~~~~~~~~~~~~~~~

type: string

This is a list of token types for which challenge response can
be used during authentication. The list is separated by whitespaces like
*"hotp totp"*.

.. note:: The TiQR token does not need this setting, since it always works with
   challenge response.

.. _policy_u2f_facets:

u2f_facets
~~~~~~~~~~

type: string

This is a white space separated list of domain names, that are trusted to
also use a U2F device that was registered with privacyIDEA.

You need to specify a list of FQDNs without the https scheme like:

*"host1.example.com host2.exmaple.com firewall.example.com"*

For more information on configuring U2F see :ref:`u2f_otp_token`.


.. [#pythonre] https://docs.python.org/2/library/re.html


reset_all_user_tokens
~~~~~~~~~~~~~~~~~~~~~

type: bool

If a user authenticates successfully all failcounter of all of his tokens
will be reset. This can be important, if using empty PINs or *otppin=None*.
