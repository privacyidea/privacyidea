.. _translation:

Setup translation
-----------------

The web UI can be translated into different languages. The system determines
the preferred language of your browser and translates the web UI and server
responses accordingly.

We are using weblate to allow the community to participate in translation.

You can go to `hosted.weblate.org <https://hosted.weblate.org/engage/privacyidea/>`_
and check, which languages need support.
This is the most important part you can do: Add words and sentences in your language!

Translations into German are provided by NetKnights while all other languages
are community translated with a fallback to English.

With the parameter ``PI_TRANSLATION_WARNING`` in :ref:`cfgfile` a prefix can be
set to be displayed in front of every string, that is not translated to the
language your browser is using.

By default, all untranslated strings fall back to English.
