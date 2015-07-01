.. _faq:

Frequently Asked Questions
==========================

.. index:: FAQ

How can I create users in the privacyIDEA Web UI?
-------------------------------------------------

So you installed privacyIDEA and want to enroll tokens to the users and are
wondering how to create users.

privacyIDEA itself does not manage users and therfor you do not need to
create users.

You very much likely already have an application (like your VPN or a Web
Application...) for which you want to increase the logon security. Then this
application already knows users. Either in an LDAP or in an SQL database.
Most web applications keep their users in a (My)SQL database.
And you also need to create users in this very user database for the user to
be able to use this application.

So there is no sense in creating the user in the application **and** in
privacyIDEA. Right?

This is why you can not create users in privacyIDEA but you only need to tell
privacyIDEA where the users are located
and you can start enrolling tokens to those users.

Please read the sections :ref:`useridresolvers` and :ref:`userview` for more
details.

So what's the thing with all the admins?
----------------------------------------

.. index:: admin accounts, pi-manage

privacyIDEA comes with its own admins, who are stored in a database table
``Admin`` in its own database (:ref:`code_db`). You can use the tool
``pi-manage.py`` to
manage those admins from the command line as the system's root user. (see
:ref:`installation`)

These admin users can logon to the WebUI using the admin's user name and the
specified password.
These admins are used to get a simple quick start.

Then you can define realms (see :ref:`realms`), that should be administrative
realms. I.e. each user in this realm will have administrative rights in the
WebUI.

.. note:: Use this carefully. Imagine you defined a resolver to a specific
   group in your Active Directory to be the pricacyIDEA admins. Then the Active
   Directory domain admins can
   simply add users to be administrator in privacyIDEA.

You define the administrative realms in the config file ``pi.cfg``, which is
usually located at ``/etc/privacyidea/pi.cfg``::

   SUPERUSER_REALM = ["adminrealm1", "super", "boss"]

In this case all the users in the realms "adminrealm1", "super" and "boss"
will have administrative rights in the WebUI, when they login with this realm.

As for all other users, you can use the :ref:`policy_login_mode` to define,
if these administrators should login to the WebUI with their userstore password
or with an OTP token.

What are possible rollout strategies?
-------------------------------------

.. index:: rollout strategy

There are different ways to enroll tokens to a big number of users.
Here are some selected high level ideas, you can do with privacyIDEA.

Autoenrollment
~~~~~~~~~~~~~~

Using the :ref:`autoassignment` policy you can distribute physical tokens to
the users. The users just start using the tokens.

.. _faq_registration_code:

Registration Code
~~~~~~~~~~~~~~~~~

If your users are physically not available and spread around the world, you can
send a registration code to the users by postal mail. The registration code
is a special token type which can be used by the user to authenticate with 2FA.
If used once, the registration token get deleted and can not be used anymore.
While logged in, the user can enroll a token on his own.

How can I translate to my language?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The web UI can be translated into different languages. The system determines
the preferred language of you browser and displays the web UI accordingly.

At the moment "en" and "de" are available.

Setup translation
.................
The translation is performed using grunt. To setup the translation
environment do::

   npm update -g npm
   # install grunt cli in system
   sudo npm install -g grunt-cli

   # install grunt in project directory
   npm install grunt --save-dev
   # Install grunt gettext plugin
   npm install grunt-angular-gettext --save-dev

This will create a subdirectory *node_modules*.

To simpley run the German translatio do::

   make translate

If you want to add a new language like Spanish do::

   cd po
   msginit -l es
   cd ..
   grunt nggettext_extract
   msgmerge po/es.po po/template.pot > po/tmp.po; mv po/tmp.po po/es.po

Now you can start translating with your preferred tool::

   poedit po/es.po

Finally you can add the translation to the javascript translation file
``privacyidea/static/components/translation/translations.js``::

   grunt nggettext_compile

.. note:: Please ask to add this translation to the Make directive
   *translation* or issue a pull request.



