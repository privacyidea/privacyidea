.. _webui_policies:

WebUI Policies
--------------

WebUI policies define the behaviour of the WebUI.
After activating WebUI policies, the UI must be reloaded once for the change to
take effect.

.. index:: WebUI Login, WebUI Policy, Login Policy, login mode
.. _policy_login_mode:

login_mode
~~~~~~~~~~

type: ``string``

allowed values: ``userstore``, ``privacyIDEA``, ``disable``

If set to *userstore* (default), users and administrators need to
authenticate with the password of their userstore, being an LDAP service or
an SQL database.

If this action is set to *login_mode=privacyIDEA*, the users and
administrators need to authenticate against privacyIDEA when logging into the WebUI.
Meaning they can not login with their domain password anymore but need to
authenticate with one of their tokens.

If set to *login_mode=disable* the users and administrators of the specified
realms can not login to the UI anymore.

.. warning:: If you set this to `privacyIDEA` and the user deletes or disables
   all of their tokens, they will not be able to login anymore.

.. note:: Administrators defined in the database using the pi-manage
   command can still login with their normal passwords.

.. note:: A sensible way to use this is to combine this action in
   a policy with the ``client`` parameter: requiring the users to
   login to the WebUI remotely from the internet with
   OTP but still login from within the LAN with the domain password.

.. note:: Another sensible way to use this policy is to *disable* the login to
   the web UI either for certain IP addresses (``client``) or for users in
   certain realms.


.. index:: remote user

remote_user
~~~~~~~~~~~

type: ``string``

allowed values: ``disable``, ``allowed``, ``force``

This policy defines if the login to privacyIDEA using the web servers
integrated authentication (like basic authentication or digest
authentication) should be allowed.

If set to "allowed" a user can choose to use the REMOTE_USER or login with
credentials. If set to "force", the user can not switch to login with credentials but
can only login with the REMOTE_USER from the browser.

.. note:: The policy is evaluated before the user is logged in. At this point
   in time there is no realm known, so a policy to allow remote_user must not
   select any realm.

.. note:: The policy setting "force" only works on the UI level. On the API level
   the user could still log in with credentials! If you want to avoid this, see
   the next note.

.. note:: The policy *login_mode* and *remote_user* work independent of each
   other. I.e. you can disable *login_mode* and allow *remote_user*.

You can use this policy to enable Single-Sign-On and integration into Kerberos
or Active Directory. Add the following template into your apache configuration
in /etc/apache2/sites-available/privacyidea.conf::

        <Directory />
                # For Apache 2.4 you need to set this:
                # Require all granted
                Options FollowSymLinks
                AllowOverride None

                SSLRequireSSL
                AuthType Kerberos
                AuthName "Kerberos Login"
                KrbMethodNegotiate On
                KrbMethodK5Passwd On
                KrbAuthRealms YOUR-REALM
                Krb5KeyTab /etc/apache2/http.keytab
                KrbServiceName HTTP
                KrbSaveCredentials On
                <RequireAny>
                    # Either we need a URL with no authentication or we need a valid user
                    <RequireAny>
                        # These URLs do NOT need a basic authentication
                        Require expr %{REQUEST_URI} =~ m#^/validate#
                        Require expr %{REQUEST_URI} =~ m#^/ttype#
                    </RequireAny>
                    Require valid-user
                </RequireAny>
        </Directory>


.. index:: logout time

logout_time
~~~~~~~~~~~

type: ``integer``

Set the timeout, after which a user in the WebUI will be logged out.
The default timeout is 120 seconds.

Being a policy this time can be set based on clients, realms and users.

.. index:: logout time, timeout

timeout_action
~~~~~~~~~~~~~~

type: ``string``

allowed values: ``lockscreen``, ``logout``, or empty

The action taken when a user is idle beyond the ``logout_time`` limit. Defaults to `lockscreen`.

.. index:: Audit view page size

audit_page_size
~~~~~~~~~~~~~~~

type: ``integer``

By default 10 entries are displayed on one page in the audit view.
On big screens you might want to display more entries. Thus you can define in
this policy how many audit entries should be displayed.

.. index:: Token view page size

token_page_size
~~~~~~~~~~~~~~~

type: ``integer``

By default 15 tokens are displayed on one page in the token view.
On big screens you might want to display more tokens. Thus you can define in
this
policy how many tokens should be displayed.

.. index:: User view page size

user_page_size
~~~~~~~~~~~~~~

type: ``integer``

By default 15 users are displayed on one page in the user view.
On big screens you might want to display more users. Thus you can define in
this policy how many users should be displayed.

.. index:: policy template URL
.. _policy_template_url:

policy_template_url
~~~~~~~~~~~~~~~~~~~

type: ``string``

Here you can define a URL from where the policies should be fetched. The
default URL is a Github repository [#defaulturl]_.

.. note:: When setting a template_url policy the modified URL will only get
   active after the user has logged out and in again.

.. [#defaulturl] https://github.com/privacyidea/policy-templates/.


.. index:: Default tokentype
.. _policy_default_tokentype:

default_tokentype
~~~~~~~~~~~~~~~~~

type: ``string``

Defines the default tokentype when enrolling a new token in the WebUI. This
tokentype will be selected when entering the enrollment dialog.

.. index:: Default Container Type
.. _policy_default_container_type:

default_container_type
~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

Defines the default container type when creating a new container in the WebUI. This container type will be selected
when entering the container create dialog. If this policy is not set, the default type is `Generic`.

New in version 3.11

.. index:: Wizard, Token wizard
.. _policy_token_wizard:

tokenwizard
~~~~~~~~~~~

type: ``bool``

If this policy is set and the user has no token, then the user will only see
an easy token wizard to enroll their first token. If the user has enrolled their
first token and they log in to the web UI, they will see the normal view.

The user will enroll a token defined in :ref:`policy_default_tokentype`.

Other sensible policies to combine can be found in the :ref:`user_policies`:
the OTP length, the TOTP timestep and the HASH-lib.

You can add a prologue and epilog to the enrollment wizard in the greeting
and after the token is enrolled and e.g. the QR code is displayed.

Create the files::

    static/customize/views/includes/token.enroll.pre.top.html
    static/customize/views/includes/token.enroll.pre.bottom.html
    static/customize/views/includes/token.enroll.post.top.html
    static/customize/views/includes/token.enroll.post.bottom.html

to display the contents in the first step (pre) or in the second step (post).

.. note:: You can change the directory *static/customize* to a URL that fits
   your needs the best by defining a variable `PI_CUSTOMIZATION` in the file
   *pi.cfg*. This way you can put all modifications in one place apart from
   the original code.

If you want to adapt the privacyIDEA look and feel even more, read :ref:`customize`.

.. index:: Wizard, Token wizard

tokenwizard_2nd_token
~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

The tokenwizard will be displayed in the token menu even if the user already has a token.

.. index:: Realm-box, Realm dropdown

realm_dropdown
~~~~~~~~~~~~~~

type: ``string``

If this policy is activated the web UI will display a realm dropdown box.
Of course this policy can not filter for users or realms, since the
user is not known at this moment.

The type of this action was changed to "string" in version 2.16. You can set
a space separated list of realm names. Only these realm names are displayed in
the dropdown box.

.. note:: The realm names in the policy are not checked, if they really exist!

.. index:: Search on Enter

search_on_enter
~~~~~~~~~~~~~~~

type: ``bool``

The searching in the user list is performed as live search. Each time a key
is pressed, the new substring is searched in the user store.

Sometimes this can be too time consuming. You can use this policy to change
the behaviour so that the administrator needs to press *enter* to trigger the
search.

.. versionadded:: 2.17

user_details
~~~~~~~~~~~~

type: ``bool``

This action adds the user ID and the resolver name to the token list.

.. index:: Customize baseline, customize footer
.. _webui_custom_baseline:

custom_baseline
~~~~~~~~~~~~~~~

type: ``string``

The administrator can replace the file ``templates/baseline.html`` with another template.
This way they can change the links to e.g. internal documentation or ticketing systems.
The new file could be called ``mytemplates/mybase.html``.

This will only work with a valid subscription of privacyIDEA Enterprise Edition.

.. note:: This policy is evaluated before login. So any realm or user setting will have no
   effect. But you can specify different baselines for different client IP addresses.

If you want to adapt the privacyIDEA look and feel even more, read :ref:`customize`.

.. versionadded:: 2.21

.. index:: Customize menu
.. _webui_custom_menu:

custom_menu
~~~~~~~~~~~

type: ``string``

The administrator can replace the file ``templates/menu.html`` with another template.
This way they can change the links to e.g. internal documentation or ticketing systems.
The new file could be called ``mytemplates/mymenu.html``.

This will only work with a valid subscription of privacyIDEA Enterprise Edition.

.. note:: This policy is evaluated before login. So any realm or user setting will have no
   effect. But you can specify different menus for different client IP addresses.

If you want to adapt the privacyIDEA look and feel even more, read :ref:`customize`.

.. versionadded:: 2.21

hide_buttons
~~~~~~~~~~~~

type: ``bool``

Buttons for actions that a user is not allowed to perform are hidden instead of
being disabled.

.. versionadded:: 3.0

deletion_confirmation
~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

To avoid careless deletion of important configurations, this policy can be
activated. After activation, an additional confirmation for the deletion is
requested for policies, events, mresolvers, resolvers and periodic-tasks.

.. versionadded:: 3.9

token_rollover
~~~~~~~~~~~~~~

type: ``string``

A whitespace separated list of tokentypes, for which a rollover button is
displayed in the token details. This button will generate a
new token secret for the displayed token.

This e.g. enables a user to transfer a softtoken to a new device while keeping the
token number restricted to 1.

.. versionadded:: 3.6

login_text
~~~~~~~~~~

type: ``string``

This way the text "Please sign in" on the login dialog can be changed. Since the policy can
also depend on the IP address of the client, you can also choose different login texts depending
on from where a user tries to log in.

.. versionadded:: 3.0

show_android_privacyidea_authenticator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is activated, the enrollment page for HOTP, TOTP and Push tokens
will contain a QR code that leads the user to the Google Play Store where they can
directly install the privacyIDEA Authenticator App for Android devices.

.. versionadded:: 3.3

show_ios_privacyidea_authenticator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is activated, the enrollment page for HOTP, TOTP and Push tokens
will contain a QR code that leads the user to the Apple App Store where they
can directly install the privacyIDEA Authenticator App for iOS devices.

.. versionadded:: 3.3

show_custom_authenticator
~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

If this policy is activated, the enrollment page for HOTP, TOTP and Push tokens
will contain a QR code that leads the user to the given URL.

An organization running privacyIDEA can create its own URL, which could be used
to:

* Show information about the used Authenticator apps.
* Do a device identification and automatically redirect the user to Google Play Store
  or Apple App Store, therefore only needing *one* QR code.
* If an organization has its own customized app or chooses to use another app, lead
  the user to another App in the Google Play Store or Apple App Store.

Other scenarios are possible.

.. versionadded:: 3.3

show_node
~~~~~~~~~

type: ``bool``

If this policy is activated the UI will display the name of the privacyIDEA node in the top left
corner next to the logo.

This is useful, if you have a lot of different privacyIDEA nodes in a redundant setup or if you have
test instances and productive instances. This way you can easily distinguish the different instances.

.. versionadded:: 3.5

show_seed
~~~~~~~~~

type: ``bool``

If this is checked, the token seed will be additionally displayed as text during enrollment.

indexedsecret_preset_attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

The secret in the enrollment dialog of the tokentype *indexedsecret* is preset
with the value of the given user attribute.

For more details of this token type see :ref:`indexedsecret_token`.

.. versionadded:: 3.3

.. index:: admin dashboard, dashboard

.. _webui_admin_dashboard:

admin_dashboard
~~~~~~~~~~~~~~~

type: ``bool``

If this policy is activated, the static dashboard can be accessed by administrators.
It is displayed as a starting page in the WebUI and contains information about
token numbers, authentication requests, recent administrative changes, policies,
event handlers and subscriptions.

.. versionadded:: 3.4

dialog_no_token
~~~~~~~~~~~~~~~

type: ``bool``

When activated, a welcome dialog will be displayed if a user, who has no token assigned, logs in to the WebUI.
The dialog is contained in the template ``dialog.no.token.html``.

hide_welcome_info
~~~~~~~~~~~~~~~~~

type: ``bool``

If this is checked, the administrator will not see the default welcome dialog anymore.

privacy_statement_link
~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

With this policy you may specify a custom privacy statement link which is displayed
in the WebUI baseline.

.. _policy_rss_feeds:

rss_feeds
~~~~~~~~~

type: str

This policy defines which RSS feeds are displayed in the Web UI to the users or administrators.
The input format is like ``'Feed Name':'URL'-'Another Feed Name':'URL'``. The feed name will be displayed as the title
for the feed defined by the URL. Feed name and url shall be wrapped in single quotes and separated by a colon.
Multiple feeds can be separated by a dash. Note that commas are not allowed in policy actions at all.

The default is:

.. code-block::

    'Community News':'https://community.privacyidea.org/c/news.rss'-
    'privacyIDEA News':'https://privacyidea.org/feed'-
    'NetKnights News':'https://netknights.it/en/feed'

This way you can display news feeds from the community, privacyIDEA and NetKnights informing you about new
updates or other critical information.
You can use your own internal news feeds, if you want to provide your own information to users.

.. _policy_rss_age:

rss_age
~~~~~~~

type: int

This defines the age of the displayed news feeds. The default is 180 days. You can specify a different age in days.

.. _note:: If you specify the age 0, then the UI tab "News" will be hidden.
