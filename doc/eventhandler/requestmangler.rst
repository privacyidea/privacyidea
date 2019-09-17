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

E.g. you could in certain cases delete the ``transaction_id`` from a
``/validate/check`` request. This way you would render challenge response inactive.

set
...

This action is used to add or modify additional request parameters.

You can set a parameter with the value or substrings of another parameter.

This is why this action takes the additional options *value*, *match_parameter* and
*match_pattern*. *match_pattern* always needs to match the *complete* value of the *match_parameter*.

If you simply want to set a parameter to a fixed value you only need the options:

* *parameter*: as the name of the parameter you want to set and
* *value*: to set to a fixed value.

If you can to set a parameter based on the value of another parameter, you can use the regex notation
**()** and the python string formatting tags **{0}**, **{1}**.

**Example 1**

To set the realm based on the user parameter::

   parameter: realm
   match_parameter: user
   match_pattern: .*@(.*)
   value: {0}

A request like::

   user=surname.givenname@example.com
   realm=

with an empty realm will be modified to::

   user=surname.givenname@example.com
   realm=example.com

since, the pattern ``.*@(.*)`` will match the email address and extract the domain after the "@"
sign. The python tag "{0}" will be replaced with the matching domainname.

**Example 2**

To simply change the domain name in the very same parameter::

   paramter: user
   match_parameter: user
   match_pattern: (.*)@example.com
   value: {0}@newcompany.com

A request like::

   user=surname.givenname@example.com

will be modified to::

   user=surname.givenname@newcompany.com

.. note:: The *match_pattern* in the above example will not match "surname.givenname@example.company",
   since it always matches the complete value as mentioned above.

Code
~~~~


.. automodule:: privacyidea.lib.eventhandler.requestmangler
   :members:
   :undoc-members: