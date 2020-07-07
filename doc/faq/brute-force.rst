.. _brute_force:

How to mitigate brute force and lock tokens
-------------------------------------------

.. index:: brute force, fail counter

For each failed authentication attempt privacyIDEA will increase a fail
counter of a token. If the maximum allowed fail counter is reached,
authentication with this token is not possible anymore. The token gets a timestamp
mark, when the maximum fail counter was reached.
Starting with version 2.20 the administrator can define a timeout in minutes.
If the last failed authentication is more than these specified minutes ago,
a successful authentication will reset the fail counter and access will be
granted.
See :ref:`clear_failcounter`.

The failcounter avoids brute force attacks which guess passwords or OTP values.
Choose a failcounter clearing timeout, which is not too long. Otherwise brute
force would also lock the token of the user forever.

Another possibility to mitigate brute force is to define an ``authorization``
policy with the action ``auth_max_fail``. This will check, if there are too
many failed authentication requests during the specified time period. If
there are, even a successful authentication will fail.
This technique uses the audit log, to search for failed authentication requests.
See :ref:`policy_auth_max_fail`.
