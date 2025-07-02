.. _register_policy:

Register Policy
---------------

.. index:: policies, register policy, user registration

.. _user_registration:

User registration
.................

Starting with privacyIDEA 2.10 users are allowed to register with privacyIDEA.
I.e. a user that does not exist in a given realm and resolver can create a
new account.

.. note:: Registering new users is only possible, if there is a writeable
   resolver and if the necessary policy in the scope *register* is defined.
   For editable UserIdResolvers see :ref:`useridresolvers`.

If a register policy is defined, the login window of the WebUI gets a new
link "Register".

.. figure:: images/register.png
   :width: 500

   *Next to the login button is a new link 'register', so that new users are
   able to register.*

A user who clicks the link to register a new account gets this registration
dialog:

.. figure:: images/register-dialog.png
   :width: 500

   *Registration form*

During registration the user is also enrolled a
:ref:`registration token<registration_token>`. This registration code is sent
to the user via a notification email.

.. note:: Using the right policies in scope *webui* and *authentication* the
   user could login with the password they set during registration and the
   registration code received via email.


Policy settings
...............

In the scope *register* several settings define the behaviour of the
registration process.

.. figure:: images/register-policy.png
   :width: 500

   *Creating a new registration policy*

realm
~~~~~

type: ``string``

This is the realm, in which a new user will be registered. If this realm is
not specified, the user will be registered in the default realm.

resolver
~~~~~~~~

type: ``string``

This is the resolver, in which the new user will be registered. If this
resolver is not specified, **registration is not possible!**

.. note:: This resolver must be an editable resolver, otherwise the user can
   not be created in this resolver.

smtpconfig
~~~~~~~~~~

type: ``string``

This is the unique identifier of the :ref:`smtpserver`. This SMTP server is
used to send the notification email with the registration code during the
registration process.

.. note:: If there is no *smtpconfig* or set to a wrong identifier, the user
   will get no notification email.

.. _policy_requiredemail:

requiredemail
~~~~~~~~~~~~~

type: ``string``

This is a regular expression according to [#pythonre]_.

Only email addresses matching this regular expression are allowed to register.

**Example**: If you only want to allow email addresses from the domain
*example.com*, a policy might look like this::

   action: requiredemail=/.*@example\.com/

registration_body
~~~~~~~~~~~~~~~~~

type: ``string``

The body of the registration email. Use ``{regkey}`` as tag for the
registration key.


.. [#pythonre] https://docs.python.org/3/library/re.html
