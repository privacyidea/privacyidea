This directory may contain files for the customization of the 
privacyIDEA Web UI.

This directory translates to the URL `/static/customize/`.

Changing the customization directory
====================================

If you want to use another directory, you can set the URL path
in `pi.cfg` like:

   PI_CUSTOMIZATION = "/mydirectory"

.. note:: You have to take care, that this directory is 
   served by the Webserver!

Example
-------

Your privacyIDEA system is running in the URL sub path ``/pi``.
The files could be addressed via a path component ``mydesign`` (in this case ``pi/mydesign``).
Thus the WebUI will look for the files in the URL path ``/pi/mydesign/``.

So you set in ``pi.cfg``:

    PI_CUSTOMIZATION = "/mydesign"

Your customized files are located in ``/etc/privacyidea/customize/``.
In the Apache webserver you need to map ``/pi/mydesign`` to ``/etc/privacyidea/customize``:

    Alias /pi/mydesign /etc/privacyidea/customize

Available customizations
========================

The following customizations are possible.

Token Wizard
------------

The token wizard expects the following files in the
sub directory ``views/includes``:

* ``token.enroll.pre.top.html``
* ``token.enroll.pre.bottom.html``
* ``token.enroll.post.top.html``
* ``token.enroll.post.bottom.html``

Paper Token
-----------

The paper token expects:

* ``token.enrolled.paper.top.html``
* ``token.enrolled.paper.bottom.html``

Cascading Style Sheets
----------------------

CSS customization can be enabled using the ``PI_CUSTOM_CSS``-setting in ``pi.cfg`` and expects a file called
``custom.css`` in the sub directory ``css``.

**Example**

PrivacyIDEA's UI was recently update to better utilize the available screen real-estate of large devices. If you prefer
the old look, you can limit the width of the app by overriding the relevant parts. Simply set ``PI_CUSTOM_CSS = True`` in
your ``pi.cfg`` and add a file called ``css/custom.css``, with the following content:

    @media (min-width: 1440px) { .container { width: 1400px!important; } }
