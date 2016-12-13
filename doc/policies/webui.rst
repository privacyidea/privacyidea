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

.. note:: Administrators defined in the database using the pi-manage
   command can still login with their normal passwords.

.. note:: A sensible way to use this, is to combine this action in
   a policy with the ``client`` parameter: requiring the users to
   login to the Web UI remotely from the internet with
   OTP but still login from within the LAN with the domain password.

.. note:: Another sensible way to use this policy is to *disable* the login to
   the web UI either for certain IP addresses (``client``) or for users in
   certain realms.


remote_user
~~~~~~~~~~~

.. index:: remote_user

type: string

This policy defines, if the login to the privacyIDEA using the web servers
integrated authentication (like basic authentication or digest
authentication) should be allowed.

Possible values are "disable" and "allowed".

.. note:: The policy *login_mode* and *remote_user* work independent of each
   other. I.e. you can disable *login_mode* and allow *remote_user*.
   
You can use this policy to enable Single-Sign-On and integration into Kerberos
or Active Directory. Add the following template into you apache configuration
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
                require valid-user
        </Directory>

        <Location /validate/check>
                Require all granted
                Options FollowSymLinks
                AllowOverride None
        </Location>

        <Location /ttype>
                Require all granted
                Options FollowSymLinks
                AllowOverride None
        </Location>


logout_time
~~~~~~~~~~~

.. index:: logout time

type: int

Set the timeout, after which a user in th WebUI will be logged out.
The default timeout is 120 seconds.

Being a policy this time can be set based on clients, realms and users.


token_page_size
~~~~~~~~~~~~~~~

.. index:: Token view page size

type: int

By default 15 tokens are displayed on one page in the token view.
On big screens you might want to display more tokens. Thus you can define in
this
policy how many tokens should be displayed.

user_page_size
~~~~~~~~~~~~~~

.. index:: User view page size

type: int

By default 15 users are displayed on one page in the user view.
On big screens you might want to display more users. Thus you can define in
this policy how many users should be displayed.




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


.. _policy_default_tokentype:

default_tokentype
~~~~~~~~~~~~~~~~~

.. index:: Default tokentype

type: str

You can define which is the default tokentype when enrolling a new token in
the Web UI. This is the token, which will be selected, when entering the
enrollment dialog.


.. _policy_token_wizard:

tokenwizard
~~~~~~~~~~~

.. index:: Wizard, Token wizard

type: bool

If this policy is set and the user has no token, then the user will only see
an easy token wizard to enroll his first token. If the user has enrolled his
first token and he logs in to the web UI, he will see the normal view.

The user will enroll a token defined in :ref:`policy_default_tokentype`.

Other sensible policies to combine are in :ref:`user_policies` the OTP
length, the TOTP timestep and the HASH-lib.

You can add a prologue and epilog to the enrollment wizard in the greeting
and after the token is enrolled and e.g. the QR code is displayed.

Create the files

 * static/customize/views/includes/token.enroll.pre.top.html
 * static/customize/views/includes/token.enroll.pre.bottom.html
 * static/customize/views/includes/token.enroll.post.top.html
 * static/customize/views/includes/token.enroll.post.bottom.html

to display the contents in the first step (pre) or in the second step (post).

.. note:: You can change the directory *static/customize* to a URL that fits
   your needs the best by defining a variable `PI_CUSTOMIZATION` in the file
   *pi.cfg*. This way you can put all modifications in one place apart from
   the original code.

realm_dropdown
~~~~~~~~~~~~~~

.. index:: Realmbox

type: str

If this policy is activated the web UI will display a realm dropdown box.
Of course this policy can not filter for users or realms, since the
user is not known at this moment.

The type of this action was changed to "string" in version 2.16. You can set
a space separated list of realm names. Only these realmnames are displayed in
the dropdown box.

.. note:: The realm names in the policy are not checked, if they realy exist!

search_on_enter
~~~~~~~~~~~~~~~

.. index:: Search on Enter

type: bool

The searching in the user list is performed as live search. Each time a key
is pressed, the new substring is searched in the user store.

Sometimes this can be too time consuming. You can use this policy to change
the bahaviour that the administrator needs to press *enter* to trigger the
search.

(Since privacyIDEA 2.17)
