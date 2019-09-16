.. _responsemanglerhandler:

ResponseMangler Handler Module
------------------------------

.. index:: ResponseMangler, Handler Modules

The ResponseMangler is a special handler module, that can modify
the response of an HTTP request.
This way privacyIDEA can change the data sent back to the client, depending
on certain conditions.

All actions take a JSON pointer, which looks like a path variable like
``/result/value``.

Possible Actions
~~~~~~~~~~~~~~~~

delete
......

This action simply deletes the given JSON pointer from the response.

.. note:: All keys underneath a node are deleted, to. So if the event handler
   deletes ``/detail``, the entries ``/detail/message`` and ``/detail/error``will
   also be deleted.

**Example**

You can use this to delete ``/detail/googleurl``, ``/detail/oathurl`` and ``/detail/otpkey``
in a ``/token/init`` event to hide the created QR code from the helpdesk admin.
This way the QR code could be used internally, but could be hidden from
the administrator.


set
...

This action is used to add additional pointers to the JSON response
or to modify existing entries. Existing entries are overwritten.

This action takes the additional attributes ``type`` and ``value``.

The value can be returned as a string, an integer or a boolean.

Code
~~~~


.. automodule:: privacyidea.lib.eventhandler.responsemangler
   :members:
   :undoc-members:
