.. _gettoken_policies:

Gettoken policies
-----------------

.. index:: gettoken policies

The scope *gettoken* defines the maximum number of OTP values
that may be retrieved from an OTP token by an administrator.

The user attribute may hold a list of administrators.

Technically, the gettoken policies control the use of the
:ref:`gettoken_controller`.

The following actions are available in the scope 
*gettoken*:

max_count_dpw
~~~~~~~~~~~~~

type: int

This is the maximum number of OTP values that are allowed to be
retrieved from a DPW token.

.. note:: Issuing only one OTP value per day, this means
   that this is the number of days, this OTP list can
   be used.

max_count_hotp
~~~~~~~~~~~~~~

type: int

This is the maximum number of OTP values that are allowed to
be retrieved from an HOTP (HMAC) token.

.. note:: As hotp values only expire, when they are used,
   you can use this to create an OTP list, that can be used
   from the first to the last OTP value.


max_count_totp
~~~~~~~~~~~~~~

type: int

This is the maximum number of OTP balues that are allowed to
be retrieved from a TOTP token.

.. note:: As the default TOTP token generates a new OTP value all
   30 seconds, retrieving 100 OTP values will only give you 
   OTP values, that are usable for 50 minutes.
