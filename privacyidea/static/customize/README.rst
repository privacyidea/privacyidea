This directory may contain files for the customization of the 
privacyIDEA Web UI.

This directory translates to the URL `/static/customize/`.

If you want to use another directory, you can set the URL 
in `pi.cfg` like:

   PI_CUSTOMIZATION = "/mydirectory"

.. note:: You have to take care, that this directory is 
   served by the Webserver!

The following customizations are possible.

Token Wizard
============

The token wizard expects the following files in the
sub directory `views/includes`:

* token.enroll.pre.top.html
* token.enroll.pre.bottom.html
* token.enroll.post.top.html
* token.enroll.post.bottom.html

Cascading Style Sheets
======================

TODO.
