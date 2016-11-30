.. _customize:


Customization
-------------

.. _customize_templates:

Templates
~~~~~~~~~

.. index:: customize, templates, HTML views

You can change the HTML views of the web UI by standard means of the
Apache webserver.

All html views are contained in::

    static/components/<component>/views/<view>.html

If you want to change the look and feel of the UI, we recommend to define
rewrite rules in the webserver. You should create a directory like
*/etc/privacyidea/customization/* and put your modified views in there.
This way you can avoid that your changes get overwritten by a system update.

In the Apache configuration you can add entries like::

    RewriteEngine On
    RewriteRule "/static/components/login/views/login.html"  \
         "/etc/privacyidea/customization/mylogin.html"

and apply all required changes to the file *mylogin.html*.

.. note:: Of course - if there are functional enhancements or bug fixes in the
   original templates - your template will also not be affected by these.

.. _themes:

Themes
~~~~~~

.. index:: themes, CSS, customize

You can create your own CSS file to adapt the look and feel of the Web UI.
The default CSS is the bootstrap CSS theme. Using ``PI_CSS`` you can specify
the URL of your own CSS file.
The default CSS file url is */static/contrib/css/bootstrap-theme.css*.
The file in the file system is located at *privacyidea/static/contrib/css*.
You might add a directory *privacyidea/static/custom/css/* and add your CSS
file there.

A good stating point might be the themes at http://bootswatch.com.

.. note:: If you add your own CSS file, the file *bootstrap-theme.css* will
   not be loaded anymore. So you might start with a copy of the original file.
