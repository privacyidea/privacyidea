.. _webui_policies:

WebUI Policies
--------------

WebUI policies define the behavior of the WebUI.
Changed WebUI policies take effect at the next login: the user has to log out and
log in again. Policies that act on the login page take effect when the login page
is reloaded.

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
Meaning they can not log in with their domain password anymore but need to
authenticate with one of their tokens.

With *privacyIDEA* the WebUI login is checked like an authentication request,
so authentication policies that match the user also apply to it, such as
``passthru``, ``passOnNoToken`` and ``otppin``. With ``passOnNoToken`` a user
without a token logs in with any password, with ``passthru`` with their user
store password.

If set to *login_mode=disable* the users and administrators of the specified
realms can not log in to the UI anymore. This includes the login with a
passkey. The other two values only decide what a password is checked against,
so they do not affect the passkey login. A *disable* policy also refuses the
login if a policy with the same priority sets another login mode. Policies of
the same priority that set *userstore* and *privacyIDEA* also refuse the
password login. With different priorities the policy with the higher priority
(lower number) applies.

.. warning:: If you set this to ``privacyIDEA`` and the user deletes or disables
   all of their tokens, they will not be able to log in anymore, unless an
   authentication policy such as ``passthru`` or ``passOnNoToken`` matches them.

.. note:: Administrators defined in the database using the pi-manage
   command can still log in with their normal passwords.

.. note:: A sensible way to use this is to combine this action in
   a policy with the ``client`` parameter: requiring the users to
   log in to the WebUI remotely from the internet with
   OTP but still log in from within the LAN with the domain password.

.. note:: Another sensible way to use this policy is to *disable* the login to
   the web UI either for certain IP addresses (``client``) or for users in
   certain realms.

.. versionadded:: 2.1

.. index:: remote user
.. _policy_remote_user:

remote_user
~~~~~~~~~~~

type: ``string``

allowed values: ``disable``, ``allowed``, ``force``

This policy defines if the login to privacyIDEA using the web server's
integrated authentication (like basic authentication or digest
authentication) should be allowed.

If set to "allowed" a user can choose to use the REMOTE_USER or log in with
credentials. If set to "force", the user can not switch to logging in with credentials but
can only log in with the REMOTE_USER from the browser.

.. note:: The policy is evaluated before the user is logged in. It is matched
   against the login name and the realm taken from REMOTE_USER (``user@realm``),
   or the default realm if REMOTE_USER contains no realm. A policy restricted to
   another realm or another user does not take effect.

.. note:: The policy setting "force" only works on the UI level. On the API level
   the user could still log in with credentials! If you want to avoid this, see
   the next note.

.. note:: The policies *login_mode* and *remote_user* work independently of each
   other. I.e. you can disable *login_mode* and allow *remote_user*.

You can use this policy to enable Single-Sign-On and integration into Kerberos
or Active Directory. Using the Apache module *mod_auth_gssapi*, add the following
template into your apache configuration
in /etc/apache2/sites-available/privacyidea.conf::

        <Directory />
                Options FollowSymLinks
                AllowOverride None

                SSLRequireSSL
                AuthType GSSAPI
                AuthName "Kerberos Login"
                GssapiCredStore keytab:/etc/apache2/http.keytab
                GssapiBasicAuth On
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

.. versionadded:: 2.8

.. index:: logout time

logout_time
~~~~~~~~~~~

type: ``integer``

Set the timeout, after which a user in the WebUI will be logged out.
The default timeout is 120 seconds.
The time counts from the last activity in the WebUI. Independent of activity, the session ends
when the JWT expires, see :ref:`policy_jwt_validity`.

Being a policy this time can be set based on clients, realms and users.

.. versionadded:: 2.2

.. index:: logout time, timeout

timeout_action
~~~~~~~~~~~~~~

type: ``string``

allowed values: ``lockscreen``, ``logout``, or empty

The action taken when a user is idle beyond the ``logout_time`` limit. Defaults to ``lockscreen``.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`. The WebUI always logs the user out.

.. versionadded:: 2.19

.. index:: Audit view page size

audit_page_size
~~~~~~~~~~~~~~~

type: ``integer``

By default 10 entries are displayed on one page in the audit view.
On big screens you might want to display more entries. Thus you can define in
this policy how many audit entries should be displayed.

.. versionadded:: 3.8

.. index:: Token view page size

token_page_size
~~~~~~~~~~~~~~~

type: ``integer``

By default 15 tokens are displayed on one page in the token view.
On big screens you might want to display more tokens. Thus you can define in
this
policy how many tokens should be displayed.

.. versionadded:: 2.8

.. index:: User view page size

user_page_size
~~~~~~~~~~~~~~

type: ``integer``

By default 15 users are displayed on one page in the user view.
On big screens you might want to display more users. Thus you can define in
this policy how many users should be displayed.

.. versionadded:: 2.8

.. index:: policy template URL
.. _policy_template_url:

policy_template_url
~~~~~~~~~~~~~~~~~~~

type: ``string``

Here you can define a URL from where the policy templates should be fetched.
The default is ``/static/policy-templates/``, which resolves to the bundled
templates shipped with privacyIDEA.

You can point this to an external URL (e.g. ``https://example.com/my-templates/``)
or any other path reachable by the WebUI to provide custom policy templates.
The templates are fetched by the browser, so an external server must allow cross-origin
requests from the privacyIDEA host. With ``PI_ENABLE_CSP`` the content security policy only
allows the privacyIDEA host and the two project hosts it lists (``community.privacyidea.org``,
``privacyidea.readthedocs.io``).

.. note:: When setting a ``policy_template_url`` policy the modified URL will only get
   active after the user has logged out and in again.

.. versionadded:: 2.5

.. index:: logout redirect
.. _policy_logout_redirect:

logout_redirect
~~~~~~~~~~~~~~~

type: ``string``

The URL of an SSO provider, to which the WebUI redirects the user after logout. The URL must start
with ``http://`` or ``https://``.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

.. versionadded:: 3.8

.. index:: Default tokentype
.. _policy_default_tokentype:

default_tokentype
~~~~~~~~~~~~~~~~~

type: ``string``

Defines the default tokentype when enrolling a new token in the WebUI. This
tokentype will be selected when entering the enrollment dialog.

.. versionadded:: 2.8

.. index:: Default Container Type
.. _policy_default_container_type:

default_container_type
~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

Defines the default container type when creating a new container in the WebUI. This container type will be selected
when entering the container create dialog. If this policy is not set, the default type is ``Generic``.

.. versionadded:: 3.11

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

    static/public/customize/token-enrollment.wizard.pre.top.html
    static/public/customize/token-enrollment.wizard.pre.bottom.html
    static/public/customize/token-enrollment.wizard.post.top.html
    static/public/customize/token-enrollment.wizard.post.bottom.html

to display the contents in the first step (pre) or in the second step (post).
The previous WebUI reads the files ``token.enroll.pre.top.html``,
``token.enroll.pre.bottom.html``, ``token.enroll.post.top.html`` and
``token.enroll.post.bottom.html`` from ``static_old/customize/views/includes/``
instead, see :ref:`enrollment_wizard`.

.. note:: In the previous WebUI you can change the directory *static_old/customize* to a URL that fits
   your needs the best by defining a variable ``PI_CUSTOMIZATION`` in the file
   *pi.cfg*. This way you can put all modifications in one place apart from
   the original code. The WebUI always reads the files from ``static/public/customize/``.

If you want to adapt the privacyIDEA look and feel even more, read :ref:`customize`.

.. versionadded:: 2.10

.. index:: Wizard, Token wizard

tokenwizard_2nd_token
~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

The tokenwizard will be displayed in the token menu even if the user already has a token.

.. versionadded:: 2.12

.. _policy_container_wizard_type:

container_wizard_type
~~~~~~~~~~~~~~~~~~~~~

type: ``string``

This policy defines the container type to be used in the container wizard. The container wizard is displayed in the ui
when the user has no container assigned. It shows a simplified view to create the first container. To activate the
container wizard, at least this policy has to be defined. The user also needs the user action ``container_create``
for the wizard. Read :ref:`container_wizard` for more information.

.. versionadded:: 3.11

.. _policy_container_wizard_template:

container_wizard_template
~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

This policy defines the template to be used in the container wizard. Note that the selected template must be of the
same container type as defined in the action ``container_wizard_type``. This policy is optional. If not set, no template
will be used to create the container in the wizard.

.. versionadded:: 3.11

.. _policy_container_wizard_registration:

container_wizard_registration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

In the container wizard, a QR code to register the created container on a smartphone will be displayed. After
registration, the smartphone can be synchronized with the server. See :ref:`container_synchronization` for more
information.
The user also needs the user action ``container_register`` for the registration QR code.
This policy is only applicable for smartphone containers and will be ignored for all other types.

.. versionadded:: 3.11

.. index:: Realm-box, Realm dropdown

realm_dropdown
~~~~~~~~~~~~~~

type: ``string``

If this policy is activated the web UI will display a realm dropdown box.
Of course this policy can not filter for users or realms, since the
user is not known at this moment.

You can set
a space separated list of realm names. Only these realm names are displayed in
the dropdown box, in the order given by the policy. The first realm in the
list is preselected.

You can include ``-`` as an entry in the list to add an empty option to the
dropdown (i.e. authenticate without selecting a specific realm). If ``-`` is
the first entry, the empty option is preselected and the login is sent without
a realm unless the user picks one.

.. versionadded:: 2.12

.. index:: Search on Enter

search_on_enter
~~~~~~~~~~~~~~~

type: ``bool``

The searching in the user list is performed as live search. Each time a key
is pressed, the new substring is searched in the user store.

Sometimes this can be too time consuming. You can use this policy to change
the behavior so that the administrator needs to press *enter* to trigger the
search.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

.. versionadded:: 2.17

user_details
~~~~~~~~~~~~

type: ``bool``

This action adds the user ID and the resolver name to the token list.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

.. versionadded:: 2.8

.. index:: Customize baseline, customize footer
.. _webui_custom_baseline:

custom_baseline
~~~~~~~~~~~~~~~

type: ``string``

The administrator can replace the file ``templates/baseline.html`` with another template.
This way they can change the links to e.g. internal documentation or ticketing systems.
The new file could be called ``mytemplates/mybase.html``.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`. The template ``templates/baseline.html`` is part of the
   previous WebUI.

This policy takes effect as long as the number of assigned active tokens is within the free tier, or with a valid
subscription of privacyIDEA Enterprise Edition. Otherwise it is ignored.

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

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`. The template ``templates/menu.html`` is part of the
   previous WebUI.

This policy takes effect as long as the number of assigned active tokens is within the free tier, or with a valid
subscription of privacyIDEA Enterprise Edition. Otherwise it is ignored.

.. note:: This policy is evaluated before login. So any realm or user setting will have no
   effect. But you can specify different menus for different client IP addresses.

If you want to adapt the privacyIDEA look and feel even more, read :ref:`customize`.

.. versionadded:: 2.21

hide_buttons
~~~~~~~~~~~~

type: ``bool``

Buttons for actions that a user is not allowed to perform are hidden instead of
being disabled.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

.. versionadded:: 3.0

deletion_confirmation
~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

To avoid careless deletion of important configurations, this policy can be
activated. After activation, an additional confirmation for the deletion is
requested for policies, events, mresolvers, resolvers and periodic-tasks.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`. The WebUI always asks for confirmation before deleting these.

.. versionadded:: 3.9

token_rollover
~~~~~~~~~~~~~~

type: ``string``

A whitespace separated list of tokentypes, for which a rollover button is
displayed in the token details. This button will generate a
new token secret for the displayed token.

This e.g. enables a user to transfer a softtoken to a new device while keeping the
token number restricted to 1.

The rollover also requires the action ``token_rollover`` in the user or admin scope (see
:ref:`user_policies` and :ref:`admin_policies`). Without it the current WebUI shows no button, and
the previous WebUI shows one whose request is refused. The current WebUI also shows no button for
token types it can not roll over.

.. versionadded:: 3.6

login_text
~~~~~~~~~~

type: ``string``

This text is displayed on the login page above the login form; in the previous WebUI it replaces the
text "Please sign in". Since the policy can also depend on the IP address of the client, you can also
choose different login texts depending on from where a user tries to log in.

This policy takes effect as long as the number of assigned active tokens is within the free tier, or with a valid
subscription of privacyIDEA Enterprise Edition. Otherwise it is ignored.

.. versionadded:: 3.0

show_android_privacyidea_authenticator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is activated, the enrollment page for HOTP, TOTP and Push tokens
will contain a QR code that leads the user to the Google Play Store where they can
directly install the privacyIDEA Authenticator App for Android devices.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

.. versionadded:: 3.3

show_ios_privacyidea_authenticator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is activated, the enrollment page for HOTP, TOTP and Push tokens
will contain a QR code that leads the user to the Apple App Store where they
can directly install the privacyIDEA Authenticator App for iOS devices.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

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

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

.. versionadded:: 3.3

show_node
~~~~~~~~~

type: ``bool``

If this policy is activated the WebUI displays the name of the privacyIDEA node on the login page
(below the login form) and, after an administrator logs in, in the profile panel at the right end of
the top bar. The self-service views do not show it after login.

This is useful, if you have a lot of different privacyIDEA nodes in a redundant setup or if you have
test instances and production instances. This way you can easily distinguish the different instances.

.. versionadded:: 3.5

show_seed
~~~~~~~~~

type: ``bool``

If this is checked, the token seed will be additionally displayed as text during enrollment.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

.. versionadded:: 3.0

indexedsecret_preset_attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

The secret in the enrollment dialog of the tokentype *indexedsecret* is preset
with the value of the given user attribute.

For more details of this token type see :ref:`indexedsecret_token`.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

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

.. deprecated:: 3.14
   The new WebUI ignores this policy and always shows the dashboard to administrators.
   It only affects the old WebUI and will be removed in a future release.

dialog_no_token
~~~~~~~~~~~~~~~

type: ``bool``

When activated, a welcome dialog will be displayed if a user, who has no token assigned, logs in to the WebUI.
The dialog is contained in the template ``dialog.no.token.html``.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

.. versionadded:: 3.1

hide_welcome_info
~~~~~~~~~~~~~~~~~

type: ``bool``

If this is checked, the administrator will not see the default welcome dialog anymore.

.. versionadded:: 2.20

privacy_statement_link
~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

With this policy you may specify a custom privacy statement link which is displayed
in the WebUI baseline.

.. note:: This applies to the previous WebUI only, which is served when ``pi.cfg`` selects it as
   described in :ref:`legacy_webui`.

This policy takes effect as long as the number of assigned active tokens is within the free tier, or with a valid
subscription of privacyIDEA Enterprise Edition. Otherwise it is ignored.

.. versionadded:: 3.5

.. _policy_rss_feeds:

rss_feeds
~~~~~~~~~

type: ``string``

This policy defines which RSS feeds are displayed in the Web UI to the users or administrators.
The input format is like ``'Feed Name':'URL'-'Another Feed Name':'URL'``. The feed name will be displayed as the title
for the feed defined by the URL. Feed name and url shall be wrapped in single quotes and separated by a colon.
Multiple feeds can be separated by a dash. Note that commas are not allowed in policy actions at all.

The default is:

.. code-block::

    'Community News':'https://community.privacyidea.org/c/news.rss'-'privacyIDEA News':'https://privacyidea.org/feed'-'NetKnights News':'https://netknights.it/en/feed'

Enter the value as one line: a line break between the feeds makes the value unreadable, and the default feeds are
then used without a warning.

This way you can display news feeds from the community, privacyIDEA and NetKnights informing you about new
updates or other critical information.
You can use your own internal news feeds, if you want to provide your own information to users.

.. versionadded:: 3.11

.. _policy_rss_age:

rss_age
~~~~~~~

type: ``integer``

This defines the age of the displayed news feeds. The default is 180 days for administrators and 0 for users, so
users see no news unless a policy sets an age for them. You can specify a different age in days.

.. note:: If you specify the age 0, then the UI tab "News" will be hidden.

.. versionadded:: 3.11

.. _policy_passkey_login:

passkey_login
~~~~~~~~~~~~~~

type: ``string``

Select whether the passkey login button should be visible on the login page.
Allowed values are ``show`` and ``hide``.
The default behavior is to show the passkey login option on the login page.

.. versionadded:: 3.13

.. _policy_jwt_validity:

jwt_validity
~~~~~~~~~~~~

type: ``integer``

privacyIDEA issues a JWT when a user or admin logs in to the WebUI.
The default validity is 1 hour.
You can specify different validity times in seconds.

.. versionadded:: 3.10

.. _policy_session_persistence:

session_persistence
~~~~~~~~~~~~~~~~~~~

type: ``string``

Where the WebUI keeps the session of the logged-in user. Allowed values are ``tab`` and
``browser``, the default is ``tab``. This applies to the current WebUI only. The previous
WebUI keeps no session across page reloads.

With ``tab`` the session belongs to the browser tab it was opened in: it is kept in
``sessionStorage``, ends when that tab is closed, and another tab has to log in for
itself. With ``browser`` the session is kept in ``localStorage``, is shared by all tabs
of the browser and survives closing it, until the JWT expires.

Releases before 3.14 did not keep a WebUI session across a page reload, so after the
upgrade the WebUI starts at the login page whatever the policy says.

The policy is evaluated for the principal that logs in, so admins and users can be given
different values. Note that ``browser`` leaves a token that is usable until its expiry on
the disk of the client, where the next person to open the browser is logged in with it,
and where every same-origin context can read it. The only upper bound on that token is
:ref:`policy_jwt_validity`; see :ref:`new_webui_hardening`.

.. versionadded:: 3.14

