.. _requestmanglerhandler:

RequestMangler Handler Module
-----------------------------

.. index:: RequestMangler, Handler Modules

The RequestMangler is a special handler module, that can modify
the request parameters of an HTTP request.
This way privacyIDEA can change the data that is processed within the request.

Usually this handler is used in the **pre** location. However there might be occasions
when you want to modify parameters only *before* passing them to the next **post** handler.
In this case you can also use the RequestMangler handler in the **post** location.

Possible Actions
~~~~~~~~~~~~~~~~

delete
......

This action simply deletes the given parameter from the request.

E.g. you could in certain cases delete the ``transaction_id`` (and ``state``,
which is accepted in its place) from a ``/validate/check`` request. Answers to a
challenge are then no longer accepted; challenges are still triggered, and SMS,
email or push messages are still sent.

set
...

This action is used to add or modify additional request parameters.

You can set a parameter with the value or substrings of another parameter.

This is why this action takes the additional options *value*, *match_parameter* and
*match_pattern*. *match_pattern* always needs to match the *complete* value of the *match_parameter*.

If you simply want to set a parameter to a fixed value you only need the options:

* *parameter*: as the name of the parameter you want to set and
* *value*: to set to a fixed value.

If you want to set a parameter based on the value of another parameter, you can use the regex notation
**()** and the Python string formatting tags **{0}**, **{1}**.

**Example 1**

To set the realm based on the username parameter::

   parameter: realm
   match_parameter: username
   match_pattern: .*@(.*)
   value: {0}

A request like::

   username=surname.givenname@example.com
   realm=

with an empty realm will be modified to::

   username=surname.givenname@example.com
   realm=example.com

since the pattern ``.*@(.*)`` will match the email address and extract the domain after the "@"
sign. The Python tag "{0}" will be replaced with the matching domain name.

**Example 2**

To simply change the domain name in the very same parameter::

   parameter: username
   match_parameter: username
   match_pattern: (.*)@example.com
   value: {0}@newcompany.com

A request like::

   username=surname.givenname@example.com

will be modified to::

   username=surname.givenname@newcompany.com

.. note:: The *match_pattern* in the above example will not match "surname.givenname@example.company",
   since it always matches the complete value as mentioned above.

**Changing the user of the request**

privacyIDEA determines the user of a request before the event handlers run, and the authentication endpoints
``/validate/check`` and ``/auth`` work with that user. Setting the parameter ``user``, ``username`` or ``realm`` does
not change it, unless the option *reset_user* is checked. The two examples above need it to change who
authenticates. With *reset_user*, the user is determined again from the modified parameters: a ``user@realm`` login
name is split according to the :ref:`splitatsign` setting, and a ``realm`` parameter that the client sent or that a
request mangler definition set takes precedence over the realm in the login name. A new login name without a realm
stays in the realm of the original request (on ``/validate/check`` and ``/auth`` this includes a
:ref:`policy_set_realm` rewrite); elsewhere the default realm is used.

:ref:`conditional_access` is checked for the user of the original request and again for the new user. Other policies
that are checked before the event handlers run still apply to the user of the original request.


A request mangler that can not set the parameter, e.g. because the value names more groups than the match pattern
has, fails the request when the definition has *Abort the request if the handler fails* set, which new request
mangler definitions have, see :ref:`event_abort_on_error`.

Code
~~~~


.. automodule:: privacyidea.lib.eventhandler.requestmangler
   :members:
   :undoc-members:
