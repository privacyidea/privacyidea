.. _tools:

Tools
=====

.. index:: tools

The menu ``tools`` contains some helpful tools to manage your tokens.

Get Serial by OTP value
-----------------------

Here you can enter an OTP value and have the system identify the token.
This can be useful if the printed serial number on the token can not
be read anymore or if the hardware token has not serial number printed
on it at all.

You can choose the

 * tokentype
 * whether the token is an assigned token or not
 * and the realm of the token

to set limits to the token search.

.. warning:: The system needs to got to all tokens and calculate the
   next (default) 10 OTP values. Depending on the number of tokens
   you have in the system this can be very time consuming!

Copy token PIN
--------------

Here you can enter a token serial number of the token from which you
want to copy the OTP PIN and the serial number of the token to which 
you want to copy it.

This function is also used in the lost token scenario.

But the help desk can also use it if the administrator enrolls
a new token to the user and 

1. the user can not set the OTP PIN and
2. the administrator should not set or know the OTP PIN.

Then the administrator can create a second token for the user and
copy the OTP PIN (which only the user knows) of the old token to
the new, second token.

Check Policy
------------

If you have complicated policy settings you can use this dialog to
determine if the policies behave as expected.
You can enter the scope, the real, action user and client to
"simulate" e.g. an authentication request.

The system will tell you if any policy is triggered.

Export token information
------------------------

Here you can export the list of the tokens to a CSV file.

.. note:: In the resolver you can define additional fields,
   that are usually not used by privacyIDEA. But you
   can add those fields to the export. Thus you can e.g.
   add special LDAP attributes in the list of the exported 
   tokens.


Export audit information
------------------------

Here you can export the audit information.

.. warning:: You should limit the export to a number of audit
   entries. As the audit log can grow very big, the export
   of 20.000 audit lines could result in blocking the system.
