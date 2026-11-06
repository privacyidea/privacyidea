.. _add_admin:

Add an administrator
--------------------

privacyIDEA does not come with a pre-defined administrator user.
If you just installed privacyIDEA, you need to create a new one
by running::

   pi-manage admin add admin -e admin@localhost

To configure privacyIDEA, continue with :ref:`login_webui`.

.. note:: This command creates a local administrator. A local administrator logs in
   with a password only, without a second factor. Use it for the first setup. For the
   daily work, set up an admin realm, and then delete the local administrator. See
   :ref:`faq_admins`.

   To give administrators different rights, add admin policies, see
   :ref:`admin_policies`.
