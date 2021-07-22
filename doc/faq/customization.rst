.. _customize:


Customization
-------------

There are several different ways to customize the UI of privacyIDEA.

.. _customize_templates:

Templates
~~~~~~~~~

.. index:: customize, templates, HTML views

You can change the HTML templates of the web UI as follows.
You can create a copy of the orignial templates, modify them and use rewrite rules of your webserver
to call your new, modified templates.

This way updates will not affect your modifications.

All HTML views are contained in::

    static/components/<component>/views/<view>.html

You can find them on `GitHub <https://github.com/privacyidea/privacyidea/tree/master/privacyidea/static>`_
or at the according location in your installation.

Follow these basic steps:

1. Create a new location, where you will keep your modifications safe from updates.
   You should create a directory like
   */etc/privacyidea/customization/* and put your modified views in there.

2. Activate the rewrite rules in your web server.
   E.g. in the Apache configuration you can add entries like::

    RewriteEngine On
    RewriteRule "/static/components/login/views/login.html"  \
         "/etc/privacyidea/customization/mylogin.html"

   and apply all required changes to the file *mylogin.html*.

   .. note:: In this case you need to create a ``RewriteRule`` for each file, you
       want to modify.

3. Now activate ``mod_rewrite`` and reload apache2.

.. warning:: Of course - if there are functional enhancements or bug fixes in the
   original templates - your template will also not be affected by these.


Translating templates
.....................

The translation in privacyIDEA is very flexible (see :ref:`translation`).
But if you change the templates the normal translation with PO files can
get a bit tricky.

Starting with privacyIDEA 3.0.1 you can use the scope variable
``browserLanguage`` in your custom templates.

You can print the browser language like this ``{{ browserLanguage }}``.

And you can display text in different languages in ``divs`` like this::

    <div ng-show="browserLanguage === 'de'">
        Das ist ein deutscher Text.
    </div>
    <div ng-show="browserLanguage === 'en'">
        This is an English text.
    </div>


.. _themes:

Themes
~~~~~~

.. index:: themes, CSS, customize

You can adapt the style and colors by changing CSS. There are at least two ways to do this.

Providing your own stylesheet in the config file
................................................

You can create your own CSS file to adapt the look and feel of the Web UI.
The default CSS is the bootstrap CSS theme. Using ``PI_CSS`` in ``pi.cfg`` you can specify
the URL of your own CSS file.
The default CSS file url is */static/contrib/css/bootstrap-theme.css*.
The file in the file system is located at *privacyidea/static/contrib/css*.
You might add a directory *privacyidea/static/custom/css/* and add your CSS
file there.

The CSS you specify here adds to the already existing styles. Thus a convenient way for
using this setting is to help you distinguish different privacyIDEA instances like "testing", "acceptances"
and "production" or different nodes in a redundant setup.

You can create a simple CSS file *[..]/privacyidea/static/custom/css/testing.css* like::

    body {
        background-color: green;
    }

and then set in the pi.cfg::

    PI_CSS = "/static/custom/css/testing.css"

This way your testing instance will be immediately distinguishable due to the green background.

Use web server rewrite modules
..............................

Again you can also use the Apache rewrite module to replace the original css file::

    RewriteEngine On
    RewriteRule "/static/contrib/css/bootstrap-theme.css"  \
         "/etc/privacyidea/customization/my.css"


A good stating point might be the themes at http://bootswatch.com.

.. note:: If you add your own CSS file, the file *bootstrap-theme.css* will
   not be loaded anymore. So you might start with a copy of the original file.


Use web server substitute module
................................

You can also use the substitute module of the Apache webserver.
It is not clear how much performance impact you get, since this
module can scan and replace any text that is delivered by the web server.

If you for example want to replace the title of the webpages, you could
do it like this::

       <Location "/">
           AddOutputFilterByType SUBSTITUTE text/html
           Substitute "s/>privacyidea Authentication System</>My own 2FA system</ni"
       </Location>


.. _customize_logo:

Logo
~~~~

The default logo is located at ``privacyidea/static/css/privacyIDEA1.png``.
If you want to use your own logo, you can put your file "mylogo.png" just
in the same folder and set

   PI_LOGO = "mylogo.png"

in the ``pi.cfg`` config file.

.. _customize_menu:

Page title
~~~~~~~~~~

You can configure the page title by setting ``PI_PAGE_TITLE`` in the
``pi.cfg`` file.

Menu
~~~~

The administrator can adapt the menu of the web UI using policies or of course web server rewrite
rules. The original menu is located in ``static/templates/menu.html``.

Note that policies are also dependent on the client IP, this way different
clients could see different menus.

Read more about it at the web UI policies at the :ref:`webui_custom_menu`.

Headers and Footers
~~~~~~~~~~~~~~~~~~~

The administrator can change the header and footer of each page. We call this the baseline of the
web UI. The original baseline is contained in ``static/templates/baseline.html``.
You can use a web UI policy to change this baseline or - of course - could use the web server
rewrite module.

Read more about changing it via the web UI policies at :ref:`webui_custom_baseline`.

.. _customize_tokenwizard:

Tokenwizard
~~~~~~~~~~~

You can add additional HTML elements above and underneath the enrollment wizard pages.
Read the :ref:`enrollment_wizard` and :ref:`policy_token_wizard`
to learn more about those code snippets.

Token customization
~~~~~~~~~~~~~~~~~~~

Some tokens allow a special customization.

The paper token allows you to add CSS for styling the printed output and
add additional headers and footers. Read more about it at the
paper token :ref:`paper_token_customize`.

.. _customize_3rd_party_tokens:

New token classes
~~~~~~~~~~~~~~~~~

You can add new token types to privacyIDEA by writing your own Python token class.
A token class in privacyIDEA is
inherited from ``privacyidea.lib.tokenclass.TokenClass``. You can either inherit from
this base class directly or from another token class. E.g. the *TOTP* token class is inherited from
*HOTP*. Take a look in the directory *privacyidea/lib/tokens/* to get an idea of token classes.

A token class can have many different methods which you can find in the base class ``TokenClass``.
Depending on the token type you are going to implement, you will need to implement several of these.
Probably the most important methods are ``check_otp``, which validates the 2nd factor and the
method ``update``, which is called during the initialization process of the token and
gathers and writes all token specific attributes.

You should only add one token class per Python module.

You can install your new Python module, wherever you want to like ``myproject.cooltoken``.

If these tokens need additional enrollment data in the UI, you can specify
two templates, that are displayed during enrollment and after the token
is enrolled. These HTML templates need to be located at
``privacyidea/static/components/token/views/token.enroll.<tokentype>.html``
and
``privacyidea/static/components/token/views/token.enrolled.<tokentype>.html``.

.. Note:: In this example the python module ``myproject.cooltoken`` should
   contain a class ``CoolTokenClass``. The tokentype of this token, should
   be named "cool". And thus the HTML templates included by privacyIDEA
   are ``token.enroll.cool.html`` and ``token.enrolled.cool.html``.

The list of the token modules you want to add, must be specified in ``pi.cfg``.
See :ref:`picfg_3rd_party_tokens`.

Custom Web UI
~~~~~~~~~~~~~

You can also write your complete new WebUI.
To do so you need to specify files and folders in ``pi.cfg``.
Read more about this at :ref:`custom_web_ui`.