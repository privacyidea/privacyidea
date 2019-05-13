.. _translation:

Setup translation
-----------------
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

To simply run the German translation do::

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
