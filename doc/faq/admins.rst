.. _faq_admins:

So what's the thing with all the admins?
----------------------------------------

.. index:: admin accounts, pi-manage, local administrator, admin realm, superuser realm

privacyIDEA has two kinds of administrators: local administrators and the
administrators of an admin realm.

.. _faq_local_admins:

Local administrators
~~~~~~~~~~~~~~~~~~~~

Local administrators are stored in the table ``Admin`` of the privacyIDEA
database (:ref:`code_db`). You manage them on the server with
:ref:`pi-manage admin <pimanage_admin>` (see also :ref:`installation`). They log
in to the WebUI with their name and password.

Local administrators are for the first setup and for recovery work:

* They log in with the password from the database. The policy
  :ref:`policy_login_mode` and the authentication policies do not apply to
  them. privacyIDEA can not require a second factor for them.
* A :ref:`policy_remote_user` policy also lets them log in without a password if
  the web server sends ``REMOTE_USER`` with their name. privacyIDEA checks this
  policy with their name and the default realm. Thus a ``remote_user`` policy for
  the default realm also applies to local administrators.
* They are in no realm. A policy with an admin realm does not apply to them, and
  they have no user attributes for ``userinfo`` conditions.

.. warning:: Do not keep local administrators in a production system. They log in
   without a second factor. Set up an admin realm, and make sure that its
   administrators can log in. Then delete the local administrators with
   ``pi-manage admin delete``. For recovery work, create a local administrator
   on the server, and delete it after the work.

.. _faq_admin_realms:

Administrators of an admin realm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All users of an admin realm are administrators. You define the admin realms in
the list ``SUPERUSER_REALM`` in the config file ``pi.cfg``, which is usually
located at ``/etc/privacyidea/pi.cfg``::

   SUPERUSER_REALM = ["adminrealm1", "super", "boss"]

In this case all users of the realms "adminrealm1", "super" and "boss" are
administrators. They log in with their realm, like ``alice@super``.

.. note:: You must create these realms in privacyIDEA (see :ref:`realms`). Only an
   existing realm can give the administrative role to its users.

.. note:: Select the users of an admin realm with care. For example, the resolver
   of the admin realm can read a group of your Active Directory. Then every domain
   administrator of the Active Directory can add administrators to privacyIDEA.

Administrators of an admin realm log in like the other users of their realm:

* :ref:`policy_login_mode` applies. With ``login_mode=privacyIDEA`` they need a
  token, unless an authentication policy like :ref:`passthru_policy` or
  :ref:`passonnotoken` lets them in.
* The authentication policies of their realm apply, for example
  :ref:`otppin_policy`.
* The WebUI policies of their realm apply, and ``userinfo`` conditions read their
  user attributes.

Policies for the two kinds
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * -
     - Local administrator
     - Administrator of an admin realm
   * - Login to the WebUI
     - Password from the privacyIDEA database, or ``REMOTE_USER`` with a
       :ref:`policy_remote_user` policy that applies to the default realm
     - Like a user of the realm: :ref:`policy_login_mode` and the authentication
       policies apply
   * - Second factor
     - Not possible
     - With ``login_mode=privacyIDEA``
   * - *admin realm* of the admin policies
     - Empty
     - The admin realm
   * - *admin user* of the admin policies
     - The login name
     - The login name
   * - Admin policy for the admin realm *super*
     - Does not apply
     - Applies to the administrators of *super*
   * - Admin policy without admin realm, or for the admin realm ``*``
     - Applies
     - Applies
   * - WebUI policies at the login, like ``logout_time``
     - Checked with the login name and an empty realm. privacyIDEA does not check
       the resolver, and ``userinfo`` conditions have no data.
     - Checked as for a user of the admin realm

In the admin policies, *realm*, *resolver*, *user* and ``userinfo`` always refer to
the user on whom the administrator acts, never to the administrator. See
:ref:`admin_policies`.

To write an admin policy for the local administrators only, set the admin realm
to ``*`` and exclude every admin realm, like ``*, !adminrealm1, !super, !boss``.
The WebUI only offers a selection of admin realms, so set such a value through the
API.
