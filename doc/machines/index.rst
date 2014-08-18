.. _machines:

Client machines
===============

.. index:: machines, client machines

.. note:: This is a very new concept and work in progress. It may enhance rapidly in future.

privacyIDEA lets you define client machines. The idea is for users to be able to authenticate
on those client machines.
Not in all cases an online authentication request is possible, so that authentication items
can be passed to those client machines.

In addition you need to define, which application on the client machine the user should authenticate
to. Different application require different authentication items.

Therefore privacyIDEA can define application types. At the moment privacyIDEA knows the application 
``luks` and ``ssh``. You can write your own application class, which is defined in 
:ref:``code_application_class``.

You need to assign an application and a token to a client machine. Each application type 
can work with certain token types and each application type can use additional parameters.

.. note:: Not all tokens work well with all applications!

SSH
---

Currently working token types: SSH

Parameters:

``user`` (optional, default=root)

When the SSH token type is assigned to a client, the user specified in the user paramter
can login with the private key of the SSH token.

To enroll SSH tokens to the client systems you have to use the privacyIDEA admin client.

To distribute the SSH tokens the privacyIDEA admin client uses salt [#saltstack]_.

In version 1.3 the command line interface of the admin client was heavily improved, so
that you can simply distribute the SSH keys by calling the following command on the
salt master::

   privacyidea-ssh-assign @secrets.txt

This script will call all SSH authentication items and will use salt to push these 
to the clients.

The ``secrets.txt`` file contains the connection data to the privacyIDEA server.

Thus you can check the access rights of ``secrets.txt`` and use this call in a 
cron job.

The secrets.txt just takes the command line parameters and might look like this::
   
   --url
   https://localhost:5001
   --admin
   admin@admin
   --password
   secretPassword


LUKS
----

Currently working token types: Yubikey Challenge Response

Parameters:

``slot`` The slot to which the authentication information should be written

``partition`` The encrypted partition (usually /dev/sda3 or /dev/sda5)

These authentication items need to be pulled on the client machine from
the privacyIDEA server.

Thus, the following script need to be executed with root rights (able to
write to LUKS) on the client machine::

   privacyidea-luks-assign @secrets.txt --cleanslot --name salt-minion

For more information please see the man page of this tool.



.. [#saltstack] http://www.saltstack.com/
