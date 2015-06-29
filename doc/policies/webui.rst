.. _webui_policies:

WebUI Policies
--------------

.. index:: WebUI Login, WebUI Policy, Login Policy

.. _policy_login_mode:

login_mode
~~~~~~~~~~

.. index:: login mode

type: string

allowed values: "userstore", "privacyIDEA", "disable"

If set to *userstore* (default), users and administrators need to
authenticate with the password of their userstore, being an LDAP service or
an SQL database.

If this action is set to *login_mode=privacyIDEA*, the users and
administrators need to
authenticate against privacyIDEA when logging into the WebUI.
I.e. they can not login with their domain password anymore
but need to authenticate with one of their tokens.

If set to *login_mode=disable* the users and administrators of the specified
realms can not login to the UI anymore.

.. warning:: If you set this action and the user deletes or disables
   all his tokens, he will not be able to login anymore.

.. note:: Administrators defined in the database using the pi-manage.py
   command can still login with their normal passwords.

.. note:: A sensible way to use this, is to combine this action in
   a policy with the ``client`` parameter: requiring the users to
   login to the Web UI remotely from the internet with
   OTP but still login from within the LAN with the domain password.

.. note:: Another sensible way to use this policy is to *disable* the login to
   the web UI either for certain IP addresses (``client``) or for users in
   certain realms.

logout_time
~~~~~~~~~~~

.. index:: logout time

type: int

Set the timeout, after which a user in th WebUI will be logged out.
The default timeout is 120 seconds.

Being a policy this time can be set based on clients, realms and users.

.. _policy_template_url:

policy_template_url
~~~~~~~~~~~~~~~~~~~

.. index:: policy template URL

type: str

Here you can define a URL from where the policies should be fetched. The
default URL is a Github repository [#defaulturl]_.

.. note:: When setting a template_url policy the modified URL will only get
   active after the user has logged out and in again.

.. [#defaulurl] https://github.com/privacyidea/policy-templates/.
