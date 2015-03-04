.. _webui_policies:

WebUI Policies
--------------

.. index:: WebUI Login, WebUI Policy, Login Policy

login_mode
~~~~~~~~~~

type: string

allowed values: "userstore", "privacyIDEA"

If this action is set to *login_mode=privacyIDEA*, the users and
administrators need to
authenticate against privacyIDEA when logging into the WebUI.
I.e. they can not login with their domain password anymore
but need to authenticate with one of their tokens.

.. warning:: If you set this action and the user deletes or disables
   all his tokens, he will not be able to login anymore.

.. note:: Administrators defined in the database using the pi-manage.py
   command can still login with their normal passwords.

.. note:: A sensible way to use this, is to combine this action in
   a policy with the ``client`` parameter: requiring the users to
   login to the Web UI remotely from the internet with
   OTP but still login from within the LAN with the domain password.

